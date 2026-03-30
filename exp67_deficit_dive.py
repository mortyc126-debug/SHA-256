#!/usr/bin/env python3
"""
EXP 67: Carry Deficit Deep Dive — IV dependence + cross-gap connections

Carry rank deficit = 13 (exp66A). The ONLY living structure.

Questions:
1. Is deficit=13 specific to SHA-256 IV, or universal?
   → Test with random IV, zero IV, all-ones IV
2. WHERE in the 256 bits is the deficit? Which 13 dimensions?
3. Does the deficit create exploitable structure in Walsh/schedule?
4. Deficit 13 at R=16 AND R=64 — what happens at R=1,2,4,8?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_carry_deficit(iv_vals, N=30, R=64):
    """Measure carry rank deficit for given IV."""
    ranks_xor=[]; ranks_carry=[]; ranks_join=[]

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, R, list(iv_vals))
        base = states[R]

        base_hash = [(iv_vals[i]+base[i])&MASK for i in range(8)]
        base_xor = [iv_vals[i]^base[i] for i in range(8)]
        base_carry = [base_hash[i]^base_xor[i] for i in range(8)]

        Jx = np.zeros((256, 512), dtype=np.int64)
        Jc = np.zeros((256, 512), dtype=np.int64)

        for j in range(512):
            w=j//32; b=j%32
            W_p=list(W16); W_p[w]^=(1<<b)
            s_p = sha256_rounds(W_p, R, list(iv_vals))
            pert = s_p[R]

            pert_hash = [(iv_vals[i]+pert[i])&MASK for i in range(8)]
            pert_xor = [iv_vals[i]^pert[i] for i in range(8)]
            pert_carry = [pert_hash[i]^pert_xor[i] for i in range(8)]

            for i in range(256):
                wi=i//32; bi=i%32
                Jx[i][j] = ((base_xor[wi]>>bi)&1) ^ ((pert_xor[wi]>>bi)&1)
                Jc[i][j] = ((base_carry[wi]>>bi)&1) ^ ((pert_carry[wi]>>bi)&1)

        J_join = np.vstack([Jx, Jc])
        ranks_xor.append(np.linalg.matrix_rank(Jx.astype(float)))
        ranks_carry.append(np.linalg.matrix_rank(Jc.astype(float)))
        ranks_join.append(np.linalg.matrix_rank(J_join.astype(float)))

    return np.mean(ranks_xor), np.mean(ranks_carry), np.mean(ranks_join)

def test_iv_dependence():
    """Is carry deficit IV-specific?"""
    print("\n--- CARRY DEFICIT vs IV ---")

    ivs = {
        'SHA-256 IV': list(IV),
        'Zero IV': [0]*8,
        'All-ones IV': [MASK]*8,
        'Random IV 1': [random.randint(0,MASK) for _ in range(8)],
        'Random IV 2': [random.randint(0,MASK) for _ in range(8)],
        'Random IV 3': [random.randint(0,MASK) for _ in range(8)],
        'Alternating': [0x55555555]*4 + [0xAAAAAAAA]*4,
        'Low HW': [0x00000001]*8,
        'High HW': [0xFFFFFFFE]*8,
    }

    print(f"{'IV type':>16} | {'rank_xor':>8} | {'rank_carry':>10} | {'rank_join':>9} | {'deficit':>7}")
    print("-"*60)

    for name, iv in ivs.items():
        rx, rc, rj = measure_carry_deficit(iv, N=15, R=64)
        deficit = 256 - rc
        print(f"{name:>16} | {rx:>8.0f} | {rc:>10.0f} | {rj:>9.0f} | {deficit:>7.0f}")

def test_deficit_per_round():
    """How does deficit evolve with rounds?"""
    print(f"\n--- CARRY DEFICIT vs ROUNDS ---")

    print(f"{'Rounds':>6} | {'rank_carry':>10} | {'deficit':>7} | {'rank_join':>9}")
    print("-"*45)

    for R in [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]:
        rx, rc, rj = measure_carry_deficit(list(IV), N=10, R=R)
        deficit = int(round(min(256, rx))) - int(round(rc))
        print(f"{R:>6} | {rc:>10.0f} | {deficit:>7} | {rj:>9.0f}")

def test_which_dimensions():
    """WHICH 13 carry dimensions are missing?"""
    print(f"\n--- WHICH DIMENSIONS ARE DEFICIT? ---")

    # For one message: measure carry Jacobian, find its nullspace
    W16 = random_w16()
    states = sha256_rounds(W16, 64)
    base = states[64]

    base_hash = [(IV[i]+base[i])&MASK for i in range(8)]
    base_xor = [IV[i]^base[i] for i in range(8)]
    base_carry = [base_hash[i]^base_xor[i] for i in range(8)]

    Jc = np.zeros((256, 512), dtype=np.float64)

    for j in range(512):
        w=j//32; b=j%32
        W_p=list(W16); W_p[w]^=(1<<b)
        s_p = sha256_rounds(W_p, 64)
        pert = s_p[64]
        pert_hash = [(IV[i]+pert[i])&MASK for i in range(8)]
        pert_xor = [IV[i]^pert[i] for i in range(8)]
        pert_carry = [pert_hash[i]^pert_xor[i] for i in range(8)]

        for i in range(256):
            wi=i//32; bi=i%32
            Jc[i][j] = float(((base_carry[wi]>>bi)&1) ^ ((pert_carry[wi]>>bi)&1))

    # SVD to find weak directions
    U, S, Vt = np.linalg.svd(Jc)

    print(f"Carry Jacobian singular values:")
    print(f"  Top 5: {S[:5].round(2)}")
    print(f"  Around deficit: S[240..256]:")
    for i in range(240, 256):
        print(f"    S[{i}] = {S[i]:.6f} {'← DEFICIT' if S[i] < 0.1 else ''}")

    # Which output bits are in the deficit?
    n_deficit = np.sum(S < 0.1)
    print(f"\n  Dimensions with S < 0.1: {n_deficit}")

    if n_deficit > 0:
        deficit_vectors = U[:, -n_deficit:]  # Last n_deficit columns of U
        # Which output bits have largest weight in deficit vectors?
        deficit_weight = np.sum(np.abs(deficit_vectors), axis=1)
        top_bits = np.argsort(deficit_weight)[::-1][:20]
        print(f"\n  Output bits most in deficit:")
        for idx in top_bits:
            w = idx // 32; b = idx % 32
            branch = "a" if w < 4 else "e"
            print(f"    H[{w}]({branch}) bit {b:>2}: weight={deficit_weight[idx]:.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 67: CARRY DEFICIT DEEP DIVE")
    print("="*60)
    test_iv_dependence()
    test_deficit_per_round()
    test_which_dimensions()

    print("\n"+"="*60)
    print("IMPLICATIONS")
    print("="*60)

if __name__ == "__main__":
    main()
