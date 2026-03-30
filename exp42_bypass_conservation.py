#!/usr/bin/env python3
"""
EXP 42: δC Modification at Fixed δL — Bypass Conservation Law

T_COLLISION_CONSERVATION: selection × pool = const.
Assumes: selection REDUCES pool.

BYPASS: modify δC WITHOUT changing δL.
δL depends on ΔW (linear, via GF(2)) — FIXED by Wang cascade.
δC depends on actual VALUES (W0, W1) — VARIABLE within same ΔW.

So: different (W0,W1) → different δC → different δH.
But δL stays CONSTANT (same Wang ΔW structure).

This is NOT selection (pool doesn't shrink).
This is TRANSFORMATION (same pool, different quality).

From exp40: at δL>P75, corr(δC, δH) = -0.122.
If we can push δC HIGH for free → δH drops by ~1.87 bits.
At full pool size → no birthday penalty.
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

def test_dL_invariance(N=2000):
    """
    VERIFY: does δL stay constant when we change (W0,W1) but keep ΔW?
    This is the KEY assumption — if δL varies, the bypass doesn't work.
    """
    print("\n--- TEST 1: IS δL INVARIANT UNDER (W0,W1) CHANGE? ---")

    # Fix ΔW through one Wang cascade, then try different (W0,W1)
    invariant_count = 0
    total = 0

    dL_variations = []

    for _ in range(N):
        # First pair: get ΔW structure
        W0a = random.randint(0, MASK)
        W1a = random.randint(0, MASK)
        Wn_a, Wf_a, DWs, _, _ = wang_cascade(W0a, W1a)

        Ln_a = xor_compress(Wn_a); Lf_a = xor_compress(Wf_a)
        dL_a = sum(hw(Ln_a[i]^Lf_a[i]) for i in range(8))

        # Second pair: SAME DWs, different (W0,W1)
        W0b = random.randint(0, MASK)
        W1b = random.randint(0, MASK)
        Wn_b = [W0b, W1b] + [0]*14
        Wf_b = [(Wn_b[i]+DWs[i])&MASK for i in range(16)]

        Ln_b = xor_compress(Wn_b); Lf_b = xor_compress(Wf_b)
        dL_b = sum(hw(Ln_b[i]^Lf_b[i]) for i in range(8))

        dL_variations.append(abs(dL_a - dL_b))
        if dL_a == dL_b:
            invariant_count += 1
        total += 1

    va = np.array(dL_variations)
    print(f"δL exact invariance: {invariant_count}/{total} ({invariant_count/total*100:.1f}%)")
    print(f"δL variation: mean={va.mean():.4f}, max={va.max()}")

    if invariant_count == total:
        print("*** δL is EXACTLY invariant under (W0,W1) change! ***")
        print("Conservation law bypass is VALID.")
    elif va.mean() < 1:
        print("*** δL is APPROXIMATELY invariant! ***")
    else:
        print("δL is NOT invariant — bypass INVALID.")

    return invariant_count == total

def test_dC_variation_at_fixed_dL(N=3000):
    """
    At FIXED ΔW (fixed δL), how much does δC vary with (W0,W1)?
    Large variation → we can steer δC → we can steer δH.
    """
    print("\n--- TEST 2: δC VARIATION AT FIXED ΔW ---")

    # For several fixed ΔW structures, measure δC range
    for trial in range(5):
        W0_ref = random.randint(0, MASK)
        W1_ref = random.randint(0, MASK)
        _, _, DWs, _, _ = wang_cascade(W0_ref, W1_ref)

        dCs = []; dHs = []; dLs = []
        for _ in range(N // 5):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn = [W0, W1] + [0]*14
            Wf = [(Wn[i]+DWs[i])&MASK for i in range(16)]

            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            Ln=xor_compress(Wn); Lf=xor_compress(Wf)

            dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
            dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
            dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

            dCs.append(dC); dHs.append(dH); dLs.append(dL)

        dCa = np.array(dCs); dHa = np.array(dHs); dLa = np.array(dLs)
        corr_CH = np.corrcoef(dCa, dHa)[0,1]

        print(f"  ΔW#{trial}: δL={dLa.mean():.1f}±{dLa.std():.1f}, "
              f"δC={dCa.mean():.1f}±{dCa.std():.1f}, "
              f"δH={dHa.mean():.1f}±{dHa.std():.1f}, "
              f"corr(δC,δH)={corr_CH:+.4f}")

def test_bypass_attack(total_budget=10000):
    """
    The bypass attack:
    1. Fix ΔW from one Wang cascade (fixes δL)
    2. Try many (W0,W1) at this fixed ΔW (varies δC)
    3. Select pair with best δH
    4. Pool = all (W0,W1) tried → NO pool reduction

    Compare with:
    A. Random Wang (different ΔW each time)
    B. Fixed ΔW, random (W0,W1), no δC guidance
    """
    print(f"\n--- TEST 3: BYPASS ATTACK (budget={total_budget}) ---")

    # Strategy A: random Wang (standard birthday)
    random_best = 256
    for _ in range(total_budget):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        random_best = min(random_best, dH)

    # Strategy B: fixed ΔW, many (W0,W1)
    # Use the BEST of several fixed ΔWs
    n_dw_candidates = 10
    n_per_dw = total_budget // n_dw_candidates

    fixed_best = 256
    fixed_best_data = None

    for dw_trial in range(n_dw_candidates):
        W0r=random.randint(0,MASK); W1r=random.randint(0,MASK)
        _,_,DWs,_,_ = wang_cascade(W0r, W1r)

        for _ in range(n_per_dw):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn=[W0,W1]+[0]*14
            Wf=[(Wn[i]+DWs[i])&MASK for i in range(16)]

            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

            if dH < fixed_best:
                fixed_best = dH
                fixed_best_data = (W0, W1, DWs, dH)

    # Birthday expectations
    birthday_A = 128 - 8*np.sqrt(2*np.log(total_budget))
    birthday_B = 128 - 8*np.sqrt(2*np.log(n_per_dw))

    print(f"Strategy A (random Wang):     best δH = {random_best}")
    print(f"Strategy B (fixed ΔW):        best δH = {fixed_best}")
    print(f"Birthday A (N={total_budget}):    ~{birthday_A:.1f}")
    print(f"Birthday B per ΔW (N={n_per_dw}): ~{birthday_B:.1f}")
    print(f"Birthday B total (10 × N):   ~{128-8*np.sqrt(2*np.log(10*n_per_dw)):.1f}")

    if fixed_best < random_best:
        print(f"*** Fixed ΔW beats random Wang by {random_best-fixed_best} bits! ***")
    else:
        print(f"Random Wang wins by {fixed_best-random_best} bits")

    # Strategy C: fixed ΔW + δC guidance
    # For the best ΔW, use conditional knowledge to select (W0,W1)
    if fixed_best_data:
        print(f"\n--- Strategy C: Fixed ΔW + conditional guidance ---")
        _, _, best_DWs, _ = fixed_best_data

        # Collect δC and δH for this ΔW
        guided_data = []
        for _ in range(total_budget):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn=[W0,W1]+[0]*14
            Wf=[(Wn[i]+best_DWs[i])&MASK for i in range(16)]

            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            Ln=xor_compress(Wn); Lf=xor_compress(Wf)

            dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
            dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
            guided_data.append((dC, dH))

        dCa = np.array([d[0] for d in guided_data])
        dHa = np.array([d[1] for d in guided_data])

        corr = np.corrcoef(dCa, dHa)[0,1]
        print(f"corr(δC, δH) at fixed ΔW: {corr:+.6f}")

        # Does selecting high-δC give lower δH? (from suppressor theorem)
        high_C = dHa[dCa > np.percentile(dCa, 75)]
        low_C = dHa[dCa < np.percentile(dCa, 25)]
        print(f"High δC: E[δH]={high_C.mean():.4f}, min={high_C.min()}")
        print(f"Low δC:  E[δH]={low_C.mean():.4f}, min={low_C.min()}")
        print(f"Overall: min={dHa.min()}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 42: δC MODIFICATION AT FIXED δL")
    print("Bypass Conservation Law: transform, don't filter")
    print("="*60)

    is_invariant = test_dL_invariance(1500)
    test_dC_variation_at_fixed_dL(2000)
    test_bypass_attack(8000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
