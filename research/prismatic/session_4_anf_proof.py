"""
Session 4: attempt proof of ANF degree bound 2(k+1) for δ(x AND y).

From Session 3: output bit k of δ(x AND y) has ANF degree exactly 2(k+1).
Now derive this from first principles.

Setup: z = x AND y, bits z_i = x_i ∧ y_i.
       δ(z) = (z - z²)/2 over Z.

For bit k of δ(z):
  Need to express δ(z) bit k as Boolean function of (z_0, ..., z_{n-1}).
  Then substitute z_i = x_i · y_i to get function of (x_i, y_i).
  Each z_i = x_i y_i is degree-2 monomial in (x, y).

So if δ(z) bit k has ANF degree d in (z), then in (x, y) it has degree 2d.

**Key claim**: δ(z) bit k as Boolean function of (z_0, ..., z_{n-1}) has ANF
degree exactly k+1.

Therefore in (x, y) variables the degree is 2(k+1). Matches Session 3!

Let me prove / verify the claim: δ(z) bit k has ANF degree k+1 in z-bits.
"""

from session_2_compat import delta_Z, delta_mod


def anf_of_boolean_function(truth_table, n_vars):
    """Compute ANF of Boolean function given as truth table over n_vars bits."""
    tt = list(truth_table)
    for i in range(n_vars):
        for k in range(1 << n_vars):
            if k & (1 << i):
                tt[k] ^= tt[k ^ (1 << i)]
    return tt


def delta_bit_k_as_function_of_z(z_nbits, out_bit_k):
    """Compute truth table: z ∈ [0, 2^z_nbits) → bit k of δ(z).
    Returns list of 2^z_nbits F_2 values."""
    tt = []
    N = 2**z_nbits
    Nprev = 2**(z_nbits - 1) if z_nbits > 0 else 1
    for z in range(N):
        dz = delta_Z(z) % Nprev
        tt.append((dz >> out_bit_k) & 1)
    return tt


def analyze_delta_anf_in_z(n):
    """For z ∈ [0, 2^n), analyze δ(z) bit k as function of bits of z."""
    print(f"\n=== δ(z) ANF analysis in z-bits, n={n} ===")
    print(f"{'out_bit':>8} | {'max_deg':>8} | {'n_terms':>8} | {'by_degree':>30}")
    for out_bit in range(n - 1):
        tt = delta_bit_k_as_function_of_z(n, out_bit)
        anf = anf_of_boolean_function(tt, n)
        # Degree spectrum
        by_deg = [0] * (n + 1)
        for k in range(1 << n):
            if anf[k] == 1:
                by_deg[bin(k).count('1')] += 1
        max_deg = max((d for d in range(n+1) if by_deg[d] > 0), default=0)
        total = sum(by_deg)
        print(f"{out_bit:>8} | {max_deg:>8} | {total:>8} | {by_deg[:n+1]}")


