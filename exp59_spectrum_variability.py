#!/usr/bin/env python3
"""
EXP 59: Spectrum Variability — Angle Between Bijection Sheets

D_KY = 256 for ONE message. But collision = intersection of TWO sheets.
If spectrum VARIES with message → sheets at different angles → intersections.
If STABLE → parallel sheets → no intersection structure.

Also: does spectrum correlate with collision properties (δH)?
A message whose spectrum has WEAKER expansion might be easier to collide.

Measure: first 8 Lyapunov exponents for 50+ messages.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_top_spectrum(W16, n_exp=8, n_rounds=64):
    """Compute first n_exp Lyapunov exponents (fast version)."""
    W = schedule(W16)
    states = sha256_rounds(W16, n_rounds)
    M = np.eye(256, n_exp, dtype=np.float64)
    lyap_sum = np.zeros(n_exp)

    for r in range(n_rounds):
        state = states[r]
        new_state = sha256_round(state, W[r], K[r])

        J = np.zeros((256, 256), dtype=np.float64)
        for j in range(256):
            w=j//32; b=j%32
            s_p=list(state); s_p[w]^=(1<<b)
            ns_p=sha256_round(s_p, W[r], K[r])
            for i in range(256):
                wi=i//32; bi=i%32
                J[i][j]=float(((new_state[wi]>>bi)&1)^((ns_p[wi]>>bi)&1))

        evolved = J @ M
        Q, R_mat = np.linalg.qr(evolved)
        M = Q[:, :n_exp]
        for i in range(n_exp):
            lyap_sum[i] += np.log2(max(abs(R_mat[i,i]), 1e-30))

    return np.sort(lyap_sum / n_rounds)[::-1]

def test_spectrum_variability(N=30):
    """Measure spectrum variability across messages."""
    print(f"\n--- SPECTRUM VARIABILITY (N={N}) ---")

    all_spectra = []
    for trial in range(N):
        W16 = random_w16()
        spec = compute_top_spectrum(W16, n_exp=8)
        all_spectra.append(spec)

    S = np.array(all_spectra)

    print(f"\nPer-exponent statistics:")
    print(f"{'Exponent':>8} | {'Mean':>8} | {'Std':>8} | {'Min':>8} | {'Max':>8} | {'CV%':>6}")
    print("-"*55)
    for i in range(8):
        col = S[:, i]
        cv = col.std() / abs(col.mean()) * 100 if col.mean() != 0 else 0
        print(f"    λ_{i+1:>2} | {col.mean():>+8.4f} | {col.std():>8.4f} | "
              f"{col.min():>+8.4f} | {col.max():>+8.4f} | {cv:>5.1f}%")

    # Is variability REAL or just finite-sample noise?
    # For finite-sample: std should decrease as √(1/n_rounds)
    # Theoretical noise for 64 rounds: std ≈ mean × √(2/64) ≈ mean × 0.177
    print(f"\nExpected noise std (finite rounds): ≈ mean × 0.177")
    for i in range(4):
        expected_noise = abs(S[:, i].mean()) * 0.177
        actual_std = S[:, i].std()
        ratio = actual_std / expected_noise if expected_noise > 0 else 0
        signal = "REAL VARIABILITY" if ratio > 2 else "noise"
        print(f"  λ_{i+1}: actual_std={actual_std:.4f}, expected_noise={expected_noise:.4f}, "
              f"ratio={ratio:.2f} → {signal}")

    # Correlation between exponents across messages
    print(f"\nCross-exponent correlations:")
    for i in range(4):
        for j in range(i+1, 4):
            c = np.corrcoef(S[:,i], S[:,j])[0,1]
            print(f"  corr(λ_{i+1}, λ_{j+1}) = {c:+.4f}")

    return S

def test_spectrum_vs_collision(N=30):
    """Does spectrum predict collision properties?"""
    print(f"\n--- SPECTRUM → COLLISION? ---")

    spectra = []; dHs = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)

        # Spectrum of normal message
        Wn = [W0, W1] + [0]*14
        spec = compute_top_spectrum(Wn, n_exp=8)
        spectra.append(spec)

        # Wang cascade δH
        Wn_w, Wf, _, _, _ = wang_cascade(W0, W1)
        Hn = sha256_compress(Wn_w); Hf = sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        dHs.append(dH)

    S = np.array(spectra); dH_arr = np.array(dHs)

    threshold = 3/np.sqrt(N)
    print(f"Threshold: {threshold:.4f}")
    for i in range(8):
        c = np.corrcoef(S[:,i], dH_arr)[0,1]
        sig = "***" if abs(c) > threshold else ""
        print(f"  corr(λ_{i+1}, δH) = {c:+.6f} {sig}")

    # Sum of positive exponents → total expansion rate
    total_expansion = S.sum(axis=1)
    c = np.corrcoef(total_expansion, dH_arr)[0,1]
    print(f"  corr(Σλ, δH) = {c:+.6f}")

    # Maximum exponent → strongest expansion
    max_exp = S[:, 0]
    c = np.corrcoef(max_exp, dH_arr)[0,1]
    print(f"  corr(λ_max, δH) = {c:+.6f}")

def test_wang_pair_spectrum(N=15):
    """
    Compute spectrum for WANG PAIR messages (Wn and Wf separately).
    If spectra of Wn and Wf are DIFFERENT → sheets diverge.
    If similar → sheets parallel.
    """
    print(f"\n--- WANG PAIR: SPECTRUM DIVERGENCE ---")

    divergences = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn, Wf, _, _, _ = wang_cascade(W0, W1)

        spec_n = compute_top_spectrum(Wn, n_exp=8)
        spec_f = compute_top_spectrum(Wf, n_exp=8)

        # Spectral divergence
        div = np.linalg.norm(spec_n - spec_f)
        divergences.append(div)

        if _ < 3:
            print(f"  Pair {_}: spec_n={[f'{s:+.3f}' for s in spec_n[:4]]}")
            print(f"         spec_f={[f'{s:+.3f}' for s in spec_f[:4]]}")
            print(f"         divergence={div:.4f}")

    da = np.array(divergences)
    print(f"\nSpectral divergence between Wang pairs:")
    print(f"  mean={da.mean():.4f}, std={da.std():.4f}")

    # Compare with divergence between UNRELATED messages
    unrelated_div = []
    for _ in range(N):
        W1r = random_w16(); W2r = random_w16()
        s1 = compute_top_spectrum(W1r, n_exp=8)
        s2 = compute_top_spectrum(W2r, n_exp=8)
        unrelated_div.append(np.linalg.norm(s1 - s2))

    ua = np.array(unrelated_div)
    print(f"  Unrelated messages: mean={ua.mean():.4f}, std={ua.std():.4f}")
    print(f"  Ratio Wang/Unrelated: {da.mean()/ua.mean():.4f}")

    if da.mean() < ua.mean() * 0.8:
        print(f"  *** Wang pairs have MORE SIMILAR spectra! ***")
        print(f"  Sheets are MORE PARALLEL → collision harder")
    elif da.mean() > ua.mean() * 1.2:
        print(f"  *** Wang pairs have MORE DIFFERENT spectra! ***")
        print(f"  Sheets at larger angle → more intersections")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 59: SPECTRUM VARIABILITY")
    print("Angle between bijection sheets")
    print("="*60)

    S = test_spectrum_variability(25)
    test_spectrum_vs_collision(20)
    test_wang_pair_spectrum(12)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
