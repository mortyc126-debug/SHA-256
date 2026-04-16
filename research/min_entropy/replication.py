"""
IT-1.2: Replication test for the k=12 chi^2 hint observed in IT-1.1.

If SHA-256 has a systematic property of being more uniform than RO at k=12,
the z-score should reproduce across multiple SAME-SIZE input sets.
If it was noise, it will be uncorrelated.

Five input sets, all of size N = 130 816:
  A. low_hw_w2     (HW=2, all 130816 codewords)
  B. counter       (i = 0..130815, 8-byte BE)
  C. ascii_64      (random 64-byte ASCII strings)
  D. low_hw_w3_sub (random subsample of HW=3 codewords, |full|=22M)
  E. uniform_64    (random 64-byte uniform strings)

For each set we compute SHA-256 chi^2 at k=12 and compare to the RO band
(R=200 keyed-BLAKE2b realizations on the same set).
"""

import hashlib
import math
import json
import os
import time
from itertools import combinations
from collections import Counter

import numpy as np

import experiment as exp     # reuse generators

LENGTH_BITS = 512
N = 130816
K_LIST = [8, 12, 16, 20]
R = 200
SEED = 0x1FEEDFACE
OUT = os.path.join(os.path.dirname(__file__), 'replication_results.json')


def chi2_at_k(trunc24, k, N):
    shift = 24 - k
    buckets = trunc24 >> shift if shift > 0 else trunc24
    M = 1 << k
    counts = np.bincount(buckets, minlength=M)
    expected = N / M
    return float(((counts - expected) ** 2).sum() / expected)


def hash_set_sha256(inputs):
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = hashlib.sha256(x).digest()
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_set_keyed(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[i] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def gen_low_hw2():
    L = LENGTH_BITS // 8
    out = []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
    return out


def gen_counter():
    return [i.to_bytes(8, 'big') for i in range(N)]


def gen_ascii():
    import random
    r = random.Random(SEED ^ 0xA5C11)
    chars = bytes(range(0x20, 0x7F))
    return [bytes(r.choices(chars, k=64)) for _ in range(N)]


def gen_low_hw3_sub():
    """Random 130816 codewords from HW=3 space (size 22.3M)."""
    import random
    r = random.Random(SEED ^ 0x4E3)
    L = LENGTH_BITS // 8
    out = []
    seen = set()
    while len(out) < N:
        positions = tuple(sorted(r.sample(range(LENGTH_BITS), 3)))
        if positions in seen:
            continue
        seen.add(positions)
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
    return out


def gen_uniform():
    import random
    r = random.Random(SEED ^ 0xCAFE)
    return [r.randbytes(64) for _ in range(N)]


SET_GENERATORS = {
    'A_low_hw_w2':      gen_low_hw2,
    'B_counter':        gen_counter,
    'C_ascii':          gen_ascii,
    'D_low_hw_w3_sub':  gen_low_hw3_sub,
    'E_uniform':        gen_uniform,
}


def main():
    t_total = time.time()
    nprng = np.random.default_rng(SEED)
    results = {'meta': {'N': N, 'k_list': K_LIST, 'R': R, 'seed': SEED}, 'sets': {}}

    print(f"# IT-1.2: replication of k=12 chi^2 hint")
    print(f"# N={N}, R={R}")

    # generate one shared key list so all sets see the same RO realizations
    keys = [nprng.bytes(16) for _ in range(R)]

    for set_name, gen in SET_GENERATORS.items():
        print(f"\n## set {set_name}")
        t0 = time.time()
        inputs = gen()
        assert len(inputs) == N, (set_name, len(inputs))
        t_gen = time.time() - t0

        # SHA-256
        t0 = time.time()
        sha_trunc = hash_set_sha256(inputs)
        sha_chi2 = {k: chi2_at_k(sha_trunc, k, N) for k in K_LIST}
        t_sha = time.time() - t0

        # RO band (R realizations)
        t0 = time.time()
        ro_chi2 = {k: [] for k in K_LIST}
        for r, key in enumerate(keys):
            trunc = hash_set_keyed(inputs, key)
            for k in K_LIST:
                ro_chi2[k].append(chi2_at_k(trunc, k, N))
        t_ro = time.time() - t0

        set_result = {'gen_time': t_gen, 'sha_time': t_sha, 'ro_time': t_ro}
        for k in K_LIST:
            arr = np.asarray(ro_chi2[k])
            mean, std = float(arr.mean()), float(arr.std(ddof=1))
            sha_v = sha_chi2[k]
            z = (sha_v - mean) / std if std > 0 else 0.0
            dev_arr = np.abs(arr - mean)
            dev_sha = abs(sha_v - mean)
            p = float((dev_arr >= dev_sha).sum() + 1) / (R + 1)
            set_result[f'k={k}'] = {
                'sha_chi2': sha_v, 'ro_mean': mean, 'ro_std': std,
                'z': z, 'p_two_sided': p,
            }
            print(f"  k={k:2d}  sha={sha_v:>14.2f}  ro={mean:>14.2f}±{std:>8.2f}  "
                  f"z={z:+5.2f}  p={p:.3f}")
        results['sets'][set_name] = set_result

    # Summary table at k=12 (the suspect)
    print("\n" + "=" * 70)
    print("SUMMARY: z-score of SHA-256 vs RO at k=12 across input sets")
    print("=" * 70)
    print(f"{'set':<22} {'z @k=12':>10}  {'p':>6}")
    for set_name in SET_GENERATORS:
        r = results['sets'][set_name]['k=12']
        print(f"{set_name:<22} {r['z']:>+10.2f}  {r['p_two_sided']:>6.3f}")

    with open(OUT, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
