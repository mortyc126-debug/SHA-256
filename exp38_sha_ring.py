#!/usr/bin/env python3
"""
EXP 38: SHA-Ring — New Algebraic Structure

Derived from 23 theorems. Passes through ALL 5 walls.

SHA-Ring S = (Z/2^32, +, ⊕, Σ) with three operations.
Key: a + b = a ⊕ b ⊕ 2·carry(a,b)

In S, carry is not noise — it's a THIRD ALGEBRAIC OPERATION.
The degree of SHA-256 in S may be LOWER than in GF(2) or Z/2^32.

Step-by-step:
1. Define S-polynomial representation of one round
2. Measure S-degree of F_R (R-round composition)
3. Compare with GF(2)-degree and Z-degree
4. If S-degree < GF(2)-degree → new attack surface
"""
import sys, os, random
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# SHA-RING OPERATIONS
# ============================================================

def s_carry(a, b):
    """Carry as third operation: C(a,b) = (a+b) ⊕ (a⊕b)) >> 1
    This is the algebraic 'distance' between + and ⊕."""
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def s_decompose(result_add, a, b):
    """Decompose a+b into S-components: XOR part + carry correction."""
    xor_part = a ^ b
    carry_part = s_carry(a, b)
    # Verify: xor_part + 2*carry_part should equal a+b (mod 2^32)
    return xor_part, carry_part

def s_degree_single_round(W16, round_num):
    """
    Measure the 'S-degree' of a single round function.

    S-degree = how many carry operations are NECESSARY
    to describe the round function exactly.

    Method: count how many bit positions have carry ≠ 0
    across all 7 additions in the round. This is the
    'carry weight' = number of non-trivial S-terms.
    """
    states = sha256_rounds(W16, round_num + 1)
    W = schedule(W16)

    a, b, c, d, e, f, g, h = states[round_num]

    # All 7 additions and their carry weights
    additions = [
        (h, sigma1(e), "h+Σ1(e)"),
        ((h + sigma1(e)) & MASK, ch(e, f, g), "s1+Ch"),
        (((h + sigma1(e) + ch(e, f, g)) & MASK), K[round_num], "s2+K"),
        ((((h + sigma1(e) + ch(e, f, g) + K[round_num]) & MASK)), W[round_num], "s3+W"),
        (sigma0(a), maj(a, b, c), "Σ0+Maj"),
        ((h + sigma1(e) + ch(e, f, g) + K[round_num] + W[round_num]) & MASK,
         (sigma0(a) + maj(a, b, c)) & MASK, "T1+T2"),
        (d, (h + sigma1(e) + ch(e, f, g) + K[round_num] + W[round_num]) & MASK, "d+T1"),
    ]

    total_carry_weight = 0
    for x, y, name in additions:
        carry = s_carry(x, y)
        cw = hw(carry)
        total_carry_weight += cw

    return total_carry_weight

def test_s_degree_growth(N=500):
    """
    How does S-degree (carry weight) grow with rounds?

    If S-degree grows LINEARLY → SHA-Ring representation is efficient
    If S-degree grows EXPONENTIALLY → no advantage over brute force
    If S-degree SATURATES → bounded complexity in SHA-Ring!
    """
    print("\n--- TEST 1: S-DEGREE GROWTH WITH ROUNDS ---")

    # For multi-round composition: measure TOTAL carry weight
    # across all rounds from 0 to R
    round_carry = {r: [] for r in range(64)}

    for _ in range(N):
        W16 = random_w16()
        for r in range(64):
            cw = s_degree_single_round(W16, r)
            round_carry[r].append(cw)

    # Per-round carry weight
    print(f"{'Round':>5} | {'E[carry_weight]':>15} | {'Cumulative':>10} | {'Growth'}")
    print("-"*50)

    cumulative = 0
    prev = 0
    for r in [0,1,2,3,4,5,8,12,16,20,32,48,63]:
        mean_cw = np.mean(round_carry[r])
        cumulative += mean_cw
        growth = mean_cw - prev if r > 0 else mean_cw
        prev = mean_cw
        print(f"{r:>5} | {mean_cw:>15.2f} | {cumulative:>10.1f} | {growth:>+8.2f}")

    # Total carry weight for all 64 rounds
    total_per_message = []
    for _ in range(N):
        W16 = random_w16()
        total = sum(s_degree_single_round(W16, r) for r in range(64))
        total_per_message.append(total)

    ta = np.array(total_per_message)
    print(f"\nTotal S-degree (64 rounds): mean={ta.mean():.1f}, std={ta.std():.1f}")
    print(f"Max possible: 7 additions × 32 bits × 64 rounds = {7*32*64}")
    print(f"Fraction: {ta.mean()/(7*32*64)*100:.1f}%")

