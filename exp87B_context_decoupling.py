#!/usr/bin/env python3
"""EXP 87B: Context Decoupling — can XOR/ADD/AND be made independent?"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

def main():
    random.seed(42);N=1000
    print("="*60)
    print("EXP 87B: CONTEXT DECOUPLING")
    print("="*60)
    # From exp66A: joint rank=490/512. Shared=22.
    # Question: WHICH 22 dimensions are shared?
    # If shared dims = specific bit positions → targeted decouple possible
    print("\nContext coupling: 22 shared dimensions (exp66A)")
    print("If shared dims are SPECIFIC → can decouple at those positions")
    # Measure: for each output bit, is carry component = XOR component?
    equal_count=np.zeros(256)
    for _ in range(N):
        W16=random_w16()
        Hn=sha256_compress(W16)
        # XOR hash
        iv=list(IV);W=list(W16)+[0]*48
        for t in range(16,64):W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
        s=list(iv)
        for r in range(64):
            a,b,c,d,e,f,g,h=s
            T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r];T2=sigma0(a)^maj(a,b,c)
            s=[T1^T2,a,b,c,d^T1,e,f,g]
        Ln=[iv[i]^s[i] for i in range(8)]
        for w in range(8):
            for b in range(32):
                if ((Hn[w]>>b)&1)==((Ln[w]>>b)&1):
                    equal_count[w*32+b]+=1
    equal_count/=N
    # Bits where hash = XOR hash > 60% of time = "coupled" bits
    coupled=np.sum(equal_count>0.55)
    decoupled=np.sum(equal_count<0.45)
    print(f"Bits where hash≈XOR (>55%): {coupled}")
    print(f"Bits where hash≠XOR (<45%): {decoupled}")
    print(f"Bits where hash≈random (45-55%): {256-coupled-decoupled}")
    # Top coupled bits
    top=np.argsort(-equal_count)[:10]
    print(f"\nMost coupled bits (hash=XOR most often):")
    for idx in top:
        w=idx//32;b=idx%32;br="a" if w<4 else "e"
        print(f"  H[{w}]({br}) bit {b:>2}: {equal_count[idx]:.4f}")

if __name__=="__main__": main()
