#!/usr/bin/env python3
"""EXP 87A: Non-Architectural Variable — is there a 12th constant that varies with message?"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

ETA=(3*math.log(3)-4*math.log(2))/(4*math.log(2))

def measure_all_11_constants(Wn,Wf):
    sn=sha256_rounds(Wn,64);sf=sha256_rounds(Wf,64)
    We=schedule(Wn);Wfe=schedule(Wf)
    Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
    # κ_63
    dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn=sn[63][7]
    df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    def cv(a,b):
        c_out=[];c=0
        for i in range(32):
            s=((a>>i)&1)+((b>>i)&1)+c;c=1 if s>=2 else 0;c_out.append(c)
        return c_out
    k63=sum(a^b for a,b in zip(cv(dn,T1n),cv(df,T1f)))
    # Cascade depth
    d=0
    for bit in range(32):
        if ((sn[64][4]^sf[64][4]>>bit)&1)==((Hn[4]^Hf[4]>>bit)&1): d+=1
        else: break
    # S-degree
    r=random.randint(0,63)
    a,b,c,dd,e,f,g,h=sn[r]
    T1=(h+sigma1(e)+ch(e,f,g)+K[r]+We[r])&MASK
    sdeg=sum(cv(dd,T1))
    dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
    return {'k63':k63,'cascade':d,'sdeg':sdeg,'dH':dH}

def main():
    random.seed(42);N=2000
    print("="*60)
    print("EXP 87A: NON-ARCHITECTURAL VARIABLE")
    print("="*60)
    # Per-message measurement of k63, cascade, sdeg
    k63s=[];cascades=[];sdegs=[];dHs=[]
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        m=measure_all_11_constants(Wn,Wf)
        k63s.append(m['k63']);cascades.append(m['cascade'])
        sdegs.append(m['sdeg']);dHs.append(m['dH'])
    # Convert to η-units and check variability
    for name,vals,expected_k in [('κ_63',k63s,84),('cascade',cascades,24),('S_degree',sdegs,int(15.3/ETA))]:
        a=np.array(vals);eta_vals=a/ETA
        cv=a.std()/a.mean()*100 if a.mean()>0 else 0
        c=np.corrcoef(a,dHs)[0,1]
        print(f"{name:>10}: E={a.mean():.2f}={a.mean()/ETA:.1f}η, CV={cv:.1f}%, "
              f"corr(δH)={c:+.4f}, expected={expected_k}η")
    # NEW: per-message η-deviation from lattice point
    print(f"\nPer-message η-deviation:")
    for name,vals,k in [('κ_63',k63s,84)]:
        a=np.array(vals)
        deviation=a-k*ETA
        corr_dev=np.corrcoef(deviation,dHs)[0,1]
        print(f"  {name}: E[deviation]={deviation.mean():.4f}, corr(dev,δH)={corr_dev:+.6f}")
        if abs(corr_dev)>3/np.sqrt(N):
            print(f"  *** DEVIATION CORRELATES WITH δH! ***")

if __name__=="__main__": main()
