"""
Escalation of T_2D_BIRTHDAY_NEGATIVE (П-27C).

П-27C tested additive separability of the r=17 barrier B(W0,W1) = delta_e_17
over a SINGLE word pair and found it non-separable (mixed 2nd-difference
never zero). This is the untried generalization:

  (P1) Influence map: which of the 16 free words actually move delta_e_17?
       Analytic prediction (from delta_e_17 = Da13 + dW16):
         Da13  depends on words used in rounds 0..12  -> W0..W12
         dW16  depends on the schedule W16 = sig1(W14)+W9+sig0(W1)+W0
                                            -> W0, W1, W9, W14
       => W13, W15 should be INERT for delta_e_17. (testable)

  (P2) All-pairs mixed 2nd-difference: extend П-27C from 1 pair to all
       C(16,2)=120 pairs; per-bit balance with z-scores + Bonferroni.
       A biased bit = partial separability = the first crack toward a MITM
       split of the barrier.

  (P3) Targeted analytic split: fix the SHARED words {W0,W1,W9}; let set
       S1 (affects Da13) and {W14} (affects dW16) vary on opposite sides.
       If the shared-word coupling is the only thing blocking separability,
       freezing it should expose structure. This is the concrete
       MITM-split hypothesis.

  (RO) Control: re-run P2/P3 with the barrier replaced by a per-input random
       oracle (keyed BLAKE2b of the same inputs). Phase 8C lesson: any
       "bias" must beat its OWN RO baseline under the identical protocol,
       or it is a harness artifact.
"""

import random
import hashlib
import math
from itertools import combinations
from sha256_core import IV, K, MASK, Sig0, Sig1, Ch, Maj, sig0, sig1


