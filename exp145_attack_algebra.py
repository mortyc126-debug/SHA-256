#!/usr/bin/env python3
"""
EXP 145: ★-ATTACK ALGEBRA — Offensive Framework

NOT: "what survives?" (defensive)
BUT: "what can be STEERED?" (offensive)

NEW OBJECTS:
  1. ★-Attack Matrix: Jacobian of round function on ★-pairs
  2. ★-Vulnerability Spectrum: eigenvalues of attack matrix product
  3. ★-Kill Chain: sequence of δW that drives δXOR → 0
  4. ★-Slow Modes: eigenvectors with |λ| close to 1
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_star_pair(s1, s2):
    """★-pair of two states: (δXOR per word, δAND per word)."""
    dxor = [s1[w] ^ s2[w] for w in range(8)]
    dand = [s1[w] & s2[w] for w in range(8)]
    return dxor, dand

def star_pair_to_bitvec(dxor, dand):
    """Convert ★-pair to 512-bit vector."""
    vec = []
    for w in range(8):
        for b in range(32):
            vec.append((dxor[w] >> b) & 1)
    for w in range(8):
        for b in range(32):
            vec.append((dand[w] >> b) & 1)
    return np.array(vec, dtype=float)

# ============================================================
# 1. ★-ATTACK MATRIX: Jacobian on ★-pairs
# ============================================================
def compute_attack_matrix(S_base, W_r, K_r, sample_size=256):
    """Compute the ★-attack matrix at a specific round.

    A_r[i,j] = how flipping bit j of ★-pair affects bit i after one round.

    We use a PAIRED approach: start with S₁=S₂=S_base, then perturb S₂
    at each bit position and measure the output ★-pair change."""

    # Base: S₁ = S₂ = S_base, same W → output S₁' = S₂' → Ψ' = (0, S'&S')
    S_base_after = sha256_round(list(S_base), W_r, K_r)

    # Perturb: flip one bit of S₂, compute new ★-pair
    n_bits = min(sample_size, 256)  # Sample columns of Jacobian

    # Output ★-pair changes for XOR-component perturbations
    A_columns = []
    bit_indices = random.sample(range(256), n_bits)

    for bit_idx in bit_indices:
        w = bit_idx // 32
        b = bit_idx % 32

        # Perturb S₂ at this bit
        S2_pert = list(S_base)
        S2_pert[w] ^= (1 << b)

        # Compute round for perturbed S₂
        S2_after = sha256_round(S2_pert, W_r, K_r)

        # ★-pair of (S_base_after, S2_after)
        dxor_out = [S_base_after[w2] ^ S2_after[w2] for w2 in range(8)]

        # Output as bit vector (just XOR part, 256 bits)
        col = []
        for w2 in range(8):
            for b2 in range(32):
                col.append((dxor_out[w2] >> b2) & 1)

        A_columns.append(col)

    A = np.array(A_columns).T  # 256 × n_bits
    return A, bit_indices

def analyze_attack_spectrum(N=50):
    """Compute and analyze ★-attack matrix eigenvalues."""
    print(f"\n{'='*60}")
    print(f"★-ATTACK MATRIX SPECTRUM (N={N})")
    print(f"{'='*60}")

    # Compute attack matrix for specific rounds
    for r in [0, 15, 31, 63]:
        all_singular = []
        for _ in range(N):
            S = [random.randint(0, MASK) for _ in range(8)]
            W_r = random.randint(0, MASK)

            A, _ = compute_attack_matrix(S, W_r, K[r], sample_size=200)

            # SVD to get singular values (≈ eigenvalues for square part)
            _, sigma, _ = np.linalg.svd(A, full_matrices=False)
            all_singular.append(sigma)

        # Average spectrum
        min_len = min(len(s) for s in all_singular)
        avg_spectrum = np.mean([s[:min_len] for s in all_singular], axis=0)

        print(f"\n  Round {r}: top singular values of ★-attack matrix:")
        print(f"    σ₁={avg_spectrum[0]:.3f}  σ₂={avg_spectrum[1]:.3f}  "
              f"σ₃={avg_spectrum[2]:.3f}  σ₅={avg_spectrum[4]:.3f}  "
              f"σ₁₀={avg_spectrum[9]:.3f}  σ₅₀={avg_spectrum[min(49, min_len-1)]:.3f}")
        print(f"    Condition: σ₁/σ_last = {avg_spectrum[0]/avg_spectrum[-1]:.2f}")
        print(f"    Effective rank (90%): {np.searchsorted(np.cumsum(avg_spectrum**2)/np.sum(avg_spectrum**2), 0.9)+1}")

# ============================================================
# 2. MULTI-ROUND ATTACK MATRIX PRODUCT
# ============================================================
def compute_multi_round_spectrum(N=30):
    """Product of attack matrices across multiple rounds."""
    print(f"\n{'='*60}")
    print(f"MULTI-ROUND ★-ATTACK SPECTRUM (N={N})")
    print(f"{'='*60}")

    n_bits = 128  # Reduced for tractability

    for n_rounds in [1, 2, 4, 8, 16]:
        all_singular = []

        for _ in range(N):
            M = random_w16()
            W = schedule(M)
            states = sha256_rounds(M, n_rounds)

            # Product of attack matrices
            T = np.eye(n_bits)

            for r in range(n_rounds):
                # Compute A_r at state after round r
                A, indices = compute_attack_matrix(states[r], W[r], K[r],
                                                   sample_size=n_bits)
                # A is 256 × n_bits, we need n_bits × n_bits
                A_square = A[:n_bits, :]
                T = A_square @ T

            _, sigma, _ = np.linalg.svd(T, full_matrices=False)
            all_singular.append(sigma)

        min_len = min(len(s) for s in all_singular)
        avg = np.mean([s[:min_len] for s in all_singular], axis=0)

        # Normalize by number of rounds
        per_round = avg ** (1.0 / n_rounds) if n_rounds > 0 else avg

        print(f"\n  {n_rounds} rounds: σ₁={avg[0]:.4f} σ₂={avg[1]:.4f} "
              f"σ₅={avg[min(4,min_len-1)]:.4f} σ₁₀={avg[min(9,min_len-1)]:.4f}")
        print(f"    Per-round: σ₁^(1/R)={per_round[0]:.4f} "
              f"σ₂^(1/R)={per_round[1]:.4f}")

        if per_round[0] > 0.9:
            print(f"    ★★★ SLOW MODE EXISTS: per-round decay = {1-per_round[0]:.4f}")

# ============================================================
# 3. ★-KILL CHAIN: Can we steer δXOR → 0?
# ============================================================
def test_kill_chain(N=30, R=4):
    """Attempt to build a kill chain: choose δM to drive δXOR → 0."""
    print(f"\n{'='*60}")
    print(f"★-KILL CHAIN ({R} rounds, N={N})")
    print(f"{'='*60}")

    # Strategy: for each message word W[r] (r=0..15),
    # choose δW[r] to CANCEL the accumulated δXOR at round r.
    #
    # At round r: δXOR_new = f(δXOR_old, δW_r)
    # We want δXOR_new ≈ 0, so δW_r should compensate δXOR_old.
    #
    # From Theorem ★-9: when states are similar (early rounds),
    # δ(new_a) ≈ δW_r. So setting δW_r ≈ -δXOR_old on word a
    # should reduce the accumulated difference.

    successes = 0

    for trial in range(N):
        M1 = random_w16()

        # Start with M2 = M1, then modify one word to create initial δ
        M2 = list(M1)
        M2[0] = (M2[0] + 1) & MASK  # Small initial difference

        # Now: can we choose M2[1]..M2[R-1] to STEER toward collision?
        s1 = sha256_rounds(M1, R)
        s2 = sha256_rounds(M2, R)

        # Greedy kill chain: at each step, try to minimize δXOR
        M2_chain = list(M2)
        best_dxor = sum(hw(s1[R][w] ^ s2[R][w]) for w in range(8))

        for step in range(min(R, 15)):
            # Try different values for M2[step+1] (if available)
            if step + 1 >= 16:
                break

            best_val = M2_chain[step + 1]
            for _ in range(200):  # Budget per word
                val = random.randint(0, MASK)
                M2_test = list(M2_chain)
                M2_test[step + 1] = val
                s2_test = sha256_rounds(M2_test, R)
                dxor = sum(hw(s1[R][w] ^ s2_test[R][w]) for w in range(8))

                if dxor < best_dxor:
                    best_dxor = dxor
                    best_val = val

            M2_chain[step + 1] = best_val

        final_dxor = best_dxor
        if final_dxor == 0:
            successes += 1
            print(f"  Trial {trial}: ★-KILL CHAIN SUCCESS! δXOR = 0")
        elif trial < 5:
            print(f"  Trial {trial}: best δXOR = {final_dxor}")

    print(f"\n  Kill chains: {successes}/{N}")

    # Compare with pure random
    rand_successes = 0
    rand_best = 256
    for trial in range(N):
        M1 = random_w16()
        for _ in range(200 * R):
            M2 = random_w16()
            s1 = sha256_rounds(M1, R)
            s2 = sha256_rounds(M2, R)
            dxor = sum(hw(s1[R][w] ^ s2[R][w]) for w in range(8))
            if dxor < rand_best:
                rand_best = dxor
            if dxor == 0:
                rand_successes += 1
                break

    print(f"  Random: {rand_successes}/{N}, best = {rand_best}")

# ============================================================
# 4. ★-SLOW MODES: Directions that decay slowest
# ============================================================
def find_slow_modes(N=100):
    """Find directions in ★-space that survive longest through rounds."""
    print(f"\n{'='*60}")
    print(f"★-SLOW MODES: Which directions survive?")
    print(f"{'='*60}")

    # For each 1-bit perturbation of the state, measure how many
    # rounds until it's fully randomized. Average over many base states.

    survival = np.zeros((8, 32))  # Per word, per bit: survival rounds

    for _ in range(N):
        S = [random.randint(0, MASK) for _ in range(8)]
        W_vals = [random.randint(0, MASK) for _ in range(64)]

        for w in range(8):
            for b in range(0, 32, 4):  # Sample every 4th bit
                S1 = list(S)
                S2 = list(S); S2[w] ^= (1 << b)

                # Track through rounds
                s1, s2 = list(S1), list(S2)
                for r in range(64):
                    s1 = sha256_round(s1, W_vals[r], K[r])
                    s2 = sha256_round(s2, W_vals[r], K[r])
                    dxor = sum(hw(s1[w2] ^ s2[w2]) for w2 in range(8))

                    if dxor > 120:  # Effectively random
                        survival[w, b] = r + 1
                        break
                else:
                    survival[w, b] = 64

    print(f"\n  Rounds until full randomization per state bit:")
    print(f"  (lower = faster decay = HARDER to exploit)")
    print(f"  {'Word':>6} | {'Bit 0':>6} | {'Bit 8':>6} | {'Bit 16':>6} | {'Bit 24':>6} | {'Avg':>6}")
    print(f"  " + "-" * 45)

    for w in range(8):
        avgs = [survival[w, b] for b in range(0, 32, 4)]
        print(f"  {w:>6} | {survival[w,0]:>6.1f} | {survival[w,8]:>6.1f} | "
              f"{survival[w,16]:>6.1f} | {survival[w,24]:>6.1f} | {np.mean(avgs):>6.1f}")

    # Which word/bit survives LONGEST?
    max_survival = 0
    best_pos = (0, 0)
    for w in range(8):
        for b in range(0, 32, 4):
            if survival[w, b] > max_survival:
                max_survival = survival[w, b]
                best_pos = (w, b)

    print(f"\n  Slowest mode: word {best_pos[0]} bit {best_pos[1]}, "
          f"survives {max_survival:.1f} rounds")
    print(f"  Fastest mode: {survival.min():.1f} rounds")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 145: ★-ATTACK ALGEBRA")
    print("Offensive framework: matrices, spectrum, kill chains")
    print("=" * 60)

    analyze_attack_spectrum(N=30)
    compute_multi_round_spectrum(N=20)
    find_slow_modes(N=50)
    test_kill_chain(N=20, R=4)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★-Attack Algebra")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
