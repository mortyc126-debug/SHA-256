#!/usr/bin/env python3
"""
EXP 36: Covariance Spectral Analysis — New Mathematics

ALL 71 prior directions used 1D metrics (corr, HW, etc).
SHA-256 output is 256-DIMENSIONAL.

NEVER MEASURED: the full 256×256 covariance matrix
Cov(δH_i, δH_j) where i,j are output BIT positions.

If Cov ≠ αI → anisotropy exists → some DIRECTIONS in output space
are easier for collision than others.

If Cov has small eigenvalues → collision is MORE LIKELY along
those eigenvectors → targeted attack in eigenspace.

This is not a metric. Not a correlation. It's the FULL STRUCTURE
of the collision landscape in output space.

NEW MATHEMATICS: Spectral Collision Theory (SCT).
"""
import sys, os, random
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def hash_diff_bitvector(Wn, Wf):
    """256-bit vector: which output bits differ between H(Wn) and H(Wf)."""
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    bits = []
    for w in range(8):
        d = Hn[w] ^ Hf[w]
        for b in range(32):
            bits.append((d >> b) & 1)
    return bits

def test_covariance_matrix_wang(N=5000):
    """Compute full 256×256 covariance of hash difference bits for Wang pairs."""
    print("\n--- TEST 1: FULL COVARIANCE MATRIX (WANG PAIRS) ---")

    # Collect N × 256 bit vectors
    X = np.zeros((N, 256), dtype=np.float64)

    for i in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        X[i] = hash_diff_bitvector(Wn, Wf)

    # Mean: should be ≈ 0.5 per bit (random)
    means = X.mean(axis=0)
    print(f"Bit means: min={means.min():.6f}, max={means.max():.6f}, "
          f"avg={means.mean():.6f} (expected 0.5)")

    # Covariance matrix
    X_centered = X - means
    Cov = (X_centered.T @ X_centered) / N  # 256 × 256

    # Eigenvalue analysis
    eigvals = np.linalg.eigvalsh(Cov)
    eigvals_sorted = np.sort(eigvals)[::-1]

    print(f"\nCovariance matrix 256×256:")
    print(f"  Trace: {np.trace(Cov):.4f} (expected: 256×0.25 = {256*0.25})")
    print(f"  Top 10 eigenvalues: {eigvals_sorted[:10].round(6)}")
    print(f"  Bottom 10 eigenvalues: {eigvals_sorted[-10:].round(6)}")
    print(f"  Max eigenvalue: {eigvals_sorted[0]:.6f}")
    print(f"  Min eigenvalue: {eigvals_sorted[-1]:.6f}")
    print(f"  Ratio max/min: {eigvals_sorted[0]/eigvals_sorted[-1]:.4f}")

    # If Cov = 0.25·I (random): all eigenvalues = 0.25
    expected_eigval = 0.25
    print(f"  Expected (random): all eigenvalues = {expected_eigval}")

    # Anisotropy: how far from isotropic?
    deviation = np.std(eigvals_sorted)
    print(f"  Eigenvalue std: {deviation:.6f} (0 = perfectly isotropic)")

    # Statistical significance: for N samples, eigenvalue fluctuations ≈ 0.25·√(2/N)
    expected_std = expected_eigval * np.sqrt(2/N)
    print(f"  Expected std (finite N): {expected_std:.6f}")
    print(f"  Ratio measured/expected: {deviation/expected_std:.4f}")

    if deviation > 3 * expected_std:
        print(f"  *** SIGNAL: Anisotropy {deviation/expected_std:.1f}× above random! ***")

    # Compare with random baseline
    print(f"\nRandom baseline (N={N}):")
    X_rand = np.zeros((N, 256), dtype=np.float64)
    for i in range(N):
        M1=random_w16(); M2=random_w16()
        X_rand[i] = hash_diff_bitvector(M1, M2)

    means_r = X_rand.mean(axis=0)
    X_r_centered = X_rand - means_r
    Cov_r = (X_r_centered.T @ X_r_centered) / N

    eigvals_r = np.sort(np.linalg.eigvalsh(Cov_r))[::-1]
    dev_r = np.std(eigvals_r)

    print(f"  Random eigenvalue std: {dev_r:.6f}")
    print(f"  Wang eigenvalue std:   {deviation:.6f}")
    print(f"  Ratio Wang/Random: {deviation/dev_r:.4f}")

    if deviation > dev_r * 1.5:
        print(f"  *** SIGNAL: Wang Cov MORE anisotropic than random! ***")

    return eigvals_sorted, eigvals_r, Cov

