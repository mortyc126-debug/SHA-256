#!/usr/bin/env python3
"""
EXP 70: Unified Signal — One Structure, Five Windows

5 signals are NOT independent weak signals.
They are 5 views of ONE structure:

"E-branch low bits at late rounds preserve carry transparency
 through pipe-pair degeneracy, visible conditionally on XOR"

Components:
  WHERE:  e-branch (H[4..7]), bits 0-4, rounds 56-63
  WHAT:   carry transparency (hash = XOR part, no carry distortion)
  WHY:    pipe pair eigenvalue degeneracy (gap 0.04)
  HOW:    conditional on δL (Simpson), measured by κ (coupling)

TEST: measure ALL 5 signals SIMULTANEOUSLY in the SPECIFIC subspace
defined above. If corr jumps dramatically → unified structure found.
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

def unified_measurement(Wn, Wf):
    """
    Measure the UNIFIED structure in its native subspace:
    e-branch, low bits, late rounds, conditional on XOR.
    """
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    We = schedule(Wn); Wfe = schedule(Wf)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    Ln = xor_compress(Wn); Lf = xor_compress(Wf)

    # SUBSPACE: e-branch (words 4-7), bits 0-4
    LOW_MASK = 0x1F  # bits 0-4

    # Component A: δH restricted to subspace
    dH_sub = sum(hw((Hn[w]^Hf[w]) & LOW_MASK) for w in range(4, 8))
    dH_full = sum(hw(Hn[w]^Hf[w]) for w in range(8))

    # Component B: carry transparency in subspace
    # = how many of the subspace bits are carry-free in feedforward?
    carry_free = 0
    for w in range(4, 8):
        state_xor = sn[64][w] ^ sf[64][w]
        hash_xor = Hn[w] ^ Hf[w]
        for bit in range(5):  # bits 0-4
            if ((state_xor >> bit) & 1) == ((hash_xor >> bit) & 1):
                carry_free += 1

    # Component C: coupling at r=63 restricted to e-branch
    kappa_e = 0
    for r in range(60, 64):
        dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
        df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+We[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wfe[r])&MASK
        cvn = carry_vec(dn, T1n); cvf = carry_vec(df, T1f)
        kappa_e += sum(a^b for a,b in zip(cvn[:5], cvf[:5]))  # Only low bits!

    # Component D: δL in subspace
    dL_sub = sum(hw((Ln[w]^Lf[w]) & LOW_MASK) for w in range(4, 8))

    # Component E: δC in subspace
    dC_sub = sum(hw(((Hn[w]^Ln[w])^(Hf[w]^Lf[w])) & LOW_MASK) for w in range(4, 8))

    return {
        'dH_sub': dH_sub,       # Target: subspace δH (20 bits max)
        'dH_full': dH_full,     # Full δH for reference
        'carry_free': carry_free, # Carry transparency in subspace
        'kappa_e_low': kappa_e, # Coupling in subspace
        'dL_sub': dL_sub,       # XOR diff in subspace
        'dC_sub': dC_sub,       # Carry diff in subspace
    }

def test_unified_signal(N=5000):
    """Measure unified structure and its correlation with δH."""
    print(f"\n--- UNIFIED SIGNAL (N={N}) ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        m = unified_measurement(Wn, Wf)
        data.append(m)

    dH_s = np.array([d['dH_sub'] for d in data])
    dH_f = np.array([d['dH_full'] for d in data])
    cf = np.array([d['carry_free'] for d in data])
    ke = np.array([d['kappa_e_low'] for d in data])
    dL = np.array([d['dL_sub'] for d in data])
    dC = np.array([d['dC_sub'] for d in data])

    threshold = 3/np.sqrt(N)

    print(f"Subspace δH (e-branch bits 0-4): E={dH_s.mean():.2f}/20")
    print(f"Full δH: E={dH_f.mean():.2f}/256")

    # Correlations with FULL δH
    print(f"\nCorrelations with FULL δH (threshold={threshold:.4f}):")
    for name, arr in [('carry_free', cf), ('κ_e_low', ke),
                       ('δL_sub', dL), ('δC_sub', dC), ('δH_sub', dH_s)]:
        c = np.corrcoef(arr, dH_f)[0, 1]
        sig = "***" if abs(c) > threshold else ""
        print(f"  corr({name:>12}, δH_full) = {c:+.6f} {sig}")

    # Correlations with SUBSPACE δH (potentially stronger)
    print(f"\nCorrelations with SUBSPACE δH:")
    for name, arr in [('carry_free', cf), ('κ_e_low', ke),
                       ('δL_sub', dL), ('δC_sub', dC)]:
        c = np.corrcoef(arr, dH_s)[0, 1]
        sig = "***" if abs(c) > threshold else ""
        print(f"  corr({name:>12}, δH_sub) = {c:+.6f} {sig}")

    # Simpson in subspace: conditional on δL_sub
    print(f"\nSimpson in subspace:")
    med_dL = np.median(dL)
    for label, mask in [("δL_sub < median", dL < med_dL),
                         ("δL_sub > median", dL >= med_dL)]:
        if mask.sum() > 100:
            c_cf = np.corrcoef(cf[mask], dH_f[mask])[0,1]
            c_dC = np.corrcoef(dC[mask], dH_f[mask])[0,1]
            c_ke = np.corrcoef(ke[mask], dH_f[mask])[0,1]
            print(f"  {label}:")
            print(f"    corr(carry_free, δH_full) = {c_cf:+.6f}")
            print(f"    corr(δC_sub, δH_full) = {c_dC:+.6f}")
            print(f"    corr(κ_e_low, δH_full) = {c_ke:+.6f}")

    # COMBINED: all subspace signals → δH
    X = np.column_stack([cf, ke, dL, dC, cf*ke, cf*dL, dC*ke,
                          cf**2, ke**2, dL*dC])
    try:
        beta = np.linalg.lstsq(X, dH_f, rcond=None)[0]
        pred = X @ beta
        r2 = 1 - np.var(dH_f - pred) / np.var(dH_f)
        corr_comb = np.corrcoef(pred, dH_f)[0, 1]

        # Random baseline
        r2_rand = []
        for _ in range(50):
            y_r = np.random.permutation(dH_f)
            b_r = np.linalg.lstsq(X, y_r, rcond=None)[0]
            p_r = X @ b_r
            r2_rand.append(1 - np.var(y_r - p_r) / np.var(y_r))

        z = (r2 - np.mean(r2_rand)) / np.std(r2_rand) if np.std(r2_rand)>0 else 0

        print(f"\nCOMBINED subspace signal:")
        print(f"  R² = {r2:.6f} (random: {np.mean(r2_rand):.6f})")
        print(f"  corr = {corr_comb:+.6f}")
        print(f"  Z = {z:.2f}")

        # Compare with exp69 (full-space): R²=0.015
        print(f"\n  exp69 full-space R² = 0.015")
        print(f"  Subspace R² = {r2:.6f}")
        print(f"  Ratio: {r2/0.015:.2f}×")

        if r2 > 0.015 * 1.5:
            print(f"  *** SUBSPACE CAPTURES MORE SIGNAL THAN FULL SPACE! ***")
    except:
        print("  Combined regression failed")

def test_subspace_vs_fullspace(N=3000):
    """Direct comparison: does the SPECIFIC subspace have more signal?"""
    print(f"\n--- SUBSPACE vs FULLSPACE ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        m = unified_measurement(Wn, Wf)
        data.append(m)

    dH_s = np.array([d['dH_sub'] for d in data])
    dH_f = np.array([d['dH_full'] for d in data])

    # Is subspace δH a BETTER predictor of full δH than expected?
    # Expected: dH_sub ≈ dH_full × (20/256) + noise
    corr_sub_full = np.corrcoef(dH_s, dH_f)[0, 1]
    expected_corr = np.sqrt(20/256)  # If bits independent

    print(f"corr(δH_sub, δH_full) = {corr_sub_full:.6f}")
    print(f"Expected (independent bits): {expected_corr:.6f}")
    print(f"Ratio: {corr_sub_full/expected_corr:.4f}")

    if corr_sub_full > expected_corr * 1.5:
        print(f"*** SUBSPACE is DISPROPORTIONATELY informative! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 70: UNIFIED SIGNAL")
    print("One structure, five windows")
    print("="*60)
    test_unified_signal(4000)
    test_subspace_vs_fullspace(3000)

if __name__ == "__main__":
    main()
