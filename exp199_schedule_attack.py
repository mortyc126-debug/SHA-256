#!/usr/bin/env python3
"""
EXP 199: SCHEDULE ATTACK — The Last Wall

Schedule: W[t] = σ₁(W[t-2]) + W[t-7] + σ₀(W[t-15]) + W[t-16]

Over GF(2): this is LINEAR. Nullspace = δM with δW_xor = 0 for all t≥16.
If nullspace > 0: message differences exist with zero XOR-schedule-diff.
Then only CARRY corrections remain → potentially solvable.

APPROACH:
1. Build the EXACT GF(2) schedule matrix (48×16 blocks of 32×32)
2. Compute nullspace dimension
3. If nullspace exists: find δM with minimum REAL schedule diff
4. Use carry analysis to check if remaining diff is manageable
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def build_gf2_schedule_matrix():
    """Build the FULL GF(2) schedule matrix.

    For each input bit (512 total): compute its effect on each
    schedule word (48 words × 32 bits = 1536 output bits).

    Matrix: 1536 × 512 over GF(2).
    """
    print(f"\n{'='*60}")
    print(f"GF(2) SCHEDULE MATRIX")
    print(f"{'='*60}")

    # Matrix M: M[output_bit, input_bit] = 1 if input_bit affects output_bit
    n_out = 48 * 32  # 1536
    n_in = 16 * 32   # 512

    M = np.zeros((n_out, n_in), dtype=int)

    for in_word in range(16):
        for in_bit in range(32):
            # Set one input bit
            dM = [0] * 16
            dM[in_word] = 1 << in_bit

            # GF(2) schedule diff
            dW = list(dM) + [0] * 48
            for t in range(16, 64):
                dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]

            # Record output
            in_idx = in_word * 32 + in_bit
            for out_word_off in range(48):
                t = out_word_off + 16
                for out_bit in range(32):
                    if (dW[t] >> out_bit) & 1:
                        M[out_word_off * 32 + out_bit, in_idx] = 1

    print(f"\n  Matrix size: {n_out} × {n_in} ({n_out}=48×32, {n_in}=16×32)")

    # Rank over GF(2)
    rank = np.linalg.matrix_rank(M % 2)
    nullity = n_in - rank

    print(f"  GF(2) Rank: {rank}")
    print(f"  Nullity: {nullity}")
    print(f"  (Nullity > 0 → nontrivial schedule GF(2)-collisions exist!)")

    if nullity > 0:
        print(f"\n  ★★★ NULLSPACE EXISTS! Dimension = {nullity}")
        print(f"  → {nullity} bits of freedom for zero XOR-schedule-diff")
    else:
        print(f"\n  Nullspace = {{0}} (only trivial solution)")
        print(f"  → NO nontrivial GF(2) schedule collision possible")

    return M, rank, nullity

def find_min_schedule_real(N=1000):
    """Find δM with minimum REAL (arithmetic) schedule difference."""
    print(f"\n{'='*60}")
    print(f"MINIMUM REAL SCHEDULE DIFFERENCE")
    print(f"{'='*60}")

    # Try many 1-bit δM: which gives smallest total |δW|?
    best_total = float('inf')
    best_info = None

    # Also: collect all for statistics
    totals = []

    for w in range(16):
        for b in range(32):
            dM = [0] * 16; dM[w] = 1 << b

            # REAL schedule (with carry)
            M1 = random_w16()
            M2 = [(M1[i] ^ dM[i]) for i in range(16)]

            W1 = schedule(M1); W2 = schedule(M2)

            # Arithmetic diff weight
            total = sum(hw((W1[t] - W2[t]) & MASK) for t in range(16, 64))
            totals.append(total)

            if total < best_total:
                best_total = total
                best_info = (w, b, total)

    ta = np.array(totals)
    print(f"\n  1-bit δM statistics:")
    print(f"    Mean total |δW|: {ta.mean():.1f}")
    print(f"    Min:  {ta.min()} (W[{best_info[0]}] bit {best_info[1]})")
    print(f"    Max:  {ta.max()}")

    # XOR diff vs arithmetic diff
    print(f"\n  XOR vs ARITHMETIC schedule diff:")
    for w_test, b_test in [(best_info[0], best_info[1]), (0, 15), (1, 28)]:
        dM = [0] * 16; dM[w_test] = 1 << b_test

        # Multiple random M bases
        xor_totals = []; arith_totals = []
        for _ in range(100):
            M1 = random_w16()
            M2 = [(M1[i] ^ dM[i]) for i in range(16)]
            W1 = schedule(M1); W2 = schedule(M2)

            xor_t = sum(hw(W1[t] ^ W2[t]) for t in range(16, 64))
            arith_t = sum(hw((W1[t] - W2[t]) & MASK) for t in range(16, 64))

            xor_totals.append(xor_t)
            arith_totals.append(arith_t)

        xor_avg = np.mean(xor_totals); arith_avg = np.mean(arith_totals)
        print(f"    W[{w_test}]b{b_test}: XOR_total={xor_avg:.0f}, ARITH_total={arith_avg:.0f}")

def test_schedule_near_collision(N=5000):
    """Among random M pairs: how often does schedule ALMOST collide?"""
    print(f"\n{'='*60}")
    print(f"SCHEDULE NEAR-COLLISIONS (N={N})")
    print(f"{'='*60}")

    # For random pairs: how many schedule words match?
    match_counts = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        W1 = schedule(M1); W2 = schedule(M2)

        matches = sum(1 for t in range(64) if W1[t] == W2[t])
        match_counts.append(matches)

    mc = np.array(match_counts)
    print(f"\n  Random pairs: how many W[t] match exactly?")
    print(f"    Mean: {mc.mean():.4f}/64")
    print(f"    Max:  {mc.max()}/64")

    # Expected: each W[t] matches with P = 2^(-32). Expected matches = 64/2^32 ≈ 0.
    print(f"    Expected: {64/2**32:.2e} (essentially 0)")

    if mc.max() > 0:
        print(f"    ★★★ FOUND {mc.max()} matching schedule words!")

    # Partial schedule: how many words have small diff?
    print(f"\n  How many W[t] have |δW| < k?")
    for k_hw in [4, 8, 12, 16]:
        counts = []
        for _ in range(min(N, 1000)):
            M1 = random_w16(); M2 = random_w16()
            W1 = schedule(M1); W2 = schedule(M2)
            n_close = sum(1 for t in range(16, 64) if hw(W1[t] ^ W2[t]) < k_hw)
            counts.append(n_close)
        avg = np.mean(counts)
        print(f"    |δW|<{k_hw}: avg {avg:.1f}/48 words")

def test_schedule_differential_path(N=200):
    """Can we find δM where schedule diff HELPS the round function?"""
    print(f"\n{'='*60}")
    print(f"SCHEDULE DIFFERENTIAL PATH")
    print(f"{'='*60}")

    # For each δM: compute schedule diff AND round function effect.
    # Find δM where schedule diff COMPENSATES round function diff.

    # Strategy: try late-word δM, measure how many rounds have
    # "helpful" schedule diff (δW[r] reduces δ(state) at that round).

    best_helpful = 0; best_info = None

    for _ in range(N):
        # Random 1-2 bit δM in late words
        dM = [0] * 16
        for _ in range(random.randint(1, 2)):
            w = random.randint(12, 15)
            b = random.randint(0, 31)
            dM[w] ^= (1 << b)
        if all(d == 0 for d in dM): continue

        M1 = random_w16()
        M2 = [(M1[i] ^ dM[i]) for i in range(16)]

        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        W1 = schedule(M1); W2 = schedule(M2)

        # Count "helpful" rounds: where δ(a,e) DECREASES
        helpful = 0
        for r in range(20, 63):
            dae_r = hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4])
            dae_r1 = hw(s1[r+1][0] ^ s2[r+1][0]) + hw(s1[r+1][4] ^ s2[r+1][4])
            if dae_r1 < dae_r - 3:
                helpful += 1

        if helpful > best_helpful:
            best_helpful = helpful
            best_info = (list(dM), helpful)

    print(f"\n  Best δM found: {best_helpful} helpful rounds (out of 43)")
    print(f"  (Helpful = δ(a,e) drops by >3 at that round)")

    # Average
    avg_helpful = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[random.randint(12,15)] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        helpful = sum(1 for r in range(20, 63)
                     if hw(s1[r+1][0]^s2[r+1][0]) + hw(s1[r+1][4]^s2[r+1][4])
                        < hw(s1[r][0]^s2[r][0]) + hw(s1[r][4]^s2[r][4]) - 3)
        avg_helpful.append(helpful)

    ah = np.array(avg_helpful)
    print(f"  Average helpful rounds: {ah.mean():.1f}")
    print(f"  (Random expectation: ~{43*0.15:.1f} based on P(drop>3)≈15%)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 199: SCHEDULE ATTACK — THE LAST WALL")
    print("=" * 60)

    M, rank, nullity = build_gf2_schedule_matrix()
    find_min_schedule_real(N=500)
    test_schedule_near_collision(N=3000)
    test_schedule_differential_path(N=200)

    print(f"\n{'='*60}")
    print(f"VERDICT: Can the schedule wall be breached?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
