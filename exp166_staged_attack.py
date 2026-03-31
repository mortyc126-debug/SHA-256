#!/usr/bin/env python3
"""
EXP 166: STAGED ATTACK — From Weakest to Strongest

Not frontal: attack SHA-256 LAYER BY LAYER.

Layer 0: SCHEDULE (linear) — find δM with favorable δW pattern
Layer 1: ROUNDS 0-3 (kill chain) — use favorable δW for +27 bits
Layer 2: ROUNDS 4-20 (rising decorrelation) — enter with advantage
Layer 3: ROUNDS 21-64 (full chaos) — ride the ★-structure
Layer 4: FEEDFORWARD — exploit blind spots

STAGED PIPELINE:
  Stage A: Schedule optimization → find δM with min schedule weight
  Stage B: Among good schedules → pick those where kill chain works
  Stage C: Among kill chain survivors → birthday on remaining bits
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def gf2_schedule_diff(dM):
    """GF(2)-linear schedule difference."""
    dW = list(dM) + [0] * 48
    for t in range(16, 64):
        dW[t] = sig1(dW[t-2]) ^ dW[t-7] ^ sig0(dW[t-15]) ^ dW[t-16]
    return dW

def schedule_weight(dM):
    """Total XOR-weight of schedule difference."""
    dW = gf2_schedule_diff(dM)
    return sum(hw(dW[t]) for t in range(64))

def early_round_distance(M1, M2, R=4):
    """State XOR distance after R rounds."""
    s1 = sha256_rounds(M1, R)[R]
    s2 = sha256_rounds(M2, R)[R]
    return sum(hw(s1[w] ^ s2[w]) for w in range(8))

def full_hash_distance(M1, M2):
    H1 = sha256_compress(M1); H2 = sha256_compress(M2)
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

# ============================================================
# STAGE A: SCHEDULE OPTIMIZATION
# ============================================================
def stage_A_schedule(n_candidates=500):
    """Find δM with minimum schedule weight."""
    candidates = []

    for _ in range(n_candidates):
        # Random 1-3 bit difference
        dM = [0] * 16
        n_bits = random.randint(1, 3)
        for _ in range(n_bits):
            w = random.randint(0, 15)
            b = random.randint(0, 31)
            dM[w] ^= (1 << b)
        if all(d == 0 for d in dM):
            continue

        sw = schedule_weight(dM)
        candidates.append((sw, list(dM)))

    candidates.sort()
    return candidates

# ============================================================
# STAGE B: KILL CHAIN FILTER
# ============================================================
def stage_B_kill_chain(M_base, dM_candidates, budget_per_candidate=50):
    """Among schedule-optimized δM: which gives best early-round distance?"""
    results = []

    for sw, dM in dM_candidates[:50]:  # Top 50 schedules
        # Try several M_base values with this δM
        best_r4 = 256
        for _ in range(budget_per_candidate):
            M1 = random_w16()
            M2 = [(M1[w] ^ dM[w]) for w in range(16)]
            d_r4 = early_round_distance(M1, M2, R=4)
            if d_r4 < best_r4:
                best_r4 = d_r4

        results.append((best_r4, sw, dM))

    results.sort()
    return results

# ============================================================
# STAGE C: FULL HASH BIRTHDAY WITH STRUCTURED PAIRS
# ============================================================
def stage_C_birthday(dM_best, budget=3000):
    """Birthday search using the BEST δM from stages A+B."""
    _, _, dM = dM_best

    best_dH = 256
    hashes_M1 = {}

    for _ in range(budget):
        M1 = random_w16()
        M2 = [(M1[w] ^ dM[w]) for w in range(16)]

        H1 = sha256_compress(M1)
        H2 = sha256_compress(M2)

        # Check M1 vs M2 (structured pair)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        if dH < best_dH:
            best_dH = dH

        # Also birthday M1 against stored
        hk = tuple(H1)
        for h_old in list(hashes_M1.keys())[-20:]:
            dd = sum(hw(H1[w] ^ list(h_old)[w]) for w in range(8))
            if dd < best_dH:
                best_dH = dd

        hashes_M1[hk] = M1

    return best_dH

def test_staged_attack(N=15, budget=3000):
    """Full staged attack pipeline."""
    print(f"\n{'='*60}")
    print(f"STAGED ATTACK PIPELINE (N={N})")
    print(f"{'='*60}")

    staged_results = []
    random_results = []

    for trial in range(N):
        # STAGE A: Find best schedule differences
        candidates = stage_A_schedule(300)
        top_sw = candidates[0][0]

        # STAGE B: Kill chain filter
        filtered = stage_B_kill_chain(None, candidates, budget_per_candidate=30)
        top_r4 = filtered[0][0]

        # STAGE C: Birthday with best δM
        best_dH = stage_C_birthday(filtered[0], budget=budget)
        staged_results.append(best_dH)

        # RANDOM BASELINE (same total budget)
        # Budget: 300 (stage A) + 50*30 (stage B) + budget (stage C)
        total_budget = 300 + 1500 + budget
        best_rand = 256
        M_base = random_w16()
        H_base = sha256_compress(M_base)
        for _ in range(total_budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H_base[w] ^ H2[w]) for w in range(8))
            if dH < best_rand:
                best_rand = dH
        random_results.append(best_rand)

        if trial < 3:
            print(f"  Trial {trial}: schedule_wt={top_sw}, r4_dist={top_r4}, "
                  f"staged_dH={best_dH}, random_dH={best_rand}")

    sa = np.array(staged_results)
    ra = np.array(random_results)
    gain = ra.mean() - sa.mean()

    print(f"\n  RESULTS:")
    print(f"    Staged:  avg={sa.mean():.1f}, min={sa.min()}")
    print(f"    Random:  avg={ra.mean():.1f}, min={ra.min()}")
    print(f"    Gain: {gain:+.1f} bits")

    if gain > 2:
        print(f"    ★★★ STAGED ATTACK WINS BY {gain:.1f} BITS!")

    return sa, ra

def test_layer_analysis(N=200):
    """Which LAYER contributes most to the staged advantage?"""
    print(f"\n{'='*60}")
    print(f"LAYER CONTRIBUTION ANALYSIS")
    print(f"{'='*60}")

    # Test: does schedule weight predict hash distance?
    sws = []; dHs_r4 = []; dHs_full = []
    for _ in range(N):
        M1 = random_w16()
        # Random 1-bit diff
        M2 = list(M1)
        w = random.randint(0, 15); b = random.randint(0, 31)
        M2[w] ^= (1 << b)

        dM = [M1[i] ^ M2[i] for i in range(16)]
        sw = schedule_weight(dM)
        d_r4 = early_round_distance(M1, M2, R=4)
        d_full = full_hash_distance(M1, M2)

        sws.append(sw); dHs_r4.append(d_r4); dHs_full.append(d_full)

    sw_arr = np.array(sws); r4_arr = np.array(dHs_r4); full_arr = np.array(dHs_full)

    print(f"\n  Layer correlations (1-bit diff):")
    print(f"    corr(schedule_wt, dH_r4):   {np.corrcoef(sw_arr, r4_arr)[0,1]:+.4f}")
    print(f"    corr(schedule_wt, dH_full):  {np.corrcoef(sw_arr, full_arr)[0,1]:+.4f}")
    print(f"    corr(dH_r4, dH_full):        {np.corrcoef(r4_arr, full_arr)[0,1]:+.4f}")

    # Binned: do low-schedule-weight diffs produce lower dH?
    p25 = np.percentile(sw_arr, 25)
    low_sw = full_arr[sw_arr <= p25].mean()
    high_sw = full_arr[sw_arr >= np.percentile(sw_arr, 75)].mean()
    print(f"\n    Low schedule weight (P25):  E[dH_full] = {low_sw:.1f}")
    print(f"    High schedule weight (P75): E[dH_full] = {high_sw:.1f}")

    # Same for dH_r4
    p25_r4 = np.percentile(r4_arr, 25)
    low_r4 = full_arr[r4_arr <= p25_r4].mean()
    high_r4 = full_arr[r4_arr >= np.percentile(r4_arr, 75)].mean()
    print(f"\n    Low dH_r4 (P25):  E[dH_full] = {low_r4:.1f}")
    print(f"    High dH_r4 (P75): E[dH_full] = {high_r4:.1f}")

def test_schedule_as_weapon(N=20, budget=3000):
    """Use ONLY schedule optimization (no kill chain, no birthday tricks)."""
    print(f"\n{'='*60}")
    print(f"SCHEDULE-ONLY WEAPON")
    print(f"{'='*60}")

    # Find THE best 1-bit δM (lowest schedule weight)
    all_1bit = []
    for w in range(16):
        for b in range(32):
            dM = [0] * 16; dM[w] = 1 << b
            sw = schedule_weight(dM)
            all_1bit.append((sw, w, b))
    all_1bit.sort()

    best_dM_info = all_1bit[0]
    worst_dM_info = all_1bit[-1]

    print(f"  Best 1-bit δM: W[{best_dM_info[1]}] bit {best_dM_info[2]}, "
          f"schedule_wt = {best_dM_info[0]}")
    print(f"  Worst 1-bit δM: W[{worst_dM_info[1]}] bit {worst_dM_info[2]}, "
          f"schedule_wt = {worst_dM_info[0]}")

    # Test: pairs with best vs worst schedule → full hash distance
    best_dHs = []; worst_dHs = []; random_dHs = []

    for _ in range(N):
        M1 = random_w16()

        # Best schedule δM
        M2_best = list(M1)
        M2_best[best_dM_info[1]] ^= (1 << best_dM_info[2])
        best_dHs.append(full_hash_distance(M1, M2_best))

        # Worst schedule δM
        M2_worst = list(M1)
        M2_worst[worst_dM_info[1]] ^= (1 << worst_dM_info[2])
        worst_dHs.append(full_hash_distance(M1, M2_worst))

        # Random pair
        M2_rand = random_w16()
        random_dHs.append(full_hash_distance(M1, M2_rand))

    ba = np.array(best_dHs); wa = np.array(worst_dHs); ra = np.array(random_dHs)

    print(f"\n  Full hash distance:")
    print(f"    Best schedule δM:  E[dH] = {ba.mean():.2f} ± {ba.std():.2f}")
    print(f"    Worst schedule δM: E[dH] = {wa.mean():.2f} ± {wa.std():.2f}")
    print(f"    Random pair:       E[dH] = {ra.mean():.2f} ± {ra.std():.2f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 166: STAGED ATTACK — WEAKEST LINK FIRST")
    print("=" * 60)

    test_schedule_as_weapon(N=50)
    test_layer_analysis(N=300)
    test_staged_attack(N=12, budget=2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Staged Attack")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
