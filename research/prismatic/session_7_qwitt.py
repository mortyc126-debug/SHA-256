"""
Session 7: q-Witt prism (Z_2[[q-1]], (1+q)) — exploration.

Background:
  Standard prism (Z_2, (2)) has φ = identity, so no non-trivial Frobenius
  to exploit. q-Witt prism gives non-trivial φ.

The q-Witt setup:
  A = Z_p[[q-1]] = formal power series in (q-1) over Z_p
  φ(q) = q^p  (q-Frobenius)
  I = ([p]_q) where [p]_q = (q^p - 1)/(q - 1) = 1 + q + ... + q^{p-1}
  For p=2: [2]_q = 1 + q

Goals for this session:
  1. Implement Z_2[[q-1]] as truncated power series
  2. Define δ on it; verify φ(q) = q² implies δ(q) = 0
  3. Verify prism conditions for (Z_2[[q-1]], (1+q))
  4. Quotient by I: what do we get?
  5. Look for connection to SHA rotations

Honest expectation: this session will be EXPLORATORY. The connection to
SHA isn't obvious. We're building infrastructure to understand if/how
q-twist might capture rotations.
"""
from typing import List


# ============================================================
# Power series Z_p[[q-1]] truncated at degree N in (q-1)
# ============================================================

class QPowerSeries:
    """
    Element of Z_p[[q-1]] truncated mod (q-1)^N.
    Represented as list of N coefficients in Z_p, each modulo p^k for some k.

    coeffs[i] = coefficient of (q-1)^i, in Z (we track precision separately).
    """
    def __init__(self, coeffs: List[int], precision_p_power: int, p: int = 2, N: int = 8):
        self.coeffs = list(coeffs[:N]) + [0] * max(0, N - len(coeffs))
        self.precision = precision_p_power  # mod p^this
        self.p = p
        self.N = N
        self._reduce()

    def _reduce(self):
        mod = self.p ** self.precision
        self.coeffs = [c % mod for c in self.coeffs]

    @staticmethod
    def constant(c: int, precision_p_power: int = 32, p: int = 2, N: int = 8):
        return QPowerSeries([c], precision_p_power, p, N)

    @staticmethod
    def q(precision_p_power: int = 32, p: int = 2, N: int = 8):
        """Element q = 1 + (q-1)."""
        return QPowerSeries([1, 1], precision_p_power, p, N)

    @staticmethod
    def q_minus_1(precision_p_power: int = 32, p: int = 2, N: int = 8):
        """Element (q-1)."""
        return QPowerSeries([0, 1], precision_p_power, p, N)

    def __add__(self, other):
        return QPowerSeries(
            [a + b for a, b in zip(self.coeffs, other.coeffs)],
            self.precision, self.p, self.N
        )

    def __sub__(self, other):
        return QPowerSeries(
            [a - b for a, b in zip(self.coeffs, other.coeffs)],
            self.precision, self.p, self.N
        )

    def __mul__(self, other):
        result = [0] * self.N
        for i in range(self.N):
            for j in range(self.N - i):
                result[i + j] += self.coeffs[i] * other.coeffs[j]
        return QPowerSeries(result, self.precision, self.p, self.N)

    def __pow__(self, k: int):
        if k == 0:
            return QPowerSeries.constant(1, self.precision, self.p, self.N)
        result = QPowerSeries.constant(1, self.precision, self.p, self.N)
        base = self
        while k > 0:
            if k & 1:
                result = result * base
            base = base * base
            k >>= 1
        return result

    def __eq__(self, other):
        return self.coeffs == other.coeffs

    def __repr__(self):
        terms = []
        for i, c in enumerate(self.coeffs):
            if c == 0: continue
            if i == 0:
                terms.append(str(c))
            elif i == 1:
                terms.append(f"{c}(q-1)" if c != 1 else "(q-1)")
            else:
                terms.append(f"{c}(q-1)^{i}" if c != 1 else f"(q-1)^{i}")
        return " + ".join(terms) if terms else "0"


# ============================================================
# δ-structure: φ(q) = q²,  δ(q) = (φ(q) - q²)/2 = 0
# ============================================================

