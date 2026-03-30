#!/usr/bin/env python3
"""
EXP 23: Coupling-Optimized Wang Cascade

Standard Wang optimizes De=0 (round function zeros).
NEW: Optimize for min(late_κ) — minimize carry coupling at rounds 56-63.

Our tools: Wang cascade + Carry Coupling Field + Selective DWs.
The 3-bit effect (exp19) comes from naturally low-κ pairs.
Can we ENGINEER low-κ pairs by choosing DWs?

Strategy: Wang cascade gives 14 deterministic DWs (for De=0).
But DW[0] is free (=1 by convention). What if DW[0] varies?
Also: W[0], W[1] are free search variables.
Optimize (W0, W1, DW0) to minimize late_κ while keeping De3..De16≈0.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    c_out = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        c_out.append(c)
    return c_out

def late_kappa(Wn, Wf, r_start=56, r_end=64):
    """Sum of κ over late rounds."""
    sn = sha256_rounds(Wn, r_end)
    sf = sha256_rounds(Wf, r_end)
    We = schedule(Wn); Wfe = schedule(Wf)
    total = 0
    for r in range(r_start, r_end):
        dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
        df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+We[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wfe[r])&MASK
        cv_n=carry_vec(dn,T1n); cv_f=carry_vec(df,T1f)
        total += sum(a^b for a,b in zip(cv_n,cv_f))
    return total

def coupling_optimized_wang(W0, W1, DW0=1):
    """Standard Wang cascade, returns (Wn, Wf, late_κ, δH)."""
    Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1, DW0)
    lk = late_kappa(Wn, Wf)
    H_n = sha256_compress(Wn); H_f = sha256_compress(Wf)
    dH = sum(hw(H_n[i]^H_f[i]) for i in range(8))
    return Wn, Wf, DWs, lk, dH

def test_dw0_optimization(N=2000):
    """Test: does varying DW0 affect late_κ?"""
    print("\n--- TEST 1: DW0 VARIATION → late_κ ---")

    results = {}
    for dw0 in [1, 2, 4, 8, 0x100, 0x10000, 0x80000000, 0x12345]:
        lks = []; dhs = []
        for _ in range(N//8):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            try:
                _, _, _, lk, dH = coupling_optimized_wang(W0, W1, dw0)
                lks.append(lk); dhs.append(dH)
            except:
                pass
        if lks:
            results[dw0] = (np.mean(lks), np.mean(dhs))
            print(f"  DW0=0x{dw0:08x}: late_κ={np.mean(lks):.2f}, δH={np.mean(dhs):.2f}")

    return results

def test_w0w1_search(N=5000):
    """Search (W0, W1) space for minimum late_κ."""
    print("\n--- TEST 2: (W0,W1) SEARCH FOR MIN late_κ ---")

    best_lk = 999; best_dH = 256; best_pair = None
    all_lk = []; all_dH = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        try:
            Wn, Wf, DWs, lk, dH = coupling_optimized_wang(W0, W1)
            all_lk.append(lk); all_dH.append(dH)
            if lk < best_lk:
                best_lk = lk; best_dH = dH
                best_pair = (W0, W1, Wn, Wf, DWs)
        except:
            pass

    lk_arr = np.array(all_lk); dh_arr = np.array(all_dH)
    print(f"late_κ: mean={lk_arr.mean():.2f}, std={lk_arr.std():.2f}, min={lk_arr.min()}")
    print(f"Best: late_κ={best_lk}, δH={best_dH}")

    corr = np.corrcoef(lk_arr, dh_arr)[0,1]
    print(f"corr(late_κ, δH): {corr:+.6f}")

    # Top 1% by late_κ
    p1 = np.percentile(lk_arr, 1)
    top1_dh = dh_arr[lk_arr <= p1]
    print(f"Top 1% (κ≤{p1:.0f}): E[δH]={top1_dh.mean():.2f}, min={top1_dh.min()}, N={len(top1_dh)}")

    # Top 0.1%
    p01 = np.percentile(lk_arr, 0.1)
    top01_dh = dh_arr[lk_arr <= p01]
    if len(top01_dh) > 0:
        print(f"Top 0.1% (κ≤{p01:.0f}): E[δH]={top01_dh.mean():.2f}, min={top01_dh.min()}, N={len(top01_dh)}")

    return best_pair, lk_arr, dh_arr

def test_hill_climb_coupling(N=500):
    """Hill-climb in (W0,W1) space to minimize late_κ, then measure δH."""
    print("\n--- TEST 3: HILL-CLIMB COUPLING OPTIMIZATION ---")

    results = []
    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        try:
            _, _, _, lk_start, dH_start = coupling_optimized_wang(W0, W1)
        except:
            continue

        best_W0, best_W1 = W0, W1
        best_lk = lk_start

        # Hill-climb: flip bits in W0 and W1
        for step in range(100):
            if random.random() < 0.5:
                trial_W0 = best_W0 ^ (1 << random.randint(0,31))
                trial_W1 = best_W1
            else:
                trial_W0 = best_W0
                trial_W1 = best_W1 ^ (1 << random.randint(0,31))

            try:
                _, _, _, lk, _ = coupling_optimized_wang(trial_W0, trial_W1)
                if lk < best_lk:
                    best_lk = lk
                    best_W0, best_W1 = trial_W0, trial_W1
            except:
                pass

        # Measure final δH
        try:
            _, _, _, final_lk, final_dH = coupling_optimized_wang(best_W0, best_W1)
            results.append((lk_start, final_lk, dH_start, final_dH))
        except:
            pass

    if results:
        starts_lk = [r[0] for r in results]
        finals_lk = [r[1] for r in results]
        starts_dH = [r[2] for r in results]
        finals_dH = [r[3] for r in results]

        print(f"Before HC: late_κ={np.mean(starts_lk):.2f}, δH={np.mean(starts_dH):.2f}")
        print(f"After HC:  late_κ={np.mean(finals_lk):.2f}, δH={np.mean(finals_dH):.2f}")
        print(f"κ reduction: {np.mean(starts_lk)-np.mean(finals_lk):.2f}")
        print(f"δH change: {np.mean(finals_dH)-np.mean(starts_dH):+.2f}")

        # Best results
        results.sort(key=lambda x: x[1])
        print(f"\nTop 10 by coupling:")
        for slk, flk, sdH, fdH in results[:10]:
            print(f"  κ: {slk}→{flk}, δH: {sdH}→{fdH}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 23: COUPLING-OPTIMIZED WANG CASCADE")
    print("="*60)
    test_dw0_optimization(1600)
    test_w0w1_search(5000)
    test_hill_climb_coupling(300)

if __name__ == "__main__":
    main()
