#!/usr/bin/env python3
"""
EXP 22: Coupling Phase Transition

Carry has phase transition at k=1 (exp13).
Coupling has τ=8-12 (exp16B) — different regime.
Does coupling have its OWN phase transition?

Define: SHA-256 with coupling-limited carry.
At each addition, if κ > k_coupling, reset carry to average.
Measure E[δH] as function of k_coupling.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def sha256_coupling_limited(Wn, Wf, k_max):
    """
    Run SHA-256 for both M and M', but limit carry COUPLING.
    When coupling κ exceeds k_max at any addition, force carries equal.
    This keeps individual carries intact but limits their DIFFERENCE.
    """
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

        # Check coupling for d+T1
        e_new_n = (dn+T1n)&MASK
        e_new_f = (df+T1f)&MASK

        # If coupling too high, force faulty carry to match normal
        kappa_e = hw((dn+T1n)&MASK ^ (dn^T1n)) ^ hw((df+T1f)&MASK ^ (df^T1f))
        # Simpler: just measure XOR diff of results
        # If result diff > k_max bits, clip it
        diff_e = e_new_n ^ e_new_f
        if hw(diff_e) > k_max:
            # Keep only k_max LSB of difference
            mask = 0
            count = 0
            for i in range(32):
                if (diff_e >> i) & 1:
                    if count < k_max:
                        mask |= (1 << i)
                        count += 1
            e_new_f = e_new_n ^ (diff_e & mask)

        a_new_n = (T1n+T2n)&MASK
        a_new_f = (T1f+T2f)&MASK
        diff_a = a_new_n ^ a_new_f
        if hw(diff_a) > k_max:
            mask = 0; count = 0
            for i in range(32):
                if (diff_a >> i) & 1:
                    if count < k_max:
                        mask |= (1 << i)
                        count += 1
            a_new_f = a_new_n ^ (diff_a & mask)

        sn = [a_new_n, an, bn, cn, e_new_n, en, fn, gn]
        sf = [a_new_f, af, bf, cf, e_new_f, ef, ff_, gf]

    Hn = [(iv[i]+sn[i])&MASK for i in range(8)]
    Hf = [(iv[i]+sf[i])&MASK for i in range(8)]
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def main():
    random.seed(42)
    N = 1500
    print("="*60)
    print("EXP 22: COUPLING PHASE TRANSITION")
    print("="*60)

    print(f"\n{'k_max':>6} | {'E[δH]':>8} | {'std':>8} | {'min':>5} | Phase")
    print("-"*45)

    for k_max in [0,1,2,3,4,5,6,8,10,12,16,20,24,32]:
        dhs = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)
            dh = sha256_coupling_limited(Wn, Wf, k_max)
            dhs.append(dh)

        arr = np.array(dhs)
        phase = "BROKEN" if arr.mean()<64 else ("TRANSITION" if arr.mean()<120 else "SECURE")
        print(f"{k_max:>6} | {arr.mean():>8.2f} | {arr.std():>8.2f} | {arr.min():>5} | {phase}")

    # Compare with carry phase transition (exp13)
    print(f"\nComparison:")
    print(f"  Carry chain: k=0→k=1 = CLIFF (115→126)")
    print(f"  Coupling:    k=0→k=? = ??? (see above)")

if __name__ == "__main__":
    main()
