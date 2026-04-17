"""Phase 1 — Walsh mixing spectrum of SHA-256 and SHA-3.

Measures τ_k = decay time constant of Ω_k(r) under round function iteration,
for k = 1, 2, 3, 4, 5, 6. First systematic measurement of the full spectrum.

Protocol (per hash):
- χ_S basis: state after r_χ rounds of compression (non-trivial transformation)
- Target: state after r > r_χ rounds
- For each k: build chi_arr with subset_size chosen so C(subset, k) ~ 5K tuples
- Measure Ω_k(r) = Pearson(direct_z[b], chain_k[b]) across 256 output bits
- Fit exponential Ω_k(r) = A_k exp(-(r-r_χ)/τ_k) + b_k

Output:
- τ_k per hash: half-life of k-th order Walsh structure under round iteration
- Plot-able spectrum comparing architectures
"""
import hashlib, json, math, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast
from keccak_vec import keccak_f, absorb_sha3_256
import sha256_chimera as ch
from it37_sha256_reference import sha256_partial_state


# Subset sizes per k: keep C(s, k) ~ 5K tuples for consistent stat precision
SUBSET = {1: 32, 2: 32, 3: 32, 4: 22, 5: 18, 6: 15}

# Round sampling: fine-grained near decay region, sparse at saturated/RO ends
ROUNDS_SHA256 = [4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64]
ROUNDS_SHA3 = [1, 2, 3, 4, 6, 8, 12, 18, 24]

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase1_walsh_spectrum.json')


