"""
IT-4 Stage 1: Walsh-Hadamard scan for linear structural information leak.

For each input feature f (a binary function of input parameters i, j) and
each output bit b of SHA-256(x) ↾ k, compute Walsh correlation:

    W(f, b) = (1/N) Σ_x (-1)^(f(x) ⊕ b(SHA(x)))

Under H_0 (RO model): W ~ N(0, 1/N), so z = W · √N ~ N(0, 1).

Detection threshold:
    Per-cell 5σ:    |z| > 5    ↔  |W| > 5/√N ≈ 0.0138 (for N=130816)
    Bonferroni for F_features × K_out_bits cells: |z| > Φ⁻¹(1 − α/(2FK))

Feature set (binary functions of (i, j) where 0 ≤ i < j < 512):
    1. Single bits:   bit_b(i), bit_b(j)                 [9 + 9 = 18]
    2. XOR bits:      bit_b(i ⊕ j)                       [9]
    3. Sum bits:      bit_b((i + j) mod 2^9)             [9]
    4. AND bits:      bit_b(i ∧ j)                       [9]
    5. OR bits:       bit_b(i ∨ j)                       [9]
    6. Parity bits of small chunks                       [4]
    7. HW(i) parity, HW(j) parity, HW(i⊕j) parity        [3]
    Total: ~60 features (after dedup)

Output bits: high 24 bits of SHA-256, indexed b ∈ [0, 24).
We test multiple k by examining different bit positions.

Comparison strategy:
    Primary: each cell is z ~ N(0, 1) under H_0. We can test analytically
    without RO simulation. But we ALSO simulate R = 100 RO realizations
    (keyed BLAKE2b) to validate that the analytic distribution is correct
    and detect any unaccounted noise.
"""

import hashlib
import math
import json
import os
import time
from itertools import combinations

import numpy as np


LENGTH_BITS = 512
N_OUT_BITS = 24
SEED = 0xCAB00D1E
R_RO = 100
OUT = os.path.join(os.path.dirname(__file__), 'it4_walsh.json')


def enumerate_low_hw2():
    out = []
    pairs_i, pairs_j = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(64)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
        pairs_i.append(positions[0])
        pairs_j.append(positions[1])
    return out, np.asarray(pairs_i, dtype=np.int64), np.asarray(pairs_j, dtype=np.int64)


