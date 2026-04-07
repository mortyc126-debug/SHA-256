"""
CLONE REDUCTION: Solve the SMALL problem on independent bits only.

Observation: n=12 has only 4-6 independent bits.
Tension predicts them almost perfectly (4/4, 6/6).
But JOINT constraint allows only 8-25% of combos.

Strategy:
1. Identify independent bits via clone detection
2. Enumerate ALL combos of independent bits (2^5 = 32)
3. For each combo: fix independent bits → propagate to clones → check

This is POLYNOMIAL if #independent is O(log n) or O(1).
If #independent = O(n) → exponential (but smaller constant).
"""

import random
import math
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


def find_clones(clauses, n):
    """
    Find clone relationships by running multiple crystallizations
    and observing which bits always agree/disagree.
    NO SOLUTIONS NEEDED.
    """
    # Run 20 crystallizations, record assignments
    assignments = []
    for run in range(20):
        fixed = {}
        order = list(range(n))
        order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.2)))
        for var in order:
            if var in fixed: continue
            sigma = bit_tension(clauses, n, var, fixed)
            fixed[var] = 1 if sigma >= 0 else 0
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
        assignments.append([fixed.get(v,0) for v in range(n)])

    # Detect clones: pairs that ALWAYS agree or ALWAYS disagree
    clone_of = {}  # var → (clone_var, is_anti)
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[a] = b

    for i in range(n):
        for j in range(i+1, n):
            same = sum(1 for a in assignments if a[i] == a[j])
            frac = same / len(assignments)
            if frac > 0.85:
                union(i, j)
                clone_of[j] = (i, False)  # j clones i
            elif frac < 0.15:
                union(i, j)
                clone_of[j] = (i, True)  # j anti-clones i

    # Find clusters and representatives
    clusters = {}
    for v in range(n):
        r = find(v)
        if r not in clusters: clusters[r] = []
        clusters[r].append(v)

    # Representatives: pick most confident bit per cluster
    independents = []
    for cluster in clusters.values():
        best = max(cluster, key=lambda v: abs(bit_tension(clauses, n, v)))
        independents.append(best)

    return independents, clone_of, clusters


# ============================================================
# CLONE REDUCTION SOLVER
# ============================================================

def clone_reduction_solver(clauses, n):
    """
    1. Find independent bits (via crystallization-based clone detection)
    2. Enumerate all 2^k combos of independent bits
    3. For each: propagate to clones via tension, check satisfaction
    """
    independents, clone_of, clusters = find_clones(clauses, n)
    k = len(independents)

    best_assignment = None
    best_sat = 0

    for combo in range(2**k):
        # Set independent bits
        fixed = {}
        for idx, var in enumerate(independents):
            fixed[var] = (combo >> idx) & 1

        # Propagate to clones
        for v in range(n):
            if v in fixed: continue
            if v in clone_of:
                src, is_anti = clone_of[v]
                if src in fixed:
                    fixed[v] = (1 - fixed[src]) if is_anti else fixed[src]

        # Fill remaining by tension
        for v in range(n):
            if v in fixed: continue
            sigma = bit_tension(clauses, n, v, fixed)
            fixed[v] = 1 if sigma >= 0 else 0

        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)

        if sat > best_sat:
            best_sat = sat
            best_assignment = assignment

        if best_sat == len(clauses):
            break  # found solution

    return best_assignment, best_sat == len(clauses), k


# ============================================================
# BENCHMARK
# ============================================================

def benchmark():
    print("=" * 70)
    print("CLONE REDUCTION SOLVER")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16, 20]:
        std_solved = 0; clone_solved = 0; total = 0
        avg_k = []; avg_combos = []; total_time = 0

        n_inst = 100 if n <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+700000)

            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            total += 1

            # Standard
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                std_solved += 1

            # Clone reduction
            t0 = time.time()
            assignment, success, k = clone_reduction_solver(clauses, n)
            t1 = time.time()
            total_time += (t1 - t0)

            if success: clone_solved += 1
            avg_k.append(k)
            avg_combos.append(min(2**k, 2**k))

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        avg_time = total_time / total * 1000 if total > 0 else 0
        print(f"\n  n={n} ({total} instances):")
        print(f"    Standard:       {std_solved}/{total} ({std_solved/total*100:.1f}%)")
        print(f"    Clone reduction: {clone_solved}/{total} ({clone_solved/total*100:.1f}%)")
        print(f"    Avg independent: {mean(avg_k):.1f} ({mean(avg_combos):.0f} combos)")
        print(f"    Avg time: {avg_time:.1f}ms")


# ============================================================
# SCALING: How does #independent grow with n?
# ============================================================

def scaling_independent():
    print("\n" + "=" * 70)
    print("SCALING: How does #independent grow with n?")
    print("=" * 70)

    random.seed(42)

    print(f"\n  {'n':>4} | {'k_indep':>8} | {'k/n':>6} | {'2^k':>8} | {'solvable':>8}")
    print("  " + "-" * 45)

    for n in [8, 10, 12, 14, 16, 20, 25, 30]:
        k_vals = []
        n_inst = 30 if n <= 20 else 15

        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+800000)
            independents, _, _ = find_clones(clauses, n)
            k_vals.append(len(independents))

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        avg_k = mean(k_vals)
        ratio = avg_k / n
        combos = 2**int(avg_k)
        solvable = "easy" if avg_k < 20 else "hard"

        print(f"  {n:>4} | {avg_k:>8.1f} | {ratio:>5.2f} | {combos:>8} | {solvable}")


if __name__ == "__main__":
    benchmark()
    scaling_independent()
