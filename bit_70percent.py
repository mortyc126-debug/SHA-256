"""
The 70% Constant — Can we derive it analytically?

Observation: at the SAT threshold (ratio≈4.27), tension σ predicts
the correct bit value ~70% of the time, regardless of n.

Can we derive this from the statistics of random 3-SAT?
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


def bit_tension(clauses, n, var, fixed=None):
    if fixed is None:
        fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        already_sat = False
        remaining = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
            else:
                remaining.append((v, s))
        if already_sat:
            continue
        for v, s in remaining:
            if v == var:
                w = 1.0 / max(1, len(remaining))
                if s == 1:
                    p1 += w
                else:
                    p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# ANALYTICAL MODEL
# ============================================================

def analytical_prediction_rate(ratio):
    """
    Attempt to derive the 70% constant.

    Model:
    - Variable x appears in d ≈ 3*ratio clauses (Poisson, mean 3r)
    - In each clause, x appears positive with prob 0.5
    - So pos ~ Binomial(d, 0.5), neg = d - pos
    - Tension σ = (pos - neg)/d = (2*pos - d)/d
    - The "correct" answer for x depends on the structure of solutions,
      which is correlated with (but not identical to) the sign distribution.

    Key insight: IF solutions are random, then the correct value of x
    is more likely to be 1 when x appears more often as positive literal.
    This is because positive appearances mean "setting x=1 satisfies this clause."

    The prediction is correct when sign(σ) = sign(correct_value - 0.5).
    This happens when the majority polarity matches the solution.

    For a variable with d appearances, pos ~ Bin(d, p_correct) where
    p_correct is the probability it appears positive given it should be 1.

    In random 3-SAT, signs are random, so p_correct = 0.5 + ε for some small ε
    that depends on the solution structure. The question: what is ε?

    Simple model: ε = 0 (signs truly random), then prediction = 50%.
    But we observe 70%, so ε > 0. The correlation between sign and
    correct value is what gives the signal.

    Let's measure ε directly.
    """
    pass  # See empirical measurement below


def measure_sign_solution_correlation():
    """
    For each bit: what fraction of its positive appearances
    correspond to "should be 1" vs "should be 0"?

    If signs are random: fraction = 0.5
    If correlated: fraction > 0.5
    """
    print("=" * 70)
    print("Measuring sign-solution correlation ε")
    print("=" * 70)

    for ratio in [2.0, 3.0, 4.0, 4.27, 5.0]:
        correlations = []

        for seed in range(200):
            n = 12
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

            for var in range(n):
                should_be_1 = prob_1[var] > 0.5

                pos = 0
                neg = 0
                for clause in clauses:
                    for v, s in clause:
                        if v == var:
                            if s == 1:
                                pos += 1
                            else:
                                neg += 1

                total = pos + neg
                if total == 0:
                    continue

                # Fraction of appearances that "agree" with correct value
                if should_be_1:
                    agree_frac = pos / total  # positive = agrees with being 1
                else:
                    agree_frac = neg / total  # negative = agrees with being 0

                correlations.append(agree_frac)

        if correlations:
            mean = sum(correlations) / len(correlations)
            epsilon = mean - 0.5
            # From epsilon, predict accuracy
            # If each appearance is a "vote" with bias 0.5+ε,
            # and we have d votes, majority is correct with probability:
            # P(correct) = P(Bin(d, 0.5+ε) > d/2)
            d = int(3 * ratio)
            p_correct = 0
            for k in range(d + 1):
                if k > d / 2:
                    prob_k = math.exp(
                        math.lgamma(d + 1) - math.lgamma(k + 1) -
                        math.lgamma(d - k + 1) +
                        k * math.log(0.5 + epsilon) +
                        (d - k) * math.log(0.5 - epsilon)
                    )
                    p_correct += prob_k
                elif k == d / 2 and d % 2 == 0:
                    # Tie — count as 50/50
                    prob_k = math.exp(
                        math.lgamma(d + 1) - math.lgamma(k + 1) -
                        math.lgamma(d - k + 1) +
                        k * math.log(0.5 + epsilon) +
                        (d - k) * math.log(0.5 - epsilon)
                    )
                    p_correct += prob_k * 0.5

            print(f"  ratio={ratio:.2f}: ε = {epsilon:+.4f}, "
                  f"d={d}, predicted accuracy = {p_correct*100:.1f}%")


def measure_actual_vs_predicted():
    """
    Compare the analytical prediction with actual measurement.
    """
    print("\n" + "=" * 70)
    print("Predicted vs actual accuracy at each ratio")
    print("=" * 70)

    print(f"\n{'ratio':>6} | {'ε':>8} | {'d':>4} | {'predicted':>9} | "
          f"{'actual':>8} | {'error':>7}")
    print("-" * 55)

    for ratio_10 in range(15, 55, 5):
        ratio = ratio_10 / 10.0
        n = 12

        # Measure ε
        correlations = []
        correct_count = 0
        total_count = 0

        for seed in range(200):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

            for var in range(n):
                should_be_1 = prob_1[var] > 0.5

                pos = 0
                neg = 0
                for clause in clauses:
                    for v, s in clause:
                        if v == var:
                            if s == 1:
                                pos += 1
                            else:
                                neg += 1

                total = pos + neg
                if total == 0:
                    continue

                if should_be_1:
                    correlations.append(pos / total)
                else:
                    correlations.append(neg / total)

                # Actual prediction
                sigma = bit_tension(clauses, n, var)
                predicted = 1 if sigma >= 0 else 0
                actual = 1 if prob_1[var] > 0.5 else 0
                if predicted == actual:
                    correct_count += 1
                total_count += 1

        if not correlations:
            continue

        epsilon = sum(correlations) / len(correlations) - 0.5
        d = int(3 * ratio)
        actual_acc = correct_count / total_count if total_count > 0 else 0

        # Predict from ε and d
        p_correct = 0
        for k in range(d + 1):
            p_ε = 0.5 + epsilon
            prob_k = math.exp(
                math.lgamma(d + 1) - math.lgamma(k + 1) -
                math.lgamma(d - k + 1) +
                k * math.log(max(p_ε, 1e-10)) +
                (d - k) * math.log(max(1 - p_ε, 1e-10))
            )
            if k > d / 2:
                p_correct += prob_k
            elif k == d / 2 and d % 2 == 0:
                p_correct += prob_k * 0.5

        error = abs(p_correct - actual_acc) * 100

        print(f"{ratio:>6.1f} | {epsilon:>+8.4f} | {d:>4} | "
              f"{p_correct*100:>8.1f}% | {actual_acc*100:>7.1f}% | "
              f"{error:>6.1f}%")


def deeper_epsilon():
    """
    WHY is ε ≈ 0.05-0.08?

    In random 3-SAT, each clause is (l₁ ∨ l₂ ∨ l₃) with random signs.
    A clause constrains: at least one literal must be true.

    If x should be 1 in the solution:
    - When x appears positive (+x) in a clause: clause is automatically
      satisfied by x, regardless of other literals.
    - When x appears negative (¬x) in a clause: x does NOT help satisfy
      this clause, putting more pressure on other variables.

    The bias ε comes from the fact that solutions favor assignments
    where variables satisfy AS MANY CLAUSES AS POSSIBLE.
    Variables that appear more often positively "want" to be 1
    because being 1 satisfies more clauses.

    So ε is related to the fraction of clauses that the variable
    satisfies by being in its correct state.
    """
    print("\n" + "=" * 70)
    print("WHY is ε what it is?")
    print("Clause satisfaction vs sign correlation")
    print("=" * 70)

    for ratio in [2.0, 4.27]:
        n = 12
        total_var_data = []

        for seed in range(200):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

            for var in range(n):
                correct_val = 1 if prob_1[var] > 0.5 else 0

                # How many clauses does this var satisfy when correct?
                clauses_with_var = 0
                clauses_satisfied = 0
                for clause in clauses:
                    for v, s in clause:
                        if v == var:
                            clauses_with_var += 1
                            if (s == 1 and correct_val == 1) or (s == -1 and correct_val == 0):
                                clauses_satisfied += 1

                if clauses_with_var > 0:
                    sat_fraction = clauses_satisfied / clauses_with_var
                    total_var_data.append({
                        'sat_fraction': sat_fraction,
                        'clauses': clauses_with_var,
                    })

        mean_sf = sum(d['sat_fraction'] for d in total_var_data) / len(total_var_data)
        mean_d = sum(d['clauses'] for d in total_var_data) / len(total_var_data)

        print(f"\n  ratio={ratio}: avg sat_fraction = {mean_sf:.4f} "
              f"(ε = {mean_sf - 0.5:+.4f}), avg degree = {mean_d:.1f}")
        print(f"  Interpretation: a correct bit satisfies "
              f"{mean_sf*100:.1f}% of its clauses vs 50% if random")


if __name__ == "__main__":
    random.seed(42)
    measure_sign_solution_correlation()
    measure_actual_vs_predicted()
    deeper_epsilon()
