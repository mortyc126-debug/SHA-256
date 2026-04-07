"""
BIT CORRECTION — Can we fix wrong bits without knowing the answer?

We know:
- WHICH bits are fragile (flip triggers 2×)
- That wrong fixes are "silent poison" (no visible disturbance)
- That correct fixes AMPLIFY signal

Strategy ideas:
1. INVERSION TEST: fix bit one way, measure system health. Fix other way,
   measure again. Pick the healthier fixation.
2. CONSENSUS: fix fragile bit both ways, run crystallization from each,
   see which produces a valid solution more often.
3. IMMUNE RESPONSE: after fixing, check if OTHER bits become MORE fragile.
   If yes → we probably poisoned. Undo.
4. SOLUTION PROBE: fix fragile bit, try WalkSAT. If WalkSAT finds
   solution → fixation was probably correct.
5. ENTROPY PROBE: fix both ways, count solutions (approximate).
   More solutions → more likely correct.
"""

import random
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


def compute_flip_triggers(clauses, n, var, fixed=None):
    if fixed is None: fixed = {}
    sigma_base = bit_tension(clauses, n, var, fixed)
    base_sign = 1 if sigma_base >= 0 else -1
    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var and v not in fixed: neighbors.add(v)
    if not neighbors: return 0.0
    triggers = 0
    for nb in neighbors:
        for val in [0, 1]:
            tf = dict(fixed); tf[nb] = val
            s = bit_tension(clauses, n, var, tf)
            if (1 if s >= 0 else -1) != base_sign:
                triggers += 1; break
    return triggers / len(neighbors)


def walksat_quick(clauses, n, fixed, max_flips=None):
    """WalkSAT starting from partial fixation."""
    if max_flips is None: max_flips = 100 * n
    assignment = [0] * n
    free_vars = []
    for v in range(n):
        if v in fixed:
            assignment[v] = fixed[v]
        else:
            assignment[v] = random.randint(0, 1)
            free_vars.append(v)

    if not free_vars:
        return assignment, evaluate(clauses, assignment) == len(clauses)

    free_set = set(free_vars)
    m = len(clauses)

    for flip in range(max_flips):
        unsat = []
        for ci in range(m):
            satisfied = False
            for v, s in clauses[ci]:
                if (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0):
                    satisfied = True; break
            if not satisfied: unsat.append(ci)
        if not unsat: return assignment, True

        ci = random.choice(unsat)
        flippable = [v for v, s in clauses[ci] if v in free_set]
        if not flippable: continue

        if random.random() < 0.3:
            v = random.choice(flippable)
            assignment[v] = 1 - assignment[v]
        else:
            best_v = None; best_b = float('inf')
            for v in flippable:
                assignment[v] = 1 - assignment[v]
                b = sum(1 for cj in range(m) if not any(
                    (ss==1 and assignment[vv]==1) or (ss==-1 and assignment[vv]==0)
                    for vv, ss in clauses[cj]))
                assignment[v] = 1 - assignment[v]
                if b < best_b: best_b = b; best_v = v
            if best_v is not None: assignment[best_v] = 1 - assignment[best_v]

    return assignment, False


# ============================================================
# CORRECTION 1: Health test — fix both ways, pick healthier
# ============================================================

def health_score(clauses, n, fixed):
    """
    System health after fixation:
    - Higher average |σ| of remaining = healthier (more confident)
    - Fewer fragile bits = healthier
    - More unit propagations possible = healthier
    """
    unfixed = [v for v in range(n) if v not in fixed]
    if not unfixed: return 0

    tensions = [abs(bit_tension(clauses, n, v, fixed)) for v in unfixed]
    avg_tension = sum(tensions) / len(tensions)

    # Unit propagation count
    test_fixed = dict(fixed)
    up_count = 0
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            satisfied = False; free = []
            for v, s in clause:
                if v in test_fixed:
                    if (s==1 and test_fixed[v]==1) or (s==-1 and test_fixed[v]==0):
                        satisfied = True; break
                else: free.append((v,s))
            if not satisfied and len(free) == 1:
                v, s = free[0]
                val = 1 if s == 1 else 0
                if v not in test_fixed:
                    test_fixed[v] = val; changed = True; up_count += 1

    return avg_tension + up_count * 0.1


def solve_health_test(clauses, n):
    """For each bit (most fragile first): try both values, pick healthier."""
    fragilities = {v: compute_flip_triggers(clauses, n, v) for v in range(n)}
    order = sorted(range(n), key=lambda v: -fragilities[v])

    fixed = {}
    for var in order:
        if var in fixed: continue

        # Try both values
        f0 = dict(fixed); f0[var] = 0
        f1 = dict(fixed); f1[var] = 1
        h0 = health_score(clauses, n, f0)
        h1 = health_score(clauses, n, f1)

        fixed[var] = 1 if h1 > h0 else 0

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
                    if v not in fixed:
                        fixed[v] = 1 if s == 1 else 0; changed = True

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# CORRECTION 2: Solution probe — fix, try WalkSAT, see if solvable
# ============================================================

