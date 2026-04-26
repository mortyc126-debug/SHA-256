"""
Session 8: Killing form computation for L_SHA^perfect (D^4, dim 264).

Goal: K(x_i, x_j) = trace(ad_{x_i} ∘ ad_{x_j}) over F_2.
- Build basis of D^4 (264 matrices in sl_32(F_2))
- Compute structure constants C^k_{i,j}: [x_i, x_j] = Σ_k C^k_{i,j} x_k
- Build adjoint matrices ad_i (264 × 264 over F_2)
- Compute Killing form K (264 × 264, symmetric, over F_2)
- Compute rank(K) over F_2

Result interpretation:
- rank K = 264 (full): K non-degenerate → D^4 semisimple in classical sense
- rank K < 264: K degenerate → either nontrivial radical (not semisimple)
                OR char-2 pathology (semisimple algebra with degenerate K).
                Block-Wilson framework needed для разрешения.
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


def setup_basis_resolver(D4):
    """Row-reduce basis matrix to find pivot columns + transformation T.
    Returns (pivot_cols, T) such that for any v in span(D4 flattened),
    coefficients c = (v[pivot_cols] @ T) mod 2.
    """
    n = 264
    BT = np.array([m.flatten() for m in D4], dtype=np.uint8)  # 264 x 1024
    work = BT.copy()
    T = np.eye(n, dtype=np.uint8)
    pivot_cols = []
    row = 0
    for col in range(BT.shape[1]):
        if row >= n:
            break
        # Find pivot in col, search rows >= row
        pivots_in_col = np.where(work[row:, col] == 1)[0]
        if len(pivots_in_col) == 0:
            continue
        pivot = row + pivots_in_col[0]
        # Swap rows
        if pivot != row:
            work[[row, pivot]] = work[[pivot, row]]
            T[[row, pivot]] = T[[pivot, row]]
        # Eliminate this column in all other rows
        ones_mask = work[:, col] == 1
        ones_mask[row] = False
        if ones_mask.any():
            work[ones_mask] ^= work[row]
            T[ones_mask] ^= T[row]
        pivot_cols.append(col)
        row += 1

    assert row == n, f"Basis not full rank: only {row} pivots found"
    return np.array(pivot_cols), T


def compute_structure_constants(D4, pivot_cols, T):
    """Compute C[i, j, k] = coefficient of x_k in [x_i, x_j].
    Returns C (264, 264, 264) over F_2.
    """
    n = 264
    C = np.zeros((n, n, n), dtype=np.uint8)

    print("  Computing brackets and structure constants...")
    start = time.time()

    for i in range(n):
        if i % 20 == 0:
            elapsed = time.time() - start
            eta = elapsed / (i + 1) * (n - i - 1)
            print(f"    i={i}/{n}, elapsed={elapsed:.1f}s, ETA={eta:.1f}s")

        Xi = D4[i]
        # Compute all 264 brackets [x_i, x_j] for j=0..263
        brackets = np.zeros((n, 1024), dtype=np.uint8)
        for j in range(n):
            Xj = D4[j]
            B = ((Xi @ Xj) ^ (Xj @ Xi)) & 1  # commutator over F_2
            brackets[j] = B.flatten()

        # Express in basis: c = brackets[:, pivot_cols] @ T (mod 2)
        coeffs = (brackets[:, pivot_cols] @ T) & 1
        # coeffs[j, k] = C^k_{i,j} = coefficient of x_k in [x_i, x_j]
        C[i] = coeffs

    print(f"  Structure constants done in {time.time()-start:.1f}s")
    return C


def verify_structure_constants(C, D4, sample_size=20):
    """Sanity check: verify [x_i, x_j] = sum_k C[i,j,k] x_k for sampled (i,j)."""
    print("  Verifying structure constants on sample...")
    n = 264
    rng = np.random.default_rng(42)
    sampled = rng.choice(n, size=(sample_size, 2), replace=True)
    fails = 0
    for i, j in sampled:
        Xi, Xj = D4[i], D4[j]
        B_actual = ((Xi @ Xj) ^ (Xj @ Xi)) & 1
        # Reconstruct from C
        B_reconstructed = np.zeros((32, 32), dtype=np.uint8)
        for k in range(n):
            if C[i, j, k] == 1:
                B_reconstructed ^= D4[k]
        B_reconstructed &= 1
        if not np.array_equal(B_actual, B_reconstructed):
            fails += 1
    if fails == 0:
        print(f"    ✓ All {sample_size} samples match")
    else:
        print(f"    ✗ {fails}/{sample_size} samples mismatch — basis/express bug!")
    return fails == 0


def compute_killing_form(C):
    """K[i, j] = trace(ad_i @ ad_j) = sum_{k, l} C[i, l, k] * C[j, k, l] (mod 2)."""
    print("  Computing Killing form via einsum...")
    start = time.time()
    # Convert to int32 to avoid overflow during sum (264^2 = 70K terms)
    C32 = C.astype(np.int32)
    # K[i, j] = sum_{l, k} C[i, l, k] * C[j, k, l]
    K = np.einsum('ilk,jkl->ij', C32, C32)
    K = (K & 1).astype(np.uint8)
    print(f"  Killing form done in {time.time()-start:.1f}s")
    return K


def gf2_rank(M):
    """Rank of binary matrix M over F_2 via Gauss elimination."""
    A = M.copy().astype(np.uint8)
    rows, cols = A.shape
    rank = 0
    row = 0
    for col in range(cols):
        if row >= rows:
            break
        # Find pivot
        pivots = np.where(A[row:, col] == 1)[0]
        if len(pivots) == 0:
            continue
        pivot = row + pivots[0]
        if pivot != row:
            A[[row, pivot]] = A[[pivot, row]]
        # Eliminate
        ones = A[:, col] == 1
        ones[row] = False
        if ones.any():
            A[ones] ^= A[row]
        rank += 1
        row += 1
    return rank


def main():
    print("=== Session 8: Killing form computation ===\n")

    print("Step 1: Extract D^4 basis (perfect sub-algebra)")
    D4 = extract_perfect_subalgebra()
    n = len(D4)
    print(f"  dim D^4 = {n}")
    assert n == 264, f"Expected 264, got {n}"

    print("\nStep 2: Setup basis resolver (row reduction)")
    start = time.time()
    pivot_cols, T = setup_basis_resolver(D4)
    print(f"  Done in {time.time()-start:.1f}s. {len(pivot_cols)} pivot columns.")

    print("\nStep 3: Compute structure constants C[i, j, k]")
    C = compute_structure_constants(D4, pivot_cols, T)
    print(f"  C shape: {C.shape}, total nonzero entries: {C.sum()}")

    print("\nStep 4: Verify structure constants on sample")
    ok = verify_structure_constants(C, D4)
    if not ok:
        print("  ABORT: structure constants invalid")
        return

    print("\nStep 5: Symmetry check (C[i,j,k] = C[j,i,k] in F_2 since char 2)")
    diff = (C ^ C.transpose(1, 0, 2)).sum()
    print(f"  Asymmetric entries: {diff} (expect 0 over F_2 since [x,y] = [y,x] in char 2)")
    # Actually: [x, y] = xy + yx; over F_2, [x,y] = [y,x]. Yes symmetric.

    print("\nStep 6: Compute Killing form K[i, j]")
    K = compute_killing_form(C)
    print(f"  K shape: {K.shape}, sum: {K.sum()}, density: {K.sum() / K.size:.4f}")

    print("\nStep 7: Symmetry of K")
    K_sym_diff = (K ^ K.T).sum()
    print(f"  K[i,j] != K[j,i] for {K_sym_diff} entries (expect 0)")

    print("\nStep 8: Compute rank(K) over F_2")
    start = time.time()
    rank_K = gf2_rank(K)
    print(f"  rank(K) = {rank_K} / 264")
    print(f"  Done in {time.time()-start:.1f}s")

    print("\n=== RESULT ===")
    print(f"  rank(Killing form over F_2) = {rank_K}")
    print(f"  Total dim D^4 = 264")
    print(f"  Radical dim (dim - rank) = {264 - rank_K}")

    if rank_K == 264:
        print("\n  ✓ Killing form NON-DEGENERATE over F_2")
        print("    → D^4 is SEMISIMPLE in classical Cartan-Killing sense")
        print("    → Conjecture 21.1 confirmed STRONGLY")
    elif rank_K == 0:
        print("\n  ✗ Killing form IDENTICALLY ZERO")
        print("    → Char-2 pathology; D^4 may still be 'restricted semisimple'")
        print("    → Need Block-Wilson framework, not classical")
    else:
        print(f"\n  ⚠ Killing form DEGENERATE (rank {rank_K} < 264)")
        print(f"    → Either nontrivial radical of dim {264 - rank_K}")
        print(f"    → OR char-2 pathology — restricted Lie framework needed")

    # Save K for later analysis
    np.save('/home/user/SHA-256/research/composition_lemma/killing_form.npy', K)
    print(f"\n  K saved to killing_form.npy")


if __name__ == "__main__":
    main()
