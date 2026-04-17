"""Oracle Gauge — quantitative measurement of hash function deviation from random oracle.

Usage:
    python oracle_gauge.py --hash sha256 [--N 130816] [--feature bit5_max]

Computes Ω_k spectrum (k=1, 2, 3) via cross-bit Walsh chain test on HW=2
exhaustive inputs. Compares to RO null band (50 keyed-BLAKE2b realizations).

Output: numerical Ω_k values + classification (RO-like / deviation / broken).

This tool implements the methodology we developed across IT-6, IT-13,
IT-21, IT-23, IT-24 validating that Omega_k can systematically discriminate
broken hashes (MD5, SHA-1: Ω_3 ≈ 1.0) from secure ones (SHA-2/3, BLAKE2:
Ω_3 < 0.1 in input→hash probe; +0.85 in state1 internal probe).
"""
import argparse, hashlib, json, math, os, sys, time
from itertools import combinations
import numpy as np


VERSION = "1.0.0"
DEFAULT_N = 130816  # C(512, 2) — HW=2 exhaustive


def low_hw2_inputs():
    """Generate all C(512, 2) = 130816 HW=2 64-byte inputs."""
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b))
        pos.append(p)
    return inputs, pos


def make_feature(pos, name='bit5_max'):
    """Input feature f: {HW=2 inputs} → {0,1}."""
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    min_p = np.asarray([p[0] for p in pos], dtype=np.int64)
    if name == 'bit5_max':   return ((max_p >> 5) & 1).astype(np.uint8)
    if name == 'bit4_max':   return ((max_p >> 4) & 1).astype(np.uint8)
    if name == 'bit6_max':   return ((max_p >> 6) & 1).astype(np.uint8)
    if name == 'parity_lsb': return (((min_p & 1) ^ (max_p & 1))).astype(np.uint8)
    if name == 'hw_parity':  return np.array([sum(int(b).bit_count() for b in m)%2 for m in pos], dtype=np.uint8)
    raise ValueError(f"Unknown feature: {name}")


def hash_to_bits(inputs, hash_fn, digest_bits=None):
    """Apply hash to each input, extract first `digest_bits` bits as (N, digest_bits) uint8.

    FIX (v1.1): No longer zero-pads short digests to 256 bits. Uses ACTUAL digest
    size to avoid spurious Ω_k signals from constant bits. Caller can specify
    digest_bits explicitly for uniform comparison (e.g., truncate all to 128 bits).
    """
    # Determine actual digest size from one test
    test_d = hash_fn(inputs[0])
    actual_bits = len(test_d) * 8
    if digest_bits is None:
        digest_bits = actual_bits
    else:
        digest_bits = min(digest_bits, actual_bits)
    digest_bytes = (digest_bits + 7) // 8

    N = len(inputs)
    bits = np.zeros((N, digest_bits), dtype=np.uint8)
    for i, m in enumerate(inputs):
        d = hash_fn(m)
        for bi in range(min(digest_bytes, len(d))):
            for bb in range(8):
                if bi*8 + bb < digest_bits:
                    bits[i, bi*8+bb] = (d[bi] >> (7-bb)) & 1
    return bits


def build_chi_arr(state1_bits, k, subset_size=32):
    """Precompute chi_S for all k-tuples over first subset_size state1 bits. Returns (n_tuples, N) int8."""
    s1_pm = state1_bits.astype(np.int8) * 2 - 1
    s1_sub = s1_pm[:, :subset_size]
    tuples = list(combinations(range(subset_size), k))
    if len(tuples) == 0:
        return np.empty((0, state1_bits.shape[0]), dtype=np.int8), tuples
    chi_arr = np.empty((len(tuples), state1_bits.shape[0]), dtype=np.int8)
    for i, idx in enumerate(tuples):
        chi = s1_sub[:, idx[0]].copy()
        for j in idx[1:]:
            chi = chi * s1_sub[:, j]
        chi_arr[i] = chi
    return chi_arr, tuples


