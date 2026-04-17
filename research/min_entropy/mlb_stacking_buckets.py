"""MLB stacking via bucketing — proper joint-close sampling.

Bucket each sample by (a63 // T, e63 // T). Pairs in same bucket
are automatically joint-close on BOTH keys.

Test: gap for single-key (a63 alone) vs joint (a63 + e63).
If independent signals stack, joint gap >> single gap.

K=10M scan, threshold T=10K (per key).
Expected same-bucket pairs: each bucket avg 10M / (2^32/10K)^2 = very few
Better: T=1M → (2^32/1M)^2 = ~18B buckets. 10M in 18B → avg 0.0006 per bucket.

Even better approach: sort by a63, within each "same-a63-bucket", look at
e63 distribution — is it narrower than uniform? If yes, signals correlated.
Finally: directly look for pairs (i,j) with both |Δa63|<T and |Δe63|<T.
"""
import math, os, json, time
from collections import defaultdict
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_stacking_buckets.json')

K = 10_000_000


def compute_a63_e63_and_state1(W0_start, W0_end):
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
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return a, e, state1  # a and e are at round 64 = 'a63', 'e63' in methodology


def main():
    t0 = time.time()
    print(f"# MLB Stacking via Bucketing")
    print(f"# K = {K:,} W[0] scans")

    # Phase 1: compute a63, e63, state1
    print(f"\n# Phase 1: computing values...")
    ts = time.time()
    BATCH = 200_000
    a63_arr = np.zeros(K, dtype=np.uint32)
    e63_arr = np.zeros(K, dtype=np.uint32)
    state1_arr = np.zeros((K, 8), dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a, e, s1 = compute_a63_e63_and_state1(start, end)
        a63_arr[start:end] = a
        e63_arr[start:end] = e
        state1_arr[start:end] = s1
        if (start + BATCH) % 2_000_000 == 0:
            print(f"  {end:,}/{K:,} ({time.time()-ts:.0f}s)", flush=True)
    print(f"  total: {time.time()-ts:.0f}s")

    # Phase 2: bucketing for joint close pairs
    # Bucket by (a63 // T, e63 // T). Pairs in same bucket are joint-close.
    # For a63 to produce enough close pairs we need T s.t. K*K / (2^32/T)^2 ≈ 1000 pairs.
    # K^2 / (2^32/T)^2 = 1000  →  T = 2^32 * sqrt(1000)/K = 2^32 * 31.6 / 10M ≈ 13580
    # Let's use T = 50000 for safety (expect ~1000 joint-close pairs)

    def sample_joint_close(T_thresh, label, max_pairs=3000):
        """Sample pairs with both |Δa63|<T and |Δe63|<T via bucketing."""
        buckets = defaultdict(list)
        for i in range(K):
            key = (int(a63_arr[i]) // T_thresh, int(e63_arr[i]) // T_thresh)
            buckets[key].append(i)
        # Find bucket-local pairs
        close_hw = []
        for bucket_ids in buckets.values():
            if len(bucket_ids) < 2: continue
            # Pairs within this bucket — check actual distances
            for ii in range(min(len(bucket_ids), 20)):  # cap inner to avoid explosion
                for jj in range(ii+1, min(len(bucket_ids), 20)):
                    i, j = bucket_ids[ii], bucket_ids[jj]
                    if abs(int(a63_arr[i]) - int(a63_arr[j])) < T_thresh and \
                       abs(int(e63_arr[i]) - int(e63_arr[j])) < T_thresh:
                        hw = 0
                        for w in range(8):
                            hw += bin(int(state1_arr[i, w]) ^ int(state1_arr[j, w])).count('1')
                        close_hw.append(hw)
                        if len(close_hw) >= max_pairs: break
                if len(close_hw) >= max_pairs: break
            if len(close_hw) >= max_pairs: break
        print(f"  {label} T={T_thresh}: got {len(close_hw)} joint-close pairs", flush=True)
        return close_hw

    # Phase 3a: baseline single-key (a63 only close)
    print(f"\n# Phase 3a: single key a63 (close + far baseline)")
    ts = time.time()
    sort_idx_a = np.argsort(a63_arr)
    a63_sorted = a63_arr[sort_idx_a]
    s1_sorted_a = state1_arr[sort_idx_a]
    single_close = []
    for i in range(K - 1):
        if int(a63_sorted[i+1]) - int(a63_sorted[i]) < 10_000:
            hw = 0
            for w in range(8):
                hw += bin(int(s1_sorted_a[i, w]) ^ int(s1_sorted_a[i+1, w])).count('1')
            single_close.append(hw)
            if len(single_close) >= 5000: break
    print(f"  a63 single close (N={len(single_close)}): mean HW = {np.mean(single_close):.3f} "
          f"({time.time()-ts:.0f}s)")

    # Far baseline
    rng = np.random.default_rng(0xF00)
    far_hw = []
    while len(far_hw) < 5000:
        i, j = rng.integers(0, K), rng.integers(0, K)
        if i == j: continue
        if abs(int(a63_arr[i]) - int(a63_arr[j])) > 10_000_000:
            hw = 0
            for w in range(8):
                hw += bin(int(state1_arr[i, w]) ^ int(state1_arr[j, w])).count('1')
            far_hw.append(hw)
    print(f"  a63 far (N={len(far_hw)}): mean HW = {np.mean(far_hw):.3f}")
    single_gap = np.mean(single_close) - np.mean(far_hw)
    print(f"  SINGLE a63 gap: {single_gap:+.3f} bits")

    # Phase 3b: joint-close for different thresholds
    print(f"\n# Phase 3b: joint-close a63 ∧ e63 via bucketing")
    joint_results = {}
    for T in [50_000, 100_000, 500_000]:
        close_list = sample_joint_close(T, f"a63∧e63", max_pairs=3000)
        if not close_list: continue
        c_mean = float(np.mean(close_list))
        joint_results[T] = {'n': len(close_list), 'mean': c_mean,
                            'gap': c_mean - float(np.mean(far_hw))}
        print(f"  T={T}: N={len(close_list)} mean={c_mean:.3f} gap={c_mean - np.mean(far_hw):+.3f}")

    # Summary
    print(f"\n=== STACKING TEST RESULT ===")
    print(f"Single key a63 (T=10K):  gap = {single_gap:+.3f} bits")
    best_joint_T = min(joint_results.keys(), key=lambda t: joint_results[t]['gap'])
    best_joint = joint_results[best_joint_T]
    print(f"Joint a63 ∧ e63 (T={best_joint_T}): gap = {best_joint['gap']:+.3f} bits (N={best_joint['n']})")
    extra = best_joint['gap'] - single_gap
    print(f"Stacking gain: {extra:+.3f} bits")
    if extra < -3:
        print(f"  → SIGNALS STACK — keys carry independent info")
        print(f"  → Effective birthday: 2^{128 + best_joint['gap']/2:.2f}")
    else:
        print(f"  → No significant stacking — a63 and e63 are redundant for this task")

    out = {'K': K, 'single_a63_gap': single_gap, 'joint_results': joint_results,
           'far_mean': float(np.mean(far_hw)), 'stacking_gain': extra,
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
