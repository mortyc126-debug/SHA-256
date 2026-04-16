"""
IT-4.1: Investigate WHY the bit5_j signal is HW=2-specific.

Three competing hypotheses:
  H1 (semantic shift): in IT-4 stage_B I used (i, j_mid) for HW=3,
       ignoring the third position. Feature semantics changed.
  H2 (HW=2 structural): per v20 §56 (T_SCHEDULE_SPARSE), HW=2 inputs
       give 63% zeros in SHA-256 message schedule — uniquely sparse.
  H3 (chance): with 64 Walsh tests we expect ~3.2 raw-α false positives;
       1 surviving at R=2000 might still be sampling noise.

Design: scan over (HW, role, bit_idx) with CONSISTENT feature semantics.

  HW ∈ {2, 3, 4, 5}
  role ∈ {min, max}            ← role of position within the input HW-tuple
  bit_idx ∈ [0, 9)             ← which bit of the 9-bit position index

For each input set (size N=130816, exhaustive for HW=2, sub-sample for
HW≥3) we compute feature = bit_idx of position[role], then Σz² over 24
output bits of SHA-256. Compare to R=300 RO null.

Output: 4 (HWs) × 2 (roles) × 9 (bits) = 72-cell heatmap of z_norm.

Decision rules:
  - H2 supported if signal appears ONLY at HW=2 across all (role, bit).
  - H1 supported if HW≥3 with role=max and bit=5 also gives signal
    (i.e., the original HW=3 test was wrong because we used mid).
  - H3 supported if HW=2 signal does not concentrate at bit5 — appears
    at random bits across HWs.
"""

import hashlib, math, json, os, time, random
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
N_TARGET = 130816
HW_LIST = [2, 3, 4, 5]
ROLES = ['min', 'max']
BIT_IDX = list(range(9))
R_RO = 300
SEED = 0xCAFE2024
OUT = os.path.join(os.path.dirname(__file__), 'it4_1_hw_scan.json')


def gen_codewords(w, n_target, seed):
    """Return list of 64-byte messages and list of position-tuples."""
    L = LENGTH_BITS // 8
    codewords, positions = [], []
    if w == 2:
        # exhaustive — n_target equals C(512, 2) = 130816
        for pos in combinations(range(LENGTH_BITS), w):
            b = bytearray(L)
            for p in pos: b[p >> 3] |= 1 << (p & 7)
            codewords.append(bytes(b))
            positions.append(pos)
        return codewords, positions
    rng = random.Random(seed)
    seen = set()
    while len(codewords) < n_target:
        pos = tuple(sorted(rng.sample(range(LENGTH_BITS), w)))
        if pos in seen: continue
        seen.add(pos)
        b = bytearray(L)
        for p in pos: b[p >> 3] |= 1 << (p & 7)
        codewords.append(bytes(b))
        positions.append(pos)
    return codewords, positions


def feature_bit_at_role(positions, role, bit_idx):
    """For each position-tuple, take role (min/max) and return bit_idx of it."""
    n = len(positions)
    out = np.zeros(n, dtype=np.uint8)
    if role == 'min':
        for i, pos in enumerate(positions):
            out[i] = (pos[0] >> bit_idx) & 1
    elif role == 'max':
        for i, pos in enumerate(positions):
            out[i] = (pos[-1] >> bit_idx) & 1
    else:
        raise ValueError(role)
    return out


def sha256_trunc24(inputs):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.sha256(x).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def keyed_blake_trunc24(inputs, key):
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def output_bit_array(trunc24, b):
    return ((trunc24 >> (N_OUT_BITS - 1 - b)) & 1).astype(np.uint8)


def walsh_sumz2_for_features(features_dict, trunc24):
    """For each feature in dict, return Σz² across 24 output bits."""
    N = len(next(iter(features_dict.values())))
    sqrtN = math.sqrt(N)
    out_bits = [output_bit_array(trunc24, b) for b in range(N_OUT_BITS)]
    result = {}
    for fname, f_arr in features_dict.items():
        s = 0.0
        for y_b in out_bits:
            equal = (f_arr == y_b)
            mean_signed = (2.0 * equal.sum() - N) / N
            z = mean_signed * sqrtN
            s += z * z
        result[fname] = s
    return result


