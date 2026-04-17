"""Cross-hash Ω_3 sweep using Oracle Gauge v1.1 (no zero-padding bug).

Probe: HW=2 exhaustive inputs, feature=bit5_max, χ_S over first 32 input bits,
target = hash output truncated to 128 bits (MD5 size, fair cross-hash).

RO null is computed ONCE (shared across all hashes, depends only on input bits).

This re-runs the IT-24 experiment correctly to test the ?OPEN-A question:
does Ω_3 ≈ 0 for SHA-3/BLAKE2 (methodology hypothesis), or is there a
family-specific signal that survives the zero-padding fix?
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import (
    low_hw2_inputs, make_feature, hash_to_bits,
    build_chi_arr, omega_k_fast, ro_null_band, classify,
)

HASHES = [
    ('md5',      lambda m: hashlib.md5(m).digest()),
    ('sha1',     lambda m: hashlib.sha1(m).digest()),
    ('sha256',   lambda m: hashlib.sha256(m).digest()),
    ('sha512',   lambda m: hashlib.sha512(m).digest()),
    ('sha3_256', lambda m: hashlib.sha3_256(m).digest()),
    ('sha3_512', lambda m: hashlib.sha3_512(m).digest()),
    ('blake2b',  lambda m: hashlib.blake2b(m).digest()),
    ('blake2s',  lambda m: hashlib.blake2s(m).digest()),
]

TRUNCATE_BITS = 128
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'cross_hash_omega3_results.json')


def main():
    t0 = time.time()
    print(f"# Cross-hash Ω_3 sweep (Oracle Gauge v1.1, truncate={TRUNCATE_BITS})")

    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N} HW=2 exhaustive inputs")

    fa = make_feature(pos, 'bit5_max')

    # Build input_bits (first 256 bits of each 64-byte input)
    input_bits = np.zeros((N, 256), dtype=np.uint8)
    for i, m in enumerate(inputs):
        for bi in range(32):
            for bb in range(8):
                input_bits[i, bi*8+bb] = (m[bi] >> (7-bb)) & 1

    # Precompute chi_arr for k=3 (shared across hashes)
    print(f"\n# Precomputing χ_S for k=3 over first 32 input bits...")
    ts = time.time()
    chi_arr_k3, tuples = build_chi_arr(input_bits, k=3, subset_size=32)
    print(f"  {len(tuples)} triples, {time.time()-ts:.1f}s")

    # Compute RO null once
    print(f"\n# RO null band (10 BLAKE2b-keyed realizations, truncate={TRUNCATE_BITS})...")
    ts = time.time()
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    for r in range(10):
        key = nprng.bytes(16)
        def f(m): return hashlib.blake2b(m, key=key, digest_size=TRUNCATE_BITS//8).digest()
        bits = hash_to_bits(inputs, f, digest_bits=TRUNCATE_BITS)
        omega, _, _, _, _ = omega_k_fast(chi_arr_k3, bits, fa)
        ro_omegas.append(omega)
    ro_mean = float(np.mean(ro_omegas))
    ro_std = float(np.std(ro_omegas, ddof=1))
    print(f"  mean={ro_mean:+.4f} std={ro_std:.4f} ({time.time()-ts:.1f}s)")

    # Sweep all hashes
    results = []
    print(f"\n# Hash sweep:")
    for name, fn in HASHES:
        ts = time.time()
        target_bits = hash_to_bits(inputs, fn, digest_bits=TRUNCATE_BITS)
        omega, ss, _, _, n_const = omega_k_fast(chi_arr_k3, target_bits, fa)
        verdict, reason, z = classify(omega, ro_mean, ro_std)
        print(f"  {name:10s}: Ω_3 = {omega:+.4f}  ss={ss:>3}/128  "
              f"z={z:>5.2f}σ  [{verdict:10s}]  ({time.time()-ts:.0f}s)")
        results.append({
            'hash': name,
            'omega3': omega,
            'same_sign': ss,
            'n_const_filtered': int(n_const),
            'z_score': z,
            'verdict': verdict,
        })

    out = {
        'N': N,
        'truncate_bits': TRUNCATE_BITS,
        'feature': 'bit5_max',
        'ro_null': {'mean': ro_mean, 'std': ro_std, 'omegas': ro_omegas},
        'hashes': results,
        'version': '1.1.0',
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}")
    print(f"# Total: {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
