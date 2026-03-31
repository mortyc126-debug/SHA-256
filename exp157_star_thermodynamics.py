#!/usr/bin/env python3
"""
EXP 157: ★-THERMODYNAMICS — Chain Entropy as Second Law

From exp156: near-collisions have LOW chain entropy (Z=-23.7).
Collision = ordered state. Random hash = chaos.

QUESTION: Does chain entropy ALWAYS INCREASE through SHA-256 rounds?
  If YES → "second law" of SHA-256 → collision gets harder each round
  If NO  → entropy can DECREASE → conditions for decrease = attack vector

ALSO: Minimum entropy of collision. What's the lowest possible?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def chain_spectrum(a, b):
    """P-chain lengths in GKP(a,b)."""
    gkp = carry_gkp_classification(a, b)
    chains = []
    current = 0
    for c in gkp:
        if c == 'P':
            current += 1
        else:
            if current > 0:
                chains.append(current)
            current = 0
    if current > 0:
        chains.append(current)
    return sorted(chains, reverse=True)

def chain_entropy(s1, s2):
    """Total chain entropy across all 8 state words."""
    total_ent = 0
    total_chains = 0
    total_max = 0
    for w in range(8):
        spec = chain_spectrum(s1[w], s2[w])
        total = sum(spec) if spec else 0
        if total > 0:
            probs = [s / total for s in spec]
            ent = -sum(p * math.log2(p) for p in probs if p > 0)
            total_ent += ent
        total_chains += len(spec)
        if spec:
            total_max = max(total_max, spec[0])
    return total_ent, total_chains, total_max

def test_entropy_flow(N=300):
    """Track chain entropy through all 64 rounds."""
    print(f"\n{'='*60}")
    print(f"★-ENTROPY FLOW THROUGH ROUNDS (N={N})")
    print(f"{'='*60}")

    # Case 1: 1-bit difference
    print(f"\n  Case 1: 1-bit message difference")
    print(f"  {'Round':>6} | {'Entropy':>8} | {'Chains':>7} | {'MaxChain':>8} | {'ΔEntropy':>9}")
    print(f"  " + "-" * 50)

    prev_ent = 0
    for R in range(0, 65):
        if R > 20 and R < 60 and R % 8 != 0:
            continue

        ents = []; chains_all = []; maxcs = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]
            ent, nc, mc = chain_entropy(s1, s2)
            ents.append(ent); chains_all.append(nc); maxcs.append(mc)

        avg_ent = np.mean(ents); avg_nc = np.mean(chains_all); avg_mc = np.mean(maxcs)
        delta_ent = avg_ent - prev_ent if R > 0 else 0

        marker = ""
        if delta_ent < -0.1:
            marker = " ← ENTROPY DECREASE!"

        print(f"  {R:>6} | {avg_ent:>8.3f} | {avg_nc:>7.1f} | {avg_mc:>8.2f} | {delta_ent:>+9.3f}{marker}")
        prev_ent = avg_ent

def test_entropy_decrease_conditions(N=500):
    """Under what conditions does chain entropy DECREASE between rounds?"""
    print(f"\n{'='*60}")
    print(f"ENTROPY DECREASE CONDITIONS")
    print(f"{'='*60}")

    # For each round pair (r, r+1): does entropy decrease?
    decrease_count = {r: 0 for r in range(1, 20)}
    increase_count = {r: 0 for r in range(1, 20)}
    total = {r: 0 for r in range(1, 20)}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[0] ^= (1 << random.randint(0, 31))

        s1_all = sha256_rounds(M1, 20)
        s2_all = sha256_rounds(M2, 20)

        for r in range(1, 20):
            ent_r, _, _ = chain_entropy(s1_all[r], s2_all[r])
            ent_r1, _, _ = chain_entropy(s1_all[r+1], s2_all[r+1])

            total[r] += 1
            if ent_r1 < ent_r - 0.01:  # Meaningful decrease
                decrease_count[r] += 1
            elif ent_r1 > ent_r + 0.01:
                increase_count[r] += 1

    print(f"\n  Per-round entropy changes:")
    print(f"  {'Round':>6} | {'Decrease%':>9} | {'Increase%':>9} | {'Flat%':>6} | {'Verdict'}")
    print(f"  " + "-" * 50)

    for r in range(1, 20):
        n = total[r]
        dec_pct = decrease_count[r] / n * 100
        inc_pct = increase_count[r] / n * 100
        flat_pct = 100 - dec_pct - inc_pct
        verdict = "GROWS" if inc_pct > dec_pct + 10 else ("SHRINKS" if dec_pct > inc_pct + 10 else "MIXED")
        print(f"  {r:>3}→{r+1:>2} | {dec_pct:>8.1f}% | {inc_pct:>8.1f}% | {flat_pct:>5.1f}% | {verdict}")

def test_minimum_entropy_collision():
    """What's the theoretical minimum chain entropy at collision?"""
    print(f"\n{'='*60}")
    print(f"MINIMUM ENTROPY OF COLLISION")
    print(f"{'='*60}")

    # At collision: s1 = s2 → δ = 0 → no P-chains → entropy = 0
    # Near-collision: small δ → few chains → low entropy

    # What entropy corresponds to dH = k bits?
    print(f"\n  Entropy vs hash distance (theoretical):")
    print(f"  {'dH':>4} | {'Min entropy':>12} | {'Configuration'}")
    print(f"  " + "-" * 45)

    # dH = 0: collision, entropy = 0
    print(f"  {0:>4} | {0:>12.3f} | all K/G, no P")

    # dH = 1: one bit differs, one P-chain of length 1
    print(f"  {1:>4} | {0:>12.3f} | one P-chain [1], ent=0")

    # dH = k: k bits differ
    # Min entropy: all k bits in ONE chain → one chain of length k → ent = 0
    # Max entropy: k chains of length 1 → ent = log₂(k)
    for k in [2, 4, 8, 16, 32, 64, 128]:
        min_ent = 0  # One chain of length k
        max_ent = math.log2(k) if k > 1 else 0  # k chains of length 1
        print(f"  {k:>4} | {min_ent:>5.3f}-{max_ent:>5.3f} | "
              f"[{k}] vs [{','.join(['1']*min(k,5))}{',...' if k>5 else ''}]")

    print(f"\n  KEY INSIGHT:")
    print(f"    Collision: entropy = 0 (no chains)")
    print(f"    Random:    entropy ≈ 22.3 (many chains of various lengths)")
    print(f"    Gap: 22.3 bits of entropy must be REMOVED to reach collision")
    print(f"")
    print(f"    If entropy increases by ε per round:")
    print(f"      Starting from entropy 0 at round 0")
    print(f"      After 64 rounds: entropy ≈ 64ε")
    print(f"      For collision: need 64ε < some threshold")
    print(f"      → SHA-256 must ADD enough entropy per round to make this impossible")

