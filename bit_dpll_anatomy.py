"""
WHAT DOES DPLL ACTUALLY DO?

DPLL = 100% at n≤16. Static prediction = 70-83%.
DPLL is NOT a "predictor" — it's a NAVIGATOR.

It doesn't predict each bit and assemble.
It EXPLORES the space, pruning dead branches.

What if the right metric is not "per-bit accuracy"
but "navigation efficiency" — how fast does DPLL
prune the search tree?

What makes DPLL work that static methods can't replicate?
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
# 1. DPLL ANATOMY: What happens inside the search tree?
# ============================================================

def dpll_anatomy():
    """
    Run DPLL and record EVERYTHING:
    - How many branches explored?
    - How deep before first backtrack?
    - How many backtracks total?
    - Which bits cause backtracks?
    - What FRACTION of the tree is explored?
    """
    print("=" * 70)
    print("1. DPLL ANATOMY: What happens inside?")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        # DPLL with full instrumentation
        calls = [0]; backtracks = [0]; max_depth = [0]
        first_backtrack_depth = [n]
        backtrack_vars = []

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

        def dpll(fixed, depth=0):
            calls[0] += 1
            if calls[0] > 50000: return None
            fixed, conflict = unit_prop(fixed)
            if conflict:
                backtracks[0] += 1
                if depth < first_backtrack_depth[0]:
                    first_backtrack_depth[0] = depth
                return None

            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed:
                a = [fixed.get(v,0) for v in range(n)]
                return a if evaluate(clauses, a) == len(clauses) else None

            max_depth[0] = max(max_depth[0], depth)
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            sigma = bit_tension(clauses, n, best, fixed)
            first_val = 1 if sigma >= 0 else 0

            f = dict(fixed); f[best] = first_val
            result = dpll(f, depth+1)
            if result: return result

            # Backtrack happened here
            backtrack_vars.append(best)
            f = dict(fixed); f[best] = 1-first_val
            return dpll(f, depth+1)

        result = dpll({})

        if result:
            total_tree = 2**n
            explored_frac = calls[0] / total_tree

            print(f"\n  Instance {seed} ({len(solutions)} solutions):")
            print(f"    Calls: {calls[0]}, Backtracks: {backtracks[0]}")
            print(f"    First backtrack at depth: {first_backtrack_depth[0]}")
            print(f"    Max depth: {max_depth[0]}")
            print(f"    Tree explored: {explored_frac*100:.4f}% of 2^{n}={total_tree}")
            if backtrack_vars:
                print(f"    Backtrack vars: {backtrack_vars[:10]}")


# ============================================================
# 2. THE PRUNING POWER: How much does UP + tension prune?
# ============================================================

def pruning_power():
    """
    At each DPLL step: how many branches does UP eliminate?
    This is the REAL source of DPLL's power — not prediction,
    but ELIMINATION of impossible branches.
    """
    print("\n" + "=" * 70)
    print("2. PRUNING POWER: How much does each decision prune?")
    print("=" * 70)

    random.seed(42); n = 12

    pruning_by_depth = {d: [] for d in range(n)}

    for seed in range(50):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        # At each depth: fix one bit, see how many get forced by UP
        correct_val = [1 if sum(s[v] for s in solutions)/len(solutions) > 0.5 else 0
                      for v in range(n)]

        fixed = {}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        for depth, var in enumerate(order):
            if var in fixed: continue

            sigma = bit_tension(clauses, n, var, fixed)
            fixed[var] = 1 if sigma >= 0 else 0

            # Count UP propagations
            f = dict(fixed); changed = True; propagated = 0
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
                        if v not in f:
                            f[v] = 1 if s==1 else 0
                            propagated += 1; changed = True

            fixed = f  # include propagated
            pruning_by_depth[depth].append(propagated)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'depth':>5} | {'avg pruned':>10} | {'cumulative':>10}")
    print("  " + "-" * 30)
    cumul = 0
    for d in range(n):
        p = mean(pruning_by_depth[d])
        cumul += p + 1  # +1 for the bit itself
        print(f"  {d:>5} | {p:>10.2f} | {cumul:>10.1f}/{n}")


# ============================================================
# 3. WHAT DPLL KNOWS THAT STATIC DOESN'T: Conditional info
# ============================================================

def conditional_info():
    """
    Static: predicts each bit INDEPENDENTLY (accuracy 70%).
    DPLL: predicts each bit CONDITIONAL on previous decisions.

    The conditional accuracy should be MUCH higher than 70%.
    After fixing k bits correctly: remaining accuracy = ?
    We showed earlier: 71→72→75→78→81% (amplification).

    But DPLL does MORE: it also DETECTS wrong decisions
    (through conflicts) and corrects them (backtracking).

    Effective per-step accuracy of DPLL = ???
    """
    print("\n" + "=" * 70)
    print("3. DPLL's EFFECTIVE per-step accuracy")
    print("=" * 70)

    random.seed(42); n = 12

    # Run DPLL, count: at each depth, is the FIRST choice correct?
    first_choice_correct_by_depth = {d: [0,0] for d in range(n)}

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        correct_val = [1 if sum(s[v] for s in solutions)/len(solutions) > 0.5 else 0
                      for v in range(n)]

        fixed = {}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        for depth, var in enumerate(order):
            if var in fixed: continue
            sigma = bit_tension(clauses, n, var, fixed)
            first_choice = 1 if sigma >= 0 else 0

            first_choice_correct_by_depth[depth][1] += 1
            if first_choice == correct_val[var]:
                first_choice_correct_by_depth[depth][0] += 1

            # Fix correctly for next step (oracle)
            fixed[var] = correct_val[var]

            # UP
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

    print(f"\n  {'depth':>5} | {'1st choice acc':>14} | {'n':>6}")
    print("  " + "-" * 30)
    for d in range(n):
        c, t = first_choice_correct_by_depth[d]
        if t > 0:
            acc = c/t*100
            print(f"  {d:>5} | {acc:>13.1f}% | {t:>6}")


# ============================================================
# 4. THE REAL METRIC: Search tree fraction explored
# ============================================================

def tree_fraction():
    """
    DPLL doesn't need 100% per-bit accuracy.
    It needs to explore a SMALL FRACTION of the search tree.

    If DPLL explores 2^k nodes (k << n): it's fast.
    k = effective number of "wrong" decisions that need backtracking.

    What is k? How does it scale with n?
    """
    print("\n" + "=" * 70)
    print("4. REAL METRIC: Fraction of search tree explored")
    print("=" * 70)

    random.seed(42)

    print(f"\n  {'n':>5} | {'calls':>8} | {'2^n':>10} | {'fraction':>10} | {'effective k':>11}")
    print("  " + "-" * 55)

    for n_test in [10, 12, 14, 16]:
        total_calls = 0; n_inst = 0

        for seed in range(50):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed)
            solutions = find_solutions(clauses, n_test)
            if not solutions: continue

            calls = [0]
            def up(fixed):
                f=dict(fixed);ch=True
                while ch:
                    ch=False
                    for clause in clauses:
                        sat=False;free=[]
                        for v,s in clause:
                            if v in f:
                                if (s==1 and f[v]==1) or (s==-1 and f[v]==0): sat=True;break
                            else: free.append((v,s))
                        if not sat and len(free)==1:
                            v,s=free[0]
                            if v not in f: f[v]=1 if s==1 else 0;ch=True
                        if not sat and len(free)==0: return f,True
                return f,False

            def dpll(fixed):
                calls[0]+=1
                if calls[0]>100000: return None
                fixed,c=up(fixed)
                if c: return None
                uf=[v for v in range(n_test) if v not in fixed]
                if not uf:
                    a=[fixed.get(v,0) for v in range(n_test)]
                    return a if evaluate(clauses,a)==len(clauses) else None
                best=max(uf,key=lambda v:abs(bit_tension(clauses,n_test,v,fixed)))
                sigma=bit_tension(clauses,n_test,best,fixed)
                fv=1 if sigma>=0 else 0
                f=dict(fixed);f[best]=fv
                r=dpll(f)
                if r: return r
                f=dict(fixed);f[best]=1-fv
                return dpll(f)

            result = dpll({})
            if result:
                total_calls += calls[0]
                n_inst += 1

        if n_inst > 0:
            avg_calls = total_calls / n_inst
            tree_size = 2**n_test
            frac = avg_calls / tree_size
            eff_k = math.log2(avg_calls) if avg_calls > 0 else 0
            print(f"  {n_test:>5} | {avg_calls:>8.0f} | {tree_size:>10} | "
                  f"{frac:>9.6f} | {eff_k:>11.1f}")


if __name__ == "__main__":
    dpll_anatomy()
    pruning_power()
    conditional_info()
    tree_fraction()
