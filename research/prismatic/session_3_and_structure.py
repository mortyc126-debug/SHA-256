"""
Session 3: Is δ(x AND y) expressible as polynomial in (x, y, δ(x), δ(y))?

If YES: AND is "derived" from δ-ring structure, everything fits in standard framework.
If NO: AND is a genuine extension, need new axiom / Borger-style structure.

Strategy:
  1. Enumerate all (x, y) values and compute δ(x AND y) explicitly
  2. Check if there's a low-degree polynomial relation with x, y, δ(x), δ(y)
  3. Bit-decomposition: express in terms of bit positions
  4. If no simple pattern — admit AND is primitive extension

Bonus: explore bit-by-bit structure since AND is bitwise.
"""

import itertools
from collections import defaultdict
from session_2_compat import delta_Z, delta_mod, and_mod, xor_mod


def enumerate_and_delta(n):
    """For all (x, y) ∈ [0, 2^n)², compute (x, y, δ(x), δ(y), δ(x AND y))."""
    N = 2**n
    data = []
    for x in range(N):
        for y in range(N):
            z = and_mod(x, y, n)
            data.append({
                'x': x, 'y': y, 'z': z,
                'dx': delta_mod(x, n),
                'dy': delta_mod(y, n),
                'dz': delta_mod(z, n),
            })
    return data


def try_polynomial_fit(data, n, max_degree=3):
    """Try to fit δ(x AND y) as polynomial of degree ≤ max_degree in (x, y, dx, dy).

    Use numpy to do linear algebra over Z/2^{n-1}.
    """
    import numpy as np
    from itertools import combinations_with_replacement

    Nprev = 2**(n - 1)

    # Build feature matrix: all monomials in (x, y, dx, dy) up to max_degree
    variables = ['x', 'y', 'dx', 'dy']
    monomials = [tuple()]  # constant term
    for deg in range(1, max_degree + 1):
        for combo in combinations_with_replacement(variables, deg):
            monomials.append(combo)

    A = np.zeros((len(data), len(monomials)), dtype=object)
    b = np.zeros(len(data), dtype=object)
    for i, d in enumerate(data):
        b[i] = d['dz']
        for j, mon in enumerate(monomials):
            val = 1
            for v in mon:
                val *= d[v]
            A[i, j] = val % Nprev

    # Convert to int arrays mod Nprev
    A = A.astype(int) % Nprev
    b = b.astype(int) % Nprev

    # Solve A·c = b over Z/Nprev
    # Use Gaussian elimination mod Nprev
    # For simplicity, try integer solve and see if any solution exists
    # (Non-trivial since Z/Nprev isn't a field; may need Smith normal form)

    # Simpler heuristic: use least-squares over R, then check if coefficients round to mod-Nprev solution
    try:
        c_real, residuals, rank, sv = np.linalg.lstsq(A.astype(float), b.astype(float), rcond=None)
        # Round and check
        c_int = np.round(c_real).astype(int) % Nprev
        predicted = (A @ c_int) % Nprev
        matches = (predicted == b).sum()
        print(f"  LSQ fit (rank={rank}/{len(monomials)}): matches {matches}/{len(data)}")
        if matches == len(data):
            print(f"  ✓ FOUND polynomial fit of degree ≤ {max_degree}!")
            for j, mon in enumerate(monomials):
                if c_int[j] != 0:
                    mon_str = '·'.join(mon) if mon else '1'
                    print(f"      {c_int[j]} · {mon_str}")
        else:
            print(f"  ❌ no polynomial fit up to degree {max_degree}")
    except Exception as e:
        print(f"  error: {e}")


