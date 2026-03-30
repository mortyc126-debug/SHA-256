#!/usr/bin/env python3
"""
EXPERIMENT 16C: Transcendent Metric

All 50 methods used LINEAR or POLYNOMIAL metrics.
SHA-256 is nonlinear + non-polynomial at 64 rounds.

Define TRANSCENDENT distance:
  d_T(M, M') = exp(-HW(H(M) ⊕ H(M')) / T)

At temperature T:
  T → 0:  only exact collisions visible (δ-function)
  T → ∞:  all pairs equivalent (flat)
  T = T*:  critical temperature where structure is maximally visible

Also define partition function:
  Z(T) = Σ_{M'} exp(-HW(H(M) ⊕ H(M')) / T)

If Z(T) has a PHASE TRANSITION at some T* → the energy landscape
has exploitable structure at that scale.

This is statistical mechanics of hash functions — genuinely new.
"""

import sys, os, random, math
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def test_energy_landscape(N=5000):
    """
    Measure the "energy" distribution E = HW(H(M) ⊕ H(M'))
    for Wang pairs and random pairs.
    """
    print("\n--- TEST 1: ENERGY LANDSCAPE ---")

    wang_energies = []
    random_energies = []

    for _ in range(N):
        # Wang pair
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        E_wang = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        wang_energies.append(E_wang)

        # Random pair
        Wr1 = random_w16()
        Wr2 = random_w16()
        Hr1 = sha256_compress(Wr1)
        Hr2 = sha256_compress(Wr2)
        E_rand = sum(hw(Hr1[i] ^ Hr2[i]) for i in range(8))
        random_energies.append(E_rand)

    we = np.array(wang_energies)
    re = np.array(random_energies)

    print(f"Wang pairs:   E mean={we.mean():.2f}, std={we.std():.2f}, min={we.min()}, max={we.max()}")
    print(f"Random pairs: E mean={re.mean():.2f}, std={re.std():.2f}, min={re.min()}, max={re.max()}")

    # Energy distribution comparison
    wang_hist = Counter(wang_energies)
    rand_hist = Counter(random_energies)

    print(f"\nEnergy distribution tails:")
    for E_thresh in [80, 90, 100, 110, 120]:
        p_wang = np.mean(we <= E_thresh)
        p_rand = np.mean(re <= E_thresh)
        ratio = p_wang / p_rand if p_rand > 0 else float('inf')
        marker = " ***" if ratio > 2 else ""
        print(f"  P(E≤{E_thresh}): Wang={p_wang:.6f}, Random={p_rand:.6f}, ratio={ratio:.3f}{marker}")

    return we, re


def test_partition_function(N=3000):
    """
    Compute partition function Z(T) and its derivatives.
    Phase transition = singularity in d²Z/dT² (specific heat).
    """
    print("\n--- TEST 2: PARTITION FUNCTION Z(T) ---")

    # Collect energies from Wang pairs
    energies = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        E = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        energies.append(E)

    E_arr = np.array(energies, dtype=np.float64)

    # Z(T) = <exp(-E/T)>
    T_values = np.logspace(-1, 3, 50)

    print(f"{'T':>10} | {'Z(T)':>12} | {'<E>/T':>10} | {'C_v':>10} | Signal")
    print("-" * 55)

    Z_values = []
    E_mean_values = []
    Cv_values = []

    for T in T_values:
        boltzmann = np.exp(-E_arr / T)
        Z = np.mean(boltzmann)
        Z_values.append(Z)

        # <E> = -T² d(ln Z)/dT ≈ <E·exp(-E/T)> / Z
        E_mean = np.mean(E_arr * boltzmann) / Z
        E_mean_values.append(E_mean)

        # C_v = (<E²> - <E>²) / T²
        E2_mean = np.mean(E_arr**2 * boltzmann) / Z
        Cv = (E2_mean - E_mean**2) / T**2
        Cv_values.append(Cv)

    # Find peak in C_v (phase transition)
    Cv_arr = np.array(Cv_values)
    T_arr = np.array(T_values)

    peak_idx = np.argmax(Cv_arr)
    T_critical = T_arr[peak_idx]
    Cv_peak = Cv_arr[peak_idx]

    for i in [0, 5, 10, 15, 20, peak_idx, 30, 35, 40, 45, 49]:
        if i < len(T_values):
            marker = " *** PEAK" if i == peak_idx else ""
            print(f"{T_values[i]:>10.4f} | {Z_values[i]:>12.6f} | "
                  f"{E_mean_values[i]:>10.4f} | {Cv_values[i]:>10.4f} | {marker}")

    print(f"\nCritical temperature T* = {T_critical:.4f}")
    print(f"Specific heat peak C_v* = {Cv_peak:.4f}")

    # Compare with random baseline
    random_energies = []
    for _ in range(N):
        Wr1 = random_w16()
        Wr2 = random_w16()
        Hr1 = sha256_compress(Wr1)
        Hr2 = sha256_compress(Wr2)
        E = sum(hw(Hr1[i] ^ Hr2[i]) for i in range(8))
        random_energies.append(E)

    Er = np.array(random_energies, dtype=np.float64)

    Cv_rand = []
    for T in T_values:
        boltz = np.exp(-Er / T)
        Z = np.mean(boltz)
        Em = np.mean(Er * boltz) / Z
        E2m = np.mean(Er**2 * boltz) / Z
        Cv_rand.append((E2m - Em**2) / T**2)

    Cv_rand_arr = np.array(Cv_rand)
    rand_peak_idx = np.argmax(Cv_rand_arr)

    print(f"\nRandom: T* = {T_arr[rand_peak_idx]:.4f}, C_v* = {Cv_rand_arr[rand_peak_idx]:.4f}")
    print(f"Wang:   T* = {T_critical:.4f}, C_v* = {Cv_peak:.4f}")

    ratio = Cv_peak / Cv_rand_arr[rand_peak_idx] if Cv_rand_arr[rand_peak_idx] > 0 else 0
    print(f"C_v ratio Wang/Random: {ratio:.4f}")

    if abs(T_critical - T_arr[rand_peak_idx]) > T_critical * 0.1:
        print("*** SIGNAL: Phase transition at DIFFERENT temperature! ***")

    return T_critical, Cv_peak


