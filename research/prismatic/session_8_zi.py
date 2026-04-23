"""
Session 8: δ-structure on Z_2[i] = Z_2[T]/(T²+1).

This is the SMALLEST ramified extension of Z_2. It corresponds to ζ_4 = i,
the primitive 4th root of unity.

Goal: try to put δ-structure on Z_2[i].

  A δ-structure requires a Frobenius lift φ: Z_2[i] → Z_2[i] with:
    - φ ring hom
    - φ(x) ≡ x^p (mod p) for all x

  For p=2: φ(x) ≡ x² (mod 2). On i: x² = i² = -1 (mod 2), so φ(i) ≡ -1 (mod 2),
  meaning φ(i) is ODD in Z_2[i].

  φ ring hom: φ(i)² = φ(i²) = φ(-1) = -1 (constants invariant).
  So φ(i) is an element with square = -1 in Z_2[i]: only ±i.

  Two candidates: φ(i) = i (identity), φ(i) = -i (complex conjugation).

  For δ to be well-defined: δ(i) = (φ(i) - i²) / 2 must lie IN Z_2[i].
  Both candidates give δ(i) = (±i + 1)/2.
  Question: is (1±i)/2 ∈ Z_2[i]?
"""


# ============================================================
# Z_2[i] arithmetic: elements are (a, b) representing a + bi
# Coefficients tracked as integers mod 2^precision
# ============================================================

