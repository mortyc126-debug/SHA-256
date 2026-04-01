#!/usr/bin/env python3
"""
EXP 183: COMPENSATION SEARCH — Can δW cancel δ(a,e)?

From recurrence: δe[r+1] = δa[r-3] + δe[r-3] + δΣ₁ + δCh + δW[r]
If δW[r] = -(δa[r-3] + δe[r-3] + δΣ₁ + δCh) → δe[r+1] = 0

Schedule gives us δW[r] for FREE from δM.
Question: for which δM does δW[r] happen to CANCEL the accumulated δ?

This is a MEETING condition: the schedule difference meets the
state difference at the right value, at the right round.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def gf2_schedule_diff(dM):
    dW = list(dM) + [0] * 48
    for t in range(16, 64):
        dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]
    return dW

def measure_compensation(M1, M2, verbose=False):
    """For each round: how close does δW come to cancelling δ(a,e)?"""
    s1_all = sha256_rounds(M1, 64)
    s2_all = sha256_rounds(M2, 64)
    W1 = schedule(M1); W2 = schedule(M2)

    compensations = []

    for r in range(4, 64):
        # Current δ(a,e)
        da = (s1_all[r][0] - s2_all[r][0]) & MASK
        de = (s1_all[r][4] - s2_all[r][4]) & MASK

        # δW at this round
        dW = (W1[r] - W2[r]) & MASK

        # For δe[r+1] = 0: need δW to cancel accumulated terms
        # δe[r+1] = d[r] + T1_diff
        # Approximate: how close is δW to the "needed" value?
        # Needed δW ≈ -(everything else contributing to δe[r+1])

        # Simple metric: HW of (δa, δe) AFTER this round
        da_next = (s1_all[r+1][0] - s2_all[r+1][0]) & MASK
        de_next = (s1_all[r+1][4] - s2_all[r+1][4]) & MASK

        # Compensation = how much did δ(a,e) DECREASE?
        before = hw(da) + hw(de)
        after = hw(da_next) + hw(de_next)
        comp = before - after  # Positive = δ decreased = compensation worked

        compensations.append(comp)

        if verbose and abs(comp) > 20:
            print(f"    Round {r}: δ(a,e) {before}→{after} (comp={comp:+d})")

    return compensations

def search_best_compensation(N=500):
    """Find δM where compensation is maximized at SOME round."""
    print(f"\n{'='*60}")
    print(f"COMPENSATION SEARCH (N={N})")
    print(f"{'='*60}")

    best_single_comp = -999
    best_total_comp = -999
    best_min_ae = 999
    best_info = None

    for trial in range(N):
        M1 = random_w16()
        # Try different δM patterns
        for dM_type in range(5):
            M2 = list(M1)
            if dM_type == 0:  # 1-bit
                w = random.randint(0, 15); b = random.randint(0, 31)
                M2[w] ^= (1 << b)
            elif dM_type == 1:  # 2-bit
                for _ in range(2):
                    w = random.randint(0, 15); b = random.randint(0, 31)
                    M2[w] ^= (1 << b)
            elif dM_type == 2:  # 1-word
                w = random.randint(0, 15)
                M2[w] = random.randint(0, MASK)
            elif dM_type == 3:  # arithmetic +1
                w = random.randint(0, 15)
                M2[w] = (M2[w] + 1) & MASK
            else:  # random
                M2 = random_w16()

            if M1 == M2: continue

            comps = measure_compensation(M1, M2)

            max_comp = max(comps)
            total_comp = sum(c for c in comps if c > 0)

            # Track minimum δ(a,e) across all rounds
            s1_all = sha256_rounds(M1, 64)
            s2_all = sha256_rounds(M2, 64)
            min_ae = 64
            min_ae_round = 0
            for r in range(4, 64):
                d = hw((s1_all[r][0] ^ s2_all[r][0])) + hw((s1_all[r][4] ^ s2_all[r][4]))
                if d < min_ae:
                    min_ae = d; min_ae_round = r

            if max_comp > best_single_comp:
                best_single_comp = max_comp
            if total_comp > best_total_comp:
                best_total_comp = total_comp
            if min_ae < best_min_ae:
                best_min_ae = min_ae
                best_info = (list(M1), list(M2), min_ae_round, dM_type)

    print(f"\n  Best SINGLE-round compensation: {best_single_comp:+d} bits")
    print(f"  Best TOTAL positive compensation: {best_total_comp:+d} bits")
    print(f"  Best minimum δ(a,e): {best_min_ae} bits at round {best_info[2]}")
    print(f"  (from δM type {best_info[3]})")

    # Show the BEST trajectory
    if best_info:
        M1, M2, _, _ = best_info
        print(f"\n  BEST TRAJECTORY:")
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(0, 64, 4):
            da = hw(s1[r][0] ^ s2[r][0])
            de = hw(s1[r][4] ^ s2[r][4])
            total_ae = da + de
            full_dH = sum(hw(s1[r][w] ^ s2[r][w]) for w in range(8))
            marker = " ★" if total_ae < 20 else ""
            print(f"    Round {r:>2}: δa={da:>3} δe={de:>3} δ(a,e)={total_ae:>3} full_dH={full_dH:>3}{marker}")

    return best_min_ae

def targeted_compensation(N=200):
    """For specific δM: which rounds have best compensation?"""
    print(f"\n{'='*60}")
    print(f"TARGETED COMPENSATION ANALYSIS")
    print(f"{'='*60}")

    # Test specific δM patterns
    patterns = [
        ("W[0] +1", lambda M: [(M[0]+1)&MASK] + M[1:]),
        ("W[0] bit 15", lambda M: [M[0]^(1<<15)] + M[1:]),
        ("W[13] +1", lambda M: M[:13] + [(M[13]+1)&MASK] + M[14:]),
        ("W[15] bit 31", lambda M: M[:15] + [M[15]^(1<<31)]),
    ]

    for name, make_M2 in patterns:
        comp_per_round = np.zeros(60)
        min_ae_per_round = np.zeros(60)

        for _ in range(N):
            M1 = random_w16()
            M2 = make_M2(list(M1))

            s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
            for r in range(4, 64):
                da = hw(s1[r][0] ^ s2[r][0])
                de = hw(s1[r][4] ^ s2[r][4])
                total = da + de

                da1 = hw(s1[r+1][0] ^ s2[r+1][0]) if r < 63 else da
                de1 = hw(s1[r+1][4] ^ s2[r+1][4]) if r < 63 else de
                total1 = da1 + de1

                comp_per_round[r-4] += (total - total1)
                min_ae_per_round[r-4] += total

        comp_per_round /= N
        min_ae_per_round /= N

        # Find round with best compensation
        best_r = np.argmax(comp_per_round) + 4
        best_comp = comp_per_round[best_r - 4]

        # Find round with minimum δ(a,e)
        min_r = np.argmin(min_ae_per_round) + 4
        min_val = min_ae_per_round[min_r - 4]

        print(f"\n  {name}:")
        print(f"    Best compensation: round {best_r}, avg comp = {best_comp:+.2f}")
        print(f"    Min δ(a,e): round {min_r}, avg = {min_val:.1f}")

        # Show trajectory at key rounds
        print(f"    Trajectory: ", end="")
        for r in [4, 8, 12, 16, 20, 32, 48, 63]:
            print(f"r{r}:{min_ae_per_round[r-4]:.0f} ", end="")
        print()

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 183: COMPENSATION SEARCH")
    print("=" * 60)

    best = search_best_compensation(N=300)
    targeted_compensation(N=150)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")
    print(f"  Best minimum δ(a,e) found: {best}/64 bits")
    print(f"  (Collision = 0/64)")

if __name__ == "__main__":
    main()
