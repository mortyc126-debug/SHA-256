#!/usr/bin/env python3
"""
EXP 43: Maxwell's Demon for SHA-256

Conservation Law: selection × pool = const (assumes independence).
Demon: uses INFORMATION from previous attempts to construct next.
Breaks independence → potentially breaks conservation.

INFORMATION AVAILABLE (from SHA-256 internals):
- All 64 intermediate states (256 bits each = 16384 bits total)
- Wang cascade structure (ΔW, De profiles)
- Carry coupling at every round

DEMON STRATEGY: Extract state[R] from attempt K,
use it to SEED attempt K+1 in a way that correlates
their carry structures.

If two attempts have CORRELATED carries at round R →
their OUTPUT differences are correlated → not independent →
birthday formula doesn't apply → potential advantage.

This is NOT hill-climbing (which uses only δH, a scalar).
This uses the FULL 16384-bit internal state.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extract_internal_info(Wn, Wf):
    """Extract demon's information: internal states at key rounds."""
    sn = sha256_rounds(Wn, 64)
    sf = sha256_rounds(Wf, 64)

    # State differences at key rounds
    info = {}
    for r in [16, 17, 32, 48, 60, 63]:
        diff_state = [(sn[r][i] ^ sf[r][i]) for i in range(8)]
        info[f'diff_{r}'] = diff_state
        info[f'state_n_{r}'] = list(sn[r])

    # Hash
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    info['dH'] = sum(hw(Hn[i]^Hf[i]) for i in range(8))
    info['Hn'] = Hn
    info['Hf'] = Hf

    return info

def demon_seed_from_state(prev_info, mutation_strength=1):
    """
    Demon constructs new (W0, W1) using information from previous attempt.

    Strategy: use state_n at round 16 (end of Wang zone) as seed.
    The idea: if state[16] is similar between attempts,
    their post-barrier behavior is correlated.
    """
    # Extract bits from previous internal state
    state16 = prev_info['state_n_16']

    # Use state16 words as new W0, W1 (deterministic seeding)
    # Add small mutation for exploration
    W0 = state16[0] ^ (random.randint(0, (1 << mutation_strength) - 1))
    W1 = state16[4] ^ (random.randint(0, (1 << mutation_strength) - 1))

    return W0 & MASK, W1 & MASK

def demon_seed_from_diff(prev_info, mutation_strength=4):
    """
    Alternative demon: use state DIFFERENCE at round 48
    to seed construction that minimizes late-round divergence.
    """
    diff48 = prev_info['diff_48']

    # Find which bits of diff48 have lowest HW (most similar)
    # Use the e-branch words (where our signal lives)
    best_word = min(range(4, 8), key=lambda w: hw(diff48[w]))
    seed = diff48[best_word]

    # Construct W0, W1 that produce states aligned with this pattern
    W0 = seed ^ random.randint(0, (1 << mutation_strength) - 1)
    W1 = (seed >> 1) ^ random.randint(0, (1 << mutation_strength) - 1)

    return W0 & MASK, W1 & MASK

def test_demon_vs_random(total_budget=10000):
    """
    Compare:
    A) Random: independent Wang pairs
    B) Demon v1: seed from state[16]
    C) Demon v2: seed from diff[48]
    D) Demon v3: HASH-based seeding (use H(M) bits as next W0,W1)
    """
    print(f"\n--- DEMON vs RANDOM (budget={total_budget}) ---")

    # Strategy A: Pure random
    random_best = 256
    for _ in range(total_budget):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        random_best = min(random_best, dH)

    # Strategy B: Demon v1 (state[16] seeding)
    demon1_best = 256
    W0=random.randint(0,MASK); W1=random.randint(0,MASK)
    Wn,Wf,_,_,_ = wang_cascade(W0,W1)
    prev_info = extract_internal_info(Wn, Wf)
    demon1_best = min(demon1_best, prev_info['dH'])

    for _ in range(total_budget - 1):
        W0, W1 = demon_seed_from_state(prev_info, mutation_strength=8)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            info = extract_internal_info(Wn, Wf)
            demon1_best = min(demon1_best, info['dH'])
            if info['dH'] < prev_info['dH']:
                prev_info = info  # Update demon's memory
        except:
            pass

    # Strategy C: Demon v2 (diff[48] seeding)
    demon2_best = 256
    W0=random.randint(0,MASK); W1=random.randint(0,MASK)
    Wn,Wf,_,_,_ = wang_cascade(W0,W1)
    prev_info = extract_internal_info(Wn, Wf)
    demon2_best = min(demon2_best, prev_info['dH'])

    for _ in range(total_budget - 1):
        W0, W1 = demon_seed_from_diff(prev_info, mutation_strength=8)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            info = extract_internal_info(Wn, Wf)
            demon2_best = min(demon2_best, info['dH'])
            if info['dH'] < prev_info['dH']:
                prev_info = info
        except:
            pass

    # Strategy D: Demon v3 (hash-based seeding — use Hn as next seed)
    demon3_best = 256
    W0=random.randint(0,MASK); W1=random.randint(0,MASK)
    Wn,Wf,_,_,_ = wang_cascade(W0,W1)
    prev_info = extract_internal_info(Wn, Wf)
    demon3_best = min(demon3_best, prev_info['dH'])

    for _ in range(total_budget - 1):
        Hn = prev_info['Hn']
        W0 = Hn[0] ^ random.randint(0, 0xFF)
        W1 = Hn[4] ^ random.randint(0, 0xFF)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            info = extract_internal_info(Wn, Wf)
            demon3_best = min(demon3_best, info['dH'])
            prev_info = info  # Always update
        except:
            pass

    birthday = 128 - 8*np.sqrt(2*np.log(total_budget))

    print(f"Random:          best δH = {random_best}")
    print(f"Demon v1 (s16):  best δH = {demon1_best}")
    print(f"Demon v2 (d48):  best δH = {demon2_best}")
    print(f"Demon v3 (hash): best δH = {demon3_best}")
    print(f"Birthday (N={total_budget}): ~{birthday:.1f}")

    for name, val in [("Demon v1", demon1_best), ("Demon v2", demon2_best),
                       ("Demon v3", demon3_best)]:
        if val < random_best:
            print(f"*** {name} BEATS random by {random_best - val} bits! ***")

    return random_best, demon1_best, demon2_best, demon3_best

