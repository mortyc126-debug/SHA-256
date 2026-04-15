"""
IT-4.Q3: Is the signal specifically on MAX position, or does any
"extreme" role work? Or does a specific ordinal position matter?

IT-4.1 on HW=2 (only 2 roles possible):
  min: z = -0.04  (nothing)
  max: z = +4.28  (strong)

For HW=4 we have 4 positions p_0 < p_1 < p_2 < p_3. Roles:
  min:     p_0
  2nd_min: p_1
  median:  (p_1 + p_2)/2 bucketed, or use p_1 or p_2 as "middle"
  2nd_max: p_2
  max:     p_3

We test feature = bit5 of each role on HW=4 subsample, R=300.

Hypotheses:
  H_max_only:  only p_3 (max) gives signal → signal is "largest position" specific
  H_extremes:  both p_0 and p_3 give signals (maybe opposite signs)
  H_any_pos:   similar |z| at all positions → signal is just "any position of HW=4"
"""

import hashlib, math, json, os, time, random
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
N_TARGET = 130816
HW = 4
R = 300
SEED = 0xCAFE03
OUT = os.path.join(os.path.dirname(__file__), 'it4_q3_role_asymmetry.json')


def gen_hw4(n_target, seed):
    L = 64
    rng = random.Random(seed)
    codewords, positions = [], []
    seen = set()
    while len(codewords) < n_target:
        pos = tuple(sorted(rng.sample(range(LENGTH_BITS), HW)))
        if pos in seen: continue
        seen.add(pos)
        b = bytearray(L)
        for p in pos:
            b[p >> 3] |= 1 << (p & 7)
        codewords.append(bytes(b))
        positions.append(pos)
    return codewords, positions


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


def walsh_sumz2(f_arr, trunc24):
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    s = 0.0
    for b in range(N_OUT_BITS):
        y_b = ((trunc24 >> (N_OUT_BITS - 1 - b)) & 1).astype(np.uint8)
        equal = (f_arr == y_b)
        mean_signed = (2.0 * equal.sum() - N) / N
        z = mean_signed * sqrtN
        s += z * z
    return s


def main():
    t_total = time.time()
    print("# IT-4.Q3: role asymmetry on HW=4")
    codewords, positions = gen_hw4(N_TARGET, SEED)
    N = len(codewords)
    print(f"# N = {N}")

    # Build bit5 features for each ordinal role
    pos_arr = np.asarray(positions, dtype=np.int64)   # (N, 4)
    feats = {}
    for role_idx, role_name in enumerate(['min', '2nd_min', '2nd_max', 'max']):
        p_role = pos_arr[:, role_idx]
        feats[f'bit5_{role_name}'] = ((p_role >> 5) & 1).astype(np.uint8)
    # XOR of extremes
    feats['bit5_min_XOR_max'] = (((pos_arr[:, 0] >> 5) & 1) ^
                                  ((pos_arr[:, 3] >> 5) & 1)).astype(np.uint8)
    # parity of all four bit5s
    bit5_all = np.zeros(N, dtype=np.uint8)
    for i in range(4):
        bit5_all ^= ((pos_arr[:, i] >> 5) & 1).astype(np.uint8)
    feats['bit5_parity_all'] = bit5_all
    # Sum of positions mod 32 bit 5 (= bit 5 of sum)
    sum_pos = pos_arr.sum(axis=1)
    feats['bit5_sum_all']   = ((sum_pos >> 5) & 1).astype(np.uint8)
    feats['bit5_sum_mod32'] = ((sum_pos % 32 >> 5) & 1).astype(np.uint8)  # always 0, trivial test

    sha = sha256_trunc24(codewords)
    sha_v = {fn: walsh_sumz2(arr, sha) for fn, arr in feats.items()}

    print(f"\n# RO null with R={R}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro = {fn: [] for fn in feats}
    t1 = time.time()
    for r, key in enumerate(keys):
        trunc = keyed_blake_trunc24(codewords, key)
        for fn, arr in feats.items():
            ro[fn].append(walsh_sumz2(arr, trunc))
        if (r + 1) % 100 == 0:
            print(f"  r={r+1}/{R} elapsed={time.time()-t1:.1f}s")

    results = {}
    bonf = 0.05 / len(feats)
    for fn in feats:
        arr = np.asarray(ro[fn])
        m, s = float(arr.mean()), float(arr.std(ddof=1))
        v = sha_v[fn]
        z = (v - m) / s
        p = float((np.abs(arr - m) >= abs(v - m)).sum() + 1) / (R + 1)
        results[fn] = {'sha': v, 'ro_mean': m, 'ro_std': s, 'z_norm': z, 'p_emp': p}

    print(f"\n## Results (HW=4, bit5 of each role + derived)")
    print(f"  Bonferroni α/F = {bonf:.4e}")
    print(f"  {'feature':<22}  {'sha_Σz²':>8}  {'RO_mean':>8}  {'RO_std':>7}  {'z':>7}  {'p_emp':>7}")
    order = sorted(results.items(), key=lambda kv: -abs(kv[1]['z_norm']))
    for fn, r in order:
        flag = ' **' if r['p_emp'] < bonf else ('  *' if r['p_emp'] < 0.05 else '')
        print(f"  {fn:<22}  {r['sha']:>8.2f}  {r['ro_mean']:>8.2f}  {r['ro_std']:>7.2f}  "
              f"{r['z_norm']:>+7.2f}  {r['p_emp']:>7.4f}{flag}")

    # Verdict
    print("\n## Verdict")
    max_z = results['bit5_max']['z_norm']
    min_z = results['bit5_min']['z_norm']
    mid1_z = results['bit5_2nd_min']['z_norm']
    mid2_z = results['bit5_2nd_max']['z_norm']
    print(f"  bit5_min     : z = {min_z:+.2f}")
    print(f"  bit5_2nd_min : z = {mid1_z:+.2f}")
    print(f"  bit5_2nd_max : z = {mid2_z:+.2f}")
    print(f"  bit5_max     : z = {max_z:+.2f}")
    if abs(max_z) > max(abs(min_z), abs(mid1_z), abs(mid2_z)) + 1.0:
        print("  → H_max_only supported: max role dominates")
    elif abs(min_z) > 2 and abs(max_z) > 2:
        print("  → H_extremes supported: both min and max significant")
    else:
        print("  → unclear pattern; inspect all roles together")

    out = {
        'meta': {'N': N, 'R': R, 'HW': HW, 'seed': SEED, 'bonf': bonf},
        'results': results,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
