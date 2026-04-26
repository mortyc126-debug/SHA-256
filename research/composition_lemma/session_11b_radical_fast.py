"""
Session 11b: Fast radical extraction via einsum.

Optimization: instead of per-pair bracket via slicing, use einsum:
[I, I] computation: result[a, b, k] = sum_{i, j} u[a, i] * C[i, j, k] * u[b, j]
einsum 'ai,ijk,bj->abk' — cost O(d^2 * n^2) per ideal.

For d=55, n=264: 200M ops/ideal × 22 = 4.4B total. ~30s.
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


LOG_FILE = '/home/user/SHA-256/research/composition_lemma/session_11b_log.txt'


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
    if not vectors:
        return 0
    basis = GF2Basis(n)
    for v in vectors:
        basis.add(v.copy())
    return basis.size()


def spans_equal(basis_a, basis_b, n):
    da = span_dim(basis_a, n)
    db = span_dim(basis_b, n)
    if da != db:
        return False
    return span_dim(list(basis_a) + list(basis_b), n) == da


def compute_derived_ideal_fast(I_basis, C):
    """Fast: compute [I, I] basis via einsum.
    result[a, b, k] = sum_{i, j} u[a, i] * C[i, j, k] * u[b, j]
    """
    n = C.shape[0]
    u = np.array(I_basis, dtype=np.int32)  # (d, n)
    d = u.shape[0]
    # einsum: ai,ijk,bj->abk
    # In two steps to manage memory:
    # First: M[a, j, k] = sum_i u[a, i] * C[i, j, k] — shape (d, n, n)
    M = np.einsum('ai,ijk->ajk', u, C.astype(np.int32))
    # Second: result[a, b, k] = sum_j M[a, j, k] * u[b, j] — shape (d, d, n)
    result = np.einsum('ajk,bj->abk', M, u)
    result = result & 1
    # Flatten to list of bracket vectors (d*d in total, take upper triangle)
    derived_vectors = []
    for a in range(d):
        for b in range(a + 1, d):  # only upper triangle (anti-symmetric in char 2 — but [u,v] = [v,u] in char 2)
            v = result[a, b].astype(np.uint8)
            if v.sum() > 0:
                derived_vectors.append(v)
    return derived_vectors


def is_solvable_fast(I_basis, C, n, max_depth=20):
    """Iterate derived series."""
    current = list(I_basis)
    for depth in range(max_depth):
        d_current = span_dim(current, n)
        if d_current == 0:
            return True, depth
        derived = compute_derived_ideal_fast(current, C)
        d_derived = span_dim(derived, n)
        if d_derived == 0:
            return True, depth + 1
        if d_derived == d_current and spans_equal(current, derived, n):
            return False, depth + 1
        current = derived
    return False, max_depth


def support_bits(I_basis_coeffs, D4_matrices):
    """F_2^32 support of ideal I."""
    n = 264
    support_rows = np.zeros(32, dtype=np.uint8)
    support_cols = np.zeros(32, dtype=np.uint8)
    for v in I_basis_coeffs:
        nonzero = np.where(v == 1)[0]
        for i in nonzero:
            row_supports = D4_matrices[i].sum(axis=1) > 0
            col_supports = D4_matrices[i].sum(axis=0) > 0
            support_rows |= row_supports.astype(np.uint8)
            support_cols |= col_supports.astype(np.uint8)
    return support_rows, support_cols


def main():
    with open(LOG_FILE, 'w') as f:
        f.write('')

    log("=== Session 11b: Fast radical extraction ===\n")

    log("Step 1: Setup")
    start = time.time()
    D4 = extract_perfect_subalgebra()
    n = len(D4)
    pivot_cols, T = setup_basis_resolver(D4)
    log(f"  D^4 dim {n} ({time.time()-start:.1f}s)")

    C = np.load('/home/user/SHA-256/research/composition_lemma/struct_constants.npy')
    log(f"  Structure constants loaded ({time.time()-start:.1f}s)")

    log("\nStep 2: Load ideals from decomposition.npz")
    decomp = np.load('/home/user/SHA-256/research/composition_lemma/decomposition.npz')
    ideals_list = []
    for key in decomp.files:
        basis = decomp[key]
        d = basis.shape[0]
        ideals_list.append((key, d, [basis[i] for i in range(d)]))
    log(f"  Loaded {len(ideals_list)} ideals")

    log("\nStep 3: TRUE distinct ideals (span equality)")
    distinct_ideals = []
    for key, d, basis in ideals_list:
        is_new = True
        for j, (rep_basis, rep_d) in enumerate(distinct_ideals):
            if spans_equal(basis, rep_basis, n):
                is_new = False
                break
        if is_new:
            distinct_ideals.append((basis, d))
    log(f"  TRUE distinct ideals: {len(distinct_ideals)}")
    log(f"  Their dims: {sorted(d for _, d in distinct_ideals)}")

    log("\nStep 4: Test solvability fast")
    solvable_ideals = []
    perfect_ideals = []
    for j, (basis, d) in enumerate(distinct_ideals):
        t0 = time.time()
        solv, depth = is_solvable_fast(basis, C, n)
        elapsed = time.time() - t0
        if solv:
            solvable_ideals.append((basis, d))
            log(f"  Ideal {j} (dim {d}): SOLVABLE depth {depth} ({elapsed:.1f}s)")
        else:
            perfect_ideals.append((basis, d))
            log(f"  Ideal {j} (dim {d}): NOT solvable ({elapsed:.1f}s)")

    log(f"\n  Solvable: {len(solvable_ideals)}, non-solvable: {len(perfect_ideals)}")

    log("\nStep 5: Solvable radical R = sum of all solvable ideals")
    R_vectors = []
    for basis, d in solvable_ideals:
        R_vectors.extend(basis)
    R_dim = span_dim(R_vectors, n)
    log(f"  R dim: {R_dim}")
    log(f"  D^4 / R dim: {n - R_dim}")

    log("\nStep 6: Sanity check — R itself solvable?")
    if R_vectors:
        R_basis = []
        rb = GF2Basis(n)
        for v in R_vectors:
            added, _ = rb.add(v.copy())
            if added:
                R_basis.append(v.copy())
        R_solv, R_depth = is_solvable_fast(R_basis, C, n)
        log(f"  R solvable: {R_solv}, derived depth {R_depth}")

    log("\nStep 7: F_2^32 bit support per ideal")
    log("  Each ideal acts on F_2^32; bit support = rows + cols nonzero")
    for j, (basis, d) in enumerate(distinct_ideals):
        sup_rows, sup_cols = support_bits(basis, D4)
        rows_pos = np.where(sup_rows == 1)[0].tolist()
        cols_pos = np.where(sup_cols == 1)[0].tolist()
        log(f"  Ideal {j} (dim {d}): row_support={rows_pos[:8]}{'...' if len(rows_pos)>8 else ''}, col_support={cols_pos[:8]}{'...' if len(cols_pos)>8 else ''}")

    log(f"\nTotal wall time: {time.time()-start:.1f}s")

    np.savez('/home/user/SHA-256/research/composition_lemma/radical_analysis.npz',
             radical_dim=np.array([R_dim]),
             num_distinct=np.array([len(distinct_ideals)]),
             num_solvable=np.array([len(solvable_ideals)]),
             num_perfect=np.array([len(perfect_ideals)]))


if __name__ == "__main__":
    main()
