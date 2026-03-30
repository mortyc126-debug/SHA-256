#!/usr/bin/env python3
"""
EXPERIMENT 15: Synchronized GKP Pairs

OUR METHOD combines: Wang cascade + Carry Algebra + Phase Transition.

Wang cascade: De3..De16=0 → e-branch IDENTICAL for M and M'.
This means: GKP patterns of e-branch additions are SYNCHRONIZED.

Key questions:
1. How synchronized are GKP patterns in Wang pairs? (measure)
2. Does synchronization predict De17? (correlation)
3. Can we find pairs where sync EXTENDS past round 16? (search)
4. What is the DIFFERENTIAL GKP: how do GKP(M) and GKP(M') relate
   through the differential ΔW?
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def gkp_overlap(state_n, state_f, W_n_r, W_f_r, K_r):
    """
    Measure GKP overlap between normal and faulty computations
    for all 7 additions in one round.

    Returns: dict with per-addition overlap metrics.
    """
    an, bn, cn, dn, en, fn, gn, hn = state_n
    af, bf, cf, df, ef, ff, gf, hf = state_f

    # Compute all intermediate values for both
    sig1_en = sigma1(en); sig1_ef = sigma1(ef)
    ch_n = ch(en, fn, gn); ch_f = ch(ef, ff, gf)
    sig0_an = sigma0(an); sig0_af = sigma0(af)
    maj_n = maj(an, bn, cn); maj_f = maj(af, bf, cf)

    s1n = (hn + sig1_en) & MASK; s1f = (hf + sig1_ef) & MASK
    s2n = (s1n + ch_n) & MASK; s2f = (s1f + ch_f) & MASK
    s3n = (s2n + K_r) & MASK; s3f = (s2f + K_r) & MASK
    T1n = (s3n + W_n_r) & MASK; T1f = (s3f + W_f_r) & MASK
    T2n = (sig0_an + maj_n) & MASK; T2f = (sig0_af + maj_f) & MASK

    additions_n = [
        (hn, sig1_en), (s1n, ch_n), (s2n, K_r), (s3n, W_n_r),
        (sig0_an, maj_n), (T1n, T2n), (dn, T1n),
    ]
    additions_f = [
        (hf, sig1_ef), (s1f, ch_f), (s2f, K_r), (s3f, W_f_r),
        (sig0_af, maj_f), (T1f, T2f), (df, T1f),
    ]
    labels = ['h+Σ1(e)', 's1+Ch', 's2+K', 's3+W', 'Σ0+Maj', 'T1+T2', 'd+T1']

    overlaps = {}
    for i, (label, (xn, yn), (xf, yf)) in enumerate(
            zip(labels, additions_n, additions_f)):
        gkp_n = carry_gkp_classification(xn, yn)
        gkp_f = carry_gkp_classification(xf, yf)

        # Overlap: fraction of positions with same GKP class
        same = sum(1 for a, b in zip(gkp_n, gkp_f) if a == b)
        overlaps[label] = same / 32

    return overlaps


def test_wang_sync_profile(N=2000):
    """Measure GKP synchronization profile across rounds for Wang pairs."""
    print("\n--- TEST 1: WANG PAIR GKP SYNCHRONIZATION PROFILE ---")

    # Per-round, per-addition overlap
    round_overlaps = {r: {label: [] for label in
        ['h+Σ1(e)', 's1+Ch', 's2+K', 's3+W', 'Σ0+Maj', 'T1+T2', 'd+T1']}
        for r in range(65)}

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        Wn_exp = schedule(Wn)
        Wf_exp = schedule(Wf)

        for r in range(64):
            ov = gkp_overlap(states_n[r], states_f[r],
                             Wn_exp[r], Wf_exp[r], K[r])
            for label, val in ov.items():
                round_overlaps[r][label].append(val)

    # Print summary: average overlap per round for key additions
    print(f"{'Round':>5} | {'h+Σ1(e)':>9} | {'s1+Ch':>9} | {'d+T1':>9} | "
          f"{'Σ0+Maj':>9} | {'T1+T2':>9} | {'Mean':>9}")
    print("-" * 70)

    key_labels = ['h+Σ1(e)', 's1+Ch', 'd+T1', 'Σ0+Maj', 'T1+T2']
    sync_data = {}

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,24,32,48,63]:
        vals = {}
        for label in key_labels:
            vals[label] = np.mean(round_overlaps[r][label])

        mean_all = np.mean(list(vals.values()))
        sync_data[r] = mean_all

        marker = ""
        if mean_all > 0.6:
            marker = " <<<SYNC"
        elif mean_all > 0.4:
            marker = " <partial"

        print(f"{r:>5} | {vals['h+Σ1(e)']:>9.4f} | {vals['s1+Ch']:>9.4f} | "
              f"{vals['d+T1']:>9.4f} | {vals['Σ0+Maj']:>9.4f} | "
              f"{vals['T1+T2']:>9.4f} | {mean_all:>9.4f}{marker}")

    # Find where sync drops
    for r in range(1, 64):
        if r in sync_data and r-1 in sync_data:
            if sync_data[r-1] > 0.5 and sync_data[r] < 0.5:
                print(f"\n*** SYNC DROP at round {r}: {sync_data[r-1]:.4f} → {sync_data[r]:.4f} ***")

    return round_overlaps


def test_sync_predicts_barrier(N=3000):
    """Does GKP synchronization at round 16 predict De17 magnitude?"""
    print("\n--- TEST 2: SYNC AT ROUND 16 → De17 PREDICTION ---")

    data = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        Wn_exp = schedule(Wn)
        Wf_exp = schedule(Wf)

        # Sync at rounds 15, 16 (near barrier)
        ov_15 = gkp_overlap(states_n[15], states_f[15],
                            Wn_exp[15], Wf_exp[15], K[15])
        ov_16 = gkp_overlap(states_n[16], states_f[16],
                            Wn_exp[16], Wf_exp[16], K[16])

        mean_sync_16 = np.mean(list(ov_16.values()))
        dT1_sync = ov_16.get('d+T1', 0)

        # De17
        De17 = de(states_n, states_f, 17)
        hw17 = hw(De17)

        # Final δH
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        hw_delta = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        data.append({
            'mean_sync_16': mean_sync_16,
            'dT1_sync': dT1_sync,
            'hw17': hw17,
            'hw_delta': hw_delta,
        })

    sync_arr = np.array([d['mean_sync_16'] for d in data])
    dt1_arr = np.array([d['dT1_sync'] for d in data])
    hw17_arr = np.array([d['hw17'] for d in data])
    hw_delta_arr = np.array([d['hw_delta'] for d in data])

    corr_sync_hw17 = np.corrcoef(sync_arr, hw17_arr)[0, 1]
    corr_dt1_hw17 = np.corrcoef(dt1_arr, hw17_arr)[0, 1]
    corr_sync_delta = np.corrcoef(sync_arr, hw_delta_arr)[0, 1]

    threshold = 3 / np.sqrt(N)

    print(f"corr(mean_sync_16, HW(De17)):  {corr_sync_hw17:+.6f} {'***' if abs(corr_sync_hw17) > threshold else ''}")
    print(f"corr(d+T1_sync, HW(De17)):     {corr_dt1_hw17:+.6f} {'***' if abs(corr_dt1_hw17) > threshold else ''}")
    print(f"corr(mean_sync_16, HW(δH)):    {corr_sync_delta:+.6f} {'***' if abs(corr_sync_delta) > threshold else ''}")
    print(f"Threshold: {threshold:.6f}")

    # Split by sync quality
    high_sync = hw17_arr[sync_arr > np.median(sync_arr)]
    low_sync = hw17_arr[sync_arr <= np.median(sync_arr)]

    print(f"\nHigh sync at r=16: E[HW(De17)]={high_sync.mean():.4f}")
    print(f"Low sync at r=16:  E[HW(De17)]={low_sync.mean():.4f}")
    print(f"Difference: {high_sync.mean() - low_sync.mean():+.4f}")

    return data


def test_differential_gkp(N=2000):
    """
    OUR NEW CONCEPT: Differential GKP.

    For an addition x+y in M and x'+y' in M' where x'=x+δx, y'=y+δy:
    Define DGKP[i] = how GKP class changes from (x,y) to (x',y').

    DGKP transitions: GG, GK, GP, KG, KK, KP, PG, PK, PP
    PP transitions are where BOTH have uncertain carry → maximum sync.
    GG/KK are where both are determined → also synced.
    GP/PG/KP/PK are DESYNC transitions → carry diverges.

    If we can maximize PP+GG+KK and minimize cross-transitions →
    the differential propagates through synchronized carry.
    """
    print("\n--- TEST 3: DIFFERENTIAL GKP ANALYSIS ---")

    # Count DGKP transitions across all rounds
    transition_counts = {r: {} for r in range(64)}

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        Wn_exp = schedule(Wn)
        Wf_exp = schedule(Wf)

        for r in range(64):
            an, bn, cn, dn, en, fn, gn, hn = states_n[r]
            af, bf, cf, df, ef, ff, gf, hf = states_f[r]

            # Main addition: d + T1 → e_new
            T1n = (hn + sigma1(en) + ch(en, fn, gn) + K[r] + Wn_exp[r]) & MASK
            T1f = (hf + sigma1(ef) + ch(ef, ff, gf) + K[r] + Wf_exp[r]) & MASK

            gkp_n = carry_gkp_classification(dn, T1n)
            gkp_f = carry_gkp_classification(df, T1f)

            counts = {}
            for cn_class, cf_class in zip(gkp_n, gkp_f):
                key = cn_class + cf_class
                counts[key] = counts.get(key, 0) + 1

            for key, val in counts.items():
                transition_counts[r][key] = transition_counts[r].get(key, 0) + val

    # Analyze transition patterns
    print(f"{'Round':>5} | {'PP':>6} | {'GG':>6} | {'KK':>6} | {'SYNC%':>7} | "
          f"{'PK+KP':>7} | {'PG+GP':>7} | {'DESYNC%':>8}")
    print("-" * 75)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,32,48,63]:
        tc = transition_counts[r]
        total = sum(tc.values())

        pp = tc.get('PP', 0) / total
        gg = tc.get('GG', 0) / total
        kk = tc.get('KK', 0) / total
        sync_pct = (pp + gg + kk) * 100

        pk = (tc.get('PK', 0) + tc.get('KP', 0)) / total
        pg = (tc.get('PG', 0) + tc.get('GP', 0)) / total
        desync_pct = (pk + pg) * 100

        # GK transitions (carry flip)
        gk = (tc.get('GK', 0) + tc.get('KG', 0)) / total

        marker = ""
        if sync_pct > 60:
            marker = " <<<SYNC"
        elif desync_pct < 30:
            marker = " <low_desync"

        print(f"{r:>5} | {pp:>6.3f} | {gg:>6.3f} | {kk:>6.3f} | {sync_pct:>6.1f}% | "
              f"{pk:>7.3f} | {pg:>7.3f} | {desync_pct:>7.1f}%{marker}")


def test_sync_extension_search(N=5000):
    """
    Search for Wang pairs where GKP sync extends PAST round 16.

    Normal: sync drops at r=17 (barrier).
    Goal: find pairs where d+T1 overlap at r=17 is high.
    """
    print("\n--- TEST 4: SYNC EXTENSION SEARCH ---")

    r17_overlaps = []
    r17_dT1_overlaps = []
    best_overlap = 0
    best_pair = None

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)
        Wn_exp = schedule(Wn)
        Wf_exp = schedule(Wf)

        ov_17 = gkp_overlap(states_n[17], states_f[17],
                            Wn_exp[17], Wf_exp[17], K[17])

        mean_ov = np.mean(list(ov_17.values()))
        dt1_ov = ov_17.get('d+T1', 0)

        r17_overlaps.append(mean_ov)
        r17_dT1_overlaps.append(dt1_ov)

        if mean_ov > best_overlap:
            best_overlap = mean_ov
            best_pair = (W0, W1, ov_17)

    arr = np.array(r17_overlaps)
    dt1_arr = np.array(r17_dT1_overlaps)

    print(f"Round 17 mean overlap: {arr.mean():.4f} ± {arr.std():.4f}")
    print(f"Round 17 d+T1 overlap: {dt1_arr.mean():.4f} ± {dt1_arr.std():.4f}")
    print(f"Max overlap: {arr.max():.4f}")
    print(f"Expected (random): ~0.375 (25%GG + 25%KK + 50%·50%PP ≈ 37.5%)")

    if best_pair:
        W0, W1, ov = best_pair
        print(f"\nBest sync pair: W0=0x{W0:08x}, W1=0x{W1:08x}")
        print(f"  Overlap detail: {ov}")

    # Distribution
    print(f"\nOverlap distribution at round 17:")
    for thresh in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
        count = np.sum(arr > thresh)
        print(f"  >{thresh:.2f}: {count}/{N} ({count/N*100:.2f}%)")


def test_forced_sync_differential(N=3000):
    """
    Instead of Wang ΔW (which optimizes De=0), try to find ΔW
    that optimizes GKP SYNCHRONIZATION at round 17.

    Trade De=0 for GKP sync: relax some earlier constraints to
    gain sync at the barrier.
    """
    print("\n--- TEST 5: FORCED SYNC DIFFERENTIAL ---")

    # Approach: Wang cascade normally, but then perturb ΔW[14] or ΔW[15]
    # to improve sync at round 17, even if it breaks De16=0 slightly

    baseline_hw17 = []
    perturbed_hw17 = []
    perturbed_sync = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf_base, DWs_base, states_n_base, states_f_base = wang_cascade(W0, W1)

        De17_base = de(states_n_base, states_f_base, 17)
        baseline_hw17.append(hw(De17_base))

        # Try small perturbations to DW[15]
        best_sync = 0
        best_hw17 = hw(De17_base)

        for _ in range(20):
            DWs_trial = list(DWs_base)
            # Perturb last free word
            DWs_trial[15] = (DWs_trial[15] + random.randint(-255, 255)) & MASK

            Wf_trial = [(Wn[i] + DWs_trial[i]) & MASK for i in range(16)]
            states_n = sha256_rounds(Wn, 18)
            states_f = sha256_rounds(Wf_trial, 18)

            Wn_exp = schedule(Wn)
            Wf_exp = schedule(Wf_trial)

            # Measure sync at round 17
            ov = gkp_overlap(states_n[17], states_f[17],
                             Wn_exp[17], Wf_exp[17], K[17])
            sync = np.mean(list(ov.values()))

            De17 = de(states_n, states_f, 17)
            hw17 = hw(De17)

            if sync > best_sync:
                best_sync = sync
                best_hw17 = hw17

        perturbed_sync.append(best_sync)
        perturbed_hw17.append(best_hw17)

    bl = np.array(baseline_hw17)
    pt = np.array(perturbed_hw17)
    ps = np.array(perturbed_sync)

    print(f"Baseline E[HW(De17)]:  {bl.mean():.4f}")
    print(f"Perturbed E[HW(De17)]: {pt.mean():.4f}")
    print(f"Difference: {pt.mean() - bl.mean():+.4f}")
    print(f"Perturbed sync at r17: {ps.mean():.4f}")

    corr = np.corrcoef(ps, pt)[0, 1]
    print(f"corr(sync_17, HW(De17)): {corr:+.6f}")

    if pt.mean() < bl.mean() - 0.5:
        print("*** SIGNAL: Sync-optimized differential reduces barrier! ***")


def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 15: SYNCHRONIZED GKP PAIRS")
    print("Wang cascade + Carry Algebra = sync analysis")
    print("=" * 70)

    test_wang_sync_profile(1500)
    test_sync_predicts_barrier(2000)
    test_differential_gkp(1500)
    test_sync_extension_search(3000)
    test_forced_sync_differential(1000)

    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

if __name__ == "__main__":
    main()