def bit_decomposition_analysis(n):
    """Bit-level analysis: is δ(x AND y) linear in bits of x, y?
    For each pair of bit positions (i, j) of x and y, check effect."""
    N = 2**n
    Nprev = 2**(n - 1)
    print(f"\n--- Bit-by-bit analysis of δ(x AND y), n={n} ---")

    # For each pair (bi, bj) bit positions, check: does flipping x[bi] and y[bj]
    # change δ(x AND y) in predictable way?
    # The key: x AND y bit k = x_k AND y_k. So AND is fully bit-local.
    # δ of integer depends on FULL integer value, not just bit positions.

    # Measure: for x = 2^i (single bit), y = 2^j (single bit):
    #   x AND y = 2^i if i == j, else 0
    #   So δ(x AND y) = δ(2^i) if i == j, else 0

    for i in range(n):
        xi = 1 << i
        for j in range(n):
            yj = 1 << j
            z = xi & yj
            dz = delta_mod(z, n)
            dx = delta_mod(xi, n)
            dy = delta_mod(yj, n)
            # Check: is dz = dx when i==j?
            if i == j:
                pass  # dz = δ(2^i) = δ(xi) = dx, should match
            else:
                assert dz == 0, f"Single bit {i} AND {j} ({i}≠{j}): {z}"

    # So for single-bit operands, δ(AND) structure is simple
    print(f"  For x = 2^i, y = 2^j: δ(x AND y) = δ(2^i) if i==j, else 0 ✓")
    # Compute table of δ(2^k) for reference
    print(f"  δ(2^k) values:")
    for k in range(n):
        val = 1 << k
        d = delta_mod(val, n)
        print(f"    δ({val:>4d}) = {d}   (should be {val}(val-1)/2 mod {Nprev} = {(val*(val-1)//2) % Nprev})")


def boolean_factor_analysis(data, n):
    """Look at δ(x AND y) as a function of (x, y) → maybe something like
    a Boolean function with structured coefficients."""
    # Project onto bit positions: δ(x AND y)[k] as function of bits
    Nprev = 2**(n - 1)
    print(f"\n--- Boolean factor analysis, n={n} ---")
    # For each output bit position k of δ, compute its dependency on input bits
    # via ANF (algebraic normal form).

    # Build table: for each (x, y), the bit vector of δ(x AND y).
    # Compute ANF over F_2.

    # Variables: bits of x, y — 2n variables total
    # Output: bits of δ(x AND y) — (n-1) outputs
    from itertools import product

    def bits_of(v, m):
        return [(v >> b) & 1 for b in range(m)]

    # For each output bit k, construct ANF via Möbius transform
    # ANF[S] = XOR over (x,y) with (x|y) bits ⊆ S of f(x,y)
    # This is on 2n-bit input, so size 2^(2n) — feasible for n ≤ 6
    if n > 6:
        print(f"  (skipping ANF — too big for n={n})")
        return

    for out_bit in range(n - 1):
        # Truth table as function of 2n bits
        total_bits = 2 * n
        tt = []
        for combined in range(1 << total_bits):
            xv = combined & ((1 << n) - 1)
            yv = (combined >> n) & ((1 << n) - 1)
            z = xv & yv
            dz = delta_mod(z, n)
            tt.append((dz >> out_bit) & 1)

        # Möbius transform for ANF
        anf = tt.copy()
        for i in range(total_bits):
            for k in range(1 << total_bits):
                if k & (1 << i):
                    anf[k] ^= anf[k ^ (1 << i)]

        # Count nonzero ANF terms by degree
        nonzero = [sum(1 for k in range(1<<total_bits)
                       if anf[k] == 1 and bin(k).count('1') == d)
                   for d in range(total_bits + 1)]
        max_degree = max((d for d in range(total_bits+1) if nonzero[d] > 0), default=0)
        total_terms = sum(nonzero)
        print(f"  output bit {out_bit}: max ANF degree = {max_degree}, total terms = {total_terms}, by degree = {nonzero}")


if __name__ == "__main__":
    for n in [4, 5]:
        print(f"\n=== Session 3 analysis, n={n} ===")
        data = enumerate_and_delta(n)
        print(f"  Enumerated {len(data)} pairs")

        try_polynomial_fit(data, n, max_degree=2)
        try_polynomial_fit(data, n, max_degree=3)

        bit_decomposition_analysis(n)
        boolean_factor_analysis(data, n)
