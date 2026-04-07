"""
GLOBAL LEVEL — Looking at the bit field as a whole.

Local properties exhausted. The 9.2% gap is invisible locally.
Now: graph structure, spectral properties, community detection,
solution space geometry.

Question: what GLOBAL property predicts which bits are in the gap?
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
    if fixed is None:
        fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False
        rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True; break
            else:
                rem.append((v, s))
        if sat:
            continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None:
        fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                s = False; rem = []; vs = None
                for v, si in clause:
                    if v in fixed:
                        if (si == 1 and fixed[v] == 1) or (si == -1 and fixed[v] == 0):
                            s = True; break
                    else:
                        rem.append((v, si))
                        if v == var: vs = si
                if s or vs is None: continue
                oh = 0.0
                for v, si in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if si == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0 - oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1 + push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


def build_adj(clauses, n):
    adj = [[0]*n for _ in range(n)]
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a+1, len(vs)):
                adj[vs[a]][vs[b]] += 1
                adj[vs[b]][vs[a]] += 1
    return adj


# ============================================================
# GLOBAL 1: Spectral analysis of constraint graph
# ============================================================

def spectral_analysis(clauses, n):
    """
    Compute eigenvalues of the adjacency matrix.
    Spectral gap, largest eigenvalue, and eigenvector alignment.
    """
    adj = build_adj(clauses, n)

    # Power iteration for largest eigenvalue and eigenvector
    vec = [random.gauss(0, 1) for _ in range(n)]
    norm = math.sqrt(sum(v*v for v in vec))
    vec = [v/norm for v in vec]

    for _ in range(100):
        new_vec = [0.0] * n
        for i in range(n):
            for j in range(n):
                new_vec[i] += adj[i][j] * vec[j]
        eigenvalue = math.sqrt(sum(v*v for v in new_vec))
        if eigenvalue > 0:
            vec = [v/eigenvalue for v in new_vec]

    # Second eigenvalue (deflate)
    v1 = list(vec)
    vec2 = [random.gauss(0, 1) for _ in range(n)]
    # Orthogonalize
    dot = sum(vec2[i]*v1[i] for i in range(n))
    vec2 = [vec2[i] - dot*v1[i] for i in range(n)]
    norm = math.sqrt(sum(v*v for v in vec2))
    if norm > 0:
        vec2 = [v/norm for v in vec2]

    for _ in range(100):
        new_vec = [0.0] * n
        for i in range(n):
            for j in range(n):
                new_vec[i] += adj[i][j] * vec2[j]
        # Orthogonalize against v1
        dot = sum(new_vec[i]*v1[i] for i in range(n))
        new_vec = [new_vec[i] - dot*v1[i] for i in range(n)]
        ev2 = math.sqrt(sum(v*v for v in new_vec))
        if ev2 > 0:
            vec2 = [v/ev2 for v in new_vec]

    return {
        'eigenvalue_1': eigenvalue,
        'eigenvalue_2': ev2,
        'spectral_gap': eigenvalue - ev2,
        'eigenvector_1': v1,
        'eigenvector_2': vec2,
    }


# ============================================================
# GLOBAL 2: Community detection (spectral bisection)
# ============================================================

def spectral_communities(eigenvector_2, n):
    """
    Split bits into two communities based on sign of 2nd eigenvector.
    This is the Fiedler vector approach.
    """
    community_A = [i for i in range(n) if eigenvector_2[i] >= 0]
    community_B = [i for i in range(n) if eigenvector_2[i] < 0]
    return community_A, community_B


# ============================================================
# GLOBAL 3: Cycle structure
# ============================================================

def count_short_cycles(clauses, n):
    """Count triangles and 4-cycles in constraint graph."""
    adj = build_adj(clauses, n)

    # Triangles
    triangles = 0
    for i in range(n):
        for j in range(i+1, n):
            if adj[i][j] == 0:
                continue
            for k in range(j+1, n):
                if adj[i][k] > 0 and adj[j][k] > 0:
                    triangles += 1

    # 4-cycles
    four_cycles = 0
    for i in range(n):
        for j in range(i+1, n):
            if adj[i][j] == 0:
                continue
            # Count common non-neighbors that connect through 2 steps
            for k in range(n):
                if k == i or k == j:
                    continue
                if adj[i][k] > 0:
                    for l in range(k+1, n):
                        if l == i or l == j:
                            continue
                        if adj[k][l] > 0 and adj[j][l] > 0 and adj[i][l] == 0:
                            four_cycles += 1

    return triangles, four_cycles


# ============================================================
# GLOBAL 4: Solution space geometry
# ============================================================

def solution_geometry(solutions, n):
    """
    Analyze the shape of the solution cluster.
    - Diameter (max pairwise Hamming distance)
    - Centroid (average solution)
    - Principal direction (which bits vary most across solutions)
    """
    if len(solutions) < 2:
        return None

    # Centroid
    centroid = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

    # Variance per bit
    bit_variance = [centroid[v] * (1 - centroid[v]) for v in range(n)]

    # Principal axis: which bits have highest variance?
    # These are the "ambiguous" dimensions of the solution cluster
    sorted_by_var = sorted(range(n), key=lambda v: -bit_variance[v])
    high_var_bits = sorted_by_var[:n//3]
    low_var_bits = sorted_by_var[2*n//3:]

    # Diameter
    max_dist = 0
    for i in range(len(solutions)):
        for j in range(i+1, len(solutions)):
            d = sum(solutions[i][k] != solutions[j][k] for k in range(n))
            max_dist = max(max_dist, d)

    # Correlation between bits in solution space
    # (different from clause-graph correlation)
    sol_correlations = []
    for i in range(n):
        for j in range(i+1, n):
            if bit_variance[i] < 0.01 or bit_variance[j] < 0.01:
                continue
            cov = sum((solutions[s][i]-centroid[i])*(solutions[s][j]-centroid[j])
                      for s in range(len(solutions))) / len(solutions)
            corr = cov / math.sqrt(bit_variance[i]*bit_variance[j])
            sol_correlations.append((i, j, corr))

    return {
        'centroid': centroid,
        'bit_variance': bit_variance,
        'high_var_bits': high_var_bits,
        'low_var_bits': low_var_bits,
        'diameter': max_dist,
        'sol_correlations': sol_correlations,
    }


# ============================================================
# GLOBAL 5: Does global position predict gap?
# ============================================================

def global_gap_analysis(clauses, n, solutions):
    """
    For each bit: compute its GLOBAL properties
    (eigenvector position, community, cycle membership, solution variance)
    and check if gap bits differ.
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    v4_t = tension_v4(clauses, n, {}, 10)
    spec = spectral_analysis(clauses, n)
    comm_A, comm_B = spectral_communities(spec['eigenvector_2'], n)
    geom = solution_geometry(solutions, n)
    triangles_per_bit = count_triangles_per_bit(clauses, n)

    gap_profiles = []
    correct_profiles = []

    for var in range(n):
        v4_pred = 1 if v4_t.get(var, 0) >= 0 else 0
        actual = correct_val[var]
        optimal = max(prob_1[var], 1-prob_1[var])

        profile = {
            'eigenvector_1_pos': abs(spec['eigenvector_1'][var]),
            'eigenvector_2_pos': abs(spec['eigenvector_2'][var]),
            'community': 0 if var in comm_A else 1,
            'solution_variance': geom['bit_variance'][var] if geom else 0,
            'is_high_var': 1 if var in (geom['high_var_bits'] if geom else []) else 0,
            'triangles': triangles_per_bit[var],
            'centroid_distance': abs(prob_1[var] - 0.5),
        }

        if v4_pred == actual:
            correct_profiles.append(profile)
        elif optimal > 0.6:
            gap_profiles.append(profile)

    return correct_profiles, gap_profiles


