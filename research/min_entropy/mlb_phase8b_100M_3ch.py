"""MLB Phase 8B: K=100M with Phase 7B filter (3-channel, T=2M).

Pure scaling test: 2× K vs Phase 7B. Predicted HW~79 per methodology's
logarithmic scaling law (K doubling → <1 bit HW reduction).
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_phase8b_100M_3ch.json')

K = 100_000_000
THRESHOLD = 2_000_000
BATCH = 500_000
TOP_N = 30


def compute_keys_3ch(W0_start, W0_end):
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


def compute_state1(W0_indices):
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
    s = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (s + ch.IV_VANILLA) & MASK


def main():
    t0 = time.time()
    print(f"# MLB Phase 8B: K={K:,}, T={THRESHOLD:,}, 3-channel (a63,e63,a62)")

    print(f"\n# Phase 1: keys...")
    ts = time.time()
    a63 = np.zeros(K, dtype=np.uint32)
    e63 = np.zeros(K, dtype=np.uint32)
    a62 = np.zeros(K, dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a, e, a2 = compute_keys_3ch(start, end)
        a63[start:end] = a
        e63[start:end] = e
        a62[start:end] = a2
        if (start + BATCH) % 10_000_000 == 0:
            el = time.time() - ts
            print(f"  {end:,}/{K:,} ({el:.0f}s)", flush=True)
    print(f"  keys: {time.time()-ts:.0f}s")

    print(f"\n# Phase 2: bucket packing...")
    ts = time.time()
    a63_bkt = (a63.astype(np.uint64) // THRESHOLD)
    e63_bkt = (e63.astype(np.uint64) // THRESHOLD)
    a62_bkt = (a62.astype(np.uint64) // THRESHOLD)
    bucket_keys = (a63_bkt << 40) | (e63_bkt << 20) | a62_bkt
    sort_idx = np.argsort(bucket_keys)
    sorted_keys = bucket_keys[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    cp = np.where(diff)[0] + 1
    run_starts = np.concatenate(([0], cp))
    run_ends = np.concatenate((cp, [K]))
    run_lengths = run_ends - run_starts
    mm = run_lengths >= 2
    multi_starts = run_starts[mm]
    multi_ends = run_ends[mm]
    multi_lengths = run_lengths[mm]
    print(f"  sort+runs: {time.time()-ts:.0f}s, {len(multi_starts):,} multi-buckets")

    print(f"\n# Phase 3: enumerate candidates...")
    ts = time.time()
    candidates = []
    for rs, re, rl in zip(multi_starts, multi_ends, multi_lengths):
        ids = sort_idx[rs:re]
        L = min(rl, 15)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(a63[i]) - int(a63[j])) >= THRESHOLD: continue
                if abs(int(e63[i]) - int(e63[j])) >= THRESHOLD: continue
                if abs(int(a62[i]) - int(a62[j])) >= THRESHOLD: continue
                candidates.append((i, j))
    print(f"  {len(candidates):,} candidates ({time.time()-ts:.0f}s)")

    print(f"\n# Phase 4: state1 computation...")
    ts = time.time()
    unique_idx = list(set(i for p in candidates for i in p))
    print(f"  {len(unique_idx):,} unique W[0]s")
    states = {}
    UBATCH = 50_000
    for bi in range(0, len(unique_idx), UBATCH):
        batch = unique_idx[bi:bi+UBATCH]
        s1b = compute_state1(batch)
        for idx, w0 in enumerate(batch):
            states[w0] = s1b[idx].copy()
    print(f"  state1s: {time.time()-ts:.0f}s")

    print(f"\n# Phase 5: HW scan...")
    ts = time.time()
    best = []
    for i, j in candidates:
        sA, sB = states[i], states[j]
        hw = sum(bin(int(sA[w]) ^ int(sB[w])).count('1') for w in range(8))
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
    print(f"  HW: {time.time()-ts:.0f}s")

    min_hw = best[0][0]
    print(f"\n=== TOP {TOP_N} ===")
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"  {r+1:>2}: HW={hw:>3}  W0_a={i:>10}  W0_b={j:>10}")

    N_u = len(candidates)
    exp_u = 128 - 8 * math.sqrt(2 * math.log(max(2, N_u)))
    print(f"\n=== SUMMARY ===")
    print(f"K={K:,}, T={THRESHOLD:,}, candidates={N_u:,}")
    print(f"Min HW: {min_hw}, Uniform baseline: {exp_u:.1f}, Advantage: +{exp_u-min_hw:.1f}")
    print(f"Phase 7B (K=50M, 3-ch, T=2M): HW=80 (125,628 pairs)")

    out = {
        'K': K, 'T': THRESHOLD, 'channels': ['a63','e63','a62'],
        'N_pairs': N_u, 'min_hw': min_hw, 'expected_uniform': exp_u,
        'top30': [(int(h), int(i), int(j)) for h, i, j in best],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
