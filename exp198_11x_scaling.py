#!/usr/bin/env python3
"""
EXP 198: DOES 11× ADVANTAGE SCALE?

exp197: P(dH<105) = 11× higher for W[15]b31 structured pairs.
= 3.5 bits advantage. If stable → 2^124.5 instead of 2^128.

CRITICAL TESTS:
1. Is 11× real or small-sample artifact? (test at N=20000)
2. Does advantage GROW at lower thresholds? (dH<100, 95, 90?)
3. Does advantage persist across different δM choices?
4. SCALING: advantage at budget 1K, 5K, 20K, 100K
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_11x_large_sample(N=30000):
    """Is 11× real at large N?"""
    print(f"\n{'='*60}")
    print(f"TEST 1: LARGE SAMPLE VERIFICATION (N={N})")
    print(f"{'='*60}")

    struct_dH = []; rand_dH = []

    t0 = time.time()
    for _ in range(N):
        M1 = random_w16()

        # Structured: W[15]b31
        M2s = list(M1); M2s[15] ^= (1 << 31)
        H1 = sha256_compress(M1); H2s = sha256_compress(M2s)
        struct_dH.append(sum(hw(H1[w] ^ H2s[w]) for w in range(8)))

        # Random
        M2r = random_w16()
        H2r = sha256_compress(M2r)
        rand_dH.append(sum(hw(H1[w] ^ H2r[w]) for w in range(8)))
    t1 = time.time()

    sa = np.array(struct_dH); ra = np.array(rand_dH)

    print(f"\n  N = {N} ({t1-t0:.1f}s)")
    print(f"  Structured (W[15]b31): mean={sa.mean():.2f}, std={sa.std():.2f}")
    print(f"  Random:                mean={ra.mean():.2f}, std={ra.std():.2f}")

    print(f"\n  {'Threshold':>10} | {'Structured':>10} | {'Random':>10} | {'Ratio':>8} | {'Log₂':>6}")
    print(f"  " + "-" * 55)

    for k in [125, 120, 115, 110, 105, 100, 95]:
        ps = np.mean(sa < k); pr = np.mean(ra < k)
        ratio = ps / pr if pr > 0 else float('inf')
        log_ratio = math.log2(ratio) if ratio > 0 and ratio < float('inf') else 0
        sig = " ★" if ratio > 2 else ""
        print(f"  dH<{k:>4}   | {ps:>10.6f} | {pr:>10.6f} | {ratio:>8.2f} | {log_ratio:>+5.1f}{sig}")

def test_different_dM(N=10000):
    """Does advantage persist for other δM choices?"""
    print(f"\n{'='*60}")
    print(f"TEST 2: DIFFERENT δM PATTERNS (N={N})")
    print(f"{'='*60}")

    patterns = [
        ("W[15]b31", lambda M: M[:15] + [M[15] ^ (1<<31)]),
        ("W[15]b0", lambda M: M[:15] + [M[15] ^ 1]),
        ("W[14]b15", lambda M: M[:14] + [M[14] ^ (1<<15)] + M[15:]),
        ("W[13]b16", lambda M: M[:13] + [M[13] ^ (1<<16)] + M[14:]),
        ("W[0]b15", lambda M: [M[0] ^ (1<<15)] + M[1:]),
        ("W[7]b16", lambda M: M[:7] + [M[7] ^ (1<<16)] + M[8:]),
    ]

    # Random baseline
    rand_dH = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        rand_dH.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))
    ra = np.array(rand_dH)
    p_rand_105 = np.mean(ra < 105)

    print(f"\n  Random baseline: P(dH<105) = {p_rand_105:.6f}")
    print(f"\n  {'Pattern':>12} | {'P(dH<105)':>10} | {'Ratio vs random':>15} | {'Log₂':>6}")
    print(f"  " + "-" * 50)

    for name, make_M2 in patterns:
        dHs = []
        for _ in range(N):
            M1 = random_w16(); M2 = make_M2(list(M1))
            H1 = sha256_compress(M1); H2 = sha256_compress(M2)
            dHs.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

        p = np.mean(np.array(dHs) < 105)
        ratio = p / p_rand_105 if p_rand_105 > 0 else 0
        log_r = math.log2(ratio) if ratio > 0 else 0
        sig = " ★" if ratio > 2 else ""
        print(f"  {name:>12} | {p:>10.6f} | {ratio:>15.2f} | {log_r:>+5.1f}{sig}")

def test_birthday_scaling(trials=15):
    """Does structured birthday find closer pairs than random birthday?"""
    print(f"\n{'='*60}")
    print(f"TEST 3: BIRTHDAY SCALING (trials={trials})")
    print(f"{'='*60}")

    for budget in [1000, 5000, 20000]:
        struct_mins = []; rand_mins = []

        for _ in range(trials):
            # Structured birthday: many W[15]b31 pairs
            best_s = 256
            hashes_s = {}
            for _ in range(budget):
                M1 = random_w16()
                M2 = list(M1); M2[15] ^= (1 << 31)
                H1 = sha256_compress(M1); H2 = sha256_compress(M2)

                # Direct pair
                d = sum(hw(H1[w] ^ H2[w]) for w in range(8))
                best_s = min(best_s, d)

                # Multi-target
                hk = tuple(H1)
                for h_old in list(hashes_s.keys())[-20:]:
                    if h_old != hk:
                        dd = sum(hw(H1[w] ^ list(h_old)[w]) for w in range(8))
                        best_s = min(best_s, dd)
                hashes_s[hk] = 1

            struct_mins.append(best_s)

            # Random birthday (same budget × 2 hashes = fair)
            best_r = 256
            hashes_r = {}
            for _ in range(budget * 2):
                M = random_w16()
                H = sha256_compress(M)
                hk = tuple(H)
                for h_old in list(hashes_r.keys())[-20:]:
                    if h_old != hk:
                        dd = sum(hw(H[w] ^ list(h_old)[w]) for w in range(8))
                        best_r = min(best_r, dd)
                hashes_r[hk] = 1

            rand_mins.append(best_r)

        sm = np.array(struct_mins); rm = np.array(rand_mins)
        gain = rm.mean() - sm.mean()

        print(f"\n  Budget {budget:>6} (struct: {budget} pairs + multi, random: {budget*2} msgs):")
        print(f"    Structured: avg min dH = {sm.mean():.1f}, best = {sm.min()}")
        print(f"    Random:     avg min dH = {rm.mean():.1f}, best = {rm.min()}")
        print(f"    Gain: {gain:+.1f} bits")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 198: DOES 11× SCALE?")
    print("=" * 60)

    test_11x_large_sample(N=20000)
    test_different_dM(N=8000)
    test_birthday_scaling(trials=12)

    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: Is the 11× real and scalable?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
