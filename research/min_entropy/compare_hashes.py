"""
IT-1b: Compare SHA-256 against SHA-512 and BLAKE2b on the same structured
sources, to isolate "SHA-256 specific" behavior from generic structural
effects of the source.

Hypothesis: if SHA-256 behaves as a random oracle for min-entropy
condensation, all three hashes give statistically equivalent (H_inf, H_2,
d_TV) on each source.

We focus on the "interesting" sources where we saw non-trivial output
min-entropy in experiment.py:
  - biased_p01    (H_inf(X) = 7.4   << k)   : input-bound regime
  - low_hw_w2     (H_inf(X) = 17    ≈ k)    : birthday region
  - coset_18      (H_inf(X) = 18    ≈ k)    : birthday region
  - coset_12      (H_inf(X) = 12    < k)    : input-bound, exact

For each (hash, source) we run R independent repetitions and report
mean ± std of H_inf_hat and d_TV_hat. Difference between hashes is
tested with two-sample t-test.
"""

import hashlib
import math
import os
import json
import time
from collections import Counter

import numpy as np

import experiment as exp     # reuse source generators

K_TRUNC = 20
N_SAMPLES = 1 << 20          # 1M per repetition (smaller, but 8 reps)
R_REPS = 8
SEED = 0xBEEF


HASHES = {
    'sha256':  lambda m: hashlib.sha256(m).digest(),
    'sha512':  lambda m: hashlib.sha512(m).digest(),
    'blake2b': lambda m: hashlib.blake2b(m).digest(),
}


def trunc_int(digest, k):
    nb = (k + 7) // 8
    val = int.from_bytes(digest[:nb], 'big')
    return val >> (nb * 8 - k)


def measure_hash(source_iter, n, k, hashfn):
    counts = Counter()
    for _ in range(n):
        msg = next(source_iter)
        counts[trunc_int(hashfn(msg), k)] += 1
    M = 1 << k
    max_c = max(counts.values())
    H_inf = -math.log2(max_c / n)
    coll = sum(c * (c - 1) for c in counts.values())
    H_2 = -math.log2(coll / (n * (n - 1))) if coll else float('inf')
    inv_M = 1.0 / M
    d_TV = 0.5 * (sum(abs(c / n - inv_M) for c in counts.values())
                  + (M - len(counts)) * inv_M)
    return H_inf, H_2, d_TV, max_c, len(counts)


def run():
    import random

    sources = ['biased_p01', 'low_hw_w2', 'coset_18', 'coset_12', 'uniform']
    table = {}

    print(f"# IT-1b: cross-hash comparison")
    print(f"# k={K_TRUNC}, N={N_SAMPLES} per rep, R={R_REPS} reps")
    print()
    print(f"{'source':<14} {'hash':<8} "
          f"{'H_inf mean±sd':>20} {'d_TV mean±sd':>22} {'max_ct mean':>14}")
    print("-" * 90)

    for name in sources:
        table[name] = {}
        for hname, hfn in HASHES.items():
            H_infs, d_TVs, max_cs = [], [], []
            for r in range(R_REPS):
                rng = random.Random(SEED ^ hash((name, hname, r)))
                src = exp.make_source_with_n(name, rng, N_SAMPLES) \
                    if hasattr(exp, 'make_source_with_n') \
                    else _make_source(name, rng, N_SAMPLES)
                Hi, H2, dTV, mc, distinct = measure_hash(src, N_SAMPLES, K_TRUNC, hfn)
                H_infs.append(Hi)
                d_TVs.append(dTV)
                max_cs.append(mc)
            H_mean, H_sd = float(np.mean(H_infs)), float(np.std(H_infs, ddof=1))
            d_mean, d_sd = float(np.mean(d_TVs)),  float(np.std(d_TVs, ddof=1))
            mc_mean = float(np.mean(max_cs))
            table[name][hname] = {
                'H_inf_mean': H_mean, 'H_inf_sd': H_sd,
                'd_TV_mean': d_mean,  'd_TV_sd': d_sd,
                'max_count_mean': mc_mean,
                'reps': R_REPS, 'n': N_SAMPLES, 'k': K_TRUNC,
            }
            print(f"{name:<14} {hname:<8} "
                  f"{H_mean:>10.4f} ± {H_sd:>5.4f}  "
                  f"{d_mean:>11.6f} ± {d_sd:>6.6f}  "
                  f"{mc_mean:>12.1f}")
        print()

    out_path = os.path.join(os.path.dirname(__file__), 'compare_results.json')
    with open(out_path, 'w') as f:
        json.dump(table, f, indent=2)
    print(f"Wrote {out_path}")

    # quick statistical test: SHA-256 vs BLAKE2b H_inf per source
    print("\n# t-test SHA-256 vs BLAKE2b on H_inf_hat (8 reps each):")
    from scipy import stats
    for name in sources:
        a = []
        b = []
        # re-derive H_inf samples from the per-rep loop (we kept only mean/sd
        # above; recompute quickly for the t-test)
        for r in range(R_REPS):
            rng = random.Random(SEED ^ hash((name, 'sha256', r)))
            src = _make_source(name, rng, N_SAMPLES)
            a.append(measure_hash(src, N_SAMPLES, K_TRUNC, HASHES['sha256'])[0])
            rng = random.Random(SEED ^ hash((name, 'blake2b', r)))
            src = _make_source(name, rng, N_SAMPLES)
            b.append(measure_hash(src, N_SAMPLES, K_TRUNC, HASHES['blake2b'])[0])
        t, p = stats.ttest_ind(a, b, equal_var=False)
        print(f"  {name:<14}  t={t:+.3f}  p={p:.3f}  "
              f"sha256_mean={np.mean(a):.4f}  blake2b_mean={np.mean(b):.4f}  "
              f"Δ={np.mean(a)-np.mean(b):+.4f}")


def _make_source(name, rng, n):
    # local mirror of experiment.make_source but parameterized by n
    if name == 'uniform':       return exp.src_uniform(n, rng)
    if name == 'counter':       return exp.src_counter(n, rng)
    if name == 'low_hw_w2':     return exp.src_low_hw(n, rng, weight=2)
    if name == 'low_hw_w4':     return exp.src_low_hw(n, rng, weight=4)
    if name == 'low_hw_w8':     return exp.src_low_hw(n, rng, weight=8)
    if name == 'ascii_64':      return exp.src_ascii(n, rng, length=64)
    if name == 'biased_p10':    return exp.src_biased(n, rng, p_one=0.1)
    if name == 'biased_p01':    return exp.src_biased(n, rng, p_one=0.01)
    if name == 'coset_24':      return exp.src_coset(n, rng, free_bits=24)
    if name == 'coset_18':      return exp.src_coset(n, rng, free_bits=18)
    if name == 'coset_12':      return exp.src_coset(n, rng, free_bits=12)
    raise KeyError(name)


if __name__ == '__main__':
    t0 = time.time()
    run()
    print(f"\nTotal time: {time.time() - t0:.1f}s")
