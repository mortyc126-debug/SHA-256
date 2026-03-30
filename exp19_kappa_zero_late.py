#!/usr/bin/env python3
"""
EXP 19: κ=0 at Late Rounds → Linear Zone

If κ=0 (carries identical), difference propagates as pure XOR.
exp12: without carry, E[δH]=20 (broken).
Question: can we FORCE κ=0 at rounds 56-63?
8 linear rounds at output + 56 normal = ???
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

def kappa_at_round(states_n, states_f, Wn_exp, Wf_exp, r):
    dn = states_n[r][3]; en = states_n[r][4]
    fn = states_n[r][5]; gn = states_n[r][6]; hn = states_n[r][7]
    df = states_f[r][3]; ef = states_f[r][4]
    ff_ = states_f[r][5]; gf = states_f[r][6]; hf = states_f[r][7]
    T1n = (hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_exp[r])&MASK
    T1f = (hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_exp[r])&MASK
    cv_n = carry_vec(dn, T1n)
    cv_f = carry_vec(df, T1f)
    return sum(a^b for a,b in zip(cv_n, cv_f))

def main():
    random.seed(42)
    N = 3000
    print("="*60)
    print("EXP 19: κ=0 AT LATE ROUNDS")
    print("="*60)

    # --- Measure natural P(κ=0) at late rounds ---
    print("\n--- NATURAL P(κ<threshold) AT LATE ROUNDS ---")
    for r_target in [56,57,58,59,60,61,62,63]:
        low_count = 0
        zero_count = 0
        for _ in range(N):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)
            Wn_e = schedule(Wn); Wf_e = schedule(Wf)
            k = kappa_at_round(sn, sf, Wn_e, Wf_e, r_target)
            if k == 0: zero_count += 1
            if k <= 4: low_count += 1
        print(f"  r={r_target}: P(κ=0)={zero_count/N:.6f}, P(κ≤4)={low_count/N:.6f}")

    # --- Search for pairs with low κ at rounds 60-63 ---
    print("\n--- SEARCH: LOW κ AT ROUNDS 60-63 ---")
    best_score = 999
    best_pair = None
    scores = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)
        Wn_e = schedule(Wn); Wf_e = schedule(Wf)
        score = sum(kappa_at_round(sn,sf,Wn_e,Wf_e,r) for r in range(60,64))
        scores.append(score)
        if score < best_score:
            best_score = score
            best_pair = (Wn, Wf, DWs)

    scores_arr = np.array(scores)
    print(f"κ_60-63 score: mean={scores_arr.mean():.2f}, min={scores_arr.min()}, max={scores_arr.max()}")

    # --- Do low-late-κ pairs have better δH? ---
    print("\n--- LOW LATE-κ vs HIGH LATE-κ: δH COMPARISON ---")
    pair_data = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)
        Wn_e = schedule(Wn); Wf_e = schedule(Wf)
        late_k = sum(kappa_at_round(sn,sf,Wn_e,Wf_e,r) for r in range(60,64))
        H_n = sha256_compress(Wn); H_f = sha256_compress(Wf)
        dH = sum(hw(H_n[i]^H_f[i]) for i in range(8))
        pair_data.append((late_k, dH))

    lk = np.array([p[0] for p in pair_data])
    dh = np.array([p[1] for p in pair_data])
    med = np.median(lk)
    low = dh[lk < med]; high = dh[lk >= med]
    corr = np.corrcoef(lk, dh)[0,1]
    print(f"Low late-κ:  E[δH]={low.mean():.4f}")
    print(f"High late-κ: E[δH]={high.mean():.4f}")
    print(f"corr(late_κ, δH): {corr:+.6f}")

    # Top 1%
    p1 = np.percentile(lk, 1)
    top1 = dh[lk <= p1]
    if len(top1) > 0:
        print(f"Top 1% (κ≤{p1:.0f}): E[δH]={top1.mean():.2f}, min={top1.min()}, N={len(top1)}")

    # --- Threshold test (nonlinear) ---
    print("\n--- THRESHOLD TEST (nonlinear κ→δH) ---")
    for thresh in [40, 45, 50, 55, 60]:
        below = dh[lk < thresh]
        above = dh[lk >= thresh]
        if len(below) > 10:
            print(f"  κ<{thresh}: E[δH]={below.mean():.2f} (N={len(below)}), "
                  f"κ≥{thresh}: E[δH]={above.mean():.2f}")

if __name__ == "__main__":
    main()