def one_round(state, w, r):
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + w) & MASK
    T2 = (Sig0(a) + Maj(a, b, c)) & MASK
    return ((T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g)


def barrier(base, delta=0x80000000):
    """delta_e_17 under the Wang chain (corrections r=1..15) with the given
    16 base words; round 16 uses the schedule-forced W16."""
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
    W16n = (sig1(Wn[14]) + Wn[9] + sig0(Wn[1]) + Wn[0]) & MASK
    W16f = (sig1(Wf[14]) + Wf[9] + sig0(Wf[1]) + Wf[0]) & MASK
    sn = one_round(sn, W16n, 16)
    sf = one_round(sf, W16f, 16)
    return (sf[4] - sn[4]) & MASK


def ro_barrier(base, delta=0x80000000):
    """Random-oracle control: a uniform 32-bit value keyed by the ACTUAL
    word values (must depend on every word, no inert words), so that the
    mixed 2nd-difference of a genuinely structureless function is sampled
    under the identical protocol (Phase 8C requirement)."""
    msg = b"".join((w & MASK).to_bytes(4, "big") for w in base)
    msg += (delta & MASK).to_bytes(4, "big")
    h = hashlib.blake2b(msg, digest_size=8, key=b"ro-control").digest()
    return int.from_bytes(h[:4], "big")


# ---------------------------------------------------------------- P1

def influence_map(trials=400, delta=0x80000000, seed=1):
    rng = random.Random(seed)
    moved = {i: 0 for i in range(16)}
    for _ in range(trials):
        base = [rng.getrandbits(32) for _ in range(16)]
        b0 = barrier(base, delta)
        for i in range(16):
            b2 = list(base)
            b2[i] ^= (1 << rng.randrange(32))  # flip one random bit of word i
            if barrier(b2, delta) != b0:
                moved[i] += 1
    print("P1  influence on delta_e_17 (fraction of single-bit flips that move it):")
    for i in range(16):
        tag = ""
        if moved[i] == 0:
            tag = "  <- INERT"
        print(f"    W[{i:2d}]: {moved[i]/trials:5.2f}{tag}")
    inert = [i for i in range(16) if moved[i] == 0]
    print(f"    predicted inert {{13,15}} ; observed inert {inert}")
    return inert


# ---------------------------------------------------------------- P2

def mixed_second_diff(eval_fn, base, i, j, rng, delta):
    """B(xi,xj)-B(xi,yj)-B(yi,xj)+B(yi,yj) over words i,j (others = base)."""
    xi, yi = rng.getrandbits(32), rng.getrandbits(32)
    xj, yj = rng.getrandbits(32), rng.getrandbits(32)

    def ev(wi, wj):
        b = list(base)
        b[i] = wi
        b[j] = wj
        return eval_fn(b, delta)
    return (ev(xi, xj) - ev(xi, yj) - ev(yi, xj) + ev(yi, yj)) & MASK


def per_bit_z(values, n):
    """For a list of 32-bit values, per-bit P(bit=1) z-score vs 0.5.
    Returns max |z| over 32 bits and the argmax bit."""
    best_z, best_bit = 0.0, -1
    for bit in range(32):
        ones = sum((v >> bit) & 1 for v in values)
        # null: Binomial(n, 0.5)
        z = (ones - n / 2) / math.sqrt(n / 4)
        if abs(z) > abs(best_z):
            best_z, best_bit = z, bit
    return best_z, best_bit


def all_pairs_scan(eval_fn, label, samples=2000, delta=0x80000000, seed=2):
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    results = []
    exact_zero_total = 0
    for (i, j) in combinations(range(16), 2):
        vals = [mixed_second_diff(eval_fn, base, i, j, rng, delta)
                for _ in range(samples)]
        ez = sum(1 for v in vals if v == 0)
        exact_zero_total += ez
        z, bit = per_bit_z(vals, samples)
        results.append((abs(z), z, bit, i, j, ez))
    results.sort(reverse=True)
    # Bonferroni over 120 pairs * 32 bits = 3840 tests => 5-sigma-ish
    n_tests = 120 * 32
    thresh = abs(_inv_norm(1 - 0.05 / (2 * n_tests)))
    print(f"\nP2  all-pairs mixed 2nd-difference [{label}] "
          f"(samples={samples}/pair):")
    print(f"    exact-zero mixed diffs across all 120 pairs: {exact_zero_total}")
    print(f"    Bonferroni |z| threshold ({n_tests} tests): {thresh:.2f}")
    print(f"    top 5 most-biased (pair, bit, z):")
    for absz, z, bit, i, j, ez in results[:5]:
        flag = "  *** EXCEEDS ***" if absz > thresh else ""
        print(f"      (W{i:2d},W{j:2d}) bit{bit:2d}  z={z:+6.2f}  ez={ez}{flag}")
    return results[0][0], thresh


def _inv_norm(p):
    # Acklam's inverse normal CDF approximation (good to ~1e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= 1 - pl:
        q = p - 0.5
        r = q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


# ---------------------------------------------------------------- P3

def targeted_split(eval_fn, label, samples=4000, delta=0x80000000, seed=3):
    """
    Fix shared words {0,1,9}. Vary an S1 word (affects Da13) on one side and
    W14 (affects dW16) on the other; measure mixed 2nd-difference per bit.
    S1 representative: W5 (a mid-chain word, pure Da13 influence).
    """
    rng = random.Random(seed)
    base = [rng.getrandbits(32) for _ in range(16)]
    # freeze shared words to fixed constants
    for s in (0, 1, 9):
        base[s] = rng.getrandbits(32)
    i, j = 5, 14  # S1 side, dW16 side
    vals = [mixed_second_diff(eval_fn, base, i, j, rng, delta)
            for _ in range(samples)]
    ez = sum(1 for v in vals if v == 0)
    z, bit = per_bit_z(vals, samples)
    n_tests = 32
    thresh = abs(_inv_norm(1 - 0.05 / (2 * n_tests)))
    flag = "  *** EXCEEDS ***" if abs(z) > thresh else ""
    print(f"\nP3  targeted split (W5 | W14, shared {{0,1,9}} fixed) [{label}]:")
    print(f"    exact-zero: {ez}/{samples}; max|z| bit{bit}={z:+.2f} "
          f"(Bonferroni-32 thresh {thresh:.2f}){flag}")
    return abs(z), thresh


if __name__ == "__main__":
    print("=" * 64)
    inert = influence_map()

    print("\n" + "=" * 64)
    sha_z, thr = all_pairs_scan(barrier, "SHA barrier")
    ro_z, _ = all_pairs_scan(ro_barrier, "RO control")
    print(f"\n  P2 verdict: SHA max|z|={sha_z:.2f}, RO max|z|={ro_z:.2f}, "
          f"thresh={thr:.2f}")
    print("    -> crack only if SHA exceeds threshold AND clearly beats RO.")

    print("\n" + "=" * 64)
    s_z, s_thr = targeted_split(barrier, "SHA barrier")
    r_z, _ = targeted_split(ro_barrier, "RO control")
    print(f"\n  P3 verdict: SHA max|z|={s_z:.2f}, RO max|z|={r_z:.2f}, "
          f"thresh={s_thr:.2f}")
