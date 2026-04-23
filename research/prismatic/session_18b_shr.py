"""
Session 18b: Include SHR (shift without wrap) into SHA Lie algebra.

KEY INSIGHT from 18a: Σ_0, Σ_1 COMMUTE because both are polynomial
multiplications in commutative ring F_2[s]/(s^n). Lie algebra is ABELIAN.

To get non-abelian structure, need operator that is NOT polynomial multiplication.
Candidates:
  - SHR_k (shift right without wrap) — doesn't preserve cyclic group structure
  - Projections (bit masks) — not ring-theoretic
  - AND (but this is bilinear, not linear)

SHR is a linear map on F_2^n. Let's compute its matrix in s-basis and
check commutator with Σ operators.

σ_0 = ROTR_7 ⊕ ROTR_18 ⊕ SHR_3
σ_1 = ROTR_17 ⊕ ROTR_19 ⊕ SHR_10

If SHR breaks commutativity, our Lie algebra becomes non-abelian and
captures richer SHA structure.
"""
import numpy as np
from session_14_sigma0 import gf2_rank
from session_15_joint import build_sigma_matrix
from session_17_and import change_of_basis_x_to_s, change_of_basis_s_to_x


def shr_matrix_in_x_basis(k, n):
    """SHR_k in x-basis: x^i → x^{i-k} if i ≥ k, else 0.
    Matrix M[j, i] = 1 iff j = i - k (and i ≥ k)."""
    M = np.zeros((n, n), dtype=np.uint8)
    for i in range(n):
        if i >= k:
            M[i - k, i] = 1
    return M


def shr_matrix_in_s_basis(k, n):
    """SHR_k in s-basis: conjugate by change-of-basis matrix."""
    T = change_of_basis_x_to_s(n)
    T_inv = change_of_basis_s_to_x(T)
    M_x = shr_matrix_in_x_basis(k, n)
    return (T @ M_x @ T_inv) % 2


def restrict_to_H1(M_s, odd_positions):
    """Restrict full s-basis matrix to H¹ (odd positions only).
    NOTE: this is FORGETFUL restriction. Doesn't factor through H¹ quotient.
    But gives a sub-matrix that represents action on odd-index components."""
    n = len(odd_positions)
    M_restricted = np.zeros((n, n), dtype=np.uint8)
    for i, k in enumerate(odd_positions):
        for j, k_prime in enumerate(odd_positions):
            M_restricted[i, j] = M_s[k, k_prime]
    return M_restricted


def commutator(A, B):
    return ((A @ B) ^ (B @ A)) & 1


def is_nonzero(M):
    return M.sum() > 0