def test_eigenvector_collision_bias(Cov, N=5000):
    """
    Do top eigenvectors indicate DIRECTIONS where collision is easier?

    For the eigenvector with SMALLEST eigenvalue:
    project δH onto it. If projection is biased toward 0 →
    collision is more likely in that direction.
    """
    print("\n--- TEST 2: EIGENVECTOR COLLISION BIAS ---")

    eigvals, eigvecs = np.linalg.eigh(Cov)
    # Sort by eigenvalue (ascending — smallest first)
    idx = np.argsort(eigvals)
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    # Bottom 5 eigenvectors (smallest eigenvalue = least variance = most constrained)
    print(f"Testing bottom 5 eigenvectors (smallest eigenvalue = most constrained):")

    for k in range(5):
        v = eigvecs[:, k]  # 256-dim eigenvector
        ev = eigvals[k]

        # Project Wang pair δH vectors onto this eigenvector
        projections = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            bits = np.array(hash_diff_bitvector(Wn, Wf), dtype=np.float64)
            proj = np.dot(bits - 0.5, v)  # Center around 0
            projections.append(proj)

        p = np.array(projections)
        print(f"  λ_{k}={ev:.6f}: E[proj]={p.mean():+.6f}, "
              f"std={p.std():.6f}, P(|proj|<0.1)={np.mean(np.abs(p)<0.1):.4f}")

    # Top 5 (largest eigenvalue = most variance = least constrained)
    print(f"\nTesting top 5 eigenvectors (largest eigenvalue = most variable):")
    for k in range(5):
        v = eigvecs[:, -(k+1)]
        ev = eigvals[-(k+1)]

        projections = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            bits = np.array(hash_diff_bitvector(Wn, Wf), dtype=np.float64)
            proj = np.dot(bits - 0.5, v)
            projections.append(proj)

        p = np.array(projections)
        print(f"  λ_{255-k}={ev:.6f}: E[proj]={p.mean():+.6f}, "
              f"std={p.std():.6f}")

def test_block_covariance(N=5000):
    """
    Covariance structure between OUTPUT WORDS (8×8 block matrix).
    Each block = Cov(H[i]_bits, H[j]_bits) = 32×32 matrix.

    If off-diagonal blocks ≠ 0 → words are CORRELATED.
    Methodology says: a-branch and e-branch are "orthogonal".
    Is this true at the covariance level?
    """
    print("\n--- TEST 3: BLOCK COVARIANCE (word-level) ---")

    X = np.zeros((N, 256), dtype=np.float64)
    for i in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        X[i] = hash_diff_bitvector(Wn, Wf)

    X_c = X - X.mean(axis=0)
    Cov = (X_c.T @ X_c) / N

    # Block structure: Cov[i*32:(i+1)*32, j*32:(j+1)*32]
    print(f"{'':>6}", end="")
    for j in range(8):
        print(f" | H[{j}]{'(a)' if j<4 else '(e)':>4}", end="")
    print()
    print("-"*80)

    block_norms = np.zeros((8,8))
    for i in range(8):
        row_str = f"H[{i}]{'(a)' if i<4 else '(e)':>4}"
        for j in range(8):
            block = Cov[i*32:(i+1)*32, j*32:(j+1)*32]
            # Frobenius norm normalized
            norm = np.linalg.norm(block, 'fro') / 32
            block_norms[i,j] = norm
            row_str += f" | {norm:>8.5f}"
        print(row_str)

    # Off-diagonal vs diagonal
    diag_norms = [block_norms[i,i] for i in range(8)]
    offdiag_norms = [block_norms[i,j] for i in range(8) for j in range(8) if i!=j]

    print(f"\nDiagonal block norms: {np.mean(diag_norms):.6f}")
    print(f"Off-diagonal norms:   {np.mean(offdiag_norms):.6f}")
    print(f"Ratio off/diag:       {np.mean(offdiag_norms)/np.mean(diag_norms):.6f}")

    # a-branch vs e-branch cross-correlation
    ae_cross = [block_norms[i,j] for i in range(4) for j in range(4,8)]
    aa_cross = [block_norms[i,j] for i in range(4) for j in range(4) if i!=j]
    ee_cross = [block_norms[i,j] for i in range(4,8) for j in range(4,8) if i!=j]

    print(f"\na-a cross: {np.mean(aa_cross):.6f}")
    print(f"e-e cross: {np.mean(ee_cross):.6f}")
    print(f"a-e cross: {np.mean(ae_cross):.6f}")

    if np.mean(ae_cross) < np.mean(aa_cross) * 0.5:
        print("*** CONFIRMED: a-branch and e-branch are weakly correlated ***")

