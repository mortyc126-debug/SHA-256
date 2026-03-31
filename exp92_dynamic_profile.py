#!/usr/bin/env python3
"""
EXP 92: Dynamic η-Lattice Full Profile — k(r) for ALL 64 rounds

From exp87C: k varies 80-100 across rounds. Shape = thermalization.

Measure k(r) at ALL 64 rounds with high N.
Look for: patterns, correlations with K[r], schedule structure.

Also: does k(r) shape DIFFER for near-collision pairs vs random?
If yes → dynamic lattice identifies near-collision conditions.
"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

ETA=(3*math.log(3)-4*math.log(2))/(4*math.log(2))

def measure_k_profile(N=500):
    """k(r) for all 64 rounds."""
    sdeg={r:[] for r in range(64)}
    for _ in range(N):
        W16=random_w16();states=sha256_rounds(W16,64);W=schedule(W16)
        for r in range(64):
            a,b,c,d,e,f,g,h=states[r]
            T1=(h+sigma1(e)+ch(e,f,g)+K[r]+W[r])&MASK
            cv=0;cc=0
            for i in range(32):
                s=((d>>i)&1)+((T1>>i)&1)+cc;cc=1 if s>=2 else 0;cv+=cc
            sdeg[r].append(cv)
    return {r:np.mean(sdeg[r]) for r in range(64)}

def main():
    random.seed(42)
    print("="*60)
    print("EXP 92: DYNAMIC η-LATTICE FULL PROFILE")
    print("="*60)

    profile=measure_k_profile(400)
    k_profile={r:profile[r]/ETA for r in range(64)}

    print(f"\nk(r) for ALL 64 rounds:")
    print(f"{'Round':>5} | {'S':>6} | {'k':>6} | {'HW(K[r])':>8} | {'Shape'}")
    print("-"*45)

    k_vals=[]; hw_ks=[]
    for r in range(64):
        k=k_profile[r]; s=profile[r]; hwk=hw(K[r])
        k_int=round(k)
        shape=""
        if k>90: shape="HIGH"
        elif k<78: shape="LOW"
        k_vals.append(k); hw_ks.append(hwk)
        if r<10 or r>58 or r%8==0:
            print(f"{r:>5} | {s:>6.2f} | {k:>6.1f} | {hwk:>8} | {shape}")

    # Correlation k(r) vs HW(K[r])
    ka=np.array(k_vals); ha=np.array(hw_ks)
    c=np.corrcoef(ka,ha)[0,1]
    print(f"\ncorr(k(r), HW(K[r])) = {c:+.4f}")

    # Fourier of k(r) profile
    k_centered=ka-ka.mean()
    fft=np.fft.fft(k_centered)
    power=np.abs(fft)**2
    peak=np.argmax(power[1:32])+1
    print(f"Fourier of k(r): peak at freq={peak} (period={64/peak:.1f})")

    # Key statistics
    print(f"\nProfile statistics:")
    print(f"  Mean k: {ka.mean():.2f}")
    print(f"  Std k:  {ka.std():.2f}")
    print(f"  Min k:  {ka.min():.2f} at round {np.argmin(ka)}")
    print(f"  Max k:  {ka.max():.2f} at round {np.argmax(ka)}")
    print(f"  Range:  {ka.max()-ka.min():.2f}")

    # Do near-collision pairs have DIFFERENT k(r)?
    print(f"\n--- k(r) FOR NEAR-COLLISION vs RANDOM PAIRS ---")
    best_profile={r:[] for r in range(64)}
    rand_profile={r:[] for r in range(64)}

    for trial in range(2000):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf=wang_cascade(W0,W1)
        We=schedule(Wn);Wfe=schedule(Wf)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))

        for r in [0,1,4,8,16,32,48,63]:
            a,b,c,d,e,f,g,h=sn[r]
            T1=(h+sigma1(e)+ch(e,f,g)+K[r]+We[r])&MASK
            cv=0;cc=0
            for i in range(32):
                s=((d>>i)&1)+((T1>>i)&1)+cc;cc=1 if s>=2 else 0;cv+=cc

            if dH<105:
                best_profile[r].append(cv)
            else:
                rand_profile[r].append(cv)

    print(f"{'Round':>5} | {'Near-coll k':>11} | {'Random k':>9} | {'Diff':>6}")
    print("-"*45)
    for r in [0,1,4,8,16,32,48,63]:
        b=np.array(best_profile[r]) if best_profile[r] else np.array([0])
        ra=np.array(rand_profile[r]) if rand_profile[r] else np.array([0])
        bk=b.mean()/ETA; rk=ra.mean()/ETA
        print(f"{r:>5} | {bk:>11.1f} | {rk:>9.1f} | {bk-rk:>+6.1f}")

if __name__=="__main__": main()
