"""
PREDICTIONS FROM BIT MECHANICS — Things the theory says but we haven't tested.

If confirmed → theory is real.
If falsified → theory needs fixing.

PREDICTION 1: 2-SAT tension accuracy should be ~44% (WORSE than random)
  ε = 1/6, d = 2r, at threshold r=1, d=2
  A = P(Bin(2, 2/3) > 1) = (2/3)² = 4/9 ≈ 44%
  But 2-SAT is in P! So tension is USELESS for 2-SAT.
  (Confirming that tension ≠ solvability)

PREDICTION 2: For large d, accuracy → Φ(2ε√d) (normal approximation)
  At threshold: ε=1/14, d=13 → Φ(2/14 × √13) ≈ Φ(0.515) ≈ 69.7%
  For d=100: Φ(2/14 × 10) = Φ(1.43) ≈ 92.4%
  → At VERY high degree, tension becomes near-perfect!

PREDICTION 3: Error correlation lift = 1 + ε²d_shared / (ε²d_total)
  Should give ~1.20 for d_shared=3, d_total=13

PREDICTION 4: Temperature at threshold
  T = 1 - E[|σ|] where σ = (2Bin(13,4/7)-13)/13
  Should be exactly computable.

PREDICTION 5: For 4-SAT at threshold (r≈9.93)
  ε = 1/30, d ≈ 40, A ≈ Φ(2/30 × √40) ≈ Φ(0.42) ≈ 66%
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            if (sign == 1 and assignment[var] == 1) or \
               (sign == -1 and assignment[var] == 0):
                sat += 1
                break
    return sat


def bit_tension(clauses, n, var, fixed=None):
    if fixed is None: fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                    sat = True; break
            else: rem.append((v,s))
        if sat: continue
        for v, s in rem:
            if v == var:
                w = 1.0/max(1,len(rem))
                if s==1: p1 += w
                else: p0 += w
    total = p1+p0
    return (p1-p0)/total if total > 0 else 0.0


def random_ksat(n, m, k, seed=None):
    """Random k-SAT instance."""
    if seed is not None: random.seed(seed)
    clauses = []
    for _ in range(m):
        vs = random.sample(range(n), k)
        signs = [random.choice([1,-1]) for _ in range(k)]
        clauses.append(list(zip(vs, signs)))
    return clauses


def accuracy_exact(d, p):
    """P(Bin(d, p) > d/2)"""
    a = 0
    for k in range(d+1):
        prob = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(max(p,1e-15)) + (d-k)*math.log(max(1-p,1e-15))
        )
        if k > d/2: a += prob
        elif k == d/2 and d % 2 == 0: a += prob * 0.5
    return a


def normal_cdf(x):
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ============================================================
# PREDICTION 1: 2-SAT tension accuracy
# ============================================================

def test_prediction_1():
    print("=" * 70)
    print("PREDICTION 1: 2-SAT tension accuracy = 44%?")
    print("  ε = 1/6, d = 2, A = P(Bin(2, 2/3) > 1) = 4/9 ≈ 44.4%")
    print("=" * 70)

    n = 20
    ratio = 1.0  # 2-SAT threshold
    predicted = accuracy_exact(2, 2/3)

    correct = 0; total = 0
    for seed in range(300):
        clauses = random_ksat(n, int(ratio*n), 2, seed=seed)
        solutions = find_solutions(clauses, n) if n <= 20 else None
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            actual = 1 if prob_1[var] > 0.5 else 0
            pred = 1 if sigma >= 0 else 0
            if pred == actual: correct += 1
            total += 1

    measured = correct/total if total > 0 else 0
    print(f"\n  Predicted: {predicted*100:.1f}%")
    print(f"  Measured:  {measured*100:.1f}%")
    print(f"  Match: {'YES' if abs(predicted - measured) < 0.05 else 'NO'}")

    # Also test at higher ratio
    for r in [0.5, 1.0, 2.0, 3.0]:
        correct = 0; total = 0
        for seed in range(200):
            clauses = random_ksat(n, int(r*n), 2, seed=seed+1000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                actual = 1 if prob_1[var] > 0.5 else 0
                if (1 if sigma >= 0 else 0) == actual: correct += 1
                total += 1

        measured = correct/total if total > 0 else 0
        d = int(round(2*r))
        pred = accuracy_exact(max(d,1), 2/3)
        print(f"  r={r}: d={d}, predicted={pred*100:.1f}%, measured={measured*100:.1f}%")


# ============================================================
# PREDICTION 2: Large-d asymptotic accuracy
# ============================================================

def test_prediction_2():
    print("\n" + "=" * 70)
    print("PREDICTION 2: Asymptotic accuracy Φ(2ε√d)")
    print("  3-SAT: ε=1/14")
    print("=" * 70)

    print(f"\n  {'d':>4} | {'exact':>8} | {'Φ(2ε√d)':>8} | {'diff':>7}")
    print("  " + "-" * 35)

    eps = 1/14
    for d in [3, 5, 8, 13, 20, 30, 50, 100, 200]:
        exact = accuracy_exact(d, 0.5 + eps)
        approx = normal_cdf(2 * eps * math.sqrt(d))
        diff = abs(exact - approx) * 100
        print(f"  {d:>4} | {exact*100:>7.2f}% | {approx*100:>7.2f}% | {diff:>6.2f}%")


# ============================================================
# PREDICTION 3: Error correlation from theory
# ============================================================

def test_prediction_3():
    print("\n" + "=" * 70)
    print("PREDICTION 3: Error correlation lift from ε")
    print("=" * 70)

    # Derive lift:
    # Two bits i,j sharing d_s clauses out of d_i, d_j total.
    # If i is wrong: its d_s shared clause-votes pointed wrong direction.
    # This biases j's votes by d_s wrong votes out of d_j total.
    # j's effective ε → ε - 2ε × d_s/d_j (roughly)
    # P(j wrong | i wrong) ≈ P(Bin(d_j, 0.5 + ε - 2ε×d_s/d_j) < d_j/2)
    # vs P(j wrong) = P(Bin(d_j, 0.5 + ε) < d_j/2) = 1 - A(d_j, ε)

    d = 13; eps = 1/14
    p_wrong = 1 - accuracy_exact(d, 0.5 + eps)

    for d_shared in [1, 2, 3, 4, 5]:
        # Effective ε for j when i is wrong:
        # Shared clauses flip from correct to wrong ≈ removes 2ε×d_s bias
        eps_eff = eps - 2 * eps * d_shared / d
        eps_eff = max(eps_eff, -0.49)

        p_wrong_given = 1 - accuracy_exact(d, 0.5 + eps_eff)
        lift = p_wrong_given / p_wrong if p_wrong > 0 else 1

        print(f"  d_shared={d_shared}: ε_eff={eps_eff:+.4f}, "
              f"P(wrong|i wrong)={p_wrong_given:.4f}, "
              f"P(wrong)={p_wrong:.4f}, lift={lift:.3f}")

    print(f"\n  Measured lift: 1.20 (for any d_shared ≥ 1)")


# ============================================================
# PREDICTION 4: Exact temperature
# ============================================================

def test_prediction_4():
    print("\n" + "=" * 70)
    print("PREDICTION 4: Exact temperature at threshold")
    print("=" * 70)

    d = 13; eps = 1/14
    p = 0.5 + eps

    # T = 1 - E[|2X/d - 1|] where X ~ Bin(d, p)
    e_abs_sigma = 0
    for k in range(d+1):
        prob = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(p) + (d-k)*math.log(1-p)
        )
        sigma = abs(2*k/d - 1)
        e_abs_sigma += prob * sigma

    T_predicted = 1 - e_abs_sigma

    # Measure
    T_measured_vals = []
    for seed in range(200):
        clauses = random_3sat(12, int(4.27*12), seed=seed+99000)
        for var in range(12):
            sigma = bit_tension(clauses, 12, var)
            T_measured_vals.append(1 - abs(sigma))

    T_measured = sum(T_measured_vals) / len(T_measured_vals)

    print(f"\n  T_predicted = 1 - E[|σ|] = {T_predicted:.4f}")
    print(f"  T_measured  = {T_measured:.4f}")
    print(f"  Error: {abs(T_predicted - T_measured)*100:.2f}%")


# ============================================================
# PREDICTION 5: 4-SAT accuracy
# ============================================================

def test_prediction_5():
    print("\n" + "=" * 70)
    print("PREDICTION 5: 4-SAT tension accuracy")
    print("  ε = 1/30, threshold r ≈ 9.93")
    print("=" * 70)

    # 4-SAT threshold is approximately r = 9.93
    # d = 4r ≈ 40
    eps_4sat = 1 / (2 * (2**4 - 1))  # 1/30
    r_4sat = 9.93
    d_4sat = int(round(4 * r_4sat))

    predicted = accuracy_exact(d_4sat, 0.5 + eps_4sat)
    approx = normal_cdf(2 * eps_4sat * math.sqrt(d_4sat))

    print(f"\n  ε = 1/30 = {eps_4sat:.6f}")
    print(f"  d = {d_4sat}")
    print(f"  A(exact) = {predicted*100:.2f}%")
    print(f"  A(normal approx) = {approx*100:.2f}%")

    # Test empirically (use smaller r since threshold for 4-SAT is hard)
    n = 15
    for r in [5.0, 7.0, 9.0]:
        correct = 0; total = 0
        for seed in range(200):
            clauses = random_ksat(n, int(r*n), 4, seed=seed+2000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                actual = 1 if prob_1[var] > 0.5 else 0
                if (1 if sigma >= 0 else 0) == actual: correct += 1
                total += 1

        if total > 0:
            measured = correct/total
            d = int(round(4*r))
            pred = accuracy_exact(d, 0.5 + eps_4sat)
            print(f"  r={r}: d={d}, predicted={pred*100:.1f}%, "
                  f"measured={measured*100:.1f}%")


# ============================================================
# BONUS: Universal accuracy formula for k-SAT
# ============================================================

def universal_formula():
    print("\n" + "=" * 70)
    print("UNIVERSAL: Tension accuracy for any k-SAT at any ratio")
    print("  A(k, r) = P(Bin(kr, 2^(k-1)/(2^k-1)) > kr/2)")
    print("=" * 70)

    print(f"\n  {'k':>3} | {'r':>6} | {'d':>4} | {'ε':>8} | {'p':>8} | {'A':>8}")
    print("  " + "-" * 50)

    for k in [2, 3, 4, 5]:
        eps = 1 / (2 * (2**k - 1))
        p = 0.5 + eps

        # Use approximate thresholds
        thresholds = {2: 1.0, 3: 4.27, 4: 9.93, 5: 21.1}
        r = thresholds.get(k, 4.0)
        d = int(round(k * r))

        a = accuracy_exact(d, p)
        print(f"  {k:>3} | {r:>6.2f} | {d:>4} | {eps:>8.5f} | {p:>8.5f} | {a*100:>7.2f}%")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    test_prediction_1()
    test_prediction_2()
    test_prediction_3()
    test_prediction_4()
    test_prediction_5()
    universal_formula()
