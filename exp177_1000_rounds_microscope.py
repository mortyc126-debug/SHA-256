#!/usr/bin/env python3
"""
EXP 177: 1000 DEAD ROUNDS UNDER MICROSCOPE

Run SHA-256 round function FAR beyond 64 rounds (up to 1000).
Track EVERYTHING at particle level. Look for:

1. INVARIANT patterns (something that NEVER changes, even after 1000 rounds)
2. PERIODIC patterns (something that oscillates with fixed period)
3. DRIFT patterns (something that slowly changes in one direction)
4. CORRELATIONS that persist across hundreds of rounds

The round function cycles K[r%64] and W[r%64], so there's a
FORCED periodicity of 64 rounds in the constants. Does the STATE
respond to this forcing? Does it SYNC?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extended_rounds(M, n_rounds):
    """Run SHA-256 round function beyond 64 rounds.
    Use W[r%64] and K[r%64] for cycling."""
    W = schedule(M)
    state = list(IV)
    states = [list(state)]

    for r in range(n_rounds):
        state = sha256_round(state, W[r % 64], K[r % 64])
        states.append(list(state))

    return states

def test_long_run_patterns(N_rounds=1000):
    """Track particle-level stats over 1000 rounds."""
    print(f"\n{'='*60}")
    print(f"1000 ROUNDS: PARTICLE-LEVEL TRACKING")
    print(f"{'='*60}")

    M1 = random_w16()
    M2 = list(M1); M2[0] ^= (1 << 15)

    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    # Track per round: dH, nG, nK, nP, max_chain, n_organisms, entropy
    dH_trace = []
    nP_trace = []
    max_chain_trace = []
    n_org_trace = []
    entropy_trace = []
    bit27_gkp_trace = []  # Track bit 27 specifically

    for r in range(N_rounds + 1):
        s1 = s1_all[r]; s2 = s2_all[r]

        dH = sum(hw(s1[w] ^ s2[w]) for w in range(8))
        dH_trace.append(dH)

        total_P = 0; max_chain = 0; n_orgs = 0; total_ent = 0
        for w in range(8):
            gkp = carry_gkp_classification(s1[w], s2[w])
            total_P += gkp.count('P')

            # Organisms
            chains = []; current = 0
            for c in gkp:
                if c != 'K': current += 1
                else:
                    if current > 0:
                        chains.append(current)
                        n_orgs += 1
                    current = 0
            if current > 0:
                chains.append(current)
                n_orgs += 1
            if chains:
                max_chain = max(max_chain, max(chains))

            total = sum(chains)
            if total > 0:
                probs = [s/total for s in chains]
                total_ent -= sum(p*math.log2(p) for p in probs if p > 0)

        nP_trace.append(total_P)
        max_chain_trace.append(max_chain)
        n_org_trace.append(n_orgs)
        entropy_trace.append(total_ent)

        # Bit 27 of word 0
        gkp_w0 = carry_gkp_classification(s1[0], s2[0])
        bit27_gkp_trace.append(gkp_w0[27])

    # Convert to arrays
    dH = np.array(dH_trace[20:])  # Skip first 20 (mixing)
    nP = np.array(nP_trace[20:])
    mc = np.array(max_chain_trace[20:])
    no = np.array(n_org_trace[20:])
    ent = np.array(entropy_trace[20:])

    print(f"\n  STATISTICS (rounds 20-{N_rounds}):")
    for name, arr in [("dH", dH), ("nP", nP), ("max_chain", mc),
                       ("n_organisms", no), ("entropy", ent)]:
        print(f"    {name:>12}: mean={arr.mean():.3f} std={arr.std():.3f} "
              f"min={arr.min():.0f} max={arr.max():.0f}")

    # 1. INVARIANT patterns: anything with std ≈ 0?
    print(f"\n  1. INVARIANTS (std < 0.01):")
    for name, arr in [("dH", dH), ("nP", nP), ("max_chain", mc),
                       ("n_organisms", no), ("entropy", ent)]:
        if arr.std() < 0.01:
            print(f"    ★★★ {name} is INVARIANT: {arr.mean():.6f} ± {arr.std():.6f}")
    print(f"    (none expected — all should fluctuate)")

    # 2. PERIODIC patterns: FFT
    print(f"\n  2. PERIODIC PATTERNS (FFT):")
    for name, arr in [("dH", dH), ("nP", nP), ("entropy", ent)]:
        centered = arr - arr.mean()
        fft = np.abs(np.fft.fft(centered))
        freqs = np.fft.fftfreq(len(centered))

        # Top frequencies (skip DC)
        top_idx = np.argsort(-fft[1:len(fft)//2])[:5] + 1
        print(f"\n    {name} top periods:")
        for idx in top_idx:
            period = 1.0 / abs(freqs[idx]) if freqs[idx] != 0 else float('inf')
            amp = fft[idx] / len(centered)
            # Is this significant? Compare to noise floor
            noise = np.median(fft[1:len(fft)//2]) / len(centered)
            snr = amp / noise if noise > 0 else 0
            sig = " ★★★" if snr > 3 else (" ★★" if snr > 2 else "")
            print(f"      Period={period:>7.1f}r, Amp={amp:.4f}, SNR={snr:.1f}{sig}")

    # 3. DRIFT patterns: is the mean changing over time?
    print(f"\n  3. DRIFT PATTERNS:")
    for name, arr in [("dH", dH), ("nP", nP), ("entropy", ent)]:
        # Split into 10 segments
        seg_size = len(arr) // 10
        seg_means = [arr[i*seg_size:(i+1)*seg_size].mean() for i in range(10)]
        slope = np.polyfit(range(10), seg_means, 1)[0]
        total_drift = slope * 10

        sig = " ★★★" if abs(total_drift) > arr.std() else ""
        print(f"    {name:>12}: drift = {total_drift:+.4f} over {N_rounds}r{sig}")

    # 4. LONG-RANGE correlations
    print(f"\n  4. LONG-RANGE CORRELATIONS:")
    for lag in [1, 2, 5, 10, 32, 64, 100, 200, 500]:
        if lag >= len(dH) - 10:
            continue
        c = np.corrcoef(dH[:-lag], dH[lag:])[0, 1]
        sig = " ★" if abs(c) > 0.1 else ""
        print(f"    dH corr(r, r+{lag:>3}): {c:+.4f}{sig}")

    # 5. 64-ROUND PERIODICITY (forced by K[r%64] cycling)
    print(f"\n  5. FORCED 64-ROUND PERIODICITY:")
    # Do rounds r and r+64 have correlated states?
    for lag in [64, 128, 192, 256, 512]:
        if lag >= len(dH) - 10:
            continue
        c = np.corrcoef(dH[:-lag], dH[lag:])[0, 1]
        print(f"    dH corr(r, r+{lag:>3}): {c:+.4f}")

    # 6. BIT 27 LIFECYCLE
    print(f"\n  6. BIT 27 (WORD 0) LIFECYCLE:")
    b27 = bit27_gkp_trace[20:]
    gkp_counts = {'G': b27.count('G'), 'K': b27.count('K'), 'P': b27.count('P')}
    total = len(b27)
    for g, c in gkp_counts.items():
        print(f"    {g}: {c/total:.4f} ({c}/{total})")

    # Bit 27 transition matrix
    transitions = {}
    for i in range(1, len(b27)):
        pair = (b27[i-1], b27[i])
        transitions[pair] = transitions.get(pair, 0) + 1

    print(f"\n    Bit 27 transition matrix:")
    print(f"           → G      K      P")
    for p1 in ['G', 'K', 'P']:
        print(f"      {p1} |", end="")
        total_from = sum(transitions.get((p1, p2), 0) for p2 in ['G', 'K', 'P'])
        for p2 in ['G', 'K', 'P']:
            count = transitions.get((p1, p2), 0)
            prob = count / total_from if total_from > 0 else 0
            print(f" {prob:>5.3f}", end="")
        print()

    return dH, nP, ent

def test_multiple_messages(N_msg=5, N_rounds=500):
    """Same analysis across multiple messages — look for UNIVERSAL patterns."""
    print(f"\n{'='*60}")
    print(f"MULTI-MESSAGE: Universal patterns? (N_msg={N_msg})")
    print(f"{'='*60}")

    all_periods = []

    for msg_idx in range(N_msg):
        M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
        s1_all = extended_rounds(M1, N_rounds)
        s2_all = extended_rounds(M2, N_rounds)

        dH_trace = []
        for r in range(20, N_rounds + 1):
            dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(8))
            dH_trace.append(dH)

        arr = np.array(dH_trace)
        centered = arr - arr.mean()
        fft = np.abs(np.fft.fft(centered))
        freqs = np.fft.fftfreq(len(centered))

        # Top period
        top_idx = np.argsort(-fft[1:len(fft)//2])[0] + 1
        period = 1.0 / abs(freqs[top_idx])
        all_periods.append(period)

        print(f"  Message {msg_idx}: mean dH={arr.mean():.1f}, "
              f"top period={period:.1f}r")

    # Universal period?
    p_arr = np.array(all_periods)
    print(f"\n  Top periods across messages: {[f'{p:.1f}' for p in all_periods]}")
    print(f"  Mean: {p_arr.mean():.1f} ± {p_arr.std():.1f}")

    if p_arr.std() < p_arr.mean() * 0.2:
        print(f"  ★★★ UNIVERSAL PERIOD: {p_arr.mean():.1f} rounds!")
    else:
        print(f"  Periods are message-dependent (not universal)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 177: 1000 DEAD ROUNDS UNDER MICROSCOPE")
    print("=" * 60)

    t0 = time.time()
    dH, nP, ent = test_long_run_patterns(N_rounds=1000)
    test_multiple_messages(N_msg=5, N_rounds=500)
    t1 = time.time()

    print(f"\n  Total time: {t1-t0:.1f}s")
    print(f"\n{'='*60}")
    print(f"VERDICT: Patterns in 1000 dead rounds?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
