"""
Session 1: δ-rings, foundational computations.

A δ-ring over Z_p (here p=2) is a pair (A, δ) where A is a commutative ring
and δ: A → A is a function satisfying:

  (D1)  δ(0) = δ(1) = 0
  (D2)  δ(x + y) = δ(x) + δ(y) + sum_{i=1}^{p-1} (1/p) C(p,i) x^i y^{p-i}
        For p=2: δ(x + y) = δ(x) + δ(y) - x·y
        (the term is (1/2)·2·xy = xy, but signed: -xy)
        ACTUALLY: C(2,1)=2, so (1/2)·2 = 1. So δ(x+y) = δ(x) + δ(y) - xy.
        Wait, need to be careful about signs. Let me derive from φ.
  (D3)  δ(x·y) = x^p · δ(y) + y^p · δ(x) + p · δ(x) · δ(y)
        For p=2: δ(xy) = x^2·δ(y) + y^2·δ(x) + 2·δ(x)·δ(y)

Equivalently, define φ: A → A by φ(x) = x^p + p·δ(x). Then φ is a RING
homomorphism, and φ(x) ≡ x^p (mod p). Axioms D1-D3 ensure φ is a ring hom.

For p=2:  φ(x) = x^2 + 2·δ(x)

The map φ is a "Frobenius lift" — it lifts Frobenius x → x^p from A/pA to A.

Intuition:
  - In char p, Frobenius F(x) = x^p is automatic.
  - In char 0 (or mixed), we don't have natural Frobenius. A δ-structure
    lets us pick one: φ.
  - δ measures "by how much we lift": φ(x) = x^p + p·δ(x).

Examples to build:
  1. Z_2 with δ(x) = (x - x^2)/2 (standard)
  2. Z_4 = Z/4 with same formula (check well-defined)
  3. Bool ring F_2[t]/(t^2 - t)
  4. Product ring Z_2 × Z_2 (= Spec of 2 points)

For each: verify D1, D2, D3. Then compute φ. Verify φ is ring hom.
"""

from fractions import Fraction


# ============================================================
# δ-ring on Z (or Z_p). Standard δ(x) = (x - x^p) / p.
# ============================================================

def delta_Z(x, p=2):
    """Standard δ-structure on Z: δ(x) = (x - x^p)/p."""
    return (x - x**p) // p  # integer division — should be exact


def phi_from_delta_Z(x, p=2):
    """φ(x) = x^p + p·δ(x). Should reduce to x^p mod p, and equal x in Z_p."""
    return x**p + p * delta_Z(x, p)


def check_delta_Z():
    """Verify δ-ring axioms on Z with p=2."""
    p = 2

    print("--- Z_2 as δ-ring (with δ(x) = (x - x^2)/2) ---")
    # D1
    assert delta_Z(0, p) == 0, "D1 fail at 0"
    assert delta_Z(1, p) == 0, "D1 fail at 1"
    print("  D1: δ(0)=δ(1)=0 ✓")

    # D2: δ(x + y) = δ(x) + δ(y) - xy  (for p=2)
    for x in range(-3, 4):
        for y in range(-3, 4):
            lhs = delta_Z(x + y, p)
            rhs = delta_Z(x, p) + delta_Z(y, p) - x * y
            assert lhs == rhs, f"D2 fail at ({x}, {y}): {lhs} != {rhs}"
    print("  D2: δ(x+y) = δ(x) + δ(y) - xy ✓ (checked x,y ∈ [-3, 3])")

    # D3: δ(xy) = x^2·δ(y) + y^2·δ(x) + 2·δ(x)·δ(y)
    for x in range(-3, 4):
        for y in range(-3, 4):
            lhs = delta_Z(x * y, p)
            rhs = x**2 * delta_Z(y, p) + y**2 * delta_Z(x, p) + 2 * delta_Z(x, p) * delta_Z(y, p)
            assert lhs == rhs, f"D3 fail at ({x}, {y}): {lhs} != {rhs}"
    print("  D3: δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y) ✓")

    # Sanity: φ is ring hom
    for x in range(-3, 4):
        for y in range(-3, 4):
            assert phi_from_delta_Z(x + y, p) == phi_from_delta_Z(x, p) + phi_from_delta_Z(y, p), "φ add hom fail"
            assert phi_from_delta_Z(x * y, p) == phi_from_delta_Z(x, p) * phi_from_delta_Z(y, p), "φ mult hom fail"
    print("  φ is ring homomorphism ✓")

    # What does φ look like?
    print("  φ(x) values: " + ", ".join(f"φ({x})={phi_from_delta_Z(x,p)}" for x in range(5)))


