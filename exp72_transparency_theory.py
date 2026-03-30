#!/usr/bin/env python3
"""
EXP 72: Transparency Theory — T(bit) = f(rotations)

From exp71: transparency pattern T = (1.00, 0.62, ..., 0.45) is non-random.
Peaks align with rotation positions.

THEORY: T(bit) is DETERMINED by rotation constants of Σ0, Σ1, σ0, σ1.

Test:
1. Is T statistically non-random? (Kolmogorov-Smirnov, runs test)
2. Can T be PREDICTED from rotation constants?
3. Does T pattern persist PER-ROUND (not just feedforward)?
4. What happens with DIFFERENT rotation constants? (modified SHA-256)
5. If T predictable → which bits are ALWAYS transparent → algebraic subspace
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_transparency_pattern(N=3000, rounds=64):
    """Measure full 32-bit transparency pattern."""
    T = np.zeros(32)
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        if rounds == 64:
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        else:
            Hn=[(IV[i]+sn[rounds][i])&MASK for i in range(8)]
            Hf=[(IV[i]+sf[rounds][i])&MASK for i in range(8)]

        for w in range(4, 8):  # e-branch
            for bit in range(32):
                s_xor = (sn[min(rounds,64)][w] ^ sf[min(rounds,64)][w] >> bit) & 1
                h_xor = (Hn[w] ^ Hf[w] >> bit) & 1
                if s_xor == h_xor:
                    T[bit] += 1

    T = T / (N * 4)  # Normalize: 4 e-branch words
    return T

def test_randomness_of_pattern():
    """Is the transparency pattern T statistically non-random?"""
    print("\n--- IS T NON-RANDOM? ---")

    T = measure_transparency_pattern(2000)

    print(f"T = [{', '.join(f'{t:.3f}' for t in T)}]")

    # Test 1: is variance of T larger than expected for random?
    # For random: each T[i] ≈ 0.5 ± 1/√(N*4). Variance across bits ≈ 0
    expected_std = 1 / np.sqrt(2000 * 4)
    actual_std = np.std(T)

    print(f"\nStd of T across bits: {actual_std:.6f}")
    print(f"Expected if random: {expected_std:.6f}")
    print(f"Ratio: {actual_std/expected_std:.2f}×")

    if actual_std > 3 * expected_std:
        print(f"*** T is NON-RANDOM (std {actual_std/expected_std:.0f}× expected)! ***")

    # Test 2: Runs test — are consecutive values correlated?
    median_T = np.median(T)
    runs = 1
    for i in range(1, 32):
        if (T[i] > median_T) != (T[i-1] > median_T):
            runs += 1

    # Expected runs for random binary sequence: (2*n_above*n_below)/n + 1
    n_above = np.sum(T > median_T)
    n_below = 32 - n_above
    expected_runs = 2*n_above*n_below/32 + 1
    print(f"\nRuns test: {runs} runs (expected {expected_runs:.1f})")

    # Test 3: Fourier — any periodicity?
    T_centered = T - T.mean()
    fft = np.fft.fft(T_centered)
    power = np.abs(fft)**2
    peak_freq = np.argmax(power[1:16]) + 1  # Exclude DC
    peak_power = power[peak_freq]

    print(f"\nFourier: peak at frequency {peak_freq} (period={32/peak_freq:.1f})")
    print(f"Peak power: {peak_power:.4f}")

    return T

def test_rotation_prediction(T):
    """Can T be predicted from rotation constants?"""
    print(f"\n--- PREDICT T FROM ROTATIONS ---")

    # Rotation positions of Σ1 (used in e-branch T1 computation)
    sig1_positions = [6, 11, 25]

    # Rotation positions of Σ0 (used in a-branch T2)
    sig0_positions = [2, 13, 22]

    # σ1 (schedule): 17, 19, SHR10
    sig1_sched = [17, 19]

    # σ0 (schedule): 7, 18, SHR3
    sig0_sched = [7, 18]

    # For each bit: compute "rotation score" = how many rotations
    # bring information TO this bit position
    rotation_score = np.zeros(32)
    for bit in range(32):
        score = 0
        for r in sig1_positions:
            source = (bit + r) % 32
            # Information from source bit → this bit through rotation
            score += 1
        for r in sig0_positions:
            source = (bit + r) % 32
            score += 1
        rotation_score[bit] = score

    # Does rotation_score predict T?
    corr = np.corrcoef(rotation_score, T)[0, 1]
    print(f"corr(rotation_score, T) = {corr:+.6f}")

    # More sophisticated: distance from nearest rotation alignment
    rotation_align = np.zeros(32)
    all_rotations = sig1_positions + sig0_positions + sig1_sched + sig0_sched
    for bit in range(32):
        min_dist = min(min(abs(bit - r), abs(bit - (r-32)), abs(bit + 32 - r))
                      for r in all_rotations)
        rotation_align[bit] = 1.0 / (min_dist + 1)

    corr_align = np.corrcoef(rotation_align, T)[0, 1]
    print(f"corr(rotation_alignment, T) = {corr_align:+.6f}")

    # Carry chain length model: T[b] ≈ (1/2)^(chain_length from last K-position)
    # K-positions reset carry. After a K, carry is 0.
    # T[0] = 1 (always, no carry-in)
    # T[1] = P(carry_0 same for both messages) = P(a₀·b₀ same) ≈ 0.625
    # T[b] ≈ P(carry chain survives b positions) = ??? depends on GKP

    # Simple model: T[b] = 0.5 + 0.5 * (1/2)^b
    model_decay = np.array([0.5 + 0.5 * (0.5)**b for b in range(32)])
    corr_decay = np.corrcoef(model_decay, T)[0, 1]
    print(f"corr(exponential_decay_model, T) = {corr_decay:+.6f}")

    # Best single predictor
    print(f"\nBest predictor of T:")
    print(f"  rotation_score: {corr:.4f}")
    print(f"  rotation_align: {corr_align:.4f}")
    print(f"  exp_decay:      {corr_decay:.4f}")

    # Plot comparison
    print(f"\n{'Bit':>4} | {'T actual':>8} | {'rot_score':>9} | {'align':>6} | {'decay':>6}")
    print("-"*45)
    for b in [0,1,2,3,5,9,10,14,19,25,27,29,31]:
        print(f"{b:>4} | {T[b]:>8.3f} | {rotation_score[b]:>9.0f} | "
              f"{rotation_align[b]:>6.3f} | {model_decay[b]:>6.3f}")

def test_modified_rotations(N=1500):
    """What if we change rotation constants? Does T change predictably?"""
    print(f"\n--- MODIFIED ROTATIONS ---")

    # Can't easily modify SHA-256 rotations in our code
    # Instead: compare T for different WORDS (which use Σ0 vs Σ1)

    # T for different additions in the round function:
    # Addition d+T1: uses Σ1(e) through T1
    # Addition T1+T2: uses both Σ0 and Σ1

    # We already measured T for e-branch (Σ1 dominant)
    # Now measure for a-branch (Σ0 dominant)

    T_e = np.zeros(32)
    T_a = np.zeros(32)

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        for bit in range(32):
            for w in range(4):  # a-branch
                s_x = (sn[64][w]^sf[64][w]>>bit)&1
                h_x = (Hn[w]^Hf[w]>>bit)&1
                if s_x == h_x: T_a[bit] += 1

            for w in range(4,8):  # e-branch
                s_x = (sn[64][w]^sf[64][w]>>bit)&1
                h_x = (Hn[w]^Hf[w]>>bit)&1
                if s_x == h_x: T_e[bit] += 1

    T_e /= (N*4); T_a /= (N*4)

    corr_ae = np.corrcoef(T_a, T_e)[0, 1]
    print(f"corr(T_a, T_e) = {corr_ae:+.6f}")
    print(f"\nComparison (peaks):")
    for b in [0,1,9,14,19,27,29]:
        print(f"  Bit {b:>2}: T_a={T_a[b]:.3f}, T_e={T_e[b]:.3f}, diff={T_a[b]-T_e[b]:+.3f}")

    if abs(corr_ae) > 0.5:
        print(f"\n*** a-branch and e-branch have SIMILAR transparency pattern! ***")
        print(f"This means: pattern comes from FEEDFORWARD, not from Σ0/Σ1")
    else:
        print(f"\n*** Patterns DIFFER → rotation constants SHAPE transparency ***")

def test_transparent_subspace_size():
    """How many bits are 'transparent' (T > threshold)?"""
    print(f"\n--- TRANSPARENT SUBSPACE SIZE ---")

    T = measure_transparency_pattern(2000)

    for thresh in [0.55, 0.60, 0.65, 0.70, 0.80, 0.90, 1.00]:
        n_bits = np.sum(T >= thresh)
        n_total = n_bits * 8  # 8 words
        birthday_gain = n_total / 2
        print(f"  T≥{thresh:.2f}: {n_bits}/32 bits × 8 words = {n_total} total, "
              f"birthday gain: {birthday_gain:.0f} bits → 2^{128-birthday_gain:.0f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 72: TRANSPARENCY THEORY")
    print("T(bit) = f(rotations)?")
    print("="*60)

    T = test_randomness_of_pattern()
    test_rotation_prediction(T)
    test_modified_rotations(1200)
    test_transparent_subspace_size()

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
