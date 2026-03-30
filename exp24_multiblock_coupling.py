#!/usr/bin/env python3
"""
EXP 24: Multi-Block Coupling Accumulation

SHA-256 processes multi-block messages: H1 = compress(IV, M1), H2 = compress(H1, M2).
Output of block 1 = IV for block 2.

If block 1 creates a state with favorable coupling properties,
block 2 INHERITS this through the chaining variable.

T_COUPLING_GRADUAL says rate=6.4 bits/k. If coupling accumulates
across blocks, each block adds to the effect.

OUR METHOD: measure coupling inheritance across block boundaries.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    c_out = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        c_out.append(c)
    return c_out

def kappa_at_round(sn, sf, We, Wfe, r):
    dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
    df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+We[r])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wfe[r])&MASK
    return sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

def two_block_analysis(M1_n, M1_f, M2_n, M2_f):
    """Analyze coupling across two blocks."""
    # Block 1
    H1_n = sha256_compress(M1_n)
    H1_f = sha256_compress(M1_f)
    dH1 = sum(hw(H1_n[i]^H1_f[i]) for i in range(8))

    # Block 2 with H1 as IV
    sn2 = sha256_rounds(M2_n, 64, H1_n)
    sf2 = sha256_rounds(M2_f, 64, H1_f)
    We2 = schedule(M2_n); Wfe2 = schedule(M2_f)

    # Final hash
    H2_n = [(H1_n[i]+sn2[64][i])&MASK for i in range(8)]
    H2_f = [(H1_f[i]+sf2[64][i])&MASK for i in range(8)]
    dH2 = sum(hw(H2_n[i]^H2_f[i]) for i in range(8))

    # Coupling at start of block 2 (inherited from block 1)
    kappa_b2_start = sum(kappa_at_round(sn2, sf2, We2, Wfe2, r) for r in range(4))
    # Coupling at end of block 2
    kappa_b2_end = sum(kappa_at_round(sn2, sf2, We2, Wfe2, r) for r in range(60,64))

    return dH1, dH2, kappa_b2_start, kappa_b2_end

def test_coupling_inheritance(N=1500):
    """Does low coupling in block 1 create low coupling at start of block 2?"""
    print("\n--- TEST 1: COUPLING INHERITANCE ACROSS BLOCKS ---")

    data = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn1, Wf1, DWs, sn1, sf1 = wang_cascade(W0, W1)

        # Block 1 late coupling
        We1 = schedule(Wn1); Wfe1 = schedule(Wf1)
        late_k1 = sum(kappa_at_round(sn1, sf1, We1, Wfe1, r) for r in range(60,64))

        # Block 2: same differential, different message
        M2_n = random_w16()
        M2_f = list(M2_n)  # Same M2 for both → only IV differs

        dH1, dH2, kb2_start, kb2_end = two_block_analysis(Wn1, Wf1, M2_n, M2_f)
        data.append((late_k1, dH1, dH2, kb2_start, kb2_end))

    lk1 = np.array([d[0] for d in data])
    dh1 = np.array([d[1] for d in data])
    dh2 = np.array([d[2] for d in data])
    kb2s = np.array([d[3] for d in data])
    kb2e = np.array([d[4] for d in data])

    print(f"Block 1: E[δH1]={dh1.mean():.2f}, E[late_κ1]={lk1.mean():.2f}")
    print(f"Block 2: E[δH2]={dh2.mean():.2f}, E[κ_start]={kb2s.mean():.2f}, E[κ_end]={kb2e.mean():.2f}")

    # Inheritance: does block1 late_κ predict block2 start_κ?
    c_inherit = np.corrcoef(lk1, kb2s)[0,1]
    c_dh = np.corrcoef(lk1, dh2)[0,1]
    c_dh1_dh2 = np.corrcoef(dh1, dh2)[0,1]

    threshold = 3/np.sqrt(N)
    print(f"\ncorr(late_κ1, κ_start_b2): {c_inherit:+.6f} {'***' if abs(c_inherit)>threshold else ''}")
    print(f"corr(late_κ1, δH2):        {c_dh:+.6f} {'***' if abs(c_dh)>threshold else ''}")
    print(f"corr(δH1, δH2):            {c_dh1_dh2:+.6f} {'***' if abs(c_dh1_dh2)>threshold else ''}")
    print(f"Threshold: {threshold:.6f}")

    return data

def test_same_diff_block2(N=1500):
    """Block 2 with SAME differential as block 1 (Wang cascade both blocks)."""
    print("\n--- TEST 2: SAME WANG DIFFERENTIAL IN BOTH BLOCKS ---")

    single_dh = []
    double_dh = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn1, Wf1, DWs1, _, _ = wang_cascade(W0, W1)

        H1_n = sha256_compress(Wn1)
        H1_f = sha256_compress(Wf1)
        dh1 = sum(hw(H1_n[i]^H1_f[i]) for i in range(8))
        single_dh.append(dh1)

        # Block 2: new Wang cascade with H1 as IV
        W0b = random.randint(0, MASK)
        W1b = random.randint(0, MASK)
        Wn2 = [W0b, W1b] + [0]*14
        DWs2 = [1] + [0]*15

        # Adaptive cascade for block 2
        Wf2_tmp = [(Wn2[i]+DWs2[i])&MASK for i in range(16)]
        sn2_tmp = sha256_rounds(Wn2, 3, H1_n)
        sf2_tmp = sha256_rounds(Wf2_tmp, 3, H1_f)
        De3 = (sf2_tmp[3][4] - sn2_tmp[3][4]) & MASK
        DWs2[2] = (-De3) & MASK

        for step in range(13):
            wi = step+3; dt = step+4
            Wfc = [(Wn2[i]+DWs2[i])&MASK for i in range(16)]
            tn = sha256_rounds(Wn2, dt, H1_n)
            tf = sha256_rounds(Wfc, dt, H1_f)
            DWs2[wi] = (-(tf[dt][4]-tn[dt][4])&MASK) & MASK

        Wf2 = [(Wn2[i]+DWs2[i])&MASK for i in range(16)]

        sn2 = sha256_rounds(Wn2, 64, H1_n)
        sf2 = sha256_rounds(Wf2, 64, H1_f)
        H2_n = [(H1_n[i]+sn2[64][i])&MASK for i in range(8)]
        H2_f = [(H1_f[i]+sf2[64][i])&MASK for i in range(8)]
        dh2 = sum(hw(H2_n[i]^H2_f[i]) for i in range(8))
        double_dh.append(dh2)

    s = np.array(single_dh); d = np.array(double_dh)
    print(f"Single block: E[δH]={s.mean():.2f}, min={s.min()}")
    print(f"Double block: E[δH]={d.mean():.2f}, min={d.min()}")
    print(f"Difference: {d.mean()-s.mean():+.2f}")

    if d.mean() < s.mean() - 1:
        print("*** SIGNAL: Two-block attack has lower δH! ***")

def test_coupling_accumulation(N=1000):
    """Test: does coupling ACCUMULATE over multiple blocks?"""
    print("\n--- TEST 3: COUPLING ACCUMULATION OVER BLOCKS ---")

    for n_blocks in [1, 2, 3, 4]:
        dhs = []
        for _ in range(N):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn1, Wf1, _, _, _ = wang_cascade(W0, W1)

            iv_n = list(IV); iv_f = list(IV)

            for block in range(n_blocks):
                if block == 0:
                    Mn, Mf = Wn1, Wf1
                else:
                    Mn = random_w16()
                    Mf = list(Mn)  # Same message, different IV

                Hn = sha256_compress(Mn) if block == 0 else \
                     [(iv_n[i]+sha256_rounds(Mn,64,iv_n)[64][i])&MASK for i in range(8)]
                Hf = sha256_compress(Mf) if block == 0 else \
                     [(iv_f[i]+sha256_rounds(Mf,64,iv_f)[64][i])&MASK for i in range(8)]

                iv_n = Hn; iv_f = Hf

            dh = sum(hw(iv_n[i]^iv_f[i]) for i in range(8))
            dhs.append(dh)

        arr = np.array(dhs)
        print(f"  {n_blocks} blocks: E[δH]={arr.mean():.2f}, min={arr.min()}, std={arr.std():.2f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 24: MULTI-BLOCK COUPLING ACCUMULATION")
    print("="*60)
    test_coupling_inheritance(1000)
    test_same_diff_block2(1000)
    test_coupling_accumulation(500)

if __name__ == "__main__":
    main()
