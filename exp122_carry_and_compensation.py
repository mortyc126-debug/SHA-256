#!/usr/bin/env python3
"""
EXP 122: Carry-AND Compensation — The ★-Native Collision Principle

From exp121: the NEGATIVE coefficient on carry∩AND overlap means:
When carry difference and AND difference align → hash distance DROPS.

WHY? In ★-algebra:
  Hash[w] = (IV[w] ⊕ state[w]) ⊕ carry_contribution
  δH[w] = δ(IV⊕s) ⊕ δ(carry_contrib)

  If δ(carry) aligns with δ(AND) → they CANCEL in the hash.
  Collision = PERFECT cancellation.

So the native collision principle is NOT "find two equal hashes."
It's: "find a pair where carry compensates AND perfectly."

This reframes the entire problem:
  OLD: minimize |H(M₁) - H(M₂)| (256-bit target)
  NEW: maximize alignment(δcarry, δAND) (★-native target)

These are the SAME at dH=0 but DIFFERENT during search:
  - Hash minimization has flat landscape (exp112: 0 correlation cheap)
  - Carry-AND alignment might have SMOOTHER landscape in ★-space

TEST: Is carry-AND alignment measurable CHEAPLY (< 20 rounds)?
If yes → we found the native shortcut.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def carry_and_alignment(M1, M2, R=64):
    """Measure carry-AND alignment at round R.

    Returns: alignment score (higher = more cancellation potential)"""
    s1 = sha256_rounds(M1, R)
    s2 = sha256_rounds(M2, R)

    alignment = 0
    for w in range(8):
        # Carry difference
        c1 = carry_word(IV[w], s1[R][w])
        c2 = carry_word(IV[w], s2[R][w])
        delta_carry = c1 ^ c2

        # AND difference
        a1 = IV[w] & s1[R][w]
        a2 = IV[w] & s2[R][w]
        delta_and = a1 ^ a2

        # Alignment: how many bits are the same in delta_carry and delta_and?
        alignment += 32 - hw(delta_carry ^ delta_and)

    return alignment  # Max 256, higher = more aligned

def test_alignment_per_round(N=3000):
    """Can carry-AND alignment be measured at EARLY rounds?"""
    print(f"\n--- ALIGNMENT MEASURABILITY PER ROUND (N={N}) ---")

    # For each pair: measure alignment at round R AND final dH
    # If corr(alignment_R, dH_64) > 0 for small R → cheap predictor!

    # Generate pairs
    pairs = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        pairs.append((M1, M2, dH))

    # Measure alignment at various rounds
    for R in [1, 2, 4, 8, 16, 32, 48, 63, 64]:
        alignments = []
        dHs = []
        for M1, M2, dH in pairs:
            a = carry_and_alignment(M1, M2, R)
            alignments.append(a)
            dHs.append(dH)

        aa = np.array(alignments)
        da = np.array(dHs)

        corr = np.corrcoef(aa, da)[0, 1]
        # Negative corr = higher alignment → lower dH → GOOD
        marker = "***" if corr < -0.05 else ""
        print(f"  Round {R:>2}: E[align]={aa.mean():.1f}, "
              f"corr(align, dH)={corr:+.6f} {marker}")

def test_alignment_at_transition(N=5000):
    """The transition region: where does alignment start predicting?"""
    print(f"\n--- ALIGNMENT PREDICTION TRANSITION (N={N}) ---")

    pairs = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        pairs.append((M1, M2, dH))

    # Fine-grained round scan
    for R in range(55, 65):
        alignments = []
        dHs = []
        for M1, M2, dH in pairs[:2000]:
            a = carry_and_alignment(M1, M2, R)
            alignments.append(a)
            dHs.append(dH)

        aa = np.array(alignments)
        da = np.array(dHs)
        corr = np.corrcoef(aa, da)[0, 1]
        print(f"  Round {R}: corr(align, dH) = {corr:+.6f}")

def test_compensation_walk(N=30, max_steps=200, R=4):
    """Walk that maximizes carry-AND alignment instead of minimizing dH."""
    print(f"\n--- COMPENSATION WALK ({R} rounds, N={N}) ---")

    best_global_dH = 256
    collisions = 0

    for trial in range(N):
        M1 = random_w16()
        target_H = [(IV[i] + sha256_rounds(M1, R)[R][i]) & MASK for i in range(8)]

        M2 = random_w16()
        current_dH = sum(hw(target_H[w] ^ ((IV[w] + sha256_rounds(M2, R)[R][w]) & MASK))
                        for w in range(8))
        current_align = carry_and_alignment(M2, M1, R)

        for step in range(max_steps):
            best_score = current_dH - 0.5 * current_align  # Minimize dH, maximize align
            best_M = None
            best_step_dH = current_dH

            for _ in range(32):
                w_idx = random.randint(0, 15)
                b_idx = random.randint(0, 31)
                M_test = list(M2)
                M_test[w_idx] ^= (1 << b_idx)

                test_H = [(IV[i] + sha256_rounds(M_test, R)[R][i]) & MASK for i in range(8)]
                test_dH = sum(hw(target_H[w] ^ test_H[w]) for w in range(8))
                test_align = carry_and_alignment(M_test, M1, R)

                score = test_dH - 0.5 * test_align
                if score < best_score:
                    best_score = score
                    best_M = M_test
                    best_step_dH = test_dH

            if best_M is not None:
                M2 = best_M
                current_dH = best_step_dH
                current_align = carry_and_alignment(M2, M1, R)

            if current_dH == 0 and M1 != M2:
                collisions += 1
                break

            if current_dH < best_global_dH:
                best_global_dH = current_dH

    print(f"  Collisions: {collisions}/{N}")
    print(f"  Best dH: {best_global_dH}")
    return collisions, best_global_dH

def test_pure_random_comparison(N=30, budget_per_trial=200*32, R=4):
    """Pure random search with same computational budget."""
    print(f"\n--- RANDOM SEARCH ({R} rounds, N={N}, budget={budget_per_trial}) ---")

    best_global_dH = 256
    collisions = 0

    for trial in range(N):
        M1 = random_w16()
        target_H = [(IV[i] + sha256_rounds(M1, R)[R][i]) & MASK for i in range(8)]

        for _ in range(budget_per_trial):
            M2 = random_w16()
            test_H = [(IV[i] + sha256_rounds(M2, R)[R][i]) & MASK for i in range(8)]
            dH = sum(hw(target_H[w] ^ test_H[w]) for w in range(8))
            if dH < best_global_dH:
                best_global_dH = dH
            if dH == 0 and M1 != M2:
                collisions += 1
                break

    print(f"  Collisions: {collisions}/{N}")
    print(f"  Best dH: {best_global_dH}")
    return collisions, best_global_dH

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 122: CARRY-AND COMPENSATION")
    print("★-native principle: align carry with AND to collapse dH")
    print("=" * 60)

    test_alignment_per_round(2000)
    test_alignment_at_transition(2000)

    # Compare three methods at R=4
    print(f"\n{'='*60}")
    print(f"THREE-WAY COMPARISON at 4 rounds")
    print(f"{'='*60}")

    comp_c, comp_best = test_compensation_walk(N=30, max_steps=200, R=4)
    rand_c, rand_best = test_pure_random_comparison(N=30, budget_per_trial=6400, R=4)

    print(f"\n  RESULTS:")
    print(f"  {'Method':>20} | {'Collisions':>10} | {'Best dH':>8}")
    print(f"  " + "-" * 45)
    print(f"  {'Compensation walk':>20} | {comp_c:>10} | {comp_best:>8}")
    print(f"  {'Random search':>20} | {rand_c:>10} | {rand_best:>8}")

if __name__ == "__main__":
    main()
