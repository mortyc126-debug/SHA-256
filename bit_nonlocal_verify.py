"""
NON-LOCAL VERIFICATION: Test across ALL seed ranges + combine with best methods.
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


def discover_nonlocal(clauses, n):
    sign_adj = [[0.0]*n for _ in range(n)]
    for clause in clauses:
        lits = [(v,s) for v,s in clause]
        for a in range(len(lits)):
            for b in range(a+1, len(lits)):
                vi,si = lits[a]; vj,sj = lits[b]
                sw = -1.0 if si==sj else 1.0
                sign_adj[vi][vj] += sw; sign_adj[vj][vi] += sw

    adj_set = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(n):
            if sign_adj[i][j] != 0: adj_set[i].add(j)

    constraints = []
    for i in range(n):
        for j in range(i+1, n):
            if j in adj_set[i]: continue
            intermediaries = adj_set[i] & adj_set[j]
            if not intermediaries: continue
            total_sign = 0; n_paths = 0
            for k in intermediaries:
                ps = sign_adj[i][k] * sign_adj[k][j]
                if abs(ps) > 0: total_sign += 1 if ps > 0 else -1; n_paths += 1
            if n_paths >= 2 and abs(total_sign) >= 2:
                constraints.append((i, j, total_sign > 0, abs(total_sign)/n_paths))
    return constraints


def solve_nonlocal(clauses, n):
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
    nl = discover_nonlocal(clauses, n)

    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        # Enhanced tension with non-local
        scores = {}
        for var in unfixed:
            sigma = bit_tension(clauses, n, var, fixed)
            nl_push = 0; nl_count = 0
            for (i,j, is_clone, strength) in nl:
                other = j if i == var else (i if j == var else None)
                if other is None: continue
                ot = tensions.get(other, 0)
                if is_clone: nl_push += ot * strength
                else: nl_push -= ot * strength
                nl_count += 1
            if nl_count > 0: nl_push /= nl_count
            scores[var] = sigma * 0.7 + nl_push * 0.3

        best = max(unfixed, key=lambda v: abs(scores.get(v, 0)))
        fixed[best] = 1 if scores.get(best, 0) >= 0 else 0

        # Update tensions
        for v in unfixed:
            if v != best:
                tensions[v] = bit_tension(clauses, n, v, fixed)

    assignment = [fixed.get(v,0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


def solve_tension(clauses, n):
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
    assignment = [fixed.get(v,0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


def solve_nonlocal_dpll(clauses, n, max_calls=50000):
    """DPLL with non-local-enhanced branching."""
    nl = discover_nonlocal(clauses, n)
    calls = [0]

    def unit_prop(fixed):
        f = dict(fixed); changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False; free = []
                for v, s in clause:
                    if v in f:
                        if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                            satisfied = True; break
                    else: free.append((v,s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    if v not in f: f[v] = 1 if s==1 else 0; changed = True
                if not satisfied and len(free) == 0: return f, True
        return f, False

    def dpll(fixed):
        calls[0] += 1
        if calls[0] > max_calls: return None
        fixed, conflict = unit_prop(fixed)
        if conflict: return None
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                return [fixed.get(v,0) for v in range(n)]
            return None

        # Non-local enhanced variable + value selection
        tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}
        scores = {}
        for var in unfixed:
            nl_push = 0; nl_count = 0
            for (i,j,is_clone,strength) in nl:
                other = j if i==var else (i if j==var else None)
                if other is None or other not in tensions: continue
                if is_clone: nl_push += tensions[other]*strength
                else: nl_push -= tensions[other]*strength
                nl_count += 1
            if nl_count > 0: nl_push /= nl_count
            scores[var] = tensions[var]*0.7 + nl_push*0.3

        best = max(unfixed, key=lambda v: abs(scores.get(v,0)))
        first_val = 1 if scores.get(best,0) >= 0 else 0

        f = dict(fixed); f[best] = first_val
        result = dpll(f)
        if result: return result

        f = dict(fixed); f[best] = 1-first_val
        return dpll(f)

    result = dpll({})
    return result, result is not None, calls[0]


# ============================================================
# BENCHMARK ACROSS MULTIPLE SEED RANGES
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("NON-LOCAL VERIFICATION: Multiple seed ranges")
    print("=" * 70)

    for n in [12, 16, 20]:
        total_tension = 0; total_nonlocal = 0; total_dpll_nl = 0; grand_total = 0

        for seed_base in [0, 1000, 5000, 8000000, 3000000]:
            t_solved = 0; nl_solved = 0; dpll_solved = 0; total = 0

            n_inst = 50 if n <= 16 else 25
            for seed in range(n_inst):
                clauses = random_3sat(n, int(4.27*n), seed=seed+seed_base)
                if n <= 16:
                    solutions = find_solutions(clauses, n)
                    if not solutions: continue
                total += 1

                _, s1 = solve_tension(clauses, n)
                if s1: t_solved += 1

                _, s2 = solve_nonlocal(clauses, n)
                if s2: nl_solved += 1

                r, s3, _ = solve_nonlocal_dpll(clauses, n, 5000)
                if s3: dpll_solved += 1

            total_tension += t_solved
            total_nonlocal += nl_solved
            total_dpll_nl += dpll_solved
            grand_total += total

        print(f"\n  n={n} ({grand_total} instances across 5 seed ranges):")
        print(f"    tension:          {total_tension}/{grand_total} ({total_tension/grand_total*100:.1f}%)")
        print(f"    nonlocal:         {total_nonlocal}/{grand_total} ({total_nonlocal/grand_total*100:.1f}%)")
        print(f"    DPLL+nonlocal:    {total_dpll_nl}/{grand_total} ({total_dpll_nl/grand_total*100:.1f}%)")
        print(f"    NL improvement:   {(total_nonlocal-total_tension)/grand_total*100:+.1f}%")
        print(f"    DPLL+NL improve:  {(total_dpll_nl-total_tension)/grand_total*100:+.1f}%")
