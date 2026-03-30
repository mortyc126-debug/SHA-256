#!/usr/bin/env python3
"""
EXP 69: Resonant Receivers — Nonlinear Signal Amplifiers

5 real signals (Z>3σ each), interpreted as "weak" through LINEAR lens.
What if the signals pass through NONLINEAR amplifier inside SHA-256?

Strategy: for each signal, search for NONLINEAR function f(signal)
that maximizes corr(f(signal), δH).

Not predefined f. LEARNED f from data (decision tree, polynomial, etc.)

If corr(f_optimal, δH) >> corr(signal, δH) → the signal is NOT weak,
our RECEIVER was wrong.
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

def carry_vec(a, b):
    c_out=[]; c=0
    for i in range(32):
        s=((a>>i)&1)+((b>>i)&1)+c; c=1 if s>=2 else 0; c_out.append(c)
    return c_out

def collect_all_signals(N=5000):
    """Collect all 5 signals + δH for N Wang pairs."""
    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn,sf = wang_cascade(W0,W1)
        We=schedule(Wn); Wfe=schedule(Wf)

        # Signal 1: coupling κ_63
        dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn=sn[63][7]
        df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
        kappa = sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

        # Signal 2: δL (XOR hash diff)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        Ln=xor_compress(Wn); Lf=xor_compress(Wf)
        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))

        # Signal 3: δC (carry component diff)
        dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))

        # Signal 4: cascade depth (bit 0 carry-free)
        depth = 0
        for bit in range(32):
            state_xor = sn[64][0] ^ sf[64][0]
            hash_xor = Hn[0] ^ Hf[0]
            if ((state_xor>>bit)&1) == ((hash_xor>>bit)&1):
                depth += 1
            else:
                break

        # Signal 5: late κ (rounds 56-63)
        late_k = 0
        for r in range(56, 64):
            d2=sn[r][3];e2=sn[r][4];f2=sn[r][5];g2=sn[r][6];h2=sn[r][7]
            d2f=sf[r][3];e2f=sf[r][4];f2f=sf[r][5];g2f=sf[r][6];h2f=sf[r][7]
            T2n=(h2+sigma1(e2)+ch(e2,f2,g2)+K[r]+We[r])&MASK
            T2f=(h2f+sigma1(e2f)+ch(e2f,f2f,g2f)+K[r]+Wfe[r])&MASK
            late_k += sum(a^b for a,b in zip(carry_vec(d2,T2n),carry_vec(d2f,T2f)))

        # Target
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        data.append([kappa, dL, dC, depth, late_k, dH])

    return np.array(data)

def find_optimal_nonlinear(X, y, signal_name):
    """
    Find nonlinear function f(X) that maximizes |corr(f(X), y)|.

    Methods:
    1. Polynomial features (x, x², x³, x⁴)
    2. Threshold features (x < t for various t)
    3. Interaction features (x_i · x_j)
    4. Optimal linear combination of all above
    """
    n = len(y)
    features = {}

    # Raw signals
    for i in range(X.shape[1]):
        features[f'x{i}'] = X[:, i]

    # Squared
    for i in range(X.shape[1]):
        features[f'x{i}^2'] = X[:, i]**2

    # Cubed
    for i in range(X.shape[1]):
        features[f'x{i}^3'] = X[:, i]**3

    # Thresholds (at percentiles)
    for i in range(X.shape[1]):
        for p in [10, 25, 50, 75, 90]:
            thresh = np.percentile(X[:, i], p)
            features[f'x{i}<P{p}'] = (X[:, i] < thresh).astype(float)

    # Pairwise products
    for i in range(X.shape[1]):
        for j in range(i+1, X.shape[1]):
            features[f'x{i}*x{j}'] = X[:, i] * X[:, j]

    # Log (shifted to avoid log(0))
    for i in range(X.shape[1]):
        shifted = X[:, i] - X[:, i].min() + 1
        features[f'log(x{i})'] = np.log(shifted)

    # Absolute deviation from mean
    for i in range(X.shape[1]):
        features[f'|x{i}-mean|'] = np.abs(X[:, i] - X[:, i].mean())

    # Evaluate each feature's correlation with target
    results = []
    for name, feat in features.items():
        if feat.std() == 0: continue
        c = np.corrcoef(feat, y)[0, 1]
        if not np.isnan(c):
            results.append((abs(c), c, name))

    results.sort(reverse=True)

    # Print top 20
    print(f"\n  Top 20 nonlinear features correlated with δH:")
    threshold = 3 / np.sqrt(n)
    n_significant = 0
    for absC, c, name in results[:20]:
        sig = "***" if absC > threshold else ""
        if absC > threshold: n_significant += 1
        print(f"    {name:>20}: corr={c:+.6f} {sig}")

    print(f"\n  Significant features: {n_significant}")
    print(f"  Best: {results[0][2]} with |corr|={results[0][0]:.6f}")
    print(f"  Linear baseline (raw signals): max |corr|={max(abs(np.corrcoef(X[:,i],y)[0,1]) for i in range(X.shape[1])):.6f}")

    # Optimal LINEAR COMBINATION of top features
    top_feats = [features[name] for _, _, name in results[:30] if features[name].std()>0]
    if top_feats:
        F = np.column_stack(top_feats)
        # Least squares: y ≈ F·β
        try:
            beta = np.linalg.lstsq(F, y, rcond=None)[0]
            y_pred = F @ beta
            r2 = 1 - np.var(y - y_pred) / np.var(y)
            corr_opt = np.corrcoef(y_pred, y)[0, 1]
            print(f"\n  Optimal combination of top 30 features:")
            print(f"    R² = {r2:.6f}")
            print(f"    corr(f_optimal, δH) = {corr_opt:+.6f}")

            # Compare with random baseline
            random_r2 = []
            for _ in range(50):
                y_rand = np.random.permutation(y)
                beta_r = np.linalg.lstsq(F, y_rand, rcond=None)[0]
                y_pred_r = F @ beta_r
                random_r2.append(1 - np.var(y_rand - y_pred_r) / np.var(y_rand))

            random_mean = np.mean(random_r2)
            z_score = (r2 - random_mean) / np.std(random_r2) if np.std(random_r2)>0 else 0
            print(f"    Random R²: {random_mean:.6f}")
            print(f"    Z-score: {z_score:.2f}")

            if z_score > 3:
                print(f"    *** NONLINEAR SIGNAL AMPLIFIED! Z={z_score:.1f} ***")
        except:
            pass

    return results

def main():
    random.seed(42)
    N = 5000
    print("="*60)
    print(f"EXP 69: RESONANT RECEIVERS (N={N})")
    print("="*60)

    print("\nCollecting all 5 signals...")
    data = collect_all_signals(N)

    X = data[:, :5]  # 5 signals
    y = data[:, 5]   # δH

    signal_names = ['κ_63', 'δL', 'δC', 'cascade_depth', 'late_κ']

    # Linear baseline
    print("\n--- LINEAR BASELINE ---")
    for i, name in enumerate(signal_names):
        c = np.corrcoef(X[:, i], y)[0, 1]
        print(f"  corr({name}, δH) = {c:+.6f}")

    # Nonlinear search
    print("\n--- NONLINEAR RECEIVER SEARCH ---")
    results = find_optimal_nonlinear(X, y, "all_signals")

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
