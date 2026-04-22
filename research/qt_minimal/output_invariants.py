"""
Test: do persistent kernel vectors (carry-preserving flips) also preserve
the full round-function OUTPUT (state_{r+1})?

If v ∈ ker(J_carry) AND v ∈ ker(J_output) → v is a TRUE round-function
invariant (flipping these bits changes nothing).

If v ∈ ker(J_carry) but NOT ker(J_output) → flips change output but not
carries → weaker handle, but could be used as probabilistic distinguisher.

This is genuinely new: methodology measures carry structure OR output
structure separately, not the overlap.
"""
import numpy as np
import random
from mini_sha import gen_IV, gen_K, single_round, sigma_params
from persistent_kernel import jacobian_at_round, gf2_left_null_basis, gf2_rank


def output_jacobian(W_base, H0, n, R):
    """J_output[i] = state_R XOR state_R_flipped_at_bit_i of W.
    Rows = input_bits, cols = 8*n (8 registers × n bits)."""
    mask = (1 << n) - 1
    K = gen_K(n, R)

    def forward(W):
        state = tuple(H0)
        for r in range(R):
            state = single_round(state, W[r], K[r], n)
        return state

    state_base = forward(W_base)
    state_vec_base = state_to_bits(state_base, n)

    input_bits = n * R
    J = np.zeros((input_bits, 8 * n), dtype=np.uint8)
    for i in range(input_bits):
        r_w = i // n; b = i % n
        W_flip = list(W_base)
        W_flip[r_w] ^= (1 << b)
        state_flip = forward(W_flip)
        J[i] = state_vec_base ^ state_to_bits(state_flip, n)
    return J


def state_to_bits(state, n):
    """Flatten state tuple to bit vector (8n bits)."""
    out = np.zeros(8 * n, dtype=np.uint8)
    for reg in range(8):
        val = state[reg]
        for b in range(n):
            out[reg * n + b] = (val >> b) & 1
    return out


def test_invariants(n, R, n_anchors=15, seed=42):
    """For each anchor:
      1. Compute carry Jacobian kernel
      2. For each kernel vector v, apply flip, check if output state changes
      3. Report: how many 'total invariants' (flip nothing) vs 'carry-only invariants'.
    """
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R

    print(f"\n=== Output-invariants test: n={n}, R={R} ===")
    total_invariants = 0
    carry_only_invariants = 0
    found_persistent_total = []  # vectors that preserve BOTH carry and output

    for a in range(n_anchors):
        W_base = [random.randint(0, mask) for _ in range(R)]

        # Combined carry Jacobian (stacked across all rounds)
        from cohomology_probe import compute_full_carries_trace
        cs_base = compute_full_carries_trace(W_base, H0, R, n)
        J_carry = np.zeros((input_bits, len(cs_base)), dtype=np.uint8)
        for i in range(input_bits):
            r_w = i // n; b = i % n
            W_flip = list(W_base)
            W_flip[r_w] ^= (1 << b)
            cs_flip = compute_full_carries_trace(W_flip, H0, R, n)
            J_carry[i] = cs_flip ^ cs_base

        # Output Jacobian
        J_out = output_jacobian(W_base, H0, n, R)

        # Kernel of carry Jacobian
        ker_carry = gf2_left_null_basis(J_carry)

        # For each carry-kernel vector v, check: does v·J_out = 0?
        a_total = 0
        a_carry_only = 0
        for v in ker_carry:
            v_J_out = np.zeros(8*n, dtype=np.uint8)
            for i in range(input_bits):
                if v[i]:
                    v_J_out ^= J_out[i]
            if v_J_out.sum() == 0:
                a_total += 1
                found_persistent_total.append(tuple(v.tolist()))
            else:
                a_carry_only += 1

        total_invariants += a_total
        carry_only_invariants += a_carry_only
        print(f"  anchor {a}: ker(J_carry) dim={len(ker_carry)}  "
              f"TOTAL invariant={a_total}  carry-only={a_carry_only}")

    print(f"\n  Summary:")
    print(f"    Total invariants (flip → no change anywhere): {total_invariants} / {sum(1 for _ in range(n_anchors))} anchors")
    print(f"    Carry-only invariants (flip → carry unchanged but output DOES change): {carry_only_invariants}")

    # Show the ones that are FULL invariants
    if found_persistent_total:
        from collections import Counter
        counter = Counter(found_persistent_total)
        print(f"\n  Total-invariant vectors (appear in persistent_total across anchors):")
        for v_tup, cnt in counter.most_common(10):
            v = np.array(v_tup)
            ones = np.where(v == 1)[0].tolist()
            decoded = [(i // n, i % n) for i in ones]  # (W_index, bit_pos)
            print(f"    count={cnt}/{n_anchors}  bits={ones}  decoded={decoded}")
    else:
        print(f"  NO full invariants found — all kernel vectors affect output.")


if __name__ == "__main__":
    print("=== Total round-function invariants from carry kernel ===")
    for n in [8, 12, 16]:
        for R in [1, 2, 3]:
            try:
                test_invariants(n, R, n_anchors=12)
            except Exception as e:
                print(f"ERR n={n} R={R}: {e}")
                import traceback; traceback.print_exc()
