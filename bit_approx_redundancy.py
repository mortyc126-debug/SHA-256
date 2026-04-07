"""
CAN WE APPROXIMATE REDUNDANCY WITHOUT KNOWING SOLUTIONS?

Redundancy of clause C for bit i = P(C satisfied without i's help).
Knowing this exactly requires solutions. But can we ESTIMATE it?

Ideas:
1. TENSION-BASED: if other literals in C have high |σ| toward satisfying,
   C is probably redundant. Use tensions as proxy for solution probabilities.
2. V4-BASED: iterative tension gives better estimates of P(literal true).
3. COUNTING: how many OTHER ways can C be satisfied? Purely structural.
4. WALKSAT-BASED: sample solutions, estimate redundancy from samples.
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


def walksat(clauses, n, max_flips=None):
    if max_flips is None: max_flips = 100*n
    assignment = [random.randint(0,1) for _ in range(n)]
    m = len(clauses)
    for flip in range(max_flips):
        unsat = [ci for ci in range(m) if not any(
            (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
            for v,s in clauses[ci])]
        if not unsat: return assignment, True
        ci = random.choice(unsat)
        if random.random() < 0.3:
            v, s = random.choice(clauses[ci])
            assignment[v] = 1-assignment[v]
        else:
            best_v = None; best_b = float('inf')
            for v,s in clauses[ci]:
                assignment[v] = 1-assignment[v]
                b = sum(1 for cj in range(m) if not any(
                    (ss==1 and assignment[vv]==1) or (ss==-1 and assignment[vv]==0)
                    for vv,ss in clauses[cj]))
                assignment[v] = 1-assignment[v]
                if b < best_b: best_b = b; best_v = v
            if best_v is not None: assignment[best_v] = 1-assignment[best_v]
    return assignment, False


# ============================================================
# METHOD 1: Tension-estimated redundancy
# ============================================================

def tension_redundancy(clauses, n, var, tensions=None):
    """
    For each clause containing var:
    Estimate P(clause satisfied by others) using tensions as probabilities.

    P(literal (v,s) true) ≈ (1 + s×σ_v) / 2
    P(clause satisfied by others) = 1 - Π(1 - P(lit_j true)) for j ≠ var
    """
    if tensions is None:
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

    push_1 = 0; push_0 = 0

    for clause in clauses:
        var_sign = None
        others = []
        for v, s in clause:
            if v == var:
                var_sign = s
            else:
                others.append((v, s))

        if var_sign is None: continue

        # P(others satisfy)
        p_others = 0.0
        for v, s in others:
            t = tensions.get(v, 0)
            if s == 1:
                p_lit = (1 + t) / 2
            else:
                p_lit = (1 - t) / 2
            p_others = 1 - (1 - p_others) * (1 - p_lit)

        # Non-redundancy weight
        weight = 1 - p_others

        if var_sign == 1:
            push_1 += weight
        else:
            push_0 += weight

    total = push_1 + push_0
    return (push_1 - push_0) / total if total > 0 else 0.0


# ============================================================
# METHOD 2: V4-estimated redundancy
# ============================================================

def v4_redundancy(clauses, n, var, n_iter=10):
    """Same as tension_redundancy but using iterative v4 tensions."""
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

    for _ in range(n_iter):
        new_t = {}
        for v in tensions:
            new_t[v] = tension_redundancy(clauses, n, v, tensions)
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)

    return tensions[var] if var in tensions else 0


# ============================================================
# METHOD 3: WalkSAT-sampled redundancy
# ============================================================

def sampled_redundancy_tension(clauses, n, var, ws_solutions):
    """
    Use WalkSAT solutions to estimate redundancy.
    For each clause: fraction of WS solutions where clause satisfied without var.
    Weight = 1 - that fraction.
    """
    if not ws_solutions: return bit_tension(clauses, n, var)

    push_1 = 0; push_0 = 0

    for clause in clauses:
        var_sign = None
        others = []
        for v, s in clause:
            if v == var: var_sign = s
            else: others.append((v, s))

        if var_sign is None: continue

        # Fraction satisfied by others across WS solutions
        sat_without = 0
        for sol in ws_solutions:
            if any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0) for v,s in others):
                sat_without += 1
        redundancy = sat_without / len(ws_solutions)
        weight = 1 - redundancy

        if var_sign == 1: push_1 += weight
        else: push_0 += weight

    total = push_1 + push_0
    return (push_1 - push_0) / total if total > 0 else 0.0


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")

    # Test all methods
    methods = {
        'standard': [],       # baseline σ
        'tension_nr': [],     # tension-estimated non-redundant
        'v4': [],             # v4 iterative
        'v4_nr': [],          # v4 + non-redundant estimation
        'oracle_nr': [],      # true non-redundant (needs solutions)
        'ws_nr_10': [],       # WalkSAT 10 samples
        'ws_nr_50': [],       # WalkSAT 50 samples
    }

    for idx, (clauses, solutions) in enumerate(instances[:60]):
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Standard tensions
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # V4 tensions
        v4_t = dict(tensions)
        for _ in range(10):
            new_t = {}
            for var in v4_t:
                new_t[var] = tension_redundancy(clauses, n, var, v4_t)
            for v in v4_t:
                v4_t[v] = 0.5*v4_t[v] + 0.5*new_t.get(v, 0)

        # WalkSAT solutions
        ws_10 = []
        ws_50 = []
        for trial in range(50):
            assignment, found = walksat(clauses, n, 200*n)
            if found:
                if len(ws_10) < 10: ws_10.append(list(assignment))
                ws_50.append(list(assignment))

        for var in range(n):
            actual = correct_val[var]

            # Standard
            pred_std = 1 if tensions[var] >= 0 else 0
            methods['standard'].append(1 if pred_std == actual else 0)

            # Tension non-redundant
            sigma_tnr = tension_redundancy(clauses, n, var, tensions)
            pred_tnr = 1 if sigma_tnr >= 0 else 0
            methods['tension_nr'].append(1 if pred_tnr == actual else 0)

            # V4
            pred_v4 = 1 if v4_t[var] >= 0 else 0
            methods['v4'].append(1 if pred_v4 == actual else 0)

            # V4 non-redundant (v4 IS already non-redundant weighted)
            methods['v4_nr'].append(1 if pred_v4 == actual else 0)

            # Oracle non-redundant
            push_1 = 0; push_0 = 0
            for ci, clause in enumerate(clauses):
                for v, s in clause:
                    if v == var:
                        others = [(vv,ss) for vv,ss in clause if vv != var]
                        sat_without = sum(1 for sol in solutions
                                         if any((ss==1 and sol[vv]==1) or (ss==-1 and sol[vv]==0)
                                               for vv,ss in others))
                        red = sat_without / len(solutions)
                        weight = 1 - red
                        if s == 1: push_1 += weight
                        else: push_0 += weight
            tot = push_1+push_0
            sigma_oracle = (push_1-push_0)/tot if tot > 0 else 0
            pred_oracle = 1 if sigma_oracle >= 0 else 0
            methods['oracle_nr'].append(1 if pred_oracle == actual else 0)

            # WalkSAT non-redundant
            if ws_10:
                sigma_ws10 = sampled_redundancy_tension(clauses, n, var, ws_10)
                pred_ws10 = 1 if sigma_ws10 >= 0 else 0
                methods['ws_nr_10'].append(1 if pred_ws10 == actual else 0)
            if ws_50:
                sigma_ws50 = sampled_redundancy_tension(clauses, n, var, ws_50)
                pred_ws50 = 1 if sigma_ws50 >= 0 else 0
                methods['ws_nr_50'].append(1 if pred_ws50 == actual else 0)

    # Results
    print("\n" + "=" * 70)
    print("PER-BIT ACCURACY: Redundancy estimation methods")
    print("=" * 70)

    print(f"\n  {'method':>15} | {'accuracy':>8} | {'vs standard':>11}")
    print("  " + "-" * 40)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    baseline = mean(methods['standard'])

    for name in ['standard', 'tension_nr', 'v4', 'v4_nr', 'oracle_nr', 'ws_nr_10', 'ws_nr_50']:
        acc = mean(methods[name])
        delta = acc - baseline
        print(f"  {name:>15} | {acc*100:>7.1f}% | {delta*100:>+10.1f}%")

    # Solver test
    print("\n" + "=" * 70)
    print("SOLVER: Does non-redundant tension solve more instances?")
    print("=" * 70)

    for method_name, tension_fn in [
        ('standard', lambda c, nn, v, f: bit_tension(c, nn, v, f)),
        ('tension_nr', lambda c, nn, v, f: tension_redundancy(c, nn, v,
            {vv: bit_tension(c, nn, vv, f) for vv in range(nn) if vv not in f})),
    ]:
        solved = 0; total_inst = 0

        for clauses, solutions in instances:
            total_inst += 1
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(tension_fn(clauses, n, v, fixed)))
                sigma = tension_fn(clauses, n, best, fixed)
                fixed[best] = 1 if sigma >= 0 else 0
            assignment = [fixed.get(v,0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                solved += 1

        print(f"  {method_name:>15}: {solved}/{total_inst} ({solved/total_inst*100:.1f}%)")
