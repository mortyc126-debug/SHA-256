#!/usr/bin/env python3
"""
EXP 49: Extended Freedom — 288 bits vs 256 target

From exp48: rank(W0,W1 → δH) = 64/64 (full).
But 64 bits < 256 needed.

STEP BACK: use more free parameters.
Partial Wang (8 zeros) frees DW[10..15] = 192 bits.
Total: W0(32) + W1(32) + DW0(32) + DW[10..15](192) = 288 bits.

If rank(288 → 256) = 256: we can SOLVE for collision directly!
One solution per 2^(288-256) = 2^32 attempts.

KEY: Is the Jacobian invertible? And does the nonlinear
correction (GF(2) solve ≠ real solve) leave a residual?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def partial_wang_with_free(W0, W1, DW0, DW_free):
    """
    Partial Wang: 8 zeros (DW[2..9]), then DW[10..15] = free.
    DW_free = list of 6 words for DW[10..15].
    """
    Wn = [W0, W1] + [0]*14
    DWs = [0]*16
    DWs[0] = DW0

    # DW2: De3=0
    Wf_tmp = [(Wn[i]+DWs[i])&MASK for i in range(16)]
    sn = sha256_rounds(Wn, 3); sf = sha256_rounds(Wf_tmp, 3)
    DWs[2] = (-de(sn, sf, 3)) & MASK

    # DW3..DW9: cascade De4..De10=0
    for step in range(7):
        wi = step+3; dt = step+4
        Wfc = [(Wn[i]+DWs[i])&MASK for i in range(16)]
        tn = sha256_rounds(Wn, dt)
        tf = sha256_rounds(Wfc, dt)
        DWs[wi] = (-de(tn, tf, dt)) & MASK

    # DW10..DW15: free
    for i in range(6):
        DWs[10+i] = DW_free[i]

    Wf = [(Wn[i]+DWs[i])&MASK for i in range(16)]
    return Wn, Wf, DWs

def test_extended_rank(N=100):
    """Measure rank of extended Jacobian (288 input bits → 256 output bits)."""
    print("\n--- TEST 1: EXTENDED RANK (288 → 256) ---")

    ranks = []
    for trial in range(N):
        # Random base point
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        DW0 = random.randint(1, MASK)  # Non-zero
        DW_free = [random.randint(0, MASK) for _ in range(6)]

        Wn, Wf, DWs = partial_wang_with_free(W0, W1, DW0, DW_free)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        # Base δH bits
        dH_base = []
        for w in range(8):
            d = Hn[w]^Hf[w]
            for b in range(32):
                dH_base.append((d>>b)&1)

        # Build Jacobian: 288 input bits → 256 output bits
        # Inputs: W0(32) + W1(32) + DW0(32) + DW10..15(192) = 288
        J = np.zeros((288, 256), dtype=np.int64)

        input_idx = 0
        # W0 bits
        for bit in range(32):
            W0p = W0 ^ (1<<bit)
            Wn_p, Wf_p, _ = partial_wang_with_free(W0p, W1, DW0, DW_free)
            Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
            for w in range(8):
                d=Hn_p[w]^Hf_p[w]
                for b in range(32):
                    J[input_idx][w*32+b] = ((d>>b)&1) ^ dH_base[w*32+b]
            input_idx += 1

        # W1 bits
        for bit in range(32):
            W1p = W1 ^ (1<<bit)
            Wn_p, Wf_p, _ = partial_wang_with_free(W0, W1p, DW0, DW_free)
            Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
            for w in range(8):
                d=Hn_p[w]^Hf_p[w]
                for b in range(32):
                    J[input_idx][w*32+b] = ((d>>b)&1) ^ dH_base[w*32+b]
            input_idx += 1

        # DW0 bits
        for bit in range(32):
            DW0p = DW0 ^ (1<<bit)
            if DW0p == 0: DW0p = 1
            Wn_p, Wf_p, _ = partial_wang_with_free(W0, W1, DW0p, DW_free)
            Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
            for w in range(8):
                d=Hn_p[w]^Hf_p[w]
                for b in range(32):
                    J[input_idx][w*32+b] = ((d>>b)&1) ^ dH_base[w*32+b]
            input_idx += 1

        # DW[10..15] bits
        for dw_idx in range(6):
            for bit in range(32):
                DW_p = list(DW_free)
                DW_p[dw_idx] ^= (1<<bit)
                Wn_p, Wf_p, _ = partial_wang_with_free(W0, W1, DW0, DW_p)
                Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
                for w in range(8):
                    d=Hn_p[w]^Hf_p[w]
                    for b in range(32):
                        J[input_idx][w*32+b] = ((d>>b)&1) ^ dH_base[w*32+b]
                input_idx += 1

        rank = np.linalg.matrix_rank(J.astype(np.float64))
        ranks.append(rank)

        if trial < 3:
            print(f"  Trial {trial}: rank = {rank}/256 (from 288 inputs)")

    ra = np.array(ranks)
    print(f"\nRank statistics ({N} trials):")
    print(f"  Mean: {ra.mean():.1f}")
    print(f"  Min: {ra.min()}, Max: {ra.max()}")
    print(f"  Always 256: {np.all(ra==256)}")

    if ra.mean() >= 255:
        print(f"\n*** RANK ≈ 256: Full controllability! ***")
        print(f"288 input bits → 256 output bits at full rank")
        print(f"Excess freedom: 288 - 256 = 32 bits")
        print(f"Expected: one collision per 2^32 attempts")
        print(f"But: this is GF(2) rank. Nonlinearity adds correction.")

    return ra

def test_gf2_solve_residual(N=200):
    """
    Solve the GF(2) system J·x = target.
    Then apply the solution to REAL SHA-256.
    Measure RESIDUAL = how many bits are WRONG.
    """
    print(f"\n--- TEST 2: GF(2) SOLVE → REAL RESIDUAL ---")

    residuals = []
    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        DW0 = random.randint(1, MASK)
        DW_free = [random.randint(0, MASK) for _ in range(6)]

        Wn, Wf, DWs = partial_wang_with_free(W0, W1, DW0, DW_free)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        # Current δH
        dH_bits = []
        for w in range(8):
            d = Hn[w]^Hf[w]
            for b in range(32):
                dH_bits.append((d>>b)&1)
        target = np.array(dH_bits, dtype=np.int64)  # Want to flip these to 0

        # Build small Jacobian (just DW[10..15] = 192 bits → 256 bits)
        J = np.zeros((192, 256), dtype=np.int64)
        for dw_idx in range(6):
            for bit in range(32):
                DW_p = list(DW_free)
                DW_p[dw_idx] ^= (1<<bit)
                Wn_p,Wf_p,_ = partial_wang_with_free(W0, W1, DW0, DW_p)
                Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
                idx = dw_idx*32+bit
                for w in range(8):
                    d=Hn_p[w]^Hf_p[w]
                    for b in range(32):
                        J[idx][w*32+b] = ((d>>b)&1) ^ dH_bits[w*32+b]

        # GF(2) solve: J^T · x = target (192 variables, 256 equations)
        # Overdetermined — use least-squares over GF(2)
        Jt = J.T  # 256 × 192
        # Solve Jt · x = target via GF(2) Gaussian elimination
        Aug = np.hstack([Jt % 2, target.reshape(-1,1) % 2]).astype(np.int64)
        m, n_plus_1 = Aug.shape
        n = n_plus_1 - 1

        rank = 0
        for col in range(n):
            pivot = -1
            for row in range(rank, m):
                if Aug[row,col] % 2 == 1:
                    pivot=row; break
            if pivot == -1: continue
            Aug[[rank,pivot]] = Aug[[pivot,rank]]
            for row in range(m):
                if row!=rank and Aug[row,col]%2==1:
                    Aug[row]=(Aug[row]+Aug[rank])%2
            rank += 1

        # Extract solution (first rank variables)
        x = np.zeros(n, dtype=np.int64)
        piv = 0
        for col in range(n):
            if piv < m and Aug[piv, col] % 2 == 1:
                x[col] = Aug[piv, -1] % 2
                piv += 1

        # Apply GF(2) solution to real SHA-256
        DW_solved = list(DW_free)
        for dw_idx in range(6):
            for bit in range(32):
                if x[dw_idx*32+bit] == 1:
                    DW_solved[dw_idx] ^= (1 << bit)

        Wn_s,Wf_s,_ = partial_wang_with_free(W0, W1, DW0, DW_solved)
        Hn_s=sha256_compress(Wn_s); Hf_s=sha256_compress(Wf_s)
        dH_after = sum(hw(Hn_s[w]^Hf_s[w]) for w in range(8))

        residuals.append(dH_after)

    ra = np.array(residuals)
    dH_before_expected = 128  # Before solving, δH ≈ 128

    print(f"Before GF(2) solve: E[δH] ≈ 128")
    print(f"After GF(2) solve:  E[δH] = {ra.mean():.2f}, min={ra.min()}")
    print(f"Reduction: {128-ra.mean():.2f} bits")

    if ra.min() == 0:
        print(f"*** COLLISION FOUND! ***")
    elif ra.mean() < 100:
        print(f"*** SIGNIFICANT REDUCTION! GF(2) solve partially works! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 49: EXTENDED FREEDOM (288 bits → 256 target)")
    print("="*60)
    ranks = test_extended_rank(50)
    test_gf2_solve_residual(100)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
