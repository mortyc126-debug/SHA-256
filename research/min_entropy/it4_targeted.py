"""
IT-4 Stage 3: targeted high-resolution follow-up on the Walsh hint.

The hint: feature bit0_i_AND_bit5_j on low_hw_w2, Σz² = 53.69, z_norm = +4.16
relative to R=200 RO null. Empirical p = 0.005, just below Bonferroni for
64 features (0.05/64 = 7.8e-4).

Two diagnostic experiments:

  (A) Tighter null on the SAME feature, SAME input set:
        R = 2000 RO realizations → empirical p resolution ~5e-4.
        If the hint stays at z > 4: it is a real linear leak feature.

  (B) Replication on a DIFFERENT input class:
        HW=3 sub-sample of size N=130 816.
        Compute SHA-256 Σz² for bit0_i_AND_bit5_j and bit5_j.
        Compute R = 500 RO null on the same.
        If hint replicates with z > 3: structural property of SHA-256.
        If does not replicate: hint was input-class-specific or
                                64-feature artifact.

Pre-registered decision:
  Hint CONFIRMED ⇔ (A_p < 0.001) AND (B_z > 3 on SAME feature).
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
SEED_A = 0xA00BABE
SEED_B = 0xB00BABE
R_A = 2000
R_B = 500
N_TARGET = 130816
OUT = os.path.join(os.path.dirname(__file__), 'it4_targeted.json')


def low_hw2_inputs():
    out, ai, aj = [], [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(64)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
        ai.append(positions[0]); aj.append(positions[1])
    return out, np.asarray(ai, dtype=np.int64), np.asarray(aj, dtype=np.int64)


def low_hw3_subsample(seed=0xDADA):
    """Random N_TARGET codewords from HW=3 space (size = 22.3M)."""
    import random
    r = random.Random(seed)
    out, ai, aj, ak = [], [], [], []
    seen = set()
    while len(out) < N_TARGET:
        positions = tuple(sorted(r.sample(range(LENGTH_BITS), 3)))
        if positions in seen:
            continue
        seen.add(positions)
        b = bytearray(64)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
        ai.append(positions[0]); aj.append(positions[1]); ak.append(positions[2])
    return out, (np.asarray(ai, dtype=np.int64),
                 np.asarray(aj, dtype=np.int64),
                 np.asarray(ak, dtype=np.int64))


# Target features (binary)
def feat_bit0_i_AND_bit5_j(i, j):
    return ((i & 1) & ((j >> 5) & 1)).astype(np.uint8)

def feat_bit5_j(i, j):
    return ((j >> 5) & 1).astype(np.uint8)

# For HW=3 we have (i, j, k). Use the smallest two as (i, j) for the same feature.
# This gives a fair replication test using the IDENTICAL feature definition.


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


def walsh_sumz2(f_arr, trunc24):
    """Σ_b z(f, b)² over all 24 output bits."""
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    sumz2 = 0.0
    for b in range(N_OUT_BITS):
        y_b = output_bit_array(trunc24, b)
        equal = (f_arr == y_b)
        mean_signed = (2.0 * equal.sum() - N) / N
        z = mean_signed * sqrtN
        sumz2 += z * z
    return sumz2


# ---------------------------------------------------------------------------
# Stage A: high-resolution null on low_hw_w2 for both target features
# ---------------------------------------------------------------------------

def stage_A():
    print(f"\n## Stage A: low_hw_w2, R={R_A} RO realizations")
    inputs, i_arr, j_arr = low_hw2_inputs()
    N = len(inputs)
    f1 = feat_bit0_i_AND_bit5_j(i_arr, j_arr)
    f2 = feat_bit5_j(i_arr, j_arr)

    sha_trunc = sha256_trunc24(inputs)
    sha_sumz2_f1 = walsh_sumz2(f1, sha_trunc)
    sha_sumz2_f2 = walsh_sumz2(f2, sha_trunc)
    print(f"  SHA-256 Σz² for bit0_i_AND_bit5_j: {sha_sumz2_f1:.3f}")
    print(f"  SHA-256 Σz² for bit5_j:            {sha_sumz2_f2:.3f}")

    nprng = np.random.default_rng(SEED_A)
    keys = [nprng.bytes(16) for _ in range(R_A)]

    ro_f1, ro_f2 = [], []
    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = keyed_blake_trunc24(inputs, key)
        ro_f1.append(walsh_sumz2(f1, trunc))
        ro_f2.append(walsh_sumz2(f2, trunc))
        if (r + 1) % 200 == 0:
            print(f"    r={r+1:4d}/{R_A}  elapsed={time.time()-t0:.1f}s")
    ro_f1 = np.asarray(ro_f1)
    ro_f2 = np.asarray(ro_f2)

    def report(label, sha_v, ro_arr):
        m = float(ro_arr.mean()); s = float(ro_arr.std(ddof=1))
        z = (sha_v - m) / s
        # one-sided upper-tail empirical p (for excess Σz²)
        p_one = float((ro_arr >= sha_v).sum() + 1) / (R_A + 1)
        # two-sided empirical p
        p_two = float((np.abs(ro_arr - m) >= abs(sha_v - m)).sum() + 1) / (R_A + 1)
        print(f"  {label}: sha={sha_v:.3f}  RO_band={m:.3f}±{s:.3f}  "
              f"z={z:+.3f}  p_one={p_one:.5f}  p_two={p_two:.5f}")
        return {'sha': sha_v, 'ro_mean': m, 'ro_std': s,
                'z': z, 'p_one': p_one, 'p_two': p_two,
                'ro_q99': float(np.quantile(ro_arr, 0.99)),
                'ro_q999': float(np.quantile(ro_arr, 0.999))}

    print(f"\n  Results at R={R_A}:")
    A1 = report('bit0_i_AND_bit5_j', sha_sumz2_f1, ro_f1)
    A2 = report('bit5_j           ', sha_sumz2_f2, ro_f2)
    return {'A_bit0_i_AND_bit5_j': A1, 'A_bit5_j': A2}


# ---------------------------------------------------------------------------
# Stage B: replication on HW=3 sub-sample
# ---------------------------------------------------------------------------

def stage_B():
    print(f"\n## Stage B: HW=3 sub-sample, R={R_B} RO realizations")
    inputs, (i_arr, j_arr, k_arr) = low_hw3_subsample()
    N = len(inputs)
    print(f"  N = {N}")
    # Use the smallest two positions as (i, j) to compute the same feature
    f1 = feat_bit0_i_AND_bit5_j(i_arr, j_arr)
    f2 = feat_bit5_j(i_arr, j_arr)

    sha_trunc = sha256_trunc24(inputs)
    sha_sumz2_f1 = walsh_sumz2(f1, sha_trunc)
    sha_sumz2_f2 = walsh_sumz2(f2, sha_trunc)
    print(f"  SHA-256 Σz² for bit0_i_AND_bit5_j: {sha_sumz2_f1:.3f}")
    print(f"  SHA-256 Σz² for bit5_j:            {sha_sumz2_f2:.3f}")

    nprng = np.random.default_rng(SEED_B)
    keys = [nprng.bytes(16) for _ in range(R_B)]
    ro_f1, ro_f2 = [], []
    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = keyed_blake_trunc24(inputs, key)
        ro_f1.append(walsh_sumz2(f1, trunc))
        ro_f2.append(walsh_sumz2(f2, trunc))
        if (r + 1) % 100 == 0:
            print(f"    r={r+1:3d}/{R_B}  elapsed={time.time()-t0:.1f}s")
    ro_f1 = np.asarray(ro_f1)
    ro_f2 = np.asarray(ro_f2)

    def report(label, sha_v, ro_arr):
        m, s = float(ro_arr.mean()), float(ro_arr.std(ddof=1))
        z = (sha_v - m) / s
        p_one = float((ro_arr >= sha_v).sum() + 1) / (R_B + 1)
        p_two = float((np.abs(ro_arr - m) >= abs(sha_v - m)).sum() + 1) / (R_B + 1)
        print(f"  {label}: sha={sha_v:.3f}  RO_band={m:.3f}±{s:.3f}  "
              f"z={z:+.3f}  p_one={p_one:.5f}  p_two={p_two:.5f}")
        return {'sha': sha_v, 'ro_mean': m, 'ro_std': s,
                'z': z, 'p_one': p_one, 'p_two': p_two}

    B1 = report('bit0_i_AND_bit5_j', sha_sumz2_f1, ro_f1)
    B2 = report('bit5_j           ', sha_sumz2_f2, ro_f2)
    return {'B_bit0_i_AND_bit5_j': B1, 'B_bit5_j': B2}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_total = time.time()
    print(f"# IT-4 Stage 3: targeted follow-up on Walsh hint")
    print(f"# Pre-registered decision: hint CONFIRMED iff "
          f"(A.p_one < 0.001) AND (B.z > 3) on bit0_i_AND_bit5_j")

    A_results = stage_A()
    B_results = stage_B()

    print(f"\n## Verdict")
    A_p = A_results['A_bit0_i_AND_bit5_j']['p_one']
    B_z = B_results['B_bit0_i_AND_bit5_j']['z']
    print(f"  A.p_one (bit0_i_AND_bit5_j, low_hw_w2, R={R_A}): {A_p:.5f}")
    print(f"  B.z   (bit0_i_AND_bit5_j, HW=3,        R={R_B}): {B_z:+.3f}")
    confirmed = (A_p < 0.001) and (B_z > 3)
    print(f"  Hint CONFIRMED? {confirmed}")
    if not confirmed:
        if A_p < 0.001:
            print(f"  → Hint survives high-R null on low_hw_w2 (p < 0.001)")
            print(f"  → But does NOT replicate on HW=3 (z = {B_z:+.2f}, need > 3)")
            print(f"  → Conclusion: input-class-specific effect, NOT general structural leak")
        elif B_z > 3:
            print(f"  → Replicates on HW=3 ({B_z:+.2f}σ)")
            print(f"  → But high-R null absorbs the original hint (p = {A_p:.4f})")
            print(f"  → Inconsistent — likely false alarm in original")
        else:
            print(f"  → Both diagnostics fail to confirm")
            print(f"  → Hint was 64-feature multiple-testing artifact")

    out = {
        'meta': {'R_A': R_A, 'R_B': R_B, 'N_target': N_TARGET},
        'stage_A': A_results,
        'stage_B': B_results,
        'verdict_confirmed': bool(confirmed),
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
