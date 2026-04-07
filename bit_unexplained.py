"""
Two unexplained phenomena:

1. The 2.3% bonus: formula predicts 68.8%, reality gives 71.0%
   Where does the extra 2.2% come from?

2. The amplification delay: first 3 fixes give +1.2%, then sudden jump
   What "unlocks" at fix #4?
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
# MYSTERY 1: The 2.3% bonus
# ============================================================

def investigate_bonus():
    """
    The formula assumes:
    - Each bit appears in d clauses with INDEPENDENT random signs
    - Signs are Binomial(d, 0.5 + ε)

    But in reality:
    - Clauses are NOT independent (they share variables)
    - Signs within a clause are correlated (clause must be satisfiable)
    - The bit's degree d is not exactly 3r (it's Poisson-distributed)

    Test each factor.
    """
    print("=" * 70)
    print("MYSTERY 1: Where does the 2.3% bonus come from?")
    print("=" * 70)

    random.seed(42)
    n = 12
    ratio = 4.27

    # Factor A: Variable degree distribution
    print("\n  Factor A: Degree distribution (Poisson vs fixed)")
    degree_acc = {}  # accuracy by degree

    for seed in range(300):
        clauses = random_3sat(n, int(ratio * n), seed=seed + 7000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            actual = 1 if prob_1[var] > 0.5 else 0
            pred = 1 if sigma >= 0 else 0

            degree = sum(1 for cl in clauses if any(v == var for v, s in cl))
            if degree not in degree_acc:
                degree_acc[degree] = [0, 0]
            degree_acc[degree][1] += 1
            if pred == actual:
                degree_acc[degree][0] += 1

    print(f"  {'degree':>8} | {'accuracy':>8} | {'n':>6} | {'predicted':>9}")
    print("  " + "-" * 45)
    for d in sorted(degree_acc.keys()):
        if degree_acc[d][1] < 10:
            continue
        acc = degree_acc[d][0] / degree_acc[d][1]
        # Analytical prediction for this degree
        eps = 0.072
        p_correct = 0
        for k in range(d + 1):
            pe = 0.5 + eps
            prob_k = math.exp(
                math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
                k*math.log(max(pe, 1e-10)) + (d-k)*math.log(max(1-pe, 1e-10))
            )
            if k > d/2:
                p_correct += prob_k
            elif k == d/2 and d % 2 == 0:
                p_correct += prob_k * 0.5

        print(f"  {d:>8} | {acc*100:>7.1f}% | {degree_acc[d][1]:>6} | {p_correct*100:>8.1f}%")

    # Factor B: Does ε vary by degree?
    print("\n  Factor B: Does ε depend on degree?")
    eps_by_degree = {}

    for seed in range(300):
        clauses = random_3sat(n, int(ratio * n), seed=seed + 7000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        for var in range(n):
            actual = 1 if prob_1[var] > 0.5 else 0
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            d = pos + neg
            if d == 0:
                continue
            if actual == 1:
                eps = pos/d - 0.5
            else:
                eps = neg/d - 0.5

            if d not in eps_by_degree:
                eps_by_degree[d] = []
            eps_by_degree[d].append(eps)

    print(f"  {'degree':>8} | {'ε':>8} | {'n':>6}")
    print("  " + "-" * 30)
    for d in sorted(eps_by_degree.keys()):
        if len(eps_by_degree[d]) < 10:
            continue
        avg_eps = sum(eps_by_degree[d]) / len(eps_by_degree[d])
        print(f"  {d:>8} | {avg_eps:>+8.4f} | {len(eps_by_degree[d]):>6}")

    # Factor C: Clause correlation
    print("\n  Factor C: Are clause signs correlated?")
    # For each bit, check: is sign in clause i correlated with sign in clause j?
    correlations = []
    for seed in range(200):
        clauses = random_3sat(n, int(ratio * n), seed=seed + 7000)
        for var in range(n):
            signs = []
            for cl in clauses:
                for v, s in cl:
                    if v == var:
                        signs.append(s)
            if len(signs) < 4:
                continue
            # Auto-correlation: does knowing sign[i] predict sign[i+1]?
            matches = sum(1 for i in range(len(signs)-1) if signs[i] == signs[i+1])
            correlations.append(matches / (len(signs)-1))

    avg_corr = sum(correlations) / len(correlations)
    print(f"  Adjacent clause sign correlation: {avg_corr:.4f} (0.5 = independent)")


# ============================================================
# MYSTERY 2: Amplification delay
# ============================================================

def investigate_delay():
    """
    First 3 fixes: +1.2% total
    Fixes 4-6: +8.6% total

    What changes at fix #4?
    Hypotheses:
    A) The first 3 fixes happen to be on "unimportant" bits
    B) There's a percolation threshold — need critical mass of fixed bits
    C) Unit propagation kicks in after enough bits are fixed
    D) The system undergoes a phase transition in remaining clause structure
    """
    print("\n" + "=" * 70)
    print("MYSTERY 2: Why does amplification delay until fix #4?")
    print("=" * 70)

    random.seed(42)
    n = 12

    # Track what happens at EACH step
    for seed_range, label in [
        (range(200), "Average over 200 instances"),
    ]:
        step_data = {i: {
            'accuracy': [], 'n_unit_prop': [], 'n_critical_clauses': [],
            'avg_tension': [], 'max_tension': [], 'pressure': [],
        } for i in range(n+1)}

        for seed in seed_range:
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 5000)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            fixed = {}
            order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed:
                    break

                # Accuracy
                correct = sum(1 for v in unfixed
                             if (1 if bit_tension(clauses, n, v, fixed) >= 0 else 0) == correct_val[v])
                acc = correct / len(unfixed)

                # Unit propagation count
                up_count = 0
                test_fixed = dict(fixed)
                while True:
                    new_forced = {}
                    for clause in clauses:
                        satisfied = False
                        free = []
                        for v, s in clause:
                            if v in test_fixed:
                                if (s==1 and test_fixed[v]==1) or (s==-1 and test_fixed[v]==0):
                                    satisfied = True; break
                            else:
                                free.append((v, s))
                        if not satisfied and len(free) == 1:
                            v, s = free[0]
                            val = 1 if s == 1 else 0
                            if v not in test_fixed and v not in new_forced:
                                new_forced[v] = val
                    if not new_forced:
                        break
                    test_fixed.update(new_forced)
                    up_count += len(new_forced)

                # Critical clauses (only 1 free literal)
                critical = 0
                active = 0
                for clause in clauses:
                    satisfied = False
                    free_count = 0
                    for v, s in clause:
                        if v in fixed:
                            if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                satisfied = True; break
                        else:
                            free_count += 1
                    if not satisfied:
                        active += 1
                        if free_count == 1:
                            critical += 1

                pressure = critical / active if active > 0 else 0

                # Tensions of unfixed
                tensions_unfixed = [abs(bit_tension(clauses, n, v, fixed)) for v in unfixed]

                step_data[step]['accuracy'].append(acc)
                step_data[step]['n_unit_prop'].append(up_count)
                step_data[step]['n_critical_clauses'].append(critical)
                step_data[step]['pressure'].append(pressure)
                step_data[step]['avg_tension'].append(
                    sum(tensions_unfixed)/len(tensions_unfixed))
                step_data[step]['max_tension'].append(
                    max(tensions_unfixed) if tensions_unfixed else 0)

                # Fix next bit correctly
                if step < len(order):
                    fixed[order[step]] = correct_val[order[step]]

        print(f"\n  {label}:")
        print(f"  {'step':>4} | {'acc':>7} | {'UP':>4} | {'crit':>5} | "
              f"{'press':>6} | {'avg|σ|':>7} | {'max|σ|':>7} | observation")
        print("  " + "-" * 75)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0

        prev_acc = 0
        for step in range(n):
            d = step_data[step]
            if not d['accuracy']:
                break
            acc = mean(d['accuracy'])
            up = mean(d['n_unit_prop'])
            crit = mean(d['n_critical_clauses'])
            press = mean(d['pressure'])
            avg_t = mean(d['avg_tension'])
            max_t = mean(d['max_tension'])

            delta = acc - prev_acc
            obs = ""
            if up > 0.5:
                obs += "UP kicks in! "
            if delta > 0.02:
                obs += f"JUMP +{delta*100:.1f}% "
            if press > 0.05:
                obs += f"pressure rising "

            print(f"  {step:>4} | {acc*100:>6.1f}% | {up:>4.1f} | {crit:>5.1f} | "
                  f"{press:>6.3f} | {avg_t:>7.3f} | {max_t:>7.3f} | {obs}")
            prev_acc = acc


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    investigate_bonus()
    investigate_delay()
