#!/usr/bin/env python3
"""
EXP 68: Cascaded Carry Solve — Bit-by-Bit Algebraic Collision

From exp67: bit 0 of each hash word is LINEAR (no carry).
Carry at bit i depends on bit i-1 → cascading solve possible.

Solve bit 0 → know carry_1 → solve bit 1 → know carry_2 → ...

KEY QUESTION: how many consecutive bits can be solved algebraically?
If k bits × 8 words = 8k bits free → birthday on remaining 256-8k.

The cascade breaks when carry becomes unpredictable.
From our theory: k* = 5 (phase transition).
If cascade works to k=5 → 40 bits free → 2^108.
If cascade works to k=32 → 256 bits → 2^0 (total algebraic solve!).
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def feedforward_carry_at_bit(iv_word, state_word, bit):
    """
    Carry contribution of feedforward (IV + state) at specific bit.
    Returns: carry bit at position 'bit' of IV[w]+state[w].
    """
    result_add = (iv_word + state_word) & MASK
    result_xor = iv_word ^ state_word
    carry_part = result_add ^ result_xor
    return (carry_part >> bit) & 1

def hash_bit_linearity(bit_pos, N=500):
    """
    Measure linearity of hash bit at position (word, bit).
    Linearity = how well a GF(2) linear model predicts the bit.

    For each input bit flip: does hash bit flip deterministically?
    This IS the Jacobian column. If the column is CONSISTENT
    across different base messages → the bit is "effectively linear".
    """
    word = bit_pos // 32
    bit = bit_pos % 32

    # Measure Jacobian column for this output bit, at multiple base messages
    jacobian_columns = []

    for _ in range(N):
        W16 = random_w16()
        H_base = sha256_compress(W16)
        base_bit = (H_base[word] >> bit) & 1

        col = []
        for j in range(512):
            w=j//32; b=j%32
            W_p = list(W16); W_p[w] ^= (1<<b)
            H_p = sha256_compress(W_p)
            col.append(((H_p[word]>>bit)&1) ^ base_bit)

        jacobian_columns.append(col)

    # Consistency: how stable is each Jacobian entry across messages?
    J = np.array(jacobian_columns)  # N × 512
    consistency = np.mean(J, axis=0)  # Average over messages

    # For truly linear bit: consistency[j] = 0 or 1 (always same)
    # For nonlinear: consistency[j] ≈ 0.5 (random)
    linearizable = np.sum((consistency > 0.9) | (consistency < 0.1))
    uncertain = np.sum((consistency > 0.4) & (consistency < 0.6))

    avg_consistency = np.mean(np.abs(consistency - 0.5)) + 0.5

    return linearizable, uncertain, avg_consistency

def test_cascade_linearity(N=200):
    """Measure linearity bit by bit, from bit 0 upward."""
    print("\n--- BIT-BY-BIT LINEARITY CASCADE ---")

    print(f"{'Bit':>4} | {'Linearizable/512':>16} | {'Uncertain':>9} | "
          f"{'Avg consistency':>15} | {'Status'}")
    print("-"*65)

    for bit in range(16):  # Test bits 0-15 of word 0
        bit_pos = 0 * 32 + bit  # H[0] bit 'bit'
        lin, unc, avg = test_cascade_linearity_single(bit_pos, N)

        status = "LINEAR" if avg > 0.95 else ("PARTIAL" if avg > 0.7 else "NONLINEAR")
        print(f"{bit:>4} | {lin:>16}/512 | {unc:>9} | {avg:>15.6f} | {status}")

        if status == "NONLINEAR":
            print(f"      CASCADE BREAKS at bit {bit}")
            return bit

    return 16  # All linear up to bit 15

def test_cascade_linearity_single(bit_pos, N):
    """Helper: measure linearity of one bit."""
    word = bit_pos // 32; bit = bit_pos % 32

    consistencies = []
    for _ in range(N):
        W16 = random_w16()
        H_base = sha256_compress(W16)
        base_bit = (H_base[word] >> bit) & 1

        # Sample 50 input bits
        for j in random.sample(range(512), 50):
            w=j//32; b=j%32
            W_p=list(W16); W_p[w]^=(1<<b)
            H_p = sha256_compress(W_p)
            flip = ((H_p[word]>>bit)&1) ^ base_bit
            consistencies.append(flip)

    c = np.array(consistencies)
    avg = np.mean(c)  # Should be ≈0.5 for random, ≈0 or ≈1 for linear
    avg_consistency = abs(avg - 0.5) + 0.5

    linearizable = int(avg_consistency > 0.95) * 512  # Approximate
    uncertain = int(0.4 < avg < 0.6) * 512

    return linearizable, uncertain, avg_consistency

def test_carry_cascade_depth(N=300):
    """
    Direct test: solve bit 0, predict carry_1, check bit 1, etc.

    For a WANG PAIR: at each bit position, is the feedforward carry
    predictable from lower bits?
    """
    print(f"\n--- CARRY CASCADE DEPTH ---")

    for word in range(8):
        depths = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

            # Bit-by-bit: can we predict hash bit from lower bits?
            depth = 0
            for bit in range(32):
                # Hash difference at this bit
                diff_bit = ((Hn[word]^Hf[word])>>bit) & 1

                # XOR difference at this bit (no carry, linear)
                state_n = sn[64]; state_f = sf[64]
                xor_diff_bit = ((state_n[word]^state_f[word])>>bit) & 1

                # Are they the same? (carry contribution = 0?)
                if diff_bit == xor_diff_bit:
                    depth += 1  # This bit = linear (carry didn't change it)
                else:
                    break  # Carry diverged

            depths.append(depth)

        da = np.array(depths)
        branch = "a" if word < 4 else "e"
        print(f"  H[{word}]({branch}): cascade depth mean={da.mean():.2f}, "
              f"min={da.min()}, max={da.max()}, P(depth≥5)={np.mean(da>=5):.4f}")

def test_algebraic_gain():
    """Calculate: if cascade depth = k, what's the collision cost?"""
    print(f"\n--- ALGEBRAIC GAIN CALCULATION ---")

    print(f"{'Cascade k':>9} | {'Free bits':>9} | {'Remaining':>9} | {'Birthday':>12} | {'Gain':>6}")
    print("-"*55)
    for k in [0, 1, 2, 3, 5, 8, 16, 32]:
        free = k * 8  # k bits × 8 words
        remaining = 256 - free
        birthday = remaining / 2
        gain = 128 - birthday
        print(f"{k:>9} | {free:>9} | {remaining:>9} | 2^{birthday:>8.0f} | {gain:>+5.0f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 68: CASCADED CARRY SOLVE")
    print("="*60)
    k = test_cascade_linearity(100)
    test_carry_cascade_depth(300)
    test_algebraic_gain()

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)
    print(f"CASCADE DEPTH determines collision advantage.")

if __name__ == "__main__":
    main()
