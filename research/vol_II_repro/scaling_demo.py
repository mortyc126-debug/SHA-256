"""
Concrete validation of the amortized-MITM scaling toward 18 e-zeros, with the
time-memory caveat made explicit.

Premise (verified in amortized_mitm.py): delta_e_18 is uniform over the
17-zero pairs the MITM produces in a frame.  Consequence: among N such pairs,
the best one has ~log2(N) trailing zero bits in delta_e_18, so reaching
delta_e_18 == 0 (full 18 e-zeros) needs ~2^32 pairs, i.e. MITM lists of ~2^32
=> ~2^33 TIME and 2^32 MEMORY.

This is a standard birthday<->MITM TIME-MEMORY TRADEOFF: the time-memory
PRODUCT (~2^64) equals T_BARRIER_16, so there is no reduction in total work,
only a shift of cost from time into memory.  It is a legitimate time-
complexity improvement by the usual convention and refutes П-27C's "MITM
impossible", but it does NOT weaken SHA-256 (e-zeros are necessary, not
sufficient; the collision bound is 2^128).

Here we VERIFY the scaling directly at small scale: collect N 17-zero pairs,
show max-trailing-zeros(delta_e_18) tracks log2(N), and gold-verify the best
pair on plain SHA-256 (delta_e_2..17 = 0 confirmed, delta_e_18 trailing zeros
confirmed from raw e-registers).
"""

import random
import math
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1, e_sequence


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def run_chain(base, delta=0x80000000):
    """Return (de17, de18, Wn, Wf) with Wn/Wf the full 16-word messages."""
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
    return de17, de18, Wn, Wf


def trailing_zeros(x):
    return 32 if x == 0 else (x & -x).bit_length() - 1


def collect(frame_seed, list_bits, delta=0x80000000):
    rng = random.Random(frame_seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    a0 = (base[10], base[11]); c0 = base[14]

    def D(w10, w11, w14):
        b = list(base); b[10], b[11], b[14] = w10, w11, w14
        return run_chain(b, delta)
    gc0 = D(*a0, c0)[0]
    L = 1 << list_bits
    sideA = {}
    for _ in range(L):
        w10, w11 = rng.getrandbits(32), rng.getrandbits(32)
        sideA.setdefault(D(w10, w11, c0)[0], (w10, w11))
    pairs = []
    for _ in range(L):
        w14 = rng.getrandbits(32)
        key = (-(D(*a0, w14)[0] - gc0)) & MASK
        hit = sideA.get(key)
        if hit:
            w10, w11 = hit
            de17, de18, Wn, Wf = D(w10, w11, w14)
            if de17 == 0:
                pairs.append((de18, Wn, Wf))
    return base, pairs


def gold_verify(Wn, Wf):
    def expand(W16):
        W = list(W16) + [0] * 48
        for t in range(16, 64):
            W[t] = (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
        return W
    en = e_sequence(expand(Wn), IV, 18)
    ef = e_sequence(expand(Wf), IV, 18)
    de = [(ef[r] - en[r]) & MASK for r in range(2, 19)]  # de2..de18
    return de


if __name__ == "__main__":
    print("Scaling: max trailing-zeros of delta_e_18 over N 17-zero pairs "
          "should track log2(N)\n")
    print(f"{'list 2^b':>9} {'pairs N':>8} {'log2 N':>7} "
          f"{'max tz(de18)':>13} {'best de18':>12}")
    best_overall = None
    for lb in (18, 19, 20):
        base, pairs = collect(frame_seed=7, list_bits=lb)
        if not pairs:
            print(f"{lb:>9} {0:>8}  (no pairs)")
            continue
        N = len(pairs)
        tzs = [trailing_zeros(d) for (d, _, _) in pairs]
        mx = max(tzs)
        best = max(pairs, key=lambda p: trailing_zeros(p[0]))
        print(f"{lb:>9} {N:>8} {math.log2(N):>7.1f} {mx:>13} "
              f"0x{best[0]:08x}")
        if best_overall is None or trailing_zeros(best[0]) > trailing_zeros(best_overall[0]):
            best_overall = best

    print("\nGOLD-VERIFY the best pair (plain SHA-256, raw e-registers):")
    de18, Wn, Wf = best_overall
    de = gold_verify(Wn, Wf)
    de2_17 = de[:16]   # de2..de17
    de18_raw = de[16]
    print(f"  delta_e_2..17 all zero: {all(x == 0 for x in de2_17)}")
    print(f"  delta_e_18 = 0x{de18_raw:08x}  (trailing zeros: "
          f"{trailing_zeros(de18_raw)})")
    print(f"  matches MITM-reported de18: {de18_raw == de18}")
    print()
    print("Interpretation: max trailing-zeros grows ~log2(N) -> reaching full")
    print("delta_e_18 = 0 needs ~2^32 pairs (lists ~2^32) => ~2^33 TIME, 2^32")
    print("MEMORY for 18 e-zeros.  Time-memory PRODUCT ~2^64 = T_BARRIER_16:")
    print("a standard tradeoff, not a reduction in total work, and NOT a break.")
