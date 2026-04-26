"""
Session 24: Why does Σ_1 have minimal polynomial degree 11?

Session 23 computed:
  Σ_0 min poly deg = 32 (= full dim)
  Σ_1 min poly deg = 11 (unexpectedly small!)
  σ_0, σ_1 min poly deg = 32

Goal: structural explanation for Σ_1 = 11.

Framework: unipotent M = ⊕_{r ∈ R}(1+s)^r in F_2[s]/(s^n), |R| odd
  ⇒ M = I + N with N nilpotent
  ⇒ min poly of M is (z+1)^a where a = nilpotency of N

Lucas's theorem (char 2):
  (1+s)^r = Σ_{bin(i) ⊆ bin(r)} s^i
  Coefficient of s^i in M: c_i = |{r ∈ R : (i & r) == i}| mod 2

Let d = min{i > 0 : c_i = 1} (smallest surviving position after cancellations).

Lemma: If c_0 = 1 and d < n, then N = s^d · u where u is a unit in F_2[[s]]/(s^{n-d}),
       so N^k = s^{kd} · u^k, nilpotency index a = ⌈n/d⌉.

Apply to SHA-256 (n=32):
  Σ_0: R={2,13,22}, d=1 (since only 13 covers bit 0), a = ⌈32/1⌉ = 32 ✓
  Σ_1: R={6,11,25}, positions 1,2 doubly covered (cancel), d=3, a = ⌈32/3⌉ = 11 ✓

This EXPLAINS the "anomaly" — position-3 is the first surviving cancellation level
because (6, 11, 25) has specific binary overlap pattern.
"""
import numpy as np
from math import ceil, log2
from session_14_sigma0 import lucas_expansion


def coverage_count(i, R):
    """How many r ∈ R have (i & r) == i (i.e., bin(i) ⊆ bin(r))."""
    return sum(1 for r in R if (i & r) == i)


def operator_polynomial(R, n):
    """Compute polynomial M = ⊕_r (1+s)^r in F_2[s]/(s^n) as a set of positions."""
    positions = set()
    for r in R:
        for p in lucas_expansion(r, n - 1):
            if p in positions:
                positions.remove(p)
            else:
                positions.add(p)
    return sorted(positions)


def smallest_surviving_positive(R, n):
    """Find smallest i > 0 with c_i = 1 (smallest surviving positive position after XOR)."""
    for i in range(1, n):
        if coverage_count(i, R) % 2 == 1:
            return i
    return None  # N is zero


def predicted_nilpotency(R, n):
    """Predicted nilpotency of N = M - I where M = ⊕_r (1+s)^r mod s^n."""
    if sum(1 for _ in R) % 2 == 0:
        # c_0 = 0; M is not unipotent in standard form
        return None
    d = smallest_surviving_positive(R, n)
    if d is None:
        return 1  # N = 0
    return ceil(n / d)


def predicted_order(nilp):
    """Order of unipotent M = I+N on F_2^n: smallest 2^m with 2^m ≥ nilp."""
    if nilp <= 1:
        return 1
    return 2 ** ceil(log2(nilp))


def build_N_polynomial(R, n):
    """N = M - I as polynomial coefficient vector of length n (F_2)."""
    poly = np.zeros(n, dtype=np.uint8)
    for i in range(n):
        poly[i] = coverage_count(i, R) % 2
    poly[0] = 0  # subtract identity
    return poly


def poly_mult_mod(p, q, n):
    """Multiply polynomials p, q in F_2[s]/(s^n)."""
    out = np.zeros(n, dtype=np.uint8)
    for i in range(n):
        if p[i] == 0:
            continue
        for j in range(n - i):
            if q[j] == 1:
                out[i + j] ^= 1
    return out


def nilpotency_of_poly(N, n):
    """Compute k = smallest power with N^k = 0 in F_2[s]/(s^n)."""
    cur = N.copy()
    for k in range(1, n + 2):
        if cur.sum() == 0:
            return k
        cur = poly_mult_mod(cur, N, n)
    return -1


def analyze(name, R, n):
    print(f"\n=== {name} (R={R}) ===")
    M_poly = operator_polynomial(R, n)
    print(f"  Polynomial positions in s-basis: {M_poly}")
    has_const = 0 in M_poly
    print(f"  Constant term (c_0 = |R| mod 2): {int(has_const)}")
    if not has_const:
        print(f"  NOT unipotent — skipping nilpotency analysis.")
        return

    # Coverage table for small i
    print(f"  Coverage c_i for i=0..8: "
          f"{[coverage_count(i, R) for i in range(9)]}")
    print(f"  Cancellations (c_i = 0 for i > 0): "
          f"{[i for i in range(1, 9) if coverage_count(i, R) % 2 == 0]}")

    d = smallest_surviving_positive(R, n)
    print(f"  Smallest surviving positive position d = {d}")

    nilp_pred = predicted_nilpotency(R, n)
    print(f"  Predicted nilpotency ⌈{n}/{d}⌉ = {nilp_pred}")

    # Verify empirically at polynomial level
    N_poly = build_N_polynomial(R, n)
    nilp_emp = nilpotency_of_poly(N_poly, n)
    print(f"  Empirical nilpotency (polynomial level): {nilp_emp}")
    assert nilp_emp == nilp_pred, f"Mismatch: {nilp_emp} vs {nilp_pred}"
    print(f"  ✓ Prediction verified")

    ord_pred = predicted_order(nilp_pred)
    print(f"  Predicted order of M: 2^⌈log2({nilp_pred})⌉ = {ord_pred}")
    print(f"  Min poly degree = nilpotency = {nilp_pred}")


