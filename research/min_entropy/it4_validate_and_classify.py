"""
IT-4 Stage 2: validate Walsh-Σz² hints + escalate to logistic-regression
distinguisher.

Two parts:
  (A) For each feature f, simulate the null distribution of Σ_b Z(f,b)²
      using R = 200 keyed-BLAKE2b realizations. SHA-256's Σz² for that
      feature is compared to the empirical null. Reports per-feature
      empirical p-value with Bonferroni correction.

  (B) Logistic regression (sklearn) on all features (single bits + XOR/AND
      combinations) → predict each output bit. Accuracy on holdout
      compared to RO null (sklearn trained on RO realizations) and to
      analytical baseline 0.5 ± sqrt(0.25/N_test).
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np
from scipy.stats import norm

LENGTH_BITS = 512
N_OUT_BITS = 24
SEED = 0x1234CAFE
R_RO = 200
TRAIN_FRAC = 0.8
OUT = os.path.join(os.path.dirname(__file__), 'it4_validate.json')


def enumerate_low_hw2():
    out, ai, aj = [], [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(64)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
        ai.append(positions[0]); aj.append(positions[1])
    return out, np.asarray(ai, dtype=np.int64), np.asarray(aj, dtype=np.int64)


def build_features(i, j):
    feats = {}
    for b in range(9):
        feats[f'bit{b}_i']     = ((i >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_j']     = ((j >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_ixorj'] = (((i ^ j) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_sum']   = ((((i + j) & 0x1FF) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_iandj'] = (((i & j) >> b) & 1).astype(np.uint8)
        feats[f'bit{b}_iorj']  = (((i | j) >> b) & 1).astype(np.uint8)
    hw_par = np.asarray([bin(v).count('1') & 1 for v in range(512)], dtype=np.uint8)
    feats['parity_HWi']      = hw_par[i]
    feats['parity_HWj']      = hw_par[j]
    feats['parity_HW_ixorj'] = hw_par[i ^ j]
    feats['parity_low4_i']   = np.asarray([bin(int(v) & 0xF).count('1') & 1 for v in i], dtype=np.uint8)
    feats['parity_high5_j']  = np.asarray([bin((int(v) >> 4) & 0x1F).count('1') & 1 for v in j], dtype=np.uint8)
    feats['bit0_i_AND_bit0_j'] = (((i & 1) & (j & 1)) & 1).astype(np.uint8)
    feats['bit3_i_AND_bit3_j'] = ((((i >> 3) & 1) & ((j >> 3) & 1)) & 1).astype(np.uint8)
    feats['bit0_i_AND_bit5_j'] = (((i & 1) & ((j >> 5) & 1)) & 1).astype(np.uint8)
    feats['parity_gap']      = ((j - i) & 1).astype(np.uint8)
    feats['parity_HW_gap']   = np.asarray([bin(int(v)).count('1') & 1 for v in (j - i)], dtype=np.uint8)
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


def output_bits(trunc24, n=N_OUT_BITS):
    return [((trunc24 >> (n - 1 - b)) & 1).astype(np.uint8) for b in range(n)]


def walsh_z_matrix(features, out_bits, fnames):
    N = len(out_bits[0])
    F = len(fnames); B = len(out_bits)
    Z = np.zeros((F, B))
    sqrtN = math.sqrt(N)
    for fi, fn in enumerate(fnames):
        f_arr = features[fn]
        for bi, b_arr in enumerate(out_bits):
            equal = (f_arr == b_arr)
            mean_signed = (2.0 * equal.sum() - N) / N
            Z[fi, bi] = mean_signed * sqrtN
    return Z


# ---------------------------------------------------------------------------
# Part A: per-feature Σz² validation
# ---------------------------------------------------------------------------

def part_A(inputs, feats, fnames, sha_obits, R, keys):
    print(f"\n## Part A: per-feature Σz² with R={R} RO null")
    Z_sha = walsh_z_matrix(feats, sha_obits, fnames)
    sumz2_sha = (Z_sha ** 2).sum(axis=1)

    # accumulate RO sumz2 per feature
    F = len(fnames)
    ro_sumz2 = np.zeros((R, F))
    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = hash_set_keyed_blake(inputs, key)
        obits = output_bits(trunc, N_OUT_BITS)
        Z_ro = walsh_z_matrix(feats, obits, fnames)
        ro_sumz2[r] = (Z_ro ** 2).sum(axis=1)
        if (r + 1) % 50 == 0:
            print(f"  r={r+1:3d}/{R}  elapsed={time.time()-t0:.1f}s")

    # per-feature stats
    means = ro_sumz2.mean(axis=0)
    stds = ro_sumz2.std(axis=0, ddof=1)
    z_norm = (sumz2_sha - means) / stds
    p_emp = np.asarray([
        (np.abs(ro_sumz2[:, fi] - means[fi]) >= abs(sumz2_sha[fi] - means[fi])).sum() + 1
        for fi in range(F)
    ]) / (R + 1)

    bonf_alpha = 0.05 / F
    print(f"\n  Bonferroni α/F threshold: p < {bonf_alpha:.4e}")
    print(f"  {'rank':>4}  {'feature':<22}  {'Σz²_sha':>10}  {'RO_mean':>9}  {'RO_std':>8}  "
          f"{'z_norm':>7}  {'p_emp':>9}")
    order = np.argsort(-z_norm)
    for r, fi in enumerate(order[:15], 1):
        flag = ' **' if p_emp[fi] < bonf_alpha else ('  *' if p_emp[fi] < 0.05/3 else '   ')
        print(f"  {r:>4}  {fnames[fi]:<22}  {sumz2_sha[fi]:>10.3f}  {means[fi]:>9.3f}  "
              f"{stds[fi]:>8.3f}  {z_norm[fi]:>+7.2f}  {p_emp[fi]:>9.4f}{flag}")

    # Are there ANY p_emp < bonf_alpha?
    n_signif = int((p_emp < bonf_alpha).sum())
    print(f"\n  Features with p_emp < Bonferroni α/F = {bonf_alpha:.4e}: {n_signif}")
    print(f"  Expected under H_0: {bonf_alpha * F:.3f}")

    return Z_sha, sumz2_sha, means, stds, z_norm, p_emp


# ---------------------------------------------------------------------------
# Part B: logistic regression distinguisher per output bit
# ---------------------------------------------------------------------------

def feature_matrix(features, fnames, N):
    X = np.zeros((N, len(fnames)), dtype=np.float32)
    for fi, fn in enumerate(fnames):
        X[:, fi] = features[fn]
    return X


def part_B(inputs, feats, fnames, sha_obits, R, keys):
    print(f"\n## Part B: logistic regression distinguisher per output bit")
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    N = len(inputs)
    X = feature_matrix(feats, fnames, N)
    print(f"  Feature matrix: {X.shape}")

    rng = np.random.default_rng(SEED)
    train_idx, test_idx = train_test_split(np.arange(N), test_size=1-TRAIN_FRAC,
                                            random_state=int(SEED & 0xFFFFFFFF))
    N_test = len(test_idx)
    print(f"  Train: {len(train_idx)}, Test: {N_test}")
    print(f"  Baseline accuracy under H_0 = 0.5  (binary prediction)")
    print(f"  Std under H_0 = sqrt(0.25/{N_test}) = {math.sqrt(0.25/N_test):.4f}")
    print(f"  5σ threshold above baseline: {5*math.sqrt(0.25/N_test):.4f}")

    # SHA-256 per-bit accuracy
    print(f"\n  Per-output-bit accuracy on test holdout (SHA-256):")
    print(f"  {'bit':>3}  {'sha_acc':>8}  {'sha_z':>7}")
    sha_accs = []
    for b in range(N_OUT_BITS):
        y = sha_obits[b]
        clf = LogisticRegression(C=1.0, max_iter=200, solver='liblinear', n_jobs=1)
        clf.fit(X[train_idx], y[train_idx])
        acc = clf.score(X[test_idx], y[test_idx])
        # z above 0.5 baseline
        z = (acc - 0.5) / math.sqrt(0.25 / N_test)
        sha_accs.append((acc, z))
        print(f"  {b:>3}  {acc:>8.5f}  {z:>+7.2f}")

    # RO null: train and test on a subset of RO realizations to keep time reasonable
    print(f"\n  RO null: training/testing on {min(20, R)} RO realizations per output bit...")
    R_trunc = min(20, R)
    ro_z_per_bit = {b: [] for b in range(N_OUT_BITS)}
    t0 = time.time()
    for r, key in enumerate(keys[:R_trunc]):
        trunc = hash_set_keyed_blake(inputs, key)
        obits = output_bits(trunc, N_OUT_BITS)
        for b in range(N_OUT_BITS):
            y = obits[b]
            clf = LogisticRegression(C=1.0, max_iter=200, solver='liblinear', n_jobs=1)
            clf.fit(X[train_idx], y[train_idx])
            acc = clf.score(X[test_idx], y[test_idx])
            z = (acc - 0.5) / math.sqrt(0.25 / N_test)
            ro_z_per_bit[b].append(z)
        if (r + 1) % 5 == 0:
            print(f"    r={r+1}/{R_trunc} elapsed={time.time()-t0:.1f}s")

    # Compare SHA-256 to RO null per output bit
    print(f"\n  Per-bit comparison: SHA-256 z vs RO null z (R={R_trunc})")
    print(f"  {'bit':>3}  {'sha_z':>7}  {'ro_mean':>8}  {'ro_std':>7}  {'norm_z':>7}  {'p_emp':>8}")
    bit_results = {}
    for b in range(N_OUT_BITS):
        sha_acc, sha_z = sha_accs[b]
        ro_arr = np.asarray(ro_z_per_bit[b])
        m, s = float(ro_arr.mean()), float(ro_arr.std(ddof=1))
        norm_z = (sha_z - m) / s if s > 0 else 0.0
        p_emp = float((np.abs(ro_arr - m) >= abs(sha_z - m)).sum() + 1) / (R_trunc + 1)
        bit_results[b] = {
            'sha_acc': sha_acc, 'sha_z': sha_z,
            'ro_z_mean': m, 'ro_z_std': s,
            'norm_z': norm_z, 'p_emp': p_emp,
        }
        flag = ' *' if p_emp < 0.05/N_OUT_BITS else ''
        print(f"  {b:>3}  {sha_z:>+7.2f}  {m:>+8.2f}  {s:>7.2f}  {norm_z:>+7.2f}  {p_emp:>8.4f}{flag}")

    return sha_accs, bit_results


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_total = time.time()
    print("# IT-4 Stage 2: validation + logistic-regression distinguisher")
    inputs, i_arr, j_arr = enumerate_low_hw2()
    N = len(inputs)
    feats = build_features(i_arr, j_arr)
    fnames = list(feats)
    print(f"# N = {N},  features = {len(fnames)}")

    sha_trunc = hash_set_sha256(inputs)
    sha_obits = output_bits(sha_trunc, N_OUT_BITS)

    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]

    Z_sha, sumz2_sha, A_means, A_stds, A_z, A_p = part_A(
        inputs, feats, fnames, sha_obits, R_RO, keys)

    sha_accs, B_results = part_B(inputs, feats, fnames, sha_obits, R_RO, keys)

    # Verdict
    print("\n## Final verdict")
    a_signal = (A_p < 0.05 / len(fnames)).any()
    b_signal_bits = [b for b, r in B_results.items() if r['p_emp'] < 0.05 / N_OUT_BITS]
    print(f"  Part A (Walsh Σz²): any feature with p < {0.05/len(fnames):.4e}? {a_signal}")
    print(f"  Part B (LogReg per bit): output bits with p < {0.05/N_OUT_BITS:.4e}: {b_signal_bits}")

    # save
    out = {
        'meta': {'N': N, 'F': len(fnames), 'B': N_OUT_BITS, 'R_RO': R_RO},
        'feature_names': fnames,
        'A_sumz2_sha': sumz2_sha.tolist(),
        'A_means': A_means.tolist(),
        'A_stds': A_stds.tolist(),
        'A_z_norm': A_z.tolist(),
        'A_p_emp': A_p.tolist(),
        'A_bonf_alpha': 0.05 / len(fnames),
        'B_per_bit': B_results,
        'B_sha_accs': [{'acc': a, 'z': z} for a, z in sha_accs],
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
