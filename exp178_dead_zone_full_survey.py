#!/usr/bin/env python3
"""
EXP 178: DEAD ZONE FULL SURVEY — Catalog EVERYTHING inside

exp177 found: 5 resonant modes, 64-cycle sync, non-monotonic memory.
NOW: systematic survey of EVERYTHING living in the dead zone.

SURVEY CATEGORIES:
A. Per-bit behavior (256 bits × 1000 rounds → individual bit histories)
B. Word-word interactions (8×8 = 28 unique pairs → which words talk?)
C. Carry organism ecology (birth/death rates, species diversity)
D. Message-resonance (which messages create which periods?)
E. K-constant fingerprint (does specific K[r] leave a mark on state?)
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extended_rounds(M, n_rounds):
    W = schedule(M)
    state = list(IV)
    states = [list(state)]
    for r in range(n_rounds):
        state = sha256_round(state, W[r % 64], K[r % 64])
        states.append(list(state))
    return states

# ============================================================
# A: PER-BIT AUTOCORRELATION MAP
# ============================================================
def survey_per_bit(N_rounds=500):
    """For each of 256 bits: autocorrelation at lag 1,2,4,8,16,32,64."""
    print(f"\n{'='*60}")
    print(f"A: PER-BIT AUTOCORRELATION MAP ({N_rounds} rounds)")
    print(f"{'='*60}")

    M = random_w16()
    states = extended_rounds(M, N_rounds)

    # Collect bit traces (rounds 20+)
    bit_traces = np.zeros((N_rounds - 20, 256))
    for r_off in range(N_rounds - 20):
        r = r_off + 20
        for w in range(8):
            for b in range(32):
                bit_traces[r_off, w*32+b] = (states[r][w] >> b) & 1

    # Autocorrelation per bit at lag 1
    lag1_corrs = []
    for bit_idx in range(256):
        trace = bit_traces[:, bit_idx]
        c = np.corrcoef(trace[:-1], trace[1:])[0, 1]
        lag1_corrs.append(c if not np.isnan(c) else 0)

    la = np.array(lag1_corrs)
    print(f"\n  Lag-1 autocorrelation per bit:")
    print(f"    Mean: {la.mean():.6f} (0 = no memory)")
    print(f"    Std:  {la.std():.6f}")
    print(f"    Max:  {la.max():.6f}")
    print(f"    Min:  {la.min():.6f}")

    # Which bits have HIGHEST autocorrelation?
    top_bits = np.argsort(-la)[:10]
    print(f"\n  TOP 10 bits with HIGHEST lag-1 memory:")
    for idx in top_bits:
        w = idx // 32; b = idx % 32
        print(f"    Word {w} bit {b:>2}: corr = {la[idx]:+.4f}")

    # Lag 64 autocorrelation (K-cycle)
    lag64_corrs = []
    for bit_idx in range(256):
        trace = bit_traces[:, bit_idx]
        if len(trace) > 64:
            c = np.corrcoef(trace[:-64], trace[64:])[0, 1]
            lag64_corrs.append(c if not np.isnan(c) else 0)
        else:
            lag64_corrs.append(0)

    l64 = np.array(lag64_corrs)
    print(f"\n  Lag-64 autocorrelation (K-cycle sync):")
    print(f"    Mean: {l64.mean():.6f}")
    print(f"    Max:  {l64.max():.6f} at Word {np.argmax(l64)//32} bit {np.argmax(l64)%32}")

    return la, l64

# ============================================================
# B: WORD-WORD INTERACTIONS
# ============================================================
def survey_word_interactions(N_rounds=500):
    """Which words influence each other in the dead zone?"""
    print(f"\n{'='*60}")
    print(f"B: WORD-WORD INTERACTIONS ({N_rounds} rounds)")
    print(f"{'='*60}")

    M = random_w16()
    states = extended_rounds(M, N_rounds)

    # Word HW traces
    word_traces = np.zeros((N_rounds - 20, 8))
    for r_off in range(N_rounds - 20):
        r = r_off + 20
        for w in range(8):
            word_traces[r_off, w] = hw(states[r][w])

    # Cross-correlation matrix (lag 0)
    print(f"\n  Word-word correlation (lag 0):")
    print(f"      w0    w1    w2    w3    w4    w5    w6    w7")
    for w1 in range(8):
        print(f"  w{w1}", end="")
        for w2 in range(8):
            c = np.corrcoef(word_traces[:, w1], word_traces[:, w2])[0, 1]
            print(f" {c:>+5.2f}", end="")
        print()

    # Cross-correlation at lag 1 (w1[r] → w2[r+1])
    print(f"\n  Word-word correlation (lag 1: w_row[r] → w_col[r+1]):")
    print(f"      w0    w1    w2    w3    w4    w5    w6    w7")
    max_cross = 0; max_pair = (0, 0)
    for w1 in range(8):
        print(f"  w{w1}", end="")
        for w2 in range(8):
            c = np.corrcoef(word_traces[:-1, w1], word_traces[1:, w2])[0, 1]
            if abs(c) > abs(max_cross) and w1 != w2:
                max_cross = c; max_pair = (w1, w2)
            print(f" {c:>+5.2f}", end="")
        print()

    print(f"\n  Strongest cross-word lag-1: w{max_pair[0]}→w{max_pair[1]} = {max_cross:+.3f}")

    # Shift register signature: w0→w1→w2→w3 and w4→w5→w6→w7
    print(f"\n  SHIFT REGISTER CHECK:")
    print(f"    a-branch: w0→w1 = {np.corrcoef(word_traces[:-1,0], word_traces[1:,1])[0,1]:+.3f}")
    print(f"              w1→w2 = {np.corrcoef(word_traces[:-1,1], word_traces[1:,2])[0,1]:+.3f}")
    print(f"              w2→w3 = {np.corrcoef(word_traces[:-1,2], word_traces[1:,3])[0,1]:+.3f}")
    print(f"    e-branch: w4→w5 = {np.corrcoef(word_traces[:-1,4], word_traces[1:,5])[0,1]:+.3f}")
    print(f"              w5→w6 = {np.corrcoef(word_traces[:-1,5], word_traces[1:,6])[0,1]:+.3f}")
    print(f"              w6→w7 = {np.corrcoef(word_traces[:-1,6], word_traces[1:,7])[0,1]:+.3f}")

# ============================================================
# C: CARRY ORGANISM ECOLOGY
# ============================================================
def survey_carry_ecology(N_rounds=500):
    """Detailed carry organism statistics in dead zone."""
    print(f"\n{'='*60}")
    print(f"C: CARRY ORGANISM ECOLOGY ({N_rounds} rounds)")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    # Track per round: births, deaths, population
    births = []; deaths = []; populations = []
    species_diversity = []  # Unique chain lengths

    prev_alive_positions = set()

    for r in range(20, N_rounds):
        s1 = s1_all[r]; s2 = s2_all[r]
        alive_positions = set()
        org_lengths = []
        current = 0

        for w in range(8):
            gkp = carry_gkp_classification(s1[w], s2[w])
            for b in range(32):
                pos = w * 32 + b
                if gkp[b] != 'K':
                    alive_positions.add(pos)
                    current += 1
                else:
                    if current > 0:
                        org_lengths.append(current)
                    current = 0
            if current > 0:
                org_lengths.append(current)
                current = 0

        born = len(alive_positions - prev_alive_positions)
        died = len(prev_alive_positions - alive_positions)
        pop = len(alive_positions)

        births.append(born)
        deaths.append(died)
        populations.append(pop)
        species_diversity.append(len(set(org_lengths)))

        prev_alive_positions = alive_positions

    ba = np.array(births); da = np.array(deaths)
    pa = np.array(populations); sd = np.array(species_diversity)

    print(f"\n  ECOLOGY STATS (rounds 20-{N_rounds}):")
    print(f"    Population: {pa.mean():.1f} ± {pa.std():.1f}")
    print(f"    Births/round: {ba.mean():.1f} ± {ba.std():.1f}")
    print(f"    Deaths/round: {da.mean():.1f} ± {da.std():.1f}")
    print(f"    Net growth: {(ba-da).mean():+.2f}/round")
    print(f"    Species diversity: {sd.mean():.1f} ± {sd.std():.1f}")

    # Birth-death BALANCE
    print(f"\n  BIRTH-DEATH BALANCE:")
    print(f"    corr(births, deaths): {np.corrcoef(ba, da)[0,1]:+.4f}")
    print(f"    Births > Deaths: {np.mean(ba > da)*100:.1f}%")
    print(f"    Perfect balance: {np.mean(ba == da)*100:.1f}%")

    # Population autocorrelation
    print(f"\n  POPULATION MEMORY:")
    for lag in [1, 2, 4, 8, 16, 32, 64]:
        if lag < len(pa) - 10:
            c = np.corrcoef(pa[:-lag], pa[lag:])[0, 1]
            print(f"    lag {lag:>3}: corr = {c:+.4f}")

# ============================================================
# D: K-CONSTANT FINGERPRINT
# ============================================================
def survey_k_fingerprint(N_rounds=640):
    """Does each K[r] leave a SPECIFIC fingerprint on the state?"""
    print(f"\n{'='*60}")
    print(f"D: K-CONSTANT FINGERPRINT ({N_rounds} rounds)")
    print(f"{'='*60}")

    # Run 10 × 64 = 640 rounds. K[r%64] cycles 10 times.
    # For each K index (0-63): collect state HW at those rounds
    # Does K[5] always produce similar state HW?

    M = random_w16()
    states = extended_rounds(M, N_rounds)

    # Group by K-index
    k_states = {k: [] for k in range(64)}
    for r in range(20, N_rounds):
        k_idx = r % 64
        total_hw = sum(hw(states[r][w]) for w in range(8))
        k_states[k_idx].append(total_hw)

    # Which K-indices produce most/least HW?
    k_means = {k: np.mean(v) for k, v in k_states.items()}
    k_stds = {k: np.std(v) for k, v in k_states.items()}

    # Sort by mean HW
    sorted_k = sorted(k_means.items(), key=lambda x: x[1])

    print(f"\n  K-index → state HW (sorted):")
    print(f"  {'K-idx':>5} | {'Mean HW':>8} | {'Std':>6} | {'K value':>12}")
    print(f"  " + "-" * 40)

    for k, mean_hw in sorted_k[:5]:
        print(f"  {k:>5} | {mean_hw:>8.2f} | {k_stds[k]:>6.2f} | 0x{K[k]:08x}  ← LOW")

    print(f"  {'...':>5}")
    for k, mean_hw in sorted_k[-5:]:
        print(f"  {k:>5} | {mean_hw:>8.2f} | {k_stds[k]:>6.2f} | 0x{K[k]:08x}  ← HIGH")

    # Range of means
    all_means = [m for _, m in sorted_k]
    total_range = max(all_means) - min(all_means)
    print(f"\n  HW range across K-indices: {total_range:.2f}")
    print(f"  Mean of means: {np.mean(all_means):.2f}")

    if total_range > 2:
        print(f"  ★★★ K-constants leave DIFFERENT fingerprints!")
    else:
        print(f"  K-fingerprints are similar (no strong differentiation)")

    # ANOVA-like: between-K variance vs within-K variance
    between_var = np.var(all_means)
    within_var = np.mean([k_stds[k]**2 for k in range(64)])
    f_ratio = between_var / within_var if within_var > 0 else 0
    print(f"\n  Between-K variance: {between_var:.4f}")
    print(f"  Within-K variance: {within_var:.4f}")
    print(f"  F-ratio: {f_ratio:.4f} (>1 = K matters)")

# ============================================================
# E: PAIR-DIFFERENCE RESONANCE
# ============================================================
def survey_pair_resonance(N_rounds=500):
    """For message PAIRS: what resonances exist in dH oscillation?"""
    print(f"\n{'='*60}")
    print(f"E: PAIR-DIFFERENCE RESONANCE ({N_rounds} rounds)")
    print(f"{'='*60}")

    # Multiple message pairs with different δM
    deltas = [
        (0, 15, "W[0]b15 (best schedule)"),
        (0, 0, "W[0]b0"),
        (7, 16, "W[7]b16"),
        (15, 31, "W[15]b31 (last)"),
    ]

    for w_d, b_d, name in deltas:
        M1 = random_w16()
        M2 = list(M1); M2[w_d] ^= (1 << b_d)

        s1_all = extended_rounds(M1, N_rounds)
        s2_all = extended_rounds(M2, N_rounds)

        dH_trace = []
        for r in range(20, N_rounds):
            dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(8))
            dH_trace.append(dH)

        arr = np.array(dH_trace)
        centered = arr - arr.mean()
        fft = np.abs(np.fft.fft(centered))
        freqs = np.fft.fftfreq(len(centered))

        top_idx = np.argsort(-fft[1:len(fft)//2])[:3] + 1
        periods = [1.0/abs(freqs[i]) for i in top_idx]

        print(f"\n  {name}:")
        print(f"    dH mean={arr.mean():.1f}, std={arr.std():.2f}")
        print(f"    Top 3 periods: {[f'{p:.1f}' for p in periods]}")

        # Lag-1 autocorrelation specific to this δM
        c1 = np.corrcoef(arr[:-1], arr[1:])[0, 1]
        c64 = np.corrcoef(arr[:-64], arr[64:])[0, 1] if len(arr) > 64 else 0
        print(f"    Lag-1 corr: {c1:+.4f}, Lag-64 corr: {c64:+.4f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 178: DEAD ZONE FULL SURVEY")
    print("=" * 60)

    t0 = time.time()
    survey_per_bit(N_rounds=500)
    survey_word_interactions(N_rounds=500)
    survey_carry_ecology(N_rounds=500)
    survey_k_fingerprint(N_rounds=640)
    survey_pair_resonance(N_rounds=500)
    t1 = time.time()

    print(f"\n  Total time: {t1-t0:.1f}s")
    print(f"\n{'='*60}")
    print(f"DEAD ZONE INVENTORY")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
