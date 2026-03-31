#!/usr/bin/env python3
"""EXP 87D: ★-Composition Shortcut — does 448-operation sequence have algebraic structure?"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

def main():
    random.seed(42);N=500
    print("="*60)
    print("EXP 87D: ★-COMPOSITION SHORTCUT")
    print("="*60)
    # If ★-composition has shortcut: F^k should have LOWER degree than k × degree(F)
    # Measure: does repeated application of round function REDUCE complexity?
    # Test via: how many input bits affect output after R rounds (= rank)?
    print("\nRank growth: if shortcut exists, rank grows SUB-linearly")
    print(f"{'R':>4} | {'Rank':>6} | {'R×32':>6} | {'Ratio':>6} | {'Shortcut?'}")
    print("-"*40)
    for R in [1,2,4,8,16,32,64]:
        ranks=[]
        for _ in range(min(N,30)):
            W16=random_w16()
            base=sha256_rounds(W16,R)
            count=0
            for w in range(16):
                for b in [0,8,16,24,31]:
                    Wp=list(W16);Wp[w]^=(1<<b)
                    pert=sha256_rounds(Wp,R)
                    d=sum(hw(base[R][i]^pert[R][i]) for i in range(8))
                    if d>0: count+=1
            ranks.append(count)
        avg_rank=np.mean(ranks)
        expected=min(R*32,256)
        ratio=avg_rank/expected if expected>0 else 0
        shortcut="SUB-LINEAR" if ratio<0.9 else "linear"
        print(f"{R:>4} | {avg_rank:>6.0f} | {expected:>6} | {ratio:>6.3f} | {shortcut}")

    # Also: is F^2 = F∘F simpler than two separate rounds?
    print(f"\n2-round composition test:")
    print(f"If F∘F has algebraic shortcut → some F² outputs = polynomial of F¹ outputs")
    # Measure: corr between round-1 state and round-2 state
    corrs=[]
    for _ in range(N):
        W16=random_w16()
        s1=sha256_rounds(W16,1);s2=sha256_rounds(W16,2)
        d=sum(hw(s1[1][i]^s2[2][i]) for i in range(8))
        corrs.append(d)
    print(f"  dist(state[1], state[2]) = {np.mean(corrs):.1f}/256")
    print(f"  If shortcut: would be < 128. Actual: {'NO shortcut' if np.mean(corrs)>120 else 'POSSIBLE'}")

if __name__=="__main__": main()