def test_free_energy_landscape(N=2000):
    """
    Free energy F(T) = -T·ln(Z(T)).
    At T=T*, the free energy has special structure.

    Compute F for different message CLASSES:
    - Wang pairs (structured differential)
    - Random pairs (baseline)
    - Near-collision pairs (low-energy tail)
    """
    print("\n--- TEST 3: FREE ENERGY BY MESSAGE CLASS ---")

    # Collect energies for each class
    classes = {
        'wang': [],
        'random': [],
        'wang_best': [],  # Wang pairs with lowest E
    }

    all_wang = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        E = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        classes['wang'].append(E)
        all_wang.append((E, W0, W1))

        Wr = random_w16()
        Hr = sha256_compress(Wr)
        E_r = sum(hw(H_n[i] ^ Hr[i]) for i in range(8))
        classes['random'].append(E_r)

    # Best Wang pairs (lowest energy)
    all_wang.sort()
    for E, W0, W1 in all_wang[:N//10]:
        classes['wang_best'].append(E)

    T_values = [1, 5, 10, 20, 50, 100, 200]

    print(f"{'T':>6} | {'F(wang)':>10} | {'F(random)':>10} | {'F(best)':>10} | {'ΔF':>8}")
    print("-" * 55)

    for T in T_values:
        F_values = {}
        for cls_name, cls_E in classes.items():
            E_arr = np.array(cls_E, dtype=np.float64)
            boltz = np.exp(-E_arr / T)
            Z = np.mean(boltz)
            F = -T * np.log(Z) if Z > 0 else float('inf')
            F_values[cls_name] = F

        delta_F = F_values['wang'] - F_values['random']
        print(f"{T:>6} | {F_values['wang']:>10.4f} | {F_values['random']:>10.4f} | "
              f"{F_values.get('wang_best', 0):>10.4f} | {delta_F:>+8.4f}")


def test_simulated_annealing_collision(N=200):
    """
    Use the transcendent metric for simulated annealing toward collision.

    Start at high T (explore freely), cool down to T=0 (collision).
    The energy landscape's structure determines if SA can find collision.
    """
    print("\n--- TEST 4: SIMULATED ANNEALING WITH TRANSCENDENT METRIC ---")

    best_overall = 256
    results = []

    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        current_DWs = list(DWs)

        Wf_curr = [(Wn[i] + current_DWs[i]) & MASK for i in range(16)]
        H_f = sha256_compress(Wf_curr)
        E_curr = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        E_best = E_curr

        # Annealing schedule
        for step in range(200):
            T = 50.0 * (1 - step / 200)  # Linear cooling
            T = max(T, 0.1)

            # Propose: flip random bit in DWs
            word = random.randint(0, 15)
            bit = random.randint(0, 31)
            trial_DWs = list(current_DWs)
            trial_DWs[word] ^= (1 << bit)

            Wf_trial = [(Wn[i] + trial_DWs[i]) & MASK for i in range(16)]
            H_trial = sha256_compress(Wf_trial)
            E_trial = sum(hw(H_n[i] ^ H_trial[i]) for i in range(8))

            # Metropolis criterion
            dE = E_trial - E_curr
            if dE < 0 or random.random() < math.exp(-dE / T):
                E_curr = E_trial
                current_DWs = trial_DWs

                if E_curr < E_best:
                    E_best = E_curr

        results.append(E_best)
        best_overall = min(best_overall, E_best)

    results_arr = np.array(results)
    print(f"SA results: mean E_best={results_arr.mean():.2f}, min={results_arr.min()}")
    print(f"Baseline (no SA): ~128")
    print(f"Improvement: {128 - results_arr.mean():.2f} bits on average")

    # Compare with pure random search (same budget: 200 evaluations per trial)
    random_results = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        H_n = sha256_compress(Wn)

        best_E = 256
        for _ in range(200):
            trial_DWs = list(DWs)
            trial_DWs[random.randint(0, 15)] ^= (1 << random.randint(0, 31))
            Wf_trial = [(Wn[i] + trial_DWs[i]) & MASK for i in range(16)]
            H_trial = sha256_compress(Wf_trial)
            E = sum(hw(H_n[i] ^ H_trial[i]) for i in range(8))
            best_E = min(best_E, E)
        random_results.append(best_E)

    rr = np.array(random_results)
    print(f"\nRandom search: mean E_best={rr.mean():.2f}, min={rr.min()}")
    print(f"SA advantage: {rr.mean() - results_arr.mean():.2f} bits")

    if results_arr.mean() < rr.mean() - 2:
        print("*** SIGNAL: SA with transcendent metric outperforms random! ***")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 16C: TRANSCENDENT METRIC")
    print("Statistical mechanics of hash functions")
    print("=" * 60)

    we, re = test_energy_landscape(3000)
    T_crit, Cv_peak = test_partition_function(2000)
    test_free_energy_landscape(1500)
    test_simulated_annealing_collision(200)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print(f"Critical temperature: T* = {T_crit:.4f}")

if __name__ == "__main__":
    main()
