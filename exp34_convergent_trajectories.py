#!/usr/bin/env python3
"""
EXP 34: Convergent Trajectories — Fourth Path

NOT collision search.
NOT coupling amplification.
CONVERGENCE: two trajectories that approach each other.

Key insight: Wang cascade forces dist=0 at rounds 3-16,
then dist JUMPS at round 17. What if instead of forcing dist=0,
we allow GRADUAL convergence over ALL 64 rounds?

Instead of:  0,0,0,...,0,JUMP,random,random,...
We aim for:  16,15,14,...,2,1,0,...,0

Gradual transition (7.24 bits/k) tells us: this path EXISTS
in coupling space. Can we realize it in MESSAGE space?

Method: allocate differential budget across ALL rounds,
not just 0-16 (Wang) or 48-64 (late coupling).
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def state_distance(s1, s2):
    """Hamming distance between two 256-bit states."""
    return sum(hw(s1[i] ^ s2[i]) for i in range(8))

def e_branch_distance(s1, s2):
    """Distance in e-branch only (words 4-7)."""
    return sum(hw(s1[i] ^ s2[i]) for i in range(4, 8))

def convergence_profile(Wn, Wf):
    """Measure state distance at every round."""
    sn = sha256_rounds(Wn, 64)
    sf = sha256_rounds(Wf, 64)
    profile = [state_distance(sn[r], sf[r]) for r in range(65)]
    e_profile = [e_branch_distance(sn[r], sf[r]) for r in range(65)]
    return profile, e_profile

def test_wang_convergence_profile(N=2000):
    """Measure convergence profile of Wang cascade pairs."""
    print("\n--- TEST 1: WANG CONVERGENCE PROFILE ---")

    profiles = []
    e_profiles = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        p, ep = convergence_profile(Wn, Wf)
        profiles.append(p)
        e_profiles.append(ep)

    P = np.array(profiles)
    EP = np.array(e_profiles)

    print(f"{'Round':>5} | {'E[dist]':>8} | {'E[e_dist]':>10} | {'Shape'}")
    print("-"*45)
    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,24,32,48,60,64]:
        shape = ""
        if P[:,r].mean() < 5: shape = "ZERO"
        elif P[:,r].mean() < 64: shape = "LOW"
        elif P[:,r].mean() < 120: shape = "TRANSITION"
        else: shape = "RANDOM"
        print(f"{r:>5} | {P[:,r].mean():>8.2f} | {EP[:,r].mean():>10.2f} | {shape}")

    # The "ideal" convergence: monotonically decreasing to 0
    # Wang: drops to 0 at r=3, stays 0 until r=16, then jumps
    # We want: starts high, decreases gradually to 0 at r=64

    return P, EP

def test_partial_wang_tradeoff(N=2000):
    """
    Trade Wang zeros for better late-round convergence.

    Standard Wang: De3..De16=0 using DW[2..15]
    Modified: use fewer DWs for early zeros, save some for late rounds.

    E.g., only force De3..De10=0 (8 zeros, using DW[2..9]),
    then use DW[10..15] for something else (minimize late-round distance).
    """
    print("\n--- TEST 2: PARTIAL WANG TRADEOFF ---")

    # Standard Wang (14 zeros)
    standard_dh = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        standard_dh.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    # Partial Wang: only 8 zeros (De3..De10), then optimize DW[10..15]
    partial_dh = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn = [W0, W1] + [0]*14
        DWs = [0]*16; DWs[0] = 1

        # DW2: force De3=0
        Wf_tmp = [(Wn[i]+DWs[i])&MASK for i in range(16)]
        sn_tmp = sha256_rounds(Wn, 3)
        sf_tmp = sha256_rounds(Wf_tmp, 3)
        DWs[2] = (-de(sn_tmp, sf_tmp, 3)) & MASK

        # DW3..DW9: cascade De4..De10=0
        for step in range(7):
            wi = step+3; dt = step+4
            Wfc = [(Wn[i]+DWs[i])&MASK for i in range(16)]
            tn = sha256_rounds(Wn, dt)
            tf = sha256_rounds(Wfc, dt)
            DWs[wi] = (-de(tn, tf, dt)) & MASK

        # DW10..DW15: OPTIMIZE for minimum FINAL δH (not De=0)
        # Try random values and keep best
        best_dh = 256
        best_DWs = list(DWs)

        for attempt in range(30):
            trial_DWs = list(DWs)
            for w in range(10, 16):
                trial_DWs[w] = random.randint(0, MASK)

            Wf_trial = [(Wn[i]+trial_DWs[i])&MASK for i in range(16)]
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf_trial)
            dh = sum(hw(Hn[i]^Hf[i]) for i in range(8))
            if dh < best_dh:
                best_dh = dh
                best_DWs = trial_DWs

        partial_dh.append(best_dh)

    sa = np.array(standard_dh); pa = np.array(partial_dh)
    print(f"Standard Wang (14 zeros): E[δH]={sa.mean():.2f}, min={sa.min()}")
    print(f"Partial Wang (8 zeros + optimize): E[δH]={pa.mean():.2f}, min={pa.min()}")
    print(f"Difference: {pa.mean()-sa.mean():+.2f}")

    if pa.mean() < sa.mean() - 1:
        print("*** SIGNAL: Partial Wang + optimization beats standard Wang! ***")

def test_monotonic_convergence(N=500):
    """
    Search for pairs with MONOTONICALLY DECREASING state distance.

    Standard Wang: dist = [high, 0, 0, ..., 0, HIGH, random, random]
    Ideal: dist = [128, 124, 120, ..., 4, 0, 0, ...]

    Measure: what fraction of pairs have monotonic segments?
    How long can monotonic convergence last?
    """
    print("\n--- TEST 3: MONOTONIC CONVERGENCE SEARCH ---")

    # For Wang pairs: find longest monotonically decreasing segment
    wang_mono = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        p, _ = convergence_profile(Wn, Wf)

        # Find longest decreasing segment
        max_mono = 0
        current_mono = 0
        for r in range(1, 65):
            if p[r] <= p[r-1]:
                current_mono += 1
                max_mono = max(max_mono, current_mono)
            else:
                current_mono = 0
        wang_mono.append(max_mono)

    # Random pairs
    rand_mono = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        p, _ = convergence_profile(M1, M2)
        max_mono = 0
        current_mono = 0
        for r in range(1, 65):
            if p[r] <= p[r-1]:
                current_mono += 1
                max_mono = max(max_mono, current_mono)
            else:
                current_mono = 0
        rand_mono.append(max_mono)

    wm = np.array(wang_mono); rm = np.array(rand_mono)
    print(f"Wang: E[max_mono]={wm.mean():.2f}, max={wm.max()}")
    print(f"Random: E[max_mono]={rm.mean():.2f}, max={rm.max()}")

    if wm.mean() > rm.mean() + 1:
        print("*** SIGNAL: Wang pairs have longer convergent segments! ***")

    # Is convergence from round 17 onward possible?
    wang_late_mono = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        p, _ = convergence_profile(Wn, Wf)

        # Count consecutive decreasing from round 17
        mono_from_17 = 0
        for r in range(18, 65):
            if p[r] <= p[r-1]:
                mono_from_17 += 1
            else:
                break
        wang_late_mono.append(mono_from_17)

    wlm = np.array(wang_late_mono)
    print(f"\nConvergence from r=17: E[length]={wlm.mean():.2f}, max={wlm.max()}")
    print(f"P(≥5 rounds): {np.mean(wlm>=5):.4f}")
    print(f"P(≥10 rounds): {np.mean(wlm>=10):.4f}")

def test_two_phase_attack(N=1000):
    """
    Two-phase convergence:
    Phase 1 (r=0-16): Wang cascade → dist=0 for e-branch
    Phase 2 (r=17-64): let dist grow, but TRACK convergent sub-rounds

    If phase 2 has convergent sub-sequences → the trajectory
    oscillates TOWARD collision rather than away from it.

    Measure: net convergence rate in phase 2.
    """
    print("\n--- TEST 4: TWO-PHASE CONVERGENCE RATE ---")

    rates = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        p, ep = convergence_profile(Wn, Wf)

        # Phase 2: rounds 17-64
        # Net rate = (dist[64] - dist[17]) / (64-17)
        # Negative = converging, positive = diverging
        if p[17] > 0:
            net_rate = (p[64] - p[17]) / 47
            rates.append(net_rate)

        # Also measure e-branch rate separately
        # (our signal is in e-branch)

    r_arr = np.array(rates)
    print(f"Phase 2 net convergence rate: mean={r_arr.mean():+.4f} bits/round")
    print(f"std: {r_arr.std():.4f}")
    print(f"P(converging, rate<0): {np.mean(r_arr < 0):.4f}")
    print(f"P(strongly converging, rate<-0.5): {np.mean(r_arr < -0.5):.4f}")

    # Theoretical: if rate is biased toward convergence, that's exploitable
    # Random walk: rate ≈ 0 (no bias)
    z = r_arr.mean() / (r_arr.std() / np.sqrt(len(r_arr)))
    print(f"Z-score of convergence bias: {z:.4f}")
    if z < -3:
        print("*** SIGNAL: Phase 2 has convergent BIAS! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 34: CONVERGENT TRAJECTORIES — FOURTH PATH")
    print("Not collision. Convergence.")
    print("="*60)

    test_wang_convergence_profile(1500)
    test_partial_wang_tradeoff(1000)
    test_monotonic_convergence(500)
    test_two_phase_attack(2000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
