"""
Does the r=17 MITM split COMPOSE to r=18 (and beyond)?

The single-barrier finding (MITM_r17_FINDING.md) only matters for the global
question if two barriers can be satisfied at MITM cost simultaneously.

Methodology: 16 e-zeros (delta_e_2..17 then ..18) cost 2^64 (T_BARRIER_16,
П-15/16), because delta_e_17 and delta_e_18 are two independent 32-bit
conditions. A 2D meet-in-the-middle would beat that to ~2^32 IF there exists
ONE bipartition (A | B) of the free words such that BOTH barriers are
additively separable across it:

    delta_e_17 = f1(A) + g1(B)   (mod 2^32)
    delta_e_18 = f2(A) + g2(B)   (mod 2^32)

Then build lists keyed on the 64-bit pair (delta_e_17, delta_e_18) and meet:
~2^32 to hit both zeros, vs 2^64.

delta_e_18 = Da14 + dW17 holds only when delta_e_17 = 0; its decomposition
involves a DIFFERENT word set:
    Da14  -> words through round 13   (W0..W13, now includes W12,W13)
    dW17  -> schedule W17 = sig1(W15)+W10+sig0(W2)+W1  -> {W15,W10,W2,W1}
So the disjoint-influence split for r=18 differs from r=17's (W10,W11|W14).
A single compatible bipartition is therefore NOT guaranteed -- this is the
test.

We measure, for several candidate bipartitions, the JOINT mixed second-
difference of the pair (delta_e_17, delta_e_18). Both must vanish for the
2D-MITM to work. RO control included.
"""

import random
import math
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def chain_de17_de18(base, delta=0x80000000):
    """Wang chain (corrections r=1..15), then schedule rounds 16,17.
    Returns (delta_e_17, delta_e_18)."""
    Wn = [0] * 16
    Wf = [0] * 16
    sn = tuple(IV)
    sf = tuple(IV)
    Wn[0] = base[0] & MASK
    Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0)
    sf = one_round(sf, Wf[0], 0)
    for r in range(1, 16):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        dW = (-(((df - dn) & MASK) + ((hf - hn) & MASK)
                + ((Sig1(ef) - Sig1(en)) & MASK)
                + ((Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK))) & MASK
        Wn[r] = base[r] & MASK
        Wf[r] = (Wn[r] + dW) & MASK
        sn = one_round(sn, Wn[r], r)
        sf = one_round(sf, Wf[r], r)
    # schedule words 16, 17 for each message independently
    def sched(W, t):
        return (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
    Wn16 = sched(Wn, 16); Wf16 = sched(Wf, 16)
    Wn = Wn + [Wn16]; Wf = Wf + [Wf16]
    sn = one_round(sn, Wn16, 16); sf = one_round(sf, Wf16, 16)
    de17 = (sf[4] - sn[4]) & MASK
    Wn17 = sched(Wn, 17); Wf17 = sched(Wf, 17)
    sn = one_round(sn, Wn17, 17); sf = one_round(sf, Wf17, 17)
    de18 = (sf[4] - sn[4]) & MASK
    return de17, de18


def joint_sep(eval_fn, A, B, samples=2000, delta=0x80000000, seed=1):
    """Mixed 2nd-difference of BOTH outputs over bipartition (A|B).
    A, B are disjoint lists of word indices that we vary together on each side.
    Returns (frac_de17_zero, frac_de18_zero, frac_both_zero, per-bit maxz17, maxz18)."""
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    nz17 = nz18 = nzboth = 0
    bits17 = [0] * 32
    bits18 = [0] * 32

    def setw(b, side, vals):
        for idx, v in zip(side, vals):
            b[idx] = v

    for _ in range(samples):
        Ax = [rng.getrandbits(32) for _ in A]
        Ay = [rng.getrandbits(32) for _ in A]
        Bx = [rng.getrandbits(32) for _ in B]
        By = [rng.getrandbits(32) for _ in B]

        def ev(av, bv):
            b = list(base)
            setw(b, A, av); setw(b, B, bv)
            return eval_fn(b, delta)
        e17_xx, e18_xx = ev(Ax, Bx)
        e17_xy, e18_xy = ev(Ax, By)
        e17_yx, e18_yx = ev(Ay, Bx)
        e17_yy, e18_yy = ev(Ay, By)
        m17 = (e17_xx - e17_xy - e17_yx + e17_yy) & MASK
        m18 = (e18_xx - e18_xy - e18_yx + e18_yy) & MASK
        if m17: nz17 += 1
        if m18: nz18 += 1
        if m17 or m18: nzboth += 1
        for bit in range(32):
            bits17[bit] += (m17 >> bit) & 1
            bits18[bit] += (m18 >> bit) & 1
    def maxz(bits):
        return max(abs((o - samples / 2) / math.sqrt(samples / 4)) for o in bits)
    return (1 - nz17 / samples, 1 - nz18 / samples, 1 - nzboth / samples,
            maxz(bits17), maxz(bits18))


def ro_eval(base, delta=0x80000000):
    import hashlib
    msg = b"".join((w & MASK).to_bytes(4, "big") for w in base)
    h = hashlib.blake2b(msg, digest_size=16, key=b"ro2").digest()
    return (int.from_bytes(h[:4], "big"), int.from_bytes(h[8:12], "big"))


CANDIDATES = {
    "(W10,W11 | W14)         [r17 split]": ([10, 11], [14]),
    "(W10,W11 | W14,W15)     [add W15]":   ([10, 11], [14, 15]),
    "(W10,W11,W12,W13 | W14,W15)":         ([10, 11, 12, 13], [14, 15]),
    "(W2,W10 | W14,W15)":                  ([2, 10], [14, 15]),
    "(W3..W11 | W14,W15)  [big A]":        ([3,4,5,6,7,8,9,10,11], [14, 15]),
}

if __name__ == "__main__":
    print("Joint separability of (delta_e_17, delta_e_18) over bipartitions")
    print("(separable side => frac_zero = 1.000; coupled => ~0)\n")
    print(f"{'bipartition':<38} {'de17_0':>7} {'de18_0':>7} {'both_0':>7} "
          f"{'mxz17':>7} {'mxz18':>7}")
    for name, (A, B) in CANDIDATES.items():
        f17, f18, fb, z17, z18 = joint_sep(chain_de17_de18, A, B)
        print(f"{name:<38} {f17:>7.3f} {f18:>7.3f} {fb:>7.3f} "
              f"{z17:>7.1f} {z18:>7.1f}")
    # RO control on the r17 split
    rf17, rf18, rfb, rz17, rz18 = joint_sep(ro_eval, [10, 11], [14])
    print(f"{'RO control (W10,W11 | W14)':<38} {rf17:>7.3f} {rf18:>7.3f} "
          f"{rfb:>7.3f} {rz17:>7.1f} {rz18:>7.1f}")
    print("\nVerdict: 2D-MITM (18 zeros at ~2^32 vs 2^64) is possible ONLY if")
    print("some bipartition shows both_0 = 1.000. Else the second barrier")
    print("blocks composition and T_BARRIER_16 = 2^64 stands.")
