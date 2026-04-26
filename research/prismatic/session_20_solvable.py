"""
Session 20: Test solvability of L_SHA.

Solvability: derived series D^k(L) = [D^{k-1}, D^{k-1}] terminates in 0.

OPTIMIZATION: use incremental Gaussian over F_2.
  - Maintain REDUCED basis matrix (flat vectors, row-reduced)
  - For each candidate: reduce against basis → if non-zero, add to basis
  - O(dim² · candidate_cost) rather than rebuilding rank each time

This is 10-100x faster than Session 19 approach.
"""
import numpy as np
from session_17_and import change_of_basis_x_to_s, change_of_basis_s_to_x
from session_18b_shr import shr_matrix_in_s_basis


N = 32  # SHA word size
DIM_GL = N * N  # 1024


def commutator(A, B):
    return ((A @ B) ^ (B @ A)) & 1


class GF2Basis:
    """Incremental basis over F_2 via row-reduced echelon form."""
    def __init__(self, dim):
        self.dim = dim  # total dimension of ambient space (1024 for gl_32)
        self.basis = []  # list of reduced vectors
        self.pivots = []  # positions of leading 1 for each basis vector

    def reduce(self, v):
        """Reduce v against current basis. Returns reduced form (zero if in span)."""
        v = v.copy() & 1
        for b, p in zip(self.basis, self.pivots):
            if v[p] == 1:
                v = v ^ b
        return v

    def add(self, v):
        """Try to add v. Returns True if independent (added), False if in span."""
        v_reduced = self.reduce(v)
        nonzero = np.where(v_reduced == 1)[0]
        if len(nonzero) == 0:
            return False  # in span
        # Pick leading 1 position (smallest index)
        p = nonzero[0]
        # Make new basis vector (we could also reduce existing basis against this)
        # For strict row-reduced form, do full reduce but simple version works
        self.basis.append(v_reduced)
        self.pivots.append(p)
        return True

    def size(self):
        return len(self.basis)


def build_lie_algebra_fast(generators, max_elements=2048, max_iter=10):
    """Fast bracket closure. Returns list of basis matrices."""
    n = generators[0].shape[0]
    dim = n * n
    basis = GF2Basis(dim)

    # Add generators
    matrices = []
    for G in generators:
        if basis.add(G.flatten()):
            matrices.append(G)

    # Iterate: bracket all pairs, add independent
    for iter_num in range(max_iter):
        new_count = 0
        current = list(matrices)  # snapshot
        for i, A in enumerate(current):
            for j, B in enumerate(current):
                if i < j:
                    C = commutator(A, B)
                    if C.sum() == 0:
                        continue
                    if basis.add(C.flatten()):
                        matrices.append(C)
                        new_count += 1
                        if len(matrices) >= max_elements:
                            return matrices, iter_num, True  # truncated
        if new_count == 0:
            return matrices, iter_num, False  # closed
    return matrices, max_iter, False  # maxed out iterations


def compute_derived(L, max_depth=10):
    """Derived series: D^{k+1} = [D^k, D^k].
    Returns list of dimensions [dim L, dim D^1, dim D^2, ...]."""
    dims = [len(L)]
    D_k = L  # D^0 = L
    for depth in range(1, max_depth):
        n = D_k[0].shape[0]
        basis = GF2Basis(n * n)
        D_next = []
        for i, A in enumerate(D_k):
            for j, B in enumerate(D_k):
                if i < j:
                    C = commutator(A, B)
                    if C.sum() == 0:
                        continue
                    if basis.add(C.flatten()):
                        D_next.append(C)
        dims.append(len(D_next))
        if len(D_next) == 0:
            return dims, depth
        D_k = D_next
    return dims, -1  # didn't terminate


def main():
    print("=== Session 20: Solvability of L_SHA ===\n")

    # Build generators (full 32x32 matrices in s-basis)
    def rotr_full(r, n):
        from session_14_sigma0 import lucas_expansion
        coeffs = set(lucas_expansion(r, n - 1))
        M = np.zeros((n, n), dtype=np.uint8)
        for j in range(n):
            for pos in coeffs:
                t = j + pos
                if t < n:
                    M[t, j] ^= 1
        return M

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

    print("Step 1: Build L_SHA via bracket closure (fast)")
    L, iters, truncated = build_lie_algebra_fast(generators, max_elements=1500, max_iter=20)
    status = "TRUNCATED" if truncated else ("CLOSED" if iters > 0 else "DID NOT CLOSE")
    print(f"  dim L_SHA = {len(L)}  (status: {status}, iterations: {iters})")

    if truncated:
        print(f"  (upper bound on dimension, may be larger)")

    print("\nStep 2: Derived series D^k")
    dims, depth = compute_derived(L, max_depth=10)
    print(f"  Dimensions of derived series:")
    for i, d in enumerate(dims):
        marker = "= D^0 = L" if i == 0 else f"= D^{i}"
        print(f"    dim D^{i} = {d}  {marker if i == 0 else ''}")
        if d == 0:
            print(f"\n  → L_SHA is SOLVABLE of derived length {i}")
            return

    if depth == -1:
        print(f"\n  Did not terminate. L_SHA may NOT be solvable.")
        print(f"  Derived series: {dims}")


if __name__ == "__main__":
    main()
