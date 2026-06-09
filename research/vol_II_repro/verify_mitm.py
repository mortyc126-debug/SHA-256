"""
DECISIVE test of the candidate r=17 MITM split found by probe_split_scan.py.

The scan indicated the barrier delta_e_17 is ADDITIVELY SEPARABLE across
(W10,W11) vs W14 when all other free words are fixed:
        delta_e_17  =  f(W10,W11)  +  g(W14)   (mod 2^32)
because W10,W11 feed only Da13 and W14 feeds only dW16, with no shared
correction coupling.  T_2D_BIRTHDAY_NEGATIVE (П-27C) tested (W0,W1) -- both
SHARED words -- and so missed this split.

If separable, a meet-in-the-middle finds delta_e_17 = 0 (the 17th zero) at
cost ~2^16 instead of the methodology's stated 2^32.  We:
  (1) verify EXACT separability (mixed 2nd-difference == 0, not just biased);
  (2) measure the value-entropy of each side (does g(W14) cover enough?);
  (3) actually RUN the MITM, find delta_e_17 == 0 pairs, and VERIFY each by
      running the full Wang chain and checking delta_e_2..delta_e_17 all zero;
  (4) report the real cost vs 2^32.

No claim is made unless (3) produces verified 17-zero pairs at sub-2^32 cost.
"""

import random
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def full_chain_deltas(base, delta=0x80000000):
    """Return list delta_e_2 .. delta_e_17 (16 values) for the Wang chain."""
    Wn = [0] * 16
    Wf = [0] * 16
    sn = tuple(IV)
    sf = tuple(IV)
    Wn[0] = base[0] & MASK
    Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0)
    sf = one_round(sf, Wf[0], 0)
    des = []
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
        des.append((sf[4] - sn[4]) & MASK)  # delta_e_{r+1}, r+1 = 2..16
    W16n = (sig1(Wn[14]) + Wn[9] + sig0(Wn[1]) + Wn[0]) & MASK
    W16f = (sig1(Wf[14]) + Wf[9] + sig0(Wf[1]) + Wf[0]) & MASK
    sn = one_round(sn, W16n, 16)
    sf = one_round(sf, W16f, 16)
    des.append((sf[4] - sn[4]) & MASK)  # delta_e_17
    return des  # length 16: de2..de17


def barrier(base, delta=0x80000000):
    return full_chain_deltas(base, delta)[-1]  # delta_e_17


# --- (1) exact separability over (W10,W11) | W14 ----------------------------

def test_exact_separability(trials=3000, delta=0x80000000, seed=1):
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    nonzero = 0
    for _ in range(trials):
        a0 = (rng.getrandbits(32), rng.getrandbits(32))  # (W10,W11)
        a1 = (rng.getrandbits(32), rng.getrandbits(32))
        c0 = rng.getrandbits(32)  # W14
        c1 = rng.getrandbits(32)

        def B(a, c):
            b = list(base)
            b[10], b[11], b[14] = a[0], a[1], c
            return barrier(b, delta)
        mixed = (B(a0, c0) - B(a0, c1) - B(a1, c0) + B(a1, c1)) & MASK
        if mixed != 0:
            nonzero += 1
    print(f"(1) EXACT separability  delta_e_17 = f(W10,W11) + g(W14):")
    print(f"    mixed 2nd-difference != 0 : {nonzero}/{trials}")
    print(f"    -> separable iff 0/{trials}")
    return nonzero == 0


# --- (2) value entropy of each side -----------------------------------------

def measure_entropy(n=1 << 16, delta=0x80000000, seed=2):
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    a0 = (base[10], base[11])
    c0 = base[14]

    def B(a, c):
        b = list(base)
        b[10], b[11], b[14] = a[0], a[1], c
        return barrier(b, delta)

    fvals = set()
    for _ in range(n):
        a = (rng.getrandbits(32), rng.getrandbits(32))
        fvals.add(B(a, c0))
    gvals = set()
    for _ in range(n):
        c = rng.getrandbits(32)
        gvals.add((B(a0, c) - B(a0, c0)) & MASK)
    import math
    print(f"(2) value-entropy of each side (from {n} samples):")
    print(f"    distinct f(W10,W11): {len(fvals):>7}  "
          f"(~2^{math.log2(max(1,len(fvals))):.1f})")
    print(f"    distinct g(W14)    : {len(gvals):>7}  "
          f"(~2^{math.log2(max(1,len(gvals))):.1f})")
    return len(fvals), len(gvals)


# --- (3) the actual MITM + full verification --------------------------------

def run_mitm(list_bits=17, delta=0x80000000, seed=3):
    """Build L_A from (W10,W11), L_B from W14, find delta_e_17 == 0, then
    VERIFY each hit by the full Wang chain (delta_e_2..delta_e_17 all zero)."""
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    a0 = (base[10], base[11])
    c0 = base[14]

    def B(a, c):
        b = list(base)
        b[10], b[11], b[14] = a[0], a[1], c
        return barrier(b, delta)

    const = B(a0, c0)  # = f(a0)+g(c0)

    L = 1 << list_bits
    # Side A: f(a) = B(a, c0).  We want f(a) + (g(c)-g(c0)) + ... = 0.
    # With separability: B(a,c) = f(a) + g(c) - const + const ... use identity
    #   B(a,c) = B(a,c0) + B(a0,c) - B(a0,c0)
    # so B(a,c)=0  <=>  B(a,c0) = -(B(a0,c) - B(a0,c0))  (mod 2^32)
    # Build map from B(a,c0) -> a ; probe with key = -(B(a0,c)-B(a0,c0)).
    print(f"(3) MITM for delta_e_17 == 0  (list size 2^{list_bits} each):")
    sideA = {}
    evalsA = 0
    for _ in range(L):
        a = (rng.getrandbits(32), rng.getrandbits(32))
        sideA.setdefault(B(a, c0), a)
        evalsA += 1
    gc0 = B(a0, c0)
    hits = []
    evalsB = 0
    for _ in range(L):
        c = rng.getrandbits(32)
        key = (-(B(a0, c) - gc0)) & MASK
        evalsB += 1
        if key in sideA:
            a = sideA[key]
            hits.append((a, c))
            if len(hits) >= 8:
                break

    print(f"    evaluations: A={evalsA}, B={evalsB} "
          f"(total ~2^{__import__('math').log2(evalsA+evalsB):.1f})")
    print(f"    candidate delta_e_17==0 hits found: {len(hits)}")

    # VERIFY each hit by the full chain
    verified = 0
    for (a, c) in hits:
        b = list(base)
        b[10], b[11], b[14] = a[0], a[1], c
        des = full_chain_deltas(b, delta)  # de2..de17
        if all(x == 0 for x in des):
            verified += 1
    print(f"    VERIFIED (delta_e_2..delta_e_17 ALL zero, full chain): "
          f"{verified}/{len(hits)}")
    if verified > 0:
        print(f"    => 17 zeros at ~2^{__import__('math').log2(evalsA+evalsB):.1f} "
              f"chain-evals vs methodology's stated 2^32 barrier.")
    return verified, evalsA + evalsB


if __name__ == "__main__":
    sep = test_exact_separability()
    print()
    measure_entropy()
    print()
    run_mitm(list_bits=17)