def solve_solution_probe(clauses, n, n_probes=5):
    """
    For fragile bits: fix both ways, probe with WalkSAT.
    If one way finds solutions and other doesn't → choose the solvable one.
    """
    fragilities = {v: compute_flip_triggers(clauses, n, v) for v in range(n)}

    # Start with robust bits by tension
    fixed = {}
    robust = [(v, bit_tension(clauses, n, v)) for v in range(n) if fragilities[v] < 0.2]
    robust.sort(key=lambda x: -abs(x[1]))

    for var, sigma in robust:
        if var in fixed: continue
        t = bit_tension(clauses, n, var, fixed)
        fixed[var] = 1 if t >= 0 else 0

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

    # For fragile bits: probe
    remaining = [v for v in range(n) if v not in fixed]
    remaining.sort(key=lambda v: -fragilities[v])

    for var in remaining:
        if var in fixed: continue

        score = [0, 0]
        for val in [0, 1]:
            test_fixed = dict(fixed); test_fixed[var] = val
            for _ in range(n_probes):
                _, found = walksat_quick(clauses, n, test_fixed, max_flips=50*n)
                if found: score[val] += 1

        if score[0] + score[1] > 0:
            fixed[var] = 1 if score[1] > score[0] else 0
        else:
            t = bit_tension(clauses, n, var, fixed)
            fixed[var] = 1 if t >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# CORRECTION 3: Immune response — detect poison, undo
# ============================================================

def solve_immune(clauses, n):
    """
    Crystallize normally but after each fix:
    check if average fragility of remaining bits INCREASED.
    If yes → undo (immune response).
    """
    fixed = {}
    history = []

    order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

    for var in order:
        if var in fixed: continue

        sigma = bit_tension(clauses, n, var, fixed)
        val = 1 if sigma >= 0 else 0

        # Measure fragility before
        unfixed_before = [v for v in range(n) if v not in fixed and v != var]
        if unfixed_before:
            frag_before = sum(compute_flip_triggers(clauses, n, v, fixed)
                            for v in unfixed_before[:5]) / min(5, len(unfixed_before))
        else:
            frag_before = 0

        fixed[var] = val

        # Measure fragility after
        unfixed_after = [v for v in range(n) if v not in fixed]
        if unfixed_after:
            frag_after = sum(compute_flip_triggers(clauses, n, v, fixed)
                           for v in unfixed_after[:5]) / min(5, len(unfixed_after))
        else:
            frag_after = 0

        # If fragility increased significantly → immune response: try other value
        if frag_after > frag_before + 0.05:
            fixed[var] = 1 - val  # flip
            history.append((var, 1-val, 'flipped'))
        else:
            history.append((var, val, 'kept'))

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# CORRECTION 4: Tension + consensus from multiple crystallizations
# ============================================================

def solve_multi_crystal(clauses, n, n_runs=15):
    """
    Run crystallization multiple times with different orderings.
    For each bit: vote across all runs.
    For fragile bits: weight votes by whether the run succeeded (found solution).
    """
    votes = [[0, 0] for _ in range(n)]
    solved_votes = [[0, 0] for _ in range(n)]

    for run in range(n_runs):
        fixed = {}
        order = list(range(n))
        random.shuffle(order)
        # Bias: sort by |tension| with noise
        order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.1)))

        for var in order:
            if var in fixed: continue
            sigma = bit_tension(clauses, n, var, fixed)
            val = 1 if sigma >= 0 else 0
            fixed[var] = val

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

        assignment = [fixed.get(v, 0) for v in range(n)]
        solved = evaluate(clauses, assignment) == len(clauses)

        for v in range(n):
            votes[v][assignment[v]] += 1
            if solved:
                solved_votes[v][assignment[v]] += 1

    # Final: prefer solved-run votes, fallback to all votes
    assignment = []
    for v in range(n):
        if solved_votes[v][0] + solved_votes[v][1] > 0:
            assignment.append(1 if solved_votes[v][1] > solved_votes[v][0] else 0)
        else:
            assignment.append(1 if votes[v][1] > votes[v][0] else 0)

    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("BIT CORRECTION: Can we fix wrong bits?")
    print("=" * 70)

    solvers = {
        'tension':       lambda c, n: (None, eval_tension(c, n)),
        'health_test':   lambda c, n: solve_health_test(c, n),
        'solution_probe': lambda c, n: solve_solution_probe(c, n, 3),
        'immune':        lambda c, n: solve_immune(c, n),
        'multi_crystal': lambda c, n: solve_multi_crystal(c, n, 15),
    }

    def eval_tension(clauses, n):
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            sigma = bit_tension(clauses, n, best, fixed)
            fixed[best] = 1 if sigma >= 0 else 0
        return evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses)

    for ratio in [3.5, 4.0, 4.27]:
        results = {name: 0 for name in solvers}
        total = 0

        for seed in range(150):
            clauses = random_3sat(12, int(ratio*12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue
            total += 1

            for name, solver in solvers.items():
                _, success = solver(clauses, 12)
                if success: results[name] += 1

        print(f"\n  ratio={ratio} ({total} instances):")
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            pct = results[name] / total * 100
            delta = pct - results['tension'] / total * 100
            marker = f" (+{delta:.1f}%)" if delta > 0 else (f" ({delta:.1f}%)" if delta < 0 else "")
            print(f"    {name:>16}: {results[name]:>4}/{total} ({pct:.1f}%){marker}")

    # Per-bit accuracy of best methods
    print("\n" + "=" * 70)
    print("PER-BIT ACCURACY of correction methods (ratio=4.27)")
    print("=" * 70)

    for method_name in ['health_test', 'immune', 'multi_crystal']:
        correct = 0; total = 0
        for seed in range(150):
            clauses = random_3sat(12, int(4.27*12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(12)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            if method_name == 'health_test':
                assignment, _ = solve_health_test(clauses, 12)
            elif method_name == 'immune':
                assignment, _ = solve_immune(clauses, 12)
            elif method_name == 'multi_crystal':
                assignment, _ = solve_multi_crystal(clauses, 12, 15)

            for v in range(12):
                total += 1
                if assignment[v] == correct_val[v]: correct += 1

        print(f"  {method_name:>16}: {correct/total*100:.1f}% per-bit accuracy")
