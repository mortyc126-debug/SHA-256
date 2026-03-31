#!/usr/bin/env python3
"""
EXP 151: Two-Ring Theory — Finding "Quiet" Bit Positions

SHA-256 operates in THREE algebraic structures simultaneously:
  Ring 1 (polynomial): Σ functions — want low-weight poly differences
  Ring 2 (coordinate): Ch, Maj — want differences avoiding active AND positions
  Ring 3 (arithmetic):  Addition — want small arithmetic differences (low carry)

A "quiet" bit position is one that's good in ALL THREE rings:
  - Low Σ expansion (Ring 1)
  - Low Ch/Maj activation (Ring 2)
  - Low carry generation (Ring 3)

Find the quietest positions → optimal differential starting points.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def analyze_quiet_positions():
    """For each bit position: how 'quiet' is it in all three rings?"""
    print(f"\n{'='*60}")
    print(f"QUIET POSITION ANALYSIS")
    print(f"{'='*60}")

    scores = np.zeros((8, 32))  # Per word, per bit: quietness score

    for w_state in range(8):
        for b in range(32):
            # Create 1-bit difference at this position
            delta = [0] * 8
            delta[w_state] = 1 << b

            # Ring 1 score: HW(Σ(δ)) — lower is better
            if w_state in [0, 1, 2, 3]:  # a-branch → Σ₀
                sigma_hw = hw(sigma0(delta[w_state]))
            else:  # e-branch → Σ₁
                sigma_hw = hw(sigma1(delta[w_state]))

            # Ring 2 score: Ch/Maj activation
            # Ch(e,f,g): if δ is in e-word, activation = HW(f⊕g) at IV
            # Maj(a,b,c): if δ is in a-word, activation = HW(b⊕c) at IV
            if w_state == 0:  # a → Maj(a,b,c), b=IV[1], c=IV[2]
                ring2_activation = hw(IV[1] ^ IV[2])
            elif w_state == 4:  # e → Ch(e,f,g), f=IV[5], g=IV[6]
                ring2_activation = hw(IV[5] ^ IV[6])
            else:
                ring2_activation = 16  # Other words: not directly in Ch/Maj at round 0

            # Ring 3 score: carry generation at this bit
            # Carry from bit b depends on IV bits at position b
            # If IV[w] bit b = 0: adding 1 generates no carry
            # If IV[w] bit b = 1: adding 1 generates carry (G position)
            iv_bit = (IV[w_state] >> b) & 1
            carry_cost = 1 if iv_bit == 1 else 0
            # Also: how long is the carry chain from this position?
            chain_len = 0
            for i in range(b + 1, 32):
                if (IV[w_state] >> i) & 1:  # P or G at position i
                    chain_len += 1
                else:
                    break
            carry_cost += chain_len

            # Combined score (lower = quieter)
            scores[w_state, b] = sigma_hw + ring2_activation * 0.5 + carry_cost * 2

    # Find quietest positions
    print(f"\n  Top 20 QUIETEST bit positions (best for differential):")
    print(f"  {'Word':>4} {'Bit':>4} | {'Σ-weight':>8} | {'Ring2':>5} | {'Carry':>5} | {'Score':>6}")
    print(f"  " + "-" * 45)

    flat_scores = [(scores[w, b], w, b) for w in range(8) for b in range(32)]
    flat_scores.sort()

    for score, w, b in flat_scores[:20]:
        delta = 1 << b
        if w in [0,1,2,3]:
            shw = hw(sigma0(delta))
        else:
            shw = hw(sigma1(delta))

        iv_bit = (IV[w] >> b) & 1
        chain = 0
        for i in range(b+1, 32):
            if (IV[w] >> i) & 1: chain += 1
            else: break

        if w == 0: r2 = hw(IV[1] ^ IV[2])
        elif w == 4: r2 = hw(IV[5] ^ IV[6])
        else: r2 = 16

        print(f"  {w:>4} {b:>4} | {shw:>8} | {r2:>5} | {chain:>5} | {score:>6.1f}")

    # Also: quietest per word
    print(f"\n  Quietest bit per word:")
    for w in range(8):
        best_b = np.argmin(scores[w])
        print(f"    Word {w}: bit {best_b}, score={scores[w, best_b]:.1f}")

    return scores

def test_quiet_differential(N=200):
    """Do quiet-position differentials survive longer?"""
    print(f"\n{'='*60}")
    print(f"QUIET DIFFERENTIAL SURVIVAL")
    print(f"{'='*60}")

    scores = analyze_quiet_positions()

    # Find quietest and loudest positions
    flat = [(scores[w, b], w, b) for w in range(8) for b in range(32)]
    flat.sort()
    quiet_positions = [(w, b) for _, w, b in flat[:10]]
    loud_positions = [(w, b) for _, w, b in flat[-10:]]

    # Track differential survival for quiet vs loud
    print(f"\n  Differential survival (rounds until dH > 200):")
    print(f"  {'Position':>15} | {'Score':>6} | {'Survival':>8}")
    print(f"  " + "-" * 35)

    for label, positions in [("QUIET", quiet_positions), ("LOUD", loud_positions)]:
        survivals = []
        for w, b in positions:
            for _ in range(N):
                M1 = random_w16()
                M2 = list(M1)
                # Create initial state difference
                # We can't directly set state bits, but we can set MESSAGE bits
                # and they affect specific state words at specific rounds
                M2[min(w, 15)] ^= (1 << b)

                s1_all = sha256_rounds(M1, 64)
                s2_all = sha256_rounds(M2, 64)

                # Find survival round
                for r in range(1, 65):
                    dH = sum(hw(s1_all[r][ww] ^ s2_all[r][ww]) for ww in range(8))
                    if dH > 200:
                        survivals.append(r)
                        break
                else:
                    survivals.append(64)

        avg_surv = np.mean(survivals)
        print(f"  {label:>15} | {flat[0][0] if label=='QUIET' else flat[-1][0]:>6.1f} | {avg_surv:>8.1f}")

def test_three_ring_compatibility(N=500):
    """Find single-bit differences that are good in ALL THREE rings."""
    print(f"\n{'='*60}")
    print(f"THREE-RING COMPATIBILITY")
    print(f"{'='*60}")

    # For each 1-bit message difference: measure its effect through SHA-256
    # at different rounds. The three-ring score predicts behavior.

    bit_effects = []

    for w in range(16):
        for b in range(32):
            M1 = [0] * 16  # Fixed base for consistency
            M2 = list(M1); M2[w] ^= (1 << b)

            s1 = sha256_rounds(M1, 64)
            s2 = sha256_rounds(M2, 64)

            # Effect at various rounds
            dH_r4 = sum(hw(s1[4][ww] ^ s2[4][ww]) for ww in range(8))
            dH_r8 = sum(hw(s1[8][ww] ^ s2[8][ww]) for ww in range(8))
            dH_r16 = sum(hw(s1[16][ww] ^ s2[16][ww]) for ww in range(8))
            dH_r64 = sum(hw(s1[64][ww] ^ s2[64][ww]) for ww in range(8))

            # Σ expansion for this bit
            sigma_hw = hw(sigma1(1 << b)) if w >= 8 else hw(sigma0(1 << b))

            bit_effects.append({
                'w': w, 'b': b,
                'sigma_hw': sigma_hw,
                'dH_r4': dH_r4, 'dH_r8': dH_r8,
                'dH_r16': dH_r16, 'dH_r64': dH_r64
            })

    # Correlation between Σ-expansion and round-4 effect
    sigma_hws = np.array([e['sigma_hw'] for e in bit_effects])
    dH_r4s = np.array([e['dH_r4'] for e in bit_effects])
    dH_r8s = np.array([e['dH_r8'] for e in bit_effects])
    dH_r64s = np.array([e['dH_r64'] for e in bit_effects])

    print(f"\n  Correlation: Σ-expansion → round effect")
    print(f"    corr(Σ_hw, dH_r4):  {np.corrcoef(sigma_hws, dH_r4s)[0,1]:+.4f}")
    print(f"    corr(Σ_hw, dH_r8):  {np.corrcoef(sigma_hws, dH_r8s)[0,1]:+.4f}")
    print(f"    corr(Σ_hw, dH_r64): {np.corrcoef(sigma_hws, dH_r64s)[0,1]:+.4f}")

    # Best bits for low dH at round 4
    sorted_by_r4 = sorted(bit_effects, key=lambda e: e['dH_r4'])
    print(f"\n  Best bits for low dH at round 4:")
    for e in sorted_by_r4[:8]:
        print(f"    M[{e['w']}] bit {e['b']:>2}: dH_r4={e['dH_r4']:>3}, "
              f"dH_r64={e['dH_r64']:>3}, Σ_hw={e['sigma_hw']}")

    print(f"\n  Worst bits for low dH at round 4:")
    for e in sorted_by_r4[-5:]:
        print(f"    M[{e['w']}] bit {e['b']:>2}: dH_r4={e['dH_r4']:>3}, "
              f"dH_r64={e['dH_r64']:>3}, Σ_hw={e['sigma_hw']}")

    # KEY: do bits with low dH_r4 also have low dH_r64?
    corr_r4_r64 = np.corrcoef(dH_r4s, dH_r64s)[0, 1]
    print(f"\n  corr(dH_r4, dH_r64): {corr_r4_r64:+.4f}")
    if abs(corr_r4_r64) > 0.1:
        print(f"  ★★★ Early-round advantage PERSISTS to round 64!")
    else:
        print(f"  Early advantage does NOT persist (decorrelation)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 151: TWO-RING THEORY — QUIET POSITIONS")
    print("=" * 60)

    analyze_quiet_positions()
    test_quiet_differential(100)
    test_three_ring_compatibility()

    print(f"\n{'='*60}")
    print(f"VERDICT: Two-Ring Theory")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
