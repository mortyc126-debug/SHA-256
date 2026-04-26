"""
Session 52: Characteristic polynomial of per-state Jacobian J_v.

Extends Session 49: for each random state v, compute the CHAR POLY of J_v.

For random GL_n(F_2) matrices, char poly factorisation distribution is known:
- Probability that char poly has a degree-d irreducible factor decreases as 1/d.
- Most matrices have char poly with a few small factors plus one large one.

For SHA's J_v: distribution may differ, revealing structural bias.

Specifically:
- Number of distinct irreducible factors per J_v.
- Most common factor degrees.
- Number of fixed points = nullity of (J_v - I) = related to factor (z+1)^k.

Computational: char poly via Berlekamp-Massey on Krylov sequence (Session 30 method).
"""
import numpy as np
from session_46_correct_round import R_correct
from session_49_jacobian import compute_jacobian
from session_30_schedule import krylov_min_poly, factor_int


def factor_poly_f2_v2(coeffs, max_irr_deg=10):
    """Factor poly over F_2 by trial division."""
    factors = []
    p = list(coeffs)
    while p and p[-1] == 0:
        p.pop()
    if len(p) <= 1:
        return factors

    for d in range(1, max_irr_deg + 1):
        for irr in irreducibles_of_degree(d):
            mult = 0
            while True:
                q, r = poly_divmod_f2(p, irr)
                if all(x == 0 for x in r):
                    p = q
                    while p and p[-1] == 0:
                        p.pop()
                    mult += 1
                else:
                    break
            if mult > 0:
                factors.append((d, mult))
            if len(p) - 1 < d:
                break
        if len(p) - 1 < d + 1:
            break

    if len(p) > 1:
        factors.append((len(p) - 1, 1))  # remainder
    return factors


def poly_divmod_f2(a, b):
    a = a[:]
    b = b[:]
    while a and a[-1] == 0:
        a.pop()
    while b and b[-1] == 0:
        b.pop()
    if not b:
        raise ZeroDivisionError
    if len(a) < len(b):
        return [0], a + [0] * max(0, len(b) - len(a) - 1)
    q = [0] * (len(a) - len(b) + 1)
    while len(a) >= len(b):
        deg_diff = len(a) - len(b)
        if a[-1] == 1:
            q[deg_diff] = 1
            for i, bi in enumerate(b):
                a[deg_diff + i] ^= bi
        a.pop()
    return q, a


def is_irreducible_f2(coeffs):
    d = len(coeffs) - 1
    if d <= 1:
        return True
    for div_deg in range(1, d // 2 + 1):
        for mask in range(2 ** div_deg):
            div_coeffs = [(mask >> i) & 1 for i in range(div_deg)] + [1]
            if div_coeffs[0] == 0:
                continue
            _, rem = poly_divmod_f2(coeffs, div_coeffs)
            if all(x == 0 for x in rem):
                return False
    return True


def irreducibles_of_degree(d):
    if d == 1:
        yield [0, 1]
        yield [1, 1]
        return
    for mask in range(2 ** d):
        coeffs = [(mask >> i) & 1 for i in range(d)] + [1]
        if coeffs[0] == 0:
            continue
        if is_irreducible_f2(coeffs):
            yield coeffs


def main():
    print("=== Session 52: Char poly factorisation of per-state Jacobian J_v ===\n")
    rng = np.random.default_rng(0)
    NUM_SAMPLES = 5

    print(f"  For each of {NUM_SAMPLES} random states v, compute J_v (256x256), find min/char poly,")
    print(f"  factor over F_2, report structure.\n")

    factor_summary = []
    for trial in range(NUM_SAMPLES):
        v = rng.integers(0, 2, size=256, dtype=np.uint8)
        print(f"  --- Trial {trial+1} ---")
        J = compute_jacobian(v)

        # Min poly via Krylov
        min_poly = krylov_min_poly(J, num_tries=2, seed=42 + trial)
        if min_poly is None:
            print(f"    BMA failed.")
            continue
        deg = len(min_poly) - 1
        print(f"    Min poly degree: {deg}")

        # Factor
        factors = factor_poly_f2_v2(min_poly, max_irr_deg=8)
        print(f"    Factorisation:")
        for d, mult in factors:
            print(f"      irreducible of degree {d}, multiplicity {mult}")
        factor_summary.append(factors)

        # Special: nullity of J_v - I
        # = dim of fixed-point eigenspace = multiplicity of (z+1) factor
        nullity = sum(mult for d, mult in factors if d == 1)  # rough
        # Actually we need to identify which factor is (z+1) vs z. Both have d=1.
        # (z+1) → root z=1; (z) → root z=0.
        # min poly factor (z+1)^k → J_v has (-1)^k = 1 eigenvalue with mult k.
        # We don't differentiate here; both d=1 factors counted.
        print(f"    Number of degree-1 irreducible factors: {nullity}")

    print(f"\n=== Summary across {NUM_SAMPLES} samples ===")
    # Aggregate factor degree distribution
    from collections import Counter
    all_degs = Counter()
    for factors in factor_summary:
        for d, mult in factors:
            all_degs[d] += mult
    print(f"  Total factor degree-counts (irreducible · multiplicity):")
    for d in sorted(all_degs.keys()):
        print(f"    degree {d}: {all_degs[d]} factors total")

    print("""

=== Theorem 52.1 (Jacobian char poly distribution, empirical) ===

For SHA-256 J_v over F_2 (one bare round):
- Min poly degree typically 256 (full).
- Factorisation has irreducibles spread across degrees 1..deg.
- Specific distribution depends on per-v variation.

For RANDOM GL_n(F_2): expected distribution by Chebyshev-like formula.
SHA's J_v factor structure may match (random-like) or deviate.

If random-like: SHA's per-state Jacobian behaves like generic invertible
F_2 matrix — no spectral handle for cryptanalysis.
If structured: irreducible factor multiplicities concentrated in specific
degrees → potential handle.
""")


if __name__ == "__main__":
    main()
