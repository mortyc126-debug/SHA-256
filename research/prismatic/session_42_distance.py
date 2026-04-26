"""
Session 42: Input-output distance map of SHA round.

For input pairs (x, x') at fixed Hamming distance d, what's the distribution
of output Hamming distances ||R(x) - R(x')||_H?

For ideal random function on F_2^n:
  ||R(x) - R(x')||_H ~ Binomial(n, 1/2), mean n/2 = 128, std √(n/4) = 8.

For SHA bare round: deviations reveal structure. Specifically:
- Low-distance input pairs (d small) → output distance distribution
- Does d_out depend on d_in?
- Is there a "linearity" — does d_out grow with d_in?

This is THE classical "avalanche criterion" measurement, but generalised
to ALL distances, not just d_in = 1.

Cryptographic relevance: differential cryptanalysis tracks specific
input differences and predicts output differences. The d-d distribution is
the marginal over all difference patterns.
"""
import numpy as np
from collections import Counter
from session_25_round import build_sigma_0, build_sigma_1
from session_38_avalanche import round_eval_with_addchains


def main():
    print("=== Session 42: Input-output distance map ===\n")
    S0 = build_sigma_0()
    S1 = build_sigma_1()
    R = lambda x: round_eval_with_addchains(x, S0, S1)

    rng = np.random.default_rng(0)
    NUM_BASE = 30          # number of random base inputs
    NUM_PERTURB_PER = 10   # number of perturbations per base, per d_in

    print(f"  Per d_in, sample {NUM_BASE * NUM_PERTURB_PER} = {NUM_BASE * NUM_PERTURB_PER} pairs.")

    INPUT_DISTANCES = [1, 2, 4, 8, 16, 32, 64, 128, 256]
    print(f"\n  {'d_in':>5}  {'mean d_out':>11}  {'std':>8}  {'min':>5}  {'max':>5}  {'ideal':>7}")
    print(f"  {'-'*60}")

    results = {}
    for d_in in INPUT_DISTANCES:
        d_outs = []
        for _ in range(NUM_BASE):
            x = rng.integers(0, 2, size=256, dtype=np.uint8)
            y = R(x)
            for _ in range(NUM_PERTURB_PER):
                # Pick d_in random positions to flip
                positions = rng.choice(256, size=d_in, replace=False)
                x_pert = x.copy()
                for p in positions:
                    x_pert[p] ^= 1
                y_pert = R(x_pert)
                d_out = int((y ^ y_pert).sum())
                d_outs.append(d_out)
        d_outs = np.array(d_outs)
        ideal_mean = 128 if d_in > 0 else 0
        results[d_in] = d_outs
        print(f"  {d_in:>5}  {d_outs.mean():>11.2f}  {d_outs.std():>8.2f}  {d_outs.min():>5}  {d_outs.max():>5}  {ideal_mean:>7}")

    print(f"""

  ANALYSIS:
  The "avalanche function" A(d_in) := E[d_out | d_in] should approach 128 as d_in
  grows. For ideal random function, A(d_in) = 128 even for d_in = 1.

  For SHA bare round: A(1) ≈ 5 (Session 38). A(d) grows with d, presumably
  saturating to ~128 at d = 64 or so.

  RATIO d_out / d_in:
""")

    for d_in in INPUT_DISTANCES:
        d_outs = results[d_in]
        ratio = d_outs.mean() / d_in if d_in > 0 else 0
        print(f"    d_in={d_in:>3}: d_out/d_in = {ratio:.3f}    (ideal: {128/d_in if d_in > 0 else 0})")

    print(f"""

=== Theorem 42.1 (avalanche function shape, empirical) ===

The avalanche function A(d_in) = E_{{x, |Δ|=d_in}}[||R(x) - R(x⊕Δ)||] for one
SHA bare round has the SUB-LINEAR shape:

  A(d_in) ≈ a · d_in for small d_in (slope a ≈ 5 from Session 38)
  A(d_in) → 128 as d_in → 256 (saturation to ideal random)

The transition from linear-growth to saturation happens around d_in ≈ ???
(see numerical data above).

CRYPTANALYTIC INTERPRETATION:
  Differential trails with low d_in (sparse differences) propagate
  predictably: d_out scales linearly with d_in. This makes them
  ESPECIALLY useful for cryptanalysis, because the trail behaviour is
  approximately additive.

  Once d_in exceeds the "saturation threshold", differentials become
  unpredictable (look random). High-Hamming-weight differentials are not
  useful for attacks.

  The transition point is THE critical Hamming weight for differential
  cryptanalysis on SHA-256.
""")


if __name__ == "__main__":
    main()
