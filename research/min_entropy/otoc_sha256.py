"""Discrete OTOC (Out-of-Time-Order Correlator) measurement for SHA-256.

Classical analog of quantum OTOC adapted for Boolean SHA round function.

Definition:
  C[i, j, r] = E_msg[ Pr(state[r][j] flips | input bit i flips) - 0.5 ]

Interpretation:
  - C[i, j, r] = 0    → input bit i has no effect on output bit j at round r
  - |C[i, j, r]| = 0.5 → deterministic flip (max correlation)
  - C[i, j, r] = 0    → fully scrambled (random 50/50)

OTOC matrix C(r) ∈ R^(512×256):
  - Frobenius norm ||C(r)||_F^2 = sum of all squared correlations
  - At r=0: bit i flip → exactly bit i flips (if i in state range), else 0
  - As r grows: C entries spread to nonzero values
  - At r→∞: all C[i,j] → 0 (deviation from 0.5 = 0)

Connections to physics:
  - Maldacena-Shenker-Stanford bound: λ_L ≤ 2π/β (quantum chaos)
  - Discrete analog: rate of approach to ||C(r)||_F → 0 = "Lyapunov exponent"
  - Methodology has T_LYAPUNOV_4: λ = 4 bit/round (П-1105)

This script measures ||C(r)||_F^2 for r ∈ {1..16} and fits exponential decay.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch
from sha256_reverse import expand_schedule, U32, MASK


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sha256_results.json'


def state_at_r_batch(M_arr, r):
    """Vectorized state[r] for N messages (each 16 uint32 words). Returns (N, 8) uint32."""
    N = M_arr.shape[0]
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, 64):
        if t > r + 16: break
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    """Pack (N, 8) uint32 → (N, 256) uint8 bits."""
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def msg_to_bits(M_arr):
    """Pack (N, 16) uint32 → (N, 512) bits."""
    bytes_be = M_arr.view('<u1').reshape(M_arr.shape[0], 16, 4)[:, :, ::-1].reshape(M_arr.shape[0], 64)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :512]


def measure_otoc_matrix(r, N=200, seed=42):
    """Compute OTOC matrix C(r) ∈ R^(512×256).

    For N random messages, for each input bit i (0..511), flip i and measure
    how state[r] changes. Average flip probability per output bit.
    """
    rng = np.random.default_rng(seed)
    M_orig = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)

    # Original state[r]
    state_orig = state_at_r_batch(M_orig, r)
    bits_orig = state_to_bits(state_orig)  # (N, 256)

    # For each input bit i, flip and measure
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32
        bit = 31 - (i % 32)  # MSB-first for big-endian view
        M_flip = M_orig.copy()
        M_flip[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_batch(M_flip, r)
        bits_flip = state_to_bits(state_flip)
        # Flip probability for each output bit
        flips = (bits_orig != bits_flip).astype(np.float64)  # (N, 256)
        C[i] = flips.mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# Discrete OTOC for SHA-256 round function")
    print("# C[i,j,r] = P(state[r][j] flips | input bit i flips) - 0.5\n")

    rounds_to_measure = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64]
    N = 200  # messages per OTOC computation

    results = {}
    print(f"  N={N} messages, 512 input bits × 256 output bits per round")
    print(f"\n{'r':>3}  {'||C||_F²':>12}  {'mean|C|':>10}  {'max|C|':>10}  {'time':>8}")
    for r in rounds_to_measure:
        ts = time.time()
        C = measure_otoc_matrix(r, N=N)
        elapsed = time.time() - ts
        F_sq = float((C ** 2).sum())  # Frobenius norm squared
        mean_abs = float(np.mean(np.abs(C)))
        max_abs = float(np.max(np.abs(C)))
        results[r] = {'frobenius_sq': F_sq, 'mean_abs': mean_abs,
                      'max_abs': max_abs, 'time': elapsed}
        print(f"{r:>3}  {F_sq:>12.2f}  {mean_abs:>10.4f}  {max_abs:>10.4f}  {elapsed:>7.1f}s")

    # Reference: random oracle baseline
    print(f"\n# RO baseline (BLAKE2b keyed) for comparison:")
    rng = np.random.default_rng(0xCAFE)
    M_orig = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    import hashlib

    def blake_state(M_arr, key):
        N = M_arr.shape[0]
        bits = np.zeros((N, 256), dtype=np.uint8)
        for i in range(N):
            data = M_arr[i].tobytes()
            d = hashlib.blake2b(data, key=key, digest_size=32).digest()
            bits[i] = np.unpackbits(np.frombuffer(d, dtype=np.uint8))[:256]
        return bits

    key = rng.bytes(16)
    bits_orig = blake_state(M_orig, key)
    C_ro = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        M_flip = M_orig.copy()
        M_flip[:, word] ^= np.uint32(1 << bit)
        bits_flip = blake_state(M_flip, key)
        C_ro[i] = (bits_orig != bits_flip).mean(axis=0) - 0.5
    F_ro = float((C_ro ** 2).sum())
    print(f"  ||C_RO||_F² = {F_ro:.2f}, mean|C_RO| = {np.mean(np.abs(C_ro)):.4f}")
    print(f"  (theoretical RO: ~512×256×var(0.5)/N = ~{512*256*0.25/N:.2f})")

    # Analysis
    print(f"\n## Frobenius norm decay (||C(r)||_F²):")
    print(f"  Theoretical scrambled limit: ~{512*256*0.25/N:.1f} (variance of binomial sample)")
    print(f"  Measured at r=64: {results[64]['frobenius_sq']:.2f}")

    # Fit Lyapunov-like decay
    # At early r, ||C||_F^2 should decay roughly exponentially toward limit
    print(f"\n## Lyapunov-analog rate fit:")
    F_inf = 512 * 256 * 0.25 / N  # ~163 for N=200
    F_vals = np.array([results[r]['frobenius_sq'] for r in rounds_to_measure])
    rs = np.array(rounds_to_measure, dtype=float)
    # Subtract limit, take log
    excess = F_vals - F_inf
    excess[excess <= 0] = 0.001
    log_excess = np.log(excess)
    # Fit linear to early rounds (1..6)
    mask = rs <= 6
    if mask.sum() >= 2:
        slope, intercept = np.polyfit(rs[mask], log_excess[mask], 1)
        lambda_decay = -slope  # rate of decay
        print(f"  Early rounds (r≤6): log(||C||²-limit) = {intercept:.2f} - {-slope:.3f}·r")
        print(f"  Effective decay rate λ = {lambda_decay:.3f} per round")

    out = {
        'N_messages': N,
        'rounds': rounds_to_measure,
        'results': {str(r): v for r, v in results.items()},
        'ro_baseline': {'frobenius_sq': F_ro, 'mean_abs': float(np.mean(np.abs(C_ro)))},
        'theoretical_limit': F_inf,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
