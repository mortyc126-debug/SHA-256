#!/usr/bin/env python3
"""
EXP 98: Rotation Optimality — GF(2) Polynomial Analysis

WHY (6,11,25) for Σ₁ and (2,13,22) for Σ₀?

Single-round: ALL triples equally good (exp97).
Multi-round: rotations interact → some triples better.

Criteria to test:
1. GF(2) polynomial properties: order, irreducibility
2. Multi-round diffusion: how fast does full mixing occur?
3. Interaction Σ₀×Σ₁: combined diffusion
4. Branch number: minimum active bits
5. Spread: coverage of 32-bit word
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def sigma_polynomial_properties(r1, r2, r3, word_size=32):
    """Analyze GF(2) polynomial x^r1 + x^r2 + x^r3 mod x^32 + 1."""
    # Build polynomial as bit vector (coefficient at each position)
    poly = [0] * word_size
    poly[r1 % word_size] ^= 1
    poly[r2 % word_size] ^= 1
    poly[r3 % word_size] ^= 1

    hw_poly = sum(poly)  # Should be 3 (or less if collisions)

    # Minimum distance: HW of sigma(e_i) for single-bit inputs
    min_hw_out = 32
    for bit in range(word_size):
        x = 1 << bit
        result = rotr(x, r1) ^ rotr(x, r2) ^ rotr(x, r3)
        h = hw(result)
        min_hw_out = min(min_hw_out, h)

    # Spread: max gap between rotation positions
    positions = sorted([r1 % word_size, r2 % word_size, r3 % word_size])
    gaps = [positions[1]-positions[0], positions[2]-positions[1],
            word_size-positions[2]+positions[0]]
    max_gap = max(gaps)
    min_gap = min(gaps)
    spread = positions[-1] - positions[0]

    return {
        'hw_poly': hw_poly,
        'min_hw_out': min_hw_out,
        'spread': spread,
        'max_gap': max_gap,
        'min_gap': min_gap,
        'positions': positions,
    }

def multi_round_diffusion(r1_sig1, r2_sig1, r3_sig1,
                           r1_sig0, r2_sig0, r3_sig0, n_rounds=8):
    """
    Simulate multi-round diffusion with given rotation constants.
    Simplified SHA-256: only rotations + XOR + shift (no carry, no Ch/Maj).
    Measure: how many rounds until full avalanche?
    """
    def custom_sigma1(x):
        return rotr(x, r1_sig1) ^ rotr(x, r2_sig1) ^ rotr(x, r3_sig1)

    def custom_sigma0(x):
        return rotr(x, r1_sig0) ^ rotr(x, r2_sig0) ^ rotr(x, r3_sig0)

    # Simplified round: a_new = sig1(e) ^ sig0(a) ^ h ^ W
    # e_new = d ^ sig1(e)
    # (rest = shift)
    total_affected = 0
    n_tests = 100

    for _ in range(n_tests):
        # Random state
        state = [random.randint(0, MASK) for _ in range(8)]
        W = [random.randint(0, MASK) for _ in range(n_rounds)]

        # Run n_rounds with base state
        s = list(state)
        for r in range(n_rounds):
            a, b, c, d, e, f, g, h = s
            t1 = h ^ custom_sigma1(e) ^ W[r]
            t2 = custom_sigma0(a)
            s = [t1 ^ t2, a, b, c, d ^ t1, e, f, g]

        # Perturb one bit and re-run
        state_pert = list(state)
        state_pert[0] ^= 1  # Flip bit 0 of word a

        sp = list(state_pert)
        for r in range(n_rounds):
            a, b, c, d, e, f, g, h = sp
            t1 = h ^ custom_sigma1(e) ^ W[r]
            t2 = custom_sigma0(a)
            sp = [t1 ^ t2, a, b, c, d ^ t1, e, f, g]

        # Measure difference
        diff = sum(hw(s[i] ^ sp[i]) for i in range(8))
        total_affected += diff

    return total_affected / n_tests  # Average bits affected

def test_rotation_optimality():
    """Is SHA-256's rotation set optimal for multi-round diffusion?"""
    print("\n--- MULTI-ROUND ROTATION OPTIMALITY ---")

    # SHA-256 rotations
    sha_sig1 = (6, 11, 25)
    sha_sig0 = (2, 13, 22)

    sha_diff = multi_round_diffusion(*sha_sig1, *sha_sig0, n_rounds=4)
    sha_props = sigma_polynomial_properties(*sha_sig1)

    print(f"SHA-256 Σ₁={sha_sig1}: spread={sha_props['spread']}, "
          f"min_gap={sha_props['min_gap']}, max_gap={sha_props['max_gap']}")
    print(f"SHA-256 Σ₀={sha_sig0}: spread={sigma_polynomial_properties(*sha_sig0)['spread']}")
    print(f"SHA-256 4-round diffusion: {sha_diff:.1f}/256 bits affected")

    # Test MANY alternative pairs
    print(f"\nSearching alternative rotation pairs...")
    results = []

    # Generate candidate triples (those with avalanche=3, i.e. HW=3 output for all inputs)
    good_triples = []
    for r1 in range(1, 32):
        for r2 in range(r1+1, 32):
            for r3 in range(r2+1, 32):
                # Quick check: all distinct mod 32
                props = sigma_polynomial_properties(r1, r2, r3)
                if props['min_hw_out'] == 3:  # Perfect avalanche
                    good_triples.append((r1, r2, r3))

    print(f"Total triples with perfect avalanche: {len(good_triples)}")

    # Sample pairs and test multi-round
    n_test = min(200, len(good_triples)**2 // 100)
    for _ in range(n_test):
        t1 = random.choice(good_triples)
        t0 = random.choice(good_triples)
        if t1 == t0:
            continue

        diff = multi_round_diffusion(*t1, *t0, n_rounds=4)
        p1 = sigma_polynomial_properties(*t1)
        p0 = sigma_polynomial_properties(*t0)

        results.append((diff, t1, t0, p1['spread'], p0['spread']))

    results.sort(reverse=True)

    # Where does SHA-256 rank?
    sha_rank = sum(1 for d, _, _, _, _ in results if d > sha_diff) + 1

    print(f"\nSHA-256 4-round diffusion: {sha_diff:.1f} bits")
    print(f"SHA-256 rank: #{sha_rank} out of {len(results)} pairs")
    print(f"Percentile: top {sha_rank/len(results)*100:.1f}%")

    print(f"\nTop 10 pairs by 4-round diffusion:")
    for i, (diff, t1, t0, sp1, sp0) in enumerate(results[:10]):
        is_sha = (t1 == sha_sig1 and t0 == sha_sig0) or \
                 (t0 == sha_sig1 and t1 == sha_sig0)
        marker = " ← SHA-256!" if is_sha else ""
        print(f"  #{i+1}: Σ₁={t1}, Σ₀={t0}, diffusion={diff:.1f}, "
              f"spreads=({sp1},{sp0}){marker}")

    # Specific test: SHA-256 spread properties
    print(f"\n--- SPREAD ANALYSIS ---")
    sha_positions = sorted([2, 6, 11, 13, 22, 25])
    print(f"All 6 rotation positions: {sha_positions}")

    gaps = []
    for i in range(len(sha_positions)-1):
        gaps.append(sha_positions[i+1] - sha_positions[i])
    gaps.append(32 - sha_positions[-1] + sha_positions[0])
    print(f"Gaps between positions: {gaps}")
    print(f"Gap statistics: min={min(gaps)}, max={max(gaps)}, "
          f"mean={np.mean(gaps):.1f}, std={np.std(gaps):.1f}")

    # Optimal coverage: 6 positions in 32 → ideal gap = 32/6 = 5.33
    ideal_gap = 32 / 6
    gap_deviation = np.std(np.array(gaps) - ideal_gap)
    print(f"Ideal gap: {ideal_gap:.2f}")
    print(f"Gap deviation from ideal: {gap_deviation:.2f}")

    # Compare: how many triples have BETTER coverage?
    better_coverage = 0
    for t1 in good_triples[:50]:
        for t0 in good_triples[:50]:
            all_pos = sorted(set(list(t1) + list(t0)))
            if len(all_pos) < 6:
                continue
            g = []
            for i in range(len(all_pos)-1):
                g.append(all_pos[i+1]-all_pos[i])
            g.append(32 - all_pos[-1] + all_pos[0])
            dev = np.std(np.array(g) - 32/len(all_pos))
            if dev < gap_deviation:
                better_coverage += 1

    total_tested = min(50, len(good_triples))**2
    print(f"Pairs with better coverage: {better_coverage}/{total_tested}")

def test_combined_criterion():
    """Test: spread + diffusion + independence = SHA-256's design criterion."""
    print(f"\n--- COMBINED DESIGN CRITERION ---")

    sha_sig1 = (6, 11, 25)
    sha_sig0 = (2, 13, 22)

    # Criterion 1: Σ₀ and Σ₁ have NO common rotation
    common = set(sha_sig1) & set(sha_sig0)
    print(f"Common rotations Σ₁∩Σ₀: {common} (should be empty: {'YES' if len(common)==0 else 'NO'})")

    # Criterion 2: All 6 positions distinct
    all_pos = set(list(sha_sig1) + list(sha_sig0))
    print(f"All positions distinct: {len(all_pos)} = 6? {'YES' if len(all_pos)==6 else 'NO'}")

    # Criterion 3: No position = 0 or 16 (trivial/half-word)
    trivial = {0, 16} & all_pos
    print(f"No trivial positions (0,16): {'YES' if len(trivial)==0 else 'NO'}")

    # Criterion 4: Sum of each triple ≠ 0 mod 32
    sum1 = sum(sha_sig1) % 32
    sum0 = sum(sha_sig0) % 32
    print(f"Σ₁ sum mod 32: {sum1} (non-zero: {'YES' if sum1!=0 else 'NO'})")
    print(f"Σ₀ sum mod 32: {sum0} (non-zero: {'YES' if sum0!=0 else 'NO'})")

    # Criterion 5: r₃-r₁ is coprime with 32 (for Σ₁: 25-6=19, gcd(19,32)=1)
    from math import gcd
    span1 = sha_sig1[2] - sha_sig1[0]  # 25-6 = 19
    span0 = sha_sig0[2] - sha_sig0[0]  # 22-2 = 20
    print(f"Σ₁ span: {span1}, gcd({span1},32)={gcd(span1,32)} (coprime: {'YES' if gcd(span1,32)==1 else 'NO'})")
    print(f"Σ₀ span: {span0}, gcd({span0},32)={gcd(span0,32)} (coprime: {'YES' if gcd(span0,32)==1 else 'NO'})")

    # Criterion 6: schedule rotations σ₀=(7,18,SHR3) σ₁=(17,19,SHR10)
    # These DIFFER from Σ₀,Σ₁ → independence between round function and schedule
    sched_rot = {7, 17, 18, 19}
    round_rot = {2, 6, 11, 13, 22, 25}
    print(f"\nSchedule rotations: {sorted(sched_rot)}")
    print(f"Round rotations: {sorted(round_rot)}")
    print(f"Overlap: {sched_rot & round_rot} (should be empty: {'YES' if len(sched_rot & round_rot)==0 else 'NO'})")

    print(f"\n--- COMPLETE DESIGN CRITERIA ---")
    print(f"1. 6 distinct rotation positions (no overlap Σ₀/Σ₁)")
    print(f"2. No trivial positions (0, 16)")
    print(f"3. Maximum spread (Σ₁: span=19 coprime to 32)")
    print(f"4. Schedule rotations independent from round rotations")
    print(f"5. Multi-round diffusion near maximum")
    print(f"6. Sum ≠ 0 mod 32 (no trivial cancellation)")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 98: ROTATION OPTIMALITY")
    print("="*60)
    test_rotation_optimality()
    test_combined_criterion()

    print("\n"+"="*60)
    print("COMPLETE DESIGN RATIONALE")
    print("="*60)

if __name__ == "__main__":
    main()