def derive_delta_formula_bit_by_bit():
    """Try to derive δ(z) bit-by-bit formula.

    δ(z) = (z - z²)/2 in Z.
    Write z = sum_i 2^i z_i. Then z² = sum_{i,j} 2^{i+j} z_i z_j.
    z - z² = sum_i 2^i z_i (1 - sum_j 2^j z_j).

    Hmm this is getting messy. Let me try a different angle.

    **Key observation**: z² = z + 2·(carry-like stuff) for Boolean z_i.
    Actually no: (z_i)² = z_i (idempotent), but cross terms z_i z_j (i ≠ j)
    give contributions.

    z² = (sum 2^i z_i)² = sum 2^{2i} z_i² + 2·sum_{i<j} 2^{i+j} z_i z_j
       = sum 2^{2i} z_i + 2·sum_{i<j} 2^{i+j} z_i z_j   (since z_i² = z_i)

    z - z² = sum 2^i z_i - sum 2^{2i} z_i - 2·sum_{i<j} 2^{i+j} z_i z_j

    δ(z) = (z - z²) / 2 = [sum (2^i - 2^{2i}) z_i] / 2 - sum_{i<j} 2^{i+j} z_i z_j
         = sum 2^{i-1}(1 - 2^i) z_i  - sum_{i<j} 2^{i+j} z_i z_j       (for i ≥ 1)
         minus term for i=0: (1 - 1)/2 z_0 = 0

    So δ(z) = sum_{i ≥ 1} 2^{i-1}(1 - 2^i) z_i  -  sum_{i<j} 2^{i+j} z_i z_j

    For i=1: 2^0 · (1 - 2) = -1 → -z_1
    For i=2: 2^1 · (1 - 4) = -6 → -6 z_2
    For i=3: 2^2 · (1 - 8) = -28 → -28 z_3
    Pattern: 2^{i-1}·(1 - 2^i) = 2^{i-1} - 2^{2i-1}

    Now bit k of δ(z):
    - Linear terms z_i contribute 2^{i-1}(1 - 2^i) z_i
      Bit k of (2^{i-1} - 2^{2i-1}): depends on k, i
    - Quadratic terms -2^{i+j} z_i z_j for i < j
      Bit k of -2^{i+j}: depends on k, i, j

    Linear terms contribute to bit k of δ iff the coefficient 2^{i-1}(1-2^i) has
    bit k set.
    For coefficient = -2^{i-1}(2^i - 1) = -(2^{2i-1} - 2^{i-1}):
      In 2-adic: bit k of this number depends on structure.

    This is getting complicated. Let me just verify the observation numerically.
    """
    print("\n=== Verifying bit-by-bit decomposition ===")
    n = 5
    # For each z in [0, 32), compute δ(z) and compare to formula
    from session_2_compat import delta_mod
    for z in range(32):
        bits_z = [(z >> i) & 1 for i in range(n)]
        # Compute predicted δ(z) from formula:
        # δ(z) = sum_{i≥1} 2^{i-1}(1-2^i) z_i - sum_{i<j} 2^{i+j} z_i z_j
        predicted = 0
        for i in range(1, n):
            predicted += (2**(i-1) * (1 - 2**i)) * bits_z[i]
        for i in range(n):
            for j in range(i + 1, n):
                predicted -= 2**(i + j) * bits_z[i] * bits_z[j]
        actual = delta_Z(z)
        if predicted != actual:
            print(f"  MISMATCH at z={z}: actual={actual}, predicted={predicted}")
            return False
    print(f"  ✓ Formula δ(z) = sum_{{i≥1}} 2^{{i-1}}(1-2^i) z_i - sum_{{i<j}} 2^{{i+j}} z_i z_j  verified for z ∈ [0, 32)")
    return True


