"""IT-31: Combined distinguisher — methodology bits + our H[5] bits on HC-like inputs.

Two-stage filter approximates methodology's HC-optimized distribution:
1. carry[62] = 0 on inputs (50% yield)
2. Bottom STATE_SUM quantile at r=62 (strictest 10% of carry-zero)
Combined yield: ~5% — matches methodology's HC target.

Then measure phi across all 256 output bits. Identify significant biased bits.
Test combined advantage:
  - Methodology bits: H[6][b28,29,31] (idx 220,221,223), H[7][b29] (idx 253)
  - Our bits: H[5][b0..b5] (idx 160..165)
  - Any new significant bits

Compute TV distance for combined distinguisher. Target: beat methodology's 0.30.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')

N_RAW = 2_000_000       # raw random inputs to generate
N_TARGET = 130_816      # target HC-like samples after filter


def compute_state_sum_and_carry(inputs):
    """Compute STATE_SUM at round 62 and carry-out of round 62 for each input."""
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
    state_sum_at62 = None
    carry62 = None
    for t in range(63):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        if t == 62:
            state_sum_at62 = (a.astype(np.uint64) + b.astype(np.uint64) + c.astype(np.uint64)
                              + d.astype(np.uint64) + e.astype(np.uint64) + f.astype(np.uint64)
                              + g.astype(np.uint64) + h.astype(np.uint64))
            d64 = d.astype(np.uint64)
            T1_64 = T1.astype(np.uint64)
            carry62 = ((d64 + T1_64) >> 32).astype(np.uint8)
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return state_sum_at62, carry62


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


def tv_distance_bits(phi_subset):
    """Exact TV distance for K independent Bernoulli bits."""
    k = len(phi_subset)
    if k > 18: return None
    tv = 0
    for mask in range(2**k):
        p_sha = 1.0
        for i in range(k):
            if (mask >> i) & 1:
                p_sha *= 0.5 + phi_subset[i]
            else:
                p_sha *= 0.5 - phi_subset[i]
        p_rnd = 0.5**k
        tv += abs(p_sha - p_rnd)
    return tv / 2


def main():
    t0 = time.time()
    print(f"# IT-31: Combined distinguisher (HC-like filter)")

    # Generate in chunks to avoid memory blowup
    CHUNK = 500_000
    all_state_sums = []
    all_carries = []
    all_inputs_arr = []

    rng = np.random.default_rng(0xD157)
    total = 0
    print(f"# Generating {N_RAW} inputs in chunks of {CHUNK}...", flush=True)
    while total < N_RAW:
        batch_size = min(CHUNK, N_RAW - total)
        chunk = rng.integers(0, 256, size=(batch_size, 64), dtype=np.uint8)
        ts = time.time()
        state_sum, carry62 = compute_state_sum_and_carry(chunk)
        print(f"  chunk {total}..{total+batch_size}: {time.time()-ts:.0f}s, "
              f"carry=0 frac {(carry62==0).sum()/batch_size:.3f}, "
              f"STATE_SUM p10 {np.percentile(state_sum, 10):.2e}", flush=True)
        all_state_sums.append(state_sum)
        all_carries.append(carry62)
        all_inputs_arr.append(chunk)
        total += batch_size

    state_sums = np.concatenate(all_state_sums)
    carries = np.concatenate(all_carries)
    inputs = np.concatenate(all_inputs_arr, axis=0)

    # Stage 1: filter carry[62]=0
    mask1 = (carries == 0)
    print(f"# Stage 1 (carry=0): {mask1.sum()}/{N_RAW} = {100*mask1.mean():.1f}%")
    ss_filtered = state_sums[mask1]
    inputs_filtered = inputs[mask1]

    # Stage 2: bottom-X quantile of STATE_SUM to match methodology HC target (~5-10%)
    threshold = np.percentile(ss_filtered, 20)  # bottom 20% of carry=0
    print(f"# Stage 2: STATE_SUM < {threshold:.2e} (p20 of carry=0 subset)")
    mask2 = ss_filtered < threshold
    print(f"# After stage 2: {mask2.sum()} inputs")

    use_inputs = inputs_filtered[mask2][:N_TARGET]
    N = len(use_inputs)
    print(f"# Using N={N} HC-like inputs")

    # Full SHA + bit extraction
    s1, s2 = compute_full_hash(use_inputs)
    s1b = sb(s1, N); s2b = sb(s2, N)

    # Per-bit phi
    ones = s2b.sum(axis=0)
    phi = ones / N - 0.5
    z = phi / (0.5 / np.sqrt(N))

    print(f"\n=== Significant bits (|z| > 3) ===")
    sig = np.where(np.abs(z) > 3)[0]
    sig_sorted = sig[np.argsort(-np.abs(z[sig]))]
    print(f"{len(sig)} significant bits")
    for idx in sig_sorted[:25]:
        w = idx // 32; off = idx % 32
        star = '★' if idx in [220, 221, 223, 253] else ('☆' if 160 <= idx <= 167 else ' ')
        print(f"  {star} bit {idx:>3} H[{w}][b{off:>2}] phi={phi[idx]:+.5f} z={z[idx]:+.2f}")

    # Methodology bits on this filter
    print(f"\n=== T_COMMIT_HIDING bits on HC-like filter ===")
    meth_bits = [('H[6][b28]', 220), ('H[6][b29]', 221), ('H[6][b31]', 223), ('H[7][b29]', 253)]
    for lbl, i in meth_bits:
        print(f"  {lbl}: phi={phi[i]:+.5f}  z={z[i]:+.2f}")

    # Compute combined TV-advantage
    print(f"\n=== Combined TV-advantage (optimal distinguisher) ===")
    # Strategy A: methodology 4 bits alone
    print(f"Methodology 4 bits alone:    TV = {tv_distance_bits(phi[[220,221,223,253]]):.4f}")
    # Strategy B: our H[5] 5 bits alone
    print(f"Our H[5] 5 bits alone:       TV = {tv_distance_bits(phi[[160,161,162,163,164]]):.4f}")
    # Strategy C: combined 9 bits
    combined_9 = [220, 221, 223, 253, 160, 161, 162, 163, 164]
    print(f"Combined 9 bits:             TV = {tv_distance_bits(phi[combined_9]):.4f}")
    # Strategy D: all significant
    sig_top = sig_sorted[:min(15, len(sig_sorted))].tolist()
    print(f"Top {len(sig_top)} significant bits:     TV = {tv_distance_bits(phi[sig_top]):.4f}")
    # Strategy E: only bits OUTSIDE H[5] to avoid carry-chain correlation
    non_h5 = [i for i in sig_sorted.tolist() if i // 32 != 5][:10]
    if non_h5:
        print(f"Top bits NOT in H[5] ({len(non_h5)}): TV = {tv_distance_bits(phi[non_h5]):.4f}")

    # Also run omega3 on this input class
    print(f"\n# Running omega3_full on HC-like inputs (stride=8)...", flush=True)
    # Use some feature
    fa = (np.unpackbits(use_inputs, axis=1).sum(axis=1) & 1).astype(np.uint8)
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

    # Save
    out = {'N': N, 'phi': phi.tolist(), 'significant_bits': sig_sorted.tolist(),
           'omega3': d['omega3'], 'ss_omega3': d['same_sign'],
           'stats': {
               'meth_4bits_tv': float(tv_distance_bits(phi[[220,221,223,253]])),
               'our_h5_5bits_tv': float(tv_distance_bits(phi[[160,161,162,163,164]])),
               'combined_9bits_tv': float(tv_distance_bits(phi[combined_9])),
           }}
    with open(os.path.join(HERE, 'it31_combined.json'), 'w') as f:
        json.dump(out, f)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