def build_features(i, j):
    """Return dict feature_name -> binary array of shape (N,)."""
    feats = {}
    for b in range(9):
        feats[f'bit{b}_i']     = ((i >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_j']     = ((j >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_ixorj'] = (((i ^ j) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_sum']   = ((((i + j) & 0x1FF) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_iandj'] = (((i & j) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_iorj']  = (((i | j) >> b) & 1).astype(np.uint8)

    # parity of HW
    hw = np.asarray([bin(v).count('1') & 1 for v in range(512)], dtype=np.uint8)
    feats['parity_HWi']      = hw[i]
    feats['parity_HWj']      = hw[j]
    feats['parity_HW_ixorj'] = hw[i ^ j]

    # parity bits of larger chunks
    feats['parity_low4_i'] = (np.bitwise_count(i & 0xF) & 1).astype(np.uint8) \
        if hasattr(np, 'bitwise_count') else np.asarray([bin(v & 0xF).count('1') & 1 for v in i], dtype=np.uint8)
    feats['parity_high5_j'] = np.asarray([bin((v >> 4) & 0x1F).count('1') & 1 for v in j], dtype=np.uint8)

    # Some non-linear combinations
    feats['bit0_i_AND_bit0_j'] = (((i & 1) & (j & 1)) & 1).astype(np.uint8)
    feats['bit3_i_AND_bit3_j'] = ((((i >> 3) & 1) & ((j >> 3) & 1)) & 1).astype(np.uint8)
    feats['bit0_i_AND_bit5_j'] = (((i & 1) & ((j >> 5) & 1)) & 1).astype(np.uint8)

    # gap parity
    feats['parity_gap'] = ((j - i) & 1).astype(np.uint8)
    feats['parity_HW_gap'] = np.asarray([bin(int(v)).count('1') & 1 for v in (j - i)], dtype=np.uint8)

    return feats


def hash_set_sha256(inputs):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.sha256(x).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_set_keyed_blake(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def output_bits(trunc24, n_bits=N_OUT_BITS):
    """Return list of binary arrays for each output bit (MSB-first)."""
    return [((trunc24 >> (N_OUT_BITS - 1 - b)) & 1).astype(np.uint8)
            for b in range(n_bits)]


def walsh_z(features, out_bits):
    """
    Compute z-score matrix [F × B], where z[f,b] = sqrt(N) * mean((-1)^(f ⊕ b)).
    """
    N = len(out_bits[0])
    fnames = list(features)
    F = len(fnames)
    B = len(out_bits)
    Z = np.zeros((F, B))
    sqrtN = math.sqrt(N)
    for fi, fn in enumerate(fnames):
        f_arr = features[fn]
        for bi, b_arr in enumerate(out_bits):
            # (-1)^(f ⊕ b) → +1 when f==b, -1 when f!=b
            equal = (f_arr == b_arr)
            mean_signed = (2.0 * equal.sum() - N) / N
            Z[fi, bi] = mean_signed * sqrtN
    return fnames, Z


def main():
    t0 = time.time()
    print("# IT-4 Stage 1: Walsh-Hadamard scan for SHA-256 linear leak")
    inputs, i_arr, j_arr = enumerate_low_hw2()
    N = len(inputs)
    print(f"# N = {N}")

    feats = build_features(i_arr, j_arr)
    F = len(feats)
    print(f"# Features: {F}")

    print("# Hashing with SHA-256...")
    sha_trunc = hash_set_sha256(inputs)
    sha_obits = output_bits(sha_trunc, N_OUT_BITS)

    print("# Computing Walsh z-scores for SHA-256...")
    fnames, Z_sha = walsh_z(feats, sha_obits)
    print(f"  Z_sha shape = {Z_sha.shape}")

    # Statistical thresholds
    n_tests = F * N_OUT_BITS
    from scipy.stats import norm
    bonferroni_alpha = 0.05 / n_tests
    bonf_z = float(norm.isf(bonferroni_alpha / 2))
    print(f"# Tests: {n_tests}, Bonferroni 5%-corrected |z| threshold: {bonf_z:.3f}")

    # ------------------------------------------------------------------
    # Top |z| cells (SHA-256)
    # ------------------------------------------------------------------
    flat = [(abs(Z_sha[fi, bi]), Z_sha[fi, bi], fnames[fi], bi)
            for fi in range(F) for bi in range(N_OUT_BITS)]
    flat.sort(reverse=True)
    print("\n## Top 25 |z| cells, SHA-256:")
    print(f"{'rank':>4}  {'feature':<22}  {'out_bit':>7}  {'z':>8}  {'|z|≥Bonf?':>10}")
    for r, (azv, zv, fn, bi) in enumerate(flat[:25], 1):
        flag = ' YES' if azv >= bonf_z else ''
        print(f"{r:>4}  {fn:<22}  {bi:>7}  {zv:>+8.3f}  {flag:>10}")

    # ------------------------------------------------------------------
    # Distribution of |z| under H_0 (RO simulation)
    # ------------------------------------------------------------------
    print(f"\n# Validating null with R={R_RO} keyed-BLAKE2b realizations...")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_max_abs_z = []
    ro_z_samples = []
    t1 = time.time()
    for r, key in enumerate(keys):
        trunc = hash_set_keyed_blake(inputs, key)
        obits = output_bits(trunc, N_OUT_BITS)
        _, Z_ro = walsh_z(feats, obits)
        ro_max_abs_z.append(float(np.abs(Z_ro).max()))
        # save a flat sample of all z's for distribution check
        ro_z_samples.extend(Z_ro.flatten().tolist())
        if (r + 1) % 20 == 0:
            print(f"  r={r+1:3d}/{R_RO}  elapsed={time.time()-t1:.1f}s")

    ro_max_abs_z = np.asarray(ro_max_abs_z)
    ro_z_samples = np.asarray(ro_z_samples)

    # SHA-256 max |z|
    sha_max_abs = float(np.abs(Z_sha).max())
    # empirical p-value: how often does RO max |z| exceed SHA's?
    p_max = float((ro_max_abs_z >= sha_max_abs).sum() + 1) / (R_RO + 1)

    print(f"\n## Max |z| comparison")
    print(f"  SHA-256 max |z| over {n_tests} cells: {sha_max_abs:.3f}")
    print(f"  RO max |z| distribution (R={R_RO}): "
          f"mean={ro_max_abs_z.mean():.3f}  std={ro_max_abs_z.std(ddof=1):.3f}  "
          f"q95={np.quantile(ro_max_abs_z, 0.95):.3f}  q99={np.quantile(ro_max_abs_z, 0.99):.3f}")
    print(f"  P(RO_max ≥ SHA_max) = {p_max:.4f}")
    print(f"  RO z-sample marginal stats: mean={ro_z_samples.mean():.4f}  "
          f"std={ro_z_samples.std(ddof=1):.4f}  (expected mean=0, std=1)")

    # ------------------------------------------------------------------
    # Per-feature aggregate: sum of z² across output bits
    # ------------------------------------------------------------------
    sum_z2_sha = (Z_sha ** 2).sum(axis=1)
    print(f"\n## Top 15 features by Σ z² across output bits")
    feat_order = np.argsort(-sum_z2_sha)
    print(f"{'rank':>4}  {'feature':<22}  {'Σz²_sha':>10}  {'expected':>10}")
    for r, fi in enumerate(feat_order[:15], 1):
        print(f"{r:>4}  {fnames[fi]:<22}  {sum_z2_sha[fi]:>10.3f}  {N_OUT_BITS:>10.3f}")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    out = {
        'meta': {'N': N, 'F': F, 'B': N_OUT_BITS, 'R_RO': R_RO,
                 'bonferroni_z_thresh': bonf_z, 'n_tests': n_tests},
        'feature_names': fnames,
        'Z_sha': Z_sha.tolist(),
        'sha_max_abs_z': sha_max_abs,
        'ro_max_abs_z': ro_max_abs_z.tolist(),
        'ro_z_marginal_mean': float(ro_z_samples.mean()),
        'ro_z_marginal_std': float(ro_z_samples.std(ddof=1)),
        'p_max': p_max,
        'sum_z2_sha': sum_z2_sha.tolist(),
        'top_cells': [{'feature': fn, 'out_bit': bi, 'z': zv}
                      for _, zv, fn, bi in flat[:25]],
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t0:.1f}s")


if __name__ == '__main__':
    main()
