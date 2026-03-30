#!/usr/bin/env python3
"""
EXP 29A: Precision measurement of the 3-bit signal + non-Wang differentials

PART 1: Large-N precision measurement of corr(late_κ, δH).
Does it have a formula? Which output bits carry the signal?

PART 2: Non-Wang differentials. All 27 prior experiments used Wang.
What if corr(late_κ, δH) depends on the DIFFERENTIAL FAMILY?
Test: constant ΔW, random ΔW, structured ΔW, single-word ΔW.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    c_out = []; c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        c_out.append(c)
    return c_out

def late_kappa_detailed(sn, sf, We, Wfe):
    """Per-round and per-word kappa for rounds 56-63."""
    kappas = []
    for r in range(56, 64):
        dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
        df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+We[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wfe[r])&MASK
        cv_n=carry_vec(dn,T1n); cv_f=carry_vec(df,T1f)
        kappas.append(sum(a^b for a,b in zip(cv_n,cv_f)))
    return sum(kappas), kappas

def compute_pair(Wn, Wf):
    """Compute all metrics for a message pair."""
    sn = sha256_rounds(Wn, 64)
    sf = sha256_rounds(Wf, 64)
    We = schedule(Wn); Wfe = schedule(Wf)

    late_k_total, late_k_per_round = late_kappa_detailed(sn, sf, We, Wfe)

    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    dH_per_word = [hw(Hn[i]^Hf[i]) for i in range(8)]
    dH_total = sum(dH_per_word)

    return {
        'late_k': late_k_total,
        'late_k_per_round': late_k_per_round,
        'dH': dH_total,
        'dH_per_word': dH_per_word,
    }

def test_precision_wang(N=10000):
    """Large-N precision measurement with Wang differential."""
    print("\n--- PART 1: PRECISION WANG (N=10000) ---")
    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)
        d = compute_pair(Wn, Wf)
        data.append(d)

    lk = np.array([d['late_k'] for d in data])
    dh = np.array([d['dH'] for d in data])
    dh_pw = np.array([d['dH_per_word'] for d in data])

    corr_total = np.corrcoef(lk, dh)[0,1]
    z_total = corr_total * np.sqrt(N)
    print(f"corr(late_κ, δH) = {corr_total:+.6f} (Z={z_total:.2f}, N={N})")

    # Per-word correlation
    print(f"\nPer-word corr(late_κ, δH_word):")
    for w in range(8):
        c = np.corrcoef(lk, dh_pw[:,w])[0,1]
        branch = "a" if w < 4 else "e"
        sig = " ***" if abs(c) > 3/np.sqrt(N) else ""
        print(f"  H[{w}]({branch}): {c:+.6f}{sig}")

    # Per-round late_κ correlation
    lk_pr = np.array([d['late_k_per_round'] for d in data])
    print(f"\nPer-round corr(κ_r, δH) for r=56..63:")
    for i, r in enumerate(range(56, 64)):
        c = np.corrcoef(lk_pr[:,i], dh)[0,1]
        sig = " ***" if abs(c) > 3/np.sqrt(N) else ""
        print(f"  r={r}: {c:+.6f}{sig}")

    # Quantile analysis
    print(f"\nQuantile analysis:")
    for q in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        thresh = np.percentile(lk, q)
        subset = dh[lk <= thresh]
        if len(subset) > 0:
            print(f"  κ≤P{q:>2} (≤{thresh:.0f}, N={len(subset):>5}): E[δH]={subset.mean():.4f}")

    return data

def test_non_wang_differentials(N=3000):
    """Test coupling signal with NON-Wang differentials."""
    print("\n--- PART 2: NON-WANG DIFFERENTIALS ---")

    diff_types = {
        'wang_dw1': {'desc': 'Wang ΔW0=1 (baseline)'},
        'constant_all': {'desc': 'ΔW = (1,1,...,1)'},
        'single_w0': {'desc': 'ΔW0=1, rest=0 (no cascade)'},
        'single_w15': {'desc': 'ΔW15=1, rest=0'},
        'random_small': {'desc': 'ΔW random HW≤3'},
        'random_large': {'desc': 'ΔW fully random'},
        'xor_single': {'desc': 'XOR flip: W0 ^= 1'},
        'opposite': {'desc': 'ΔW = (1, -1, 1, -1, ...)'},
    }

    for dtype, info in diff_types.items():
        lks = []; dhs = []
        for _ in range(N):
            Wn = random_w16()

            if dtype == 'wang_dw1':
                try:
                    Wn_w, Wf, DWs, _, _ = wang_cascade(Wn[0], Wn[1])
                    d = compute_pair(Wn_w, Wf)
                    lks.append(d['late_k']); dhs.append(d['dH'])
                except: pass
                continue

            elif dtype == 'constant_all':
                Wf = [(w + 1) & MASK for w in Wn]
            elif dtype == 'single_w0':
                Wf = list(Wn); Wf[0] = (Wf[0] + 1) & MASK
            elif dtype == 'single_w15':
                Wf = list(Wn); Wf[15] = (Wf[15] + 1) & MASK
            elif dtype == 'random_small':
                Wf = list(Wn)
                for _ in range(3):
                    w = random.randint(0,15)
                    Wf[w] = (Wf[w] + (1 << random.randint(0,31))) & MASK
            elif dtype == 'random_large':
                Wf = random_w16()
            elif dtype == 'xor_single':
                Wf = list(Wn); Wf[0] ^= 1
            elif dtype == 'opposite':
                Wf = list(Wn)
                for i in range(16):
                    Wf[i] = (Wf[i] + (1 if i%2==0 else MASK)) & MASK

            d = compute_pair(Wn, Wf)
            lks.append(d['late_k']); dhs.append(d['dH'])

        if len(lks) < 100:
            continue

        lk_arr = np.array(lks); dh_arr = np.array(dhs)
        corr = np.corrcoef(lk_arr, dh_arr)[0,1]
        z = corr * np.sqrt(len(lks))

        print(f"  {dtype:>15} | E[κ]={lk_arr.mean():>6.1f} | E[δH]={dh_arr.mean():>6.1f} | "
              f"corr={corr:>+.4f} | Z={z:>+6.1f} | {info['desc']}")

def test_differential_coupling_landscape(N=5000):
    """
    Map the (ΔW, late_κ, δH) landscape.
    Different differentials → different coupling → different δH?
    """
    print("\n--- PART 3: DIFFERENTIAL-COUPLING-δH LANDSCAPE ---")

    # Vary ΔW0 value and measure the coupling-δH relationship
    results = {}
    for dw0 in [1, 0x80000000, 0x55555555, 0xAAAAAAAA, 0xFF, 0xFF00, 0xFFFF0000]:
        lks = []; dhs = []
        for _ in range(N // 7):
            Wn = random_w16()
            Wf = list(Wn)
            Wf[0] = (Wf[0] + dw0) & MASK
            d = compute_pair(Wn, Wf)
            lks.append(d['late_k']); dhs.append(d['dH'])

        lk_a = np.array(lks); dh_a = np.array(dhs)
        c = np.corrcoef(lk_a, dh_a)[0,1] if lk_a.std() > 0 else 0

        # Also: does this differential give inherently lower late_κ?
        results[dw0] = (lk_a.mean(), dh_a.mean(), c)
        print(f"  ΔW0=0x{dw0:08x}: E[κ]={lk_a.mean():.1f}, E[δH]={dh_a.mean():.2f}, corr={c:+.4f}")

    # Find: which ΔW0 gives lowest E[late_κ]?
    best_dw0 = min(results, key=lambda k: results[k][0])
    print(f"\nBest ΔW0 for low coupling: 0x{best_dw0:08x} "
          f"(E[κ]={results[best_dw0][0]:.1f}, E[δH]={results[best_dw0][1]:.2f})")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 29: PRECISION SIGNAL + NON-WANG DIFFERENTIALS")
    print("="*60)

    test_precision_wang(8000)
    test_non_wang_differentials(2000)
    test_differential_coupling_landscape(3500)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
