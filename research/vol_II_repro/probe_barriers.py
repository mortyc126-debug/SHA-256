"""
(1) Systematic re-test of the methodology's barrier-cost claims with the
disjoint-influence split that cracked r=17.

Question: was T_2D_BIRTHDAY_NEGATIVE's oversight (testing separability only
over a SHARED word pair) a one-off, or do other "barrier = 2^N" claims hide
the same crack?

Structural hypothesis (from delta_e_r = Da_{r-4} + ΔW_{r-1}):
  ΔW16 = sig1(W14)+W9+sig0(W1)+W0   -> unique free late word = W14
  ΔW17 = sig1(W15)+W10+sig0(W2)+W1  -> unique free late word = W15
  ΔW18 = sig1(W16)+W11+sig0(W3)+W2  -> W16 is COMPUTED, no free late word
  ΔW19 = sig1(W17)+W12+sig0(W4)+W3  -> W17 computed, no free late word
=> Predict: delta_e_17 cracks (via W14), delta_e_18 cracks alone (via W15),
   delta_e_19 / delta_e_20 do NOT (no free late word remains). And NO
   consecutive pair composes (the wall), since a single split can't serve
   two barriers whose late words differ.

For each barrier we test exact additive separability over the analytic
disjoint split + an RO control, and we test joint separability of pairs.
"""

import random
import math
import hashlib
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def chain_des(base, delta=0x80000000, upto=20):
    """Wang chain (corrections r=1..15) then schedule rounds 16..upto-1.
    Returns dict de[r] = delta_e_r for r = 17..upto."""
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

    def sched(W, t):
        return (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK

    de = {}
    for r in range(16, upto):
        Wn_t = sched(Wn, r); Wf_t = sched(Wf, r)
        Wn = Wn + [Wn_t]; Wf = Wf + [Wf_t]
        sn = one_round(sn, Wn_t, r)
        sf = one_round(sf, Wf_t, r)
        de[r + 1] = (sf[4] - sn[4]) & MASK   # delta_e_{r+1}
    return de


def influence(target_r, trials=300, delta=0x80000000, seed=1):
    rng = random.Random(seed)
    moved = {i: 0 for i in range(16)}
    for _ in range(trials):
        base = [rng.getrandbits(32) for _ in range(16)]
        d0 = chain_des(base, delta, upto=target_r)[target_r]
        for i in range(16):
            b2 = list(base)
            b2[i] ^= (1 << rng.randrange(32))
            if chain_des(b2, delta, upto=target_r)[target_r] != d0:
                moved[i] += 1
    return [i for i in range(16) if moved[i] == 0], \
           {i: moved[i] / trials for i in range(16)}


def sep_single(target_r, A, B, samples=3000, delta=0x80000000, seed=2,
               eval_ro=False):
    """Exact additive separability of delta_e_{target_r} over (A | B)."""
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    nz = 0
    bits = [0] * 32

    def setw(b, idxs, vals):
        for i, v in zip(idxs, vals):
            b[i] = v

    def ev(av, bv):
        b = list(base)
        setw(b, A, av); setw(b, B, bv)
        if eval_ro:
            msg = b"".join((w & MASK).to_bytes(4, "big") for w in b)
            return int.from_bytes(hashlib.blake2b(
                msg, digest_size=4, key=b"ro").digest(), "big")
        return chain_des(b, delta, upto=target_r)[target_r]

    for _ in range(samples):
        Ax = [rng.getrandbits(32) for _ in A]
        Ay = [rng.getrandbits(32) for _ in A]
        Bx = [rng.getrandbits(32) for _ in B]
        By = [rng.getrandbits(32) for _ in B]
        m = (ev(Ax, Bx) - ev(Ax, By) - ev(Ay, Bx) + ev(Ay, By)) & MASK
        if m:
            nz += 1
        for bit in range(32):
            bits[bit] += (m >> bit) & 1
    maxz = max(abs((o - samples / 2) / math.sqrt(samples / 4)) for o in bits)
    return 1 - nz / samples, maxz


def sep_joint(rs, A, B, samples=3000, delta=0x80000000, seed=3):
    """Joint separability: ALL barriers in rs must have vanishing mixed diff."""
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    upto = max(rs)
    bothzero = 0

    def setw(b, idxs, vals):
        for i, v in zip(idxs, vals):
            b[i] = v

    def ev(av, bv):
        b = list(base)
        setw(b, A, av); setw(b, B, bv)
        d = chain_des(b, delta, upto=upto)
        return [d[r] for r in rs]

    for _ in range(samples):
        Ax = [rng.getrandbits(32) for _ in A]
        Ay = [rng.getrandbits(32) for _ in A]
        Bx = [rng.getrandbits(32) for _ in B]
        By = [rng.getrandbits(32) for _ in B]
        vxx = ev(Ax, Bx); vxy = ev(Ax, By)
        vyx = ev(Ay, Bx); vyy = ev(Ay, By)
        allz = True
        for k in range(len(rs)):
            m = (vxx[k] - vxy[k] - vyx[k] + vyy[k]) & MASK
            if m:
                allz = False
                break
        if allz:
            bothzero += 1
    return bothzero / samples


if __name__ == "__main__":
    print("=== influence maps (which free words move delta_e_r) ===")
    inert = {}
    for r in (17, 18, 19, 20):
        inrt, frac = influence(r, trials=200)
        inert[r] = inrt
        active = [i for i in range(16) if frac[i] > 0.5]
        print(f"  delta_e_{r}: inert words {inrt}; active(>0.5) {active}")

    print("\n=== single-barrier separability over analytic disjoint split ===")
    print("    (frac_zero = 1.000 => exactly separable => single-barrier MITM)")
    # analytic late-word splits
    splits = {
        17: ([10, 11], [14]),
        18: ([11, 12], [15]),
        19: ([11, 12], [13]),     # no free late word -> expect coupled
        20: ([10, 11], [13]),     # no free late word -> expect coupled
    }
    for r, (A, B) in splits.items():
        fz, mz = sep_single(r, A, B)
        ro_fz, ro_mz = sep_single(r, A, B, eval_ro=True)
        tag = "SEPARABLE (cracks)" if fz > 0.999 else "coupled (holds)"
        print(f"  delta_e_{r}  split({A}|{B}): frac_zero={fz:.3f} "
              f"maxz={mz:.1f} | RO frac_zero={ro_fz:.3f}  -> {tag}")

    print("\n=== joint composition (do consecutive barriers share a split?) ===")
    for rs, (A, B) in [((17, 18), ([10, 11], [14])),
                       ((18, 19), ([11, 12], [15])),
                       ((17, 18, 19), ([10, 11], [14]))]:
        bz = sep_joint(list(rs), A, B, samples=2000)
        tag = "COMPOSES (wall falls!)" if bz > 0.999 else "does NOT compose (wall holds)"
        print(f"  barriers {rs} over ({A}|{B}): joint_zero={bz:.3f} -> {tag}")
