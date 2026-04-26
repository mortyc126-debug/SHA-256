"""
Session 2 continued: derive EXPLICIT formula for XOR discrepancy.

Key algebraic identity:  x XOR y = (x + y) - 2·(x AND y)

Using D2 (δ(x+y) = δ(x) + δ(y) - xy) repeatedly:

Let z = x AND y. Then:
  δ(x XOR y)
    = δ(x + y - 2z)
    = δ(x+y) + δ(-2z) - (x+y)·(-2z)                      [by D2]
    = [δ(x) + δ(y) - xy] + δ(-2z) + 2z(x+y)              [expand δ(x+y)]

  δ(-2z) = -δ(2z) - (2z)² = -(2δ(z) - z²) - 4z² = -2δ(z) - 3z²
  (using D2 twice: δ(2z) = 2δ(z) - z², then δ(a + (-a)) = 0)

  Combining:
  δ(x XOR y) = δ(x) + δ(y) - xy  +  2z(x+y) - 2δ(z) - 3z²

Discrepancy (vs ring-+ formula):
  D_XOR(x, y) := δ(x XOR y) - [δ(x) + δ(y) - xy]
              = 2z(x+y) - 2δ(z) - 3z²   where z = x AND y

This is AN EXPLICIT POLYNOMIAL in (x, y, δ(x AND y)).
Not random — it's a concrete obstruction.

If we include δ on x AND y into the structure, XOR becomes derived.
"""
from session_2_compat import (
    delta_Z, delta_mod, add_mod, xor_mod, and_mod, rotr_mod
)


def xor_discrepancy_predicted(x, y, n):
    """Predicted XOR discrepancy via derived formula, mod 2^{n-1}."""
    Nprev = 2**(n - 1)
    z = x & y
    pred = 2 * z * (x + y) - 2 * delta_Z(z) - 3 * z**2
    return pred % Nprev


def xor_discrepancy_actual(x, y, n):
    Nprev = 2**(n - 1)
    actual = delta_mod(xor_mod(x, y, n), n)
    ring_formula = (delta_mod(x, n) + delta_mod(y, n) - x * y) % Nprev
    return (actual - ring_formula) % Nprev


def verify_xor_formula(n):
    """Verify predicted formula matches actual discrepancy EXACTLY."""
    N = 2**n
    bad = 0
    for x in range(N):
        for y in range(N):
            if xor_discrepancy_actual(x, y, n) != xor_discrepancy_predicted(x, y, n):
                bad += 1
                if bad < 5:
                    print(f"    MISMATCH at ({x},{y}): actual={xor_discrepancy_actual(x,y,n)} pred={xor_discrepancy_predicted(x,y,n)}")
    status = "✓ EXACT formula" if bad == 0 else f"❌ {bad} mismatches"
    print(f"  XOR discrepancy = 2z(x+y) - 2δ(z) - 3z²  where z = x AND y:  {status}")


def verify_and_formula(n):
    """Derive formula for AND.
    Since x AND y = ((x + y) - (x XOR y)) / 2, we can derive δ(x AND y)
    from δ(x XOR y) and δ(x + y).
    But this is circular — x AND y is PRIMITIVE, not derived from + and XOR.

    Alternative: find δ(x AND y) polynomial in (x, y, δ(x), δ(y))?
    Let's check: is δ(x AND y) a polynomial in x, y, δ(x), δ(y)?
    """
    N = 2**n
    # Collect triples (x, y) → δ(x AND y). See if there's a polynomial relation.
    # Quick test: fix x and see how δ(x AND y) varies with y.
    print(f"\n  AND: does δ(x AND y) have closed form?")
    print(f"    x | y | x AND y | δ(x AND y) | polynomial attempt")
    for x in [3, 5, 7, 15]:
        if x >= N: continue
        for y in [3, 5, 7, 15]:
            if y >= N: continue
            z = x & y
            dz = delta_mod(z, n)
            # Try: δ(x AND y) in terms of lower bits of x, y?
            print(f"    {x} | {y} | {z} | {dz}  | (raw value, no obvious formula)")


def test_xor_formula_scales():
    print("=== XOR discrepancy formula verification ===")
    for n in [4, 6, 8, 10]:
        print(f"\n--- n = {n} (Z/{2**n} → Z/{2**(n-1)}) ---")
        verify_xor_formula(n)


def test_rotr_discrepancy_structure(n):
    """For ROTR, is there a formula? Unlikely clean. Test empirically.

    ROTR_r: δ(ROTR_r(x)) vs ROTR_r(δ(x))?
    These live in different rings (Z/2^{n-1} vs Z/2^{n}), need care."""
    Nprev = 2**(n - 1)
    print(f"\n  ROTR_r discrepancy pattern (n={n}):")
    # Check if discrepancy depends LINEARLY on bits of x
    # Systematic: for each bit position b in x, measure effect on discrepancy

    # For fixed r, compute δ(ROTR(x)) - ROTR_{n-1}(δ(x)) for each x
    for r in [1, 2, 3]:
        if r >= n: continue
        count = 0; zeros = 0
        for x in range(2**n):
            actual = delta_mod(rotr_mod(x, r, n), n)
            expected = rotr_mod(delta_mod(x, n), r, n - 1)  # rotate in smaller ring
            disc = (actual - expected) % Nprev
            if disc == 0: zeros += 1
            count += 1
        print(f"    ROTR_{r}: {zeros}/{count} = {zeros/count:.3f} zero")


if __name__ == "__main__":
    test_xor_formula_scales()

    print("\n\n=== AND analysis ===")
    verify_and_formula(6)

    print("\n\n=== ROTR analysis ===")
    test_rotr_discrepancy_structure(6)
    test_rotr_discrepancy_structure(8)
