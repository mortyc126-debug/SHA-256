#!/usr/bin/env python3
"""
EXP 159: INVERSE ATTACK — Kill Bits Through Carry Absorption

CONCEPT: Don't match all 256 output bits.
Instead, KILL some bits by forcing them into G/K positions
(where carry is determined). Only match the remaining P-bits.

If nP < 256: birthday on nP bits = 2^(nP/2) < 2^128

HOW TO KILL: Force state to AGREE with IV at specific positions.
  state_bit = IV_bit → G or K → carry determined → bit "dead"
  state_bit ≠ IV_bit → P → carry uncertain → bit "alive"

QUESTION: Can we cheaply find messages where state ≈ IV
at MANY positions? If state agrees with IV on k > 128 positions,
then nP < 128 → birthday < 2^64.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def count_gkp_feedforward(M):
    """Count G, K, P in feedforward GKP(IV, state_64)."""
    states = sha256_rounds(M, 64)
    s = states[64]
    nG = 0; nK = 0; nP = 0
    for w in range(8):
        gkp = carry_gkp_classification(IV[w], s[w])
        nG += gkp.count('G')
        nK += gkp.count('K')
        nP += gkp.count('P')
    return nG, nK, nP

def test_natural_gkp_distribution(N=2000):
    """What's the natural distribution of nP at feedforward?"""
    print(f"\n{'='*60}")
    print(f"NATURAL GKP DISTRIBUTION AT FEEDFORWARD")
    print(f"{'='*60}")

    nPs = []; nGs = []; nKs = []
    for _ in range(N):
        M = random_w16()
        nG, nK, nP = count_gkp_feedforward(M)
        nPs.append(nP); nGs.append(nG); nKs.append(nK)

    pa = np.array(nPs)
    print(f"\n  E[nP] = {pa.mean():.2f} ± {pa.std():.2f}")
    print(f"  E[nG] = {np.mean(nGs):.2f}")
    print(f"  E[nK] = {np.mean(nKs):.2f}")
    print(f"  min(nP) = {pa.min()}")
    print(f"  max(nP) = {pa.max()}")

    # Distribution
    print(f"\n  nP distribution:")
    for threshold in [120, 115, 110, 105, 100, 96]:
        count = np.sum(pa <= threshold)
        pct = count / N * 100
        if count > 0:
            print(f"    nP ≤ {threshold}: {count}/{N} ({pct:.2f}%)")

    # Birthday implication
    print(f"\n  Birthday implications:")
    print(f"    nP = 128 (avg): birthday = 2^{128//2} = 2^64 feedforward bits")
    print(f"    nP = 100:       birthday = 2^{100//2} = 2^50")
    print(f"    nP = 80:        birthday = 2^{80//2} = 2^40")
    print(f"    But full collision needs ALL 256 bits = 0, not just P-bits")

    return pa

def test_can_we_reduce_nP(N=500):
    """Can we find messages with low nP at feedforward?"""
    print(f"\n{'='*60}")
    print(f"REDUCING nP — SEARCHING FOR LOW-P MESSAGES")
    print(f"{'='*60}")

    # Strategy: brute force search for messages with min nP
    best_nP = 256
    best_M = None

    for _ in range(N):
        M = random_w16()
        _, _, nP = count_gkp_feedforward(M)
        if nP < best_nP:
            best_nP = nP
            best_M = list(M)

    print(f"\n  Random search ({N} messages):")
    print(f"    Best nP = {best_nP}")

    # Greedy optimization: start from best, modify one word at a time
    M = list(best_M) if best_M else random_w16()
    for iteration in range(5):
        improved = False
        for w in range(16):
            best_val = M[w]
            for _ in range(200):
                val = random.randint(0, MASK)
                M_test = list(M); M_test[w] = val
                _, _, nP = count_gkp_feedforward(M_test)
                if nP < best_nP:
                    best_nP = nP
                    best_val = val
                    improved = True
            M[w] = best_val
        if not improved:
            break

    print(f"    Greedy optimized nP = {best_nP}")

    # What's the THEORETICAL minimum nP?
    # If state = IV: nP = 0 (all G or K). But state = IV requires
    # round function to return to starting point = fixed point.
    print(f"\n  Theoretical minimum nP = 0 (state = IV)")
    print(f"  Achieved nP = {best_nP}")

    return best_nP, M

