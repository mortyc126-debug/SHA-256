"""
CLONE DETECTION: Can we find MORE clones with better methods?

Current: 20 noisy crystallizations → k/n ≈ 0.5
Maybe: better detection → k/n < 0.5 → faster solver

Methods to try:
1. MORE crystallizations (50, 100)
2. Clause-based clone detection (structural, no crystallization)
3. Transitive clones: if A~B and B~C, then A~C
4. INDIRECT clones: bits that agree through a CHAIN
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


def noisy_crystallize(clauses, n, noise=0.15):
    fixed = {}
    order = list(range(n))
    order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, noise)))
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
    return [fixed.get(v,0) for v in range(n)]


def detect_clones(assignments, n, threshold=0.85):
    """Detect clone pairs from assignments."""
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[a] = b

    clone_of = {}
    for i in range(n):
        for j in range(i+1, n):
            same = sum(1 for a in assignments if a[i] == a[j]) / len(assignments)
            if same > threshold:
                union(i, j)
                clone_of[j] = (i, False)
            elif same < (1-threshold):
                union(i, j)
                clone_of[j] = (i, True)

    clusters = {}
    for v in range(n):
        r = find(v)
        if r not in clusters: clusters[r] = []
        clusters[r].append(v)

    independents = []
    for cluster in clusters.values():
        best = max(cluster, key=lambda v: sum(abs(a[v] - 0.5) for a in assignments))
        independents.append(best)

    return independents, clone_of, clusters


# ============================================================
# 1. DOES MORE DATA FIND MORE CLONES?
# ============================================================

def more_data():
    print("=" * 70)
    print("1. Does more data find more clones?")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16, 20]:
        print(f"\n  n={n}:")
        print(f"  {'runs':>6} | {'k_indep':>8} | {'k/n':>6} | {'time ms':>8}")
        print("  " + "-" * 40)

        for n_runs in [10, 20, 50, 100]:
            k_vals = []
            t_total = 0

            n_inst = 20 if n <= 16 else 10
            for seed in range(n_inst):
                clauses = random_3sat(n, int(4.27*n), seed=seed+900000)

                t0 = time.time()
                assignments = [noisy_crystallize(clauses, n, 0.15) for _ in range(n_runs)]
                independents, _, _ = detect_clones(assignments, n, 0.85)
                t1 = time.time()

                k_vals.append(len(independents))
                t_total += (t1-t0)

            mean = lambda lst: sum(lst)/len(lst) if lst else 0
            avg_t = t_total / n_inst * 1000
            print(f"  {n_runs:>6} | {mean(k_vals):>8.1f} | {mean(k_vals)/n:>5.2f} | {avg_t:>7.0f}")


# ============================================================
# 2. CLAUSE-BASED CLONE DETECTION (structural, no crystallization)
# ============================================================

def structural_clones():
    """
    Two bits are likely clones if:
    - They appear in the SAME clauses with the SAME signs
    - Or: same clauses with OPPOSITE signs (anti-clones)

    Structural similarity = Jaccard of clause neighborhoods.
    """
    print("\n" + "=" * 70)
    print("2. STRUCTURAL clone detection (no crystallization)")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16, 20, 30]:
        k_structural = []
        k_crystal = []

        n_inst = 20 if n <= 20 else 10
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+900000)

            # Structural: build clause-signature per bit
            signatures = {}
            for var in range(n):
                sig = []
                for ci, clause in enumerate(clauses):
                    for v, s in clause:
                        if v == var:
                            sig.append((ci, s))
                signatures[var] = set(sig)

            # Structural similarity
            parent = list(range(n))
            def find(x):
                while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
                return x
            def union(a, b):
                a, b = find(a), find(b)
                if a != b: parent[a] = b

            for i in range(n):
                for j in range(i+1, n):
                    # Same clauses? (ignoring signs)
                    ci = {c for c, s in signatures[i]}
                    cj = {c for c, s in signatures[j]}
                    overlap = len(ci & cj)
                    total = len(ci | cj)
                    jaccard = overlap / total if total > 0 else 0

                    if jaccard > 0.6:
                        union(i, j)

            clusters = {}
            for v in range(n):
                r = find(v)
                if r not in clusters: clusters[r] = []
                clusters[r].append(v)
            k_structural.append(len(clusters))

            # Crystallization-based for comparison
            assignments = [noisy_crystallize(clauses, n, 0.15) for _ in range(20)]
            inds, _, _ = detect_clones(assignments, n, 0.85)
            k_crystal.append(len(inds))

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"\n  n={n}: structural k={mean(k_structural):.1f} ({mean(k_structural)/n:.2f}), "
              f"crystal k={mean(k_crystal):.1f} ({mean(k_crystal)/n:.2f})")


# ============================================================
# 3. CAN WE REDUCE k/n BELOW 0.5?
# ============================================================

def reduce_k():
    """
    Current: 85% threshold for clone detection.
    What if we LOWER the threshold? More clones found → smaller k.
    But: false clones → wrong propagation → lower accuracy.

    Find the OPTIMAL threshold.
    """
    print("\n" + "=" * 70)
    print("3. OPTIMAL clone threshold — minimize k while solving")
    print("=" * 70)

    random.seed(42); n = 16

    print(f"\n  {'threshold':>9} | {'k':>5} | {'k/n':>5} | {'solved':>7}")
    print("  " + "-" * 35)

    for thresh_100 in [95, 90, 85, 80, 75, 70, 60, 50]:
        threshold = thresh_100 / 100

        solved = 0; total = 0; k_vals = []

        for seed in range(50):
            clauses = random_3sat(n, int(4.27*n), seed=seed+900000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            total += 1

            assignments = [noisy_crystallize(clauses, n, 0.15) for _ in range(20)]
            independents, clone_of, clusters = detect_clones(assignments, n, threshold)
            k = len(independents)
            k_vals.append(k)

            # Solve by enumeration
            best_sat = 0
            for combo in range(min(2**k, 50000)):
                fixed = {}
                for idx, var in enumerate(independents):
                    fixed[var] = (combo >> idx) & 1
                for v in range(n):
                    if v in fixed: continue
                    if v in clone_of:
                        src, is_anti = clone_of[v]
                        if src in fixed:
                            fixed[v] = (1-fixed[src]) if is_anti else fixed[src]
                for v in range(n):
                    if v in fixed: continue
                    sigma = bit_tension(clauses, n, v, fixed)
                    fixed[v] = 1 if sigma >= 0 else 0

                a = [fixed.get(v,0) for v in range(n)]
                s = evaluate(clauses, a)
                if s > best_sat: best_sat = s
                if best_sat == len(clauses): break

            if best_sat == len(clauses): solved += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"  {threshold:>9.2f} | {mean(k_vals):>5.1f} | {mean(k_vals)/n:>5.2f} | "
              f"{solved}/{total} ({solved/total*100:.0f}%)" if total > 0 else "")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    more_data()
    structural_clones()
    reduce_k()
