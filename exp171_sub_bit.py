#!/usr/bin/env python3
"""
EXP 171: SUB-BIT STRUCTURE — What's below 0 and 1?

INVENTION: Every bit has a hidden "color" (origin) and
"interference type" (how it was created).

★-COLOR: where the bit came from
  RED (⊕): born from XOR (linear)
  BLUE (&): born from AND/carry (nonlinear)
  GREEN (M): from message
  WHITE (C): from constant

★-INTERFERENCE: what happened when paths merged
  CONSTRUCTIVE-0: both inputs agreed on 0, output = 0
  CONSTRUCTIVE-1: both inputs agreed on 1, but XOR made 0 (HIDDEN agreement)
  DESTRUCTIVE: inputs disagreed, output = 1

Track these sub-bit properties through SHA-256 rounds.
Does the COLOR MIX predict anything? Does interference have structure?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def trace_colors_one_round():
    """Track ★-color of each bit through one round."""
    print(f"\n{'='*70}")
    print(f"★-COLOR TRACING: Round 0")
    print(f"{'='*70}")

    a, b, c, d, e, f, g, h = IV
    W0 = 0x61626380  # "abc" + padding
    K0 = K[0]

    # BEFORE round 0: all bits are WHITE (from IV)
    # W[0] bits are GREEN (from message)
    # K[0] bits are WHITE (constant)

    # Step 1: Σ₁(e) = ROTR₆(e) ⊕ ROTR₁₁(e) ⊕ ROTR₂₅(e)
    # All inputs are WHITE → XOR of WHITE = RED
    r6 = rotr(e, 6); r11 = rotr(e, 11); r25 = rotr(e, 25)
    sig1 = sigma1(e)

    # Step 2: Ch(e,f,g) = (e&f) ⊕ (~e&g)
    # AND of WHITE × WHITE = BLUE; XOR of BLUE × BLUE = RED(BLUE)
    # But the AND creates BLUE bits first, then XOR makes them RED
    # Net color: RED (but with BLUE ancestry)
    ch_val = ch(e, f, g)

    # Interference analysis of Ch at bit 0:
    e0 = (e >> 0) & 1; f0 = (f >> 0) & 1; g0 = (g >> 0) & 1
    ef = e0 & f0  # AND: BLUE
    neg_e_g = (1 - e0) & g0  # AND: BLUE
    ch0 = ef ^ neg_e_g  # XOR of two BLUEs: RED(BLUE)

    print(f"\n  Ch(e,f,g) bit 0:")
    print(f"    e[0]={e0}, f[0]={f0}, g[0]={g0}")
    print(f"    e&f = {ef} (BLUE: AND created)")
    print(f"    ~e&g = {neg_e_g} (BLUE: AND created)")
    print(f"    Ch = {ef}⊕{neg_e_g} = {ch0} (RED: XOR of two BLUEs)")

    # Interference type:
    if ef == neg_e_g:
        if ef == 0:
            interference = "CONSTRUCTIVE-0 (both BLUE=0 → XOR=0)"
        else:
            interference = "CONSTRUCTIVE-HIDDEN (both BLUE=1 → XOR=0, AGREEMENT HIDDEN!)"
    else:
        interference = "DESTRUCTIVE (BLUEs disagree → XOR=1)"
    print(f"    Interference: {interference}")

    # Step 3: T1 = h + Σ₁(e) + Ch(e,f,g) + K[0] + W[0]
    # This is ADDITION. Colors mix through carry:
    # XOR part: RED (from all inputs XOR'd)
    # Carry part: BLUE (from all AND operations in carry chain)
    # Final bits: mix of RED and BLUE depending on carry

    T1 = (h + sig1 + ch_val + K0 + W0) & MASK

    # For each bit of T1: is it RED (came from XOR) or BLUE (came from carry)?
    # T1[i] = (h⊕Σ₁⊕Ch⊕K⊕W)[i] ⊕ carry_in[i]
    # If carry_in = 0: T1[i] is RED (pure XOR of inputs)
    # If carry_in = 1: T1[i] is RED⊕BLUE = PURPLE (mixed!)

    # Compute carry chain
    partial = h
    components = [sig1, ch_val, K0, W0]
    carries = [0] * 32
    result_colors = []

    current = h
    for comp in components:
        new_carry = carry(current, comp)
        for b_pos in range(32):
            if (new_carry >> b_pos) & 1:
                carries[b_pos] = 1  # This bit was touched by carry
        current = (current + comp) & MASK

    # Classify each T1 bit
    red_count = 0; blue_count = 0; purple_count = 0
    for b_pos in range(32):
        if carries[b_pos]:
            result_colors.append("PURPLE")  # XOR + carry
            purple_count += 1
        else:
            result_colors.append("RED")     # Pure XOR
            red_count += 1

    print(f"\n  T1 color census (32 bits):")
    print(f"    RED (pure XOR, no carry): {red_count}")
    print(f"    PURPLE (XOR + carry): {purple_count}")
    print(f"    → {purple_count/32*100:.0f}% of T1 bits touched by carry (BLUE contamination)")

    return red_count, purple_count

def trace_interference_full(N=500):
    """Track interference patterns across full SHA-256."""
    print(f"\n{'='*70}")
    print(f"★-INTERFERENCE MAP: Full 64 rounds (N={N})")
    print(f"{'='*70}")

    # For each addition in SHA-256: classify each bit as
    # constructive-0, constructive-hidden, or destructive

    constructive_0 = np.zeros(64)  # Per round
    constructive_hidden = np.zeros(64)
    destructive = np.zeros(64)

    for _ in range(N):
        M = random_w16()
        W = schedule(M)
        states = sha256_rounds(M, 64)

        for r in range(64):
            s = states[r]
            a_val, b_val, c_val, d_val = s[0], s[1], s[2], s[3]
            e_val, f_val, g_val, h_val = s[4], s[5], s[6], s[7]

            # T1 = h + Σ₁(e) + Ch(e,f,g) + K[r] + W[r]
            sig1 = sigma1(e_val)
            ch_val = ch(e_val, f_val, g_val)

            # Look at the FINAL addition T1+T2 → a_new
            T1 = (h_val + sig1 + ch_val + K[r] + W[r]) & MASK
            sig0 = sigma0(a_val)
            maj_val = maj(a_val, b_val, c_val)
            T2 = (sig0 + maj_val) & MASK

            # For each bit: classify the T1+T2 interference
            for b_pos in range(32):
                t1_bit = (T1 >> b_pos) & 1
                t2_bit = (T2 >> b_pos) & 1

                if t1_bit == t2_bit:
                    if t1_bit == 0:
                        constructive_0[r] += 1
                    else:
                        constructive_hidden[r] += 1  # Both 1, XOR=0
                else:
                    destructive[r] += 1

    # Normalize
    total = N * 32
    constructive_0 /= total
    constructive_hidden /= total
    destructive /= total

    print(f"\n  Per-round interference (T1+T2→a_new addition):")
    print(f"  {'Round':>5} | {'Constr-0':>8} | {'Hidden':>8} | {'Destruct':>8} | {'Hidden/Total':>12}")
    print(f"  " + "-" * 55)

    for r in [0, 1, 2, 4, 8, 16, 32, 48, 63]:
        h_ratio = constructive_hidden[r] / (constructive_0[r] + constructive_hidden[r] + 0.001)
        print(f"  {r:>5} | {constructive_0[r]:>8.4f} | {constructive_hidden[r]:>8.4f} | "
              f"{destructive[r]:>8.4f} | {h_ratio:>12.4f}")

    # HIDDEN interference = both inputs 1, XOR makes 0
    # This is where information is DESTROYED by XOR
    # High hidden rate → more information loss → more "randomization"
    avg_hidden = constructive_hidden.mean()
    print(f"\n  Average HIDDEN interference: {avg_hidden:.4f}")
    print(f"  Expected (random): 0.250 (P(both=1)=0.25)")

    if abs(avg_hidden - 0.25) > 0.01:
        print(f"  ★★★ DEVIATION from random: {avg_hidden - 0.25:+.4f}")

def invent_sub_bits():
    """Define and test INVENTED sub-bit objects."""
    print(f"\n{'='*70}")
    print(f"INVENTING SUB-BITS: New objects below 0 and 1")
    print(f"{'='*70}")

    print(f"""
  STANDARD: bit ∈ {{0, 1}}

  ★-EXTENSION: bit ∈ {{0_K, 0_P, 1_P, 1_G}}

  A bit value PLUS its GKP context in the next operation:
    0_K = "zero that will KILL carry" (both bits 0 in next addition)
    0_P = "zero that will PROPAGATE" (bits differ, result 0 somehow)
    1_P = "one that will PROPAGATE" (bits differ, result 1)
    1_G = "one that will GENERATE carry" (both bits 1)

  These 4 sub-bits have DIFFERENT futures:
    0_K: carry DIES here → bit is "dead end"
    0_P: carry PASSES through → bit is "transparent"
    1_P: carry PASSES through → bit is "transparent"
    1_G: carry BORN here → bit is "source"

  In standard SHA-256: we see only 0 or 1.
  In ★-SHA-256: we see 0_K, 0_P, 1_P, or 1_G.

  4 sub-bits vs 2 bits = 1 EXTRA bit of information per position!

  Over 256 positions: 256 extra bits of hidden information.
  This hidden information IS the carry structure.
    """)

    # Compute sub-bit distribution
    print(f"  Sub-bit distribution at feedforward (N=500):")
    N = 500
    counts = {'0_K': 0, '0_P': 0, '1_P': 0, '1_G': 0}
    total = 0

    for _ in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]
        for w in range(8):
            for b in range(32):
                iv_b = (IV[w] >> b) & 1
                s_b = (s[w] >> b) & 1
                h_b = ((IV[w] + s[w]) & MASK >> b) & 1  # Hash bit

                # Sub-bit = hash value + GKP context
                if iv_b == 0 and s_b == 0:
                    counts['0_K'] += 1
                elif iv_b == 1 and s_b == 1:
                    counts['1_G'] += 1
                elif h_b == 0:
                    counts['0_P'] += 1
                else:
                    counts['1_P'] += 1
                total += 1

    for sb, count in counts.items():
        print(f"    {sb}: {count/total:.4f} (×{total} = {count})")

    print(f"\n  INSIGHT: Every hash bit carries a HIDDEN sub-bit label.")
    print(f"  Two hashes that are bit-identical (collision) may have")
    print(f"  DIFFERENT sub-bit structures!")
    print(f"  Sub-bit structure = the 'dark matter' of SHA-256.")

    # KEY: do near-collision pairs have different sub-bit distributions?
    print(f"\n  Near-collision sub-bit analysis:")
    near_counts = {'0_K': 0, '0_P': 0, '1_P': 0, '1_G': 0}
    rand_counts = {'0_K': 0, '0_P': 0, '1_P': 0, '1_G': 0}
    n_near = 0; n_rand = 0

    for _ in range(N * 30):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))

        s1 = sha256_rounds(M1, 64)[64]

        if dH < 110:
            for w in range(8):
                for b in range(32):
                    iv_b = (IV[w] >> b) & 1; s_b = (s1[w] >> b) & 1
                    h_b = (H1[w] >> b) & 1
                    if iv_b == s_b == 0: near_counts['0_K'] += 1
                    elif iv_b == s_b == 1: near_counts['1_G'] += 1
                    elif h_b == 0: near_counts['0_P'] += 1
                    else: near_counts['1_P'] += 1
            n_near += 1
        elif random.random() < 0.01:
            for w in range(8):
                for b in range(32):
                    iv_b = (IV[w] >> b) & 1; s_b = (s1[w] >> b) & 1
                    h_b = (H1[w] >> b) & 1
                    if iv_b == s_b == 0: rand_counts['0_K'] += 1
                    elif iv_b == s_b == 1: rand_counts['1_G'] += 1
                    elif h_b == 0: rand_counts['0_P'] += 1
                    else: rand_counts['1_P'] += 1
            n_rand += 1

    if n_near > 5 and n_rand > 5:
        print(f"  Near-collisions ({n_near})  vs  Random ({n_rand}):")
        for sb in ['0_K', '0_P', '1_P', '1_G']:
            nr = near_counts[sb] / (n_near * 256)
            rr = rand_counts[sb] / (n_rand * 256)
            diff = nr - rr
            z = diff / math.sqrt(0.25 * 0.75 / min(n_near, n_rand) / 256) if n_near > 0 else 0
            sig = "★★★" if abs(z) > 5 else ("★★" if abs(z) > 3 else "")
            print(f"    {sb}: near={nr:.4f} rand={rr:.4f} Δ={diff:+.4f} Z={z:+.1f} {sig}")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 171: SUB-BIT STRUCTURE")
    print("What's below 0 and 1?")
    print("=" * 70)

    trace_colors_one_round()
    trace_interference_full(300)
    invent_sub_bits()

    print(f"\n{'='*70}")
    print(f"VERDICT: Sub-bits exist?")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
