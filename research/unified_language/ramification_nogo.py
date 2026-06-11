"""
Measuring the strength of the prismatic no-go (Thm 3.3 analog) on a toy.

A delta-ring requires a Frobenius lift phi (phi(a) = a^2 mod 2). The
obstruction to lifting Frobenius is exactly NON-SEPARABILITY (ramification)
at 2 of the structure you are lifting.

Rotation lives in the cyclic group C_n, whose group algebra over F_2 is
    F_2[C_n] = F_2[x] / (x^n - 1).
Frobenius (squaring) lifts cleanly to a delta-structure over Z_2 IFF this
ring is SEPARABLE (etale) at 2, i.e. iff x^n - 1 is squarefree over F_2.

Fact to verify computationally (not just cite):
  write n = 2^v * m, m odd. Then over F_2:  x^n - 1 = (x^m - 1)^(2^v),
  and x^m - 1 is squarefree.  So the ramification index (max multiplicity)
  is e_2(n) = 2^v = the 2-part of n.

Consequence:
  - n ODD  (Mersenne-like): e=1, separable, ETALE -> Frobenius lifts ->
    rotation + carry delta-structure UNIFY (matches Mersenne 1.000 result).
  - n = 2^k (SHA word size 32 = 2^5): e = 2^k, TOTALLY RAMIFIED ->
    Frobenius does NOT lift -> maximal obstruction. SHA-256's 32-bit words
    sit at the MAXIMUM of this no-go.

We compute e_2(n) rigorously via polynomial arithmetic over F_2 (a poly is a
Python int; bit i = coefficient of x^i), self-verifying the (x^m-1)^(2^v)
structure by repeated square-roots while the derivative is zero.
"""


def deriv_F2(p):
    """Derivative over F_2: only odd-power terms survive, shifted down by 1."""
    d = 0
    i = 0
    q = p
    while q:
        if (q & 1) and (i & 1):      # coeff of x^i present and i odd
            d |= 1 << (i - 1)
        q >>= 1
        i += 1
    return d


def is_perfect_square_F2(p):
    """Over F_2, p is a square iff all set bits are at even exponents."""
    i = 0
    q = p
    while q:
        if (q & 1) and (i & 1):
            return False
        q >>= 1
        i += 1
    return True


def sqrt_F2(p):
    """Square root of a perfect square over F_2: halve all exponents."""
    r = 0
    i = 0
    q = p
    while q:
        if q & 1:
            r |= 1 << (i // 2)
        q >>= 1
        i += 1
    return r


def x_pow_n_minus_1(n):
    """Polynomial x^n - 1 over F_2 == x^n + 1 (char 2)."""
    return (1 << n) | 1


def ramification_e2(n):
    """Max multiplicity of x^n-1 over F_2, by repeated sqrt while deriv==0.
    Returns (e = 2^v, v, residual_separable_check)."""
    f = x_pow_n_minus_1(n)
    v = 0
    while True:
        df = deriv_F2(f)
        if df != 0:
            break               # separable part reached
        if f in (0, 1):
            break
        # deriv == 0 => f is a perfect square; take root
        assert is_perfect_square_F2(f), "deriv 0 but not a square?!"
        f = sqrt_F2(f)
        v += 1
    # f is now the squarefree (separable) core; verify gcd(f,f')==const
    sep = (gcd_F2(f, deriv_F2(f)) <= 1) if deriv_F2(f) else True
    return (1 << v), v, sep


def gcd_F2(a, b):
    while b:
        # polynomial mod over F_2
        a, b = b, mod_F2(a, b)
    return a


def deg(p):
    return p.bit_length() - 1


def mod_F2(a, b):
    db = deg(b)
    while a and deg(a) >= db:
        a ^= b << (deg(a) - db)
    return a


def ord_2_mod(m):
    """Multiplicative order of 2 mod m (m odd) = size of a rotation-Frobenius
    orbit; relates to how the squaring-Frobenius acts on C_m."""
    if m == 1:
        return 1
    o = 1
    val = 2 % m
    while val != 1:
        val = (val * 2) % m
        o += 1
        if o > m:
            return -1
    return o


if __name__ == "__main__":
    print("Frobenius-lift obstruction = ramification of x^n - 1 at 2\n")
    print(f"{'n':>3} {'2-part v':>9} {'e=2^v':>7} {'separable core?':>16} "
          f"{'ord_2(odd part)':>16} {'verdict':>22}")
    highlights = {8, 16, 32, 64}
    for n in list(range(1, 17)) + [24, 32, 48, 64]:
        e, v, sep = ramification_e2(n)
        # odd part
        m = n
        while m % 2 == 0:
            m //= 2
        ordm = ord_2_mod(m)
        if e == 1:
            verdict = "ETALE: lifts -> UNIFY"
        elif e == n:
            verdict = "TOTALLY RAMIFIED"
        else:
            verdict = "partially ramified"
        star = "  <== SHA word" if n in (32, 64) else ""
        print(f"{n:>3} {v:>9} {e:>7} {str(sep):>16} {ordm:>16} "
              f"{verdict:>22}{star}")

    print("\nReading:")
    print("  e=1 (odd n): x^n-1 separable over F_2 -> etale at 2 -> Frobenius")
    print("    lifts -> rotation+carry delta-structure UNIFY (the Mersenne win).")
    print("  e=2^k (n=2^k): totally ramified -> NO Frobenius lift -> the")
    print("    prismatic Thm-3.3 obstruction is MAXIMAL.")
    print("  SHA-256 words are 32 = 2^5  -> e = 32, the maximum of the no-go.")
    print("  This is WHY a unifying delta-ring fails precisely for SHA's")
    print("  power-of-two word size: it is the most-ramified cyclic structure.")
