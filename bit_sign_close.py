"""
CLOSING THE SIGN GAP: Can v4/self-cancel/multi-run predict clone signs?

Current: tension agreement → 60.6%.
Target: 85% for useful solver.

New approaches:
1. V4 agreement (iterative tension) — v4 better than v1 for bits, maybe for signs too?
2. Self-cancellation sign: SC(i) and SC(j) relationship → sign?
3. Multi-run voting: across 20 runs, how often do i,j agree? → sign
4. Contrastive: from SUCCESSFUL runs only
5. COMBINED: all signals together
"""

import random
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


def get_real_pairs(solutions, n, threshold=0.85):
    pairs = {}
    for i in range(n):
        for j in range(i+1, n):
            same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
            if same > threshold: pairs[(i,j)] = True   # clone
            elif same < (1-threshold): pairs[(i,j)] = False  # anti
    return pairs


# ============================================================
# ALL SIGN PREDICTORS
# ============================================================

def test_all_sign_predictors():
    random.seed(42); n = 12

    predictors = {
        'tension_agree': 0,     # σ_i, σ_j same sign?
        'v4_agree': 0,          # v4 tensions same sign?
        'multi_run': 0,         # >50% agreement across runs?
        'contrastive': 0,       # >50% agreement in SUCCESSFUL runs?
        'self_cancel': 0,       # SC_i × SC_j > 0?
        'combined_vote': 0,     # majority of all above
    }
    total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        real_pairs = get_real_pairs(solutions, n, 0.85)
        if not real_pairs: continue

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # V4 tensions
        v4_t = dict(tensions)
        for _ in range(10):
            new_t = {}
            for var in v4_t:
                push_1, push_0 = 0.0, 0.0
                for clause in clauses:
                    rem = []; vs = None
                    for v, s in clause: rem.append((v,s));
                    for v, s in rem:
                        if v == var: vs = s
                    if vs is None: continue
                    oh = 0.0
                    for v, s in rem:
                        if v == var: continue
                        t = v4_t.get(v, 0)
                        p = (1+t)/2 if s==1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs==1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in v4_t:
                v4_t[v] = 0.5*v4_t[v] + 0.5*new_t.get(v,0)

        # Multi-run crystallizations
        runs = [noisy_crystallize(clauses, n, 0.15) for _ in range(20)]
        success_runs = [r for r in runs if evaluate(clauses, r) == len(clauses)]

        # Self-cancellation scores
        sc = {}
        for var in range(n):
            nbs = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: nbs.add(v)
            nb_avg = sum(tensions[nb] for nb in nbs)/len(nbs) if nbs else 0
            sc[var] = tensions[var] + nb_avg

        for (i,j), is_clone in real_pairs.items():
            total += 1

            # 1. Tension agreement
            t_agree = (tensions[i] >= 0) == (tensions[j] >= 0)
            if t_agree == is_clone: predictors['tension_agree'] += 1

            # 2. V4 agreement
            v4_agree = (v4_t[i] >= 0) == (v4_t[j] >= 0)
            if v4_agree == is_clone: predictors['v4_agree'] += 1

            # 3. Multi-run agreement
            if runs:
                agree_count = sum(1 for r in runs if r[i] == r[j])
                mr_pred = agree_count > len(runs) / 2
                if mr_pred == is_clone: predictors['multi_run'] += 1

            # 4. Contrastive (success runs only)
            if success_runs:
                s_agree = sum(1 for r in success_runs if r[i] == r[j])
                c_pred = s_agree > len(success_runs) / 2
                if c_pred == is_clone: predictors['contrastive'] += 1
            else:
                if t_agree == is_clone: predictors['contrastive'] += 1

            # 5. Self-cancel sign
            sc_agree = (sc[i] > 0) == (sc[j] > 0)
            if sc_agree == is_clone: predictors['self_cancel'] += 1

            # 6. Combined vote
            votes_clone = 0
            if t_agree: votes_clone += 1
            if v4_agree: votes_clone += 1
            if runs and agree_count > len(runs)/2: votes_clone += 1
            if success_runs and s_agree > len(success_runs)/2: votes_clone += 2  # double weight
            if sc_agree: votes_clone += 1

            combined_pred = votes_clone >= 3
            if combined_pred == is_clone: predictors['combined_vote'] += 1

    print("=" * 70)
    print("SIGN PREDICTION: All methods compared")
    print("=" * 70)

    print(f"\n  Total clone pairs tested: {total}")
    print(f"\n  {'method':>20} | {'accuracy':>8} | {'gap to 85%':>10}")
    print("  " + "-" * 45)

    for name in sorted(predictors.keys(), key=lambda k: -predictors[k]):
        acc = predictors[name] / total * 100 if total > 0 else 0
        gap = 85 - acc
        marker = " ★" if acc > 75 else ""
        print(f"  {name:>20} | {acc:>7.1f}% | {gap:>+9.1f}%{marker}")


