"""
(3)-entry: does amortized MITM threaten T_BARRIER_16 = 2^64?

Logic:
  - The MITM produces delta_e_17 = 0 pairs at AMORTIZED ~O(1) cost from large
    lists (build n, get n^2/2^32 solutions).
  - T_BARRIER_16 = 2^64 assumed each delta_e_17=0 pair costs 2^32, so
    2^32 pairs -> 2^64.  If delta_e_17 pairs are amortized-cheap and
    delta_e_18 is uniform/independent over them (methodology's own
    T_DE18_INDEPENDENCE: P(de18=0|de17=0)=2^-32), then an 18-zero pair costs
    ~2^33-2^34 time (+ memory), NOT 2^64.

DECISIVE PREMISE TEST: collect many delta_e_17=0 pairs in ONE frame and
measure the distribution of delta_e_18 over them.
  - If ~uniform (full ~32-bit entropy, low bits balanced): the 2^34 attack is
    real (modulo memory) and T_BARRIER_16 is too pessimistic.
  - If constrained (low entropy / never 0 / biased): the MITM pairs are
    correlated and the wall holds.

We ALSO directly validate the cost scaling: find a 17-zero pair that ALSO has
delta_e_18 == 0 mod 2^k for growing k, and check cost tracks the uniform
prediction ~2^16 * 2^(k/2).
"""

import random
import math
from collections import Counter
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def de17_de18(base, delta=0x80000000):
    """Wang chain, then schedule rounds 16,17 -> (delta_e_17, delta_e_18)."""
    Wn = [0] * 16
    Wf = [0] * 16
    sn = tuple(IV); sf = tuple(IV)
    Wn[0] = base[0] & MASK
    Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0); sf = one_round(sf, Wf[0], 0)
    for r in range(1, 16):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        dW = (-(((df - dn) & MASK) + ((hf - hn) & MASK)
                + ((Sig1(ef) - Sig1(en)) & MASK)
                + ((Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK))) & MASK
        Wn[r] = base[r] & MASK
        Wf[r] = (Wn[r] + dW) & MASK
        sn = one_round(sn, Wn[r], r); sf = one_round(sf, Wf[r], r)

    def sched(W, t):
        return (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
    W16n = sched(Wn, 16); W16f = sched(Wf, 16)
    Wn = Wn + [W16n]; Wf = Wf + [W16f]
    sn = one_round(sn, W16n, 16); sf = one_round(sf, W16f, 16)
    de17 = (sf[4] - sn[4]) & MASK
    W17n = sched(Wn, 17); W17f = sched(Wf, 17)
    sn = one_round(sn, W17n, 17); sf = one_round(sf, W17f, 17)
    de18 = (sf[4] - sn[4]) & MASK
    return de17, de18


def collect_17zero_pairs(frame_seed=0, list_bits=20, delta=0x80000000):
    """MITM over (W10,W11 | W14): build side A keyed on f=de17(., c0), probe
    with W14.  Collect ALL de17=0 pairs and their de18 values."""
    rng = random.Random(frame_seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    a0 = (base[10], base[11]); c0 = base[14]

    def B17(w10, w11, w14):
        b = list(base)
        b[10], b[11], b[14] = w10, w11, w14
        return de17_de18(b, delta)

    gc0, _ = B17(*a0, c0)
    L = 1 << list_bits
    sideA = {}
    for _ in range(L):
        w10, w11 = rng.getrandbits(32), rng.getrandbits(32)
        d17, _ = B17(w10, w11, c0)
        sideA.setdefault(d17, (w10, w11))
    de18_vals = []
    for _ in range(L):
        w14 = rng.getrandbits(32)
        d17c, _ = B17(*a0, w14)
        key = (-(d17c - gc0)) & MASK
        hit = sideA.get(key)
        if hit is not None:
            w10, w11 = hit
            d17, d18 = B17(w10, w11, w14)
            if d17 == 0:                    # genuine 17-zero pair
                de18_vals.append(d18)
    return de18_vals


def analyze(de18_vals):
    n = len(de18_vals)
    distinct = len(set(de18_vals))
    print(f"  collected {n} genuine 17-zero pairs; distinct de18 = {distinct}")
    if n < 8:
        print("  too few pairs; raise list_bits.")
        return
    # per-bit balance of de18 (uniform -> each bit ~0.5)
    worst_z, worst_bit = 0.0, -1
    for bit in range(32):
        ones = sum((v >> bit) & 1 for v in de18_vals)
        z = (ones - n / 2) / math.sqrt(n / 4)
        if abs(z) > abs(worst_z):
            worst_z, worst_bit = z, bit
    # any value repeated a lot? (constraint signature)
    top = Counter(de18_vals).most_common(1)[0]
    print(f"  de18 per-bit max|z| = {worst_z:+.2f} at bit {worst_bit} "
          f"(uniform => |z| small)")
    print(f"  most common de18 value occurs {top[1]}x out of {n} "
          f"(uniform => ~1)")
    frac_distinct = distinct / n
    verdict = ("UNIFORM -> de18 independent over MITM pairs; T_BARRIER_16 "
               "beatable to ~2^33-2^34 (+memory)") if (abs(worst_z) < 5 and
               frac_distinct > 0.9) else \
              ("CONSTRAINED -> MITM pairs correlate de18; wall holds")
    print(f"  VERDICT: {verdict}")


if __name__ == "__main__":
    print("Premise test: distribution of delta_e_18 over MITM-generated "
          "17-zero pairs (one frame)")
    for lb in (19, 20):
        print(f"\n[list size 2^{lb} per side]")
        vals = collect_17zero_pairs(frame_seed=1, list_bits=lb)
        analyze(vals)
