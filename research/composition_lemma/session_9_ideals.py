"""
Session 9: Minimal ideals of D^4 = L_SHA^perfect (dim 264).

After Session 8 found Killing form ≡ 0 (char-2 pathology), classical Cartan-Killing
test inconclusive. Subgoal B: find minimal ideals directly.

Approach:
- For random x ∈ D^4, compute I_x = smallest ideal containing x:
    I_x = span{x} ∪ span{[y, x] : y ∈ D^4} ∪ span{[y, [z, x]] : y, z ∈ D^4} ∪ ...
    Iterate until closed under [D^4, ·].
- Test if I_x = D^4 (whole algebra) or proper.
- If proper minimal ideals exist, D^4 is not simple. Could be semisimple (direct sum)
  or have radical (nilpotent ideal).

Test for "abelian" ideal (= simple test): an ideal I with [I, I] = 0 is abelian.
If D^4 contains abelian ideal → D^4 has nontrivial solvable radical → NOT semisimple.

Sub-goals:
1. Compute several I_x for random x.
2. Find minimum dim across multiple trials → smallest ideal candidate.
3. Test smallest ideal for abelian property.
4. If smallest ideal = full D^4 for ALL random x → D^4 is simple Lie algebra.
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


def setup_basis_resolver(D4):
    """Same as Session 8."""
    n = 264
    BT = np.array([m.flatten() for m in D4], dtype=np.uint8)
    work = BT.copy()
    T = np.eye(n, dtype=np.uint8)
    pivot_cols = []
    row = 0
    for col in range(BT.shape[1]):
        if row >= n:
            break
        pivots_in_col = np.where(work[row:, col] == 1)[0]
        if len(pivots_in_col) == 0:
            continue
        pivot = row + pivots_in_col[0]
        if pivot != row:
            work[[row, pivot]] = work[[pivot, row]]
            T[[row, pivot]] = T[[pivot, row]]
        ones_mask = work[:, col] == 1
        ones_mask[row] = False
        if ones_mask.any():
            work[ones_mask] ^= work[row]
            T[ones_mask] ^= T[row]
        pivot_cols.append(col)
        row += 1
    return np.array(pivot_cols), T


def express_in_basis(v_flat, pivot_cols, T):
    """Express vector in D^4 basis. Returns coefficient vector (264-dim)."""
    return (v_flat[pivot_cols] @ T) & 1


def express_matrix(M, pivot_cols, T):
    """Express 32x32 matrix in basis."""
    return express_in_basis(M.flatten(), pivot_cols, T)


def compute_ideal_orbit(x_coeffs, D4, C, max_iter=20):
    """Given starting element x (as coeff vector in D^4 basis), compute smallest
    ideal containing x via repeated bracket [D^4, x].

    Returns: GF2Basis with all elements of ideal (as coefficient vectors in D^4).
    """
    n = 264
    ideal = GF2Basis(n)
    added, _ = ideal.add(x_coeffs)
    if not added:
        return ideal  # x = 0

    frontier = [x_coeffs.copy()]
    for it in range(max_iter):
        new_elements = []
        # Compute [x_i, y] for all i ∈ D^4 generators, y ∈ frontier
        for y in frontier:
            # For each y (coefficient vector), compute [x_i, y] for i = 0..263
            # [x_i, y] = sum_j y[j] [x_i, x_j] = sum_j y[j] sum_k C[i, j, k] x_k
            # In coeff form: ([x_i, y])[k] = sum_j y[j] C[i, j, k]
            for i in range(n):
                # bracket = sum_j y[j] * C[i, j, :] in F_2
                contributing_j = np.where(y == 1)[0]
                if len(contributing_j) == 0:
                    continue
                bracket = C[i, contributing_j, :].sum(axis=0) & 1
                if bracket.sum() > 0:
                    new_elements.append(bracket)
        # Add to ideal
        next_frontier = []
        for v in new_elements:
            added, v_red = ideal.add(v)
            if added:
                next_frontier.append(v)  # use original, not reduced (preserves info)
        frontier = next_frontier
        if not frontier:
            break  # closed

    return ideal


def test_ideal_abelian(ideal_basis_vecs, C):
    """Test if ideal I is abelian: [I, I] = 0.
    ideal_basis_vecs: list of coefficient vectors (each 264-dim).
    """
    for i, u in enumerate(ideal_basis_vecs):
        for j, v in enumerate(ideal_basis_vecs):
            if i >= j:
                continue
            # [u, v] = sum_a u[a] sum_b v[b] [x_a, x_b]
            # In coeffs: ([u, v])[k] = sum_a sum_b u[a] v[b] C[a, b, k]
            ua = np.where(u == 1)[0]
            vb = np.where(v == 1)[0]
            bracket = np.zeros(264, dtype=np.uint8)
            for a in ua:
                for b in vb:
                    bracket ^= C[a, b, :]
            bracket &= 1
            if bracket.sum() > 0:
                return False, (i, j, bracket)
    return True, None


def main():
    print("=== Session 9: Minimal ideals of D^4 ===\n")

    print("Step 1: Setup (extract D^4, compute structure constants)")
    start = time.time()
    D4 = extract_perfect_subalgebra()
    n = len(D4)
    pivot_cols, T = setup_basis_resolver(D4)
    print(f"  dim D^4 = {n}, basis resolver ready ({time.time()-start:.1f}s)")

    # Reuse structure constants from Session 8
    print("  Computing structure constants (or load from cache)...")
    cache_file = '/home/user/SHA-256/research/composition_lemma/struct_constants.npy'
    try:
        C = np.load(cache_file)
        print(f"  Loaded C from cache: {C.shape}")
    except Exception:
        # Recompute (same as Session 8)
        C = np.zeros((n, n, n), dtype=np.uint8)
        for i in range(n):
            Xi = D4[i]
            brackets = np.zeros((n, 1024), dtype=np.uint8)
            for j in range(n):
                Xj = D4[j]
                B = ((Xi @ Xj) ^ (Xj @ Xi)) & 1
                brackets[j] = B.flatten()
            C[i] = (brackets[:, pivot_cols] @ T) & 1
        np.save(cache_file, C)
        print(f"  Computed and saved C ({time.time()-start:.1f}s)")

    print("\nStep 2: Compute ideal orbits for random elements")
    rng = np.random.default_rng(42)
    n_trials = 30
    ideal_dims = []
    smallest_ideal = None
    smallest_dim = n + 1

    for trial in range(n_trials):
        # Random element of D^4 — random combination of basis
        x_coeffs = rng.integers(0, 2, size=n, dtype=np.uint8)
        if x_coeffs.sum() == 0:
            x_coeffs[0] = 1

        t0 = time.time()
        ideal = compute_ideal_orbit(x_coeffs, D4, C, max_iter=20)
        d = ideal.size()
        elapsed = time.time() - t0
        ideal_dims.append(d)
        if d < smallest_dim:
            smallest_dim = d
            smallest_ideal = ideal
        if trial < 5 or trial % 5 == 0:
            print(f"  Trial {trial}: |I_x| = {d} (took {elapsed:.1f}s)")

    print(f"\n  All ideal dims: min={min(ideal_dims)}, max={max(ideal_dims)}")
    print(f"  Distribution: {sorted(set(ideal_dims))}")
    counts = {d: ideal_dims.count(d) for d in sorted(set(ideal_dims))}
    print(f"  Counts: {counts}")

    print(f"\nStep 3: Smallest ideal found has dim {smallest_dim}")

    if smallest_dim == n:
        print("\n  ★ ALL random x generate full D^4 as ideal.")
        print("    → Strong evidence: D^4 is SIMPLE Lie algebra over F_2")
        print("    → Conjecture 21.1 confirmed in strongest form (D^4 itself simple)")
    else:
        print(f"\n  Proper ideal of dim {smallest_dim} found.")
        print("    → D^4 is NOT simple — has nontrivial proper ideal")

        # Test if smallest is abelian (= solvable radical)
        print("\nStep 4: Test if smallest ideal is abelian")
        abelian, info = test_ideal_abelian(smallest_ideal.basis, C)
        if abelian:
            print(f"  ✗ Smallest ideal IS abelian → D^4 has solvable radical")
            print(f"    → NOT semisimple. Conjecture 21.1 REFUTED.")
        else:
            print(f"  ✓ Smallest ideal NOT abelian → no immediate radical evidence")
            print(f"    → D^4 may still be semisimple (direct sum simples)")
            if info:
                i, j, bracket = info
                print(f"    Witness: [u_{i}, u_{j}] non-zero ({bracket.sum()} nonzero coords)")

    # Save smallest ideal basis for further analysis
    if smallest_ideal:
        ideal_basis_arr = np.array(smallest_ideal.basis, dtype=np.uint8)
        np.save('/home/user/SHA-256/research/composition_lemma/smallest_ideal.npy', ideal_basis_arr)
        print(f"\n  Smallest ideal basis saved ({ideal_basis_arr.shape})")


if __name__ == "__main__":
    main()
