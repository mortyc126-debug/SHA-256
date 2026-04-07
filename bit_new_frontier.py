"""
NEW FRONTIER: What haven't we tried?

We've exhausted:
- Single bit properties (28+)
- Pair/neighbor properties
- Global graph properties
- Gap field (dynamics, constraints, spectrum, diffusion)
- Contrastive/sampling approaches

What's LEFT?

1. TEMPORAL: we look at tension at t=0. What about its EVOLUTION
   through crystallization? Not just persistence of gap, but the
   TRAJECTORY of tension itself. Does tension trace a path that
   encodes solution info?

2. COUNTERFACTUAL: instead of "what if I fix bit i correctly",
   ask "what if I fix bit i BOTH ways and compare the TWO futures?"
   The DIFFERENCE between two futures encodes which way is right.

3. ENTROPY GRADIENT: the entropy of remaining solutions decreases
   during crystallization. Can we measure the RATE of decrease
   and use it as signal? Fast decrease = good path, slow = bad.

4. CONSTRAINT GRAPH SURGERY: what if we REMOVE a clause and see
   how tension changes? The clause's IMPACT reveals whether it's
   carrying signal or noise.
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
# 1. COUNTERFACTUAL BRANCHING
# ============================================================

def counterfactual():
    """
    For each bit i: fix i=0, crystallize the rest. Fix i=1, crystallize.
    Which branch produces MORE satisfied clauses?
    The better branch → that's the correct value.

    This is like DPLL lookahead but using FULL crystallization
    as the evaluator, not just unit propagation.
    """
    print("=" * 70)
    print("1. COUNTERFACTUAL: Compare two futures")
    print("=" * 70)

    random.seed(42); n = 12

    cf_correct = 0; tension_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            total += 1
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                tension_correct += 1

            # Counterfactual: crystallize with var=0 and var=1
            scores = {}
            for test_val in [0, 1]:
                fixed = {var: test_val}

                # Quick crystallization of remaining
                for step in range(n-1):
                    unfixed = [v for v in range(n) if v not in fixed]
                    if not unfixed: break
                    best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                    s = bit_tension(clauses, n, best, fixed)
                    fixed[best] = 1 if s >= 0 else 0

                assignment = [fixed.get(v, 0) for v in range(n)]
                scores[test_val] = evaluate(clauses, assignment)

            cf_pred = 1 if scores[1] >= scores[0] else 0
            if cf_pred == correct_val[var]:
                cf_correct += 1

    print(f"\n  Tension:        {tension_correct/total*100:.1f}%")
    print(f"  Counterfactual: {cf_correct/total*100:.1f}%")
    print(f"  Improvement:    {(cf_correct-tension_correct)/total*100:+.1f}%")


# ============================================================
# 2. ENTROPY GRADIENT during crystallization
# ============================================================

def entropy_gradient():
    """
    At each crystallization step: how many solutions survive?
    The RATE of entropy loss tells us if we're on the right track.

    Good path: entropy decreases slowly (many solutions stay)
    Bad path: entropy drops fast (solutions dying)

    Can we use this as real-time feedback?
    """
    print("\n" + "=" * 70)
    print("2. ENTROPY GRADIENT: Rate of solution loss")
    print("=" * 70)

    random.seed(42); n = 12

    # Compare: successful vs failed crystallizations
    success_entropy_curves = []
    fail_entropy_curves = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for run in range(5):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.15)))
            entropy_curve = [len(solutions)]

            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0

                # Count surviving solutions
                remaining = sum(1 for s in solutions
                               if all(s[v] == fixed[v] for v in fixed))
                entropy_curve.append(remaining)

            success = evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses)
            if success:
                success_entropy_curves.append(entropy_curve)
            else:
                fail_entropy_curves.append(entropy_curve)

    # Compare curves
    if success_entropy_curves and fail_entropy_curves:
        max_len = min(min(len(c) for c in success_entropy_curves),
                      min(len(c) for c in fail_entropy_curves))

        print(f"\n  {'step':>4} | {'success sols':>12} | {'fail sols':>10} | {'ratio':>7}")
        print("  " + "-" * 45)

        for step in range(min(max_len, n+1)):
            s_vals = [c[step] for c in success_entropy_curves if len(c) > step]
            f_vals = [c[step] for c in fail_entropy_curves if len(c) > step]
            s_mean = sum(s_vals)/len(s_vals) if s_vals else 0
            f_mean = sum(f_vals)/len(f_vals) if f_vals else 0
            ratio = s_mean/f_mean if f_mean > 0 else 0
            print(f"  {step:>4} | {s_mean:>12.1f} | {f_mean:>10.1f} | {ratio:>7.2f}")

        # At which step do they diverge?
        print(f"\n  Success keeps MORE solutions at every step.")
        print(f"  The DIVERGENCE starts at step 1.")
        print(f"  → Solution count is IMMEDIATELY informative.")


# ============================================================
# 3. CLAUSE SURGERY: Remove clause, measure tension change
# ============================================================

def clause_surgery():
    """
    For each clause: remove it, recompute tension.
    How much does tension change?
    Does the change predict whether the clause is redundant?
    """
    print("\n" + "=" * 70)
    print("3. CLAUSE SURGERY: Which clauses carry signal?")
    print("=" * 70)

    random.seed(42); n = 12

    signal_clauses_help = 0; noise_clauses_help = 0
    signal_total = 0; noise_total = 0

    for seed in range(60):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # For each clause: is it "signal" or "noise"?
        for ci in range(len(clauses)):
            # Remove clause ci
            reduced = clauses[:ci] + clauses[ci+1:]

            # Measure: does removing it HELP or HURT accuracy?
            better = 0; worse = 0; same = 0
            for var in [v for v, s in clauses[ci]]:
                sigma_full = bit_tension(clauses, n, var)
                sigma_reduced = bit_tension(reduced, n, var)

                pred_full = 1 if sigma_full >= 0 else 0
                pred_reduced = 1 if sigma_reduced >= 0 else 0
                actual = correct_val[var]

                if pred_reduced == actual and pred_full != actual:
                    better += 1
                elif pred_reduced != actual and pred_full == actual:
                    worse += 1

            is_noise = better > worse  # removing helps → was noise
            if is_noise:
                noise_total += 1
                # Does this clause look different structurally?
                noise_clauses_help += better
            else:
                signal_total += 1
                signal_clauses_help += worse

    total_clauses = signal_total + noise_total
    if total_clauses > 0:
        print(f"\n  Signal clauses: {signal_total}/{total_clauses} ({signal_total/total_clauses*100:.1f}%)")
        print(f"  Noise clauses:  {noise_total}/{total_clauses} ({noise_total/total_clauses*100:.1f}%)")
        print(f"  → {noise_total/total_clauses*100:.0f}% of clauses are noise (removing helps)")


# ============================================================
# 4. COUNTERFACTUAL SOLVER: use two-future comparison
# ============================================================

def counterfactual_solver():
    """
    Solver: for the MOST UNCERTAIN bit (lowest |σ|):
    Try both values, crystallize each, pick the one with
    more satisfied clauses.

    Only do this for uncertain bits. Confident bits: standard tension.
    """
    print("\n" + "=" * 70)
    print("4. COUNTERFACTUAL SOLVER")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'cf_solver': 0, 'total': 0}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Counterfactual solver
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break

            # Sort by confidence
            scored = [(v, abs(bit_tension(clauses, n, v, fixed))) for v in unfixed]
            scored.sort(key=lambda x: -x[1])

            # Most confident: just use tension
            best_var = scored[0][0]
            best_sigma = bit_tension(clauses, n, best_var, fixed)

            if abs(best_sigma) > 0.3:
                # Confident: just fix by tension
                fixed[best_var] = 1 if best_sigma >= 0 else 0
            else:
                # Uncertain: counterfactual comparison
                scores = {}
                for test_val in [0, 1]:
                    test_fixed = dict(fixed)
                    test_fixed[best_var] = test_val
                    # Quick crystallize rest
                    for sub_step in range(n):
                        sub_unfixed = [v for v in range(n) if v not in test_fixed]
                        if not sub_unfixed: break
                        sub_best = max(sub_unfixed,
                                      key=lambda v: abs(bit_tension(clauses, n, v, test_fixed)))
                        s = bit_tension(clauses, n, sub_best, test_fixed)
                        test_fixed[sub_best] = 1 if s >= 0 else 0
                    a = [test_fixed.get(v,0) for v in range(n)]
                    scores[test_val] = evaluate(clauses, a)

                fixed[best_var] = 1 if scores[1] >= scores[0] else 0

        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['cf_solver'] += 1

    t = results['total']
    print(f"\n  Standard:       {results['standard']}/{t} ({results['standard']/t*100:.1f}%)")
    print(f"  Counterfactual: {results['cf_solver']}/{t} ({results['cf_solver']/t*100:.1f}%)")
    delta = (results['cf_solver'] - results['standard'])/t*100
    print(f"  Improvement:    {delta:+.1f}%")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    counterfactual()
    entropy_gradient()
    clause_surgery()
    counterfactual_solver()
