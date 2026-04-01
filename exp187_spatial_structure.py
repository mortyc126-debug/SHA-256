#!/usr/bin/env python3
"""
EXP 187: SPATIAL STRUCTURE — WHERE are the differences, not just how many?

Thermostat controls HW(δ) ≈ 32. But WHICH 32 bits?
If the SAME bits keep differing → spatial pattern → predictable → exploitable.

The thermostat is BLIND to spatial arrangement.
This might be the unguarded window.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_ae_diff_vector(s1, s2):
    """64-bit difference vector for (a,e)."""
    vec = []
    for b in range(32):
        vec.append(((s1[0] >> b) & 1) ^ ((s2[0] >> b) & 1))
    for b in range(32):
        vec.append(((s1[4] >> b) & 1) ^ ((s2[4] >> b) & 1))
    return np.array(vec, dtype=int)

def spatial_persistence(N=300, N_rounds=200):
    """Do the SAME bit positions keep differing across rounds?"""
    print(f"\n{'='*60}")
    print(f"SPATIAL PERSISTENCE — Same bits differing round after round?")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1)
    M2[15] ^= (1 << 31)

    s1_all = sha256_rounds(M1, min(N_rounds, 64))
    s2_all = sha256_rounds(M2, min(N_rounds, 64))

    # For rounds 30-60: which bit positions MOST OFTEN differ?
    bit_diff_freq = np.zeros(64)  # How often each bit is in δ
    consecutive_same = np.zeros(64)  # How often δ[r] bit = δ[r+1] bit

    prev_vec = None
    for r in range(30, min(N_rounds, 64)):
        vec = get_ae_diff_vector(s1_all[r], s2_all[r])
        bit_diff_freq += vec

        if prev_vec is not None:
            # How many bits stayed the SAME between rounds?
            consecutive_same += (vec == prev_vec).astype(int)
        prev_vec = vec

    n_rounds = min(N_rounds, 64) - 30
    bit_diff_freq /= n_rounds
    consecutive_same /= (n_rounds - 1)

    # Expected: each bit differs 50% of the time (random)
    # Expected consecutive same: 50% (bit has 50% chance of same value)
    print(f"\n  Per-bit difference frequency (expected: 0.500):")
    print(f"    Mean: {bit_diff_freq.mean():.4f}")
    print(f"    Std:  {bit_diff_freq.std():.4f}")
    print(f"    Max:  {bit_diff_freq.max():.4f} at bit {np.argmax(bit_diff_freq)}")
    print(f"    Min:  {bit_diff_freq.min():.4f} at bit {np.argmin(bit_diff_freq)}")

    # HOT SPOTS (differ more often) and COLD SPOTS (differ less)
    hot = np.argsort(-bit_diff_freq)[:8]
    cold = np.argsort(bit_diff_freq)[:8]

    print(f"\n  HOT SPOTS (most often different):")
    for idx in hot:
        word = "a" if idx < 32 else "e"
        b = idx % 32
        print(f"    {word}[{b:>2}]: diff freq = {bit_diff_freq[idx]:.4f}, "
              f"persist = {consecutive_same[idx]:.4f}")

    print(f"\n  COLD SPOTS (least often different):")
    for idx in cold:
        word = "a" if idx < 32 else "e"
        b = idx % 32
        print(f"    {word}[{b:>2}]: diff freq = {bit_diff_freq[idx]:.4f}, "
              f"persist = {consecutive_same[idx]:.4f}")

    # PERSISTENCE: how often does a bit STAY in δ for multiple rounds?
    print(f"\n  Bit persistence (same δ-status across consecutive rounds):")
    print(f"    Mean: {consecutive_same.mean():.4f} (expected: 0.500 for random)")
    print(f"    Max:  {consecutive_same.max():.4f}")

    if consecutive_same.mean() > 0.55:
        print(f"    ★★★ SPATIAL PERSISTENCE EXISTS! Bits 'stick' at {consecutive_same.mean():.1%}")
    elif consecutive_same.mean() > 0.52:
        print(f"    ★★ SLIGHT persistence ({consecutive_same.mean():.1%})")

    return bit_diff_freq, consecutive_same

def spatial_across_messages(N=200):
    """Are hot/cold spots UNIVERSAL or message-dependent?"""
    print(f"\n{'='*60}")
    print(f"UNIVERSAL SPATIAL PATTERN? (N={N} messages)")
    print(f"{'='*60}")

    # Collect bit_diff_freq for MANY message pairs
    all_freqs = np.zeros((N, 64))

    for trial in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[random.randint(12,15)] ^= (1 << random.randint(0,31))

        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        freq = np.zeros(64)
        for r in range(30, 64):
            vec = get_ae_diff_vector(s1_all[r], s2_all[r])
            freq += vec
        freq /= 34
        all_freqs[trial] = freq

    # Average across messages
    avg_freq = all_freqs.mean(axis=0)
    std_freq = all_freqs.std(axis=0)

    print(f"\n  Average bit-diff frequency across {N} messages:")
    print(f"    Mean: {avg_freq.mean():.4f} (expected: 0.500)")
    print(f"    Std of mean: {std_freq.mean():.4f}")

    # Are there UNIVERSALLY hot/cold positions?
    z_scores = (avg_freq - 0.5) / (std_freq / math.sqrt(N) + 1e-6)

    n_hot = np.sum(z_scores > 3)
    n_cold = np.sum(z_scores < -3)

    print(f"    Universally HOT (Z>3): {n_hot}/64 positions")
    print(f"    Universally COLD (Z<-3): {n_cold}/64 positions")

    if n_hot + n_cold > 0:
        print(f"\n    ★★★ UNIVERSAL SPATIAL STRUCTURE EXISTS!")
        print(f"\n    Hot positions:")
        for idx in np.where(z_scores > 3)[0]:
            word = "a" if idx < 32 else "e"
            b = idx % 32
            print(f"      {word}[{b:>2}]: freq={avg_freq[idx]:.4f}, Z={z_scores[idx]:+.2f}")

        print(f"\n    Cold positions:")
        for idx in np.where(z_scores < -3)[0]:
            word = "a" if idx < 32 else "e"
            b = idx % 32
            print(f"      {word}[{b:>2}]: freq={avg_freq[idx]:.4f}, Z={z_scores[idx]:+.2f}")
    else:
        print(f"    No universal structure (all positions equally likely)")

    # CORRELATION between messages: do different messages have similar patterns?
    inter_msg_corrs = []
    for i in range(min(50, N)):
        for j in range(i+1, min(50, N)):
            c = np.corrcoef(all_freqs[i], all_freqs[j])[0, 1]
            if not np.isnan(c):
                inter_msg_corrs.append(c)

    if inter_msg_corrs:
        mc = np.array(inter_msg_corrs)
        print(f"\n    Inter-message spatial correlation:")
        print(f"      Mean: {mc.mean():.4f} (0 = independent, 1 = identical)")
        if mc.mean() > 0.05:
            print(f"      ★★ Messages share spatial structure!")

    return avg_freq, z_scores

def spatial_vector_dynamics(N=300):
    """Track the DIRECTION (not magnitude) of δ through rounds."""
    print(f"\n{'='*60}")
    print(f"DIRECTION DYNAMICS — Where δ POINTS, not how big")
    print(f"{'='*60}")

    # Cosine similarity between δ[r] and δ[r+k]
    # If direction persists: cosine ≈ 1
    # If direction randomizes: cosine ≈ 0

    for k in [1, 2, 4, 8, 16, 32]:
        cosines = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

            for r in range(30, min(64-k, 60)):
                v1 = get_ae_diff_vector(s1[r], s2[r]).astype(float)
                v2 = get_ae_diff_vector(s1[r+k], s2[r+k]).astype(float)

                n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
                if n1 > 0 and n2 > 0:
                    cos = np.dot(v1, v2) / (n1 * n2)
                    cosines.append(cos)

        ca = np.array(cosines) if cosines else np.array([0])
        # Expected for random 64-bit vectors with ~32 ones each:
        # cosine ≈ 0.5 (half of bits agree)
        expected = 0.5

        print(f"  Lag {k:>2}: cos(δ[r], δ[r+{k}]) = {ca.mean():.4f} "
              f"(random={expected:.3f})", end="")
        if ca.mean() > expected + 0.02:
            print(f" ★ DIRECTION PERSISTS!")
        elif ca.mean() < expected - 0.02:
            print(f" ★ DIRECTION ANTI-PERSISTS!")
        else:
            print()

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 187: SPATIAL STRUCTURE IN δ(a,e)")
    print("WHERE differ the bits, not just how many")
    print("=" * 60)

    freq, persist = spatial_persistence(N_rounds=64)
    avg_freq, z_scores = spatial_across_messages(N=150)
    spatial_vector_dynamics(N=200)

    print(f"\n{'='*60}")
    print(f"VERDICT: Spatial structure?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
