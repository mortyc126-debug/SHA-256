#!/usr/bin/env python3
"""
EXP 44: Solve Simpson's Equation

NOT search. NOT selection. COMPUTATION.

Simpson's Paradox: corr(δC, δH | δL > P75) = -0.122 (Z=5.6).
This means: in the high-δL regime, δH ≈ α - 0.122·δC + noise.

This is a LINEAR EQUATION. Equations can be SOLVED.

If we can find (M, M') where:
  1. δL > P75 (filter by cheap XOR computation)
  2. δC is MAXIMAL (push carry correction high)
  3. Then δH is MINIMIZED (by the -0.122 slope)

The key: we need δC to be CONTROLLABLE at fixed δL.
exp42 showed δL is NOT invariant. BUT the correlation
at -0.122 means the relationship EXISTS statistically.

NEW APPROACH: Instead of trying to control δC directly,
find the REGRESSION EQUATION and solve for δH=0.

Required δC for δH=0: δC = (128 - intercept) / 0.122
If this δC value is REACHABLE → collision exists at that point.
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

def measure_all(Wn, Wf):
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    Ln=xor_compress(Wn); Lf=xor_compress(Wf)
    dL=sum(hw(Ln[i]^Lf[i]) for i in range(8))
    dC=sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
    dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
    return dL, dC, dH

def test_regression_equation(N=15000):
    """
    Fit the FULL regression: δH = a + b·δL + c·δC + d·δL·δC + noise.
    In the high-δL regime: δH = a' + c'·δC.
    Solve for δH=0: δC* = -a'/c'.
    Is δC* reachable?
    """
    print("\n--- TEST 1: REGRESSION EQUATION ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        dL,dC,dH = measure_all(Wn,Wf)
        data.append((dL,dC,dH))

    dL=np.array([d[0] for d in data])
    dC=np.array([d[1] for d in data])
    dH=np.array([d[2] for d in data])

    # Full regression: δH = a + b·δL + c·δC + d·δL·δC
    X = np.column_stack([np.ones(N), dL, dC, dL*dC])
    beta = np.linalg.lstsq(X, dH, rcond=None)[0]
    dH_pred = X @ beta
    r_squared = 1 - np.var(dH - dH_pred) / np.var(dH)

    print(f"Full regression: δH = {beta[0]:.2f} + {beta[1]:.4f}·δL + {beta[2]:.4f}·δC + {beta[3]:.6f}·δL·δC")
    print(f"R² = {r_squared:.6f}")

    # Conditional regressions by δL quartile
    print(f"\nConditional regressions:")
    for label, mask in [("δL < P25", dL < np.percentile(dL, 25)),
                         ("P25-P50", (dL >= np.percentile(dL,25)) & (dL < np.percentile(dL,50))),
                         ("P50-P75", (dL >= np.percentile(dL,50)) & (dL < np.percentile(dL,75))),
                         ("δL > P75", dL >= np.percentile(dL, 75))]:
        dC_sub = dC[mask]; dH_sub = dH[mask]
        n = len(dC_sub)
        if n < 100: continue

        # Simple regression: δH = a + b·δC
        X_sub = np.column_stack([np.ones(n), dC_sub])
        b = np.linalg.lstsq(X_sub, dH_sub, rcond=None)[0]
        r2 = 1 - np.var(dH_sub - X_sub@b) / np.var(dH_sub)

        # Solve for δH=0: 0 = b[0] + b[1]·δC → δC* = -b[0]/b[1]
        if abs(b[1]) > 1e-6:
            dC_star = -b[0] / b[1]
        else:
            dC_star = float('inf')

        print(f"  {label:>10} (N={n:>4}): δH = {b[0]:.2f} + {b[1]:+.4f}·δC  "
              f"R²={r2:.6f}  δC*={dC_star:.1f}")

        # Is δC* reachable?
        print(f"    δC range: [{dC_sub.min()}, {dC_sub.max()}]  "
              f"δC* {'REACHABLE' if dC_sub.min() <= dC_star <= dC_sub.max() else 'UNREACHABLE'}")

def test_extreme_dC_pairs(N=20000):
    """
    The equation says: high δC → low δH (in high-δL regime).
    Search for pairs with MAXIMUM δC in high-δL regime.
    These should have the LOWEST δH.
    """
    print(f"\n--- TEST 2: EXTREME δC SEARCH (N={N}) ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        dL,dC,dH = measure_all(Wn,Wf)
        data.append((dL,dC,dH))

    dL=np.array([d[0] for d in data])
    dC=np.array([d[1] for d in data])
    dH=np.array([d[2] for d in data])

    # High δL regime
    mask_highL = dL >= np.percentile(dL, 75)
    dC_h = dC[mask_highL]; dH_h = dH[mask_highL]

    # Sort by δC (descending) within high-δL
    order = np.argsort(-dC_h)

    print(f"High-δL regime (N={mask_highL.sum()}):")
    for pct_label, n_take in [("Top 1% δC", max(1, len(order)//100)),
                               ("Top 5% δC", max(1, len(order)//20)),
                               ("Top 10% δC", max(1, len(order)//10)),
                               ("Top 25% δC", len(order)//4),
                               ("All", len(order))]:
        subset = order[:n_take]
        print(f"  {pct_label:>12}: N={n_take:>5}, E[δC]={dC_h[subset].mean():.1f}, "
              f"E[δH]={dH_h[subset].mean():.2f}, min(δH)={dH_h[subset].min()}")

    # Low δL regime
    mask_lowL = dL <= np.percentile(dL, 25)
    dC_l = dC[mask_lowL]; dH_l = dH[mask_lowL]
    order_l = np.argsort(dC_l)  # Low δC for low-δL (positive corr)

    print(f"\nLow-δL regime (N={mask_lowL.sum()}):")
    for pct_label, n_take in [("Bottom 1% δC", max(1,len(order_l)//100)),
                               ("Bottom 5% δC", max(1,len(order_l)//20)),
                               ("Bottom 10% δC", max(1,len(order_l)//10)),
                               ("All", len(order_l))]:
        subset = order_l[:n_take]
        print(f"  {pct_label:>14}: N={n_take:>5}, E[δC]={dC_l[subset].mean():.1f}, "
              f"E[δH]={dH_l[subset].mean():.2f}, min(δH)={dH_l[subset].min()}")

    # OVERALL best by combined score
    # Score = δH (lower is better)
    overall_best_idx = np.argmin(dH)
    print(f"\nOverall best: δL={dL[overall_best_idx]}, δC={dC[overall_best_idx]}, "
          f"δH={dH[overall_best_idx]}")

    # Best in high-δL+high-δC regime
    combined = mask_highL & (dC >= np.percentile(dC[mask_highL], 90))
    if combined.sum() > 0:
        best_combined = np.argmin(dH[combined])
        dH_combined = dH[combined]
        print(f"Best (highL+highC): N={combined.sum()}, E[δH]={dH_combined.mean():.2f}, "
              f"min(δH)={dH_combined.min()}")

def test_per_bit_regression(N=10000):
    """
    The regression δH = f(δL, δC) is over TOTAL Hamming weights.
    But what about PER-BIT regression?

    For each output bit i: P(bit_i flips) = f(δL, δC)?
    If some bits have STRONG dependence → targeted partial collision.
    """
    print(f"\n--- TEST 3: PER-BIT REGRESSION ---")

    # Collect bit-level data
    dL_list = []; dC_list = []
    bit_flips = np.zeros((N, 256))

    for idx in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        Ln=xor_compress(Wn); Lf=xor_compress(Wf)

        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
        dL_list.append(dL); dC_list.append(dC)

        for w in range(8):
            d = Hn[w] ^ Hf[w]
            for b in range(32):
                bit_flips[idx, w*32+b] = (d >> b) & 1

    dL = np.array(dL_list); dC = np.array(dC_list)

    # For each bit: regress flip_probability on (δL, δC)
    # In high-δL regime
    mask = dL >= np.percentile(dL, 75)
    dC_h = dC[mask]
    flips_h = bit_flips[mask]

    # Per-bit correlation with δC in high-δL regime
    bit_corrs = []
    for bit_idx in range(256):
        c = np.corrcoef(dC_h, flips_h[:, bit_idx])[0,1]
        w = bit_idx // 32; b = bit_idx % 32
        bit_corrs.append((abs(c), c, w, b))

    bit_corrs.sort(reverse=True)

    threshold = 3 / np.sqrt(mask.sum())
    significant = [bc for bc in bit_corrs if bc[0] > threshold]

    print(f"Significant bits (|corr| > {threshold:.4f}): {len(significant)}/256")
    print(f"Expected by chance: ~{256*0.003:.1f}")

    if len(significant) > 256 * 0.01:
        print(f"*** {len(significant)} significant — MORE than expected! ***")
        print(f"\nTop 10 bits:")
        for absC, c, w, b in bit_corrs[:10]:
            branch = "a" if w < 4 else "e"
            print(f"  H[{w}]({branch}) bit {b:>2}: corr(δC, flip) = {c:+.6f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 44: SOLVE SIMPSON'S EQUATION")
    print("="*60)

    test_regression_equation(12000)
    test_extreme_dC_pairs(15000)
    test_per_bit_regression(8000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
