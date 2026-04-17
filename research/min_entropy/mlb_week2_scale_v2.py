"""MLB Week 2 Day 2 v2: numpy-vectorized bucketing for K=50M.

Previous version died on Python dict insert for 50M samples.
Use numpy: pack 3 bucket IDs into one uint64, sort, find runs.

Bucket key packing:
  key = a63_bkt * 2^40 + e63_bkt * 2^20 + a62_bkt
  (each bkt_i fits in 20 bits: 2^32 / T = 2^32 / 2^21 = 2^11 buckets per dim,
  so 20 bits is plenty)
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week2_scale50M_v2.json')

K = 50_000_000
THRESHOLD = 2_000_000


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
    print(f"# MLB Week 2 Day 2 v2: K={K:,}, T={THRESHOLD:,}, numpy bucketing")

    # Phase 1: compute keys
    print(f"\n# Phase 1: keys for {K:,}...")
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
    print(f"  time: {time.time()-ts:.0f}s")

    # Phase 2: numpy bucketing
    print(f"\n# Phase 2: numpy bucketing...")
    ts = time.time()
    # Pack bucket IDs into single uint64: a63_bkt << 40 | e63_bkt << 20 | a62_bkt
    a63_bkt = (a63_all // THRESHOLD).astype(np.uint64)
    e63_bkt = (e63_all // THRESHOLD).astype(np.uint64)
    a62_bkt = (a62_all // THRESHOLD).astype(np.uint64)
    bucket_keys = (a63_bkt << 40) | (e63_bkt << 20) | a62_bkt
    # Sort
    sort_idx = np.argsort(bucket_keys)
    sorted_keys = bucket_keys[sort_idx]
    print(f"  sort: {time.time()-ts:.0f}s")

    # Find runs of equal bucket keys
    ts = time.time()
    # Find boundaries where key changes
    diff = sorted_keys[1:] != sorted_keys[:-1]
    change_points = np.where(diff)[0] + 1
    # Prepend 0, append K
    run_starts = np.concatenate(([0], change_points))
    run_ends = np.concatenate((change_points, [K]))
    # Filter to runs of length >= 2
    run_lengths = run_ends - run_starts
    multi_run_mask = run_lengths >= 2
    multi_starts = run_starts[multi_run_mask]
    multi_ends = run_ends[multi_run_mask]
    multi_lengths = run_lengths[multi_run_mask]
    print(f"  run finding: {time.time()-ts:.0f}s, {len(multi_starts):,} multi-buckets, "
          f"max len {multi_lengths.max() if len(multi_lengths) else 0}")

    # Phase 3: enumerate pairs
    print(f"\n# Phase 3: enumerating candidate pairs...")
    ts = time.time()
    candidate_pairs = []
    for rs, re, rl in zip(multi_starts, multi_ends, multi_lengths):
        ids = sort_idx[rs:re]
        L = min(rl, 15)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                # Verify exact threshold (neighboring buckets can still be far)
                if abs(int(a63_all[i]) - int(a63_all[j])) >= THRESHOLD: continue
                if abs(int(e63_all[i]) - int(e63_all[j])) >= THRESHOLD: continue
                if abs(int(a62_all[i]) - int(a62_all[j])) >= THRESHOLD: continue
                candidate_pairs.append((i, j))
    print(f"  {len(candidate_pairs):,} candidates ({time.time()-ts:.0f}s)")

    # Phase 4: state1 for candidates
    print(f"\n# Phase 4: state1 for unique W[0]s...")
    ts = time.time()
    unique_idx = list(set(i for p in candidate_pairs for i in p))
    print(f"  {len(unique_idx):,} unique")
    states = {}
    UBATCH = 50_000
    for bi in range(0, len(unique_idx), UBATCH):
        batch = unique_idx[bi:bi+UBATCH]
        s1_batch = compute_state1_for_indices(batch)
        for idx, w0 in enumerate(batch):
            states[w0] = s1_batch[idx].copy()
    print(f"  {time.time()-ts:.0f}s")

    # Phase 5: HW computation
    print(f"\n# Phase 5: HW scan...")
    ts = time.time()
    best = []; TOP_N = 30
    for i, j in candidate_pairs:
        hw = 0
        s_A, s_B = states[i], states[j]
        for w in range(8): hw += bin(int(s_A[w]) ^ int(s_B[w])).count('1')
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
    print(f"  {time.time()-ts:.0f}s")

    # Report
    min_hw = best[0][0] if best else None
    print(f"\n=== TOP {TOP_N} NEAR-COLLISIONS ===")
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"  {r+1:>2}: HW={hw:>3}  W0_a={i:>10}  W0_b={j:>10}")

    N_used = len(candidate_pairs)
    exp_uniform = 128 - 8 * math.sqrt(2 * math.log(max(2, N_used)))
    print(f"\n=== SUMMARY ===")
    print(f"K = {K:,}, T = {THRESHOLD:,}, candidate pairs = {N_used:,}")
    print(f"Minimum HW: {min_hw}")
    print(f"Uniform baseline: ≈ {exp_uniform:.1f}")
    print(f"Advantage: {exp_uniform - min_hw:+.1f} bits")
    print(f"Previous (K=10M): 85")
    if min_hw and min_hw < 85:
        print(f"★ IMPROVED: {min_hw} (-{85-min_hw} vs K=10M)")

    out = {'K': K, 'T': THRESHOLD, 'N_pairs': N_used, 'min_hw': min_hw,
           'expected_uniform': exp_uniform,
           'top30': [(int(h), int(i), int(j)) for h, i, j in best],
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
