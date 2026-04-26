"""
Question: is there a LINEAR basis change over F_2 that makes rotations
filtration-preserving (AND keeps ADD, XOR filtration-preserving)?

Answer from algebraic theory: NO, because:
  1. ROTR has minimal polynomial (x-1)^n over F_2 (not semisimple)
  2. Only 1-dim rotation-invariant subspace = span((1,1,...,1))
  3. No filtration with more non-trivial levels can be rotation-invariant

Let me verify this numerically + formalize.

Then ask: what about NON-LINEAR basis changes?
"""

import numpy as np
import random
from witt_vectors import int_to_witt, witt_to_int, witt_rotr, witt_xor, witt_add


def rotation_matrix(n, r):
    """ROTR_r as n×n matrix over F_2. Matrix M such that M·x = rotr(x, r)."""
    M = np.zeros((n, n), dtype=np.uint8)
    for i in range(n):
        # bit i of output = bit (i+r) mod n of input
        M[i, (i + r) % n] = 1
    return M


def gf2_char_poly(M):
    """Compute characteristic polynomial of M over F_2 (symbolic, via minors — for small n)."""
    # For n small, use sympy or direct
    from sympy import Matrix, symbols
    x = symbols('x')
    M_sym = Matrix(M.astype(int))
    # char poly: det(xI - M)
    p = M_sym.charpoly(x)
    # Reduce coefficients mod 2
    expr = p.as_expr()
    coeffs = [int(expr.coeff(x, i)) % 2 for i in range(n + 1)]
    return coeffs  # ascending powers


def min_poly(M, n):
    """Find minimal polynomial of M over F_2.
    Try polynomials of increasing degree: does M satisfy p(M) = 0?"""
    # Over F_2, minimal poly of ROTR_r where r·k = n for some k...
    # For cyclic shift ROTR_1 on Z/2^n, order is n (ROTR_1^n = I)
    # Minimal polynomial divides x^n - 1 = x^n + 1 over F_2
    # x^n + 1 factors over F_2 based on n
    # For general n, x^n + 1 = prod of cyclotomic polynomials
    return None  # leave as analysis


def rotation_invariant_subspaces(n, r):
    """Find all rotation-invariant subspaces (eigenspaces) of ROTR_r.

    Over F_2, ROTR has minimal poly (x-1)^n for n=2^k case, making it
    NON-SEMISIMPLE. Only 1-dim invariant: span of (1,1,...,1).
    """
    M = rotation_matrix(n, r)
    I = np.eye(n, dtype=np.uint8)
    # Kernel of (M - I) over F_2 = eigenspace for eigenvalue 1
    K = (M - I) % 2
    # Gaussian elimination to find null space
    from cohomology_probe import gf2_rank
    from persistent_kernel import gf2_left_null_basis
    null = gf2_left_null_basis(K.T.astype(np.uint8))
    return null


def test_all_filtration_preserving_basis(n):
    """Search for filtration + rotation-preserving basis.

    A linear basis change T: F_2^n → F_2^n is filtration-preserving if T
    maps F_k to F_k for all k.  This means T is LOWER-TRIANGULAR in bit basis.

    We want T such that ALSO T·ROTR_r·T^{-1} is lower-triangular for r ∈ rotations.

    For ROTR_r to be lower-triangular in SOME basis, that basis must diagonalize
    its eigenstructure. But ROTR has only 1 Jordan block → can only be put in
    1 Jordan form (with dim = n), which is full-rank everywhere.

    We verify: lower-triangular M commuting with triangular ROTR requires
    specific structure. Computationally: enumerate upper-triangular T ∈ GL(F_2^n)
    and check.
    """
    print(f"\n--- Rotation-invariant subspaces of ROTR in F_2^{n} ---")
    for r in [1, 2, 3, 5, 7]:
        if r >= n: continue
        inv = rotation_invariant_subspaces(n, r)
        print(f"  ROTR_{r}: dim of eigenspace(λ=1) = {len(inv)}")
        if len(inv) <= 4:
            for v in inv:
                print(f"    {list(v)}")

    print(f"\n--- Is ROTR_1 semisimple over F_2^{n}? ---")
    M = rotation_matrix(n, 1)
    I = np.eye(n, dtype=np.uint8)
    # Check if (M-I)^2 = 0 already. If not, Jordan block has size > 2.
    D = (M - I) % 2
    for power in range(1, n + 1):
        D_power = D.copy()
        for _ in range(power - 1):
            D_power = (D_power @ D) % 2
        if D_power.sum() == 0:
            print(f"  (M-I)^{power} = 0  →  Jordan block of size ≤ {power}")
            print(f"  → ROTR_1 is {'semisimple' if power == 1 else 'NOT semisimple (nilpotent-plus-I)'}")
            break
    else:
        print(f"  (M-I)^{n} ≠ 0  (shouldn't happen)")


def measure_rotation_filtration_break(n, rotations):
    """Numerical measurement: for specific SHA rotations, what's the 'obstruction'?
    For each level k and rotation r: fraction of inputs in F_k whose ROTR image leaves F_k.
    """
    print(f"\n--- Numerical obstruction table (n={n}) ---")
    print(f"{'rotation':>10} | " + " ".join(f"F_{k:>2}" for k in range(1, n, 2)))
    print("-" * (12 + 5 * (n // 2)))
    for r in rotations:
        if r >= n: continue
        rates = []
        for k in range(1, n, 2):
            random.seed(0)
            preserves = 0
            trials = 500
            for _ in range(trials):
                x = random.randint(0, 2**(n-k) - 1) << k
                wx = int_to_witt(x, n)
                out = witt_rotr(wx, r)
                out_int = witt_to_int(out)
                if (out_int & ((1 << k) - 1)) == 0:  # still in F_k
                    preserves += 1
            break_rate = 1.0 - preserves / trials
            rates.append(break_rate)
        print(f"ROTR_{r:>3} | " + " ".join(f"{rate:>4.2f}" for rate in rates))


if __name__ == "__main__":
    for n in [8, 16]:
        test_all_filtration_preserving_basis(n)
    # SHA-256-like rotation constants (scaled down)
    print()
    measure_rotation_filtration_break(16, [1, 2, 3, 7, 11, 13])
