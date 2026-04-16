"""
IT-1.3: Critical control test.

The k=12 chi^2 dip (sha256 below RO band) replicates across input sets,
but ONLY at k=12 and ONLY for SHA-256 vs keyed-BLAKE2b RO.

Two competing explanations:
  H_A: SHA-256 has a real micro-property of being more uniform at k=12.
  H_B: The dip is an artifact of comparing ANY deterministic standard
       hash against keyed-BLAKE2b realizations.

Discriminator: test seven standard hashes (SHA-256, SHA-512, SHA3-256,
BLAKE2b, BLAKE2s, MD5, SHA-1) at k=12 on set A (low_hw_w2). If all
seven show similar negative z, H_B wins. If only SHA-256 shows the dip,
H_A wins.

Also: scan k ∈ {8, 9, 10, 11, 12, 13, 14, 15, 16} to localize the
anomaly precisely, and compute it for ALL seven hashes. This produces
a (k, hash) heatmap of z-scores.
"""

import hashlib
import math
import json
import os
import time
from itertools import combinations
from collections import Counter

import numpy as np

LENGTH_BITS = 512
WEIGHT = 2
K_LIST = list(range(8, 17))    # 8..16 inclusive
R = 200
SEED = 0xFA571DEA
OUT = os.path.join(os.path.dirname(__file__), 'cross_hash_k12_results.json')

HASHES = {
    'sha256':   lambda x: hashlib.sha256(x).digest(),
    'sha512':   lambda x: hashlib.sha512(x).digest(),
    'sha3_256': lambda x: hashlib.sha3_256(x).digest(),
    'blake2b':  lambda x: hashlib.blake2b(x).digest(),
    'blake2s':  lambda x: hashlib.blake2s(x).digest(),
    'md5':      lambda x: hashlib.md5(x).digest(),
    'sha1':     lambda x: hashlib.sha1(x).digest(),
}


def gen_low_hw2():
    L = LENGTH_BITS // 8
    out = []
    for positions in combinations(range(LENGTH_BITS), WEIGHT):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
    return out


def chi2_at_k(trunc24, k, N):
    shift = 24 - k
    buckets = trunc24 >> shift if shift > 0 else trunc24
    M = 1 << k
    counts = np.bincount(buckets, minlength=M)
    expected = N / M
    return float(((counts - expected) ** 2).sum() / expected)


def hash_set(inputs, fn):
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = fn(x)
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_set_keyed_blake(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def main():
    t_total = time.time()
    print("# IT-1.3: cross-hash k-scan on low_hw_w2")
    inputs = gen_low_hw2()
    N = len(inputs)
    print(f"# N = {N}, K = {K_LIST}, R = {R}")

    # 1. Compute each hash, single shot, all at once (1 pass, 24-bit truncation)
    hash_truncs = {}
    for name, fn in HASHES.items():
        t0 = time.time()
        hash_truncs[name] = hash_set(inputs, fn)
        print(f"  {name:<10}: {time.time()-t0:.2f}s")

    # 2. RO band: R realizations of keyed BLAKE2b
    print(f"\n# RO simulation: R={R} realizations of keyed BLAKE2b")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro_chi2 = {k: [] for k in K_LIST}
    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = hash_set_keyed_blake(inputs, key)
        for k in K_LIST:
            ro_chi2[k].append(chi2_at_k(trunc, k, N))
        if (r + 1) % 50 == 0:
            print(f"  r={r+1:3d}/{R}  elapsed={time.time()-t0:.1f}s")

    # 3. Build z-score table
    z_table = {}    # z_table[hash_name][k] = z-score
    for hname, trunc in hash_truncs.items():
        z_table[hname] = {}
        for k in K_LIST:
            arr = np.asarray(ro_chi2[k])
            mean, std = float(arr.mean()), float(arr.std(ddof=1))
            v = chi2_at_k(trunc, k, N)
            z = (v - mean) / std
            z_table[hname][k] = {
                'chi2': v, 'z': z,
                'ro_mean': mean, 'ro_std': std,
            }

    # Pretty heatmap
    print(f"\n{'hash':<10}  " + "  ".join(f"k={k:>2}" for k in K_LIST))
    print('-' * (12 + 7 * len(K_LIST)))
    for hname in HASHES:
        row = [f"{z_table[hname][k]['z']:+5.2f}" for k in K_LIST]
        print(f"{hname:<10}  " + "  ".join(row))

    # Also show RO band stats per k
    print("\nRO band (chi^2 mean ± std):")
    for k in K_LIST:
        arr = np.asarray(ro_chi2[k])
        print(f"  k={k:2d}: {arr.mean():>14.2f} ± {arr.std(ddof=1):>10.2f}")

    # Save
    out = {
        'meta': {'N': N, 'k_list': K_LIST, 'R': R, 'seed': SEED},
        'z_table': z_table,
        'ro_band': {k: {
            'mean': float(np.mean(ro_chi2[k])),
            'std': float(np.std(ro_chi2[k], ddof=1)),
            'q025': float(np.quantile(ro_chi2[k], 0.025)),
            'q975': float(np.quantile(ro_chi2[k], 0.975)),
        } for k in K_LIST},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