def test_inverse_attack_collision(N=20, budget=3000):
    """Use low-nP messages for collision search."""
    print(f"\n{'='*60}")
    print(f"INVERSE ATTACK: COLLISION AMONG LOW-nP MESSAGES")
    print(f"{'='*60}")

    # Strategy: generate messages optimized for low nP,
    # then birthday among them. Lower nP → fewer "hard" bits.

    # Phase 1: collect low-nP messages
    print(f"\n  Phase 1: Collecting low-nP messages...")
    messages = []
    hashes_stored = []
    nPs_stored = []

    for _ in range(budget):
        M = random_w16()
        _, _, nP = count_gkp_feedforward(M)
        H = sha256_compress(M)
        messages.append(M)
        hashes_stored.append(H)
        nPs_stored.append(nP)

    nP_arr = np.array(nPs_stored)
    p25 = np.percentile(nP_arr, 25)

    # Phase 2: birthday among LOW-nP messages only
    low_indices = np.where(nP_arr <= p25)[0]
    n_low = len(low_indices)

    best_low = 256
    for i in range(n_low):
        for j in range(i+1, min(n_low, i+50)):
            idx_i = low_indices[i]; idx_j = low_indices[j]
            dH = sum(hw(hashes_stored[idx_i][w] ^ hashes_stored[idx_j][w]) for w in range(8))
            if dH < best_low: best_low = dH

    # Compare: birthday among ALL messages
    best_all = 256
    for i in range(0, min(budget, 1000)):
        for j in range(i+1, min(i+50, budget)):
            dH = sum(hw(hashes_stored[i][w] ^ hashes_stored[j][w]) for w in range(8))
            if dH < best_all: best_all = dH

    # Compare: birthday among HIGH-nP messages
    high_indices = np.where(nP_arr >= np.percentile(nP_arr, 75))[0]
    n_high = len(high_indices)
    best_high = 256
    for i in range(n_high):
        for j in range(i+1, min(n_high, i+50)):
            idx_i = high_indices[i]; idx_j = high_indices[j]
            dH = sum(hw(hashes_stored[idx_i][w] ^ hashes_stored[idx_j][w]) for w in range(8))
            if dH < best_high: best_high = dH

    avg_nP_low = nP_arr[low_indices].mean()
    avg_nP_high = nP_arr[high_indices].mean()

    print(f"\n  Results:")
    print(f"    Low-nP messages (avg nP={avg_nP_low:.0f}, n={n_low}): best dH = {best_low}")
    print(f"    All messages (avg nP=128, n={min(budget,1000)}): best dH = {best_all}")
    print(f"    High-nP messages (avg nP={avg_nP_high:.0f}, n={n_high}): best dH = {best_high}")

    if best_low < best_all:
        print(f"    ★★★ LOW-nP WINS by {best_all - best_low} bits!")
    elif best_high < best_all:
        print(f"    Unexpected: HIGH-nP wins by {best_all - best_high}")
    else:
        print(f"    No significant difference")

def test_pair_gkp_matching(N=3000):
    """KEY TEST: Do message PAIRS with matching GKP patterns
    have closer hashes than random pairs?"""
    print(f"\n{'='*60}")
    print(f"GKP PATTERN MATCHING BETWEEN PAIRS")
    print(f"{'='*60}")

    # For collision: need s₁ = s₂ → GKP(IV, s₁) = GKP(IV, s₂)
    # → nP₁ = nP₂ AND P-positions identical

    # Easier test: do pairs with similar nP have closer hashes?
    data = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        _, _, nP1 = count_gkp_feedforward(M1)
        _, _, nP2 = count_gkp_feedforward(M2)
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        data.append((abs(nP1 - nP2), dH))

    dnP = np.array([d[0] for d in data])
    dH = np.array([d[1] for d in data])

    corr = np.corrcoef(dnP, dH)[0, 1]
    print(f"\n  corr(|nP₁-nP₂|, dH): {corr:+.6f}")

    # Binned
    close_nP = dH[dnP <= 3].mean()  # Pairs with similar nP
    far_nP = dH[dnP >= 10].mean()   # Pairs with different nP
    print(f"  Similar nP (|Δ|≤3): E[dH] = {close_nP:.1f}")
    print(f"  Different nP (|Δ|≥10): E[dH] = {far_nP:.1f}")

    if close_nP < far_nP - 1:
        print(f"  ★★★ nP-MATCHING BRINGS HASHES CLOSER!")

def test_dead_bit_analysis():
    """Which specific bit positions are most often 'dead' (G/K)?"""
    print(f"\n{'='*60}")
    print(f"DEAD BIT POSITIONS (most often G/K, not P)")
    print(f"{'='*60}")

    dead_counts = np.zeros(256)  # How often each position is G or K

    N = 2000
    for _ in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]
        for w in range(8):
            gkp = carry_gkp_classification(IV[w], s[w])
            for b in range(32):
                if gkp[b] != 'P':
                    dead_counts[w*32 + b] += 1

    dead_counts /= N

    # For random: P(G or K) = P(agree) = 0.5
    print(f"\n  Bit positions most often DEAD (G/K, not P):")
    print(f"  Expected: 0.500 for all (random)")

    most_dead = np.argsort(-dead_counts)[:10]
    least_dead = np.argsort(dead_counts)[:10]

    print(f"\n  MOST dead (easiest to absorb):")
    for idx in most_dead:
        w = idx // 32; b = idx % 32
        print(f"    Word {w} bit {b:>2}: dead {dead_counts[idx]:.4f}")

    print(f"\n  LEAST dead (most alive = hardest):")
    for idx in least_dead:
        w = idx // 32; b = idx % 32
        print(f"    Word {w} bit {b:>2}: dead {dead_counts[idx]:.4f}")

    max_dev = max(abs(dead_counts - 0.5))
    print(f"\n  Max deviation from 0.5: {max_dev:.4f}")
    if max_dev < 0.02:
        print(f"  All positions equally dead (no exploitable bias)")
    else:
        print(f"  ★★★ Some positions preferentially dead!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 159: INVERSE ATTACK — KILL BITS VIA CARRY")
    print("=" * 60)

    nP_dist = test_natural_gkp_distribution(1500)
    best_nP, best_M = test_can_we_reduce_nP(300)
    test_dead_bit_analysis()
    test_pair_gkp_matching(2000)
    test_inverse_attack_collision(N=15, budget=3000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Inverse Attack")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
