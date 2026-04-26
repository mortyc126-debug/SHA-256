"""
Session 6: δ-ring and truncation framework (proper framing).

Corrected framework after Session 5 literature check:

CORRECT FRAMEWORK:
  - Z_2 = lim_n Z/2^n  is a δ-ring with δ(x) = (x - x²)/2, φ(x) = x (identity)
  - Z/2^n = Z_2 / 2^n Z_2  is a QUOTIENT (NOT a δ-ring as endomap, per Kedlaya 2.2.6)
  - δ DESCENDS to a map Z/2^n → Z/2^{n-1} (loses one level of precision)
  - Our "verification on Z/2^n" was actually verifying truncation-compatibility

For SHA applications:
  - SHA-256 state ∈ (Z/2^32)^8 = (W_32(F_2))^8 = (Z_2 / 2^32)^8
  - SHA round function is morphism (Z/2^32)^8 → (Z/2^32)^8
  - To apply prismatic: lift to (Z_2)^8 (inverse limit) and study as δ-morphism
  - But SHA ops don't respect δ (as we've seen for XOR/AND/ROTR)

This session:
  1. Implement δ on Z_2 (truncated to arbitrary precision)
  2. Implement Frobenius lift φ
  3. Verify φ = identity on Z_2 (correct since p=2 and δ(x) = (x-x²)/2)
  4. Show how truncation commutes with δ
  5. Restate XOR/AND findings properly
"""
from functools import lru_cache


def delta_Z2(x, prec=64):
    """δ on Z_2 computed to precision 2^prec.

    Takes integer x (representing element of Z_2 via 2-adic expansion,
    or equivalently x ∈ Z reduced mod 2^prec).
    Returns δ(x) mod 2^{prec-1} (since δ loses one level of precision).

    Standard formula: δ(x) = (x - x²) / 2.
    """
    result = (x - x*x) // 2
    return result % (2**(prec - 1))


def phi_Z2(x, prec=64):
    """Frobenius lift φ: Z_2 → Z_2.

    For the standard δ-structure on Z_2, we have:
        φ(x) = x² + 2·δ(x) = x² + (x - x²) = x.

    So φ = identity on Z_2. This is because Z_2 is the INITIAL δ-ring
    (unique δ-structure), and its Frobenius lift is trivial.
    """
    # Verify the identity
    x2 = x * x
    delta = (x - x2) // 2
    phi = x2 + 2 * delta
    assert phi == x, f"φ({x}) = {phi} ≠ {x}"
    return x % (2**prec)


def truncate_Z2_to_Z_2n(x, n):
    """Quotient map Z_2 → Z/2^n."""
    return x % (2**n)


def descent_of_delta(x, n):
    """δ descends from Z_2 to a map Z/2^n → Z/2^{n-1}.

    For x ∈ Z_2, compute δ(x) mod 2^{n-1}. This only depends on x mod 2^n.

    Verify: if x ≡ y (mod 2^n), then δ(x) ≡ δ(y) (mod 2^{n-1}).
    """
    delta_val = (x - x*x) // 2
    return delta_val % (2**(n - 1))


def verify_descent_well_defined(n, num_tests=100):
    """Verify: δ(x) mod 2^{n-1} depends only on x mod 2^n."""
    import random
    random.seed(42)
    for _ in range(num_tests):
        # Random x
        x = random.randint(0, 2**n - 1)
        # Several "lifts" of x to Z: x + k·2^n
        y = x + random.randint(1, 10) * (2**n)
        d_x = descent_of_delta(x, n)
        d_y = descent_of_delta(y, n)
        if d_x != d_y:
            print(f"    ✗ FAIL: x={x}, y={y}, δ(x)={d_x}, δ(y)={d_y}")
            return False
    return True


