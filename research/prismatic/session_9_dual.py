"""
Session 9: Prismatic cohomology of F_2[ε]/(ε²) (dual numbers).

After Session 8 closed direct path through Z_2[i] (no δ-structure),
identified F_2[i]/(i²+1) = F_2[ε]/(ε²) as canonical algebraic object
(via substitution ε = i+1).

Goal: compute prismatic cohomology of F_2[ε]/(ε²) over prism (Z_2, (2)).

Strategy:
  1. Find δ-ring lift of F_2[ε]/(ε²) over Z_2
  2. Compute Kähler differentials Ω¹
  3. Compute de Rham complex
  4. Discuss connection to prismatic cohomology

For smooth case: prismatic = de Rham (after appropriate completion).
For non-smooth (our case): prismatic may differ by torsion adjustments.
"""

# ============================================================
# Z_2[ε]/(ε²) — dual numbers over Z_2
# Elements: a + b·ε with a, b ∈ Z_2
# ============================================================

class DualZ2:
    def __init__(self, a, b, precision=32):
        mod = 2**precision
        self.a = a % mod
        self.b = b % mod
        self.precision = precision

    def __add__(self, other):
        return DualZ2(self.a + other.a, self.b + other.b, self.precision)

    def __sub__(self, other):
        return DualZ2(self.a - other.a, self.b - other.b, self.precision)

    def __mul__(self, other):
        # (a + bε)(c + dε) = ac + (ad + bc)ε   [since ε² = 0]
        return DualZ2(self.a * other.a, self.a * other.b + self.b * other.a, self.precision)

    def __neg__(self):
        return DualZ2(-self.a, -self.b, self.precision)

    def __eq__(self, other):
        return self.a == other.a and self.b == other.b

    def __repr__(self):
        if self.b == 0:
            return f"{self.a}"
        elif self.a == 0:
            return f"{self.b}·ε"
        else:
            return f"{self.a} + {self.b}·ε"


# ============================================================
# Verify Z_2[ε]/(ε²) is a δ-ring with φ(ε) = 0
# ============================================================

def phi_dual(x: DualZ2) -> DualZ2:
    """Frobenius lift: φ(ε) = 0, φ(constant) = constant.

    Then φ(a + bε) = a + b·φ(ε) = a (component dropping ε).

    Wait — that's not a ring hom! φ(a + bε) needs to be valid algebra.
    Let me think.

    φ(a + bε) = φ(a) + φ(b)·φ(ε) = a + b·0 = a.

    Check: φ ring hom?
      φ((a+bε)(c+dε)) = φ(ac + (ad+bc)ε) = ac
      φ(a+bε)·φ(c+dε) = a · c = ac  ✓

    Frobenius mod 2:
      x = a + bε, x² = a² + 2ab·ε + b²·ε² = a² (mod 2 in Z, b²·ε² = 0 anyway)
      Need φ(x) ≡ x² mod 2: a ≡ a² mod 2.
      Fermat: a² ≡ a mod 2 ✓ for any a ∈ Z_2 (=Z_p mod p).
    """
    return DualZ2(x.a, 0, x.precision)


