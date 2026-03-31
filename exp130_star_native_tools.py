#!/usr/bin/env python3
"""
EXP 130: ★-Native Toolset — Tools Built FROM the Algebra

Previous experiments: external strategies (gradient, Newton) applied IN ★-space.
This experiment: strategies that ARE ★-operations.

KEY SHIFT: Work on PAIRS (M₁, M₂) in ★-space, not on individual messages.

★(M₁, M₂) = (M₁⊕M₂, M₁&M₂) per word = (δXOR, δAND)

Collision: state₁ = state₂ ⟺ δXOR_state = 0 for all 8 words.

★-NATIVE TOOLS operate on the pair's ★-decomposition:
  Tool A: ★-XOR-flip — flip a bit in δXOR (flip one bit of M₂)
  Tool B: ★-AND-set — force M₁,M₂ to agree at specific bit (set AND)
  Tool C: ★-GKP-reshape — change GKP pattern to extend P-chains
  Tool D: ★-carry-inject — add carry at specific position to one message
  Tool E: ★-Maj-balance — use ★²(a,b,c)=Maj for 3-element balance

★-NATIVE METRIC: not xor_dist(H₁,H₂) but the ★-structure of the
state pair: GKP distribution, carry chain lengths, AND-weight.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def xor_dist(s1, s2):
    return sum(hw(s1[w] ^ s2[w]) for w in range(8))

# ============================================================
# ★-NATIVE METRIC
# ============================================================
def star_metric(M1, M2, R=64):
    """★-native distance: measures pair structure, not just hash diff.

    Components:
    - δXOR weight (standard: want 0)
    - δAND alignment (from exp121: negative coeff = good)
    - GKP propagate chain quality
    - Carry chain coherence
    """
    s1 = sha256_rounds(M1, R); s2 = sha256_rounds(M2, R)
    st1 = s1[R]; st2 = s2[R]

    # 1. XOR distance (must be 0 for collision)
    d_xor = sum(hw(st1[w] ^ st2[w]) for w in range(8))

    # 2. AND alignment: how much do states agree where IV has 1-bits?
    and_align = 0
    for w in range(8):
        # Where IV[w] bit = 1, do st1 and st2 agree?
        agree = ~(st1[w] ^ st2[w]) & IV[w]
        and_align += hw(agree)

    # 3. Carry coherence: do the feedforward carries agree?
    carry_agree = 0
    for w in range(8):
        c1 = carry_word(IV[w], st1[w])
        c2 = carry_word(IV[w], st2[w])
        carry_agree += 32 - hw(c1 ^ c2)

    # 4. GKP P-chain match: do both states have similar GKP patterns with IV?
    gkp_match = 0
    for w in range(8):
        g1 = carry_gkp_classification(IV[w], st1[w])
        g2 = carry_gkp_classification(IV[w], st2[w])
        gkp_match += sum(1 for a, b in zip(g1, g2) if a == b)

    # Combined metric (lower = better, 0 = collision)
    # Weight: XOR must be 0 (primary), others help navigate
    score = d_xor * 4 - and_align - carry_agree * 0.5 - gkp_match * 0.25
    return score, d_xor, and_align, carry_agree, gkp_match

# ============================================================
# ★-NATIVE TOOLS
# ============================================================

def tool_star_xor_flip(M1, M2, R, n_eval=32):
    """★-XOR-flip: flip bits in M₂ to change δXOR of the pair.
    Targets bits where δXOR_state is 1 (needs to become 0)."""
    s1 = sha256_rounds(M1, R)[R]; s2 = sha256_rounds(M2, R)[R]
    current_score, current_dxor, _, _, _ = star_metric(M1, M2, R)
    best_M2 = M2; best_score = current_score

    for _ in range(n_eval):
        w = random.randint(0, 15)
        b = random.randint(0, 31)
        M2t = list(M2); M2t[w] ^= (1 << b)  # XOR-flip = bit flip
        sc, dx, _, _, _ = star_metric(M1, M2t, R)
        if sc < best_score:
            best_score = sc; best_M2 = M2t

    return best_M2, best_score, n_eval

def tool_star_and_set(M1, M2, R, n_eval=32):
    """★-AND-set: force M₂ to agree with M₁ at random bit positions.
    This directly reduces δXOR by copying bits from M₁ to M₂."""
    current_score, _, _, _, _ = star_metric(M1, M2, R)
    best_M2 = M2; best_score = current_score

    for _ in range(n_eval):
        w = random.randint(0, 15)
        b = random.randint(0, 31)
        M2t = list(M2)
        # Copy bit b of M1[w] to M2[w]
        M2t[w] = (M2t[w] & ~(1 << b)) | (M1[w] & (1 << b))
        sc, _, _, _, _ = star_metric(M1, M2t, R)
        if sc < best_score:
            best_score = sc; best_M2 = M2t

    return best_M2, best_score, n_eval

def tool_star_carry_inject(M1, M2, R, n_eval=32):
    """★-carry-inject: add ±1 to M₂ words to change carry structure."""
    current_score, _, _, _, _ = star_metric(M1, M2, R)
    best_M2 = M2; best_score = current_score

    for _ in range(n_eval):
        w = random.randint(0, 15)
        direction = random.choice([-1, +1])
        M2t = list(M2); M2t[w] = (M2t[w] + direction) & MASK
        sc, _, _, _, _ = star_metric(M1, M2t, R)
        if sc < best_score:
            best_score = sc; best_M2 = M2t

    return best_M2, best_score, n_eval

def tool_star_gkp_reshape(M1, M2, R, n_eval=32):
    """★-GKP-reshape: modify M₂ to change GKP pattern with M₁.
    Target: maximize P-chains (propagate carry further)."""
    current_score, _, _, _, _ = star_metric(M1, M2, R)
    best_M2 = M2; best_score = current_score

    for _ in range(n_eval):
        # Find a K or G position in message pair, try to make it P
        w = random.randint(0, 15)
        b = random.randint(0, 31)
        m1_bit = (M1[w] >> b) & 1
        m2_bit = (M2[w] >> b) & 1

        M2t = list(M2)
        if m1_bit == m2_bit:
            # Both same (G or K) → flip M2 to make P
            M2t[w] ^= (1 << b)
        else:
            # Already P → try making it G (both 1) or K (both 0)
            if m1_bit == 1:
                M2t[w] |= (1 << b)  # Set to 1 → G
            else:
                M2t[w] &= ~(1 << b)  # Clear → K

        sc, _, _, _, _ = star_metric(M1, M2t, R)
        if sc < best_score:
            best_score = sc; best_M2 = M2t

    return best_M2, best_score, n_eval

def tool_star_swap_words(M1, M2, R, n_eval=32):
    """★-swap: swap a word of M₂ with corresponding word of M₁.
    Directly sets δXOR=0 for that word (but changes schedule)."""
    current_score, _, _, _, _ = star_metric(M1, M2, R)
    best_M2 = M2; best_score = current_score

    for _ in range(n_eval):
        w = random.randint(0, 15)
        M2t = list(M2)
        M2t[w] = M1[w]  # Copy entire word → δXOR[w] = 0 for message
        sc, _, _, _, _ = star_metric(M1, M2t, R)
        if sc < best_score:
            best_score = sc; best_M2 = M2t

    return best_M2, best_score, n_eval

# ============================================================
# ★-NATIVE SOLVER
# ============================================================
def star_native_solve(M1, R=64, budget=10000):
    """Solver using only ★-native tools and ★-native metric."""
    M2 = random_w16()
    current_score, current_dxor, _, _, _ = star_metric(M1, M2, R)

    tools = [
        ("★-XOR-flip", tool_star_xor_flip),
        ("★-AND-set", tool_star_and_set),
        ("★-carry-inject", tool_star_carry_inject),
        ("★-GKP-reshape", tool_star_gkp_reshape),
        ("★-swap-words", tool_star_swap_words),
    ]

    evals_used = 0
    tool_wins = {n: 0 for n, _ in tools}
    best_dxor = current_dxor
    stagnation = 0

    while evals_used < budget:
        improved = False
        for name, fn in tools:
            M2_new, score_new, evals = fn(M1, M2, R, n_eval=24)
            evals_used += evals

            _, dxor_new, _, _, _ = star_metric(M1, M2_new, R)
            if dxor_new < best_dxor:
                M2 = M2_new
                best_dxor = dxor_new
                current_score = score_new
                tool_wins[name] += 1
                improved = True

                if best_dxor == 0 and M1 != M2:
                    return M2, best_dxor, tool_wins, True

        if not improved:
            stagnation += 1
            if stagnation > 3:
                # ★-native restart: keep partial structure
                # Copy half of M1's words to M2, randomize rest
                M2 = random_w16()
                for w in random.sample(range(16), 8):
                    M2[w] = M1[w]
                _, best_dxor, _, _, _ = star_metric(M1, M2, R)
                stagnation = 0

    return M2, best_dxor, tool_wins, False

def test_star_native(N=20, budget=12000, R=64):
    """Test ★-native solver."""
    print(f"\n--- ★-NATIVE SOLVER ({R} rounds, N={N}, budget={budget}) ---")

    star_results = []
    all_wins = {}

    for trial in range(N):
        M1 = random_w16()
        M2, dxor, wins, found = star_native_solve(M1, R, budget)

        star_results.append(dxor)
        for name in wins:
            all_wins[name] = all_wins.get(name, 0) + wins[name]

        if found:
            print(f"  Trial {trial}: ★-COLLISION FOUND!")

    # Random search comparison
    rand_results = []
    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]
        best = 256
        for _ in range(budget):
            M2 = random_w16()
            d = xor_dist(sha256_rounds(M2, R)[R], target)
            best = min(best, d)
        rand_results.append(best)

    sa = np.array(star_results); ra = np.array(rand_results)

    print(f"\n  RESULTS:")
    print(f"  {'':>15} | {'Avg dH':>8} | {'Min dH':>8} | {'Median':>8}")
    print(f"  {'-'*45}")
    print(f"  {'★-Native':>15} | {sa.mean():>8.1f} | {sa.min():>8} | {np.median(sa):>8.1f}")
    print(f"  {'Random':>15} | {ra.mean():>8.1f} | {ra.min():>8} | {np.median(ra):>8.1f}")

    if sa.mean() < ra.mean():
        print(f"\n  ★-NATIVE WINS by {ra.mean() - sa.mean():.1f} bits!")
    else:
        print(f"\n  Random wins by {sa.mean() - ra.mean():.1f} bits")

    # Tool analysis
    print(f"\n  ★-TOOL EFFECTIVENESS:")
    total = sum(all_wins.values()) or 1
    for name in sorted(all_wins, key=lambda x: -all_wins[x]):
        w = all_wins[name]
        print(f"    {name:>15}: {w:>4} wins ({w/total*100:.1f}%)")

def test_star_native_rounds(N=15, budget=8000):
    """★-native at various rounds."""
    print(f"\n--- ★-NATIVE vs ROUNDS ---")
    for R in [4, 8, 16, 32, 64]:
        results = []
        for trial in range(N):
            M1 = random_w16()
            M2, dxor, _, found = star_native_solve(M1, R, budget)
            results.append(dxor)
        arr = np.array(results)
        print(f"  {R:>2} rounds: avg={arr.mean():.1f}, min={arr.min()}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 130: ★-NATIVE TOOLSET")
    print("Tools built FROM ★-algebra, operating on pairs")
    print("=" * 60)

    test_star_native_rounds(N=12, budget=6000)
    test_star_native(N=15, budget=10000, R=64)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★-Native Toolset")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
