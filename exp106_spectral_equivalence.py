#!/usr/bin/env python3
"""
EXP 106: Spectral Equivalence — ≡ in Fourier Space

From exp105: carry power spectrum is 0.992 ROTR-invariant.
This is the STRONGEST ROTR-invariant signal found.

KEY INSIGHT: carry(ROTR_k(a), ROTR_k(b)) ≠ ROTR_k(carry(a,b))
BUT: |FFT(carry(ROTR_k(a), ROTR_k(b)))|² ≈ |FFT(carry(a,b))|²

WHY? Hypothesis: GKP bit pattern just rotates (trivially), so the
carry chain STRUCTURE rotates with it. Carry VALUES change at
chain BOUNDARIES (where G or K meets rotated context), but the
SPECTRAL envelope of the chain is preserved.

PLAN:
1. Define spectral equivalence: α ≡_S β iff |FFT(carry(α))|² = |FFT(carry(β))|²
2. Measure: how many spectral equivalence classes exist?
3. Test: does spectral equivalence IMPLY anything about hash collision?
4. Test: can we do birthday search in spectral space?

If spectral space has dimension D_S < 256 → birthday on D_S bits.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_bits(a, b):
    """Return all 32 carry bits for a+b."""
    c = 0
    carries = []
    for i in range(32):
        ai = (a >> i) & 1; bi = (b >> i) & 1
        c = (ai & bi) | ((ai ^ bi) & c)
        carries.append(c)
    return carries

def carry_word(a, b):
    """Return carry as 32-bit word."""
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def carry_spectrum(a, b):
    """Power spectrum of carry(a,b)."""
    cb = np.array(carry_bits(a, b), dtype=float)
    return np.abs(np.fft.fft(cb))**2

def hash_spectrum(W16):
    """Compute hash AND carry spectrum for feedforward."""
    H = sha256_compress(W16)
    states = sha256_rounds(W16, 64)
    # Carry spectrum per word of feedforward
    spectra = []
    for w in range(8):
        spec = carry_spectrum(IV[w], states[64][w])
        spectra.append(spec)
    return H, np.concatenate(spectra)  # 8 × 32 = 256-dim spectrum

def spectral_distance(s1, s2):
    """L2 distance between two spectra."""
    return np.sqrt(np.sum((s1 - s2)**2))

def spectral_cosine(s1, s2):
    """Cosine similarity between spectra."""
    n1 = np.linalg.norm(s1); n2 = np.linalg.norm(s2)
    if n1 < 1e-10 or n2 < 1e-10:
        return 0.0
    return np.dot(s1, s2) / (n1 * n2)

def test_spectral_dimension(N=10000):
    """What is the EFFECTIVE dimension of spectral space?"""
    print(f"\n--- SPECTRAL DIMENSION (N={N}) ---")

    spectra = []
    for _ in range(N):
        W16 = random_w16()
        _, spec = hash_spectrum(W16)
        spectra.append(spec)

    S = np.array(spectra)

    # PCA to find effective dimension
    S_centered = S - S.mean(axis=0)
    # Use SVD on a subset for efficiency
    n_sub = min(N, 5000)
    U, sigma, Vt = np.linalg.svd(S_centered[:n_sub], full_matrices=False)

    # Explained variance
    var_explained = sigma**2 / np.sum(sigma**2)
    cumvar = np.cumsum(var_explained)

    # Effective dimension: how many components to explain 95%/99% variance
    dim_95 = np.searchsorted(cumvar, 0.95) + 1
    dim_99 = np.searchsorted(cumvar, 0.99) + 1
    dim_999 = np.searchsorted(cumvar, 0.999) + 1

    print(f"Spectral space: {S.shape[1]} dimensions (8 words × 32 freqs)")
    print(f"Effective dimension (95% var): {dim_95}")
    print(f"Effective dimension (99% var): {dim_99}")
    print(f"Effective dimension (99.9% var): {dim_999}")
    print(f"Top 10 singular values: {sigma[:10].astype(int)}")
    print(f"Variance ratio top/bottom: {sigma[0]/sigma[-1]:.1f}")

    # Birthday implication
    print(f"\nBirthday implications:")
    print(f"  Standard: 2^128 (256 bits / 2)")
    print(f"  Spectral 95%: 2^{dim_95//2} (if search in spectral space)")
    print(f"  Spectral 99%: 2^{dim_99//2}")

    return dim_95, dim_99, sigma

def test_spectral_collision_correlation(N=20000):
    """Does spectral closeness → hash closeness?"""
    print(f"\n--- SPECTRAL → HASH CORRELATION (N={N}) ---")

    hashes = []; spectra = []
    for _ in range(N):
        W16 = random_w16()
        H, spec = hash_spectrum(W16)
        hashes.append(H)
        spectra.append(spec)

    # Sample pairs and compare spectral distance vs hash distance
    n_pairs = min(N * 20, 300000)
    spec_dists = []; hash_dists = []

    for _ in range(n_pairs):
        i = random.randint(0, N-1); j = random.randint(0, N-1)
        if i == j: continue
        sd = spectral_distance(spectra[i], spectra[j])
        hd = sum(hw(hashes[i][w] ^ hashes[j][w]) for w in range(8))
        spec_dists.append(sd)
        hash_dists.append(hd)

    sd_arr = np.array(spec_dists)
    hd_arr = np.array(hash_dists)

    corr = np.corrcoef(sd_arr, hd_arr)[0, 1]
    print(f"corr(spectral_dist, hash_dist) = {corr:+.6f}")

    # Binned analysis
    print(f"\n{'Spectral dist percentile':>25} | {'E[hash_dist]':>12} | {'N pairs':>8}")
    print("-" * 55)
    for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        thresh = np.percentile(sd_arr, pct)
        mask = sd_arr <= thresh
        n = mask.sum()
        if n > 10:
            print(f"{'≤ P' + str(pct):>25} | {hd_arr[mask].mean():>12.2f} | {n:>8}")

    # KEY: among spectrally close pairs, what's the minimum hash distance?
    p5_thresh = np.percentile(sd_arr, 5)
    close_mask = sd_arr <= p5_thresh
    close_hd = hd_arr[close_mask]

    # Compare with random sample of same size
    random_hd = hd_arr[~close_mask][:close_mask.sum()]

    print(f"\nSpectrally close (P5) pairs:")
    print(f"  N = {close_mask.sum()}")
    print(f"  E[hash_dist] = {close_hd.mean():.2f} (random: {random_hd.mean():.2f})")
    print(f"  min hash_dist = {close_hd.min()} (random: {random_hd.min()})")
    print(f"  std hash_dist = {close_hd.std():.2f} (random: {random_hd.std():.2f})")

    gain = random_hd.mean() - close_hd.mean()
    print(f"  Gain: {gain:.2f} bits closer")

    return corr

def test_spectral_rotr_invariance_in_rounds(N=3000):
    """Does spectral invariance PERSIST through SHA-256 rounds?"""
    print(f"\n--- SPECTRAL INVARIANCE ACROSS ROUNDS (N={N}) ---")

    rotations = [6, 11, 25]  # Σ₁ rotations

    # For each round: compute carry spectrum of state addition
    # Check if spectrum is invariant to input rotation

    for R in [1, 4, 8, 16, 32, 64]:
        spec_corrs = []
        for _ in range(N):
            W16 = random_w16()
            states = sha256_rounds(W16, R)

            # Carry spectrum at round R (state[R] with IV)
            spec_orig = []
            for w in range(8):
                spec_orig.extend(carry_spectrum(IV[w], states[R][w]))
            spec_orig = np.array(spec_orig)

            # Perturbed: rotate W[0]
            for k in rotations:
                W16p = list(W16)
                W16p[0] = rotr(W16p[0], k)
                states_p = sha256_rounds(W16p, R)

                spec_pert = []
                for w in range(8):
                    spec_pert.extend(carry_spectrum(IV[w], states_p[R][w]))
                spec_pert = np.array(spec_pert)

                c = spectral_cosine(spec_orig, spec_pert)
                spec_corrs.append(c)

        avg_corr = np.mean(spec_corrs)
        print(f"  Round {R:>2}: avg spectral cosine = {avg_corr:.6f}")

def test_spectral_birthday(N=30000):
    """
    Two-phase birthday attack using spectral space:
    Phase 1: Find spectrally-close pairs (birthday on spectral dim)
    Phase 2: Among those, find hash-close pairs

    Compare cost vs standard birthday.
    """
    print(f"\n--- SPECTRAL BIRTHDAY ATTACK (N={N}) ---")

    hashes = []; spectra = []; spec_keys = []

    for _ in range(N):
        W16 = random_w16()
        H, spec = hash_spectrum(W16)
        hashes.append(H)
        spectra.append(spec)
        # Discretize spectrum for bucketing
        # Use top-K spectral components as bucket key
        key = tuple(int(s) % 100 for s in spec[:8])  # First 8 components, mod 100
        spec_keys.append(key)

    # Bucket by spectral key
    buckets = {}
    for idx, key in enumerate(spec_keys):
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(idx)

    # Find pairs in same bucket
    bucket_pairs = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        for i in range(min(len(bucket), 50)):
            for j in range(i+1, min(len(bucket), 50)):
                idx_i = bucket[i]; idx_j = bucket[j]
                hd = sum(hw(hashes[idx_i][w] ^ hashes[idx_j][w]) for w in range(8))
                sd = spectral_distance(spectra[idx_i], spectra[idx_j])
                bucket_pairs.append((hd, sd))

    if not bucket_pairs:
        print("No bucket collisions found")
        return

    bp_hd = np.array([p[0] for p in bucket_pairs])
    bp_sd = np.array([p[1] for p in bucket_pairs])

    # Compare with random pairs
    random_pairs = []
    for _ in range(len(bucket_pairs)):
        i = random.randint(0, N-1); j = random.randint(0, N-1)
        if i == j: continue
        hd = sum(hw(hashes[i][w] ^ hashes[j][w]) for w in range(8))
        random_pairs.append(hd)

    rp = np.array(random_pairs)

    print(f"Spectral-bucketed pairs: {len(bucket_pairs)}")
    print(f"  E[hash_dist] = {bp_hd.mean():.2f} (random: {rp.mean():.2f})")
    print(f"  min(hash_dist) = {bp_hd.min()} (random: {rp.min()})")
    print(f"  E[spectral_dist] = {bp_sd.mean():.2f}")
    print(f"  Bucket count: {len(buckets)}")
    print(f"  Avg bucket size: {N/len(buckets):.2f}")

    gain = rp.min() - bp_hd.min()
    print(f"\n  Spectral gain: {gain} bits closer to collision")

def test_why_spectrum_invariant(N=5000):
    """WHY is carry spectrum 0.992 ROTR-invariant?"""
    print(f"\n--- WHY IS SPECTRUM INVARIANT? (N={N}) ---")

    # Hypothesis: because GKP pattern just rotates (trivially),
    # and carry at each position depends only on LOCAL GKP context.
    # So the carry BIT PATTERN approximately rotates with GKP.
    # A rotated bit pattern has the SAME power spectrum.

    # Test: is carry(ROTR_k(a), ROTR_k(b)) ≈ ROTR_k(carry(a,b))?
    rotations = [2, 6, 11, 13, 22, 25]
    approx_rotr = {k: [] for k in rotations}

    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        cw = carry_word(a, b)

        for k in rotations:
            a_rot = rotr(a, k); b_rot = rotr(b, k)
            cw_rot = carry_word(a_rot, b_rot)
            cw_expected = rotr(cw, k)  # What carry WOULD be if it just rotated

            # How close is actual rotated carry to "just rotate carry"?
            diff = hw(cw_rot ^ cw_expected)
            approx_rotr[k].append(diff)

    print(f"HW(carry(ROTR_k(a,b)) ⊕ ROTR_k(carry(a,b))):")
    print(f"  (0 = carry exactly rotates with inputs)")
    for k in rotations:
        arr = np.array(approx_rotr[k])
        print(f"  ROTR-{k:>2}: mean={arr.mean():.3f}, exact_match={np.sum(arr==0)/N:.4f}")

    avg = np.mean([np.mean(approx_rotr[k]) for k in rotations])
    print(f"  Average: {avg:.3f} bits differ (out of 32)")
    print(f"  Fraction preserved: {1 - avg/16:.4f}")

    # INSIGHT: if avg ≈ 6.2 bits differ → 19.4% of carry changes
    # → 80.6% of carry IS just rotation!
    # → power spectrum correlation ≈ (1 - 6.2/32)² ≈ 0.66... no, higher
    # → The 0.992 comes from spectral properties being more robust than bit-level

    print(f"\n  If {avg:.1f} bits change: naive bit preservation = {(32-avg)/32:.3f}")
    print(f"  But spectral correlation = 0.992")
    print(f"  Spectrum >> bit-level because:")
    print(f"    - Changed bits are at chain BOUNDARIES (high frequency)")
    print(f"    - Core chain structure (low frequency) is PERFECTLY preserved")
    print(f"    - Power spectrum weights low frequencies more")

def test_low_freq_invariance(N=5000):
    """Are LOW-frequency carry components MORE invariant than high?"""
    print(f"\n--- LOW vs HIGH FREQUENCY INVARIANCE (N={N}) ---")

    rotations = [2, 6, 11, 13, 22, 25]

    # Per-frequency band invariance
    freq_bands = {
        "DC (f=0)": [0],
        "Low (f=1-4)": list(range(1, 5)),
        "Mid (f=5-11)": list(range(5, 12)),
        "High (f=12-16)": list(range(12, 17)),
    }

    band_corrs = {band: [] for band in freq_bands}

    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        cb = np.array(carry_bits(a, b), dtype=float)
        fft_orig = np.fft.fft(cb)

        for k in rotations:
            a_rot = rotr(a, k); b_rot = rotr(b, k)
            cb_rot = np.array(carry_bits(a_rot, b_rot), dtype=float)
            fft_rot = np.fft.fft(cb_rot)

            for band_name, freqs in freq_bands.items():
                orig_power = sum(abs(fft_orig[f])**2 for f in freqs)
                rot_power = sum(abs(fft_rot[f])**2 for f in freqs)
                if orig_power > 0.01 and rot_power > 0.01:
                    ratio = min(orig_power, rot_power) / max(orig_power, rot_power)
                    band_corrs[band_name].append(ratio)

    print(f"Per-band power invariance (1.0 = perfect):")
    for band_name in freq_bands:
        arr = np.array(band_corrs[band_name])
        print(f"  {band_name:>20}: {arr.mean():.6f} ± {arr.std():.4f}")

    print(f"\n  If LOW >> HIGH → chain structure preserved, boundaries change")
    print(f"  → ≡ can be defined on low-frequency carry components only")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 106: SPECTRAL EQUIVALENCE")
    print("Define ≡ in carry Fourier space")
    print("=" * 60)

    test_why_spectrum_invariant(5000)
    test_low_freq_invariance(5000)
    dim95, dim99, sigma = test_spectral_dimension(8000)
    corr = test_spectral_collision_correlation(15000)
    test_spectral_rotr_invariance_in_rounds(1000)
    test_spectral_birthday(20000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Spectral equivalence as ≡")
    print(f"  Spectral dim (95%): {dim95}")
    print(f"  Spectral dim (99%): {dim99}")
    print(f"  Spectral-hash correlation: {corr:+.6f}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