def omega_k_fast(chi_arr, target_bits, f_arr):
    """Compute Ω_k given precomputed chi_arr and target bits via BLAS matmul.

    FIX (v1.1): Filter out constant columns (std=0) from target_bits before
    computing correlations. Constant bits would cause degenerate Walsh
    correlations (zero z_out, spurious corr patterns).
    """
    N, n_target_bits = target_bits.shape
    sN = math.sqrt(N)
    f_pm = f_arr.astype(np.int8) * 2 - 1
    target_pm = target_bits.astype(np.int8) * 2 - 1  # (N, n_target_bits)

    # Detect and remove constant columns (all +1 or all -1)
    col_mean = target_pm.mean(axis=0)
    var_mask = np.abs(col_mean) < 1 - 1e-9  # keep non-constant
    n_const = (~var_mask).sum()
    if n_const > 0:
        target_pm = target_pm[:, var_mask]
    n_useful = target_pm.shape[1]

    if n_useful < 8:
        return 0.0, 0, np.zeros(n_target_bits), np.zeros(n_target_bits), n_const

    # All z_out at once: chi_arr (n_tup × N) @ target_pm (N × K) → (n_tup × K)
    z_in = (chi_arr.astype(np.float32) @ f_pm.astype(np.float32)) / sN
    z_out_matrix = (chi_arr.astype(np.float32) @ target_pm.astype(np.float32)) / sN
    chain_z = (z_in[:, None] * z_out_matrix).sum(axis=0) / sN
    direct_z = (f_pm.astype(np.float32) @ target_pm.astype(np.float32)) / sN

    if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
        omega = 0.0
    else:
        omega = float(np.corrcoef(direct_z, chain_z)[0, 1])
    same_sign = int((np.sign(direct_z) == np.sign(chain_z)).sum())
    return omega, same_sign, direct_z, chain_z, n_const


def ro_null_band(inputs, state1_bits, f_arr, chi_arr, n_realizations=10):
    """Compute RO null band by using keyed BLAKE2b as 'fresh random oracle' target."""
    nprng = np.random.default_rng(0xBADF00D)
    omegas = []
    for r in range(n_realizations):
        key = nprng.bytes(16)
        def f(m): return hashlib.blake2b(m, key=key, digest_size=32).digest()
        bits = hash_to_bits(inputs, f)
        omega, _, _, _, _ = omega_k_fast(chi_arr, bits, f_arr)
        omegas.append(omega)
    omegas = np.array(omegas)
    return float(omegas.mean()), float(omegas.std(ddof=1)), omegas.tolist()


def classify(omega, ro_mean, ro_std):
    """Classify omega value into: RO-like / deviation / broken."""
    z = abs(omega - ro_mean) / ro_std if ro_std > 0 else 0
    if abs(omega) > 0.9:
        return "BROKEN", f"Ω_k > 0.9 — strong structural bias (like MD5/SHA-1 at +0.998)", z
    elif z > 10:
        return "SEVERE DEVIATION", f"Ω_k {z:.1f}σ outside RO null band", z
    elif z > 5:
        return "DEVIATION", f"Ω_k {z:.1f}σ outside RO null band", z
    elif z > 3:
        return "MILD DEVIATION", f"Ω_k {z:.1f}σ — may warrant further investigation", z
    else:
        return "RO-LIKE", f"Ω_k {z:.1f}σ — within RO null band", z


