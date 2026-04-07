"""
THE MISMATCH TENSOR — Formalizing the gap between clause space and solution space.

Lift 1.20 is NOT from:
- Sign independence (gives 1.00)
- Solution correlations (gives 1.02)
- Any single-space property

It IS from: the RELATIONSHIP between two spaces.
Clause space says one thing, solution space says another.
Where they disagree — errors cluster.

Let's formalize this and measure the mismatch directly.
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
# Define the MISMATCH for each bit
# ============================================================

def mismatch_vector(clauses, n, solutions):
    """
    For each bit:
    - clause_direction: sign(σ) — what clauses say
    - solution_direction: sign(P(=1) - 0.5) — what solutions say
    - mismatch: when these disagree

    The MISMATCH VECTOR M ∈ {0,1}^n where M_i = 1 if clause ≠ solution.
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

    mismatches = []
    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        clause_dir = 1 if sigma >= 0 else 0
        sol_dir = 1 if prob_1[var] > 0.5 else 0
        mismatch = 1 if clause_dir != sol_dir else 0

        mismatches.append({
            'var': var,
            'mismatch': mismatch,
            'sigma': sigma,
            'prob_1': prob_1[var],
            'clause_confidence': abs(sigma),
            'solution_confidence': abs(prob_1[var] - 0.5),
            'gap': sigma - (2*prob_1[var] - 1),  # difference between clause and solution signals
        })

    return mismatches


# ============================================================
# PAIRWISE MISMATCH: are mismatches correlated?
# ============================================================

def pairwise_mismatch_correlation(instances, n):
    """
    For each pair (i,j):
    P(both mismatch) vs P(i mismatch) × P(j mismatch)

    THIS should give the lift = 1.20.
    Then decompose: WHY are mismatches correlated?
    """
    shared_both = 0
    shared_total = 0
    unshared_both = 0
    unshared_total = 0
    p_mismatch_count = 0
    p_mismatch_total = 0

    # Also track: the GAP signal correlation
    shared_gap_corrs = []
    unshared_gap_corrs = []

    for clauses, solutions in instances:
        mm = mismatch_vector(clauses, n, solutions)
        if mm is None: continue

        # Shared pairs
        shared_pairs = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    shared_pairs.add((min(vs[a],vs[b]), max(vs[a],vs[b])))

        for i in range(n):
            for j in range(i+1, n):
                is_shared = (i,j) in shared_pairs

                mi = mm[i]['mismatch']
                mj = mm[j]['mismatch']

                p_mismatch_total += 2
                p_mismatch_count += mi + mj

                if is_shared:
                    shared_total += 1
                    if mi and mj: shared_both += 1
                else:
                    unshared_total += 1
                    if mi and mj: unshared_both += 1

                # Gap correlation
                gi = mm[i]['gap']
                gj = mm[j]['gap']
                if is_shared:
                    shared_gap_corrs.append(gi * gj)
                else:
                    unshared_gap_corrs.append(gi * gj)

    p_mismatch = p_mismatch_count / p_mismatch_total if p_mismatch_total > 0 else 0

    shared_lift = (shared_both/shared_total) / (p_mismatch**2) if shared_total > 0 and p_mismatch > 0 else 0
    unshared_lift = (unshared_both/unshared_total) / (p_mismatch**2) if unshared_total > 0 and p_mismatch > 0 else 0

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    return {
        'p_mismatch': p_mismatch,
        'shared_lift': shared_lift,
        'unshared_lift': unshared_lift,
        'shared_gap_corr': mean(shared_gap_corrs),
        'unshared_gap_corr': mean(unshared_gap_corrs),
    }


# ============================================================
# The GAP FIELD: σ_clause - σ_solution for each bit
# ============================================================

def gap_field_analysis(instances, n):
    """
    gap_i = σ_i(clauses) - (2·P(i=1 in solutions) - 1)

    This is the "mismatch field." When gap ≠ 0, clause and solution
    disagree about bit i's preference.

    Properties of the gap field:
    - Mean: should be near 0 (both signals agree on average)
    - Variance: how much disagreement?
    - Spatial correlation: do nearby bits have similar gaps?
    """
    gap_means = []
    gap_vars = []
    gap_neighbor_corrs = []

    for clauses, solutions in instances:
        mm = mismatch_vector(clauses, n, solutions)
        if mm is None: continue

        gaps = [m['gap'] for m in mm]
        mean_g = sum(gaps)/len(gaps)
        var_g = sum((g-mean_g)**2 for g in gaps)/len(gaps)

        gap_means.append(mean_g)
        gap_vars.append(var_g)

        # Neighbor gap correlation
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        for i in range(n):
            for j in adj[i]:
                if j > i:
                    gap_neighbor_corrs.append(gaps[i] * gaps[j])

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    return {
        'gap_mean': mean(gap_means),
        'gap_variance': mean(gap_vars),
        'gap_neighbor_product': mean(gap_neighbor_corrs),
    }


