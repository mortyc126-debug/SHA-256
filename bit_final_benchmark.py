"""
FINAL BENCHMARK: All our best solvers head-to-head.

1. Standard tension (baseline)
2. DPLL + tension (our early best)
3. DPLL + nonlocal (our latest)
4. Native solver (Phase 1-5 from theory)
5. Clone reduction (from clone structure)
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


def unit_prop(clauses, n, fixed):
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
            ts = 0; np_ = 0
            for k in intermediaries:
                ps = sign_adj[i][k]*sign_adj[k][j]
                if abs(ps) > 0: ts += 1 if ps > 0 else -1; np_ += 1
            if np_ >= 2 and abs(ts) >= 2:
                constraints.append((i,j,ts>0,abs(ts)/np_))
    return constraints


# ============================================================
# SOLVERS
# ============================================================

def solve_tension(clauses, n):
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
    a = [fixed.get(v,0) for v in range(n)]
    return a, evaluate(clauses, a) == len(clauses)


def dpll_solve(clauses, n, use_nonlocal=False, max_calls=10000):
    nl = discover_nonlocal(clauses, n) if use_nonlocal else []
    calls = [0]

    def get_score(var, fixed, unfixed_tensions):
        sigma = unfixed_tensions.get(var, 0)
        if not use_nonlocal: return sigma
        nl_push = 0; nl_count = 0
        for (i,j,is_clone,strength) in nl:
            other = j if i==var else (i if j==var else None)
            if other is None or other not in unfixed_tensions: continue
            if is_clone: nl_push += unfixed_tensions[other]*strength
            else: nl_push -= unfixed_tensions[other]*strength
            nl_count += 1
        if nl_count > 0: nl_push /= nl_count
        return sigma*0.7 + nl_push*0.3

    def dpll(fixed):
        calls[0] += 1
        if calls[0] > max_calls: return None
        fixed, conflict = unit_prop(clauses, n, fixed)
        if conflict: return None
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            a = [fixed.get(v,0) for v in range(n)]
            return a if evaluate(clauses, a) == len(clauses) else None

        tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}
        scores = {v: get_score(v, fixed, tensions) for v in unfixed}
        best = max(unfixed, key=lambda v: abs(scores[v]))
        first_val = 1 if scores[best] >= 0 else 0

        f = dict(fixed); f[best] = first_val
        result = dpll(f)
        if result: return result
        f = dict(fixed); f[best] = 1-first_val
        return dpll(f)

    result = dpll({})
    return result, result is not None, calls[0]


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 75)
    print("FINAL BENCHMARK: All solvers head-to-head")
    print("=" * 75)

    print(f"\n  {'n':>4} | {'tension':>10} | {'DPLL+T':>10} | {'DPLL+NL':>10} | "
          f"{'T time':>8} | {'D+T time':>8} | {'D+NL time':>9}")
    print("  " + "-" * 75)

    for n in [12, 16, 20, 25, 30]:
        t_solved = 0; dt_solved = 0; dnl_solved = 0; total = 0
        t_time = 0; dt_time = 0; dnl_time = 0
        dt_calls = []; dnl_calls = []

        max_dpll = 20000 if n <= 20 else 50000
        n_inst = 80 if n <= 16 else (40 if n <= 20 else 20)

        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            total += 1

            # Tension
            t0 = time.time()
            _, s = solve_tension(clauses, n)
            t_time += time.time()-t0
            if s: t_solved += 1

            # DPLL + tension
            t0 = time.time()
            _, s, calls = dpll_solve(clauses, n, False, max_dpll)
            dt_time += time.time()-t0
            dt_calls.append(calls)
            if s: dt_solved += 1

            # DPLL + nonlocal
            t0 = time.time()
            _, s, calls = dpll_solve(clauses, n, True, max_dpll)
            dnl_time += time.time()-t0
            dnl_calls.append(calls)
            if s: dnl_solved += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0

        t_pct = t_solved/total*100 if total > 0 else 0
        dt_pct = dt_solved/total*100 if total > 0 else 0
        dnl_pct = dnl_solved/total*100 if total > 0 else 0
        t_ms = t_time/total*1000 if total > 0 else 0
        dt_ms = dt_time/total*1000 if total > 0 else 0
        dnl_ms = dnl_time/total*1000 if total > 0 else 0

        print(f"  {n:>4} | {t_pct:>5.1f}%({t_solved:>2}) | {dt_pct:>5.1f}%({dt_solved:>2}) | "
              f"{dnl_pct:>5.1f}%({dnl_solved:>2}) | {t_ms:>6.0f}ms | {dt_ms:>6.0f}ms | {dnl_ms:>7.0f}ms")

    # Summary
    print(f"\n  DPLL+nonlocal vs DPLL+tension: which needs fewer backtracks?")
    print(f"  (Tested at n=12)")

    random.seed(42)
    dt_all_calls = []; dnl_all_calls = []
    for seed in range(80):
        clauses = random_3sat(12, int(4.27*12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions: continue
        _, _, c1 = dpll_solve(clauses, 12, False, 20000)
        _, _, c2 = dpll_solve(clauses, 12, True, 20000)
        dt_all_calls.append(c1)
        dnl_all_calls.append(c2)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"    DPLL+tension avg calls: {mean(dt_all_calls):.1f}")
    print(f"    DPLL+nonlocal avg calls: {mean(dnl_all_calls):.1f}")
    print(f"    Ratio: {mean(dnl_all_calls)/mean(dt_all_calls):.2f}x")
