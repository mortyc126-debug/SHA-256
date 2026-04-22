"""MLB Phase 8C: K=200M scaling (2× beyond Phase 8B).

Phase 8B at K=100M: HW=78
Scaling law (logarithmic): K doubling → ~2 bit reduction
Prediction: K=200M → HW≈76
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_phase8c_200M.json')

K = 200_000_000
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
    print(f"# MLB Phase 8C: K={K:,}, T={THRESHOLD:,}, 3-channel")

    print(f"\n# Phase 1: keys for {K:,}...")
    ts = time.time()
    a63 = np.zeros(K, dtype=np.uint32)
    e63 = np.zeros(K, dtype=np.uint32)
    a62 = np.zeros(K, dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a, e, a2 = compute_keys_3ch(start, end)
        a63[start:end] = a; e63[start:end] = e; a62[start:end] = a2
        if (start + BATCH) % 20_000_000 == 0:
            el = time.time() - ts
            eta = el / (start + BATCH) * (K - start - BATCH)
            print(f"  {end:,}/{K:,} ({el:.0f}s, eta {eta:.0f}s)", flush=True)
    print(f"  keys: {time.time()-ts:.0f}s")

    print(f"\n# Phase 2: bucketing...")
    ts = time.time()
    a63_b = (a63.astype(np.uint64) // THRESHOLD)
    e63_b = (e63.astype(np.uint64) // THRESHOLD)
    a62_b = (a62.astype(np.uint64) // THRESHOLD)
    bkey = (a63_b << 40) | (e63_b << 20) | a62_b
    sort_idx = np.argsort(bkey)
    sorted_keys = bkey[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    cp = np.where(diff)[0] + 1
    rs = np.concatenate(([0], cp))
    re = np.concatenate((cp, [K]))
    rl = re - rs
    mm = rl >= 2
    multi_s = rs[mm]; multi_e = re[mm]; multi_l = rl[mm]
    print(f"  {time.time()-ts:.0f}s, {len(multi_s):,} multi-buckets")

    print(f"\n# Phase 3: candidates...")
    ts = time.time()
    cands = []
    for rs_, re_, rl_ in zip(multi_s, multi_e, multi_l):
        ids = sort_idx[rs_:re_]
        L = min(rl_, 12)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(a63[i]) - int(a63[j])) >= THRESHOLD: continue
                if abs(int(e63[i]) - int(e63[j])) >= THRESHOLD: continue
                if abs(int(a62[i]) - int(a62[j])) >= THRESHOLD: continue
                cands.append((i, j))
    print(f"  {len(cands):,} candidates ({time.time()-ts:.0f}s)")

    print(f"\n# Phase 4: state1...")
    ts = time.time()
    unique = list(set(i for p in cands for i in p))
    print(f"  {len(unique):,} unique W[0]s")
    states = {}
    for bi in range(0, len(unique), 50_000):
        batch = unique[bi:bi+50_000]
        sb = compute_state1(batch)
        for k, w0 in enumerate(batch): states[w0] = sb[k].copy()
    print(f"  {time.time()-ts:.0f}s")

    print(f"\n# Phase 5: HW...")
    ts = time.time()
    best = []
    for i, j in cands:
        sA, sB = states[i], states[j]
        hw = sum(bin(int(sA[w]) ^ int(sB[w])).count('1') for w in range(8))
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
    print(f"  {time.time()-ts:.0f}s")

    min_hw = best[0][0]
    print(f"\n=== TOP {TOP_N} ===")
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"  {r+1:>2}: HW={hw:>3}  W0_a={i:>10}  W0_b={j:>10}")

    N_u = len(cands)
    exp_u = 128 - 8 * math.sqrt(2 * math.log(max(2, N_u)))
    print(f"\n=== SUMMARY ===")
    print(f"K={K:,}, T={THRESHOLD:,}, candidates={N_u:,}")
    print(f"Min HW: {min_hw}, Uniform: {exp_u:.1f}, Advantage: +{exp_u-min_hw:.1f}")
    print(f"Previous: Phase 8B K=100M → HW=78 (504K pairs)")
    if min_hw < 78: print(f"★★★ NEW RECORD: HW={min_hw} (-{78-min_hw} vs Phase 8B)")

    out = {
        'K': K, 'T': THRESHOLD, 'channels': ['a63','e63','a62'],
        'N_pairs': N_u, 'min_hw': min_hw, 'expected_uniform': exp_u,
        'top30': [(int(h), int(i), int(j)) for h, i, j in best],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