def test_entropy_rate(N=1000):
    """Measure the RATE of entropy production per round."""
    print(f"\n{'='*60}")
    print(f"ENTROPY PRODUCTION RATE (★-Second Law)")
    print(f"{'='*60}")

    # Start from ZERO entropy (identical states) and measure entropy growth
    # This happens when δW first becomes nonzero

    # At round 0: states identical → entropy 0
    # After round with δW ≠ 0: entropy jumps

    # Measure entropy added per round for different starting entropies
    for start_ent_label, make_pair in [
        ("zero (identical)", lambda M: (M, list(M))),
        ("1-bit", lambda M: (M, [M[0]^1]+M[1:])),
        ("1-word", lambda M: (M, [random.randint(0,MASK)]+M[1:])),
        ("random pair", lambda M: (M, random_w16())),
    ]:
        delta_ents = []
        for _ in range(N):
            M1 = random_w16()
            M1_list, M2 = make_pair(M1)
            if isinstance(M1_list, list):
                M1 = M1_list

            for r in range(min(10, 64)):
                s1 = sha256_rounds(M1, r+1)
                s2 = sha256_rounds(M2, r+1)

                if r == 0:
                    ent_before = 0
                else:
                    ent_before, _, _ = chain_entropy(
                        sha256_rounds(M1, r)[r], sha256_rounds(M2, r)[r])

                ent_after, _, _ = chain_entropy(s1[r+1], s2[r+1])
                delta_ents.append(ent_after - ent_before)
                break  # Only first round for each

        de = np.array(delta_ents)
        print(f"\n  Start: {start_ent_label}")
        print(f"    ΔEntropy (1 round): {de.mean():+.3f} ± {de.std():.3f}")

        if de.mean() > 0:
            rounds_to_max = 22.3 / de.mean()
            print(f"    Rounds to max entropy: {rounds_to_max:.1f}")

def test_find_entropy_decreasing_messages(N=2000):
    """Find messages where entropy DECREASES between specific rounds."""
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR ENTROPY-DECREASING MESSAGES")
    print(f"{'='*60}")

    # At rounds 3→4 (where entropy is still growing): find pairs where it DROPS
    best_decrease = 0
    best_pair = None

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[0] ^= (1 << random.randint(0, 31))

        s1_3 = sha256_rounds(M1, 3)[3]; s2_3 = sha256_rounds(M2, 3)[3]
        s1_4 = sha256_rounds(M1, 4)[4]; s2_4 = sha256_rounds(M2, 4)[4]

        ent3, _, _ = chain_entropy(s1_3, s2_3)
        ent4, _, _ = chain_entropy(s1_4, s2_4)

        decrease = ent3 - ent4  # Positive = entropy decreased
        if decrease > best_decrease:
            best_decrease = decrease
            best_pair = (list(M1), list(M2), ent3, ent4)

    if best_pair:
        M1, M2, e3, e4 = best_pair
        print(f"\n  Best entropy decrease found:")
        print(f"    Round 3 entropy: {e3:.3f}")
        print(f"    Round 4 entropy: {e4:.3f}")
        print(f"    Decrease: {best_decrease:.3f}")
        print(f"    δM = W[0] bit {(M1[0] ^ M2[0]).bit_length()-1}")

        # Track full entropy trajectory for this pair
        print(f"\n    Full trajectory:")
        for r in range(0, 20):
            s1 = sha256_rounds(M1, r)[r]; s2 = sha256_rounds(M2, r)[r]
            ent, nc, mc = chain_entropy(s1, s2)
            marker = " ← DECREASE" if r == 4 else ""
            print(f"      Round {r:>2}: ent={ent:.3f}, chains={nc}, max={mc}{marker}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 157: ★-THERMODYNAMICS")
    print("Chain entropy as the Second Law of SHA-256")
    print("=" * 60)

    test_entropy_flow(200)
    test_entropy_decrease_conditions(300)
    test_minimum_entropy_collision()
    test_entropy_rate(500)
    test_find_entropy_decreasing_messages(1000)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★-Second Law")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
