"""IT-32: Proper HC optimizer (matching methodology's protocol).

Methodology's HC: 150 iterations of bit-flipping on W[0] (or W[0..15]?) with
objective STATE_SUM at round 62 MINIMIZE.

Per methodology:
  Start: random W[0..15]
  Step: flip random bit, compute STATE_SUM[r=62]
  If STATE_SUM decreased → accept, else revert
  After 150 iters: W[0..15] with low STATE_SUM
  → carry[62]=0 with high probability
  → biased hash output at H[6][b28..b31], H[7][b29] with methodology's phi

Vectorized HC: run N_PARALLEL samples in parallel, each with independent
bit flips. Each iteration = 1 batch SHA through round 62.

Goal: reproduce methodology's biased-bit pattern, then apply OUR H[5] bits
and Ω_3 on this distribution. Check if combined advantage > 0.30.
"""
import json, math, os, subprocess, tempfile, time
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')

N_SAMPLES = 20000    # parallel HC samples (smaller than 130K due to HC compute cost)
N_ITERS = 80         # HC iterations (methodology used 150, we use 80 for time)


def state_sum_r62(inputs):
    """Compute STATE_SUM at round 62 of block 2 compression."""
    N = inputs.shape[0]
    b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, 64), dtype=U32); W[:, :16] = pad_block
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (s1[:, i].copy() for i in range(8))
    K = ch.K_VANILLA
    for t in range(62):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    ss = (a.astype(np.uint64) + b.astype(np.uint64) + c.astype(np.uint64)
          + d.astype(np.uint64) + e.astype(np.uint64) + f.astype(np.uint64)
          + g.astype(np.uint64) + h.astype(np.uint64))
    return ss


