#!/usr/bin/env python3
"""
EXP 93: k(8) as Predictor — Causation or Correlation?

exp92: near-collision pairs have k(8)=113 vs random k(8)=82. Diff=+30!
But: is this CAUSE or CONSEQUENCE of low δH?

CAUSAL TEST: compute k(8) for MANY pairs FIRST (cheap: 8 rounds).
THEN: among high-k(8) pairs, check if δH is LOWER (full 64 rounds).

If yes → k(8) PREDICTS near-collision → filter at 12.5% cost.
If no → k(8) is consequence of Wang structure, not predictor.

Also: k(8) is cheap (8/64 rounds). If predictive → practical speedup.
"""
import sys,os,random,math
import numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from sha256_core import *

ETA=(3*math.log(3)-4*math.log(2))/(4*math.log(2))

def measure_k8(Wn):
    """Measure k(8) = carry weight at round 8. Cost: 8 rounds."""
    states=sha256_rounds(Wn,8)
    W=schedule(Wn)
    a,b,c,d,e,f,g,h=states[8]
    T1=(h+sigma1(e)+ch(e,f,g)+K[8]+W[8])&MASK
    cv=0;cc=0
    for i in range(32):
        s=((d>>i)&1)+((T1>>i)&1)+cc;cc=1 if s>=2 else 0;cv+=cc
    return cv

def test_k8_predicts_dH(N=10000):
    """CAUSAL: does k(8) computed from Wn PREDICT δH of Wang pair?"""
    print(f"\n--- k(8) AS δH PREDICTOR (N={N}) ---")

    k8s=[]; dHs=[]
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn=[W0,W1]+[0]*14

        # CHEAP: compute k(8) (8 rounds only)
        k8=measure_k8(Wn)
        k8s.append(k8)

        # EXPENSIVE: full Wang cascade + hash (64 rounds)
        Wn_w,Wf,_,_,_=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn_w);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        dHs.append(dH)

    k8a=np.array(k8s);dHa=np.array(dHs)
    threshold=3/np.sqrt(N)
    c=np.corrcoef(k8a,dHa)[0,1]

    print(f"corr(k(8), δH) = {c:+.6f} {'***' if abs(c)>threshold else ''}")
    print(f"Threshold: {threshold:.4f}")

    # Quartile analysis
    for label,mask in [("k(8) top 10%",k8a>np.percentile(k8a,90)),
                        ("k(8) top 25%",k8a>np.percentile(k8a,75)),
                        ("k(8) bottom 25%",k8a<np.percentile(k8a,25)),
                        ("k(8) bottom 10%",k8a<np.percentile(k8a,10))]:
        sub=dHa[mask]
        print(f"  {label:>20}: E[δH]={sub.mean():.4f}, min={sub.min()}, N={len(sub)}")

    # PRACTICAL: filter by k(8), then birthday on filtered set
    print(f"\nPRACTICAL FILTER TEST:")
    # Select pairs with k(8) > threshold, check δH
    for k_thresh in [18,19,20,21,22]:
        selected=dHa[k8a>=k_thresh]
        n_sel=len(selected)
        if n_sel<10: continue
        pct=n_sel/N*100
        print(f"  k(8)≥{k_thresh}: N={n_sel} ({pct:.1f}%), "
              f"E[δH]={selected.mean():.2f}, min={selected.min()}")

def test_k8_vs_random_search(N=50000):
    """Compare: k(8)-guided search vs pure random at same budget."""
    print(f"\n--- k(8)-GUIDED vs RANDOM (budget={N}) ---")

    # Strategy 1: random search
    best_random=256
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        best_random=min(best_random,dH)

    # Strategy 2: compute k(8) for 8× more candidates (cheap),
    # select top 12.5%, then full hash only those
    n_screen=N*8  # 8× more screened (k(8) costs 12.5%)
    k8_candidates=[]
    for _ in range(n_screen):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        k8=measure_k8([W0,W1]+[0]*14)
        k8_candidates.append((k8,W0,W1))

    # Select top 12.5% by k(8) → N candidates
    k8_candidates.sort(reverse=True)
    selected=k8_candidates[:N]

    best_guided=256
    for k8,W0,W1 in selected:
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        best_guided=min(best_guided,dH)

    birthday=128-8*math.sqrt(2*math.log(N))

    print(f"Random search (N={N}):   best δH = {best_random}")
    print(f"k(8)-guided (N={N}):     best δH = {best_guided}")
    print(f"Birthday (N={N}):        ~{birthday:.0f}")

    if best_guided<best_random:
        print(f"*** k(8)-GUIDED BEATS RANDOM by {best_random-best_guided} bits! ***")
    else:
        print(f"Random wins by {best_guided-best_random}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 93: k(8) AS PREDICTOR")
    print("Causation or correlation?")
    print("="*60)
    test_k8_predicts_dH(8000)
    test_k8_vs_random_search(20000)

if __name__=="__main__": main()
