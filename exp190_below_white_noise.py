#!/usr/bin/env python3
"""
EXP 190: BELOW WHITE NOISE — The 62 hidden dimensions

"White noise" σ=4.0 in HW(δa)+HW(δe).
But HW collapses 64 bits → 1 number.
The "noise" = 62 dimensions we're not seeing.

KEY TEST: σ_measured vs σ_independent.
For independent random bits: σ(HW) = √(n·p·(1-p)) = √(32×0.25) = 2.83
If σ_measured > 2.83 → bits are CORRELATED → structure below white noise!
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_diff_vector(s1, s2):
    """64-bit diff vector: first 32 = δa bits, next 32 = δe bits."""
    vec = np.zeros(64, dtype=int)
    for b in range(32):
        vec[b] = ((s1[0] >> b) & 1) ^ ((s2[0] >> b) & 1)
        vec[32+b] = ((s1[4] >> b) & 1) ^ ((s2[4] >> b) & 1)
    return vec

def test_variance_inflation(N=300):
    """Is σ(HW) > σ_independent? → bits are correlated."""
    print(f"\n{'='*60}")
    print(f"VARIANCE INFLATION TEST")
    print(f"{'='*60}")

    # For independent bits: σ²(HW) = n×p×(1-p) = 32×0.25 = 8 → σ = 2.83
    sigma_independent = math.sqrt(32 * 0.25)

    da_vals = []; de_vals = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        for r in range(30, 64):
            da_vals.append(hw(s1[r][0] ^ s2[r][0]))
            de_vals.append(hw(s1[r][4] ^ s2[r][4]))

    da = np.array(da_vals); de = np.array(de_vals)

    print(f"\n  σ(δa): measured = {da.std():.4f}, independent = {sigma_independent:.4f}")
    print(f"  σ(δe): measured = {de.std():.4f}, independent = {sigma_independent:.4f}")
    print(f"  Variance inflation factor (VIF):")
    print(f"    δa: VIF = {(da.std()/sigma_independent)**2:.4f}")
    print(f"    δe: VIF = {(de.std()/sigma_independent)**2:.4f}")

    vif_a = (da.std()/sigma_independent)**2
    vif_e = (de.std()/sigma_independent)**2

    if vif_a > 1.1:
        print(f"\n  ★★★ VARIANCE INFLATED! δa bits are CORRELATED (VIF={vif_a:.2f})")
        print(f"  There's structure BELOW white noise!")
    else:
        print(f"  Bits are approximately independent")

    return vif_a, vif_e

def test_bit_pair_correlations(N=200):
    """Which bit PAIRS in δa are correlated?"""
    print(f"\n{'='*60}")
    print(f"BIT-PAIR CORRELATIONS WITHIN δa")
    print(f"{'='*60}")

    # Collect many δa vectors
    vectors = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        for r in range(30, 64):
            vec = np.zeros(32, dtype=int)
            diff = s1[r][0] ^ s2[r][0]
            for b in range(32):
                vec[b] = (diff >> b) & 1
            vectors.append(vec)

    V = np.array(vectors, dtype=float)

    # Correlation matrix
    C = np.corrcoef(V.T)  # 32×32

    # Remove diagonal (self-correlation = 1)
    np.fill_diagonal(C, 0)

    # Statistics
    upper = C[np.triu_indices(32, k=1)]
    print(f"\n  Pairwise bit correlations within δa:")
    print(f"    Mean |corr|: {np.mean(np.abs(upper)):.6f}")
    print(f"    Max |corr|: {np.max(np.abs(upper)):.6f}")
    print(f"    Expected (independent): ~{1/math.sqrt(len(vectors)):.6f}")

    threshold = 3 / math.sqrt(len(vectors))
    n_sig = np.sum(np.abs(upper) > threshold)
    n_total = len(upper)
    print(f"    Significant pairs (|c|>{threshold:.4f}): {n_sig}/{n_total}")
    print(f"    Expected false positives: {n_total * 0.003:.0f}")

    if n_sig > n_total * 0.003 * 3:
        print(f"    ★★★ EXCESS CORRELATIONS! Structure exists below white noise!")

    # Top correlated pairs
    pairs = []
    for i in range(32):
        for j in range(i+1, 32):
            pairs.append((abs(C[i,j]), C[i,j], i, j))
    pairs.sort(reverse=True)

    print(f"\n  TOP 10 correlated bit pairs:")
    for ac, c, i, j in pairs[:10]:
        # Are they adjacent? (carry-related)
        adj = "ADJACENT" if abs(i-j) == 1 else ""
        rot = ""
        if abs(i-j) in [2, 6, 11, 13, 22, 25]:
            rot = f"Σ-ROTATION({abs(i-j)})"
        print(f"    bit {i:>2} ↔ bit {j:>2}: corr={c:+.4f} {adj} {rot}")

    # ADJACENT-BIT correlations (carry chain signature)
    adj_corrs = [C[i, i+1] for i in range(31)]
    print(f"\n  ADJACENT-BIT correlations (carry chain):")
    print(f"    Mean: {np.mean(adj_corrs):+.6f}")
    print(f"    (Positive = carry creates positive correlation)")

    # Σ-ROTATION correlations (bits separated by rotation distance)
    for rot_dist in [2, 6, 11, 13, 22, 25]:
        rot_corrs = [C[i, (i+rot_dist)%32] for i in range(32)]
        avg = np.mean(rot_corrs)
        sig = " ★" if abs(avg) > 0.01 else ""
        print(f"    Σ-distance {rot_dist:>2}: mean corr = {avg:+.6f}{sig}")

def test_principal_components(N=200):
    """PCA on the 64-bit δ vector: how many REAL dimensions?"""
    print(f"\n{'='*60}")
    print(f"PCA ON FULL 64-BIT δ VECTOR")
    print(f"{'='*60}")

    vectors = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        for r in range(30, 64):
            vec = get_diff_vector(s1[r], s2[r])
            vectors.append(vec)

    V = np.array(vectors, dtype=float)
    V_centered = V - V.mean(axis=0)

    _, sigma, Vt = np.linalg.svd(V_centered[:min(len(V), 2000)], full_matrices=False)
    cumvar = np.cumsum(sigma**2) / np.sum(sigma**2)

    d90 = np.searchsorted(cumvar, 0.90) + 1
    d95 = np.searchsorted(cumvar, 0.95) + 1
    d99 = np.searchsorted(cumvar, 0.99) + 1

    print(f"\n  PCA on {len(vectors)} 64-bit δ vectors:")
    print(f"    dim(90%): {d90}/64")
    print(f"    dim(95%): {d95}/64")
    print(f"    dim(99%): {d99}/64")
    print(f"    σ₁/σ₆₄: {sigma[0]/sigma[min(63, len(sigma)-1)]:.2f}")

    if d95 < 60:
        print(f"    ★★★ EFFECTIVE DIMENSION < 64! ({d95} at 95%)")
        print(f"    → δ lives in a SUBSPACE of dimension {d95}")
        print(f"    → {64 - d95} dimensions are EMPTY (pure noise)")
    else:
        print(f"    Full 64 dimensions used (no dimensional reduction)")

    # Top singular values
    print(f"\n  Top singular values:")
    for i in [0, 1, 2, 3, 4, 9, 19, 31, 63]:
        if i < len(sigma):
            print(f"    σ_{i+1}: {sigma[i]:.3f}")

def test_diff_vector_prediction(N=150):
    """Can we predict the FULL 64-bit δ vector at round r+1?"""
    print(f"\n{'='*60}")
    print(f"FULL VECTOR PREDICTION: δ[r] → δ[r+1]")
    print(f"{'='*60}")

    # Collect pairs (δ[r], δ[r+1])
    X = []; Y = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        for r in range(30, 63):
            x = get_diff_vector(s1[r], s2[r])
            y = get_diff_vector(s1[r+1], s2[r+1])
            X.append(x); Y.append(y)

    X = np.array(X, dtype=float); Y = np.array(Y, dtype=float)

    # Per-output-bit: which input bits predict it?
    print(f"\n  Per-output-bit prediction (best single input bit):")

    best_corrs = []
    for out_bit in range(64):
        max_c = 0
        for in_bit in range(64):
            c = np.corrcoef(X[:, in_bit], Y[:, out_bit])[0, 1]
            if not np.isnan(c) and abs(c) > abs(max_c):
                max_c = c
        best_corrs.append(abs(max_c))

    bc = np.array(best_corrs)
    print(f"    Mean best |corr|: {bc.mean():.4f}")
    print(f"    Max best |corr|:  {bc.max():.4f}")
    print(f"    (Random baseline: ~{3/math.sqrt(len(X)):.4f})")

    n_predictable = np.sum(bc > 3/math.sqrt(len(X)))
    print(f"    Predictable bits (|corr| > 3σ): {n_predictable}/64")

    if n_predictable > 5:
        print(f"    ★★★ {n_predictable} BITS ARE PREDICTABLE from previous round!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 190: BELOW WHITE NOISE")
    print("The 62 dimensions we've been ignoring")
    print("=" * 60)

    vif_a, vif_e = test_variance_inflation(N=200)
    test_bit_pair_correlations(N=150)
    test_principal_components(N=150)
    test_diff_vector_prediction(N=100)

    print(f"\n{'='*60}")
    print(f"VERDICT: Is there structure below white noise?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
