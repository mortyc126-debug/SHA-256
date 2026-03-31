#!/usr/bin/env python3
"""
EXP 136: ★-Invariant Evolution — Track |I_r| Through Rounds

THEORY (from mathematical derivation):
  I_r = set of bit positions where δ_XOR = 0 at round r
  |I_r| starts at 256 (when S₁ = S₂ = IV)
  |I_r| decreases as δW injects differences
  Rate: ~1.5 bits lost per round (theoretical estimate)
  Prediction: |I_64| ≈ 256 - 96 = 160?

TEST: For actual message pairs, track |I_r| round by round.
  If |I_r| decays SLOWER than expected → ★-invariant is real.
  If |I_r| decays to 128 immediately → no invariant.

ALSO: Track per-word, per-bit to find WHERE invariant survives longest.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def track_invariant(M1, M2, max_R=64):
    """Track |I_r| = number of matching bits in states, per round."""
    s1 = sha256_rounds(M1, max_R)
    s2 = sha256_rounds(M2, max_R)

    I_sizes = []
    per_word = []

    for r in range(max_R + 1):
        # Count matching bits (δ_XOR = 0 positions)
        match_total = 0
        word_matches = []
        for w in range(8):
            xor_diff = s1[r][w] ^ s2[r][w]
            matching = 32 - hw(xor_diff)
            match_total += matching
            word_matches.append(matching)

        I_sizes.append(match_total)
        per_word.append(word_matches)

    return I_sizes, per_word

def test_invariant_decay(N=500):
    """Average |I_r| decay across many random pairs."""
    print(f"\n--- ★-INVARIANT DECAY (N={N}) ---")

    # Case 1: Fully random pairs (M1, M2 independent)
    print(f"\n  Case 1: Random pairs (M1 ≠ M2, independent)")
    all_I = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16(); M2 = random_w16()
        I_sizes, _ = track_invariant(M1, M2)
        all_I[trial] = I_sizes

    print(f"  {'Round':>6} | {'E[|I|]':>8} | {'std':>6} | {'Δ/round':>8} | {'Theory':>8}")
    print(f"  " + "-" * 50)
    prev = None
    for r in [0, 1, 2, 4, 8, 12, 16, 20, 24, 32, 48, 64]:
        avg = all_I[:, r].mean()
        std = all_I[:, r].std()
        delta = f"{avg - prev:.2f}" if prev is not None else "-"
        # Theory: random bits → |I| = 128 always (half match by chance)
        theory = 128.0
        print(f"  {r:>6} | {avg:>8.2f} | {std:>5.2f} | {delta:>8} | {theory:>8.1f}")
        prev = avg

    # Case 2: Related pairs (M2 = M1 with 1 word changed)
    print(f"\n  Case 2: Related pairs (M2 = M1 + 1 word different)")
    all_I2 = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        w_change = random.randint(0, 15)
        M2[w_change] = random.randint(0, MASK)
        I_sizes, _ = track_invariant(M1, M2)
        all_I2[trial] = I_sizes

    print(f"  {'Round':>6} | {'E[|I|]':>8} | {'std':>6} | {'Δ/round':>8}")
    print(f"  " + "-" * 40)
    prev = None
    for r in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 32, 64]:
        avg = all_I2[:, r].mean()
        std = all_I2[:, r].std()
        delta_s = f"{avg - prev:.2f}" if prev is not None else "-"
        print(f"  {r:>6} | {avg:>8.2f} | {std:>5.2f} | {delta_s:>8}")
        prev = avg

    # Case 3: Very related (M2 = M1 + 1 bit flipped)
    print(f"\n  Case 3: 1-bit difference (M2 = M1 ⊕ single bit)")
    all_I3 = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        w_flip = random.randint(0, 15)
        b_flip = random.randint(0, 31)
        M2[w_flip] ^= (1 << b_flip)
        I_sizes, _ = track_invariant(M1, M2)
        all_I3[trial] = I_sizes

    print(f"  {'Round':>6} | {'E[|I|]':>8} | {'std':>6} | {'decay rate':>10}")
    print(f"  " + "-" * 42)
    for r in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 32, 64]:
        avg = all_I3[:, r].mean()
        std = all_I3[:, r].std()
        if r > 0:
            decay = (all_I3[:, 0].mean() - avg) / r
        else:
            decay = 0
        print(f"  {r:>6} | {avg:>8.2f} | {std:>5.2f} | {decay:>10.3f}/round")

    return all_I, all_I2, all_I3

def test_per_word_survival(N=500):
    """Which STATE WORDS preserve |I| longest?"""
    print(f"\n--- PER-WORD ★-INVARIANT SURVIVAL ---")

    # 1-bit difference, track per word
    word_survival = np.zeros((N, 65, 8))
    for trial in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[0] ^= 1  # Flip bit 0 of W[0]
        _, per_word = track_invariant(M1, M2)
        for r in range(65):
            for w in range(8):
                word_survival[trial, r, w] = per_word[r][w]

    print(f"\n  1-bit diff (W[0] bit 0), E[matching bits per word] (max=32):")
    print(f"  {'Round':>6}", end="")
    for w in range(8):
        print(f" | {'w'+str(w):>6}", end="")
    print()
    print(f"  " + "-" * (8 + 9 * 8))

    for r in [0, 1, 2, 3, 4, 5, 8, 12, 16, 20, 64]:
        print(f"  {r:>6}", end="")
        for w in range(8):
            avg = word_survival[:, r, w].mean()
            print(f" | {avg:>6.2f}", end="")
        print()

    # Which word survives longest above 20 (= significantly above random 16)?
    print(f"\n  Round where each word drops below 20 matching bits:")
    for w in range(8):
        for r in range(65):
            if word_survival[:, r, w].mean() < 20:
                print(f"    Word {w}: drops at round {r}")
                break
        else:
            print(f"    Word {w}: SURVIVES all 64 rounds!")

def test_invariant_vs_near_collision(N=300):
    """Do near-collision pairs have higher |I| at intermediate rounds?"""
    print(f"\n--- ★-INVARIANT IN NEAR-COLLISIONS ---")

    # Collect near-collisions and random pairs
    near_I = []; random_I = []

    for _ in range(N * 100):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        if dH < 110:
            I_sizes, _ = track_invariant(M1, M2)
            near_I.append(I_sizes)
            if len(near_I) >= N:
                break
        elif len(random_I) < N and random.random() < 0.05:
            I_sizes, _ = track_invariant(M1, M2)
            random_I.append(I_sizes)

    if len(near_I) < 10:
        print(f"  Not enough near-collisions found ({len(near_I)})")
        return

    near_arr = np.array(near_I[:min(len(near_I), N)])
    rand_arr = np.array(random_I[:min(len(random_I), N)])

    print(f"  Near-collisions: {len(near_arr)}, Random: {len(rand_arr)}")
    print(f"\n  {'Round':>6} | {'Near |I|':>9} | {'Rand |I|':>9} | {'Diff':>6} | {'Signal'}")
    print(f"  " + "-" * 50)

    for r in [0, 4, 8, 16, 32, 48, 60, 62, 63, 64]:
        if r >= near_arr.shape[1]:
            continue
        near_avg = near_arr[:, r].mean()
        rand_avg = rand_arr[:, r].mean() if len(rand_arr) > 0 else 128
        diff = near_avg - rand_avg
        n = min(len(near_arr), len(rand_arr))
        if n > 1 and len(rand_arr) > 0:
            pooled = math.sqrt((near_arr[:, r].std()**2 + rand_arr[:, r].std()**2) / 2)
            z = diff / (pooled / math.sqrt(n)) if pooled > 0 else 0
        else:
            z = 0
        sig = "***" if abs(z) > 3 else ""
        print(f"  {r:>6} | {near_avg:>9.2f} | {rand_avg:>9.2f} | {diff:>+5.1f} | Z={z:+.1f} {sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 136: ★-INVARIANT EVOLUTION")
    print("Track |I_r| through rounds — theory vs reality")
    print("=" * 60)

    all_I, all_I2, all_I3 = test_invariant_decay(300)
    test_per_word_survival(300)
    test_invariant_vs_near_collision(200)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★-Invariant")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
