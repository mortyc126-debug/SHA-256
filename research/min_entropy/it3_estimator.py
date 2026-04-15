"""
IT-3, Stage 1: rigorous Δ estimator with bias correction + sanity tests.

DEFINITIONS
-----------
Let h be a deterministic hash, X a random variable with distribution P_X
on a finite support, k a truncation length, Y_h := h(X) ↾ k.

For RO null model: assume Y_h is independent of any function f(X) with
P(Y = y) = 1/M  (M = 2^k).

Define structural information leak (IT-3 main quantity):
    I_h(f, k) := I(f(X); Y_h)
              = H(f(X)) + H(Y_h) − H(f(X), Y_h)

For random oracle:  E_RO[I_RO(f, k)] = sampling_bias(N, K_f, M).
For real hash h:    measure I_h(f, k) directly.

Structural Information Excess:
    Δ_h(f, k) := I_h(f, k) − E_RO[I_RO(f, k)]                  (in bits)

Operational interpretation: Δ_h(f, k) > 0 means the hash leaks more
information about feature f(X) into the truncated output than a random
oracle would on the same input set.

Z-statistic for detection:
    z := (I_h − mean(I_RO_realizations)) / std(I_RO_realizations)

The RO null is estimated by R independent realizations (keyed BLAKE2b
with random salts). With N = 130 816 inputs and ~200 realizations we
get a stable null distribution.

ESTIMATOR
---------
Plug-in MI:
    Î_plug = Σ_{x,y} ĉ(x,y)/N · log2( ĉ(x,y) · N / (ĉ(x) ĉ(y)) )

Miller-Madow bias correction:
    bias(Ĥ_plug) = -(K_obs - 1) / (2 N ln 2)            [in bits]
where K_obs = number of NON-EMPTY cells.

For I = H(f) + H(Y) - H(f,Y):
    bias(Î_plug) = (K_fY - K_f - K_Y + 1) / (2 N ln 2)

So:
    Î_MM = Î_plug - (K_fY - K_f - K_Y + 1) / (2 N ln 2)

This correction does NOT cancel the entire bias for small N, but it
reduces it from O(1/N) coefficient by a known factor. Importantly, for
fair comparison SHA vs RO, we apply the SAME correction to both.

For the z-statistic, we don't even need the correction because both
SHA-256 and RO realizations have the same K_obs distribution; the bias
mostly cancels in (I_h - mean(I_RO)). The correction is reported only
for context.

SANITY TESTS (in this file)
---------------------------
Test 1: Y completely independent of X (synthetic uniform Y).
        → expect I_hat ≈ 0, Î_MM ≈ 0.

Test 2: Y is a deterministic function of f(X) (full leak).
        → expect I_hat → H(f).

Test 3: Y is a noisy function of f(X) — verify estimate matches the
        analytic value within tolerance.
"""

import math
import numpy as np
from collections import Counter


def mi_plugin(f_arr, y_arr):
    """Plug-in MI estimate (in bits) and Miller-Madow corrected version.

    Both arrays must be 1-D integer arrays of the same length N.
    Returns: (I_plug, I_MM, K_f, K_y, K_fy)  all in bits / counts.
    """
    assert f_arr.shape == y_arr.shape and f_arr.ndim == 1
    N = f_arr.shape[0]

    # marginals
    f_counts = np.bincount(f_arr)
    y_counts = np.bincount(y_arr)
    K_f = int((f_counts > 0).sum())
    K_y = int((y_counts > 0).sum())

    # joint via numpy bincount on combined index
    K_y_size = y_arr.max() + 1
    combined = f_arr.astype(np.int64) * K_y_size + y_arr.astype(np.int64)
    fy_counts = np.bincount(combined)
    K_fy = int((fy_counts > 0).sum())

    # plug-in MI in bits
    p_f = f_counts / N
    p_y = y_counts / N
    # iterate over non-empty joint cells only
    nz = np.nonzero(fy_counts)[0]
    f_idx = nz // K_y_size
    y_idx = nz % K_y_size
    p_fy = fy_counts[nz] / N
    log_arg = p_fy / (p_f[f_idx] * p_y[y_idx])
    I_plug = float((p_fy * np.log2(log_arg)).sum())

    # Miller-Madow correction (in bits): bias = (K_fy - K_f - K_y + 1) / (2 N ln 2)
    bias_bits = (K_fy - K_f - K_y + 1) / (2.0 * N * math.log(2))
    I_MM = I_plug - bias_bits

    return I_plug, I_MM, K_f, K_y, K_fy, bias_bits


# ---------------------------------------------------------------------------
# Sanity tests
# ---------------------------------------------------------------------------

