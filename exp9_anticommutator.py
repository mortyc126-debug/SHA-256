#!/usr/bin/env python3
"""
EXPERIMENT 9: Anti-Commutator {Ψ, Σ₀} Structure

Proven: [Ψ, Σ₀] is MAXIMAL (commutator).
NOT tested: {Ψ, Σ₀} = ΨΣ₀ + Σ₀Ψ (anti-commutator).

If {Ψ, Σ₀} has eigenstructure, its eigenvectors are "resonant"
directions where carry and rotation don't fully mix.

Ψ = carry operator (lower-triangular, nilpotent)
Σ₀ = Sigma0 rotation operator (circulant)

We work over GF(2)^32 (bit-level) and over Z/2^32 (word-level).
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# OPERATOR CONSTRUCTION
# ============================================================

def sigma0_matrix_gf2():
    """Construct 32×32 GF(2) matrix for Σ0(x) = ROTR²(x) ⊕ ROTR¹³(x) ⊕ ROTR²²(x)."""
    M = np.zeros((32, 32), dtype=np.int64)
    for i in range(32):
        # ROTR²: bit i comes from bit (i+2)%32
        M[i][(i + 2) % 32] ^= 1
        # ROTR¹³: bit i comes from bit (i+13)%32
        M[i][(i + 13) % 32] ^= 1
        # ROTR²²: bit i comes from bit (i+22)%32
        M[i][(i + 22) % 32] ^= 1
    return M

def sigma1_matrix_gf2():
    """Construct 32×32 GF(2) matrix for Σ1(x) = ROTR⁶(x) ⊕ ROTR¹¹(x) ⊕ ROTR²⁵(x)."""
    M = np.zeros((32, 32), dtype=np.int64)
    for i in range(32):
        M[i][(i + 6) % 32] ^= 1
        M[i][(i + 11) % 32] ^= 1
        M[i][(i + 25) % 32] ^= 1
    return M

def carry_jacobian_at(a, b, n=32):
    """
    Compute Jacobian of carry operator C(a,b) with respect to a at point (a,b).
    J[i][j] = ∂c_i/∂a_j over GF(2).
    Lower-triangular (carry propagates upward).
    """
    J = np.zeros((n, n), dtype=np.int64)

    # Compute carry vector
    c = [0] * (n + 1)
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        c[i + 1] = 1 if (ai + bi + c[i]) >= 2 else 0

    # ∂c_{i+1}/∂a_j: only j ≤ i matters (lower triangular)
    # Flip a_j and see how carries change
    for j in range(n):
        a_flipped = a ^ (1 << j)
        c_new = [0] * (n + 1)
        for i in range(n):
            ai = (a_flipped >> i) & 1
            bi = (b >> i) & 1
            c_new[i + 1] = 1 if (ai + bi + c_new[i]) >= 2 else 0

        for i in range(n):
            J[i][j] = (c[i + 1] ^ c_new[i + 1])

    return J

def anti_commutator_gf2(Psi, Sigma):
    """Compute {Ψ, Σ} = ΨΣ + ΣΨ over GF(2)."""
    return (Psi @ Sigma + Sigma @ Psi) % 2

def commutator_gf2(Psi, Sigma):
    """Compute [Ψ, Σ] = ΨΣ - ΣΨ = ΨΣ + ΣΨ over GF(2) (same as anti-comm in char 2!)."""
    return (Psi @ Sigma + Sigma @ Psi) % 2

def matrix_rank_gf2_np(M):
    """Rank over GF(2) using numpy."""
    A = M.copy() % 2
    m, n = A.shape
    rank = 0
    for col in range(n):
        pivot = -1
        for row in range(rank, m):
            if A[row, col] % 2 == 1:
                pivot = row
                break
        if pivot == -1:
            continue
        A[[rank, pivot]] = A[[pivot, rank]]
        for row in range(m):
            if row != rank and A[row, col] % 2 == 1:
                A[row] = (A[row] + A[rank]) % 2
        rank += 1
    return rank

def test_anticommutator_structure(N=1000):
    """
    Compute {Ψ, Σ₀} for many random (a,b) pairs and analyze its structure.

    Key insight: over GF(2), [A,B] = {A,B} (same thing!).
    But over Z/2^32 they differ because of carries in matrix multiplication.
    So we work over REAL numbers (or Z) to see the TRUE anti-commutator.
    """
    print("\n--- TEST 1: ANTI-COMMUTATOR STRUCTURE ---")

    Sigma0 = sigma0_matrix_gf2()
    Sigma1 = sigma1_matrix_gf2()

    print(f"Σ₀ GF(2) rank: {matrix_rank_gf2_np(Sigma0)}")
    print(f"Σ₁ GF(2) rank: {matrix_rank_gf2_np(Sigma1)}")

    # Over GF(2): [Ψ,Σ] = {Ψ,Σ} always (char 2)
    # So we need to work over REALS to distinguish them

    # Sample carry Jacobians and compute anti-commutator over R
    anticomm_ranks = []
    anticomm_eigenvalues = []
    comm_ranks = []

    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)

        Psi = carry_jacobian_at(a, b).astype(np.float64)
        Sig0 = Sigma0.astype(np.float64)

        # Real-valued anti-commutator and commutator
        AC = Psi @ Sig0 + Sig0 @ Psi  # {Ψ, Σ₀}
        CM = Psi @ Sig0 - Sig0 @ Psi  # [Ψ, Σ₀]

        ac_rank = np.linalg.matrix_rank(AC)
        cm_rank = np.linalg.matrix_rank(CM)

        anticomm_ranks.append(ac_rank)
        comm_ranks.append(cm_rank)

        # Eigenvalues of anti-commutator
        eigvals = np.linalg.eigvals(AC)
        anticomm_eigenvalues.append(eigvals)

    ac_ranks = np.array(anticomm_ranks)
    cm_ranks = np.array(comm_ranks)

    print(f"\nAnti-commutator rank: mean={ac_ranks.mean():.2f}, min={ac_ranks.min()}, max={ac_ranks.max()}")
    print(f"Commutator rank:      mean={cm_ranks.mean():.2f}, min={cm_ranks.min()}, max={cm_ranks.max()}")
    print(f"Rank difference:      {ac_ranks.mean() - cm_ranks.mean():+.2f}")

    if ac_ranks.mean() < cm_ranks.mean() - 1:
        print("*** SIGNAL: Anti-commutator has LOWER rank than commutator! ***")
        print("Eigenvectors of {Ψ,Σ₀} span a SMALLER subspace → resonant directions exist!")

    # Eigenvalue analysis
    all_eigvals = np.concatenate(anticomm_eigenvalues)
    real_parts = np.real(all_eigvals)

    print(f"\nEigenvalue distribution of {{Ψ, Σ₀}}:")
    print(f"  Real part: mean={real_parts.mean():.4f}, std={real_parts.std():.4f}")
    print(f"  P(|λ| < 0.01): {np.mean(np.abs(all_eigvals) < 0.01):.4f}")
    print(f"  P(|λ| > 1.0):  {np.mean(np.abs(all_eigvals) > 1.0):.4f}")

    # Spectral gap
    avg_eigvals = np.mean([np.sort(np.abs(ev))[::-1] for ev in anticomm_eigenvalues], axis=0)
    print(f"  Top 5 avg |λ|: {avg_eigvals[:5]}")
    print(f"  Bottom 5 avg |λ|: {avg_eigvals[-5:]}")

    spectral_gap = avg_eigvals[0] - avg_eigvals[1] if len(avg_eigvals) > 1 else 0
    print(f"  Spectral gap (λ₁-λ₂): {spectral_gap:.4f}")

    return ac_ranks, cm_ranks, avg_eigvals

def test_resonant_directions(N=500):
    """
    Find eigenvectors of {Ψ, Σ₀} with large eigenvalues.
    These are "resonant directions" where carry and rotation interact coherently.
    Test if these directions create exploitable differential paths.
    """
    print("\n--- TEST 2: RESONANT DIRECTION EXPLOITATION ---")

    # Collect top eigenvectors
    top_eigvecs = []

    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)

        Psi = carry_jacobian_at(a, b).astype(np.float64)
        Sig0 = Sigma0.astype(np.float64)
        AC = Psi @ Sig0 + Sig0 @ Psi

        eigvals, eigvecs = np.linalg.eig(AC)

        # Top eigenvector (by absolute eigenvalue)
        idx = np.argmax(np.abs(eigvals))
        top_eigvecs.append(np.real(eigvecs[:, idx]))

    # Average top eigenvector direction
    avg_top = np.mean(top_eigvecs, axis=0)
    avg_top = avg_top / np.linalg.norm(avg_top) if np.linalg.norm(avg_top) > 0 else avg_top

    print(f"Average top eigenvector (resonant direction):")
    print(f"  Norm: {np.linalg.norm(avg_top):.4f}")

    # Which bits does this direction emphasize?
    top_bits = np.argsort(np.abs(avg_top))[::-1][:10]
    print(f"  Top 10 active bits: {list(top_bits)}")
    print(f"  Their weights: {[f'{avg_top[b]:.3f}' for b in top_bits]}")

    # Test: does inputting differential along resonant direction give better results?
    # Convert eigenvector to 32-bit differential
    resonant_diff = 0
    for i in range(32):
        if abs(avg_top[i]) > 0.15:  # Threshold
            resonant_diff |= (1 << i)

    print(f"\n  Resonant differential: 0x{resonant_diff:08x} (HW={hw(resonant_diff)})")

    # Compare: resonant diff vs random diff vs single-bit diff
    hw_results = {'resonant': [], 'random': [], 'single': []}

    for _ in range(2000):
        W16 = random_w16()

        for label, dw in [
            ('resonant', resonant_diff),
            ('random', random.randint(1, MASK)),
            ('single', 1 << random.randint(0, 31)),
        ]:
            W16_f = list(W16)
            W16_f[0] = (W16_f[0] ^ dw) & MASK

            H_n = sha256_compress(W16)
            H_f = sha256_compress(W16_f)

            delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
            hw_delta = sum(hw(d) for d in delta_H)
            hw_results[label].append(hw_delta)

    for label in ['resonant', 'random', 'single']:
        arr = np.array(hw_results[label])
        print(f"  {label:>10}: E[HW(δH)]={arr.mean():.2f}, std={arr.std():.2f}, min={arr.min()}")

    resonant_mean = np.mean(hw_results['resonant'])
    random_mean = np.mean(hw_results['random'])

    if resonant_mean < random_mean - 1:
        print("*** SIGNAL: Resonant direction produces smaller δH! ***")

Sigma0 = sigma0_matrix_gf2()

def test_sigma_pair_interaction(N=500):
    """
    Test interaction between Σ₀ and Σ₁ through carry.
    SHA-256 uses both: Σ₀ in T2 (a-branch), Σ₁ in T1 (e-branch).
    The a-e interaction through carry might have resonances.
    """
    print("\n--- TEST 3: Σ₀-Σ₁ CARRY RESONANCE ---")

    Sig0 = sigma0_matrix_gf2().astype(np.float64)
    Sig1 = sigma1_matrix_gf2().astype(np.float64)

    # Pure rotation anti-commutator (no carry)
    AC_pure = Sig0 @ Sig1 + Sig1 @ Sig0
    pure_rank = np.linalg.matrix_rank(AC_pure)
    pure_eigvals = np.sort(np.abs(np.linalg.eigvals(AC_pure)))[::-1]

    print(f"Pure {'{'}Σ₀, Σ₁{'}'}: rank={pure_rank}, top eigenvalues={pure_eigvals[:5]}")

    # With carry
    ac_with_carry_ranks = []

    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)
        c_val = random.randint(0, MASK)

        Psi_ab = carry_jacobian_at(a, b).astype(np.float64)
        Psi_ac = carry_jacobian_at(a, c_val).astype(np.float64)

        # {Σ₀·Ψ_ab, Σ₁·Ψ_ac} — interaction of both sigma through carries
        M1 = Sig0 @ Psi_ab
        M2 = Sig1 @ Psi_ac
        AC = M1 @ M2 + M2 @ M1

        ac_with_carry_ranks.append(np.linalg.matrix_rank(AC))

    avg_rank = np.mean(ac_with_carry_ranks)
    print(f"With carry {'{'}Σ₀Ψ, Σ₁Ψ{'}'}: avg rank={avg_rank:.2f}")
    print(f"Rank reduction from carry: {pure_rank - avg_rank:+.2f}")

    if avg_rank < pure_rank * 0.8:
        print("*** SIGNAL: Carry reduces Σ₀-Σ₁ interaction rank! ***")
        print("This means fewer independent constraints → potentially exploitable.")

def test_nullspace_exploitation(N=500):
    """
    Find the nullspace of {Ψ, Σ₀}.
    Vectors in ker({Ψ,Σ₀}) are directions where carry and rotation CANCEL.
    These might represent free parameters for the attacker.
    """
    print("\n--- TEST 4: NULLSPACE OF ANTI-COMMUTATOR ---")

    nullspace_dims = []

    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)

        Psi = carry_jacobian_at(a, b).astype(np.float64)
        Sig0 = Sigma0.astype(np.float64)
        AC = Psi @ Sig0 + Sig0 @ Psi

        # Nullspace dimension = 32 - rank
        rank = np.linalg.matrix_rank(AC, tol=1e-10)
        nullspace_dims.append(32 - rank)

    ns = np.array(nullspace_dims)
    print(f"Nullspace dimension: mean={ns.mean():.2f}, min={ns.min()}, max={ns.max()}")
    print(f"Distribution:")
    for dim in sorted(set(nullspace_dims)):
        count = sum(1 for d in nullspace_dims if d == dim)
        print(f"  dim={dim}: {count}/{N} ({count/N*100:.1f}%)")

    if ns.mean() > 5:
        print(f"*** SIGNAL: Average nullspace dimension {ns.mean():.0f} > 5! ***")
        print("Attacker has ~{ns.mean():.0f} free directions per round where carry and rotation cancel.")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 9: ANTI-COMMUTATOR {Ψ, Σ₀} STRUCTURE")
    print("=" * 70)

    ac_ranks, cm_ranks, avg_eigvals = test_anticommutator_structure(500)
    test_resonant_directions(300)
    test_sigma_pair_interaction(300)
    test_nullspace_exploitation(500)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Anti-commutator avg rank: {ac_ranks.mean():.2f}/32")
    print(f"Commutator avg rank: {cm_ranks.mean():.2f}/32")
    print(f"Spectral gap: {avg_eigvals[0] - avg_eigvals[1]:.4f}")

if __name__ == "__main__":
    main()
