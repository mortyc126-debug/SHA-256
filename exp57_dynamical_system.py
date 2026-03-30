#!/usr/bin/env python3
"""
EXP 57: SHA-256 as Dynamical System — Fractal Dimension

SHA-256 is an ITERATED MAP: s[r+1] = F(s[r], W[r], K[r]).
NOT algebra. NOT statistics. DYNAMICS.

Known from our experiments:
  λ = 1.03 bits/round (Lyapunov exponent, exp34)
  τ = 8-12 rounds (correlation time, exp16B)

UNKNOWN: fractal dimension of the SHA-256 attractor.
If D < 256 → collision cost = 2^(D/2) < 2^128.

Method: compute Kaplan-Yorke dimension from Lyapunov spectrum.
D_KY = j + Σ_{i=1}^{j} λ_i / |λ_{j+1}|
where j = largest k such that Σ λ_i > 0.

Need: FULL Lyapunov spectrum λ_1 ≥ λ_2 ≥ ... ≥ λ_256.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def lyapunov_spectrum_round(state, W_r, K_r, perturbation_matrix):
    """
    One step of Lyapunov spectrum computation.
    Propagate perturbation matrix through one round.

    perturbation_matrix: 256 × 256 (orthonormal frame)
    Returns: new state, new perturbation matrix, local expansion rates
    """
    n = 256
    new_state = sha256_round(state, W_r, K_r)

    # Compute Jacobian at this state by finite differences
    J = np.zeros((n, n), dtype=np.float64)

    for j in range(n):
        # Perturb bit j of state
        word = j // 32
        bit = j % 32

        state_pert = list(state)
        state_pert[word] ^= (1 << bit)

        new_state_pert = sha256_round(state_pert, W_r, K_r)

        for i in range(n):
            w = i // 32
            b = i % 32
            J[i][j] = float(((new_state[w] >> b) & 1) ^ ((new_state_pert[w] >> b) & 1))

    # Propagate perturbation frame: M' = J · M
    new_M = (J @ perturbation_matrix) % 2  # Over GF(2)

    # For Lyapunov exponents: use REAL-valued computation
    # Treat binary J as real matrix, QR decompose
    J_real = J.astype(np.float64)
    M_real = perturbation_matrix.astype(np.float64)

    evolved = J_real @ M_real

    # QR decomposition (Gram-Schmidt reorthogonalization)
    Q, R = np.linalg.qr(evolved)

    # Local Lyapunov exponents = log of diagonal of R
    local_lyap = np.log2(np.abs(np.diag(R)) + 1e-30)

    return new_state, Q, local_lyap

def compute_lyapunov_spectrum(W16, n_rounds=64, n_exponents=32):
    """
    Compute first n_exponents Lyapunov exponents of SHA-256.

    Uses QR method: propagate orthonormal frame through rounds,
    reorthogonalize at each step, accumulate log(R_ii).
    """
    states = sha256_rounds(W16, n_rounds)
    W = schedule(W16)

    # Initialize perturbation matrix (n_exp columns of size 256)
    n = min(n_exponents, 256)
    M = np.eye(256, n, dtype=np.float64)  # First n columns of identity

    lyap_sum = np.zeros(n)

    for r in range(n_rounds):
        state = states[r]

        # Compute Jacobian
        new_state = sha256_round(state, W[r], K[r])
        J = np.zeros((256, 256), dtype=np.float64)

        for j in range(256):
            word = j // 32; bit = j % 32
            s_pert = list(state); s_pert[word] ^= (1 << bit)
            ns_pert = sha256_round(s_pert, W[r], K[r])

            for i in range(256):
                w = i // 32; b = i % 32
                J[i][j] = float(((new_state[w]>>b)&1) ^ ((ns_pert[w]>>b)&1))

        # Propagate frame
        evolved = J @ M  # 256 × n

        # QR decomposition
        Q, R = np.linalg.qr(evolved)
        M = Q[:, :n]  # Keep first n columns

        # Accumulate Lyapunov exponents
        for i in range(n):
            lyap_sum[i] += np.log2(max(abs(R[i, i]), 1e-30))

    # Average over rounds
    lyap_exponents = lyap_sum / n_rounds

    return np.sort(lyap_exponents)[::-1]  # Sorted descending

def kaplan_yorke_dimension(lyap_spectrum):
    """
    Kaplan-Yorke dimension:
    D_KY = j + Σ_{i=1}^{j} λ_i / |λ_{j+1}|
    where j = largest k such that Σ_{i=1}^{k} λ_i > 0
    """
    cumsum = np.cumsum(lyap_spectrum)

    # Find j: last index where cumsum > 0
    positive = np.where(cumsum > 0)[0]

    if len(positive) == 0:
        return 0  # No positive exponents

    j = positive[-1]

    if j + 1 >= len(lyap_spectrum):
        return len(lyap_spectrum)  # All positive

    D_KY = (j + 1) + cumsum[j] / abs(lyap_spectrum[j + 1])
    return D_KY

def test_lyapunov_spectrum(N=5):
    """Compute Lyapunov spectrum of SHA-256."""
    print("\n--- LYAPUNOV SPECTRUM ---")

    all_spectra = []

    for trial in range(N):
        W16 = random_w16()

        # Compute first 32 Lyapunov exponents (full 256 too expensive)
        spectrum = compute_lyapunov_spectrum(W16, n_rounds=64, n_exponents=32)
        all_spectra.append(spectrum)

        if trial == 0:
            print(f"First 32 Lyapunov exponents:")
            for i in range(32):
                print(f"  λ_{i+1:>2} = {spectrum[i]:+.4f} bits/round")

    # Average spectrum
    avg_spectrum = np.mean(all_spectra, axis=0)

    print(f"\nAverage spectrum (over {N} messages):")
    print(f"  λ_max = {avg_spectrum[0]:+.4f}")
    print(f"  λ_min (of 32) = {avg_spectrum[-1]:+.4f}")
    n_positive = np.sum(avg_spectrum > 0)
    n_negative = np.sum(avg_spectrum < 0)
    print(f"  Positive exponents: {n_positive}/32")
    print(f"  Negative exponents: {n_negative}/32")
    print(f"  Sum of all 32: {avg_spectrum.sum():+.4f}")

    # Kaplan-Yorke dimension (from 32 exponents)
    D_KY = kaplan_yorke_dimension(avg_spectrum)
    print(f"\nKaplan-Yorke dimension (from 32 exponents): {D_KY:.2f}")
    print(f"Full space dimension: 256")

    if D_KY < 200:
        print(f"*** FRACTAL ATTRACTOR: D={D_KY:.0f} < 256! ***")
        print(f"Collision cost estimate: 2^({D_KY/2:.0f}) instead of 2^128")

    # Extrapolate: if λ_i pattern continues, what's D_KY for all 256?
    if avg_spectrum[-1] < 0:
        # Linear extrapolation of spectrum
        slope = (avg_spectrum[-1] - avg_spectrum[0]) / 31
        full_spectrum = np.array([avg_spectrum[0] + slope * i for i in range(256)])
        D_KY_full = kaplan_yorke_dimension(full_spectrum)
        print(f"\nExtrapolated D_KY (all 256): {D_KY_full:.2f}")

    return avg_spectrum

def test_correlation_dimension(N=3000):
    """
    Alternative: correlation dimension via Grassberger-Procaccia.

    D_2 = lim_{r→0} log C(r) / log r
    where C(r) = fraction of pairs closer than r.

    Apply to HASH OUTPUTS of Wang pairs.
    If D_2 < 256 → fractal structure in output space.
    """
    print(f"\n--- CORRELATION DIMENSION (output space) ---")

    # Collect hash differences for Wang pairs
    diffs = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        d = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        diffs.append(d)

    diffs = np.array(diffs, dtype=np.float64)

    # Correlation integral C(r) = fraction of pairs within distance r
    print(f"{'r':>5} | {'C(r)':>10} | {'log C(r)/log r':>15}")
    print("-"*35)

    for r in [80, 90, 100, 110, 115, 120, 125, 128, 130, 135, 140]:
        pairs_within = 0
        total_pairs = N * (N-1) // 2

        for i in range(min(N, 500)):
            for j in range(i+1, min(N, 500)):
                if abs(diffs[i] - diffs[j]) <= r:
                    pairs_within += 1

        n_tested = min(N, 500)
        total_tested = n_tested * (n_tested-1) // 2
        C_r = pairs_within / total_tested if total_tested > 0 else 0

        if C_r > 0 and r > 0:
            D_est = np.log(C_r) / np.log(r / 256)  # Normalize by max distance
            print(f"{r:>5} | {C_r:>10.6f} | {D_est:>15.4f}")
        else:
            print(f"{r:>5} | {C_r:>10.6f} | {'N/A':>15}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 57: SHA-256 AS DYNAMICAL SYSTEM")
    print("Lyapunov spectrum + fractal dimension")
    print("="*60)

    spectrum = test_lyapunov_spectrum(3)
    test_correlation_dimension(1000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
