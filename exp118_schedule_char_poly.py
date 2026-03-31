#!/usr/bin/env python3
"""
EXP 118: Schedule Characteristic Polynomial over Z/2^32Z

The schedule: W[t] = σ₁(W[t-2]) + W[t-7] + σ₀(W[t-15]) + W[t-16] mod 2^32

STANDARD APPROACH: Over GF(2), this is linear but carry makes it nonlinear.
★-APPROACH: Over Z/2^32Z, addition IS the native operation. The schedule
IS a linear recurrence over this ring (if we treat σ₀, σ₁ as linear maps).

σ₀ and σ₁ ARE linear over GF(2): σ₀(x) = ROTR7(x) ⊕ ROTR18(x) ⊕ SHR3(x)
But over Z/2^32Z: σ₀ is NOT linear (ROTR is, SHR is, but ⊕ ≠ + over Z).

KEY INSIGHT: Decompose into XOR-part and CARRY-part.
W[t] = σ₁(W[t-2]) ⊕ W[t-7] ⊕ σ₀(W[t-15]) ⊕ W[t-16] ⊕ CARRY_CORRECTIONS

The XOR-part IS a linear recurrence over GF(2)^32.
The CARRY-part is the nonlinear correction.

PLAN:
1. Compute characteristic polynomial of XOR-part (standard, linear algebra)
2. Measure carry corrections (★-native deviation from linearity)
3. If carry corrections are SMALL or STRUCTURED → exploitable
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def gf2_schedule_diff(dM):
    """GF(2)-linear schedule difference for message difference dM."""
    dW = list(dM) + [0] * 48
    for t in range(16, 64):
        dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]
    return dW

def real_schedule_diff(M1, M2):
    """Actual schedule difference (includes carry)."""
    S1 = schedule(M1); S2 = schedule(M2)
    return [S1[t] ^ S2[t] for t in range(64)]

def carry_correction(M1, M2):
    """Carry correction = real_diff ⊕ gf2_diff."""
    dM = [M1[i] ^ M2[i] for i in range(16)]
    gf2 = gf2_schedule_diff(dM)
    real = real_schedule_diff(M1, M2)
    return [gf2[t] ^ real[t] for t in range(64)]

def test_char_poly_gf2():
    """Characteristic polynomial of schedule over GF(2)^32."""
    print(f"\n--- CHARACTERISTIC POLYNOMIAL (GF(2)) ---")

    # The GF(2) schedule: dW[t] = σ₁(dW[t-2]) ⊕ dW[t-7] ⊕ σ₀(dW[t-15]) ⊕ dW[t-16]
    # This is a linear recurrence of order 16 over GF(2)^32.
    #
    # Characteristic polynomial: x^16 + σ₁·x^14 + x^9 + σ₀·x + 1
    # (where σ₀, σ₁ are 32×32 matrices over GF(2))
    #
    # Actually, the recurrence has indices t-2, t-7, t-15, t-16.
    # Rewrite: dW[t] + σ₁·dW[t-2] + dW[t-7] + σ₀·dW[t-15] + dW[t-16] = 0
    # Char. poly: z^16 + σ₁·z^14 + z^9 + σ₀·z + 1 = 0 (over GF(2)^{32×32})

    # Compute the PERIOD of the GF(2) schedule
    # Start with a single-bit message diff, track how long until it repeats

    periods = []
    for w in range(4):  # Test a few message words
        for b in range(4):  # A few bits
            dM = [0] * 16
            dM[w] = 1 << b

            # Run schedule forward and look for period
            history = []
            dW = list(dM) + [0] * 48
            for t in range(16, 64):
                dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]

            # The schedule has only 48 steps (16→63), so period detection
            # requires extending beyond 64
            dW_ext = list(dW)
            for t in range(64, 256):
                val = sig1(dW_ext[t-2]) ^ dW_ext[t-7] ^ sig0(dW_ext[t-15]) ^ dW_ext[t-16]
                dW_ext.append(val)

            # Check if the pattern repeats
            for period in range(1, 128):
                match = True
                for t in range(16, min(64, 256 - period)):
                    if dW_ext[t] != dW_ext[t + period]:
                        match = False
                        break
                if match:
                    periods.append(period)
                    break
            else:
                periods.append(-1)  # No period found

    print(f"  GF(2) schedule periods for single-bit diffs: {periods[:8]}")
    print(f"  (Period = -1 means > 128)")

    # Compute nullity: how many independent message diffs give zero schedule at t?
    print(f"\n  GF(2) nullspace of schedule propagation:")
    for target_t in [20, 30, 40, 50, 63]:
        # Build 512×32 matrix: each message bit → schedule word at target_t
        M_matrix = np.zeros((512, 32), dtype=int)
        for w in range(16):
            for b in range(32):
                dM = [0] * 16
                dM[w] = 1 << b
                dW = gf2_schedule_diff(dM)
                for ob in range(32):
                    M_matrix[w*32 + b, ob] = (dW[target_t] >> ob) & 1

        rank = np.linalg.matrix_rank(M_matrix % 2)
        nullity = 512 - rank
        print(f"    W[{target_t}]: rank={rank}/32, nullity in msg space={nullity}")

def test_carry_corrections(N=5000):
    """Measure carry corrections: how big and structured?"""
    print(f"\n--- CARRY CORRECTIONS (N={N}) ---")

    corrections_hw = np.zeros((N, 48))

    for i in range(N):
        M1 = random_w16(); M2 = random_w16()
        cc = carry_correction(M1, M2)
        for t in range(16, 64):
            corrections_hw[i, t-16] = hw(cc[t])

    print(f"  Mean HW(carry_correction) per schedule step:")
    for t_off in [0, 1, 2, 4, 8, 16, 32, 47]:
        t = t_off + 16
        mean_hw = corrections_hw[:, t_off].mean()
        std_hw = corrections_hw[:, t_off].std()
        print(f"    W[{t:>2}]: mean={mean_hw:.2f} ± {std_hw:.2f} (random=16)")

    # Is carry correction CORRELATED across schedule steps?
    print(f"\n  Carry correction inter-step correlation:")
    for t1, t2 in [(16, 17), (16, 18), (16, 20), (16, 30), (16, 63)]:
        corr = np.corrcoef(corrections_hw[:, t1-16], corrections_hw[:, t2-16])[0, 1]
        print(f"    corr(W[{t1}], W[{t2}]): {corr:+.4f}")

    # ★-NATIVE: what does carry correction look like in ★-space?
    print(f"\n  ★-decomposition of carry correction:")
    # The carry correction cc[t] = gf2_diff[t] ⊕ real_diff[t]
    # In ★-space: cc represents the CARRY CONTRIBUTION to schedule mixing
    # This is what GF(2) analysis MISSES

    # How many bits of the schedule are explained by GF(2) vs carry?
    gf2_explained = []
    for i in range(min(N, 1000)):
        M1 = random_w16(); M2 = random_w16()
        dM = [M1[j] ^ M2[j] for j in range(16)]
        gf2 = gf2_schedule_diff(dM)
        real = real_schedule_diff(M1, M2)

        total_diff_bits = sum(hw(real[t]) for t in range(16, 64))
        gf2_correct = sum(32 - hw(gf2[t] ^ real[t]) for t in range(16, 64))
        gf2_explained.append(gf2_correct / (48 * 32))

    ge = np.array(gf2_explained)
    print(f"  GF(2) prediction accuracy: {ge.mean():.4f} ({ge.mean()*100:.1f}%)")
    print(f"  Carry explains: {1-ge.mean():.4f} ({(1-ge.mean())*100:.1f}%)")

def test_schedule_native_structure(N=3000):
    """★-native schedule analysis: treat addition as fundamental."""
    print(f"\n--- ★-NATIVE SCHEDULE STRUCTURE (N={N}) ---")

    # Over Z/2^32Z, the schedule IS linear:
    # W[t] = σ₁(W[t-2]) + W[t-7] + σ₀(W[t-15]) + W[t-16]
    #
    # But σ₀, σ₁ are NOT linear over Z/2^32Z!
    # σ₀(x) = ROTR7(x) ⊕ ROTR18(x) ⊕ SHR3(x)
    # ⊕ is NOT + over Z/2^32Z.
    #
    # ★-insight: σ₀(x) = ★_add(★_add(ROTR7(x), ROTR18(x)), SHR3(x))
    # where ★_add means: the XOR-component of the ★-sum
    #
    # The schedule mixes TWO algebras:
    #   - Addition (+): in the recurrence itself
    #   - XOR (⊕): inside σ₀, σ₁
    #
    # THIS MIXING is what makes SHA-256 hard!

    # Test: if σ₀ used + instead of ⊕, how different would the schedule be?
    def sig0_additive(x):
        """sig0 with + instead of ⊕."""
        return (rotr(x, 7) + rotr(x, 18) + shr(x, 3)) & MASK

    def sig1_additive(x):
        """sig1 with + instead of ⊕."""
        return (rotr(x, 17) + rotr(x, 19) + shr(x, 10)) & MASK

    diffs = []
    for _ in range(N):
        x = random.randint(0, MASK)
        d0 = hw(sig0(x) ^ sig0_additive(x))
        d1 = hw(sig1(x) ^ sig1_additive(x))
        diffs.append((d0, d1))

    da = np.array(diffs)
    print(f"  HW(σ₀_xor ⊕ σ₀_add): mean={da[:,0].mean():.3f}")
    print(f"  HW(σ₁_xor ⊕ σ₁_add): mean={da[:,1].mean():.3f}")
    print(f"  (0 = identical, 16 = random)")

    # ★-native recurrence: what if entire schedule used ★?
    # W[t] = σ₁(W[t-2]) ★_add W[t-7] ★_add σ₀(W[t-15]) ★_add W[t-16]
    # where ★_add(a,b) = (a⊕b) | carry_component
    # This IS standard addition! So the schedule already IS ★-native for +.
    # The non-★ part is inside σ₀, σ₁ (which use ⊕ instead of +).

    print(f"\n  INSIGHT:")
    print(f"    Schedule addition (+): IS ★-native")
    print(f"    σ₀, σ₁ internals (⊕): NOT ★-native")
    print(f"    σ₀ vs σ₀_additive: {da[:,0].mean():.1f} bits differ")
    print(f"    σ₁ vs σ₁_additive: {da[:,1].mean():.1f} bits differ")
    print(f"")

    if da[:,0].mean() < 8:
        print(f"    σ functions are CLOSE to additive ({da[:,0].mean():.1f} < 8 bits)")
        print(f"    → Schedule is APPROXIMATELY linear over Z/2^32Z!")
        print(f"    → Characteristic polynomial analysis is APPROXIMATELY valid!")
    else:
        print(f"    σ functions are FAR from additive ({da[:,0].mean():.1f} ≈ 16)")
        print(f"    → Schedule mixes two algebras fundamentally")
        print(f"    → No single-algebra characteristic polynomial exists")
        print(f"    → This is SHA-256's ALGEBRAIC BARRIER:")
        print(f"       Cannot linearize over GF(2) (carry breaks it)")
        print(f"       Cannot linearize over Z/2^32Z (⊕ in σ breaks it)")
        print(f"       SHA-256 lives in NEITHER algebra — it lives in ★")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 118: SCHEDULE CHARACTERISTIC POLYNOMIAL")
    print("Standard: GF(2). ★-native: Z/2^32Z. Which works?")
    print("=" * 60)

    test_char_poly_gf2()
    test_carry_corrections(3000)
    test_schedule_native_structure(2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Schedule over two algebras")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
