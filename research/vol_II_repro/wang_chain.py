"""
Re-verification of the central Volume II result: T_WANG_CHAIN (П-26/П-92).

Claim (unified/02_vol_II/04_wang_chain_p23_p101.md §II.4.6):
  Starting from two messages differing only in W0 by delta, an adaptive
  correction delta_W_r applied at each round r = 1..15 forces
      delta_e_2 = delta_e_3 = ... = delta_e_16 = 0   with P = 1.0,
  while delta_e_17 is uncontrollable (P ~ 2^-32) -- the r=17 barrier,
  because W[16] is fixed by the message schedule, not a free word.

Mechanism (T_WANG_ADAPTIVE, §II.4.4):
  e_{r+1} = d_r + T1_r,  T1_r = h_r + Sig1(e_r) + Ch(e_r,f_r,g_r) + K_r + W_r
  => delta_e_{r+1} = delta_d_r + delta_h_r + delta_Sig1(e_r)
                     + delta_Ch(e_r,f_r,g_r) + delta_W_r
  Choosing delta_W_r = -(everything except delta_W_r) gives delta_e_{r+1}=0.

We run two FULL parallel SHA-256 states (n and f) round by round, using
free words W[1..15] with the adaptive correction, and read delta_e at each
round.  No characteristic, no probability -- pure algebra, so it must be
exact for every base message if the claim holds.
"""

import random
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def wang_run(delta=0x80000000, n_free_corrections=15, rng=None, base=None):
    """
    Returns the list of delta_e_r for r = 1 .. n_free_corrections+2.
    delta_e_r = e_r(f) - e_r(n) mod 2^32.
    """
    if rng is None:
        rng = random
    # base message words W0..W15 for the 'n' (reference) message
    if base is None:
        base = [rng.getrandbits(32) for _ in range(16)]
    W0 = base[0]

    sn = tuple(IV)
    sf = tuple(IV)

    # round 0: only W0 differs by delta
    Wn0 = W0
    Wf0 = (W0 + delta) & MASK
    sn = one_round(sn, Wn0, 0)
    sf = one_round(sf, Wf0, 0)

    delta_e = []  # delta_e_1, delta_e_2, ...
    delta_e.append((sf[4] - sn[4]) & MASK)  # delta_e_1 (= nonzero, uncontrolled)

    # rounds 1..n_free_corrections : adaptive correction to kill delta_e_{r+1}
    for r in range(1, n_free_corrections + 1):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        # delta_e_{r+1} = delta_d_r + delta_h_r + delta_Sig1(e_r)
        #               + delta_Ch(e_r,f_r,g_r) + delta_W_r
        ddelta = (df - dn) & MASK
        hdelta = (hf - hn) & MASK
        sig1delta = (Sig1(ef) - Sig1(en)) & MASK
        chdelta = (Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK
        # base free word for round r (same nominal value for both messages)
        Wn_r = base[r] if r < 16 else 0
        dW_r = (-(ddelta + hdelta + sig1delta + chdelta)) & MASK
        Wf_r = (Wn_r + dW_r) & MASK
        sn = one_round(sn, Wn_r, r)
        sf = one_round(sf, Wf_r, r)
        delta_e.append((sf[4] - sn[4]) & MASK)  # delta_e_{r+1}

    return delta_e  # delta_e[k] is delta_e_{k+1}


def main(trials=1000, delta=0x80000000, seed=12345):
    rng = random.Random(seed)
    # zeros we EXPECT to be forced: delta_e_2 .. delta_e_16  (indices 1..15 in list)
    all_zero_hits = 0
    e17_zero = 0
    e17_samples = []
    for _ in range(trials):
        de = wang_run(delta=delta, n_free_corrections=15, rng=rng)
        # de[0]=de1, de[1]=de2, ..., de[15]=de16
        controlled = de[1:16]  # de2..de16  (15 values)
        if all(x == 0 for x in controlled):
            all_zero_hits += 1
        # to probe the barrier we need delta_e_17 -> one more round with a
        # SCHEDULE-DERIVED word (not free).  Done separately below.
    print(f"delta = 0x{delta:08x}, trials = {trials}")
    print(f"  delta_e_2..delta_e_16 all zero: {all_zero_hits}/{trials} "
          f"(claim: P=1.0)")

    # --- r=17 barrier: extend with the real schedule word W16 ---
    barrier_zero = 0
    for _ in range(trials):
        de17 = wang_run_to_17(delta=delta, rng=rng)
        if de17 == 0:
            barrier_zero += 1
    print(f"  delta_e_17 == 0 (schedule-forced W16): {barrier_zero}/{trials} "
          f"(claim: P ~ 2^-32, i.e. ~0)")


def wang_run_to_17(delta=0x80000000, rng=None):
    """
    Same Wang chain but we now must produce W[16] from the *actual* schedule
    of each message, so delta_W_16 is NOT free -> probes the r=17 barrier.
    Returns delta_e_17.
    """
    if rng is None:
        rng = random
    base = [rng.getrandbits(32) for _ in range(16)]
    # We build the full corrected W0..W15 for both messages first, then run.
    # Reference and faulted message words:
    Wn = [0] * 16
    Wf = [0] * 16
    sn = tuple(IV)
    sf = tuple(IV)
    Wn[0] = base[0]
    Wf[0] = (base[0] + delta) & MASK
    sn = one_round(sn, Wn[0], 0)
    sf = one_round(sf, Wf[0], 0)
    for r in range(1, 16):
        an, bn, cn, dn, en, fn, gn, hn = sn
        af, bf, cf, df, ef, ff, gf, hf = sf
        ddelta = (df - dn) & MASK
        hdelta = (hf - hn) & MASK
        sig1delta = (Sig1(ef) - Sig1(en)) & MASK
        chdelta = (Ch(ef, ff, gf) - Ch(en, fn, gn)) & MASK
        Wn[r] = base[r]
        dW_r = (-(ddelta + hdelta + sig1delta + chdelta)) & MASK
        Wf[r] = (Wn[r] + dW_r) & MASK
        sn = one_round(sn, Wn[r], r)
        sf = one_round(sf, Wf[r], r)
    # now round 16 uses schedule-derived W16 for each message independently
    from sha256_core import sig0, sig1
    W16n = (sig1(Wn[14]) + Wn[9] + sig0(Wn[1]) + Wn[0]) & MASK
    W16f = (sig1(Wf[14]) + Wf[9] + sig0(Wf[1]) + Wf[0]) & MASK
    sn = one_round(sn, W16n, 16)
    sf = one_round(sf, W16f, 16)
    return (sf[4] - sn[4]) & MASK


if __name__ == "__main__":
    # The unified text uses delta = 0x8000 in places and 0x80000000 in others;
    # the mechanism is delta-agnostic, so we test both.
    main(trials=1000, delta=0x80000000)
    print()
    main(trials=1000, delta=0x00008000)
