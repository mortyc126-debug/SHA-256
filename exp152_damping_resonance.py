#!/usr/bin/env python3
"""
EXP 152: DAMPING RESONANCE — Find directions where δ SHRINKS

From exp145: σ₁ ≈ 12 (amplification), condition ≈ 120.
→ σ_min ≈ 0.1 (DAMPING — difference SHRINKS!)

If σ_min < 1: perturbation in that direction decreases each round.
After 64 rounds: 0.1^64 → δ ≈ 0 → COLLISION?

PLAN:
1. Compute FULL singular value spectrum of ★-attack matrix
2. Identify ALL damping modes (σ < 1)
3. Find the damping EIGENVECTOR
4. Inject δ along damping direction
5. Track: does it actually shrink through real SHA-256 rounds?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_full_attack_matrix(S, W_r, K_r, n_bits=256):
    """Full 256×256 ★-attack matrix at one round."""
    S_after = sha256_round(list(S), W_r, K_r)

    A = np.zeros((n_bits, n_bits), dtype=float)

    for j in range(n_bits):
        w_in = j // 32
        b_in = j % 32

        S2 = list(S); S2[w_in] ^= (1 << b_in)
        S2_after = sha256_round(S2, W_r, K_r)

        for i in range(n_bits):
            w_out = i // 32
            b_out = i % 32
            A[i, j] = ((S_after[w_out] ^ S2_after[w_out]) >> b_out) & 1

    return A

def test_full_spectrum(N=20):
    """Compute full 256×256 singular value spectrum."""
    print(f"\n{'='*60}")
    print(f"FULL SINGULAR VALUE SPECTRUM (N={N})")
    print(f"{'='*60}")

    all_spectra = []
    for _ in range(N):
        S = [random.randint(0, MASK) for _ in range(8)]
        W_r = random.randint(0, MASK)
        r = random.randint(0, 63)

        A = compute_full_attack_matrix(S, W_r, K[r])
        _, sigma, _ = np.linalg.svd(A)
        all_spectra.append(sigma)

    # Average spectrum
    avg = np.mean(all_spectra, axis=0)

    print(f"\n  Singular value spectrum (256 values):")
    print(f"    σ₁   = {avg[0]:.4f}")
    print(f"    σ₅   = {avg[4]:.4f}")
    print(f"    σ₁₀  = {avg[9]:.4f}")
    print(f"    σ₅₀  = {avg[49]:.4f}")
    print(f"    σ₁₀₀ = {avg[99]:.4f}")
    print(f"    σ₂₀₀ = {avg[199]:.4f}")
    print(f"    σ₂₅₀ = {avg[249]:.4f}")
    print(f"    σ₂₅₆ = {avg[255]:.4f}")

    n_damping = np.sum(avg < 1.0)
    n_strong_damping = np.sum(avg < 0.5)
    print(f"\n    Modes with σ < 1.0 (damping): {n_damping}/256")
    print(f"    Modes with σ < 0.5 (strong damping): {n_strong_damping}/256")
    print(f"    Modes with σ < 0.1 (extreme damping): {np.sum(avg < 0.1)}/256")

    print(f"\n    Condition: σ₁/σ₂₅₆ = {avg[0]/avg[255]:.1f}")

    if n_damping > 0:
        print(f"\n  ★★★ DAMPING MODES EXIST! {n_damping} directions shrink per round!")
        print(f"    If σ_min = {avg[255]:.4f}: after 64 rounds = {avg[255]**64:.2e}")

    return avg, all_spectra

def test_damping_eigenvector(N=10):
    """Find the damping eigenvector and test if it works."""
    print(f"\n{'='*60}")
    print(f"DAMPING EIGENVECTOR — DOES δ SHRINK?")
    print(f"{'='*60}")

    for trial in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)
        W = schedule(M)

        # Compute attack matrix at round 0
        A = compute_full_attack_matrix(states[0], W[0], K[0])
        U, sigma, Vt = np.linalg.svd(A)

        # Damping direction = last right singular vector (smallest σ)
        v_damp = Vt[-1]  # 256-dim vector

        # Amplifying direction = first right singular vector (largest σ)
        v_amp = Vt[0]

        # Convert to state perturbation
        def vec_to_state_delta(v):
            """Convert 256-dim vector to 8-word state difference."""
            delta = [0] * 8
            for i in range(256):
                if abs(v[i]) > 0.5:  # Threshold to binary
                    w = i // 32; b = i % 32
                    delta[w] |= (1 << b)
            return delta

        delta_damp = vec_to_state_delta(v_damp)
        delta_amp = vec_to_state_delta(v_amp)

        # Apply perturbation and track through REAL SHA-256
        M2_damp = list(M)
        # Apply state delta via message word 0 (approximate)
        M2_damp[0] ^= delta_damp[0]  # Only word 0 for simplicity

        M2_amp = list(M)
        M2_amp[0] ^= delta_amp[0]

        M2_rand = list(M)
        M2_rand[0] ^= random.randint(1, MASK)

        s1 = sha256_rounds(M, 64)
        s_damp = sha256_rounds(M2_damp, 64)
        s_amp = sha256_rounds(M2_amp, 64)
        s_rand = sha256_rounds(M2_rand, 64)

        if trial < 3:
            print(f"\n  Trial {trial}: σ_min={sigma[-1]:.4f}, σ_max={sigma[0]:.4f}")
            print(f"    HW(δ_damp[0]) = {hw(delta_damp[0])}")
            print(f"    HW(δ_amp[0]) = {hw(delta_amp[0])}")

            for label, s2 in [("damping", s_damp), ("amplifying", s_amp), ("random", s_rand)]:
                dH_vals = []
                for r in [1, 2, 4, 8, 16, 32, 64]:
                    dH = sum(hw(s1[r][w] ^ s2[r][w]) for w in range(8))
                    dH_vals.append(f"{dH:>3}")
                print(f"    {label:>10}: r1={dH_vals[0]} r2={dH_vals[1]} r4={dH_vals[2]} "
                      f"r8={dH_vals[3]} r16={dH_vals[4]} r32={dH_vals[5]} r64={dH_vals[6]}")

def test_multi_round_damping(N=30):
    """Compute PRODUCT of attack matrices, find damping across rounds."""
    print(f"\n{'='*60}")
    print(f"MULTI-ROUND DAMPING SPECTRUM (N={N})")
    print(f"{'='*60}")

    for n_rounds in [2, 4, 8]:
        all_sigma_min = []

        for _ in range(N):
            M = random_w16()
            states = sha256_rounds(M, n_rounds)
            W = schedule(M)

            T = np.eye(256)
            for r in range(n_rounds):
                A = compute_full_attack_matrix(states[r], W[r], K[r])
                T = A @ T

            _, sigma, Vt = np.linalg.svd(T)
            all_sigma_min.append(sigma[-1])

            # Per-round damping rate
            sigma_min_per_round = sigma[-1] ** (1.0/n_rounds) if sigma[-1] > 0 else 0

        avg_min = np.mean(all_sigma_min)
        per_round = avg_min ** (1.0/n_rounds) if avg_min > 0 else 0

        print(f"\n  {n_rounds} rounds:")
        print(f"    σ_min (product) = {avg_min:.6f}")
        print(f"    Per-round damping = {per_round:.6f}")
        if per_round < 1:
            after_64 = per_round ** 64
            print(f"    After 64 rounds: {after_64:.2e}")
            if after_64 < 1e-10:
                print(f"    ★★★ DAMPING TO ZERO — collision direction EXISTS!")

def test_damping_collision_search(N=20, R=4):
    """Use damping direction to search for collision."""
    print(f"\n{'='*60}")
    print(f"DAMPING-GUIDED COLLISION SEARCH ({R} rounds, N={N})")
    print(f"{'='*60}")

    damp_results = []; rand_results = []

    for trial in range(N):
        M1 = random_w16()
        s1 = sha256_rounds(M1, R)
        W = schedule(M1)

        # Compute attack matrix product for R rounds
        T = np.eye(256)
        for r in range(min(R, 4)):  # Limit for speed
            A = compute_full_attack_matrix(s1[r], W[r], K[r])
            T = A @ T

        _, sigma, Vt = np.linalg.svd(T)

        # Get damping direction
        v_damp = Vt[-1]

        # Try perturbations ALONG damping direction
        best_damp = 256
        for _ in range(200):
            M2 = list(M1)
            # Perturb along damping direction with random magnitude
            for i in range(256):
                if abs(v_damp[i]) > 0.5 and random.random() < 0.5:
                    w = i // 32; b = i % 32
                    if w < 16:
                        M2[w] ^= (1 << b)

            if M1 == M2: continue
            s2 = sha256_rounds(M2, R)
            dH = sum(hw(s1[R][w] ^ s2[R][w]) for w in range(8))
            best_damp = min(best_damp, dH)

        damp_results.append(best_damp)

        # Random comparison
        best_rand = 256
        for _ in range(200):
            M2 = random_w16()
            s2 = sha256_rounds(M2, R)
            dH = sum(hw(s1[R][w] ^ s2[R][w]) for w in range(8))
            best_rand = min(best_rand, dH)

        rand_results.append(best_rand)

    da = np.array(damp_results); ra = np.array(rand_results)
    gain = ra.mean() - da.mean()
    print(f"\n  Damping-guided: avg={da.mean():.1f}, min={da.min()}")
    print(f"  Random:         avg={ra.mean():.1f}, min={ra.min()}")
    print(f"  Gain: {gain:+.1f} bits")

    if gain > 3:
        print(f"  ★★★ DAMPING DIRECTION BEATS RANDOM!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 152: DAMPING RESONANCE")
    print("Find directions where differences SHRINK")
    print("=" * 60)

    avg_spectrum, _ = test_full_spectrum(15)
    test_damping_eigenvector(5)
    test_multi_round_damping(15)
    test_damping_collision_search(N=15, R=4)

    print(f"\n{'='*60}")
    print(f"VERDICT: Damping Resonance")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
