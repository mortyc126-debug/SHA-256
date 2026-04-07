"""
PROCESS INFORMATION — Can we extract gap's process info without solutions?

Gap tells us the optimal ORDER for crystallization.
We can't compute gap without solutions.
But crystallization FAILURES might reveal gap indirectly.

Key insight: if we try many orderings and some FAIL while others SUCCEED,
the PATTERN of failures encodes gap information.

Failed crystallizations tell us: "this ordering was wrong."
Which bits caused the failure? Those are high-gap bits.

Can we learn gap from failures?
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
# 1. FAILURE FINGERPRINT: which bits differ between success and failure?
# ============================================================

def failure_fingerprint():
    """
    Run many crystallizations. For each bit:
    How often does it have DIFFERENT values in successful vs failed runs?

    If bit v has the same value in all successful runs but different
    in failed runs → it's a "failure point" → high gap.
    """
    print("=" * 70)
    print("1. FAILURE FINGERPRINT: Learning gap from crystallization failures")
    print("=" * 70)

    random.seed(42)
    n = 12

    fingerprint_gap_corr = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        # Ground truth gap
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        sol_signal = [2*p-1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        actual_gap = [abs(clause_signal[v] - sol_signal[v]) for v in range(n)]

        # Run 30 crystallizations
        success_vals = {v: [] for v in range(n)}
        fail_vals = {v: [] for v in range(n)}

        for run in range(30):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.15)))

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

            assignment = [fixed.get(v,0) for v in range(n)]
            success = evaluate(clauses, assignment) == len(clauses)

            for v in range(n):
                if success:
                    success_vals[v].append(assignment[v])
                else:
                    fail_vals[v].append(assignment[v])

        # Fingerprint: variance of values across FAILED runs
        # High variance = bit is UNSTABLE in failures → high gap?
        fingerprint = []
        for v in range(n):
            if fail_vals[v]:
                p1 = sum(fail_vals[v]) / len(fail_vals[v])
                var = p1 * (1 - p1)
                fingerprint.append(var)
            else:
                fingerprint.append(0)

        # Disagreement between success and failure values
        disagreement = []
        for v in range(n):
            if success_vals[v] and fail_vals[v]:
                s_avg = sum(success_vals[v]) / len(success_vals[v])
                f_avg = sum(fail_vals[v]) / len(fail_vals[v])
                disagreement.append(abs(s_avg - f_avg))
            else:
                disagreement.append(0)

        # Correlation with actual gap
        for proxy, proxy_name in [(fingerprint, "fail_variance"), (disagreement, "disagree")]:
            if sum(proxy) < 0.001: continue
            mg = sum(actual_gap)/n; mp = sum(proxy)/n
            sg = math.sqrt(sum((g-mg)**2 for g in actual_gap)/n)
            sp = math.sqrt(sum((p-mp)**2 for p in proxy)/n)
            if sg > 0.01 and sp > 0.01:
                cov = sum((actual_gap[i]-mg)*(proxy[i]-mp) for i in range(n))/n
                corr = cov/(sg*sp)
                fingerprint_gap_corr.append((proxy_name, corr))

    # Aggregate
    for proxy_name in ["fail_variance", "disagree"]:
        corrs = [c for name, c in fingerprint_gap_corr if name == proxy_name]
        if corrs:
            mean_corr = sum(corrs)/len(corrs)
            print(f"\n  {proxy_name:>15}: corr with |gap| = {mean_corr:.4f} (n={len(corrs)})")


# ============================================================
# 2. CONTRASTIVE GAP: difference between success and failure
# ============================================================

def contrastive_gap():
    """
    For each bit: value_in_success - value_in_failure.
    This is computable WITHOUT solutions (just run crystallization many times).
    Does it approximate the actual gap?
    Does it IMPROVE prediction?
    """
    print("\n" + "=" * 70)
    print("2. CONTRASTIVE GAP: Success vs Failure as gap proxy")
    print("=" * 70)

    random.seed(42)
    n = 12

    std_correct = 0; contrastive_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Run crystallizations
        success_runs = []
        fail_runs = []

        for run in range(30):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.15)))
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

            assignment = [fixed.get(v,0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                success_runs.append(assignment)
            else:
                fail_runs.append(assignment)

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Standard tension
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == actual: std_correct += 1

            # Contrastive: prefer success-run values
            if success_runs:
                s_avg = sum(r[var] for r in success_runs) / len(success_runs)
                pred = 1 if s_avg > 0.5 else 0
            elif fail_runs:
                # No success? Use fail majority but with tension tiebreak
                f_avg = sum(r[var] for r in fail_runs) / len(fail_runs)
                if abs(f_avg - 0.5) > 0.1:
                    pred = 1 if f_avg > 0.5 else 0
                else:
                    pred = 1 if sigma >= 0 else 0
            else:
                pred = 1 if sigma >= 0 else 0

            if pred == actual: contrastive_correct += 1

    print(f"\n  Standard tension:  {std_correct/total*100:.1f}%")
    print(f"  Contrastive:       {contrastive_correct/total*100:.1f}%")
    print(f"  Improvement:       {(contrastive_correct-std_correct)/total*100:+.1f}%")


# ============================================================
# 3. GAP-AWARE ORDERING: use estimated gap to choose order
# ============================================================

def gap_aware_solver():
    """
    If gap tells us the optimal ORDER:
    And failure fingerprint approximates gap:
    Then we can build an ORDER from failures.

    Two-phase solver:
    Phase 1: run 10 crystallizations, identify "unstable" bits
    Phase 2: fix STABLE bits first, UNSTABLE bits last
    """
    print("\n" + "=" * 70)
    print("3. GAP-AWARE SOLVER: Learn ordering from failures")
    print("=" * 70)

    random.seed(42)
    n = 12

    results = {'standard': 0, 'gap_aware': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard crystallization
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            sigma = bit_tension(clauses, n, best, fixed)
            fixed[best] = 1 if sigma >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Phase 1: discover unstable bits through 10 quick runs
        bit_stability = {v: [] for v in range(n)}
        for run in range(10):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.2)))
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0
            for v in range(n):
                bit_stability[v].append(fixed.get(v, 0))

        # Stability score: how consistent is each bit?
        stability = {}
        for v in range(n):
            vals = bit_stability[v]
            p1 = sum(vals) / len(vals)
            stability[v] = 1 - 4 * p1 * (1 - p1)  # 1=always same, 0=50/50

        # Phase 2: fix STABLE bits first, UNSTABLE last
        order = sorted(range(n), key=lambda v: (-stability[v], -abs(bit_tension(clauses, n, v))))
        fixed = {}
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

        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['gap_aware'] += 1

    t = results['total']
    print(f"\n  Standard:   {results['standard']}/{t} ({results['standard']/t*100:.1f}%)")
    print(f"  Gap-aware:  {results['gap_aware']}/{t} ({results['gap_aware']/t*100:.1f}%)")
    print(f"  Improvement: {(results['gap_aware']-results['standard'])/t*100:+.1f}%")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    failure_fingerprint()
    contrastive_gap()
    gap_aware_solver()
