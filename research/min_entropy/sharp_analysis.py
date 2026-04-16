"""
IT-1.1: Sharp analysis of SHA-256 on low-Hamming-weight inputs.

Replaces the coarse t-test with a full distributional fingerprint
against the analytical random-oracle null:

  H0 (RO):  for any fixed input set S of size |S|, the truncated
            output (bucket index) is Multinomial(|S|, 1/M, …, 1/M).
            Statistics computed from the count vector follow known
            sampling distributions; we estimate them empirically by
            R independent random-oracle realizations (keyed BLAKE2b
            with fresh random salt per realization).

For each k ∈ K_LIST we compute on the count vector:
  - max, min, median
  - chi^2  =  Σ (c_i − N/M)² / (N/M)
  - KL(p_emp ‖ uniform) =  Σ (c_i/N) log( (c_i/N) / (1/M) )
  - Hellinger =  ½ Σ ( √(c_i/N) − √(1/M) )²
  - TV =  ½ Σ |c_i/N − 1/M|
  - H_2 (Renyi-2) and H_inf
  - Tsallis_α=3  =  (1 − Σ p_i^3) / 2   (sensitive to medium-mass tail)

Everything is enumerated exhaustively over the 130 816 inputs (no
sampling), so noise from the input distribution is exactly zero.

Reference null is the empirical distribution of the same statistics
under R = 200 keyed-BLAKE2b realizations.

Output: results.json with the SHA-256 statistic, BLAKE2b statistic,
and the empirical RO-band (mean, std, 2.5%, 97.5%, p-value of SHA-256).
"""

import hashlib
import math
import json
import os
import time
from collections import Counter
from itertools import combinations

import numpy as np

LENGTH_BITS = 512
WEIGHT = 2
K_LIST = [8, 12, 16, 18, 20, 22]
R_REALIZATIONS = 200
SEED = 0xD15EA5E

OUT_PATH = os.path.join(os.path.dirname(__file__), 'sharp_results.json')


# ---------------------------------------------------------------------------
# Input enumeration
# ---------------------------------------------------------------------------

def enumerate_low_hw():
    """All 512-bit byte strings with exactly WEIGHT bits set."""
    L = LENGTH_BITS // 8
    inputs = []
    for positions in combinations(range(LENGTH_BITS), WEIGHT):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
    return inputs


# ---------------------------------------------------------------------------
# Hash + truncation
# ---------------------------------------------------------------------------

def hash_all(inputs, hash_constructor):
    """Return a numpy array of 24-bit truncations (uint32) of digest."""
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = hash_constructor(x).digest()
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_all_keyed(inputs, key):
    """BLAKE2b(key=salt) over inputs → 24-bit truncations."""
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


# ---------------------------------------------------------------------------
# Statistics on count vector (numpy, for speed)
# ---------------------------------------------------------------------------

