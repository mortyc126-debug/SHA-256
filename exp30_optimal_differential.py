#!/usr/bin/env python3
"""
EXP 30: Verify 0x55555555 + Construct Optimal Differential

From exp29:
- Signal is E-BRANCH ONLY (H[4..7]), ROUND 63
- Wang: corr=0.079. ΔW0=0x55555555: corr=0.124 (but N=500)
- Signal is DIFFERENTIAL-SPECIFIC

Part 1: Verify 0x55555555 at large N
Part 2: Systematic scan of ΔW0 to find OPTIMAL differential
Part 3: Construct differential that MAXIMIZES e-branch r=63 coupling→H[4] signal
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

def measure_signal(Wn_list, Wf_list):
    """Measure corr(late_κ, δH_e_branch) for a list of pairs."""
    lks = []; dhs_e = []; dhs_total = []
    for Wn, Wf in zip(Wn_list, Wf_list):
        sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
        We = schedule(Wn); Wfe = schedule(Wf)

        # Late κ (round 63 only — strongest signal)
        dn=sn[63][3]; en=sn[63][4]; fn=sn[63][5]; gn=sn[63][6]; hn=sn[63][7]
        df=sf[63][3]; ef=sf[63][4]; ff_=sf[63][5]; gf=sf[63][6]; hf=sf[63][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
        k63 = sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))
        lks.append(k63)

        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        dh_e = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))  # e-branch only
        dh_t = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        dhs_e.append(dh_e); dhs_total.append(dh_t)

    lk = np.array(lks); de = np.array(dhs_e); dt = np.array(dhs_total)
    ce = np.corrcoef(lk, de)[0,1] if lk.std()>0 and de.std()>0 else 0
    ct = np.corrcoef(lk, dt)[0,1] if lk.std()>0 and dt.std()>0 else 0
    return ce, ct, lk.mean(), de.mean(), dt.mean(), len(lks)

def test_verify_0x55555555(N=5000):
    """Verify alternating-bit differential at large N."""
    print("\n--- TEST 1: VERIFY ΔW0=0x55555555 (N=5000) ---")

    pairs_5 = []
    pairs_wang = []
    pairs_1 = []

    for _ in range(N):
        Wn = random_w16()

        # 0x55555555
        Wf5 = list(Wn); Wf5[0] = (Wf5[0] + 0x55555555) & MASK
        pairs_5.append((Wn, Wf5))

        # 0x1 baseline
        Wf1 = list(Wn); Wf1[0] = (Wf1[0] + 1) & MASK
        pairs_1.append((Wn, Wf1))

        # Wang
        try:
            Wn_w, Wf_w, _, _, _ = wang_cascade(Wn[0], Wn[1])
            pairs_wang.append((Wn_w, Wf_w))
        except:
            pass

    for label, pairs in [("ΔW0=0x55555555", pairs_5),
                          ("ΔW0=0x00000001", pairs_1),
                          ("Wang cascade", pairs_wang)]:
        Wns = [p[0] for p in pairs]; Wfs = [p[1] for p in pairs]
        ce, ct, mk, me, mt, n = measure_signal(Wns, Wfs)
        ze = ce * np.sqrt(n); zt = ct * np.sqrt(n)
        print(f"  {label:>18}: corr_e={ce:+.4f}(Z={ze:+.1f}) corr_t={ct:+.4f}(Z={zt:+.1f}) "
              f"E[κ63]={mk:.1f} E[δH_e]={me:.1f} N={n}")

def test_systematic_dw0_scan(N=2000):
    """Scan ΔW0 space systematically for maximum signal."""
    print("\n--- TEST 2: SYSTEMATIC ΔW0 SCAN ---")

    # Test patterns with different bit structures
    candidates = {
        0x00000001: "single bit 0",
        0x00000003: "bits 0-1",
        0x0000000F: "bits 0-3",
        0x000000FF: "bits 0-7",
        0x0000FFFF: "bits 0-15",
        0xFFFFFFFF: "all bits",
        0x55555555: "alternating 01",
        0xAAAAAAAA: "alternating 10",
        0x33333333: "pairs 0011",
        0xCCCCCCCC: "pairs 1100",
        0x0F0F0F0F: "nibbles 0000,1111",
        0xF0F0F0F0: "nibbles 1111,0000",
        0x00FF00FF: "bytes 00,FF",
        0xFF00FF00: "bytes FF,00",
        0x80000000: "single bit 31",
        0x01010101: "every 8th bit",
        0x11111111: "every 4th bit",
        0x80808080: "MSB every byte",
    }

    results = []
    for dw0, desc in candidates.items():
        pairs = []
        for _ in range(N):
            Wn = random_w16()
            Wf = list(Wn); Wf[0] = (Wf[0] + dw0) & MASK
            pairs.append((Wn, Wf))

        Wns = [p[0] for p in pairs]; Wfs = [p[1] for p in pairs]
        ce, ct, mk, me, mt, n = measure_signal(Wns, Wfs)
        ze = ce * np.sqrt(n)
        results.append((ce, ze, dw0, desc, mk))

    results.sort(key=lambda x: -x[0])
    print(f"{'ΔW0':>12} | {'corr_e':>8} | {'Z':>6} | {'E[κ63]':>7} | Description")
    print("-"*65)
    for ce, ze, dw0, desc, mk in results:
        sig = " ***" if ze > 3 else ""
        print(f"0x{dw0:08x} | {ce:>+8.4f} | {ze:>+6.1f} | {mk:>7.1f} | {desc}{sig}")

    # Best differential
    best = results[0]
    print(f"\nBest: ΔW0=0x{best[2]:08x} ({best[3]}), corr_e={best[0]:+.4f}, Z={best[1]:.1f}")

    return results

def test_multi_word_differential(N=2000):
    """Extend beyond single-word: ΔW with multiple non-zero words."""
    print("\n--- TEST 3: MULTI-WORD DIFFERENTIAL ---")

    configs = [
        ("ΔW[0]=0x55555555 only", lambda Wn: set_diff(Wn, {0: 0x55555555})),
        ("ΔW[0,1]=0x55...", lambda Wn: set_diff(Wn, {0: 0x55555555, 1: 0x55555555})),
        ("ΔW[0..3]=0x55...", lambda Wn: set_diff(Wn, {i: 0x55555555 for i in range(4)})),
        ("ΔW[0..7]=0x55...", lambda Wn: set_diff(Wn, {i: 0x55555555 for i in range(8)})),
        ("ΔW[0..15]=0x55...", lambda Wn: set_diff(Wn, {i: 0x55555555 for i in range(16)})),
        ("ΔW[0]=0x55, ΔW[15]=0xAA", lambda Wn: set_diff(Wn, {0: 0x55555555, 15: 0xAAAAAAAA})),
        ("Wang + ΔW[0]=0x55", None),  # Special case
    ]

    for label, diff_fn in configs:
        if diff_fn is None:
            # Wang with 0x55555555
            pairs = []
            for _ in range(N):
                W0=random.randint(0,MASK); W1=random.randint(0,MASK)
                try:
                    Wn,Wf,_,_,_ = wang_cascade(W0,W1,0x55555555)
                    pairs.append((Wn,Wf))
                except: pass
            if not pairs: continue
        else:
            pairs = []
            for _ in range(N):
                Wn = random_w16()
                Wf = diff_fn(Wn)
                pairs.append((Wn, Wf))

        Wns=[p[0] for p in pairs]; Wfs=[p[1] for p in pairs]
        ce,ct,mk,me,mt,n = measure_signal(Wns, Wfs)
        ze = ce * np.sqrt(n)
        print(f"  {label:>30}: corr_e={ce:+.4f} Z={ze:+.1f} E[κ63]={mk:.1f} E[δH]={mt:.1f} N={n}")

def set_diff(Wn, diffs):
    """Apply additive differentials to specific words."""
    Wf = list(Wn)
    for idx, dw in diffs.items():
        Wf[idx] = (Wf[idx] + dw) & MASK
    return Wf

def test_hill_climb_differential(N=200):
    """Hill-climb in ΔW0 space to maximize corr(κ63, δH_e)."""
    print("\n--- TEST 4: HILL-CLIMB OPTIMAL DIFFERENTIAL ---")

    # Start from best known (0x55555555)
    current_dw0 = 0x55555555
    M_eval = 500  # Pairs per evaluation

    def eval_dw0(dw0):
        pairs = []
        for _ in range(M_eval):
            Wn = random_w16()
            Wf = list(Wn); Wf[0] = (Wf[0] + dw0) & MASK
            pairs.append((Wn, Wf))
        Wns=[p[0] for p in pairs]; Wfs=[p[1] for p in pairs]
        ce,_,mk,_,_,_ = measure_signal(Wns, Wfs)
        return ce

    best_corr = eval_dw0(current_dw0)
    best_dw0 = current_dw0
    print(f"Start: ΔW0=0x{current_dw0:08x}, corr_e={best_corr:+.4f}")

    # Hill-climb: flip bits
    for step in range(N):
        bit = random.randint(0, 31)
        trial_dw0 = current_dw0 ^ (1 << bit)
        trial_corr = eval_dw0(trial_dw0)

        if trial_corr > best_corr:
            best_corr = trial_corr
            current_dw0 = trial_dw0
            best_dw0 = trial_dw0

    print(f"After {N} steps: ΔW0=0x{best_dw0:08x}, corr_e={best_corr:+.4f}")
    print(f"Binary: {bin(best_dw0)}")
    print(f"HW: {hw(best_dw0)}")

    # Final verification at large N
    pairs = []
    for _ in range(3000):
        Wn = random_w16()
        Wf = list(Wn); Wf[0] = (Wf[0] + best_dw0) & MASK
        pairs.append((Wn, Wf))
    Wns=[p[0] for p in pairs]; Wfs=[p[1] for p in pairs]
    ce,ct,mk,me,mt,n = measure_signal(Wns, Wfs)
    ze = ce * np.sqrt(n)
    print(f"Verification (N=3000): corr_e={ce:+.4f} (Z={ze:+.1f})")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 30: OPTIMAL DIFFERENTIAL FOR E-BRANCH SIGNAL")
    print("="*60)
    test_verify_0x55555555(4000)
    results = test_systematic_dw0_scan(1500)
    test_multi_word_differential(1500)
    test_hill_climb_differential(100)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
