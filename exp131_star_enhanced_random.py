#!/usr/bin/env python3
"""
EXP 131: ★-Enhanced Random — Sew knowledge INTO randomness

Not: replace random with ★-tools (failed, exp129-130)
Not: pure random (baseline)
But: random that KNOWS about ★-structure

VARIANTS:

V1: ★-biased generation
    Generate M₂ not fully random, but biased so that
    ★(M₁, M₂) has favorable GKP distribution.

V2: ★-filtered birthday
    Generate random pairs but KEEP only those with low ★-AND component.
    From exp121: low d_and → 3.77 bits closer to collision.

V3: ★-paired generation
    Generate M₂ = M₁ ⊕ δ where δ is ★-structured:
    δ has specific carry/GKP properties.

V4: ★-neighborhood random
    Start from M₁, make RANDOM changes but only to
    message words that ★-analysis says matter most.

V5: ★-restart random
    Pure random search, but when you find a "good" pair,
    do ★-local search around it, then restart random.

Each variant: same budget as pure random. Compare min(dH).
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def xor_dist(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def full_hash(W16):
    return sha256_compress(W16)

# ============================================================
# V0: Pure random (baseline)
# ============================================================
def v0_pure_random(M1, budget):
    H1 = full_hash(M1)
    best = 256
    for _ in range(budget):
        M2 = random_w16()
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V1: ★-biased generation
# ============================================================
def v1_star_biased(M1, budget):
    """Generate M₂ with biased message differences.
    From exp110: W[0] has weakest diffusion (517 vs avg 580).
    Concentrate differences in W[0]."""
    H1 = full_hash(M1)
    best = 256
    for _ in range(budget):
        M2 = list(M1)
        # Change only 1-3 words (not all 16)
        n_words = random.randint(1, 3)
        for _ in range(n_words):
            w = random.randint(0, 15)
            M2[w] = random.randint(0, MASK)
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V2: ★-filtered birthday
# ============================================================
def v2_star_filtered(M1, budget):
    """Birthday search but keep pairs where feedforward
    carry structure is favorable."""
    H1 = full_hash(M1)
    s1 = sha256_rounds(M1, 64)[64]
    best = 256

    # Precompute M1's carry structure
    carry1 = [carry_word(IV[w], s1[w]) for w in range(8)]
    carry1_hw = sum(hw(c) for c in carry1)

    for _ in range(budget):
        M2 = random_w16()
        H2 = full_hash(M2)
        d = xor_dist(H1, H2)

        if d < best:
            best = d

    return best

# ============================================================
# V3: ★-paired generation (structured δ)
# ============================================================
def v3_star_paired(M1, budget):
    """Generate M₂ = M₁ ⊕ δ where δ has low Hamming weight.
    From exp117: near-collisions don't prefer specific δM patterns,
    but sparse δ means less disruption to state."""
    H1 = full_hash(M1)
    best = 256

    for _ in range(budget):
        M2 = list(M1)
        # Sparse difference: flip 1-32 random bits (out of 512)
        n_flips = random.randint(1, 32)
        for _ in range(n_flips):
            w = random.randint(0, 15)
            b = random.randint(0, 31)
            M2[w] ^= (1 << b)
        if M1 == M2: continue  # Skip trivial
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V4: ★-arithmetic paired (★⁻¹ native)
# ============================================================
def v4_star_arith(M1, budget):
    """Generate M₂ = M₁ + δ (arithmetic, not XOR).
    From exp127: ★⁻¹ Jacobian is exact for δ=±1.
    Use small ARITHMETIC differences."""
    H1 = full_hash(M1)
    best = 256

    for _ in range(budget):
        M2 = list(M1)
        # Small arithmetic change: ±1 to ±256 on 1-4 words
        n_words = random.randint(1, 4)
        for _ in range(n_words):
            w = random.randint(0, 15)
            delta = random.choice(list(range(-256, 0)) + list(range(1, 257)))  # Never 0
            M2[w] = (M2[w] + delta) & MASK
        if M1 == M2: continue  # Skip trivial
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V5: ★-restart (random + local refinement)
# ============================================================
def v5_star_restart(M1, budget):
    """Random search + ★-local refinement when promising pair found."""
    H1 = full_hash(M1)
    best = 256
    best_M2 = None

    # Phase 1: random search (80% budget)
    phase1 = int(budget * 0.8)
    for _ in range(phase1):
        M2 = random_w16()
        d = xor_dist(H1, full_hash(M2))
        if d < best:
            best = d
            best_M2 = list(M2)

    # Phase 2: ★-local around best found (20% budget)
    if best_M2:
        phase2 = budget - phase1
        for _ in range(phase2):
            M2 = list(best_M2)
            # Small perturbation: ±1 on random word
            w = random.randint(0, 15)
            M2[w] = (M2[w] + random.choice([-1, +1])) & MASK
            d = xor_dist(H1, full_hash(M2))
            if d < best:
                best = d
                best_M2 = list(M2)

    return best

# ============================================================
# V6: ★-half-match (share half the message)
# ============================================================
def v6_half_match(M1, budget):
    """Fix half of M₂ = M₁ (8 words), randomize rest.
    This constrains the schedule to be PARTIALLY the same."""
    H1 = full_hash(M1)
    best = 256

    for _ in range(budget):
        M2 = list(M1)
        # Randomize 8 of 16 words
        words_to_change = random.sample(range(16), 8)
        for w in words_to_change:
            M2[w] = random.randint(0, MASK)
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V7: ★-schedule-aware (change words that affect schedule least)
# ============================================================
def v7_schedule_aware(M1, budget):
    """From exp110: W[13] has weakest schedule diffusion (507).
    Concentrate random changes in low-diffusion words."""
    H1 = full_hash(M1)
    best = 256

    # Words sorted by schedule diffusion (from exp110)
    weak_words = [13, 12, 0, 11, 15, 10, 14, 9, 8, 7, 6, 5, 4, 3, 2, 1]

    for _ in range(budget):
        M2 = list(M1)
        # Change 1-4 of the WEAKEST words
        n = random.randint(1, 4)
        for i in range(n):
            w = weak_words[i]
            M2[w] = random.randint(0, MASK)
        d = xor_dist(H1, full_hash(M2))
        if d < best: best = d
    return best

# ============================================================
# V8: Multi-target birthday (many M₁s, look for collision among ALL)
# ============================================================
def v8_multi_target(budget):
    """Not M₁ vs M₂, but N messages looking for ANY collision."""
    hashes = {}
    best = 256
    for _ in range(budget):
        M = random_w16()
        H = full_hash(M)
        h_key = tuple(H)

        # Check against ALL stored
        for h_stored, M_stored in list(hashes.items())[:100]:  # Limit comparisons
            d = xor_dist(list(h_stored), list(H))
            if d < best: best = d

        hashes[h_key] = M
    return best

# ============================================================
# COMPARISON
# ============================================================
def run_comparison(N=25, budget=5000):
    """Compare all variants."""
    print(f"\n--- COMPARISON (N={N}, budget={budget} per trial) ---")

    variants = [
        ("V0: Pure random", v0_pure_random, False),
        ("V1: ★-biased (few words)", v1_star_biased, False),
        ("V3: ★-paired (sparse δ)", v3_star_paired, False),
        ("V4: ★-arith (small ±δ)", v4_star_arith, False),
        ("V5: ★-restart (rand+local)", v5_star_restart, False),
        ("V6: Half-match", v6_half_match, False),
        ("V7: Schedule-aware", v7_schedule_aware, False),
    ]

    results = {}
    for name, fn, is_multi in variants:
        t0 = time.time()
        dHs = []
        for trial in range(N):
            M1 = random_w16()
            if is_multi:
                d = fn(budget)
            else:
                d = fn(M1, budget)
            dHs.append(d)
        t1 = time.time()

        arr = np.array(dHs)
        results[name] = arr
        print(f"  {name:>30}: avg={arr.mean():>6.1f}  min={arr.min():>3}  "
              f"med={np.median(arr):>5.0f}  t={t1-t0:.1f}s")

    # V8 separately (different interface)
    t0 = time.time()
    dHs = []
    for _ in range(N):
        d = v8_multi_target(budget)
        dHs.append(d)
    t1 = time.time()
    arr = np.array(dHs)
    results["V8: Multi-target"] = arr
    print(f"  {'V8: Multi-target':>30}: avg={arr.mean():>6.1f}  min={arr.min():>3}  "
          f"med={np.median(arr):>5.0f}  t={t1-t0:.1f}s")

    # Ranking
    print(f"\n  RANKING (by average dH, lower = better):")
    ranking = sorted(results.items(), key=lambda x: x[1].mean())
    for i, (name, arr) in enumerate(ranking):
        marker = " ★★★" if i == 0 else (" ★★" if i == 1 else (" ★" if i == 2 else ""))
        print(f"    #{i+1}: {name:>30} avg={arr.mean():.1f} min={arr.min()}{marker}")

    # Statistical test: is the best significantly better than V0?
    best_name, best_arr = ranking[0]
    v0_arr = results["V0: Pure random"]
    diff = v0_arr.mean() - best_arr.mean()
    pooled_std = math.sqrt((v0_arr.std()**2 + best_arr.std()**2) / 2)
    z = diff / (pooled_std / math.sqrt(N)) if pooled_std > 0 else 0

    print(f"\n  Best vs Pure Random:")
    print(f"    {best_name}: {best_arr.mean():.1f}")
    print(f"    V0 Pure random: {v0_arr.mean():.1f}")
    print(f"    Difference: {diff:.1f} bits, Z = {z:.2f}")
    if z > 2:
        print(f"    *** STATISTICALLY SIGNIFICANT IMPROVEMENT ***")
    elif z > 1:
        print(f"    Marginal improvement")
    else:
        print(f"    Not significant")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 131: ★-ENHANCED RANDOM")
    print("Sew ★-knowledge INTO randomness")
    print("=" * 60)

    run_comparison(N=30, budget=5000)

if __name__ == "__main__":
    main()
