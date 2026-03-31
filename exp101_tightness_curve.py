#!/usr/bin/env python3
"""
EXP 101: Tightness Curve — corr(δα, δC) vs δH, precise

From exp100: corr(HW(δα), HW(δC)) grows monotonically as δH decreases.
  δH=135-160: 0.190
  δH=105-115: 0.459

This is the GRADIENT in ★-space. If monotonic → navigable path.
If accelerating → collision at finite extrapolation.

Measure tightness curve with FINE bins to determine SHAPE:
  Linear → collision at corr extrapolation
  Quadratic → faster convergence
  Logarithmic → slow saturation (asymptotic)

Also: is this tightness MESSAGE-PREDICTABLE?
(Not just a consequence of δH, but independently measurable?)
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def decompose(W0, W1):
    Wn, Wf, _, sn, sf = wang_cascade(W0, W1)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    da = [sn[64][w] ^ sf[64][w] for w in range(8)]
    dc = [((IV[w]+sn[64][w])&MASK)^(IV[w]^sn[64][w]) ^
          ((IV[w]+sf[64][w])&MASK)^(IV[w]^sf[64][w]) for w in range(8)]
    hw_da = sum(hw(da[w]) for w in range(8))
    hw_dc = sum(hw(dc[w]) for w in range(8))
    hw_dh = sum(hw(Hn[w]^Hf[w]) for w in range(8))
    match = sum(32 - hw(da[w] ^ dc[w]) for w in range(8))
    return hw_da, hw_dc, hw_dh, match

def test_tightness_curve(N=20000):
    """Precise tightness curve with fine bins."""
    print(f"\n--- TIGHTNESS CURVE (N={N}) ---")

    data = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        hw_da, hw_dc, hw_dh, match = decompose(W0, W1)
        data.append((hw_da, hw_dc, hw_dh, match))

    da_arr = np.array([d[0] for d in data])
    dc_arr = np.array([d[1] for d in data])
    dh_arr = np.array([d[2] for d in data])
    match_arr = np.array([d[3] for d in data])

    # Fine bins of 5
    print(f"{'δH bin':>12} | {'N':>6} | {'corr(HW)':>9} | {'match_rate':>10} | {'E[δα]':>7} | {'E[δC]':>7}")
    print("-" * 65)

    corrs = []; centers = []
    for lo in range(90, 160, 5):
        hi = lo + 5
        mask = (dh_arr >= lo) & (dh_arr < hi)
        n = mask.sum()
        if n < 30:
            continue

        c = np.corrcoef(da_arr[mask], dc_arr[mask])[0, 1]
        mr = match_arr[mask].mean() / 256
        eda = da_arr[mask].mean()
        edc = dc_arr[mask].mean()

        corrs.append(c); centers.append(lo + 2.5)
        print(f"{'δH='+str(lo)+'-'+str(hi):>12} | {n:>6} | {c:>+9.4f} | {mr:>10.4f} | {eda:>7.1f} | {edc:>7.1f}")

    # Fit: corr = f(δH)
    if len(corrs) > 3:
        ca = np.array(corrs); xa = np.array(centers)

        # Linear fit
        slope, intercept = np.polyfit(xa, ca, 1)
        # Quadratic fit
        coeffs2 = np.polyfit(xa, ca, 2)

        # Extrapolate to δH=0
        linear_at_0 = intercept  # slope × 0 + intercept
        quad_at_0 = coeffs2[2]  # a×0² + b×0 + c

        print(f"\nFit: corr = {slope:+.6f} × δH + {intercept:.4f}")
        print(f"  Linear extrapolation to δH=0: corr = {linear_at_0:.4f}")
        print(f"  At δH=0: corr = {intercept:.4f}")
        print(f"")
        print(f"Quadratic: corr = {coeffs2[0]:.8f}δH² + {coeffs2[1]:.6f}δH + {coeffs2[2]:.4f}")
        print(f"  Quad extrapolation to δH=0: corr = {quad_at_0:.4f}")

        # What δH gives corr = 1.0?
        # Linear: 1.0 = slope × δH + intercept → δH = (1.0 - intercept) / slope
        if slope != 0:
            dh_at_corr1 = (1.0 - intercept) / slope
            print(f"\n  Linear: corr=1.0 at δH = {dh_at_corr1:.1f}")
            if dh_at_corr1 > 0:
                print(f"  *** corr reaches 1.0 at POSITIVE δH = {dh_at_corr1:.0f} ***")
                print(f"  This means: collision condition satisfied when δH ≈ {dh_at_corr1:.0f}")
            else:
                print(f"  corr=1.0 at NEGATIVE δH → never reaches 1.0 naturally")

def test_tightness_per_word(N=10000):
    """Per-word tightness: which words have strongest self-reference?"""
    print(f"\n--- PER-WORD TIGHTNESS ---")

    data = {w: {'da': [], 'dc': [], 'dh': []} for w in range(8)}

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, sn, sf = wang_cascade(W0, W1)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        for w in range(8):
            da_w = hw(sn[64][w] ^ sf[64][w])
            carry_n = ((IV[w]+sn[64][w])&MASK) ^ (IV[w]^sn[64][w])
            carry_f = ((IV[w]+sf[64][w])&MASK) ^ (IV[w]^sf[64][w])
            dc_w = hw(carry_n ^ carry_f)
            dh_w = hw(Hn[w] ^ Hf[w])

            data[w]['da'].append(da_w)
            data[w]['dc'].append(dc_w)
            data[w]['dh'].append(dh_w)

    print(f"{'Word':>6} | {'corr(δα,δC)':>11} | {'E[δα]':>7} | {'E[δC]':>7}")
    print("-" * 40)

    for w in range(8):
        da = np.array(data[w]['da'])
        dc = np.array(data[w]['dc'])
        c = np.corrcoef(da, dc)[0, 1]
        branch = "a" if w < 4 else "e"
        print(f"H[{w}]({branch}) | {c:>+11.6f} | {da.mean():>7.2f} | {dc.mean():>7.2f}")

def test_independent_tightness(N=10000):
    """
    KEY: can tightness be measured WITHOUT computing δH?
    If yes → independent predictor → navigable.

    Tightness ≈ corr(HW(δα), HW(δC)). But this requires BOTH messages.
    What about: tightness from SINGLE message properties?
    """
    print(f"\n--- INDEPENDENT TIGHTNESS PREDICTOR ---")

    # For each pair: measure tightness AND single-message properties
    tightnesses = []; dHs = []; hw_w0s = []; k8s = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        hw_da, hw_dc, hw_dh, match = decompose(W0, W1)

        # Tightness proxy: |HW(δα) - HW(δC)| (smaller = tighter)
        tightness = abs(hw_da - hw_dc)
        tightnesses.append(tightness)
        dHs.append(hw_dh)
        hw_w0s.append(hw(W0))

    ta = np.array(tightnesses); da = np.array(dHs)

    c_tight_dh = np.corrcoef(ta, da)[0, 1]
    print(f"corr(|HW(δα)-HW(δC)|, δH) = {c_tight_dh:+.6f}")

    # Low tightness (small |da-dc|) → lower δH?
    low_tight = da[ta < np.percentile(ta, 25)]
    high_tight = da[ta > np.percentile(ta, 75)]
    print(f"Low |δα-δC| (tight): E[δH]={low_tight.mean():.2f}")
    print(f"High |δα-δC| (loose): E[δH]={high_tight.mean():.2f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 101: TIGHTNESS CURVE")
    print("★-algebra self-reference gradient")
    print("=" * 60)

    test_tightness_curve(15000)
    test_tightness_per_word(6000)
    test_independent_tightness(8000)

if __name__ == "__main__":
    main()
