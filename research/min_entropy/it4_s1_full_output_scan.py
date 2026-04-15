"""
IT-4.S1 (surgical): full 256-bit output Walsh scan for bit5_max on HW=2.

Previous tests used only 24 output bits (first 3 bytes of SHA-256 output).
Amplify by using all 256 bits:
  - 256 z-scores per hash instance
  - Σz² over 256 bits (χ²_256 under H_0, mean=256, std=22.6)
  - max |z| across 256 bits (H_0 expects ~3.33)
  - Identify individual bit positions with significant |z|

R = 500 RO realizations for stronger null.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
N_OUT_BITS = 256
R = 500
SEED = 0x516201
OUT = os.path.join(os.path.dirname(__file__), 'it4_s1_full_output.json')


def low_hw2():
    L = 64
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def sha256_full256(inputs):
    """Return array of shape (N, 32) bytes — full 256-bit output."""
    N = len(inputs)
    out = np.zeros((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        out[i] = np.frombuffer(hashlib.sha256(x).digest(), dtype=np.uint8)
    return out


def blake2b_full256_keyed(inputs, key):
    """BLAKE2b keyed, first 256 bits."""
    N = len(inputs)
    out = np.zeros((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        out[i] = np.frombuffer(hashlib.blake2b(x, key=key, digest_size=32).digest(),
                               dtype=np.uint8)
    return out


def extract_all_bits(digest_bytes):
    """digest_bytes: (N, 32) → (N, 256) binary array, MSB first per byte."""
    N = digest_bytes.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for byte_idx in range(32):
        b = digest_bytes[:, byte_idx]
        for bit_in_byte in range(8):
            col = byte_idx * 8 + bit_in_byte
            bits[:, col] = (b >> (7 - bit_in_byte)) & 1
    return bits


def walsh_z_vector(f_arr, out_bits):
    """out_bits: (N, 256); f_arr: (N,). Return vector of 256 z-scores."""
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    f_mat = f_arr[:, None].astype(np.int32)
    # equal[:, b] = 1 if f == out_bit_b else 0
    equal = (out_bits == f_mat).astype(np.int32)
    eq_counts = equal.sum(axis=0)
    mean_signed = (2.0 * eq_counts - N) / N
    return mean_signed * sqrtN    # shape (256,)


def main():
    t_total = time.time()
    print("# IT-4.S1: full 256-bit output Walsh scan for bit5_max on HW=2")
    inputs, pos = low_hw2()
    N = len(inputs)
    print(f"# N = {N}, outputs = 256 bits, R = {R}")
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f = ((max_p >> 5) & 1).astype(np.uint8)

    # SHA-256
    t0 = time.time()
    sha_digest = sha256_full256(inputs)
    sha_bits = extract_all_bits(sha_digest)
    print(f"# SHA-256 hashing + bit extraction: {time.time()-t0:.1f}s")
    sha_z = walsh_z_vector(f, sha_bits)
    sha_sumz2 = float((sha_z ** 2).sum())
    sha_maxz = float(np.abs(sha_z).max())
    sha_max_idx = int(np.argmax(np.abs(sha_z)))
    print(f"  Σz² over 256 bits: {sha_sumz2:.2f}")
    print(f"  max |z|:           {sha_maxz:.2f} at bit {sha_max_idx}")
    print(f"  z[bit {sha_max_idx}] = {sha_z[sha_max_idx]:+.2f}")

    # RO null
    print(f"\n# RO null with R={R}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R)]
    ro_sumz2 = []
    ro_maxz = []
    ro_z_samples = []       # flat sample of z's for marginal stats
    t0 = time.time()
    for r, key in enumerate(keys):
        digest = blake2b_full256_keyed(inputs, key)
        bits = extract_all_bits(digest)
        z_vec = walsh_z_vector(f, bits)
        ro_sumz2.append(float((z_vec ** 2).sum()))
        ro_maxz.append(float(np.abs(z_vec).max()))
        if r < 5 or (r + 1) % 50 == 0:
            print(f"  r={r+1}/{R}  elapsed={time.time()-t0:.1f}s  "
                  f"Σz²={ro_sumz2[-1]:.1f}  maxz={ro_maxz[-1]:.2f}")
        if r < 20:
            ro_z_samples.extend(z_vec.tolist())
    ro_sumz2 = np.asarray(ro_sumz2)
    ro_maxz = np.asarray(ro_maxz)
    ro_z_samples = np.asarray(ro_z_samples)
    print(f"\n  RO marginal z: mean={ro_z_samples.mean():+.4f}, "
          f"std={ro_z_samples.std(ddof=1):.4f}  (expected 0, 1)")

    # Σz² analysis
    m_sum, s_sum = float(ro_sumz2.mean()), float(ro_sumz2.std(ddof=1))
    z_sum = (sha_sumz2 - m_sum) / s_sum
    p_sum = float((np.abs(ro_sumz2 - m_sum) >= abs(sha_sumz2 - m_sum)).sum() + 1) / (R + 1)
    print(f"\n## Σz² (256 bits)")
    print(f"  SHA-256:  {sha_sumz2:.2f}")
    print(f"  RO band:  {m_sum:.2f} ± {s_sum:.2f}")
    print(f"  z_norm:   {z_sum:+.3f}")
    print(f"  p_emp:    {p_sum:.5f}")

    # max|z| analysis
    m_max, s_max = float(ro_maxz.mean()), float(ro_maxz.std(ddof=1))
    z_max = (sha_maxz - m_max) / s_max
    p_max_emp = float((ro_maxz >= sha_maxz).sum() + 1) / (R + 1)
    print(f"\n## max|z| across 256 bits")
    print(f"  SHA-256:  {sha_maxz:.2f}  at bit {sha_max_idx}")
    print(f"  RO band:  {m_max:.3f} ± {s_max:.3f}")
    print(f"  q95:      {float(np.quantile(ro_maxz, 0.95)):.3f}")
    print(f"  q99:      {float(np.quantile(ro_maxz, 0.99)):.3f}")
    print(f"  z_norm:   {z_max:+.3f}")
    print(f"  P(RO_max ≥ SHA_max) = {p_max_emp:.5f}")

    # Identify all bits with |z| > threshold
    thresh = 3.0
    sig_bits = [(i, float(sha_z[i])) for i in range(256) if abs(sha_z[i]) >= thresh]
    print(f"\n## Bits with |z| > {thresh} (total 256, expected ≈ {256 * 0.0027:.1f} under H_0):")
    if sig_bits:
        sig_bits.sort(key=lambda x: -abs(x[1]))
        for bit_idx, zv in sig_bits:
            byte_pos = bit_idx // 8
            bit_in_byte = bit_idx % 8
            print(f"  bit {bit_idx:>3}  (byte {byte_pos}, bit-in-byte {bit_in_byte})  z = {zv:+.3f}")
    else:
        print("  (none)")

    # Save
    out = {
        'meta': {'N': N, 'R': R, 'feature': 'bit5_max', 'HW': 2, 'n_out_bits': 256},
        'sha_z_per_bit': sha_z.tolist(),
        'sha_sumz2': sha_sumz2,
        'sha_maxz': sha_maxz,
        'sha_max_bit_idx': sha_max_idx,
        'sumz2': {'sha': sha_sumz2, 'ro_mean': m_sum, 'ro_std': s_sum,
                  'z_norm': z_sum, 'p_emp': p_sum},
        'maxz': {'sha': sha_maxz, 'ro_mean': m_max, 'ro_std': s_max,
                 'z_norm': z_max, 'p_emp': p_max_emp,
                 'ro_q95': float(np.quantile(ro_maxz, 0.95)),
                 'ro_q99': float(np.quantile(ro_maxz, 0.99))},
        'significant_bits': [{'bit': i, 'z': z} for i, z in sig_bits],
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
