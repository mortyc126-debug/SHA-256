#!/usr/bin/env python3
"""
EXP 21: Nonlinear Coupling→Output Channel

Linear corr(κ,δH)<0.05 (exp17). But SHA-256 is nonlinear.
exp17 hint: corr(κ_17·κ_18, δH) = -0.065 (***).

Test NONLINEAR functions of κ:
- Products κ_r · κ_{r+k}
- Thresholds 1{κ < t}
- Quadratic forms κ^T · A · κ
- Entropy H(κ_r..κ_{r+k})
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    carries = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        carries.append(c)
    return carries

def kappa_eT1(states_n, states_f, Wn_exp, Wf_exp, r):
    dn=states_n[r][3]; en=states_n[r][4]; fn=states_n[r][5]
    gn=states_n[r][6]; hn=states_n[r][7]
    df=states_f[r][3]; ef=states_f[r][4]; ff_=states_f[r][5]
    gf=states_f[r][6]; hf=states_f[r][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_exp[r])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_exp[r])&MASK
    cv_n=carry_vec(dn,T1n); cv_f=carry_vec(df,T1f)
    return sum(a^b for a,b in zip(cv_n,cv_f))

def main():
    random.seed(42)
    N = 3000
    print("="*60)
    print("EXP 21: NONLINEAR COUPLING→OUTPUT CHANNEL")
    print("="*60)

    # Collect coupling vectors
    kappas = []
    dHs = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn,sf = wang_cascade(W0,W1)
        We=schedule(Wn); Wfe=schedule(Wf)
        kv = [kappa_eT1(sn,sf,We,Wfe,r) for r in range(64)]
        kappas.append(kv)
        H_n=sha256_compress(Wn); H_f=sha256_compress(Wf)
        dHs.append(sum(hw(H_n[i]^H_f[i]) for i in range(8)))

    K = np.array(kappas); dH = np.array(dHs)
    threshold = 3/np.sqrt(N)

    # --- Products κ_r · κ_{r+k} ---
    print(f"\n--- PRODUCTS κ_r · κ_{{r+k}} → δH (threshold={threshold:.4f}) ---")
    signals = []
    for r in range(60):
        for lag in [1,2,3,4,5]:
            if r+lag >= 64: continue
            prod = K[:,r] * K[:,r+lag]
            if prod.std() == 0: continue
            c = np.corrcoef(prod, dH)[0,1]
            if abs(c) > threshold:
                signals.append((r, lag, c))

    signals.sort(key=lambda x: -abs(x[2]))
    print(f"Significant products: {len(signals)}")
    for r, lag, c in signals[:15]:
        print(f"  κ_{r}·κ_{r+lag}: corr={c:+.6f}")

    expected = 60*5 * 0.003  # ~300 tests, P(>3σ)≈0.3%
    print(f"Expected by chance: ~{expected:.1f}")

    # --- Threshold indicators ---
    print(f"\n--- THRESHOLD: 1{{κ_r < t}} → δH ---")
    for r in [16,17,32,48,63]:
        for t in [8, 12, 16]:
            indicator = (K[:,r] < t).astype(float)
            if indicator.std() == 0: continue
            c = np.corrcoef(indicator, dH)[0,1]
            if abs(c) > threshold:
                print(f"  1{{κ_{r}<{t}}}: corr={c:+.6f} ***")

    # --- Cumulative products ---
    print(f"\n--- CUMULATIVE PRODUCTS Π κ_r (rounds a..b) ---")
    for a,b in [(16,20),(20,30),(30,40),(40,50),(50,60),(56,64)]:
        b = min(b, 64)
        prod = np.prod(K[:,a:b], axis=1).astype(float)
        if prod.std() == 0: continue
        c = np.corrcoef(prod, dH)[0,1]
        sig = " ***" if abs(c) > threshold else ""
        print(f"  Π κ_[{a}..{b}): corr={c:+.6f}{sig}")

    # --- Min/Max over windows ---
    print(f"\n--- MIN/MAX OVER WINDOWS ---")
    for w_start in [0,16,32,48]:
        w_end = min(w_start+16, 64)
        mn = np.min(K[:,w_start:w_end], axis=1)
        mx = np.max(K[:,w_start:w_end], axis=1)
        rng = mx - mn
        for name, arr in [('min',mn),('max',mx),('range',rng)]:
            c = np.corrcoef(arr, dH)[0,1]
            sig = " ***" if abs(c) > threshold else ""
            if abs(c) > threshold:
                print(f"  {name}(κ_[{w_start}..{w_end})): corr={c:+.6f}{sig}")

    # --- Variance of κ over windows ---
    print(f"\n--- VARIANCE OF κ OVER WINDOWS ---")
    for w_start in [0,16,32,48]:
        w_end = min(w_start+16, 64)
        v = np.var(K[:,w_start:w_end], axis=1)
        c = np.corrcoef(v, dH)[0,1]
        sig = " ***" if abs(c) > threshold else ""
        if abs(c) > threshold or w_start in [16,48]:
            print(f"  var(κ_[{w_start}..{w_end})): corr={c:+.6f}{sig}")

    # --- Summary ---
    print(f"\n--- SUMMARY ---")
    print(f"Total nonlinear signals found: {len(signals)}")
    print(f"Expected by chance (multiple testing): ~{expected:.0f}")
    if len(signals) > expected * 2:
        print("*** MORE SIGNALS THAN EXPECTED — possible real nonlinear channel! ***")
    else:
        print("Signals consistent with multiple testing noise.")

if __name__ == "__main__":
    main()
