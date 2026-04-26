"""
Session 2: δ-structure on Z/2^n, compatibility test with SHA operations.

From Session 1 we know:
  δ on Z is standard: δ(x) = (x - x²)/2
  δ on Z/2^n is well-defined as map Z/2^n → Z/2^{n-1}

Question: how do SHA's operations interact with δ?
  - ADD: RING operation, δ respects via D2: δ(x+y) = δ(x) + δ(y) - xy
  - · (mult): RING operation, δ respects via D3
  - XOR: NOT a ring op in Z/2^n. δ may or may not.
  - ROTR: permutation of bits. Not a ring endomorphism.
  - AND: not a ring op in usual sense.
  - Ch/Maj: compositions of XOR/AND.

For each non-ring op, define "discrepancy":
  discrepancy(op)(x, y) = δ(op(x, y)) - "expected" for a ring-like op

We'll compute discrepancy distributions. Small/structured discrepancy =
some hope for extension. Random discrepancy = obstruction.
"""

from fractions import Fraction


def delta_Z(x, p=2):
    """Standard δ on Z: δ(x) = (x - x^p)/p."""
    return (x - x**p) // p


def delta_mod(x, n, p=2):
    """δ on Z/p^n → Z/p^{n-1}. Compute in Z then reduce."""
    x_lifted = x % (p**n)
    d = delta_Z(x_lifted, p)
    return d % (p**(n - 1)) if n > 1 else d % 1


def add_mod(x, y, n):
    return (x + y) % (2**n)


def xor_mod(x, y, n):
    return (x ^ y) % (2**n)


def and_mod(x, y, n):
    return (x & y) % (2**n)


def not_mod(x, n):
    return ((~x) & (2**n - 1))


def rotr_mod(x, r, n):
    mask = 2**n - 1
    return ((x >> r) | (x << (n - r))) & mask


def ch_mod(e, f, g, n):
    mask = 2**n - 1
    return ((e & f) ^ (~e & g)) & mask


def maj_mod(a, b, c, n):
    mask = 2**n - 1
    return ((a & b) ^ (a & c) ^ (b & c)) & mask


# === SECTION 1: Verify δ axioms on Z/2^n ===

def verify_axioms(n):
    """Verify D1, D2, D3 on Z/2^n (with δ: Z/2^n → Z/2^{n-1})."""
    p = 2
    N = 2**n
    Nprev = 2**(n - 1)

    print(f"\n--- Z/{N} as δ-ring (δ: Z/{N} → Z/{Nprev}) ---")

    # D1
    assert delta_mod(0, n) == 0
    assert delta_mod(1, n) == 0
    print(f"  D1: δ(0) = δ(1) = 0 ✓")

    # D2: δ(x + y) = δ(x) + δ(y) - xy  (all mod 2^{n-1})
    bad = 0
    for x in range(N):
        for y in range(N):
            lhs = delta_mod(add_mod(x, y, n), n)
            rhs = (delta_mod(x, n) + delta_mod(y, n) - x * y) % Nprev
            if lhs != rhs:
                bad += 1
    print(f"  D2: δ(x+y) = δ(x) + δ(y) - xy in Z/{Nprev} -- {'✓ all' if bad == 0 else f'❌ {bad} failures'}")

    # D3: δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y)  mod 2^{n-1}
    bad = 0
    for x in range(N):
        for y in range(N):
            lhs = delta_mod((x * y) % N, n)
            rhs = (x**2 * delta_mod(y, n) + y**2 * delta_mod(x, n) +
                   2 * delta_mod(x, n) * delta_mod(y, n)) % Nprev
            if lhs != rhs:
                bad += 1
    print(f"  D3: δ(xy) formula in Z/{Nprev} -- {'✓ all' if bad == 0 else f'❌ {bad} failures'}")


# === SECTION 2: SHA operations discrepancy ===

def discrepancy_xor(x, y, n):
    """For XOR, measure how far δ(x XOR y) is from the 'ring-analog' expectation.

    Ring + gives: δ(x+y) = δ(x) + δ(y) - xy.
    XOR is NOT +. So δ(x XOR y) may differ. We compute the discrepancy
    relative to that formula — if 0 for all (x,y), XOR respects δ-structure.
    """
    Nprev = 2**(n - 1)
    actual = delta_mod(xor_mod(x, y, n), n)
    ring_expected = (delta_mod(x, n) + delta_mod(y, n) - x * y) % Nprev
    return (actual - ring_expected) % Nprev


