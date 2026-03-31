#!/usr/bin/env python3
"""
EXP 104: ROTR-Invariant Carry Bits — The Unknown Object ≡

From fundamental barrier: ROTR breaks carry cascade → R=1.
From exp82: 19.4% carry SURVIVES rotation (3.1 bits per ROTR).

Question: ARE there specific bit positions where carry is
ROTR-INVARIANT? If yes → these bits have R > 1 → exploitable.

ROTR-invariant carry bit: a bit position where
carry(a,b)[i] = carry(ROTR_k(a), ROTR_k(b))[i+k]
for ALL a, b, k.

This means: the carry at this position doesn't CHANGE
under rotation — it moves WITH the rotation.

If such bits exist → carry cascade CONTINUES across rotation
at these specific positions → R > 1 at these positions.

Test: for each bit position, measure how STABLE carry is
across ALL SHA-256 rotations (2,6,11,13,22,25).
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_at_bit(a, b, bit):
    """Compute carry at specific bit position for a+b."""
    c = 0
    for i in range(bit + 1):
        ai = (a >> i) & 1; bi = (b >> i) & 1
        c = (ai & bi) | ((ai ^ bi) & c)
    return c

def test_rotr_invariance_per_bit(N=5000):
    """For each bit: how often does carry SURVIVE rotation?"""
    print(f"\n--- PER-BIT ROTR INVARIANCE (N={N}) ---")

    rotations = [2, 6, 11, 13, 22, 25]  # All SHA-256 rotations
    invariance = np.zeros((32, len(rotations)))

    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)

        # Standard carry
        std_carry = [carry_at_bit(a, b, i) for i in range(32)]

        for ki, k in enumerate(rotations):
            # Rotated carry
            a_rot = rotr(a, k); b_rot = rotr(b, k)
            rot_carry = [carry_at_bit(a_rot, b_rot, i) for i in range(32)]

            # For each bit i: does carry[i] = rotated_carry[(i+k)%32]?
            for i in range(32):
                target = (i + k) % 32
                if std_carry[i] == rot_carry[target]:
                    invariance[i][ki] += 1

    invariance /= N

    # Which bits are most ROTR-invariant?
    avg_invariance = invariance.mean(axis=1)  # Average over all rotations

    print(f"{'Bit':>4} | {'Avg invariance':>14} | {'Per rotation':>50}")
    print("-" * 75)

    for i in range(32):
        per_rot = ' '.join(f'{invariance[i][ki]:.3f}' for ki in range(len(rotations)))
        marker = " *** INVARIANT" if avg_invariance[i] > 0.55 else ""
        if i < 8 or i > 27 or avg_invariance[i] > 0.55:
            print(f"{i:>4} | {avg_invariance[i]:>14.6f} | {per_rot}{marker}")

    # Statistics
    n_invariant = np.sum(avg_invariance > 0.55)
    print(f"\nBits with avg invariance > 0.55: {n_invariant}/32")
    print(f"Mean invariance across all bits: {avg_invariance.mean():.6f}")
    print(f"Expected (random): 0.500000")
    print(f"Max invariance: bit {np.argmax(avg_invariance)} = {avg_invariance.max():.6f}")
    print(f"Min invariance: bit {np.argmin(avg_invariance)} = {avg_invariance.min():.6f}")

    return avg_invariance

def test_invariant_across_rounds(N=1000):
    """Do ROTR-invariant carry bits PERSIST across SHA-256 rounds?"""
    print(f"\n--- ROTR-INVARIANT ACROSS ROUNDS ---")

    # For Wang pairs: which carry bits are invariant at MULTIPLE rounds?
    # A bit that's invariant at round r AND r+1 → cascade survives!

    persistent = np.zeros(32)
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, sn, sf = wang_cascade(W0, W1)
        We = schedule(Wn)

        # Carry at round 16 (Wang boundary)
        d16 = sn[16][3]; T1_16 = (sn[16][7] + sigma1(sn[16][4]) +
              ch(sn[16][4], sn[16][5], sn[16][6]) + K[16] + We[16]) & MASK
        carry_16 = [carry_at_bit(d16, T1_16, i) for i in range(32)]

        # Carry at round 17 (after ROTR via Σ₁)
        d17 = sn[17][3]; T1_17 = (sn[17][7] + sigma1(sn[17][4]) +
              ch(sn[17][4], sn[17][5], sn[17][6]) + K[17] + We[17]) & MASK
        carry_17 = [carry_at_bit(d17, T1_17, i) for i in range(32)]

        # Which bits have SAME carry at both rounds?
        for i in range(32):
            if carry_16[i] == carry_17[i]:
                persistent[i] += 1

    persistent /= N
    n_persistent = np.sum(persistent > 0.55)

    print(f"Bits with persistent carry (r=16→17):")
    print(f"  N > 0.55: {n_persistent}/32")
    print(f"  Mean: {persistent.mean():.6f} (random: 0.5)")
    print(f"  Max: bit {np.argmax(persistent)} = {persistent.max():.6f}")

    # The key: do SAME bits persist as are ROTR-invariant?
    return persistent

def test_40_invariant_candidate(invariance, persistent, N=5000):
    """Do invariant bits + persistent bits overlap → 40-bit candidate?"""
    print(f"\n--- 40-BIT CANDIDATE ---")

    # Bits that are both ROTR-invariant AND round-persistent
    combined = (invariance + persistent) / 2

    # Top bits by combined score
    top_bits = np.argsort(-combined)[:10]
    print(f"Top 10 combined (invariant × persistent) bits:")
    for idx in top_bits:
        print(f"  Bit {idx:>2}: invariance={invariance[idx]:.4f}, "
              f"persistent={persistent[idx]:.4f}, combined={combined[idx]:.4f}")

    # How many bits are "strong" (combined > 0.55)?
    strong = np.sum(combined > 0.55)
    print(f"\nStrong bits (combined > 0.55): {strong}/32")
    print(f"Per 8 words: {strong} × 8 = {strong * 8} total")

    if strong * 8 >= 40:
        print(f"*** ≥40 ROTR-INVARIANT BITS EXIST! ***")
        print(f"Birthday on {strong*8} bits: 2^{strong*8//2}")
        print(f"Remaining: 2^{(256-strong*8)//2}")
        print(f"Total potential: 2^{max(strong*8//2, (256-strong*8)//2)}")
    elif strong > 0:
        print(f"Some invariant bits ({strong*8}), but fewer than 40")
    else:
        print(f"No ROTR-invariant bits found")

    # Verify: does selecting by invariant bits → lower δH?
    print(f"\n--- INVARIANT BITS → δH? ---")
    # Build mask from top bits
    mask = 0
    for idx in top_bits[:strong if strong > 0 else 5]:
        mask |= (1 << idx)

    dHs = []; inv_match = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, _, _ = wang_cascade(W0, W1)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        dH = sum(hw(Hn[w] ^ Hf[w]) for w in range(8))
        # Match on invariant bits only (e-branch word 4)
        inv_dH = hw((Hn[4] ^ Hf[4]) & mask)
        dHs.append(dH)
        inv_match.append(inv_dH)

    da = np.array(dHs); ia = np.array(inv_match)
    c = np.corrcoef(ia, da)[0, 1]
    print(f"corr(invariant_bits_δH, full_δH) = {c:+.6f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 104: ROTR-INVARIANT CARRY BITS")
    print("The Unknown Object ≡")
    print("=" * 60)

    invariance = test_rotr_invariance_per_bit(3000)
    persistent = test_invariant_across_rounds(1500)
    test_40_invariant_candidate(invariance, persistent, 3000)

    print("\n" + "=" * 60)
    print("VERDICT: Do 40 ROTR-invariant carry bits exist?")
    print("=" * 60)

if __name__ == "__main__":
    main()
