"""
Test: for v in ker(J_carry), is v·J_out state-INDEPENDENT?

Motivation: carry-kernel vectors preserve carries. If they also produce
state-INDEPENDENT output change (v·J_out = fixed const regardless of W_base),
that's a STRUCTURAL linear invariant:
    "flip input bits v  →  output XOR'd by a fixed constant"
independent of current state. Algebraic handle.

If output change IS state-dependent, it's less useful (still carry-preserving
differential, but needs full W knowledge).

Method:
  1. Sample W_base A, compute ker(J_carry[A])
  2. Sample W_base B, compute ker(J_carry[B])
  3. Intersect kernels to get shared v's
  4. For each v in intersection, compute v·J_out[A] and v·J_out[B]
  5. Compare: same result = linear invariant; different = state-dep
"""
import numpy as np
import random
from mini_sha import gen_IV, gen_K, single_round
from output_invariants import output_jacobian, state_to_bits
from cohomology_probe import compute_full_carries_trace
from persistent_kernel import gf2_left_null_basis, gf2_rank, _gf2_intersect_two


def carry_jacobian_full(W_base, H0, n, R):
    """Combined carry Jacobian (all rounds)."""
    cs_base = compute_full_carries_trace(W_base, H0, R, n)
    input_bits = n * R
    J = np.zeros((input_bits, len(cs_base)), dtype=np.uint8)
    for i in range(input_bits):
        r_w = i // n; b = i % n
        W_flip = list(W_base)
        W_flip[r_w] ^= (1 << b)
        cs_flip = compute_full_carries_trace(W_flip, H0, R, n)
        J[i] = cs_flip ^ cs_base
    return J


def run_test(n, R, n_pairs=30, seed=42):
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R

    print(f"\n=== Linear invariant test: n={n} R={R} ===")
    shared_count = 0
    state_indep_count = 0
    state_dep_count = 0
    invariant_examples = []

    for trial in range(n_pairs):
        W_A = [random.randint(0, mask) for _ in range(R)]
        W_B = [random.randint(0, mask) for _ in range(R)]

        J_c_A = carry_jacobian_full(W_A, H0, n, R)
        J_c_B = carry_jacobian_full(W_B, H0, n, R)
        ker_A = gf2_left_null_basis(J_c_A)
        ker_B = gf2_left_null_basis(J_c_B)

        # Intersect
        shared = _gf2_intersect_two(ker_A, ker_B, input_bits)
        if not shared:
            continue
        shared_count += len(shared)

        # For each shared kernel vector, compute output change at A and B
        J_o_A = output_jacobian(W_A, H0, n, R)
        J_o_B = output_jacobian(W_B, H0, n, R)

        for v in shared:
            out_A = np.zeros(8 * n, dtype=np.uint8)
            out_B = np.zeros(8 * n, dtype=np.uint8)
            for i in range(input_bits):
                if v[i]:
                    out_A ^= J_o_A[i]
                    out_B ^= J_o_B[i]
            if np.array_equal(out_A, out_B):
                state_indep_count += 1
                ones = np.where(v == 1)[0].tolist()
                out_diff_pos = np.where(out_A == 1)[0].tolist()
                invariant_examples.append((trial, ones, out_diff_pos))
            else:
                state_dep_count += 1

    print(f"  shared kernel vectors (A ∩ B): {shared_count}")
    print(f"  → state-INDEPENDENT (fixed output change): {state_indep_count}")
    print(f"  → state-DEPENDENT (output change varies with W): {state_dep_count}")

    if invariant_examples:
        print(f"\n  === State-invariant patterns (first 10) ===")
        for tr, ones, out_diff in invariant_examples[:10]:
            input_dec = [(i // n, i % n) for i in ones]
            output_dec = [(j // n, j % n) for j in out_diff]
            print(f"    trial #{tr}: flip W-bits {input_dec}  →  output bits {output_dec}")

    return shared_count, state_indep_count, state_dep_count


if __name__ == "__main__":
    print("=== Structural linear invariants test ===")
    for n, R in [(8, 1), (8, 2), (12, 2), (16, 1), (16, 2)]:
        try:
            run_test(n, R, n_pairs=30)
        except Exception as e:
            print(f"ERR n={n} R={R}: {e}")
            import traceback; traceback.print_exc()
