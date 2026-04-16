"""
IT-4.Q2: Does bit5_max signal hold at HW=6, 7, 8?

IT-4.1 scan found:
  HW=2 → +4.28, HW=3 → +0.47, HW=4 → +2.82, HW=5 → −0.31

Hypothesis: signal on EVEN HW only. Test extension:
  HW ∈ {6, 7, 8} with R=300 RO null.

If even-HW pattern holds: HW=6 positive, HW=7 ≈ 0, HW=8 positive.
Otherwise: pattern was artifact of small sample of even HWs.
"""

import hashlib, math, json, os, time, random
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
N_TARGET = 130816
HW_NEW = [6, 7, 8]          # already have 2, 3, 4, 5 from IT-4.1
R = 300
SEED = 0xCAFE02
OUT = os.path.join(os.path.dirname(__file__), 'it4_q2_hw_parity.json')


def gen_codewords(w, n_target, seed):
    L = 64
    codewords, positions = [], []
    if w == 2:
        for pos in combinations(range(LENGTH_BITS), w):
            b = bytearray(L)
            for p in pos:
                b[p >> 3] |= 1 << (p & 7)
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
    print("# IT-4.Q2: HW parity hypothesis — test HW ∈ {6, 7, 8}")

    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]

    results = {}
    for hw in HW_NEW:
        print(f"\n## HW = {hw}")
        t_hw = time.time()
        codewords, positions = gen_codewords(hw, N_TARGET, SEED ^ hw)
        N = len(codewords)
        print(f"  N = {N}")
        # Feature: bit5 of max position
        max_p = np.asarray([p[-1] for p in positions], dtype=np.int64)
        f = ((max_p >> 5) & 1).astype(np.uint8)

        sha = sha256_trunc24(codewords)
        sha_v = walsh_sumz2(f, sha)

        ro = []
        t1 = time.time()
        for r, key in enumerate(keys):
            trunc = keyed_blake_trunc24(codewords, key)
            ro.append(walsh_sumz2(f, trunc))
            if (r + 1) % 100 == 0:
                print(f"    r={r+1}/{R} elapsed={time.time()-t1:.1f}s")
        ro = np.asarray(ro)
        m, s = float(ro.mean()), float(ro.std(ddof=1))
        z = (sha_v - m) / s
        p = float((np.abs(ro - m) >= abs(sha_v - m)).sum() + 1) / (R + 1)
        results[hw] = {'sha': sha_v, 'ro_mean': m, 'ro_std': s, 'z_norm': z, 'p_emp': p}
        print(f"  bit5_max: sha={sha_v:.2f}, RO={m:.2f}±{s:.2f}, z={z:+.2f}, p={p:.4f}")

    # Full picture combining IT-4.1 + Q2
    print("\n## Combined picture (bit5_max, role=max):")
    print(f"  {'HW':>3}  {'z_norm':>7}  {'p_emp':>7}  {'parity':>7}")
    # from IT-4.1
    it41_data = json.load(open(os.path.join(os.path.dirname(__file__), 'it4_1_hw_scan.json')))
    for hw in [2, 3, 4, 5]:
        z = it41_data['results'][str(hw)]['max']['5']['z_norm']
        p = it41_data['results'][str(hw)]['max']['5']['p_emp']
        parity = 'even' if hw % 2 == 0 else 'odd'
        print(f"  {hw:>3}  {z:>+7.2f}  {p:>7.4f}  {parity:>7}")
    for hw in HW_NEW:
        z = results[hw]['z_norm']
        p = results[hw]['p_emp']
        parity = 'even' if hw % 2 == 0 else 'odd'
        print(f"  {hw:>3}  {z:>+7.2f}  {p:>7.4f}  {parity:>7}")

    # Parity test
    even_zs = [it41_data['results'][str(hw)]['max']['5']['z_norm'] for hw in [2, 4]]
    even_zs += [results[hw]['z_norm'] for hw in HW_NEW if hw % 2 == 0]
    odd_zs = [it41_data['results'][str(hw)]['max']['5']['z_norm'] for hw in [3, 5]]
    odd_zs += [results[hw]['z_norm'] for hw in HW_NEW if hw % 2 == 1]
    print(f"\n  Even-HW z-scores: {even_zs}  mean={np.mean(even_zs):+.2f}")
    print(f"  Odd-HW  z-scores: {odd_zs}  mean={np.mean(odd_zs):+.2f}")
    from scipy.stats import mannwhitneyu
    u_stat, u_p = mannwhitneyu(even_zs, odd_zs, alternative='greater')
    print(f"  Mann-Whitney U (even > odd): U={u_stat}, p={u_p:.4f}")

    # Save
    out = {
        'meta': {'N_target': N_TARGET, 'R': R, 'HW_new': HW_NEW, 'seed': SEED},
        'results': {str(hw): results[hw] for hw in HW_NEW},
        'even_odd_test': {
            'even_mean': float(np.mean(even_zs)),
            'odd_mean': float(np.mean(odd_zs)),
            'mann_whitney_u': float(u_stat),
            'mann_whitney_p_oneside': float(u_p),
        },
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
