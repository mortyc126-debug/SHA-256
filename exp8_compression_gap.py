#!/usr/bin/env python3
"""
EXPERIMENT 8: Carry Compression Gap — Rare High-Compression Pairs

Carry algebra gives 93% theoretical compression, but SHA-256 schedule
(through rotation) destroys this to 2.6% average compression.

The GAP is 90.4%. But this is an AVERAGE. Question:
What is the TAIL of the compression distribution?
If P(compression > 50%) = 2^{-k}, and this gives speedup 2^c,
then c > k means we win.

We define carry compression as the fraction of carry bits that can be
predicted from the GKP classification alone (without knowing actual values).
"""

import sys, os, random, math
from collections import Counter
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_compression_single_add(a, b):
    """
    Measure carry compression for a single addition a+b.
    Compression = fraction of carry bits determined by GKP alone.
    G positions: carry=1 (determined), K positions: carry=0 (determined),
    P positions: carry depends on previous (not determined without cascade).
    """
    n = 32
    gkp = carry_gkp_classification(a, b, n)

    determined = sum(1 for c in gkp if c in ('G', 'K'))
    return determined / n  # Fraction of determined positions

def carry_compression_round(state, W_r, K_r):
    """
    Measure total carry compression across all additions in one SHA-256 round.
    Returns (total_determined, total_positions, compression_rate).
    """
    a, b, c, d, e, f, g, h = state

    additions = []

    # T1 = h + Σ1(e) + Ch(e,f,g) + K_r + W_r (4 additions)
    sig1_e = sigma1(e)
    sum1 = (h + sig1_e) & MASK
    additions.append((h, sig1_e))

    ch_val = ch(e, f, g)
    sum2 = (sum1 + ch_val) & MASK
    additions.append((sum1, ch_val))

    sum3 = (sum2 + K_r) & MASK
    additions.append((sum2, K_r))

    T1 = (sum3 + W_r) & MASK
    additions.append((sum3, W_r))

    # T2 = Σ0(a) + Maj(a,b,c) (1 addition)
    sig0_a = sigma0(a)
    maj_val = maj(a, b, c)
    additions.append((sig0_a, maj_val))

    # a_new = T1 + T2 (1 addition)
    T2 = (sig0_a + maj_val) & MASK
    additions.append((T1, T2))

    # e_new = d + T1 (1 addition)
    additions.append((d, T1))

    total_determined = 0
    total_positions = 0

    for x, y in additions:
        comp = carry_compression_single_add(x, y)
        total_determined += comp * 32
        total_positions += 32

    return total_determined, total_positions, total_determined / total_positions

def carry_compression_full(W16):
    """
    Measure carry compression across all 64 rounds of SHA-256.
    Returns per-round compression and total.
    """
    states = sha256_rounds(W16, 64)
    W = schedule(W16)

    per_round = []
    total_det = 0
    total_pos = 0

    for r in range(64):
        det, pos, comp = carry_compression_round(states[r], W[r], K[r])
        per_round.append(comp)
        total_det += det
        total_pos += pos

    return per_round, total_det / total_pos

def test_compression_distribution(N=5000):
    """Test the distribution of carry compression across random messages."""
    print("\n--- TEST 1: COMPRESSION DISTRIBUTION ---")

    total_compressions = []
    round_compressions = {r: [] for r in range(64)}

    for _ in range(N):
        W16 = random_w16()
        per_round, total = carry_compression_full(W16)
        total_compressions.append(total)
        for r, c in enumerate(per_round):
            round_compressions[r].append(c)

    tc = np.array(total_compressions)
    print(f"Overall compression: mean={tc.mean():.6f}, std={tc.std():.6f}")
    print(f"Min={tc.min():.6f}, Max={tc.max():.6f}")
    print(f"Theoretical max (all G/K): 1.0")
    print(f"Expected (50% P): 0.5")

    # Percentiles
    for p in [90, 95, 99, 99.9]:
        val = np.percentile(tc, p)
        print(f"  {p}th percentile: {val:.6f}")

    # Per-round analysis
    print(f"\n{'Round':>5} | {'Mean comp':>10} | {'Std':>8} | {'Max':>8} | {'P(>0.6)':>10}")
    print("-" * 50)
    for r in [0, 1, 2, 3, 4, 5, 8, 16, 32, 48, 63]:
        rc = np.array(round_compressions[r])
        p_high = np.mean(rc > 0.6)
        print(f"{r:>5} | {rc.mean():>10.6f} | {rc.std():>8.4f} | {rc.max():>8.4f} | {p_high:>10.6f}")

    return tc

def test_wang_pair_compression(N=3000):
    """Compare compression between normal messages and Wang cascade pairs."""
    print("\n--- TEST 2: WANG PAIR COMPRESSION ---")

    normal_comp = []
    wang_n_comp = []
    wang_f_comp = []

    for _ in range(N):
        # Normal message
        W16 = random_w16()
        _, total = carry_compression_full(W16)
        normal_comp.append(total)

        # Wang cascade pair
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        _, total_n = carry_compression_full(Wn)
        _, total_f = carry_compression_full(Wf)
        wang_n_comp.append(total_n)
        wang_f_comp.append(total_f)

    normal_arr = np.array(normal_comp)
    wang_n_arr = np.array(wang_n_comp)
    wang_f_arr = np.array(wang_f_comp)

    print(f"Normal messages:  mean={normal_arr.mean():.6f}, std={normal_arr.std():.6f}")
    print(f"Wang Wn:          mean={wang_n_arr.mean():.6f}, std={wang_n_arr.std():.6f}")
    print(f"Wang Wf:          mean={wang_f_arr.mean():.6f}, std={wang_f_arr.std():.6f}")

    diff_nw = wang_n_arr.mean() - normal_arr.mean()
    print(f"\nDifference (Wang - Normal): {diff_nw:+.6f}")

    if abs(diff_nw) > 2 * normal_arr.std() / np.sqrt(N):
        print("*** SIGNAL: Wang pairs have significantly different compression! ***")

