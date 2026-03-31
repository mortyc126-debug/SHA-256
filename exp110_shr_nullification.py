#!/usr/bin/env python3
"""
EXP 110: SHR Nullification — Exploiting Schedule's Weak Point

From exp109: SHR is SHA-256's PRIMARY equivariance defense.
SHR_3 and SHR_10 destroy MSBs in schedule computation.

KEY INSIGHT: SHR_n(x) = ROTR_n(x) when top n bits of x are ZERO.
If we can make schedule words have zero MSBs → SHR = ROTR → equivariant!

STRATEGY:
1. Choose message words W[0..15] such that sig0/sig1 inputs have zero MSBs
2. This constrains the message but may leave enough freedom
3. Measure: how many message bits remain free after SHR-nullification?
4. If enough free bits remain → search collision in equivariant subspace

ANALYSIS:
- sig0(W[t-15]) uses SHR_3: need top 3 bits of W[t-15] = 0
  → For t=16: need W[1] top 3 = 0 → costs 3 bits of W[1]
  → For t=17: need W[2] top 3 = 0 → costs 3 bits of W[2]
  etc.
- sig1(W[t-2]) uses SHR_10: need top 10 bits of W[t-2] = 0
  → For t=16: need W[14] top 10 = 0 → costs 10 bits of W[14]
  → For t=17: need W[15] top 10 = 0 → costs 10 bits of W[15]
  → For t=18: need W[16] top 10 = 0 → W[16] is COMPUTED!
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_shr_null_cost():
    """How many message bits must be constrained for SHR nullification?"""
    print(f"\n--- SHR NULLIFICATION COST ---")

    # For schedule words W[16..63]:
    # W[t] = sig1(W[t-2]) + W[t-7] + sig0(W[t-15]) + W[t-16]
    #
    # sig0(x) = ROTR_7(x) ^ ROTR_18(x) ^ SHR_3(x)
    # SHR_3(x) = ROTR_3(x) when x[31:29] = 000
    # → need top 3 bits of W[t-15] = 0
    #
    # sig1(x) = ROTR_17(x) ^ ROTR_19(x) ^ SHR_10(x)
    # SHR_10(x) = ROTR_10(x) when x[31:22] = 0000000000
    # → need top 10 bits of W[t-2] = 0

    # Which message words need constraints?
    sig0_targets = {}  # t-15 → which t uses it
    sig1_targets = {}  # t-2 → which t uses it

    for t in range(16, 64):
        s0_input = t - 15  # sig0 input
        s1_input = t - 2   # sig1 input

        if s0_input not in sig0_targets:
            sig0_targets[s0_input] = []
        sig0_targets[s0_input].append(t)

        if s1_input not in sig1_targets:
            sig1_targets[s1_input] = []
        sig1_targets[s1_input].append(t)

    print(f"\nsig0 targets (need top 3 bits = 0):")
    free_cost = 0
    for w in sorted(sig0_targets.keys()):
        status = "FREE" if w < 16 else "COMPUTED"
        if w < 16:
            free_cost += 3
        print(f"  W[{w:>2}] ({status}): used by W[{', '.join(str(t) for t in sig0_targets[w])}]")

    print(f"\nsig1 targets (need top 10 bits = 0):")
    for w in sorted(sig1_targets.keys()):
        status = "FREE" if w < 16 else "COMPUTED"
        if w < 16:
            free_cost += 10
        print(f"  W[{w:>2}] ({status}): used by W[{', '.join(str(t) for t in sig1_targets[w])}]")

    # Free message words: W[0..15] = 512 bits
    # sig0 constrains: W[1..15] top 3 = 0 → 15 words × 3 bits = 45 bits
    # sig1 constrains: W[14, 15] top 10 = 0 → 2 words × 10 bits = 20 bits
    # Overlap: W[14,15] both sig0 and sig1 → top 10 already covers top 3

    # Count precisely
    constraints = {}  # word → bits constrained (as set of bit positions)
    for w in range(16):
        constraints[w] = set()

    # sig0: need top 3 bits = 0 for W[1..15]
    for w in range(1, 16):
        if w in sig0_targets:
            constraints[w].update({29, 30, 31})

    # sig1: need top 10 bits = 0 for W[14, 15]
    for w in range(16):
        if w in sig1_targets and w < 16:
            constraints[w].update(range(22, 32))

    total_constrained = sum(len(c) for c in constraints.values())
    total_free = 512 - total_constrained

    print(f"\nSummary (FREE message words only):")
    for w in range(16):
        if constraints[w]:
            print(f"  W[{w:>2}]: {len(constraints[w])} bits constrained → {32-len(constraints[w])} free")

    print(f"\nTotal constrained: {total_constrained} bits")
    print(f"Total free: {total_free} bits")
    print(f"Birthday on free space: 2^{total_free//2}")

    return total_free

def test_computed_word_shr(N=5000):
    """For COMPUTED words W[16+]: can SHR be nullified?
    Need top bits of W[t] = 0 for t ≥ 16.
    This is a CONSTRAINT on W[0..15]."""
    print(f"\n--- COMPUTED WORD SHR NULLIFICATION (N={N}) ---")

    # sig1 needs W[t-2] top 10 = 0 for t ≥ 18
    # W[16] top 10 = 0: is this achievable?

    # W[16] = sig1(W[14]) + W[9] + sig0(W[1]) + W[0]
    # Each term is ~32 bits. Sum has MSBs that depend on carry.
    # Hard to force top 10 = 0 without specific constraints.

    # Measure: what fraction of W[16] have top 10 = 0?
    top10_zero = 0
    for _ in range(N):
        W16_msg = random_w16()
        W = schedule(W16_msg)
        if (W[16] >> 22) == 0:
            top10_zero += 1

    p_natural = top10_zero / N
    print(f"P(W[16] top 10 = 0, random msg): {p_natural:.6f} (expected: 2^-10 = {2**-10:.6f})")

    # With constrained W[14] (top 10 = 0) and W[1] (top 3 = 0):
    top10_constrained = 0
    for _ in range(N):
        W16_msg = random_w16()
        W16_msg[1] &= (MASK >> 3)     # top 3 of W[1] = 0
        W16_msg[14] &= (MASK >> 10)   # top 10 of W[14] = 0
        W = schedule(W16_msg)
        if (W[16] >> 22) == 0:
            top10_constrained += 1

    p_constrained = top10_constrained / N
    print(f"P(W[16] top 10 = 0, constrained): {p_constrained:.6f}")

    # How about W[17..20]?
    print(f"\nTop-10-zero probability for computed words:")
    for t in range(16, 25):
        count = 0
        for _ in range(N):
            W16_msg = random_w16()
            # Apply all free-word constraints
            for w in range(1, 16):
                W16_msg[w] &= (MASK >> 3)  # top 3 = 0
            W16_msg[14] &= (MASK >> 10)
            W16_msg[15] &= (MASK >> 10)
            W = schedule(W16_msg)
            if (W[t] >> 22) == 0:
                count += 1
        print(f"  W[{t}] top 10 = 0: {count/N:.6f} (need ~1.0)")

    print(f"\n  Computed words do NOT have zero MSBs naturally.")
    print(f"  SHR nullification only works for first 2 schedule steps.")

def test_partial_equivariance(N=1000):
    """Even partial SHR nullification helps: first few rounds equivariant."""
    print(f"\n--- PARTIAL EQUIVARIANCE (N={N}) ---")

    # If W[14,15] have top 10=0 and W[1..15] have top 3=0:
    # W[16], W[17] schedule words computed with sig0/sig1 ≈ ROTR
    # But W[18+] lose equivariance as computed words don't have zero MSBs

    # How many rounds remain approximately equivariant?
    def constrained_msg():
        W16_msg = random_w16()
        for w in range(1, 16):
            W16_msg[w] &= (MASK >> 3)
        W16_msg[14] &= (MASK >> 10)
        W16_msg[15] &= (MASK >> 10)
        return W16_msg

    # Compare schedule with SHR vs ROTR for constrained messages
    for t in range(16, 30):
        shr_vs_rotr = []
        for _ in range(N):
            W16_msg = constrained_msg()
            W_real = schedule(W16_msg)

            # ROTR schedule
            def sig0_rotr(x):
                return rotr(x, 7) ^ rotr(x, 18) ^ rotr(x, 3)
            def sig1_rotr(x):
                return rotr(x, 17) ^ rotr(x, 19) ^ rotr(x, 10)

            W_rotr = list(W16_msg) + [0] * 48
            for s in range(16, t+1):
                W_rotr[s] = (sig1_rotr(W_rotr[s-2]) + W_rotr[s-7] +
                            sig0_rotr(W_rotr[s-15]) + W_rotr[s-16]) & MASK

            diff = hw(W_real[t] ^ W_rotr[t])
            shr_vs_rotr.append(diff)

        avg = np.mean(shr_vs_rotr)
        exact = np.sum(np.array(shr_vs_rotr) == 0) / N
        print(f"  W[{t:>2}]: SHR vs ROTR diff = {avg:.3f}, exact_match = {exact:.4f}")

def test_schedule_linearity(N=3000):
    """The schedule IS linear over integers (mod 2^32).
    Can we exploit this linearity for collision?"""
    print(f"\n--- SCHEDULE LINEARITY (N={N}) ---")

    # W[t] = sig1(W[t-2]) + W[t-7] + sig0(W[t-15]) + W[t-16]
    # This is LINEAR in the W[i] values (each sig is linear in GF(2)
    # but NOT linear over integers due to carry).

    # Over GF(2): sig0(x) = x ⊕ ROTR_7(x) ⊕ ROTR_18(x) ⊕ SHR_3(x)
    # which IS linear.

    # So schedule is: W[t] = L_0(W[t-2]) + W[t-7] + L_1(W[t-15]) + W[t-16]
    # where L_0 = sig1 and L_1 = sig0 are GF(2)-linear but + is mod 2^32.

    # For COLLISION: need W(M) and W(M') to produce same hash.
    # Schedule diff: ΔW[t] = sig1(ΔW[t-2]) + ΔW[t-7] + sig0(ΔW[t-15]) + ΔW[t-16]
    # (mod 2^32, WITH carry effects)

    # Test: is the schedule difference approximately GF(2)-linear?
    diffs_linear = []; diffs_nonlinear = []
    for _ in range(N):
        W1 = random_w16(); W2 = random_w16()
        S1 = schedule(W1); S2 = schedule(W2)

        # XOR difference of schedules
        dW_xor = [S1[t] ^ S2[t] for t in range(64)]

        # "Expected" XOR diff if schedule were GF(2)-linear
        # sig0 and sig1 ARE GF(2)-linear
        dM = [W1[i] ^ W2[i] for i in range(16)]
        dW_expected = list(dM) + [0] * 48
        for t in range(16, 64):
            dW_expected[t] = (sig1(dW_expected[t-2]) ^
                             dW_expected[t-7] ^
                             sig0(dW_expected[t-15]) ^
                             dW_expected[t-16])

        # Compare
        for t in range(16, 64):
            diff = hw(dW_xor[t] ^ dW_expected[t])
            if t < 24:
                diffs_linear.append(diff)
            else:
                diffs_nonlinear.append(diff)

    dl = np.array(diffs_linear); dn = np.array(diffs_nonlinear)
    print(f"Schedule XOR-diff vs GF(2)-linear prediction:")
    print(f"  Early (t=16-23): mean error = {dl.mean():.3f} bits (0 = perfect)")
    print(f"  Late  (t=24-63): mean error = {dn.mean():.3f} bits (16 = random)")

    # Per-round breakdown
    print(f"\nPer schedule step:")
    for t in range(16, 40):
        errs = []
        for _ in range(N):
            W1 = random_w16(); W2 = random_w16()
            S1 = schedule(W1); S2 = schedule(W2)
            dW = S1[t] ^ S2[t]

            dM = [W1[i] ^ W2[i] for i in range(16)]
            dW_pred = list(dM) + [0] * 48
            for s in range(16, t+1):
                dW_pred[s] = (sig1(dW_pred[s-2]) ^ dW_pred[s-7] ^
                             sig0(dW_pred[s-15]) ^ dW_pred[s-16])

            errs.append(hw(dW ^ dW_pred[t]))

        avg = np.mean(errs)
        print(f"  W[{t:>2}]: mean GF(2) prediction error = {avg:.3f}")

def test_schedule_nullspace(N=1000):
    """Find messages where schedule difference is SMALL.
    These are messages where the schedule's mixing is weakest."""
    print(f"\n--- SCHEDULE NULLSPACE (N={N}) ---")

    # GF(2) nullspace of the schedule: find ΔM such that
    # schedule(M) ⊕ schedule(M⊕ΔM) has minimum weight.

    # The GF(2) schedule is a 64×16 binary matrix (each entry is a 32×32 block).
    # Nullspace = ΔM with all schedule words zero.
    # This is equivalent to sig1(ΔW[t-2]) ⊕ ΔW[t-7] ⊕ sig0(ΔW[t-15]) ⊕ ΔW[t-16] = 0
    # for t=16..63.

    # In GF(2): this is a 48*32 = 1536 constraint system on 16*32 = 512 unknowns.
    # Heavily overconstrained → nullspace is likely {0}.

    # But: what about APPROXIMATE nullspace? (minimum weight, not zero)
    best_schedule_hw = 2048  # 64 words × 32 bits
    best_dm = None

    for _ in range(N):
        # Random 1-bit difference
        w_idx = random.randint(0, 15)
        b_idx = random.randint(0, 31)
        dM = [0] * 16
        dM[w_idx] = (1 << b_idx)

        # Compute GF(2) schedule diff
        dW = list(dM) + [0] * 48
        for t in range(16, 64):
            dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]

        total_hw = sum(hw(dW[t]) for t in range(64))
        if total_hw < best_schedule_hw:
            best_schedule_hw = total_hw
            best_dm = (w_idx, b_idx)

    print(f"Best 1-bit schedule diff:")
    print(f"  ΔW[{best_dm[0]}] bit {best_dm[1]}: total schedule HW = {best_schedule_hw}")

    # Average for 1-bit diffs
    hw_by_word = np.zeros(16)
    for w_idx in range(16):
        total = 0
        for b_idx in range(32):
            dM = [0] * 16
            dM[w_idx] = (1 << b_idx)
            dW = list(dM) + [0] * 48
            for t in range(16, 64):
                dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]
            total += sum(hw(dW[t]) for t in range(64))
        hw_by_word[w_idx] = total / 32

    print(f"\nAverage schedule diff HW by message word:")
    for w in range(16):
        print(f"  W[{w:>2}]: avg schedule HW = {hw_by_word[w]:.1f}")

    print(f"\n  Minimum: W[{np.argmin(hw_by_word)}] = {hw_by_word.min():.1f}")
    print(f"  Maximum: W[{np.argmax(hw_by_word)}] = {hw_by_word.max():.1f}")
    print(f"  This shows which message words have WEAKEST diffusion")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 110: SHR NULLIFICATION")
    print("Exploiting schedule's weak point")
    print("=" * 60)

    free_bits = test_shr_null_cost()
    test_computed_word_shr(3000)
    test_partial_equivariance(500)
    test_schedule_linearity(1000)
    test_schedule_nullspace(500)

    print(f"\n{'='*60}")
    print(f"VERDICT: SHR Nullification")
    print(f"  Free message bits: {free_bits}")
    print(f"  Partial equivariance: first 2 schedule steps only")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