def test_information_correlation(N=3000):
    """
    Does internal state information CREATE correlation between attempts?

    If demon's seeding creates correlated (W0,W1) →
    the Wang pairs are NOT independent → birthday formula invalid.

    Measure: autocorrelation of δH in demon sequence.
    Random sequence: autocorr = 0.
    Demon sequence: autocorr > 0 → correlation exists.
    """
    print(f"\n--- INFORMATION CORRELATION TEST ---")

    # Random sequence
    random_dHs = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        random_dHs.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    # Demon v1 sequence
    demon_dHs = []
    W0=random.randint(0,MASK); W1=random.randint(0,MASK)
    Wn,Wf,_,_,_ = wang_cascade(W0,W1)
    prev_info = extract_internal_info(Wn, Wf)
    demon_dHs.append(prev_info['dH'])

    for _ in range(N-1):
        W0, W1 = demon_seed_from_state(prev_info, mutation_strength=16)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            info = extract_internal_info(Wn, Wf)
            demon_dHs.append(info['dH'])
            prev_info = info
        except:
            demon_dHs.append(128)

    ra = np.array(random_dHs)
    da = np.array(demon_dHs)

    print(f"Random: E[δH]={ra.mean():.2f}, std={ra.std():.2f}")
    print(f"Demon:  E[δH]={da.mean():.2f}, std={da.std():.2f}")

    # Autocorrelation
    print(f"\nAutocorrelation of δH sequence:")
    for lag in [1, 2, 3, 5, 10]:
        # Random
        rc = np.corrcoef(ra[:-lag], ra[lag:])[0,1]
        # Demon
        dc = np.corrcoef(da[:-lag], da[lag:])[0,1]
        sig = " ***" if abs(dc) > 3/np.sqrt(N) else ""
        print(f"  Lag {lag:>2}: random={rc:+.4f}, demon={dc:+.4f}{sig}")

    # Key: if demon autocorrelation > 0 → samples NOT independent
    # → birthday formula doesn't apply → potential advantage
    demon_autocorr_1 = np.corrcoef(da[:-1], da[1:])[0,1]
    if abs(demon_autocorr_1) > 3/np.sqrt(N):
        print(f"\n*** DEMON CREATES CORRELATED SAMPLES (autocorr={demon_autocorr_1:.4f})! ***")
        print(f"Birthday formula may not apply!")
    else:
        print(f"\nDemon samples are INDEPENDENT (autocorr={demon_autocorr_1:.4f})")

def test_multi_round_demon(total_budget=10000, n_runs=10):
    """Multiple independent runs to get statistics."""
    print(f"\n--- MULTI-RUN COMPARISON (budget={total_budget}, {n_runs} runs) ---")

    random_bests = []
    demon_bests = []

    for run in range(n_runs):
        # Random
        best_r = 256
        for _ in range(total_budget):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            best_r = min(best_r, sum(hw(Hn[i]^Hf[i]) for i in range(8)))
        random_bests.append(best_r)

        # Best demon: try all 3 strategies, take best
        best_d = 256
        for demon_fn in [demon_seed_from_state, demon_seed_from_diff]:
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            prev_info = extract_internal_info(Wn, Wf)
            best_this = prev_info['dH']

            for _ in range(total_budget // 3):
                W0, W1 = demon_fn(prev_info, mutation_strength=12)
                try:
                    Wn,Wf,_,_,_ = wang_cascade(W0,W1)
                    info = extract_internal_info(Wn, Wf)
                    best_this = min(best_this, info['dH'])
                    prev_info = info
                except: pass

            best_d = min(best_d, best_this)
        demon_bests.append(best_d)

    ra = np.array(random_bests)
    da = np.array(demon_bests)

    print(f"Random: E[best]={ra.mean():.1f}, min={ra.min()}")
    print(f"Demon:  E[best]={da.mean():.1f}, min={da.min()}")
    print(f"Difference: {da.mean()-ra.mean():+.1f}")

    # Paired comparison
    wins = sum(1 for r, d in zip(random_bests, demon_bests) if d < r)
    print(f"Demon wins: {wins}/{n_runs}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 43: MAXWELL'S DEMON FOR SHA-256")
    print("Break independence. Break conservation.")
    print("="*60)

    test_demon_vs_random(6000)
    test_information_correlation(2000)
    test_multi_round_demon(5000, 8)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
