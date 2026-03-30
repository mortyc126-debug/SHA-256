#!/usr/bin/env python3
"""
EXP 66A: A_JOIN — Joint Algebra where XOR and MOD are ONE operation

Gap B from UTSCR: A_XOR and A_MOD connected by 50% carry noise.
Need: algebra where carry is NOT noise but PART of the operation.

IDEA: Work in Z/2^32 directly but represent elements as
(linear_part, carry_part) pairs. Define operations that
preserve this decomposition.

If A_JOIN has lower effective dimension than A_XOR or A_MOD
→ collision is cheaper in A_JOIN.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def join_representation(x):
    """Represent x ∈ Z/2^32 as (parity_vector, carry_potential).
    parity_vector = x (bits as-is)
    carry_potential[i] = number of consecutive 1-bits ending at position i.
    """
    parity = x
    # Carry potential: length of trailing 1-run at each position
    potential = [0]*32
    run = 0
    for i in range(32):
        if (x >> i) & 1:
            run += 1
        else:
            run = 0
        potential[i] = run
    return parity, potential

def join_add(a, b):
    """Addition in A_JOIN representation."""
    result = (a + b) & MASK
    # Decompose
    xor_part = a ^ b
    carry_part = ((a + b) & MASK) ^ (a ^ b)  # = 2*Γ(a,b)
    return result, xor_part, carry_part

def test_join_rank(N=50):
    """What is the rank of SHA-256 in A_JOIN representation?"""
    print("\n--- A_JOIN RANK ---")

    for R in [4, 16, 64]:
        # Build Jacobian in A_JOIN: for each input bit,
        # measure change in (xor_output, carry_output) separately
        ranks_xor = []; ranks_carry = []; ranks_join = []

        for _ in range(N):
            W16 = random_w16()
            states = sha256_rounds(W16, R)
            base = states[R]

            Jx = np.zeros((256, 512), dtype=np.int64)  # XOR Jacobian
            Jc = np.zeros((256, 512), dtype=np.int64)  # Carry Jacobian

            Hn = sha256_compress(W16) if R==64 else None
            base_hash = Hn if R==64 else [(IV[i]+base[i])&MASK for i in range(8)]
            base_xor = [IV[i]^base[i] for i in range(8)]
            base_carry_part = [base_hash[i]^base_xor[i] for i in range(8)]

            for j in range(512):
                w=j//32; b=j%32
                W_p=list(W16); W_p[w]^=(1<<b)

                if R==64:
                    pert_hash = sha256_compress(W_p)
                else:
                    s_p = sha256_rounds(W_p, R)
                    pert_hash = [(IV[i]+s_p[R][i])&MASK for i in range(8)]

                pert_xor = [IV[i]^(sha256_rounds(W_p,R)[R][i] if R<64 else 0) for i in range(8)]
                pert_carry = [pert_hash[i]^pert_xor[i] for i in range(8)]

                for i in range(256):
                    wi=i//32; bi=i%32
                    Jx[i][j] = ((base_xor[wi]>>bi)&1) ^ ((pert_xor[wi]>>bi)&1)
                    Jc[i][j] = ((base_carry_part[wi]>>bi)&1) ^ ((pert_carry[wi]>>bi)&1)

            # Joint Jacobian: stack XOR and carry
            J_join = np.vstack([Jx, Jc])  # 512 × 512

            rx = np.linalg.matrix_rank(Jx.astype(float))
            rc = np.linalg.matrix_rank(Jc.astype(float))
            rj = np.linalg.matrix_rank(J_join.astype(float))

            ranks_xor.append(rx); ranks_carry.append(rc); ranks_join.append(rj)

        print(f"  R={R:>2}: rank_xor={np.mean(ranks_xor):.0f}, "
              f"rank_carry={np.mean(ranks_carry):.0f}, "
              f"rank_join={np.mean(ranks_join):.0f}/512")

        if np.mean(ranks_join) < 512:
            deficit = 512 - np.mean(ranks_join)
            print(f"    *** JOIN RANK DEFICIT: {deficit:.0f} ***")
            print(f"    XOR and carry share {deficit:.0f} dimensions!")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 66A: A_JOIN ALGEBRA")
    print("="*60)
    test_join_rank(20)

if __name__ == "__main__":
    main()
