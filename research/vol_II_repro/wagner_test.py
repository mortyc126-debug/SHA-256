"""
(3) Wagner / generalized-birthday applicability test.

A 2-list MITM only trades time for memory (product fixed at the birthday
cost).  The ONLY classical tool that lowers the time-memory PRODUCT is a
k-list algorithm (Wagner): for a target that is the modular sum of k
INDEPENDENT group-contributions, a zero-sum is found in ~2^(n/(1+floor(log2
k))) time and memory.  For the joint 64-bit barrier (delta_e_17, delta_e_18)
and k=4 that would be ~2^21, well under the 2^32 MITM product -> a real
reduction in total work, if it applies.

Wagner applies IFF the joint barrier is FULLY additively separable across k
disjoint word groups:
    delta_e_17 = sum_i f_i(G_i)   AND   delta_e_18 = sum_i g_i(G_i)   (mod 2^32)
Full k-group additive separability  <=>  EVERY pairwise mixed 2nd-difference
over groups (G_a, G_b) vanishes (and exact-zero, not just small bias).

We already know:
  - delta_e_17 is separable over (W10,W11 | W14)  -> good for that pair
  - delta_e_18 is NOT separable over that split    -> bad
The decisive question: is there ANY k>=3 partition under which BOTH barriers
are pairwise-separable across all group pairs?  We scan partitions and, for
each, test every pair of groups for exact mixed-2nd-difference vanishing,
for BOTH de17 and de18.  RO control included.

Prior: the nonlinear carry coupling forbids it (de18 couples broadly), so
Wagner should NOT apply and the time-memory product (~2^64 for 18 zeros)
stands.  We test rather than assert.
"""

import random
import math
import hashlib
from itertools import combinations
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def de17_de18(base, delta=0x80000000):
    Wn = [0] * 16; Wf = [0] * 16
    sn = tuple(IV); sf = tuple(IV)
    Wn[0] = base[0] & MASK; Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0); sf = one_round(sf, Wf[0], 0)
    for r in range(1, 16):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        dW = (-(((df - dn) & MASK) + ((hf - hn) & MASK)
                + ((Sig1(ef) - Sig1(en)) & MASK)
                + ((Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK))) & MASK
        Wn[r] = base[r] & MASK; Wf[r] = (Wn[r] + dW) & MASK
        sn = one_round(sn, Wn[r], r); sf = one_round(sf, Wf[r], r)

    def sched(W, t):
        return (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
    W16n = sched(Wn, 16); W16f = sched(Wf, 16)
    Wn2 = Wn + [W16n]; Wf2 = Wf + [W16f]
    sn = one_round(sn, W16n, 16); sf = one_round(sf, W16f, 16)
    de17 = (sf[4] - sn[4]) & MASK
    W17n = sched(Wn2, 17); W17f = sched(Wf2, 17)
    sn = one_round(sn, W17n, 17); sf = one_round(sf, W17f, 17)
    de18 = (sf[4] - sn[4]) & MASK
    return de17, de18


def ro_eval(base, delta=0x80000000):
    msg = b"".join((w & MASK).to_bytes(4, "big") for w in base)
    h = hashlib.blake2b(msg, digest_size=16, key=b"wag").digest()
    return int.from_bytes(h[:4], "big"), int.from_bytes(h[8:12], "big")


def pair_mixed_diff(eval_fn, base, Ga, Gb, samples, rng, delta):
    """Fraction of samples with mixed 2nd-diff == 0, separately for de17/de18,
    when varying group Ga vs group Gb (other words fixed at base)."""
    z17 = z18 = 0
    bits17 = [0] * 32; bits18 = [0] * 32

    def setw(b, idxs, vals):
        for i, v in zip(idxs, vals):
            b[i] = v

    for _ in range(samples):
        ax = [rng.getrandbits(32) for _ in Ga]
        ay = [rng.getrandbits(32) for _ in Ga]
        bx = [rng.getrandbits(32) for _ in Gb]
        by = [rng.getrandbits(32) for _ in Gb]

        def ev(av, bv):
            b = list(base)
            setw(b, Ga, av); setw(b, Gb, bv)
            return eval_fn(b, delta)
        e17xx, e18xx = ev(ax, bx)
        e17xy, e18xy = ev(ax, by)
        e17yx, e18yx = ev(ay, bx)
        e17yy, e18yy = ev(ay, by)
        m17 = (e17xx - e17xy - e17yx + e17yy) & MASK
        m18 = (e18xx - e18xy - e18yx + e18yy) & MASK
        if m17 == 0:
            z17 += 1
        if m18 == 0:
            z18 += 1
        for bit in range(32):
            bits17[bit] += (m17 >> bit) & 1
            bits18[bit] += (m18 >> bit) & 1

    def mz(bits):
        return max(abs((o - samples / 2) / math.sqrt(samples / 4)) for o in bits)
    return z17 / samples, z18 / samples, mz(bits17), mz(bits18)


def test_partition(eval_fn, groups, samples=1500, delta=0x80000000, seed=1):
    """A partition is Wagner-usable iff EVERY group-pair is exactly separable
    for BOTH de17 and de18."""
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    worst17 = worst18 = 1.0
    detail = []
    for Ga, Gb in combinations(groups, 2):
        f17, f18, mz17, mz18 = pair_mixed_diff(eval_fn, base, Ga, Gb,
                                               samples, rng, delta)
        worst17 = min(worst17, f17)
        worst18 = min(worst18, f18)
        detail.append((Ga, Gb, f17, f18, mz17, mz18))
    return worst17, worst18, detail


# active words for delta_e_17/18 (W12,W13,W15-ish inert for 17; 18 uses more).
# Candidate partitions into k groups of the FREE words that actually move both.
PARTITIONS = {
    "k=2  (W10,W11 | W14)":            [[10, 11], [14]],
    "k=3  (W10,W11 | W14 | W15)":      [[10, 11], [14], [15]],
    "k=3  (W2,W3 | W10,W11 | W14,W15)":[[2, 3], [10, 11], [14, 15]],
    "k=4  (W2,W3|W4,W5|W10,W11|W14,W15)": [[2, 3], [4, 5], [10, 11], [14, 15]],
    "k=4  singles (W10|W11|W14|W15)":  [[10], [11], [14], [15]],
}

if __name__ == "__main__":
    print("Wagner applicability: does ANY k>=3 partition make BOTH de17 and")
    print("de18 fully additively separable (all group-pairs exact-zero)?\n")
    print(f"{'partition':<38} {'worst de17':>11} {'worst de18':>11} {'verdict':>22}")
    for name, groups in PARTITIONS.items():
        w17, w18, detail = test_partition(de17_de18, groups)
        usable = (w17 > 0.999 and w18 > 0.999)
        verdict = "WAGNER APPLIES" if usable else "no (coupled)"
        print(f"{name:<38} {w17:>11.3f} {w18:>11.3f} {verdict:>22}")
    # RO control on the k=3 partition
    rw17, rw18, _ = test_partition(ro_eval,
                                   [[10, 11], [14], [15]])
    print(f"{'RO control k=3':<38} {rw17:>11.3f} {rw18:>11.3f}")
    print()
    print("Reading: 'worst de18' is the min over group-pairs of the fraction")
    print("of exact-zero mixed 2nd-differences. Wagner needs BOTH worst==1.000.")
    print("If de18's worst stays ~0 (like RO), no k-group additive structure")
    print("exists -> Wagner cannot lower the time-memory product. Wall holds.")
