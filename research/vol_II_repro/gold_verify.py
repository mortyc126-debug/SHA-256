"""
GOLD-STANDARD independent check of a MITM-found 17-zero pair.

The MITM and full_chain_deltas both use the Wang-correction machinery, which
could in principle be self-consistently fooling itself.  This script removes
all doubt: it takes a found hit, reconstructs the TWO actual 16-word messages
(W_n and W_f), then runs the PLAIN verified SHA-256 compression (the one that
matches hashlib) on each, reads the raw e-register sequence, and checks
e_r(f) - e_r(n) == 0 for r = 2..17 with NO differential logic involved.

If this passes, the 17-zero pair is real and the MITM genuinely produces what
П-97 produced by 2^33 brute force.
"""

import random
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1, e_sequence


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def build_messages(base, delta=0x80000000):
    """Run the Wang chain and RECORD the actual Wn[0..15] and Wf[0..15]."""
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
    return Wn, Wf


def barrier(base, delta=0x80000000):
    Wn, Wf = build_messages(base, delta)
    # round 16 schedule word + read e_17 difference, the MITM target
    en = e_sequence(_expand(Wn), IV, 17)
    ef = e_sequence(_expand(Wf), IV, 17)
    return (ef[17] - en[17]) & MASK


def _expand(W16):
    W = list(W16) + [0] * 48
    for t in range(16, 64):
        W[t] = (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
    return W


def find_one_hit(list_bits=16, delta=0x80000000, seed=3):
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    a0 = (base[10], base[11])
    c0 = base[14]

    def B(a, c):
        b = list(base)
        b[10], b[11], b[14] = a[0], a[1], c
        return barrier(b, delta)

    gc0 = B(a0, c0)
    L = 1 << list_bits
    sideA = {}
    for _ in range(L):
        a = (rng.getrandbits(32), rng.getrandbits(32))
        sideA.setdefault(B(a, c0), a)
    for _ in range(L):
        c = rng.getrandbits(32)
        key = (-(B(a0, c) - gc0)) & MASK
        if key in sideA:
            a = sideA[key]
            b = list(base)
            b[10], b[11], b[14] = a[0], a[1], c
            return b
    return None


def gold_check(base, delta=0x80000000):
    """Reconstruct both messages, run PLAIN SHA-256, check e2..e17 deltas."""
    Wn, Wf = build_messages(base, delta)
    en = e_sequence(_expand(Wn), IV, 17)  # e_0..e_17 via plain compression
    ef = e_sequence(_expand(Wf), IV, 17)
    deltas = [(ef[r] - en[r]) & MASK for r in range(2, 18)]  # de2..de17
    # also confirm the two messages differ ONLY by the intended schedule-driven
    # structure (W0 differs by delta; W1..W15 differ by the corrections)
    w0diff = (Wf[0] - Wn[0]) & MASK
    return deltas, Wn, Wf, w0diff


if __name__ == "__main__":
    print("Finding a 17-zero pair via MITM (list size 2^16)...")
    base = find_one_hit(list_bits=16)
    if base is None:
        print("  no hit at 2^16 lists (try larger); rerun.")
        raise SystemExit
    deltas, Wn, Wf, w0diff = gold_check(base)
    print(f"  W0 difference (delta): 0x{w0diff:08x}")
    print(f"  Wn[0..5] = {[hex(x) for x in Wn[:6]]}")
    print(f"  Wf[0..5] = {[hex(x) for x in Wf[:6]]}")
    print()
    print("GOLD CHECK (plain verified SHA-256, raw e-register, NO diff logic):")
    labels = [f"de{r}" for r in range(2, 18)]
    allzero = all(d == 0 for d in deltas)
    for lab, d in zip(labels, deltas):
        mark = "" if d == 0 else "  <-- NONZERO"
        print(f"    {lab:>5} = 0x{d:08x}{mark}")
    print()
    print(f"  e2..e17 ALL zero on plain SHA-256: {allzero}")
    if allzero:
        print("  => MITM-found pair is a GENUINE 17-zero (delta_e_2..17=0) Wang pair,")
        print("     reproduced by raw SHA-256.  Confirms the sub-2^32 cost is real.")