def phi_on_q_series(x: QPowerSeries) -> QPowerSeries:
    """Apply Frobenius lift φ. φ(q) = q², φ(constant) = constant.
    For a polynomial P(q-1) = Σ a_i (q-1)^i, compute P(q²-1).
    Note: q² - 1 = (q-1)(q+1) = (q-1)(2 + (q-1)) = 2(q-1) + (q-1)².
    """
    # Compute (q² - 1) as a power series in (q-1)
    # q² - 1 = 2(q-1) + (q-1)²
    q_squared_minus_one = QPowerSeries([0, 2, 1], x.precision, x.p, x.N)

    # Now substitute (q-1) → q²-1 in x = Σ a_i (q-1)^i
    result = QPowerSeries.constant(0, x.precision, x.p, x.N)
    power_of_qsm1 = QPowerSeries.constant(1, x.precision, x.p, x.N)
    for i, c in enumerate(x.coeffs):
        if c != 0:
            term = QPowerSeries.constant(c, x.precision, x.p, x.N) * power_of_qsm1
            result = result + term
        power_of_qsm1 = power_of_qsm1 * q_squared_minus_one
    return result


def delta_on_q_series(x: QPowerSeries) -> QPowerSeries:
    """δ(x) = (φ(x) - x²) / 2.
    For p=2, division by 2 only works if (φ(x) - x²) ∈ 2·R.
    """
    phi_x = phi_on_q_series(x)
    x_squared = x * x
    diff = phi_x - x_squared
    # Divide by 2 (or by 2 in the precision).
    # Since coefficients are mod 2^precision, division by 2 means
    # right shift the coefficients (if all are even).
    result_coeffs = []
    for c in diff.coeffs:
        if c % 2 != 0:
            # Cannot divide by 2 — δ-structure fails or precision issue
            return None
        result_coeffs.append(c // 2)
    return QPowerSeries(result_coeffs, diff.precision - 1, diff.p, diff.N)


# ============================================================
# Verify δ-axioms on q-power series
# ============================================================

def test_qpow_arithmetic():
    print("=== Test Z_2[[q-1]] arithmetic ===")
    q = QPowerSeries.q()
    qm1 = QPowerSeries.q_minus_1()
    one = QPowerSeries.constant(1)

    # q = 1 + (q-1)
    assert q == one + qm1, "q should be 1 + (q-1)"
    print(f"  q = {q}")
    print(f"  q² = {q * q}")
    print(f"  q² - 1 = {q * q - one}")
    print(f"  (q-1)(q+1) = {qm1 * (q + one)}")
    assert q * q - one == qm1 * (q + one), "q²-1 ≠ (q-1)(q+1)"
    print("  Identity q²-1 = (q-1)(q+1) ✓")


def test_phi_q():
    print("\n=== Test φ(q) = q² ===")
    q = QPowerSeries.q()
    phi_q = phi_on_q_series(q)
    print(f"  φ(q)   = {phi_q}")
    print(f"  q²     = {q * q}")
    assert phi_q == q * q, f"φ(q) should be q², got {phi_q}"
    print("  ✓ φ(q) = q²")

    # Test φ(q²) = q^4
    q2 = q * q
    phi_q2 = phi_on_q_series(q2)
    print(f"  φ(q²) = {phi_q2}")
    print(f"  q⁴    = {q ** 4}")
    assert phi_q2 == q ** 4
    print("  ✓ φ(q²) = q⁴")


def test_delta_q():
    print("\n=== Test δ(q) ===")
    q = QPowerSeries.q()
    dq = delta_on_q_series(q)
    print(f"  δ(q) = {dq}")
    # By construction, δ(q) = (φ(q) - q²)/2 = (q² - q²)/2 = 0
    zero = QPowerSeries.constant(0, dq.precision)
    assert dq.coeffs == zero.coeffs[:dq.N]
    print("  ✓ δ(q) = 0 (by construction since φ(q) = q²)")


def verify_prism_conditions():
    print("\n=== Verify prism (Z_2[[q-1]], (1+q)) ===")
    q = QPowerSeries.q()
    one = QPowerSeries.constant(1)
    one_plus_q = one + q  # = 2 + (q-1)
    print(f"  I = (1+q) = {one_plus_q}")

    # 1. A = Z_2[[q-1]] is δ-ring (with δ(q)=0, φ(q)=q²) ✓
    print("  1. A = Z_2[[q-1]] is δ-ring with φ(q)=q², δ(q)=0  ✓")

    # 2. I principal? Yes, generated by (1+q).
    print("  2. I = (1+q) is principal  ✓")

    # 3. (p, I)-complete? p=2, I=(1+q). Note 2 = (1+q) - (q-1).
    #    So (2, 1+q) = (1+q, q-1) in some sense. Need (q-1)-completion.
    #    Z_2[[q-1]] is (q-1)-complete by definition. ✓
    print("  3. Z_2[[q-1]] is (q-1)-complete (and 2-complete) by construction  ✓")

    # 4. Distinguished: δ(d) = unit. d = 1+q.
    delta_d = delta_on_q_series(one_plus_q)
    if delta_d is None:
        print("  4. ❌ δ(1+q) not well-defined!")
        return
    print(f"  4. δ(1+q) = {delta_d}")
    # Compute manually: δ(1+q) = δ(1) + δ(q) - 1·q = 0 + 0 - q = -q
    expected = QPowerSeries.constant(0, delta_d.precision) - QPowerSeries.q(delta_d.precision)
    print(f"     Expected -q (at precision {delta_d.precision}) = {expected}")
    assert delta_d.coeffs == expected.coeffs[:delta_d.N], f"got {delta_d.coeffs} vs {expected.coeffs}"
    print(f"     ✓ δ(1+q) = -q (constant term is odd → unit in Z_2[[q-1]])")

    print("\n  → (Z_2[[q-1]], (1+q)) is a valid prism (q-de Rham prism for p=2)!")


def quotient_mod_I():
    """What is Z_2[[q-1]] / (1+q)?

    Setting (1+q) = 0 means q = -1. So in the quotient, q acts as -1.
    Then 1+q = 0, q² = 1, δ(q) = 0, φ(q) = 1.

    What ring is this? Z_2[[q-1]] / (1+q).
    Substituting q = -1: q-1 = -2. So (q-1) is identified with -2.
    Power series in (q-1) becomes power series in -2, i.e., 2-adic power series.
    This converges to Z_2!

    So Z_2[[q-1]] / (1+q) ≅ Z_2 (with q-1 → -2).

    Key: in this quotient, Frobenius φ becomes:
      φ(q) = q² ≡ 1 (mod (1+q))
      So φ(q-1) ≡ -1 - 1 = -2 ≡ q-1 ... hmm, need careful analysis.
    """
    print("\n=== Quotient (Z_2[[q-1]]) / (1+q) ===")
    print("  Setting q = -1 in quotient:")
    print("    q - 1 → -2")
    print("    Power series Σ a_i (q-1)^i → Σ a_i (-2)^i  (a 2-adic series)")
    print("  Quotient ring ≅ Z_2 (via q-1 ↦ -2).")
    print("  Frobenius descent: φ(q) = q², so in quotient φ(-1) = 1, φ(q-1) = (q-1)·(q+1)/(q-1) ... ?")
    print("  φ on quotient is 'doubling' on (q-1): (q-1) → q²-1 = (q-1)(q+1) ↦ -2·0 = 0 in quotient.")
    print("  Hmm, this is trivial in quotient. Real action of φ visible at higher levels of (1+q)-adic filtration.")


def link_to_rotations():
    """Conjectural connection: SHA rotations as q-twists in q-Witt cohomology.

    Hypothesis:
      For a 32-bit register, rotation ROTR_r corresponds to multiplication by
      ζ_32^r where ζ_32 is a primitive 32nd root of unity.
      In q-Witt with q = ζ_32: rotation = q^r.

    Problem: ζ_32 doesn't exist in Z_2 (gcd(32, 2) = 2).
      Cyclotomic Φ_32(x) = x^16 + 1. Over F_2, Φ_32 = (x+1)^16 (totally ramified).
      So Z_2[ζ_32] is RAMIFIED extension of degree 16.

    To realize rotations: work in Z_2[ζ_32] = Z_2[T]/(T^16 + 1) (or similar).
    This has its own δ-structure (or doesn't — needs verification).

    For session 7, just IDENTIFY the issue. Resolution requires Session 8+.
    """
    print("\n=== Link to SHA rotations (preliminary) ===")
    print("  Hypothesis: rotation ROTR_r corresponds to multiplication by q^r")
    print("  in some q-Witt setting, where q is appropriate root of unity.")
    print()
    print("  Issue 1: For 32-bit ROTR, need ζ_32 (primitive 32nd root of unity).")
    print("           But ζ_32 doesn't exist in Z_2; needs RAMIFIED extension")
    print("           Z_2[ζ_32] = Z_2[T]/(T^16 + 1), degree 16.")
    print()
    print("  Issue 2: This extension has its own δ-structure questions.")
    print("           Φ_32 over F_2 = (x+1)^16 means totally ramified.")
    print()
    print("  CONCLUSION: q-Witt is the RIGHT direction, but we need to work in")
    print("              ramified cyclotomic extension. This is concrete but")
    print("              technically heavy — requires Session 8+ to set up.")


if __name__ == "__main__":
    test_qpow_arithmetic()
    test_phi_q()
    test_delta_q()
    verify_prism_conditions()
    quotient_mod_I()
    link_to_rotations()