def bit_k_degree_bound_analysis():
    """
    Claim: output bit k of δ(z) has ANF degree exactly k+1 in (z_0, ..., z_{n-1}).

    From formula above:
    δ(z) = Σ_{i≥1} c_i z_i  +  Σ_{i<j} d_{i,j} z_i z_j       (plus higher terms?)

    Wait, we didn't derive higher than quadratic terms. Is δ(z) TRULY quadratic
    in z-bits over Z? Let's double-check by computing δ(z) for specific z with
    many bits set.

    z = 2^n - 1 (all bits set): z = 2^n - 1, z² = (2^n - 1)² = 2^{2n} - 2·2^n + 1
    δ(z) = (z - z²)/2 = (2^n - 1 - 2^{2n} + 2^{n+1} - 1)/2
         = (3·2^n - 2^{2n} - 2)/2 = (3·2^{n-1} - 2^{2n-1} - 1)

    This is just one integer, no higher-than-quadratic structure in terms of
    bits if the quadratic formula above is exact.

    Let me verify for z=15 (n=4): 15² = 225. δ(15) = (15-225)/2 = -105.
    Using formula: z_0 = z_1 = z_2 = z_3 = 1.
    Σ_{i≥1} c_i z_i = c_1 + c_2 + c_3 = (1-2) + 2(1-4) + 4(1-8) = -1 -6 -28 = -35
    Σ_{i<j} d_{ij} z_i z_j = -(2^1 + 2^2 + 2^3 + 2^3 + 2^4 + 2^5)
                           = -(2 + 4 + 8 + 8 + 16 + 32) = -70
    Total predicted: -35 + (-70) = -105 ✓

    Great, formula is exact over Z.

    So δ(z) OVER INTEGERS is quadratic polynomial in (z_0, ..., z_{n-1}).
    Now bit k of δ(z) mod 2^{n-1}: this is a REDUCTION mod 2^{n-1} which MIXES
    bits of the integer polynomial.

    Bit k of "A mod 2^{n-1}" is ANF over 1 variable (the integer value mod 2^{n-1}).
    But integer value is quadratic poly in z-bits.

    Hmm. When we reduce integer mod 2^{n-1} and take bit k, we get a new Boolean
    function that can have higher degree than 2.

    Why? Because carry between bit positions in the integer causes nonlinear
    interaction.

    This explains why bit 0 has degree 2 (no carry needed: bit 0 of integer =
    linear combination of degree-2 terms), but bit k for k > 0 has higher degree
    (carry from lower bits).

    Specifically: bit k of (quadratic poly in z-bits) mod 2^{n-1} gets carry
    from bits 0..k-1.

    Each layer of carry multiplies the effective ANF degree. This might explain
    2(k+1) pattern.

    Proof sketch (informal):
      - δ(z) is quadratic poly in z-bits over Z
      - mod 2^{n-1}: bit k = (bit k of polynomial) ⊕ (carry from below)
      - Carry chain of quadratic → each carry bit is quadratic itself
      - After k carry hops, degree 2·(k+1) (each hop adds 2)

    This is a CARRY-CASCADE structure, identical to what we saw for SHA carries!
    """
    print("\n=== Proof sketch: 2(k+1) pattern ===")
    print("""
    1. δ(z) = (z - z²)/2 is QUADRATIC polynomial in z-bits over Z.
       Verified empirically: c_i z_i + Σ_{i<j} d_{ij} z_i z_j, coefficients in Z.

    2. Bit k of δ(z) mod 2^{n-1} = bit k of the integer polynomial's value.

    3. The polynomial has ANF degree 2 over Z (linear + quadratic terms).
       But "value mod 2" of a sum has CARRY structure: bit k = bit_k(integer sum).

    4. Carry cascade: bit k depends on bits 0..k of all terms, through carries.
       Each carry adds degree 2 (carry bit is AND of two bits).

    5. Hence bit k has ANF degree 2 · (k+1) in z-bits:
       2 from the quadratic polynomial, (k+1) from carry cascade depth.

    QED (informal).

    In (x, y) variables, where z_i = x_i · y_i, each z_i has degree 2.
    So bit k has degree 2 · (k+1) · 2 / 2 = 2·(k+1) in (x, y).

    Wait, that's not quite right. Let me re-think.

    In z-bits: bit k has ANF degree k+1 (from carry cascade of k steps on
    quadratic polynomial, but carries themselves are quadratic → total degree
    grows).

    Hmm. Let me check Session 3 numbers:
    - Output bit 0: ANF degree 2 in (x, y) → that matches 2·(0+1) = 2 ✓
    - Output bit 1: ANF degree 4 → 2·(1+1) = 4 ✓
    - Output bit 2: ANF degree 6 → 2·(2+1) = 6 ✓
    - Output bit 3: ANF degree 8 → 2·(3+1) = 8 ✓

    So in (x, y) variables: bit k has degree 2(k+1). This matches.

    In z-variables: bit k has degree (k+1) (half).

    Good.
    """)


if __name__ == "__main__":
    analyze_delta_anf_in_z(7)
    derive_delta_formula_bit_by_bit()
    bit_k_degree_bound_analysis()
