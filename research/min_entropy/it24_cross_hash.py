"""IT-24: Cross-hash Ω_3 — is conservation SHA-2-family-specific?

Tests Ω_3 across hash families:
  SHA-1 (Merkle-Damgård, 160 bits → truncate 160, use all)
  SHA-256, SHA-512 (Merkle-Damgård, SHA-2 family)
  SHA-3-256 (sponge / Keccak)
  BLAKE2b, BLAKE2s (HAIFA)

For each hash h, compute:
  state1 = first 256 bits of h(input)  [self-consistency reference]
  state2 = full h(input) truncated to 256 bits
  Ω_3 = corr(direct_z, chain_3) across 256 output bits

Expected:
  SHA-2 family (256, 512): Ω_3 ≈ +0.85 (Omega_3 conservation, our finding)
  SHA-1:                   ? — similar MD structure, may also show
  SHA-3:                   Ω_3 ≈ 0 (sponge, no 3rd-order Walsh bias)
  BLAKE2:                  Ω_3 ≈ 0 (HAIFA, different)

This produces the clean family-discriminator paper result.

Uses omega3_full C binary for speed. For each hash: ~50s.
"""
import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')


def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos


def hash_to_bits(inputs, hash_func, digest_size=32):
    """Apply hash to each input, extract 256 bits (truncate digest if needed)."""
    N = len(inputs)
    bits = np.zeros((N, 256), dtype=np.uint8)
    for i, m in enumerate(inputs):
        d = hash_func(m).digest()
        if len(d) > 32: d = d[:32]   # truncate to 256 bits
        elif len(d) < 32: d = d + bytes(32 - len(d))  # pad
        arr = np.frombuffer(d, dtype=np.uint8)
        # MSB-first bit extraction per byte
        for bi in range(32):
            for bb in range(8):
                bits[i, bi*8 + bb] = (arr[bi] >> (7 - bb)) & 1
    return bits


def pack(v):
    pd = np.zeros(WORDS * 64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def omega3_measure(state1_bits, state2_bits, fa, stride=8):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        N = len(fa)
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(state1_bits[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(state2_bits[:, b]).tobytes())
        res = subprocess.run([C_BIN, tp, str(stride)], capture_output=True, text=True, check=True, timeout=120)
        return json.loads(res.stdout)
    finally:
        os.unlink(tp)


def main():
    t0 = time.time()
    print("# IT-24: Cross-hash Ω_3 on HW=2 exhaustive (N=130816)")
    inputs, pos = low_hw2(); N = len(inputs)
    mp = np.asarray([p[-1] for p in pos])
    fa = ((mp >> 5) & 1).astype(np.uint8)

    # Hash functions to compare
    hashes = [
        ('md5',        hashlib.md5,                  16),
        ('sha1',       hashlib.sha1,                 20),
        ('sha256',     hashlib.sha256,               32),
        ('sha512',     hashlib.sha512,               64),
        ('sha3_256',   hashlib.sha3_256,             32),
        ('sha3_512',   hashlib.sha3_512,             64),
        ('blake2b',    lambda m: hashlib.blake2b(m), 64),
        ('blake2s',    lambda m: hashlib.blake2s(m), 32),
    ]

    results = []
    for name, hfunc, digest_size in hashes:
        print(f"\n## {name} (digest = {digest_size} bytes)")
        print(f"  Computing hashes for {N} inputs...", flush=True)
        ts = time.time()
        # For "state1" reference use input bits (first 256 of 512)
        # Actually let's use the hash itself: state1 = state2 (r=0 case)
        # This measures self-consistency of the hash output in Walsh-3
        state2_bits = hash_to_bits(inputs, hfunc)
        # state1 bits = input bits (first 256 bits of 512-bit input)
        input_bits = np.zeros((N, 256), dtype=np.uint8)
        for i, m in enumerate(inputs):
            for bi in range(32):  # first 32 bytes = 256 bits
                for bb in range(8):
                    input_bits[i, bi*8 + bb] = (m[bi] >> (7 - bb)) & 1
        print(f"  Hash time: {time.time()-ts:.0f}s. Running omega3_full...", flush=True)
        ts2 = time.time()
        d = omega3_measure(input_bits, state2_bits, fa, stride=8)
        print(f"  Ω_3 = {d['omega3']:+.4f}  ss = {d['same_sign']}/256  "
              f"(C time: {time.time()-ts2:.0f}s)", flush=True)
        results.append({'hash': name, 'omega3': d['omega3'], 'ss': d['same_sign'],
                        'n_triples': d.get('n_triples', 0)})

    print("\n=== IT-24 SUMMARY ===")
    print(f"{'hash':<12} {'family':<20} {'Omega_3':>10} {'ss':>8} {'p_signed':>10}")
    families = {
        'md5': 'Merkle-Damgård (MD)',
        'sha1': 'Merkle-Damgård (SHA-1)',
        'sha256': 'Merkle-Damgård (SHA-2)',
        'sha512': 'Merkle-Damgård (SHA-2)',
        'sha3_256': 'Sponge (Keccak)',
        'sha3_512': 'Sponge (Keccak)',
        'blake2b': 'HAIFA',
        'blake2s': 'HAIFA',
    }
    for r in results:
        ss = r['ss']
        # sign-test z for |ss-128|
        zscore = (max(ss, 256-ss) - 128) / math.sqrt(64)
        p_approx = 2 * math.erfc(zscore/math.sqrt(2)) / 2 if zscore > 0 else 1.0
        print(f"{r['hash']:<12} {families[r['hash']]:<20} {r['omega3']:>+10.4f} "
              f"{ss:>4}/256 {p_approx:>10.2e}")

    print("\n--- FAMILY INTERPRETATION ---")
    print("SHA-2 family (sha256, sha512): expected +0.85 (our Ω_3 conservation)")
    print("SHA-1, MD5 (MD family, older):  may show similar due to MD structure")
    print("SHA-3 (sponge):                 expected ≈ 0 (different arch)")
    print("BLAKE2 (HAIFA):                 expected ≈ 0 (different arch)")
    print("Clean discriminator if SHA-2 >> 0 while SHA-3, BLAKE2 ≈ 0")

    with open(os.path.join(HERE, 'it24_cross_hash.json'), 'w') as f:
        json.dump({'results': results, 'meta': {'N': N, 'n_triples_stride': '2.76M/8=345K'}}, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
