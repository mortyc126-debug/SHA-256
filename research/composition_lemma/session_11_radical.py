"""
Session 11: Find solvable radical R of D^4, decompose D^4/R, cryptanalytic translation.

After Session 10:
- D^4 has 47 proper ideals (dims 45/55/65/75)
- Union span 145 of 264 dim
- Likely structure: D^4 = R (solvable radical) + S (semisimple part)

Tasks:
1. Fix signature: count true distinct ideals via dim-of-union test
2. For each true distinct ideal I, test solvability:
   - [I, I] = derived. If = 0 → abelian → solvable
   - If proper sub → check derived series
3. Sum all solvable ideals → solvable radical R
4. D^4 / R dim → semisimple part
5. Cryptanalytic translation: для each I, find F_2^32 support (bits affected)
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


LOG_FILE = '/home/user/SHA-256/research/composition_lemma/session_11_log.txt'


def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')


def setup_basis_resolver(D4):
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


def span_dim(vectors, n):
    """Dim of span of vectors over F_2."""
    if not vectors:
        return 0
    basis = GF2Basis(n)
    for v in vectors:
        basis.add(v.copy())
    return basis.size()


def spans_equal(basis_a, basis_b, n):
    """Test if span(basis_a) = span(basis_b) over F_2."""
    da = span_dim(basis_a, n)
    db = span_dim(basis_b, n)
    if da != db:
        return False
    combined = list(basis_a) + list(basis_b)
    return span_dim(combined, n) == da


def span_contains(basis_big, vectors_small, n):
    """Test if span(basis_big) ⊇ span(vectors_small)."""
    d_big = span_dim(basis_big, n)
    combined = list(basis_big) + list(vectors_small)
    return span_dim(combined, n) == d_big


def bracket_basis_x_basis(basis_a, basis_b, ad_flat, n):
    """Compute [span(a), span(b)] = span of all [u, v] for u ∈ a, v ∈ b.
    Returns list of nonzero brackets."""
    result = []
    for u in basis_a:
        nonzero_u = np.where(u == 1)[0]
        if len(nonzero_u) == 0:
            continue
        for v in basis_b:
            if v.sum() == 0:
                continue
            # [u, v] = sum_i u[i] (ad[i] @ v)
            # ad_flat indexed by (i*n + k, l) → ad_subset_flat[i_local, k, l]
            ad_subset_flat = ad_flat[(nonzero_u[:, None] * n + np.arange(n)[None, :]).flatten()]
            partials = (ad_subset_flat @ v.astype(np.int32)) & 1
            partials = partials.reshape(len(nonzero_u), n)
            bracket = partials.sum(axis=0) & 1
            if bracket.sum() > 0:
                result.append(bracket.astype(np.uint8))
    return result


def derived_ideal(I_basis, ad_flat, n):
    """Compute [I, I]: derived sub-ideal."""
    derived = bracket_basis_x_basis(I_basis, I_basis, ad_flat, n)
    return derived


def is_solvable(I_basis, ad_flat, n, max_depth=20):
    """Test if ideal I is solvable: derived series eventually = 0."""
    current = list(I_basis)
    for depth in range(max_depth):
        if span_dim(current, n) == 0:
            return True, depth
        next_derived = derived_ideal(current, ad_flat, n)
        if span_dim(next_derived, n) == 0:
            return True, depth + 1
        if spans_equal(current, next_derived, n):
            return False, depth + 1  # stabilized at non-zero
        current = next_derived
    return False, max_depth


def support_bits(I_basis_coeffs, D4_matrices):
    """Find F_2^32 support of ideal I: union of nonzero rows in matrices spanning I."""
    n = 264
    support = np.zeros(32, dtype=np.uint8)
    for v in I_basis_coeffs:
        # v is coefficient vector (length 264) in D^4 basis
        # actual matrix = sum_i v[i] D4_matrices[i]
        nonzero = np.where(v == 1)[0]
        for i in nonzero:
            # Each row of D4_matrices[i] tells which output bit is affected
            row_supports = D4_matrices[i].sum(axis=1) > 0
            support |= row_supports.astype(np.uint8)
            col_supports = D4_matrices[i].sum(axis=0) > 0
            support |= col_supports.astype(np.uint8)
    return support


def main():
    with open(LOG_FILE, 'w') as f:
        f.write('')

    log("=== Session 11: Radical extraction + decomposition + bit translation ===\n")

    log("Step 1: Setup")
    start = time.time()
    D4 = extract_perfect_subalgebra()
    n = len(D4)
    pivot_cols, T = setup_basis_resolver(D4)
    log(f"  D^4 dim {n} ({time.time()-start:.1f}s)")

    C = np.load('/home/user/SHA-256/research/composition_lemma/struct_constants.npy')
    ad = np.transpose(C, (0, 2, 1))
    ad_flat = ad.reshape(n*n, n)
    log(f"  Structure constants and ad matrices loaded ({time.time()-start:.1f}s)")

    log("\nStep 2: Load 47 ideals from decomposition.npz")
    decomp = np.load('/home/user/SHA-256/research/composition_lemma/decomposition.npz')
    ideals_list = []  # (key, dim, basis)
    for key in decomp.files:
        basis = decomp[key]
        d = basis.shape[0]
        ideals_list.append((key, d, [basis[i] for i in range(d)]))
    log(f"  Loaded {len(ideals_list)} ideals")

    log("\nStep 3: Cluster by TRUE span equality (fix Session 10 bug)")
    distinct_ideals = []  # list of (representative_basis, dim)
    for key, d, basis in ideals_list:
        is_new = True
        for j, (rep_basis, rep_d) in enumerate(distinct_ideals):
            if spans_equal(basis, rep_basis, n):
                is_new = False
                break
        if is_new:
            distinct_ideals.append((basis, d))

    log(f"  TRUE distinct ideals: {len(distinct_ideals)}")
    dims = sorted(d for _, d in distinct_ideals)
    log(f"  Their dims: {dims}")

    log("\nStep 4: Test solvability of each distinct ideal")
    solvable_ideals = []
    perfect_ideals = []
    for j, (basis, d) in enumerate(distinct_ideals):
        solv, depth = is_solvable(basis, ad_flat, n)
        if solv:
            solvable_ideals.append((basis, d))
            log(f"  Ideal {j} (dim {d}): SOLVABLE (derived series → 0 at depth {depth})")
        else:
            perfect_ideals.append((basis, d))
            log(f"  Ideal {j} (dim {d}): NOT solvable (derived stabilized at depth {depth})")

    log(f"\n  Solvable ideals: {len(solvable_ideals)}")
    log(f"  Non-solvable (perfect or semisimple-with-perfect-derived): {len(perfect_ideals)}")

    log("\nStep 5: Compute solvable radical R = sum of all solvable ideals")
    R_vectors = []
    for basis, d in solvable_ideals:
        R_vectors.extend(basis)
    R_dim = span_dim(R_vectors, n)
    log(f"  Radical R dim: {R_dim}")
    log(f"  D^4 / R dim: {n - R_dim}")

    log("\nStep 6: Sanity check — is R itself solvable?")
    if R_vectors:
        R_basis = []
        rb = GF2Basis(n)
        for v in R_vectors:
            added, _ = rb.add(v.copy())
            if added:
                R_basis.append(v.copy())
        R_solv, R_depth = is_solvable(R_basis, ad_flat, n)
        log(f"  R solvable: {R_solv}, derived depth {R_depth}")

    log("\nStep 7: Cryptanalytic translation — F_2^32 bit support per ideal")
    for j, (basis, d) in enumerate(distinct_ideals):
        # basis vectors are coefficient vectors in D^4. Get support in F_2^32.
        support = support_bits(basis, D4)
        bit_positions = np.where(support == 1)[0]
        log(f"  Ideal {j} (dim {d}): bit support = {bit_positions.tolist()}")

    log(f"\nTotal wall time: {time.time()-start:.1f}s")

    # Save analysis
    np.savez('/home/user/SHA-256/research/composition_lemma/radical_analysis.npz',
             radical_dim=np.array([R_dim]),
             num_distinct=np.array([len(distinct_ideals)]),
             num_solvable=np.array([len(solvable_ideals)]))


if __name__ == "__main__":
    main()