def discrepancy_and(x, y, n):
    """δ(x AND y) discrepancy from D3 (multiplication) formula.
    AND in Z/2^n is NOT multiplication, but similar in char 2."""
    Nprev = 2**(n - 1)
    actual = delta_mod(and_mod(x, y, n), n)
    mult_expected = (x**2 * delta_mod(y, n) + y**2 * delta_mod(x, n) +
                     2 * delta_mod(x, n) * delta_mod(y, n)) % Nprev
    return (actual - mult_expected) % Nprev


def discrepancy_rotr(x, r, n):
    """δ(ROTR(x, r)) vs δ(x)?
    Natural expectation: if ROTR were a ring automorphism, δ(ROTR(x)) = ROTR(δ(x)).
    But ROTR isn't a ring auto for Z/2^n (multiplication by 2 = left shift with wrap,
    nothing to do with ROTR).
    So just measure: |δ(ROTR(x))  -  ROTR(δ(x))| distribution."""
    Nprev = 2**(n - 1)
    # Careful: ROTR is on n bits, but δ lives in (n-1) bits.
    # For 'expected' we rotate δ(x) as an (n-1)-bit number
    dx_rotated = rotr_mod(delta_mod(x, n), r, n - 1)
    actual = delta_mod(rotr_mod(x, r, n), n)
    return (actual - dx_rotated) % Nprev


def histogram_discrepancy(op_func, n, sample_all=True, max_samples=10000):
    """For binary op, compute discrepancy distribution."""
    N = 2**n
    counts = {}
    total = 0
    if sample_all and N*N <= 65536:
        pairs = [(x, y) for x in range(N) for y in range(N)]
    else:
        import random
        random.seed(42)
        pairs = [(random.randint(0, N-1), random.randint(0, N-1))
                 for _ in range(max_samples)]
    for x, y in pairs:
        d = op_func(x, y, n)
        counts[d] = counts.get(d, 0) + 1
        total += 1
    # Return top entries
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    return items, total


def histogram_discrepancy_unary(op_func, n, r=None, sample_all=True, max_samples=10000):
    """For unary op (with optional param r)."""
    N = 2**n
    counts = {}
    total = 0
    values = range(N) if sample_all else [random.randint(0, N-1) for _ in range(max_samples)]
    for x in values:
        if r is not None:
            d = op_func(x, r, n)
        else:
            d = op_func(x, n)
        counts[d] = counts.get(d, 0) + 1
        total += 1
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    return items, total


def test_compatibility(n):
    print(f"\n=== δ-compatibility test, Z/2^{n} ===")

    # ADD: should be 0 discrepancy by D2 (exact)
    def disc_add(x, y, n):
        Nprev = 2**(n - 1)
        actual = delta_mod(add_mod(x, y, n), n)
        ring_expected = (delta_mod(x, n) + delta_mod(y, n) - x * y) % Nprev
        return (actual - ring_expected) % Nprev
    hist, total = histogram_discrepancy(disc_add, n)
    print(f"\n  ADD:")
    print(f"    All discrepancies zero?  {len(hist)==1 and hist[0][0]==0}")
    print(f"    Top discrepancies: {hist[:5]}")

    # XOR: not ring op, expect nonzero
    hist, total = histogram_discrepancy(discrepancy_xor, n)
    n_zero = next((c for d, c in hist if d == 0), 0)
    print(f"\n  XOR:")
    print(f"    Fraction with disc=0: {n_zero}/{total} = {n_zero/total:.3f}")
    print(f"    Top discrepancies (disc, count): {hist[:5]}")

    # AND: not ring op, expect nonzero
    hist, total = histogram_discrepancy(discrepancy_and, n)
    n_zero = next((c for d, c in hist if d == 0), 0)
    print(f"\n  AND:")
    print(f"    Fraction with disc=0: {n_zero}/{total} = {n_zero/total:.3f}")
    print(f"    Top discrepancies: {hist[:5]}")

    # ROTR: not ring op
    for r in [1, 2, 3]:
        if r >= n: continue
        hist, total = histogram_discrepancy_unary(discrepancy_rotr, n, r=r)
        n_zero = next((c for d, c in hist if d == 0), 0)
        print(f"\n  ROTR_{r}:")
        print(f"    Fraction with disc=0: {n_zero}/{total} = {n_zero/total:.3f}")
        print(f"    Top discrepancies: {hist[:5]}")


if __name__ == "__main__":
    for n in [4, 6, 8]:
        verify_axioms(n)
        test_compatibility(n)
