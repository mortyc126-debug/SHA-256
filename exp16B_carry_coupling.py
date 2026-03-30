#!/usr/bin/env python3
"""
EXPERIMENT 16B: Carry Coupling Field

Not carry(M) or carry(M'), but the COUPLING between them.
Define: κ(M, M', r, i) = carry_i(M, r) ⊕ carry_i(M', r)
        (carry DIFFERENCE at position i, round r)

For Wang pairs at De=0 rounds: κ should be structured (synced carries).
Beyond the barrier: κ should randomize.

KEY QUESTION: Can we CONTROL κ past the barrier?
If κ stays structured past r=17, the carry coupling provides
a channel between M and M' that survives the barrier.
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def carry_vector(a, b, n=32):
    """Compute carry vector for a+b."""
    carries = []
    c = 0
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        s = ai + bi + c
        c = 1 if s >= 2 else 0
        carries.append(c)
    return carries


def carry_coupling_field(Wn, Wf, num_rounds=64):
    """
    Compute carry coupling field κ for the main addition (d+T1→e_new)
    across all rounds.

    κ[r][i] = carry_i(d_n + T1_n) ⊕ carry_i(d_f + T1_f)

    Returns: num_rounds × 32 binary matrix
    """
    states_n = sha256_rounds(Wn, num_rounds)
    states_f = sha256_rounds(Wf, num_rounds)
    Wn_exp = schedule(Wn)
    Wf_exp = schedule(Wf)

    kappa = np.zeros((num_rounds, 32), dtype=int)

    for r in range(num_rounds):
        an, bn, cn, dn, en, fn, gn, hn = states_n[r]
        af, bf, cf, df, ef, ff, gf, hf = states_f[r]

        T1n = (hn + sigma1(en) + ch(en, fn, gn) + K[r] + Wn_exp[r]) & MASK
        T1f = (hf + sigma1(ef) + ch(ef, ff, gf) + K[r] + Wf_exp[r]) & MASK

        cv_n = carry_vector(dn, T1n)
        cv_f = carry_vector(df, T1f)

        for i in range(32):
            kappa[r][i] = cv_n[i] ^ cv_f[i]

    return kappa


def test_coupling_profile(N=1500):
    """Measure carry coupling field profile across rounds."""
    print("\n--- TEST 1: CARRY COUPLING FIELD PROFILE ---")

    # Per-round statistics
    kappa_hw = {r: [] for r in range(64)}  # HW of κ per round
    kappa_persistence = []  # How many rounds does κ stay low?

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        kappa = carry_coupling_field(Wn, Wf)

        for r in range(64):
            kappa_hw[r].append(np.sum(kappa[r]))

        # Persistence: how many rounds is HW(κ) < 8?
        persist = 0
        for r in range(64):
            if np.sum(kappa[r]) < 8:
                persist += 1
            else:
                break
        kappa_persistence.append(persist)

    print(f"{'Round':>5} | {'E[HW(κ)]':>10} | {'Std':>8} | {'P(κ=0)':>8} | {'P(HW<8)':>8} | Signal")
    print("-" * 65)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,24,32,48,63]:
        arr = np.array(kappa_hw[r])
        p_zero = np.mean(arr == 0)
        p_low = np.mean(arr < 8)

        marker = ""
        if p_zero > 0.01:
            marker = f" κ=0:{p_zero:.3f}"
        if arr.mean() < 12:
            marker += " LOW"

        print(f"{r:>5} | {arr.mean():>10.4f} | {arr.std():>8.4f} | {p_zero:>8.4f} | "
              f"{p_low:>8.4f} | {marker}")

    pers = np.array(kappa_persistence)
    print(f"\nκ persistence (rounds with HW<8): mean={pers.mean():.2f}, max={pers.max()}")

    return kappa_hw


def test_coupling_autocorrelation(N=1000):
    """Does κ at round r predict κ at round r+k?"""
    print("\n--- TEST 2: COUPLING AUTOCORRELATION ---")

    all_kappas = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        kappa = carry_coupling_field(Wn, Wf)
        all_kappas.append(kappa)

    print(f"{'Lag':>4} | {'corr(HW_κ)':>12} | Signal")
    print("-" * 35)

    for lag in [1, 2, 3, 4, 5, 8, 16, 32]:
        corrs = []
        for kappa in all_kappas:
            hw_seq = [np.sum(kappa[r]) for r in range(64)]
            for r in range(64 - lag):
                corrs.append((hw_seq[r], hw_seq[r + lag]))

        x = np.array([c[0] for c in corrs])
        y = np.array([c[1] for c in corrs])
        c = np.corrcoef(x, y)[0, 1]
        marker = " ***" if abs(c) > 0.05 else ""
        print(f"{lag:>4} | {c:>12.6f} | {marker}")


def test_coupling_controls_output(N=2000):
    """Does carry coupling at intermediate rounds predict final δH?"""
    print("\n--- TEST 3: COUPLING → OUTPUT CORRELATION ---")

    data = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        kappa = carry_coupling_field(Wn, Wf)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dh = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        # Coupling metrics at various rounds
        kappa_17 = np.sum(kappa[16])  # Round 17 (0-indexed: 16)
        kappa_32 = np.sum(kappa[31])
        kappa_48 = np.sum(kappa[47])
        kappa_total = np.sum(kappa)

        data.append((dh, kappa_17, kappa_32, kappa_48, kappa_total))

    dh_arr = np.array([d[0] for d in data])
    k17 = np.array([d[1] for d in data])
    k32 = np.array([d[2] for d in data])
    k48 = np.array([d[3] for d in data])
    kt = np.array([d[4] for d in data])

    threshold = 3 / np.sqrt(N)

    for name, arr in [('κ_17', k17), ('κ_32', k32), ('κ_48', k48), ('κ_total', kt)]:
        c = np.corrcoef(dh_arr, arr)[0, 1]
        sig = " ***" if abs(c) > threshold else ""
        print(f"corr(δH, {name:>8}): {c:+.6f}{sig}")


def test_coupling_manipulation(N=2000):
    """
    Can we CHOOSE ΔW to control κ past the barrier?

    Strategy: Wang cascade gives DWs with De=0 for r=3..16.
    Perturb DWs to minimize κ at round 17-20.
    Measure if low κ correlates with low δH.
    """
    print("\n--- TEST 4: COUPLING MANIPULATION ---")

    baseline_k17 = []
    optimized_k17 = []
    baseline_dh = []
    optimized_dh = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        # Baseline κ
        kappa_base = carry_coupling_field(Wn, Wf, 20)
        k17_base = np.sum(kappa_base[16])
        baseline_k17.append(k17_base)

        H_n = sha256_compress(Wn)
        Wf_base = [(Wn[i] + DWs[i]) & MASK for i in range(16)]
        H_f = sha256_compress(Wf_base)
        dh_base = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        baseline_dh.append(dh_base)

        # Optimize: try 20 perturbations of DWs[15], pick lowest κ_17
        best_k17 = k17_base
        best_DWs = list(DWs)

        for _ in range(20):
            trial_DWs = list(DWs)
            trial_DWs[15] = random.randint(0, MASK)

            Wf_trial = [(Wn[i] + trial_DWs[i]) & MASK for i in range(16)]
            kappa_trial = carry_coupling_field(Wn, Wf_trial, 20)
            k17_trial = np.sum(kappa_trial[16])

            if k17_trial < best_k17:
                best_k17 = k17_trial
                best_DWs = trial_DWs

        optimized_k17.append(best_k17)

        Wf_opt = [(Wn[i] + best_DWs[i]) & MASK for i in range(16)]
        H_f_opt = sha256_compress(Wf_opt)
        dh_opt = sum(hw(H_n[i] ^ H_f_opt[i]) for i in range(8))
        optimized_dh.append(dh_opt)

    bl_k = np.array(baseline_k17)
    op_k = np.array(optimized_k17)
    bl_d = np.array(baseline_dh)
    op_d = np.array(optimized_dh)

    print(f"Baseline κ_17:  mean={bl_k.mean():.2f}")
    print(f"Optimized κ_17: mean={op_k.mean():.2f}")
    print(f"κ reduction: {bl_k.mean() - op_k.mean():.2f}")

    print(f"\nBaseline δH:  mean={bl_d.mean():.2f}")
    print(f"Optimized δH: mean={op_d.mean():.2f}")
    print(f"δH change: {op_d.mean() - bl_d.mean():+.2f}")

    if op_d.mean() < bl_d.mean() - 1:
        print("*** SIGNAL: Coupling manipulation reduces δH! ***")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 16B: CARRY COUPLING FIELD")
    print("Coupling between carry(M) and carry(M')")
    print("=" * 60)

    test_coupling_profile(1000)
    test_coupling_autocorrelation(500)
    test_coupling_controls_output(1500)
    test_coupling_manipulation(1000)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

if __name__ == "__main__":
    main()
