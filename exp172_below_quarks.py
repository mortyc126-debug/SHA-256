#!/usr/bin/env python3
"""
EXP 172: BELOW QUARKS — Decomposing Sub-Bits

Sub-bit = meeting of TWO computation paths.
Below sub-bit: the PATHS themselves and their PREDICTABILITY.

DECOMPOSITION:
  For each sub-bit at (round, word, bit):
    Path A: how did THIS operand arrive at its value?
    Path B: how did the OTHER operand arrive?

  Predictability of each path:
    - Known if path comes from IV/K (constants) → DETERMINISTIC
    - Partially known if path involves few message bits → LOW ENTROPY
    - Unknown if path involves many message bits → HIGH ENTROPY

  Sub-bit "FLAVOR" = (value, GKP, path_A_depth, path_B_depth)

  At round 0: paths are shallow (1-2 operations) → predictable
  At round 64: paths are deep (64 operations) → unpredictable
  The TRANSITION = where quarks become opaque = τ_★ = 4
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_operand_predictability(N=200):
    """For each addition in SHA-256: how predictable are the two operands?

    Predictability = how much does the operand vary across different messages?
    Low variance = predictable. High variance = unpredictable."""
    print(f"\n{'='*70}")
    print(f"OPERAND PREDICTABILITY PER ROUND")
    print(f"{'='*70}")

    # For T1+T2 → a_new at each round:
    # Track T1 and T2 bit values across many messages
    # Variance = 0 → deterministic (fully predictable)
    # Variance = 0.25 → random (fully unpredictable, for binary)

    print(f"\n  T1, T2 predictability per round (bit-variance, 0=deterministic, 0.25=random):")
    print(f"  {'Round':>5} | {'T1 var':>8} | {'T2 var':>8} | {'T1 pred%':>9} | {'T2 pred%':>9} | {'Meet':>6}")
    print(f"  " + "-" * 60)

    for r in range(0, 64):
        if r > 10 and r < 60 and r % 8 != 0:
            continue

        T1_bits = np.zeros((N, 32))
        T2_bits = np.zeros((N, 32))

        for trial in range(N):
            M = random_w16()
            W = schedule(M)
            states = sha256_rounds(M, r+1)
            s = states[r]

            a_val, b_val, c_val = s[0], s[1], s[2]
            e_val, f_val, g_val, h_val = s[4], s[5], s[6], s[7]

            T1 = (h_val + sigma1(e_val) + ch(e_val, f_val, g_val) + K[r] + W[r]) & MASK
            T2 = (sigma0(a_val) + maj(a_val, b_val, c_val)) & MASK

            for b_pos in range(32):
                T1_bits[trial, b_pos] = (T1 >> b_pos) & 1
                T2_bits[trial, b_pos] = (T2 >> b_pos) & 1

        # Variance per bit (0 = all same = deterministic, 0.25 = random)
        T1_var = np.mean(T1_bits.var(axis=0))
        T2_var = np.mean(T2_bits.var(axis=0))

        # Predictability = 1 - var/0.25 (1 = fully predictable, 0 = random)
        T1_pred = max(0, 1 - T1_var / 0.25) * 100
        T2_pred = max(0, 1 - T2_var / 0.25) * 100

        # Meeting predictability: how much can we predict about the PAIR?
        meet_pred = T1_pred * T2_pred / 100

        print(f"  {r:>5} | {T1_var:>8.4f} | {T2_var:>8.4f} | {T1_pred:>8.1f}% | {T2_pred:>8.1f}% | {meet_pred:>5.1f}%")

def decompose_sub_bit_paths(N=300):
    """For each sub-bit at feedforward: trace its TWO parent paths."""
    print(f"\n{'='*70}")
    print(f"SUB-BIT PATH DECOMPOSITION (feedforward)")
    print(f"{'='*70}")

    # At feedforward: H[w] = IV[w] + state[w]
    # Operand A: IV[w] — FULLY DETERMINISTIC (depth 0)
    # Operand B: state[w] — depends on 64 rounds (depth 64)

    # This is MAXIMALLY ASYMMETRIC:
    # One path has depth 0 (known), other has depth 64 (unknown)

    print(f"\n  Feedforward path asymmetry:")
    print(f"    Operand A (IV): depth 0, predictability 100%")
    print(f"    Operand B (state_64): depth 64, predictability 0%")
    print(f"    Asymmetry: MAXIMUM (0 vs 64)")
    print(f"")
    print(f"    Sub-bit type determined by:")
    print(f"      IV bit (KNOWN) × state bit (UNKNOWN)")
    print(f"      IV=1 → G or P (known from IV alone)")
    print(f"      IV=0 → K or P (known from IV alone)")
    print(f"      The sub-bit's GKP type is HALF-DETERMINED by the known path!")

    # What about INTERMEDIATE rounds?
    print(f"\n  For T1+T2→a_new at round r:")
    print(f"    Both T1 and T2 have depth r (both computed from state)")
    print(f"    Paths are SYMMETRIC (both equally deep)")
    print(f"    Sub-bit type: FULLY UNPREDICTABLE after round ~4")

    # MEASURE: at which round do sub-bit types become unpredictable?
    print(f"\n  Sub-bit type predictability per round:")

    for r in range(0, 20):
        # For each round: compute GKP distribution of T1+T2 bits
        # How much does it deviate from (0.25, 0.50, 0.25)?
        gkp_counts = {'G': 0, 'K': 0, 'P': 0}
        total = 0

        for _ in range(N):
            M = random_w16()
            W = schedule(M)
            states = sha256_rounds(M, r+1)
            s = states[r]

            T1 = (s[7] + sigma1(s[4]) + ch(s[4], s[5], s[6]) + K[r] + W[r]) & MASK
            T2 = (sigma0(s[0]) + maj(s[0], s[1], s[2])) & MASK

            gkp = carry_gkp_classification(T1, T2)
            for g in gkp:
                gkp_counts[g] += 1
                total += 1

        pG = gkp_counts['G'] / total
        pK = gkp_counts['K'] / total
        pP = gkp_counts['P'] / total

        # Deviation from uniform
        dev = abs(pG - 0.25) + abs(pK - 0.25) + abs(pP - 0.50)
        pred = dev * 100  # Higher = more structured = more predictable

        print(f"    Round {r:>2}: G={pG:.4f} K={pK:.4f} P={pP:.4f} deviation={dev:.4f} pred={pred:.1f}%")

def invent_quark_flavors():
    """Define "flavors" of sub-bit quarks based on path properties."""
    print(f"\n{'='*70}")
    print(f"QUARK FLAVORS: Deeper decomposition of sub-bits")
    print(f"{'='*70}")

    print(f"""
  Sub-bit = value × GKP = {{0_K, 0_P, 1_P, 1_G}}

  Quark flavor = sub-bit × path_depth × path_type

  PATH DEPTH (how many operations from known values):
    d=0: "SURFACE" quark — directly from IV or message (known)
    d=1-4: "SHALLOW" quark — few operations, partially predictable
    d=5+: "DEEP" quark — many operations, effectively random

  PATH TYPE (what operations dominate):
    L-type: mostly LINEAR (XOR/ROTR) — RED ancestry
    N-type: mostly NONLINEAR (AND/carry) — BLUE ancestry
    M-type: MIXED — PURPLE ancestry

  QUARK TABLE (partial):
    0_K_surface_L: zero, kill, shallow, linear → MOST PREDICTABLE
    1_G_deep_N:    one, generate, deep, nonlinear → LEAST PREDICTABLE

  Total flavors: 4 (sub-bit) × 3 (depth) × 3 (type) = 36 quark types

  At round 0: mostly surface quarks (depth 0-1)
  At round 4: transition to shallow quarks (depth 2-4)
  At round 8+: all deep quarks (depth 5+)

  The TRANSITION from surface to deep = τ_★ = 4
  After transition: all quarks are deep → indistinguishable → random
  BEFORE transition: quarks have flavor → structure → potentially exploitable
    """)

    # MEASURE: quark flavor distribution at different rounds
    print(f"  Quark flavor distribution:")
    N = 200

    for r in [0, 1, 2, 4, 8, 16, 64]:
        # Proxy for "depth": how much does the bit depend on message?
        # Measure: flip message bit, does this T1/T2 bit change?
        sensitivity = 0
        total_bits = 0

        for _ in range(N):
            M = random_w16()
            W = schedule(M)
            states = sha256_rounds(M, min(r+1, 64))
            s = states[min(r, 63)]

            T1 = (s[7] + sigma1(s[4]) + ch(s[4], s[5], s[6]) + K[min(r,63)] + W[min(r,63)]) & MASK

            # Flip one message bit
            M2 = list(M)
            M2[r % 16] ^= (1 << (r % 32))
            W2 = schedule(M2)
            s2 = sha256_rounds(M2, min(r+1, 64))[min(r, 63)]
            T1_2 = (s2[7] + sigma1(s2[4]) + ch(s2[4], s2[5], s2[6]) + K[min(r,63)] + W2[min(r,63)]) & MASK

            sensitivity += hw(T1 ^ T1_2)
            total_bits += 32

        avg_sens = sensitivity / total_bits  # Fraction of bits that changed
        depth_label = "SURFACE" if avg_sens < 0.1 else ("SHALLOW" if avg_sens < 0.3 else "DEEP")

        print(f"    Round {r:>2}: sensitivity={avg_sens:.4f} → {depth_label}")

def the_absolute_bottom():
    """What's below quark flavors? The absolute smallest unit."""
    print(f"\n{'='*70}")
    print(f"THE ABSOLUTE BOTTOM")
    print(f"{'='*70}")

    print(f"""
  Quark = sub-bit with flavor.
  Below quark = the TWO input bits that CREATE the quark.
  Below those input bits = THEIR quarks from the previous operation.
  Below THOSE = their inputs. And so on.

  The recursion terminates at:
    MESSAGE BITS (M[0]..M[15]) — the 512 primordial bits
    IV BITS — the 256 creation constants
    K BITS — the 64×32 = 2048 round constants

  TOTAL PRIMORDIAL BITS: 512 + 256 + 2048 = 2816

  Everything in SHA-256 is built from these 2816 primordial bits
  through ~24,576 AND operations and ~similar XOR operations.

  The ABSOLUTE BOTTOM:
    ┌─────────────────────────────────────┐
    │  2816 PRIMORDIAL BITS               │
    │  (512 message + 256 IV + 2048 K)    │
    │                                     │
    │  Combined through ~50,000 gates     │
    │  (XOR, AND, OR in carry chains)     │
    │                                     │
    │  Producing 256 hash bits            │
    │  Each carrying sub-bit flavor       │
    │  Each a meeting of two paths        │
    │  Each path traceable to primordials │
    └─────────────────────────────────────┘

  This IS the bottom. Below 2816 primordials — nothing.
  They are the AXIOMS of SHA-256's universe.
  Everything else is DERIVED.
    """)

    print(f"  PRIMORDIAL BIT CENSUS:")
    print(f"    Message bits: 512 (under attacker control)")
    print(f"    IV bits:      256 (fixed, public)")
    iv_ones = sum(hw(IV[w]) for w in range(8))
    print(f"      IV ones: {iv_ones}/256 ({iv_ones/256*100:.1f}%)")
    print(f"      IV zeros: {256-iv_ones}/256")
    print(f"    K bits:       {64*32} (fixed, public)")
    k_ones = sum(hw(K[r]) for r in range(64))
    print(f"      K ones: {k_ones}/{64*32} ({k_ones/(64*32)*100:.1f}%)")
    print(f"    TOTAL:        2816 primordial bits")
    print(f"    Under control: 512/2816 = {512/2816*100:.1f}%")
    print(f"    Fixed/known:   2304/2816 = {2304/2816*100:.1f}%")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 172: BELOW QUARKS")
    print("Decomposing the sub-bits")
    print("=" * 70)

    measure_operand_predictability(N=150)
    decompose_sub_bit_paths(N=200)
    invent_quark_flavors()
    the_absolute_bottom()

    print(f"\n{'='*70}")
    print(f"VERDICT: Is there anything below?")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