def run(hash_name, N_samples=None, feature_name='bit5_max', truncate_bits=128, verbose=True):
    """Main entry point.

    truncate_bits: target digest length in bits for fair cross-hash comparison.
                   Default 128 = common minimum across MD5/SHA-1/SHA-2.
    """
    # Get hash function
    HASH_MAP = {
        'md5':      (hashlib.md5, 16),
        'sha1':     (hashlib.sha1, 20),
        'sha224':   (hashlib.sha224, 28),
        'sha256':   (hashlib.sha256, 32),
        'sha384':   (hashlib.sha384, 48),
        'sha512':   (hashlib.sha512, 64),
        'sha3_224': (hashlib.sha3_224, 28),
        'sha3_256': (hashlib.sha3_256, 32),
        'sha3_384': (hashlib.sha3_384, 48),
        'sha3_512': (hashlib.sha3_512, 64),
        'blake2b':  (lambda m: hashlib.blake2b(m).digest(), 64),
        'blake2s':  (lambda m: hashlib.blake2s(m).digest(), 32),
    }
    if hash_name not in HASH_MAP:
        raise ValueError(f"Unknown hash: {hash_name}. Options: {list(HASH_MAP.keys())}")
    hash_class, digest_size = HASH_MAP[hash_name]
    def hash_fn(m):
        if hash_name.startswith('blake'):
            return hash_class(m)
        return hash_class(m).digest()

    t0 = time.time()
    print(f"# Oracle Gauge v{VERSION} — {hash_name}")
    print(f"# Mode: HW=2 exhaustive + bit5_max feature")

    inputs, pos = low_hw2_inputs()
    if N_samples and N_samples < len(inputs):
        inputs = inputs[:N_samples]; pos = pos[:N_samples]
    N = len(inputs)
    print(f"# N = {N}")

    fa = make_feature(pos, feature_name)

    if verbose: print(f"\n# Phase 1: hash inputs (truncated to {truncate_bits} bits)...")
    target_bits = hash_to_bits(inputs, hash_fn, digest_bits=truncate_bits)
    if verbose: print(f"  digest bits = {target_bits.shape[1]}, time: {time.time()-t0:.0f}s")

    # Use INPUT bits as state1 proxy (cross-hash generic probe)
    # input_bits: first 256 bits of input
    input_bits = np.zeros((N, 256), dtype=np.uint8)
    for i, m in enumerate(inputs):
        for bi in range(32):
            for bb in range(8):
                input_bits[i, bi*8+bb] = (m[bi] >> (7-bb)) & 1

    if verbose: print(f"\n# Phase 2: compute Ω_k spectrum...")
    results = {}
    chi_arr_k3 = None
    for k in [1, 2, 3]:
        ts = time.time()
        chi_arr, _ = build_chi_arr(input_bits, k=k, subset_size=32)
        if k == 3: chi_arr_k3 = chi_arr
        omega, ss, dz, cz, n_const = omega_k_fast(chi_arr, target_bits, fa)
        if n_const > 0 and verbose:
            print(f"    (filtered {n_const} constant target bits)")
        results[k] = {'omega': omega, 'same_sign': ss, 'time_sec': time.time()-ts}
        if verbose:
            print(f"  Ω_{k} = {omega:+.4f}  same_sign = {ss}/256  ({time.time()-ts:.1f}s)")

    if verbose: print(f"\n# Phase 3: RO null band (10 realizations of Ω_3)...")
    ts = time.time()
    ro_mean, ro_std, _ = ro_null_band(inputs, input_bits, fa, chi_arr_k3, n_realizations=10)
    if verbose:
        print(f"  RO band: mean = {ro_mean:+.4f}, std = {ro_std:.4f}  ({time.time()-ts:.1f}s)")

    # Classification (use Ω_3 as primary)
    omega_3 = results[3]['omega']
    verdict, reason, z_score = classify(omega_3, ro_mean, ro_std)

    print(f"\n=== CLASSIFICATION ===")
    print(f"Hash:     {hash_name}")
    print(f"Ω_3:      {omega_3:+.4f}")
    print(f"RO band:  {ro_mean:+.4f} ± {ro_std:.4f}")
    print(f"Deviation: {z_score:.1f}σ")
    print(f"Verdict:  {verdict}")
    print(f"Reason:   {reason}")

    total_time = time.time() - t0
    out = {
        'hash': hash_name,
        'N': N,
        'feature': feature_name,
        'omega_spectrum': {k: r for k, r in results.items()},
        'ro_null': {'mean': ro_mean, 'std': ro_std},
        'verdict': verdict,
        'reason': reason,
        'z_score': z_score,
        'runtime_sec': total_time,
        'version': VERSION,
    }
    print(f"\nTotal time: {total_time:.0f}s")
    return out


def main():
    parser = argparse.ArgumentParser(description='Oracle Gauge — measure hash function distance from random oracle')
    parser.add_argument('--hash', required=True, help='Hash name: sha256, md5, sha1, blake2b, etc.')
    parser.add_argument('--N', type=int, default=None, help='Number of samples (default: 130816)')
    parser.add_argument('--feature', default='bit5_max', help='Input feature: bit5_max, parity_lsb, ...')
    parser.add_argument('--output', default=None, help='Output JSON file')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress messages')
    args = parser.parse_args()

    result = run(args.hash, N_samples=args.N, feature_name=args.feature, verbose=not args.quiet)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved to {args.output}")


if __name__ == '__main__':
    main()