def main():
    t_total = time.time()
    print("# IT-4.1: HW × role × bit_idx scan to attribute the bit5_j signal")
    print(f"# HW ∈ {HW_LIST}, roles = {ROLES}, bits = {BIT_IDX}")
    print(f"# N_target = {N_TARGET}, R = {R_RO}")

    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]

    # results[hw][role][bit] = {sha, ro_mean, ro_std, z_norm, p_emp}
    results = {hw: {role: {} for role in ROLES} for hw in HW_LIST}

    for hw in HW_LIST:
        print(f"\n## HW = {hw}")
        t_hw = time.time()
        codewords, positions = gen_codewords(hw, N_TARGET, SEED ^ hw)
        N = len(codewords)
        print(f"  N = {N}, gen time = {time.time()-t_hw:.1f}s")

        # build features for all (role, bit_idx)
        feats = {}
        for role in ROLES:
            for b in BIT_IDX:
                feats[f'{role}_bit{b}'] = feature_bit_at_role(positions, role, b)

        # SHA-256 single shot
        t0 = time.time()
        sha_trunc = sha256_trunc24(codewords)
        sha_sumz2 = walsh_sumz2_for_features(feats, sha_trunc)
        print(f"  SHA-256: {time.time()-t0:.1f}s")

        # RO null
        ro_sumz2 = {fname: [] for fname in feats}
        t0 = time.time()
        for r, key in enumerate(keys):
            trunc = keyed_blake_trunc24(codewords, key)
            sd = walsh_sumz2_for_features(feats, trunc)
            for fname, v in sd.items():
                ro_sumz2[fname].append(v)
            if (r + 1) % 100 == 0:
                el = time.time() - t0
                print(f"    r={r+1}/{R_RO}  elapsed={el:.1f}s  "
                      f"eta={el/(r+1)*(R_RO-r-1):.1f}s")

        for fname in feats:
            arr = np.asarray(ro_sumz2[fname])
            m, s = float(arr.mean()), float(arr.std(ddof=1))
            sha_v = sha_sumz2[fname]
            z = (sha_v - m) / s if s > 0 else 0.0
            p = float((np.abs(arr - m) >= abs(sha_v - m)).sum() + 1) / (R_RO + 1)
            role, bit_part = fname.split('_bit')
            b = int(bit_part)
            results[hw][role][b] = {
                'sha': sha_v, 'ro_mean': m, 'ro_std': s,
                'z_norm': z, 'p_emp': p,
            }

    # ----- Print heatmap -----
    print("\n## Z-score heatmap: rows = (HW, role), cols = bit_idx")
    print(f"{'HW':>3} {'role':>4} | " + "  ".join(f"b{b}" for b in BIT_IDX))
    print("-" * (12 + 6 * len(BIT_IDX)))
    for hw in HW_LIST:
        for role in ROLES:
            cells = "  ".join(f"{results[hw][role][b]['z_norm']:+5.2f}" for b in BIT_IDX)
            print(f"{hw:>3} {role:>4} | {cells}")

    # ----- Top-cell summary -----
    print("\n## Cells with |z_norm| ≥ 3 (Bonferroni for 72 cells: |z| > 3.30):")
    flat = []
    for hw in HW_LIST:
        for role in ROLES:
            for b in BIT_IDX:
                z = results[hw][role][b]['z_norm']
                p = results[hw][role][b]['p_emp']
                if abs(z) >= 3.0:
                    flat.append((abs(z), hw, role, b, z, p))
    flat.sort(reverse=True)
    if not flat:
        print("  (none)")
    else:
        print(f"  {'|z|':>6}  {'HW':>3}  {'role':>4}  {'bit':>3}  {'z':>6}  {'p_emp':>7}")
        for azv, hw, role, b, z, p in flat:
            print(f"  {azv:>6.2f}  {hw:>3}  {role:>4}  {b:>3}  {z:>+6.2f}  {p:>7.4f}")

    # ----- Hypothesis evaluation -----
    print("\n## Hypothesis evaluation")
    # H1: signal on HW=3, role=max, bit=5
    z_h3_max5 = results[3]['max'][5]['z_norm']
    print(f"  H1 check: HW=3 role=max bit=5 z_norm = {z_h3_max5:+.2f}")
    print(f"           If H1 true (semantic shift) — should be >3 (we missed it before)")
    # H2: signal ONLY on HW=2 across all (role, bit)
    n_signif_per_hw = {hw: sum(1 for role in ROLES for b in BIT_IDX
                               if abs(results[hw][role][b]['z_norm']) >= 3) for hw in HW_LIST}
    print(f"  H2 check: # of |z|≥3 cells per HW: {n_signif_per_hw}")
    print(f"           If H2 true (HW=2 structural) — concentrated at HW=2")
    # H3: signal randomly distributed
    print(f"  H3 check: total |z|≥3 cells: {sum(n_signif_per_hw.values())} "
          f"out of 72 (expected under H_0: ≈{72*0.0027:.2f})")

    # save
    out = {
        'meta': {'HW_list': HW_LIST, 'roles': ROLES, 'bits': BIT_IDX,
                 'N_target': N_TARGET, 'R': R_RO, 'seed': SEED},
        'results': {str(hw): {role: {str(b): results[hw][role][b]
                                     for b in BIT_IDX}
                              for role in ROLES}
                    for hw in HW_LIST},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
