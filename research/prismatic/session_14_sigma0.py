"""
Session 14: Compute Σ_0 action on H¹(F_2[s]/(s^32)).

SHA-256 Σ_0(x) = ROTR_2(x) ⊕ ROTR_13(x) ⊕ ROTR_22(x).

In our framework:
  ROTR_r = multiplication by (1+s)^r in F_2[s]/(s^32).
  Σ_0 = sum of three ROTR's (as Z_2-module operators, XOR'd).

Action on H¹ = linear map on 16-dim Z_2-module (Session 10).

STEP 1: Compute (1+s)^r via Lucas's theorem (char 2).
STEP 2: Compute Σ_0 = (1+s)^2 + (1+s)^13 + (1+s)^22 as polynomial.
STEP 3: Extract EVEN-shift components (only even shifts contribute on H¹ basis).
STEP 4: Build 16x16 matrix over F_2.
STEP 5: Compute kernel/image ranks.
"""

import numpy as np


def lucas_expansion(r, max_deg=31):
    """Positions of non-zero coefficients in (1+s)^r over F_2, up to degree max_deg.
    By Lucas: bin(i) ⊆ bin(r)."""
    positions = []
    for i in range(max_deg + 1):
        if (i & r) == i:  # binary(i) ⊆ binary(r)
            positions.append(i)
    return positions


def sigma_0_positions(n=32):
    """Compute Σ_0 = (1+s)^2 + (1+s)^13 + (1+s)^22 modulo s^n.
    Return (non-zero positions).
    """
    p2 = set(lucas_expansion(2, n - 1))
    p13 = set(lucas_expansion(13, n - 1))
    p22 = set(lucas_expansion(22, n - 1))

    # XOR (symmetric difference for sum in F_2)
    result = p2.symmetric_difference(p13).symmetric_difference(p22)
    return sorted(result)


def build_sigma_0_matrix_on_H1(n=32):
    """Build matrix of Σ_0 action on H¹ generators.

    Generators: [s^k · ds] for k odd, k ∈ {1, 3, ..., 31}.
    Σ_0 · [s^k · ds] = Σ_j [s^{k+j} · ds] where j runs over non-zero positions of Σ_0 polynomial.

    On H¹:
    - Position k+j contributes only if k+j is ODD (= j is EVEN, since k odd)
    - AND k+j ≤ n-1 (= 31)
    """
    sigma_0 = sigma_0_positions(n)
    print(f"  Σ_0 polynomial non-zero positions: {sigma_0}")

    # Only EVEN positions in Σ_0 contribute to H¹ action (odd shifts take odd→even, 0 in H¹)
    even_shifts = [j for j in sigma_0 if j % 2 == 0]
    print(f"  Even-position contributions (relevant for H¹): {even_shifts}")

    # Build matrix: rows = input k (odd, 16 values), cols = output k' (odd, 16 values)
    odd_positions = list(range(1, n, 2))  # [1, 3, 5, ..., 31]
    idx = {k: i for i, k in enumerate(odd_positions)}
    M = np.zeros((len(odd_positions), len(odd_positions)), dtype=np.uint8)

    for k in odd_positions:
        for j in even_shifts:
            k_prime = k + j
            if k_prime in idx:
                M[idx[k], idx[k_prime]] ^= 1

    return M, odd_positions, even_shifts


def gf2_rank(M):
    """Rank over F_2 via Gaussian elimination."""
    M = M.copy() & 1
    rows, cols = M.shape
    rank = 0
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = None
        for rr in range(r, rows):
            if M[rr, c] == 1:
                pivot = rr
                break
        if pivot is None:
            continue
        if pivot != r:
            M[[r, pivot]] = M[[pivot, r]]
        for rr in range(rows):
            if rr != r and M[rr, c] == 1:
                M[rr] ^= M[r]
        rank += 1
        r += 1
    return rank


