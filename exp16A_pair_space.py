#!/usr/bin/env python3
"""
EXPERIMENT 16A: Pair Space Geometry

(M, M') is ONE point in 1024-bit space (not two points in 512-bit space).
Collision submanifold V = {(M,M') : H(M) = H(M'), M ≠ M'}.

NOLLOCAL: V is defined by ALL 64 rounds simultaneously.
We study the geometry of V by sampling near-collision pairs
and measuring the structure of the 1024-dim space around them.

Key questions:
1. What is the effective dimension of near-collision set?
2. Is there a preferred DIRECTION in pair-space toward collision?
3. Does the pair-space metric differ from product metric?
4. Can we detect V's "shadow" from finite-distance observations?
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def pair_hash_distance(W1, W2):
    """Hash distance between two messages."""
    H1 = sha256_compress(W1)
    H2 = sha256_compress(W2)
    return sum(hw(H1[i] ^ H2[i]) for i in range(8))


def pair_to_vector(W1, W2):
    """Convert (M, M') pair to compact representation: (M, ΔM)."""
    delta = [(W2[i] - W1[i]) & MASK for i in range(16)]
    return delta


def test_pair_space_dimension(N=2000):
    """
    Measure effective dimension of near-collision pairs in pair-space.
    Generate Wang pairs (best near-collisions available).
    Compute PCA of the pair vectors to find effective dim.
    """
    print("\n--- TEST 1: EFFECTIVE DIMENSION OF PAIR SPACE ---")

    # Collect Wang pair differentials (ΔW vectors)
    delta_vectors = []
    hw_deltas = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # ΔW as a bit vector (512 bits)
        bits = []
        for w in range(16):
            dw = DWs[w]
            for b in range(32):
                bits.append((dw >> b) & 1)
        delta_vectors.append(bits)

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dh = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        hw_deltas.append(dh)

    X = np.array(delta_vectors, dtype=np.float64)
    hw_arr = np.array(hw_deltas)

    # PCA via SVD
    X_centered = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)

    # Effective dimension
    total_var = np.sum(S**2)
    cumvar = np.cumsum(S**2) / total_var

    d90 = np.searchsorted(cumvar, 0.90) + 1
    d95 = np.searchsorted(cumvar, 0.95) + 1
    d99 = np.searchsorted(cumvar, 0.99) + 1

    # Shannon effective dimension
    p = S**2 / total_var
    p = p[p > 1e-15]
    eff_dim = 2**(-np.sum(p * np.log2(p)))

    print(f"Wang ΔW vectors: {X.shape}")
    print(f"Top 10 singular values: {S[:10].round(2)}")
    print(f"Dim for 90% variance: {d90}/512")
    print(f"Dim for 95% variance: {d95}/512")
    print(f"Dim for 99% variance: {d99}/512")
    print(f"Shannon effective dim: {eff_dim:.1f}/512")

    if d90 < 400:
        print(f"*** SIGNAL: Pair space has reduced dimension {d90}! ***")

    # Does principal direction correlate with δH?
    pc1_scores = X_centered @ Vt[0]
    corr = np.corrcoef(pc1_scores, hw_arr)[0, 1]
    print(f"\ncorr(PC1, δH): {corr:+.6f}")

    # Top 5 PC correlations
    for i in range(5):
        pc_scores = X_centered @ Vt[i]
        c = np.corrcoef(pc_scores, hw_arr)[0, 1]
        print(f"  corr(PC{i+1}, δH): {c:+.6f}")

    return S, Vt, hw_arr