def count_triangles_per_bit(clauses, n):
    adj = build_adj(clauses, n)
    counts = [0] * n
    for i in range(n):
        for j in range(i+1, n):
            if adj[i][j] == 0:
                continue
            for k in range(j+1, n):
                if adj[i][k] > 0 and adj[j][k] > 0:
                    counts[i] += 1
                    counts[j] += 1
                    counts[k] += 1
    return counts


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    print("=" * 75)
    print("GLOBAL LEVEL ANALYSIS")
    print("=" * 75)

    # Global properties across ratios
    print("\n## Graph-level properties by ratio")
    print(f"{'ratio':>6} | {'λ1':>6} | {'λ2':>6} | {'gap':>6} | "
          f"{'triangles':>9} | {'4-cycles':>8} | {'diameter':>8}")
    print("-" * 65)

    for ratio_10 in range(20, 50, 5):
        ratio = ratio_10 / 10.0
        ev1s, ev2s, gaps, tris, fours, diams = [], [], [], [], [], []

        for seed in range(50):
            clauses = random_3sat(n, int(ratio*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions or len(solutions) < 2:
                continue

            spec = spectral_analysis(clauses, n)
            ev1s.append(spec['eigenvalue_1'])
            ev2s.append(spec['eigenvalue_2'])
            gaps.append(spec['spectral_gap'])

            t, f = count_short_cycles(clauses, n)
            tris.append(t)
            fours.append(f)

            geom = solution_geometry(solutions, n)
            if geom:
                diams.append(geom['diameter'])

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"{ratio:>6.1f} | {mean(ev1s):>6.2f} | {mean(ev2s):>6.2f} | "
              f"{mean(gaps):>6.2f} | {mean(tris):>9.1f} | "
              f"{mean(fours):>8.1f} | {mean(diams):>8.1f}")

    # Gap analysis with global properties
    print("\n" + "=" * 75)
    print("GLOBAL GAP ANALYSIS: Do global properties predict the 9% gap?")
    print("=" * 75)

    all_correct = []
    all_gap = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue

        result = global_gap_analysis(clauses, n, solutions)
        if result:
            correct, gap = result
            all_correct.extend(correct)
            all_gap.extend(gap)

    if all_correct and all_gap:
        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        props = list(all_correct[0].keys())

        print(f"\n  {len(all_correct)} correct, {len(all_gap)} gap bits")
        print(f"\n  {'property':>25} | {'CORRECT':>10} | {'GAP':>10} | "
              f"{'ratio':>7} | sig")
        print("  " + "-" * 75)

        for prop in props:
            c = mean([p[prop] for p in all_correct])
            g = mean([p[prop] for p in all_gap])
            if abs(c) > 0.001:
                ratio = g / c
            elif abs(g) > 0.001:
                ratio = 999
            else:
                ratio = 1.0

            sig = ""
            if ratio > 1.5 or ratio < 0.67:
                sig = "*** STRONG ***"
            elif ratio > 1.2 or ratio < 0.83:
                sig = "* notable *"

            print(f"  {prop:>25} | {c:>10.4f} | {g:>10.4f} | "
                  f"{ratio:>7.2f} | {sig}")

    # Community analysis
    print("\n" + "=" * 75)
    print("COMMUNITY: Do gap bits concentrate in one community?")
    print("=" * 75)

    comm_gap = {0: 0, 1: 0}
    comm_correct = {0: 0, 1: 0}

    for p in all_correct:
        comm_correct[p['community']] += 1
    for p in all_gap:
        comm_gap[p['community']] += 1

    for c in [0, 1]:
        total_c = comm_correct[c] + comm_gap[c]
        if total_c > 0:
            gap_frac = comm_gap[c] / total_c
            print(f"  Community {c}: {comm_gap[c]} gap / {total_c} total = "
                  f"{gap_frac*100:.1f}% gap")
