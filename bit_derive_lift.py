"""
DERIVING LIFT = 1.20: The second-order effect.

We proved: with independent signs, lift = 1.00.
Real SAT has lift = 1.20. The difference = sign correlation from satisfiability.

The satisfiability constraint creates correlations:
  If clause (i,j,k) must be satisfied by x*:
  → at least one literal must be true
  → signs are NOT independent given x*

But wait: for a FIXED x*, signs ARE independent (random ±1).
The correlation appears when we consider MULTIPLE solutions.

KEY INSIGHT: ε = 1/14 was computed for a SINGLE fixed solution x*.
But when measuring "correct value" we use the MAJORITY across ALL solutions.
Different solutions may disagree → the "correct value" is a CONSENSUS.

The lift comes from: two bits sharing a clause are constrained
to have CORRELATED correct values across the solution space.
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


# ============================================================
# TEST: Is the correlation between SOLUTION VALUES the source?
# ============================================================

def solution_value_correlation():
    """
    For bits i,j sharing a clause:
    Is P(x*_i = x*_j) ≠ 0.5 across solutions?

    A clause (i,j,k) with signs (si,sj,sk) constrains:
    (si=+1→x_i=1 or si=-1→x_i=0) OR same for j OR same for k.

    This creates CORRELATION between solution values.
    """
    print("=" * 70)
    print("SOURCE OF LIFT: Solution value correlations")
    print("=" * 70)

    random.seed(42)
    n = 12

    # For each pair: correlation of values across solutions
    # Separated by: sharing clauses or not
    shared_corrs = []
    unshared_corrs = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 3:
            continue

        # Shared clause pairs
        shared = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    shared.add((min(vs[a],vs[b]), max(vs[a],vs[b])))

        # Correlation of values across solutions
        for i in range(n):
            vals_i = [s[i] for s in solutions]
            mean_i = sum(vals_i) / len(vals_i)
            std_i = math.sqrt(sum((v-mean_i)**2 for v in vals_i)/len(vals_i))

            for j in range(i+1, n):
                vals_j = [s[j] for s in solutions]
                mean_j = sum(vals_j) / len(vals_j)
                std_j = math.sqrt(sum((v-mean_j)**2 for v in vals_j)/len(vals_j))

                if std_i < 0.01 or std_j < 0.01:
                    continue

                cov = sum((vals_i[k]-mean_i)*(vals_j[k]-mean_j)
                         for k in range(len(solutions)))/len(solutions)
                corr = cov / (std_i * std_j)

                if (i,j) in shared:
                    shared_corrs.append(corr)
                else:
                    unshared_corrs.append(corr)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correlation of bit values across solutions:")
    print(f"    Sharing clauses:     avg corr = {mean(shared_corrs):+.4f} (n={len(shared_corrs)})")
    print(f"    Not sharing clauses: avg corr = {mean(unshared_corrs):+.4f} (n={len(unshared_corrs)})")
    print(f"    Difference: {mean(shared_corrs) - mean(unshared_corrs):+.4f}")


# ============================================================
# THE MECHANISM: How clause sharing creates error correlation
# ============================================================

def mechanism_analysis():
    """
    Step by step:
    1. Bits i,j share a clause → their SOLUTION VALUES are correlated
    2. Their solution values being correlated → their MAJORITY values correlated
    3. Majority values correlated → their CORRECTNESS correlated
    4. Correctness correlated = LIFT

    The lift should be a function of the solution-value correlation.
    """
    print("\n" + "=" * 70)
    print("MECHANISM: From solution correlation to error lift")
    print("=" * 70)

    random.seed(42)
    n = 12

    # Bin by solution-value correlation, measure error lift in each bin
    data_by_corr = {}

    for seed in range(300):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 3:
            continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Tension predictions
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        is_wrong = {v: (1 if tensions[v] >= 0 else 0) != correct_val[v] for v in range(n)}

        for i in range(n):
            vals_i = [s[i] for s in solutions]
            mean_i = sum(vals_i)/len(vals_i)
            std_i = math.sqrt(sum((v-mean_i)**2 for v in vals_i)/len(vals_i))

            for j in range(i+1, n):
                vals_j = [s[j] for s in solutions]
                mean_j = sum(vals_j)/len(vals_j)
                std_j = math.sqrt(sum((v-mean_j)**2 for v in vals_j)/len(vals_j))

                if std_i < 0.01 or std_j < 0.01:
                    continue

                cov = sum((vals_i[k]-mean_i)*(vals_j[k]-mean_j)
                         for k in range(len(solutions)))/len(solutions)
                corr = cov/(std_i*std_j)

                # Bin correlation
                corr_bin = round(corr * 5) / 5  # round to nearest 0.2
                if corr_bin not in data_by_corr:
                    data_by_corr[corr_bin] = {'both_wrong': 0, 'i_wrong': 0,
                                               'j_wrong': 0, 'total': 0}
                data_by_corr[corr_bin]['total'] += 1
                if is_wrong[i]: data_by_corr[corr_bin]['i_wrong'] += 1
                if is_wrong[j]: data_by_corr[corr_bin]['j_wrong'] += 1
                if is_wrong[i] and is_wrong[j]: data_by_corr[corr_bin]['both_wrong'] += 1

    print(f"\n  {'sol_corr':>8} | {'lift':>7} | {'n':>6} | pattern")
    print("  " + "-" * 45)

    lifts_by_corr = []
    for corr_bin in sorted(data_by_corr.keys()):
        d = data_by_corr[corr_bin]
        if d['total'] < 20: continue
        p_i = d['i_wrong'] / d['total']
        p_j = d['j_wrong'] / d['total']
        p_both = d['both_wrong'] / d['total']
        if p_i * p_j > 0:
            lift = p_both / (p_i * p_j)
        else:
            lift = 1.0
        bar = "+" * int(max(0, (lift-1)) * 50) if lift > 1 else "-" * int(max(0, (1-lift)) * 50)
        print(f"  {corr_bin:>+8.1f} | {lift:>7.3f} | {d['total']:>6} | {bar}")
        lifts_by_corr.append((corr_bin, lift, d['total']))

    # Is there a linear relationship?
    if lifts_by_corr:
        x = [c for c, l, n in lifts_by_corr if n > 50]
        y = [l for c, l, n in lifts_by_corr if n > 50]
        if x and y:
            mean_x = sum(x)/len(x)
            mean_y = sum(y)/len(y)
            cov_xy = sum((x[i]-mean_x)*(y[i]-mean_y) for i in range(len(x)))/len(x)
            var_x = sum((xi-mean_x)**2 for xi in x)/len(x)
            if var_x > 0:
                slope = cov_xy / var_x
                intercept = mean_y - slope * mean_x
                print(f"\n  Linear fit: lift = {intercept:.3f} + {slope:.3f} × sol_corr")
                print(f"  At sol_corr=0: lift = {intercept:.3f}")
                print(f"  Measured overall lift: 1.20")


# ============================================================
# THE FORMULA: Can we compute lift from ε and solution structure?
# ============================================================

def derive_lift_formula():
    """
    If bits i,j have solution-value correlation ρ:
    - P(i=1 in solution) = p_i, P(j=1) = p_j
    - P(i=1 AND j=1) = p_i*p_j + ρ*σ_i*σ_j (where σ = std)

    "Wrong" = tension majority doesn't match solution majority.

    If i and j have correlated solution values:
    → When i's solution value is "atypical" (minority),
      j's is also more likely atypical
    → Both are harder to predict → both wrong more often

    P(both wrong) = P(both have atypical values in solutions)
    × P(tension misreads atypical values)
    """
    print("\n" + "=" * 70)
    print("FORMULA: Lift from solution correlation")
    print("=" * 70)

    # Measure: what is the average solution correlation
    # for pairs sharing vs not sharing clauses?
    random.seed(42)

    avg_rho_shared = []
    avg_rho_unshared = []

    for seed in range(200):
        clauses = random_3sat(12, int(4.27*12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions or len(solutions) < 3: continue

        shared_pairs = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    shared_pairs.add((min(vs[a],vs[b]), max(vs[a],vs[b])))

        for i in range(12):
            vals_i = [s[i] for s in solutions]
            mi = sum(vals_i)/len(vals_i)
            si = math.sqrt(sum((v-mi)**2 for v in vals_i)/len(vals_i))
            for j in range(i+1, 12):
                vals_j = [s[j] for s in solutions]
                mj = sum(vals_j)/len(vals_j)
                sj = math.sqrt(sum((v-mj)**2 for v in vals_j)/len(vals_j))
                if si < 0.01 or sj < 0.01: continue
                cov = sum((vals_i[k]-mi)*(vals_j[k]-mj) for k in range(len(solutions)))/len(solutions)
                rho = cov/(si*sj)
                if (i,j) in shared_pairs:
                    avg_rho_shared.append(rho)
                else:
                    avg_rho_unshared.append(rho)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    rho_s = mean(avg_rho_shared)
    rho_u = mean(avg_rho_unshared)

    print(f"\n  Average solution correlation:")
    print(f"    Shared pairs:   ρ = {rho_s:+.4f}")
    print(f"    Unshared pairs: ρ = {rho_u:+.4f}")
    print(f"    Difference Δρ:    = {rho_s - rho_u:+.4f}")

    # Theoretical lift from ρ:
    # If errors are driven by solution-value fluctuations,
    # and fluctuations are correlated with strength ρ:
    # lift ≈ 1 + ρ × (some function of d and ε)
    #
    # Simple model: lift ≈ 1 + ρ × d/(d × ε²)
    # = 1 + ρ/ε²?
    #
    # More carefully:
    # P(wrong) ≈ 0.30 (at threshold)
    # P(both wrong | correlated) ≈ P(wrong)² × (1 + ρ × f(ε))
    # where f(ε) ≈ 1/variance = 1/(p(1-p)/d) = d/(p(1-p))

    eps = 1/14
    p_corr = 4/7
    d = 13
    variance_per_bit = p_corr * (1-p_corr) / d

    # For a bivariate normal approximation:
    # P(both below threshold) increases by factor (1 + ρ × correction)
    # correction = φ(z)²/(Φ(-z)²) × ρ  (approximately, from bivariate normal)
    # where z = 2ε√d (the z-score for being wrong)

    z = 2 * eps * math.sqrt(d)
    phi_z = math.exp(-z**2/2) / math.sqrt(2*math.pi)
    Phi_neg_z = 0.5 * (1 - math.erf(z/math.sqrt(2)))

    if Phi_neg_z > 0:
        correction = (phi_z / Phi_neg_z) ** 2
    else:
        correction = 0

    predicted_lift_shared = 1 + rho_s * correction
    predicted_lift_unshared = 1 + rho_u * correction

    print(f"\n  Bivariate normal model:")
    print(f"    z = 2ε√d = {z:.4f}")
    print(f"    correction = (φ(z)/Φ(-z))² = {correction:.4f}")
    print(f"    Predicted lift (shared):   1 + {rho_s:.4f} × {correction:.4f} = {predicted_lift_shared:.3f}")
    print(f"    Predicted lift (unshared): 1 + {rho_u:.4f} × {correction:.4f} = {predicted_lift_unshared:.3f}")
    print(f"    Measured lift (shared):   1.20")
    print(f"    Measured lift (unshared): 0.95")


if __name__ == "__main__":
    solution_value_correlation()
    mechanism_analysis()
    derive_lift_formula()
