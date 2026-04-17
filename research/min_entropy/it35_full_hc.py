"""IT-35 (direction B): Full HC matching methodology protocol.

150 iters matching methodology.
Flip bits across W[0..15] (full 512-bit space), not just W[0..1].
N=50K samples (reduced from 130K due to compute; HC is 150 × batch SHA).

Measure at end:
- Mean STATE_SUM at r=62 (target: < 1.1e9 methodology threshold)
- Fraction of samples below threshold
- phi for all 256 output bits
- Methodology bits H[6][b28,29,31], H[7][b29]
- Ω_3 on full 256-bit spectrum
- TV advantage combined methodology + our H[5] bits
"""
import json, math, os, subprocess, tempfile, time
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')

N_SAMPLES = 50000
N_ITERS = 150

def state_sum_r62(inputs):
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
    return (a.astype(np.uint64) + b.astype(np.uint64) + c.astype(np.uint64) + d.astype(np.uint64)
          + e.astype(np.uint64) + f.astype(np.uint64) + g.astype(np.uint64) + h.astype(np.uint64))


def full_hash(inputs):
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
    rng = np.random.default_rng(0xBB77)
    print(f"# IT-35 (dir B): full HC {N_SAMPLES} samples × {N_ITERS} iters, bits W[0..15]")

    inputs = rng.integers(0, 256, size=(N_SAMPLES, 64), dtype=np.uint8)
    ss = state_sum_r62(inputs)
    print(f"# initial: mean SS = {ss.mean():.3e}, min = {ss.min():.3e}")

    accepts = 0
    for it in range(N_ITERS):
        trial = inputs.copy()
        # Flip 1 bit anywhere in 64-byte input
        byte_idx = rng.integers(0, 64, size=N_SAMPLES)
        bit_idx = rng.integers(0, 8, size=N_SAMPLES)
        flip_vals = (1 << bit_idx).astype(np.uint8)
        trial[np.arange(N_SAMPLES), byte_idx] ^= flip_vals
        ss_trial = state_sum_r62(trial)
        better = ss_trial < ss
        inputs = np.where(better[:, None], trial, inputs)
        ss = np.where(better, ss_trial, ss)
        accepts += better.sum()
        if (it + 1) % 25 == 0:
            frac_below = (ss < 1.1e9).mean()
            print(f"  iter {it+1}/{N_ITERS}: mean SS = {ss.mean():.3e}, "
                  f"min = {ss.min():.3e}, frac < 1.1e9 = {frac_below:.3f}", flush=True)

    print(f"\n# HC done: mean SS = {ss.mean():.3e}, min = {ss.min():.3e}")
    print(f"# Fraction below methodology threshold 1.1e9: {(ss < 1.1e9).mean():.3f}")

    # Compute hash, measure phi
    s1, s2 = full_hash(inputs)
    s1b = sb(s1, N_SAMPLES); s2b = sb(s2, N_SAMPLES)
    phi = s2b.sum(axis=0) / N_SAMPLES - 0.5
    z = phi / (0.5 / np.sqrt(N_SAMPLES))

    print(f"\n=== Top 15 biased bits ===")
    top = np.argsort(-np.abs(z))[:15]
    for i in top:
        w, off = i // 32, i % 32
        star = '★' if i in [220, 221, 223, 253] else (' ☆' if 160 <= i <= 167 else '  ')
        print(f"  {star} bit {i:>3} H[{w}][b{off:>2}] phi={phi[i]:+.5f} z={z[i]:+.2f}")

    # Methodology bits
    print(f"\n=== Methodology T_COMMIT_HIDING bits ===")
    meth = [('H[6][b28]', 220), ('H[6][b29]', 221), ('H[6][b31]', 223), ('H[7][b29]', 253)]
    for lbl, i in meth:
        print(f"  {lbl}: phi={phi[i]:+.5f}  z={z[i]:+.2f}")

    # Our H[5] bits
    print(f"\n=== Our H[5][b0..b5] bits ===")
    for b in range(6):
        i = 160 + b
        print(f"  H[5][b{b}]: phi={phi[i]:+.5f}  z={z[i]:+.2f}")

    # TV distances
    print(f"\n=== Combined TV advantage ===")
    print(f"  Methodology 4 bits alone:  TV = {tv_dist(phi[[220,221,223,253]]):.4f}")
    print(f"  Our H[5] 5 bits alone:     TV = {tv_dist(phi[[160,161,162,163,164]]):.4f}")
    print(f"  Combined 9 bits:           TV = {tv_dist(phi[[160,161,162,163,164,220,221,223,253]]):.4f}")
    # Top 15 bits
    top15 = np.argsort(-np.abs(z))[:15].tolist()
    print(f"  Top 15 significant:        TV = {tv_dist(phi[top15]):.4f}")

    # Ω_3
    print(f"\n# Running omega3_full (stride=8)...")
    fa = (np.unpackbits(inputs, axis=1).sum(axis=1) & 1).astype(np.uint8)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N_SAMPLES).tobytes())
            for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(s2b[:, b]).tobytes())
        ts = time.time()
        res = subprocess.run([C_BIN, tp, '8'], capture_output=True, text=True, check=True, timeout=150)
        d = json.loads(res.stdout)
        print(f"  Ω_3 = {d['omega3']:+.4f}  ss = {d['same_sign']}/256  t = {time.time()-ts:.0f}s")
    finally:
        os.unlink(tp)

    out = {
        'N': N_SAMPLES, 'N_ITERS': N_ITERS,
        'SS_final_mean': float(ss.mean()), 'SS_final_min': float(ss.min()),
        'frac_below_threshold': float((ss < 1.1e9).mean()),
        'phi': phi.tolist(),
        'top_bits': [(int(i), float(z[i])) for i in top],
        'meth_phi': {'H[6][b28]': float(phi[220]), 'H[6][b29]': float(phi[221]),
                     'H[6][b31]': float(phi[223]), 'H[7][b29]': float(phi[253])},
        'our_h5_phi': [float(phi[160+b]) for b in range(6)],
        'tv_meth_4': float(tv_dist(phi[[220,221,223,253]])),
        'tv_our_5': float(tv_dist(phi[[160,161,162,163,164]])),
        'tv_combined_9': float(tv_dist(phi[[160,161,162,163,164,220,221,223,253]])),
        'tv_top_15': float(tv_dist(phi[top15])),
        'omega3': d['omega3'], 'omega3_ss': d['same_sign'],
    }
    with open(os.path.join(HERE, 'it35_full_hc.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