def compute_kernel(M):
    """Compute left null space (kernel) of M over F_2.
    Returns basis vectors v such that v · M = 0."""
    rows, cols = M.shape
    # Augment with identity: [M | I], row-reduce M side
    aug = np.hstack([M.copy() & 1, np.eye(rows, dtype=np.uint8)])
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = None
        for rr in range(r, rows):
            if aug[rr, c] == 1:
                pivot = rr
                break
        if pivot is None:
            continue
        if pivot != r:
            aug[[r, pivot]] = aug[[pivot, r]]
        for rr in range(rows):
            if rr != r and aug[rr, c] == 1:
                aug[rr] ^= aug[r]
        r += 1

    # Rows with zero M-side are kernel vectors
    kernel = []
    for i in range(rows):
        if aug[i, :cols].sum() == 0:
            kernel.append(aug[i, cols:].copy())
    return kernel


def check_sigma_0_invertibility(n=32):
    """Σ_0 should be invertible on R = F_2[s]/(s^n) (since its constant term is 1+1+1 = 1).
    But on H¹ (torsion), invertibility may differ."""
    M, odd_positions, even_shifts = build_sigma_0_matrix_on_H1(n)

    print(f"\n  Σ_0 matrix on H¹ (16x16 over F_2):")
    print(f"  {'':5}", end="")
    for p in odd_positions:
        print(f"{p:>3}", end="")
    print()
    for i, p in enumerate(odd_positions):
        print(f"  k={p:>2}: ", end="")
        for j in range(len(odd_positions)):
            print(f"  {M[i,j]}", end="")
        print()

    # Rank
    r = gf2_rank(M)
    print(f"\n  Rank over F_2: {r}/{len(odd_positions)}")

    # Identity + M structure: Σ_0 = I + ... on H¹
    # If I = eye, and other shifts produce additional structure
    identity_part = M[0, 0]  # Check diagonal
    print(f"  Diagonal entries: {[int(M[i,i]) for i in range(len(odd_positions))]}")
    print(f"  (Identity contribution from '0' shift)")

    # Compute kernel
    kernel = compute_kernel(M)
    print(f"\n  Kernel dimension: {len(kernel)}")
    if kernel:
        print(f"  Kernel basis vectors (as combinations of H¹ generators):")
        for v in kernel:
            nonzero = np.where(v == 1)[0]
            positions = [odd_positions[i] for i in nonzero]
            print(f"    Σ of [s^k·ds] for k ∈ {positions}")

    return M


def invariants_interpretation(M, odd_positions):
    """Explain what kernel means."""
    kernel = compute_kernel(M)
    print(f"\n=== Σ_0 invariants ===")
    if not kernel:
        print("  Σ_0 has TRIVIAL kernel on H¹ over F_2.")
        print("  I.e., Σ_0 is INJECTIVE → no non-trivial Σ_0-invariants in H¹ mod 2.")
        print("  This means Σ_0 does NOT have H¹-level invariants beyond trivial.")
    else:
        print(f"  Σ_0 has {len(kernel)}-dimensional kernel on H¹.")
        print("  I.e., there are {len(kernel)} invariant directions.")
        print("  These are potential 'handles' — classes unchanged by Σ_0.")


def compare_with_other_ops():
    """Compare Σ_0 with other SHA operations."""
    ops = {
        'Σ_0 (ROTR_2⊕ROTR_13⊕ROTR_22)': [2, 13, 22],
        'Σ_1 (ROTR_6⊕ROTR_11⊕ROTR_25)': [6, 11, 25],
    }

    print(f"\n=== Comparison of SHA rotation ops ===")
    for name, rs in ops.items():
        positions = set()
        for r in rs:
            for p in lucas_expansion(r):
                if p in positions:
                    positions.remove(p)
                else:
                    positions.add(p)
        positions = sorted(positions)
        even_shifts = [p for p in positions if p % 2 == 0]
        print(f"\n  {name}:")
        print(f"    Polynomial positions: {positions}")
        print(f"    Even shifts (H¹ action): {even_shifts}")


if __name__ == "__main__":
    print("=== Session 14: Σ_0 action on H¹(F_2[s]/(s^32)) ===\n")
    M = check_sigma_0_invertibility(n=32)
    M2, odd_positions, _ = build_sigma_0_matrix_on_H1(n=32)
    invariants_interpretation(M2, odd_positions)
    compare_with_other_ops()
