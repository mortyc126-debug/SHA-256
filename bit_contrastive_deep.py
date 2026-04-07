"""
CONTRASTIVE DEEP DIVE

86.4% per-bit via success-only voting. Can we go FURTHER?

Ideas:
1. WEIGHTED contrastive: weight successful runs by HOW successful
   (how many clauses satisfied, how fast found)
2. ITERATIVE contrastive: use contrastive result as SEED for next round
3. FAILURE INVERSION: what do FAILED runs teach us? (not just ignore them)
4. HYBRID: contrastive + v4 tension for bits without successful data
5. SCALE: does 86% hold at larger n?
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


def noisy_crystallize(clauses, n, noise=0.15):
    """Run one noisy crystallization with unit propagation."""
    fixed = {}
    order = list(range(n))
    order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, noise)))
    for var in order:
        if var in fixed: continue
        sigma = bit_tension(clauses, n, var, fixed)
        fixed[var] = 1 if sigma >= 0 else 0
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
    return [fixed.get(v,0) for v in range(n)]


# ============================================================
# 1. FAILURE INVERSION: use failures as NEGATIVE signal
# ============================================================

def failure_inversion():
    """
    Failed runs give WRONG answers. If a bit has value 1 in most
    failed runs → maybe it should be 0.

    Contrastive+Inversion: success_vote - failure_vote
    """
    print("=" * 70)
    print("1. FAILURE INVERSION: Subtract failure signal")
    print("=" * 70)

    random.seed(42); n = 12
    methods = {'tension': 0, 'success_only': 0, 'contrastive_inv': 0,
               'weighted': 0, 'total': 0}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        methods['total'] += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        success_runs = []; fail_runs = []
        for run in range(30):
            assignment = noisy_crystallize(clauses, n, 0.15)
            if evaluate(clauses, assignment) == len(clauses):
                success_runs.append(assignment)
            else:
                fail_runs.append(assignment)

        for var in range(n):
            actual = correct_val[var]
            sigma = bit_tension(clauses, n, var)

            # Standard
            if (1 if sigma >= 0 else 0) == actual: methods['tension'] += 1

            # Success only
            if success_runs:
                s_avg = sum(r[var] for r in success_runs)/len(success_runs)
                pred_s = 1 if s_avg > 0.5 else 0
            else:
                pred_s = 1 if sigma >= 0 else 0
            if pred_s == actual: methods['success_only'] += 1

            # Contrastive inversion: success - failure
            if success_runs and fail_runs:
                s_avg = sum(r[var] for r in success_runs)/len(success_runs)
                f_avg = sum(r[var] for r in fail_runs)/len(fail_runs)
                contrast = s_avg - f_avg  # positive = success prefers 1
                # Combine with tension
                combined = 0.5 * (2*s_avg-1) + 0.3 * contrast + 0.2 * sigma
                pred_ci = 1 if combined > 0 else 0
            elif success_runs:
                pred_ci = pred_s
            else:
                pred_ci = 1 if sigma >= 0 else 0
            if pred_ci == actual: methods['contrastive_inv'] += 1

            # Weighted: more weight to bits with HIGH agreement across successes
            if success_runs:
                s_avg = sum(r[var] for r in success_runs)/len(success_runs)
                confidence = abs(s_avg - 0.5) * 2  # 0-1
                # High confidence → trust success; Low → fallback to tension
                if confidence > 0.3:
                    pred_w = 1 if s_avg > 0.5 else 0
                else:
                    pred_w = 1 if sigma >= 0 else 0
            else:
                pred_w = 1 if sigma >= 0 else 0
            if pred_w == actual: methods['weighted'] += 1

    t = methods['total'] * n
    print(f"\n  Per-bit accuracy:")
    for name in ['tension', 'success_only', 'contrastive_inv', 'weighted']:
        pct = methods[name]/t*100
        delta = pct - methods['tension']/t*100
        print(f"    {name:>20}: {pct:.1f}% ({delta:+.1f}%)")


# ============================================================
# 2. ITERATIVE CONTRASTIVE: use result as seed for next round
# ============================================================

def iterative_contrastive():
    """
    Round 1: standard contrastive → get per-bit estimates
    Round 2: use Round 1 estimates as STARTING POINT for new crystallizations
             (not random start — start from contrastive result)
    Round 3: refine further
    """
    print("\n" + "=" * 70)
    print("2. ITERATIVE CONTRASTIVE: Multiple rounds of refinement")
    print("=" * 70)

    random.seed(42); n = 12

    for n_rounds in [1, 2, 3]:
        correct = 0; total = 0

        for seed in range(150):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            # Round 1: standard contrastive
            estimates = [0.5] * n  # initial: no information
            for round_idx in range(n_rounds):
                success_runs = []
                for run in range(20):
                    if round_idx == 0:
                        assignment = noisy_crystallize(clauses, n, 0.15)
                    else:
                        # Start from previous estimate with noise
                        fixed = {}
                        order = list(range(n))
                        random.shuffle(order)
                        # Fix high-confidence bits from estimate first
                        order.sort(key=lambda v: -abs(estimates[v] - 0.5))
                        for var in order:
                            if var in fixed: continue
                            # Use estimate with noise
                            if abs(estimates[var] - 0.5) > 0.3:
                                fixed[var] = 1 if estimates[var] > 0.5 else 0
                            else:
                                sigma = bit_tension(clauses, n, var, fixed)
                                fixed[var] = 1 if sigma >= 0 else 0
                            # UP
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
                        assignment = [fixed.get(v,0) for v in range(n)]

                    if evaluate(clauses, assignment) == len(clauses):
                        success_runs.append(assignment)

                # Update estimates from successes
                if success_runs:
                    for v in range(n):
                        estimates[v] = sum(r[v] for r in success_runs)/len(success_runs)

            for var in range(n):
                total += 1
                pred = 1 if estimates[var] > 0.5 else 0
                if pred == correct_val[var]: correct += 1

        print(f"  {n_rounds} rounds: {correct/total*100:.1f}%")


# ============================================================
# 3. SCALING: Does contrastive work at larger n?
# ============================================================

def contrastive_scaling():
    print("\n" + "=" * 70)
    print("3. CONTRASTIVE SCALING")
    print("=" * 70)

    for n_test in [12, 16, 20]:
        random.seed(42)

        # For n>16 we can't compute solutions for ground truth.
        # Use: does contrastive SOLVE the instance?

        std_solved = 0; contrast_solved = 0; total = 0

        for seed in range(100):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed+500000)

            if n_test <= 16:
                solutions = find_solutions(clauses, n_test)
                if not solutions: continue
            total += 1

            # Standard crystallization
            assignment = noisy_crystallize(clauses, n_test, 0.0)  # no noise
            if evaluate(clauses, assignment) == len(clauses):
                std_solved += 1

            # Contrastive
            success_runs = []
            for run in range(30):
                a = noisy_crystallize(clauses, n_test, 0.15)
                if evaluate(clauses, a) == len(clauses):
                    success_runs.append(a)

            if success_runs:
                # Vote across successes
                c_assignment = []
                for v in range(n_test):
                    s_avg = sum(r[v] for r in success_runs)/len(success_runs)
                    c_assignment.append(1 if s_avg > 0.5 else 0)
                if evaluate(clauses, c_assignment) == len(clauses):
                    contrast_solved += 1

        print(f"\n  n={n_test}: standard={std_solved}/{total} ({std_solved/total*100:.1f}%), "
              f"contrastive={contrast_solved}/{total} ({contrast_solved/total*100:.1f}%)")


# ============================================================
# 4. WHAT MAKES CONTRASTIVE WORK: analysis
# ============================================================

def contrastive_analysis():
    """
    Why does success-only voting give 86%?
    Is it just because successful runs ARE solutions?
    If so: contrastive = cheap solution sampling.
    If not: something deeper.
    """
    print("\n" + "=" * 70)
    print("4. ANALYSIS: Why does contrastive work?")
    print("=" * 70)

    random.seed(42); n = 12

    n_success_runs = []
    unique_solutions = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        success_runs = []
        for run in range(30):
            a = noisy_crystallize(clauses, n, 0.15)
            if evaluate(clauses, a) == len(clauses):
                success_runs.append(tuple(a))

        n_success_runs.append(len(success_runs))
        unique_solutions.append(len(set(success_runs)))

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg successful runs (out of 30): {mean(n_success_runs):.1f}")
    print(f"  Avg UNIQUE solutions found:      {mean(unique_solutions):.1f}")
    print(f"  Total solutions in instance:     {mean([len(find_solutions(random_3sat(n, int(4.27*n), seed=seed), n)) for seed in range(20)]):.1f}")

    # Is contrastive just solution sampling?
    print(f"\n  Contrastive IS solution sampling:")
    print(f"  It finds ~{mean(n_success_runs):.0f} solutions via crystallization.")
    print(f"  These are ~{mean(unique_solutions):.0f} unique solutions.")
    print(f"  Voting across them ≈ marginal MAP ≈ 86-89% accuracy.")
    print(f"  This matches our earlier WalkSAT voting result (90%).")
    print(f"  Contrastive = crystallization-based solution sampling.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    failure_inversion()
    iterative_contrastive()
    contrastive_scaling()
    contrastive_analysis()
