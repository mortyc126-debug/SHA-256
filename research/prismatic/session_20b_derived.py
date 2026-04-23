"""
Session 20b: Derived series computation — smarter approach.

Instead of building full L_SHA (expensive), directly compute derived series:
  D^0 = span(generators)
  D^{k+1} = span{[A, B] : A, B ∈ D^k}

If D^k = 0 for some k → L_SHA is solvable of derived length k.
If D^k stabilizes at non-zero → L_SHA NOT solvable.

This is MUCH faster because D^k usually stays small.
"""
import numpy as np
from session_17_and import change_of_basis_x_to_s, change_of_basis_s_to_x
from session_18b_shr import shr_matrix_in_s_basis
from session_14_sigma0 import lucas_expansion

N = 32


def commutator(A, B):
    return ((A @ B) ^ (B @ A)) & 1


def rotr_full(r, n):
    coeffs = set(lucas_expansion(r, n - 1))
    M = np.zeros((n, n), dtype=np.uint8)
    for j in range(n):
        for pos in coeffs:
            t = j + pos
            if t < n:
                M[t, j] ^= 1
    return M


class GF2Basis:
    """Incremental basis over F_2. O(n) per add."""
    def __init__(self, dim):
        self.dim = dim
        self.basis = []
        self.pivots = []

    def reduce(self, v):
        v = v.copy() & 1
        for b, p in zip(self.basis, self.pivots):
            if v[p] == 1:
                v = v ^ b
        return v

    def add(self, v):
        v_red = self.reduce(v)
        nz = np.where(v_red == 1)[0]
        if len(nz) == 0:
            return False, None
        p = nz[0]
        self.basis.append(v_red)
        self.pivots.append(p)
        return True, v_red

    def size(self):
        return len(self.basis)


def span_of(matrices):
    """Given list of matrices, return independent basis (as list of matrices)."""
    if not matrices:
        return []
    n = matrices[0].shape[0]
    basis = GF2Basis(n * n)
    indep = []
    for M in matrices:
        if M.sum() == 0:
            continue
        added, _ = basis.add(M.flatten())
        if added:
            indep.append(M)
    return indep


def bracket_all_pairs(matrices):
    """Compute [A, B] for all distinct pairs, return list of brackets."""
    result = []
    for i, A in enumerate(matrices):
        for j, B in enumerate(matrices):
            if i < j:
                C = commutator(A, B)
                if C.sum() > 0:
                    result.append(C)
    return result


def derived_series(generators, max_depth=15, time_budget_s=90):
    """Compute derived series starting from generators.
    Returns (dims, depth_where_terminated or -1)."""
    import time
    start = time.time()

    # D^0 = span(generators)
    D = span_of(generators)
    dims = [len(D)]
    print(f"  D^0 = span(generators), dim = {len(D)}")

    for depth in range(1, max_depth):
        if time.time() - start > time_budget_s:
            print(f"  [Time budget exhausted at depth {depth}]")
            return dims, -1

        # D^{depth} = span of brackets of D^{depth-1}
        brackets = bracket_all_pairs(D)
        D_next = span_of(brackets)
        dims.append(len(D_next))
        print(f"  D^{depth} dim = {len(D_next)}")
        if len(D_next) == 0:
            return dims, depth
        if len(D_next) == len(D):
            # check if D_next = D
            basis_old = GF2Basis(D[0].shape[0] ** 2)
            for M in D:
                basis_old.add(M.flatten())
            combined = list(D) + D_next
            basis_combined = GF2Basis(D[0].shape[0] ** 2)
            for M in combined:
                basis_combined.add(M.flatten())
            if basis_combined.size() == basis_old.size():
                # D^{depth} = D^{depth-1} (fixed point, not solvable)
                print(f"  D^{depth} = D^{depth-1} (fixed point): NOT SOLVABLE")
                return dims, -1

        D = D_next

    return dims, -1


def main():
    print("=== Session 20b: Derived series of L_SHA ===\n")

    S0 = np.zeros((N, N), dtype=np.uint8)
    for r in [2, 13, 22]: S0 ^= rotr_full(r, N)
    S0 &= 1
    S1 = np.zeros((N, N), dtype=np.uint8)
    for r in [6, 11, 25]: S1 ^= rotr_full(r, N)
    S1 &= 1
    sig0 = np.zeros((N, N), dtype=np.uint8)
    for r in [7, 18]: sig0 ^= rotr_full(r, N)
    sig0 ^= shr_matrix_in_s_basis(3, N)
    sig0 &= 1
    sig1 = np.zeros((N, N), dtype=np.uint8)
    for r in [17, 19]: sig1 ^= rotr_full(r, N)
    sig1 ^= shr_matrix_in_s_basis(10, N)
    sig1 &= 1

    I = np.eye(N, dtype=np.uint8)
    generators = [(S ^ I) & 1 for S in [S0, S1, sig0, sig1]]

    print("Computing derived series D^0, D^1, D^2, ...")
    dims, depth = derived_series(generators, max_depth=12, time_budget_s=90)

    print(f"\n=== Conclusion ===")
    print(f"Derived series dimensions: {dims}")
    if depth > 0:
        print(f"D^{depth} = 0")
        print(f"L_SHA is SOLVABLE of derived length {depth}.")
    elif depth == -1:
        if dims[-1] == 0:
            print(f"L_SHA is SOLVABLE.")
        else:
            # Check if stabilized
            if len(dims) >= 2 and dims[-1] == dims[-2]:
                print(f"D^k stabilized at dim {dims[-1]} > 0.")
                print(f"L_SHA has non-trivial [L, L] = L sub-structure.")
                print(f"L_SHA is NOT SOLVABLE (contains non-solvable sub-algebra).")
            else:
                print(f"Did not determine solvability in given depth/time.")


if __name__ == "__main__":
    main()
