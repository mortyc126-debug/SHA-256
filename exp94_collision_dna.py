#!/usr/bin/env python3
"""
EXP 94: Collision DNA — Simultaneous Property Satisfaction

We know 7 properties of collision pairs (from 93 experiments).
Never tested: how many can be satisfied SIMULTANEOUSLY?

If 7/7 → collision.
If N/7 with N < 7 → measure gap.
The GAP tells us HOW FAR we are and WHERE the bottleneck is.

Properties:
  P1: δH close to 0
  P2: κ_63 close to 0
  P3: k(8) close to 113 (high carry at data flow saturation)
  P4: k(63) close to 69 (low carry at output)
  P5: carry_free close to max (transparency)
  P6: δCh_63 close to 0
  P7: δMaj close to 0

For each Wang pair: count how many properties are in "good" range.
Find: distribution of property satisfaction count.
And: does higher count → lower δH?
"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

ETA=(3*math.log(3)-4*math.log(2))/(4*math.log(2))

def carry_weight_at_round(states, W_expanded, r):
    a,b,c,d,e,f,g,h=states[r]
    T1=(h+sigma1(e)+ch(e,f,g)+K[r]+W_expanded[r])&MASK
    cv=0;cc=0
    for i in range(32):
        s=((d>>i)&1)+((T1>>i)&1)+cc;cc=1 if s>=2 else 0;cv+=cc
    return cv

def measure_dna(W0, W1):
    """Measure all 7 collision-DNA properties for one Wang pair."""
    Wn,Wf,DWs,sn,sf=wang_cascade(W0,W1)
    We=schedule(Wn);Wfe=schedule(Wf)
    Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)

    # P1: δH
    dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))

    # P2: κ_63
    def cv(a,b):
        c_out=[];c=0
        for i in range(32):
            s=((a>>i)&1)+((b>>i)&1)+c;c=1 if s>=2 else 0;c_out.append(c)
        return c_out
    dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn=sn[63][7]
    df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    k63=sum(a^b for a,b in zip(cv(dn,T1n),cv(df,T1f)))

    # P3: k(8)
    k8=carry_weight_at_round(sn,We,8)

    # P4: k(63)
    k63_weight=carry_weight_at_round(sn,We,63)

    # P5: carry_free (transparency)
    cf=0
    for w in range(4,8):
        for bit in range(5):
            sx=(sn[64][w]^sf[64][w]>>bit)&1
            hx=(Hn[w]^Hf[w]>>bit)&1
            if sx==hx: cf+=1

    # P6: δCh_63
    dch=hw(ch(en,fn,gn)^ch(ef,ff_,gf))

    # P7: δMaj (a-branch)
    an=sn[63][0];bn=sn[63][1];cn=sn[63][2]
    af=sf[63][0];bf=sf[63][1];cf_=sf[63][2]
    dmaj=hw(maj(an,bn,cn)^maj(af,bf,cf_))

    return {
        'dH':dH, 'k63_coupling':k63, 'k8':k8, 'k63_weight':k63_weight,
        'carry_free':cf, 'dCh63':dch, 'dMaj63':dmaj
    }

def property_score(dna):
    """Count how many properties are in "collision-like" range."""
    score=0
    # P1: δH < 100 (near-collision territory)
    if dna['dH']<110: score+=1
    # P2: κ_63 < 12 (low coupling)
    if dna['k63_coupling']<12: score+=1
    # P3: k(8) > 18 (high carry at round 8)
    if dna['k8']>18: score+=1
    # P4: k(63) weight in normal range (not extreme)
    if dna['k63_weight']>14 and dna['k63_weight']<18: score+=1
    # P5: carry_free > 12 (high transparency)
    if dna['carry_free']>12: score+=1
    # P6: δCh_63 < 12 (low Ch differential)
    if dna['dCh63']<12: score+=1
    # P7: δMaj_63 < 12
    if dna['dMaj63']<12: score+=1
    return score

def main():
    random.seed(42);N=10000
    print("="*60)
    print(f"EXP 94: COLLISION DNA (N={N})")
    print("="*60)

    scores=[];dHs=[];dnas=[]
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        dna=measure_dna(W0,W1)
        s=property_score(dna)
        scores.append(s);dHs.append(dna['dH']);dnas.append(dna)

    sa=np.array(scores);da=np.array(dHs)

    print(f"\nProperty satisfaction distribution:")
    for s in range(8):
        count=np.sum(sa==s)
        if count>0:
            sub_dH=da[sa==s]
            print(f"  Score {s}/7: N={count:>5} ({count/N*100:>5.1f}%), "
                  f"E[δH]={sub_dH.mean():.2f}, min={sub_dH.min()}")

    c=np.corrcoef(sa,da)[0,1]
    print(f"\ncorr(score, δH) = {c:+.6f}")

    # Best pairs by score
    best_idx=np.argsort(-sa)[:20]
    print(f"\nTop 20 by DNA score:")
    for rank,idx in enumerate(best_idx[:10]):
        d=dnas[idx]
        print(f"  #{rank+1}: score={sa[idx]}/7, δH={d['dH']}, "
              f"κ63={d['k63_coupling']}, k8={d['k8']}, "
              f"δCh={d['dCh63']}, δMaj={d['dMaj63']}")

    # KEY: does max score → min δH?
    max_score=sa.max()
    max_score_dH=da[sa==max_score]
    print(f"\nMax score {max_score}/7: N={len(max_score_dH)}, "
          f"E[δH]={max_score_dH.mean():.2f}, min={max_score_dH.min()}")

    random_dH=da[sa==int(np.median(sa))]
    print(f"Median score: E[δH]={random_dH.mean():.2f}")
    print(f"Difference: {random_dH.mean()-max_score_dH.mean():+.2f}")

if __name__=="__main__": main()
