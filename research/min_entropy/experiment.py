"""
IT-1: Min-entropy of SHA-256 output on structured inputs.

Hypothesis under test:
    H_inf(SHA-256(X) | trunc k bits) ≈ min(k, H_inf(X)) − o(1)

i.e. SHA-256 acts as a near-optimal min-entropy condenser: it neither
loses min-entropy (within O(log n)) nor magically creates it beyond what
the input source provides.

We measure on truncated outputs (k bits) because measuring H_inf on
full 256-bit output requires ~2^128 samples.

Estimators:
  H_inf_hat   = -log2(max_count / N)               (Rényi H_∞, plug-in)
  H_2_hat     = -log2( (Σ count_i² - N) / (N(N-1)) )   (Rényi H_2, unbiased collision est.)
  d_TV_hat    = ½ Σ |count_i/N - 1/2^k|             (statistical distance to uniform)

For uniform output with N samples in 2^k buckets:
  E[max count] ≈ N/2^k + sqrt(2 ln(2^k) · N/2^k)
  → H_inf_hat is biased DOWNWARD (overestimates max → underestimates H_inf).
  We compare each source against the UNIFORM baseline measured the same way,
  so the bias cancels.
"""

import hashlib
import math
import time
import json
import os
import secrets
from collections import Counter

import numpy as np

K_TRUNC = 20         # truncate SHA-256 output to k bits
N_SAMPLES = 1 << 22  # 4_194_304 samples per source
SEED = 0xC0FFEE


# ---------------------------------------------------------------------------
# Source generators: each yields N input bytes (any length) for hashing.
# ---------------------------------------------------------------------------

def src_uniform(n, rng):
    """Baseline: 64-byte (512-bit) uniformly random inputs. H_inf(X) = 512."""
    for _ in range(n):
        yield rng.randbytes(64)

def src_counter(n, rng):
    """Counter source: X = i, 8-byte big-endian. H_inf(X) = log2(n)."""
    for i in range(n):
        yield i.to_bytes(8, 'big')

def src_low_hw(n, rng, weight=4, length_bits=512):
    """
    Low Hamming-weight: choose `weight` bit positions out of length_bits,
    set them to 1. H_inf(X) = log2( C(length_bits, weight) ).
    """
    L = length_bits // 8
    for _ in range(n):
        positions = rng.sample(range(length_bits), weight)
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        yield bytes(b)

def src_ascii(n, rng, length=64):
    """Printable ASCII (95 chars). H_inf(X) = length · log2(95) ≈ 420 bits."""
    chars = bytes(range(0x20, 0x7F))   # 95 printable
    for _ in range(n):
        yield bytes(rng.choices(chars, k=length))

def src_biased(n, rng, p_one=0.1, length_bits=512):
    """
    Biased coin: each bit i.i.d. Bernoulli(p_one).
    H_inf(X) = length_bits · (-log2 max(p_one, 1-p_one)).
    Vectorised with numpy for speed; seeded from `rng` for reproducibility.
    """
    L = length_bits // 8
    seed = rng.getrandbits(64)
    nprng = np.random.default_rng(seed)
    # generate in chunks to avoid huge memory
    CHUNK = 1 << 14
    remaining = n
    while remaining > 0:
        c = min(CHUNK, remaining)
        bits = (nprng.random((c, length_bits)) < p_one).astype(np.uint8)
        # pack 8 bits into a byte
        bytes_arr = np.packbits(bits, axis=1, bitorder='little')  # shape (c, L)
        for row in bytes_arr:
            yield row.tobytes()
        remaining -= c

def src_coset(n, rng, free_bits=24, length_bits=512):
    """
    Coset: fixed random base b0 + xor with vector ranging over free_bits LSBs.
    H_inf(X) = free_bits.
    """
    L = length_bits // 8
    base = rng.randbytes(L)
    if n > (1 << free_bits):
        # we want each X drawn uniformly from the 2^free_bits coset; with
        # replacement is fine for our purposes (still has H_inf = free_bits).
        pass
    mask = (1 << free_bits) - 1
    for _ in range(n):
        e = rng.randint(0, mask)
        b = bytearray(base)
        for j in range(min(free_bits, length_bits)):
            if (e >> j) & 1:
                b[j >> 3] ^= 1 << (j & 7)
        yield bytes(b)


# ---------------------------------------------------------------------------
# Min-entropy + collision-entropy estimation on truncated SHA-256 output.
# ---------------------------------------------------------------------------

def truncated_hash(message_bytes, k):
    """First k bits of SHA-256(message), big-endian."""
    h = hashlib.sha256(message_bytes).digest()
    # take first ceil(k/8) bytes as int, shift down to k bits
    nb = (k + 7) // 8
    val = int.from_bytes(h[:nb], 'big')
    excess = nb * 8 - k
    return val >> excess

