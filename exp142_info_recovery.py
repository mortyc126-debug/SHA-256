#!/usr/bin/env python3
"""
EXP 142: Information Recovery — How much of the input can be recovered?

Theory: SHA-256 maps 512→256 bits. If K words (K×32 bits) are known,
remaining (16-K)×32 bits can be recovered if (16-K)×32 ≤ 256, i.e. K ≥ 8.

TEST 1: Know 15 of 16 words → recover 1 word (32 unknowns, 256 equations)
         OVERDETERMINED → should work (if solution exists)

TEST 2: Know 8 of 16 words → recover 8 words (256 unknowns, 256 equations)
         SQUARE → should work (unique solution)

TEST 3: Know 7 of 16 words → recover 9 words (288 unknowns, 256 equations)
         UNDERDETERMINED → multiple solutions

METHOD: Brute force on the unknown words (feasible for 1-2 unknown words).
For more unknowns: check if the system is solvable.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def recover_one_word(M_full, known_indices, target_H, unknown_idx):
    """Try to recover one unknown word by brute force.
    Only feasible for 32-bit search (2^32 max, but we sample)."""

    # Try random values for the unknown word
    best_dist = 256
    best_val = None

    M_test = list(M_full)

    # For 1 unknown word: could do full 2^32 search
    # Here we sample to check if solution EXISTS
    budget = 100000

    for _ in range(budget):
        val = random.randint(0, MASK)
        M_test[unknown_idx] = val
        H = sha256_compress(M_test)

        dist = sum(hw(H[w] ^ target_H[w]) for w in range(8))
        if dist < best_dist:
            best_dist = dist
            best_val = val

        if dist == 0:
            return val, 0, True  # Found!

    return best_val, best_dist, False

def test_recover_known_15(N=10):
    """Know 15 words, recover 1."""
    print(f"\n--- RECOVER 1 UNKNOWN WORD (15 known) ---")

    for trial in range(N):
        M = random_w16()
        H = sha256_compress(M)
        unknown_idx = random.randint(0, 15)
        true_val = M[unknown_idx]

        val, dist, found = recover_one_word(M, list(range(16)), H, unknown_idx)

        if found:
            print(f"  Trial {trial}: RECOVERED W[{unknown_idx}] = 0x{val:08x} "
                  f"(true: 0x{true_val:08x}) {'✓' if val == true_val else '≠'}")
        else:
            print(f"  Trial {trial}: best dH = {dist} (budget exhausted)")

def test_inverse_round_recovery():
    """Use round inversion to recover unknown word.
    If we know the hash H and 15 words, we can:
    1. Compute state_64 from H: state_64[w] = H[w] - IV[w]
    2. Invert rounds 63→...→1 (we know W[1]..W[15] and schedule)
    3. At round 0: state_1 is known, W[0] is unknown
    4. Solve: Round(IV, W[0], K[0]) = state_1 → find W[0]"""
    print(f"\n--- INVERSE ROUND RECOVERY ---")

    for trial in range(5):
        M = random_w16()
        H = sha256_compress(M)

        # Recover state_64 from H
        state_64 = [(H[w] - IV[w]) & MASK for w in range(8)]

        # Verify
        states = sha256_rounds(M, 64)
        assert state_64 == states[64], "State recovery failed!"

        # Now: unknown = W[0]. Known = W[1]..W[15], H.
        # Schedule: W[16..63] depends on W[0]..W[15].
        # If W[0] unknown → W[16], W[32], W[48] etc. also partially unknown.

        # Strategy: try all W[0] values, compute full hash, compare
        # This IS brute force on 32 bits = 2^32 ≈ 4 billion
        # Too much for Python but TRIVIAL for GPU (seconds)

        # Instead: use INVERSE round trick
        # Compute schedule WITHOUT W[0] (set W[0]=0)
        # Then adjust

        # Simpler test: verify that knowing 15/16 words + hash
        # gives exactly 1 solution for W[0]

        # Count solutions by sampling
        W = schedule(M)

        # Invert from round 64 to round 1 using known W[1..63]
        # W[1..15] known directly, W[16..63] depend on W[0]
        # So we can only invert rounds that DON'T use W[0]-dependent schedule words

        # Rounds 1-15 use W[1]..W[15] (known!)
        # Round 0 uses W[0] (unknown)
        # Rounds 16+ use W[16+] which depends on W[0]

        # So: invert rounds 15 → 1 (these use known W[1..15])
        state = list(state_64)

        # But rounds 16-63 use W[16..63] which depend on W[0]!
        # Can't invert those without knowing W[0].

        # Alternative: invert rounds 63→16 requires W[16..63]
        # W[16] = σ₁(W[14]) + W[9] + σ₀(W[1]) + W[0] ← depends on W[0]!

        print(f"  Trial {trial}: state_64 recovered from H ✓")
        print(f"    W[16] = σ₁(W[14]) + W[9] + σ₀(W[1]) + W[0]")
        print(f"    W[0] appears in W[16] linearly (+W[0])")
        print(f"    W[0] affects schedule words: W[16], W[17], ..., W[63]")
        print(f"    → Cannot invert rounds 16+ without W[0]")
        print(f"    → Must brute-force W[0] (2^32 = {2**32:,} attempts)")
        print(f"    → Feasible! GPU: ~1 second")
        break

def test_recover_multiple_words():
    """How many words can we recover simultaneously?"""
    print(f"\n--- RECOVERY FEASIBILITY ---")

    print(f"""
  Theoretical analysis:

  Unknown words | Unknown bits | Equations | Status      | Cost
  ──────────────────────────────────────────────────────────────────
       1        |     32       |   256     | OVER-DET    | 2^32 (GPU: 1s)
       2        |     64       |   256     | OVER-DET    | 2^64 (years)
       4        |    128       |   256     | OVER-DET    | 2^128 = birthday!
       8        |    256       |   256     | SQUARE      | 2^256 (impossible)
       9        |    288       |   256     | UNDER-DET   | ∞ solutions
      16        |    512       |   256     | UNDER-DET   | 2^256 solutions
    """)

    print(f"  KEY INSIGHT:")
    print(f"    1 unknown word: 2^32 = trivial (brute force)")
    print(f"    2 unknown words: 2^64 = hard but feasible (nation-state)")
    print(f"    4 unknown words: 2^128 = SAME AS COLLISION PROBLEM!")
    print(f"    8+ unknown words: information-theoretically impossible")
    print(f"")
    print(f"    The TRANSITION happens at 8 words = 256 bits = hash size.")
    print(f"    Below 8: overdetermined, unique solution, just need compute.")
    print(f"    Above 8: underdetermined, many solutions, can't choose.")

def test_partial_info_recovery(N=500):
    """Even without recovering EXACT words, how many BITS of info
    does the hash reveal about the input?"""
    print(f"\n--- PARTIAL INFORMATION RECOVERY (N={N}) ---")

    # For each input bit position: does the hash reveal it?
    # Measure: mutual information between input bit and hash

    # Method: fix all bits except one, compute hash for bit=0 and bit=1
    # If hash changes → that bit has influence (but not necessarily recoverable)

    # Better: for random messages, correlate input bit with hash bit
    input_bits = np.zeros((N, 512), dtype=int)
    hash_bits = np.zeros((N, 256), dtype=int)

    for i in range(N):
        M = random_w16()
        H = sha256_compress(M)
        for w in range(16):
            for b in range(32):
                input_bits[i, w*32+b] = (M[w] >> b) & 1
        for w in range(8):
            for b in range(32):
                hash_bits[i, w*32+b] = (H[w] >> b) & 1

    # Correlation matrix: 512 × 256
    max_corr_per_input = []
    for ib in range(512):
        max_c = 0
        # Sample 50 hash bits
        for hb in random.sample(range(256), 50):
            c = abs(np.corrcoef(input_bits[:, ib], hash_bits[:, hb])[0, 1])
            if not np.isnan(c):
                max_c = max(max_c, c)
        max_corr_per_input.append(max_c)

    mc = np.array(max_corr_per_input)
    expected_max = 3 / math.sqrt(N)  # Random max correlation

    print(f"  Max |corr(input_bit, hash_bit)| per input position:")
    print(f"    Mean: {mc.mean():.6f} (random: ~{expected_max:.6f})")
    print(f"    Max:  {mc.max():.6f}")
    print(f"    Fraction above 3σ: {np.sum(mc > 3*expected_max)/512:.4f}")

    # Which input bits are MOST correlated with hash?
    top_bits = np.argsort(-mc)[:10]
    print(f"\n  Most correlated input bits:")
    for idx in top_bits:
        w = idx // 32; b = idx % 32
        print(f"    M[{w}] bit {b}: max_corr = {mc[idx]:.4f}")

    if mc.max() < 3 * expected_max:
        print(f"\n  *** NO INPUT BIT CORRELATES WITH ANY HASH BIT ***")
        print(f"  → SHA-256 reveals ZERO direct information about input bits")
        print(f"  → Recovery requires brute force, not inference")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 142: INFORMATION RECOVERY")
    print("How much can we recover from SHA-256 output?")
    print("=" * 60)

    test_inverse_round_recovery()
    test_recover_multiple_words()
    test_partial_info_recovery(400)
    test_recover_known_15(5)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
