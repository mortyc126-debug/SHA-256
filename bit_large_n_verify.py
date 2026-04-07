"""
LARGE-N VERIFICATION: Do our laws and constants hold at n=50-200?

At these sizes we can't compute solutions directly.
Strategy: use WalkSAT as ground truth proxy + structural measurements.

VERIFY:
1. ε ≈ 1/14 (from WalkSAT solutions)
2. Tension accuracy ≈ 70%
3. Flip trigger ratio ≈ 2.0
4. Eigenmode k/n ≈ 1/3
5. DPLL+tension solve rate and timing
6. Non-local constraint count scaling
7. Clone fraction from crystallization
"""

import random
import math
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


def dpll_tension(clauses, n, max_calls):
    calls = [0]
    def up(fixed):
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
        fixed, conflict = up(fixed)
        if conflict: return None
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            a = [fixed.get(v,0) for v in range(n)]
            return a if evaluate(clauses, a) == len(clauses) else None
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        first = 1 if sigma >= 0 else 0
        f = dict(fixed); f[best] = first
        r = dpll(f)
        if r: return r
        f = dict(fixed); f[best] = 1-first
        return dpll(f)

    result = dpll({})
    return result, result is not None, calls[0]


# ============================================================
# VERIFICATION
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 75)
    print("LARGE-N VERIFICATION")
    print("=" * 75)

    # ---- 1. Core constants via WalkSAT ground truth ----
    print(f"\n  1. CORE CONSTANTS (ε, accuracy, flip triggers)")
    print(f"  {'n':>5} | {'ε':>8} | {'acc':>7} | {'FT ratio':>8} | {'WS found':>8}")
    print("  " + "-" * 50)

    for n in [20, 50, 100, 200]:
        eps_vals = []; acc_vals = []; ft_correct = []; ft_wrong = []
        ws_found = 0

        n_inst = 10 if n <= 50 else 5
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+10000000)

            # WalkSAT for ground truth
            ws_solutions = []
            for _ in range(30):
                a, found = walksat(clauses, n, 300*n)
                if found: ws_solutions.append(list(a))
            if len(ws_solutions) < 3: continue
            ws_found += 1

            prob_1 = [sum(s[v] for s in ws_solutions)/len(ws_solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            # Sample bits (not all — too slow at n=200)
            sample = random.sample(range(n), min(20, n))

            for var in sample:
                sigma = bit_tension(clauses, n, var)
                actual = correct_val[var]
                pred = 1 if sigma >= 0 else 0

                # ε
                pos = sum(1 for cl in clauses for v,s in cl if v==var and s==1)
                neg = sum(1 for cl in clauses for v,s in cl if v==var and s==-1)
                d = pos+neg
                if d > 0:
                    if actual == 1: eps_vals.append(pos/d - 0.5)
                    else: eps_vals.append(neg/d - 0.5)

                # Accuracy
                acc_vals.append(1 if pred == actual else 0)

                # Flip triggers (sample 3 neighbors)
                nbs = set()
                for clause in clauses:
                    vs = [v for v,s in clause]
                    if var in vs:
                        for v in vs:
                            if v != var: nbs.add(v)
                nb_list = list(nbs)[:3]
                base_sign = 1 if sigma >= 0 else -1
                triggers = 0
                for nb in nb_list:
                    for val in [0, 1]:
                        s = bit_tension(clauses, n, var, {nb: val})
                        if (1 if s >= 0 else -1) != base_sign:
                            triggers += 1; break
                ft = triggers / len(nb_list) if nb_list else 0

                if pred == actual: ft_correct.append(ft)
                else: ft_wrong.append(ft)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        ft_r = mean(ft_wrong)/mean(ft_correct) if mean(ft_correct) > 0 else 0
        print(f"  {n:>5} | {mean(eps_vals):>+7.4f} | {mean(acc_vals)*100:>6.1f}% | "
              f"{ft_r:>8.2f} | {ws_found:>8}")

    # ---- 2. DPLL+tension performance ----
    print(f"\n  2. DPLL+TENSION PERFORMANCE")
    print(f"  {'n':>5} | {'solved':>8} | {'avg calls':>9} | {'avg time':>8}")
    print("  " + "-" * 40)

    for n in [20, 30, 50, 75, 100]:
        solved = 0; total = 0; total_calls = 0; total_time = 0
        max_calls = 100000 if n <= 50 else 50000

        n_inst = 20 if n <= 50 else 10
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+10000000)
            total += 1

            t0 = time.time()
            _, success, calls = dpll_tension(clauses, n, max_calls)
            t1 = time.time()

            total_time += (t1-t0)
            total_calls += calls
            if success: solved += 1

        avg_calls = total_calls/total if total > 0 else 0
        avg_time = total_time/total*1000 if total > 0 else 0
        print(f"  {n:>5} | {solved:>3}/{total:>2} ({solved/total*100:>4.0f}%) | "
              f"{avg_calls:>9.0f} | {avg_time:>6.0f}ms")

    # ---- 3. Structural measurements ----
    print(f"\n  3. STRUCTURAL: |σ|, temperature, clone fraction")
    print(f"  {'n':>5} | {'avg|σ|':>7} | {'pred|σ|':>7} | {'T':>7} | {'clone_frac':>10}")
    print("  " + "-" * 50)

    eps = 1/14; p_correct = 4/7
    for n in [20, 50, 100, 200, 500]:
        sigma_vals = []; clone_pairs = 0; total_pairs = 0

        n_inst = 5 if n <= 100 else 2
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+10000000)

            # Sample |σ|
            sample = random.sample(range(n), min(30, n))
            for var in sample:
                sigma_vals.append(abs(bit_tension(clauses, n, var)))

            # Clone fraction from 5 crystallizations
            assignments = []
            for run in range(5):
                fixed = {}
                order = list(range(n))
                order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.15)))
                for var in order:
                    if var in fixed: continue
                    sigma = bit_tension(clauses, n, var, fixed)
                    fixed[var] = 1 if sigma >= 0 else 0
                assignments.append([fixed.get(v,0) for v in range(n)])

            # Sample pairs for clone detection
            pair_sample = [(random.randint(0,n-1), random.randint(0,n-1))
                          for _ in range(100)]
            for i, j in pair_sample:
                if i == j: continue
                total_pairs += 1
                agree = sum(1 for a in assignments if a[i] == a[j])
                if agree/len(assignments) > 0.85 or agree/len(assignments) < 0.15:
                    clone_pairs += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        avg_sigma = mean(sigma_vals)
        T = 1 - avg_sigma

        d = int(round(3*4.27))
        pred_sigma = sum(math.exp(math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
                                  k*math.log(p_correct)+(d-k)*math.log(1-p_correct)
                                  )*abs(2*k/d-1) for k in range(d+1))

        clone_frac = clone_pairs/total_pairs if total_pairs > 0 else 0

        print(f"  {n:>5} | {avg_sigma:>7.4f} | {pred_sigma:>7.4f} | {T:>7.4f} | {clone_frac:>10.3f}")

    # ---- Summary ----
    print(f"\n  PREDICTED (from theory at threshold):")
    print(f"    ε = 1/14 = {1/14:.4f}")
    print(f"    Accuracy = 70.1%")
    print(f"    Flip trigger ratio = 2.0")
    print(f"    |σ| = {pred_sigma:.4f}")
