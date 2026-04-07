"""
DEEP DIVE: Self-cancellation, cloning, and conditional visibility.

Three new properties from SHA-256 that work in SAT.
Can they IMPROVE our solvers? Can they EXTEND our theory?

1. Self-cancellation as SOLVER signal
2. Clone structure: what are the EFFECTIVE degrees of freedom?
3. Visibility gating: can we USE it for better ordering?
4. COMBINED: all new properties together
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


def get_neighbors(clauses, n, var):
    neighbors = set()
    for clause in clauses:
        vs = [v for v,s in clause]
        if var in vs:
            for v in vs:
                if v != var: neighbors.add(v)
    return neighbors


def self_cancel_score(clauses, n, var, fixed=None):
    """σ_i + avg(σ_neighbors). Low = self-cancelling = suspect."""
    if fixed is None: fixed = {}
    sigma = bit_tension(clauses, n, var, fixed)
    nbs = get_neighbors(clauses, n, var)
    nbs = [nb for nb in nbs if nb not in fixed]
    if not nbs: return abs(sigma)
    nb_avg = sum(bit_tension(clauses, n, nb, fixed) for nb in nbs) / len(nbs)
    return abs(sigma + nb_avg)


# ============================================================
# 1. Self-cancellation as FILTER and SOLVER signal
# ============================================================

def self_cancel_filter():
    """
    Use |σ + avg_neighbors| as confidence score.
    High = consistent with neighborhood = trust.
    Low = contradicts neighborhood = distrust.
    """
    print("=" * 70)
    print("1. SELF-CANCELLATION: As prediction filter")
    print("=" * 70)

    random.seed(42); n = 12

    # Per-bit accuracy with different filters
    results = {'all': [0,0], 'high_cancel': [0,0], 'low_cancel': [0,0]}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        scores = []
        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            sc = self_cancel_score(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]
            scores.append((var, sc, is_correct))

            results['all'][1] += 1
            if is_correct: results['all'][0] += 1

        median_sc = sorted([s[1] for s in scores])[n//2]

        for var, sc, is_correct in scores:
            if sc > median_sc:
                results['high_cancel'][1] += 1
                if is_correct: results['high_cancel'][0] += 1
            else:
                results['low_cancel'][1] += 1
                if is_correct: results['low_cancel'][0] += 1

    for name in results:
        c, t = results[name]
        print(f"  {name:>15}: {c/t*100:.1f}% ({c}/{t})")


# ============================================================
# 2. CLONE STRUCTURE: Find independent variables
# ============================================================

def clone_analysis():
    """
    37% of pairs are clones/anti-clones.
    This means many bits are redundant copies.

    Find the INDEPENDENT SET: minimal set of bits that determines all others.
    """
    print("\n" + "=" * 70)
    print("2. CLONE STRUCTURE: Effective degrees of freedom")
    print("=" * 70)

    random.seed(42); n = 12

    effective_dof = []
    clone_helps = 0; total_tested = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        # Build clone graph: connect bits that are >90% same or >90% opposite
        clone_pairs = set()
        anti_pairs = set()
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.9:
                    clone_pairs.add((i,j))
                elif same < 0.1:
                    anti_pairs.add((i,j))

        # Find connected components (clones form clusters)
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a,b):
            a,b = find(a), find(b)
            if a != b: parent[a] = b

        for i,j in clone_pairs:
            union(i, j)
        for i,j in anti_pairs:
            union(i, j)

        clusters = len(set(find(v) for v in range(n)))
        effective_dof.append(clusters)

        # Can we use clones to IMPROVE prediction?
        # If bit i is uncertain but its clone j is confident → use j's value
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            total_tested += 1
            sigma = tensions[var]

            # Find most confident clone/anti-clone
            best_clone_sigma = None
            is_anti = False
            for other in range(n):
                if other == var: continue
                if (var, other) in clone_pairs or (other, var) in clone_pairs:
                    if best_clone_sigma is None or abs(tensions[other]) > abs(best_clone_sigma):
                        best_clone_sigma = tensions[other]
                        is_anti = False
                elif (var, other) in anti_pairs or (other, var) in anti_pairs:
                    if best_clone_sigma is None or abs(tensions[other]) > abs(best_clone_sigma):
                        best_clone_sigma = tensions[other]
                        is_anti = True

            if best_clone_sigma is not None and abs(best_clone_sigma) > abs(sigma):
                # Clone is more confident → use its prediction
                if is_anti:
                    clone_pred = 0 if best_clone_sigma >= 0 else 1
                else:
                    clone_pred = 1 if best_clone_sigma >= 0 else 0

                if clone_pred == correct_val[var]:
                    clone_helps += 1
            else:
                if (1 if sigma >= 0 else 0) == correct_val[var]:
                    clone_helps += 1

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Average effective DOF: {mean(effective_dof):.1f} / {n}")
    print(f"  Clone-boosted accuracy: {clone_helps/total_tested*100:.1f}%")


# ============================================================
# 3. VISIBILITY GATING: Use revealing pairs for ordering
# ============================================================

def visibility_ordering():
    """
    If fixing bit i REVEALS bit j (|σ_j| doubles):
    Then fix i FIRST → j becomes easy.

    Ordering: fix bits that REVEAL the most others first.
    """
    print("\n" + "=" * 70)
    print("3. VISIBILITY-BASED ORDERING")
    print("=" * 70)

    random.seed(42); n = 12

    std_solved = 0; vis_solved = 0; total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
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

        # Visibility-ordered: fix bits that reveal the most
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break

            # For each candidate: how many bits would it REVEAL?
            best_var = None; best_score = -1
            for var in unfixed:
                sigma = bit_tension(clauses, n, var, fixed)
                val = 1 if sigma >= 0 else 0

                test_fixed = dict(fixed); test_fixed[var] = val
                reveals = 0
                for other in unfixed:
                    if other == var: continue
                    before = abs(bit_tension(clauses, n, other, fixed))
                    after = abs(bit_tension(clauses, n, other, test_fixed))
                    if before > 0.01 and after / before > 1.5:
                        reveals += 1

                # Score: combine confidence with reveal power
                score = abs(sigma) * 0.7 + reveals * 0.3
                if score > best_score:
                    best_score = score
                    best_var = var

            sigma = bit_tension(clauses, n, best_var, fixed)
            fixed[best_var] = 1 if sigma >= 0 else 0

        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            vis_solved += 1

    print(f"\n  Standard:   {std_solved}/{total} ({std_solved/total*100:.1f}%)")
    print(f"  Visibility: {vis_solved}/{total} ({vis_solved/total*100:.1f}%)")


# ============================================================
# 4. COMBINED: self-cancel + clones + visibility
# ============================================================

def combined_solver():
    """
    Best of all new properties:
    - Order by: |σ| × (1 + reveal_power) × non_cancellation
    - For uncertain bits: check clones for stronger signal
    """
    print("\n" + "=" * 70)
    print("4. COMBINED SOLVER: All new properties")
    print("=" * 70)

    random.seed(42); n = 12

    std_solved = 0; combined_solved = 0; total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
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

        # Combined: confidence × non-cancellation
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break

            best_var = None; best_score = -1
            for var in unfixed:
                sigma = bit_tension(clauses, n, var, fixed)
                sc = self_cancel_score(clauses, n, var, fixed)

                # Combined score: confident AND consistent with neighbors
                score = abs(sigma) * (0.5 + sc)
                if score > best_score:
                    best_score = score
                    best_var = var

            sigma = bit_tension(clauses, n, best_var, fixed)
            fixed[best_var] = 1 if sigma >= 0 else 0

            # Unit propagation
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

        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            combined_solved += 1

    print(f"\n  Standard: {std_solved}/{total} ({std_solved/total*100:.1f}%)")
    print(f"  Combined: {combined_solved}/{total} ({combined_solved/total*100:.1f}%)")
    print(f"  Delta:    {(combined_solved-std_solved)/total*100:+.1f}%")


# ============================================================
# 5. ACCURACY: Per-bit with self-cancel score
# ============================================================

def cancel_accuracy():
    """How much does self-cancellation improve per-bit accuracy?"""
    print("\n" + "=" * 70)
    print("5. PER-BIT: Self-cancel score as confidence")
    print("=" * 70)

    random.seed(42); n = 12

    correct_by_bucket = {}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            sc = self_cancel_score(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            # Bucket by self-cancel score
            bucket = round(sc * 5) / 5  # round to 0.2
            bucket = min(bucket, 1.0)
            if bucket not in correct_by_bucket:
                correct_by_bucket[bucket] = [0, 0]
            correct_by_bucket[bucket][1] += 1
            if is_correct: correct_by_bucket[bucket][0] += 1

    print(f"\n  {'|σ+nb|':>8} | {'accuracy':>8} | {'n':>6} | visual")
    print("  " + "-" * 45)
    for bucket in sorted(correct_by_bucket.keys()):
        c, t = correct_by_bucket[bucket]
        if t < 10: continue
        acc = c/t*100
        bar = "█" * int(acc/2)
        print(f"  {bucket:>8.1f} | {acc:>7.1f}% | {t:>6} | {bar}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    self_cancel_filter()
    clone_analysis()
    visibility_ordering()
    combined_solver()
    cancel_accuracy()
