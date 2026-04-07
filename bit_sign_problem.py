"""
CLONE SIGN PROBLEM: Can we guess clone vs anti-clone from clauses?

The ENTIRE hardness of SAT reduces to:
Given pairs (i,j) that are clones → determine sign (+/−).

30 pairs, each binary → 2^30 possibilities.
But we don't need ALL correct — even 80% correct helps.

Can clause structure predict the SIGN?
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
# 1. SIGN PREDICTORS: What clause features predict clone sign?
# ============================================================

def sign_predictors():
    print("=" * 70)
    print("1. Can clause features predict clone SIGN?")
    print("=" * 70)

    random.seed(42); n = 12

    # Collect: for each real clone pair, clause features + actual sign
    data = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same < 0.85 and same > 0.15: continue  # not a clone

                is_clone = same > 0.85  # True=clone, False=anti-clone

                # Feature 1: sign agreement in tension
                tension_agree = (tensions[i] >= 0) == (tensions[j] >= 0)

                # Feature 2: co-occurrence sign pattern
                # In shared clauses: do i and j appear with SAME sign or opposite?
                same_sign_count = 0
                diff_sign_count = 0
                for clause in clauses:
                    signs = {}
                    for v, s in clause:
                        if v == i or v == j:
                            signs[v] = s
                    if i in signs and j in signs:
                        if signs[i] == signs[j]:
                            same_sign_count += 1
                        else:
                            diff_sign_count += 1

                sign_balance = same_sign_count - diff_sign_count

                # Feature 3: self-cancellation agreement
                nbs_i = set()
                nbs_j = set()
                for clause in clauses:
                    vs = [v for v,s in clause]
                    if i in vs:
                        for v in vs:
                            if v != i: nbs_i.add(v)
                    if j in vs:
                        for v in vs:
                            if v != j: nbs_j.add(v)

                nb_overlap = len(nbs_i & nbs_j) / len(nbs_i | nbs_j) if nbs_i | nbs_j else 0

                # Feature 4: tension product
                tension_product = tensions[i] * tensions[j]

                data.append({
                    'is_clone': is_clone,
                    'tension_agree': tension_agree,
                    'sign_balance': sign_balance,
                    'nb_overlap': nb_overlap,
                    'tension_product': tension_product,
                })

    # Analyze each predictor
    print(f"\n  {len(data)} clone/anti-clone pairs found")
    print(f"  Clones: {sum(1 for d in data if d['is_clone'])}, "
          f"Anti: {sum(1 for d in data if not d['is_clone'])}")

    # Predictor 1: tension agreement
    ta_correct = sum(1 for d in data if d['tension_agree'] == d['is_clone'])
    print(f"\n  Tension agreement predicts sign: {ta_correct/len(data)*100:.1f}%")

    # Predictor 2: sign balance in shared clauses
    sb_correct = sum(1 for d in data if (d['sign_balance'] > 0) == d['is_clone'])
    print(f"  Clause sign balance predicts:   {sb_correct/len(data)*100:.1f}%")

    # Predictor 3: tension product > 0 → clone
    tp_correct = sum(1 for d in data if (d['tension_product'] > 0) == d['is_clone'])
    print(f"  Tension product predicts:       {tp_correct/len(data)*100:.1f}%")

    # Combined: majority vote of all three
    combined_correct = 0
    for d in data:
        votes = 0
        if d['tension_agree']: votes += 1
        if d['sign_balance'] > 0: votes += 1
        if d['tension_product'] > 0: votes += 1
        pred_clone = votes >= 2
        if pred_clone == d['is_clone']:
            combined_correct += 1
    print(f"  Combined (majority vote):       {combined_correct/len(data)*100:.1f}%")


# ============================================================
# 2. SIGN-AWARE CLONE SOLVER: predict sign, then solve
# ============================================================

def sign_aware_solver():
    print("\n" + "=" * 70)
    print("2. SIGN-AWARE SOLVER: Predict signs from clauses, then solve")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'sign_predicted': 0, 'oracle': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue
        results['total'] += 1

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Real clones
        real_pairs = {}
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.85:
                    real_pairs[(i,j)] = False  # clone
                elif same < 0.15:
                    real_pairs[(i,j)] = True  # anti

        # Predicted signs: use tension product
        predicted_pairs = {}
        for (i,j) in real_pairs:
            # Predict: same tension sign → clone, different → anti
            predicted_anti = (tensions[i] >= 0) != (tensions[j] >= 0)
            predicted_pairs[(i,j)] = predicted_anti

        # Solve with predicted signs
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            a, b = find(a), find(b)
            if a != b: parent[a] = b

        for (i,j) in predicted_pairs:
            union(i, j)

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

        if found: results['sign_predicted'] += 1

        # Oracle signs
        parent2 = list(range(n))
        def find2(x):
            while parent2[x] != x: parent2[x] = parent2[parent2[x]]; x = parent2[x]
            return x
        def union2(a, b):
            a, b = find2(a), find2(b)
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
    print(f"\n  Standard:                  {results['standard']}/{t} ({results['standard']/t*100:.1f}%)")
    print(f"  Sign-predicted clone solver: {results['sign_predicted']}/{t} ({results['sign_predicted']/t*100:.1f}%)")
    print(f"  Oracle clone solver:        {results['oracle']}/{t} ({results['oracle']/t*100:.1f}%)")


# ============================================================
# 3. HOW MANY SIGNS NEED TO BE CORRECT?
# ============================================================

def sign_accuracy_threshold():
    print("\n" + "=" * 70)
    print("3. How many signs must be correct to solve?")
    print("=" * 70)

    random.seed(42); n = 12

    print(f"\n  {'sign_acc':>8} | {'solved':>7} | {'rate':>6}")
    print("  " + "-" * 30)

    for accuracy_pct in [50, 60, 70, 80, 90, 100]:
        solved = 0; total = 0

        for seed in range(100):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions or len(solutions) < 2: continue
            total += 1

            real_pairs = {}
            for i in range(n):
                for j in range(i+1, n):
                    same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                    if same > 0.85: real_pairs[(i,j)] = False
                    elif same < 0.15: real_pairs[(i,j)] = True

            # Corrupt X% of signs
            pairs_list = list(real_pairs.items())
            n_correct = int(len(pairs_list) * accuracy_pct / 100)
            random.shuffle(pairs_list)
            corrupted = {}
            for idx, ((i,j), is_anti) in enumerate(pairs_list):
                if idx < n_correct:
                    corrupted[(i,j)] = is_anti  # correct
                else:
                    corrupted[(i,j)] = not is_anti  # flipped

            # Solve with corrupted signs
            parent = list(range(n))
            def find(x):
                while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
                return x
            def union(a, b):
                a, b = find(a), find(b)
                if a != b: parent[a] = b

            for (i,j) in corrupted: union(i,j)
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
                for (i,j), is_anti in corrupted.items():
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

        rate = solved/total*100 if total > 0 else 0
        print(f"  {accuracy_pct:>7}% | {solved:>3}/{total} | {rate:>5.1f}%")


if __name__ == "__main__":
    sign_predictors()
    sign_aware_solver()
    sign_accuracy_threshold()