def test_gradient_toward_collision(N=2000):
    """
    In pair-space, is there a GRADIENT toward collision?

    For each Wang pair, perturb ΔW slightly and measure if δH changes
    systematically. A gradient means: pair-space has a preferred direction.
    """
    print("\n--- TEST 2: GRADIENT IN PAIR SPACE ---")

    # For each pair, try 32 perturbations and measure δH change
    gradient_exists = 0
    gradient_magnitudes = []

    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dh_base = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        # Perturb DWs[15] (last free word) by single bits
        improvements = 0
        best_improvement = 0

        for bit in range(32):
            DWs_pert = list(DWs)
            DWs_pert[15] ^= (1 << bit)

            Wf_pert = [(Wn[i] + DWs_pert[i]) & MASK for i in range(16)]
            H_f_pert = sha256_compress(Wf_pert)
            dh_pert = sum(hw(H_n[i] ^ H_f_pert[i]) for i in range(8))

            if dh_pert < dh_base:
                improvements += 1
                best_improvement = max(best_improvement, dh_base - dh_pert)

        if improvements > 0:
            gradient_exists += 1
            gradient_magnitudes.append(best_improvement)

    p_gradient = gradient_exists / N
    print(f"Pairs with improving perturbation: {gradient_exists}/{N} ({p_gradient*100:.1f}%)")
    print(f"Expected (random): ~50% (each flip equally likely to improve/worsen)")

    if gradient_magnitudes:
        print(f"Best improvement magnitude: mean={np.mean(gradient_magnitudes):.2f}, "
              f"max={max(gradient_magnitudes)}")

    # Multi-step gradient descent in pair-space
    print(f"\nGradient descent in pair-space (10 best runs):")
    best_runs = []

    for trial in range(min(N, 200)):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        current_DWs = list(DWs)
        H_n = sha256_compress(Wn)

        Wf_curr = [(Wn[i] + current_DWs[i]) & MASK for i in range(16)]
        dh_curr = sum(hw(H_n[i] ^ sha256_compress(Wf_curr)[i]) for i in range(8))
        dh_start = dh_curr

        for step in range(100):
            # Try random bit flip in DWs[8..15] (upper free words)
            word = random.randint(8, 15)
            bit = random.randint(0, 31)

            trial_DWs = list(current_DWs)
            trial_DWs[word] ^= (1 << bit)

            Wf_trial = [(Wn[i] + trial_DWs[i]) & MASK for i in range(16)]
            H_f_trial = sha256_compress(Wf_trial)
            dh_trial = sum(hw(H_n[i] ^ H_f_trial[i]) for i in range(8))

            if dh_trial < dh_curr:
                dh_curr = dh_trial
                current_DWs = trial_DWs

        best_runs.append((dh_start, dh_curr, dh_start - dh_curr))

    best_runs.sort(key=lambda x: x[2], reverse=True)
    for start, end, gain in best_runs[:10]:
        print(f"  {start} → {end} (gain={gain})")

    avg_gain = np.mean([g for _, _, g in best_runs])
    print(f"\nAverage gain from gradient descent: {avg_gain:.2f}")


def test_pair_metric_structure(N=1000):
    """
    Test: is the pair-space metric a PRODUCT metric (d_pair = d_M + d_M'),
    or does it have cross-terms?

    Cross-terms would mean: changing M and M' simultaneously
    can be better/worse than changing them independently.
    """
    print("\n--- TEST 3: PAIR METRIC CROSS-TERMS ---")

    cross_terms = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        Wf_base = [(Wn[i] + DWs[i]) & MASK for i in range(16)]
        H_f = sha256_compress(Wf_base)
        dh_base = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        # Perturbation A: change only M (Wn[15])
        bit_a = random.randint(0, 31)
        Wn_a = list(Wn); Wn_a[15] ^= (1 << bit_a)
        H_na = sha256_compress(Wn_a)
        Wf_a = [(Wn_a[i] + DWs[i]) & MASK for i in range(16)]
        H_fa = sha256_compress(Wf_a)
        dh_a = sum(hw(H_na[i] ^ H_fa[i]) for i in range(8))

        # Perturbation B: change only DW (DWs[15])
        bit_b = random.randint(0, 31)
        DWs_b = list(DWs); DWs_b[15] ^= (1 << bit_b)
        Wf_b = [(Wn[i] + DWs_b[i]) & MASK for i in range(16)]
        H_fb = sha256_compress(Wf_b)
        dh_b = sum(hw(H_n[i] ^ H_fb[i]) for i in range(8))

        # Perturbation A+B: change both
        Wf_ab = [(Wn_a[i] + DWs_b[i]) & MASK for i in range(16)]
        H_fab = sha256_compress(Wf_ab)
        dh_ab = sum(hw(H_na[i] ^ H_fab[i]) for i in range(8))

        # Cross-term: dh_ab - dh_a - dh_b + dh_base
        # If metric is product: cross_term ≈ 0
        cross = dh_ab - dh_a - dh_b + dh_base
        cross_terms.append(cross)

    ct = np.array(cross_terms)
    print(f"Cross-term: mean={ct.mean():.4f}, std={ct.std():.4f}")
    print(f"If product metric: mean ≈ 0, std ≈ small")
    print(f"|mean|/std = {abs(ct.mean())/ct.std():.4f}")

    if abs(ct.mean()) > 3 * ct.std() / np.sqrt(N):
        print("*** SIGNAL: Pair metric has systematic cross-terms! ***")
        print("This means M and M' changes INTERACT → pair-space is NOT a product.")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 16A: PAIR SPACE GEOMETRY")
    print("(M,M') as ONE point in 1024-bit space")
    print("=" * 60)

    S, Vt, hw_arr = test_pair_space_dimension(1500)
    test_gradient_toward_collision(1000)
    test_pair_metric_structure(1500)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

if __name__ == "__main__":
    main()
