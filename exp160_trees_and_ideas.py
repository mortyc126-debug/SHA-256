#!/usr/bin/env python3
"""
EXP 160: Information Trees + Five Dismissed Ideas

TRACK A: INFORMATION TREES
  Each input bit creates a "tree" of influenced output bits.
  If any tree is THIN (few output bits influenced) → that input bit
  is nearly "dead" → free for collision.

TRACK B: FIVE DISMISSED IDEAS (testing ALL)
  B1: Carry Harvesting — does carry compute useful Boolean functions?
  B2: Ring Transition — what happens at Σ→Addition boundary?
  B3: Overshoot Exploit — round 4 non-equilibrium
  B4: Carry Interference — T1+T2 carry interaction
  B5: Topological — fiber self-intersection detection
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# TRACK A: INFORMATION TREES
# ============================================================
def compute_influence_tree(N=100):
    """For each input bit: how many output bits does it influence?"""
    print(f"\n{'='*60}")
    print(f"A: INFORMATION TREES — INPUT BIT INFLUENCE (N={N})")
    print(f"{'='*60}")

    # Influence[j] = number of output bits that CHANGE when input bit j flips
    influence = np.zeros(512)
    influence_per_output = np.zeros((512, 256))

    for _ in range(N):
        M = random_w16()
        H_base = sha256_compress(M)

        for j in range(512):
            w = j // 32; b = j % 32
            M_flip = list(M); M_flip[w] ^= (1 << b)
            H_flip = sha256_compress(M_flip)

            for ow in range(8):
                diff = H_base[ow] ^ H_flip[ow]
                for ob in range(32):
                    if (diff >> ob) & 1:
                        influence[j] += 1
                        influence_per_output[j, ow*32+ob] += 1

    influence /= N
    influence_per_output /= N

    # Each input bit should influence ~128 output bits (half)
    print(f"\n  Per-input-bit influence (output bits affected):")
    print(f"    Mean: {influence.mean():.2f} (ideal=128.0)")
    print(f"    Std:  {influence.std():.2f}")
    print(f"    Min:  {influence.min():.2f} ← THINNEST tree")
    print(f"    Max:  {influence.max():.2f}")

    # Find thinnest trees (least influential input bits)
    thinnest = np.argsort(influence)
    print(f"\n  THINNEST trees (least influential input bits):")
    for idx in thinnest[:10]:
        w = idx // 32; b = idx % 32
        print(f"    M[{w:>2}] bit {b:>2}: influence = {influence[idx]:.2f}/256")

    # Find thickest
    thickest = np.argsort(-influence)
    print(f"\n  THICKEST trees (most influential):")
    for idx in thickest[:5]:
        w = idx // 32; b = idx % 32
        print(f"    M[{w:>2}] bit {b:>2}: influence = {influence[idx]:.2f}/256")

    # KEY: is the RANGE significant?
    inf_range = influence.max() - influence.min()
    print(f"\n  Range: {inf_range:.2f}")
    if inf_range > 5:
        print(f"  ★★★ SIGNIFICANT VARIATION! Some bits {inf_range:.0f}× less influential")
    else:
        print(f"  All bits nearly equally influential (no thin trees)")

    # Correlation: does influence predict collision?
    # If thin-tree bits are modified → less hash change → closer to collision
    print(f"\n  Thin-tree vs thick-tree hash change:")
    thin_changes = []; thick_changes = []
    thin_bits = set(thinnest[:50]); thick_bits = set(thickest[:50])

    for _ in range(200):
        M = random_w16()
        H_base = sha256_compress(M)

        # Flip a THIN bit
        j = random.choice(list(thin_bits))
        w = j // 32; b = j % 32
        M_thin = list(M); M_thin[w] ^= (1 << b)
        H_thin = sha256_compress(M_thin)
        thin_changes.append(sum(hw(H_base[ww] ^ H_thin[ww]) for ww in range(8)))

        # Flip a THICK bit
        j = random.choice(list(thick_bits))
        w = j // 32; b = j % 32
        M_thick = list(M); M_thick[w] ^= (1 << b)
        H_thick = sha256_compress(M_thick)
        thick_changes.append(sum(hw(H_base[ww] ^ H_thick[ww]) for ww in range(8)))

    tc = np.array(thin_changes); thc = np.array(thick_changes)
    print(f"    Thin-tree flip: E[dH] = {tc.mean():.2f}")
    print(f"    Thick-tree flip: E[dH] = {thc.mean():.2f}")
    print(f"    Difference: {thc.mean() - tc.mean():+.2f}")

    return influence

# ============================================================
# TRACK B1: CARRY HARVESTING
# ============================================================
def test_carry_harvesting():
    """Does carry compute useful Boolean functions?"""
    print(f"\n{'='*60}")
    print(f"B1: CARRY HARVESTING")
    print(f"{'='*60}")

    # In T1 = h + Σ₁(e) + Ch(e,f,g) + K + W:
    # The carry chain resolves these 5 additions.
    # Each carry step computes: c_i = g_i | (p_i & c_{i-1})
    # Total free computation: 32 carry steps per addition × 4 additions ≈ 128

    # What does this carry COMPUTE?
    # carry(a,b) bit i = OR of all generate bits from bit i down to first kill
    # This is a RANGE-OR query on the generate bits!

    # Test: is carry(state, IV) correlated with some useful property?
    N = 1000
    carries = []; hash_bits_0 = []
    for _ in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]
        H = sha256_compress(M)

        c = carry(IV[0], s[0])  # Carry of feedforward, word 0
        carries.append(c)
        hash_bits_0.append(H[0])

    # Correlation between carry word and hash word
    ca = np.array(carries); ha = np.array(hash_bits_0)
    corr_bits = []
    for b in range(32):
        c_bit = np.array([(c >> b) & 1 for c in ca])
        h_bit = np.array([(h >> b) & 1 for h in ha])
        corr_bits.append(np.corrcoef(c_bit, h_bit)[0, 1])

    cb = np.array(corr_bits)
    print(f"\n  Carry(IV[0], state[0]) → Hash[0] bit correlations:")
    print(f"    Mean |corr|: {np.mean(np.abs(cb)):.4f}")
    print(f"    Max |corr|: {np.max(np.abs(cb)):.4f}")
    print(f"    Significant (>0.1): {np.sum(np.abs(cb) > 0.1)}/32")

# ============================================================
# TRACK B2: RING TRANSITION
# ============================================================
def test_ring_transition():
    """What happens when information crosses ring boundaries?"""
    print(f"\n{'='*60}")
    print(f"B2: RING TRANSITION — Σ→Addition Boundary")
    print(f"{'='*60}")

    # Σ₁(e) is in Ring 1 (polynomial). Then it's ADDED to h (Ring 3).
    # At the transition: Σ₁ output (3 bits per input bit) enters addition
    # where carry can absorb bits.

    # HOW MANY of the 3 Σ-output bits survive the addition?
    N = 500
    sigma_bits_surviving = []

    for _ in range(N):
        e = random.randint(0, MASK)
        h = random.randint(0, MASK)

        sig_e = sigma1(e)
        result = (h + sig_e) & MASK
        result_xor = h ^ sig_e  # What result WOULD be without carry

        # Bits where carry changed the result
        carry_changed = result ^ result_xor
        n_carry_changed = hw(carry_changed)
        sigma_bits_surviving.append(32 - n_carry_changed)

    avg = np.mean(sigma_bits_surviving)
    print(f"\n  Σ₁ output bits surviving addition (not absorbed by carry):")
    print(f"    Mean: {avg:.1f}/32")
    print(f"    → {32-avg:.1f} bits absorbed at ring transition")
    print(f"    → {(32-avg)/32*100:.0f}% of Σ information lost at transition")

# ============================================================
# TRACK B3: OVERSHOOT EXPLOIT
# ============================================================
def test_overshoot():
    """At round 4: M₃ entropy EXCEEDS equilibrium.
    Are there long-range correlations at the overshoot?"""
    print(f"\n{'='*60}")
    print(f"B3: OVERSHOOT AT ROUND 4")
    print(f"{'='*60}")

    # At round 4: entropy = 1.578 > equilibrium 1.500
    # Does this create exploitable correlations?

    N = 1000
    # Measure: correlation between state bits at round 4
    # that DON'T exist at round 8 (equilibrium)

    corr_r4 = []; corr_r8 = []
    for _ in range(N):
        M = random_w16()
        s4 = sha256_rounds(M, 4)[4]
        s8 = sha256_rounds(M, 8)[8]

        # Correlation between word 0 and word 4 (a-branch and e-branch)
        c4 = 0; c8 = 0
        for b in range(32):
            b0_4 = (s4[0] >> b) & 1; b4_4 = (s4[4] >> b) & 1
            b0_8 = (s8[0] >> b) & 1; b4_8 = (s8[4] >> b) & 1
            c4 += (b0_4 == b4_4)
            c8 += (b0_8 == b4_8)

        corr_r4.append(c4 / 32); corr_r8.append(c8 / 32)

    r4 = np.array(corr_r4); r8 = np.array(corr_r8)
    print(f"\n  Word 0↔Word 4 agreement:")
    print(f"    Round 4 (overshoot): {r4.mean():.4f} (random=0.5)")
    print(f"    Round 8 (equilibrium): {r8.mean():.4f}")
    print(f"    Overshoot excess: {r4.mean() - r8.mean():+.4f}")

    z = (r4.mean() - 0.5) / (r4.std() / math.sqrt(N))
    print(f"    Z-score at round 4: {z:+.2f}")

# ============================================================
# TRACK B4: CARRY INTERFERENCE
# ============================================================
def test_carry_interference():
    """T1 + T2 → a'. Do carries of T1 and T2 interfere?"""
    print(f"\n{'='*60}")
    print(f"B4: CARRY INTERFERENCE (T1 + T2)")
    print(f"{'='*60}")

    N = 1000
    constructive = 0; destructive = 0; total = 0

    for _ in range(N):
        M = random_w16()
        s = sha256_rounds(M, 0)[0]  # IV
        W_val = schedule(M)

        a, b_s, c_s, d, e, f, g, h = s
        T1 = (h + sigma1(e) + ch(e, f, g) + K[0] + W_val[0]) & MASK
        T2 = (sigma0(a) + maj(a, b_s, c_s)) & MASK

        # Carry of T1 + T2
        c_total = carry(T1, T2)

        # Individual carries leading to T1
        c_T1_partial = carry(h, sigma1(e))

        # Do they ALIGN or ANTI-ALIGN?
        aligned = hw(c_total & c_T1_partial)  # Both carry = constructive
        anti = hw(c_total & ~c_T1_partial & MASK)  # Disagree = destructive

        constructive += aligned
        destructive += anti
        total += 32

    c_rate = constructive / total
    d_rate = destructive / total

    print(f"\n  Carry interference in a' = T1 + T2:")
    print(f"    Constructive (aligned): {c_rate:.4f}")
    print(f"    Destructive (anti): {d_rate:.4f}")
    print(f"    Ratio: {c_rate/d_rate:.4f} (1.0 = no preference)")

    if abs(c_rate / d_rate - 1) > 0.05:
        print(f"    ★★★ INTERFERENCE BIAS EXISTS!")

