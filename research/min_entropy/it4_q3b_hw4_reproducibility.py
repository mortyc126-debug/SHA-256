"""
IT-4.Q3b: Is the HW=4 signal real or sub-sample artifact?

IT-4.1 at HW=4 with seed=0xCAFE202X gave z=+2.82 for bit5_max.
IT-4.Q3 at HW=4 with seed=0xCAFE03  gave z=-0.66 for bit5_max.

Two data points ⇒ inconclusive. Run 10 independent seeds, plot
distribution of z for bit5_max at HW=4. If z's cluster around 0
→ HW=4 shows no reproducible signal. If systematically >0
→ signal is real but weak.

R=300 RO null per seed. 10 seeds total = ~10 min.
"""

import hashlib, math, json, os, time, random
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 24
N_TARGET = 130816
HW = 4
R = 200
N_SEEDS = 10
OUT = os.path.join(os.path.dirname(__file__), 'it4_q3b_hw4_reproducibility.json')


def gen_hw(w, n_target, seed):
    L = 64
    rng = random.Random(seed)
    codewords, positions = [], []
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
    print(f"# IT-4.Q3b: HW={HW} reproducibility check")
    print(f"# {N_SEEDS} independent seeds, R={R} per seed")

    z_per_seed = []
    sha_per_seed = []
    for seed_idx in range(N_SEEDS):
        seed = 0x11111111 * (seed_idx + 1)
        print(f"\n## Seed {seed_idx+1}/{N_SEEDS}: {hex(seed)}")
        codewords, positions = gen_hw(HW, N_TARGET, seed)
        N = len(codewords)
        max_p = np.asarray([p[-1] for p in positions], dtype=np.int64)
        f = ((max_p >> 5) & 1).astype(np.uint8)

        sha = sha256_trunc24(codewords)
        sha_v = walsh_sumz2(f, sha)

        nprng = np.random.default_rng(seed ^ 0xAAAA)
        ro = []
        t0 = time.time()
        for r in range(R):
            key = nprng.bytes(16)
            trunc = keyed_blake_trunc24(codewords, key)
            ro.append(walsh_sumz2(f, trunc))
        ro = np.asarray(ro)
        m, s = float(ro.mean()), float(ro.std(ddof=1))
        z = (sha_v - m) / s
        sha_per_seed.append(sha_v)
        z_per_seed.append(z)
        print(f"  sha_Σz²={sha_v:.2f}  RO={m:.2f}±{s:.2f}  z={z:+.2f}  "
              f"({time.time()-t0:.1f}s)")

    z_arr = np.asarray(z_per_seed)
    print(f"\n## Distribution of z for bit5_max at HW={HW} across {N_SEEDS} seeds:")
    print(f"  z's: {[f'{z:+.2f}' for z in z_arr]}")
    print(f"  mean = {z_arr.mean():+.2f}")
    print(f"  std  = {z_arr.std(ddof=1):.2f}")
    print(f"  expected std under H_0: ~1.0 (since z_norm itself has std 1)")

    # One-sample t-test vs 0
    from scipy.stats import ttest_1samp
    t_stat, t_p = ttest_1samp(z_arr, 0)
    print(f"  t-test (mean z ≠ 0): t={t_stat:+.3f}, p={t_p:.4f}")

    # Verdict
    print("\n## Verdict")
    if abs(z_arr.mean()) < 1.0 and z_arr.std(ddof=1) < 2.0 and t_p > 0.05:
        print(f"  → NO reproducible signal at HW={HW}. Previous z=+2.82 was sub-sample artifact.")
    elif z_arr.mean() > 1.0 and t_p < 0.05:
        print(f"  → Weak but real signal at HW={HW}: mean z = {z_arr.mean():+.2f}")
    else:
        print(f"  → Inconclusive (or: signal variance > expected)")

    out = {
        'meta': {'HW': HW, 'N_target': N_TARGET, 'R': R, 'n_seeds': N_SEEDS},
        'z_per_seed': [float(z) for z in z_arr],
        'sha_sumz2_per_seed': [float(v) for v in sha_per_seed],
        'mean_z': float(z_arr.mean()),
        'std_z': float(z_arr.std(ddof=1)),
        't_stat': float(t_stat),
        't_p': float(t_p),
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
