#!/usr/bin/env python3
"""
EXP 20: Joint (κ_e, κ_a) Coupling — Two-Branch Structure

Collision requires δe=0 AND δa=0. We only measured κ for e-branch.
Joint (κ_e, κ_a) is a 2D object. Its structure may differ from marginals.

Also: exp17 nonlinear hint — corr(κ_17·κ_18, δH) = -0.065 (***).
Explore nonlinear coupling-output connections.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    carries = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        carries.append(c)
    return carries

def joint_kappa(states_n, states_f, Wn_exp, Wf_exp, r):
    """Compute κ_e (d+T1) and κ_a (T1+T2) at round r."""
    an,bn,cn,dn,en,fn,gn,hn = states_n[r]
    af,bf,cf,df,ef,ff_,gf,hf = states_f[r]

    T1n = (hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_exp[r])&MASK
    T1f = (hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_exp[r])&MASK
    T2n = (sigma0(an)+maj(an,bn,cn))&MASK
    T2f = (sigma0(af)+maj(af,bf,cf))&MASK

    # κ_e: d+T1
    ke = sum(a^b for a,b in zip(carry_vec(dn,T1n), carry_vec(df,T1f)))
    # κ_a: T1+T2
    ka = sum(a^b for a,b in zip(carry_vec(T1n,T2n), carry_vec(T1f,T2f)))
    return ke, ka

def main():
    random.seed(42)
    N = 2000
    print("="*60)
    print("EXP 20: JOINT (κ_e, κ_a) COUPLING")
    print("="*60)

    # --- Joint profile ---
    print("\n--- JOINT COUPLING PROFILE ---")
    round_data = {r: {'ke':[], 'ka':[], 'dH':[]} for r in range(64)}

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)
        We = schedule(Wn); Wfe = schedule(Wf)
        H_n = sha256_compress(Wn); H_f = sha256_compress(Wf)
        dH = sum(hw(H_n[i]^H_f[i]) for i in range(8))

        for r in range(64):
            ke, ka = joint_kappa(sn, sf, We, Wfe, r)
            round_data[r]['ke'].append(ke)
            round_data[r]['ka'].append(ka)
            round_data[r]['dH'].append(dH)

    print(f"{'Round':>5} | {'E[κ_e]':>8} | {'E[κ_a]':>8} | {'corr(e,a)':>10} | "
          f"{'corr(κ_e,δH)':>13} | {'corr(κ_a,δH)':>13}")
    print("-"*75)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,32,48,63]:
        ke = np.array(round_data[r]['ke'])
        ka = np.array(round_data[r]['ka'])
        dH = np.array(round_data[r]['dH'])

        corr_ea = np.corrcoef(ke, ka)[0,1] if ke.std()>0 and ka.std()>0 else 0
        corr_eH = np.corrcoef(ke, dH)[0,1] if ke.std()>0 else 0
        corr_aH = np.corrcoef(ka, dH)[0,1] if ka.std()>0 else 0

        sig = ""
        if abs(corr_ea) > 0.1: sig += " ea***"
        if abs(corr_eH) > 0.067 or abs(corr_aH) > 0.067: sig += " →δH***"

        print(f"{r:>5} | {ke.mean():>8.2f} | {ka.mean():>8.2f} | {corr_ea:>+10.4f} | "
              f"{corr_eH:>+13.6f} | {corr_aH:>+13.6f} | {sig}")

    # --- Joint product: κ_e · κ_a → δH ---
    print("\n--- NONLINEAR: κ_e · κ_a → δH ---")
    for r in [16,17,18,20,32,48,63]:
        ke = np.array(round_data[r]['ke'])
        ka = np.array(round_data[r]['ka'])
        dH = np.array(round_data[r]['dH'])
        prod = ke * ka
        c = np.corrcoef(prod, dH)[0,1] if prod.std()>0 else 0
        sig = " ***" if abs(c) > 0.067 else ""
        print(f"  r={r:>2}: corr(κ_e·κ_a, δH) = {c:+.6f}{sig}")

    # --- Joint sum κ_e + κ_a → δH ---
    print("\n--- SUM: κ_e + κ_a → δH ---")
    for r in [16,17,18,20,32,48,63]:
        ke = np.array(round_data[r]['ke'])
        ka = np.array(round_data[r]['ka'])
        dH = np.array(round_data[r]['dH'])
        s = ke + ka
        c = np.corrcoef(s, dH)[0,1]
        sig = " ***" if abs(c) > 0.067 else ""
        print(f"  r={r:>2}: corr(κ_e+κ_a, δH) = {c:+.6f}{sig}")

    # --- Conditional: joint low κ → δH ---
    print("\n--- JOINT LOW κ → δH ---")
    for r in [17, 32, 63]:
        ke = np.array(round_data[r]['ke'])
        ka = np.array(round_data[r]['ka'])
        dH = np.array(round_data[r]['dH'])
        joint_low = dH[(ke < np.median(ke)) & (ka < np.median(ka))]
        joint_high = dH[(ke >= np.median(ke)) & (ka >= np.median(ka))]
        if len(joint_low)>0 and len(joint_high)>0:
            print(f"  r={r:>2}: low(κ_e,κ_a) E[δH]={joint_low.mean():.4f} vs "
                  f"high E[δH]={joint_high.mean():.4f} Δ={joint_low.mean()-joint_high.mean():+.4f}")

if __name__ == "__main__":
    main()
