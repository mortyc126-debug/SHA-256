#!/usr/bin/env python3
"""
EXP 189: REMAINING NOISE — What's in the last 68%?

exp188: 32% of noise = f(δa, δe, δa×δe). R²=0.320.
Remaining 68% — is it truly random or further decomposable?

Key clue: noise autocorrelation = -0.43 at lag 1.
After removing δa×δe, does autocorrelation remain?

DECOMPOSE LAYER 2:
1. Remove δa×δe component → residual_2
2. Check residual_2 autocorrelation
3. Test HISTORY terms: δa[r-1], δe[r-1], δa[r-2]
4. Test K[r%64] modulation
5. Test HIGHER-ORDER: δa³, δa²δe, etc.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def collect_full_data(N=200):
    """Collect ALL variables for noise decomposition."""
    data = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        W1 = schedule(M1); W2 = schedule(M2)
        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        for r in range(30, 63):
            da_r = hw(s1_all[r][0] ^ s2_all[r][0])
            de_r = hw(s1_all[r][4] ^ s2_all[r][4])
            dae_r = da_r + de_r

            da_r1 = hw(s1_all[r+1][0] ^ s2_all[r+1][0])
            de_r1 = hw(s1_all[r+1][4] ^ s2_all[r+1][4])
            dae_r1 = da_r1 + de_r1

            # History
            da_prev = hw(s1_all[r-1][0] ^ s2_all[r-1][0]) if r > 0 else 16
            de_prev = hw(s1_all[r-1][4] ^ s2_all[r-1][4]) if r > 0 else 16
            da_prev2 = hw(s1_all[r-2][0] ^ s2_all[r-2][0]) if r > 1 else 16
            de_prev2 = hw(s1_all[r-2][4] ^ s2_all[r-2][4]) if r > 1 else 16

            dW = hw(W1[r] ^ W2[r])
            k_idx = r % 64

            # Level 1 residual (after linear thermostat)
            pred_1 = 0.69 * dae_r + 9.92
            noise_1 = dae_r1 - pred_1

            data.append({
                'da': da_r, 'de': de_r, 'dae': dae_r,
                'da_next': da_r1, 'de_next': de_r1, 'dae_next': dae_r1,
                'da_prev': da_prev, 'de_prev': de_prev,
                'da_prev2': da_prev2, 'de_prev2': de_prev2,
                'dW': dW, 'k_idx': k_idx,
                'noise_1': noise_1, 'r': r,
            })

    return data

def decompose_layer2(data):
    """Remove δa×δe and check what remains."""
    print(f"\n{'='*60}")
    print(f"LAYER 2: After removing δa×δe")
    print(f"{'='*60}")

    n = len(data)
    noise_1 = np.array([d['noise_1'] for d in data])
    da = np.array([d['da'] for d in data])
    de = np.array([d['de'] for d in data])
    cross = da * de

    # Remove layer 1 (δa, δe, δa×δe)
    X1 = np.column_stack([da, de, cross])
    coeffs1 = np.linalg.lstsq(X1, noise_1, rcond=None)[0]
    pred_layer1 = X1 @ coeffs1
    residual_2 = noise_1 - pred_layer1

    r2_layer1 = 1 - np.var(residual_2) / np.var(noise_1)
    print(f"\n  Layer 1 (δa, δe, δa×δe): R² = {r2_layer1:.4f}")
    print(f"  Residual_2 std: {residual_2.std():.3f} (original: {noise_1.std():.3f})")

    # Check: autocorrelation of residual_2
    # Group by message pair for proper autocorrelation
    print(f"\n  Residual_2 autocorrelation:")
    for lag in [1, 2, 3, 4]:
        c = np.corrcoef(residual_2[:-lag], residual_2[lag:])[0, 1]
        sig = " ★★★" if abs(c) > 0.1 else ""
        print(f"    Lag {lag}: {c:+.4f}{sig}")

    return residual_2

def test_history_terms(data, residual_2):
    """Does HISTORY predict remaining noise?"""
    print(f"\n{'='*60}")
    print(f"HISTORY TERMS (δa[r-1], δe[r-1], δa[r-2], δe[r-2])")
    print(f"{'='*60}")

    n = len(data)
    da_prev = np.array([d['da_prev'] for d in data])
    de_prev = np.array([d['de_prev'] for d in data])
    da_prev2 = np.array([d['da_prev2'] for d in data])
    de_prev2 = np.array([d['de_prev2'] for d in data])
    da = np.array([d['da'] for d in data])
    de = np.array([d['de'] for d in data])

    print(f"\n  Individual correlations with residual_2:")
    for name, arr in [("δa[r-1]", da_prev), ("δe[r-1]", de_prev),
                       ("δa[r-2]", da_prev2), ("δe[r-2]", de_prev2),
                       ("δa[r-1]×δe[r-1]", da_prev*de_prev),
                       ("δa×δa[r-1]", da*da_prev),
                       ("δe×δe[r-1]", de*de_prev)]:
        c = np.corrcoef(residual_2, arr)[0, 1]
        sig = " ★★★" if abs(c) > 0.05 else ""
        print(f"    corr(res2, {name:>16}): {c:+.4f}{sig}")

    # Combined history model
    X2 = np.column_stack([da_prev, de_prev, da_prev*de_prev,
                          da_prev2, de_prev2,
                          da*da_prev, de*de_prev])
    coeffs2 = np.linalg.lstsq(X2, residual_2, rcond=None)[0]
    pred2 = X2 @ coeffs2
    residual_3 = residual_2 - pred2
    r2_history = 1 - np.var(residual_3) / np.var(residual_2)

    print(f"\n  History model R² (on residual_2): {r2_history:.4f}")
    print(f"  Residual_3 std: {residual_3.std():.3f}")

    return residual_3, r2_history

def test_k_modulation(data, residual_2):
    """Does K[r%64] modulate the noise?"""
    print(f"\n{'='*60}")
    print(f"K-CONSTANT MODULATION")
    print(f"{'='*60}")

    k_idx = np.array([d['k_idx'] for d in data])

    # Average residual per K-index
    k_means = {}
    for i in range(len(data)):
        k = k_idx[i]
        k_means.setdefault(k, []).append(residual_2[i])

    k_avgs = {k: np.mean(v) for k, v in k_means.items()}
    k_arr = np.array([k_avgs.get(k, 0) for k in range(64)])

    between_var = np.var(k_arr)
    within_var = np.mean([np.var(v) for v in k_means.values()])
    f_ratio = between_var / (within_var / len(data) * 64) if within_var > 0 else 0

    print(f"\n  K-modulation:")
    print(f"    Between-K variance: {between_var:.4f}")
    print(f"    Within-K variance: {within_var:.4f}")
    print(f"    F-ratio: {f_ratio:.2f} (>2 = significant)")

    if f_ratio > 2:
        print(f"    ★★★ K-constants MODULATE the noise!")
        sorted_k = sorted(k_avgs.items(), key=lambda x: x[1])
        print(f"    Lowest noise K: K[{sorted_k[0][0]}] = {sorted_k[0][1]:+.3f}")
        print(f"    Highest noise K: K[{sorted_k[-1][0]}] = {sorted_k[-1][1]:+.3f}")

def total_predictability(data):
    """Combine ALL layers: what's the total R²?"""
    print(f"\n{'='*60}")
    print(f"TOTAL PREDICTABILITY STACK")
    print(f"{'='*60}")

    n = len(data)
    y = np.array([d['dae_next'] for d in data])

    # Layer 0: baseline (predict mean)
    r2_0 = 0
    print(f"  Layer 0 (predict mean 32):    R² = {r2_0:.4f}")

    # Layer 1: linear thermostat
    dae = np.array([d['dae'] for d in data])
    pred_1 = 0.69 * dae + 9.92
    r2_1 = 1 - np.var(y - pred_1) / np.var(y)
    print(f"  Layer 1 (linear thermostat):  R² = {r2_1:.4f}")

    # Layer 2: + δa, δe, δa×δe
    da = np.array([d['da'] for d in data])
    de = np.array([d['de'] for d in data])
    X2 = np.column_stack([dae, da, de, da*de, da**2, de**2])
    c2 = np.linalg.lstsq(X2, y, rcond=None)[0]
    pred_2 = X2 @ c2
    r2_2 = 1 - np.var(y - pred_2) / np.var(y)
    print(f"  Layer 2 (+ δa×δe nonlinear): R² = {r2_2:.4f}")

    # Layer 3: + history
    da_prev = np.array([d['da_prev'] for d in data])
    de_prev = np.array([d['de_prev'] for d in data])
    da_prev2 = np.array([d['da_prev2'] for d in data])
    de_prev2 = np.array([d['de_prev2'] for d in data])
    X3 = np.column_stack([dae, da, de, da*de, da**2, de**2,
                          da_prev, de_prev, da_prev*de_prev,
                          da_prev2, de_prev2])
    c3 = np.linalg.lstsq(X3, y, rcond=None)[0]
    pred_3 = X3 @ c3
    r2_3 = 1 - np.var(y - pred_3) / np.var(y)
    print(f"  Layer 3 (+ history):          R² = {r2_3:.4f}")

    # Layer 4: + δW + K-index
    dW = np.array([d['dW'] for d in data])
    k_idx = np.array([d['k_idx'] for d in data])
    # One-hot K (sparse)
    k_sin = np.sin(2 * np.pi * k_idx / 64)
    k_cos = np.cos(2 * np.pi * k_idx / 64)
    X4 = np.column_stack([dae, da, de, da*de, da**2, de**2,
                          da_prev, de_prev, da_prev*de_prev,
                          da_prev2, de_prev2,
                          dW, k_sin, k_cos])
    c4 = np.linalg.lstsq(X4, y, rcond=None)[0]
    pred_4 = X4 @ c4
    r2_4 = 1 - np.var(y - pred_4) / np.var(y)
    print(f"  Layer 4 (+ schedule, K):      R² = {r2_4:.4f}")

    # Summary
    unexplained = 1 - r2_4
    print(f"\n  TOTAL EXPLAINED: {r2_4*100:.1f}%")
    print(f"  UNEXPLAINED:     {unexplained*100:.1f}%")
    print(f"\n  Remaining noise std: {np.std(y - pred_4):.3f}")
    print(f"  Original std: {np.std(y):.3f}")
    print(f"  Reduction: {(1-np.std(y-pred_4)/np.std(y))*100:.1f}%")

    print(f"\n  LAYER CONTRIBUTION:")
    layers = [("Thermostat", r2_1), ("δa×δe", r2_2-r2_1),
              ("History", r2_3-r2_2), ("Schedule+K", r2_4-r2_3)]
    for name, contrib in layers:
        bar = "█" * int(contrib * 100)
        print(f"    {name:>15}: {contrib*100:>5.1f}% {bar}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 189: REMAINING NOISE DECOMPOSITION")
    print("=" * 60)

    print(f"  Collecting data...")
    data = collect_full_data(N=200)
    print(f"  {len(data)} data points collected")

    residual_2 = decompose_layer2(data)
    residual_3, r2_hist = test_history_terms(data, residual_2)
    test_k_modulation(data, residual_2)
    total_predictability(data)

    print(f"\n{'='*60}")
    print(f"VERDICT: How deep does predictability go?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
