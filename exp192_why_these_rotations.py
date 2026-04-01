#!/usr/bin/env python3
"""
EXP 192: WHY THESE 4 ROTATIONS? — Level 8 of SHA-256

12 rotation numbers in SHA-256: 2,3,6,7,10,11,13,17,18,19,22,25
Only 4 left fingerprints: 2, 17, 18, 19
WHY these 4? What makes them special?

HYPOTHESIS: They're from the LAST operations before the output.
  a_new = T1 + T2 where T2 = Σ₀(a) + Maj(a,b,c)
  Σ₀ uses ROTR_2 → dist=2 survives

  e_new = d + T1 where T1 uses Σ₁(e) with ROTR_6,11,25
  BUT σ₁ uses ROTR_17,19 in schedule → dist=17,19 from schedule!
  σ₀ uses ROTR_18 → dist=18 from schedule!

The fingerprints come from the SCHEDULE, not the round function!
Schedule rotations (17,18,19) dominate over round rotations (6,11,25).

WHY? Because schedule is CLOSER to the message (less mixing).
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_diff_vector(s1, s2):
    vec = np.zeros(64, dtype=int)
    for b in range(32):
        vec[b] = ((s1[0] >> b) & 1) ^ ((s2[0] >> b) & 1)
        vec[32+b] = ((s1[4] >> b) & 1) ^ ((s2[4] >> b) & 1)
    return vec

def test_all_rotation_distances(N=400):
    """Measure correlation at EVERY rotation distance 0-31."""
    print(f"\n{'='*60}")
    print(f"ALL 32 ROTATION DISTANCES — Which are special?")
    print(f"{'='*60}")

    X_all = []; Y_all = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(30, 63):
            X_all.append(get_diff_vector(s1[r], s2[r]))
            Y_all.append(get_diff_vector(s1[r+1], s2[r+1]))

    X = np.array(X_all, dtype=float); Y = np.array(Y_all, dtype=float)

    # For each rotation distance d: average |corr| between bits separated by d
    # Within a-word (bits 0-31) and within e-word (bits 32-63)

    print(f"\n  {'Dist':>4} | {'a→a corr':>9} | {'e→e corr':>9} | {'Total':>7} | SHA-256 rotation?")
    print(f"  " + "-" * 60)

    all_dist_corrs = {}
    for dist in range(32):
        a_corrs = []; e_corrs = []

        for b in range(32):
            b2 = (b + dist) % 32

            # a-word: X[b] → Y[b2]
            c_a = np.corrcoef(X[:, b], Y[:, b2])[0, 1]
            if not np.isnan(c_a): a_corrs.append(abs(c_a))

            # e-word: X[32+b] → Y[32+b2]
            c_e = np.corrcoef(X[:, 32+b], Y[:, 32+b2])[0, 1]
            if not np.isnan(c_e): e_corrs.append(abs(c_e))

        avg_a = np.mean(a_corrs) if a_corrs else 0
        avg_e = np.mean(e_corrs) if e_corrs else 0
        total = avg_a + avg_e

        # Which SHA-256 rotation?
        rot_label = ""
        if dist == 2: rot_label = "Σ₀(2)"
        elif dist == 13: rot_label = "Σ₀(13)"
        elif dist == 22: rot_label = "Σ₀(22)"
        elif dist == 6: rot_label = "Σ₁(6)"
        elif dist == 11: rot_label = "Σ₁(11)"
        elif dist == 25: rot_label = "Σ₁(25)"
        elif dist == 7: rot_label = "σ₀(7)"
        elif dist == 18: rot_label = "σ₀(18)"
        elif dist == 3: rot_label = "σ₀(3)/SHR₃"
        elif dist == 17: rot_label = "σ₁(17)"
        elif dist == 19: rot_label = "σ₁(19)"
        elif dist == 10: rot_label = "σ₁(10)/SHR₁₀"

        marker = " ★" if rot_label else ""
        all_dist_corrs[dist] = total
        print(f"  {dist:>4} | {avg_a:>9.5f} | {avg_e:>9.5f} | {total:>7.5f} | {rot_label}{marker}")

    # Rank ALL distances
    ranked = sorted(all_dist_corrs.items(), key=lambda x: -x[1])
    print(f"\n  TOP 8 rotation distances (by total correlation):")
    for dist, total in ranked[:8]:
        rot = ""
        if dist in [2,13,22]: rot = f"Σ₀({dist})"
        elif dist in [6,11,25]: rot = f"Σ₁({dist})"
        elif dist in [7,18,3]: rot = f"σ₀({dist})"
        elif dist in [17,19,10]: rot = f"σ₁({dist})"
        print(f"    dist={dist:>2}: total={total:.5f} {rot}")

    # Are SHA-256 rotation distances HIGHER than non-rotation?
    sha_dists = [2,3,6,7,10,11,13,17,18,19,22,25]
    sha_vals = [all_dist_corrs[d] for d in sha_dists]
    non_sha = [all_dist_corrs[d] for d in range(32) if d not in sha_dists]

    print(f"\n  SHA-256 rotation distances: avg = {np.mean(sha_vals):.6f}")
    print(f"  Non-rotation distances:     avg = {np.mean(non_sha):.6f}")
    ratio = np.mean(sha_vals) / np.mean(non_sha) if np.mean(non_sha) > 0 else 0
    print(f"  Ratio: {ratio:.4f}")

    if ratio > 1.05:
        print(f"  ★★★ SHA-256 rotations are {(ratio-1)*100:.1f}% MORE correlated!")

def test_schedule_vs_round(N=300):
    """Are schedule rotations (σ) stronger than round rotations (Σ)?"""
    print(f"\n{'='*60}")
    print(f"SCHEDULE vs ROUND ROTATIONS")
    print(f"{'='*60}")

    # Compare: σ₀(7,18,3) + σ₁(17,19,10) vs Σ₀(2,13,22) + Σ₁(6,11,25)

    X_all = []; Y_all = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(30, 63):
            X_all.append(get_diff_vector(s1[r], s2[r]))
            Y_all.append(get_diff_vector(s1[r+1], s2[r+1]))

    X = np.array(X_all, dtype=float); Y = np.array(Y_all, dtype=float)

    schedule_rots = [3, 7, 10, 17, 18, 19]  # σ₀, σ₁
    round_rots = [2, 6, 11, 13, 22, 25]     # Σ₀, Σ₁

    def avg_corr_at_dists(dists):
        corrs = []
        for dist in dists:
            for b in range(32):
                b2 = (b + dist) % 32
                c = np.corrcoef(X[:, b], Y[:, b2])[0, 1]
                if not np.isnan(c): corrs.append(abs(c))
                c = np.corrcoef(X[:, 32+b], Y[:, 32+b2])[0, 1]
                if not np.isnan(c): corrs.append(abs(c))
        return np.mean(corrs) if corrs else 0

    sched_corr = avg_corr_at_dists(schedule_rots)
    round_corr = avg_corr_at_dists(round_rots)
    random_corr = avg_corr_at_dists([1, 4, 5, 8, 9, 14, 15, 16, 20, 21])

    print(f"\n  Schedule rotations (σ₀,σ₁): avg |corr| = {sched_corr:.6f}")
    print(f"  Round rotations (Σ₀,Σ₁):    avg |corr| = {round_corr:.6f}")
    print(f"  Non-rotation distances:      avg |corr| = {random_corr:.6f}")

    if sched_corr > round_corr:
        excess = (sched_corr - round_corr) / round_corr * 100
        print(f"\n  ★★ SCHEDULE rotations {excess:.1f}% STRONGER than round rotations!")
        print(f"  The schedule's σ leaves deeper fingerprints than the round's Σ.")

def test_which_round_creates_fingerprint(N=200):
    """At which ROUND does each fingerprint first appear?"""
    print(f"\n{'='*60}")
    print(f"WHEN DO FINGERPRINTS APPEAR?")
    print(f"{'='*60}")

    target_dists = [2, 17, 18, 19]

    for dist in target_dists:
        print(f"\n  dist={dist}:")
        for R_target in [5, 10, 15, 20, 30, 40, 50, 63]:
            corrs = []
            for _ in range(N):
                M1 = random_w16(); M2 = list(M1)
                M2[15] ^= (1 << random.randint(0, 31))
                s1 = sha256_rounds(M1, R_target+1)
                s2 = sha256_rounds(M2, R_target+1)

                v1 = get_diff_vector(s1[R_target], s2[R_target])
                v2 = get_diff_vector(s1[R_target+1], s2[R_target+1])

                for b in range(32):
                    b2 = (b + dist) % 32
                    c = np.corrcoef([v1[b]], [v2[b2]])[0, 1] if len(set([v1[b]])) > 1 else 0
                    # Single sample — need batch
                    pass

            # Batch computation
            X_batch = []; Y_batch = []
            for _ in range(N):
                M1 = random_w16(); M2 = list(M1)
                M2[15] ^= (1 << random.randint(0, 31))
                s1 = sha256_rounds(M1, min(R_target+1, 64))
                s2 = sha256_rounds(M2, min(R_target+1, 64))
                if R_target < 64:
                    X_batch.append(get_diff_vector(s1[R_target], s2[R_target]))
                    Y_batch.append(get_diff_vector(s1[min(R_target+1,64)], s2[min(R_target+1,64)]))

            if X_batch:
                Xb = np.array(X_batch); Yb = np.array(Y_batch)
                batch_corrs = []
                for b in range(32):
                    b2 = (b + dist) % 32
                    c = np.corrcoef(Xb[:, b], Yb[:, b2])[0, 1]
                    if not np.isnan(c): batch_corrs.append(abs(c))
                avg = np.mean(batch_corrs) if batch_corrs else 0
                sig = " ★" if avg > 0.02 else ""
                print(f"    Round {R_target:>2}: avg |corr| = {avg:.5f}{sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 192: WHY THESE 4 ROTATIONS?")
    print("=" * 60)

    test_all_rotation_distances(N=300)
    test_schedule_vs_round(N=200)
    test_which_round_creates_fingerprint(N=100)

    print(f"\n{'='*60}")
    print(f"VERDICT: Level 8 — Origin of fingerprints")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