def test_high_compression_search(N=10000):
    """
    Actively search for messages with abnormally high carry compression.
    These are the "rare pairs" where schedule creates high compression.
    """
    print("\n--- TEST 3: HIGH COMPRESSION SEARCH ---")

    # Strategy: hill-climb on compression
    best_compression = 0
    best_W = None

    compressions = []

    for i in range(N):
        W16 = random_w16()
        _, total = carry_compression_full(W16)
        compressions.append(total)

        if total > best_compression:
            best_compression = total
            best_W = list(W16)

    compressions = np.array(compressions)

    print(f"Best compression found: {best_compression:.6f}")
    print(f"Mean: {compressions.mean():.6f}")
    print(f"Best message: W[0]=0x{best_W[0]:08x}")

    # Now try local search around the best
    print("\nLocal search around best...")
    current_W = list(best_W)
    current_comp = best_compression

    improvements = 0
    for step in range(5000):
        # Mutate one word
        word_idx = random.randint(0, 15)
        bit_idx = random.randint(0, 31)

        trial_W = list(current_W)
        trial_W[word_idx] ^= (1 << bit_idx)

        _, trial_comp = carry_compression_full(trial_W)

        if trial_comp > current_comp:
            current_comp = trial_comp
            current_W = trial_W
            improvements += 1

    print(f"After local search: {current_comp:.6f} ({improvements} improvements)")
    print(f"Gain over random best: {current_comp - best_compression:+.6f}")

    # What does this compression imply for collision cost?
    # If compression = c, then effective carry bits = (1-c) * total_carry_bits
    total_carry_bits = 7 * 32 * 64  # 7 adds per round × 32 bits × 64 rounds
    effective_bits_random = (1 - compressions.mean()) * total_carry_bits
    effective_bits_best = (1 - current_comp) * total_carry_bits

    print(f"\nTotal carry bit positions: {total_carry_bits}")
    print(f"Effective carry bits (random): {effective_bits_random:.0f}")
    print(f"Effective carry bits (best): {effective_bits_best:.0f}")
    print(f"Bit savings: {effective_bits_random - effective_bits_best:.0f}")

    return current_comp, compressions.mean()

def test_compression_collision_correlation(N=3000):
    """
    Key test: does high carry compression correlate with
    better collision properties (lower HW of δH)?
    """
    print("\n--- TEST 4: COMPRESSION → COLLISION CORRELATION ---")

    data = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # Compression of normal message
        _, comp_n = carry_compression_full(Wn)

        # Hash difference
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        hw_delta = sum(hw(d) for d in delta_H)

        # De17
        De17 = de(states_n, states_f, 17)
        hw17 = hw(De17)

        data.append((comp_n, hw_delta, hw17))

    comp_arr = np.array([d[0] for d in data])
    hw_arr = np.array([d[1] for d in data])
    hw17_arr = np.array([d[2] for d in data])

    corr_comp_hw = np.corrcoef(comp_arr, hw_arr)[0, 1]
    corr_comp_hw17 = np.corrcoef(comp_arr, hw17_arr)[0, 1]

    print(f"corr(compression, HW(δH)):   {corr_comp_hw:+.6f}")
    print(f"corr(compression, HW(De17)): {corr_comp_hw17:+.6f}")

    # Split into high/low compression and compare
    median_comp = np.median(comp_arr)
    high_comp_hw = hw_arr[comp_arr > median_comp]
    low_comp_hw = hw_arr[comp_arr <= median_comp]

    print(f"\nHigh compression half: E[HW(δH)] = {high_comp_hw.mean():.2f}")
    print(f"Low compression half:  E[HW(δH)] = {low_comp_hw.mean():.2f}")
    print(f"Difference: {high_comp_hw.mean() - low_comp_hw.mean():+.4f}")

    threshold = 2 / np.sqrt(N)
    if abs(corr_comp_hw) > threshold:
        print(f"*** SIGNAL: Compression correlates with δH! (>{threshold:.4f}) ***")
    if abs(corr_comp_hw17) > threshold:
        print(f"*** SIGNAL: Compression correlates with De17! (>{threshold:.4f}) ***")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 8: CARRY COMPRESSION GAP")
    print("=" * 70)

    tc = test_compression_distribution(3000)
    test_wang_pair_compression(2000)
    best, avg = test_high_compression_search(5000)
    test_compression_collision_correlation(2000)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Compression gap: {(best - avg)/avg * 100:.1f}% above average achievable")
    print(f"Best compression: {best:.6f} (theoretical max: 1.0)")
    print(f"Average compression: {avg:.6f}")

if __name__ == "__main__":
    main()
