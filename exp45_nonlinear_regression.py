#!/usr/bin/env python3
"""
EXP 45: Nonlinear Simpson Regression — Phase Transition in Slope?

exp44: linear slope = 0.096 → δC*=1464 (unreachable).
BUT: SHA-256 is nonlinear. What if slope INCREASES at extreme δC?

If slope(δC) → ∞ at some δC_critical → phase transition.
At that critical point, δH could drop DISCONTINUOUSLY.

Also: exp44 used HW(δC) as scalar. But δC is 256-dimensional.
What if the regression works better on SPECIFIC δC bits?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_compress(W16, iv=None):
    if iv is None: iv=list(IV)
    W=list(W16)+[0]*48
    for t in range(16,64): W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r]; T2=sigma0(a)^maj(a,b,c)
        s=[T1^T2,a,b,c,d^T1,e,f,g]
    return [iv[i]^s[i] for i in range(8)]

def measure(Wn,Wf):
    Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
    Ln=xor_compress(Wn);Lf=xor_compress(Wf)
    dL=sum(hw(Ln[i]^Lf[i]) for i in range(8))
    dC=sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
    dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
    return dL,dC,dH

def test_local_slope(N=20000):
    """Measure slope at DIFFERENT δC values. Is there phase transition?"""
    print("\n--- LOCAL SLOPE ANALYSIS ---")

    data=[]
    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        dL,dC,dH=measure(Wn,Wf)
        data.append((dL,dC,dH))

    dL=np.array([d[0] for d in data])
    dC=np.array([d[1] for d in data])
    dH=np.array([d[2] for d in data])

    # High-δL regime only
    mask=dL>=np.percentile(dL,75)
    dC_h=dC[mask]; dH_h=dH[mask]

    # Bin by δC and measure LOCAL slope
    print(f"{'δC bin':>12} | {'N':>5} | {'E[δH]':>8} | {'Local slope':>12}")
    print("-"*45)

    bins = np.percentile(dC_h, np.arange(0,101,10))
    for i in range(len(bins)-1):
        in_bin = (dC_h >= bins[i]) & (dC_h < bins[i+1])
        if in_bin.sum() < 20: continue
        mean_dC = dC_h[in_bin].mean()
        mean_dH = dH_h[in_bin].mean()

        # Local slope via neighbors
        if i > 0 and i < len(bins)-2:
            prev_bin = (dC_h >= bins[i-1]) & (dC_h < bins[i])
            next_bin = (dC_h >= bins[i+1]) & (dC_h < bins[i+2])
            if prev_bin.sum()>10 and next_bin.sum()>10:
                slope = (dH_h[next_bin].mean() - dH_h[prev_bin].mean()) / \
                        (dC_h[next_bin].mean() - dC_h[prev_bin].mean())
            else:
                slope = 0
        else:
            slope = 0

        print(f"[{bins[i]:.0f}-{bins[i+1]:.0f}] | {in_bin.sum():>5} | "
              f"{mean_dH:>8.2f} | {slope:>+12.4f}")

    # Polynomial fit: δH = a + b·δC + c·δC² + d·δC³
    print(f"\nPolynomial fits (high-δL regime):")
    for degree in [1, 2, 3, 4]:
        coeffs = np.polyfit(dC_h, dH_h, degree)
        pred = np.polyval(coeffs, dC_h)
        r2 = 1 - np.var(dH_h - pred) / np.var(dH_h)
        print(f"  Degree {degree}: R²={r2:.6f}, coeffs={[f'{c:.4e}' for c in coeffs]}")

    # Critical: does QUADRATIC or CUBIC term change the picture?
    coeffs3 = np.polyfit(dC_h, dH_h, 3)
    # Predicted δH at extreme δC
    for dC_test in [150, 200, 300, 500, 1000]:
        pred = np.polyval(coeffs3, dC_test)
        print(f"  Cubic prediction at δC={dC_test}: δH={pred:.1f}")

def test_per_word_simpson(N=15000):
    """
    Simpson with PER-WORD δC instead of total.
    Maybe one word has slope >> 0.096?
    """
    print(f"\n--- PER-WORD SIMPSON (N={N}) ---")

    dL_list=[]; dH_list=[]
    dC_per_word = [[] for _ in range(8)]

    for _ in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        Ln=xor_compress(Wn);Lf=xor_compress(Wf)

        dL=sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        dL_list.append(dL); dH_list.append(dH)

        for w in range(8):
            dC_w = hw((Hn[w]^Ln[w])^(Hf[w]^Lf[w]))
            dC_per_word[w].append(dC_w)

    dL=np.array(dL_list); dH=np.array(dH_list)
    mask=dL>=np.percentile(dL,75)

    threshold=3/np.sqrt(mask.sum())
    print(f"High-δL regime (N={mask.sum()}):")
    for w in range(8):
        dCw=np.array(dC_per_word[w])[mask]
        dHm=dH[mask]
        c=np.corrcoef(dCw,dHm)[0,1]
        branch="a" if w<4 else "e"

        # Local regression
        X=np.column_stack([np.ones(len(dCw)),dCw])
        b=np.linalg.lstsq(X,dHm,rcond=None)[0]

        sig="***" if abs(c)>threshold else ""
        print(f"  H[{w}]({branch}): corr={c:+.6f}{sig:>4}, slope={b[1]:+.4f}")

def test_massive_search(N=50000):
    """Just throw compute at it. N=50000 Wang pairs. What's the minimum δH?"""
    print(f"\n--- MASSIVE SEARCH (N={N}) ---")

    best = 256
    best_pair = None

    for i in range(N):
        W0=random.randint(0,MASK);W1=random.randint(0,MASK)
        Wn,Wf,_,_,_=wang_cascade(W0,W1)
        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[j]^Hf[j]) for j in range(8))
        if dH<best:
            best=dH
            best_pair=(W0,W1)
            if best < 95:
                print(f"  New best at i={i}: δH={best}, W0=0x{W0:08x}")

    birthday=128-8*np.sqrt(2*np.log(N))
    print(f"\nBest δH found: {best}")
    print(f"Birthday expected (N={N}): ~{birthday:.1f}")
    print(f"{'ABOVE' if best > birthday else 'AT/BELOW'} birthday")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 45: NONLINEAR SIMPSON + MASSIVE SEARCH")
    print("="*60)
    test_local_slope(15000)
    test_per_word_simpson(10000)
    test_massive_search(50000)

if __name__=="__main__":
    main()
