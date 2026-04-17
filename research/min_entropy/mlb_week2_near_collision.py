"""MLB Week 2 Day 1: concrete near-collision search.

Use our 3-channel sort-key filter to find the PAIR WITH MINIMUM HW(Δstate1).

Standard birthday math: for N=10M random state1 samples (256 bits each),
expected minimum HW(Δ) over all N²/2 pairs ≈ 128 - sqrt(2·log(N²))·8 ≈ 68-72.

If our 3-channel filter gives 2^119 effective birthday:
- Advantage ~17 bits shift in HW(Δ) mean (111 vs 128 uniform)
- Tail extreme might shift by ~sqrt(17) bits → min HW ~60-65

Concrete goal: find minimum HW(Δstate1) from joint-close pairs.
If << 60 → breaking world records on near-collisions.

Method:
1. Generate K=10M W[0] scan, compute state1 + sort keys (a63, e63, a62)
2. Bucket by (a63//T, e63//T, a62//T) for T=500K
3. For each same-bucket pair, compute actual HW(Δstate1)
4. Track minimum HW found
5. Report top-10 near-collision pairs with their W[0] values
"""
import math, os, json, time
from collections import defaultdict
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week2_near_collision.json')

K = 10_000_000
THRESHOLD = 500_000
TOP_N = 20


def compute_registers_state1(W0_start, W0_end):
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
    # a63, e63 are the current a, e after round 63
    a63_arr = a.copy()
    e63_arr = e.copy()
    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return a63_arr, e63_arr, a62_arr, state1


def hw_diff_full256(s_A, s_B):
    hw = 0
    for w in range(8):
        hw += bin(int(s_A[w]) ^ int(s_B[w])).count('1')
    return hw


def main():
    t0 = time.time()
    print(f"# MLB Week 2 Day 1: near-collision search")
    print(f"# K = {K:,}, 3-channel sort-key with T={THRESHOLD:,}")

    # Phase 1: compute everything
    print(f"\n# Phase 1: computing registers + state1...")
    ts = time.time()
    a63_all = np.zeros(K, dtype=np.uint32)
    e63_all = np.zeros(K, dtype=np.uint32)
    a62_all = np.zeros(K, dtype=np.uint32)
    state1_all = np.zeros((K, 8), dtype=np.uint32)
    BATCH = 200_000
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        a63, e63, a62, s1 = compute_registers_state1(start, end)
        a63_all[start:end] = a63
        e63_all[start:end] = e63
        a62_all[start:end] = a62
        state1_all[start:end] = s1
        if (start + BATCH) % 2_000_000 == 0:
            print(f"  {end:,}/{K:,} ({time.time()-ts:.0f}s)", flush=True)
    print(f"  time: {time.time()-ts:.0f}s")

    # Phase 2: bucketing
    print(f"\n# Phase 2: bucketing by (a63, e63, a62) // T={THRESHOLD}...")
    ts = time.time()
    buckets = defaultdict(list)
    for i in range(K):
        key = (int(a63_all[i]) // THRESHOLD,
               int(e63_all[i]) // THRESHOLD,
               int(a62_all[i]) // THRESHOLD)
        buckets[key].append(i)
    # Keep only non-empty buckets
    n_buckets_nonempty = sum(1 for v in buckets.values() if len(v) >= 2)
    print(f"  time: {time.time()-ts:.0f}s, {len(buckets):,} total buckets, "
          f"{n_buckets_nonempty:,} with ≥2 samples")

    # Phase 3: enumerate pairs within each bucket, track MIN HW
    print(f"\n# Phase 3: enumerating pairs, finding min HW...")
    ts = time.time()
    best = []  # [(hw, i, j), ...] — keep top-TOP_N smallest HW
    pair_count = 0
    for bucket_ids in buckets.values():
        if len(bucket_ids) < 2: continue
        L = len(bucket_ids)
        # Cap inner loop at 30 to limit combinatorial explosion
        L = min(L, 30)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = bucket_ids[ii], bucket_ids[jj]
                # Verify 3-channel close
                if abs(int(a63_all[i]) - int(a63_all[j])) >= THRESHOLD: continue
                if abs(int(e63_all[i]) - int(e63_all[j])) >= THRESHOLD: continue
                if abs(int(a62_all[i]) - int(a62_all[j])) >= THRESHOLD: continue
                hw = hw_diff_full256(state1_all[i], state1_all[j])
                pair_count += 1
                if len(best) < TOP_N:
                    best.append((hw, i, j))
                    best.sort()
                elif hw < best[-1][0]:
                    best[-1] = (hw, i, j)
                    best.sort()
    print(f"  time: {time.time()-ts:.0f}s, evaluated {pair_count:,} pairs")

    # Phase 4: report
    print(f"\n=== TOP-{TOP_N} NEAR-COLLISIONS ===")
    print(f"{'rank':>4} {'HW(Δstate1)':>13} {'W0_a':>10} {'W0_b':>10} {'Δa63':>12} {'Δe63':>12} {'Δa62':>12}")
    for r, (hw, i, j) in enumerate(best):
        da = abs(int(a63_all[i]) - int(a63_all[j]))
        de = abs(int(e63_all[i]) - int(e63_all[j]))
        da2 = abs(int(a62_all[i]) - int(a62_all[j]))
        print(f"{r+1:>4} {hw:>13} {i:>10} {j:>10} {da:>12} {de:>12} {da2:>12}")

    min_hw = best[0][0] if best else 0
    print(f"\n=== SUMMARY ===")
    print(f"Minimum HW(Δstate1) found: {min_hw}")
    print(f"Random baseline (N²/2 = {K*K/2:.1e} pairs, N(128, 8²) min):")
    # Expected min for N²/2 uniform draws from Binomial(256, 0.5)
    # approx: x = 128 - sqrt(2·log(N²/2)) · sqrt(64)
    N2 = K*K/2
    exp_min = 128 - math.sqrt(2 * math.log(N2)) * 8
    print(f"  Expected min HW ≈ {exp_min:.1f}")
    print(f"Our min: {min_hw}, delta from uniform: {min_hw - exp_min:+.1f}")
    if min_hw < exp_min - 2:
        print(f"  ★ REAL ADVANTAGE: our sort-key filter finds smaller-HW pair than uniform search")
    elif min_hw > exp_min + 2:
        print(f"  (sampling penalty — filter restricts pair space)")
    else:
        print(f"  (no significant tail advantage)")

    out = {'K': K, 'T': THRESHOLD, 'n_pairs_evaluated': pair_count,
           'min_hw': min_hw, 'expected_uniform_min': exp_min,
           'top_n': [{'rank': r+1, 'hw': hw, 'i': i, 'j': j,
                      'delta_a63': abs(int(a63_all[i]) - int(a63_all[j])),
                      'delta_e63': abs(int(e63_all[i]) - int(e63_all[j])),
                      'delta_a62': abs(int(a62_all[i]) - int(a62_all[j]))}
                     for r, (hw, i, j) in enumerate(best)],
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