def measure(source_iter, n, k):
    """
    Hash n inputs from source_iter, truncate to k bits, return (H_inf_hat,
    H_2_hat, d_TV_hat, max_count, num_distinct).
    """
    counts = Counter()
    for _ in range(n):
        msg = next(source_iter)
        counts[truncated_hash(msg, k)] += 1

    M = 1 << k
    max_count = max(counts.values())
    H_inf = -math.log2(max_count / n)

    # unbiased collision count: Σ c_i (c_i - 1) ≈ N(N-1)·Σ p_i²
    coll = sum(c * (c - 1) for c in counts.values())
    if coll == 0:
        H_2 = float('inf')
    else:
        p2 = coll / (n * (n - 1))
        H_2 = -math.log2(p2)

    # statistical distance to uniform
    inv_M = 1.0 / M
    # buckets present in counter
    d_present = sum(abs(c / n - inv_M) for c in counts.values())
    # buckets missing: contribute (M - num_distinct) * inv_M
    d_missing = (M - len(counts)) * inv_M
    d_TV = 0.5 * (d_present + d_missing)

    return {
        'H_inf_hat': H_inf,
        'H_2_hat': H_2,
        'd_TV_hat': d_TV,
        'max_count': max_count,
        'num_distinct': len(counts),
        'expected_per_bucket': n / M,
    }


# ---------------------------------------------------------------------------
# Experiment driver
# ---------------------------------------------------------------------------

def H_inf_X_theoretical(name):
    """Theoretical input min-entropy (bits) for each source."""
    if name == 'uniform':       return 512.0
    if name == 'counter':       return math.log2(N_SAMPLES)
    if name == 'low_hw_w2':     return math.log2(math.comb(512, 2))   # ≈ 17.0
    if name == 'low_hw_w4':     return math.log2(math.comb(512, 4))   # ≈ 32.7
    if name == 'low_hw_w8':     return math.log2(math.comb(512, 8))   # ≈ 60.5
    if name == 'ascii_64':      return 64 * math.log2(95)             # ≈ 420.5
    if name == 'biased_p10':    return 512 * (-math.log2(0.9))        # ≈ 77.8
    if name == 'biased_p01':    return 512 * (-math.log2(0.99))       # ≈  7.4
    if name == 'coset_24':      return 24.0
    if name == 'coset_18':      return 18.0
    if name == 'coset_12':      return 12.0
    raise KeyError(name)


def make_source(name, rng):
    if name == 'uniform':       return src_uniform(N_SAMPLES, rng)
    if name == 'counter':       return src_counter(N_SAMPLES, rng)
    if name == 'low_hw_w2':     return src_low_hw(N_SAMPLES, rng, weight=2)
    if name == 'low_hw_w4':     return src_low_hw(N_SAMPLES, rng, weight=4)
    if name == 'low_hw_w8':     return src_low_hw(N_SAMPLES, rng, weight=8)
    if name == 'ascii_64':      return src_ascii(N_SAMPLES, rng, length=64)
    if name == 'biased_p10':    return src_biased(N_SAMPLES, rng, p_one=0.1)
    if name == 'biased_p01':    return src_biased(N_SAMPLES, rng, p_one=0.01)
    if name == 'coset_24':      return src_coset(N_SAMPLES, rng, free_bits=24)
    if name == 'coset_18':      return src_coset(N_SAMPLES, rng, free_bits=18)
    if name == 'coset_12':      return src_coset(N_SAMPLES, rng, free_bits=12)
    raise KeyError(name)


def run():
    import random
    sources = [
        'uniform',
        'counter',
        'ascii_64',
        'biased_p10',
        'biased_p01',
        'low_hw_w8',
        'low_hw_w4',
        'low_hw_w2',
        'coset_24',
        'coset_18',
        'coset_12',
    ]

    results = {
        'meta': {
            'k_truncation_bits': K_TRUNC,
            'n_samples': N_SAMPLES,
            'expected_per_bucket': N_SAMPLES / (1 << K_TRUNC),
            'seed': SEED,
        },
        'sources': {},
    }

    print(f"# IT-1: SHA-256 min-entropy on structured inputs")
    print(f"# k = {K_TRUNC} bits truncation, N = {N_SAMPLES} samples")
    print(f"# Expected per bucket (uniform): {N_SAMPLES / (1<<K_TRUNC):.2f}")
    print()
    print(f"{'source':<14} {'H_inf(X)':>10} {'H_inf(Y)':>10} {'H_2(Y)':>10} {'d_TV':>12} "
          f"{'max_ct':>8} {'distinct':>10} {'time_s':>8}")
    print("-" * 100)

    for name in sources:
        rng = random.Random(SEED ^ hash(name))
        source = make_source(name, rng)
        t0 = time.time()
        m = measure(source, N_SAMPLES, K_TRUNC)
        elapsed = time.time() - t0
        H_in = H_inf_X_theoretical(name)
        results['sources'][name] = {
            'H_inf_X_theoretical': H_in,
            **m,
            'time_s': elapsed,
        }
        print(f"{name:<14} {H_in:>10.2f} {m['H_inf_hat']:>10.4f} {m['H_2_hat']:>10.4f} "
              f"{m['d_TV_hat']:>12.6f} {m['max_count']:>8d} {m['num_distinct']:>10d} {elapsed:>8.1f}")

    out_path = os.path.join(os.path.dirname(__file__), 'results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == '__main__':
    run()
