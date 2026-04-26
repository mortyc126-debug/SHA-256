"""
Session 15: Joint invariants of Σ_0 and Σ_1 on H¹(F_2[s]/(s^32)).

SHA-256 uses:
  Σ_0 = ROTR_2 ⊕ ROTR_13 ⊕ ROTR_22
  Σ_1 = ROTR_6 ⊕ ROTR_11 ⊕ ROTR_25

Both are unipotent on H¹ (Session 14). We compute:
  1. Σ_1 matrix structure
  2. Kernel(Σ_0 - I) = fixed points of Σ_0
  3. Kernel(Σ_1 - I) = fixed points of Σ_1
  4. Joint kernel = common fixed points of BOTH

Joint invariants = classes invariant under BOTH Σ operators.
If non-trivial, potentially exploitable as structural handle.
"""

import numpy as np
from session_14_sigma0 import (
    lucas_expansion, build_sigma_0_matrix_on_H1, gf2_rank, compute_kernel
)


def sigma_polynomial_even_shifts(rotation_list, n=32):
    """Given list of ROTR amounts [r1, r2, r3], compute Σ = XOR of (1+s)^r
    and return only even-shift positions (relevant for H¹ action)."""
    combined = set()
    for r in rotation_list:
        for p in lucas_expansion(r, n - 1):
            combined.symmetric_difference_update([p])

    all_positions = sorted(combined)
    even_shifts = [p for p in all_positions if p % 2 == 0]
    return all_positions, even_shifts


def build_sigma_matrix(rotation_list, n=32):
    """Build matrix of Σ action on H¹ basis."""
    _, even_shifts = sigma_polynomial_even_shifts(rotation_list, n)

    odd_positions = list(range(1, n, 2))
    idx = {k: i for i, k in enumerate(odd_positions)}
    M = np.zeros((len(odd_positions), len(odd_positions)), dtype=np.uint8)

    for k in odd_positions:
        for j in even_shifts:
            k_prime = k + j
            if k_prime in idx:
                M[idx[k], idx[k_prime]] ^= 1

    return M, odd_positions, even_shifts


def matrix_minus_identity(M):
    """Compute M - I (equivalently M + I over F_2)."""
    I = np.eye(M.shape[0], dtype=np.uint8)
    return (M ^ I) & 1


def joint_kernel(M1, M2):
    """Compute joint kernel: {v : v·M1 = 0 AND v·M2 = 0}.

    Stack matrices horizontally, then kernel of stacked is intersection of kernels.
    """
    rows = M1.shape[0]
    stacked = np.hstack([M1, M2])
    return compute_kernel(stacked)


def decode_vector(v, odd_positions):
    """Decode kernel vector: which k-positions contribute."""
    return [odd_positions[i] for i in range(len(v)) if v[i] == 1]


def main_analysis(n=32):
    print(f"=== Σ_0 and Σ_1 action on H¹(F_2[s]/(s^{n})) ===\n")

    # Build both matrices
    M_s0, odd_positions, shifts_s0 = build_sigma_matrix([2, 13, 22], n)
    M_s1, _, shifts_s1 = build_sigma_matrix([6, 11, 25], n)

    print(f"  Σ_0 even-shifts: {shifts_s0}")
    print(f"  Σ_1 even-shifts: {shifts_s1}")

    # Ranks
    print(f"\n  rank(Σ_0) = {gf2_rank(M_s0)}")
    print(f"  rank(Σ_1) = {gf2_rank(M_s1)}")

    # Compute (Σ - I) = N (nilpotent part)
    N0 = matrix_minus_identity(M_s0)
    N1 = matrix_minus_identity(M_s1)

    print(f"\n  rank(N_0 = Σ_0 - I) = {gf2_rank(N0)}")
    print(f"  rank(N_1 = Σ_1 - I) = {gf2_rank(N1)}")

    # Kernel of N_0 = fixed points of Σ_0 over F_2
    ker_s0 = compute_kernel(N0)
    ker_s1 = compute_kernel(N1)

    print(f"\n  dim kernel(Σ_0 - I) = {len(ker_s0)} (= fixed points of Σ_0 over F_2)")
    if ker_s0:
        print(f"    Basis vectors (as k-position combinations):")
        for v in ker_s0:
            positions = decode_vector(v, odd_positions)
            print(f"      [s^k·ds] for k ∈ {positions}")

    print(f"\n  dim kernel(Σ_1 - I) = {len(ker_s1)}")
    if ker_s1:
        print(f"    Basis vectors:")
        for v in ker_s1:
            positions = decode_vector(v, odd_positions)
            print(f"      [s^k·ds] for k ∈ {positions}")

    # Joint kernel
    joint = joint_kernel(N0, N1)
    print(f"\n  JOINT kernel dimension: {len(joint)}")
    if joint:
        print(f"    These are CLASSES INVARIANT under BOTH Σ_0 AND Σ_1 (over F_2):")
        for v in joint:
            positions = decode_vector(v, odd_positions)
            print(f"      Σ of [s^k·ds] for k ∈ {positions}")
    else:
        print(f"    NO common fixed points. Σ_0 and Σ_1 have no shared H¹-invariants.")

    return M_s0, M_s1, N0, N1, ker_s0, ker_s1, joint


def add_sigma_operations(n=32):
    """Also compute σ_0 and σ_1 (message schedule ops — but these include SHR).

    σ_0(x) = ROTR_7(x) ⊕ ROTR_18(x) ⊕ SHR_3(x)
    σ_1(x) = ROTR_17(x) ⊕ ROTR_19(x) ⊕ SHR_10(x)

    SHR is shift without wrap — NOT a rotation! SHR_k(x) = x >> k (integer division).
    In polynomial form F_2[x]/(x^n - 1): SHR doesn't preserve this structure since
    bits shift OUT rather than wrap around.

    More carefully: SHR on Z/2^n = division by 2^k rounded down. Different
    algebraic object. Cannot directly fit into same cyclic group algebra.

    For this session, let's note this but skip σ_0, σ_1 analysis.
    """
    print(f"\n=== Note on σ_0, σ_1 (message schedule) ===")
    print("""
    σ_0 = ROTR_7 ⊕ ROTR_18 ⊕ SHR_3
    σ_1 = ROTR_17 ⊕ ROTR_19 ⊕ SHR_10

    SHR (shift right without wrap) does NOT live in cyclic group algebra
    F_2[x]/(x^n - 1) — it's a different algebraic operation (breaks cyclic
    structure).

    For cohomological analysis restricted to rotation ring, we can only
    handle ROTR-based operations. σ_0, σ_1 need separate framework.

    This means our H¹-analysis is INCOMPLETE for message schedule. Session
    16+ should address this — potentially via "monoidal" or "semigroup"
    structure instead of cyclic group.
""")


if __name__ == "__main__":
    main_analysis(n=32)
    add_sigma_operations()
