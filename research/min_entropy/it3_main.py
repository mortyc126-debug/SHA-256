"""
IT-3 Stage 2: measure Structural Information Excess Δ(h, f, k) for all
seven hashes from IT-1.3 across multiple structural features and
truncation lengths.

Reuses estimator from it3_estimator.py (already validated).
Reuses input set: exhaustive low_hw_w2.

Pipeline
--------
1. Enumerate all C(512, 2) = 130 816 inputs.
2. For each input compute structural features f_1, ..., f_F (small K_f).
3. For each h ∈ HASHES compute Y_h^k (truncated output) for k ∈ K_LIST.
4. For each (h, f, k) compute Î_plug(f; Y_h^k).
5. RO null: R independent keyed-BLAKE2b realizations →
   {Î_RO(f; Y^k)}_{r=1..R}. Mean and std define the null band.
6. Δ_h(f, k) = Î_h - mean(Î_RO).  z = Δ / std(Î_RO).
7. Detection threshold quantified per (f, k) cell — never silently
   declare "no signal".

We do NOT do multiple-comparison correction in the table itself; raw
z-scores are reported with the explicit warning that we run F × K × H
tests.
"""

import hashlib
import math
import json
import os
import time
from itertools import combinations

import numpy as np

from it3_estimator import mi_plugin

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

LENGTH_BITS = 512
K_LIST = [8, 10, 12, 14]
R = 200
SEED = 0xDEC0DE
OUT = os.path.join(os.path.dirname(__file__), 'it3_results.json')

HASHES = {
    'sha256':   lambda x: hashlib.sha256(x).digest(),
    'sha512':   lambda x: hashlib.sha512(x).digest(),
    'sha3_256': lambda x: hashlib.sha3_256(x).digest(),
    'blake2b':  lambda x: hashlib.blake2b(x).digest(),
    'blake2s':  lambda x: hashlib.blake2s(x).digest(),
    'md5':      lambda x: hashlib.md5(x).digest(),
    'sha1':     lambda x: hashlib.sha1(x).digest(),
}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def enumerate_low_hw2():
    """All 512-bit byte strings with exactly 2 bits set, plus parameter pairs."""
    L = LENGTH_BITS // 8
    inputs = []
    pairs = []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pairs.append(positions)
    return inputs, np.asarray(pairs, dtype=np.int64)   # shape (N, 2)


# ---------------------------------------------------------------------------
# Structural features (each returns int array of shape (N,))
# ---------------------------------------------------------------------------

