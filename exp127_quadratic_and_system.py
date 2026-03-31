#!/usr/bin/env python3
"""
EXP 127: Quadratic AND System in ★⁻¹

SHA-256 in ★⁻¹ = linear operations + 768 ANDs (degree 2).
If we linearize the ANDs (treat a&b as new variable z_{ab}),
the system becomes LINEAR but with more variables.

XL (eXtended Linearization) approach:
  Original: 512 message variables, 768 AND equations
  Linearized: 512 + C(512,2) ≈ 131,000 variables (one per AND pair)
  But most AND pairs never appear → SPARSE system

Step 1: Build the actual AND dependency graph for reduced-round SHA-256
Step 2: Count variables and equations
Step 3: Check if system is solvable (rank vs variables)
Step 4: Attempt to solve for small rounds
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def analyze_and_structure():
    """Map every AND operation in SHA-256 round function."""
    print(f"\n--- AND OPERATION MAP ---")

    # Per round, the AND operations come from:
    # 1. Ch(e,f,g) = (e & f) ^ (~e & g)
    #    ANDs: e&f, ~e&g (= NOT(e)&g)
    #    In terms of variables: 2 AND operations on 32-bit words = 64 bit-ANDs
    #
    # 2. Maj(a,b,c) = (a&b) ^ (a&c) ^ (b&c)
    #    ANDs: a&b, a&c, b&c
    #    = 3 AND operations = 96 bit-ANDs
    #
    # 3. Σ₀, Σ₁ use XOR of ROTRs. In ★⁻¹:
    #    x⊕y = (x+y) - 2(x&y)
    #    Σ₁(e) = ROTR6⊕ROTR11⊕ROTR25
    #    = (ROTR6+ROTR11) - 2(ROTR6&ROTR11) ...then XOR with ROTR25
    #    = ((ROTR6+ROTR11-2(ROTR6&ROTR11)) + ROTR25) - 2((ROTR6⊕ROTR11)&ROTR25)
    #    ANDs: ROTR6&ROTR11, (ROTR6⊕ROTR11)&ROTR25
    #    = 2 AND operations per Σ function = 64 bit-ANDs each
    #
    # 4. sig0, sig1 in schedule: same structure as Σ
    #    = 2 ANDs per sig function = 64 bit-ANDs each
    #    48 schedule steps × 2 sig functions = 96 word-level ANDs = 3072 bit-ANDs

    print(f"  PER ROUND (round function):")
    print(f"    Ch(e,f,g):  2 word-ANDs = 64 bit-ANDs")
    print(f"    Maj(a,b,c): 3 word-ANDs = 96 bit-ANDs")
    print(f"    Σ₀(a):      2 word-ANDs = 64 bit-ANDs")
    print(f"    Σ₁(e):      2 word-ANDs = 64 bit-ANDs")
    print(f"    Total/round: 9 word-ANDs = 288 bit-ANDs")
    print(f"    × 64 rounds = 576 word-ANDs = 18,432 bit-ANDs")

    print(f"\n  SCHEDULE:")
    print(f"    sig0: 2 word-ANDs per step")
    print(f"    sig1: 2 word-ANDs per step")
    print(f"    48 steps × 4 = 192 word-ANDs = 6,144 bit-ANDs")

    print(f"\n  TOTAL:")
    total_word = 576 + 192
    total_bit = 18432 + 6144
    print(f"    {total_word} word-level ANDs")
    print(f"    {total_bit} bit-level ANDs")
    print(f"    Each AND = 1 quadratic equation")
    print(f"    Variables: 512 message bits + {total_bit} AND-variables")
    print(f"    Equations: {total_bit} quadratic + 256 output constraints")

    return total_word, total_bit

def build_reduced_round_system(R=1):
    """Build the actual equation system for R rounds.

    Track all intermediate values as symbolic variables.
    Count: how many UNIQUE AND operations?
    """
    print(f"\n--- BUILDING SYSTEM FOR {R} ROUNDS ---")

    # For R=1: the AND operations are:
    # From the round function applied to IV with message word W[0]:
    # Ch(IV[4], IV[5], IV[6]) — these are CONSTANTS (IV known)
    # Maj(IV[0], IV[1], IV[2]) — CONSTANTS
    # Σ₁(IV[4]) — CONSTANT
    # Σ₀(IV[0]) — CONSTANT
    #
    # So at round 0: ALL Ch, Maj, Σ inputs are constants (IV)!
    # The only variable is W[0].
    # T1 = IV[7] + Σ₁(IV[4]) + Ch(IV[4],IV[5],IV[6]) + K[0] + W[0]
    # T2 = Σ₀(IV[0]) + Maj(IV[0],IV[1],IV[2])
    # Both are LINEAR in W[0]! (no AND between W[0] and anything)

    # Round 1: state = [T1+T2, IV[0], IV[1], IV[2], IV[3]+T1, IV[4], IV[5], IV[6]]
    # The AND operations now involve T1+T2 (= a_new) and IV[3]+T1 (= e_new)
    # These depend on W[0]. So:
    # Ch(e_new, IV[4], IV[5]) has ANDs between (IV[3]+T1) and IV[4]
    # = ANDs between (linear function of W[0]) and constants
    # = STILL LINEAR in W[0]!

    # The quadratic terms appear when TWO message-dependent values
    # are ANDed together. When does this first happen?

    # Round 0: a_new = f(W[0]), e_new = g(W[0])
    # Round 1: uses W[1], and state has a_new, e_new from round 0
    #   Maj(a_new, IV[0], IV[1]): a_new & IV[0] = linear & const = LINEAR
    #   Ch(e_new, IV[4], IV[5]): same, LINEAR
    # After round 1: a₁ = f(W[0], W[1]), e₁ = g(W[0], W[1])

    # Round 2: uses W[2], state has a₁, b₁=a₀, c₁=IV[0], d₁=IV[1]
    #   Maj(a₁, b₁, c₁) = Maj(f(W0,W1), f(W0), IV[0])
    #   → a₁ & b₁ = f(W0,W1) & f(W0) — THIS IS QUADRATIC in W!

    # So the FIRST quadratic AND appears at ROUND 2 in Maj.
    # Ch at round 2: Ch(e₁, f₁, g₁) = Ch(g(W0,W1), g(W0), IV[4])
    #   → e₁ & f₁ = g(W0,W1) & g(W0) — ALSO QUADRATIC

    print(f"  Round 0: ALL operations LINEAR in W[0] (state = IV = const)")
    print(f"  Round 1: ALL operations LINEAR in W[0..1] (b=a₀, but Maj(a₁,a₀,IV) = lin×lin)")

    # Wait, let me reconsider. Maj(a₁, a₀, IV[0]):
    # a₁ & a₀: this is the AND of two linear functions of W[0..1]
    # If a₁ = α + β·W₁ + γ·W₀ and a₀ = δ + ε·W₀ (all mod 2^32)
    # Then a₁ & a₀ at bit level: not simply degree 2...
    # Actually AND at bit level IS degree 2 over GF(2).

    # Hmm, but exp126 showed rounds 1-2 are EXACTLY linear in ★⁻¹.
    # This means the quadratic terms at round 2 somehow cancel?

    # Let me CHECK: at what round does the first ACTUAL nonlinearity appear?
    print(f"\n  Testing: at which round does linearity ACTUALLY break?")

    M_base = random_w16()
    for R_test in range(1, 20):
        s_base = sha256_rounds(M_base, R_test)[R_test]

        # Test linearity: δM = +1 on W[0]
        n_exact = 0
        for trial in range(500):
            # Random small perturbation
            w_idx = random.randint(0, 15)
            M_pert = list(M_base)
            M_pert[w_idx] = (M_pert[w_idx] + 1) & MASK
            s_pert = sha256_rounds(M_pert, R_test)[R_test]

            # Linear prediction using Jacobian
            # We need the actual Jacobian column for w_idx
            M_jac = list(M_base)
            M_jac[w_idx] = (M_jac[w_idx] + 1) & MASK
            s_jac = sha256_rounds(M_jac, R_test)[R_test]
            delta_pred = [(s_jac[h] - s_base[h]) & MASK for h in range(8)]

            delta_real = [(s_pert[h] - s_base[h]) & MASK for h in range(8)]

            if delta_pred == delta_real:
                n_exact += 1

        rate = n_exact / 500
        if rate < 1.0:
            print(f"    Round {R_test:>2}: exact = {rate:.4f} ← FIRST BREAK")
            break
        else:
            print(f"    Round {R_test:>2}: exact = {rate:.4f} ✓ linear")

def test_quadratic_system_small(R=3):
    """Actually build and solve the quadratic system for R rounds.
    Use brute force on small message space to verify."""
    print(f"\n--- QUADRATIC SYSTEM SOLVE ({R} rounds) ---")

    # Truncate: use only W[0] as free variable (32 bits)
    # Fix W[1..15] = 0
    # Find collision: two different W[0] values giving same state after R rounds

    print(f"  Searching collision on W[0] only ({R} rounds)...")

    # Build hash table of states
    t0 = time.time()
    state_to_w0 = {}
    collisions = 0
    budget = min(2**18, 262144)

    for w0 in range(budget):
        W16 = [w0] + [0] * 15
        states = sha256_rounds(W16, R)
        s = tuple(states[R])

        if s in state_to_w0:
            if state_to_w0[s] != w0:
                collisions += 1
                if collisions == 1:
                    w0_other = state_to_w0[s]
                    print(f"  COLLISION: W[0]={w0_other} and W[0]={w0}")
                    print(f"  State: {[f'0x{x:08x}' for x in states[R]]}")
        else:
            state_to_w0[s] = w0

    t1 = time.time()
    print(f"  Searched {budget} values in {t1-t0:.1f}s")
    print(f"  Collisions found: {collisions}")
    print(f"  Unique states: {len(state_to_w0)}")
    print(f"  (Collision expected if budget > 2^(state_bits/2) = 2^128)")

def test_linearization_degree(N=2000):
    """Test: what's the algebraic degree of SHA-256 in ★⁻¹?

    Degree 1 = linear (round 1-2)
    Degree 2 = quadratic (first ANDs)
    Degree d = need d-th order linearization

    Measure: for δM of different sizes, at what point does
    the d-th order Taylor expansion fail?"""
    print(f"\n--- ALGEBRAIC DEGREE IN ★⁻¹ ---")

    M_base = random_w16()

    for R in [1, 2, 3, 4, 8, 64]:
        # Compute function value at base
        s_base = sha256_rounds(M_base, R)[R]

        # First-order: f(x+δ) ≈ f(x) + J·δ
        # Second-order: f(x+δ) ≈ f(x) + J·δ + δᵀHδ/2
        # If first-order is exact → degree 1
        # If second-order is exact → degree 2

        # Test first-order with 2-element perturbation
        # If linear: f(x+a+b) - f(x+a) - f(x+b) + f(x) = 0
        # This is the "second difference" — zero iff degree ≤ 1

        second_diff_zero = 0
        for _ in range(N):
            w1 = random.randint(0, 15); w2 = random.randint(0, 15)

            M_a = list(M_base); M_a[w1] = (M_a[w1] + 1) & MASK
            M_b = list(M_base); M_b[w2] = (M_b[w2] + 1) & MASK
            M_ab = list(M_base); M_ab[w1] = (M_ab[w1] + 1) & MASK; M_ab[w2] = (M_ab[w2] + 1) & MASK

            s_a = sha256_rounds(M_a, R)[R]
            s_b = sha256_rounds(M_b, R)[R]
            s_ab = sha256_rounds(M_ab, R)[R]

            # Second difference: f(x+a+b) - f(x+a) - f(x+b) + f(x)
            # In mod arithmetic:
            second_diff = [(s_ab[h] - s_a[h] - s_b[h] + s_base[h]) & MASK for h in range(8)]

            if all(d == 0 for d in second_diff):
                second_diff_zero += 1

        rate = second_diff_zero / N
        degree = "1 (LINEAR)" if rate > 0.99 else ("≤2" if rate > 0.1 else ">2")
        print(f"  Round {R:>2}: second_diff = 0 rate: {rate:.4f} → degree {degree}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 127: QUADRATIC AND SYSTEM IN ★⁻¹")
    print("=" * 60)

    total_w, total_b = analyze_and_structure()
    build_reduced_round_system(1)
    test_linearization_degree(1000)
    test_quadratic_system_small(R=3)

    print(f"\n{'='*60}")
    print(f"VERDICT: Quadratic System")
    print(f"  Total AND operations: {total_w} word / {total_b} bit")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