def sanity_independent():
    """Y truly uniform random, independent of f(X). Expect I ≈ 0."""
    rng = np.random.default_rng(0)
    N = 130816
    K_f = 64
    M = 4096
    f = rng.integers(0, K_f, size=N, dtype=np.int64)
    y = rng.integers(0, M,   size=N, dtype=np.int64)
    I_plug, I_MM, *_ = mi_plugin(f, y)
    expected_bias = (K_f * M - K_f - M + 1) / (2.0 * N * math.log(2))
    print(f"  independent: I_plug={I_plug:.6f}  I_MM={I_MM:.6f}  "
          f"expected_bias={expected_bias:.6f}")
    return I_plug, I_MM


def sanity_perfect_leak():
    """Y = f(X) deterministically. Expect I ≈ H(f) = log2(K_f)."""
    rng = np.random.default_rng(1)
    N = 130816
    K_f = 64
    f = rng.integers(0, K_f, size=N, dtype=np.int64)
    y = f.copy()                     # perfect leak
    I_plug, I_MM, *_ = mi_plugin(f, y)
    H_f = math.log2(K_f)
    print(f"  perfect leak: I_plug={I_plug:.6f}  I_MM={I_MM:.6f}  "
          f"H(f)={H_f:.6f}")


def sanity_partial_leak():
    """Y = f(X) ⊕ noise with known noise level. Expect MI matches analytic."""
    rng = np.random.default_rng(2)
    N = 130816
    K_f = 16
    M = 4096   # so y = f * (M/K_f) + noise
    f = rng.integers(0, K_f, size=N, dtype=np.int64)
    # y embeds f in the high bits of M, plus uniform noise in low bits
    bits_y = int(math.log2(M))            # 12
    bits_f = int(math.log2(K_f))          # 4
    bits_noise = bits_y - bits_f          # 8
    noise = rng.integers(0, 1 << bits_noise, size=N, dtype=np.int64)
    y = (f << bits_noise) | noise
    I_plug, I_MM, *_ = mi_plugin(f, y)
    # analytic: I(f; y) = H(f) since f is fully recoverable from y high bits
    H_f = math.log2(K_f)
    print(f"  partial leak: I_plug={I_plug:.6f}  I_MM={I_MM:.6f}  "
          f"analytic H(f)={H_f:.6f}")


def sanity_weak_correlation(rho=0.05):
    """Y mostly random, but with prob rho deterministically encodes f."""
    rng = np.random.default_rng(3)
    N = 130816
    K_f = 64
    M = 4096
    f = rng.integers(0, K_f, size=N, dtype=np.int64)
    bits_y = 12
    bits_f = 6
    noise = rng.integers(0, 1 << (bits_y - bits_f), size=N, dtype=np.int64)
    embedded = (f << (bits_y - bits_f)) | noise
    random_y = rng.integers(0, M, size=N, dtype=np.int64)
    use_embedded = rng.random(N) < rho
    y = np.where(use_embedded, embedded, random_y)
    I_plug, I_MM, *_ = mi_plugin(f, y)
    # rough analytic: I ≈ rho * H(f) when rho << 1
    approx = rho * math.log2(K_f)
    print(f"  weak corr ρ={rho}: I_plug={I_plug:.6f}  I_MM={I_MM:.6f}  "
          f"rough analytic ≈ ρ·H(f) = {approx:.6f}")


def sanity_variance(R=200):
    """
    Variance of plug-in I under H_0 (independence). Important for z-tests.
    Run R independent realizations of (f, y) ~ uniform×uniform.
    """
    rng = np.random.default_rng(42)
    N = 130816
    K_f = 64
    M = 4096
    Is = []
    for _ in range(R):
        f = rng.integers(0, K_f, size=N, dtype=np.int64)
        y = rng.integers(0, M,   size=N, dtype=np.int64)
        I_plug, I_MM, *_ = mi_plugin(f, y)
        Is.append(I_plug)
    arr = np.asarray(Is)
    print(f"  H_0 variance (R={R}): mean(I_plug)={arr.mean():.6f}  "
          f"std={arr.std(ddof=1):.6f}  ")
    print(f"      → 5σ resolution on Δ ≈ {5*arr.std(ddof=1):.6f} bits")
    return arr.mean(), arr.std(ddof=1)


if __name__ == '__main__':
    print("# IT-3 Stage 1: estimator sanity tests")
    print()
    print("Test 1: independent (expect I ≈ bias):")
    sanity_independent()
    print()
    print("Test 2: perfect leak (expect I ≈ H(f) = 6.0):")
    sanity_perfect_leak()
    print()
    print("Test 3: partial leak (expect I ≈ H(f) = 4.0):")
    sanity_partial_leak()
    print()
    print("Test 4: weak correlation ρ=0.05 (expect I ≈ ρ·H(f) ≈ 0.3):")
    sanity_weak_correlation(0.05)
    print()
    print("Test 5: H_0 variance over 200 reps (calibrates z-test resolution):")
    sanity_variance(R=200)
