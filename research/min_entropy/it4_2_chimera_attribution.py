"""
IT-4.2: Attribute the (HW=2, max, bit5) signal to SHA-256 components.

Use chimera variants from IT-2 to test which component carries the
signal. If a chimera replacement KILLS the signal, that component is
implicated.

Variants from sha256_chimera.py:
  V0 vanilla
  V1 no_Sigma_compr (Σ0, Σ1 → identity)
  V2 no_sigma_sched (σ0, σ1 → identity)
  V5 linear_chmaj   (Ch, Maj → XOR)
  V0 with K=zero
  V0 with K=golden

For each variant: compute Σz² for feature bit5_max on HW=2 input set,
compare to the same R=300 RO null used in IT-4.1.
"""

import json, math, time, os
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
N_OUT_BITS = 24
R = 300
SEED = 0xFEED4242
OUT = os.path.join(os.path.dirname(__file__), 'it4_2_chimera_attr.json')


def low_hw2():
    L = LENGTH_BITS // 8
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def feature_bit5_max(positions):
    return np.asarray([(p[-1] >> 5) & 1 for p in positions], dtype=np.uint8)


def trunc24_from_state(state):
    """Take first 24 bits of state[0]."""
    return (state[:, 0] >> ch.U32(8)).astype(np.uint32)


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


def keyed_blake_trunc24(inputs, key):
    import hashlib
    out = np.empty(len(inputs), dtype=np.uint32)
    for idx, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=8).digest()
        out[idx] = (d[0] << 16) | (d[1] << 8) | d[2]
    return out


def main():
    t_total = time.time()
    print("# IT-4.2: chimera attribution of (HW=2, max, bit5) signal")
    inputs, pos = low_hw2()
    N = len(inputs)
    print(f"# N = {N}")
    f5 = feature_bit5_max(pos)

    # ----- Compute Σz² for each chimera variant -----
    EXPS = [
        ('V0_vanilla',          ch.VARIANTS['V0_vanilla'],          ch.K_VANILLA, 'K_vanilla'),
        ('V1_no_Sigma_compr',   ch.VARIANTS['V1_no_Sigma_compr'],   ch.K_VANILLA, 'K_vanilla'),
        ('V2_no_sigma_sched',   ch.VARIANTS['V2_no_sigma_sched'],   ch.K_VANILLA, 'K_vanilla'),
        ('V5_linear_chmaj',     ch.VARIANTS['V5_linear_chmaj'],     ch.K_VANILLA, 'K_vanilla'),
        ('V0_K_zero',           ch.VARIANTS['V0_vanilla'],          ch.K_ZERO,    'K_zero'),
        ('V0_K_golden',         ch.VARIANTS['V0_vanilla'],          ch.K_GOLDEN,  'K_golden'),
    ]

    print("\n## Σz² for bit5_max feature, each chimera:")
    chimera_sumz2 = {}
    for name, flags, K, klabel in EXPS:
        t0 = time.time()
        state = ch.hash_messages(inputs, flags, K=K)
        trunc = trunc24_from_state(state)
        s = walsh_sumz2(f5, trunc)
        chimera_sumz2[f'{name} | {klabel}'] = s
        print(f"  {name:<25} | {klabel:<10}  Σz² = {s:>9.3f}  ({time.time()-t0:.1f}s)")

    # ----- RO null at R=300 -----
    print(f"\n## RO null at R={R}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro = []
    t0 = time.time()
    for r, key in enumerate(keys):
        trunc = keyed_blake_trunc24(inputs, key)
        ro.append(walsh_sumz2(f5, trunc))
        if (r + 1) % 100 == 0:
            print(f"  r={r+1}/{R} elapsed={time.time()-t0:.1f}s")
    ro = np.asarray(ro)
    m = float(ro.mean()); s = float(ro.std(ddof=1))
    print(f"  RO band: {m:.3f} ± {s:.3f}")

    print("\n## Final z_norm comparison (bit5_max, HW=2):")
    print(f"  {'variant':<35}  {'Σz²':>9}  {'z_norm':>7}  {'p_emp':>7}")
    print('-' * 75)
    out_table = {}
    for label, sha_v in chimera_sumz2.items():
        z = (sha_v - m) / s
        p = float((np.abs(ro - m) >= abs(sha_v - m)).sum() + 1) / (R + 1)
        out_table[label] = {'sumz2': sha_v, 'z_norm': z, 'p_emp': p}
        marker = ' **' if p < 0.05 / len(chimera_sumz2) else ('  *' if p < 0.05 else '')
        print(f"  {label:<35}  {sha_v:>9.3f}  {z:>+7.2f}  {p:>7.4f}{marker}")

    # Verdict
    v0_z = out_table['V0_vanilla | K_vanilla']['z_norm']
    print(f"\n## Vanilla baseline: z = {v0_z:+.2f}")
    print(f"  Variants that REDUCE |z| by ≥50% relative to vanilla:")
    for label, info in out_table.items():
        if label == 'V0_vanilla | K_vanilla':
            continue
        reduction = 1 - abs(info['z_norm']) / abs(v0_z)
        flag = ' **' if reduction >= 0.5 else ''
        print(f"  {label:<35}  z = {info['z_norm']:+.2f}  "
              f"reduction = {reduction*100:>+.0f}%{flag}")

    out = {
        'meta': {'N': N, 'R': R, 'feature': 'bit5_max', 'HW': 2},
        'ro_band': {'mean': m, 'std': s},
        'variants': out_table,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