# ============================================================
# KEY TEST: Is the gap field SPATIALLY correlated?
# ============================================================

def gap_spatial_correlation(instances, n):
    """
    If the gap field is spatially correlated:
    → nearby bits have SIMILAR gap
    → when one bit's clause signal is wrong, neighbors' are too
    → THIS would explain the lift

    The gap is the UNEXPLAINED part of tension.
    If it's correlated → errors are correlated → lift > 1.
    """
    by_distance = {1: [], 2: [], 3: []}

    for clauses, solutions in instances:
        mm = mismatch_vector(clauses, n, solutions)
        if mm is None: continue

        gaps = [m['gap'] for m in mm]

        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        # BFS distances
        for start in range(n):
            dist = {start: 0}
            queue = [start]; idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr]+1
                        queue.append(nb)

            for end in range(start+1, n):
                d = dist.get(end, 99)
                if d in by_distance:
                    by_distance[d].append(gaps[start] * gaps[end])

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    return by_distance


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
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")

    # --- Pairwise mismatch ---
    print("\n" + "=" * 70)
    print("PAIRWISE MISMATCH CORRELATION")
    print("=" * 70)

    result = pairwise_mismatch_correlation(instances, n)
    print(f"\n  P(mismatch per bit) = {result['p_mismatch']:.4f}")
    print(f"  Shared clause lift:   {result['shared_lift']:.3f}")
    print(f"  Unshared clause lift: {result['unshared_lift']:.3f}")
    print(f"  Shared gap product:   {result['shared_gap_corr']:.6f}")
    print(f"  Unshared gap product: {result['unshared_gap_corr']:.6f}")

    # --- Gap field ---
    print("\n" + "=" * 70)
    print("GAP FIELD: σ_clause - σ_solution")
    print("=" * 70)

    gf = gap_field_analysis(instances, n)
    print(f"\n  Gap mean:          {gf['gap_mean']:.6f}")
    print(f"  Gap variance:      {gf['gap_variance']:.6f}")
    print(f"  Gap neighbor corr: {gf['gap_neighbor_product']:.6f}")

    if gf['gap_neighbor_product'] > 0:
        print(f"  → Gap is POSITIVELY correlated between neighbors")
        print(f"  → Clause-solution mismatch is SPATIALLY COHERENT")
    else:
        print(f"  → Gap is negatively correlated or zero")

    # --- Spatial correlation by distance ---
    print("\n" + "=" * 70)
    print("GAP SPATIAL CORRELATION BY DISTANCE")
    print("=" * 70)

    by_dist = gap_spatial_correlation(instances, n)
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  {'distance':>8} | {'gap product':>11} | {'n':>7} | meaning")
    print("  " + "-" * 50)
    for d in [1, 2, 3]:
        vals = by_dist.get(d, [])
        gp = mean(vals)
        meaning = "CORRELATED" if gp > 0.001 else ("anti-correlated" if gp < -0.001 else "independent")
        print(f"  {d:>8} | {gp:>11.6f} | {len(vals):>7} | {meaning}")

    # --- Is gap correlation the SAME as lift?
    print("\n" + "=" * 70)
    print("CONNECTION: Gap correlation → Error lift")
    print("=" * 70)

    # If gap_product at distance 1 > 0:
    # When one bit's tension is wrong, its neighbor's tension is ALSO
    # wrong in the same direction. This creates error correlation = lift.

    # The lift should be: 1 + gap_corr / (gap_variance × P(mismatch))
    gp_d1 = mean(by_dist.get(1, []))
    gv = gf['gap_variance']
    pm = result['p_mismatch']

    if gv > 0 and pm > 0:
        predicted_lift = 1 + gp_d1 / (gv * pm * pm)
        print(f"\n  Predicted lift from gap correlation:")
        print(f"    gap_product(d=1) / (gap_var × P(mm)²)")
        print(f"    = {gp_d1:.6f} / ({gv:.6f} × {pm:.4f}²)")
        print(f"    = {predicted_lift:.3f}")
        print(f"  Measured lift: 1.20")
