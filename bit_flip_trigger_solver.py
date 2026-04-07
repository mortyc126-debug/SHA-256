"""
FLIP TRIGGER SOLVER — Using the strongest discriminator (1.97×)

Strategy: compute flip_trigger fraction for each bit.
Fragile bits (high flip triggers) → distrust tension, use sampling.
Robust bits (low flip triggers) → trust tension, crystallize.

Also: test if flip triggers scale with n.
"""

import random
import time
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
    """Fraction of neighbors that can flip σ's sign."""
    if fixed is None: fixed = {}
    sigma_base = bit_tension(clauses, n, var, fixed)
    base_sign = 1 if sigma_base >= 0 else -1

    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var and v not in fixed:
                    neighbors.add(v)

    if not neighbors:
        return 0.0

    triggers = 0
    for nb in neighbors:
        for val in [0, 1]:
            test_fixed = dict(fixed)
            test_fixed[nb] = val
            s = bit_tension(clauses, n, var, test_fixed)
            if (1 if s >= 0 else -1) != base_sign:
                triggers += 1
                break  # one flip is enough

    return triggers / len(neighbors)


def walksat(clauses, n, max_flips=None):
    if max_flips is None: max_flips = 50 * n
    assignment = [random.randint(0, 1) for _ in range(n)]
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
        if random.random() < 0.3:
            v, s = random.choice(clauses[ci])
            assignment[v] = 1 - assignment[v]
        else:
            best_var = None; best_break = float('inf')
            for v, s in clauses[ci]:
                assignment[v] = 1 - assignment[v]
                breaks = sum(1 for cj in range(m) if not any(
                    (ss==1 and assignment[vv]==1) or (ss==-1 and assignment[vv]==0)
                    for vv, ss in clauses[cj]))
                assignment[v] = 1 - assignment[v]
                if breaks < best_break: best_break = breaks; best_var = v
            if best_var is not None: assignment[best_var] = 1 - assignment[best_var]
    return assignment, False


# ============================================================
# SOLVER: Fragility-aware hybrid
# ============================================================

def solve_fragility_hybrid(clauses, n, fragility_threshold=0.25):
    """
    1. Compute fragility (flip triggers) for each bit
    2. Robust bits (fragility < threshold): crystallize by tension
    3. Fragile bits: try WalkSAT sampling + voting
    """
    # Compute fragilities
    fragilities = {}
    tensions = {}
    for var in range(n):
        fragilities[var] = compute_flip_triggers(clauses, n, var)
        tensions[var] = bit_tension(clauses, n, var)

    robust = [(v, tensions[v]) for v in range(n) if fragilities[v] < fragility_threshold]
    fragile = [v for v in range(n) if fragilities[v] >= fragility_threshold]

    # Phase 1: crystallize robust bits
    robust.sort(key=lambda x: -abs(x[1]))
    fixed = {}
    for var, sigma in robust:
        # Recompute tension with current fixed
        t = bit_tension(clauses, n, var, fixed)
        fixed[var] = 1 if t >= 0 else 0

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
                    val = 1 if s == 1 else 0
                    if v not in fixed:
                        fixed[v] = val; changed = True

    # Phase 2: for remaining fragile bits, try WalkSAT sampling
    remaining = [v for v in range(n) if v not in fixed]

    if not remaining:
        assignment = [fixed.get(v, 0) for v in range(n)]
        return assignment, evaluate(clauses, assignment) == len(clauses), 'crystallized'

    # WalkSAT sampling with partial fixation
    votes = {v: [0, 0] for v in remaining}
    n_found = 0

    for _ in range(30):
        # Start WalkSAT from partially fixed state
        assignment = [0] * n
        for v, val in fixed.items():
            assignment[v] = val
        for v in remaining:
            assignment[v] = random.randint(0, 1)

        # WalkSAT on remaining bits only
        for flip in range(200 * n):
            unsat = []
            for ci, clause in enumerate(clauses):
                satisfied = False
                for v, s in clause:
                    if (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0):
                        satisfied = True; break
                if not satisfied: unsat.append(ci)
            if not unsat:
                n_found += 1
                for v in remaining:
                    votes[v][assignment[v]] += 1
                break
            ci = random.choice(unsat)
            # Only flip remaining bits
            flippable = [(v, s) for v, s in clauses[ci] if v in remaining or v not in fixed]
            if not flippable: continue
            if random.random() < 0.3:
                v, s = random.choice(flippable)
                if v not in fixed: assignment[v] = 1 - assignment[v]
            else:
                best_var = None; best_break = float('inf')
                for v, s in flippable:
                    if v in fixed: continue
                    assignment[v] = 1 - assignment[v]
                    breaks = sum(1 for cl in clauses if not any(
                        (ss==1 and assignment[vv]==1) or (ss==-1 and assignment[vv]==0)
                        for vv, ss in cl))
                    assignment[v] = 1 - assignment[v]
                    if breaks < best_break: best_break = breaks; best_var = v
                if best_var is not None: assignment[best_var] = 1 - assignment[best_var]

    # Vote for fragile bits
    for v in remaining:
        if votes[v][0] + votes[v][1] > 0:
            fixed[v] = 1 if votes[v][1] > votes[v][0] else 0
        else:
            # Fallback to tension
            fixed[v] = 1 if bit_tension(clauses, n, v, fixed) >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses), f'hybrid({n_found}found)'


