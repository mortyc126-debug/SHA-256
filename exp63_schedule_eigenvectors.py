#!/usr/bin/env python3
"""
EXP 63: Schedule Eigenvectors — Self-Referential Messages

Schedule: W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]
This is a LINEAR recurrence over GF(2) (ignoring carries in +).

XOR-schedule: W[t] = σ1(W[t-2]) ⊕ W[t-7] ⊕ σ0(W[t-15]) ⊕ W[t-16]
This IS linear over GF(2). Has eigenvalues.

If W[0..15] = eigenvector of XOR-schedule → W[16..63] = structured.
These messages make the schedule PREDICTABLE → round function
receives STRUCTURED input → potentially exploitable.

Even with carries: messages near eigenvectors have
PARTIALLY structured schedules → partial exploitation.

Questions:
1. What are the eigenvalues of the XOR-schedule matrix?
2. Do eigenvector messages have different collision properties?
3. Does structured schedule create lower δH?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def build_xor_schedule_matrix():
    """
    Build 512×512 GF(2) matrix M such that
    [W[16]..W[31]] = M · [W[0]..W[15]] over GF(2).

    Each W[t] is 32 bits, so the matrix maps 16×32=512 bits → 16×32=512 bits.
    """
    n = 512  # 16 words × 32 bits

    # Represent schedule as bit operations
    # W[t] = σ1(W[t-2]) ⊕ W[t-7] ⊕ σ0(W[t-15]) ⊕ W[t-16]

    # Build bit-level matrix: output[i] = XOR of input bits
    # Output bits: W[16..31] = 16 words × 32 bits = 512
    # Input bits: W[0..15] = 512

    M = np.zeros((n, n), dtype=np.int64)

    # For each output bit, determine which input bits affect it
    for out_word_offset in range(16):  # W[16+offset]
        t = 16 + out_word_offset

        # Determine which input words are needed
        # σ1(W[t-2]): need W[t-2] = W[14+offset] or W[offset-2+16] if offset<2
        # W[t-7]: need W[t-7]
        # σ0(W[t-15]): need W[t-15]
        # W[t-16]: need W[t-16] = W[offset]

        deps = {
            't-2': t - 2,   # For σ1
            't-7': t - 7,   # Direct
            't-15': t - 15, # For σ0
            't-16': t - 16, # Direct
        }

        for out_bit in range(32):
            out_idx = out_word_offset * 32 + out_bit

            # σ1(W[t-2]): ROTR17 ⊕ ROTR19 ⊕ SHR10
            w_idx = deps['t-2']
            if 0 <= w_idx < 16:
                for rot, is_shr in [(17, False), (19, False), (10, True)]:
                    if is_shr:
                        src_bit = out_bit + rot
                        if src_bit < 32:
                            M[out_idx][(w_idx * 32 + src_bit) % n] ^= 1
                    else:
                        src_bit = (out_bit + rot) % 32
                        M[out_idx][(w_idx * 32 + src_bit) % n] ^= 1

            # W[t-7]: direct copy
            w_idx = deps['t-7']
            if 0 <= w_idx < 16:
                M[out_idx][(w_idx * 32 + out_bit) % n] ^= 1

            # σ0(W[t-15]): ROTR7 ⊕ ROTR18 ⊕ SHR3
            w_idx = deps['t-15']
            if 0 <= w_idx < 16:
                for rot, is_shr in [(7, False), (18, False), (3, True)]:
                    if is_shr:
                        src_bit = out_bit + rot
                        if src_bit < 32:
                            M[out_idx][(w_idx * 32 + src_bit) % n] ^= 1
                    else:
                        src_bit = (out_bit + rot) % 32
                        M[out_idx][(w_idx * 32 + src_bit) % n] ^= 1

            # W[t-16]: direct copy
            w_idx = deps['t-16']
            if 0 <= w_idx < 16:
                M[out_idx][(w_idx * 32 + out_bit) % n] ^= 1

    return M % 2

def gf2_eigenanalysis(M):
    """Analyze eigenstructure of binary matrix over GF(2)."""
    n = M.shape[0]

    # Check: M^k = I for what k? (Order of M in GL(n, GF(2)))
    current = M.copy()
    for k in range(1, 100):
        current = (current @ M) % 2
        if np.array_equal(current, np.eye(n, dtype=np.int64)):
            return k  # Order of M
    return -1  # Order > 100

def test_schedule_matrix(N=100):
    """Analyze XOR-schedule matrix."""
    print("\n--- XOR-SCHEDULE MATRIX ---")

    M = build_xor_schedule_matrix()
    rank = np.linalg.matrix_rank(M.astype(np.float64))

    print(f"Schedule matrix: {M.shape}")
    print(f"GF(2)-approx rank: {rank}/512")
    print(f"Density: {M.sum()/(512*512):.4f}")

    # Fixed points: M·x = x over GF(2) → (M+I)·x = 0
    MI = (M + np.eye(512, dtype=np.int64)) % 2
    rank_MI = np.linalg.matrix_rank(MI.astype(np.float64))
    nullity_MI = 512 - rank_MI
    print(f"\nFixed points (M·x = x):")
    print(f"  rank(M+I) = {rank_MI}")
    print(f"  nullity(M+I) = {nullity_MI}")
    if nullity_MI > 0:
        print(f"  *** {nullity_MI} fixed-point dimensions! ***")

    # Period-2: M²·x = x → (M²+I)·x = 0
    M2 = (M @ M) % 2
    MI2 = (M2 + np.eye(512, dtype=np.int64)) % 2
    rank_MI2 = np.linalg.matrix_rank(MI2.astype(np.float64))
    nullity_MI2 = 512 - rank_MI2
    print(f"\nPeriod-2 points (M²·x = x):")
    print(f"  nullity(M²+I) = {nullity_MI2}")

    return M, nullity_MI

def test_eigenvector_messages(M, N=500):
    """Test: do messages near schedule eigenvectors have special properties?"""
    print(f"\n--- EIGENVECTOR MESSAGES vs RANDOM ---")

    # If M+I has nullity k → there are 2^k fixed-point messages
    # These messages have W[16..31] = W[0..15] (in XOR-schedule)

    MI = (M + np.eye(512, dtype=np.int64)) % 2

    # Find a nullspace vector (if exists)
    # Simple: try random x, compute (M+I)·x, check if 0
    fixed_msgs = []
    for _ in range(N):
        x = np.random.randint(0, 2, 512).astype(np.int64)
        if np.all((MI @ x) % 2 == 0):
            fixed_msgs.append(x)

    print(f"Fixed-point messages found: {len(fixed_msgs)}/{N}")

    if len(fixed_msgs) > 0:
        # Convert to W16 and measure collision properties
        eigen_dHs = []
        for x in fixed_msgs[:50]:
            W16 = [0]*16
            for i in range(16):
                for b in range(32):
                    W16[i] |= (int(x[i*32+b]) << b)

            # Wang cascade
            try:
                Wn,Wf,_,_,_ = wang_cascade(W16[0], W16[1])
                Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
                dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
                eigen_dHs.append(dH)
            except:
                pass

        if eigen_dHs:
            ea = np.array(eigen_dHs)
            print(f"Eigenvector δH: E={ea.mean():.2f}, min={ea.min()}")

    # Random baseline
    random_dHs = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            random_dHs.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))
        except: pass

    ra = np.array(random_dHs)
    print(f"Random δH: E={ra.mean():.2f}, min={ra.min()}")

def test_schedule_structure_impact(N=500):
    """How structured is the REAL (non-XOR) schedule for different messages?"""
    print(f"\n--- SCHEDULE STRUCTURE IMPACT ---")

    # Measure: for each message, how close is real schedule to XOR schedule?
    # Difference = carry contribution to schedule
    dists = []
    for _ in range(N):
        W16 = random_w16()
        W_real = schedule(W16)

        # XOR schedule
        W_xor = list(W16) + [0]*48
        for t in range(16, 64):
            W_xor[t] = sig1(W_xor[t-2]) ^ W_xor[t-7] ^ sig0(W_xor[t-15]) ^ W_xor[t-16]

        # Distance real vs XOR
        dist = sum(hw(W_real[t] ^ W_xor[t]) for t in range(16, 64))
        dists.append(dist)

    da = np.array(dists)
    print(f"Schedule real vs XOR: E[HW]={da.mean():.1f}, std={da.std():.1f}")
    print(f"Max possible: {48*32} = {48*32}")
    print(f"Fraction: {da.mean()/(48*32)*100:.1f}%")

    # Does schedule distance predict δH?
    dH_list = []
    sched_list = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        W_real = schedule(Wn)
        W_xor = list(Wn)+[0]*48
        for t in range(16,64):
            W_xor[t]=sig1(W_xor[t-2])^W_xor[t-7]^sig0(W_xor[t-15])^W_xor[t-16]

        sd = sum(hw(W_real[t]^W_xor[t]) for t in range(16,64))
        sched_list.append(sd)

        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH_list.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    c = np.corrcoef(sched_list, dH_list)[0,1]
    print(f"\ncorr(schedule_carry_dist, δH) = {c:+.6f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 63: SCHEDULE EIGENVECTORS")
    print("Self-referential messages")
    print("="*60)

    M, nullity = test_schedule_matrix()
    test_eigenvector_messages(M, 200)
    test_schedule_structure_impact(400)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
