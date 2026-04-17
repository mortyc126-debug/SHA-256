"""MLB Week 3 Day 1: honest baseline — uniform random search vs our 3-channel filter.

Question: is our HW=80 really better than UNIFORM random pair search
with SAME compute budget?

Protocol:
1. K=50M W[0] scan (compute keys + nothing else = 280s SHA)
2. Baseline: pick 125K RANDOM uniform pairs from K, compute state1, find min HW.
3. Filtered:  3-channel bucketing → ~125K joint-close pairs → find min HW.
4. Compare.

Both use SAME # SHA computations and SAME # pair evaluations.

Expected:
  Uniform 125K pairs: min HW ≈ 88 (128 - 8·sqrt(2·ln(125K)) = 128 - 40)
  Filtered:           min HW = 80  (our Week 2 Day 2 result)
  Advantage:          8 bits

Validates our sort-key method has real signal vs uniform sampling.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week3_baseline.json')

K = 50_000_000
THRESHOLD = 2_000_000
N_UNIFORM_PAIRS = 125_000


def compute_keys_only(W0_start, W0_end):
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
    print(f"# MLB Week 3 Day 1: uniform baseline vs filter")
    print(f"# K={K:,}, T={THRESHOLD:,}, N_uniform_pairs={N_UNIFORM_PAIRS:,}")

    # Phase 1: compute keys
    print(f"\n# Phase 1: K={K:,} scan (keys only)...")
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
        if (start + BATCH) % 10_000_000 == 0:
            print(f"  {end:,}/{K:,} ({time.time()-ts:.0f}s)", flush=True)
    print(f"  total: {time.time()-ts:.0f}s")

    # Phase 2a: UNIFORM BASELINE
    print(f"\n# Phase 2a: UNIFORM baseline ({N_UNIFORM_PAIRS:,} random pairs)...")
    ts = time.time()
    rng = np.random.default_rng(0xB45E)
    # Pick 2*N_UNIFORM_PAIRS random W[0] indices
    pair_idx_a = rng.integers(0, K, size=N_UNIFORM_PAIRS)
    pair_idx_b = rng.integers(0, K, size=N_UNIFORM_PAIRS)
    # Deduplicate self-pairs
    mask = pair_idx_a != pair_idx_b
    pair_idx_a = pair_idx_a[mask]
    pair_idx_b = pair_idx_b[mask]
    print(f"  {len(pair_idx_a):,} valid pairs after self-dedup")
    # Compute state1 for all unique
    unique_w0 = np.unique(np.concatenate([pair_idx_a, pair_idx_b]))
    print(f"  {len(unique_w0):,} unique W[0] for state1 recompute")
    states = {}
    UBATCH = 50_000
    for bi in range(0, len(unique_w0), UBATCH):
        batch = list(unique_w0[bi:bi+UBATCH])
        s1_batch = compute_state1_for_indices(batch)
        for idx, w0 in enumerate(batch):
            states[int(w0)] = s1_batch[idx].copy()
    print(f"  state1 compute: {time.time()-ts:.0f}s")

    # Compute HW for each pair
    best_uniform = []; TOP_N = 30
    for i, j in zip(pair_idx_a, pair_idx_b):
        i, j = int(i), int(j)
        hw = 0
        s_A, s_B = states[i], states[j]
        for w in range(8): hw += bin(int(s_A[w]) ^ int(s_B[w])).count('1')
        if len(best_uniform) < TOP_N: best_uniform.append((hw, i, j)); best_uniform.sort()
        elif hw < best_uniform[-1][0]: best_uniform[-1] = (hw, i, j); best_uniform.sort()

    uniform_min = best_uniform[0][0]
    print(f"\n  UNIFORM result: min HW = {uniform_min}")
    print(f"  Top 10 uniform: {[h for h, _, _ in best_uniform[:10]]}")
    # Free state1 cache before filtered phase
    del states

    # Phase 2b: FILTERED (3-channel bucketing)
    print(f"\n# Phase 2b: FILTERED (3-channel 3-channel)...")
    ts = time.time()
    a63_bkt = (a63_all // THRESHOLD).astype(np.uint64)
    e63_bkt = (e63_all // THRESHOLD).astype(np.uint64)
    a62_bkt = (a62_all // THRESHOLD).astype(np.uint64)
    bucket_keys = (a63_bkt << 40) | (e63_bkt << 20) | a62_bkt
    sort_idx = np.argsort(bucket_keys)
    sorted_keys = bucket_keys[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    change_points = np.where(diff)[0] + 1
    run_starts = np.concatenate(([0], change_points))
    run_ends = np.concatenate((change_points, [K]))
    run_lengths = run_ends - run_starts
    multi_mask = run_lengths >= 2
    multi_starts = run_starts[multi_mask]
    multi_ends = run_ends[multi_mask]

    candidate_pairs = []
    for rs, re in zip(multi_starts, multi_ends):
        ids = sort_idx[rs:re]
        L = min(len(ids), 15)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(a63_all[i]) - int(a63_all[j])) >= THRESHOLD: continue
                if abs(int(e63_all[i]) - int(e63_all[j])) >= THRESHOLD: continue
                if abs(int(a62_all[i]) - int(a62_all[j])) >= THRESHOLD: continue
                candidate_pairs.append((i, j))

    # Match uniform pair count — truncate if more
    if len(candidate_pairs) > N_UNIFORM_PAIRS:
        candidate_pairs = candidate_pairs[:N_UNIFORM_PAIRS]
    print(f"  {len(candidate_pairs):,} filtered pairs")

    unique_filter = list(set(i for p in candidate_pairs for i in p))
    print(f"  {len(unique_filter):,} unique W[0] to compute")
    states = {}
    for bi in range(0, len(unique_filter), UBATCH):
        batch = unique_filter[bi:bi+UBATCH]
        s1_batch = compute_state1_for_indices(batch)
        for idx, w0 in enumerate(batch):
            states[w0] = s1_batch[idx].copy()

    best_filter = []
    for i, j in candidate_pairs:
        hw = 0
        s_A, s_B = states[i], states[j]
        for w in range(8): hw += bin(int(s_A[w]) ^ int(s_B[w])).count('1')
        if len(best_filter) < TOP_N: best_filter.append((hw, i, j)); best_filter.sort()
        elif hw < best_filter[-1][0]: best_filter[-1] = (hw, i, j); best_filter.sort()

    filter_min = best_filter[0][0]
    print(f"\n  FILTERED result: min HW = {filter_min}")
    print(f"  Top 10 filtered: {[h for h, _, _ in best_filter[:10]]}")

    # Report
    print(f"\n=== COMPARISON ({len(candidate_pairs):,} pair evaluations each) ===")
    print(f"  Uniform random pairs: min HW = {uniform_min}")
    print(f"  3-channel filtered:   min HW = {filter_min}")
    print(f"  Advantage:            {uniform_min - filter_min:+d} bits (filter better)")

    uniform_mean = np.mean([h for h, _, _ in best_uniform])
    filter_mean = np.mean([h for h, _, _ in best_filter])
    print(f"\nTop-30 mean HW:")
    print(f"  Uniform: {uniform_mean:.2f}")
    print(f"  Filter:  {filter_mean:.2f}")
    print(f"  Gap:     {uniform_mean - filter_mean:+.2f}")

    out = {'K': K, 'T': THRESHOLD, 'N_pairs_each': len(candidate_pairs),
           'uniform_min_hw': int(uniform_min),
           'filter_min_hw': int(filter_min),
           'uniform_top30': [int(h) for h, _, _ in best_uniform],
           'filter_top30': [int(h) for h, _, _ in best_filter],
           'uniform_top30_mean': float(uniform_mean),
           'filter_top30_mean': float(filter_mean),
           'advantage_min': int(uniform_min) - int(filter_min),
           'advantage_mean_top30': float(uniform_mean - filter_mean),
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
