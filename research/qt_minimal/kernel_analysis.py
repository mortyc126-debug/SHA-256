"""
Second-stage probe: identify THE SPECIFIC kernel directions of the carry Jacobian.

From cohomology_probe.py we found:
  Local Jacobian of carry map (W-flip → carry-change) has stable deficit ≈ 3
  for n=16 across all R. Deficit ≈ n/8 + 1 pattern.

Now: what ARE these 3 linearly-dependent flip directions?
If we can describe them algebraically, they'd be a SHA-256 cohomology signature.

Method:
  1. Build Jacobian J (input_bits × total_carry_bits) at a random anchor W_base
  2. Compute left null space of J over GF(2): kernel = {v ∈ F_2^{input_bits} : v·J = 0}
  3. Describe kernel basis: which input bits combine to give zero carry effect?
  4. Stability: repeat at many anchors — is kernel fixed (structural) or anchor-dependent?
"""
import numpy as np
import random
from cohomology_probe import (compute_full_carries_trace, gf2_rank,
                               extract_carries_single_round)
from mini_sha import gen_IV


def gf2_left_null_basis(mat):
    """Find basis of left null space over GF(2).
    mat: rows x cols. Returns list of row-vectors v such that v @ mat = 0 mod 2."""
    rows, cols = mat.shape
    # Augment mat with identity: [mat | I].  After Gaussian on rows, rows that
    # become all-zero in the left part have identity-combo on the right.
    aug = np.zeros((rows, cols + rows), dtype=np.uint8)
    aug[:, :cols] = mat & 1
    for i in range(rows):
        aug[i, cols + i] = 1

    r = 0
    for col in range(cols):
        if r >= rows:
            break
        pivot = None
        for rr in range(r, rows):
            if aug[rr, col] == 1:
                pivot = rr
                break
        if pivot is None:
            continue
        if pivot != r:
            aug[[r, pivot]] = aug[[pivot, r]]
        for rr in range(rows):
            if rr != r and aug[rr, col] == 1:
                aug[rr] ^= aug[r]
        r += 1

    # Rows with all zeros in left part → their right part is a null vector
    null = []
    for i in range(rows):
        if aug[i, :cols].sum() == 0:
            null.append(aug[i, cols:].copy())
    return null


def compute_jacobian(W_base, H0, R, n):
    mask = (1 << n) - 1
    cs_base = compute_full_carries_trace(W_base, H0, R, n)
    input_bits = n * R
    total_bits = len(cs_base)
    J = np.zeros((input_bits, total_bits), dtype=np.uint8)
    for i in range(input_bits):
        r = i // n; b = i % n
        W_flip = list(W_base)
        W_flip[r] ^= (1 << b)
        cs_flip = compute_full_carries_trace(W_flip, H0, R, n)
        J[i] = cs_flip ^ cs_base
    return J


def analyze(n, R, n_anchors=30, seed=42):
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R
    print(f"\n=== n={n} R={R}  (input {input_bits} bits) ===")

    all_kernels = []
    for a in range(n_anchors):
        W_base = [random.randint(0, mask) for _ in range(R)]
        J = compute_jacobian(W_base, H0, R, n)
        null = gf2_left_null_basis(J)
        all_kernels.append(null)
        rank = input_bits - len(null)
        if a < 3:  # print first few anchors in detail
            print(f"  anchor #{a}: J rank = {rank}, kernel dim = {len(null)}")
            for ki, v in enumerate(null):
                # decode positions
                ones = np.where(v == 1)[0].tolist()
                # interpret: bit i = W[i//n] bit (i%n)
                decoded = [(i // n, i % n) for i in ones]
                print(f"    kernel[{ki}]: bits {ones} = flip {decoded}")

    # Stability: is the kernel DIRECTION fixed across anchors?
    # Turn each kernel into a set of basis matrices, compute intersection.
    # Simpler: for each anchor compute the rank of the concatenation of kernel vectors.
    # If kernel is stable, all n_anchors * k vectors span only k dimensions.
    kdims = [len(k) for k in all_kernels]
    print(f"  kernel dim across anchors: min={min(kdims)} max={max(kdims)} "
          f"unique={sorted(set(kdims))}")

    # Are the kernels ALIGNED?
    first_dim = kdims[0]
    if all(k == first_dim for k in kdims):
        # stack all kernel bases into one big matrix
        stacked = np.vstack([np.array(k) for k in all_kernels if len(k) == first_dim])
        combined_rank = gf2_rank(stacked)
        print(f"  combined rank of {n_anchors}*{first_dim}={len(stacked)} rows: "
              f"{combined_rank}  (if structural: ~{first_dim})")
    else:
        print(f"  kernel dim VARIES across anchors — less structural")

    return all_kernels


if __name__ == "__main__":
    # Key test: deficit as function of (n, R)
    for n in [8, 12, 16, 20, 24]:
        for R in [1, 2, 4]:
            try:
                analyze(n, R, n_anchors=10)
            except Exception as e:
                print(f"ERR n={n} R={R}: {e}")