# ============================================================
# SOLVER: Two-dimensional filter (|σ| × fragility)
# ============================================================

def solve_2d_filter(clauses, n):
    """
    Confidence = |σ| × (1 - fragility).
    High confidence = high tension AND low fragility.
    Fix in order of confidence.
    """
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        candidates = []
        for var in unfixed:
            sigma = bit_tension(clauses, n, var, fixed)
            frag = compute_flip_triggers(clauses, n, var, fixed)
            confidence = abs(sigma) * (1 - frag)
            candidates.append((var, sigma, confidence))

        candidates.sort(key=lambda c: -c[2])
        best_var, best_sigma, _ = candidates[0]
        fixed[best_var] = 1 if best_sigma >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    # --- Q1: Flip triggers in solver ---
    print("=" * 70)
    print("Q1: FLIP TRIGGER SOLVERS vs BASELINES")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        results = {
            'tension': 0, '2d_filter': 0,
            'hybrid_0.20': 0, 'hybrid_0.25': 0, 'hybrid_0.30': 0,
        }
        total = 0

        for seed in range(150):
            clauses = random_3sat(12, int(ratio*12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue
            total += 1

            # Baseline tension
            fixed = {}
            for step in range(12):
                unfixed = [v for v in range(12) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, 12, v, fixed)))
                sigma = bit_tension(clauses, 12, best, fixed)
                fixed[best] = 1 if sigma >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(12)]) == len(clauses):
                results['tension'] += 1

            # 2D filter
            _, success = solve_2d_filter(clauses, 12)
            if success: results['2d_filter'] += 1

            # Hybrid at different thresholds
            for thresh in [0.20, 0.25, 0.30]:
                _, success, _ = solve_fragility_hybrid(clauses, 12, thresh)
                if success: results[f'hybrid_{thresh:.2f}'] += 1

        print(f"\n  ratio={ratio} ({total} instances):")
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            pct = results[name] / total * 100
            print(f"    {name:>15}: {results[name]:>4}/{total} ({pct:.1f}%)")

    # --- Q7: Does flip_trigger ratio hold at larger n? ---
    print("\n" + "=" * 70)
    print("Q7: FLIP TRIGGER RATIO vs n (SCALING TEST)")
    print("=" * 70)

    print(f"\n  {'n':>4} | {'correct FT':>10} | {'wrong FT':>10} | "
          f"{'ratio':>7} | {'instances':>9}")
    print("  " + "-" * 55)

    for n_test in [10, 12, 14, 16, 20]:
        correct_fts = []
        wrong_fts = []
        n_inst = 0

        n_trials = 100 if n_test <= 16 else 50
        for seed in range(n_trials):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed+50000)

            if n_test <= 16:
                solutions = find_solutions(clauses, n_test)
                if not solutions: continue
            else:
                continue  # skip n>16 for ground truth

            n_inst += 1
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n_test)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            for var in range(n_test):
                sigma = bit_tension(clauses, n_test, var)
                pred = 1 if sigma >= 0 else 0
                ft = compute_flip_triggers(clauses, n_test, var)

                if pred == correct_val[var]:
                    correct_fts.append(ft)
                else:
                    wrong_fts.append(ft)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        c = mean(correct_fts)
        w = mean(wrong_fts)
        ratio = w / c if c > 0 else 0

        print(f"  {n_test:>4} | {c:>10.4f} | {w:>10.4f} | {ratio:>7.2f} | {n_inst:>9}")
