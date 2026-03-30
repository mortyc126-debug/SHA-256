#!/usr/bin/env python3
"""
EXP 40: Verify Triple Interaction at Large N

exp39 found conditional sign-flip:
  corr(δL, δH | δR low) = +0.060
  corr(δL, δH | δR high) = -0.052
  Simpson's paradox in SHA-256.

Need N=10000+ to confirm/deny.
Also: test if the effect scales with conditioning strength.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_compress(W16, iv=None):
    if iv is None: iv = list(IV)
    W=list(W16)+[0]*48
    for t in range(16,64): W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r]; T2=sigma0(a)^maj(a,b,c)
        s=[T1^T2,a,b,c,d^T1,e,f,g]
    return [iv[i]^s[i] for i in range(8)]

def no_rot_compress(W16, iv=None):
    if iv is None: iv = list(IV)
    W=list(W16)+[0]*48
    for t in range(16,64): W[t]=((W[t-2]>>10)+(W[t-7])+(W[t-15]>>3)+W[t-16])&MASK
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=(h+0+ch(e,f,g)+K[r]+W[r])&MASK; T2=(0+maj(a,b,c))&MASK
        s=[(T1+T2)&MASK,a,b,c,(d+T1)&MASK,e,f,g]
    return [(iv[i]+s[i])&MASK for i in range(8)]

def measure_triple(Wn, Wf):
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    Ln=xor_compress(Wn); Lf=xor_compress(Wf)
    Nn=no_rot_compress(Wn); Nf=no_rot_compress(Wf)
    dL=sum(hw(Ln[i]^Lf[i]) for i in range(8))
    dC=sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
    dR=sum(hw((Hn[i]^Nn[i])^(Hf[i]^Nf[i])) for i in range(8))
    dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
    return dL, dC, dR, dH

def main():
    random.seed(42)
    N = 10000
    print("="*60)
    print(f"EXP 40: VERIFY TRIPLE INTERACTION (N={N})")
    print("="*60)

    dL_a=[]; dC_a=[]; dR_a=[]; dH_a=[]
    for i in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        dL,dC,dR,dH = measure_triple(Wn,Wf)
        dL_a.append(dL); dC_a.append(dC); dR_a.append(dR); dH_a.append(dH)

    dL=np.array(dL_a); dC=np.array(dC_a); dR=np.array(dR_a); dH=np.array(dH_a)
    threshold = 3/np.sqrt(N)

    print(f"\nN={N}, threshold={threshold:.4f}")

    # --- Unconditional ---
    print(f"\n--- UNCONDITIONAL ---")
    print(f"corr(δL, δH) = {np.corrcoef(dL,dH)[0,1]:+.6f}")
    print(f"corr(δC, δH) = {np.corrcoef(dC,dH)[0,1]:+.6f}")
    print(f"corr(δR, δH) = {np.corrcoef(dR,dH)[0,1]:+.6f}")
    print(f"corr(δL, δC) = {np.corrcoef(dL,dC)[0,1]:+.6f}")
    print(f"corr(δL, δR) = {np.corrcoef(dL,dR)[0,1]:+.6f}")
    print(f"corr(δC, δR) = {np.corrcoef(dC,dR)[0,1]:+.6f}")

    # --- Conditional on δR (THE KEY TEST) ---
    print(f"\n--- CONDITIONAL ON δR (sign-flip test) ---")
    med_R = np.median(dR)

    for label, mask in [("δR < P25", dR < np.percentile(dR, 25)),
                         ("δR < P50", dR < med_R),
                         ("δR > P50", dR > med_R),
                         ("δR > P75", dR > np.percentile(dR, 75))]:
        n = mask.sum()
        if n < 50: continue
        c_LH = np.corrcoef(dL[mask], dH[mask])[0,1]
        c_CH = np.corrcoef(dC[mask], dH[mask])[0,1]
        t = 3/np.sqrt(n)
        sig_L = "***" if abs(c_LH)>t else ""
        sig_C = "***" if abs(c_CH)>t else ""
        print(f"  {label:>12} (N={n:>5}): corr(δL,δH)={c_LH:+.6f}{sig_L:>4}  "
              f"corr(δC,δH)={c_CH:+.6f}{sig_C:>4}")

    # --- Conditional on δL ---
    print(f"\n--- CONDITIONAL ON δL ---")
    med_L = np.median(dL)
    for label, mask in [("δL < P25", dL < np.percentile(dL, 25)),
                         ("δL < P50", dL < med_L),
                         ("δL > P50", dL > med_L),
                         ("δL > P75", dL > np.percentile(dL, 75))]:
        n = mask.sum()
        if n < 50: continue
        c_CH = np.corrcoef(dC[mask], dH[mask])[0,1]
        c_RH = np.corrcoef(dR[mask], dH[mask])[0,1]
        t = 3/np.sqrt(n)
        print(f"  {label:>12} (N={n:>5}): corr(δC,δH)={c_CH:+.6f}{'***' if abs(c_CH)>t else '':>4}  "
              f"corr(δR,δH)={c_RH:+.6f}{'***' if abs(c_RH)>t else '':>4}")

    # --- ALL combinations ---
    print(f"\n--- JOINT LOW/HIGH ANALYSIS ---")
    med_C = np.median(dC)

    for lL, lC, lR in [("low","low","low"), ("low","low","high"),
                         ("low","high","low"), ("high","low","low"),
                         ("high","high","high")]:
        mask = np.ones(N, dtype=bool)
        if lL=="low": mask &= dL<med_L
        else: mask &= dL>=med_L
        if lC=="low": mask &= dC<med_C
        else: mask &= dC>=med_C
        if lR=="low": mask &= dR<med_R
        else: mask &= dR>=med_R

        n = mask.sum()
        if n < 20: continue
        m = dH[mask].mean()
        print(f"  L={lL:>4} C={lC:>4} R={lR:>4}: N={n:>5}, E[δH]={m:.4f} (Δ={m-dH.mean():+.4f})")

    # --- Strongest test: sign-flip MAGNITUDE ---
    print(f"\n--- SIGN-FLIP MAGNITUDE ---")
    for p in [10, 20, 30, 40, 50]:
        low_thresh = np.percentile(dR, p)
        high_thresh = np.percentile(dR, 100-p)

        mask_low = dR <= low_thresh
        mask_high = dR >= high_thresh

        if mask_low.sum()<50 or mask_high.sum()<50: continue

        c_low = np.corrcoef(dL[mask_low], dH[mask_low])[0,1]
        c_high = np.corrcoef(dL[mask_high], dH[mask_high])[0,1]
        flip = c_low - c_high

        print(f"  P{p:>2}/P{100-p}: corr_low={c_low:+.4f}, corr_high={c_high:+.4f}, "
              f"FLIP={flip:+.4f}")

    print(f"\n--- VERDICT ---")

if __name__ == "__main__":
    main()
