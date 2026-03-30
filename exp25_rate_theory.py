#!/usr/bin/env python3
"""
EXP 25: Rate Theory — Why rate=6.4 ≈ λ=C/4.5?

Coupling phase transition (exp22): E[δH] grows by ~6.4 bits per unit k_max.
From methodology: absorption rate λ = C/4.5 ≈ 7.1 bits/round.

Are these the SAME constant? If yes, coupling rate = absorption rate,
meaning coupling security is governed by the SAME mechanism as diffusion.

OUR METHOD: decompose the 6.4 rate into contributions from
our known components (Carry Theory, TLC, Pipe Conservation).
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

def sha256_coupling_limited(Wn, Wf, k_max):
    """From exp22: coupling-limited SHA-256."""
    iv = list(IV)
    Wn_e = schedule(Wn); Wf_e = schedule(Wf)
    sn = list(iv); sf = list(iv)
    for r in range(64):
        an,bn,cn,dn,en,fn,gn,hn = sn
        af,bf,cf,df,ef,ff_,gf,hf = sf
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK
        T2n=(sigma0(an)+maj(an,bn,cn))&MASK
        T2f=(sigma0(af)+maj(af,bf,cf))&MASK
        e_new_n=(dn+T1n)&MASK; e_new_f=(df+T1f)&MASK
        diff_e=e_new_n^e_new_f
        if hw(diff_e)>k_max:
            mask=0;count=0
            for i in range(32):
                if (diff_e>>i)&1:
                    if count<k_max: mask|=(1<<i); count+=1
            e_new_f=e_new_n^(diff_e&mask)
        a_new_n=(T1n+T2n)&MASK; a_new_f=(T1f+T2f)&MASK
        diff_a=a_new_n^a_new_f
        if hw(diff_a)>k_max:
            mask=0;count=0
            for i in range(32):
                if (diff_a>>i)&1:
                    if count<k_max: mask|=(1<<i); count+=1
            a_new_f=a_new_n^(diff_a&mask)
        sn=[a_new_n,an,bn,cn,e_new_n,en,fn,gn]
        sf=[a_new_f,af,bf,cf,e_new_f,ef,ff_,gf]
    Hn=[(iv[i]+sn[i])&MASK for i in range(8)]
    Hf=[(iv[i]+sf[i])&MASK for i in range(8)]
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def test_fine_grained_transition(N=1000):
    """Measure transition with fine k resolution to extract exact rate."""
    print("\n--- TEST 1: FINE-GRAINED COUPLING TRANSITION ---")

    k_values = list(range(0, 33))
    results = {}

    for k in k_values:
        dhs = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            dh = sha256_coupling_limited(Wn, Wf, k)
            dhs.append(dh)
        results[k] = np.mean(dhs)

    # Compute rate = d(E[δH])/dk
    print(f"{'k':>4} | {'E[δH]':>8} | {'Δ/Δk':>8} | {'Cumul rate':>10}")
    print("-"*40)
    for k in k_values:
        rate = results[k]-results[k-1] if k>0 else results[k]
        cum_rate = results[k]/(k+1) if k>=0 else 0
        print(f"{k:>4} | {results[k]:>8.2f} | {rate:>8.2f} | {cum_rate:>10.2f}")

    # Linear fit in transition region (k=2..16)
    ks = np.array([k for k in range(2,17)])
    dhs = np.array([results[k] for k in range(2,17)])
    slope, intercept = np.polyfit(ks, dhs, 1)
    print(f"\nLinear fit (k=2..16): slope={slope:.4f} bits/k, intercept={intercept:.2f}")
    print(f"Methodology λ=C/4.5: {256/4.5:.4f}")
    print(f"Ratio slope/λ: {slope/(256/4.5):.4f}")

    return results, slope

def test_per_component_rate(N=500):
    """Decompose rate into L/Q/C components (TLC decomposition applied to coupling)."""
    print("\n--- TEST 2: TLC DECOMPOSITION OF COUPLING RATE ---")

    # Measure: at each k, how much of δH comes from L, Q, C?
    for k in [4, 8, 12, 16, 32]:
        l_contributions = []
        c_contributions = []

        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)

            # Full coupling-limited
            dh_full = sha256_coupling_limited(Wn, Wf, k)

            # XOR-only (L component) — approximate by ignoring carries
            iv = list(IV)
            Wn_e=schedule(Wn); Wf_e=schedule(Wf)
            sn=list(iv);sf=list(iv)
            for r in range(64):
                an,bn,cn,dn,en,fn,gn,hn=sn
                af,bf,cf,df,ef,ff_,gf,hf=sf
                T1n=(hn^sigma1(en)^ch(en,fn,gn)^K[r]^Wn_e[r])
                T1f=(hf^sigma1(ef)^ch(ef,ff_,gf)^K[r]^Wf_e[r])
                T2n=(sigma0(an)^maj(an,bn,cn))
                T2f=(sigma0(af)^maj(af,bf,cf))
                sn=[T1n^T2n,an,bn,cn,dn^T1n,en,fn,gn]
                sf=[T1f^T2f,af,bf,cf,df^T1f,ef,ff_,gf]
            Hn_x=[(iv[i]^sn[i])&MASK for i in range(8)]
            Hf_x=[(iv[i]^sf[i])&MASK for i in range(8)]
            dh_xor = sum(hw(Hn_x[i]^Hf_x[i]) for i in range(8))

            l_contributions.append(dh_xor)
            c_contributions.append(dh_full - dh_xor)

        l_mean = np.mean(l_contributions)
        c_mean = np.mean(c_contributions)

        print(f"  k={k:>2}: total={l_mean+c_mean:.1f}, L(xor)={l_mean:.1f}, "
              f"C(carry)={c_mean:+.1f}, L%={l_mean/(l_mean+c_mean)*100:.1f}%")

def test_round_contribution(N=500):
    """Which rounds contribute most to the coupling rate?"""
    print("\n--- TEST 3: PER-ROUND COUPLING RATE CONTRIBUTION ---")

    # Compare coupling-limited at different ROUND ranges
    for k in [8, 16]:
        print(f"\n  k={k}:")
        # Apply coupling limit only to specific round ranges
        for r_start, r_end, label in [(0,16,"early"), (16,32,"mid1"),
                                       (32,48,"mid2"), (48,64,"late")]:
            dhs = []
            for _ in range(N):
                W0=random.randint(0,MASK); W1=random.randint(0,MASK)
                Wn,Wf,_,_,_ = wang_cascade(W0,W1)

                iv=list(IV)
                Wn_e=schedule(Wn); Wf_e=schedule(Wf)
                sn=list(iv); sf=list(iv)
                for r in range(64):
                    an,bn,cn,dn,en,fn,gn,hn=sn
                    af,bf,cf,df,ef,ff_,gf,hf=sf
                    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
                    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK
                    T2n=(sigma0(an)+maj(an,bn,cn))&MASK
                    T2f=(sigma0(af)+maj(af,bf,cf))&MASK
                    e_new_n=(dn+T1n)&MASK; e_new_f=(df+T1f)&MASK
                    a_new_n=(T1n+T2n)&MASK; a_new_f=(T1f+T2f)&MASK

                    # Apply limit only in target range
                    if r_start <= r < r_end:
                        diff_e=e_new_n^e_new_f
                        if hw(diff_e)>k:
                            m=0;c=0
                            for i in range(32):
                                if (diff_e>>i)&1:
                                    if c<k: m|=(1<<i); c+=1
                            e_new_f=e_new_n^(diff_e&m)
                        diff_a=a_new_n^a_new_f
                        if hw(diff_a)>k:
                            m=0;c=0
                            for i in range(32):
                                if (diff_a>>i)&1:
                                    if c<k: m|=(1<<i); c+=1
                            a_new_f=a_new_n^(diff_a&m)

                    sn=[a_new_n,an,bn,cn,e_new_n,en,fn,gn]
                    sf=[a_new_f,af,bf,cf,e_new_f,ef,ff_,gf]

                Hn=[(iv[i]+sn[i])&MASK for i in range(8)]
                Hf=[(iv[i]+sf[i])&MASK for i in range(8)]
                dh=sum(hw(Hn[i]^Hf[i]) for i in range(8))
                dhs.append(dh)

            print(f"    limit@{label:>5} (r={r_start}-{r_end}): E[δH]={np.mean(dhs):.2f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 25: RATE THEORY — WHY rate=6.4 ≈ λ=C/4.5?")
    print("="*60)
    results, slope = test_fine_grained_transition(800)
    test_per_component_rate(300)
    test_round_contribution(300)

if __name__ == "__main__":
    main()
