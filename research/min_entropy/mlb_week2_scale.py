"""MLB Week 2 Day 2: scale K to 50M for better near-collisions.

Previous K=10M gave min HW = 85 (beat methodology 87).
Expected scaling: min HW drops as ~sqrt(log N) from mean shift.

N = effective close pairs ~ K² × (T/2^32)^3
At K=50M, T=2M: 50M² × (2M/2^32)^3 ≈ 25*10^14 × 1.1e-10 = 2.7*10^5 pairs
Expected min HW at 270K uniform pairs: 128 - 8·sqrt(2·ln(270K)) = 128 - 30 = 98
With our 17-bit compression: should reach ~80 or lower.

Memory strategy: don't store state1 for all K. Store only (W0, a63, e63, a62).
After bucketing, recompute state1 only for candidate pairs.
"""
import math, os, json, time
from collections import defaultdict
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week2_scale50M.json')

K = 50_000_000
THRESHOLD = 2_000_000


def compute_keys_only(W0_start, W0_end):
    """Compute a63, e63, a62 for range — no state1 storage."""
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
    a62_arr = None
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 62: a62_arr = a.copy()
    return a.copy(), e.copy(), a62_arr


def compute_state1_for_indices(W0_indices):
    """Compute state1 for specific W[0] values (small list)."""
    N = len(W0_indices)
    block1 = np.zeros((N, 16), dtype=ch.U32)
    block1[:, 0] = np.array(W0_indices, dtype=ch.U32)
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
    return state1


def main():
    t0 = time.time()
    print(f"# MLB Week 2 Day 2: scale K={K:,}, T={THRESHOLD:,}")

    # Phase 1: compute only keys (memory efficient)
    print(f"\n# Phase 1: computing keys for {K:,} scans...")
    ts = time.time()
    a63_all = np.zeros(K, dtype=np.uint32)
    e63_all = np.zeros(K, dtype=np.uint32)
    a62_all = np.zeros(K, dtype=np.uint32)
    BATCH = 200_000
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a63, e63, a62 = compute_keys_only(start, end)
        a63_all[start:end] = a63
        e63_all[start:end] = e63
        a62_all[start:end] = a62
        if (start + BATCH) % 5_000_000 == 0:
            el = time.time() - ts
            eta = el / (end / K) - el
            print(f"  {end:,}/{K:,} ({el:.0f}s, ETA {eta:.0f}s)", flush=True)
    print(f"  total: {time.time()-ts:.0f}s")

    # Phase 2: bucketing
    print(f"\n# Phase 2: bucketing by (a63, e63, a62) // {THRESHOLD:,}...")
    ts = time.time()
    buckets = defaultdict(list)
    for i in range(K):
        key = (int(a63_all[i]) // THRESHOLD,
               int(e63_all[i]) // THRESHOLD,
               int(a62_all[i]) // THRESHOLD)
        buckets[key].append(i)
    n_active = sum(1 for v in buckets.values() if len(v) >= 2)
    print(f"  time: {time.time()-ts:.0f}s, {n_active:,} active buckets")

    # Phase 3: find candidate pairs (in same bucket, all 3 keys within T)
    print(f"\n# Phase 3: enumerating candidate pairs...")
    ts = time.time()
    candidate_pairs = []  # (i, j)
    for bucket_ids in buckets.values():
        if len(bucket_ids) < 2: continue
        L = min(len(bucket_ids), 15)  # cap per bucket
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = bucket_ids[ii], bucket_ids[jj]
                if abs(int(a63_all[i]) - int(a63_all[j])) >= THRESHOLD: continue
                if abs(int(e63_all[i]) - int(e63_all[j])) >= THRESHOLD: continue
                if abs(int(a62_all[i]) - int(a62_all[j])) >= THRESHOLD: continue
                candidate_pairs.append((i, j))
    print(f"  {len(candidate_pairs):,} candidate pairs ({time.time()-ts:.0f}s)")

    # Phase 4: compute state1 for all unique W[0] indices, then HW for pairs
    print(f"\n# Phase 4: computing state1 for candidates...")
    ts = time.time()
    unique_idx = list(set(i for p in candidate_pairs for i in p))
    print(f"  {len(unique_idx):,} unique W[0] values to compute state1 for")
    # Batch compute
    states = {}
    UBATCH = 50_000
    for bi in range(0, len(unique_idx), UBATCH):
        batch = unique_idx[bi:bi+UBATCH]
        s1_batch = compute_state1_for_indices(batch)
        for idx, w0 in enumerate(batch):
            states[w0] = s1_batch[idx].copy()
        if bi % 200_000 == 0 and bi > 0:
            print(f"  {bi:,}/{len(unique_idx):,} ({time.time()-ts:.0f}s)", flush=True)
    print(f"  state1 compute: {time.time()-ts:.0f}s")

    # Phase 5: compute HW for each pair, find min
    print(f"\n# Phase 5: computing HW for pairs, finding minimum...")
    ts = time.time()
    best = []
    TOP_N = 30
    for i, j in candidate_pairs:
        s_A, s_B = states[i], states[j]
        hw = 0
        for w in range(8):
            hw += bin(int(s_A[w]) ^ int(s_B[w])).count('1')
        if len(best) < TOP_N:
            best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]:
            best[-1] = (hw, i, j); best.sort()
    print(f"  time: {time.time()-ts:.0f}s")

    # Report
    min_hw = best[0][0] if best else None
    print(f"\n=== TOP {TOP_N} NEAR-COLLISIONS ===")
    print(f"{'rank':>4} {'HW':>5} {'W0_a':>12} {'W0_b':>12}")
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"{r+1:>4} {hw:>5} {i:>12} {j:>12}")

    N_used = len(candidate_pairs)
    exp_uniform = 128 - 8 * math.sqrt(2 * math.log(N_used))
    print(f"\n=== SUMMARY ===")
    print(f"K = {K:,}, T = {THRESHOLD:,}")
    print(f"Candidate pairs: {N_used:,}")
    print(f"Minimum HW found: {min_hw}")
    print(f"Uniform baseline for same N: ≈ {exp_uniform:.1f}")
    print(f"Advantage below uniform: {exp_uniform - min_hw:+.1f} bits")
    print(f"Methodology SA best: 87")
    print(f"Our K=10M result: 85")
    if min_hw < 85:
        print(f"★ NEW BEST: {min_hw} (improves {85-min_hw} bits over Week 2 Day 1)")

    out = {'K': K, 'T': THRESHOLD, 'N_pairs': N_used,
           'min_hw': min_hw, 'expected_uniform': exp_uniform,
           'top30': [(h, i, j) for h, i, j in best],
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
