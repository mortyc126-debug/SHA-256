#!/usr/bin/env python3
"""
EXPERIMENT 10: Carry Amplitude Theory (CAT) — New Method

All 44 previous approaches treated carry as BINARY (0/1).
Binary carry decays with τ=1.80 rounds (proven).

BUT carry PROBABILITY is CONTINUOUS: ρ_i = 1/2 - 2^{-(i+2)}.
Continuous amplitudes can INTERFERE (constructive/destructive).

This experiment:
Part A: Construct carry amplitude propagation operator L
Part B: Compute eigenvalues of L — check if |λ|≈1 exists
Part C: Test if amplitude-guided differential beats random
Part D: Measure interference patterns in carry field
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# PART A: CARRY AMPLITUDE FIELD
# ============================================================

def carry_amplitude_vector(a, b, n=32):
    """
    Carry amplitude at each bit position.
    α[i] = P(carry_i = 1 | a, b) - 0.5
    For KNOWN a,b this is deterministic (0.5 or -0.5).
    For RANDOM a,b with known GKP: G→+0.5, K→-0.5, P→depends on prev.
    """
    alphas = np.zeros(n)
    c = 0
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        s = ai + bi + c
        c = 1 if s >= 2 else 0
        alphas[i] = c - 0.5  # +0.5 if carry, -0.5 if no carry
    return alphas

def carry_amplitude_field(W16, num_rounds=64):
    """
    Compute full carry amplitude field: 32 positions × 64 rounds × 7 additions.
    Returns condensed field: 32 × num_rounds (main e-branch addition d+T1).
    """
    states = sha256_rounds(W16, num_rounds)
    W = schedule(W16)

    field = np.zeros((num_rounds, 32))

    for r in range(num_rounds):
        state = states[r]
        a, b, c, d, e, f, g, h = state

        # Main carry: d + T1 → e_new
        T1 = (h + sigma1(e) + ch(e, f, g) + K[r] + W[r]) & MASK
        alpha = carry_amplitude_vector(d, T1)
        field[r] = alpha

    return field

def print_part_header(name):
    print(f"\n{'='*60}")
    print(f"PART {name}")
    print(f"{'='*60}")


def part_A(N=1000):
    """Construct and analyze carry amplitude fields."""
    print_part_header("A: CARRY AMPLITUDE FIELD STATISTICS")

    fields = []
    for _ in range(N):
        W16 = random_w16()
        field = carry_amplitude_field(W16)
        fields.append(field)

    fields = np.array(fields)  # N × 64 × 32

    # Mean amplitude per round
    mean_by_round = np.mean(fields, axis=(0, 2))  # average over messages and bits
    std_by_round = np.std(np.mean(fields, axis=2), axis=0)  # std over messages

    print(f"{'Round':>5} | {'Mean α':>10} | {'Std α':>10} | {'|Mean|':>10}")
    print("-" * 45)
    for r in [0, 1, 2, 3, 4, 5, 8, 16, 32, 48, 63]:
        print(f"{r:>5} | {mean_by_round[r]:>10.6f} | {std_by_round[r]:>10.6f} | {abs(mean_by_round[r]):>10.6f}")

    # Per-bit amplitude structure
    mean_by_bit = np.mean(fields, axis=(0, 1))  # average over messages and rounds
    print(f"\nPer-bit mean amplitude (averaged over rounds):")
    print(f"  Bits 0-7:  {mean_by_bit[:8]}")
    print(f"  Bits 24-31: {mean_by_bit[24:]}")
    print(f"  Overall mean: {np.mean(mean_by_bit):.6f}")

    return fields


# ============================================================
# PART B: PROPAGATION OPERATOR EIGENVALUES
# ============================================================

def part_B(N=500):
    """Compute eigenvalues of carry amplitude propagation operator."""
    print_part_header("B: PROPAGATION OPERATOR EIGENVALUES")

    # Estimate L: α_{r+1} ≈ L · α_r (linear approximation)
    # Collect (α_r, α_{r+1}) pairs and fit L via least squares

    X_data = []  # α_r vectors
    Y_data = []  # α_{r+1} vectors

    for _ in range(N):
        W16 = random_w16()
        field = carry_amplitude_field(W16)

        for r in range(63):
            X_data.append(field[r])
            Y_data.append(field[r + 1])

    X = np.array(X_data)  # (N*63) × 32
    Y = np.array(Y_data)  # (N*63) × 32

    # Least squares: Y ≈ X · L^T → L^T = (X^T X)^{-1} X^T Y
    # L is 32×32
    XtX = X.T @ X
    XtY = X.T @ Y

    try:
        L = np.linalg.solve(XtX, XtY).T  # 32×32
    except np.linalg.LinAlgError:
        L = np.linalg.lstsq(X, Y, rcond=None)[0].T

    # Eigenvalues of L
    eigvals = np.linalg.eigvals(L)
    eigvals_sorted = np.sort(np.abs(eigvals))[::-1]

    print(f"Propagation operator L (32×32):")
    print(f"  Rank: {np.linalg.matrix_rank(L)}")
    print(f"  Frobenius norm: {np.linalg.norm(L, 'fro'):.4f}")
    print(f"\nEigenvalues (sorted by |λ|):")
    print(f"  Top 10: {eigvals_sorted[:10]}")
    print(f"  Bottom 5: {eigvals_sorted[-5:]}")

    # CRITICAL: Is max |λ| close to 1?
    max_eigval = eigvals_sorted[0]
    print(f"\n  MAX |λ| = {max_eigval:.6f}")

    if max_eigval > 0.95:
        print(f"  *** SIGNAL: |λ_max| = {max_eigval:.4f} ≈ 1! Non-decaying mode exists! ***")
        # Find the eigenvector
        idx = np.argmax(np.abs(eigvals))
        eigvec = np.real(np.linalg.eig(L)[1][:, idx])
        print(f"  Resonant eigenvector (top bits): {np.argsort(np.abs(eigvec))[::-1][:10]}")
    elif max_eigval > 0.7:
        print(f"  PARTIAL: |λ_max| = {max_eigval:.4f} — slow decay (τ = {-1/np.log(max_eigval):.1f} rounds)")
    else:
        print(f"  NO SIGNAL: |λ_max| = {max_eigval:.4f} — fast decay")

    # Spectral gap
    if len(eigvals_sorted) > 1:
        gap = eigvals_sorted[0] - eigvals_sorted[1]
        print(f"  Spectral gap: {gap:.6f}")

    # Residual: how well does L predict?
    Y_pred = X @ L.T
    residual = np.mean((Y - Y_pred)**2)
    total_var = np.var(Y)
    r_squared = 1 - residual / total_var if total_var > 0 else 0

    print(f"\n  Linear model R²: {r_squared:.6f}")
    print(f"  (R²=1 means perfectly linear, R²=0 means random)")

    return L, eigvals


# ============================================================
# PART C: AMPLITUDE-GUIDED DIFFERENTIAL
# ============================================================

def part_C(L, eigvals, N=3000):
    """Test if amplitude-guided differential beats random."""
    print_part_header("C: AMPLITUDE-GUIDED DIFFERENTIAL SEARCH")

    # Strategy: find messages where carry amplitudes align
    # to create destructive interference at output

    # Compute dominant eigenvector
    idx = np.argmax(np.abs(eigvals))
    eigvec = np.real(np.linalg.eig(L)[1][:, idx])
    eigvec = eigvec / np.linalg.norm(eigvec)

    # Score each Wang pair by alignment with eigenvector
    aligned_hw = []
    antialigned_hw = []
    random_hw = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # Carry amplitude at barrier (round 17)
        field_n = carry_amplitude_field(Wn, 18)
        alpha_17 = field_n[16]  # Round 16 (0-indexed before round 17)

        # Alignment score
        score = np.dot(alpha_17, eigvec)

        # Hash difference
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        hw_delta = sum(hw(d) for d in delta_H)

        if score > 0.5:
            aligned_hw.append(hw_delta)
        elif score < -0.5:
            antialigned_hw.append(hw_delta)
        else:
            random_hw.append(hw_delta)

    print(f"Aligned (score>0.5):      N={len(aligned_hw)}, E[HW(δH)]={np.mean(aligned_hw):.2f}" if aligned_hw else "Aligned: N=0")
    print(f"Anti-aligned (score<-0.5): N={len(antialigned_hw)}, E[HW(δH)]={np.mean(antialigned_hw):.2f}" if antialigned_hw else "Anti-aligned: N=0")
    print(f"Neutral:                   N={len(random_hw)}, E[HW(δH)]={np.mean(random_hw):.2f}" if random_hw else "Neutral: N=0")

    if aligned_hw and random_hw:
        diff = np.mean(aligned_hw) - np.mean(random_hw)
        print(f"\nDifference (aligned - neutral): {diff:+.4f}")
        if abs(diff) > 1.0:
            print("*** SIGNAL: Amplitude alignment affects collision distance! ***")


# ============================================================
# PART D: INTERFERENCE PATTERNS
# ============================================================

def part_D(N=2000):
    """Measure interference patterns in carry amplitude field."""
    print_part_header("D: INTERFERENCE PATTERNS")

    # For Wang pairs, compute carry amplitude DIFFERENCE field
    # δα_r = α_r(faulty) - α_r(normal)
    # If interference exists: δα should have structure (not random)

    diff_fields = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        field_n = carry_amplitude_field(Wn)
        field_f = carry_amplitude_field(Wf)

        diff_field = field_f - field_n  # 64 × 32
        diff_fields.append(diff_field)

    diff_fields = np.array(diff_fields)  # N × 64 × 32

    # Autocorrelation of δα across rounds
    print("Autocorrelation of δα (carry amplitude difference):")
    print(f"{'Lag':>4} | {'Autocorr':>10} | {'Signal'}")
    print("-" * 35)

    for lag in range(1, 20):
        corrs = []
        for trial in range(min(N, 500)):
            df = diff_fields[trial]
            for r in range(64 - lag):
                c = np.corrcoef(df[r], df[r + lag])[0, 1]
                if not np.isnan(c):
                    corrs.append(c)

        avg_corr = np.mean(corrs) if corrs else 0
        marker = " ***" if abs(avg_corr) > 0.05 else ""
        print(f"{lag:>4} | {avg_corr:>10.6f} | {marker}")

    # Fourier analysis of δα field
    print("\nFourier analysis of δα (frequency domain):")

    # Average power spectrum across rounds
    power_spectra = []
    for trial in range(min(N, 500)):
        df = diff_fields[trial]
        # FFT along round axis for each bit
        fft_field = np.fft.fft(df, axis=0)
        power = np.abs(fft_field)**2
        power_spectra.append(np.mean(power, axis=1))  # avg over bits

    avg_power = np.mean(power_spectra, axis=0)

    # Normalize
    avg_power = avg_power / np.sum(avg_power)

    # Check for peaks (deviation from flat spectrum)
    flat = 1.0 / 64
    peak_ratio = np.max(avg_power) / flat
    peak_freq = np.argmax(avg_power)

    print(f"  Peak frequency: {peak_freq} (period={64/peak_freq if peak_freq>0 else 'inf'})")
    print(f"  Peak/flat ratio: {peak_ratio:.4f}")
    print(f"  Top 5 frequencies: {np.argsort(avg_power)[::-1][:5]}")
    print(f"  Top 5 powers: {avg_power[np.argsort(avg_power)[::-1][:5]]}")

    if peak_ratio > 2.0:
        print(f"  *** SIGNAL: Spectral peak at freq={peak_freq}! Resonance! ***")

    # Per-round variance of δα (does it grow, shrink, or oscillate?)
    print("\nδα variance by round:")
    print(f"{'Round':>5} | {'Var(δα)':>10} | {'Mean|δα|':>10}")
    print("-" * 35)

    var_by_round = np.var(diff_fields, axis=(0, 2))  # var over messages and bits per round
    mean_abs_by_round = np.mean(np.abs(diff_fields), axis=(0, 2))

    for r in [0, 1, 2, 3, 4, 5, 8, 16, 17, 18, 20, 32, 48, 63]:
        print(f"{r:>5} | {var_by_round[r]:>10.6f} | {mean_abs_by_round[r]:>10.6f}")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 10: CARRY AMPLITUDE THEORY (CAT)")
    print("New method: continuous carry amplitudes + interference")
    print("=" * 60)

    # Part A
    fields = part_A(500)

    # Part B — the key test
    L, eigvals = part_B(500)

    # Part C
    part_C(L, eigvals, 2000)

    # Part D
    part_D(1000)

    print("\n" + "=" * 60)
    print("FINAL VERDICT")
    print("=" * 60)
    max_ev = np.max(np.abs(eigvals))
    print(f"Max eigenvalue |λ| of carry propagation operator: {max_ev:.6f}")
    if max_ev > 0.95:
        print("τ_amplitude = ∞ (or very large) — NON-DECAYING MODE EXISTS")
        print("This is a genuinely new result: carry amplitudes survive longer than binary carry!")
    elif max_ev > 0.7:
        tau = -1 / np.log(max_ev)
        print(f"τ_amplitude = {tau:.1f} rounds (vs τ_binary = 1.80)")
        if tau > 3.0:
            print("PARTIAL SIGNAL: amplitude decay slower than binary!")
    else:
        print(f"τ_amplitude ≈ τ_binary — no advantage from continuous amplitudes")

if __name__ == "__main__":
    main()
