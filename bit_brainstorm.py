"""
BRAIN EXPLOSION — Three wild ideas that might be breakthroughs.

IDEA 1: TIME REVERSAL
  Instead of fixing bits and watching forward,
  START from a random "solution" and UNFFIX bits backward.
  Which bits can we unffix without losing solvability?
  The last bit to unffix = the most essential = fix it FIRST.

IDEA 2: SHADOW SOLVING
  Create a SIMPLER problem (fewer clauses) that has the same solutions.
  Solve the simple problem. Use its solution as starting point.
  Gradually add clauses back, adjusting the solution.
  Like annealing but in CONSTRAINT space, not temperature.

IDEA 3: DUAL PROBLEM
  Instead of asking "which BITS are correct",
  ask "which CLAUSES are hardest"?
  Remove the hardest clauses. Solve the easy remaining.
  Then satisfy the hard clauses by minimal adjustment.
  The hard clauses are the "skeleton" of the problem.
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


def walksat(clauses, n, max_flips=None, start=None):
    if max_flips is None: max_flips = 100*n
    assignment = list(start) if start else [random.randint(0,1) for _ in range(n)]
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
# IDEA 1: TIME REVERSAL
# ============================================================

def solve_time_reversal(clauses, n):
    """
    1. Find a solution (WalkSAT)
    2. Try REMOVING each bit's value — which removal hurts most?
    3. The bit whose removal hurts least = least essential = fix last
    4. Build ordering from "most essential" to "least essential"
    5. Use this ordering for crystallization on a FRESH instance

    Actually: use WalkSAT solution to determine OPTIMAL ordering,
    then apply that ordering's tension-guided crystallization.
    """
    # Find a solution
    assignment, found = walksat(clauses, n, max_flips=500*n)
    if not found:
        # Fallback to tension
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        assignment = [fixed.get(v,0) for v in range(n)]
        return assignment, evaluate(clauses, assignment) == len(clauses)

    # We have a solution. Now determine essentiality of each bit.
    essentiality = {}
    for var in range(n):
        # How many clauses break if we flip this bit?
        flipped = list(assignment)
        flipped[var] = 1 - flipped[var]
        broken = len(clauses) - evaluate(clauses, flipped)
        essentiality[var] = broken

    # Crystallize: most essential first, using TENSION direction (not solution)
    order = sorted(range(n), key=lambda v: -essentiality[v])
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

    result = [fixed.get(v,0) for v in range(n)]
    return result, evaluate(clauses, result) == len(clauses)


# ============================================================
# IDEA 2: SHADOW SOLVING (constraint annealing)
# ============================================================

def solve_shadow(clauses, n):
    """
    1. Start with HALF the clauses (random subset) — easy problem
    2. Solve it (tension crystallization)
    3. Add more clauses gradually
    4. After each addition, adjust solution with WalkSAT
    """
    m = len(clauses)
    indices = list(range(m))
    random.shuffle(indices)

    # Phase 1: solve easy subset
    n_start = m // 3
    easy_clauses = [clauses[i] for i in indices[:n_start]]

    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(easy_clauses, n, v, fixed)))
        sigma = bit_tension(easy_clauses, n, best, fixed)
        fixed[best] = 1 if sigma >= 0 else 0
    assignment = [fixed.get(v,0) for v in range(n)]

    # Phase 2: gradually add clauses, adjust
    step_size = max(1, (m - n_start) // 5)
    for i in range(n_start, m, step_size):
        current_clauses = [clauses[j] for j in indices[:min(i + step_size, m)]]
        assignment, found = walksat(current_clauses, n, max_flips=50*n, start=assignment)
        if not found:
            # If stuck, try harder
            assignment, found = walksat(current_clauses, n, max_flips=200*n, start=assignment)

    # Final check on ALL clauses
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# IDEA 3: DUAL PROBLEM (clause difficulty)
# ============================================================

def clause_difficulty(clauses, n, ci):
    """How hard is this clause to satisfy?
    Based on tensions of its variables."""
    clause = clauses[ci]
    # For each literal: probability it satisfies the clause
    prob_sat = 0
    for v, s in clause:
        sigma = bit_tension(clauses, n, v)
        if s == 1:
            p = (1 + sigma) / 2  # prob var=1
        else:
            p = (1 - sigma) / 2  # prob var=0
        prob_sat = 1 - (1 - prob_sat) * (1 - p)
    return 1 - prob_sat  # difficulty = prob NOT satisfied


def solve_dual(clauses, n):
    """
    1. Rank clauses by difficulty
    2. Remove hardest 20%
    3. Solve easy 80% by tension
    4. Adjust to satisfy hard 20% via WalkSAT
    """
    m = len(clauses)
    difficulties = [(ci, clause_difficulty(clauses, n, ci)) for ci in range(m)]
    difficulties.sort(key=lambda x: x[1])

    # Easy clauses (80%)
    n_easy = int(m * 0.8)
    easy_indices = [ci for ci, d in difficulties[:n_easy]]
    easy_clauses = [clauses[ci] for ci in easy_indices]

    # Solve easy part
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(easy_clauses, n, v, fixed)))
        sigma = bit_tension(easy_clauses, n, best, fixed)
        fixed[best] = 1 if sigma >= 0 else 0
    assignment = [fixed.get(v,0) for v in range(n)]

    # Adjust for hard clauses via WalkSAT on full problem
    assignment, found = walksat(clauses, n, max_flips=200*n, start=assignment)

    return assignment, found


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("BRAIN EXPLOSION: Three wild ideas")
    print("=" * 70)

    solvers = {
        'tension':       None,  # baseline
        'time_reversal': solve_time_reversal,
        'shadow':        solve_shadow,
        'dual':          solve_dual,
    }

    for ratio in [3.5, 4.0, 4.27]:
        results = {name: 0 for name in solvers}
        total = 0

        for seed in range(150):
            clauses = random_3sat(12, int(ratio*12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue
            total += 1

            # Baseline
            fixed = {}
            for step in range(12):
                unfixed = [v for v in range(12) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, 12, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, 12, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(12)]) == len(clauses):
                results['tension'] += 1

            for name, solver in solvers.items():
                if solver is None: continue
                _, success = solver(clauses, 12)
                if success: results[name] += 1

        print(f"\n  ratio={ratio} ({total} instances):")
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            pct = results[name] / total * 100
            delta = pct - results['tension'] / total * 100
            marker = f" (+{delta:.1f}%)" if delta > 0 else (f" ({delta:.1f}%)" if delta < 0 else "")
            print(f"    {name:>16}: {results[name]:>4}/{total} ({pct:.1f}%){marker}")

    # Scaling test for winners
    print("\n" + "=" * 70)
    print("SCALING: Best wild ideas at larger n")
    print("=" * 70)

    for n_test in [12, 16, 20, 30]:
        results = {'tension': 0, 'shadow': 0, 'dual': 0, 'time_reversal': 0}
        total = 0
        t0 = time.time()

        for seed in range(50):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed+60000)
            total += 1

            # Tension
            fixed = {}
            for step in range(n_test):
                unfixed = [v for v in range(n_test) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n_test, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n_test, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n_test)]) == len(clauses):
                results['tension'] += 1

            _, s = solve_shadow(clauses, n_test)
            if s: results['shadow'] += 1

            _, s = solve_dual(clauses, n_test)
            if s: results['dual'] += 1

            _, s = solve_time_reversal(clauses, n_test)
            if s: results['time_reversal'] += 1

        t1 = time.time()
        print(f"\n  n={n_test} ({(t1-t0)*1000:.0f}ms total):")
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            print(f"    {name:>16}: {results[name]:>3}/{total} ({results[name]/total*100:.1f}%)")
