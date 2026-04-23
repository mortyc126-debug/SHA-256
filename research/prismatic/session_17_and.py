"""
Session 17: AND integration — exploration.

AND is the primary obstruction in our framework (Sessions 3-4 established
δ(x AND y) not derivable from ring operations).

In rotation ring F_2[x]/(x^n - 1) = F_2[s]/(s^n):
  - Convolution mult (ring op): x^i · x^j = x^{(i+j) mod n}
  - AND (pointwise): not the ring op

Two rings on same F_2-vector space F_2^n:
  - Rotation ring: convolution (F_2[x]/(x^n - 1))
  - Boolean ring: pointwise ≅ F_2^n = ∏ F_2 (product ring)

Boolean ring has TRIVIAL higher cohomology (product of fields).
Rotation ring has non-trivial H¹.

AND bridges these: it's bilinear pairing R × R → R where R has TWO
multiplication structures simultaneously.

This session explores concrete change-of-basis and what happens to AND
when we express it in s-basis (the rotation-theoretic basis).
"""

import numpy as np
from session_14_sigma0 import lucas_expansion, gf2_rank, compute_kernel


def change_of_basis_x_to_s(n):
    """Change-of-basis matrix: expressing x^k in s-basis.
    T[i, k] = coefficient of s^i in x^k.
    By Lucas: T[i, k] = 1 iff bin(i) ⊆ bin(k).
    """
    T = np.zeros((n, n), dtype=np.uint8)
    for k in range(n):
        for i in range(n):
            if (i & k) == i:  # bin(i) ⊆ bin(k)
                T[i, k] = 1
    return T


def change_of_basis_s_to_x(T):
    """Inverse of T over F_2. For our upper-triangular T with 1s on diagonal,
    T^{-1} has specific structure (also upper triangular)."""
    n = T.shape[0]
    # Augment with identity and row-reduce to get T^{-1}
    aug = np.hstack([T.copy(), np.eye(n, dtype=np.uint8)])
    r = 0
    for c in range(n):
        if r >= n: break
        pivot = None
        for rr in range(r, n):
            if aug[rr, c] == 1:
                pivot = rr; break
        if pivot is None: continue
        if pivot != r:
            aug[[r, pivot]] = aug[[pivot, r]]
        for rr in range(n):
            if rr != r and aug[rr, c] == 1:
                aug[rr] ^= aug[r]
        r += 1
    return aug[:, n:]


def and_matrix_in_s_basis(n):
    """Build AND operation as matrix in s-basis.

    In x-basis: AND is pointwise: (x AND y)_i = α_i · β_i (where α, β are x-basis coeffs)
    This gives bilinear form. For y FIXED, it's a linear map on x (as vector).

    But we want to understand: given x, y in s-basis, what's x AND y in s-basis?
    Compute: convert to x-basis (via T^{-1}), pointwise multiply, convert back (via T).

    For simplicity, let's demonstrate with specific y and compute "AND-with-y" as a linear map.
    """
    T = change_of_basis_x_to_s(n)
    T_inv = change_of_basis_s_to_x(T)

    # Verify T · T^{-1} = I mod 2
    I_test = (T @ T_inv) % 2
    assert np.array_equal(I_test, np.eye(n, dtype=np.uint8)), "Change of basis not invertible"

    return T, T_inv


def and_with_fixed_y_linear_map(y_s_basis, n):
    """Return matrix M such that (M · x)_s = (x AND y)_s (in s-basis).

    M = T · diag(T^{-1} · y_s_basis) · T^{-1}
    (compose: s → x, pointwise mult by y in x-basis, then x → s)
    """
    T, T_inv = and_matrix_in_s_basis(n)
    # y in x-basis
    y_x = (T_inv @ y_s_basis) % 2
    # Diagonal matrix of y in x-basis (pointwise mult by y)
    D = np.diag(y_x).astype(np.uint8)
    # Combined linear map in s-basis
    M = (T @ D @ T_inv) % 2
    return M


