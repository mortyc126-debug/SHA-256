#!/usr/bin/env python3
"""
EXP 195: SELF-AMPLIFYING CYCLE — Does dip in δa cascade through shift register?

THEORY:
  δa dip at round r → δd = δa[r] at round r+3 (shift register)
  → small δd → δe_new = δd + δT1 has LESS input → δe smaller
  → small δe at r+3 → through Ch/Σ₁ → less noise in T1
  → δa_new smaller at r+4 → ... → CYCLE?

If this cycle EXISTS and AMPLIFIES → self-reinforcing dip → collision!
Period ≈ 3 rounds (shift register delay a→d).
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_ae_trace(M1, M2, max_r=64):
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)
    da = [hw(s1[r][0] ^ s2[r][0]) for r in range(max_r+1)]
    de = [hw(s1[r][4] ^ s2[r][4]) for r in range(max_r+1)]
    return np.array(da), np.array(de)

def test_dip_propagation(N=500):
    """When δa dips at round r, does δe dip at round r+3?"""
    print(f"\n{'='*60}")
    print(f"DIP PROPAGATION: δa[r] → δe[r+3]?")
    print(f"{'='*60}")

    # Collect: when δa < 12 at round r, what's δe at r+1, r+2, r+3, r+4?
    after_dip = {lag: [] for lag in range(1, 8)}
    after_normal = {lag: [] for lag in range(1, 8)}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        da, de = get_ae_trace(M1, M2)

        for r in range(30, 57):
            is_dip = da[r] < 12

            for lag in range(1, 8):
                if r + lag <= 64:
                    if is_dip:
                        after_dip[lag].append(de[r + lag])
                    else:
                        after_normal[lag].append(de[r + lag])

    print(f"\n  After δa DIP (<12): what happens to δe?")
    print(f"  {'Lag':>4} | {'δe after dip':>12} | {'δe after normal':>15} | {'Diff':>6} | {'Signal'}")
    print(f"  " + "-" * 55)

    for lag in range(1, 8):
        dip_avg = np.mean(after_dip[lag]) if after_dip[lag] else 16
        norm_avg = np.mean(after_normal[lag]) if after_normal[lag] else 16
        diff = dip_avg - norm_avg
        n_dip = len(after_dip[lag])

        z = diff / math.sqrt(16 * 0.25 / max(n_dip, 1)) if n_dip > 10 else 0
        sig = " ★★★" if abs(z) > 5 else (" ★★" if abs(z) > 3 else "")

        print(f"  {lag:>4} | {dip_avg:>12.2f} | {norm_avg:>15.2f} | {diff:>+6.2f} | Z={z:+.1f}{sig}")

        if lag == 3:
            print(f"         ↑ LAG 3 = shift register delay a→d→e_new")

def test_cycle_detection(N=300):
    """Look for self-amplifying cycles: dip→dip→dip with period ~3."""
    print(f"\n{'='*60}")
    print(f"CYCLE DETECTION: Repeating dips?")
    print(f"{'='*60}")

    # For each message pair: does δa have PERIODIC dips?
    periodic_counts = {p: 0 for p in range(2, 10)}
    total = 0

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        da, de = get_ae_trace(M1, M2)

        # Find dip positions (δa < 12 in dead zone)
        dip_rounds = [r for r in range(25, 64) if da[r] < 12]
        total += 1

        if len(dip_rounds) >= 3:
            # Check for periodicity in dip spacing
            spacings = [dip_rounds[i+1] - dip_rounds[i] for i in range(len(dip_rounds)-1)]
            for period in range(2, 10):
                if all(abs(s - period) <= 1 for s in spacings[:3]):
                    periodic_counts[period] += 1

    print(f"\n  Periodic dip patterns (N={total}):")
    for period, count in sorted(periodic_counts.items()):
        pct = count / total * 100
        sig = " ★★★" if pct > 1 else ""
        print(f"    Period {period}: {count}/{total} ({pct:.2f}%){sig}")

    print(f"\n  Period 3 = shift register delay (a→b→c→d→e)")

def test_correlation_at_lag3(N=500):
    """Direct test: corr(δa[r], δe[r+3]) in the dead zone."""
    print(f"\n{'='*60}")
    print(f"DIRECT CORRELATION: δa[r] → δe[r+3]")
    print(f"{'='*60}")

    for lag in range(1, 8):
        corrs = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))
            da, de = get_ae_trace(M1, M2)

            # Correlation in dead zone
            da_slice = da[30:60]
            de_slice = de[30+lag:60+lag]
            min_len = min(len(da_slice), len(de_slice))
            if min_len > 5:
                c = np.corrcoef(da_slice[:min_len], de_slice[:min_len])[0, 1]
                if not np.isnan(c):
                    corrs.append(c)

        avg = np.mean(corrs) if corrs else 0
        sig = " ★★★" if abs(avg) > 0.1 else (" ★★" if abs(avg) > 0.05 else "")
        print(f"  corr(δa[r], δe[r+{lag}]): {avg:+.4f}{sig}")
        if lag == 3:
            print(f"    ↑ THIS is the shift register coupling")

    # Also: δe[r] → δa[r+k] (reverse direction)
    print(f"\n  Reverse: corr(δe[r], δa[r+k]):")
    for lag in range(1, 8):
        corrs = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))
            da, de = get_ae_trace(M1, M2)

            de_slice = de[30:60]
            da_slice = da[30+lag:60+lag]
            min_len = min(len(de_slice), len(da_slice))
            if min_len > 5:
                c = np.corrcoef(de_slice[:min_len], da_slice[:min_len])[0, 1]
                if not np.isnan(c):
                    corrs.append(c)

        avg = np.mean(corrs) if corrs else 0
        sig = " ★★★" if abs(avg) > 0.1 else (" ★★" if abs(avg) > 0.05 else "")
        print(f"  corr(δe[r], δa[r+{lag}]): {avg:+.4f}{sig}")
        if lag == 1:
            print(f"    ↑ THIS is the T1 coupling (e→a via Σ₁+Ch)")

def test_equilibrium_shift(N=300):
    """Does a dip in δa SHIFT the equilibrium for subsequent rounds?"""
    print(f"\n{'='*60}")
    print(f"EQUILIBRIUM SHIFT after δa dip")
    print(f"{'='*60}")

    # After δa < 10: measure the AVERAGE δ(a,e) for the next 10 rounds
    # Compare with unconditional average (32)

    post_dip_avgs = {k: [] for k in range(1, 15)}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        da, de = get_ae_trace(M1, M2)

        for r in range(30, 50):
            if da[r] < 10:
                for k in range(1, 15):
                    if r + k <= 64:
                        post_dip_avgs[k].append(da[r+k] + de[r+k])

    print(f"\n  Average δ(a,e) at round r+k AFTER δa[r] < 10:")
    print(f"  {'k':>3} | {'E[δ(a,e)]':>10} | {'vs equilibrium':>14} | Signal")
    print(f"  " + "-" * 45)

    for k in range(1, 15):
        if post_dip_avgs[k]:
            avg = np.mean(post_dip_avgs[k])
            diff = avg - 32
            z = diff / math.sqrt(32 / max(len(post_dip_avgs[k]), 1))
            sig = " ★★★" if abs(z) > 5 else (" ★★" if abs(z) > 3 else "")
            marker = ""
            if k == 3: marker = " ← shift delay"
            if k == 4: marker = " ← shift+1"
            print(f"  {k:>3} | {avg:>10.2f} | {diff:>+14.2f} | Z={z:+.1f}{sig}{marker}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 195: SELF-AMPLIFYING CYCLE")
    print("=" * 60)

    test_dip_propagation(N=400)
    test_correlation_at_lag3(N=400)
    test_equilibrium_shift(N=300)
    test_cycle_detection(N=200)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
