"""
IT-4.S3 (surgical): test bit5_max signal on SHA-1 and SHA-512.

If the signal is a Merkle-Damgård family property (as IT-1.3 chi^2
suggested), SHA-1 and SHA-512 should show similar bit5_max behavior.
Test: HW=2 exhaustive, full output scan (160 bits for SHA-1, 512 for
SHA-512), R=300 RO null.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

LENGTH_BITS = 512
R = 300
SEED = 0x53C0BEEF
OUT = os.path.join(os.path.dirname(__file__), 'it4_s3_cross_hash.json')


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


def _bytes_to_bits_vectorised(byte_mat):
    """(N, n_bytes) uint8 → (N, n_bytes*8) uint8 binary, MSB-first per byte."""
    return np.unpackbits(byte_mat, axis=1, bitorder='big')


def hash_bits(inputs, hash_fn, n_bytes):
    """Apply hash_fn, return (N, n_bytes*8) binary array (vectorised)."""
    N = len(inputs)
    byte_mat = np.empty((N, n_bytes), dtype=np.uint8)
    for i, x in enumerate(inputs):
        d = hash_fn(x)[:n_bytes]
        byte_mat[i] = np.frombuffer(d, dtype=np.uint8)
    return _bytes_to_bits_vectorised(byte_mat)


def blake2b_bits_keyed(inputs, key, n_bytes):
    """Keyed BLAKE2b truncated to n_bytes, vectorised bit extraction."""
    N = len(inputs)
    byte_mat = np.empty((N, n_bytes), dtype=np.uint8)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=n_bytes).digest()
        byte_mat[i] = np.frombuffer(d, dtype=np.uint8)
    return _bytes_to_bits_vectorised(byte_mat)


def walsh_z_vec(f_arr, out_bits):
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    equal = (out_bits == f_arr[:, None])
    eq = equal.sum(axis=0)
    return (2.0 * eq - N) / N * sqrtN


def main():
    t_total = time.time()
    print("# IT-4.S3: cross-hash test of bit5_max on HW=2")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, R_RO = {R}")

    HASHES = [
        ('sha256',   lambda x: hashlib.sha256(x).digest(),   32),
        ('sha1',     lambda x: hashlib.sha1(x).digest(),     20),
        ('sha512',   lambda x: hashlib.sha512(x).digest(),   64),
        ('sha3_256', lambda x: hashlib.sha3_256(x).digest(), 32),
        ('blake2b',  lambda x: hashlib.blake2b(x).digest(),  32),
        ('md5',      lambda x: hashlib.md5(x).digest(),      16),
    ]

    sha_metrics = {}
    for hname, fn, nb in HASHES:
        print(f"\n## {hname} ({nb*8} bits)")
        t0 = time.time()
        bits = hash_bits(inputs, fn, nb)
        z_vec = walsh_z_vec(f, bits)
        maxz = float(np.abs(z_vec).max())
        maxidx = int(np.argmax(np.abs(z_vec)))
        sumz2 = float((z_vec ** 2).sum())
        # top 5
        top5 = sorted(enumerate(z_vec), key=lambda kv: -abs(kv[1]))[:5]
        sha_metrics[hname] = {
            'n_bytes': nb, 'n_bits': nb * 8,
            'sha_sumz2': sumz2, 'sha_maxz': maxz, 'sha_maxz_idx': maxidx,
            'top5': [{'bit': int(i), 'z': float(v)} for i, v in top5],
            'time': time.time() - t0,
        }
        print(f"  Σz² = {sumz2:.1f}  max|z| = {maxz:.2f} at bit {maxidx}")
        print(f"  top 5: " + ", ".join(f"bit{i}:{v:+.2f}" for i, v in top5))

    # RO null for each output length
    ro_band = {}
    for n_bytes in sorted(set(nb for _, _, nb in HASHES)):
        print(f"\n## RO null for {n_bytes*8}-bit output (R={R})")
        nprng = np.random.default_rng(SEED ^ n_bytes)
        keys = [nprng.bytes(16) for _ in range(R)]
        ro_sumz2 = []
        ro_maxz = []
        t0 = time.time()
        for r, key in enumerate(keys):
            bits = blake2b_bits_keyed(inputs, key, n_bytes)
            z_vec = walsh_z_vec(f, bits)
            ro_sumz2.append(float((z_vec ** 2).sum()))
            ro_maxz.append(float(np.abs(z_vec).max()))
            if (r + 1) % 100 == 0:
                print(f"  r={r+1}/{R} elapsed={time.time()-t0:.1f}s")
        ro_sumz2 = np.asarray(ro_sumz2)
        ro_maxz = np.asarray(ro_maxz)
        ro_band[n_bytes] = {
            'sumz2_mean': float(ro_sumz2.mean()),
            'sumz2_std':  float(ro_sumz2.std(ddof=1)),
            'maxz_mean':  float(ro_maxz.mean()),
            'maxz_std':   float(ro_maxz.std(ddof=1)),
            'maxz_q95':   float(np.quantile(ro_maxz, 0.95)),
            'maxz_q99':   float(np.quantile(ro_maxz, 0.99)),
        }
        print(f"  Σz²: {ro_band[n_bytes]['sumz2_mean']:.1f} ± {ro_band[n_bytes]['sumz2_std']:.2f}")
        print(f"  maxz: {ro_band[n_bytes]['maxz_mean']:.2f} ± {ro_band[n_bytes]['maxz_std']:.3f}  "
              f"q99={ro_band[n_bytes]['maxz_q99']:.2f}")

    # Per-hash verdict
    print("\n## Per-hash z_norm for bit5_max at HW=2")
    print(f"  {'hash':<10}  {'n_bits':>6}  {'Σz²':>8}  {'z_Σz²':>7}  {'max|z|':>6}  {'z_max':>6}")
    table = {}
    for hname, fn, nb in HASHES:
        sm = sha_metrics[hname]
        rb = ro_band[nb]
        z_sumz2 = (sm['sha_sumz2'] - rb['sumz2_mean']) / rb['sumz2_std']
        z_maxz = (sm['sha_maxz'] - rb['maxz_mean']) / rb['maxz_std']
        table[hname] = {
            'sumz2': sm['sha_sumz2'],
            'z_sumz2': z_sumz2,
            'maxz': sm['sha_maxz'],
            'z_maxz': z_maxz,
            'maxz_idx': sm['sha_maxz_idx'],
            'n_bits': nb * 8,
        }
        print(f"  {hname:<10}  {nb*8:>6}  {sm['sha_sumz2']:>8.1f}  "
              f"{z_sumz2:>+7.2f}  {sm['sha_maxz']:>6.2f}  {z_maxz:>+6.2f}")

    out = {
        'meta': {'N': N, 'R': R, 'feature': 'bit5_max', 'HW': 2},
        'sha_metrics': sha_metrics,
        'ro_band': {str(k): v for k, v in ro_band.items()},
        'verdict_table': table,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