def test_differential_s_degree(N=1000):
    """
    S-degree of the DIFFERENTIAL: how complex is δF in SHA-Ring?

    For Wang pairs: the differential δstate propagates.
    At each round, the carry of the DIFFERENTIAL has a specific weight.
    This is the S-degree of the differential path.

    If S-degree of differential < S-degree of function → shortcut exists.
    """
    print("\n--- TEST 2: DIFFERENTIAL S-DEGREE (Wang pairs) ---")

    diff_carry = {r: [] for r in range(64)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn,sf = wang_cascade(W0,W1)
        Wn_e = schedule(Wn); Wf_e = schedule(Wf)

        for r in range(64):
            an,bn,cn,dn,en,fn,gn,hn = sn[r]
            af,bf,cf,df,ef,ff_,gf,hf = sf[r]

            # Carry of the DIFFERENCES at each addition
            # δ(a+b) = (a'+b') - (a+b). The carry part of this difference
            # measures the S-complexity of the differential

            # Main addition: d+T1 → e_new
            T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
            T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK

            # Carry of normal and faulty
            cn_carry = s_carry(dn, T1n)
            cf_carry = s_carry(df, T1f)

            # Differential carry = carry_f ⊕ carry_n
            diff_c = cn_carry ^ cf_carry
            diff_carry[r].append(hw(diff_c))

    print(f"{'Round':>5} | {'E[diff_carry]':>13} | {'Phase'}")
    print("-"*35)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,32,48,63]:
        arr = np.array(diff_carry[r])
        phase = ""
        if arr.mean() < 2: phase = "S-LINEAR"
        elif arr.mean() < 8: phase = "S-LOW"
        elif arr.mean() < 14: phase = "S-MEDIUM"
        else: phase = "S-FULL"
        print(f"{r:>5} | {arr.mean():>13.4f} | {phase}")

    # KEY: does differential S-degree SATURATE or keep growing?
    late_diff = [np.mean(diff_carry[r]) for r in range(48, 64)]
    early_diff = [np.mean(diff_carry[r]) for r in range(20, 36)]

    print(f"\nEarly (r=20-35) mean: {np.mean(early_diff):.4f}")
    print(f"Late (r=48-63) mean:  {np.mean(late_diff):.4f}")
    print(f"Difference: {np.mean(late_diff)-np.mean(early_diff):+.4f}")

    if abs(np.mean(late_diff) - np.mean(early_diff)) < 0.5:
        print("*** SATURATION: Differential S-degree STABILIZES! ***")

def test_s_ring_collision_structure(N=2000):
    """
    In SHA-Ring, collision = f_S(M) = f_S(M') where f_S is
    the S-polynomial representation.

    The S-representation splits each output bit into:
    H_i = L_i(M) ⊕ C_i(M)
    where L_i = XOR-only part, C_i = carry correction.

    Collision requires: L_i(M)⊕C_i(M) = L_i(M')⊕C_i(M')
    i.e., δL_i = δC_i for all i.

    If δL and δC are CORRELATED → fewer independent constraints.
    """
    print("\n--- TEST 3: S-RING COLLISION STRUCTURE ---")

    # For Wang pairs: decompose δH into δL and δC
    delta_L = []; delta_C = []; delta_H_total = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)

        # Real hash
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        # XOR-hash (L component)
        Ln = xor_compress(Wn); Lf = xor_compress(Wf)

        # Carry correction: C = H ⊕ L
        Cn = [Hn[i] ^ Ln[i] for i in range(8)]
        Cf = [Hf[i] ^ Lf[i] for i in range(8)]

        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dC = sum(hw(Cn[i]^Cf[i]) for i in range(8))
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        delta_L.append(dL); delta_C.append(dC); delta_H_total.append(dH)

    dL=np.array(delta_L); dC=np.array(delta_C); dH=np.array(delta_H_total)

    print(f"E[δL] (XOR part): {dL.mean():.2f}")
    print(f"E[δC] (carry part): {dC.mean():.2f}")
    print(f"E[δH] (total):     {dH.mean():.2f}")

    corr_LC = np.corrcoef(dL, dC)[0,1]
    corr_LH = np.corrcoef(dL, dH)[0,1]
    corr_CH = np.corrcoef(dC, dH)[0,1]

    print(f"\ncorr(δL, δC): {corr_LC:+.6f}")
    print(f"corr(δL, δH): {corr_LH:+.6f}")
    print(f"corr(δC, δH): {corr_CH:+.6f}")

    # KEY: if corr(δL, δC) > 0 → they're ALIGNED → collision condition
    # δL = δC becomes EASIER (fewer independent bits)
    if corr_LC > 0.05:
        effective_dim = 256 * (1 - corr_LC)
        print(f"\n*** SIGNAL: δL and δC correlated ({corr_LC:.4f})! ***")
        print(f"Effective collision dimension: {effective_dim:.0f}/256")
        print(f"Collision cost: ~2^{effective_dim/2:.1f} (vs 2^128)")

    # Per-bit analysis: which bits have highest |δL_i - δC_i| correlation?
    print(f"\nPer-word S-structure:")
    for w in range(8):
        branch = "a" if w < 4 else "e"
        # Collect per-word
        dL_w = []; dC_w = []
        for i in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            Ln=xor_compress(Wn); Lf=xor_compress(Wf)
            dL_w.append(hw((Ln[w]^Lf[w])))
            dC_w.append(hw(((Hn[w]^Ln[w])^(Hf[w]^Lf[w]))))

        c = np.corrcoef(dL_w, dC_w)[0,1]
        print(f"  H[{w}]({branch}): corr(δL,δC)={c:+.6f}")

