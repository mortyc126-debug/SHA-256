#!/usr/bin/env python3
"""
EXP 188: THERMOSTAT NOISE DECOMPOSITION

δ[r+1] = 0.69·δ[r] + 9.92 + noise(σ=5.4)

The noise is NOT random — SHA-256 is deterministic.
The noise = everything our linear model DOESN'T capture.

DECOMPOSE: What IS the noise made of?
1. δa vs δe SEPARATELY (do they have different noise?)
2. Is noise correlated with δW (schedule)?
3. Is noise AUTOCORRELATED (noise[r] → noise[r+1])?
4. Does noise depend on FULL state (not just δ)?
5. The (a→e) 3-round delay feedback — does it explain noise?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_residuals(M1, M2, max_r=64):
    """Compute thermostat residuals (noise) for a message pair."""
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)

    da_trace = []; de_trace = []; dae_trace = []
    for r in range(max_r + 1):
        da = hw(s1[r][0] ^ s2[r][0])
        de = hw(s1[r][4] ^ s2[r][4])
        da_trace.append(da); de_trace.append(de); dae_trace.append(da + de)

    # Residuals: noise[r] = δ[r+1] - (0.69·δ[r] + 9.92)
    residuals_ae = []
    residuals_a = []
    residuals_e = []
    for r in range(30, max_r):
        pred_ae = 0.69 * dae_trace[r] + 9.92
        residuals_ae.append(dae_trace[r+1] - pred_ae)

        pred_a = 0.69 * da_trace[r] + 0.31 * 16
        residuals_a.append(da_trace[r+1] - pred_a)

        pred_e = 0.69 * de_trace[r] + 0.31 * 16
        residuals_e.append(de_trace[r+1] - pred_e)

    return (np.array(residuals_ae), np.array(residuals_a), np.array(residuals_e),
            np.array(da_trace), np.array(de_trace), np.array(dae_trace))

def noise_basic_stats(N=200):
    """Basic noise statistics."""
    print(f"\n{'='*60}")
    print(f"NOISE BASIC STATISTICS (N={N})")
    print(f"{'='*60}")

    all_res_ae = []; all_res_a = []; all_res_e = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        res_ae, res_a, res_e, _, _, _ = compute_residuals(M1, M2)
        all_res_ae.extend(res_ae)
        all_res_a.extend(res_a)
        all_res_e.extend(res_e)

    ae = np.array(all_res_ae); a = np.array(all_res_a); e = np.array(all_res_e)

    print(f"\n  Combined δ(a,e) noise:")
    print(f"    Mean: {ae.mean():+.3f} (expect 0)")
    print(f"    Std:  {ae.std():.3f}")
    print(f"    Skew: {np.mean(((ae-ae.mean())/ae.std())**3):.3f} (expect 0)")
    print(f"    Kurt: {np.mean(((ae-ae.mean())/ae.std())**4):.3f} (expect 3)")

    print(f"\n  SEPARATE a and e noise:")
    print(f"    δa noise: mean={a.mean():+.3f}, std={a.std():.3f}")
    print(f"    δe noise: mean={e.mean():+.3f}, std={e.std():.3f}")
    print(f"    corr(noise_a, noise_e): {np.corrcoef(a[:len(e)], e[:len(a)])[0,1]:+.4f}")

    return ae, a, e

def noise_autocorrelation(N=200):
    """Is noise[r] correlated with noise[r+k]?"""
    print(f"\n{'='*60}")
    print(f"NOISE AUTOCORRELATION")
    print(f"{'='*60}")

    all_res = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        res_ae, _, _, _, _, _ = compute_residuals(M1, M2)
        all_res.append(res_ae)

    # Average autocorrelation
    min_len = min(len(r) for r in all_res)
    combined = np.array([r[:min_len] for r in all_res])

    print(f"\n  Noise autocorrelation:")
    for lag in [1, 2, 3, 4, 5, 8, 16]:
        corrs = []
        for trace in combined:
            if len(trace) > lag:
                c = np.corrcoef(trace[:-lag], trace[lag:])[0, 1]
                if not np.isnan(c):
                    corrs.append(c)
        avg = np.mean(corrs) if corrs else 0
        sig = " ★★★" if abs(avg) > 0.1 else (" ★" if abs(avg) > 0.05 else "")
        print(f"    Lag {lag:>2}: {avg:+.4f}{sig}")

def noise_vs_schedule(N=200):
    """Does δW predict noise?"""
    print(f"\n{'='*60}")
    print(f"NOISE vs SCHEDULE")
    print(f"{'='*60}")

    noise_vals = []; dW_vals = []; dW_cumulative = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        W1 = schedule(M1); W2 = schedule(M2)
        res_ae, _, _, _, _, _ = compute_residuals(M1, M2)

        for r_off in range(len(res_ae)):
            r = r_off + 30
            if r < 64:
                noise_vals.append(res_ae[r_off])
                dW_vals.append(hw(W1[r] ^ W2[r]))
                dW_cumulative.append(sum(hw(W1[t] ^ W2[t]) for t in range(15, r+1)))

    nv = np.array(noise_vals); dw = np.array(dW_vals); dwc = np.array(dW_cumulative)

    corr_dw = np.corrcoef(nv, dw)[0, 1]
    corr_dwc = np.corrcoef(nv, dwc)[0, 1]

    print(f"\n  corr(noise, δW[r]):       {corr_dw:+.4f}")
    print(f"  corr(noise, Σ δW[15..r]): {corr_dwc:+.4f}")

    if abs(corr_dw) > 0.05:
        print(f"  ★★★ Schedule EXPLAINS part of noise!")

def noise_vs_cross_terms(N=200):
    """Does noise depend on δa×δe interaction?"""
    print(f"\n{'='*60}")
    print(f"NOISE vs CROSS-TERMS (δa, δe, δa×δe)")
    print(f"{'='*60}")

    noise_vals = []; da_vals = []; de_vals = []; cross_vals = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        res_ae, _, _, da_trace, de_trace, _ = compute_residuals(M1, M2)

        for r_off in range(len(res_ae)):
            r = r_off + 30
            noise_vals.append(res_ae[r_off])
            da_vals.append(da_trace[r])
            de_vals.append(de_trace[r])
            cross_vals.append(da_trace[r] * de_trace[r])

    nv = np.array(noise_vals)
    da = np.array(da_vals); de = np.array(de_vals)
    cross = np.array(cross_vals)

    print(f"  corr(noise, δa):      {np.corrcoef(nv, da)[0,1]:+.4f}")
    print(f"  corr(noise, δe):      {np.corrcoef(nv, de)[0,1]:+.4f}")
    print(f"  corr(noise, δa×δe):   {np.corrcoef(nv, cross)[0,1]:+.4f}")
    print(f"  corr(noise, δa²):     {np.corrcoef(nv, da**2)[0,1]:+.4f}")
    print(f"  corr(noise, δe²):     {np.corrcoef(nv, de**2)[0,1]:+.4f}")

    # Multivariate regression: noise = α·δa + β·δe + γ·δa·δe + ...
    X = np.column_stack([da, de, cross, da**2, de**2])
    try:
        coeffs = np.linalg.lstsq(X, nv, rcond=None)[0]
        pred = X @ coeffs
        r2 = 1 - np.var(nv - pred) / np.var(nv)
        print(f"\n  Multivariate R²: {r2:.4f}")
        print(f"  Coefficients: δa={coeffs[0]:.3f}, δe={coeffs[1]:.3f}, "
              f"δa×δe={coeffs[2]:.4f}, δa²={coeffs[3]:.4f}, δe²={coeffs[4]:.4f}")

        if r2 > 0.01:
            print(f"  ★★★ NOISE IS PARTIALLY PREDICTABLE! R²={r2:.3f}")
            print(f"  → {r2*100:.1f}% of noise explained by (δa, δe, δa×δe)")
            print(f"  → Per round: {r2 * 5.4:.2f} bits predictable from noise")
    except:
        print(f"  Regression failed")

def feedback_delay_analysis(N=200):
    """The a→e 3-round delay: does it create structured noise?"""
    print(f"\n{'='*60}")
    print(f"FEEDBACK DELAY: a[r-3] → e[r] coupling")
    print(f"{'='*60}")

    # Noise in δe should correlate with δa at lag 3 (feedback delay)
    corrs_by_lag = {}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        _, _, res_e, da_trace, de_trace, _ = compute_residuals(M1, M2)

        for lag in range(1, 8):
            if lag >= len(res_e):
                continue
            # Does δa[r-lag] predict noise_e[r]?
            da_lagged = da_trace[30-lag:30-lag+len(res_e)]
            if len(da_lagged) == len(res_e):
                c = np.corrcoef(da_lagged, res_e)[0, 1]
                if not np.isnan(c):
                    corrs_by_lag.setdefault(lag, []).append(c)

    print(f"\n  corr(δa[r-k], noise_e[r]):")
    for lag in range(1, 8):
        if lag in corrs_by_lag:
            avg = np.mean(corrs_by_lag[lag])
            sig = " ★★★" if abs(avg) > 0.1 else (" ★★" if abs(avg) > 0.05 else "")
            print(f"    k={lag}: {avg:+.4f}{sig}")
            if lag == 3:
                print(f"         (k=3 = feedback delay a→d→e)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 188: THERMOSTAT NOISE DECOMPOSITION")
    print("=" * 60)

    ae_noise, a_noise, e_noise = noise_basic_stats(N=150)
    noise_autocorrelation(N=150)
    noise_vs_schedule(N=150)
    noise_vs_cross_terms(N=150)
    feedback_delay_analysis(N=150)

    print(f"\n{'='*60}")
    print(f"VERDICT: What IS the noise?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
