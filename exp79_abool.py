#!/usr/bin/env python3
"""
EXP 79: A_BOOL — Ch and Maj as Separate Algebra

78 experiments studied carry (A_MOD) and XOR (A_XOR).
ZERO experiments isolated Ch and Maj (A_BOOL).

Ch(e,f,g) = e·(f⊕g) ⊕ g — degree 2, bilinear
Maj(a,b,c) = (a·b)⊕(a·c)⊕(b·c) — degree 2, symmetric

These are the ONLY nonlinear boolean operations in SHA-256
(besides carry in mod-add, which we studied extensively).

Questions:
1. Does δCh have structure beyond what carry analysis shows?
2. Does the Ch CHAIN (64 rounds) have algebraic properties?
3. Does Ch×Maj interaction in T1+T2 create exploitable structure?
4. Is A_BOOL independent of A_MOD and A_XOR, or correlated?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def ch_differential(e, f, g, de, df, dg):
    """Exact Ch differential over GF(2)."""
    # Ch(e,f,g) = (e & f) ^ (~e & g)
    # δCh = Ch(e^de, f^df, g^dg) ^ Ch(e,f,g)
    ch_orig = ch(e, f, g)
    ch_pert = ch(e ^ de, f ^ df, g ^ dg)
    return ch_orig ^ ch_pert

def maj_differential(a, b, c, da, db, dc):
    """Exact Maj differential over GF(2)."""
    maj_orig = maj(a, b, c)
    maj_pert = maj(a ^ da, b ^ db, c ^ dc)
    return maj_orig ^ maj_pert

def test_ch_differential_structure(N=3000):
    """Analyze δCh for Wang pairs across rounds."""
    print("\n--- δCh STRUCTURE ---")

    ch_diffs = {r: [] for r in range(64)}
    ch_hws = {r: [] for r in range(64)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        for r in range(64):
            en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]
            ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]
            de=en^ef; df=fn^ff_; dg=gn^gf

            dch = ch_differential(en, fn, gn, de, df, dg)
            ch_hws[r].append(hw(dch))

    print(f"{'Round':>5} | {'E[HW(δCh)]':>11} | {'Std':>6} | {'P(δCh=0)':>9} | Phase")
    print("-"*50)
    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,32,48,63]:
        arr = np.array(ch_hws[r])
        p_zero = np.mean(arr == 0)
        phase = ""
        if arr.mean() < 1: phase = "ZERO"
        elif arr.mean() < 8: phase = "LOW"
        elif arr.mean() < 14: phase = "PARTIAL"
        else: phase = "FULL"
        print(f"{r:>5} | {arr.mean():>11.4f} | {arr.std():>6.2f} | {p_zero:>9.4f} | {phase}")

def test_maj_differential_structure(N=3000):
    """Analyze δMaj for Wang pairs."""
    print(f"\n--- δMaj STRUCTURE ---")

    maj_hws = {r: [] for r in range(64)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        for r in range(64):
            an=sn[r][0]; bn=sn[r][1]; cn=sn[r][2]
            af=sf[r][0]; bf=sf[r][1]; cf=sf[r][2]
            da=an^af; db=bn^bf; dc=cn^cf

            dmaj = maj_differential(an, bn, cn, da, db, dc)
            maj_hws[r].append(hw(dmaj))

    print(f"{'Round':>5} | {'E[HW(δMaj)]':>12} | {'P(δMaj=0)':>10}")
    print("-"*40)
    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,32,48,63]:
        arr = np.array(maj_hws[r])
        p_zero = np.mean(arr == 0)
        print(f"{r:>5} | {arr.mean():>12.4f} | {p_zero:>10.4f}")

def test_ch_vs_dH(N=3000):
    """Does δCh at late rounds predict δH?"""
    print(f"\n--- δCh → δH CORRELATION ---")

    for r_test in [60, 61, 62, 63]:
        ch_list=[]; dH_list=[]
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
            en=sn[r_test][4]; fn=sn[r_test][5]; gn=sn[r_test][6]
            ef=sf[r_test][4]; ff_=sf[r_test][5]; gf=sf[r_test][6]
            dch = hw(ch_differential(en,fn,gn,en^ef,fn^ff_,gn^gf))
            ch_list.append(dch)

            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            dH_list.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

        c = np.corrcoef(ch_list, dH_list)[0,1]
        threshold = 3/np.sqrt(N)
        sig = "***" if abs(c) > threshold else ""
        print(f"  r={r_test}: corr(HW(δCh), δH) = {c:+.6f} {sig}")

def test_ch_maj_interaction(N=3000):
    """Does Ch×Maj interaction in T1+T2 have structure?"""
    print(f"\n--- Ch × Maj INTERACTION ---")

    for r_test in [16, 32, 63]:
        data = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
            We=schedule(Wn); Wfe=schedule(Wf)

            # T1 contains Ch
            en=sn[r_test][4]; fn=sn[r_test][5]; gn=sn[r_test][6]; hn=sn[r_test][7]
            ef=sf[r_test][4]; ff_=sf[r_test][5]; gf=sf[r_test][6]; hf=sf[r_test][7]
            T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r_test]+We[r_test])&MASK
            T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r_test]+Wfe[r_test])&MASK
            dT1 = hw(T1n ^ T1f)

            # T2 contains Maj
            an=sn[r_test][0]; bn=sn[r_test][1]; cn=sn[r_test][2]
            af=sf[r_test][0]; bf=sf[r_test][1]; cf=sf[r_test][2]
            T2n=(sigma0(an)+maj(an,bn,cn))&MASK
            T2f=(sigma0(af)+maj(af,bf,cf))&MASK
            dT2 = hw(T2n ^ T2f)

            # Interaction: carry of T1+T2
            carry_n = ((T1n+T2n)&MASK) ^ (T1n ^ T2n)
            carry_f = ((T1f+T2f)&MASK) ^ (T1f ^ T2f)
            d_interaction = hw(carry_n ^ carry_f)

            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

            data.append((dT1, dT2, d_interaction, dH))

        dT1a=np.array([d[0] for d in data])
        dT2a=np.array([d[1] for d in data])
        dia=np.array([d[2] for d in data])
        dHa=np.array([d[3] for d in data])

        threshold = 3/np.sqrt(N)
        c_T1 = np.corrcoef(dT1a, dHa)[0,1]
        c_T2 = np.corrcoef(dT2a, dHa)[0,1]
        c_int = np.corrcoef(dia, dHa)[0,1]
        c_T1T2 = np.corrcoef(dT1a, dT2a)[0,1]

        print(f"  r={r_test}:")
        print(f"    corr(δT1, δH) = {c_T1:+.6f} {'***' if abs(c_T1)>threshold else ''}")
        print(f"    corr(δT2, δH) = {c_T2:+.6f} {'***' if abs(c_T2)>threshold else ''}")
        print(f"    corr(δInteraction, δH) = {c_int:+.6f} {'***' if abs(c_int)>threshold else ''}")
        print(f"    corr(δT1, δT2) = {c_T1T2:+.6f} {'***' if abs(c_T1T2)>threshold else ''}")
        print(f"    E[δT1]={dT1a.mean():.1f}, E[δT2]={dT2a.mean():.1f}, "
              f"E[δInteraction]={dia.mean():.1f}")

def test_ch_chain_algebraic(N=1000):
    """
    Ch chain: Ch at round r uses e_r, f_r=e_{r-1}, g_r=e_{r-2}.
    So Ch_r = Ch(e_r, e_{r-1}, e_{r-2}) — depends on 3 consecutive e-values.

    After Wang cascade (De=0 for r=3-16):
    e_3=e_4=...=e_16 (same for both messages).
    So Ch_r for r=5..16: Ch(e_r, e_{r-1}, e_{r-2}) = SAME for both!
    → δCh = 0 for those rounds.

    At r=17: e_17 diverges, but f_17=e_16 (same), g_17=e_15 (same).
    → δCh_17 = Ch(e_17⊕δe_17, f_17, g_17) ⊕ Ch(e_17, f_17, g_17)
             = δe_17 · (f_17 ⊕ g_17) = δe_17 · (e_16 ⊕ e_15)

    This is a SPECIFIC algebraic expression for δCh at barrier!
    """
    print(f"\n--- Ch CHAIN AT BARRIER ---")

    for _ in range(min(N, 5)):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        # At r=17:
        e17_n = sn[17][4]; e17_f = sf[17][4]
        de17 = e17_n ^ e17_f
        f17 = sn[17][5]  # = e_16 (same for both)
        g17 = sn[17][6]  # = e_15 (same for both)

        # Predicted δCh_17 = de17 & (f17 ^ g17)
        predicted = de17 & (f17 ^ g17)

        # Actual δCh_17
        actual = ch(e17_n, f17, g17) ^ ch(e17_f, f17, g17)

        match = predicted == actual
        print(f"  δCh_17 prediction: {'EXACT' if match else 'WRONG'} "
              f"(predicted=0x{predicted:08x}, actual=0x{actual:08x})")

    # For r=18: f_18=e_17 (DIFFERENT!), g_18=e_16 (same)
    print(f"\n  At r=18: f_18=e_17 (different), g_18=e_16 (same)")
    print(f"  δCh_18 = Ch(e18⊕δe18, e17⊕δe17, e16) ⊕ Ch(e18, e17, e16)")
    print(f"  This involves PRODUCTS of δe17 and δe18 — degree 2!")

    # Verify
    for _ in range(3):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        e18_n=sn[18][4]; e18_f=sf[18][4]
        e17_n=sn[18][5]; e17_f=sf[18][5]  # f_18 = e_17
        e16=sn[18][6]  # g_18 = e_16 (same)

        actual = ch(e18_n,e17_n,e16) ^ ch(e18_f,e17_f,e16)

        # δCh_18 = de18·(e17_n⊕e16) ⊕ e18_n·(de17) ⊕ de18·de17 ⊕ 0
        de18 = e18_n ^ e18_f
        de17 = e17_n ^ e17_f
        predicted = (de18 & (e17_n ^ e16)) ^ (e18_n & de17) ^ (de18 & de17)

        match = predicted == actual
        print(f"  δCh_18: {'EXACT' if match else 'WRONG'}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 79: A_BOOL — Ch AND Maj ALGEBRA")
    print("="*60)
    test_ch_differential_structure(2000)
    test_maj_differential_structure(2000)
    test_ch_vs_dH(2000)
    test_ch_maj_interaction(2000)
    test_ch_chain_algebraic(500)

if __name__ == "__main__":
    main()
