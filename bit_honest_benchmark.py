"""
HONEST BENCHMARK: Our methods vs standard algorithms.
Same problem, same time budget. Who wins?

No tricks — pure comparison.
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


# ============================================================
# STANDARD: Pure WalkSAT (no tension, no bit mechanics)
# ============================================================

def pure_walksat(clauses, n, max_flips):
    assignment = [random.randint(0,1) for _ in range(n)]
    m = len(clauses)
    for flip in range(max_flips):
        unsat = [ci for ci in range(m) if not any(
            (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
            for v,s in clauses[ci])]
        if not unsat: return assignment, True, flip
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
    return assignment, False, max_flips


# ============================================================
# STANDARD: Pure DPLL (no tension guidance)
# ============================================================

def pure_dpll(clauses, n, max_calls=50000):
    calls = [0]

    def unit_prop(fixed):
        f = dict(fixed)
        changed = True
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
                if not satisfied and len(free) == 0:
                    return f, True  # conflict
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

        var = random.choice(unfixed)
        for val in [random.randint(0,1), None]:
            if val is None: val = 1 - (random.randint(0,1))
            f = dict(fixed); f[var] = val
            result = dpll(f)
            if result is not None: return result
        return None

    result = dpll({})
    return result, result is not None, calls[0]


# ============================================================
# OURS: DPLL + tension guidance
# ============================================================

def dpll_tension(clauses, n, max_calls=50000):
    calls = [0]

    def unit_prop(fixed):
        f = dict(fixed)
        changed = True
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
                if not satisfied and len(free) == 0:
                    return f, True
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

        # TENSION-GUIDED: pick most confident bit, try tension direction first
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        first_val = 1 if sigma >= 0 else 0

        f = dict(fixed); f[best] = first_val
        result = dpll(f)
        if result is not None: return result

        f = dict(fixed); f[best] = 1 - first_val
        return dpll(f)

    result = dpll({})
    return result, result is not None, calls[0]


# ============================================================
# OURS: Shadow solving
# ============================================================

def shadow_solve(clauses, n, max_flips_per_stage=None):
    if max_flips_per_stage is None: max_flips_per_stage = 100*n
    m = len(clauses)
    indices = list(range(m))
    random.shuffle(indices)

    n_start = m // 3
    easy = [clauses[i] for i in indices[:n_start]]

    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(easy, n, v, fixed)))
        fixed[best] = 1 if bit_tension(easy, n, best, fixed) >= 0 else 0
    assignment = [fixed.get(v,0) for v in range(n)]

    step_size = max(1, (m - n_start) // 5)
    total_flips = 0
    for i in range(n_start, m, step_size):
        current = [clauses[j] for j in indices[:min(i+step_size, m)]]
        result, found, flips = pure_walksat(current, n, max_flips_per_stage)
        # Start from previous assignment
        for v in range(n): result[v] = assignment[v] if not found else result[v]
        if found: assignment = result
        total_flips += max_flips_per_stage

    # Final on full
    if evaluate(clauses, assignment) != len(clauses):
        result, found, flips = pure_walksat(clauses, n, max_flips_per_stage)
        # Start from assignment
        a2 = list(assignment)
        for flip in range(max_flips_per_stage):
            unsat = [ci for ci in range(m) if not any(
                (s==1 and a2[v]==1) or (s==-1 and a2[v]==0)
                for v,s in clauses[ci])]
            if not unsat: return a2, True, total_flips + flip
            ci = random.choice(unsat)
            if random.random() < 0.3:
                v, s = random.choice(clauses[ci])
                a2[v] = 1-a2[v]
            else:
                best_v = None; best_b = float('inf')
                for v,s in clauses[ci]:
                    a2[v] = 1-a2[v]
                    b = sum(1 for cj in range(m) if not any(
                        (ss==1 and a2[vv]==1) or (ss==-1 and a2[vv]==0)
                        for vv,ss in clauses[cj]))
                    a2[v] = 1-a2[v]
                    if b < best_b: best_b = b; best_v = v
                if best_v: a2[best_v] = 1-a2[best_v]
        assignment = a2
        total_flips += max_flips_per_stage

    return assignment, evaluate(clauses, assignment) == len(clauses), total_flips


# ============================================================
# BENCHMARK: Same time budget
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 75)
    print("HONEST BENCHMARK: Our methods vs standard algorithms")
    print("Same problems, measuring time and solve rate")
    print("=" * 75)

    for n in [12, 16, 20, 30]:
        print(f"\n  n={n}, ratio=4.27:")
        print(f"  {'method':>20} | {'solved':>8} | {'avg time':>10} | {'avg calls':>10}")
        print("  " + "-" * 60)

        methods = {}
        n_inst = 50

        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+70000)

            for name, solver in [
                ('pure WalkSAT', lambda c, nn: pure_walksat(c, nn, 200*nn)),
                ('pure DPLL', lambda c, nn: pure_dpll(c, nn, 50000)),
                ('DPLL+tension', lambda c, nn: dpll_tension(c, nn, 50000)),
                ('shadow', lambda c, nn: shadow_solve(c, nn)),
            ]:
                if name not in methods:
                    methods[name] = {'solved': 0, 'time': 0, 'calls': 0, 'total': 0}

                t0 = time.time()
                result, found, calls = solver(clauses, n)
                t1 = time.time()

                methods[name]['total'] += 1
                methods[name]['time'] += (t1-t0)
                methods[name]['calls'] += calls
                if found:
                    # Verify
                    if result is not None and evaluate(clauses, result) == len(clauses):
                        methods[name]['solved'] += 1

        for name in ['pure WalkSAT', 'pure DPLL', 'DPLL+tension', 'shadow']:
            m = methods[name]
            avg_time = m['time'] / m['total'] * 1000
            avg_calls = m['calls'] / m['total']
            pct = m['solved'] / m['total'] * 100
            print(f"  {name:>20} | {m['solved']:>3}/{m['total']} ({pct:>5.1f}%) | "
                  f"{avg_time:>8.1f}ms | {avg_calls:>10.0f}")
