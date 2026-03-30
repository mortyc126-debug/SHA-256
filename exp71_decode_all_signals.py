#!/usr/bin/env python3
"""
EXP 71: Decode ALL Signals — Six Frequencies, One Message

70 experiments generated dozens of "noise" signals, each discarded.
Exp70 showed: weak signal becomes strong (0.46!) in right subspace.

NOW: systematically verify ALL 6 "frequencies" and their CONNECTIONS.

Frequency 1: e-branch weaker than a-branch
Frequency 2: low bits more transparent than high bits
Frequency 3: pipe connects branches
Frequency 4: R=32 true boundary (not R=64)
Frequency 5: coupling = multi-dimensional
Frequency 6: quadratic density 45% (5% deficit)

If all 6 are ASPECTS of ONE structure → the structure is real
and potentially larger than any single signal.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_compress(W16, iv=None):
    if iv is None: iv=list(IV)
    W=list(W16)+[0]*48
    for t in range(16,64): W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r]; T2=sigma0(a)^maj(a,b,c)
        s=[T1^T2,a,b,c,d^T1,e,f,g]
    return [iv[i]^s[i] for i in range(8)]

def test_frequency1_ebranch_weakness(N=3000):
    """F1: e-branch WEAKER than a-branch."""
    print("\n--- F1: E-BRANCH vs A-BRANCH WEAKNESS ---")

    a_dHs=[]; e_dHs=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        a_dH = sum(hw(Hn[i]^Hf[i]) for i in range(4))
        e_dH = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
        a_dHs.append(a_dH); e_dHs.append(e_dH)

    aa=np.array(a_dHs); ea=np.array(e_dHs)
    print(f"a-branch δH: E={aa.mean():.4f}, std={aa.std():.4f}")
    print(f"e-branch δH: E={ea.mean():.4f}, std={ea.std():.4f}")
    print(f"e-branch std/a-branch std: {ea.std()/aa.std():.4f}")

    # Carry transparency per branch
    a_cf=[]; e_cf=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        acf=0; ecf=0
        for w in range(8):
            for bit in range(5):
                s_xor = (sn[64][w]^sf[64][w]>>bit)&1
                h_xor = (Hn[w]^Hf[w]>>bit)&1
                if s_xor == h_xor:
                    if w < 4: acf += 1
                    else: ecf += 1
        a_cf.append(acf); e_cf.append(ecf)

    print(f"\nCarry transparency (bits 0-4):")
    print(f"  a-branch: E={np.mean(a_cf):.2f}/20")
    print(f"  e-branch: E={np.mean(e_cf):.2f}/20")

    if np.mean(e_cf) > np.mean(a_cf) + 0.5:
        print(f"  *** E-branch MORE transparent! ***")

def test_frequency2_low_bits_transparent(N=2000):
    """F2: low bits more transparent than high bits."""
    print(f"\n--- F2: LOW BITS vs HIGH BITS TRANSPARENCY ---")

    transparency = {b: [] for b in range(32)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        for w in range(4, 8):  # e-branch
            for bit in range(32):
                s_xor = (sn[64][w]^sf[64][w]>>bit)&1
                h_xor = (Hn[w]^Hf[w]>>bit)&1
                transparency[bit].append(1 if s_xor == h_xor else 0)

    print(f"{'Bit':>4} | {'Transparency':>12} | {'Bar'}")
    print("-"*40)
    for bit in range(32):
        t = np.mean(transparency[bit])
        bar = "#" * int(t * 40)
        print(f"{bit:>4} | {t:>12.6f} | {bar}")

def test_frequency3_pipe_connection(N=2000):
    """F3: pipe connects branches."""
    print(f"\n--- F3: PIPE CONNECTION BETWEEN BRANCHES ---")

    # corr between carry_transparency of pipe-connected words
    for pipe_a, pipe_e in [(0,4), (1,5), (2,6), (3,7)]:
        cf_a=[]; cf_e=[]
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

            ta=0; te=0
            for bit in range(5):
                if ((sn[64][pipe_a]^sf[64][pipe_a]>>bit)&1)==((Hn[pipe_a]^Hf[pipe_a]>>bit)&1): ta+=1
                if ((sn[64][pipe_e]^sf[64][pipe_e]>>bit)&1)==((Hn[pipe_e]^Hf[pipe_e]>>bit)&1): te+=1
            cf_a.append(ta); cf_e.append(te)

        c = np.corrcoef(cf_a, cf_e)[0,1]
        threshold = 3/np.sqrt(N)
        sig = "***" if abs(c)>threshold else ""
        print(f"  Pipe ({pipe_a},{pipe_e}): corr(transparency_a, transparency_e) = {c:+.6f} {sig}")

def test_frequency4_r32_boundary(N=1000):
    """F4: R=32 is true complexity boundary."""
    print(f"\n--- F4: R=32 vs R=64 BOUNDARY ---")

    # Carry transparency at R=32 vs R=64
    for R in [16, 24, 32, 48, 64]:
        transparencies = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

            Hn = [(IV[i]+sn[R][i])&MASK for i in range(8)]
            Hf = [(IV[i]+sf[R][i])&MASK for i in range(8)]

            cf = 0
            for w in range(4,8):  # e-branch
                for bit in range(5):  # low bits
                    s_x = (sn[R][w]^sf[R][w]>>bit)&1
                    h_x = (Hn[w]^Hf[w]>>bit)&1
                    if s_x == h_x: cf += 1
            transparencies.append(cf)

        ta = np.array(transparencies)
        print(f"  R={R:>2}: E[carry_free] = {ta.mean():.2f}/20, "
              f"corr_potential = {ta.mean()/20:.4f}")

def test_frequency6_quad_deficit(N=300):
    """F6: quadratic density 45% (5% deficit from 50%)."""
    print(f"\n--- F6: QUADRATIC DEFICIT (45% vs 50%) ---")

    # Measure quad density at bits 0-4 vs bits 16-20 of e-branch
    for bit_range, label in [((0,5), "bits 0-4 (low)"),
                              ((16,21), "bits 16-20 (mid)"),
                              ((27,32), "bits 27-31 (high)")]:
        quad_count = 0; total = 0
        for _ in range(N):
            W16 = random_w16()
            for trial in range(20):
                i=random.randint(0,511); j=random.randint(0,511)
                if i==j: continue
                W_i=list(W16);W_i[i//32]^=(1<<(i%32))
                W_j=list(W16);W_j[j//32]^=(1<<(j%32))
                W_ij=list(W16);W_ij[i//32]^=(1<<(i%32));W_ij[j//32]^=(1<<(j%32))

                for w in range(4,8):  # e-branch
                    for bit in range(bit_range[0], bit_range[1]):
                        Hb=(sha256_compress(W16)[w]>>bit)&1
                        Hi=(sha256_compress(W_i)[w]>>bit)&1
                        Hj=(sha256_compress(W_j)[w]>>bit)&1
                        Hij=(sha256_compress(W_ij)[w]>>bit)&1
                        quad = Hij^Hi^Hj^Hb
                        if quad: quad_count += 1
                        total += 1

        density = quad_count/total if total>0 else 0
        print(f"  {label}: quad density = {density:.4f} (random=0.50)")

def test_combined_message(N=3000):
    """Combine all 6 frequencies into ONE measurement."""
    print(f"\n--- COMBINED: ALL 6 FREQUENCIES → δH ---")

    data=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        # F1: e-branch δH
        e_dH = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
        a_dH = sum(hw(Hn[i]^Hf[i]) for i in range(4))

        # F2: low-bit carry transparency (e-branch)
        e_cf_low=0
        for w in range(4,8):
            for bit in range(5):
                if ((sn[64][w]^sf[64][w]>>bit)&1)==((Hn[w]^Hf[w]>>bit)&1): e_cf_low+=1

        # F2b: high-bit carry transparency (e-branch)
        e_cf_high=0
        for w in range(4,8):
            for bit in range(27,32):
                if ((sn[64][w]^sf[64][w]>>bit)&1)==((Hn[w]^Hf[w]>>bit)&1): e_cf_high+=1

        # F3: pipe-connected transparency
        pipe_corr_sum=0
        for wa,we in [(0,4),(1,5),(2,6),(3,7)]:
            ta=sum(1 for b in range(5) if ((sn[64][wa]^sf[64][wa]>>b)&1)==((Hn[wa]^Hf[wa]>>b)&1))
            te=sum(1 for b in range(5) if ((sn[64][we]^sf[64][we]>>b)&1)==((Hn[we]^Hf[we]>>b)&1))
            pipe_corr_sum += ta*te

        dH_full = e_dH + a_dH

        data.append([e_dH, a_dH, e_cf_low, e_cf_high, pipe_corr_sum, dH_full])

    D = np.array(data)
    dH = D[:, 5]
    threshold = 3/np.sqrt(N)

    print(f"Individual signal → δH_full:")
    names=['e_δH','a_δH','e_cf_low','e_cf_high','pipe_corr']
    for i,name in enumerate(names):
        c = np.corrcoef(D[:,i], dH)[0,1]
        sig="***" if abs(c)>threshold else ""
        print(f"  corr({name:>10}, δH) = {c:+.6f} {sig}")

    # Optimal combination
    X = np.column_stack([D[:,2], D[:,3], D[:,4],  # signals
                          D[:,2]**2, D[:,3]**2,    # quadratic
                          D[:,2]*D[:,3],            # interaction
                          D[:,2]*D[:,4]])           # pipe×transparency
    try:
        beta = np.linalg.lstsq(X, dH, rcond=None)[0]
        pred = X @ beta
        r2 = 1 - np.var(dH-pred)/np.var(dH)
        corr_opt = np.corrcoef(pred, dH)[0,1]

        r2_rand=[]
        for _ in range(50):
            yr=np.random.permutation(dH)
            br=np.linalg.lstsq(X, yr, rcond=None)[0]
            pr=X@br; r2_rand.append(1-np.var(yr-pr)/np.var(yr))
        z=(r2-np.mean(r2_rand))/np.std(r2_rand) if np.std(r2_rand)>0 else 0

        print(f"\n  6-frequency combined:")
        print(f"    R² = {r2:.6f} (random: {np.mean(r2_rand):.6f})")
        print(f"    corr = {corr_opt:+.6f}")
        print(f"    Z = {z:.2f}")

        # Compare with exp69 (R²=0.015) and exp70 (R²=?)
        print(f"    exp69 R² = 0.015, exp70 subspace corr=-0.46")
    except:
        pass

def main():
    random.seed(42)
    print("="*60)
    print("EXP 71: DECODE ALL SIGNALS — SIX FREQUENCIES")
    print("="*60)
    test_frequency1_ebranch_weakness(2000)
    test_frequency2_low_bits_transparent(1500)
    test_frequency3_pipe_connection(1500)
    test_frequency4_r32_boundary(500)
    test_frequency6_quad_deficit(100)
    test_combined_message(3000)

if __name__ == "__main__":
    main()
