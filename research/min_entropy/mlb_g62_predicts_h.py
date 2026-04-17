"""MLB Week 1c: validate T_G62_PREDICTS_H (methodology ★★★★★ claim).

Methodology claim (П-1256):
  Close g62 (|Δg62|<10K):    E[HW(Δstate1)] = 109.0 bits
  Far g62 (|Δg62|>10M):      E[HW(Δstate1)] = 127.2 bits
  Difference: -18.2 bits (18.2-bit advantage from g62-proximity)

g62 = g register value at round 62 of block-1 compression.
state1 = full 8-word state after round 64 of block-1.

Test setup:
- K = 2M W[0] values, W[1..15] = 0
- For each: compute state at round 62 (extract g62), save full state1
- Sort pairs by Δg62
- Close pairs (<10K apart in g62): N1=10K sample, compute mean HW(Δstate1)
- Far pairs (>10M apart): N2=10K sample, compute mean HW(Δstate1)
- Compare

Methodology tested presumably small N; we do robust statistics at N=10K pairs each.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_g62_predicts_h.json')

K = 2_000_000  # W[0] values to scan


def compute_g62_and_state1(W0_start, W0_end):
    """For W0 in [start, end), compute g register at round 62 AND full state1 (round 64)."""
    N = W0_end - W0_start
    block1 = np.zeros((N, 16), dtype=ch.U32)
    block1[:, 0] = np.arange(W0_start, W0_end, dtype=ch.U32)

    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, 64), dtype=U32); W[:, :16] = block1
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK

    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA

    g62 = None
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 62:
            g62 = g.copy()  # g register value AT round 62 (AFTER round 62 update)

    # Finalize to state1 (feed-forward add with IV)
    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return g62, state1


def popcount32_vec(arr):
    x = arr.astype(np.uint32)
    x = x - ((x >> 1) & 0x55555555)
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
    x = (x + (x >> 4)) & 0x0f0f0f0f
    return ((x * np.uint32(0x01010101)) >> 24).astype(np.int32)


def hw_sum_across_words(s_A, s_B):
    """Sum of popcount(s_A XOR s_B) across 8 words — total HW difference."""
    hw = np.zeros(len(s_A), dtype=np.int32)
    for i in range(8):
        hw += popcount32_vec(s_A[:, i] ^ s_B[:, i])
    return hw


def main():
    t0 = time.time()
    print(f"# MLB Week 1c: T_G62_PREDICTS_H validation")
    print(f"# Scanning K = {K:,} W[0] values")

    # Phase 1: compute g62 and state1 for all
    print(f"\n# Phase 1: computing g62 + state1 for {K:,} values...")
    ts = time.time()
    g62_arr = np.zeros(K, dtype=np.uint32)
    state1_arr = np.zeros((K, 8), dtype=np.uint32)
    BATCH = 200_000
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        g62_chunk, s1_chunk = compute_g62_and_state1(start, end)
        g62_arr[start:end] = g62_chunk
        state1_arr[start:end] = s1_chunk
        if (start + BATCH) % 500_000 == 0:
            el = time.time() - ts
            print(f"  {end:,}/{K:,} ({el:.0f}s)", flush=True)

    # Phase 2: sort by g62
    print(f"\n# Phase 2: sort by g62...")
    sort_idx = np.argsort(g62_arr)
    g62_sorted = g62_arr[sort_idx]
    state1_sorted = state1_arr[sort_idx]

    # Phase 3a: close pairs (|Δg62| < 10K)
    # Use consecutive sorted pairs. After sort, check Δ between neighbors.
    print(f"\n# Phase 3a: close-g62 pairs (|Δg62| < 10,000)...")
    N_CLOSE_TARGET = 10_000
    close_hw_list = []
    rng = np.random.default_rng(42)
    # For randomness, pick random i, look at pair (i, i+1), accept if Δ<10K
    attempts = 0
    while len(close_hw_list) < N_CLOSE_TARGET and attempts < 500_000:
        i = rng.integers(0, K - 1)
        g_diff = int(g62_sorted[i+1]) - int(g62_sorted[i])
        if g_diff < 10_000:
            # valid close pair
            hw = 0
            for w in range(8):
                hw += bin(int(state1_sorted[i, w]) ^ int(state1_sorted[i+1, w])).count('1')
            close_hw_list.append(hw)
        attempts += 1
    print(f"  Got {len(close_hw_list)} close pairs in {attempts} attempts")

    # Phase 3b: far pairs (|Δg62| > 10M)
    print(f"\n# Phase 3b: far-g62 pairs (|Δg62| > 10,000,000)...")
    N_FAR_TARGET = 10_000
    far_hw_list = []
    attempts = 0
    while len(far_hw_list) < N_FAR_TARGET and attempts < 500_000:
        i = rng.integers(0, K)
        j = rng.integers(0, K)
        if i == j: continue
        g_diff = abs(int(g62_arr[i]) - int(g62_arr[j]))
        if g_diff > 10_000_000:
            hw = 0
            for w in range(8):
                hw += bin(int(state1_arr[i, w]) ^ int(state1_arr[j, w])).count('1')
            far_hw_list.append(hw)
        attempts += 1
    print(f"  Got {len(far_hw_list)} far pairs in {attempts} attempts")

    # Phase 4: statistics
    close_arr = np.array(close_hw_list)
    far_arr = np.array(far_hw_list)
    close_mean = float(close_arr.mean())
    close_std = float(close_arr.std(ddof=1))
    far_mean = float(far_arr.mean())
    far_std = float(far_arr.std(ddof=1))

    print(f"\n=== MLB T_G62 validation (N_close={len(close_arr):,}, N_far={len(far_arr):,}) ===")
    print(f"{'class':<12} {'N':>8} {'mean HW':>10} {'std':>7} {'SE':>7}")
    print(f"close g62    {len(close_arr):>8} {close_mean:>10.3f} {close_std:>7.2f} {close_std/math.sqrt(len(close_arr)):>7.3f}")
    print(f"far g62      {len(far_arr):>8} {far_mean:>10.3f} {far_std:>7.2f} {far_std/math.sqrt(len(far_arr)):>7.3f}")
    print(f"\nDifference (close - far): {close_mean - far_mean:+.3f} bits")
    print(f"  Methodology predicts:    -18.2 bits")
    print(f"  Uniform baseline would:  ≈ 0 (close and far should be same)")

    z_diff = (close_mean - far_mean) / math.sqrt(close_std**2/len(close_arr) + far_std**2/len(far_arr))
    print(f"\nZ-statistic (close vs far): {z_diff:+.2f}σ")

    # Compare to methodology
    meth_close = 109.0
    meth_far = 127.2
    agree_close = abs(close_mean - meth_close) < 1.0
    agree_far = abs(far_mean - meth_far) < 1.0

    print(f"\n=== Methodology comparison ===")
    print(f"close: our {close_mean:.2f} vs meth {meth_close}   {'★★★' if agree_close else 'DIFFER'}")
    print(f"far:   our {far_mean:.2f} vs meth {meth_far}   {'★★★' if agree_far else 'DIFFER'}")

    if agree_close and agree_far:
        print("\n★★★ T_G62_PREDICTS_H REPLICATED — g62 structure is real")
    elif abs(close_mean - far_mean) > 2.0 and z_diff < -5:
        print("\n✓ Partial: difference exists but not at methodology's magnitude")
    else:
        print("\n✗ T_G62_PREDICTS_H NOT REPLICATED — likely small-sample artifact")

    out = {'K': K, 'N_close': len(close_arr), 'N_far': len(far_arr),
           'close_mean': close_mean, 'close_std': close_std,
           'far_mean': far_mean, 'far_std': far_std,
           'diff': close_mean - far_mean, 'z_diff': z_diff,
           'methodology_close': meth_close, 'methodology_far': meth_far,
           'agreement': {'close': agree_close, 'far': agree_far}}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
