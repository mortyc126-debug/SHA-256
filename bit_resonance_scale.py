"""
RESONANCE vs V4 AT SCALE

At n=12: v4=79%, resonance=76%. V4 wins.
But: does the gap HOLD at larger n? Or does resonance catch up?

Also: resonance is O(nm) per pass. V4 is O(n²m) per iteration.
At n=1000: resonance may be the only option.
"""

import random
import time
from bit_catalog_static import random_3sat


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


def walksat(clauses, n, max_flips):
    a = [random.randint(0,1) for _ in range(n)]; m = len(clauses)
    for f in range(max_flips):
        u = [ci for ci in range(m) if not any(
            (s==1 and a[v]==1) or (s==-1 and a[v]==0) for v,s in clauses[ci])]
        if not u: return a, True
        ci = random.choice(u)
        if random.random() < 0.3:
            v,s = random.choice(clauses[ci]); a[v]=1-a[v]
        else:
            bv=None; bb=999
            for v,s in clauses[ci]:
                a[v]=1-a[v]
                b = sum(1 for cj in range(m) if not any(
                    (ss==1 and a[vv]==1) or (ss==-1 and a[vv]==0) for vv,ss in clauses[cj]))
                a[v]=1-a[v]
                if b<bb: bb=b; bv=v
            if bv: a[bv]=1-a[bv]
    return a, False


# ============================================================
# SOLVERS
# ============================================================

def solve_tension(clauses, n):
    """Standard tension crystallization."""
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
    assignment = [fixed.get(v,0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


def solve_v4(clauses, n, n_iter=10):
    """V4 iterative tension crystallization."""
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}
        for _ in range(n_iter):
            new_t = {}
            for var in tensions:
                push_1, push_0 = 0.0, 0.0
                for clause in clauses:
                    sat = False; rem = []; vs = None
                    for v, s in clause:
                        if v in fixed:
                            if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                sat = True; break
                        else: rem.append((v,s));
                        if v == var: vs = s
                    if sat or vs is None: continue
                    oh = 0.0
                    for v, s in rem:
                        if v == var: continue
                        t = tensions.get(v, 0)
                        p = (1+t)/2 if s==1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs==1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in tensions:
                tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v,0)

        best = max(unfixed, key=lambda v: abs(tensions.get(v, 0)))
        fixed[best] = 1 if tensions.get(best, 0) >= 0 else 0

    assignment = [fixed.get(v,0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


def solve_resonance(clauses, n, n_iter=5):
    """Iterative resonance crystallization."""
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}

        # Iterative resonance
        for _ in range(n_iter):
            new_t = {}
            for var in tensions:
                votes = []
                for clause in clauses:
                    signs = {v: s for v, s in clause}
                    if var not in signs: continue
                    has_fixed_sat = False
                    for v, s in clause:
                        if v in fixed:
                            if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                has_fixed_sat = True; break
                    if has_fixed_sat: continue

                    for v, s in clause:
                        if v == var or v in fixed: continue
                        if v not in tensions: continue
                        nb_dir = 1 if tensions[v] >= 0 else -1
                        nb_sat = (s==1 and nb_dir==1) or (s==-1 and nb_dir==-1)
                        if nb_sat:
                            votes.append(0)
                        else:
                            votes.append(signs[var])

                res = sum(votes) / len(votes) if votes else 0
                new_t[var] = 0.6 * tensions[var] + 0.4 * res
            tensions = new_t

        best = max(unfixed, key=lambda v: abs(tensions.get(v, 0)))
        fixed[best] = 1 if tensions.get(best, 0) >= 0 else 0

    assignment = [fixed.get(v,0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# BENCHMARK AT SCALE
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("RESONANCE vs V4 AT SCALE")
    print("=" * 70)

    print(f"\n  {'n':>5} | {'tension':>12} | {'v4':>12} | {'resonance':>12} | "
          f"{'t_tension':>10} | {'t_v4':>10} | {'t_res':>10}")
    print("  " + "-" * 80)

    for n in [12, 20, 30, 50, 75, 100]:
        n_inst = 30 if n <= 50 else 15
        t_solved = 0; v4_solved = 0; r_solved = 0; total = 0
        t_time = 0; v4_time = 0; r_time = 0

        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+2000000)
            total += 1

            # Tension
            t0 = time.time()
            _, success = solve_tension(clauses, n)
            t_time += time.time() - t0
            if success: t_solved += 1

            # V4 (reduce iterations for large n)
            v4_iter = 10 if n <= 30 else 5 if n <= 50 else 3
            t0 = time.time()
            _, success = solve_v4(clauses, n, v4_iter)
            v4_time += time.time() - t0
            if success: v4_solved += 1

            # Resonance
            r_iter = 5 if n <= 30 else 3
            t0 = time.time()
            _, success = solve_resonance(clauses, n, r_iter)
            r_time += time.time() - t0
            if success: r_solved += 1

        t_pct = t_solved/total*100
        v4_pct = v4_solved/total*100
        r_pct = r_solved/total*100
        t_ms = t_time/total*1000
        v4_ms = v4_time/total*1000
        r_ms = r_time/total*1000

        print(f"  {n:>5} | {t_pct:>5.1f}% ({t_solved:>2}) | {v4_pct:>5.1f}% ({v4_solved:>2}) | "
              f"{r_pct:>5.1f}% ({r_solved:>2}) | {t_ms:>8.0f}ms | {v4_ms:>8.0f}ms | {r_ms:>8.0f}ms")