def compute_features(pairs):
    """pairs: (N, 2) int array of (i, j), i < j, 0 ≤ i < j < 512.
    Returns dict feature_name → (int_array, K_f)."""
    i = pairs[:, 0]
    j = pairs[:, 1]
    feats = {}

    # f1: (i + j) mod 16
    feats['sum_mod16'] = ((i + j) & 0xF, 16)
    # f2: gap j - i bucketed in 16 bins of width 32
    feats['gap_div32'] = ((j - i) // 32, 16)
    # f3: (i mod 8, j mod 8) flattened
    feats['imod8_jmod8'] = ((i & 7) * 8 + (j & 7), 64)
    # f4: i // 32 (which 32-bit word for lower position)
    feats['iword'] = (i // 32, 16)
    # f5: i mod 32 (within-word position)
    feats['imod32'] = (i & 31, 32)
    # f6: j // 32
    feats['jword'] = (j // 32, 16)
    # f7: HW(i) (Hamming weight of 9-bit position index)
    hw_table = np.asarray([bin(v).count('1') for v in range(512)], dtype=np.int64)
    feats['HWi'] = (hw_table[i], 10)        # K=10 covers 0..9
    # f8: i XOR j popcount (distance between positions in bit terms)
    feats['popxor_ij'] = (hw_table[i ^ j], 10)
    return feats


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def hash_set(inputs, fn):
    """Apply hash fn to each input, return uint32 array of first 24 bits."""
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = fn(x)
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_set_keyed_blake(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def buckets_at_k(trunc24, k):
    shift = 24 - k
    if shift > 0:
        return (trunc24 >> shift).astype(np.int64)
    return trunc24.astype(np.int64)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_total = time.time()
    print("# IT-3 Stage 2: structural information excess Δ(h, f, k)")

    print("# Enumerating low_hw_w2 inputs...")
    inputs, pairs = enumerate_low_hw2()
    N = len(inputs)
    print(f"# N = {N}")

    print("# Computing structural features...")
    feats = compute_features(pairs)
    for name, (arr, K_f) in feats.items():
        max_seen = int(arr.max()) + 1
        nonempty = len(np.unique(arr))
        print(f"  {name:<14}: K_declared={K_f:>3}, K_actual={nonempty:>3}")

    # ----------------------------------------------------------------------
    # 1. Hash all inputs once per real hash
    # ----------------------------------------------------------------------
    print("\n# Hashing inputs with each real hash...")
    real_truncs = {}
    for hname, fn in HASHES.items():
        t0 = time.time()
        real_truncs[hname] = hash_set(inputs, fn)
        print(f"  {hname:<10}: {time.time()-t0:.2f}s")

    # ----------------------------------------------------------------------
    # 2. RO null: R realizations of keyed BLAKE2b
    #    For each, compute I(f; Y_RO) for all (f, k) and store
    # ----------------------------------------------------------------------
    print(f"\n# RO null: R = {R} keyed-BLAKE2b realizations")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]

    # ro_I[k][f] = list of length R, each entry I_plug for that realization
    ro_I = {k: {fname: [] for fname in feats} for k in K_LIST}

    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = hash_set_keyed_blake(inputs, key)
        for k in K_LIST:
            buckets = buckets_at_k(trunc, k)
            for fname, (f_arr, _) in feats.items():
                I_plug, _, *_ = mi_plugin(f_arr, buckets)
                ro_I[k][fname].append(I_plug)
        if (r + 1) % 25 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (r + 1) * (R - r - 1)
            print(f"  r={r+1:3d}/{R}  elapsed={elapsed:.1f}s  eta={eta:.1f}s")

    # convert to numpy
    for k in K_LIST:
        for fname in feats:
            ro_I[k][fname] = np.asarray(ro_I[k][fname])

    # ----------------------------------------------------------------------
    # 3. Real-hash MI and z-scores
    # ----------------------------------------------------------------------
    print("\n# Computing Δ and z for each (hash, feature, k)")
    z_table = {}    # z_table[hash][k][feature] = dict
    for hname, trunc in real_truncs.items():
        z_table[hname] = {}
        for k in K_LIST:
            z_table[hname][k] = {}
            buckets = buckets_at_k(trunc, k)
            for fname, (f_arr, K_f) in feats.items():
                I_plug, I_MM, _, _, K_fy, bias = mi_plugin(f_arr, buckets)
                arr = ro_I[k][fname]
                ro_mean = float(arr.mean())
                ro_std = float(arr.std(ddof=1))
                delta = I_plug - ro_mean
                z = delta / ro_std if ro_std > 0 else 0.0
                # empirical two-sided p-value
                dev_arr = np.abs(arr - ro_mean)
                p_two = float((dev_arr >= abs(delta)).sum() + 1) / (R + 1)
                z_table[hname][k][fname] = {
                    'I_plug': I_plug, 'I_MM': I_MM,
                    'ro_mean': ro_mean, 'ro_std': ro_std,
                    'delta_bits': delta, 'z': z, 'p_two': p_two,
                    'K_fy': K_fy, 'bias_bits': bias,
                }

    # ----------------------------------------------------------------------
    # 4. Heatmap-style printout per k
    # ----------------------------------------------------------------------
    feat_names = list(feats.keys())
    for k in K_LIST:
        print(f"\n## z-scores at k = {k}  (RO std for context per row right)")
        print(f"{'hash':<10}  " + "  ".join(f"{n[:9]:>9}" for n in feat_names)
              + "  | RO_std_med")
        print('-' * (12 + 11 * len(feat_names) + 14))
        ro_stds = [float(np.median([z_table[h][k][fn]['ro_std'] for fn in feat_names]))
                   for h in HASHES]   # informational
        for hname in HASHES:
            zs = [z_table[hname][k][fn]['z'] for fn in feat_names]
            zstr = "  ".join(f"{z:+9.2f}" for z in zs)
            std_med = np.median([z_table[hname][k][fn]['ro_std'] for fn in feat_names])
            print(f"{hname:<10}  {zstr}  |  {std_med:.2e}")

    # ----------------------------------------------------------------------
    # 5. Detection-threshold report (resolution per cell)
    # ----------------------------------------------------------------------
    print("\n## Detection thresholds (5σ on Δ in bits)")
    print(f"{'feature':<14}  " + "  ".join(f"k={k:>2}" for k in K_LIST))
    for fname in feat_names:
        thresholds = []
        for k in K_LIST:
            stds = [z_table[hname][k][fname]['ro_std'] for hname in HASHES]
            thresholds.append(5 * float(np.median(stds)))
        tstr = "  ".join(f"{t:.2e}" for t in thresholds)
        print(f"{fname:<14}  {tstr}")

    # ----------------------------------------------------------------------
    # 6. Aggregate signs per hash (sign-test summary across all f × k cells)
    # ----------------------------------------------------------------------
    print("\n## Sign summary across all (f, k) cells:")
    print(f"{'hash':<10}  {'n_pos':>6} {'n_neg':>6}  {'sum_z':>9}  "
          f"{'mean_z':>8}  {'sign_p':>8}")
    from scipy.stats import binomtest
    for hname in HASHES:
        zs = [z_table[hname][k][fn]['z']
              for k in K_LIST for fn in feat_names]
        n_pos = sum(1 for z in zs if z > 0)
        n_neg = sum(1 for z in zs if z < 0)
        s = sum(zs)
        m = s / len(zs)
        bt = binomtest(min(n_pos, n_neg), len(zs), p=0.5, alternative='two-sided')
        print(f"{hname:<10}  {n_pos:>6} {n_neg:>6}  {s:>+9.2f}  {m:>+8.3f}  "
              f"{bt.pvalue:>8.4f}")

    # ----------------------------------------------------------------------
    # Save full results
    # ----------------------------------------------------------------------
    out = {
        'meta': {
            'N': N, 'k_list': K_LIST, 'R': R, 'seed': SEED,
            'features': {fn: int(K) for fn, (_, K) in feats.items()},
        },
        'z_table': {h: {str(k): {fn: z_table[h][k][fn] for fn in feat_names}
                        for k in K_LIST} for h in HASHES},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
