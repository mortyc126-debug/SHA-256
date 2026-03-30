#!/usr/bin/env python3
"""
EXP 56: Algebraic Composition Structure

SHA-256 = f63∘...∘f0. Each fr is degree 2.
Naive composition: degree 2^64. Actual: degree ~32.
GAP: 2^64 → 32 means massive algebraic cancellation.

KEY QUESTION: How many MONOMIALS does SHA-256 actually need?
If #monomials < 2^128 → polynomial system is sparse → solvable.

Also: degree grows as min(r, 32), NOT 2^r.
Why 32? Because carry chain length = word size = 32.
At degree 32: all 32 carry bits contribute → saturation.

Structure: shift register makes 6/8 state words COPIES.
Only a[r] and e[r] are nonlinear per round.
→ 2 nonlinear operations per round × 64 rounds.
→ But degree saturates at 32, not 128.

The algebraic cancellation = carry chain SELF-HEALING.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_algebraic_degree(W16, target_word, target_bit, max_order=10):
    """
    Measure algebraic degree of output bit (word, bit) w.r.t. input bits.

    Use higher-order differentials:
    Δ^k f = Σ_{S⊆{1..k}} (-1)^{|S|+k} f(x ⊕ ⊕_{i∈S} e_i)

    If Δ^k f = 0 for all directions → degree < k.
    """
    Hn_base = sha256_compress(W16)
    base_bit = (Hn_base[target_word] >> target_bit) & 1

    for order in range(1, max_order + 1):
        # Pick random directions
        directions = [random.randint(0, 15) * 32 + random.randint(0, 31)
                     for _ in range(order)]

        # Compute higher-order differential
        total = 0
        for subset_mask in range(1 << order):
            W_pert = list(W16)
            for i in range(order):
                if (subset_mask >> i) & 1:
                    word = directions[i] // 32
                    bit = directions[i] % 32
                    W_pert[word] ^= (1 << bit)

            H_pert = sha256_compress(W_pert)
            bit_val = (H_pert[target_word] >> target_bit) & 1
            total ^= bit_val

        if total == 0:
            return order - 1  # Degree < order

    return max_order  # Degree ≥ max_order

def test_degree_per_round(N=50):
    """Measure actual algebraic degree at different round counts."""
    print("\n--- ALGEBRAIC DEGREE vs ROUNDS ---")

    print(f"{'Rounds':>6} | {'Measured degree':>14} | {'Theory (min(r,32))':>18}")
    print("-"*45)

    for R in [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 48, 64]:
        degrees = []
        for _ in range(N):
            W16 = random_w16()

            # Compute R-round hash
            states = sha256_rounds(W16, R)
            final = states[R]

            # Measure degree of output bit e[R] bit 0
            # Use higher-order differential at this round count
            for order in range(1, 35):
                dirs = [random.randint(0, 511) for _ in range(order)]

                total = 0
                for mask in range(1 << order):
                    W_p = list(W16)
                    for i in range(order):
                        if (mask >> i) & 1:
                            W_p[dirs[i]//32] ^= (1 << (dirs[i]%32))

                    s_p = sha256_rounds(W_p, R)
                    bit = (s_p[R][4] >> 0) & 1  # e-register bit 0
                    total ^= bit

                if total == 0:
                    degrees.append(order - 1)
                    break
            else:
                degrees.append(34)

            if len(degrees) >= 5:
                break  # Enough samples per round count

        mean_deg = np.mean(degrees) if degrees else 0
        theory = min(R, 32)
        print(f"{R:>6} | {mean_deg:>14.1f} | {theory:>18}")

def test_monomial_count(N=200):
    """
    Estimate number of active monomials in SHA-256's ANF.

    Method: for each input bit i, measure if it INDIVIDUALLY
    affects the output. Count of "active" input bits = degree-1 monomial count.

    For degree-2: count pairs (i,j) where flipping BOTH changes output
    differently from flipping each alone. This is the quadratic monomial count.
    """
    print(f"\n--- MONOMIAL COUNTING ---")

    for R in [4, 8, 16, 64]:
        # Degree-1 monomials: how many input bits affect output bit?
        active_inputs = set()

        W16 = random_w16()
        states = sha256_rounds(W16, R)
        base_bit = (states[R][4] >> 0) & 1  # e[R] bit 0

        for word in range(16):
            for bit in range(32):
                W_p = list(W16)
                W_p[word] ^= (1 << bit)
                s_p = sha256_rounds(W_p, R)
                if ((s_p[R][4] >> 0) & 1) != base_bit:
                    active_inputs.add(word * 32 + bit)

        # Degree-2 monomials (sample)
        n_quad = 0
        n_tested = 0
        for _ in range(min(N, 1000)):
            i = random.randint(0, 511)
            j = random.randint(0, 511)
            if i == j: continue

            # Flip i only
            W_i = list(W16); W_i[i//32] ^= (1 << (i%32))
            s_i = sha256_rounds(W_i, R)
            b_i = (s_i[R][4] >> 0) & 1

            # Flip j only
            W_j = list(W16); W_j[j//32] ^= (1 << (j%32))
            s_j = sha256_rounds(W_j, R)
            b_j = (s_j[R][4] >> 0) & 1

            # Flip both
            W_ij = list(W16)
            W_ij[i//32] ^= (1 << (i%32))
            W_ij[j//32] ^= (1 << (j%32))
            s_ij = sha256_rounds(W_ij, R)
            b_ij = (s_ij[R][4] >> 0) & 1

            # Quadratic term = f(x+ei+ej) ⊕ f(x+ei) ⊕ f(x+ej) ⊕ f(x)
            quad = b_ij ^ b_i ^ b_j ^ base_bit
            if quad: n_quad += 1
            n_tested += 1

        quad_density = n_quad / n_tested if n_tested > 0 else 0
        est_total_quad = int(quad_density * 512 * 511 / 2)

        print(f"  R={R:>2}: active_inputs={len(active_inputs)}/512, "
              f"quad_density={quad_density:.4f}, "
              f"est_quad_monomials≈{est_total_quad}")

def test_composition_cancellation(N=100):
    """
    Measure algebraic cancellation in composition.

    At round R: degree-2 has ~X monomials.
    At round R+1: if no cancellation, ~X^2 monomials.
    Actual: measure X at R+1.
    Cancellation = X^2 - actual.
    """
    print(f"\n--- COMPOSITION CANCELLATION ---")

    W16 = random_w16()
    prev_quad_density = 0

    print(f"{'Round':>5} | {'Active inputs':>13} | {'Quad density':>12} | "
          f"{'Cancellation':>12}")
    print("-"*50)

    for R in range(1, 33):
        states = sha256_rounds(W16, R)
        base_bit = (states[R][4] >> 0) & 1

        # Count active inputs
        active = 0
        for word in range(16):
            for bit in range(32):
                W_p = list(W16); W_p[word] ^= (1 << bit)
                s_p = sha256_rounds(W_p, R)
                if ((s_p[R][4] >> 0) & 1) != base_bit:
                    active += 1

        # Sample quadratic density
        n_quad = 0; n_test = min(N, 500)
        for _ in range(n_test):
            i = random.randint(0, 511); j = random.randint(0, 511)
            if i == j: continue
            W_i=list(W16); W_i[i//32]^=(1<<(i%32))
            W_j=list(W16); W_j[j//32]^=(1<<(j%32))
            W_ij=list(W16); W_ij[i//32]^=(1<<(i%32)); W_ij[j//32]^=(1<<(j%32))
            s_i=sha256_rounds(W_i,R); s_j=sha256_rounds(W_j,R); s_ij=sha256_rounds(W_ij,R)
            quad = ((s_ij[R][4]>>0)&1) ^ ((s_i[R][4]>>0)&1) ^ ((s_j[R][4]>>0)&1) ^ base_bit
            if quad: n_quad += 1

        qd = n_quad / n_test
        expected_qd = min(1.0, prev_quad_density * 2 + 0.01) if R > 1 else qd
        cancellation = max(0, expected_qd - qd)
        prev_quad_density = qd

        if R in [1,2,3,4,5,6,7,8,10,12,16,20,24,32]:
            print(f"{R:>5} | {active:>13}/512 | {qd:>12.4f} | {cancellation:>12.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 56: ALGEBRAIC COMPOSITION STRUCTURE")
    print("="*60)
    test_degree_per_round(20)
    test_monomial_count(200)
    test_composition_cancellation(200)

    print("\n"+"="*60)
    print("IMPLICATIONS")
    print("="*60)
    print("If #monomials << 2^128 → sparse polynomial system")
    print("→ potential for algebraic solving below birthday")

if __name__ == "__main__":
    main()