# ============================================================
# TRACK B5: TOPOLOGICAL
# ============================================================
def test_topological():
    """Do ★-fibers self-intersect? (Quick check)"""
    print(f"\n{'='*60}")
    print(f"B5: TOPOLOGICAL — FIBER SELF-INTERSECTION")
    print(f"{'='*60}")

    # A fiber self-intersection: two messages M₁≠M₂ with
    # same hash AND same ★-pair structure.
    # Quick test: generate many messages, check if any pair has
    # both same hash AND same carry pattern

    N = 3000
    hash_carry_pairs = {}
    near_intersections = 0

    for _ in range(N):
        M = random_w16()
        H = sha256_compress(M)
        s = sha256_rounds(M, 64)[64]

        # ★-signature: (hash, carry_pattern)
        carry_sig = tuple(carry(IV[w], s[w]) & 0xFF for w in range(8))  # Truncated
        hash_sig = tuple(H[w] & 0xFF for w in range(8))  # Truncated

        key = hash_sig
        if key in hash_carry_pairs:
            old_carry = hash_carry_pairs[key]
            if old_carry != carry_sig:
                near_intersections += 1
        hash_carry_pairs[key] = carry_sig

    print(f"\n  Truncated (8-bit) hash collisions with different carry: {near_intersections}")
    print(f"  (This would indicate different ★-fiber points mapping to same hash)")

    if near_intersections > 0:
        print(f"  ★ Near-fiber-intersections found!")
    else:
        print(f"  No intersections at this truncation level")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 160: TREES + FIVE IDEAS")
    print("=" * 60)

    influence = compute_influence_tree(N=50)
    test_carry_harvesting()
    test_ring_transition()
    test_overshoot()
    test_carry_interference()
    test_topological()

    print(f"\n{'='*60}")
    print(f"GRAND SUMMARY: Which ideas have signal?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
