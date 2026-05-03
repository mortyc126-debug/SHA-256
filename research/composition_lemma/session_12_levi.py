"""
Session 12: Levi decomposition, semisimple part characterization, full bit support.

After Session 11b:
- D^4 dim 264 = R (solvable radical, 145) + Q (quotient, 119)
- All 22 minimal proper ideals are solvable (depth 1-2)
- R itself solvable depth 2

Tasks:
1. Print FULL bit support per ideal (32 bits, fix print truncation)
2. Find Levi complement L: subspace V such that D^4 = R ⊕ V (vector space)
3. Test if L is sub-algebra (Levi splitting): [L, L] ⊆ L?
   - If yes: D^4 = R ⋊ L semidirect product
   - L is candidate semisimple Lie algebra
4. Test if L is simple, semisimple, or has further structure
5. Compute bit support of L action
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


LOG_FILE = '/home/user/SHA-256/research/composition_lemma/session_12_log.txt'


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


def get_R_basis(decomp_file, n):
    """Build R basis from all 22 ideals (sum)."""
    decomp = np.load(decomp_file)
    R_basis = GF2Basis(n)
    for key in decomp.files:
        basis = decomp[key]
        for i in range(basis.shape[0]):
            R_basis.add(basis[i].copy())
    return R_basis


def find_levi_complement(R_basis, n):
    """Find a vector subspace V ⊆ D^4 with D^4 = R ⊕ V, dim V = n - dim R = 119.
    Greedy: take standard basis vectors (e_0, e_1, ...) not in R."""
    R_pivots = set(R_basis.pivots)  # positions where R has leading 1s after reduction
    # Vectors NOT covered: those with leading bit in non-pivot position
    # Actually: V = quotient representatives. Take standard basis e_i for i NOT in R_pivots.
    L_basis = []
    for i in range(n):
        if i not in R_pivots:
            v = np.zeros(n, dtype=np.uint8)
            v[i] = 1
            L_basis.append(v)
    return L_basis


def compute_brackets_set(basis_a, basis_b, C):
    """Compute [span(a), span(b)] basis using einsum."""
    n = C.shape[0]
    u = np.array(basis_a, dtype=np.int32)
    v = np.array(basis_b, dtype=np.int32)
    # result[i, j, k] = sum_a sum_b u[i, a] * v[j, b] * C[a, b, k]
    M = np.einsum('ia,abk->ibk', u, C.astype(np.int32))  # (|u|, n, n)
    result = np.einsum('ibk,jb->ijk', M, v)  # (|u|, |v|, n)
    result = result & 1
    out = []
    for i in range(result.shape[0]):
        for j in range(result.shape[1]):
            v_ij = result[i, j].astype(np.uint8)
            if v_ij.sum() > 0:
                out.append(v_ij)
    return out


def test_subalgebra(L_basis, C, n):
    """Test if [L, L] ⊆ L."""
    brackets = compute_brackets_set(L_basis, L_basis, C)
    if not brackets:
        return True, 0  # trivially closed
    # Check if all brackets are in span of L
    L_check = GF2Basis(n)
    for v in L_basis:
        L_check.add(v.copy())
    L_dim = L_check.size()
    out_count = 0
    for b in brackets:
        added, _ = L_check.add(b.copy())
        if added:
            out_count += 1
    if out_count == 0:
        return True, len(brackets)
    return False, out_count


def project_to_L_mod_R(brackets, R_basis_mat, n):
    """Project brackets to D^4/R. Returns coefficient vectors mod R.
    R_basis_mat: rows = R basis vectors after reduction.
    """
    out = []
    for b in brackets:
        # Reduce b mod R: subtract R basis vectors as needed
        v = b.copy()
        for r in R_basis_mat:
            # If v has a 1 at r's pivot position, XOR
            pos = np.where(r == 1)[0]
            if len(pos) > 0 and v[pos[0]] == 1:
                v ^= r
        out.append(v)
    return out


def support_bits_full(I_basis_coeffs, D4_matrices):
    """Full F_2^32 bit support."""
    support_rows = np.zeros(32, dtype=np.uint8)
    support_cols = np.zeros(32, dtype=np.uint8)
    for v in I_basis_coeffs:
        nonzero = np.where(v == 1)[0]
        for i in nonzero:
            support_rows |= (D4_matrices[i].sum(axis=1) > 0).astype(np.uint8)
            support_cols |= (D4_matrices[i].sum(axis=0) > 0).astype(np.uint8)
    return support_rows, support_cols


def main():
    with open(LOG_FILE, 'w') as f:
        f.write('')

    log("=== Session 12: Levi decomposition + bit support ===\n")

    log("Step 1: Setup")
    start = time.time()
    D4 = extract_perfect_subalgebra()
    n = len(D4)
    pivot_cols, T = setup_basis_resolver(D4)
    C = np.load('/home/user/SHA-256/research/composition_lemma/struct_constants.npy')
    log(f"  D^4 dim {n} ({time.time()-start:.1f}s)")

    log("\nStep 2: Reconstruct R basis (solvable radical)")
    R_basis = get_R_basis('/home/user/SHA-256/research/composition_lemma/decomposition.npz', n)
    R_dim = R_basis.size()
    log(f"  R dim: {R_dim}")
    R_basis_vecs = R_basis.basis  # reduced basis vectors

    log("\nStep 3: Find Levi complement (vector space basis for D^4/R)")
    L_basis = find_levi_complement(R_basis, n)
    log(f"  Levi complement dim: {len(L_basis)}")

    log("\nStep 4: Verify D^4 = R ⊕ V (direct sum vector space)")
    combined = GF2Basis(n)
    for v in R_basis_vecs:
        combined.add(v.copy())
    for v in L_basis:
        combined.add(v.copy())
    log(f"  R + L span dim: {combined.size()}")
    if combined.size() == n:
        log(f"  ✓ R ⊕ L = D^4 (vector space)")
    else:
        log(f"  ✗ Doesn't span D^4 — ERROR")
        return

    log("\nStep 5: Test if L is sub-algebra (Levi splitting in algebra sense)")
    is_sub, out_count = test_subalgebra(L_basis, C, n)
    if is_sub:
        log(f"  ✓ [L, L] ⊆ L. L is sub-algebra of dim {len(L_basis)}.")
        log(f"    → True Levi decomposition: D^4 = R ⋊ L (semidirect product)")
    else:
        log(f"  ✗ [L, L] ⊄ L. {out_count} brackets escape L.")
        log(f"    → No clean Levi splitting on this basis. Standard char-2 phenomenon.")
        log(f"    → BUT: D^4 / R is still well-defined as quotient algebra.")

    log("\nStep 6: Compute D^4 / R structure via projection")
    R_mat = np.array(R_basis_vecs)  # (145, 264)
    L_arr = np.array(L_basis)  # (119, 264)

    # Compute brackets [L, L] and project mod R
    log("  Computing brackets [L, L]...")
    LL_brackets = compute_brackets_set(L_basis, L_basis, C)
    log(f"  Total nonzero brackets: {len(LL_brackets)}")

    # Project to D^4/R
    log("  Projecting brackets mod R...")
    LL_projected = project_to_L_mod_R(LL_brackets, R_mat, n)
    LL_proj_nonzero = [v for v in LL_projected if v.sum() > 0]
    log(f"  Nonzero brackets in quotient: {len(LL_proj_nonzero)}")

    # Span
    LL_span_dim = span_dim(LL_proj_nonzero, n)
    log(f"  [L, L] mod R span dim: {LL_span_dim}")
    log(f"  L mod R dim: {len(L_basis)}")

    if LL_span_dim == 0:
        log("  → D^4/R is ABELIAN — entirely in radical sense. Strange.")
    elif LL_span_dim == len(L_basis):
        log("  → D^4/R is PERFECT (= [D^4/R, D^4/R]) — typical of semisimple")

    log("\nStep 7: Test solvability of D^4/R (in quotient)")
    # Iterate derived series in quotient
    current = LL_proj_nonzero
    for depth in range(10):
        d_curr = span_dim(current, n)
        if d_curr == 0:
            log(f"  D^4/R derived → 0 at depth {depth + 1} → SOLVABLE")
            break
        next_brackets = compute_brackets_set(current, current, C)
        next_proj = project_to_L_mod_R(next_brackets, R_mat, n)
        next_nonzero = [v for v in next_proj if v.sum() > 0]
        d_next = span_dim(next_nonzero, n)
        log(f"    depth {depth+1}: dim {d_next}")
        if d_next == d_curr and spans_equal(current, next_nonzero, n):
            log(f"    Stabilized at dim {d_next} — D^4/R has perfect part")
            break
        current = next_nonzero

    log("\nStep 8: Full bit support per ideal (all 32 bits)")
    decomp = np.load('/home/user/SHA-256/research/composition_lemma/decomposition.npz')
    log("  Each ideal acts on F_2^32; rows + cols of nonzero positions:")

    distinct_supports = {}
    for j, key in enumerate(decomp.files):
        basis = decomp[key]
        basis_list = [basis[i] for i in range(basis.shape[0])]
        sup_rows, sup_cols = support_bits_full(basis_list, D4)
        rows_pos = np.where(sup_rows == 1)[0]
        cols_pos = np.where(sup_cols == 1)[0]
        d = basis.shape[0]
        log(f"    Ideal {j} (dim {d}): rows={rows_pos.tolist()}")
        log(f"                          cols={cols_pos.tolist()}")
        sig = (tuple(rows_pos), tuple(cols_pos))
        if sig not in distinct_supports:
            distinct_supports[sig] = []
        distinct_supports[sig].append(j)

    log(f"\n  Distinct support patterns: {len(distinct_supports)}")
    for (rows, cols), ideals in distinct_supports.items():
        log(f"    Pattern: rows {list(rows)}, cols {list(cols)} → ideals {ideals}")

    log("\nStep 9: Bit support of R (full radical) and L (Levi complement)")
    sup_R_r, sup_R_c = support_bits_full(R_basis_vecs, D4)
    sup_L_r, sup_L_c = support_bits_full(L_basis, D4)
    log(f"  R: rows={np.where(sup_R_r==1)[0].tolist()}")
    log(f"     cols={np.where(sup_R_c==1)[0].tolist()}")
    log(f"  L: rows={np.where(sup_L_r==1)[0].tolist()}")
    log(f"     cols={np.where(sup_L_c==1)[0].tolist()}")

    log(f"\nTotal wall time: {time.time()-start:.1f}s")


if __name__ == "__main__":
    main()