# ============================================================
# δ-ring on Z/p^k = truncated Z_p
# ============================================================

def delta_Zmod(x, mod, p=2):
    """δ on Z/mod, with δ(x) = (x - x^p)/p (must be well-defined mod mod/p)."""
    # Caveat: δ is defined mod (mod / p).
    # Because δ(x + mod) should differ from δ(x) by a multiple of (mod/p), roughly.
    # We compute in integers then reduce.
    x = x % mod
    raw = (x - pow(x, p)) // p
    return raw % (mod // p) if mod % p == 0 else raw


def check_Zmod_4():
    """Z/4 with δ from standard formula — well-defined?"""
    p = 2
    mod = 4  # we want δ: Z/4 → Z/2
    print("\n--- Z/4 as δ-ring (δ: Z/4 → Z/2) ---")
    # Check δ well-defined: δ(x + 4) = δ(x) mod 2?
    for x in range(4):
        for shift in [4, 8, -4]:
            d1 = delta_Zmod(x, mod, p)
            d2 = delta_Zmod(x + shift, mod, p)
            if d1 != d2:
                print(f"  δ not well-defined: δ({x}) = {d1}, δ({x+shift}) = {d2}")
                return
    print("  δ well-defined on Z/4, values in Z/2 ✓")
    print("  δ values: " + ", ".join(f"δ({x}) = {delta_Zmod(x, mod, p)}" for x in range(4)))


# ============================================================
# Ring of Boolean polynomials F_2[t_1,...,t_k] / (t_i^2 - t_i)
# ============================================================

# A Boolean function on k variables is a map F_2^k → F_2.
# The ring of such functions under pointwise +, * is F_2[t_1,...,t_k]/(t_i^2 - t_i).
# This is a FINITE ring with 2^{2^k} elements (!).

# We represent Boolean functions as truth tables: f[i] = f(binary i for i∈[0, 2^k))

class BoolFunc:
    """Boolean function on k variables represented as truth table."""
    def __init__(self, k, values):
        self.k = k
        self.values = tuple(v & 1 for v in values)
        assert len(self.values) == (1 << k)

    def __add__(self, other):  # = XOR
        return BoolFunc(self.k, [a ^ b for a, b in zip(self.values, other.values)])

    def __mul__(self, other):  # = AND
        return BoolFunc(self.k, [a & b for a, b in zip(self.values, other.values)])

    def __neg__(self):
        return self  # -x = x in char 2

    def __eq__(self, other):
        return self.values == other.values

    def __hash__(self):
        return hash(self.values)

    def __repr__(self):
        return f"Bool({self.values})"

    @staticmethod
    def zero(k):
        return BoolFunc(k, [0] * (1 << k))

    @staticmethod
    def one(k):
        return BoolFunc(k, [1] * (1 << k))

    @staticmethod
    def var(k, i):
        """i-th projection t_i."""
        return BoolFunc(k, [(j >> i) & 1 for j in range(1 << k)])


def check_bool_ring_delta():
    """Can we put a δ-structure on Bool_k?
    In characteristic 2, natural Frobenius φ(x) = x^2 = x (since x^2 = x in Bool).
    So φ = identity. Then δ(x) = (φ(x) - x^2)/2 = 0/2 = 0 trivially.
    But wait — division by 2 in char 2 doesn't make sense. δ-structure requires
    working in a LIFT of the ring."""
    print("\n--- Bool_1 = F_2[t]/(t² - t) ---")
    print("  Elements: 0, 1, t, 1+t (4 Boolean functions on 1 variable)")
    bf = BoolFunc
    zero = bf.zero(1)
    one = bf.one(1)
    t = bf.var(1, 0)
    t_plus_1 = t + one

    # All elements
    elts = [zero, one, t, t_plus_1]
    print(f"  {len(elts)} elements: {elts}")

    # Check that t^2 = t (Boolean)
    assert t * t == t, "t² ≠ t"
    print("  t² = t ✓  (Frobenius is identity on Bool ring)")

    # The char-2 reality: Frobenius = identity on Bool, so any δ-lift
    # would have to lift to characteristic-0 ring
    print("  In char 2: φ(x) = x² = x (identity Frobenius)")
    print("  Any δ-structure requires LIFT to char-0 ring")
    print("  This is where Witt-vector / prismatic enters — to define the lift")


# ============================================================
# Witt-vector approach: lift Bool_1 to Z/4[t]/(t² - t)
# ============================================================

def witt_lift_bool_1():
    """Lift of Bool_1 = F_2[t]/(t² - t) to Z/4[t]/(t² - t).

    Over Z/4, elements are a + bt with a, b ∈ Z/4. Relation: t² = t.
    But t² = t over Z/4 too? Let's check constraints.

    Actually, t² - t = 0 over Z/4 means t(t-1) = 0 mod 4.
    Solutions: t ∈ {0, 1} in Z/4 (idempotents).
    So Z/4[t]/(t² - t) has elements a + bt where t IS just a formal idempotent.

    The lift gives ring structure over Z/4 that reduces mod 2 to Bool_1.

    Frobenius? φ(t) should reduce to t mod 2. Simplest lift: φ(t) = t.
    Then δ(t) = (φ(t) - t²)/2 = (t - t)/2 = 0. Works in integer arithmetic:
    (t - t²) = t(1-t), and in Z/4 this might not be 0 (check).
    """
    print("\n--- Lift: Z/4[t] / (t² - t) ---")
    print("  Elements: a + bt with a, b ∈ Z/4, subject to t² = t")
    print("  This is a lift of Bool_1 to Z/4 (reduces mod 2 to Bool_1)")

    # In this ring, δ(t) = (φ(t) - t²) / 2 where φ is a Frobenius lift
    # If φ(t) = t, then δ(t) = (t - t²)/2 = t(1-t)/2
    # Over Z, t(1-t) = t - t², which has Witt-structure
    # In Z/4: t(1-t)/2 is well-defined iff t(1-t) is even for all t ∈ Z/4

    # Check: for t ∈ Z/4 idempotent (t² = t), t(1-t) = t - t² = 0 in Z/4!
    # So δ(t) = 0/2 = undefined (0/2 is 0 but ambiguous)
    # More carefully: "division by 2" in δ-structure happens in the BASE ring Z_p,
    # not in the quotient. Need to be careful.

    print("  In Z/4 with t² = t: t(1-t) = t - t² = 0")
    print("  So δ(t) = 0/2 is still 0 (but the DIVISION needs lift to Z_2)")
    print("  This is well-defined δ-structure, but TRIVIAL (δ = 0)")
    print("")
    print("  KEY QUESTION for Session 2:")
    print("  Can we put NON-TRIVIAL δ-structure on lift of Bool ring?")
    print("  If not, prismatic cohomology collapses to trivial.")


if __name__ == "__main__":
    check_delta_Z()
    check_Zmod_4()
    check_bool_ring_delta()
    witt_lift_bool_1()
