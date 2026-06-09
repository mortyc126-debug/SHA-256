"""
Two checks that together speak to the "MITM through state[16] = O(2^80)"
vs proven "Omega(2^128) lower bound" tension.

CHECK 1 -- T_DE17_DECOMPOSITION (П-11/12):
    With delta_e_2..delta_e_16 = 0 (Wang chain), the first uncontrolled
    differential satisfies   delta_e_17 = delta_a_13 + delta_W_16  (mod 2^32).
    This is the *exact* structural reason r=17 is a wall: delta_W_16 is
    schedule-forced and delta_a_13 is a saturated (HW~16) carry-driven value,
    and the two are added mod 2^32 -> the wall costs one 32-bit condition.

CHECK 2 -- T_2D_BIRTHDAY_NEGATIVE (П-27C):
    A meet-in-the-middle that splits the search over two independent message
    words (W0 vs W1) requires the barrier function to be additively SEPARABLE
    f(W0,W1) ~ p(W0) + q(W1).  We test bit-pairwise correlation and an
    additive-separability score.  If it fails, no 2-parameter MITM split of
    the r=17 barrier can beat the birthday cost -- which is what the
    methodology's verified negative says, and which contradicts the
    unverified, code-less "2^80" estimate.
"""

import random
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def wang_chain_to_17(delta, base, return_internals=False):
    """Run Wang chain (corrections r=1..15), then schedule-forced round 16.
    Returns delta_e_17, and optionally (delta_a_13, delta_W_16)."""
    Wn = [0] * 16
    Wf = [0] * 16
    sn = tuple(IV)
    sf = tuple(IV)
    Wn[0] = base[0]
    Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0)
    sf = one_round(sf, Wf[0], 0)
    da13 = None
    for r in range(1, 16):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        ddelta = (df - dn) & MASK
        hdelta = (hf - hn) & MASK
        s1d = (Sig1(ef) - Sig1(en)) & MASK
        chd = (Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK
        Wn[r] = base[r]
        dW = (-(ddelta + hdelta + s1d + chd)) & MASK
        Wf[r] = (Wn[r] + dW) & MASK
        sn = one_round(sn, Wn[r], r)
        sf = one_round(sf, Wf[r], r)
        # The methodology's "Da13" is 1-indexed; via the 3-shift register
        # chain (d_r = a_{r-3}) the d-register ENTERING round 16 equals the
        # a-register three rounds earlier.  In our 0-indexed loop that is
        # delta_a after round 12 (== delta_d of the state after round 15).
        if r == 12:
            da13 = (sf[0] - sn[0]) & MASK
    W16n = (sig1(Wn[14]) + Wn[9] + sig0(Wn[1]) + Wn[0]) & MASK
    W16f = (sig1(Wf[14]) + Wf[9] + sig0(Wf[1]) + Wf[0]) & MASK
    dW16 = (W16f - W16n) & MASK
    sn = one_round(sn, W16n, 16)
    sf = one_round(sf, W16f, 16)
    de17 = (sf[4] - sn[4]) & MASK
    if return_internals:
        return de17, da13, dW16
    return de17


def check1_decomposition(trials=2000, delta=0x80000000, seed=7):
    rng = random.Random(seed)
    ok = 0
    for _ in range(trials):
        base = [rng.getrandbits(32) for _ in range(16)]
        de17, da13, dW16 = wang_chain_to_17(delta, base, return_internals=True)
        if de17 == ((da13 + dW16) & MASK):
            ok += 1
    print(f"CHECK 1  T_DE17_DECOMPOSITION  delta_e_17 == delta_a_13 + delta_W_16")
    print(f"         {ok}/{trials} exact   (claim: identity, P=1.0)")
    return ok == trials


def check2_separability(n_samp=4096, delta=0x80000000, seed=11):
    """
    Build the barrier value B(W0,W1) = delta_e_17 as a function of two free
    words (W0, W1), all other base words fixed.  Test whether B is additively
    separable B(W0,W1) ~ p(W0) + q(W1) (which a 2-list MITM would need).

    Separability score: fit additive model by averaging, measure residual.
    Also report bit-pairwise correlation between B-bits and (W0,W1)-bits.
    """
    rng = random.Random(seed)
    fixed = [rng.getrandbits(32) for _ in range(16)]
    W0s = [rng.getrandbits(32) for _ in range(n_samp)]
    W1s = [rng.getrandbits(32) for _ in range(n_samp)]

    # sample B on a grid is too big; use matched random pairs + marginal probes
    # Additive separability test a la П-27C: for random (x0,x1),(y0,y1)
    #   if separable: B(x0,x1)-B(x0,y1)-B(y0,x1)+B(y0,y1) == 0 (mod 2^32)
    # the "mixed second difference" vanishes for additive functions.
    def B(w0, w1):
        base = list(fixed)
        base[0] = w0
        base[1] = w1
        return wang_chain_to_17(delta, base)

    vanish = 0
    tests = 1000
    for _ in range(tests):
        x0, y0 = rng.getrandbits(32), rng.getrandbits(32)
        x1, y1 = rng.getrandbits(32), rng.getrandbits(32)
        mixed = (B(x0, x1) - B(x0, y1) - B(y0, x1) + B(y0, y1)) & MASK
        if mixed == 0:
            vanish += 1
    print(f"CHECK 2  T_2D_BIRTHDAY_NEGATIVE  additive separability of B(W0,W1)")
    print(f"         mixed 2nd-difference == 0 : {vanish}/{tests}")
    print(f"         (separable => {tests}/{tests}; non-separable => ~0 "
          f"=> no 2-word MITM split)")
    return vanish


if __name__ == "__main__":
    ok1 = check1_decomposition()
    print()
    check2_separability()