def systematic_scan(n=32, max_r=31):
    """Scan triples of rotation constants to find other 'anomalies'.
    Find triples (a, b, c) where smallest surviving d > 1.
    """
    print(f"\n=== Systematic scan: rotation triples with d ≥ 2 ===")
    found = []
    for a in range(1, max_r + 1):
        for b in range(a + 1, max_r + 1):
            for c in range(b + 1, max_r + 1):
                R = [a, b, c]
                d = smallest_surviving_positive(R, n)
                if d is not None and d >= 2:
                    nilp = ceil(n / d)
                    found.append((d, nilp, R))
    found.sort(key=lambda x: (-x[0], x[2]))
    print(f"  Found {len(found)} triples with d ≥ 2:")
    print(f"  Top by d (d, nilpotency, triple):")
    for d, nilp, R in found[:15]:
        mark = " ← SHA Σ_1" if R == [6, 11, 25] else ""
        print(f"    d={d}, nilp={nilp:>3}, R={R}{mark}")


def theorem_statement():
    print("""

=== Theorem 24.1 (Lucas-XOR nilpotency) ===

Setting: Let R ⊆ Z_{>0} be a finite multiset with |R| odd.
         Let M = ⊕_{r ∈ R} (1+s)^r in F_2[s]/(s^n).

Then:
  (a) M = I + N with N nilpotent.
  (b) Let d = min{i > 0 : c_i(M) = 1}, where
        c_i(M) = |{r ∈ R : (i & r) = i}| mod 2.
      (d = ∞ means M = I.)
  (c) Nilpotency index of N is exactly ⌈n / d⌉.
  (d) Minimal polynomial of M over F_2 is (z + 1)^{⌈n/d⌉}.
  (e) Order of M on F_2^n is 2^{⌈log_2⌈n/d⌉⌉}.

Proof sketch (c):
  By Lucas (char 2): (1+s)^r = Σ_{bin(i) ⊆ bin(r)} s^i.
  So coefficient of s^i in M is c_i as defined.
  N = M - I has expansion N = Σ_{i ≥ d} c_i s^i = s^d · u, u ∈ F_2[[s]] unit.
  In F_2[s]/(s^n): N^k = s^{kd} · u^k; u^k still unit.
  N^k = 0 iff kd ≥ n, i.e., k ≥ ⌈n/d⌉.  ∎

Application to SHA-256:
  Σ_0 (rotations 2,13,22):  d = 1 (13 covers bit 0), nilp = 32.
  Σ_1 (rotations 6,11,25):  d = 3 (bits 0,1 doubly covered, cancel).
                            nilp = ⌈32/3⌉ = 11.

The "anomaly" at Σ_1 is explained by the specific binary structure of (6,11,25):
  - Bit 0 covered by {11, 25}       → cancels
  - Bit 1 covered by {6, 11}        → cancels
  - Bit 2 ≡ 10 (binary): covered by {6, 11} (11 has bits 0,1,3; wait...)

  Rechecking coverage for i ∈ {1, 2, 3}:
    i=1 (bit 0):     r with (1 & r)==1 ⇒ bit 0 set ⇒ {11, 25}         → 2, cancels
    i=2 (bit 1):     r with (2 & r)==2 ⇒ bit 1 set ⇒ {6, 11}          → 2, cancels
    i=3 (bits 0,1):  r with (3 & r)==3 ⇒ bits 0,1 both ⇒ {11}         → 1, survives

So d = 3 for Σ_1.

(Corresponds to Session 23 observation: Σ_1 minimal polynomial has degree 11.)
""")


def main():
    print("=== Session 24: Structural explanation of Σ_1 min poly deg 11 ===")

    analyze("Σ_0", [2, 13, 22], 32)
    analyze("Σ_1", [6, 11, 25], 32)

    # σ's include SHR which is NOT of the form (1+s)^r, so theorem doesn't apply directly.
    # Just analyze the pure-rotation part for comparison.
    analyze("Pure rotations only — σ_0 rot part", [7, 18], 32)  # |R|=2 even → no constant
    # Add an extra copy of one rotation to make |R| odd for demo:
    analyze("σ_1 rot part trimmed", [17, 19], 32)  # even, skipped

    systematic_scan(n=32, max_r=31)

    theorem_statement()


if __name__ == "__main__":
    main()