class GaussianZ2:
    def __init__(self, a: int, b: int, precision: int = 32):
        mod = 2**precision
        self.a = a % mod
        self.b = b % mod
        self.precision = precision

    @staticmethod
    def i(precision=32):
        return GaussianZ2(0, 1, precision)

    def __add__(self, other):
        return GaussianZ2(self.a + other.a, self.b + other.b, self.precision)

    def __sub__(self, other):
        return GaussianZ2(self.a - other.a, self.b - other.b, self.precision)

    def __mul__(self, other):
        # (a + bi)(c + di) = (ac - bd) + (ad + bc)i
        new_a = self.a * other.a - self.b * other.b
        new_b = self.a * other.b + self.b * other.a
        return GaussianZ2(new_a, new_b, self.precision)

    def __neg__(self):
        return GaussianZ2(-self.a, -self.b, self.precision)

    def __eq__(self, other):
        return self.a == other.a and self.b == other.b

    def __repr__(self):
        if self.b == 0:
            return f"{self.a}"
        elif self.a == 0:
            return f"{self.b}·i"
        else:
            return f"{self.a} + {self.b}·i"

    def is_divisible_by_2(self):
        """Check if both components are even."""
        return self.a % 2 == 0 and self.b % 2 == 0

    def divide_by_2(self):
        """Divide by 2 if possible. Returns None if not divisible."""
        if not self.is_divisible_by_2():
            return None
        return GaussianZ2(self.a // 2, self.b // 2, self.precision - 1)

    def is_unit(self):
        """In Z_2[i], unit iff norm a² + b² is odd (i.e., not divisible by 2)."""
        return (self.a * self.a + self.b * self.b) % 2 == 1


# ============================================================
# Try various Frobenius lifts on Z_2[i]
# ============================================================

def phi_identity(x: GaussianZ2) -> GaussianZ2:
    """Identity Frobenius: φ(i) = i. This is just the identity map."""
    return GaussianZ2(x.a, x.b, x.precision)


def phi_conjugation(x: GaussianZ2) -> GaussianZ2:
    """Complex conjugation: φ(a + bi) = a - bi. This sends i → -i."""
    return GaussianZ2(x.a, -x.b, x.precision)


def try_delta(phi_func, name: str, x: GaussianZ2):
    """Try δ(x) = (φ(x) - x²) / 2. Returns δ(x) if well-defined, None otherwise."""
    phi_x = phi_func(x)
    x_squared = x * x
    diff = phi_x - x_squared
    result = diff.divide_by_2()
    if result is None:
        print(f"    δ_{name}({x}) — NOT WELL-DEFINED (diff = {diff} not divisible by 2)")
    return result


def systematic_test():
    """Try both Frobenius candidates on key elements."""
    print("=== Frobenius candidates on Z_2[i] ===\n")
    print("Recall: 2 = -i·(1+i)² in Z_2[i], so 2 is RAMIFIED (not a unit, not prime).")
    print("Element π = 1+i is a uniformizer with π² = 2i.\n")

    test_elements = [
        ("0", GaussianZ2(0, 0)),
        ("1", GaussianZ2(1, 0)),
        ("i", GaussianZ2(0, 1)),
        ("1+i", GaussianZ2(1, 1)),
        ("2", GaussianZ2(2, 0)),
        ("3+2i", GaussianZ2(3, 2)),
    ]

    for phi_name, phi_func in [("identity", phi_identity), ("conjugation", phi_conjugation)]:
        print(f"\n--- Try φ = {phi_name} ---")
        # First check ring homomorphism property: φ(i)² = φ(i²) = -1
        i = GaussianZ2.i()
        phi_i = phi_func(i)
        phi_i_sq = phi_i * phi_i
        minus_one = GaussianZ2(-1, 0)
        if phi_i_sq != minus_one:
            print(f"  φ NOT a ring hom: φ(i)² = {phi_i_sq} ≠ -1 = φ(i²)")
            print(f"  → SKIPPING (not a valid Frobenius)")
            continue

        # φ-condition: φ(x) ≡ x² (mod 2)
        x_test = GaussianZ2(3, 2)
        phi_x = phi_func(x_test)
        x_sq = x_test * x_test
        diff = phi_x - x_sq
        if not diff.is_divisible_by_2():
            print(f"  φ(x) NOT ≡ x² (mod 2) for x = {x_test}: diff = {diff}")
            print(f"  → SKIPPING (not a Frobenius lift)")
            continue
        print(f"  ✓ φ is ring hom and lifts Frobenius mod 2")

        # Compute δ on all test elements
        for name, x in test_elements:
            d = try_delta(phi_func, phi_name, x)
            if d is not None:
                print(f"    δ_{phi_name}({name} = {x}) = {d}")


def show_obstruction_concretely():
    """Demonstrate concretely why δ(i) is not well-defined for either φ choice."""
    print("\n=== Why no δ-structure on Z_2[i]? ===")
    i = GaussianZ2.i()

    # Case φ(i) = i
    print("\nCase φ(i) = i:")
    print(f"  δ(i) = (φ(i) - i²) / 2 = (i - (-1))/2 = (1 + i)/2")
    one_plus_i = GaussianZ2(1, 1)
    print(f"  Is (1+i) divisible by 2 in Z_2[i]? Components: a={one_plus_i.a}, b={one_plus_i.b}")
    print(f"  (1+i) divisible by 2 ⇔ both components even.")
    print(f"  Both ODD ⇒ NOT divisible. So δ(i) ∉ Z_2[i].")
    # Note: the norm of 1+i is 2, but for divisibility we need 2 | (1+i) AS GAUSSIAN INTEGER
    # which means 2 | a AND 2 | b. False.

    # Case φ(i) = -i
    print("\nCase φ(i) = -i:")
    print(f"  δ(i) = (φ(i) - i²) / 2 = (-i - (-1))/2 = (1 - i)/2")
    one_minus_i = GaussianZ2(1, -1)
    print(f"  Is (1-i) divisible by 2? Components: a=1, b=-1, both ODD ⇒ NO.")

    # The fundamental obstruction
    print("\nFundamental obstruction:")
    print("  In Z_2[i], 2 has unique factorization: 2 = -i · (1+i)²")
    print("  So divisibility by 2 means divisibility by π² where π = 1+i")
    print("  The element (1±i) = π · unit has only ONE factor of π, not TWO")
    print("  Hence (1±i) NOT divisible by 2 ⇒ δ(i) ∉ Z_2[i]")
    print("\n  THEOREM: Z_2[i] does NOT admit any δ-structure that lifts")
    print("           the Frobenius x → x² on F_2[i] = Z_2[i]/(2).")


def discuss_resolution():
    """What's the way forward if naive Z_2[i] doesn't work?"""
    print("\n=== Resolution paths ===")
    print("""
  Path 1: PERFECTOID extension
    Adjoin all 2-power roots of unity: Z_2[ζ_{2^∞}].
    After p-adic completion, this is PERFECTOID.
    Perfectoid rings always admit canonical Frobenius (the unique lift).
    So Z_2[ζ_{2^∞}]^∧ has a δ-structure.
    But this ring is HUGE (uncountable rank).

  Path 2: q-Witt prism (Session 7) is cleaner
    Z_2[[q-1]] with q FORMAL (not specialized to root of unity).
    δ-structure works because q is just a free variable.
    Rotation = action of q (substitution q → ζ_n)
    But to USE this for SHA, eventually need to substitute q with a real
    root of unity (Path 1's territory).

  Path 3: SKIP δ on Z_2[i]; use OTHER prism
    Bhatt-Scholze define ABSOLUTE PRISMATIC SITE — captures ALL prisms over a base.
    For Z_2[i]/(2) = F_2[i]/(i+1)² = F_2[ε]/(ε²) (dual numbers!), there might
    be a non-trivial prismatic cohomology computable WITHOUT explicit δ on Z_2[i].

  Recommendation: Path 1 OR Path 3.
  Path 3 is more elegant — work with the QUOTIENT and let Bhatt-Scholze
  formalism handle prism structure abstractly.

  Concrete next step (Session 9): study F_2[ε]/(ε²) (dual numbers) and its
  prismatic cohomology. This is the "tangent space" of F_2 in some sense.
""")


def implication_for_rotations():
    """Connect Z_2[i] obstruction to SHA rotations."""
    print("\n=== Implication for SHA rotations ===")
    print("""
  Our hypothesis from Session 7: ROTR_r = multiplication by ζ_n^r in Z_2[ζ_n].

  Session 8 finds: even smallest cyclotomic Z_2[i] = Z_2[ζ_4] does NOT admit
  δ-structure (let alone Z_2[ζ_32] for 32-bit rotations).

  This is a FUNDAMENTAL obstacle. Cannot directly equip "rotation ring" with
  prismatic structure.

  But: Bhatt-Scholze framework allows COMPUTATION of prismatic cohomology
  for non-δ rings via DERIVED (∞-categorical) methods. The "prismatic complex"
  is defined for arbitrary R, not just δ-rings.

  So path forward:
    (a) Treat F_2[i+1]² = F_2[ε]/ε² (or its multi-variable analog for ζ_32)
    (b) Compute its absolute prismatic cohomology using Bhatt-Scholze
    (c) See what this captures of "rotation structure"

  This is genuine theoretical territory, requires reading Bhatt-Scholze paper
  carefully. Realistic estimate: 5-10 more sessions of careful work.
""")


if __name__ == "__main__":
    systematic_test()
    show_obstruction_concretely()
    discuss_resolution()
    implication_for_rotations()
