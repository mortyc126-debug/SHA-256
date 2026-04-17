"""MLB Week 1 Day 3: 3+ channel stacking — cross-round independence.

Day 2 result: 2-channel (a63, e63) gives 15-bit gap → 2^120.5 birthday.

Day 3 question: does adding MORE independent sort-keys stack further?
Candidates:
- a62, e62 (one round earlier — cross-round)
- a60, e60 (earlier still — phase transition boundary)

If a60 and a63 are ALGEBRAICALLY independent (not just shift copies),
their combined close-sort gives extra bits.

Test configurations:
1. Baseline 2ch: a63 + e63
2. 3ch A: a63 + e63 + a62
3. 3ch B: a63 + e63 + e62
4. 4ch: a63 + e63 + a62 + e62
5. Wide 4ch: a60 + e60 + a63 + e63

For each: bucketing with matched T, measure gap.
"""
import math, os, json, time
from collections import defaultdict
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_stack_3plus.json')

K = 10_000_000


def compute_registers_at_rounds(W0_start, W0_end, rounds):
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
    snapshots = {}
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t in rounds:
            snapshots[('a', t)] = a.copy()
            snapshots[('e', t)] = e.copy()
    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return snapshots, state1


def joint_close_via_buckets(keys_list, state1, T, max_pairs=3000):
    """Return list of HW(Δstate1) for pairs joint-close on all keys (within T)."""
    Kn = len(keys_list[0])
    buckets = defaultdict(list)
    for i in range(Kn):
        key = tuple(int(k[i]) // T for k in keys_list)
        buckets[key].append(i)
    close_hw = []
    # Iterate buckets, check actual distances
    for bucket_ids in buckets.values():
        if len(bucket_ids) < 2: continue
        L = min(len(bucket_ids), 15)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = bucket_ids[ii], bucket_ids[jj]
                # Verify all keys within T
                ok = all(abs(int(k[i]) - int(k[j])) < T for k in keys_list)
                if not ok: continue
                hw = 0
                for w in range(8):
                    hw += bin(int(state1[i, w]) ^ int(state1[j, w])).count('1')
                close_hw.append(hw)
                if len(close_hw) >= max_pairs: return close_hw
    return close_hw


def sample_far_baseline(state1, key_single, T_far, n_target, rng):
    Kn = len(state1)
    far_hw = []
    attempts = 0
    while len(far_hw) < n_target and attempts < 200_000:
        i, j = rng.integers(0, Kn), rng.integers(0, Kn)
        if i == j: attempts += 1; continue
        if abs(int(key_single[i]) - int(key_single[j])) > T_far:
            hw = 0
            for w in range(8):
                hw += bin(int(state1[i, w]) ^ int(state1[j, w])).count('1')
            far_hw.append(hw)
        attempts += 1
    return far_hw


def main():
    t0 = time.time()
    print(f"# MLB Day 3: 3+ channel stacking")
    print(f"# K = {K:,} W[0]")

    print(f"\n# Phase 1: computing registers at rounds {{60, 62, 63}}...")
    ts = time.time()
    BATCH = 200_000
    rounds_needed = {60, 62, 63}
    snaps_all = {(r, t): np.zeros(K, dtype=np.uint32) for r in ['a', 'e'] for t in rounds_needed}
    state1_all = np.zeros((K, 8), dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        s, s1 = compute_registers_at_rounds(start, end, rounds_needed)
        for key, arr in s.items():
            snaps_all[key][start:end] = arr
        state1_all[start:end] = s1
        if (start + BATCH) % 2_000_000 == 0:
            print(f"  {end:,}/{K:,} ({time.time()-ts:.0f}s)", flush=True)
    print(f"  time: {time.time()-ts:.0f}s")

    rng = np.random.default_rng(0xBEEF)

    # Far baseline using a63
    print(f"\n# Far baseline (Δa63 > 10M, random pairs)...")
    far_hw = sample_far_baseline(state1_all, snaps_all[('a', 63)], 10_000_000, 5000, rng)
    far_mean = float(np.mean(far_hw))
    print(f"  N_far = {len(far_hw)}, mean HW = {far_mean:.3f}")

    # Test configurations
    configs = [
        ('1ch: a63',                    [snaps_all[('a', 63)]]),
        ('2ch: a63 + e63',              [snaps_all[('a', 63)], snaps_all[('e', 63)]]),
        ('3ch: a63 + e63 + a62',        [snaps_all[('a', 63)], snaps_all[('e', 63)], snaps_all[('a', 62)]]),
        ('3ch: a63 + e63 + e62',        [snaps_all[('a', 63)], snaps_all[('e', 63)], snaps_all[('e', 62)]]),
        ('4ch: a63+e63+a62+e62',        [snaps_all[('a', 63)], snaps_all[('e', 63)],
                                         snaps_all[('a', 62)], snaps_all[('e', 62)]]),
        ('4ch wide: a60+e60+a63+e63',   [snaps_all[('a', 60)], snaps_all[('e', 60)],
                                         snaps_all[('a', 63)], snaps_all[('e', 63)]]),
    ]

    # Use different T per channel count (more channels need bigger T for sampling)
    # 1ch: T=10K, 2ch: T=50K, 3ch: T=500K, 4ch: T=5M
    T_by_nchannels = {1: 10_000, 2: 50_000, 3: 500_000, 4: 5_000_000}

    print(f"\n# Stacking tests:")
    print(f"{'config':<35} {'T':>10} {'N':>6} {'mean':>8} {'gap':>8}")
    results = {}
    for label, keys in configs:
        n = len(keys)
        T = T_by_nchannels[n]
        ts = time.time()
        close_hw = joint_close_via_buckets(keys, state1_all, T, max_pairs=3000)
        if not close_hw:
            print(f"  {label:<35} T={T:<8} FAILED"); continue
        mean_c = float(np.mean(close_hw))
        gap = mean_c - far_mean
        results[label] = {'T': T, 'n_close': len(close_hw), 'mean': mean_c, 'gap': gap}
        print(f"  {label:<35} {T:>10} {len(close_hw):>6} {mean_c:>8.3f} {gap:>+8.3f}  t={time.time()-ts:.0f}s",
              flush=True)

    print(f"\n=== ANALYSIS ===")
    best_lbl = min(results, key=lambda k: results[k]['gap'])
    best_gap = results[best_lbl]['gap']
    baseline = results['2ch: a63 + e63']['gap']
    improvement = best_gap - baseline

    print(f"2-channel baseline (a63+e63): gap = {baseline:+.3f}")
    print(f"Best multi-channel:  {best_lbl} = {best_gap:+.3f}")
    print(f"Additional gain:     {improvement:+.3f} bits")
    print(f"Effective birthday:  2^{128 + best_gap/2:.2f}")

    # Note: threshold differences make comparison subtle
    # The THEORETICAL max gap is the sum of all independent channels
    # But we're limited by bucketing at different T, so it's an apples-to-oranges comparison
    print(f"\nNote: T differs per n_channels. Compare same-T configs.")
    same_T_3ch = [r for lbl, r in results.items() if r['T'] == 500_000]
    if len(same_T_3ch) >= 2:
        print(f"\nSame-T (T=500K) 3-channel configs:")
        for lbl, r in results.items():
            if r['T'] == 500_000:
                print(f"  {lbl}: gap = {r['gap']:+.3f}")

    out = {'K': K, 'far_mean': far_mean, 'results': results,
           'best_config': best_lbl, 'best_gap': best_gap,
           'effective_birthday_exp': 128 + best_gap/2,
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