def delta_dual(x: DualZ2):
    """δ(x) = (φ(x) - x²) / 2."""
    phi_x = phi_dual(x)
    x_sq = x * x
    diff = phi_x - x_sq
    # Divide by 2
    if diff.a % 2 != 0 or diff.b % 2 != 0:
        return None  # not divisible by 2
    return DualZ2(diff.a // 2, diff.b // 2, x.precision - 1)


def verify_delta_dual_axioms():
    """Check D1, D2, D3 for δ on Z_2[ε]/(ε²)."""
    print("=== Verify δ-axioms on Z_2[ε]/(ε²) ===\n")

    # D1: δ(0) = δ(1) = 0
    z = DualZ2(0, 0)
    o = DualZ2(1, 0)
    d_z = delta_dual(z)
    d_o = delta_dual(o)
    print(f"  D1: δ(0) = {d_z}, δ(1) = {d_o}")
    assert d_z == DualZ2(0, 0, d_z.precision), "δ(0) ≠ 0"
    assert d_o == DualZ2(0, 0, d_o.precision), "δ(1) ≠ 0"
    print("    ✓\n")

    # D2: δ(x+y) = δ(x) + δ(y) - xy  (for p=2)
    print("  D2: δ(x+y) = δ(x) + δ(y) - xy")
    test_pairs = [
        (DualZ2(2, 0), DualZ2(3, 0)),
        (DualZ2(0, 1), DualZ2(0, 1)),
        (DualZ2(1, 1), DualZ2(2, 3)),
        (DualZ2(5, 7), DualZ2(11, 13)),
    ]
    bad = 0
    for x, y in test_pairs:
        x_plus_y = x + y
        lhs = delta_dual(x_plus_y)
        if lhs is None:
            # Need to check: lhs in (2)·R; if not, axiom doesn't apply
            print(f"    Skip ({x}, {y}): δ(x+y) not well-defined (x+y not divisible by 2)")
            continue
        # δ(x) + δ(y) - xy
        d_x = delta_dual(x)
        d_y = delta_dual(y)
        if d_x is None or d_y is None:
            print(f"    Skip ({x}, {y}): δ(x) or δ(y) not defined")
            continue
        # Compute xy in Z_2[ε]/(ε²)
        xy = x * y
        # rhs = d_x + d_y - xy (need to be in same precision)
        rhs_a = (d_x.a + d_y.a - xy.a) % (2**lhs.precision)
        rhs_b = (d_x.b + d_y.b - xy.b) % (2**lhs.precision)
        rhs = DualZ2(rhs_a, rhs_b, lhs.precision)
        if lhs == rhs:
            print(f"    ✓ ({x}, {y}): δ(x+y) = δ(x) + δ(y) - xy = {lhs}")
        else:
            print(f"    ✗ ({x}, {y}): {lhs} ≠ {rhs}")
            bad += 1

    if bad == 0:
        print("    All passes ✓")

    # D3: δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y)
    print("\n  D3: δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y)")
    bad = 0
    for x, y in test_pairs:
        xy = x * y
        lhs = delta_dual(xy)
        if lhs is None:
            print(f"    Skip ({x}, {y}): δ(xy) not defined")
            continue
        d_x = delta_dual(x)
        d_y = delta_dual(y)
        if d_x is None or d_y is None:
            print(f"    Skip ({x}, {y}): δ(x) or δ(y) not defined")
            continue
        # x², y² in dual numbers
        x_sq = x * x
        y_sq = y * y
        # Build rhs at precision lhs.precision
        prec = lhs.precision
        mod = 2**prec
        # x² · δ(y) + y² · δ(x) + 2·δ(x)·δ(y)
        # Note: precision of d_x, d_y is one less than x, y; but we operate at lhs.precision (= prec(x.prec - 1))
        # x², y² have full precision; multiplied by d_y, d_x at one less precision; result mod prec is OK
        term1 = x_sq * DualZ2(d_y.a, d_y.b, x_sq.precision)
        term2 = y_sq * DualZ2(d_x.a, d_x.b, y_sq.precision)
        term3 = DualZ2(d_x.a, d_x.b, prec) * DualZ2(d_y.a, d_y.b, prec)
        # 2·term3 in dual numbers
        term3_doubled = DualZ2(2 * term3.a, 2 * term3.b, prec)
        rhs = DualZ2(
            (term1.a + term2.a + term3_doubled.a) % (2**prec),
            (term1.b + term2.b + term3_doubled.b) % (2**prec),
            prec
        )
        if lhs == rhs:
            print(f"    ✓ ({x}, {y}): δ(xy) = {lhs}")
        else:
            print(f"    ✗ ({x}, {y}): {lhs} ≠ {rhs}")
            bad += 1

    if bad == 0:
        print("    All passes ✓")


# ============================================================
# Kähler differentials Ω¹_{Z_2[ε]/Z_2}
# ============================================================

def explain_kahler_differentials():
    """Compute Ω¹_{Z_2[ε]/(ε²) / Z_2} algebraically.

    R = Z_2[ε]/(ε²). Generated over Z_2 by single element ε.
    Universal property of Kähler differentials:
      Ω¹_{R/Z_2} = R-module generated by {dx : x ∈ R} mod relations:
        d(constant from Z_2) = 0
        d(x+y) = dx + dy
        d(xy) = x dy + y dx (Leibniz)

    Since R = Z_2 ⊕ Z_2·ε (free Z_2-module rank 2), and Z_2 generators are constants:
      d(a + bε) = b · dε     (a is constant, b·ε differential is b·dε)

    So Ω¹ generated by single element dε as R-module.

    Relations from R: ε² = 0, so d(ε²) = 0. Compute d(ε²) = 2ε dε.
    So 2ε · dε = 0 in Ω¹.

    Ω¹ = R · dε / (2ε · dε)
       = (Z_2 ⊕ Z_2·ε) · dε / (2ε dε)
       = Z_2 · dε ⊕ Z_2·ε dε / (2ε dε)
       = Z_2 · dε ⊕ (Z_2/2Z_2)·ε dε
       = Z_2 · dε ⊕ F_2·ε dε

    As Z_2-module: Ω¹ = Z_2 ⊕ F_2.

    Differential d: R → Ω¹:
      d(a + bε) = b · dε
      Image: Z_2 · dε (any b ∈ Z_2).
      Kernel: {a + 0·ε : a ∈ Z_2} = Z_2 (constants).

    Cohomology de Rham:
      H⁰ = ker(d) = Z_2
      H¹ = coker(d) = Ω¹ / Im(d) = (Z_2 · dε ⊕ F_2 · ε dε) / Z_2 · dε = F_2 · ε dε ≅ F_2
      H^i = 0 for i ≥ 2 (Ω² = Λ²(Ω¹) computation gives 0 due to dimension)
    """
    print("\n=== Kähler differentials Ω¹_{Z_2[ε]/(ε²) / Z_2} ===")
    print("""
  Setup: R = Z_2[ε]/(ε²) over Z_2. Single generator ε.

  Ω¹ = R-module generated by dε with relations from ring relations of R:
       d(ε²) = 0 → 2ε·dε = 0

  As Z_2-module:
       Ω¹ = R·dε / (2ε·dε)
          = Z_2·dε ⊕ Z_2·ε dε / (2ε dε)
          = Z_2·dε ⊕ F_2·ε dε
          ≅ Z_2 ⊕ F_2

  Differential d: R → Ω¹:
       d(a + bε) = b·dε
       Im(d) = Z_2·dε
       Ker(d) = Z_2 (constants)

  de Rham cohomology:
       H⁰_dR = Ker(d) = Z_2
       H¹_dR = Ω¹ / Im(d) = F_2·ε dε ≅ F_2
       H^i_dR = 0 for i ≥ 2

  This is concrete and standard. Now what about prismatic?
""")


def discuss_prismatic_vs_de_rham():
    """For SMOOTH case prismatic ≅ de Rham (after appropriate completion).
    Dual numbers are NOT smooth — they have a singular point at ε = 0.

    For non-smooth: prismatic generally has MORE cohomology (or different torsion).

    For computing prismatic of dual numbers, we'd use Bhatt-Scholze framework:
      1. Take the natural lift R̃ = Z_2[ε]/(ε²) (which IS a δ-Z_2-algebra)
      2. Compute "Hodge-Tate complex" or "prismatic complex" via derived methods
      3. The result lives in derived category; H^* are computed

    For "small" rings like dual numbers, the answer often reduces to de Rham
    of the lift modulo torsion adjustments.

    Without going through full Bhatt-Scholze machinery, our de Rham computation
    is the BEST CONCRETE APPROXIMATION we can do session-level.

    Conjecture: prismatic cohomology of F_2[ε]/(ε²) over (Z_2, (2)) is
    "derived enhancement" of (Z_2 in degree 0, F_2 in degree 1).
    """
    print("\n=== Prismatic vs de Rham ===")
    print("""
  For SMOOTH R/k: prismatic cohomology RΓ_prism(R/A) computes de Rham cohomology
    of the lift R̃/A modulo appropriate filtration shifts (Hodge-Tate filter).

  Our case R = F_2[ε]/(ε²) is NOT smooth — singular point at ε=0
  (locus where ε² = 0 has dimension 1 but is set-theoretically a point).

  For non-smooth, prismatic cohomology can have:
    - Additional torsion classes
    - Derived (∞-categorical) enhancements
    - Conjugate filtration giving different graded pieces

  Our computation gives:
    de Rham:  H⁰ = Z_2,  H¹ = F_2,  H^i = 0 (i≥2)

  Prismatic (conjectural based on framework):
    Same in degrees 0, 1; possibly extra torsion in higher degrees from
    derived corrections.

  KEY OBSERVATION: H¹ = F_2 is NON-ZERO. This means dual numbers have
  non-trivial first cohomology. For SHA program: this is the FIRST place
  prismatic gives non-trivial output that's NOT just Z_p.
""")


def link_to_sha_rotations():
    """Connect dual numbers cohomology to SHA rotation structure.

    From Session 8: F_2[i]/(i²+1) = F_2[ε]/(ε²) via ε = i+1.
    Each rotation ROTR (cyclic shift by 1 bit) on F_2^n corresponds to
    multiplication by ζ_n = primitive n-th root of unity. For n = 2^k (=32 for SHA),
    ζ_n satisfies ζ_n^{2^k} = 1, and minimal polynomial is x^{2^{k-1}} + 1.

    Equivalently: F_2[ζ_{2^k}] ≅ F_2[t]/(t^{2^{k-1}} + 1) ≅ F_2[s]/(s^{2^{k-1}})
      via s = t + 1.

    This is "fat thickening" by the uniformizer to power 2^{k-1}.
    For n = 2: F_2[ε]/(ε²) (our case)
    For n = 4: F_2[ε]/(ε^4)? Need check.
    ...
    For n = 32: F_2[ε]/(ε^{16}) (16-th order thickening).

    Each gives different prismatic cohomology. As n grows, expect MORE
    torsion classes (more "infinitesimal directions").
    """
    print("\n=== Link to SHA rotations ===")
    print("""
  ROTR on n-bit register:
    n = 2:  F_2[s]/(s²)         — our dual numbers (H¹ = F_2)
    n = 4:  F_2[s]/(s⁴)         — order-4 thickening
    n = 8:  F_2[s]/(s⁸)         — order-8 thickening
    n = 16: F_2[s]/(s^16)       — order-16 thickening
    n = 32: F_2[s]/(s^16)       — same! (since 32 = 2·16, Φ_32 = x^16+1, after sub)

  Actually for n = 2^k, the "rotation ring" is F_2[s]/(s^{2^{k-1}}).

  For SHA-256 (32-bit register): rotation ring = F_2[s]/(s^16).

  Conjectural prismatic cohomology pattern:
    H⁰ = Z_2 (always)
    H¹ = F_2 ⊕ ??? (more torsion for higher thickenings)

  Concrete Session 10 target: compute prismatic of F_2[s]/(s^4), F_2[s]/(s^8)
  to see pattern of H¹ growth.
""")


if __name__ == "__main__":
    # Step 1: verify δ-structure on Z_2[ε]/(ε²)
    verify_delta_dual_axioms()

    # Step 2-3: Kähler differentials and de Rham
    explain_kahler_differentials()

    # Step 4: prismatic discussion
    discuss_prismatic_vs_de_rham()

    # Step 5: SHA connection
    link_to_sha_rotations()
