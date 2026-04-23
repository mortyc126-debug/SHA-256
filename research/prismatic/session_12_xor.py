"""
Session 12: Correction — right rotation ring is F_2[s]/(s^n), not F_2[s]/(s^{n/2}).
Then start XOR integration.

CORRECTION (important):

In Sessions 9-11, I identified "rotation ring" для n-bit register as F_2[ζ_n] =
F_2[s]/(s^{n/2}). This is the MINIMAL POLYNOMIAL's ring — contains only ζ_n and
its powers.

BUT: actual ROTR action on F_2^n lives in the FULL GROUP ALGEBRA
F_2[Z/n] = F_2[x]/(x^n - 1).

For n = 2^k: x^n - 1 = (x - 1)^n = (x + 1)^n in F_2.
So F_2[x]/(x^n - 1) = F_2[s]/(s^n) via s = x + 1 (NOT s^{n/2}).

ROTR on F_2^n (as polynomial shift): multiplication by x = 1 + s in F_2[s]/(s^n).

For SHA-256 (n = 32): rotation ring is **F_2[s]/(s^32)**, not F_2[s]/(s^16).

Impact: Session 10's theorem applied to d=32 gives bigger H¹.

This session:
  1. Verify correction
  2. Compute H¹(F_2[s]/(s^32)) via Session 10 theorem
  3. Multi-register (8 copies)
  4. Start XOR integration (from Session 2 formula)
"""


def v_2(k):
    if k == 0: return float('inf')
    count = 0
    while k % 2 == 0:
        k //= 2
        count += 1
    return count


def H1_structure(d):
    """Session 10 theorem: H¹(F_2[s]/(s^d)) = ⊕ Z/2^{v_2(k+1)} for odd k in [1, d-1]."""
    return [v_2(k+1) for k in range(1, d, 2)]


def show_correction():
    print("=== Correction: rotation ring ===")
    print("""
For n-bit register, rotation ring choice:

  OPTION A: F_2[ζ_n] = F_2[s]/(s^{n/2})
    - Minimal polynomial of primitive ζ_n
    - Contains only ζ_n and its powers
    - Small: dim n/2 as F_2-vector space

  OPTION B: F_2[x]/(x^n - 1) = F_2[s]/(s^n)   ← CORRECT for ROTR action
    - Full group algebra of Z/n
    - All elements of F_2^n naturally embed
    - ROTR = multiplication by x in this ring
    - Larger: dim n as F_2-vector space

For SHA-256 (n = 32):
  Option A (my earlier sessions): F_2[s]/(s^16), dim 16
  Option B (correct): F_2[s]/(s^32), dim 32

Both ARE quotients of Z/2^32 structure, but Option B is the natural
rotation ring. Let me apply Session 10 theorem to d=32.
""")


def compute_corrected():
    print("\n=== H¹(F_2[s]/(s^32)) — corrected SHA-256 rotation cohomology ===")
    H1_exp = H1_structure(32)
    print(f"  H¹ structure: exponents = {H1_exp}")
    print(f"  Number of cyclic factors: {len(H1_exp)}")
    print(f"  Order: 2^{sum(H1_exp)}")

    print(f"\n=== Compare to earlier (wrong d=16) case ===")
    H1_wrong = H1_structure(16)
    print(f"  d=16: factors={len(H1_wrong)}, order 2^{sum(H1_wrong)}")
    print(f"  d=32 (correct): factors={len(H1_exp)}, order 2^{sum(H1_exp)}")

    print(f"\n=== Multi-register (8 copies) ===")
    n_reg = 8
    total_exp = sum(H1_exp) * n_reg
    print(f"  H¹(R^⊗8) with R = F_2[s]/(s^32):")
    print(f"  Order 2^{total_exp} per Künneth formula")

    print(f"\n=== Compare to SHA-256 birthday ===")
    print(f"  Rotation cohomology: 2^{total_exp}")
    print(f"  SHA-256 birthday:   2^128")
    if total_exp > 128:
        excess = total_exp - 128
        print(f"  Rotation cohomology EXCEEDS birthday by 2^{excess}")
        print(f"  → rotation layer alone has 'enough' classes to potentially distinguish outputs")
    else:
        short = 128 - total_exp
        print(f"  Rotation cohomology: 2^{128 - total_exp} short of birthday")


def xor_in_cohomology_setup():
    """Begin integrating XOR via Session 2 formula.

    Session 2 formula: δ(x ⊕ y) = δ(x) + δ(y) - xy + 2z(x+y) - 2δ(z) - 3z²
    where z = x ∧ y.

    In cohomological language:
      XOR: R_sum ⊗ R_sum → R_sum (if R_sum is "word ring")
      On δ-structure: XOR's discrepancy from + involves AND-term

    Concrete approach for Session 12 setup:

    1. XOR acts ring-theoretically as: x ⊕ y = x + y - 2·(x ∧ y)
       (so XOR = ADD modulated by AND, essentially)

    2. In rotation ring R = F_2[s]/(s^32):
       - R has ADD (= XOR at bit level within F_2 coefficients)
       - Does NOT have separate "AND" on coefficients
       - BUT has multiplication (ring), which mod 2 corresponds to bit-AND

    3. Observation: in characteristic 2 rings, multiplication of basis elements
       s^i · s^j = s^{i+j} (NOT bitwise AND).
       So "ring multiplication in F_2[s]" ≠ "bitwise AND in F_2^n".

    4. Key issue: XOR (SHA's XOR on words) operates BIT-WISE. Rotation ring
       captures ROTATION but not BIT STRUCTURE.

    5. For full SHA cohomology, need ring that captures BOTH rotation AND
       bit-wise ops. Candidate: R_full = F_2[s_1, s_2, ..., s_{32}]/(s_i^2)
       (multi-variable dual numbers) — but s_i don't respect rotation.

    Or: use more complex derived structure that has both.

    Let me think about this: maybe XOR in cohomology is trivial / straightforward,
    and the ISSUE is AND.
    """
    print("\n=== XOR integration — setup ===")
    print("""
From Session 2: δ(x ⊕ y) = δ(x) + δ(y) - xy + 2z(x+y) - 2δ(z) - 3z²

Cohomological interpretation attempt:

A. IF we view ⊕ as a map of rings R ⊗ R → R (the "⊕ morphism"):
   - On H*(R ⊗ R) = H*(R) ⊗ H*(R) (Künneth), get induced map to H*(R)
   - For TRIVIAL comultiplication (addition): H¹ → H¹ would be sum
   - For XOR specifically: need to track the AND correction

B. IF we view XOR as difference from ADD:
   - ADD = ring operation, acts canonically on H*
   - XOR = ADD modulated by AND (from x⊕y = x+y - 2(x∧y))
   - So XOR-action on H* = ADD-action - 2·(AND-action)

C. For rotation ring F_2[s]/(s^n):
   - "Multiplication" in this ring is NOT bit-wise AND (structurally different)
   - Bit-wise AND requires different ring structure (multi-variable ε_i)

This is the fundamental tension: ROTATION RING (for rotations) vs
BOOLEAN ALGEBRA (for XOR/AND).

Resolution options:
  (i)  Tensor product: R_rot ⊗ R_bool — captures both, but might be overlarge
  (ii) Derived functor approach — extracts each piece separately then combines
  (iii) Give up "integration" — just compute invariants under each op separately

Session 12 identifies this tension concretely. Session 13 target: pick approach.
""")


if __name__ == "__main__":
    show_correction()
    compute_corrected()
    xor_in_cohomology_setup()
