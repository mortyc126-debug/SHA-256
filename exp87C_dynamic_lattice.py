#!/usr/bin/env python3
"""EXP 87C: Dynamic η-Lattice — do constants change with round?"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

ETA=(3*math.log(3)-4*math.log(2))/(4*math.log(2))

def main():
    random.seed(42);N=500
    print("="*60)
    print("EXP 87C: DYNAMIC η-LATTICE")
    print("="*60)
    # Measure S-degree (carry weight) PER ROUND
    print("\nS-degree per round (is it CONSTANT or varies?):")
    sdeg_per_round={r:[] for r in range(64)}
    for _ in range(N):
        W16=random_w16()
        states=sha256_rounds(W16,64);W=schedule(W16)
        for r in range(64):
            a,b,c,d,e,f,g,h=states[r]
            T1=(h+sigma1(e)+ch(e,f,g)+K[r]+W[r])&MASK
            cv=[];cc=0
            for i in range(32):
                s=((d>>i)&1)+((T1>>i)&1)+cc;cc=1 if s>=2 else 0;cv.append(cc)
            sdeg_per_round[r].append(sum(cv))
    print(f"{'Round':>5} | {'E[S]':>6} | {'S/η':>6} | {'k':>4} | {'Stable?'}")
    print("-"*40)
    k_values=[]
    for r in [0,1,4,8,16,32,48,63]:
        arr=np.array(sdeg_per_round[r])
        k=round(arr.mean()/ETA)
        k_values.append(k)
        stable="yes" if abs(arr.mean()/ETA-k)<2 else "DRIFT"
        print(f"{r:>5} | {arr.mean():>6.2f} | {arr.mean()/ETA:>6.1f} | {k:>4} | {stable}")
    # Does k change with round?
    if len(set(k_values))>1:
        print(f"\n*** k VARIES: {k_values} → DYNAMIC LATTICE! ***")
    else:
        print(f"\nk constant = {k_values[0]} → STATIC lattice")

if __name__=="__main__": main()
