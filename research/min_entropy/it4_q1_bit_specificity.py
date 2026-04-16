"""
IT-4.Q1: Is bit 5 of max position specifically special, or do other
binary functions of max position give similar signals?

bit_5(p) = (p >> 5) & 1 = parity of word_index where word_index = p // 32.

Hypotheses:
  H_bit5     : specifically bit 5 is special (rotation-amount resonance?)
  H_word_idx : any function of word_index gives signal (block parity matters)
  H_arbitrary: random — bit 5 was lucky

Scan: on HW=2, role=max, 30 different binary functions of max position:
  single bits 0..8, parity of various windows, mod patterns, thresholds.
  R=300 RO null.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
N_TARGET = 130816
R = 300
SEED = 0xCAFE01
OUT = os.path.join(os.path.dirname(__file__), 'it4_q1_bit_specificity.json')


def gen_low_hw2():
    L = 64
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def build_max_features(pos):
    """Many binary functions of max position."""
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    feats = {}
    # Single bits (already known, for baseline)
    for b in range(9):
        feats[f'bit{b}'] = ((max_p >> b) & 1).astype(np.uint8)
    # Parity of windows (concatenation of consecutive bits)
    for b_lo in range(0, 9):
        for width in (2, 3, 4):
            if b_lo + width > 9: continue
            mask = (1 << width) - 1
            windows = (max_p >> b_lo) & mask
            parity = np.asarray([bin(int(v)).count('1') & 1 for v in windows], dtype=np.uint8)
            feats[f'par_b{b_lo}w{width}'] = parity
    # Word-index functions
    word_idx = max_p // 32
    feats['word_parity'] = (word_idx & 1).astype(np.uint8)   # same as bit5
    feats['word_b1']     = ((word_idx >> 1) & 1).astype(np.uint8)  # = bit6
    feats['word_b2']     = ((word_idx >> 2) & 1).astype(np.uint8)  # = bit7
    feats['word_b3']     = ((word_idx >> 3) & 1).astype(np.uint8)  # = bit8
    feats['word_HW_par'] = np.asarray([bin(int(v)).count('1') & 1 for v in word_idx], dtype=np.uint8)
    # Mod patterns
    for m in (3, 5, 7, 11):
        feats[f'mod{m}_par'] = (max_p % m & 1).astype(np.uint8)
    # Byte/bit position within message
    feats['byte_par']   = ((max_p >> 3) & 1).astype(np.uint8)   # = bit3
    feats['byte_within_word'] = (((max_p >> 3) & 3) ^ ((max_p >> 3) >> 1) & 1).astype(np.uint8)
    # Threshold
    feats['ge256']      = (max_p >= 256).astype(np.uint8)   # = bit8
    feats['ge128']      = (max_p >= 128).astype(np.uint8)   # NOT a single bit
    feats['ge64']       = (max_p >= 64).astype(np.uint8)
    # XOR of two bits
    feats['bit4_xor_bit5'] = (((max_p >> 4) & 1) ^ ((max_p >> 5) & 1)).astype(np.uint8)
    feats['bit5_xor_bit6'] = (((max_p >> 5) & 1) ^ ((max_p >> 6) & 1)).astype(np.uint8)
    feats['bit5_xor_bit7'] = (((max_p >> 5) & 1) ^ ((max_p >> 7) & 1)).astype(np.uint8)
    return feats


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
    t0 = time.time()
    print("# IT-4.Q1: bit specificity scan on HW=2 max position")
    inputs, pos = gen_low_hw2()
    N = len(inputs)
    print(f"# N = {N}")
    feats = build_max_features(pos)
    print(f"# Features: {len(feats)}")

    sha = sha256_trunc24(inputs)
    sha_sumz2 = {fn: walsh_sumz2(arr, sha) for fn, arr in feats.items()}

    print(f"\n# RO null with R={R}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro = {fn: [] for fn in feats}
    t1 = time.time()
    for r, key in enumerate(keys):
        trunc = keyed_blake_trunc24(inputs, key)
        for fn, arr in feats.items():
            ro[fn].append(walsh_sumz2(arr, trunc))
        if (r + 1) % 100 == 0:
            print(f"  r={r+1}/{R} elapsed={time.time()-t1:.1f}s")

    results = {}
    for fn in feats:
        arr = np.asarray(ro[fn])
        m, s = float(arr.mean()), float(arr.std(ddof=1))
        sha_v = sha_sumz2[fn]
        z = (sha_v - m) / s
        p = float((np.abs(arr - m) >= abs(sha_v - m)).sum() + 1) / (R + 1)
        results[fn] = {'sha': sha_v, 'ro_mean': m, 'ro_std': s, 'z_norm': z, 'p_emp': p}

    bonf = 0.05 / len(feats)
    print(f"\n## Per-feature z_norm (Bonferroni α/F = {bonf:.4e})")
    print(f"{'feature':<22}  {'sha_Σz²':>8}  {'RO_mean':>8}  {'RO_std':>7}  {'z':>7}  {'p_emp':>7}")
    order = sorted(results.items(), key=lambda kv: -abs(kv[1]['z_norm']))
    for fn, r in order:
        flag = ' **' if r['p_emp'] < bonf else ('  *' if r['p_emp'] < 0.05 else '')
        print(f"{fn:<22}  {r['sha']:>8.2f}  {r['ro_mean']:>8.2f}  {r['ro_std']:>7.2f}  "
              f"{r['z_norm']:>+7.2f}  {r['p_emp']:>7.4f}{flag}")

    # Save
    out = {
        'meta': {'N': N, 'R': R, 'n_features': len(feats), 'bonferroni_alpha': bonf},
        'results': results,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time()-t0:.1f}s")


if __name__ == '__main__':
    main()
