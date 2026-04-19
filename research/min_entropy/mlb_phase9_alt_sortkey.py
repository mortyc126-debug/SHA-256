"""MLB Phase 9: alternative sort-key choice at K=200M.

Phase 8C used sort-key = (a63, e63, a62) = state1[0, 4, 1] and got HW=77.
Question: do alternative sort-keys find DIFFERENT (lower HW) pairs?

Test: (a61, a60, e62) = state1[2, 3, 5] — completely different state words.

If finds HW<77 → algorithmic diversity matters, multi-sort strategy promising.
If finds HW≈77 → raw scaling is only path forward.

Runtime ~25 min matching Phase 8C.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_phase9_alt_sortkey.json')

K = 200_000_000
THRESHOLD = 2_000_000
BATCH = 500_000
TOP_N = 30

# Alternative sort-key: probe state1[2], state1[3], state1[5]
# state1[2] = c63 = b62 = a61 (+IV)
# state1[3] = d63 = c62 = b61 = a60 (+IV)
# state1[5] = f63 = e62 (+IV)


def compute_alt_keys(W0_start, W0_end):
    """Compute (a61, a60, e62) keys."""
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
    a61_arr = None; a60_arr = None; e62_arr = None
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 60: a60_arr = a.copy()
        if t == 61: a61_arr = a.copy()
        if t == 62: e62_arr = e.copy()
    return a61_arr, a60_arr, e62_arr


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
    print(f"# MLB Phase 9: K={K:,}, T={THRESHOLD:,}, alt sort-key (a61,a60,e62)", flush=True)

    print(f"\n# Phase 1: alt keys...", flush=True)
    ts = time.time()
    a61 = np.zeros(K, dtype=np.uint32)
    a60 = np.zeros(K, dtype=np.uint32)
    e62 = np.zeros(K, dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        k1, k2, k3 = compute_alt_keys(start, end)
        a61[start:end] = k1; a60[start:end] = k2; e62[start:end] = k3
        if (start + BATCH) % 20_000_000 == 0:
            el = time.time() - ts
            print(f"  {end:,}/{K:,} ({el:.0f}s)", flush=True)
    print(f"  keys: {time.time()-ts:.0f}s", flush=True)

    print(f"\n# Phase 2: bucketing...", flush=True)
    ts = time.time()
    k1b = (a61.astype(np.uint64) // THRESHOLD)
    k2b = (a60.astype(np.uint64) // THRESHOLD)
    k3b = (e62.astype(np.uint64) // THRESHOLD)
    bkey = (k1b << 40) | (k2b << 20) | k3b
    sort_idx = np.argsort(bkey)
    sorted_keys = bkey[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    cp = np.where(diff)[0] + 1
    rs = np.concatenate(([0], cp))
    re = np.concatenate((cp, [K]))
    rl = re - rs
    mm = rl >= 2
    ms = rs[mm]; me = re[mm]; ml = rl[mm]
    print(f"  {time.time()-ts:.0f}s, {len(ms):,} multi-buckets", flush=True)

    print(f"\n# Phase 3: candidates...", flush=True)
    ts = time.time()
    cands = []
    for rs_, re_, rl_ in zip(ms, me, ml):
        ids = sort_idx[rs_:re_]
        L = min(rl_, 12)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(a61[i]) - int(a61[j])) >= THRESHOLD: continue
                if abs(int(a60[i]) - int(a60[j])) >= THRESHOLD: continue
                if abs(int(e62[i]) - int(e62[j])) >= THRESHOLD: continue
                cands.append((i, j))
    print(f"  {len(cands):,} candidates ({time.time()-ts:.0f}s)", flush=True)

    print(f"\n# Phase 4: state1...", flush=True)
    ts = time.time()
    unique = list(set(i for p in cands for i in p))
    print(f"  {len(unique):,} unique W[0]s", flush=True)
    states = {}
    for bi in range(0, len(unique), 50_000):
        batch = unique[bi:bi+50_000]
        sb = compute_state1(batch)
        for k, w0 in enumerate(batch): states[w0] = sb[k].copy()
    print(f"  {time.time()-ts:.0f}s", flush=True)

    print(f"\n# Phase 5: HW...", flush=True)
    ts = time.time()
    best = []
    for i, j in cands:
        sA, sB = states[i], states[j]
        hw = sum(bin(int(sA[w]) ^ int(sB[w])).count('1') for w in range(8))
        if len(best) < TOP_N: best.append((hw, i, j)); best.sort()
        elif hw < best[-1][0]: best[-1] = (hw, i, j); best.sort()
    print(f"  {time.time()-ts:.0f}s", flush=True)

    min_hw = best[0][0]
    print(f"\n=== TOP {TOP_N} (alt sort-key) ===", flush=True)
    for r, (hw, i, j) in enumerate(best[:TOP_N]):
        print(f"  {r+1:>2}: HW={hw:>3}  W0_a={i:>10}  W0_b={j:>10}", flush=True)

    N_u = len(cands)
    exp_u = 128 - 8 * math.sqrt(2 * math.log(max(2, N_u)))
    print(f"\n=== SUMMARY ===", flush=True)
    print(f"Alt sort-key (a61,a60,e62): K={K:,}, candidates={N_u:,}", flush=True)
    print(f"Min HW: {min_hw}, Uniform: {exp_u:.1f}, Advantage: +{exp_u-min_hw:.1f}", flush=True)
    print(f"Phase 8C (a63,e63,a62): K=200M → HW=77", flush=True)
    if min_hw < 77:
        print(f"★★★ ALT SORT BETTER: HW={min_hw} — algorithmic diversity wins!", flush=True)
    elif min_hw == 77:
        print(f"Same HW=77 — maybe different pair. Check W0 values.", flush=True)
    else:
        print(f"Alt worse: HW={min_hw} vs 77. (a63,e63,a62) superior.", flush=True)

    out = {
        'K': K, 'T': THRESHOLD, 'channels': ['a61','a60','e62'],
        'N_pairs': N_u, 'min_hw': min_hw, 'expected_uniform': exp_u,
        'top30': [(int(h), int(i), int(j)) for h, i, j in best],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == '__main__': main()
