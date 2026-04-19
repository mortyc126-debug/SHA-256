"""MLB Phase 10: multi-sort-key union at K=100M.

Hypothesis: Phase 9 showed different sort-keys find different pairs.
Union of 2 sort-key candidate sets at fixed K should find lower HW than
either alone.

Experiment:
- K = 100M
- Sort-key 1: (a63, e63, a62) — original
- Sort-key 2: (a61, a60, e62) — alternative
- Compute both in SINGLE pass (same compression)
- Bucket each, union candidates, find min HW

Expected:
- Each alone: ~HW=78-80 at K=100M
- Union: HW=76-77 possible (extra candidates)

Runtime ~15 min (one compression pass, two buckets).
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_phase10_union.json')

K = 100_000_000
THRESHOLD = 2_000_000
BATCH = 500_000
TOP_N = 30


def compute_all_keys(W0_start, W0_end):
    """Compute all 6 keys in single pass: (a63, e63, a62, a61, a60, e62)."""
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
    a60, a61, a62, a63 = None, None, None, None
    e62, e63 = None, None
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 60: a60 = a.copy()
        if t == 61: a61 = a.copy()
        if t == 62: a62 = a.copy(); e62 = e.copy()
        if t == 63: a63 = a.copy(); e63 = e.copy()
    return a63, e63, a62, a61, a60, e62


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


def bucket_and_enum(k1, k2, k3, T, K_tot):
    """Bucket on (k1//T, k2//T, k3//T), return candidate pairs."""
    k1b = (k1.astype(np.uint64) // T)
    k2b = (k2.astype(np.uint64) // T)
    k3b = (k3.astype(np.uint64) // T)
    bkey = (k1b << 40) | (k2b << 20) | k3b
    sort_idx = np.argsort(bkey)
    sorted_keys = bkey[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    cp = np.where(diff)[0] + 1
    rs = np.concatenate(([0], cp))
    re = np.concatenate((cp, [K_tot]))
    rl = re - rs
    mm = rl >= 2
    ms = rs[mm]; me = re[mm]; ml = rl[mm]
    cands = []
    for rs_, re_, rl_ in zip(ms, me, ml):
        ids = sort_idx[rs_:re_]
        L = min(rl_, 12)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(k1[i]) - int(k1[j])) >= T: continue
                if abs(int(k2[i]) - int(k2[j])) >= T: continue
                if abs(int(k3[i]) - int(k3[j])) >= T: continue
                cands.append((i, j))
    return cands, len(ms)


def main():
    t0 = time.time()
    print(f"# MLB Phase 10: K={K:,}, multi-sort-key union", flush=True)

    print(f"\n# Phase 1: compute all 6 keys (single pass)...", flush=True)
    ts = time.time()
    a63 = np.zeros(K, dtype=np.uint32); e63 = np.zeros(K, dtype=np.uint32)
    a62 = np.zeros(K, dtype=np.uint32); a61 = np.zeros(K, dtype=np.uint32)
    a60 = np.zeros(K, dtype=np.uint32); e62 = np.zeros(K, dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        k1,k2,k3,k4,k5,k6 = compute_all_keys(start, end)
        a63[start:end]=k1; e63[start:end]=k2; a62[start:end]=k3
        a61[start:end]=k4; a60[start:end]=k5; e62[start:end]=k6
        if (start+BATCH) % 10_000_000 == 0:
            el = time.time()-ts
            print(f"  {end:,}/{K:,} ({el:.0f}s)", flush=True)
    print(f"  keys: {time.time()-ts:.0f}s", flush=True)

    print(f"\n# Phase 2: bucket sort-key A (a63,e63,a62)...", flush=True)
    ts = time.time()
    cands_A, nbA = bucket_and_enum(a63, e63, a62, THRESHOLD, K)
    print(f"  {len(cands_A):,} cand A, {nbA:,} buckets ({time.time()-ts:.0f}s)", flush=True)

    print(f"\n# Phase 2b: bucket sort-key B (a61,a60,e62)...", flush=True)
    ts = time.time()
    cands_B, nbB = bucket_and_enum(a61, a60, e62, THRESHOLD, K)
    print(f"  {len(cands_B):,} cand B, {nbB:,} buckets ({time.time()-ts:.0f}s)", flush=True)

    # Union
    set_A = set(cands_A)
    set_B = set(cands_B)
    union = set_A | set_B
    intersect = set_A & set_B
    print(f"\n  A: {len(set_A):,}, B: {len(set_B):,}, "
          f"Union: {len(union):,}, Intersect: {len(intersect):,}", flush=True)

    print(f"\n# Phase 3: state1 for union...", flush=True)
    ts = time.time()
    union_list = list(union)
    unique = list(set(i for p in union_list for i in p))
    print(f"  {len(unique):,} unique W[0]s", flush=True)
    states = {}
    for bi in range(0, len(unique), 50_000):
        batch = unique[bi:bi+50_000]
        sb = compute_state1(batch)
        for k, w0 in enumerate(batch): states[w0] = sb[k].copy()
    print(f"  state1s: {time.time()-ts:.0f}s", flush=True)

    print(f"\n# Phase 4: HW scan...", flush=True)
    ts = time.time()
    best = []; best_A = []; best_B = []
    for i, j in union_list:
        sA, sB = states[i], states[j]
        hw = sum(bin(int(sA[w]) ^ int(sB[w])).count('1') for w in range(8))
        p = (i, j)
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
        # track which sort-key caught it
        if p in set_A:
            if len(best_A) < 5: best_A.append((hw, i, j)); best_A.sort()
            elif hw < best_A[-1][0]: best_A[-1] = (hw, i, j); best_A.sort()
        if p in set_B:
            if len(best_B) < 5: best_B.append((hw, i, j)); best_B.sort()
            elif hw < best_B[-1][0]: best_B[-1] = (hw, i, j); best_B.sort()
    print(f"  HW: {time.time()-ts:.0f}s", flush=True)

    min_hw = best[0][0]
    print(f"\n=== TOP {TOP_N} (UNION) ===", flush=True)
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        src = ""
        if (i,j) in set_A and (i,j) in set_B: src = "[both]"
        elif (i,j) in set_A: src = "[A only]"
        elif (i,j) in set_B: src = "[B only]"
        print(f"  {r+1:>2}: HW={hw:>3}  ({i:>10}, {j:>10})  {src}", flush=True)

    print(f"\n=== TOP 5 per sort-key ===", flush=True)
    print("A (a63,e63,a62):", [b[0] for b in best_A])
    print("B (a61,a60,e62):", [b[0] for b in best_B])

    N_u = len(union)
    exp_u = 128 - 8 * math.sqrt(2 * math.log(max(2, N_u)))
    print(f"\n=== SUMMARY ===", flush=True)
    print(f"K={K:,}, T={THRESHOLD:,}, union cands={N_u:,}", flush=True)
    print(f"Min HW (union): {min_hw}", flush=True)
    print(f"A alone min: {best_A[0][0] if best_A else None}", flush=True)
    print(f"B alone min: {best_B[0][0] if best_B else None}", flush=True)
    print(f"Uniform baseline: {exp_u:.1f}, Advantage: +{exp_u-min_hw:.1f}", flush=True)
    print(f"Phase 8B reference: K=100M single sort → HW=78", flush=True)
    print(f"Phase 8C reference: K=200M single sort → HW=77", flush=True)
    if min_hw < 78:
        print(f"★★★ UNION IMPROVES: HW={min_hw}", flush=True)

    out = {
        'K': K, 'T': THRESHOLD,
        'sort_key_A': ['a63','e63','a62'],
        'sort_key_B': ['a61','a60','e62'],
        'N_A': len(set_A), 'N_B': len(set_B),
        'N_union': len(union), 'N_intersect': len(intersect),
        'min_hw_union': min_hw,
        'min_hw_A': best_A[0][0] if best_A else None,
        'min_hw_B': best_B[0][0] if best_B else None,
        'top30': [(int(h), int(i), int(j)) for h, i, j in best],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == '__main__': main()
