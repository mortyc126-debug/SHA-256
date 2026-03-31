#!/usr/bin/env python3
"""EXP 87E: Ternary Collision — work in base 3 (GKP space)"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

def gkp_encode(a, b):
    """Encode addition a+b as ternary GKP sequence (0=K, 1=G, 2=P)."""
    t=[]
    for i in range(32):
        ai=(a>>i)&1;bi=(b>>i)&1
        if ai==1 and bi==1: t.append(1)  # G
        elif ai==0 and bi==0: t.append(0) # K
        else: t.append(2)                  # P
    return t

def main():
    random.seed(42);N=2000
    print("="*60)
    print("EXP 87E: TERNARY COLLISION")
    print("="*60)
    # SHA-256 carry = ternary (GKP). What if we search in TERNARY space?
    # GKP encoding: each carry position = {G=1, K=0, P=2}
    # Birthday in ternary: 3^{n/2} for n ternary positions
    # Key: what is effective TERNARY dimension of SHA-256?

    # From T_CARRY_RANK_TERNARY: carry_rank = 3^5 = 243
    # This IS the ternary dimension!
    # Birthday in ternary: 3^{243/2} = 3^{121.5}
    # In bits: 121.5 × log₂3 = 121.5 × 1.585 = 192.6 bits
    # This is WORSE than binary birthday (128)

    print(f"Ternary dimension: 3^5 = 243 (from T_CARRY_RANK_TERNARY)")
    print(f"Ternary birthday: 3^{{243/2}} = 3^{{121.5}}")
    print(f"In bits: {121.5*math.log2(3):.1f} > 128 → WORSE than binary")

    # BUT: ternary space might have DIFFERENT collision structure
    # GKP = {K(0), G(1), P(2)}. K and G are DETERMINED. Only P is free.
    # Effective ternary DOF = number of P-positions
    # P ≈ 50% of 448×32 = 14336 positions → 7168 P-positions
    # But P carries 1 bit of info (propagate or not) → binary
    # Ternary encoding DOESN'T add DOF — it describes structure

    # Alternative: ternary HASH — encode hash in base 3
    # Each output bit has GKP from feedforward carry
    # GKP at output → ternary encoding of hash

    # For Wang pairs: measure GKP distribution at output
    gkp_profiles=[]
    dHs=[]
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        # GKP of feedforward carry for each word
        total_gkp=[0,0,0] # K,G,P counts
        for w in range(8):
            gkp=gkp_encode(IV[w],sn[64][w])
            for g in gkp:
                total_gkp[g]+=1
        gkp_profiles.append(total_gkp)
        dHs.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    gkp_a=np.array(gkp_profiles) # N×3
    dH_a=np.array(dHs)
    print(f"\nGKP at output feedforward:")
    print(f"  K: {gkp_a[:,0].mean():.1f}, G: {gkp_a[:,1].mean():.1f}, P: {gkp_a[:,2].mean():.1f}")
    print(f"  (out of {8*32}={256})")

    # Does GKP distribution predict δH?
    for i,name in enumerate(['K','G','P']):
        c=np.corrcoef(gkp_a[:,i],dH_a)[0,1]
        sig="***" if abs(c)>3/np.sqrt(N) else ""
        print(f"  corr({name}_count, δH) = {c:+.6f} {sig}")

    # SHA-512 prediction
    print(f"\n--- SHA-512 PREDICTION ---")
    print(f"SHA-256: carry_rank = 3^5 = 243 < 256 → deficit 13")
    print(f"SHA-512: carry_rank = 3^6 = 729 > 512 → deficit 0 (PREDICTED)")
    print(f"If SHA-512 deficit = 0 → UALRA confirmed on different architecture!")

if __name__=="__main__": main()
