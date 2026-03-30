#!/usr/bin/env python3
"""
EXP 41: XOR-Guided Carry Selection

From exp40: corr(δC, δH | δL > P75) = -0.122 (Z=5.6).
When XOR-diff is HIGH → low carry = low δH.
When XOR-diff is LOW  → low carry = low δH (positive corr too).

Both: low carry → low δH. But we can PREDICT which regime using
XOR-SHA-256 (computable in O(N), linear, no carry).

STRATEGY:
1. Compute XOR-SHA-256 for many pairs (CHEAP)
2. Classify into δL-high / δL-low groups
3. Within each group, find pairs with LOW carry contribution
4. These pairs should have lower δH than random

KEY: XOR computation is ~3× faster (no carry propagation).
If XOR-guided selection gives even 1 bit advantage →
effective birthday cost = 2^127 with constant-factor speedup.
"""
import sys, os, random, time
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

def xor_hash_diff(Wn, Wf):
    """XOR-SHA-256 hash difference (cheap)."""
    Ln = xor_compress(Wn); Lf = xor_compress(Wf)
    return sum(hw(Ln[i]^Lf[i]) for i in range(8))

def carry_component_diff(Wn, Wf):
    """Carry component δC = δ(H ⊕ L)."""
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    Ln=xor_compress(Wn); Lf=xor_compress(Wf)
    return sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))