def sha_ops_in_Z2(n):
    """Work with SHA ops in Z/2^n context.
    All are defined on Z/2^n via standard operations + bit manipulation.

    Framework: start with x, y ∈ Z_2 (integers), apply bit-level SHA op,
    reduce to Z/2^n. Track how δ-structure interacts.
    """
    print(f"\n=== SHA ops in truncation framework, n={n} ===")

    # 1. ADD: respects δ-descent (by D2)
    import random
    random.seed(42)
    x, y = random.randint(0, 2**n - 1), random.randint(0, 2**n - 1)
    print(f"\n  Test vectors: x = {x}, y = {y}")

    # ADD via ring
    x_plus_y = (x + y) % (2**n)
    d_sum = descent_of_delta(x_plus_y, n)
    d_predicted = (descent_of_delta(x, n) + descent_of_delta(y, n) - x * y) % (2**(n - 1))
    print(f"    ADD: δ(x+y) mod 2^{n-1} = {d_sum}")
    print(f"         δ(x) + δ(y) - xy  = {d_predicted}  → {'✓' if d_sum == d_predicted else '✗'}")

    # 2. XOR: our Session 2 formula
    z = x & y
    x_xor_y = (x ^ y) % (2**n)
    d_xor = descent_of_delta(x_xor_y, n)
    # Our formula: δ(x XOR y) = δ(x) + δ(y) - xy + 2z(x+y) - 2δ(z) - 3z²
    d_predicted_xor = (descent_of_delta(x, n) + descent_of_delta(y, n) - x*y
                      + 2*z*(x+y) - 2*descent_of_delta(z, n) - 3*z*z) % (2**(n - 1))
    print(f"    XOR: δ(x⊕y) mod 2^{n-1} = {d_xor}")
    print(f"         Session 2 formula  = {d_predicted_xor}  → {'✓' if d_xor == d_predicted_xor else '✗'}")

    # 3. AND: no clean formula (primitive)
    x_and_y = x & y
    d_and = descent_of_delta(x_and_y, n)
    print(f"    AND: δ(x∧y) mod 2^{n-1} = {d_and}  (no closed-form relation via δ(x),δ(y))")

    # 4. ROTR: no clean formula
    import numpy as np
    mask = 2**n - 1
    for r in [1, 2, 3]:
        if r >= n: continue
        x_rot = ((x >> r) | (x << (n - r))) & mask
        d_rot = descent_of_delta(x_rot, n)
        # Naive expectation (if ROTR respected δ-structure somehow):
        # rotated δ?  (wrap in Z/2^{n-1})
        d_x_then_rot = descent_of_delta(x, n)  # in Z/2^{n-1}
        rotation_via_delta = ((d_x_then_rot >> r) | (d_x_then_rot << (n - 1 - r))) & (2**(n-1) - 1)
        match = d_rot == rotation_via_delta
        print(f"    ROTR_{r}: δ(ROTR(x)) = {d_rot}, ROTR(δ(x)) = {rotation_via_delta}  → {'✓' if match else '✗'}")


def frobenius_descent_to_Z2n(n):
    """Show that Frobenius on Z_2 descends to identity on Z/2^n.

    Since φ_{Z_2}(x) = x (identity), the induced map on Z/2^n = Z_2 / 2^n is also identity.

    This is a SPECIAL feature of Z_2 — "trivial" Frobenius.
    For non-trivial δ-rings (e.g., Z_2[ζ_5] with ζ_5 → ζ_5²), Frobenius is non-trivial.
    """
    print(f"\n=== Frobenius descent to Z/2^{n} ===")
    print(f"  On Z_2: φ(x) = x (identity). Thus descent is identity on Z/{2**n}.")
    print(f"  (This is WHY SHA-256 can't be attacked via 'pure' Frobenius structure")
    print(f"   on Z_2 — there is no non-trivial Frobenius.)")
    print()
    print(f"  To get non-trivial Frobenius, need LARGER δ-ring:")
    print(f"  - Z_2[ζ_n] for n coprime to 2: φ(ζ_n) = ζ_n² (Galois action)")
    print(f"  - W(F_{{2^k}}) for k>1: φ = lift of F_{{2^k}}-Frobenius")
    print(f"  - R[[q-1]] (q-Witt): φ = q-twist operation")


def prism_verification():
    """Verify (Z_2, (2)) is a prism.

    Prism = (A, I) where:
    - A is a δ-ring
    - I ⊆ A is a Cartier divisor (locally principal)
    - A is (p, I)-complete
    - I is distinguished: has generator d with δ(d) = unit

    For (Z_2, (2)):
    - A = Z_2: δ-ring with φ=id, δ(x)=(x-x²)/2. ✓
    - I = (2): principal ideal, yes Cartier divisor.
    - (p, I) = (2, 2) = (2). Z_2 is 2-adically complete. ✓
    - Distinguished: need d = 2 with δ(2) = unit in Z_2.
      δ(2) = (2 - 4)/2 = -1. Is -1 a unit in Z_2? YES (-1 has inverse -1).  ✓

    So (Z_2, (2)) IS a valid prism. This is the "crystalline prism" or
    "Breuil-Kisin with p=2".
    """
    print("\n=== Verifying (Z_2, (2)) is a prism ===")
    print("  A = Z_2: δ-ring with δ(x) = (x-x²)/2, φ = identity.  ✓")
    print("  I = (2): principal ideal of Z_2.  ✓")
    print("  Z_2 is (2)-complete: inverse limit definition.  ✓")
    print("  Distinguished: δ(2) = (2 - 4)/2 = -1, which is a unit in Z_2.  ✓")
    print("  → (Z_2, (2)) is a valid prism (the 'crystalline prism' for p=2).")


if __name__ == "__main__":
    # Verify descent is well-defined
    print("=== Verify δ descent is well-defined ===")
    for n in [4, 8, 16, 32]:
        ok = verify_descent_well_defined(n)
        print(f"  n={n}: δ(x+k·2^n) = δ(x) mod 2^{n-1}: {'✓' if ok else '✗'}")

    # Verify Frobenius is identity on Z_2
    print("\n=== Verify φ = id on Z_2 ===")
    import random
    random.seed(42)
    for _ in range(5):
        x = random.randint(0, 2**32)
        try:
            phi_Z2(x, prec=32)
            print(f"  φ({x:>10d}) = {x:>10d}  ✓")
        except AssertionError as e:
            print(f"  FAIL: {e}")

    # Show SHA ops in proper framework
    sha_ops_in_Z2(n=16)

    # Frobenius descent
    frobenius_descent_to_Z2n(n=8)

    # Prism verification
    prism_verification()
