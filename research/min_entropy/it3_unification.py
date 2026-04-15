"""
IT-3 Stage 3: unification check.

The crucial claim of IT-3 is that the marginal-uniformity excess of
SHA-2 (Δ_χ² < 0 from IT-1.3) is NOT accompanied by a structural-MI
excess (Δ_I ≈ 0 from IT-3 Stage 2).

To prove this is a real dissociation and not an artifact of comparing
different RO simulations, we compute BOTH metrics on the SAME 200 RO
realizations, plus the same SHA-256 single-shot.

Output: z_χ² and z_I (per feature) on identical RO band, k = 12, low_hw_w2.
If z_χ² ≈ -2.5 and z_I ≈ 0 ± 1 across all features → confirmed.
"""
import hashlib, math, json, os, time
from itertools import combinations
import numpy as np
from it3_estimator import mi_plugin

LENGTH_BITS = 512
K = 12
R = 1000           # ↑ increased to tighten resolution
SEED = 0xCAFEBABE
OUT = os.path.join(os.path.dirname(__file__), 'it3_unification.json')


def enumerate_low_hw2():
    out, pairs = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(64)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
        pairs.append(positions)
    return out, np.asarray(pairs, dtype=np.int64)


def compute_features(pairs):
    i, j = pairs[:, 0], pairs[:, 1]
    hw = np.asarray([bin(v).count('1') for v in range(512)], dtype=np.int64)
    return {
        'sum_mod16':    ((i + j) & 0xF, 16),
        'gap_div32':    ((j - i) // 32, 16),
        'imod8_jmod8':  ((i & 7) * 8 + (j & 7), 64),
        'iword':        (i // 32, 16),
        'imod32':       (i & 31, 32),
        'jword':        (j // 32, 16),
        'HWi':          (hw[i], 10),
        'popxor_ij':    (hw[i ^ j], 10),
    }


def hash_set_sha256(inputs):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.sha256(x).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def hash_set_keyed(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def chi2_at_k(trunc, k, N):
    shift = 24 - k
    buckets = trunc >> shift if shift > 0 else trunc
    M = 1 << k
    counts = np.bincount(buckets, minlength=M)
    expected = N / M
    return float(((counts - expected) ** 2).sum() / expected)


def buckets_at_k(trunc, k):
    shift = 24 - k
    return (trunc >> shift if shift > 0 else trunc).astype(np.int64)


def main():
    t0 = time.time()
    print(f"# IT-3 Stage 3: unification check at k={K}, R={R}")
    inputs, pairs = enumerate_low_hw2()
    N = len(inputs)
    feats = compute_features(pairs)
    print(f"# N={N}, features={list(feats)}")

    # SHA-256 single-shot
    sha_trunc = hash_set_sha256(inputs)
    sha_chi2 = chi2_at_k(sha_trunc, K, N)
    sha_buckets = buckets_at_k(sha_trunc, K)
    sha_I = {fn: mi_plugin(arr, sha_buckets)[0]
             for fn, (arr, _) in feats.items()}

    # RO null with R realizations on the SAME inputs and SAME feature defs
    print(f"# Running {R} RO realizations...")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro_chi2 = []
    ro_I = {fn: [] for fn in feats}
    t_loop = time.time()
    for r, key in enumerate(keys):
        trunc = hash_set_keyed(inputs, key)
        ro_chi2.append(chi2_at_k(trunc, K, N))
        b = buckets_at_k(trunc, K)
        for fn, (arr, _) in feats.items():
            ro_I[fn].append(mi_plugin(arr, b)[0])
        if (r + 1) % 100 == 0:
            print(f"  r={r+1:4d}/{R}  elapsed={time.time()-t_loop:.1f}s")
    ro_chi2 = np.asarray(ro_chi2)
    for fn in feats:
        ro_I[fn] = np.asarray(ro_I[fn])

    # Build report
    chi2_mean = float(ro_chi2.mean())
    chi2_std = float(ro_chi2.std(ddof=1))
    z_chi2 = (sha_chi2 - chi2_mean) / chi2_std
    p_chi2 = float((np.abs(ro_chi2 - chi2_mean) >= abs(sha_chi2 - chi2_mean)).sum() + 1) / (R + 1)

    print(f"\n## χ² metric at k={K} (same {R} RO realizations)")
    print(f"  SHA-256: {sha_chi2:.2f}")
    print(f"  RO band: {chi2_mean:.2f} ± {chi2_std:.2f}")
    print(f"  z = {z_chi2:+.2f}, two-sided p = {p_chi2:.5f}")
    print(f"  5σ resolution: ±{5*chi2_std:.2f} (in χ² units)")

    print(f"\n## I(f; Y) metric at k={K} for each feature (same {R} RO realizations)")
    print(f"{'feature':<14}  {'I_SHA':>10}  {'I_RO mean':>10}  {'I_RO std':>10}  "
          f"{'Δ bits':>10}  {'z':>6}  {'p_two':>7}  {'5σ thresh':>12}")
    print('-' * 100)
    out_table = {}
    for fn in feats:
        arr = ro_I[fn]
        m, s = float(arr.mean()), float(arr.std(ddof=1))
        d = sha_I[fn] - m
        z = d / s if s > 0 else 0.0
        p = float((np.abs(arr - m) >= abs(d)).sum() + 1) / (R + 1)
        thresh = 5 * s
        print(f"{fn:<14}  {sha_I[fn]:>10.6f}  {m:>10.6f}  {s:>10.6f}  "
              f"{d:>+10.6f}  {z:>+6.2f}  {p:>7.4f}  {thresh:>12.2e}")
        out_table[fn] = {
            'I_SHA': sha_I[fn], 'I_RO_mean': m, 'I_RO_std': s,
            'delta_bits': d, 'z': z, 'p_two': p, 'thresh_5sig': thresh,
        }

    print(f"\n## Verdict")
    if abs(z_chi2) > 2 and all(abs(out_table[fn]['z']) < 2 for fn in feats):
        print("  Dissociation CONFIRMED:")
        print("    χ² metric:   |z| = {:.2f}  (signal)".format(abs(z_chi2)))
        print("    I(f;Y) max: |z| = {:.2f}  (no signal in any feature)".format(
            max(abs(out_table[fn]['z']) for fn in feats)))
        print("  → SHA-256 has marginal-uniformity excess WITHOUT structural-MI excess.")

    out = {
        'meta': {'k': K, 'R': R, 'N': N, 'seed': SEED},
        'chi2': {'sha': sha_chi2, 'ro_mean': chi2_mean, 'ro_std': chi2_std,
                 'z': z_chi2, 'p_two': p_chi2},
        'I_per_feature': out_table,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t0:.1f}s")


if __name__ == '__main__':
    main()