# ============================================================
# SOLVER with best sign predictor
# ============================================================

def sign_solver_best():
    print("\n" + "=" * 70)
    print("SOLVER: Using best sign predictor")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'contrastive_signs': 0, 'oracle': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue
        results['total'] += 1

        real_pairs = get_real_pairs(solutions, n, 0.85)

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Contrastive sign prediction
        runs = [noisy_crystallize(clauses, n, 0.15) for _ in range(30)]
        success_runs = [r for r in runs if evaluate(clauses, r) == len(clauses)]

        # Detect clones from runs (correlation > 0.85)
        predicted_pairs = {}
        for i in range(n):
            for j in range(i+1, n):
                if success_runs:
                    agree = sum(1 for r in success_runs if r[i] == r[j])
                    frac = agree / len(success_runs)
                    if frac > 0.85:
                        predicted_pairs[(i,j)] = False  # clone
                    elif frac < 0.15:
                        predicted_pairs[(i,j)] = True   # anti
                elif runs:
                    agree = sum(1 for r in runs if r[i] == r[j])
                    frac = agree / len(runs)
                    if frac > 0.85:
                        predicted_pairs[(i,j)] = False
                    elif frac < 0.15:
                        predicted_pairs[(i,j)] = True

        # Solve with contrastive-predicted pairs
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            a, b = find(a), find(b)
            if a != b: parent[a] = b

        for (i,j) in predicted_pairs: union(i,j)
        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)
        indeps = [min(c) for c in clusters.values()]
        k = len(indeps)

        found = False
        for combo in range(min(2**k, 50000)):
            fixed = {}
            for idx, var in enumerate(indeps):
                fixed[var] = (combo >> idx) & 1
            for (i,j), is_anti in predicted_pairs.items():
                if i in fixed and j not in fixed:
                    fixed[j] = (1-fixed[i]) if is_anti else fixed[i]
                elif j in fixed and i not in fixed:
                    fixed[i] = (1-fixed[j]) if is_anti else fixed[j]
            for v in range(n):
                if v not in fixed:
                    fixed[v] = 1 if bit_tension(clauses, n, v, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                found = True; break

        if found: results['contrastive_signs'] += 1

        # Oracle
        parent2 = list(range(n))
        def find2(x):
            while parent2[x] != x: parent2[x] = parent2[parent2[x]]; x = parent2[x]
            return x
        def union2(a,b):
            a,b = find2(a),find2(b)
            if a != b: parent2[a] = b
        for (i,j) in real_pairs: union2(i,j)
        clusters2 = {}
        for v in range(n):
            r = find2(v)
            if r not in clusters2: clusters2[r] = []
            clusters2[r].append(v)
        indeps2 = [min(c) for c in clusters2.values()]
        k2 = len(indeps2)
        found2 = False
        for combo in range(min(2**k2, 50000)):
            fixed = {}
            for idx, var in enumerate(indeps2):
                fixed[var] = (combo >> idx) & 1
            for (i,j), is_anti in real_pairs.items():
                if i in fixed and j not in fixed:
                    fixed[j] = (1-fixed[i]) if is_anti else fixed[i]
                elif j in fixed and i not in fixed:
                    fixed[i] = (1-fixed[j]) if is_anti else fixed[j]
            for v in range(n):
                if v not in fixed:
                    fixed[v] = 1 if bit_tension(clauses, n, v, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                found2 = True; break
        if found2: results['oracle'] += 1

    t = results['total']
    for name in ['standard', 'contrastive_signs', 'oracle']:
        pct = results[name]/t*100
        print(f"  {name:>20}: {results[name]}/{t} ({pct:.1f}%)")


if __name__ == "__main__":
    test_all_sign_predictors()
    sign_solver_best()
