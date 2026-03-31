#!/usr/bin/env python3
"""
EXP 161: Trees + Ring Transition — Parallel Deep Dive

TRACK 1: THIN-TREE ATTACK
  Modify ONLY thin-tree bits → less hash change → closer to collision.
  Build pairs from thin-tree differences only → birthday among them.

TRACK 2: RING TRANSITION BLIND SPOTS
  48% of Σ absorbed by carry. WHICH 48%?
  If specific bit positions are ALWAYS absorbed → "blind spots"
  → differences at blind spots are invisible → free collision bits
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# TRACK 1: THIN-TREE ATTACK
# ============================================================
def compute_tree_thickness(N=80):
    """Compute per-bit influence with better statistics."""
    influence = np.zeros(512)
    for _ in range(N):
        M = random_w16()
        H_base = sha256_compress(M)
        for j in range(512):
            w = j // 32; b = j % 32
            M_flip = list(M); M_flip[w] ^= (1 << b)
            H_flip = sha256_compress(M_flip)
            influence[j] += sum(hw(H_base[ww] ^ H_flip[ww]) for ww in range(8))
    influence /= N
    return influence

def test_thin_tree_attack(N=20, budget=3000):
    """Build pairs from thin-tree bits, birthday among them."""
    print(f"\n{'='*60}")
    print(f"THIN-TREE ATTACK (N={N}, budget={budget})")
    print(f"{'='*60}")

    # Compute tree thickness
    print(f"  Computing tree thickness...")
    influence = compute_tree_thickness(N=60)

    # Sort bits by thickness
    sorted_bits = np.argsort(influence)
    thin_bits = sorted_bits[:50]   # 50 thinnest
    thick_bits = sorted_bits[-50:]  # 50 thickest
    mid_bits = sorted_bits[200:250]  # 50 medium

    print(f"  Thin bits avg influence: {influence[thin_bits].mean():.2f}")
    print(f"  Thick bits avg influence: {influence[thick_bits].mean():.2f}")
    print(f"  Range: {influence[thick_bits].mean() - influence[thin_bits].mean():.2f}")

    thin_results = []; thick_results = []; rand_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)

        # Thin-tree weapon: flip only THIN bits
        best_thin = 256
        for _ in range(budget):
            M2 = list(M1)
            n_flips = random.randint(2, 8)
            for _ in range(n_flips):
                j = random.choice(thin_bits)
                w = j // 32; b = j % 32
                M2[w] ^= (1 << b)
            if M1 == M2: continue
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_thin = min(best_thin, dH)
        thin_results.append(best_thin)

        # Thick-tree weapon: flip only THICK bits
        best_thick = 256
        for _ in range(budget):
            M2 = list(M1)
            n_flips = random.randint(2, 8)
            for _ in range(n_flips):
                j = random.choice(thick_bits)
                w = j // 32; b = j % 32
                M2[w] ^= (1 << b)
            if M1 == M2: continue
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_thick = min(best_thick, dH)
        thick_results.append(best_thick)

        # Random baseline
        best_rand = 256
        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_rand = min(best_rand, dH)
        rand_results.append(best_rand)

    ta = np.array(thin_results); tha = np.array(thick_results); ra = np.array(rand_results)

    print(f"\n  Results:")
    print(f"    Thin-tree: avg={ta.mean():.1f}, min={ta.min()}")
    print(f"    Thick-tree: avg={tha.mean():.1f}, min={tha.min()}")
    print(f"    Random:    avg={ra.mean():.1f}, min={ra.min()}")

    gain_thin = ra.mean() - ta.mean()
    gain_thick = ra.mean() - tha.mean()
    print(f"\n    Thin-tree gain vs random: {gain_thin:+.1f} bits")
    print(f"    Thick-tree gain vs random: {gain_thick:+.1f} bits")

    if gain_thin > gain_thick + 1:
        print(f"    ★★★ THIN TREES BEAT THICK TREES!")

# ============================================================
# TRACK 2: RING TRANSITION BLIND SPOTS
# ============================================================
def test_ring_transition_map(N=500):
    """Map WHICH Σ output bits are absorbed at the Ring1→Ring3 transition."""
    print(f"\n{'='*60}")
    print(f"RING TRANSITION ABSORPTION MAP (N={N})")
    print(f"{'='*60}")

    # For Σ₁(e) + rest → T1:
    # Which BITS of Σ₁ output are absorbed by carry?

    absorption = np.zeros(32)  # Per bit: how often absorbed

    for _ in range(N):
        e = random.randint(0, MASK)
        h = random.randint(0, MASK)
        ch_val = ch(e, random.randint(0, MASK), random.randint(0, MASK))
        k_val = K[random.randint(0, 63)]
        w_val = random.randint(0, MASK)

        sig_e = sigma1(e)

        # T1 with real addition
        T1_real = (h + sig_e + ch_val + k_val + w_val) & MASK

        # T1 with XOR (no carry)
        T1_xor = h ^ sig_e ^ ch_val ^ k_val ^ w_val

        # Absorbed bits = where real ≠ xor
        absorbed = T1_real ^ T1_xor
        for b in range(32):
            if (absorbed >> b) & 1:
                absorption[b] += 1

    absorption /= N

    print(f"\n  Per-bit absorption rate (real ≠ xor):")
    print(f"  (Higher = more carry absorption = more 'blind')")
    print(f"\n  Bit | Absorption | Bar")
    print(f"  " + "-" * 50)

    for b in range(32):
        bar = "█" * int(absorption[b] * 50)
        marker = " ← BLIND SPOT" if absorption[b] > 0.55 else (
                 " ← LOW ABSORB" if absorption[b] < 0.40 else "")
        print(f"  {b:>3} | {absorption[b]:>10.4f} | {bar}{marker}")

    # KEY: is absorption UNIFORM?
    uniformity = absorption.std()
    print(f"\n  Absorption uniformity:")
    print(f"    Mean: {absorption.mean():.4f}")
    print(f"    Std:  {uniformity:.4f}")
    print(f"    Range: {absorption.min():.4f} - {absorption.max():.4f}")

    if uniformity > 0.02:
        print(f"    ★★★ NON-UNIFORM! Some bits absorb {absorption.max()/absorption.min():.1f}× more!")
        print(f"    Blind spots: bits with absorption > 0.55")
        blind_bits = [b for b in range(32) if absorption[b] > 0.55]
        clear_bits = [b for b in range(32) if absorption[b] < 0.40]
        print(f"    Blind: {blind_bits}")
        print(f"    Clear: {clear_bits}")
    else:
        print(f"    Absorption is UNIFORM (no blind spots)")

    return absorption

def test_blind_spot_exploitation(N=15, budget=3000):
    """If blind spots exist: inject differences AT blind spots → invisible."""
    print(f"\n{'='*60}")
    print(f"BLIND SPOT EXPLOITATION (N={N})")
    print(f"{'='*60}")

    absorption = test_ring_transition_map(300)

    # Find bits with LOWEST absorption (clearest path through ring transition)
    clear_bits = np.argsort(absorption)[:8]  # 8 clearest
    blind_bits = np.argsort(-absorption)[:8]  # 8 most absorbed

    print(f"\n  Clear bits (survive transition): {list(clear_bits)}")
    print(f"  Blind bits (absorbed at transition): {list(blind_bits)}")

    # Weapon: create differences ONLY at blind spots (where they get absorbed)
    # vs differences at clear spots (where they survive)

    clear_results = []; blind_results = []; rand_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)

        # Blind-spot weapon: flip bits at high-absorption positions
        best_blind = 256
        for _ in range(budget):
            M2 = list(M1)
            w_msg = random.randint(0, 15)
            for b in random.sample(list(blind_bits), random.randint(1, 4)):
                M2[w_msg] ^= (1 << int(b))
            if M1 == M2: continue
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_blind = min(best_blind, dH)
        blind_results.append(best_blind)

        # Clear-spot weapon: flip bits at low-absorption positions
        best_clear = 256
        for _ in range(budget):
            M2 = list(M1)
            w_msg = random.randint(0, 15)
            for b in random.sample(list(clear_bits), random.randint(1, 4)):
                M2[w_msg] ^= (1 << int(b))
            if M1 == M2: continue
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_clear = min(best_clear, dH)
        clear_results.append(best_clear)

        # Random
        best_rand = 256
        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[ww] ^ H2[ww]) for ww in range(8))
            best_rand = min(best_rand, dH)
        rand_results.append(best_rand)

    ba = np.array(blind_results); ca = np.array(clear_results); ra = np.array(rand_results)
    print(f"\n  Results:")
    print(f"    Blind-spot weapon: avg={ba.mean():.1f}, min={ba.min()}")
    print(f"    Clear-spot weapon: avg={ca.mean():.1f}, min={ca.min()}")
    print(f"    Random:            avg={ra.mean():.1f}, min={ra.min()}")

    if ba.mean() < ca.mean():
        print(f"    ★ Blind spots: {ca.mean()-ba.mean():.1f} bits better than clear")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 161: TREES + RINGS — PARALLEL DEEP DIVE")
    print("=" * 60)

    test_thin_tree_attack(N=12, budget=2000)
    test_blind_spot_exploitation(N=12, budget=2000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