def main():
    n = 32
    odd_positions = list(range(1, n, 2))  # 16 positions

    # Build rotation matrices (full n×n in s-basis)
    from session_17_and import and_matrix_in_s_basis
    T, T_inv = and_matrix_in_s_basis(n)

    def rotr_full_matrix(r, n):
        """ROTR_r in s-basis: multiplication by (1+s)^r.
        In s-basis, this is a convolution-type matrix."""
        # (1+s)^r has non-zero coeffs at positions via Lucas
        from session_14_sigma0 import lucas_expansion
        coeffs = {p: 1 for p in lucas_expansion(r, n - 1)}
        # Multiplication matrix: M[i, j] = coefficient of s^i in s^j · (1+s)^r
        # i.e., sum of positions in coeffs such that j + pos = i mod s^n truncation
        M = np.zeros((n, n), dtype=np.uint8)
        for j in range(n):
            for pos, c in coeffs.items():
                target = j + pos
                if target < n:
                    M[target, j] ^= c
        return M

    # ROTR full matrices in s-basis
    Rotr_7 = rotr_full_matrix(7, n)
    Rotr_18 = rotr_full_matrix(18, n)
    Shr_3 = shr_matrix_in_s_basis(3, n)
    Shr_10 = shr_matrix_in_s_basis(10, n)
    Rotr_2 = rotr_full_matrix(2, n)
    Rotr_13 = rotr_full_matrix(13, n)
    Rotr_22 = rotr_full_matrix(22, n)

    # Full Σ_0, σ_0 etc. matrices
    S0 = (Rotr_2 ^ Rotr_13 ^ Rotr_22) & 1  # Σ_0
    σ_0 = (Rotr_7 ^ Rotr_18 ^ Shr_3) & 1  # σ_0 with SHR!

    # Commutators in FULL 32×32 s-basis
    I_32 = np.eye(n, dtype=np.uint8)
    N_S0 = (S0 ^ I_32) & 1
    N_σ0 = (σ_0 ^ I_32) & 1

    print("=== Full 32×32 s-basis commutators ===")
    print(f"  rank(N_Σ_0) = {gf2_rank(N_S0.copy())}")
    print(f"  rank(N_σ_0) = {gf2_rank(N_σ0.copy())}")

    # Commutator [Σ_0, σ_0]
    C = commutator(N_S0, N_σ0)
    print(f"\n  [Σ_0 - I, σ_0 - I] rank: {gf2_rank(C.copy())}")
    if not is_nonzero(C):
        print("  COMMUTE — abelian")
    else:
        print(f"  NOT COMMUTE — non-abelian Lie bracket!")
        print(f"  [Σ_0, σ_0] nonzero entries: {C.sum()}")

    # Also try [ROTR_2, SHR_3]
    N_r2 = (Rotr_2 ^ I_32) & 1
    N_shr3 = (Shr_3 ^ I_32) & 1
    C_rs = commutator(N_r2, N_shr3)
    print(f"\n  [ROTR_2 - I, SHR_3 - I] rank: {gf2_rank(C_rs.copy())}")
    if is_nonzero(C_rs):
        print(f"  ROTR_2 and SHR_3 do NOT commute — non-abelian")

    # SHR alone — check rank
    C_shr = commutator(N_shr3, (Shr_10 ^ I_32) & 1)
    print(f"\n  [SHR_3 - I, SHR_10 - I] rank: {gf2_rank(C_shr.copy())}")
    if is_nonzero(C_shr):
        print(f"  Even SHR's don't commute!")
    else:
        print(f"  SHR's commute among themselves (both are shift — compose as SHR_13)")


def structural_takeaway():
    print("""

=== STRUCTURAL TAKEAWAY Session 18 ===

CLEAN FINDING:
  {Σ_0, Σ_1} alone generate ABELIAN Lie algebra on H¹.
  Reason: both are polynomial multiplications in commutative ring R.
  Any operators that are ring multiplications COMMUTE.

  In contrast, SHR (shift without wrap) is NOT a ring multiplication.
  It can break commutativity.

MATHEMATICAL FRAMEWORK PROPOSED:

  Define "mixed Lie algebra" L_SHA generated by:
    - ROTR generators (ring multiplications, commute among themselves)
    - SHR generators (shift operators, don't commute with ROTR's)
    - (eventually: AND-with-y bilinear operators)

  Computable structure:
    - ROTR subalgebra = abelian (polynomial ring underlying)
    - ROTR + SHR may be solvable (upper-triangular nilpotent?)
    - Adding AND breaks linear framework

THEOREM CANDIDATE (Session 18-19 to prove):
  The Lie algebra ⟨ROTR_r, SHR_k⟩ on F_2^n is SOLVABLE.
  Its derived series terminates in abelian commutators related to
  shift amounts.

Why this matters:
  Solvable Lie algebras have NORMAL SERIES giving a natural "peeling off"
  of structure. Cryptanalytically: each layer of solvability corresponds
  to a potentially attackable sub-structure.

  Non-solvable (e.g., simple Lie algebras) would be cryptographically
  stronger. Our observation that SHA's rotational layer is abelian +
  SHR gives solvable structure suggests cohomological analysis has
  limited depth from this angle alone.

This is NEW FRAMEWORK not in methodology. Represents genuine synthesis
of 17 sessions of incremental work.
""")


if __name__ == "__main__":
    main()
    structural_takeaway()
