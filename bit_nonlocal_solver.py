"""
NON-LOCAL SOLVER: Exploit the 73% holographic correlations.

Distance-2 bits: solution correlation = 0.354, tension transmission = 0.000.
73% of these correlations are NON-LOCAL (don't travel through paths).

KEY IDEA: Use distance-2 correlations as ADDITIONAL CONSTRAINTS.
If bits i and j are correlated at distance 2 (through the hidden network),
add a SOFT CONSTRAINT: "i and j should agree (or disagree)."

This is like discovering EXTRA CLAUSES that aren't in the formula
but ARE implied by the holographic structure.
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
# DISCOVER NON-LOCAL CONSTRAINTS
# ============================================================

def discover_nonlocal(clauses, n):
    """
    For each pair at distance 2: compute IMPLIED relationship
    from the clause structure (through the signed Laplacian path).

    Path i → k → j: sign(i,k) × sign(k,j) implies sign(i,j).
    Multiple paths may agree or disagree.
    Strong agreement = strong non-local constraint.
    """
    # Build signed adjacency
    sign_adj = [[0.0]*n for _ in range(n)]
    for clause in clauses:
        lits = [(v,s) for v,s in clause]
        for a in range(len(lits)):
            for b in range(a+1, len(lits)):
                vi,si = lits[a]; vj,sj = lits[b]
                # INVERTED (L15): same signs → anti-clone → -1
                sign_val = -1.0 if si == sj else 1.0
                sign_adj[vi][vj] += sign_val
                sign_adj[vj][vi] += sign_val

    # Distance-2 implied signs: via intermediate nodes
    nonlocal_constraints = []

    adj_set = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(n):
            if sign_adj[i][j] != 0:
                adj_set[i].add(j)

    for i in range(n):
        for j in range(i+1, n):
            if j in adj_set[i]: continue  # skip distance-1

            # Find intermediaries
            intermediaries = adj_set[i] & adj_set[j]
            if not intermediaries: continue

            # Accumulate path-implied signs
            total_sign = 0
            n_paths = 0
            for k in intermediaries:
                # sign(i,k) × sign(k,j) = implied sign(i,j)
                path_sign = sign_adj[i][k] * sign_adj[k][j]
                # Normalize
                if abs(path_sign) > 0:
                    total_sign += 1 if path_sign > 0 else -1
                    n_paths += 1

            if n_paths >= 2 and abs(total_sign) >= 2:
                # Strong consensus among paths
                implied_clone = total_sign > 0
                strength = abs(total_sign) / n_paths
                nonlocal_constraints.append((i, j, implied_clone, strength))

    return nonlocal_constraints


# ============================================================
# NON-LOCAL ENHANCED TENSION
# ============================================================

def nonlocal_tension(clauses, n, var, tensions, nonlocal_constraints):
    """
    Enhanced tension: standard σ + non-local constraint influence.

    For each non-local constraint involving var:
    If (var, other) should be clones → push var toward other's tension
    If anti-clones → push var opposite to other's tension
    """
    sigma = tensions[var]

    # Non-local influence
    nl_push = 0.0; nl_count = 0
    for (i, j, is_clone, strength) in nonlocal_constraints:
        if i == var:
            other = j
        elif j == var:
            other = i
        else:
            continue

        other_dir = tensions[other]
        if is_clone:
            nl_push += other_dir * strength
        else:
            nl_push -= other_dir * strength
        nl_count += 1

    if nl_count > 0:
        nl_push /= nl_count

    # Combined: tension + non-local
    combined = sigma * 0.7 + nl_push * 0.3

    return combined


# ============================================================
# NON-LOCAL SOLVER
# ============================================================

def solve_nonlocal(clauses, n):
    """
    Phase 1: Discover non-local constraints
    Phase 2: Crystallize using non-local-enhanced tension
    """
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
    nl_constraints = discover_nonlocal(clauses, n)

    # Crystallize
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        # Rank by enhanced tension
        best_var = max(unfixed,
                      key=lambda v: abs(nonlocal_tension(clauses, n, v, tensions, nl_constraints)))
        nl_sigma = nonlocal_tension(clauses, n, best_var, tensions, nl_constraints)
        fixed[best_var] = 1 if nl_sigma >= 0 else 0

        # Update tensions with fixed context
        for v in unfixed:
            if v != best_var:
                tensions[v] = bit_tension(clauses, n, v, fixed)

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses), len(nl_constraints)


# ============================================================
# ITERATIVE NON-LOCAL
# ============================================================

def solve_iterative_nonlocal(clauses, n, n_iter=5):
    """
    Iterate: compute non-local constraints from current tensions,
    update tensions, recompute constraints, repeat.
    """
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

    for iteration in range(n_iter):
        nl_constraints = discover_nonlocal(clauses, n)

        # Update tensions with non-local influence
        new_t = {}
        for var in range(n):
            new_t[var] = nonlocal_tension(clauses, n, var, tensions, nl_constraints)
        tensions = new_t

    # Crystallize with final tensions
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(tensions.get(v, 0)))
        fixed[best] = 1 if tensions.get(best, 0) >= 0 else 0

        # Update with fixed context
        for v in unfixed:
            if v != best:
                tensions[v] = bit_tension(clauses, n, v, fixed)

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    import time

    print("=" * 70)
    print("NON-LOCAL SOLVER: Using holographic correlations")
    print("=" * 70)

    for n in [12, 16, 20]:
        results = {'tension': 0, 'nonlocal': 0, 'iter_nonlocal': 0, 'total': 0}
        avg_constraints = []

        n_inst = 100 if n <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+8000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            results['total'] += 1

            # Standard tension
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v)))
                fixed[best] = 1 if bit_tension(clauses, n, best) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                results['tension'] += 1

            # Non-local solver
            _, success, n_constr = solve_nonlocal(clauses, n)
            avg_constraints.append(n_constr)
            if success: results['nonlocal'] += 1

            # Iterative non-local
            _, success = solve_iterative_nonlocal(clauses, n, 5)
            if success: results['iter_nonlocal'] += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        t = results['total']
        print(f"\n  n={n} ({t} instances, avg {mean(avg_constraints):.1f} non-local constraints):")
        for name in ['tension', 'nonlocal', 'iter_nonlocal']:
            pct = results[name]/t*100 if t > 0 else 0
            delta = pct - results['tension']/t*100 if t > 0 else 0
            print(f"    {name:>15}: {results[name]:>3}/{t} ({pct:>5.1f}%) {delta:>+6.1f}%")
