"""
BEYOND KNOWN MATHEMATICS

The gap field lives BETWEEN clause space and solution space.
It's structured but unpredictable from either side alone.

What if the gap field has its own dynamics?
Not derived from clauses. Not derived from solutions.
EMERGENT from the interaction between the two.

Three radical directions:

1. GAP FIELD EQUATION OF MOTION:
   Does gap_i at step t predict gap_i at step t+1
   during crystallization? If yes → gap has dynamics.

2. GAP FIELD SELF-CONSISTENCY:
   The gap field must satisfy constraints.
   gap = σ_clause - σ_solution.
   Both σ_clause and σ_solution satisfy constraints.
   What constraints does gap itself satisfy?

3. GAP AS OBSERVABLE:
   Can we MEASURE gap without knowing σ_solution?
   Not predict it from clauses — but OBSERVE it through
   some indirect measurement, like a physical experiment
   that reveals hidden structure without solving.
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
# DIRECTION 1: Gap field dynamics during crystallization
# ============================================================

def gap_dynamics():
    """
    During crystallization, we fix bits one by one.
    At each step: gap_i changes (because σ_clause changes, and
    remaining solutions change).

    Question: is gap at step t+1 predictable from gap at step t?
    If gap has INERTIA — it persists — then we can track it.
    """
    print("=" * 70)
    print("DIRECTION 1: Gap field dynamics")
    print("Does gap persist during crystallization?")
    print("=" * 70)

    random.seed(42)
    n = 12

    gap_persistence = []  # correlation of gap between consecutive steps

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        fixed = {}
        prev_gaps = None

        for step in range(n-1):
            unfixed = [v for v in range(n) if v not in fixed]
            if len(unfixed) < 3: break

            # Current gap field
            remaining_solutions = [s for s in solutions
                                   if all(s[v] == fixed[v] for v in fixed)]
            if len(remaining_solutions) < 1: break

            curr_prob = [sum(s[v] for s in remaining_solutions)/len(remaining_solutions)
                        for v in range(n)]
            curr_sol_signal = [2*p-1 for p in curr_prob]
            curr_clause_signal = [bit_tension(clauses, n, v, fixed) for v in range(n)]
            curr_gaps = {v: curr_clause_signal[v] - curr_sol_signal[v] for v in unfixed}

            # Correlation with previous step
            if prev_gaps is not None:
                common = [v for v in curr_gaps if v in prev_gaps]
                if len(common) >= 3:
                    g_prev = [prev_gaps[v] for v in common]
                    g_curr = [curr_gaps[v] for v in common]
                    mp = sum(g_prev)/len(g_prev)
                    mc = sum(g_curr)/len(g_curr)
                    sp = math.sqrt(sum((g-mp)**2 for g in g_prev)/len(g_prev))
                    sc = math.sqrt(sum((g-mc)**2 for g in g_curr)/len(g_curr))
                    if sp > 0.01 and sc > 0.01:
                        cov = sum((g_prev[i]-mp)*(g_curr[i]-mc)
                                 for i in range(len(common)))/len(common)
                        corr = cov/(sp*sc)
                        gap_persistence.append(corr)

            prev_gaps = curr_gaps

            # Fix most confident bit correctly
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = correct_val[best]

    if gap_persistence:
        mean_p = sum(gap_persistence)/len(gap_persistence)
        print(f"\n  Gap persistence (correlation step t → t+1): {mean_p:.4f}")
        print(f"  n measurements: {len(gap_persistence)}")
        if mean_p > 0.5:
            print(f"  → Gap is PERSISTENT (>0.5). It has inertia!")
            print(f"  → Gap field has DYNAMICS, not just static noise.")
        elif mean_p > 0.2:
            print(f"  → Gap is MODERATELY persistent.")
        else:
            print(f"  → Gap is NOT persistent. Resets each step.")


# ============================================================
# DIRECTION 2: Gap field constraints
# ============================================================

def gap_constraints():
    """
    gap_i = σ_clause_i - σ_solution_i

    σ_clause satisfies: Σ σ_clause ≈ 0 (balanced by construction)
    σ_solution satisfies: Σ σ_solution ≈ 0 (solutions balanced)
    Therefore: Σ gap_i ≈ 0 (gap sums to zero)

    But are there STRONGER constraints?

    For each clause (i,j,k): is there a constraint on gap_i + gap_j + gap_k?
    The clause connects three bits. Their gaps might be constrained jointly.
    """
    print("\n" + "=" * 70)
    print("DIRECTION 2: Gap field constraints")
    print("Are there LAWS the gap field must obey?")
    print("=" * 70)

    random.seed(42)
    n = 12

    gap_sums = []  # Σ gap_i
    clause_gap_sums = []  # gap_i + gap_j + gap_k for each clause
    clause_gap_products = []  # gap_i × gap_j × gap_k

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        sol_signal = [2*p-1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        gap = [clause_signal[v] - sol_signal[v] for v in range(n)]

        gap_sums.append(sum(gap))

        for clause in clauses:
            vs = [v for v, s in clause]
            g_sum = sum(gap[v] for v in vs)
            g_prod = 1
            for v in vs: g_prod *= gap[v]
            clause_gap_sums.append(g_sum)
            clause_gap_products.append(g_prod)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    std = lambda lst: math.sqrt(sum((x-mean(lst))**2 for x in lst)/len(lst)) if lst else 0

    print(f"\n  Σ gap_i (global sum):")
    print(f"    Mean: {mean(gap_sums):.4f}")
    print(f"    Std:  {std(gap_sums):.4f}")
    print(f"    → {'ZERO (constrained)' if abs(mean(gap_sums)) < std(gap_sums)*0.1 else 'NOT zero'}")

    print(f"\n  Per-clause gap sum (gap_i + gap_j + gap_k):")
    print(f"    Mean: {mean(clause_gap_sums):.4f}")
    print(f"    Std:  {std(clause_gap_sums):.4f}")
    print(f"    → {'CONSTRAINED' if abs(mean(clause_gap_sums)) < std(clause_gap_sums)*0.1 else 'has bias'}")

    print(f"\n  Per-clause gap product (gap_i × gap_j × gap_k):")
    print(f"    Mean: {mean(clause_gap_products):.6f}")
    print(f"    Std:  {std(clause_gap_products):.6f}")

    # Check: is gap product biased positive or negative?
    if mean(clause_gap_products) > 2 * std(clause_gap_products) / math.sqrt(len(clause_gap_products)):
        print(f"    → BIASED POSITIVE: gaps tend to have same sign in a clause")
    elif mean(clause_gap_products) < -2 * std(clause_gap_products) / math.sqrt(len(clause_gap_products)):
        print(f"    → BIASED NEGATIVE: gaps tend to have mixed signs in a clause")
    else:
        print(f"    → No significant bias")


# ============================================================
# DIRECTION 3: Indirect gap observation
# ============================================================

def indirect_gap_observation():
    """
    Can we OBSERVE the gap field without knowing solutions?

    Idea: the gap field affects CRYSTALLIZATION DYNAMICS.
    If we crystallize many times with different orderings,
    the bits where gap is large should show MORE VARIANCE
    across crystallization runs.

    Variance of prediction across runs = proxy for |gap|.
    This doesn't require solutions!
    """
    print("\n" + "=" * 70)
    print("DIRECTION 3: Observing gap without solutions")
    print("Multi-run variance as proxy for |gap|")
    print("=" * 70)

    random.seed(42)
    n = 12

    corr_variance_gap = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        sol_signal = [2*p-1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        actual_gap = [abs(clause_signal[v] - sol_signal[v]) for v in range(n)]

        # Run crystallization 20 times with random order
        predictions = {v: [] for v in range(n)}
        for run in range(20):
            fixed = {}
            order = list(range(n))
            random.shuffle(order)
            # Sort with noise
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.1)))

            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0

                # Unit propagation
                changed = True
                while changed:
                    changed = False
                    for clause in clauses:
                        satisfied = False; free = []
                        for v, s in clause:
                            if v in fixed:
                                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                    satisfied = True; break
                            else: free.append((v,s))
                        if not satisfied and len(free) == 1:
                            v, s = free[0]
                            if v not in fixed: fixed[v] = 1 if s==1 else 0; changed = True

            for v in range(n):
                predictions[v].append(fixed.get(v, 0))

        # Variance of predictions per bit
        pred_variance = []
        for v in range(n):
            p_1 = sum(predictions[v]) / len(predictions[v])
            var = p_1 * (1 - p_1)  # Bernoulli variance
            pred_variance.append(var)

        # Correlation between pred_variance and actual |gap|
        if len(actual_gap) > 2:
            mg = sum(actual_gap)/len(actual_gap)
            mv = sum(pred_variance)/len(pred_variance)
            sg = math.sqrt(sum((g-mg)**2 for g in actual_gap)/len(actual_gap))
            sv = math.sqrt(sum((v-mv)**2 for v in pred_variance)/len(pred_variance))
            if sg > 0.01 and sv > 0.01:
                cov = sum((actual_gap[i]-mg)*(pred_variance[i]-mv)
                         for i in range(n))/n
                corr = cov/(sg*sv)
                corr_variance_gap.append(corr)

    if corr_variance_gap:
        mean_corr = sum(corr_variance_gap)/len(corr_variance_gap)
        print(f"\n  Correlation(prediction_variance, actual |gap|): {mean_corr:.4f}")
        print(f"  n instances: {len(corr_variance_gap)}")

        if mean_corr > 0.3:
            print(f"\n  → STRONG CORRELATION!")
            print(f"  → Multi-run variance IS a proxy for gap.")
            print(f"  → We can OBSERVE gap without solutions!")
            print(f"  → This opens a new pathway: use variance to")
            print(f"     weight bits, improving beyond the wall.")
        elif mean_corr > 0.1:
            print(f"\n  → Moderate correlation. Partial proxy.")
        else:
            print(f"\n  → Weak correlation. Variance is not a good proxy.")

    # If variance is a proxy: use it to improve prediction
    print(f"\n  Test: does variance-weighted tension beat standard?")

    std_correct = 0; var_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Multi-run to get variance
        predictions = {v: [] for v in range(n)}
        for run in range(15):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.15)))
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0
            for v in range(n):
                predictions[v].append(fixed.get(v, 0))

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Standard: tension
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == actual: std_correct += 1

            # Variance-weighted: use multi-run majority
            p_1 = sum(predictions[var])/len(predictions[var])
            if (1 if p_1 > 0.5 else 0) == actual: var_correct += 1

    print(f"\n  Standard tension:    {std_correct/total*100:.1f}%")
    print(f"  Multi-run majority:  {var_correct/total*100:.1f}%")
    print(f"  Improvement:         {(var_correct-std_correct)/total*100:+.1f}%")


# ============================================================
# DIRECTION 4: The third space
# ============================================================

def the_third_space():
    """
    Clause space → tension → 70%
    Solution space → marginal → 88%
    Gap space → ??? → ???

    What if we define operations DIRECTLY on the gap field?
    Not through clauses or solutions — but on the gap itself.

    Gap field is a vector in R^n.
    It has spatial correlation (measured).
    It sums to ~0 (measured).
    Its magnitude correlates with multi-run variance (measured).

    What if gap satisfies a DIFFUSION EQUATION?
    gap(t+1) = gap(t) + D × Δgap + noise
    where Δgap is the graph Laplacian applied to gap?

    This would mean: gap "flows" through the constraint graph.
    High-gap regions diffuse into low-gap regions over time.
    If we could simulate this diffusion, we could predict gap.
    """
    print("\n" + "=" * 70)
    print("DIRECTION 4: Does gap satisfy a diffusion equation?")
    print("=" * 70)

    random.seed(42)
    n = 12

    # Test: does graph-Laplacian of gap predict gap evolution?
    laplacian_corrs = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        sol_signal = [2*p-1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        gap = [clause_signal[v] - sol_signal[v] for v in range(n)]

        # Build adjacency
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        # Graph Laplacian of gap: Δgap_i = avg(gap_j for j neighbor) - gap_i
        laplacian_gap = []
        for v in range(n):
            if adj[v]:
                avg_nb = sum(gap[j] for j in adj[v]) / len(adj[v])
                laplacian_gap.append(avg_nb - gap[v])
            else:
                laplacian_gap.append(0)

        # Fix one bit, measure new gap
        best = max(range(n), key=lambda v: abs(clause_signal[v]))
        fixed = {best: correct_val[best]}
        remaining_sol = [s for s in solutions if s[best] == correct_val[best]]
        if len(remaining_sol) < 1: continue

        new_prob = [sum(s[v] for s in remaining_sol)/len(remaining_sol) for v in range(n)]
        new_sol_signal = [2*p-1 for p in new_prob]
        new_clause_signal = [bit_tension(clauses, n, v, fixed) for v in range(n)]
        new_gap = [new_clause_signal[v] - new_sol_signal[v] for v in range(n)]

        # Delta gap
        delta_gap = [new_gap[v] - gap[v] for v in range(n) if v != best]
        laplacian_vals = [laplacian_gap[v] for v in range(n) if v != best]

        # Correlation: does Δgap ∝ Laplacian(gap)?
        if len(delta_gap) > 3:
            md = sum(delta_gap)/len(delta_gap)
            ml = sum(laplacian_vals)/len(laplacian_vals)
            sd = math.sqrt(sum((d-md)**2 for d in delta_gap)/len(delta_gap))
            sl = math.sqrt(sum((l-ml)**2 for l in laplacian_vals)/len(laplacian_vals))
            if sd > 0.01 and sl > 0.01:
                cov = sum((delta_gap[i]-md)*(laplacian_vals[i]-ml)
                         for i in range(len(delta_gap)))/len(delta_gap)
                corr = cov/(sd*sl)
                laplacian_corrs.append(corr)

    if laplacian_corrs:
        mean_corr = sum(laplacian_corrs)/len(laplacian_corrs)
        print(f"\n  Correlation(Δgap, Laplacian(gap)): {mean_corr:.4f}")
        print(f"  n instances: {len(laplacian_corrs)}")

        if mean_corr > 0.2:
            print(f"\n  → Gap DOES follow diffusion-like dynamics!")
            print(f"  → Δgap ∝ D × Lap(gap) + noise")
            print(f"  → This is a HEAT EQUATION for the gap field.")
            print(f"  → Gap \"flows\" through the constraint graph.")
        elif mean_corr > 0.05:
            print(f"\n  → Weak diffusion signal. Partially consistent.")
        else:
            print(f"\n  → No diffusion. Gap dynamics are not Laplacian.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    gap_dynamics()
    gap_constraints()
    indirect_gap_observation()
    the_third_space()
