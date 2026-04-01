#!/usr/bin/env python3
"""
EXP 184: PENDULUM — Can δ(a,e) swing out and COME BACK?

exp183: δ(a,e)=2 at round 16, grows to 32 by round 20.
What if it RETURNS to low values at some later round?

Like a pendulum: δ swings up (rounds 16-30),
then comes back down (rounds 30-64)?

SEARCH: Among many δM, find those where δ(a,e) has a SECOND MINIMUM
at rounds 40-64 (after the initial explosion).

If δ(a,e) can return to <10 at ANY round 40+ →
that's a near-convergence deep in the dead zone.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def ae_trajectory(M1, M2, max_r=64):
    """Full δ(a,e) trajectory."""
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)
    traj = []
    for r in range(max_r + 1):
        da = hw(s1[r][0] ^ s2[r][0])
        de = hw(s1[r][4] ^ s2[r][4])
        traj.append(da + de)
    return traj

def search_pendulum(N=2000):
    """Search for δM where δ(a,e) has a second minimum after round 30."""
    print(f"\n{'='*60}")
    print(f"PENDULUM SEARCH: δ(a,e) return (N={N})")
    print(f"{'='*60}")

    best_late_min = 64
    best_late_round = -1
    best_pair = None
    all_late_mins = []

    for trial in range(N):
        M1 = random_w16()

        # Various δM
        for dtype in range(4):
            M2 = list(M1)
            if dtype == 0:
                M2[15] ^= (1 << 31)  # W[15]b31 (best from exp183)
            elif dtype == 1:
                M2[15] ^= (1 << random.randint(0, 31))
            elif dtype == 2:
                M2[random.randint(12, 15)] ^= (1 << random.randint(0, 31))
            else:
                # 2-3 bit changes in late words
                for _ in range(random.randint(2, 3)):
                    w = random.randint(10, 15)
                    b = random.randint(0, 31)
                    M2[w] ^= (1 << b)

            if M1 == M2: continue
            traj = ae_trajectory(M1, M2)

            # Find minimum δ(a,e) in rounds 35-64
            late_min = 64
            late_min_r = 35
            for r in range(35, 65):
                if traj[r] < late_min:
                    late_min = traj[r]
                    late_min_r = r

            all_late_mins.append(late_min)

            if late_min < best_late_min:
                best_late_min = late_min
                best_late_round = late_min_r
                best_pair = (list(M1), list(M2))

    alm = np.array(all_late_mins)
    print(f"\n  Late minimum δ(a,e) distribution (rounds 35-64):")
    print(f"    Mean: {alm.mean():.1f}")
    print(f"    Min:  {alm.min()}")
    print(f"    Std:  {alm.std():.1f}")

    for thresh in [25, 20, 15, 10, 5]:
        count = np.sum(alm <= thresh)
        if count > 0:
            print(f"    δ(a,e) ≤ {thresh}: {count}/{len(alm)} ({count/len(alm)*100:.2f}%)")

    print(f"\n  BEST PENDULUM:")
    print(f"    Late min δ(a,e) = {best_late_min} at round {best_late_round}")

    if best_pair:
        M1, M2 = best_pair
        traj = ae_trajectory(M1, M2)

        print(f"\n    Full trajectory:")
        for r in range(0, 65, 1 if r < 20 or best_late_round - 5 <= r <= best_late_round + 5 else 4):
            marker = " ★" if traj[r] <= best_late_min + 2 and r >= 35 else ""
            if r <= 20 or r >= 30 or r % 4 == 0:
                print(f"      Round {r:>2}: δ(a,e) = {traj[r]:>3}{marker}")

    return best_late_min, alm

def search_deep_pendulum(N=5000):
    """Larger search focused on finding δ(a,e) < 20 at rounds 50+."""
    print(f"\n{'='*60}")
    print(f"DEEP PENDULUM SEARCH (N={N})")
    print(f"{'='*60}")

    best = 64; best_round = -1; best_pair = None

    for _ in range(N):
        M1 = random_w16()
        M2 = list(M1)

        # Mix of strategies
        strategy = random.randint(0, 5)
        if strategy <= 2:
            # Late word change
            w = random.randint(12, 15)
            M2[w] ^= (1 << random.randint(0, 31))
        elif strategy == 3:
            # Multi-bit in one late word
            w = random.randint(13, 15)
            M2[w] = random.randint(0, MASK)
        elif strategy == 4:
            # Two late words
            M2[14] ^= (1 << random.randint(0, 31))
            M2[15] ^= (1 << random.randint(0, 31))
        else:
            # Arithmetic
            w = random.randint(12, 15)
            M2[w] = (M2[w] + random.randint(1, 256)) & MASK

        if M1 == M2: continue

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        # Check ONLY late rounds (speed)
        for r in range(50, 65):
            d = hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4])
            if d < best:
                best = d; best_round = r
                best_pair = (list(M1), list(M2))

    print(f"\n  Best δ(a,e) at rounds 50-64: {best} at round {best_round}")

    if best_pair and best < 25:
        M1, M2 = best_pair
        traj = ae_trajectory(M1, M2)
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        print(f"\n  BEST TRAJECTORY (key rounds):")
        for r in [0, 4, 8, 12, 16, 20, 30, 40, 50, 55, 60, 62, 63, 64]:
            d_ae = traj[r]
            d_full = sum(hw(s1[r][w] ^ s2[r][w]) for w in range(8))
            marker = " ★★★" if d_ae <= best + 2 and r >= 50 else ""
            print(f"    Round {r:>2}: δ(a,e)={d_ae:>3}, full_dH={d_full:>3}{marker}")

        # Hash distance
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        print(f"\n    HASH distance: {dH}")

    return best

def statistical_pendulum_analysis(N=1000):
    """How often does δ(a,e) dip below various thresholds at late rounds?"""
    print(f"\n{'='*60}")
    print(f"STATISTICAL: P(δ(a,e) < k) at late rounds (N={N})")
    print(f"{'='*60}")

    # For random 1-bit δM in W[15]:
    dips = {r: [] for r in range(50, 65)}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        for r in range(50, 65):
            d = hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4])
            dips[r].append(d)

    print(f"\n  P(δ(a,e) < k) per round, 1-bit diff W[15]:")
    print(f"  Round |  E[δ] | P(<25) | P(<20) | P(<15) | P(<10)")
    print(f"  " + "-" * 55)

    for r in range(50, 65):
        arr = np.array(dips[r])
        p25 = np.mean(arr < 25); p20 = np.mean(arr < 20)
        p15 = np.mean(arr < 15); p10 = np.mean(arr < 10)
        print(f"  {r:>5} | {arr.mean():>5.1f} | {p25:>6.4f} | {p20:>6.4f} | {p15:>6.4f} | {p10:>6.4f}")

    # Expected for RANDOM pair: each bit independent, E[δ]=32
    # P(δ<k) = P(binomial(64, 0.5) < k)
    print(f"\n  Random pair comparison:")
    from scipy.stats import binom
    for k in [25, 20, 15, 10]:
        p = binom.cdf(k, 64, 0.5)
        print(f"    P(binomial(64,0.5) < {k}) = {p:.6f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 184: PENDULUM — δ(a,e) RETURN?")
    print("=" * 60)

    t0 = time.time()
    best1, dist1 = search_pendulum(N=1500)
    best2 = search_deep_pendulum(N=3000)
    statistical_pendulum_analysis(N=800)
    t1 = time.time()

    print(f"\n  Time: {t1-t0:.1f}s")
    print(f"\n{'='*60}")
    print(f"VERDICT: Does the pendulum return?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