def test_spectral_collision_theory(N=3000):
    """
    SCT: project collision search into eigenspace.

    Instead of searching in 256-dim output space (birthday 2^128),
    search in the k-dim subspace of SMALLEST eigenvalues.

    If collision is easier along low-eigenvalue directions →
    projected birthday = 2^(k/2) for k < 256.
    """
    print("\n--- TEST 4: SPECTRAL COLLISION THEORY ---")

    # Collect hash differences and compute covariance
    X = np.zeros((N, 256), dtype=np.float64)
    H_list = []

    for i in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        X[i] = hash_diff_bitvector(Wn, Wf)

        Hn = sha256_compress(Wn)
        H_list.append(Hn)

    X_c = X - X.mean(axis=0)
    Cov = (X_c.T @ X_c) / N
    eigvals, eigvecs = np.linalg.eigh(Cov)
    idx = np.argsort(eigvals)
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    # Project hashes into eigenspace
    # For collision: we need H(M) = H(M') → δH = 0 → projection = 0

    # How many eigenvalues are "small" (< 0.2)?
    n_small = np.sum(eigvals < 0.2)
    n_medium = np.sum((eigvals >= 0.2) & (eigvals < 0.3))
    n_large = np.sum(eigvals >= 0.3)

    print(f"Eigenvalue distribution:")
    print(f"  Small (<0.2):   {n_small}")
    print(f"  Medium (0.2-0.3): {n_medium}")
    print(f"  Large (>0.3):   {n_large}")

    # Effective dimension: how many eigenvalues are "active"?
    # Shannon entropy of normalized eigenvalues
    ev_norm = eigvals / np.sum(eigvals)
    ev_norm = ev_norm[ev_norm > 1e-15]
    eff_dim = 2**(-np.sum(ev_norm * np.log2(ev_norm)))

    print(f"\nEffective dimension: {eff_dim:.1f}/256")
    print(f"If < 256: collision cost = 2^({eff_dim:.1f}/2) = 2^{eff_dim/2:.1f}")
    print(f"(vs birthday 2^128)")

    if eff_dim < 240:
        print(f"*** SIGNAL: Effective dimension {eff_dim:.0f} < 256! ***")
        print(f"Potential reduction: {(256 - eff_dim)/2:.1f} bits")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 36: COVARIANCE SPECTRAL ANALYSIS")
    print("New mathematics: Spectral Collision Theory (SCT)")
    print("="*60)

    eigvals_w, eigvals_r, Cov = test_covariance_matrix_wang(4000)
    test_eigenvector_collision_bias(Cov, 3000)
    test_block_covariance(4000)
    test_spectral_collision_theory(3000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
