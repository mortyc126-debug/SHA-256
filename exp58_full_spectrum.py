#!/usr/bin/env python3
"""
EXP 58: Full Lyapunov Spectrum + Pipe Structure

From exp57: first 32 exponents show THREE-LEVEL hierarchy:
  Level 1 (λ≈2.1-2.7): Word-pair expansion (4 pipe pairs)
  Level 2 (λ≈1.0-1.2): Intra-word bit mixing
  Level 3 (λ≈0.7-0.9): Carry chain mixing

This is NOT random — random spectrum = smooth Marchenko-Pastur.
Three steps = structural hierarchy.

NOW: compute FULL 256 spectrum.
For bijection: Σλᵢ = 0 → negative exponents exist.
The WEAKLY CONTRACTING directions = most vulnerable to collision.

Also: verify pipe pair structure (does eigenvalue pairing match
the (a,e), (b,f), (c,g), (d,h) pipe structure?)
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_full_spectrum(W16, n_rounds=64):
    """Compute FULL 256-exponent Lyapunov spectrum."""
    W = schedule(W16)
    states = sha256_rounds(W16, n_rounds)

    # Full 256×256 perturbation frame
    M = np.eye(256, dtype=np.float64)
    lyap_sum = np.zeros(256)

    for r in range(n_rounds):
        state = states[r]
        new_state = sha256_round(state, W[r], K[r])

        # Full 256×256 Jacobian
        J = np.zeros((256, 256), dtype=np.float64)
        for j in range(256):
            w = j//32; b = j%32
            s_p = list(state); s_p[w] ^= (1<<b)
            ns_p = sha256_round(s_p, W[r], K[r])
            for i in range(256):
                wi = i//32; bi = i%32
                J[i][j] = float(((new_state[wi]>>bi)&1) ^ ((ns_p[wi]>>bi)&1))

        # Evolve frame and QR
        evolved = J @ M
        Q, R_mat = np.linalg.qr(evolved)
        M = Q

        # Accumulate
        for i in range(256):
            lyap_sum[i] += np.log2(max(abs(R_mat[i,i]), 1e-30))

    return np.sort(lyap_sum / n_rounds)[::-1]

def test_full_spectrum(N=2):
    """Compute and analyze full 256-exponent spectrum."""
    print("\n--- FULL LYAPUNOV SPECTRUM (256 exponents) ---")

    all_spectra = []
    for trial in range(N):
        print(f"  Computing trial {trial+1}/{N}...", flush=True)
        W16 = random_w16()
        spec = compute_full_spectrum(W16)
        all_spectra.append(spec)

    avg = np.mean(all_spectra, axis=0)

    # Summary statistics
    n_pos = np.sum(avg > 0.01)
    n_neg = np.sum(avg < -0.01)
    n_zero = 256 - n_pos - n_neg

    print(f"\nSpectrum summary:")
    print(f"  Positive (λ>0.01): {n_pos}")
    print(f"  Near-zero (|λ|<0.01): {n_zero}")
    print(f"  Negative (λ<-0.01): {n_neg}")
    print(f"  Sum of ALL: {avg.sum():+.4f} (bijection → should be ≈0)")
    print(f"  Max: {avg[0]:+.4f}, Min: {avg[-1]:+.4f}")

    # Hierarchical structure
    print(f"\nSpectrum by groups of 8:")
    for g in range(32):
        start = g*8; end = start+8
        group = avg[start:end]
        print(f"  λ_{start+1:>3}-{end:>3}: [{group[0]:+.4f} ... {group[-1]:+.4f}] "
              f"mean={group.mean():+.4f}")

    # Kaplan-Yorke dimension
    cumsum = np.cumsum(avg)
    j = np.max(np.where(cumsum > 0)[0]) if np.any(cumsum > 0) else 0
    if j + 1 < 256 and avg[j+1] < 0:
        D_KY = (j+1) + cumsum[j] / abs(avg[j+1])
    else:
        D_KY = 256
    print(f"\nKaplan-Yorke dimension: D_KY = {D_KY:.2f} / 256")
    print(f"Collision cost estimate: 2^({D_KY/2:.1f})")

    # Pipe pair structure: check if eigenvalues pair up
    print(f"\nPipe pair structure test:")
    print(f"  Eigenvalue gaps for consecutive pairs:")
    for k in range(16):
        i1 = 2*k; i2 = 2*k+1
        gap = avg[i1] - avg[i2]
        pipe_pair = gap < 0.3 * abs(avg[i1]) if avg[i1] != 0 else False
        print(f"    k={k:>2}: l={avg[i1]:+.4f}, {avg[i2]:+.4f}  "
              f"gap={gap:.4f} {'<- PAIR' if pipe_pair else ''}")

    return avg

def main():
    random.seed(42)
    print("="*60)
    print("EXP 58: FULL LYAPUNOV SPECTRUM (256 exponents)")
    print("="*60)
    spectrum = test_full_spectrum(2)

if __name__ == "__main__":
    main()