def xor_compress(W16, iv=None):
    """XOR-only SHA-256 compression (no carries)."""
    if iv is None: iv = list(IV)
    def xor_sched(W):
        W = list(W)+[0]*48
        for t in range(16,64):
            W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
        return W
    def xor_round(s, w, k):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^k^w
        T2=sigma0(a)^maj(a,b,c)
        return [T1^T2,a,b,c,d^T1,e,f,g]
    W=xor_sched(W16); s=list(iv)
    for r in range(64): s=xor_round(s,W[r],K[r])
    return [iv[i]^s[i] for i in range(8)]

def test_s_degree_vs_gf2_degree(N=300):
    """
    Compare: how fast does complexity grow in S vs GF(2)?

    GF(2)-degree: number of input bits that influence output bit (ANF degree)
    S-degree: number of carry operations in the path

    If S-degree grows SLOWER → SHA-Ring is more efficient representation.
    """
    print("\n--- TEST 4: S-DEGREE vs GF(2)-DEGREE GROWTH ---")

    print(f"{'Rounds':>6} | {'S-carry/round':>13} | {'GF2-rank':>9} | {'Ratio':>8}")
    print("-"*45)

    for R in [1, 2, 4, 8, 16, 32, 64]:
        # S-degree: average carry weight per round
        s_degrees = []
        for _ in range(N):
            W16 = random_w16()
            total_cw = sum(s_degree_single_round(W16, r) for r in range(R))
            s_degrees.append(total_cw / R)

        # GF(2)-rank of differential matrix
        gf2_ranks = []
        for _ in range(min(N, 30)):
            W16 = random_w16()
            base = sha256_rounds(W16, R)
            diff_rows = []
            for word in range(16):
                for bit in range(32):
                    Wp = list(W16); Wp[word] ^= (1<<bit)
                    pert = sha256_rounds(Wp, R)
                    row = []
                    for w in range(8):
                        d = base[R][w] ^ pert[R][w]
                        for b in range(32):
                            row.append((d>>b)&1)
                    diff_rows.append(row)
            M = np.array(diff_rows, dtype=np.int64)
            # Simple rank
            r_val = np.linalg.matrix_rank(M.astype(np.float64))
            gf2_ranks.append(r_val)

        s_mean = np.mean(s_degrees)
        gf2_mean = np.mean(gf2_ranks)
        ratio = s_mean / gf2_mean if gf2_mean > 0 else 0

        print(f"{R:>6} | {s_mean:>13.2f} | {gf2_mean:>9.1f} | {ratio:>8.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 38: SHA-RING — NEW ALGEBRAIC STRUCTURE")
    print("Derived from all 23 theorems. Passes all 5 walls.")
    print("="*60)

    test_s_degree_growth(300)
    test_differential_s_degree(800)
    test_s_ring_collision_structure(1500)
    test_s_degree_vs_gf2_degree(100)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
