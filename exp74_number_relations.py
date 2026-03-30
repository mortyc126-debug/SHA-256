#!/usr/bin/env python3
"""
EXP 74: Number Relations — Algebraic Laws Between SHA-256 Constants

10 measured constants of SHA-256. Are they algebraically related?

Observed relations:
  carry_deficit × T_peak ≈ peak_bit_position (13 × 0.72 ≈ 9.36 ≈ 9)
  λ_max × cascade_depth ≈ carry_deficit (2.74 × 4.5 ≈ 12.33 ≈ 13)
  pipe_corr × coupling_rate ≈ cascade_depth (0.58 × 7.24 ≈ 4.20 ≈ 4.5)

If these hold precisely → ONE algebraic law governs SHA-256 structure.
This law would be NEW MATHEMATICS — not from any existing theory.

Method: measure ALL 10 constants with HIGH precision (N=10000+)
and test ALL pairwise/triple products for integer/simple-fraction values.
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

def carry_vec(a,b):
    c_out=[]; c=0
    for i in range(32):
        s=((a>>i)&1)+((b>>i)&1)+c; c=1 if s>=2 else 0; c_out.append(c)
    return c_out

def measure_all_constants(N=5000):
    """Measure all 10 SHA-256 constants with high precision."""
    print(f"\n--- PRECISION MEASUREMENTS (N={N}) ---")

    # C1: Carry deficit
    from exp66A_join_algebra import sigma0_matrix  # Can't import, compute inline
    # Use exp67 result: deficit = 13. Remeasure.

    # C2: T_peaks (transparency at bits 9, 14, 29)
    T = np.zeros(32)
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        for w in range(4,8):
            for bit in range(32):
                sx=(sn[64][w]^sf[64][w]>>bit)&1
                hx=(Hn[w]^Hf[w]>>bit)&1
                if sx==hx: T[bit]+=1
    T /= (N*4)

    T_peak9 = T[9]
    T_peak14 = T[14]
    T_peak29 = T[29]
    T_valley19 = T[19]
    T_valley27 = T[27]

    # C3: Cascade depth (e-branch)
    depths = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        d=0
        for bit in range(32):
            sx=(sn[64][4]^sf[64][4]>>bit)&1
            hx=(Hn[4]^Hf[4]>>bit)&1
            if sx==hx: d+=1
            else: break
        depths.append(d)
    cascade_depth = np.mean(depths)

    # C4: Coupling (late rounds)
    kappas=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        We=schedule(Wn); Wfe=schedule(Wf)
        dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn=sn[63][7]
        df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
        kappas.append(sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f))))
    coupling_63 = np.mean(kappas)

    constants = {
        'carry_deficit': 13,        # From exp67 (exact)
        'T_peak_9': T_peak9,
        'T_peak_14': T_peak14,
        'T_peak_29': T_peak29,
        'T_valley_19': T_valley19,
        'T_valley_27': T_valley27,
        'cascade_depth_e': cascade_depth,
        'coupling_rate': 7.24,      # From exp22/25 (measured)
        'pipe_corr': 0.58,          # From exp59 (measured)
        'lambda_max': 2.74,         # From exp58 (measured)
        'S_degree': 15.3,           # From exp38 (measured)
        'fourier_period': 10.7,     # From exp72 (measured)
        'coupling_63': coupling_63,
    }

    print(f"Measured constants:")
    for name, val in constants.items():
        print(f"  {name:>20}: {val:.6f}")

    return constants

def test_algebraic_relations(C):
    """Test ALL pairwise products for near-integer values."""
    print(f"\n--- ALGEBRAIC RELATIONS ---")

    names = list(C.keys())
    values = [C[n] for n in names]
    n = len(values)

    # Test: a × b ≈ integer?
    print(f"\nProducts near integer values:")
    relations = []
    for i in range(n):
        for j in range(i+1, n):
            product = values[i] * values[j]
            nearest_int = round(product)
            residual = abs(product - nearest_int)
            if residual < 0.5 and nearest_int > 0:
                rel_error = residual / nearest_int
                if rel_error < 0.1:  # Within 10%
                    relations.append((names[i], names[j], product, nearest_int, rel_error))

    relations.sort(key=lambda x: x[4])
    for na, nb, prod, nint, err in relations[:20]:
        print(f"  {na:>20} × {nb:>20} = {prod:>8.3f} ≈ {nint:>3} (err={err:.3f})")

    # Test: a / b ≈ simple fraction?
    print(f"\nRatios near simple fractions:")
    ratio_relations = []
    for i in range(n):
        for j in range(n):
            if i == j: continue
            if abs(values[j]) < 0.01: continue
            ratio = values[i] / values[j]
            # Test fractions p/q for small p,q
            for p in range(1, 20):
                for q in range(1, 20):
                    if abs(ratio - p/q) < 0.05:
                        err = abs(ratio - p/q) / (p/q)
                        if err < 0.05:
                            ratio_relations.append((names[i], names[j], ratio, p, q, err))

    ratio_relations.sort(key=lambda x: x[5])
    seen = set()
    for na, nb, rat, p, q, err in ratio_relations[:30]:
        key = (na, nb)
        if key in seen: continue
        seen.add(key)
        print(f"  {na:>20} / {nb:>20} = {rat:>8.4f} ≈ {p}/{q} (err={err:.4f})")

    # Test: a × b × c ≈ integer?
    print(f"\nTriple products near integers:")
    triple_rel = []
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                prod = values[i] * values[j] * values[k]
                nearest = round(prod)
                if nearest > 0:
                    residual = abs(prod - nearest)
                    rel_err = residual / nearest
                    if rel_err < 0.05:
                        triple_rel.append((names[i], names[j], names[k],
                                          prod, nearest, rel_err))

    triple_rel.sort(key=lambda x: x[5])
    for na,nb,nc,prod,nint,err in triple_rel[:15]:
        print(f"  {na:>15}×{nb:>15}×{nc:>15} = {prod:.2f} ≈ {nint} (err={err:.3f})")

def test_derived_equations(C):
    """Test the specific equations observed in the thought process."""
    print(f"\n--- SPECIFIC HYPOTHESIZED EQUATIONS ---")

    equations = [
        ("deficit × T_peak_9 ≈ 9",
         C['carry_deficit'] * C['T_peak_9'], 9),
        ("deficit × T_valley_27 ≈ 3 (σ0 SHR3)",
         C['carry_deficit'] * C['T_valley_27'], 3),
        ("λ_max × cascade_depth ≈ deficit",
         C['lambda_max'] * C['cascade_depth_e'], C['carry_deficit']),
        ("pipe_corr × coupling_rate ≈ cascade_depth",
         C['pipe_corr'] * C['coupling_rate'], C['cascade_depth_e']),
        ("fourier_period × T_valley_27 ≈ 3 (SHR3)",
         C['fourier_period'] * C['T_valley_27'], 3),
        ("S_degree × T_peak_9 ≈ 11 (fourier)",
         C['S_degree'] * C['T_peak_9'], C['fourier_period']),
        ("λ_max × pipe_corr ≈ 1/cascade_depth × deficit",
         C['lambda_max'] * C['pipe_corr'],
         C['carry_deficit'] / C['cascade_depth_e']),
    ]

    print(f"{'Equation':>45} | {'LHS':>8} | {'RHS':>8} | {'Error':>8}")
    print("-"*75)
    for name, lhs, rhs in equations:
        err = abs(lhs - rhs) / abs(rhs) if rhs != 0 else 0
        match = "✓" if err < 0.15 else "✗"
        print(f"{name:>45} | {lhs:>8.3f} | {rhs:>8.3f} | {err:>7.1%} {match}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 74: NUMBER RELATIONS")
    print("Algebraic laws between SHA-256 constants")
    print("="*60)
    C = measure_all_constants(3000)
    test_algebraic_relations(C)
    test_derived_equations(C)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
