"""
Persistent kernel probe: is there a FIXED subspace V ⊂ F_2^{input_bits}
that lives in ker(J_r) for ALL r=1..R at a given anchor?

Our cohomology probe found: deficit = input_bits - rank(J_r) is R-invariant.
Mean deficit = const for varying R. But this is AVERAGE behavior.

Open question: at a SPECIFIC anchor W_base, do the per-round kernels
OVERLAP? Three hypotheses:

  H1 (persistent): ker(J_1) ∩ ker(J_2) ∩ ... ∩ ker(J_R) ≠ 0
      → same subspace lives in all kernels → algebraic invariant
  H2 (rotating): kernels have equal dim but different basis per round
      → structure is rotating predictably
  H3 (absorbed): kernels are independently random, intersection = 0
      → no structural handle

Method:
  1. Fix anchor (H0, W_base) at full R rounds.
  2. For each r=1..R, compute J_r: input_bits → carry-bits-at-round-r
  3. Extract ker(J_r) = left null space (bit combinations giving zero
     carry change at round r specifically)
  4. Intersect kernels across r. Dimension of intersection = H1 measure.
  5. Sample many anchors, see if intersection is stable or anchor-dependent.
"""
import numpy as np
import random, time
from mini_sha import gen_IV, gen_K, single_round, sigma_params


def extract_carries_per_round(state_in, W_r, K_r, n):
    """Same as cohomology_probe.extract_carries_single_round."""
    from cohomology_probe import extract_carries_single_round
    return extract_carries_single_round(state_in, W_r, K_r, n)


def run_rounds_with_carries(W_list, H0, R, n):
    """Returns list of (carry_vec_at_round_r, new_state) for r=0..R-1."""
    mask = (1 << n) - 1
    K = gen_K(n, R)
    state = tuple(H0)
    per_round_carries = []
    for r in range(R):
        cs = extract_carries_per_round(state, W_list[r], K[r], n)
        per_round_carries.append(cs)
        state = single_round(state, W_list[r], K[r], n)
    return per_round_carries


def jacobian_at_round(W_base, H0, r_target, n, R_total):
    """For input variation through W, compute J[r_target]:
    Row i = XOR of (carries at round r_target when flipping input bit i) vs base.
    Input bits = all n*R_total bits of W."""
    input_bits = n * R_total
    carries_base = run_rounds_with_carries(W_base, H0, R_total, n)
    cs_r_base = carries_base[r_target]
    total_carry_bits = len(cs_r_base)

    J = np.zeros((input_bits, total_carry_bits), dtype=np.uint8)
    for i in range(input_bits):
        r_w = i // n; b = i % n
        W_flip = list(W_base)
        W_flip[r_w] ^= (1 << b)
        carries_flip = run_rounds_with_carries(W_flip, H0, R_total, n)
        J[i] = carries_flip[r_target] ^ cs_r_base
    return J


def gf2_left_null_basis(mat):
    rows, cols = mat.shape
    aug = np.zeros((rows, cols + rows), dtype=np.uint8)
    aug[:, :cols] = mat & 1
    for i in range(rows):
        aug[i, cols + i] = 1

    r = 0
    for col in range(cols):
        if r >= rows: break
        pivot = None
        for rr in range(r, rows):
            if aug[rr, col] == 1:
                pivot = rr; break
        if pivot is None: continue
        if pivot != r:
            aug[[r, pivot]] = aug[[pivot, r]]
        for rr in range(rows):
            if rr != r and aug[rr, col] == 1:
                aug[rr] ^= aug[r]
        r += 1

    null = []
    for i in range(rows):
        if aug[i, :cols].sum() == 0:
            null.append(aug[i, cols:].copy())
    return null


def gf2_rank(mat):
    mat = mat.copy().astype(np.uint8) & 1
    rows, cols = mat.shape
    rank = 0
    r = 0
    for col in range(cols):
        if r >= rows: break
        pivot = None
        for rr in range(r, rows):
            if mat[rr, col] == 1:
                pivot = rr; break
        if pivot is None: continue
        if pivot != r:
            mat[[r, pivot]] = mat[[pivot, r]]
        for rr in range(rows):
            if rr != r and mat[rr, col] == 1:
                mat[rr] ^= mat[r]
        rank += 1
        r += 1
    return rank


def subspace_intersection_dim(basis_list):
    """Intersect multiple subspaces of GF(2)^n. Each basis_list[i] is
    list of row-vectors spanning V_i. Returns dim(V_0 ∩ V_1 ∩ ...).

    Method: V_1 ∩ V_2 = ker([[V_1⊥]; [V_2⊥]]) = complement of span(V_1⊥ ∪ V_2⊥).
    Simpler: find vectors in V_1 that ALSO lie in V_2.
    For V_1 ⊂ F_2^n spanned by k rows, V_2 also, we solve
      x = a·V_1^T = b·V_2^T  (both have same vector)
    which is [V_1^T | -V_2^T] [a; b] = 0, find kernel of size.
    For GF(2) -V_2 = V_2.
    """
    if not basis_list: return 0
    n_dim = len(basis_list[0][0]) if basis_list[0] else 0

    # Iteratively intersect: V_current ∩ V_i
    V_curr = basis_list[0]  # initial basis
    for V_next in basis_list[1:]:
        V_curr = _gf2_intersect_two(V_curr, V_next, n_dim)
        if not V_curr:
            return 0
    return len(V_curr)