def stats_from_truncations(trunc24, k, N):
    """Compute statistic vector from 24-bit truncations down to k bits."""
    shift = 24 - k
    if shift > 0:
        buckets = trunc24 >> shift
    else:
        buckets = trunc24
    M = 1 << k
    # bincount up to M
    counts = np.bincount(buckets, minlength=M)
    # statistics
    nz = counts[counts > 0]
    p = counts.astype(np.float64) / N
    p_unif = 1.0 / M

    max_c = int(counts.max())
    min_c = int(counts.min())
    median_c = float(np.median(counts))
    num_distinct = int((counts > 0).sum())

    expected = N / M
    # chi^2 (Pearson)
    chi2 = float(((counts - expected) ** 2).sum() / expected)

    # KL(p || uniform); for p_i = 0 contribution is 0
    p_nz = nz.astype(np.float64) / N
    kl = float((p_nz * np.log(p_nz / p_unif)).sum() / math.log(2))   # in bits

    # Hellinger
    hell = 0.5 * float(((np.sqrt(p) - math.sqrt(p_unif)) ** 2).sum())

    # TV
    tv = 0.5 * float(np.abs(p - p_unif).sum())

    # H_2  (Renyi-2)
    p2 = float((p ** 2).sum())
    H_2 = -math.log2(p2)

    # H_inf
    H_inf = -math.log2(max_c / N) if max_c > 0 else float('inf')

    # Tsallis alpha=3
    p3 = float((p ** 3).sum())
    tsallis3 = (1.0 - p3) / 2.0

    return {
        'max': max_c, 'min': min_c, 'median': median_c,
        'num_distinct': num_distinct,
        'chi2': chi2, 'kl': kl, 'hellinger': hell, 'tv': tv,
        'H_2': H_2, 'H_inf': H_inf, 'tsallis3': tsallis3,
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_total = time.time()

    print("# IT-1.1: sharp distributional analysis on low_hw_w2")
    print(f"# Enumerating all 512-bit inputs of HW={WEIGHT}...")
    inputs = enumerate_low_hw()
    N = len(inputs)
    print(f"# |S| = {N}  (= C(512,{WEIGHT}))")

    # ------------------------------------------------------------------
    # 1. SHA-256 statistic (exact, single-shot)
    # ------------------------------------------------------------------
    t0 = time.time()
    sha256_trunc = hash_all(inputs, hashlib.sha256)
    print(f"# SHA-256: {time.time()-t0:.1f}s")
    sha256_stats = {k: stats_from_truncations(sha256_trunc, k, N) for k in K_LIST}

    # ------------------------------------------------------------------
    # 2. BLAKE2b reference (single-shot, default no-key)
    # ------------------------------------------------------------------
    t0 = time.time()
    blake2_trunc = hash_all(inputs, hashlib.blake2b)
    print(f"# BLAKE2b: {time.time()-t0:.1f}s")
    blake2_stats = {k: stats_from_truncations(blake2_trunc, k, N) for k in K_LIST}

    # ------------------------------------------------------------------
    # 3. Random-oracle null: R realizations of keyed BLAKE2b.
    #    Stream stats incrementally to disk so a crash doesn't lose work.
    # ------------------------------------------------------------------
    rng = np.random.default_rng(SEED)
    ro_stats = {k: {stat: [] for stat in sha256_stats[K_LIST[0]]} for k in K_LIST}

    print(f"# RO simulation: R = {R_REALIZATIONS} realizations")
    t_ro = time.time()
    for r in range(R_REALIZATIONS):
        key = rng.bytes(16)
        trunc = hash_all_keyed(inputs, key)
        for k in K_LIST:
            s = stats_from_truncations(trunc, k, N)
            for name, v in s.items():
                ro_stats[k][name].append(v)
        if (r + 1) % 25 == 0:
            elapsed = time.time() - t_ro
            print(f"  r={r+1:3d}/{R_REALIZATIONS}  elapsed={elapsed:.1f}s  "
                  f"eta={elapsed/(r+1)*(R_REALIZATIONS-r-1):.1f}s")
            # checkpoint
            _save_checkpoint(sha256_stats, blake2_stats, ro_stats, r + 1)

    # ------------------------------------------------------------------
    # 4. Build report: for each (k, stat) compute empirical p-value
    # ------------------------------------------------------------------
    report = {
        'meta': {
            'length_bits': LENGTH_BITS, 'weight': WEIGHT,
            'N_inputs': N, 'k_list': K_LIST,
            'R_realizations': R_REALIZATIONS, 'seed': SEED,
        },
        'sha256': sha256_stats,
        'blake2b': blake2_stats,
        'ro_band': {},
    }

    for k in K_LIST:
        report['ro_band'][k] = {}
        for stat in sha256_stats[k]:
            arr = np.asarray(ro_stats[k][stat], dtype=np.float64)
            sha_v = sha256_stats[k][stat]
            blake_v = blake2_stats[k][stat]
            mean = float(arr.mean())
            std = float(arr.std(ddof=1))
            q025 = float(np.quantile(arr, 0.025))
            q975 = float(np.quantile(arr, 0.975))
            # two-sided empirical p-value (rank of |sha_v - mean| in |arr - mean|)
            dev_arr = np.abs(arr - mean)
            dev_sha = abs(sha_v - mean)
            p_value = float((dev_arr >= dev_sha).sum() + 1) / (R_REALIZATIONS + 1)
            # z-score (for normal-approx interpretation)
            z = (sha_v - mean) / std if std > 0 else 0.0
            report['ro_band'][k][stat] = {
                'sha256': sha_v,
                'blake2b': blake_v,
                'ro_mean': mean, 'ro_std': std,
                'ro_q025': q025, 'ro_q975': q975,
                'z': z, 'p_two_sided': p_value,
            }

    with open(OUT_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    # pretty-print key findings
    print()
    print(f"{'k':>3} {'stat':<12} {'sha256':>14} {'ro_mean':>14} {'ro_std':>10} "
          f"{'z':>7} {'p':>7} {'flag':>5}")
    print('-' * 90)
    for k in K_LIST:
        for stat in ['max', 'chi2', 'kl', 'tv', 'H_inf']:
            r = report['ro_band'][k][stat]
            flag = ''
            if r['p_two_sided'] < 0.01:   flag = '**'
            elif r['p_two_sided'] < 0.05: flag = '*'
            sval = r['sha256']
            sval_s = f"{sval:14.6f}" if isinstance(sval, float) else f"{sval:14d}"
            print(f"{k:>3} {stat:<12} {sval_s} {r['ro_mean']:14.6f} "
                  f"{r['ro_std']:10.6f} {r['z']:+7.2f} {r['p_two_sided']:7.4f} {flag:>5}")
        print()

    print(f"Wrote {OUT_PATH}")
    print(f"Total time: {time.time() - t_total:.1f}s")


def _save_checkpoint(sha256_stats, blake2_stats, ro_stats, r_done):
    cp = {
        'r_done': r_done,
        'sha256_stats': sha256_stats,
        'blake2b_stats': blake2_stats,
        'ro_stats': ro_stats,
    }
    cp_path = OUT_PATH + '.checkpoint'
    with open(cp_path, 'w') as f:
        json.dump(cp, f)


if __name__ == '__main__':
    main()
