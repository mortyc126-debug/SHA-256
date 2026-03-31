#!/usr/bin/env python3
"""
EXP 137: Minimum Schedule Difference — Slowest ★-Invariant Decay

THEORY: |I_r| decays at rate α(δW) per round.
  α depends on the SCHEDULE DIFFERENCE δW_0...δW_63.
  δW is determined by δM through the schedule recurrence.
  E[α] = 6.5 bits/round (exp136).

QUESTION: What δM minimizes Σ HW(δW_r)?
  Minimum total schedule weight → slowest invariant decay
  → longest-lived ★-invariant → possible cheap predictor

The schedule is GF(2)-linear in δM (XOR part).
  δW_t = σ₁(δW_{t-2}) ⊕ δW_{t-7} ⊕ σ₀(δW_{t-15}) ⊕ δW_{t-16}

So: total_HW(δW) = Σ_{t=0}^{63} HW(δW_t) is a function of δM.
Minimize over all δM ≠ 0.

ALSO: measure actual |I_r| decay for the OPTIMAL δM.
Does slow schedule → slow invariant decay?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def gf2_schedule_diff(dM):
    """GF(2)-linear schedule difference."""
    dW = list(dM) + [0] * 48
    for t in range(16, 64):
        dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]
    return dW

def total_schedule_weight(dM):
    """Total Hamming weight of schedule difference."""
    dW = gf2_schedule_diff(dM)
    return sum(hw(dW[t]) for t in range(64))

def find_min_schedule_diff():
    """Find δM with minimum total schedule HW."""
    print(f"\n--- MINIMUM SCHEDULE DIFFERENCE ---")

    # Method 1: Test all single-bit δM (512 candidates)
    print(f"\n  Single-bit δM (512 candidates):")
    results_1bit = []
    for w in range(16):
        for b in range(32):
            dM = [0] * 16
            dM[w] = 1 << b
            tw = total_schedule_weight(dM)
            results_1bit.append((tw, w, b))

    results_1bit.sort()
    print(f"  Top 10 lightest single-bit diffs:")
    for tw, w, b in results_1bit[:10]:
        dM = [0] * 16; dM[w] = 1 << b
        dW = gf2_schedule_diff(dM)
        # Show per-round weight
        round_hws = [hw(dW[t]) for t in range(64)]
        zero_rounds = sum(1 for h in round_hws if h == 0)
        print(f"    W[{w}] bit {b:>2}: total_HW = {tw:>4}, zero_rounds = {zero_rounds}")

    best_1bit = results_1bit[0]
    worst_1bit = results_1bit[-1]
    avg_1bit = np.mean([r[0] for r in results_1bit])
    print(f"\n  Best:  W[{best_1bit[1]}] bit {best_1bit[2]}, HW = {best_1bit[0]}")
    print(f"  Worst: W[{worst_1bit[1]}] bit {worst_1bit[2]}, HW = {worst_1bit[0]}")
    print(f"  Average: {avg_1bit:.1f}")
    print(f"  Ratio worst/best: {worst_1bit[0]/best_1bit[0]:.2f}")

    # Method 2: Test random multi-bit δM
    print(f"\n  Random multi-bit δM (10000 candidates):")
    results_multi = []
    for _ in range(10000):
        dM = [0] * 16
        # 1-4 bits flipped
        n_bits = random.randint(1, 4)
        for _ in range(n_bits):
            w = random.randint(0, 15)
            b = random.randint(0, 31)
            dM[w] ^= (1 << b)
        if all(d == 0 for d in dM):
            continue
        tw = total_schedule_weight(dM)
        results_multi.append((tw, list(dM)))

    results_multi.sort()
    print(f"  Best multi-bit: HW = {results_multi[0][0]}")
    print(f"  Worst multi-bit: HW = {results_multi[-1][0]}")

    # Method 3: XOR combinations of good single-bit diffs
    print(f"\n  Combinations of best single-bit diffs:")
    top_singles = results_1bit[:20]
    combo_results = []
    for i in range(len(top_singles)):
        for j in range(i+1, len(top_singles)):
            dM = [0] * 16
            dM[top_singles[i][1]] ^= (1 << top_singles[i][2])
            dM[top_singles[j][1]] ^= (1 << top_singles[j][2])
            if all(d == 0 for d in dM):
                continue
            tw = total_schedule_weight(dM)
            combo_results.append((tw, top_singles[i], top_singles[j]))

    combo_results.sort()
    if combo_results:
        print(f"  Best combo: HW = {combo_results[0][0]}")
        print(f"    = W[{combo_results[0][1][1]}]b{combo_results[0][1][2]} ⊕ W[{combo_results[0][2][1]}]b{combo_results[0][2][2]}")

    return results_1bit[0], results_1bit[-1]

def analyze_best_diff(best_info):
    """Detailed analysis of the best δM."""
    tw, w_best, b_best = best_info
    print(f"\n--- ANALYSIS OF BEST δM: W[{w_best}] bit {b_best} ---")

    dM = [0] * 16; dM[w_best] = 1 << b_best
    dW = gf2_schedule_diff(dM)

    print(f"\n  Per-round schedule diff HW:")
    print(f"  {'Round':>6} | {'HW(δW)':>6} | {'Cumulative':>10} | {'Bar'}")
    print(f"  " + "-" * 45)

    cumulative = 0
    for r in range(64):
        h = hw(dW[r])
        cumulative += h
        bar = "█" * min(h, 40)
        if r < 20 or h > 0:
            print(f"  {r:>6} | {h:>6} | {cumulative:>10} | {bar}")

    # Rounds with zero diff
    zero_rounds = [r for r in range(64) if hw(dW[r]) == 0]
    print(f"\n  Zero-diff rounds: {zero_rounds}")
    print(f"  Count: {len(zero_rounds)}/64")

    # Which rounds have the heaviest diff?
    heavy = sorted(range(64), key=lambda r: -hw(dW[r]))[:5]
    print(f"  Heaviest rounds: {[(r, hw(dW[r])) for r in heavy]}")

def test_invariant_with_best_diff(best_info, N=300):
    """Does the best δM actually lead to slower invariant decay?"""
    tw, w_best, b_best = best_info
    print(f"\n--- INVARIANT DECAY WITH BEST δM (N={N}) ---")

    # Best δM
    all_I_best = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        M2[w_best] ^= (1 << b_best)

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        for r in range(65):
            match = sum(32 - hw(s1[r][w] ^ s2[r][w]) for w in range(8))
            all_I_best[trial, r] = match

    # Random single-bit δM (average case)
    all_I_rand = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        w_r = random.randint(0, 15)
        b_r = random.randint(0, 31)
        M2[w_r] ^= (1 << b_r)

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        for r in range(65):
            match = sum(32 - hw(s1[r][w] ^ s2[r][w]) for w in range(8))
            all_I_rand[trial, r] = match

    # Worst δM
    # Find it
    worst_results = []
    for w in range(16):
        for b in range(32):
            dM = [0]*16; dM[w] = 1 << b
            worst_results.append((total_schedule_weight(dM), w, b))
    worst_results.sort(reverse=True)
    tw_w, w_worst, b_worst = worst_results[0]

    all_I_worst = np.zeros((N, 65))
    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        M2[w_worst] ^= (1 << b_worst)

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        for r in range(65):
            match = sum(32 - hw(s1[r][w] ^ s2[r][w]) for w in range(8))
            all_I_worst[trial, r] = match

    print(f"  Best δM: W[{w_best}] bit {b_best} (schedule HW = {tw})")
    print(f"  Worst δM: W[{w_worst}] bit {b_worst} (schedule HW = {tw_w})")
    print(f"  Random: average single-bit")

    print(f"\n  {'Round':>6} | {'Best |I|':>9} | {'Random |I|':>10} | {'Worst |I|':>10} | {'Best-Rand':>10}")
    print(f"  " + "-" * 58)

    for r in [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 32, 64]:
        b_avg = all_I_best[:, r].mean()
        r_avg = all_I_rand[:, r].mean()
        w_avg = all_I_worst[:, r].mean()
        diff = b_avg - r_avg
        print(f"  {r:>6} | {b_avg:>9.2f} | {r_avg:>10.2f} | {w_avg:>10.2f} | {diff:>+10.2f}")

    # KEY: at which round does BEST still have |I| > 140 (significantly above 128)?
    print(f"\n  Round where |I| first drops below 140:")
    for label, arr in [("Best", all_I_best), ("Random", all_I_rand), ("Worst", all_I_worst)]:
        for r in range(65):
            if arr[:, r].mean() < 140:
                print(f"    {label:>8}: round {r}")
                break

    # Decay rate comparison
    for label, arr in [("Best", all_I_best), ("Random", all_I_rand), ("Worst", all_I_worst)]:
        rates = []
        for r in range(1, 21):
            rate = (arr[:, 0].mean() - arr[:, r].mean()) / r
            rates.append(rate)
        avg_rate = np.mean(rates[-5:])  # Average over rounds 16-20
        print(f"    {label:>8}: avg decay rate (r=16-20) = {avg_rate:.2f} bits/round")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 137: MINIMUM SCHEDULE DIFFERENCE")
    print("Find δM that slows ★-invariant decay")
    print("=" * 60)

    best, worst = find_min_schedule_diff()
    analyze_best_diff(best)
    test_invariant_with_best_diff(best, N=200)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
