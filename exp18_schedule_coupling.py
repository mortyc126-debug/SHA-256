#!/usr/bin/env python3
"""
EXP 18: Schedule Coupling — κ in message schedule

Schedule: W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]
Has 4 additions with LONG-RANGE dependencies (lag 2,7,15,16).
Schedule IS the barrier (T_BARRIER_EQUALS_SCHEDULE).

Unmeasured: does schedule coupling have different τ?
Does it connect to Da13 + ΔW16 = 0 (barrier equation)?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    carries = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1) + ((b>>i)&1) + c
        c = 1 if s >= 2 else 0
        carries.append(c)
    return carries

def schedule_coupling(Wn, Wf):
    """Compute carry coupling in message schedule for W[16..63]."""
    Wn_s = schedule(Wn)
    Wf_s = schedule(Wf)
    DW = [(Wf_s[t] - Wn_s[t]) & MASK for t in range(64)]

    kappa_schedule = []
    for t in range(16, 64):
        # W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]
        # 3 additions chained. Measure coupling on the TOTAL
        # Carry of the full sum for normal
        a_n = sig1(Wn_s[t-2])
        b_n = Wn_s[t-7]
        c_n = sig0(Wn_s[t-15])
        d_n = Wn_s[t-16]
        sum1_n = (a_n + b_n) & MASK
        sum2_n = (sum1_n + c_n) & MASK
        # Final addition
        cv_n = carry_vec(sum2_n, d_n)

        a_f = sig1(Wf_s[t-2])
        b_f = Wf_s[t-7]
        c_f = sig0(Wf_s[t-15])
        d_f = Wf_s[t-16]
        sum1_f = (a_f + b_f) & MASK
        sum2_f = (sum1_f + c_f) & MASK
        cv_f = carry_vec(sum2_f, d_f)

        kappa = sum(a ^ b for a, b in zip(cv_n, cv_f))
        kappa_schedule.append((t, kappa, hw(DW[t])))

    return kappa_schedule

def main():
    random.seed(42)
    N = 1500
    print("="*60)
    print("EXP 18: SCHEDULE COUPLING")
    print("="*60)

    # --- Profile ---
    print("\n--- SCHEDULE κ PROFILE ---")
    sched_kappa = {t: [] for t in range(16, 64)}
    sched_dw_hw = {t: [] for t in range(16, 64)}
    dH_list = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        sk = schedule_coupling(Wn, Wf)
        for t, k, dwh in sk:
            sched_kappa[t].append(k)
            sched_dw_hw[t].append(dwh)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dH_list.append(sum(hw(H_n[i]^H_f[i]) for i in range(8)))

    dH_arr = np.array(dH_list)

    print(f"{'W[t]':>5} | {'E[κ]':>8} | {'E[HW(ΔW)]':>10} | {'corr(κ,δH)':>11} | Signal")
    print("-"*55)
    for t in [16,17,18,19,20,24,28,32,40,48,56,63]:
        ka = np.array(sched_kappa[t])
        dwa = np.array(sched_dw_hw[t])
        c = np.corrcoef(ka, dH_arr)[0,1] if ka.std()>0 else 0
        sig = " ***" if abs(c) > 0.077 else ""
        print(f"W[{t:>2}] | {ka.mean():>8.2f} | {dwa.mean():>10.2f} | {c:>+11.6f} | {sig}")

    # --- Autocorrelation ---
    print("\n--- SCHEDULE κ AUTOCORRELATION ---")
    for lag in [1,2,3,5,7,8,15,16]:
        pairs = []
        for _ in range(500):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
            sk = schedule_coupling(Wn, Wf)
            kvals = [k for _, k, _ in sk]
            for i in range(len(kvals)-lag):
                pairs.append((kvals[i], kvals[i+lag]))
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        c = np.corrcoef(x,y)[0,1]
        sig = " ***" if abs(c) > 0.05 else ""
        print(f"  Lag {lag:>2}: {c:+.6f}{sig}")

    # --- Barrier equation correlation ---
    print("\n--- κ_schedule → BARRIER EQUATION ---")
    k16_list = []
    k17_list = []
    hw17_list = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)
        sk = schedule_coupling(Wn, Wf)
        k16 = sk[0][1]  # W[16] coupling
        k17 = sk[1][1]  # W[17] coupling
        De17 = de(sn, sf, 17)
        k16_list.append(k16)
        k17_list.append(k17)
        hw17_list.append(hw(De17))

    c16 = np.corrcoef(k16_list, hw17_list)[0,1]
    c17 = np.corrcoef(k17_list, hw17_list)[0,1]
    print(f"corr(κ_W16, HW(De17)): {c16:+.6f}")
    print(f"corr(κ_W17, HW(De17)): {c17:+.6f}")

    # Conditional: P(HW(De17)<12 | κ_W16 < median) vs > median
    k16a = np.array(k16_list)
    hw17a = np.array(hw17_list)
    med = np.median(k16a)
    low_k = hw17a[k16a < med]
    high_k = hw17a[k16a >= med]
    print(f"Low κ_W16:  E[HW(De17)]={low_k.mean():.4f}")
    print(f"High κ_W16: E[HW(De17)]={high_k.mean():.4f}")

if __name__ == "__main__":
    main()