def _gf2_intersect_two(V1, V2, n):
    """Intersection of two GF(2) subspaces given by row-bases V1, V2 ⊂ F_2^n."""
    if not V1 or not V2: return []
    k1 = len(V1); k2 = len(V2)
    # A vector v is in V_1 ∩ V_2 iff v = a·V_1 and v = b·V_2
    # so a·V_1 + b·V_2 = 0, matrix [V_1; V_2].T · [a; b] = 0
    M = np.zeros((n, k1 + k2), dtype=np.uint8)
    for i, v in enumerate(V1):
        M[:, i] = v & 1
    for j, v in enumerate(V2):
        M[:, k1 + j] = v & 1
    # Find null space of M over GF(2)
    null = gf2_left_null_basis(M.T)  # null of column-space = left null of transpose
    # For each null vector (a|b), compute a·V_1 (or b·V_2, same result)
    intersection = []
    for v in null:
        a = v[:k1]
        result = np.zeros(n, dtype=np.uint8)
        for i, coef in enumerate(a):
            if coef:
                result ^= V1[i]
        if result.sum() > 0:  # nonzero
            intersection.append(result)
    # Deduplicate via rank
    if not intersection:
        return []
    mat = np.array(intersection, dtype=np.uint8)
    rank = gf2_rank(mat)
    # Return independent subset
    if rank == 0: return []
    # Just keep first `rank` linearly independent rows via Gaussian
    kept = []
    basis_mat = np.zeros((0, n), dtype=np.uint8)
    for v in intersection:
        if not kept:
            kept.append(v)
            basis_mat = np.vstack([basis_mat, v])
        else:
            test = np.vstack([basis_mat, v])
            if gf2_rank(test) > gf2_rank(basis_mat):
                kept.append(v)
                basis_mat = test
        if len(kept) == rank: break
    return kept


def run_persistent_kernel(n, R, n_anchors=15, seed=42):
    """Main experiment.

    For each anchor, compute ker(J_r) for r=1..R.
    Measure intersection dimension = H1 score.
    If intersections are nonzero for most anchors, persistence is real."""
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R

    print(f"\n=== Persistent kernel probe: n={n}, R={R}, input={input_bits} bits ===")
    print(f"{'anchor':>6} | {'|ker_r|':>30} | {'intersection_dim':>17}")

    intersect_dims = []
    persistent_vectors_all = []

    for a in range(n_anchors):
        W_base = [random.randint(0, mask) for _ in range(R)]
        kernels = []
        kernel_dims = []
        for r_target in range(R):
            # J at this specific round
            J = jacobian_at_round(W_base, H0, r_target, n, R)
            ker = gf2_left_null_basis(J)
            kernels.append(ker)
            kernel_dims.append(len(ker))

        # Intersect all kernels
        inter_dim = subspace_intersection_dim(kernels)
        intersect_dims.append(inter_dim)

        # Collect persistent vectors
        if inter_dim > 0:
            V_curr = kernels[0]
            for V_next in kernels[1:]:
                V_curr = _gf2_intersect_two(V_curr, V_next, input_bits)
            persistent_vectors_all.append(V_curr)
        else:
            persistent_vectors_all.append([])

        print(f"{a:>6} | {kernel_dims!s:>30} | {inter_dim:>17}")

    # Statistics
    import statistics
    print(f"\n  Per-anchor intersection dims: {intersect_dims}")
    print(f"  Mean intersection dim: {statistics.mean(intersect_dims):.2f}")
    print(f"  Median: {statistics.median(intersect_dims):.1f}")
    print(f"  Std: {statistics.stdev(intersect_dims) if len(intersect_dims) > 1 else 0:.2f}")
    print(f"  Min/Max: {min(intersect_dims)}/{max(intersect_dims)}")

    # Decode persistent vectors that appear in ≥ half the anchors
    print(f"\n  === Persistent vectors across anchors ===")
    all_vecs = []
    for pv in persistent_vectors_all:
        for v in pv:
            all_vecs.append(tuple(v.tolist()))
    from collections import Counter
    counter = Counter(all_vecs)
    most_common = counter.most_common(20)
    for v_tup, cnt in most_common:
        v = np.array(v_tup)
        ones = np.where(v == 1)[0].tolist()
        decoded = [(i // n, i % n) for i in ones]  # (W_index, bit_position)
        print(f"  count={cnt}/{n_anchors}  bits={ones}  decoded={decoded}")

    return intersect_dims, persistent_vectors_all


if __name__ == "__main__":
    print("=== Persistent kernel across rounds ===")
    # Small cases for feasibility
    for n, R in [(8, 2), (8, 4), (12, 3), (16, 2), (16, 3)]:
        try:
            run_persistent_kernel(n, R, n_anchors=10)
        except Exception as e:
            print(f"ERR n={n} R={R}: {e}")
            import traceback; traceback.print_exc()
