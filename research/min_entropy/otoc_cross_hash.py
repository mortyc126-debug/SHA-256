"""OTOC cross-hash comparison: SHA-256 vs SHA-3 vs BLAKE2.

Replaces broken Ω_k probe (⊘ROLL) with rigorous OTOC scrambling measurement.

For each hash family, measure ||C(r)||_F² as function of "rounds" or evaluations.
For SHA-3 and BLAKE2 we don't have round-level access via hashlib, so we measure
**at full hash output** for varying input space restrictions.

Key comparisons:
1. SHA-256 round-by-round (already done in otoc_sha256.py)
2. Full output OTOC for all hash families on RANDOM inputs
3. Full output OTOC on STRUCTURED inputs (HW=2 like)

OTOC at full hash output should approach RO limit for all secure hashes.
Differences (if any) reveal architectural fingerprint.
"""
import hashlib, json, os, time
import numpy as np


OUT = '/home/user/SHA-256/research/min_entropy/otoc_cross_hash_results.json'


def hash_function_factory(name):
    if name == 'md5':
        return lambda data: hashlib.md5(data).digest()
    elif name == 'sha1':
        return lambda data: hashlib.sha1(data).digest()
    elif name == 'sha256':
        return lambda data: hashlib.sha256(data).digest()
    elif name == 'sha512':
        return lambda data: hashlib.sha512(data).digest()
    elif name == 'sha3_256':
        return lambda data: hashlib.sha3_256(data).digest()
    elif name == 'sha3_512':
        return lambda data: hashlib.sha3_512(data).digest()
    elif name == 'blake2b':
        return lambda data: hashlib.blake2b(data, digest_size=32).digest()
    elif name == 'blake2s':
        return lambda data: hashlib.blake2s(data).digest()
    raise ValueError(name)


def measure_otoc_fullhash(hash_fn, output_bits, N=200, msg_bits=512, seed=42):
    """Compute OTOC matrix for full hash output.

    Returns C ∈ R^(msg_bits × output_bits) with C[i,j] = P(out[j] flips | in bit i flips) - 0.5
    """
    rng = np.random.default_rng(seed)
    msg_bytes = msg_bits // 8

    # Generate N base messages
    base_msgs = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)

    # Compute base hashes
    base_outputs = np.zeros((N, output_bits), dtype=np.uint8)
    for i in range(N):
        d = hash_fn(base_msgs[i].tobytes())
        bits = np.unpackbits(np.frombuffer(d, dtype=np.uint8))
        base_outputs[i] = bits[:output_bits]

    # For each input bit i, flip and measure
    C = np.zeros((msg_bits, output_bits), dtype=np.float64)
    for i in range(msg_bits):
        byte = i // 8; bit = 7 - (i % 8)  # MSB-first
        flip_msgs = base_msgs.copy()
        flip_msgs[:, byte] ^= np.uint8(1 << bit)
        flip_outputs = np.zeros((N, output_bits), dtype=np.uint8)
        for j in range(N):
            d = hash_fn(flip_msgs[j].tobytes())
            bits = np.unpackbits(np.frombuffer(d, dtype=np.uint8))
            flip_outputs[j] = bits[:output_bits]
        C[i] = (base_outputs != flip_outputs).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# OTOC cross-hash comparison (full output)")
    print("# C[i,j] = P(output[j] flips | input bit i flips) - 0.5")

    HASHES = [
        ('md5', 128),
        ('sha1', 160),
        ('sha256', 256),
        ('sha512', 512),
        ('sha3_256', 256),
        ('sha3_512', 512),
        ('blake2b', 256),
        ('blake2s', 256),
    ]

    N = 200
    msg_bits = 512  # 64-byte input

    print(f"\n  N={N} messages, input={msg_bits} bits")
    print(f"\n{'hash':>10}  {'out_bits':>8}  {'||C||_F²':>10}  {'mean|C|':>10}  {'theoretical':>12}  {'match?':>8}")

    results = {}
    for name, out_bits in HASHES:
        ts = time.time()
        hash_fn = hash_function_factory(name)
        C = measure_otoc_fullhash(hash_fn, out_bits, N=N, msg_bits=msg_bits)
        F_sq = float((C ** 2).sum())
        mean_abs = float(np.mean(np.abs(C)))
        # Theoretical RO limit: msg_bits × out_bits × 0.25 / N
        theoretical = msg_bits * out_bits * 0.25 / N
        match = abs(F_sq - theoretical) / theoretical
        elapsed = time.time() - ts
        results[name] = {'output_bits': out_bits, 'frobenius_sq': F_sq,
                         'mean_abs': mean_abs, 'theoretical_RO': theoretical,
                         'rel_diff': match, 'time': elapsed}
        marker = '✓' if match < 0.05 else '⚠' if match < 0.15 else '✗'
        print(f"{name:>10}  {out_bits:>8}  {F_sq:>10.2f}  {mean_abs:>10.4f}  "
              f"{theoretical:>12.2f}  {marker}  ({elapsed:.0f}s)")

    print(f"\n## Interpretation:")
    print(f"  ✓ matches RO theoretical limit within 5% → fully scrambled output")
    print(f"  ⚠ within 15% → mostly scrambled, possible weak structure")
    print(f"  ✗ deviates more → distinguishable from RO")

    # Find any outliers
    print(f"\n## Cross-hash structural comparison:")
    print(f"  All secure hashes should show RO-like behavior at full output.")
    for name, info in results.items():
        rel = info['rel_diff']
        verdict = "RO-like" if rel < 0.05 else "weak structure" if rel < 0.15 else "DISTINGUISHABLE"
        print(f"  {name:>10}: rel_diff = {rel:.4f} → {verdict}")

    out = {
        'N_messages': N,
        'msg_bits': msg_bits,
        'results': results,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
