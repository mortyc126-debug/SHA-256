"""
Decisive follow-up to probe_separability.py P3, with a FIXED random-oracle
control (the earlier RO was accidentally constant).

Setup: r=17 barrier delta_e_17. Freeze the shared words {W0,W1,W9}. For each
"Da13-side" active word i in {2,3,4,5,6,7,8,10,11}, form the mixed
second-difference across (W_i | W14), where W14 is the (essentially) pure
dW16-side word. Measure per-bit balance vs 0.5.

Compare SHA barrier against the random-oracle control under the IDENTICAL
protocol. Phase 8C rule: a per-bit |z| only counts as structure if SHA
beats RO on the same bit/pair. We report bit 0 (LSB, structurally trivial)
separately from bits 1..31.
"""

import random
import math
from probe_separability import barrier, ro_barrier, _inv_norm, mixed_second_diff
from sha256_core import MASK


def per_bit_ones(values, n):
    return [sum((v >> bit) & 1 for v in values) for bit in range(32)]


def zscore(ones, n):
    return (ones - n / 2) / math.sqrt(n / 4)


def scan(eval_fn, label, samples, delta, seed, shared_seed):
    rng = random.Random(seed)
    # fixed base; freeze shared words deterministically from shared_seed
    base = [rng.getrandbits(32) for _ in range(16)]
    srng = random.Random(shared_seed)
    for s in (0, 1, 9):
        base[s] = srng.getrandbits(32)
    da13_side = [2, 3, 4, 5, 6, 7, 8, 10, 11]
    out = {}
    for i in da13_side:
        vals = [mixed_second_diff(eval_fn, base, i, 14, rng, delta)
                for _ in range(samples)]
        ones = per_bit_ones(vals, samples)
        zs = [zscore(o, samples) for o in ones]
        ez = sum(1 for v in vals if v == 0)
        out[i] = (zs, ez)
    return out, label


def summarize(sha, ro, samples):
    n_tests = 9 * 31  # 9 pairs * bits 1..31 (exclude trivial bit0)
    thr = abs(_inv_norm(1 - 0.05 / (2 * n_tests)))
    print(f"\nPer-pair max|z| over bits 1..31 (exclude LSB), samples={samples}")
    print(f"Bonferroni threshold ({n_tests} tests): {thr:.2f}")
    print(f"{'word i':>7} | {'SHA bit0 z':>11} {'SHA max(1..31)':>16} "
          f"{'RO max(1..31)':>15} {'verdict':>10}")
    sha_z, ro_z = sha[0], ro[0]
    flagged = []
    for i in sorted(sha_z):
        szs, sez = sha_z[i]
        rzs, rez = ro_z[i]
        sha_bit0 = szs[0]
        sha_max = max(range(1, 32), key=lambda b: abs(szs[b]))
        ro_max = max(range(1, 32), key=lambda b: abs(rzs[b]))
        sha_peak = szs[sha_max]
        ro_peak = rzs[ro_max]
        beats = abs(sha_peak) > thr and abs(sha_peak) > abs(ro_peak) + 1.0
        verdict = "STRUCTURE" if beats else "noise"
        if beats:
            flagged.append((i, sha_max, sha_peak))
        print(f"{i:>7} | {sha_bit0:>+11.2f} "
              f"{f'bit{sha_max}={sha_peak:+.2f}':>16} "
              f"{f'bit{ro_max}={ro_peak:+.2f}':>15} {verdict:>10}")
    print()
    if flagged:
        print(f"  CANDIDATE STRUCTURE (SHA beats RO + Bonferroni): {flagged}")
        print("  -> worth deeper sampling / multi-seed replication before any claim.")
    else:
        print("  No bit beats RO under Bonferroni. r=17 barrier shows no "
              "exploitable per-bit separability across the Da13|dW16 split.")
    return flagged


if __name__ == "__main__":
    SAMP = 12000
    DELTA = 0x80000000
    sha = scan(barrier, "SHA", SAMP, DELTA, seed=100, shared_seed=7)
    ro = scan(ro_barrier, "RO", SAMP, DELTA, seed=100, shared_seed=7)
    flagged = summarize(sha, ro, SAMP)

    # If anything flagged, replicate on a different shared-word seed to test
    # robustness (Phase 8C fragility lesson).
    if flagged:
        print("\n== replication on different shared-word freeze (seed=999) ==")
        sha2 = scan(barrier, "SHA", SAMP, DELTA, seed=100, shared_seed=999)
        ro2 = scan(ro_barrier, "RO", SAMP, DELTA, seed=100, shared_seed=999)
        summarize(sha2, ro2, SAMP)
