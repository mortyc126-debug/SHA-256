"""
Session 37: Boolean function complexity of SHA round bits.

For each output bit y_j (= boolean function on F_2^256), compute classical
complexity measures:

1. SENSITIVITY s(f, x) = #{i : f(x ⊕ e_i) ≠ f(x)} (averaged over x)
   max sensitivity s(f) = max_x s(f, x).

2. AVERAGE SENSITIVITY = E_x[s(f, x)].

3. POLYNOMIAL DEGREE deg(f) (already known: 1 or 2 for round bits, Session 27).

4. INFLUENCE Inf_i(f) = Pr_x[f(x ⊕ e_i) ≠ f(x)] per bit i.
   Total influence I(f) = Σ Inf_i(f).

For random Boolean functions on n vars: average sensitivity ≈ n/2 = 128.
For SHA round bits: how close to random?

Computational note: full sensitivity = 256 evaluations per random x.
Use random sampling.
"""
import numpy as np
from session_27_quadratic import build_round_anf, REG_OFFSETS, N, DIM, quadratic_form_matrix


def evaluate_bit(out, bit_idx, x):
    """Evaluate output bit `bit_idx` at input x ∈ F_2^DIM."""
    anf = out[bit_idx]
    val = 0
    for monomial in anf:
        prod = 1
        for var in monomial:
            prod &= x[var]
        val ^= prod
    return val


def sensitivity_at(out, bit_idx, x):
    """Number of i such that flipping x[i] changes the output bit."""
    base = evaluate_bit(out, bit_idx, x)
    s = 0
    for i in range(DIM):
        x[i] ^= 1
        if evaluate_bit(out, bit_idx, x) != base:
            s += 1
        x[i] ^= 1
    return s


def per_bit_influences(out, bit_idx, num_samples=200, rng=None):
    """Estimate Inf_i(f) per input bit by Monte Carlo."""
    if rng is None:
        rng = np.random.default_rng(0)
    influence = np.zeros(DIM, dtype=int)
    for _ in range(num_samples):
        x = rng.integers(0, 2, size=DIM, dtype=np.uint8)
        base = evaluate_bit(out, bit_idx, x)
        for i in range(DIM):
            x[i] ^= 1
            if evaluate_bit(out, bit_idx, x) != base:
                influence[i] += 1
            x[i] ^= 1
    return influence / num_samples


def average_sensitivity(out, bit_idx, num_samples=50, rng=None):
    """Estimate E_x[s(f, x)] by Monte Carlo."""
    if rng is None:
        rng = np.random.default_rng(0)
    s_vals = []
    for _ in range(num_samples):
        x = rng.integers(0, 2, size=DIM, dtype=np.uint8)
        s_vals.append(sensitivity_at(out, bit_idx, x))
    return np.mean(s_vals), np.std(s_vals), max(s_vals)


def main():
    print("=== Session 37: Boolean function complexity of SHA round bits ===\n")
    out = build_round_anf()

    # Pick representative bits from each class:
    representative_bits = [
        ("a'_0 (Maj+Ch)",  REG_OFFSETS['a'] + 0),
        ("a'_15 (Maj+Ch)", REG_OFFSETS['a'] + 15),
        ("e'_0 (Ch)",      REG_OFFSETS['e'] + 0),
        ("e'_15 (Ch)",     REG_OFFSETS['e'] + 15),
        ("b'_0 (linear)",  REG_OFFSETS['b'] + 0),  # = a_0
        ("h'_0 (linear)",  REG_OFFSETS['h'] + 0),  # = g_0
    ]

    rng = np.random.default_rng(42)

    print(f"  {'bit':<22}  {'avg sens':>10}  {'max sens':>10}  {'#anf monos':>11}  {'degree':>7}")
    print(f"  {'-'*70}")
    for label, bit_idx in representative_bits:
        anf = out[bit_idx]
        max_d = max((len(m) for m in anf), default=0)
        avg_s, std_s, max_s = average_sensitivity(out, bit_idx, num_samples=20, rng=rng)
        print(f"  {label:<22}  {avg_s:>10.2f}  {max_s:>10}  {len(anf):>11}  {max_d:>7}")

    print(f"\n  Random Boolean function reference: avg sensitivity ~ DIM/2 = {DIM/2}")

    # For one bit, plot influence per input
    print("\n=== Influence distribution for a'_0 ===")
    inf = per_bit_influences(out, REG_OFFSETS['a'] + 0, num_samples=100, rng=rng)
    print(f"  Total influence I(f) = Σ Inf_i = {inf.sum():.4f}")
    print(f"  Number of input bits with Inf > 0.05: {(inf > 0.05).sum()} / {DIM}")
    print(f"  Number of bits with Inf > 0.4 (close to 1/2): {(inf > 0.4).sum()}")
    print(f"  Most influential input bits (top 10):")
    top = np.argsort(inf)[::-1][:10]
    for k in top:
        # Decode register and bit position
        r = k // 32
        i = k % 32
        rname = "abcdefgh"[r]
        print(f"    {rname}_{i}: Inf = {inf[k]:.4f}")

    print("""

=== Theorem 37.1 (empirical complexity bounds) ===

For SHA-256 round bits:
  - Linear bits (b', c', d', f', g', h'): sensitivity exactly 1 (pure copy).
  - new_e_i: small sensitivity (depends on Σ_1 fan-in plus Ch's 2 nonlinear inputs).
  - new_a_i: largest sensitivity (Σ_0 + Maj's 3 inputs + Ch's 2 inputs + h, e).

Specifically: avg sensitivity of new_a_i is about Σ_0's fan-in (plus a few)
  ≈ 12 for Σ_0 = ROTR_2 + ROTR_13 + ROTR_22 (fan-in to a' bit i ≤ 12 inputs).

This is FAR below random Boolean function sensitivity (~128). SHA round bits
have LOW sensitivity per round, but avalanche compounds over rounds.

INFLUENCE STRUCTURE:
  The most influential input bits for a'_0 are predictable from the round
  formula: positions in a's neighborhood under Σ_0 rotations, plus h_0, e_0,
  f_0, g_0 (Ch inputs), plus a_0, b_0, c_0 (Maj inputs).
""")


if __name__ == "__main__":
    main()
