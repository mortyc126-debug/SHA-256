#!/usr/bin/env python3
"""
EXP 95: UALRA-Native — The Native Algebra of SHA-256

DERIVED FROM FIRST PRINCIPLES:

★(a,b) = (a⊕b, a&b) ∈ {0,1}^64

This is THE native operation. From it:
  π_xor(★) = first component = a⊕b
  π_and(★) = second component = a&b
  π_add(★) = a⊕b ⊕ 2·carry(a⊕b, a&b) = a+b

ROTR is automorphism of ★ (acts component-wise).
Carry = DERIVED (not fundamental) — computed from (xor, and).

SHA-256 state in UALRA = 8 × 64 = 512 bits (8 pairs).
Each pair = (xor_component, and_component).

COLLISION in UALRA: π_add(state₁) = π_add(state₂)
where state₁, state₂ ∈ A^8 = {0,1}^512.

KEY TEST: does UALRA-native representation make collision
ALGEBRAICALLY simpler?
"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

def star_encode(a, b):
    """★(a,b) = (a⊕b, a&b) — native UALRA representation."""
    return (a ^ b, a & b)

def star_to_add(xor_comp, and_comp):
    """Recover a+b from ★ representation."""
    # carry[i] = and_comp[i] | (xor_comp[i] & carry[i-1])
    # a+b = xor_comp ^ (carry << 1)
    carry = 0
    result = 0
    for i in range(32):
        x_bit = (xor_comp >> i) & 1
        a_bit = (and_comp >> i) & 1
        c_new = a_bit | (x_bit & carry)
        result |= ((x_bit ^ carry) << i)
        carry = c_new
    return result & MASK

def test_star_correctness(N=10000):
    """Verify ★ encoding is correct."""
    print("\n--- ★ CORRECTNESS ---")
    correct = 0
    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)
        x, y = star_encode(a, b)
        recovered = star_to_add(x, y)
        expected = (a + b) & MASK

        if recovered == expected and x == (a ^ b) and y == (a & b):
            correct += 1

    print(f"★ encoding correct: {correct}/{N}")

def test_star_rank(N=50):
    """What is the GF(2) rank in ★-representation?"""
    print(f"\n--- ★ RANK ---")

    for R in [4, 16, 64]:
        ranks = []
        for _ in range(N):
            W16 = random_w16()
            states = sha256_rounds(W16, R)
            base = states[R]

            # Build Jacobian in ★-space: 64-bit output per word
            # For word 4 (e-register): ★(IV[4], state[4]) = (IV[4]⊕state[4], IV[4]&state[4])
            base_xor = IV[4] ^ base[4]
            base_and = IV[4] & base[4]

            # 64-bit ★-output: (xor_32bits, and_32bits)
            J = np.zeros((64, 512), dtype=np.int64)

            for j in range(512):
                w = j // 32; b = j % 32
                W_p = list(W16); W_p[w] ^= (1 << b)
                s_p = sha256_rounds(W_p, R)
                pert = s_p[R]

                pert_xor = IV[4] ^ pert[4]
                pert_and = IV[4] & pert[4]

                for i in range(32):
                    J[i][j] = ((base_xor >> i) & 1) ^ ((pert_xor >> i) & 1)
                    J[32+i][j] = ((base_and >> i) & 1) ^ ((pert_and >> i) & 1)

            rank = np.linalg.matrix_rank(J.astype(float))
            ranks.append(rank)

        print(f"  R={R:>2}: ★-rank = {np.mean(ranks):.0f}/64 (vs standard 32)")

def test_star_collision_structure(N=2000):
    """In ★-space: do near-collision pairs have special ★-structure?"""
    print(f"\n--- ★ COLLISION STRUCTURE ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        # ★-difference: (δxor, δand) for feedforward
        star_diffs = []
        for w in range(8):
            xor_n = IV[w] ^ sn[64][w]; and_n = IV[w] & sn[64][w]
            xor_f = IV[w] ^ sf[64][w]; and_f = IV[w] & sf[64][w]
            d_xor = hw(xor_n ^ xor_f)
            d_and = hw(and_n ^ and_f)
            star_diffs.append((d_xor, d_and))

        total_d_xor = sum(d[0] for d in star_diffs)
        total_d_and = sum(d[1] for d in star_diffs)

        data.append((dH, total_d_xor, total_d_and))

    dH_a = np.array([d[0] for d in data])
    dx_a = np.array([d[1] for d in data])
    da_a = np.array([d[2] for d in data])

    print(f"E[δH]:     {dH_a.mean():.2f}")
    print(f"E[δ★_xor]: {dx_a.mean():.2f}")
    print(f"E[δ★_and]: {da_a.mean():.2f}")

    c_xor = np.corrcoef(dx_a, dH_a)[0,1]
    c_and = np.corrcoef(da_a, dH_a)[0,1]
    c_star = np.corrcoef(dx_a + da_a, dH_a)[0,1]
    c_diff = np.corrcoef(dx_a - da_a, dH_a)[0,1]
    c_prod = np.corrcoef(dx_a * da_a, dH_a)[0,1]

    threshold = 3/np.sqrt(N)
    print(f"\ncorr(δ★_xor, δH) = {c_xor:+.6f} {'***' if abs(c_xor)>threshold else ''}")
    print(f"corr(δ★_and, δH) = {c_and:+.6f} {'***' if abs(c_and)>threshold else ''}")
    print(f"corr(δ★_xor+δ★_and, δH) = {c_star:+.6f} {'***' if abs(c_star)>threshold else ''}")
    print(f"corr(δ★_xor−δ★_and, δH) = {c_diff:+.6f} {'***' if abs(c_diff)>threshold else ''}")
    print(f"corr(δ★_xor×δ★_and, δH) = {c_prod:+.6f} {'***' if abs(c_prod)>threshold else ''}")

    # KEY: is ★-difference MORE STRUCTURED than hash difference?
    # If δ★_xor and δ★_and are CORRELATED → structure
    c_xor_and = np.corrcoef(dx_a, da_a)[0,1]
    print(f"\ncorr(δ★_xor, δ★_and) = {c_xor_and:+.6f} {'***' if abs(c_xor_and)>threshold else ''}")

    if abs(c_xor_and) > threshold:
        print("*** XOR and AND components are CORRELATED in ★-space! ***")
        print("This means: ★-space has LOWER effective dimension than 2×256")

def test_star_vs_standard_birthday(N=30000):
    """Does ★-representation improve birthday?"""
    print(f"\n--- ★ BIRTHDAY TEST ---")

    # Standard: birthday on H (256 bits)
    standard_best = 256
    for _ in range(N):
        W1=random_w16(); W2=random_w16()
        H1=sha256_compress(W1); H2=sha256_compress(W2)
        d=sum(hw(H1[i]^H2[i]) for i in range(8))
        standard_best=min(standard_best,d)

    # ★-birthday: birthday on ★-hash (512 bits, but projected to 256)
    # If ★ has lower effective dimension → fewer unique ★-hashes → easier birthday
    star_hashes = set()
    for _ in range(N):
        W16=random_w16()
        states=sha256_rounds(W16,64)
        # ★-hash: (xor_components, and_components) for all 8 words
        star_h = []
        for w in range(8):
            star_h.append(IV[w]^states[64][w])
            star_h.append(IV[w]&states[64][w])
        star_hashes.add(tuple(star_h))

    standard_unique = N  # Assume all unique for standard (2^256 space)
    star_unique = len(star_hashes)

    birthday_standard = 128 - 8*math.sqrt(2*math.log(N))

    print(f"Standard: best δH = {standard_best}, birthday ≈ {birthday_standard:.0f}")
    print(f"★-unique hashes: {star_unique}/{N}")
    print(f"★-collision (same ★-hash): {N - star_unique}")

    if star_unique < N * 0.99:
        print(f"*** ★-space has COLLISIONS! {N-star_unique} pairs! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 95: UALRA-NATIVE")
    print("★(a,b) = (a⊕b, a&b)")
    print("="*60)

    test_star_correctness(5000)
    test_star_rank(20)
    test_star_collision_structure(3000)
    test_star_vs_standard_birthday(20000)

    print("\n"+"="*60)
    print("UALRA-NATIVE: ★ = (⊕, &)")
    print("SHA-256 lives in {0,1}^64 per word, not {0,1}^32")
    print("="*60)

if __name__=="__main__": main()