def hc_optimize(N_parallel, n_iters, rng):
    """Parallel HC: minimize STATE_SUM[r=62] by flipping bits in W[0] word."""
    # Inputs as 64-byte arrays; we flip bits in first 4 bytes (W[0])
    inputs = rng.integers(0, 256, size=(N_parallel, 64), dtype=np.uint8)
    ss_current = state_sum_r62(inputs)
    accepts = 0
    print(f"# HC start: N={N_parallel}, iters={n_iters}")
    print(f"  initial STATE_SUM mean: {ss_current.mean():.3e}, min: {ss_current.min():.3e}")
    for it in range(n_iters):
        # Flip random bit in first 64 bits (W[0]..W[1]) per sample
        # Flip more bits early, fewer later (simulated annealing-ish)
        bits_to_flip_per_sample = max(1, (n_iters - it) // (n_iters // 3 + 1))
        # Simple: flip 1 bit per sample per iter
        trial = inputs.copy()
        # Random bit position in first 8 bytes (W[0..1])
        byte_idx = rng.integers(0, 8, size=N_parallel)
        bit_idx = rng.integers(0, 8, size=N_parallel)
        for i in range(N_parallel):
            trial[i, byte_idx[i]] ^= (1 << bit_idx[i])
        ss_trial = state_sum_r62(trial)
        # Accept if lower
        better = ss_trial < ss_current
        inputs = np.where(better[:, None], trial, inputs)
        ss_current = np.where(better, ss_trial, ss_current)
        accepts += better.sum()
        if (it + 1) % 10 == 0:
            print(f"  iter {it+1}/{n_iters}: mean SS = {ss_current.mean():.3e}, "
                  f"accept_rate = {accepts/((it+1)*N_parallel):.3f}")
    return inputs, ss_current


def compute_full_hash(inputs):
    N = inputs.shape[0]
    b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))
    s2 = ch.compress(s1, pad_block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return s1, s2


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v):
    pd = np.zeros(WORDS*64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def tv_dist(phi_arr):
    k = len(phi_arr)
    if k > 18: return None
    tv = 0
    for mask in range(2**k):
        p_sha = 1.0
        for i in range(k):
            if (mask >> i) & 1: p_sha *= 0.5 + phi_arr[i]
            else: p_sha *= 0.5 - phi_arr[i]
        tv += abs(p_sha - 0.5**k)
    return tv / 2


def main():
    t0 = time.time()
    rng = np.random.default_rng(0x1337ABBA)
    print(f"# IT-32: proper HC optimizer + combined distinguisher")

    # Step 1: HC optimize
    ts = time.time()
    inputs_hc, ss_final = hc_optimize(N_SAMPLES, N_ITERS, rng)
    print(f"# HC done: {time.time()-ts:.0f}s, final mean SS = {ss_final.mean():.3e}")
    print(f"  Fraction with SS < 1.1e9 (methodology threshold): {(ss_final < 1.1e9).mean():.3f}")

    # Step 2: compute full hash
    print(f"\n# Computing full hashes on HC-optimized inputs...")
    s1, s2 = compute_full_hash(inputs_hc)
    N = N_SAMPLES
    s2b = sb(s2, N)
    s1b = sb(s1, N)

    # Step 3: measure phi per bit
    phi = s2b.sum(axis=0) / N - 0.5
    z = phi / (0.5 / np.sqrt(N))

    print(f"\n=== Top significant bits on HC-optimized inputs ===")
    sig_idx = np.argsort(-np.abs(z))
    for i in sig_idx[:20]:
        w, off = i // 32, i % 32
        star = '★' if i in [220, 221, 223, 253] else (' ☆' if 160 <= i <= 167 else '  ')
        print(f" {star} bit {i:>3} H[{w}][b{off:>2}] phi={phi[i]:+.5f} z={z[i]:+.2f}")

    meth_bits = {'H[6][b28]': 220, 'H[6][b29]': 221, 'H[6][b31]': 223, 'H[7][b29]': 253}
    print(f"\n=== Methodology bits on HC-optimized (should match their phi pattern) ===")
    for lbl, i in meth_bits.items():
        print(f"  {lbl}: phi={phi[i]:+.5f} z={z[i]:+.2f}")

    # Combined TV advantage
    print(f"\n=== Combined TV-advantage ===")
    print(f"  Methodology 4 bits:  TV = {tv_dist(phi[[220,221,223,253]]):.4f}")
    print(f"  Our H[5] 5 bits:     TV = {tv_dist(phi[[160,161,162,163,164]]):.4f}")
    print(f"  Combined 9 bits:     TV = {tv_dist(phi[[160,161,162,163,164,220,221,223,253]]):.4f}")
    # Top significant
    top_sig_15 = sig_idx[:15]
    print(f"  Top 15 significant:  TV = {tv_dist(phi[top_sig_15]):.4f}")

    # Ω_3 check
    print(f"\n# Running omega3_full on HC-optimized inputs (stride=8)...")
    fa = (np.unpackbits(inputs_hc, axis=1).sum(axis=1) & 1).astype(np.uint8)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(s2b[:, b]).tobytes())
        ts = time.time()
        res = subprocess.run([C_BIN, tp, '8'], capture_output=True, text=True, check=True, timeout=120)
        d = json.loads(res.stdout)
        print(f"  Ω_3 = {d['omega3']:+.4f}  ss = {d['same_sign']}/256  t = {time.time()-ts:.0f}s")
    finally:
        os.unlink(tp)

    out = {'N': N, 'n_iters': N_ITERS, 'state_sum_final_mean': float(ss_final.mean()),
           'phi': phi.tolist(), 'omega3': d['omega3'],
           'tv_meth_4': tv_dist(phi[[220,221,223,253]]),
           'tv_our_5': tv_dist(phi[[160,161,162,163,164]]),
           'tv_combined_9': tv_dist(phi[[160,161,162,163,164,220,221,223,253]]),
           'tv_top_15': tv_dist(phi[top_sig_15])}
    with open(os.path.join(HERE, 'it32_hc_combined.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
