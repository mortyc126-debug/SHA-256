"""
DERIVE c = 0.30 in ε(r) = c/r from first principles.

ε = P(clause sign matches correct value) - 0.5

For random 3-SAT with solution x*:
- Bit i with x*ᵢ = 1
- Clause containing bit i with sign s

P(s = +1 | x* is solution, i in clause) = ?

Key: we condition on the instance being SATISFIABLE by x*.
This conditioning creates the bias.

Method: compute exactly for small cases, find the pattern.
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


# ============================================================
# ANALYTICAL APPROACH: One clause at a time
# ============================================================

def single_clause_bias():
    """
    Consider ONE clause with bit i and two other bits j, k.
    All signs random. x* is a solution.

    What is P(sign_i matches x*_i | clause is satisfied by x*)?

    Enumerate all possibilities.
    """
    print("=" * 70)
    print("Single clause analysis")
    print("=" * 70)

    # For one clause (i, j, k) with signs (si, sj, sk):
    # si, sj, sk each ∈ {+1, -1}
    # x*_i, x*_j, x*_k each ∈ {0, 1}
    # Clause satisfied if any literal true:
    #   (si=+1 and x*_i=1) or (si=-1 and x*_i=0) or
    #   (sj=+1 and x*_j=1) or (sj=-1 and x*_j=0) or
    #   (sk=+1 and x*_k=1) or (sk=-1 and x*_k=0)

    # P(sign_i matches x*_i | clause satisfied)
    # "matches" means: (si=+1 and x*_i=1) or (si=-1 and x*_i=0)
    # i.e., si = 2*x*_i - 1

    total_satisfied = 0
    match_and_satisfied = 0

    for xi in [0, 1]:
        for xj in [0, 1]:
            for xk in [0, 1]:
                for si in [+1, -1]:
                    for sj in [+1, -1]:
                        for sk in [+1, -1]:
                            # Is clause satisfied?
                            lit_i = (si == 1 and xi == 1) or (si == -1 and xi == 0)
                            lit_j = (sj == 1 and xj == 1) or (sj == -1 and xk == 0)
                            lit_k = (sk == 1 and xk == 1) or (sk == -1 and xk == 0)

                            # Wait, xk is used for both j and k — bug. Fix:
                            pass

    # Redo properly
    total_satisfied = 0
    match_and_satisfied = 0
    not_match_and_satisfied = 0

    for xi in [0, 1]:
        for xj in [0, 1]:
            for xk in [0, 1]:
                for si in [+1, -1]:
                    for sj in [+1, -1]:
                        for sk in [+1, -1]:
                            # Each literal satisfied?
                            li = (si == 1 and xi == 1) or (si == -1 and xi == 0)
                            lj = (sj == 1 and xj == 1) or (sj == -1 and xj == 0)
                            lk = (sk == 1 and xk == 1) or (sk == -1 and xk == 0)

                            satisfied = li or lj or lk

                            if satisfied:
                                total_satisfied += 1
                                # Does sign_i match x*_i?
                                si_matches = (si == (2 * xi - 1))
                                if si_matches:
                                    match_and_satisfied += 1
                                else:
                                    not_match_and_satisfied += 1

    p_match = match_and_satisfied / total_satisfied
    p_nomatch = not_match_and_satisfied / total_satisfied

    print(f"\n  Uniform over all (x*, signs):")
    print(f"    P(sign_i matches x*_i | satisfied) = {p_match:.6f}")
    print(f"    P(sign_i doesn't match | satisfied) = {p_nomatch:.6f}")
    print(f"    ε_uniform = {p_match - 0.5:.6f}")

    # But this is uniform over x*. In reality, x* is FIXED and signs are random.
    # For a GIVEN x*, P(clause satisfied | signs random) varies.
    # Let's compute for x* = (1,1,1):

    print(f"\n  For x* = (1,1,1):")
    total = 0; match = 0

    for si in [+1, -1]:
        for sj in [+1, -1]:
            for sk in [+1, -1]:
                li = (si == 1)  # xi=1
                lj = (sj == 1)  # xj=1
                lk = (sk == 1)  # xk=1
                satisfied = li or lj or lk
                if satisfied:
                    total += 1
                    if si == 1:  # matches xi=1
                        match += 1

    print(f"    P(si=+1 | satisfied, x*=(1,1,1)) = {match/total:.6f}")
    print(f"    ε = {match/total - 0.5:.6f}")

    # For x* = (1,0,1):
    print(f"\n  For x* = (1,0,1):")
    total = 0; match = 0

    for si in [+1, -1]:
        for sj in [+1, -1]:
            for sk in [+1, -1]:
                li = (si == 1)   # xi=1
                lj = (sj == -1)  # xj=0
                lk = (sk == 1)   # xk=1
                satisfied = li or lj or lk
                if satisfied:
                    total += 1
                    if si == 1:
                        match += 1

    print(f"    P(si=+1 | satisfied, x*=(1,0,1)) = {match/total:.6f}")
    print(f"    ε = {match/total - 0.5:.6f}")


def conditional_epsilon():
    """
    THE KEY CALCULATION:

    In random 3-SAT, clauses are generated RANDOMLY.
    Then we ask: given that x* is a SOLUTION, what is
    P(sign_i matches x*_i)?

    For a SINGLE clause containing bit i:
    - 3 variables chosen uniformly
    - 3 signs chosen uniformly from {+1,-1}
    - CONDITION: x* satisfies this clause

    P(si matches x*_i | x* satisfies clause)
    = P(si matches AND x* satisfies) / P(x* satisfies)
    """
    print("\n" + "=" * 70)
    print("CONDITIONAL ε: P(sign matches | clause satisfied by x*)")
    print("=" * 70)

    # P(clause satisfied by x*) for random signs
    # Each literal has P(true) = 1/2 (random sign, fixed x*)
    # P(at least one true) = 1 - P(all false) = 1 - (1/2)^3 = 7/8

    p_sat = 1 - (1/2)**3
    print(f"\n  P(random clause satisfied by x*) = {p_sat:.6f} = 7/8")

    # P(si matches AND clause satisfied)
    # If si matches: literal i is TRUE. Clause satisfied regardless.
    # P(si matches) = 1/2
    # P(clause satisfied | si matches) = 1 (literal i alone satisfies)
    # → P(si matches AND satisfied) = 1/2 × 1 = 1/2

    p_match_and_sat = 0.5 * 1.0
    print(f"  P(si matches AND satisfied) = {p_match_and_sat:.6f}")

    # P(si matches | satisfied) = P(match AND sat) / P(sat)
    p_match_given_sat = p_match_and_sat / p_sat
    print(f"  P(si matches | satisfied) = {p_match_given_sat:.6f}")

    epsilon_single = p_match_given_sat - 0.5
    print(f"  ε_single_clause = {epsilon_single:.6f}")
    print(f"                  = 1/(2 × 7/8) - 1/2")
    print(f"                  = 4/7 - 1/2")
    print(f"                  = 1/14")
    print(f"                  = {1/14:.6f}")

    # BUT: this is ε per CLAUSE. A bit with d clauses has d independent
    # biased estimates. The COMBINED ε should be different.
    #
    # Actually no — ε is the bias per APPEARANCE.
    # If bit i appears in d clauses, each with independent ε = 1/14 bias,
    # then the total positive count ~ Bin(d, 1/2 + 1/14).
    #
    # So ε(single clause) = 1/14 ≈ 0.0714
    # This should be INDEPENDENT of r!
    # But we measured ε(r) = 0.30/r, which DEPENDS on r.

    print(f"\n  WAIT: ε = 1/14 ≈ 0.0714, independent of r?")
    print(f"  But we measured ε(r) = 0.30/r, which varies with r.")
    print(f"  At r=4.27: 0.30/4.27 = {0.30/4.27:.4f}")
    print(f"  And 1/14 = {1/14:.4f}")
    print(f"  These are CLOSE! {0.30/4.27:.4f} vs {1/14:.4f}")
    print(f"  Difference: {abs(0.30/4.27 - 1/14):.4f}")

    # Let me check: is ε actually CONSTANT, and the r-dependence was an artifact?
    print(f"\n  Predictions at different r:")
    print(f"  If ε = 1/14 (constant):")
    for r in [2.0, 3.0, 4.0, 4.27, 5.0]:
        d = int(round(3 * r))
        # A(d, 1/14)
        pe = 0.5 + 1/14
        p_correct = 0
        for k in range(d+1):
            prob_k = math.exp(
                math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
                k*math.log(pe) + (d-k)*math.log(1-pe)
            )
            if k > d/2: p_correct += prob_k
            elif k == d/2 and d % 2 == 0: p_correct += prob_k * 0.5

        print(f"    r={r:.2f}, d={d}: predicted accuracy = {p_correct*100:.1f}%")


def verify_constant_epsilon():
    """Check: is ε actually 1/14 regardless of r?"""
    print("\n" + "=" * 70)
    print("VERIFICATION: Is ε constant at 1/14 ≈ 0.0714?")
    print("=" * 70)

    print(f"\n  {'ratio':>6} | {'ε measured':>10} | {'1/14':>8} | {'diff':>8}")
    print("  " + "-" * 40)

    for ratio_10 in range(15, 55, 5):
        ratio = ratio_10 / 10.0
        epsilons = []

        for seed in range(200):
            clauses = random_3sat(12, int(ratio*12), seed=seed+80000)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(12)]
            for var in range(12):
                actual = 1 if prob_1[var] > 0.5 else 0
                pos = sum(1 for cl in clauses for v, s in cl if v==var and s==1)
                neg = sum(1 for cl in clauses for v, s in cl if v==var and s==-1)
                d = pos + neg
                if d == 0: continue
                if actual == 1:
                    epsilons.append(pos/d - 0.5)
                else:
                    epsilons.append(neg/d - 0.5)

        measured = sum(epsilons)/len(epsilons)
        diff = measured - 1/14
        print(f"  {ratio:>6.1f} | {measured:>+10.4f} | {1/14:>8.4f} | {diff:>+8.4f}")


# ============================================================
# For k-SAT: does ε = 1/(2^k - 2)?
# ============================================================

def ksat_epsilon():
    """
    For k-SAT:
    P(clause satisfied) = 1 - (1/2)^k = (2^k - 1) / 2^k
    P(si matches AND satisfied) = 1/2
    P(si matches | satisfied) = (1/2) / ((2^k-1)/2^k) = 2^(k-1) / (2^k - 1)
    ε = 2^(k-1)/(2^k-1) - 1/2 = (2^(k-1) - (2^k-1)/2) / (2^k-1)
      = (2^k - 2^k + 1) / (2(2^k-1))
      = 1 / (2(2^k - 1))

    For k=3: ε = 1/(2×7) = 1/14 ✓
    For k=2: ε = 1/(2×3) = 1/6 ≈ 0.167
    For k=4: ε = 1/(2×15) = 1/30 ≈ 0.033
    """
    print("\n" + "=" * 70)
    print("GENERAL k-SAT: ε = 1 / (2(2^k - 1))")
    print("=" * 70)

    for k in [2, 3, 4, 5]:
        eps = 1 / (2 * (2**k - 1))
        print(f"  k={k}: ε = 1/{2*(2**k-1)} = {eps:.6f}")


if __name__ == "__main__":
    single_clause_bias()
    conditional_epsilon()
    ksat_epsilon()
    verify_constant_epsilon()