def extract_sha3_state_bits(state, n_bits=256):
    N = state.shape[0]
    n_lanes = (n_bits + 63) // 64
    lanes_out = np.zeros((N, n_lanes), dtype=np.uint64)
    for idx in range(n_lanes):
        x = idx % 5; y = idx // 5
        lanes_out[:, idx] = state[:, y, x]
    out_bytes = lanes_out.view(dtype='<u1').reshape(N, n_lanes * 8)[:, :n_bits // 8]
    bits = np.unpackbits(out_bytes, axis=1, bitorder='big')[:, :n_bits]
    return bits


def fit_exponential_decay(r_vals, omega_vals, r0, ro_offset):
    """Fit Ω(r) - ro_offset = A exp(-(r-r0)/τ) via log-linear regression.

    Only uses data points where Ω-ro_offset > 3×noise (avoid log of noise).
    Returns (tau, A, r_valid_count). Returns None if insufficient data.
    """
    r_arr = np.array(r_vals, dtype=float)
    omega_arr = np.array(omega_vals, dtype=float)
    delta = omega_arr - ro_offset
    # Keep only points significantly above RO band
    mask = delta > 0.1
    if mask.sum() < 3:
        return None, None, 0
    r_fit = r_arr[mask] - r0
    y_fit = np.log(delta[mask])
    # Weighted linear fit
    slope, intercept = np.polyfit(r_fit, y_fit, 1)
    tau = -1.0 / slope if slope < 0 else float('inf')
    A = math.exp(intercept)
    return tau, A, int(mask.sum())


def measure_spectrum_sha256(inputs, fa, r_chi=4, verbose=True):
    """Measure Ω_k(r) spectrum for SHA-256."""
    N = len(inputs)

    # chi_S basis: state at r_chi
    if verbose: print(f"\n## SHA-256: χ_S basis = state at r={r_chi}")
    ts = time.time()
    state_chi = sha256_partial_state(inputs, r_chi)
    if verbose: print(f"  basis state: {time.time()-ts:.1f}s")

    # Pre-compute chi_arr per k
    chi_cache = {}
    for k in SUBSET:
        ts = time.time()
        chi_arr, _ = build_chi_arr(state_chi, k=k, subset_size=SUBSET[k])
        chi_cache[k] = chi_arr
        if verbose: print(f"  chi_arr k={k} (subset={SUBSET[k]}, M={chi_arr.shape[0]}): {time.time()-ts:.1f}s")

    # Target at each round
    results = {k: [] for k in SUBSET}
    round_list = [r for r in ROUNDS_SHA256 if r >= r_chi]
    for r in round_list:
        ts = time.time()
        target_bits = sha256_partial_state(inputs, r)
        for k in SUBSET:
            omega, ss, _, _, _ = omega_k_fast(chi_cache[k], target_bits, fa)
            results[k].append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        if verbose:
            omegas = [results[k][-1]['omega'] for k in sorted(SUBSET)]
            print(f"  r={r:>2}: " + "  ".join(f"Ω_{k}={o:+.3f}" for k, o in zip(sorted(SUBSET), omegas))
                  + f"  ({time.time()-ts:.1f}s)")

    return {'r_chi': r_chi, 'rounds': round_list, 'per_k': results}


def measure_spectrum_sha3(inputs, fa, r_chi=1, verbose=True):
    """Measure Ω_k(r) spectrum for SHA-3-256 (Keccak-f)."""
    N = len(inputs)

    if verbose: print(f"\n## SHA-3: χ_S basis = state at r={r_chi} Keccak-f rounds")
    ts = time.time()
    state_chi = keccak_f(absorb_sha3_256(inputs), num_rounds=r_chi)
    state_chi_bits = extract_sha3_state_bits(state_chi, 256)
    if verbose: print(f"  basis state: {time.time()-ts:.1f}s")

    chi_cache = {}
    for k in SUBSET:
        ts = time.time()
        chi_arr, _ = build_chi_arr(state_chi_bits, k=k, subset_size=SUBSET[k])
        chi_cache[k] = chi_arr
        if verbose: print(f"  chi_arr k={k}: M={chi_arr.shape[0]} ({time.time()-ts:.1f}s)")

    results = {k: [] for k in SUBSET}
    round_list = [r for r in ROUNDS_SHA3 if r >= r_chi]
    state0 = absorb_sha3_256(inputs)
    for r in round_list:
        ts = time.time()
        target_state = keccak_f(state0, num_rounds=r)
        target_bits = extract_sha3_state_bits(target_state, 256)
        for k in SUBSET:
            omega, ss, _, _, _ = omega_k_fast(chi_cache[k], target_bits, fa)
            results[k].append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        if verbose:
            omegas = [results[k][-1]['omega'] for k in sorted(SUBSET)]
            print(f"  r={r:>2}: " + "  ".join(f"Ω_{k}={o:+.3f}" for k, o in zip(sorted(SUBSET), omegas))
                  + f"  ({time.time()-ts:.1f}s)")

    return {'r_chi': r_chi, 'rounds': round_list, 'per_k': results}


def compute_ro_baselines(inputs, fa, chi_cache, n_realizations=10):
    """Per-k RO null band using keyed BLAKE2b as random oracle target."""
    N = len(inputs)
    nprng = np.random.default_rng(0xBADF00D)
    ro_stats = {}
    for k in chi_cache:
        ts = time.time()
        omegas = []
        for rr in range(n_realizations):
            key = nprng.bytes(16)
            target_bits = np.zeros((N, 256), dtype=np.uint8)
            for i, m in enumerate(inputs):
                d = hashlib.blake2b(m, key=key, digest_size=32).digest()
                for bi in range(32):
                    for bb in range(8):
                        target_bits[i, bi*8+bb] = (d[bi] >> (7-bb)) & 1
            omega, _, _, _, _ = omega_k_fast(chi_cache[k], target_bits, fa)
            omegas.append(float(omega))
        ro_stats[k] = {'mean': float(np.mean(omegas)), 'std': float(np.std(omegas, ddof=1))}
        print(f"  k={k}: RO={ro_stats[k]['mean']:+.3f}±{ro_stats[k]['std']:.3f} "
              f"({time.time()-ts:.0f}s)")
    return ro_stats


def main():
    t0 = time.time()
    print("# Phase 1 — Walsh mixing spectrum (τ_k) of SHA-256 and SHA-3-256")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N = {N} HW=2 exhaustive, feature=bit5_max")
    print(f"# k values: {sorted(SUBSET)}, subset sizes: {SUBSET}")

    # SHA-256 spectrum
    sha256_data = measure_spectrum_sha256(inputs, fa, r_chi=4)

    # SHA-3 spectrum
    sha3_data = measure_spectrum_sha3(inputs, fa, r_chi=1)

    # Compute RO baselines (once with SHA-256 chi_cache — per-k RO doesn't
    # depend on which hash we probe, only on chi_arr dimensionality)
    print(f"\n# RO null band (per k):")
    state_chi = sha256_partial_state(inputs, 4)
    chi_cache = {k: build_chi_arr(state_chi, k=k, subset_size=SUBSET[k])[0] for k in SUBSET}
    ro_stats = compute_ro_baselines(inputs, fa, chi_cache, n_realizations=10)

    # Fit τ_k per hash
    print(f"\n# Fitting τ_k (exponential decay):")
    tau_sha256 = {}
    tau_sha3 = {}
    for k in sorted(SUBSET):
        # SHA-256
        rounds = [e['r'] for e in sha256_data['per_k'][k]]
        omegas = [e['omega'] for e in sha256_data['per_k'][k]]
        tau, A, npts = fit_exponential_decay(rounds, omegas, sha256_data['r_chi'],
                                              ro_stats[k]['mean'])
        tau_sha256[k] = {'tau': tau, 'A': A, 'n_fit_points': npts}
        print(f"  SHA-256 k={k}: τ_{k} = {tau:.1f} rounds  (A={A:.2f}, fit on {npts} pts)"
              if tau and tau != float('inf') else
              f"  SHA-256 k={k}: τ_{k} = N/A (insufficient dynamic range)")

        # SHA-3
        rounds = [e['r'] for e in sha3_data['per_k'][k]]
        omegas = [e['omega'] for e in sha3_data['per_k'][k]]
        tau, A, npts = fit_exponential_decay(rounds, omegas, sha3_data['r_chi'],
                                              ro_stats[k]['mean'])
        tau_sha3[k] = {'tau': tau, 'A': A, 'n_fit_points': npts}
        print(f"  SHA-3   k={k}: τ_{k} = {tau:.1f} rounds  (A={A:.2f}, fit on {npts} pts)"
              if tau and tau != float('inf') else
              f"  SHA-3   k={k}: τ_{k} = N/A (insufficient dynamic range)")

    # Summary table
    print(f"\n=== WALSH MIXING SPECTRUM ===")
    print(f"{'k':>2}  {'τ_k SHA-256':>12}  {'τ_k SHA-3':>12}  {'ratio':>8}")
    for k in sorted(SUBSET):
        t256 = tau_sha256[k]['tau']
        t3 = tau_sha3[k]['tau']
        ratio = t256 / t3 if (t3 and t3 != float('inf') and t3 > 0) else None
        t256_s = f"{t256:.1f}" if (t256 and t256 != float('inf')) else "N/A"
        t3_s = f"{t3:.1f}" if (t3 and t3 != float('inf')) else "N/A"
        ratio_s = f"{ratio:.2f}×" if ratio else "-"
        print(f"  {k}  {t256_s:>12}  {t3_s:>12}  {ratio_s:>8}")

    out = {
        'N': N,
        'feature': 'bit5_max',
        'subset_sizes': SUBSET,
        'sha256': sha256_data,
        'sha3': sha3_data,
        'ro_null': ro_stats,
        'tau_sha256': tau_sha256,
        'tau_sha3': tau_sha3,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