def full_hash_diff(Wn, Wf):
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def test_xor_guided_vs_random(total_budget=10000):
    """
    Compare:
    A) Random: evaluate total_budget Wang pairs, take best δH
    B) XOR-guided: evaluate total_budget/2 XOR-diffs (cheap),
       select best half by δL extremity, evaluate SHA-256 only on those
    C) XOR+δC guided: use both XOR and carry component
    """
    print(f"\n--- XOR-GUIDED vs RANDOM (budget={total_budget}) ---")

    # Strategy A: Pure random
    random_dHs = []
    for _ in range(total_budget):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        random_dHs.append(full_hash_diff(Wn, Wf))

    # Strategy B: XOR-guided
    # Phase 1: compute XOR-diff for 2× budget (cheap)
    candidates = []
    for _ in range(total_budget * 2):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        dL = xor_hash_diff(Wn, Wf)
        candidates.append((dL, Wn, Wf))

    # Phase 2: select by δL extremity (high or low — both useful)
    # From exp40: high δL → carry suppression → want low carry
    # Select top/bottom quartiles
    candidates.sort(key=lambda x: x[0])
    n_select = total_budget // 2

    # Take extreme δL (both tails)
    selected = candidates[:n_select//2] + candidates[-n_select//2:]

    guided_dHs = []
    for dL, Wn, Wf in selected:
        guided_dHs.append(full_hash_diff(Wn, Wf))

    # Strategy C: XOR+condition guided
    # Among high-δL: prefer low carry. Among low-δL: also prefer low carry.
    # For simplicity: just take extreme δL and evaluate
    # (carry estimation requires full SHA, so same cost)

    ra = np.array(random_dHs)
    ga = np.array(guided_dHs)

    print(f"Random:      E[δH]={ra.mean():.2f}, min={ra.min()}, "
          f"P(δH<110)={np.mean(ra<110):.4f}")
    print(f"XOR-guided:  E[δH]={ga.mean():.2f}, min={ga.min()}, "
          f"P(δH<110)={np.mean(ga<110):.4f}")
    print(f"Difference:  {ga.mean()-ra.mean():+.2f}")

    # Birthday-expected minimum
    birthday_rand = 128 - 8*np.sqrt(2*np.log(total_budget))
    birthday_guid = 128 - 8*np.sqrt(2*np.log(len(selected)))
    print(f"\nBirthday expected (random, N={total_budget}): ~{birthday_rand:.1f}")
    print(f"Birthday expected (guided, N={len(selected)}): ~{birthday_guid:.1f}")

    if ga.min() < ra.min():
        print(f"*** XOR-guided finds better pair: {ga.min()} < {ra.min()} ***")

    return ra, ga

def test_conditional_selection(N=8000):
    """
    Full conditional strategy:
    1. Compute all (dL, dC, dH) for N Wang pairs
    2. Split by dL quartile
    3. Within each quartile, rank by dC
    4. Check if dC-selected subset has lower dH
    """
    print(f"\n--- CONDITIONAL SELECTION (N={N}) ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        Ln=xor_compress(Wn); Lf=xor_compress(Wf)
        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        data.append((dL, dC, dH))

    dL=np.array([d[0] for d in data])
    dC=np.array([d[1] for d in data])
    dH=np.array([d[2] for d in data])

    # Split into δL quartiles
    q25 = np.percentile(dL, 25)
    q75 = np.percentile(dL, 75)

    for label, mask_dL in [("δL < P25", dL < q25),
                            ("P25 ≤ δL < P75", (dL >= q25) & (dL < q75)),
                            ("δL ≥ P75", dL >= q75)]:
        subset_dC = dC[mask_dL]
        subset_dH = dH[mask_dL]
        n = len(subset_dH)

        # Within this δL group: select by low dC (bottom 25%)
        dC_thresh = np.percentile(subset_dC, 25)
        low_C_mask = subset_dC <= dC_thresh
        high_C_mask = subset_dC > np.percentile(subset_dC, 75)

        dH_low_C = subset_dH[low_C_mask]
        dH_high_C = subset_dH[high_C_mask]

        if len(dH_low_C)>10 and len(dH_high_C)>10:
            print(f"\n  {label} (N={n}):")
            print(f"    Low δC:  E[δH]={dH_low_C.mean():.4f}, min={dH_low_C.min()} (N={len(dH_low_C)})")
            print(f"    High δC: E[δH]={dH_high_C.mean():.4f}, min={dH_high_C.min()} (N={len(dH_high_C)})")
            print(f"    Δ = {dH_low_C.mean()-dH_high_C.mean():+.4f}")

            if label == "δL ≥ P75":
                # This is where suppression is strongest (corr=-0.122)
                # Low carry → low δH expected
                if dH_low_C.mean() < dH_high_C.mean():
                    print(f"    *** CONFIRMED: low carry → low δH in high-δL regime ***")

    # OPTIMAL strategy: select δL>P75 AND δC<P25 (within that group)
    print(f"\n--- OPTIMAL COMBINED SELECTION ---")
    mask_optimal = (dL >= q75)
    n_opt = mask_optimal.sum()
    if n_opt > 50:
        subset_dC_opt = dC[mask_optimal]
        subset_dH_opt = dH[mask_optimal]
        dC_opt_q25 = np.percentile(subset_dC_opt, 25)

        optimal_dH = subset_dH_opt[subset_dC_opt <= dC_opt_q25]
        random_dH = dH

        print(f"  Optimal selection (δL>P75, δC<P25 within): N={len(optimal_dH)}")
        print(f"    E[δH] = {optimal_dH.mean():.4f}, min = {optimal_dH.min()}")
        print(f"  Random (all pairs): N={len(random_dH)}")
        print(f"    E[δH] = {random_dH.mean():.4f}, min = {random_dH.min()}")
        print(f"  Advantage: {random_dH.mean() - optimal_dH.mean():+.4f} bits")

        # At same N: compare optimal vs random sample of same size
        n_compare = len(optimal_dH)
        random_sample = np.random.choice(dH, n_compare, replace=False)
        print(f"\n  Same-size comparison (N={n_compare}):")
        print(f"    Optimal: E[δH]={optimal_dH.mean():.4f}, min={optimal_dH.min()}")
        print(f"    Random:  E[δH]={random_sample.mean():.4f}, min={random_sample.min()}")

def test_speed_comparison():
    """Measure actual speed: XOR-SHA-256 vs real SHA-256."""
    print(f"\n--- SPEED COMPARISON ---")

    N = 1000
    W_samples = [random_w16() for _ in range(N)]

    t0 = time.time()
    for W in W_samples:
        sha256_compress(W)
    t_real = time.time() - t0

    t0 = time.time()
    for W in W_samples:
        xor_compress(W)
    t_xor = time.time() - t0

    print(f"Real SHA-256: {t_real:.3f}s for {N} hashes ({N/t_real:.0f}/sec)")
    print(f"XOR-SHA-256:  {t_xor:.3f}s for {N} hashes ({N/t_xor:.0f}/sec)")
    print(f"Speedup: {t_real/t_xor:.2f}×")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 41: XOR-GUIDED CARRY SELECTION")
    print("Use Simpson's Paradox as attack tool")
    print("="*60)

    test_speed_comparison()
    test_xor_guided_vs_random(8000)
    test_conditional_selection(8000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
