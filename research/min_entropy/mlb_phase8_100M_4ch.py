"""MLB Phase 8 scaling: K=100M with tighter 4-channel filter.

Extensions over Phase 7B (K=50M, 3-channel, T=2M → HW=80):
- Scale: K = 100M (2× more inputs → more pair candidates)
- Channels: 4 (a63, e63, a62, e62) — adds state e at r=62 as discriminant
- Tighter filter: T = 1M (half of Phase 7B)

Prediction per methodology scaling: HW_min ≈ 79 at K=100M+3ch+T=2M.
With 4th channel + tighter T, target HW ≤ 78.

Memory: 100M × 4 × uint32 = 1.6 GB for keys; bucketing adds ~1 GB.
Runtime: ~20 min based on Phase 7B scaling.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_phase8_100M_4ch.json')

K = 100_000_000
THRESHOLD = 1_000_000
BATCH = 500_000
TOP_N = 50


def compute_keys_4ch(W0_start, W0_end):
    """Compute 4-channel sort-keys: (a63, e63, a62, e62)."""
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
    a62_arr = None; e62_arr = None
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 62:
            a62_arr = a.copy(); e62_arr = e.copy()
    return a.copy(), e.copy(), a62_arr, e62_arr


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
    print(f"# MLB Phase 8: K={K:,}, T={THRESHOLD:,}, 4-channel (a63,e63,a62,e62)")

    # Phase 1: keys
    print(f"\n# Phase 1: computing keys for {K:,}...")
    ts = time.time()
    a63 = np.zeros(K, dtype=np.uint32)
    e63 = np.zeros(K, dtype=np.uint32)
    a62 = np.zeros(K, dtype=np.uint32)
    e62 = np.zeros(K, dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a, e, a2, e2 = compute_keys_4ch(start, end)
        a63[start:end] = a
        e63[start:end] = e
        a62[start:end] = a2
        e62[start:end] = e2
        if (start + BATCH) % 10_000_000 == 0:
            el = time.time() - ts
            eta = el / (start + BATCH) * (K - start - BATCH)
            print(f"  {end:,}/{K:,} ({el:.0f}s, eta {eta:.0f}s)", flush=True)
    print(f"  keys: {time.time()-ts:.0f}s")

    # Phase 2: 4-channel bucket packing
    # Pack: bucket_id = a63_bkt<<60 | e63_bkt<<40 | a62_bkt<<20 | e62_bkt
    # Each bucket ID fits 20 bits (~1M buckets per channel at T=1M, within uint64 bounds)
    print(f"\n# Phase 2: 4-channel bucket packing (T={THRESHOLD:,})...")
    ts = time.time()
    a63_bkt = (a63.astype(np.uint64) // THRESHOLD)
    e63_bkt = (e63.astype(np.uint64) // THRESHOLD)
    a62_bkt = (a62.astype(np.uint64) // THRESHOLD)
    e62_bkt = (e62.astype(np.uint64) // THRESHOLD)
    # Mask: 16 bits per channel (up to 65536 buckets; 2^32/1M = ~4300, fits)
    bucket_keys = (a63_bkt << 48) | (e63_bkt << 32) | (a62_bkt << 16) | e62_bkt

    sort_idx = np.argsort(bucket_keys)
    sorted_keys = bucket_keys[sort_idx]
    print(f"  sort: {time.time()-ts:.0f}s")

    ts = time.time()
    diff = sorted_keys[1:] != sorted_keys[:-1]
    change_points = np.where(diff)[0] + 1
    run_starts = np.concatenate(([0], change_points))
    run_ends = np.concatenate((change_points, [K]))
    run_lengths = run_ends - run_starts
    multi_mask = run_lengths >= 2
    multi_starts = run_starts[multi_mask]
    multi_ends = run_ends[multi_mask]
    multi_lengths = run_lengths[multi_mask]
    print(f"  runs: {time.time()-ts:.0f}s, {len(multi_starts):,} multi-buckets, "
          f"max run={multi_lengths.max() if len(multi_lengths) else 0}")

    # Phase 3: exact-threshold verification + candidate enumeration
    print(f"\n# Phase 3: enumerating pairs...")
    ts = time.time()
    candidates = []
    for rs, re, rl in zip(multi_starts, multi_ends, multi_lengths):
        ids = sort_idx[rs:re]
        L = min(rl, 20)  # limit within-bucket pairs
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(a63[i]) - int(a63[j])) >= THRESHOLD: continue
                if abs(int(e63[i]) - int(e63[j])) >= THRESHOLD: continue
                if abs(int(a62[i]) - int(a62[j])) >= THRESHOLD: continue
                if abs(int(e62[i]) - int(e62[j])) >= THRESHOLD: continue
                candidates.append((i, j))
    print(f"  {len(candidates):,} candidate pairs ({time.time()-ts:.0f}s)")

    # Phase 4: state1 for unique candidates
    print(f"\n# Phase 4: state1 computation...")
    ts = time.time()
    unique_idx = list(set(i for p in candidates for i in p))
    print(f"  {len(unique_idx):,} unique W[0]s")
    states = {}
    UBATCH = 50_000
    for bi in range(0, len(unique_idx), UBATCH):
        batch = unique_idx[bi:bi+UBATCH]
        s1_batch = compute_state1_for_indices(batch)
        for idx, w0 in enumerate(batch):
            states[w0] = s1_batch[idx].copy()
    print(f"  state1s: {time.time()-ts:.0f}s")

    # Phase 5: HW scan
    print(f"\n# Phase 5: HW computation...")
    ts = time.time()
    best = []
    for i, j in candidates:
        s_A = states[i]; s_B = states[j]
        hw = sum(bin(int(s_A[w]) ^ int(s_B[w])).count('1') for w in range(8))
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
    print(f"  HW scan: {time.time()-ts:.0f}s")

    # Report
    min_hw = best[0][0] if best else None
    print(f"\n=== TOP {TOP_N} NEAR-COLLISIONS ===")
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"  {r+1:>2}: HW={hw:>3}  W0_a={i:>10}  W0_b={j:>10}")

    N_used = len(candidates)
    exp_uniform = 128 - 8 * math.sqrt(2 * math.log(max(2, N_used)))
    print(f"\n=== SUMMARY ===")
    print(f"K = {K:,}, T = {THRESHOLD:,}, candidates = {N_used:,}")
    print(f"Minimum HW: {min_hw}")
    print(f"Uniform baseline: ≈ {exp_uniform:.1f}")
    print(f"Advantage: {exp_uniform - min_hw:+.1f} bits")
    print(f"Phase 7B (K=50M, 3-ch, T=2M): HW=80")
    if min_hw and min_hw < 80:
        print(f"★ IMPROVED: {min_hw} (-{80-min_hw} vs Phase 7B)")

    out = {
        'K': K, 'T': THRESHOLD, 'channels': ['a63','e63','a62','e62'],
        'N_pairs': N_used, 'min_hw': min_hw,
        'expected_uniform': exp_uniform,
        'top50': [(int(h), int(i), int(j)) for h, i, j in best],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
