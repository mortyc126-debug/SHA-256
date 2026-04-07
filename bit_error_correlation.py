"""
Error Correlation — The missing term in our equations.

Two anomalies point here:
1. Amplification faster than predicted (errors removed in clusters)
2. Contradictions fewer than predicted (errors correlated, not independent)

Question: What is the STRUCTURE of error correlation?
Can we write an equation for it?
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


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None: fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                s = False; rem = []; vs = None
                for v, si in clause:
                    if v in fixed:
                        if (si==1 and fixed[v]==1) or (si==-1 and fixed[v]==0):
                            s = True; break
                    else: rem.append((v,si));
                    if v == var: vs = si
                if s or vs is None: continue
                oh = 0.0
                for v, si in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if si == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# 1. ERROR CORRELATION MATRIX
# ============================================================

def error_correlation_matrix(instances, n):
    """
    Across many instances, for each pair (i,j):
    Compute correlation of errors.

    error_i = 1 if v4 predicts wrong, 0 if correct.
    corr(error_i, error_j) across instances.
    """
    # Collect error vectors
    error_vectors = []

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        errors = [0] * n
        for var in range(n):
            pred = 1 if v4_t.get(var, 0) >= 0 else 0
            if pred != correct_val[var]:
                errors[var] = 1
        error_vectors.append(errors)

    # Compute correlation matrix
    n_inst = len(error_vectors)
    mean_err = [sum(ev[v] for ev in error_vectors)/n_inst for v in range(n)]

    corr_matrix = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            cov = sum((error_vectors[k][i] - mean_err[i]) *
                      (error_vectors[k][j] - mean_err[j])
                      for k in range(n_inst)) / n_inst
            std_i = math.sqrt(sum((error_vectors[k][i] - mean_err[i])**2
                                  for k in range(n_inst)) / n_inst)
            std_j = math.sqrt(sum((error_vectors[k][j] - mean_err[j])**2
                                  for k in range(n_inst)) / n_inst)
            if std_i > 0 and std_j > 0:
                corr_matrix[i][j] = cov / (std_i * std_j)
                corr_matrix[j][i] = corr_matrix[i][j]

    return corr_matrix, mean_err


# ============================================================
# 2. WITHIN-INSTANCE error correlation
# ============================================================

def within_instance_correlation(instances, n):
    """
    For a SINGLE instance: given that bit i is wrong,
    what's P(bit j is wrong)?

    But we only have one error vector per instance.
    Instead: across instances, when #wrong = k,
    are the k wrong bits clustered or spread?

    Measure: average graph distance between wrong bits.
    Compare to average distance between random k bits.
    """
    results = []

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        wrong = []
        for var in range(n):
            pred = 1 if v4_t.get(var, 0) >= 0 else 0
            if pred != correct_val[var]:
                wrong.append(var)

        if len(wrong) < 2:
            continue

        # Build adjacency and distances
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        def bfs_dist(start):
            dist = {start: 0}
            queue = [start]; idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr] + 1
                        queue.append(nb)
            return dist

        # Average distance between wrong bits
        wrong_dists = []
        for i in range(len(wrong)):
            d = bfs_dist(wrong[i])
            for j in range(i+1, len(wrong)):
                wrong_dists.append(d.get(wrong[j], n))

        avg_wrong_dist = sum(wrong_dists)/len(wrong_dists) if wrong_dists else 0

        # Average distance between random k bits
        random_dists_avg = []
        for _ in range(10):
            rnd = random.sample(range(n), len(wrong))
            rnd_dists = []
            for i in range(len(rnd)):
                d = bfs_dist(rnd[i])
                for j in range(i+1, len(rnd)):
                    rnd_dists.append(d.get(rnd[j], n))
            random_dists_avg.append(sum(rnd_dists)/len(rnd_dists) if rnd_dists else 0)

        avg_random_dist = sum(random_dists_avg)/len(random_dists_avg)

        results.append({
            'n_wrong': len(wrong),
            'avg_wrong_dist': avg_wrong_dist,
            'avg_random_dist': avg_random_dist,
            'clustering_ratio': avg_wrong_dist / avg_random_dist if avg_random_dist > 0 else 1,
        })

    return results


# ============================================================
# 3. ERROR PROPAGATION: does fixing a wrong bit CAUSE more errors?
# ============================================================

def error_propagation(instances, n):
    """
    Fix bit i with WRONG value. How many OTHER bits flip direction?
    Compare: fix with RIGHT value — how many flip?

    If wrong-fix causes MORE flips: errors propagate.
    """
    wrong_flips = []
    right_flips = []

    for clauses, solutions in instances[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            base_tensions = {v: bit_tension(clauses, n, v) for v in range(n) if v != var}

            # Fix WRONG
            wrong_val = 1 - correct_val[var]
            tensions_wrong = {v: bit_tension(clauses, n, v, {var: wrong_val})
                             for v in range(n) if v != var}

            # Fix RIGHT
            right_val = correct_val[var]
            tensions_right = {v: bit_tension(clauses, n, v, {var: right_val})
                             for v in range(n) if v != var}

            # Count direction flips
            wrong_flip_count = 0
            right_flip_count = 0
            for v in base_tensions:
                base_dir = 1 if base_tensions[v] >= 0 else 0
                wrong_dir = 1 if tensions_wrong[v] >= 0 else 0
                right_dir = 1 if tensions_right[v] >= 0 else 0

                if wrong_dir != base_dir:
                    wrong_flip_count += 1
                if right_dir != base_dir:
                    right_flip_count += 1

            wrong_flips.append(wrong_flip_count)
            right_flips.append(right_flip_count)

    return wrong_flips, right_flips


# ============================================================
# 4. THE CORRELATION EQUATION
# ============================================================

def derive_correlation_equation(instances, n):
    """
    Hypothesis: error correlation between bits i,j depends on:
    - Number of shared clauses (d_shared)
    - Sign agreement in shared clauses

    Measure the actual correlation as function of shared clauses.
    """
    # For each (shared_clauses, sign_pattern) → error correlation
    by_shared = {}

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        is_wrong = {}
        for var in range(n):
            pred = 1 if v4_t.get(var, 0) >= 0 else 0
            is_wrong[var] = 1 if pred != correct_val[var] else 0

        # Count shared clauses for each pair
        shared = [[0]*n for _ in range(n)]
        same_sign = [[0]*n for _ in range(n)]
        for clause in clauses:
            vs = [(v,s) for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    va, sa = vs[a]
                    vb, sb = vs[b]
                    shared[va][vb] += 1
                    shared[vb][va] += 1
                    if sa == sb:
                        same_sign[va][vb] += 1
                        same_sign[vb][va] += 1

        for i in range(n):
            for j in range(i+1, n):
                d = shared[i][j]
                if d not in by_shared:
                    by_shared[d] = {'both_wrong': 0, 'total': 0,
                                    'i_wrong': 0, 'j_wrong': 0,
                                    'same_sign_frac': []}
                by_shared[d]['total'] += 1
                if is_wrong[i]: by_shared[d]['i_wrong'] += 1
                if is_wrong[j]: by_shared[d]['j_wrong'] += 1
                if is_wrong[i] and is_wrong[j]: by_shared[d]['both_wrong'] += 1
                if d > 0:
                    by_shared[d]['same_sign_frac'].append(same_sign[i][j] / d)

    return by_shared


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(300):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")

    # --- Test 1: Cross-instance error correlation ---
    print("\n" + "=" * 70)
    print("1. ERROR CORRELATION MATRIX (cross-instance)")
    print("=" * 70)

    corr_matrix, mean_err = error_correlation_matrix(instances, n)

    # Statistics of off-diagonal correlations
    off_diag = []
    for i in range(n):
        for j in range(i+1, n):
            off_diag.append(corr_matrix[i][j])

    print(f"\n  Mean error rate per position: {sum(mean_err)/n:.3f}")
    print(f"  Off-diagonal correlations:")
    print(f"    Mean: {sum(off_diag)/len(off_diag):+.4f}")
    print(f"    Max:  {max(off_diag):+.4f}")
    print(f"    Min:  {min(off_diag):+.4f}")
    print(f"    Std:  {math.sqrt(sum((c-sum(off_diag)/len(off_diag))**2 for c in off_diag)/len(off_diag)):.4f}")

    pos_count = sum(1 for c in off_diag if c > 0.05)
    neg_count = sum(1 for c in off_diag if c < -0.05)
    print(f"    Significantly positive (>0.05): {pos_count}/{len(off_diag)}")
    print(f"    Significantly negative (<-0.05): {neg_count}/{len(off_diag)}")

    # --- Test 2: Within-instance clustering ---
    print("\n" + "=" * 70)
    print("2. WITHIN-INSTANCE: Are wrong bits closer in the graph?")
    print("=" * 70)

    wi_results = within_instance_correlation(instances, n)

    by_nwrong = {}
    for r in wi_results:
        k = r['n_wrong']
        if k not in by_nwrong:
            by_nwrong[k] = []
        by_nwrong[k].append(r['clustering_ratio'])

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'#wrong':>6} | {'clustering ratio':>16} | {'n':>5} | meaning")
    print("  " + "-" * 55)
    for k in sorted(by_nwrong.keys()):
        if len(by_nwrong[k]) < 5:
            continue
        cr = mean(by_nwrong[k])
        meaning = "CLUSTERED" if cr < 0.95 else ("SPREAD" if cr > 1.05 else "random")
        print(f"  {k:>6} | {cr:>16.3f} | {len(by_nwrong[k]):>5} | {meaning}")

    # --- Test 3: Error propagation ---
    print("\n" + "=" * 70)
    print("3. ERROR PROPAGATION: Wrong fix causes more flips?")
    print("=" * 70)

    wrong_flips, right_flips = error_propagation(instances, n)
    print(f"\n  Wrong fix flips {mean(wrong_flips):.2f} bits' directions")
    print(f"  Right fix flips {mean(right_flips):.2f} bits' directions")
    print(f"  Ratio: {mean(wrong_flips)/mean(right_flips):.2f}x")

    # --- Test 4: Correlation equation ---
    print("\n" + "=" * 70)
    print("4. ERROR CORRELATION vs SHARED CLAUSES")
    print("=" * 70)

    by_shared = derive_correlation_equation(instances, n)

    print(f"\n  {'shared':>6} | {'P(both)':>8} | {'P(i)*P(j)':>10} | "
          f"{'lift':>6} | {'n':>6} | {'same_sign':>9}")
    print("  " + "-" * 60)

    overall_p_wrong = sum(mean_err) / n

    for d in sorted(by_shared.keys()):
        data = by_shared[d]
        if data['total'] < 20:
            continue
        p_both = data['both_wrong'] / data['total']
        p_ind = (data['i_wrong']/data['total']) * (data['j_wrong']/data['total'])
        lift = p_both / p_ind if p_ind > 0 else 0
        ss = mean(data['same_sign_frac']) if data['same_sign_frac'] else 0

        print(f"  {d:>6} | {p_both:>8.4f} | {p_ind:>10.4f} | "
              f"{lift:>6.2f} | {data['total']:>6} | {ss:>9.3f}")
