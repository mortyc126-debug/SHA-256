#!/usr/bin/env python3
"""
EXP 174: DEAD ZONE AUTOPSY — Is rounds 21-64 truly dead?

exp173 showed: aggregate stats (dH, G/K/P, entropy) are FLAT at r=21+.
But aggregates can HIDE structure. Look for:

1. BIT-SPECIFIC patterns (individual bits non-random at late rounds?)
2. WORD-LEVEL asymmetry (a-branch vs e-branch at late rounds?)
3. TEMPORAL correlations (round r vs r+k for k > 1?)
4. MICRO-OSCILLATIONS in entropy (structured, not random?)
5. POSITIONAL drift (do G/K/P positions CHANGE even if counts don't?)
6. LONG-RANGE correlations (round 25 state → round 64 hash?)

Maximum statistical power: large N, precise measurements.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_bit_specific_patterns(N=2000):
    """Are specific bit positions non-random at rounds 21+?"""
    print(f"\n{'='*60}")
    print(f"1. BIT-SPECIFIC PATTERNS AT ROUNDS 21+ (N={N})")
    print(f"{'='*60}")

    # For each of 256 state bits at round 25 and 40:
    # measure P(bit=1). Deviation from 0.5 = non-random.
    for R in [25, 40, 60]:
        bits = np.zeros((N, 256))
        for i in range(N):
            M = random_w16()
            s = sha256_rounds(M, R)[R]
            for w in range(8):
                for b in range(32):
                    bits[i, w*32+b] = (s[w] >> b) & 1

        # Per-bit bias
        bias = bits.mean(axis=0) - 0.5
        max_bias = np.max(np.abs(bias))
        threshold = 3 / math.sqrt(N)  # 3σ
        n_significant = np.sum(np.abs(bias) > threshold)

        # Find most biased bits
        top_biased = np.argsort(-np.abs(bias))[:5]

        print(f"\n  Round {R}:")
        print(f"    Max |bias|: {max_bias:.6f} (3σ threshold: {threshold:.6f})")
        print(f"    Significant bits: {n_significant}/256")
        for idx in top_biased:
            w = idx // 32; b = idx % 32
            print(f"      Word {w} bit {b:>2}: bias = {bias[idx]:+.6f}")

def test_word_asymmetry(N=1000):
    """Do a-branch and e-branch behave differently at rounds 21+?"""
    print(f"\n{'='*60}")
    print(f"2. WORD-LEVEL ASYMMETRY (N={N})")
    print(f"{'='*60}")

    for R in [21, 30, 50, 64]:
        a_branch_hw = []  # Words 0-3 (a→b→c→d)
        e_branch_hw = []  # Words 4-7 (e→f→g→h)

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1); M2[0] ^= 1

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            a_hw = sum(hw(s1[w] ^ s2[w]) for w in range(4))
            e_hw = sum(hw(s1[w] ^ s2[w]) for w in range(4, 8))

            a_branch_hw.append(a_hw)
            e_branch_hw.append(e_hw)

        aa = np.array(a_branch_hw); ea = np.array(e_branch_hw)
        diff = aa.mean() - ea.mean()
        z = diff / math.sqrt((aa.std()**2 + ea.std()**2) / (2*N))

        sig = "★★★" if abs(z) > 5 else ("★★" if abs(z) > 3 else "")
        print(f"  Round {R:>2}: a-branch={aa.mean():.2f}, e-branch={ea.mean():.2f}, "
              f"diff={diff:+.3f}, Z={z:+.2f} {sig}")

def test_temporal_correlations(N=500):
    """Correlations between state at round r and round r+k."""
    print(f"\n{'='*60}")
    print(f"3. TEMPORAL CORRELATIONS IN DEAD ZONE (N={N})")
    print(f"{'='*60}")

    # For a fixed message: how correlated are state_25 and state_30?
    # (Not pair difference — single message state evolution)

    print(f"\n  corr(HW(state_r), HW(state_{'{r+k}'})) for k = 1,2,5,10,20:")
    print(f"  {'Base r':>7} | {'k=1':>7} | {'k=2':>7} | {'k=5':>7} | {'k=10':>7} | {'k=20':>7}")
    print(f"  " + "-" * 50)

    for r_base in [21, 25, 30, 40, 50]:
        corrs = []
        for k in [1, 2, 5, 10, 20]:
            if r_base + k > 64:
                corrs.append(float('nan'))
                continue

            hw_r = []; hw_rk = []
            for _ in range(N):
                M = random_w16()
                states = sha256_rounds(M, r_base + k)
                s_r = states[r_base]; s_rk = states[r_base + k]

                hw_r.append(sum(hw(s_r[w]) for w in range(8)))
                hw_rk.append(sum(hw(s_rk[w]) for w in range(8)))

            c = np.corrcoef(hw_r, hw_rk)[0, 1]
            corrs.append(c)

        print(f"  r={r_base:>3}   |", end="")
        for c in corrs:
            if np.isnan(c):
                print(f"     N/A", end="")
            else:
                print(f" {c:>+7.4f}", end="")
        print()

def test_micro_oscillations(N=500):
    """Are entropy oscillations structured (periodic) or random?"""
    print(f"\n{'='*60}")
    print(f"4. MICRO-OSCILLATION STRUCTURE (N={N})")
    print(f"{'='*60}")

    # Compute chain entropy at rounds 20-64 for many messages
    # Look for PERIODIC structure in the oscillations

    entropy_traces = np.zeros((N, 45))  # Rounds 20-64

    for trial in range(N):
        M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        for r_off in range(45):
            r = r_off + 20
            total_ent = 0
            for w in range(8):
                gkp = carry_gkp_classification(s1_all[r][w], s2_all[r][w])
                chains = []; current = 0
                for c in gkp:
                    if c == 'P': current += 1
                    else:
                        if current > 0: chains.append(current)
                        current = 0
                if current > 0: chains.append(current)
                total = sum(chains)
                if total > 0:
                    probs = [s/total for s in chains]
                    total_ent -= sum(p*math.log2(p) for p in probs if p > 0)
            entropy_traces[trial, r_off] = total_ent

    # Average entropy trace
    avg_trace = entropy_traces.mean(axis=0)

    # Autocorrelation of the entropy trace
    centered = avg_trace - avg_trace.mean()
    autocorr = np.correlate(centered, centered, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr /= autocorr[0]

    print(f"\n  Entropy autocorrelation in dead zone (rounds 20-64):")
    for lag in [1, 2, 3, 4, 5, 8, 10, 15, 20]:
        if lag < len(autocorr):
            print(f"    Lag {lag:>2}: {autocorr[lag]:+.4f}")

    # FFT to find periodicity
    fft = np.abs(np.fft.fft(centered))
    freqs = np.fft.fftfreq(len(centered))
    top_freq_idx = np.argsort(-fft[1:len(fft)//2])[:5] + 1

    print(f"\n  Top Fourier frequencies:")
    for idx in top_freq_idx:
        period = 1.0 / abs(freqs[idx]) if freqs[idx] != 0 else float('inf')
        print(f"    Freq={freqs[idx]:.4f}, Period={period:.1f} rounds, Amplitude={fft[idx]:.4f}")

def test_positional_drift(N=500):
    """Do G/K/P positions CHANGE even when counts stay same?"""
    print(f"\n{'='*60}")
    print(f"5. POSITIONAL DRIFT (N={N})")
    print(f"{'='*60}")

    # For consecutive rounds in dead zone: how many POSITIONS change
    # their GKP type, even though total counts are ~same?

    print(f"\n  GKP position changes between consecutive rounds:")
    print(f"  {'Rounds':>10} | {'Changed':>8} | {'%Changed':>8} | {'Interpretation'}")
    print(f"  " + "-" * 50)

    for r in [21, 25, 30, 40, 50, 60, 63]:
        changes_all = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1); M2[0] ^= 1
            s1 = sha256_rounds(M1, r+1)
            s2 = sha256_rounds(M2, r+1)

            # GKP at round r and r+1
            changed = 0
            for w in range(8):
                gkp_r = carry_gkp_classification(s1[r][w], s2[r][w])
                gkp_r1 = carry_gkp_classification(s1[r+1][w], s2[r+1][w])
                for b in range(32):
                    if gkp_r[b] != gkp_r1[b]:
                        changed += 1

            changes_all.append(changed)

        avg = np.mean(changes_all)
        pct = avg / 256 * 100
        interp = "FROZEN" if pct < 10 else ("SLOW" if pct < 30 else ("ACTIVE" if pct < 60 else "FULL CHURN"))
        print(f"  r={r:>2}→{r+1:>2} | {avg:>8.1f} | {pct:>7.1f}% | {interp}")

def test_long_range_correlation(N=500):
    """Does state at round 25 predict ANYTHING about hash at round 64?"""
    print(f"\n{'='*60}")
    print(f"6. LONG-RANGE: DEAD ZONE STATE → FINAL HASH (N={N})")
    print(f"{'='*60}")

    # For each round r in dead zone: corr(HW(state_r diff), dH_final)
    for r in [21, 25, 30, 35, 40, 50, 60, 63, 64]:
        state_hws = []; hash_dists = []
        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            s1 = sha256_rounds(M1, max(r, 64))
            s2 = sha256_rounds(M2, max(r, 64))

            # State diff at round r
            state_hw = sum(hw(s1[min(r,64)][w] ^ s2[min(r,64)][w]) for w in range(8))
            state_hws.append(state_hw)

            # Hash distance
            H1 = sha256_compress(M1); H2 = sha256_compress(M2)
            hash_dists.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

        corr = np.corrcoef(state_hws, hash_dists)[0, 1]
        sig = "★★★" if abs(corr) > 0.05 else ""
        print(f"  Round {r:>2} → hash: corr = {corr:+.6f} {sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 174: DEAD ZONE AUTOPSY")
    print("Is rounds 21-64 truly dead?")
    print("=" * 60)

    test_bit_specific_patterns(1500)
    test_word_asymmetry(800)
    test_temporal_correlations(300)
    test_positional_drift(300)
    test_micro_oscillations(300)
    test_long_range_correlation(400)

    print(f"\n{'='*60}")
    print(f"VERDICT: Dead or alive?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
