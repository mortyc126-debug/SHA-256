#!/usr/bin/env python3
"""
EXP 47: Carry Freedom — New Mathematical Framework

Step-by-step derivation from scratch:

1. SHA-256 = linear (XOR, rotate) + carry + quadratic (Ch, Maj)
2. Introduce carry as FREE VARIABLES → main system becomes linear
3. Carry constraints: c_{i+1} = a_i·b_i ⊕ (a_i⊕b_i)·c_i
4. P-positions: carry_out = carry_in → NO new constraint (free!)
5. G/K-positions: carry determined → constraint

Count:
- 448 additions × 32 bits = 14336 carry positions
- 50% P → 7168 free carry bits
- 7168 G/K constraints + 256 output constraints = 7424 total
- 14848 variables − 7424 constraints = 7424 degrees of freedom
- Need 256 for collision → EXCESS: 7168

KEY QUESTION: Can we navigate 7168 free carry-bits to satisfy
256 output equations? If yes → polynomial-time collision.

TEST: For a concrete message, count ACTUAL free carries
and verify the constraint count.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def count_carry_freedom_single_addition(a, b):
    """
    For one addition a+b, count P/G/K positions.
    P = free carry, G/K = determined carry.
    """
    p = 0; g = 0; k = 0
    for i in range(32):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        if ai == 1 and bi == 1:
            g += 1
        elif ai == 0 and bi == 0:
            k += 1
        else:
            p += 1
    return p, g, k

def count_total_carry_freedom(W16):
    """Count total carry freedom across all 448 additions."""
    states = sha256_rounds(W16, 64)
    W = schedule(W16)

    total_p = 0; total_g = 0; total_k = 0

    for r in range(64):
        a, b, c, d, e, f, g_reg, h = states[r]

        sig1_e = sigma1(e)
        ch_val = ch(e, f, g_reg)
        sig0_a = sigma0(a)
        maj_val = maj(a, b, c)

        s1 = (h + sig1_e) & MASK
        s2 = (s1 + ch_val) & MASK
        s3 = (s2 + K[r]) & MASK
        T1 = (s3 + W[r]) & MASK
        T2 = (sig0_a + maj_val) & MASK

        additions = [
            (h, sig1_e), (s1, ch_val), (s2, K[r]), (s3, W[r]),
            (sig0_a, maj_val), (T1, T2), (d, T1),
        ]

        for x, y in additions:
            p, g, k_count = count_carry_freedom_single_addition(x, y)
            total_p += p
            total_g += g
            total_k += k_count

    return total_p, total_g, total_k

def test_carry_freedom_count(N=1000):
    """Verify carry freedom count across random messages."""
    print("\n--- STEP 6 VERIFICATION: CARRY FREEDOM COUNT ---")

    all_p = []; all_g = []; all_k = []

    for _ in range(N):
        W16 = random_w16()
        p, g, k = count_total_carry_freedom(W16)
        all_p.append(p); all_g.append(g); all_k.append(k)

    pa = np.array(all_p); ga = np.array(all_g); ka = np.array(all_k)
    total = pa + ga + ka

    print(f"Total carry positions: {total.mean():.0f} (expected: 448×32={448*32})")
    print(f"P (free): {pa.mean():.1f} ± {pa.std():.1f} ({pa.mean()/total.mean()*100:.1f}%)")
    print(f"G (carry=1): {ga.mean():.1f} ± {ga.std():.1f} ({ga.mean()/total.mean()*100:.1f}%)")
    print(f"K (carry=0): {ka.mean():.1f} ± {ka.std():.1f} ({ka.mean()/total.mean()*100:.1f}%)")

    print(f"\nConstraint count:")
    print(f"  G+K constraints: {(ga.mean()+ka.mean()):.0f}")
    print(f"  Output constraints: 256")
    print(f"  Total constraints: {(ga.mean()+ka.mean()+256):.0f}")
    print(f"  Variables: {total.mean()+512:.0f} (carry + input)")
    print(f"  Freedom: {total.mean()+512-(ga.mean()+ka.mean()+256):.0f}")
    print(f"  Excess over collision: {total.mean()+512-(ga.mean()+ka.mean()+256)-256:.0f}")

def test_carry_chain_structure(N=100):
    """
    P-carries are free, but they form CHAINS.
    In a chain of k consecutive P's, carry propagates:
    c_out = c_in (through all k positions).

    So a chain of k P's = 1 free bit (the chain's carry-in),
    NOT k free bits!

    CORRECTED freedom = number of P-CHAINS, not P-positions.
    """
    print("\n--- STEP 6b: CORRECTED FREEDOM (P-CHAINS, not P-positions) ---")

    chain_counts = []
    chain_lengths = []

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        n_chains = 0
        all_lengths = []

        for r in range(64):
            a, b, c, d, e, f, g_reg, h = states[r]
            sig1_e = sigma1(e)
            ch_val = ch(e, f, g_reg)
            sig0_a = sigma0(a)
            maj_val = maj(a, b, c)
            s1 = (h + sig1_e) & MASK
            s2 = (s1 + ch_val) & MASK
            s3 = (s2 + K[r]) & MASK
            T1 = (s3 + W[r]) & MASK
            T2 = (sig0_a + maj_val) & MASK

            additions = [
                (h, sig1_e), (s1, ch_val), (s2, K[r]), (s3, W[r]),
                (sig0_a, maj_val), (T1, T2), (d, T1),
            ]

            for x, y in additions:
                gkp = carry_gkp_classification(x, y)
                # Count chains
                in_chain = False
                chain_len = 0
                for cls in gkp:
                    if cls == 'P':
                        if not in_chain:
                            n_chains += 1
                            in_chain = True
                            chain_len = 1
                        else:
                            chain_len += 1
                    else:
                        if in_chain:
                            all_lengths.append(chain_len)
                        in_chain = False
                        chain_len = 0
                if in_chain:
                    all_lengths.append(chain_len)

        chain_counts.append(n_chains)
        chain_lengths.extend(all_lengths)

    cc = np.array(chain_counts)
    cl = np.array(chain_lengths)

    print(f"P-chains per message: {cc.mean():.1f} ± {cc.std():.1f}")
    print(f"Chain length: mean={cl.mean():.2f}, max={cl.max()}")
    print(f"\nCORRECTED freedom:")
    print(f"  Free carry-bits = P-chains ≈ {cc.mean():.0f}")
    print(f"  (NOT P-positions ≈ 7168)")
    print(f"  Total constraints: G+K + output = {14336*0.5+256:.0f}")
    print(f"  Variables: {14336+512}")
    print(f"  Corrected freedom: {cc.mean()+512-(14336*0.5+256):.0f}")

    # Each P-CHAIN gives 1 bit of freedom (carry-in of the chain)
    # But the chain carry-in is DETERMINED by the previous G or K
    # Actually: first P in chain after K → carry-in = 0
    # First P after G → carry-in = 1
    # First P at bit 0 → carry-in = 0

    # So P-chain freedom = 0! The carry-in is DETERMINED by the
    # preceding G/K position!

    print(f"\n*** CRITICAL CORRECTION ***")
    print(f"P-chain carry-in is determined by preceding G/K!")
    print(f"  After K: carry-in = 0")
    print(f"  After G: carry-in = 1")
    print(f"  At bit 0: carry-in = 0")
    print(f"  TRUE carry freedom = 0")
    print(f"  Carry is FULLY DETERMINED by input bits.")

def test_freedom_for_wang_pairs(N=1000):
    """
    For WANG PAIRS: the differential ΔW creates specific carry changes.
    How much freedom exists in the DIFFERENTIAL carry?

    Differential carry: Δc = carry(M') ⊕ carry(M).
    P-positions in differential: where BOTH M and M' have P.
    """
    print("\n--- STEP 7: DIFFERENTIAL CARRY FREEDOM ---")

    diff_p = []; diff_g = []; diff_k = []; diff_mixed = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn,sf = wang_cascade(W0,W1)
        Wn_e=schedule(Wn); Wf_e=schedule(Wf)

        dp = 0; dg = 0; dk = 0; dmixed = 0

        for r in range(64):
            an,_,_,dn,en,fn,gn,hn = sn[r]
            af,_,_,df,ef,ff_,gf,hf = sf[r]

            T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
            T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK

            gkp_n = carry_gkp_classification(dn, T1n)
            gkp_f = carry_gkp_classification(df, T1f)

            for cn, cf in zip(gkp_n, gkp_f):
                if cn == 'P' and cf == 'P':
                    dp += 1  # Both uncertain → differential carry free
                elif cn == cf:
                    if cn == 'G': dg += 1
                    else: dk += 1
                else:
                    dmixed += 1  # One G/K, other P → constrained

        diff_p.append(dp)
        diff_g.append(dg)
        diff_k.append(dk)
        diff_mixed.append(dmixed)

    dpa=np.array(diff_p); dga=np.array(diff_g)
    dka=np.array(diff_k); dma=np.array(diff_mixed)

    print(f"Differential carry per round 64:")
    print(f"  PP (both free):    {dpa.mean():.1f} ({dpa.mean()/2048*100:.1f}%)")
    print(f"  GG (both carry=1): {dga.mean():.1f} ({dga.mean()/2048*100:.1f}%)")
    print(f"  KK (both carry=0): {dka.mean():.1f} ({dka.mean()/2048*100:.1f}%)")
    print(f"  Mixed (GK/KG/GP/KP): {dma.mean():.1f} ({dma.mean()/2048*100:.1f}%)")

    print(f"\nDifferential freedom:")
    print(f"  PP positions = {dpa.mean():.0f} potential free diff-carry bits")
    print(f"  But PP chain freedom < PP positions (same chain argument)")

    # For collision: need δH = 0 on 256 bits
    # PP positions give freedom in differential carry
    # If PP freedom > 256 → potentially solvable
    print(f"\n  PP freedom ({dpa.mean():.0f}) vs collision requirement (256):")
    if dpa.mean() > 256:
        print(f"  *** PP > 256: POTENTIAL freedom exceeds requirement! ***")
    else:
        print(f"  PP < 256: insufficient freedom")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 47: CARRY FREEDOM — NEW FRAMEWORK")
    print("Step-by-step derivation from scratch")
    print("="*60)

    test_carry_freedom_count(500)
    test_carry_chain_structure(200)
    test_freedom_for_wang_pairs(1000)

    print("\n"+"="*60)
    print("NEXT STEPS")
    print("="*60)
    print("If PP > 256: build equation system over PP positions")
    print("If PP < 256: need to find more freedom (step back)")

if __name__ == "__main__":
    main()
