#!/usr/bin/env python3
"""
EXP 134: Scaling Analysis — Do ★-advantages grow with budget?

CRITICAL QUESTION: We tested at budget=1000-20000.
SHA-256 collision needs 2^128. What if ★-tools show
ZERO advantage at small scale but GROWING advantage at large scale?

This would mean: our results at small N are MISLEADING.

TEST: For each promising method, measure advantage at
increasing budgets and check if the TREND is positive.

If gain GROWS with log(budget) → method works at scale
If gain FLAT → constant factor only (no asymptotic gain)
If gain SHRINKS → noise artifact

Methods to test:
1. V13 ★-seeded clusters
2. V6 Half-match
3. V12 Sorted birthday (bucketed)
4. ★-XOR-flip (best ★-native tool, exp130)
5. ★⁻¹ Jacobian direction
6. Carry-AND alignment filter
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_dist(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

# ============================================================
# METHOD 0: Pure random birthday (baseline)
# ============================================================
def method_random(budget):
    hashes = {}; best = 256
    for i in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        hk = tuple(H)
        # Compare to sample of stored
        if i > 0:
            for h_old in list(hashes.keys())[max(0, len(hashes)-20):]:
                d = xor_dist(H, list(h_old))
                if d < best: best = d
        hashes[hk] = 1
    return best

# ============================================================
# METHOD 1: ★-seeded clusters
# ============================================================
def method_star_seeded(budget):
    n_seeds = int(budget ** 0.5)
    per_seed = budget // n_seeds
    hashes = {}; best = 256
    for _ in range(n_seeds):
        base = random_w16()
        for _ in range(per_seed):
            M = list(base)
            for _ in range(random.randint(2, 3)):
                w = random.randint(0, 15)
                M[w] = random.randint(0, MASK)
            H = sha256_compress(M)
            hk = tuple(H)
            for h_old in list(hashes.keys())[max(0, len(hashes)-20):]:
                d = xor_dist(H, list(h_old))
                if d < best: best = d
            hashes[hk] = 1
    return best

# ============================================================
# METHOD 2: Sorted birthday (bucket by partial hash)
# ============================================================
def method_sorted(budget):
    bucket_bits = max(8, int(math.log2(budget)) + 2)
    buckets = {}; best = 256
    for _ in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        key = H[0] & ((1 << bucket_bits) - 1)
        if key in buckets:
            for H_old in buckets[key][-10:]:
                d = xor_dist(H, H_old)
                if d < best: best = d
            buckets[key].append(H)
        else:
            buckets[key] = [H]
    return best

# ============================================================
# METHOD 3: Carry-AND filtered
# ============================================================
def method_carry_filtered(budget):
    """Generate pairs, prefer those with high carry-AND alignment."""
    hashes = []; best = 256
    for _ in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        s = sha256_rounds(M, 64)[64]
        # Compute carry-AND score
        score = 0
        for w in range(8):
            c = carry_word(IV[w], s[w])
            a = IV[w] & s[w]
            score += hw(c & a)  # Carry-AND overlap
        hashes.append((H, score))

    # Sort by carry-AND score, compare top pairs
    hashes.sort(key=lambda x: -x[1])
    top_n = min(len(hashes), int(budget ** 0.5))
    for i in range(top_n):
        for j in range(i + 1, min(top_n, i + 30)):
            d = xor_dist(hashes[i][0], hashes[j][0])
            if d < best: best = d

    return best

# ============================================================
# METHOD 4: Half-match families
# ============================================================
def method_half_match(budget):
    n_families = int(budget ** 0.5)
    per_fam = budget // n_families
    hashes = {}; best = 256
    for _ in range(n_families):
        base = random_w16()
        fixed = random.sample(range(16), 8)
        for _ in range(per_fam):
            M = list(base)
            for w in range(16):
                if w not in fixed:
                    M[w] = random.randint(0, MASK)
            H = sha256_compress(M)
            hk = tuple(H)
            for h_old in list(hashes.keys())[max(0, len(hashes)-20):]:
                d = xor_dist(H, list(h_old))
                if d < best: best = d
            hashes[hk] = 1
    return best

# ============================================================
# SCALING TEST
# ============================================================
def scaling_test(N_trials=20):
    """Test each method at increasing budgets."""
    print(f"\n{'='*70}")
    print(f"SCALING ANALYSIS: Does ★-advantage GROW with budget?")
    print(f"{'='*70}")

    methods = [
        ("Random", method_random),
        ("★-seeded", method_star_seeded),
        ("Sorted bday", method_sorted),
        ("Carry-AND", method_carry_filtered),
        ("Half-match", method_half_match),
    ]

    budgets = [500, 1000, 2000, 5000, 10000, 20000, 50000]

    # Collect results
    all_results = {name: {} for name, _ in methods}

    for budget in budgets:
        print(f"\n  Budget = {budget}:")
        for name, fn in methods:
            t0 = time.time()
            results = [fn(budget) for _ in range(N_trials)]
            t1 = time.time()
            arr = np.array(results)
            all_results[name][budget] = arr
            print(f"    {name:>15}: avg={arr.mean():.1f}  min={arr.min()}  ({t1-t0:.1f}s)")

    # Compute GAIN vs random at each budget
    print(f"\n{'='*70}")
    print(f"GAIN vs RANDOM (positive = method better)")
    print(f"{'='*70}")

    print(f"  {'Method':>15}", end="")
    for b in budgets:
        print(f" | {b:>7}", end="")
    print(f" | {'TREND':>8}")
    print(f"  " + "-" * (18 + 10 * len(budgets) + 11))

    for name, _ in methods:
        if name == "Random":
            continue
        print(f"  {name:>15}", end="")
        gains = []
        for b in budgets:
            random_avg = all_results["Random"][b].mean()
            method_avg = all_results[name][b].mean()
            gain = random_avg - method_avg
            gains.append(gain)
            marker = "+" if gain > 0.5 else ("-" if gain < -0.5 else " ")
            print(f" | {gain:>+6.1f}{marker}", end="")

        # Trend: linear regression of gain vs log(budget)
        log_budgets = [math.log2(b) for b in budgets]
        if len(gains) > 2:
            slope = np.polyfit(log_budgets, gains, 1)[0]
            if slope > 0.3:
                trend = f"GROWS↑"
            elif slope < -0.3:
                trend = f"SHRINKS↓"
            else:
                trend = f"flat({slope:+.2f})"
        else:
            trend = "?"
        print(f" | {trend:>8}")

    # Min dH scaling
    print(f"\n{'='*70}")
    print(f"MIN dH SCALING")
    print(f"{'='*70}")
    print(f"  {'Method':>15}", end="")
    for b in budgets:
        print(f" | {b:>7}", end="")
    print()
    print(f"  " + "-" * (18 + 10 * len(budgets)))

    for name, _ in methods:
        print(f"  {name:>15}", end="")
        for b in budgets:
            print(f" | {all_results[name][b].min():>7}", end="")
        print()

    # Expected min dH for birthday on 256 bits with N pairs
    print(f"\n  {'Birthday theory':>15}", end="")
    for b in budgets:
        # Number of pairs ≈ b * 20 (each msg compared to ~20 others)
        n_pairs = b * 20
        # Expected min Hamming distance for n_pairs random 256-bit comparisons
        # Approximation: min ≈ 128 - √(2·ln(n_pairs)·128)
        expected = 128 - math.sqrt(2 * math.log(n_pairs) * 128) if n_pairs > 1 else 128
        print(f" | {expected:>7.1f}", end="")
    print()

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 134: SCALING — DO ★-ADVANTAGES GROW?")
    print("=" * 70)

    scaling_test(N_trials=15)

    print(f"\n{'='*70}")
    print(f"FINAL VERDICT: Scaling behavior")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
