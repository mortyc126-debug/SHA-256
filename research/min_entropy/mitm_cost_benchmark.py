"""MITM Phase C: forward vs reverse compression cost benchmark.

Measures per-round and per-r evaluation cost. Confirms forward and reverse
are symmetric (same cost per round) — important for MITM balance.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch
from sha256_reverse import (forward_compression, reverse_compression,
                             expand_schedule, U32, MASK)


OUT = '/home/user/SHA-256/research/min_entropy/mitm_cost_benchmark.json'


def time_forward(N, r, seed=0):
    rng = np.random.default_rng(seed)
    W = expand_schedule([int(x) for x in rng.integers(0, 2**32, size=16, dtype=np.int64)])
    state0 = tuple(U32(x) for x in rng.integers(0, 2**32, size=8))
    ts = time.time()
    for _ in range(N):
        forward_compression(state0, W, r)
    return time.time() - ts


def time_reverse(N, r, seed=0):
    rng = np.random.default_rng(seed)
    W = expand_schedule([int(x) for x in rng.integers(0, 2**32, size=16, dtype=np.int64)])
    state_at_r = tuple(U32(x) for x in rng.integers(0, 2**32, size=8))
    ts = time.time()
    for _ in range(N):
        reverse_compression(state_at_r, W, r, r)
    return time.time() - ts


def main():
    t0 = time.time()
    print("# MITM cost benchmark: forward vs reverse compression timing")
    N = 1000
    rounds_to_test = [8, 12, 16, 20, 24, 32, 48, 64]

    print(f"\n{'r':>3}  {'fwd time':>10}  {'rev time':>10}  {'ratio rev/fwd':>14}")
    results = {}
    for r in rounds_to_test:
        fwd = time_forward(N, r)
        rev = time_reverse(N, r)
        ratio = rev / fwd if fwd > 0 else 0
        results[r] = {'forward_time_s': fwd, 'reverse_time_s': rev,
                      'ratio': ratio,
                      'us_per_round_fwd': 1e6 * fwd / (N * r),
                      'us_per_round_rev': 1e6 * rev / (N * r)}
        print(f"{r:>3}  {fwd:>9.3f}s  {rev:>9.3f}s  {ratio:>14.3f}")

    # Summary
    print(f"\n## Per-round microseconds:")
    for r in rounds_to_test:
        d = results[r]
        print(f"  r={r:>2}: fwd {d['us_per_round_fwd']:.2f}μs/round, "
              f"rev {d['us_per_round_rev']:.2f}μs/round")

    # MITM cost extrapolation
    print(f"\n## MITM cost extrapolation (split at r/2):")
    print(f"  For N forward + N backward, time = N * (r/2) * us_per_round + lookups")
    for r in [16, 24, 32]:
        d = results[r]
        avg_us = (d['us_per_round_fwd'] + d['us_per_round_rev']) / 2
        for N_log in [16, 20, 24]:
            N_total = 2**N_log * (r/2) * avg_us / 1e6  # seconds
            print(f"  r={r}, N=2^{N_log}: ~{N_total:.0f}s ({N_total/3600:.1f}h)")

    out = {
        'N_per_test': N,
        'results': {str(r): v for r, v in results.items()},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