def study_and_action(n=8):
    """For small n, study AND-with-various-y action on R."""
    print(f"=== AND-with-y action on F_2[s]/(s^{n}) ===\n")

    T, T_inv = and_matrix_in_s_basis(n)

    print(f"  Change-of-basis matrix T (x-basis → s-basis), {n}×{n} upper triangular:")
    for i in range(n):
        print("    " + " ".join(str(T[i, j]) for j in range(n)))

    print(f"\n  Select a few y values (in s-basis) and compute AND-with-y as linear map:")
    # Interesting y choices:
    ys = {
        "1 (= all x-bits set?)": np.array([1] + [0]*(n-1), dtype=np.uint8),
        "s (=single s-bit)": np.array([0, 1] + [0]*(n-2), dtype=np.uint8),
        "1+s (=ζ_n = x)": np.array([1, 1] + [0]*(n-2), dtype=np.uint8),
    }

    for label, y_s in ys.items():
        y_x = (T_inv @ y_s) % 2
        print(f"\n    y = {label}")
        print(f"      In s-basis: {y_s.tolist()}")
        print(f"      In x-basis: {y_x.tolist()}")
        if y_x.sum() == 0:
            print(f"      → AND-with-y = 0 (zero operator)")
            continue
        M = and_with_fixed_y_linear_map(y_s, n)
        print(f"      AND-with-y matrix (in s-basis):")
        for i in range(n):
            print("        " + " ".join(str(M[i, j]) for j in range(n)))
        print(f"      Rank over F_2: {gf2_rank(M)}")


def action_on_H1():
    """Action of AND on H¹ of F_2[s]/(s^n).

    H¹ has basis [s^k · ds] for odd k. But AND is not a ring op,
    so doesn't directly act on cohomology in functorial way.

    What we CAN compute: for fixed y, "AND-with-y" is F_2-linear on R.
    It induces map on H¹ (as Z_2-linear self-map).

    But this is NOT a ring automorphism — it's just a linear endomorphism.
    """
    print("\n=== Action of AND on H¹ — structural note ===")
    print("""
    AND is BILINEAR, not a ring operation on rotation ring.

    For fixed y, map x → (x AND y) is Z_2-linear on R.
    Induces Z_2-linear map on cohomology: H¹(R) → H¹(R).

    BUT: this map is NOT a ring automorphism. So it doesn't preserve
    cup products or ring structure on cohomology.

    Rank of induced map varies with choice of y. Specific y values
    correspond to specific "projection" structures.

    This is different from ROTR actions (Session 13) which ARE ring
    automorphisms.

    CONCLUSION: AND can be studied as family of Z_2-linear maps on H¹
    parameterized by y ∈ R. NOT as single element acting.
    """)


def ch_maj_decomposition():
    """How do Ch, Maj decompose into AND and XOR operations?"""
    print("\n=== Ch, Maj decomposition via AND and XOR ===")
    print("""
    SHA uses:
      Ch(e, f, g) = (e AND f) XOR (NOT e AND g)
                  = e·f + (1-e)·g  in F_2-algebra on bits
                  = e·f + g + e·g
                  = g + e·(f + g)
                  = g + e·(f XOR g)

    So Ch = (FIXED g) + (e AND (f XOR g))

      Maj(a, b, c) = (a AND b) XOR (a AND c) XOR (b AND c)
                   = a·b + a·c + b·c
                   = a·(b+c) + b·c
                   = a·(b XOR c) + (b AND c)
                   = (a AND (b XOR c)) XOR (b AND c)

    Both Ch, Maj involve AND with XOR-argument, then XOR'd with additional terms.

    For cohomology framework: Ch/Maj require handling both XOR and AND.
    Our rotation ring handles XOR via ring addition. AND remains extension.
    """)


def summary_of_obstruction():
    print("\n=== Summary: AND's place in cohomology framework ===")
    print("""
    THREE DIFFERENT STRUCTURES ON F_2^n:

    1. Rotation ring R = F_2[x]/(x^n - 1)
       - Convolution multiplication
       - Non-trivial H¹ (our Session 10 theorem)
       - ROTR = mult by units in R

    2. Boolean ring B = F_2^n = ∏ F_2
       - Pointwise multiplication (= AND)
       - Trivial higher cohomology
       - Includes idempotents (= bits as projections)

    3. Combined "full" structure:
       - Same additive group
       - Hopf algebra structure? (Fourier duality?)
       - Not explored in literature for cryptographic purposes

    SHA round function involves:
      - Rotations (live in R)
      - XOR = addition (in both R and B)
      - AND (lives in B, not R)
      - ADD mod 2^n (different algebra: Z_2-lift)

    Each needs different algebraic structure. Integrating all — open problem.

    FOR OUR PROGRAM: H¹(R) captures rotation structure. Other structures
    would need separate cohomology theories. The "full" answer requires
    bialgebra or derived category framework, which we haven't built.
    """)


if __name__ == "__main__":
    study_and_action(n=8)
    action_on_H1()
    ch_maj_decomposition()
    summary_of_obstruction()
