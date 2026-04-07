"""
IS CLONE DETECTION EQUIVALENT TO SAT SOLVING?

Claim: if you can detect clones from clauses alone → you can solve SAT.
Test: is this TRUE? Or can clones be detected WITHOUT solving?

Three approaches:
1. Can UNIT PROPAGATION detect some clones? (poly time, no solving)
2. Can IMPLICATION GRAPH detect clones? (2-SAT like structure)
3. FORMAL: if we HAD an oracle for clones → can we always solve?
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
# 1. UNIT PROPAGATION CLONES
# ============================================================

def up_clones(clauses, n):
    """
    Can UP detect clones?
    If fixing bit i=1 FORCES bit j=1 via UP, AND
    fixing bit i=0 FORCES bit j=0 via UP → i and j are UP-clones.

    This is poly time and uses only clause structure.
    """
    def propagate(fixed):
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
                    if v not in f:
                        f[v] = 1 if s==1 else 0
                        changed = True
                if not satisfied and len(free) == 0:
                    return f, True  # conflict
        return f, False

    clone_pairs = set()
    anti_pairs = set()

    for i in range(n):
        # Fix i=1, propagate
        f1, c1 = propagate({i: 1})
        # Fix i=0, propagate
        f0, c0 = propagate({i: 0})

        for j in range(n):
            if j == i: continue
            # Clone: j follows i (both 1→1, 0→0)
            if j in f1 and j in f0:
                if f1[j] == 1 and f0[j] == 0:
                    clone_pairs.add((min(i,j), max(i,j)))
                elif f1[j] == 0 and f0[j] == 1:
                    anti_pairs.add((min(i,j), max(i,j)))

    return clone_pairs, anti_pairs


# ============================================================
# 2. IMPLICATION GRAPH CLONES
# ============================================================

def implication_clones(clauses, n):
    """
    Build implication graph from binary clauses created by UP.
    (a ∨ b) → (¬a → b) and (¬b → a).

    If there's a path a → b AND b → a → they're equivalent (clone).
    If a → ¬b AND ¬b → a → they're anti-clones.

    This is the 2-SAT equivalence detection.
    """
    # Build implications from each clause
    # 3-SAT clause (a ∨ b ∨ c): fix one literal false → binary clause
    # (¬a → b ∨ c), etc. Not directly binary.
    # But after UP on one variable, some clauses become binary.

    # Simpler: for each pair, check if fixing one implies the other
    clone_pairs = set()
    anti_pairs = set()

    for i in range(n):
        for val_i in [0, 1]:
            fixed = {i: val_i}
            # UP
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
                        if v not in f:
                            f[v] = 1 if s==1 else 0; changed = True

            for j in range(n):
                if j == i or j not in f: continue
                # i=val_i implies j=f[j]
                if val_i == 1 and f[j] == 1:
                    # i=1 → j=1. Need also i=0 → j=0 for clone.
                    pass  # will check both vals
                # Store implication
                if val_i == f.get(j, -1):
                    clone_pairs.add((min(i,j), max(i,j)))
                elif val_i != f.get(j, -1) and j in f:
                    anti_pairs.add((min(i,j), max(i,j)))

    # Filter: only keep pairs where BOTH directions imply
    true_clones = set()
    true_anti = set()
    for i, j in clone_pairs:
        # Check both: i=1→j=1 AND i=0→j=0
        f1 = {i: 1}; f0 = {i: 0}
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False; free = []
                for v, s in clause:
                    if v in f1:
                        if (s==1 and f1[v]==1) or (s==-1 and f1[v]==0):
                            satisfied = True; break
                    else: free.append((v,s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    if v not in f1: f1[v] = 1 if s==1 else 0; changed = True
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False; free = []
                for v, s in clause:
                    if v in f0:
                        if (s==1 and f0[v]==1) or (s==-1 and f0[v]==0):
                            satisfied = True; break
                    else: free.append((v,s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    if v not in f0: f0[v] = 1 if s==1 else 0; changed = True

        if j in f1 and j in f0:
            if f1[j] == 1 and f0[j] == 0:
                true_clones.add((i,j))
            elif f1[j] == 0 and f0[j] == 1:
                true_anti.add((i,j))

    return true_clones, true_anti


# ============================================================
# 3. COMPARE: UP-clones vs real clones vs solver performance
# ============================================================

def compare_methods():
    print("=" * 70)
    print("CLONE DETECTION: Structural (poly) vs Crystallization vs Real")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16, 20]:
        up_clone_counts = []
        crystal_clone_counts = []
        real_clone_counts = []
        up_solve = 0; crystal_solve = 0; total = 0

        n_inst = 50 if n <= 16 else 20
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+950000)

            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue

            total += 1

            # UP clones (poly time, clause-only)
            up_c, up_a = up_clones(clauses, n)
            up_total = len(up_c) + len(up_a)
            up_clone_counts.append(up_total)

            # UP-based k
            parent = list(range(n))
            def find(x):
                while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
                return x
            def union(a, b):
                a, b = find(a), find(b)
                if a != b: parent[a] = b
            for i, j in up_c: union(i, j)
            for i, j in up_a: union(i, j)
            up_k = len(set(find(v) for v in range(n)))

            # UP-based solver: enumerate independent, propagate clones
            up_indeps = []
            seen_roots = set()
            for v in range(n):
                r = find(v)
                if r not in seen_roots:
                    seen_roots.add(r)
                    up_indeps.append(v)

            solved = False
            for combo in range(min(2**len(up_indeps), 100000)):
                fixed = {}
                for idx, var in enumerate(up_indeps):
                    fixed[var] = (combo >> idx) & 1
                # Propagate clones
                for i, j in up_c:
                    if i in fixed and j not in fixed: fixed[j] = fixed[i]
                    elif j in fixed and i not in fixed: fixed[i] = fixed[j]
                for i, j in up_a:
                    if i in fixed and j not in fixed: fixed[j] = 1-fixed[i]
                    elif j in fixed and i not in fixed: fixed[i] = 1-fixed[j]
                # Fill rest by tension
                for v in range(n):
                    if v not in fixed:
                        sigma = bit_tension(clauses, n, v, fixed)
                        fixed[v] = 1 if sigma >= 0 else 0
                if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                    solved = True; break

            if solved: up_solve += 1

            # Real clones (from solutions, for comparison)
            if n <= 16 and solutions and len(solutions) >= 2:
                real_c = 0
                for i in range(n):
                    for j in range(i+1, n):
                        same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                        if same > 0.9 or same < 0.1: real_c += 1
                real_clone_counts.append(real_c)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"\n  n={n} ({total} instances):")
        print(f"    UP clone pairs found:   {mean(up_clone_counts):.1f}")
        if real_clone_counts:
            print(f"    Real clone pairs:       {mean(real_clone_counts):.1f}")
        print(f"    UP-based solve rate:    {up_solve}/{total} ({up_solve/total*100:.1f}%)")


# ============================================================
# 4. THE KEY QUESTION: Oracle clone → SAT?
# ============================================================

def oracle_clone_solver():
    """
    If we had a PERFECT oracle for clones (from solutions):
    Use it to reduce to k independent bits → enumerate → solve.

    Does this ALWAYS work? Or do some instances remain hard
    even with perfect clone knowledge?
    """
    print("\n" + "=" * 70)
    print("ORACLE CLONE SOLVER: Perfect clones → SAT?")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16]:
        solved = 0; total = 0; k_vals = []

        for seed in range(100):
            clauses = random_3sat(n, int(4.27*n), seed=seed+950000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            total += 1

            # Perfect clone detection from solutions
            parent = list(range(n))
            def find(x):
                while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
                return x
            def union(a, b):
                a, b = find(a), find(b)
                if a != b: parent[a] = b

            clone_info = {}
            for i in range(n):
                for j in range(i+1, n):
                    same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                    if same > 0.9:
                        union(i, j); clone_info[(i,j)] = False
                    elif same < 0.1:
                        union(i, j); clone_info[(i,j)] = True

            clusters = {}
            for v in range(n):
                r = find(v)
                if r not in clusters: clusters[r] = []
                clusters[r].append(v)

            indeps = [min(c) for c in clusters.values()]
            k = len(indeps)
            k_vals.append(k)

            # Enumerate
            found = False
            for combo in range(2**k):
                fixed = {}
                for idx, var in enumerate(indeps):
                    fixed[var] = (combo >> idx) & 1
                # Propagate
                for (i,j), is_anti in clone_info.items():
                    if i in fixed and j not in fixed:
                        fixed[j] = (1-fixed[i]) if is_anti else fixed[i]
                    elif j in fixed and i not in fixed:
                        fixed[i] = (1-fixed[j]) if is_anti else fixed[j]
                for v in range(n):
                    if v not in fixed:
                        fixed[v] = 1 if bit_tension(clauses, n, v, fixed) >= 0 else 0

                if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                    found = True; break

            if found: solved += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"\n  n={n}: oracle clones → {solved}/{total} solved "
              f"({solved/total*100:.1f}%), avg k={mean(k_vals):.1f}")


if __name__ == "__main__":
    compare_methods()
    oracle_clone_solver()
