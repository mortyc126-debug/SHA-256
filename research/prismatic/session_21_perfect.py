"""
Session 21: Structural analysis of L_SHA perfect sub-algebra (dim 264).

After Session 20 proved L_SHA NOT solvable, with perfect D^4 = D^5 of dim 264.
This session tries to characterize this 264-dim Lie algebra.

Tests:
  1. Extract explicit basis of D^4 (perfect sub-algebra)
  2. Compute center Z(D^4) = elements commuting with all
  3. Check action on F_2^32: is it irreducible?
  4. Look for non-trivial ideals (simplicity test)
  5. Compare to known classical dimensions

Classical Lie algebras over F_2:
  gl_n: n² = 1024 (n=32)
  sl_n: n²-1 = 1023
  so_n: n(n-1)/2 for n odd = special in char 2
  sp_n: n(n+1)/2 = 528 (n=32)
  psl_n = sl_n / center: 1022 or 1023

  Note: dim 264 = 32·33/4 (specific combinatorial expression).
  Or 264 = 2^8 + 8 = 256 + 8.
  Doesn't match classical directly.
"""
import numpy as np
from session_17_and import change_of_basis_x_to_s, change_of_basis_s_to_x
from session_18b_shr import shr_matrix_in_s_basis
from session_14_sigma0 import lucas_expansion
from session_20b_derived import GF2Basis, rotr_full, bracket_all_pairs, span_of, commutator

N = 32


def extract_perfect_subalgebra():
    """Extract basis of D^4 from derived series."""
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

    # D^0 = span(generators)
    D = span_of(generators)
    # Iterate derived series
    for _ in range(4):  # D^0, D^1, D^2, D^3, D^4
        brackets = bracket_all_pairs(D)
        D = span_of(brackets)
    return D  # D^4 = D^5, perfect sub-algebra


def compute_center(L):
    """Center Z(L) = {x ∈ L : [x, y] = 0 for all y ∈ L}."""
    print(f"  Computing center of L (dim {len(L)})...")
    # For each x in L, check if [x, generator] = 0 for all generators
    # Use L itself as generating set
    center = []
    basis_flat = np.array([m.flatten() for m in L], dtype=np.uint8)

    for x in L:
        is_central = True
        for y in L:
            C = commutator(x, y)
            if C.sum() > 0:
                is_central = False
                break
        if is_central:
            center.append(x)

    # Span of center
    center_basis = span_of(center)
    return center_basis


def check_representation_kernel(L):
    """Kernel of L → gl(F_2^32): elements acting as 0."""
    zero_elements = [m for m in L if m.sum() == 0]
    return zero_elements


def compute_trace_structure(L):
    """Over F_2, trace is in F_2. Check which elements have zero trace.
    sl sub-algebra = trace 0 elements."""
    zero_trace = 0
    nonzero_trace = 0
    for m in L:
        t = np.trace(m) % 2
        if t == 0:
            zero_trace += 1
        else:
            nonzero_trace += 1
    return zero_trace, nonzero_trace


def test_irreducibility(L):
    """Is F_2^32 irreducible as L-module?
    Equivalently: are there non-trivial L-invariant subspaces?

    Quick test: start with a vector v, generate submodule L·v (all iterated Lv).
    If submodule = full F_2^32, v is cyclic. If exists v with small submodule,
    module is reducible."""
    n = 32
    # Try several starting vectors
    results = []
    for start_bit in [0, 1, 5, 15, 31]:
        v = np.zeros(n, dtype=np.uint8)
        v[start_bit] = 1
        # Submodule = span of L·v, L·L·v, ...
        submodule = GF2Basis(n)
        submodule.add(v)
        frontier = [v]
        while frontier:
            new_frontier = []
            for u in frontier:
                for A in L[:20]:  # use first 20 elements (sub-sample)
                    Au = (A @ u) % 2
                    added, _ = submodule.add(Au)
                    if added:
                        new_frontier.append(Au)
            frontier = new_frontier
            if submodule.size() >= n:
                break
        results.append((start_bit, submodule.size()))
    return results


def dimension_analysis():
    """Match 264 to known structures."""
    print("\n=== Dimension 264 analysis ===")
    print(f"  264 = 8 × 33")
    print(f"  264 = 2^3 × 3 × 11")
    print(f"  264 = 32 × 33 / 4")
    print(f"  264 = 16 × 16.5 (not integer)")
    print()
    print(f"  Classical Lie algebras over F_2 (n=32):")
    print(f"    gl_32  = 1024")
    print(f"    sl_32  = 1023")
    print(f"    sp_32  = 528")
    print(f"    so_32  ~ 496 (char 2 subtleties)")
    print(f"    psl_n = n²-1 (n=17: 288), (n=16: 255)")
    print()
    print(f"  264 doesn't match classical directly.")
    print()
    print(f"  Decomposition possibilities:")
    print(f"    As direct sum of simples?")
    print(f"      264 = 2 × 132 (psl_?)")
    print(f"      264 = 3 × 88")
    print(f"      264 = 8 × 33 = 8 × sl_? (sl_n with n(n+1)/2=33: n=? no match)")
    print()
    print(f"  Likely: specific structure particular to SHA-256 rotation+shift pattern.")
    print(f"  Not easily classified without deeper analysis.")


def main():
    print("=== Session 21: L_SHA^perfect analysis ===\n")

    print("Step 1: Extract basis of D^4 (perfect sub-algebra)")
    D4 = extract_perfect_subalgebra()
    print(f"  dim D^4 = {len(D4)}  (expected 264)")

    print("\nStep 2: Compute center Z(D^4)")
    # May be expensive; sample-based
    # Center: x such that [x, y] = 0 for all y in D^4
    # Since D^4 = [D^4, D^4] (perfect), if x is central, x commutes with brackets,
    # which are all of D^4.
    center = compute_center(D4)
    print(f"  dim Z(D^4) = {len(center)}")

    print("\nStep 3: Check identity action (kernel of representation)")
    zero_count = sum(1 for m in D4 if m.sum() == 0)
    print(f"  Elements acting as 0: {zero_count} / {len(D4)}")

    print("\nStep 4: Trace structure")
    zt, nzt = compute_trace_structure(D4)
    print(f"  Zero-trace elements: {zt}, non-zero trace: {nzt}")
    print(f"  If all zero trace, D^4 ⊆ sl_{N}(F_2)")

    print("\nStep 5: Test irreducibility of F_2^32 as L-module")
    results = test_irreducibility(D4)
    for start_bit, dim in results:
        print(f"    e_{start_bit} generates submodule of dim {dim}")

    dimension_analysis()


if __name__ == "__main__":
    main()
