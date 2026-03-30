#!/usr/bin/env python3
"""
EXP 35: Schedule Difference Minimization — Fifth Path

Divergence = +1.03 bits/round (LINEAR, not exponential).
Each round, ΔW[r] contributes to divergence.
If |ΔW[r]| is SMALL at late rounds → less fuel for divergence.

Schedule: W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]
For Wang pairs: ΔW[0..15] fixed by cascade.
→ ΔW[16..63] = deterministic function of ΔW[0..15].

Key question: can we choose Wang params (W0,W1) such that
ΔW[48..63] are anomalously small?

If HW(ΔW[48..63]) << 16 (random) → divergence STARVED of fuel
→ state distance grows slower → δH potentially lower.

NOT coupling. NOT convergence. FUEL STARVATION.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def schedule_diff_profile(Wn, Wf):
    """Compute HW of ΔW[t] = W_f[t] - W_n[t] for t=0..63."""
    Wn_s = schedule(Wn)
    Wf_s = schedule(Wf)
    return [hw((Wf_s[t] - Wn_s[t]) & MASK) for t in range(64)]

def late_schedule_diff(Wn, Wf, r_start=48, r_end=64):
    """Sum of HW(ΔW[t]) for late rounds."""
    Wn_s = schedule(Wn); Wf_s = schedule(Wf)
    return sum(hw((Wf_s[t] - Wn_s[t]) & MASK) for t in range(r_start, r_end))

def test_schedule_diff_profile(N=2000):
    """Profile: how does HW(ΔW[t]) evolve across schedule?"""
    print("\n--- TEST 1: SCHEDULE DIFFERENCE PROFILE ---")

    profiles = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)
        p = schedule_diff_profile(Wn, Wf)
        profiles.append(p)

    P = np.array(profiles)

    print(f"{'W[t]':>5} | {'E[HW(ΔW)]':>10} | {'std':>8} | {'min':>5} | {'max':>5} | Phase")
    print("-"*55)
    for t in list(range(16)) + [16,17,18,19,20,24,28,32,40,48,52,56,60,63]:
        if t >= 64: continue
        arr = P[:,t]
        phase = ""
        if t < 16:
            phase = "FREE (Wang)"
        elif arr.mean() < 12:
            phase = "LOW"
        elif arr.mean() < 14:
            phase = "BELOW RANDOM"
        else:
            phase = "RANDOM"
        print(f"W[{t:>2}] | {arr.mean():>10.2f} | {arr.std():>8.2f} | {arr.min():>5} | "
              f"{arr.max():>5} | {phase}")

    # Key: correlation between late ΔW and δH
    late_dw = np.array([sum(P[i, 48:64]) for i in range(N)])

    # Need δH
    dHs = []
    for _ in range(N):  # Recompute
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dHs.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))
    dH = np.array(dHs)

    # We can't directly correlate since different random seeds
    # Redo with paired data
    return P

def test_schedule_diff_vs_dH(N=5000):
    """KEY TEST: does small late ΔW predict small δH?"""
    print("\n--- TEST 2: LATE ΔW → δH CORRELATION ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)

        Wn_s = schedule(Wn); Wf_s = schedule(Wf)
        late_dw_hw = sum(hw((Wf_s[t]-Wn_s[t])&MASK) for t in range(48,64))
        mid_dw_hw = sum(hw((Wf_s[t]-Wn_s[t])&MASK) for t in range(32,48))
        early_dw_hw = sum(hw((Wf_s[t]-Wn_s[t])&MASK) for t in range(16,32))

        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        data.append((late_dw_hw, mid_dw_hw, early_dw_hw, dH))

    late = np.array([d[0] for d in data])
    mid = np.array([d[1] for d in data])
    early = np.array([d[2] for d in data])
    dH = np.array([d[3] for d in data])

    threshold = 3 / np.sqrt(N)

    c_late = np.corrcoef(late, dH)[0,1]
    c_mid = np.corrcoef(mid, dH)[0,1]
    c_early = np.corrcoef(early, dH)[0,1]

    print(f"corr(HW(ΔW[48-63]), δH): {c_late:+.6f} {'***' if abs(c_late)>threshold else ''}")
    print(f"corr(HW(ΔW[32-47]), δH): {c_mid:+.6f} {'***' if abs(c_mid)>threshold else ''}")
    print(f"corr(HW(ΔW[16-31]), δH): {c_early:+.6f} {'***' if abs(c_early)>threshold else ''}")
    print(f"Threshold: {threshold:.6f}")

    # Quantile analysis
    print(f"\nLate ΔW quantiles → δH:")
    for q in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        thresh_val = np.percentile(late, q)
        subset = dH[late <= thresh_val]
        if len(subset) > 0:
            print(f"  ΔW≤P{q:>2} (≤{thresh_val:.0f}, N={len(subset):>5}): E[δH]={subset.mean():.4f}")

    return data

def test_search_low_schedule_diff(N=5000):
    """Search (W0,W1) space for minimum late schedule difference."""
    print("\n--- TEST 3: SEARCH FOR LOW LATE ΔW ---")

    all_late_dw = []
    all_dH = []
    best_late = 999
    best_pair = None

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)

        late_dw = late_schedule_diff(Wn, Wf)
        all_late_dw.append(late_dw)

        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        all_dH.append(dH)

        if late_dw < best_late:
            best_late = late_dw
            best_pair = (W0, W1, Wn, Wf, dH)

    ld = np.array(all_late_dw); dh = np.array(all_dH)
    print(f"Late ΔW: mean={ld.mean():.1f}, std={ld.std():.1f}, min={ld.min()}, max={ld.max()}")
    print(f"Best: late_ΔW={best_late}, δH={best_pair[4]}")

    # Hill-climb for minimum late ΔW
    print(f"\nHill-climbing for min late ΔW...")
    best_W0, best_W1 = best_pair[0], best_pair[1]
    best_score = best_late

    for step in range(3000):
        if random.random() < 0.5:
            tW0 = best_W0 ^ (1<<random.randint(0,31)); tW1 = best_W1
        else:
            tW0 = best_W0; tW1 = best_W1 ^ (1<<random.randint(0,31))
        try:
            Wn,Wf,_,_,_ = wang_cascade(tW0, tW1)
            score = late_schedule_diff(Wn, Wf)
            if score < best_score:
                best_score = score
                best_W0, best_W1 = tW0, tW1
        except: pass

    # Final measurement
    Wn,Wf,_,_,_ = wang_cascade(best_W0, best_W1)
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    final_dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

    print(f"After hill-climb: late_ΔW={best_score}, δH={final_dH}")
    print(f"W0=0x{best_W0:08x}, W1=0x{best_W1:08x}")

    # Schedule profile of best
    p = schedule_diff_profile(Wn, Wf)
    print(f"Schedule profile (W[48..63]):")
    for t in range(48, 64):
        print(f"  W[{t}]: HW(ΔW)={p[t]}")

    return best_score, final_dH

def test_per_round_dw_contribution(N=3000):
    """Which ΔW[t] contributes most to δH? Per-round analysis."""
    print("\n--- TEST 4: PER-ROUND ΔW CONTRIBUTION TO δH ---")

    # For each round t: corr(HW(ΔW[t]), δH)
    dw_per_round = {t: [] for t in range(16, 64)}
    dHs = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        Wn_s = schedule(Wn); Wf_s = schedule(Wf)
        for t in range(16, 64):
            dw_per_round[t].append(hw((Wf_s[t]-Wn_s[t])&MASK))

        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dHs.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    dH = np.array(dHs)
    threshold = 3/np.sqrt(N)

    print(f"{'W[t]':>5} | {'corr(ΔW,δH)':>12} | Signal")
    print("-"*35)

    significant = []
    for t in range(16, 64):
        arr = np.array(dw_per_round[t])
        c = np.corrcoef(arr, dH)[0,1]
        sig = " ***" if abs(c) > threshold else ""
        if abs(c) > threshold:
            significant.append((t, c))
        if t in [16,17,18,19,20,24,28,32,40,48,52,56,60,63]:
            print(f"W[{t:>2}] | {c:>+12.6f} | {sig}")

    print(f"\nSignificant rounds: {len(significant)}")
    if significant:
        significant.sort(key=lambda x: -abs(x[1]))
        print(f"Top 5:")
        for t, c in significant[:5]:
            print(f"  W[{t}]: corr={c:+.6f}")

def test_combined_dw_coupling(N=3000):
    """Does schedule diff AMPLIFY coupling signal?"""
    print("\n--- TEST 5: SCHEDULE DIFF × COUPLING → δH ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn,sf = wang_cascade(W0,W1)

        We=schedule(Wn); Wfe=schedule(Wf)
        late_dw = sum(hw((Wfe[t]-We[t])&MASK) for t in range(48,64))

        # κ_63
        dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn=sn[63][7]
        df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
        cv_n=[0]*32;cv_f=[0]*32
        c=0
        for i in range(32):
            s=((dn>>i)&1)+((T1n>>i)&1)+c;c=1 if s>=2 else 0;cv_n[i]=c
        c=0
        for i in range(32):
            s=((df>>i)&1)+((T1f>>i)&1)+c;c=1 if s>=2 else 0;cv_f[i]=c
        k63=sum(a^b for a,b in zip(cv_n,cv_f))

        Hn=sha256_compress(Wn);Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))

        data.append((late_dw, k63, dH))

    ld=np.array([d[0] for d in data])
    k63=np.array([d[1] for d in data])
    dH=np.array([d[2] for d in data])

    # Individual
    c1=np.corrcoef(ld,dH)[0,1]
    c2=np.corrcoef(k63,dH)[0,1]
    # Product
    prod=ld*k63
    c3=np.corrcoef(prod,dH)[0,1]
    # Sum
    combined=ld+k63*8  # Weight κ by 8 (our measured ratio)
    c4=np.corrcoef(combined,dH)[0,1]

    threshold=3/np.sqrt(N)
    print(f"corr(late_ΔW, δH):          {c1:+.6f} {'***' if abs(c1)>threshold else ''}")
    print(f"corr(κ_63, δH):             {c2:+.6f} {'***' if abs(c2)>threshold else ''}")
    print(f"corr(late_ΔW × κ_63, δH):   {c3:+.6f} {'***' if abs(c3)>threshold else ''}")
    print(f"corr(late_ΔW + 8·κ_63, δH): {c4:+.6f} {'***' if abs(c4)>threshold else ''}")

    if abs(c4) > abs(c1) and abs(c4) > abs(c2):
        print(f"*** COMBINED SIGNAL STRONGER: {abs(c4):.4f} > max({abs(c1):.4f}, {abs(c2):.4f}) ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 35: SCHEDULE DIFF MINIMIZATION — FIFTH PATH")
    print("Starve divergence of fuel")
    print("="*60)
    test_schedule_diff_profile(1500)
    test_schedule_diff_vs_dH(4000)
    test_search_low_schedule_diff(3000)
    test_per_round_dw_contribution(3000)
    test_combined_dw_coupling(3000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
