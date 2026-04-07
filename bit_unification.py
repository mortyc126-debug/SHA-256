"""
UNIFICATION: Are clones and eigenmodes THE SAME THING?

Clone structure → k ≈ n/3 independent bits
Eigenmodes → k ≈ n/3 modes for 85% accuracy
Same number. Coincidence or identity?

Tests:
1. Do clone GROUPS align with eigenmode PROJECTIONS?
2. Do INDEPENDENT bits span the same subspace as top eigenmodes?
3. If we project onto clone basis vs eigenmode basis — same accuracy?
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


def build_signed_laplacian(clauses, n):
    L = [[0.0]*n for _ in range(n)]
    for clause in clauses:
        lits = [(v,s) for v,s in clause]
        for a in range(len(lits)):
            for b in range(a+1, len(lits)):
                vi,si = lits[a]; vj,sj = lits[b]
                sw = 1.0 if si==sj else -1.0
                L[vi][vj] -= sw; L[vj][vi] -= sw
                L[vi][vi] += abs(sw); L[vj][vj] += abs(sw)
    return L


def power_iteration(matrix, n, k, n_iter=200):
    vectors = []; eigenvalues = []
    residual = [row[:] for row in matrix]
    for idx in range(k):
        vec = [random.gauss(0,1) for _ in range(n)]
        norm = math.sqrt(sum(v*v for v in vec))
        vec = [v/norm for v in vec]
        for _ in range(n_iter):
            new = [sum(residual[i][j]*vec[j] for j in range(n)) for i in range(n)]
            for prev in vectors:
                dot = sum(new[i]*prev[i] for i in range(n))
                new = [new[i]-dot*prev[i] for i in range(n)]
            ev = math.sqrt(sum(v*v for v in new))
            if ev > 1e-10: vec = [v/ev for v in new]
        vectors.append(vec); eigenvalues.append(ev)
        for i in range(n):
            for j in range(n):
                residual[i][j] -= ev*vec[i]*vec[j]
    return eigenvalues, vectors


# ============================================================
# 1. Do clone groups align with eigenmode structure?
# ============================================================

def clone_eigenmode_alignment():
    """
    Clone groups: bits that always agree in solutions.
    Eigenmodes: basis vectors of signed Laplacian.

    If clones = eigenmodes: bits in same clone group should have
    SIMILAR coordinates in eigenmode space.

    Measure: within-group variance vs between-group variance
    of eigenmode coordinates.
    """
    print("=" * 70)
    print("1. Do clone groups align with eigenmodes?")
    print("=" * 70)

    random.seed(42); n = 12

    alignment_scores = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        # Clone groups
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a,b):
            a,b = find(a),find(b)
            if a != b: parent[a] = b

        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.85 or same < 0.15:
                    union(i, j)

        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)

        if len(clusters) == n: continue  # no clones

        # Eigenmodes
        L = build_signed_laplacian(clauses, n)
        eigenvalues, vectors = power_iteration(L, n, 4)

        # For each eigenmode: measure within-group vs between-group variance
        for mode_idx in range(min(4, len(vectors))):
            coords = vectors[mode_idx]

            # Within-group variance
            within = []
            for cluster in clusters.values():
                if len(cluster) < 2: continue
                cluster_coords = [coords[v] for v in cluster]
                mean_c = sum(cluster_coords) / len(cluster_coords)
                for c in cluster_coords:
                    within.append((c - mean_c)**2)

            # Between-group variance
            group_means = []
            for cluster in clusters.values():
                cluster_coords = [coords[v] for v in cluster]
                group_means.append(sum(cluster_coords)/len(cluster_coords))

            if not within or not group_means: continue

            overall_mean = sum(group_means)/len(group_means)
            between = [len(clusters[r]) * (m - overall_mean)**2
                      for r, m in zip(clusters.keys(), group_means)]

            var_within = sum(within)/len(within) if within else 0
            var_between = sum(between)/len(between) if between else 0

            if var_within + var_between > 0:
                # F-ratio: high = groups are well-separated in eigenspace
                f_ratio = var_between / (var_within + 0.001)
                alignment_scores.append(f_ratio)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  F-ratio (between/within group variance in eigenspace):")
    print(f"  Average: {mean(alignment_scores):.4f}")
    print(f"  (>1 = groups ARE aligned with eigenmodes)")
    print(f"  (<1 = groups NOT aligned)")


# ============================================================
# 2. Same subspace? Overlap between clone basis and eigenmode basis
# ============================================================

def subspace_overlap():
    """
    Clone basis: indicator vectors for each clone group.
    Eigenmode basis: top-k eigenvectors.

    Overlap = how much of clone basis is INSIDE eigenmode subspace.
    If 100%: they span the same space.
    """
    print("\n" + "=" * 70)
    print("2. SUBSPACE OVERLAP: Clone basis vs Eigenmode basis")
    print("=" * 70)

    random.seed(42); n = 12

    overlaps = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        # Clone groups → indicator vectors
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a,b):
            a,b = find(a),find(b)
            if a != b: parent[a] = b

        clone_info = {}
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.85: union(i,j); clone_info[(i,j)] = 1
                elif same < 0.15: union(i,j); clone_info[(i,j)] = -1

        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)

        n_indep = len(clusters)
        if n_indep == n: continue

        # Clone indicator vectors: for each group, vector with ±1 for members
        clone_vectors = []
        for root, members in clusters.items():
            vec = [0.0]*n
            for m in members:
                vec[m] = 1.0  # same sign within group (simplification)
            norm = math.sqrt(sum(v*v for v in vec))
            if norm > 0: vec = [v/norm for v in vec]
            clone_vectors.append(vec)

        # Eigenmode vectors
        L = build_signed_laplacian(clauses, n)
        k = min(n_indep, 6)
        eigenvalues, eigvecs = power_iteration(L, n, k)

        # Overlap: for each clone vector, project onto eigenspace
        total_overlap = 0
        for cv in clone_vectors:
            # Projection onto eigenspace
            proj_sq = 0
            for ev in eigvecs:
                dot = sum(cv[i]*ev[i] for i in range(n))
                proj_sq += dot**2
            # proj_sq / |cv|² = fraction of clone vector IN eigenspace
            cv_sq = sum(v*v for v in cv)
            if cv_sq > 0:
                total_overlap += proj_sq / cv_sq

        avg_overlap = total_overlap / len(clone_vectors) if clone_vectors else 0
        overlaps.append(avg_overlap)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Average overlap (clone vectors projected onto eigenspace): {mean(overlaps):.4f}")
    print(f"  (1.0 = identical subspaces, 0.0 = orthogonal)")


# ============================================================
# 3. ACCURACY COMPARISON: clone basis vs eigenmode basis
# ============================================================

def basis_comparison():
    """
    Reconstruct solution from:
    A. Clone basis (independent bits → propagate)
    B. Eigenmode basis (project → reconstruct)
    C. Both combined

    Same number of "dimensions" (k ≈ n/3). Same accuracy?
    """
    print("\n" + "=" * 70)
    print("3. ACCURACY: Clone basis vs Eigenmode basis")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'clone': [], 'eigen': [], 'combined': []}

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        sol_vec = [2*correct_val[v]-1 for v in range(n)]

        # Clone basis reconstruction
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a,b):
            a,b = find(a),find(b)
            if a != b: parent[a] = b

        clone_info = {}
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.85: union(i,j); clone_info[(i,j)] = False
                elif same < 0.15: union(i,j); clone_info[(i,j)] = True

        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)

        indeps = [min(c) for c in clusters.values()]
        k_clone = len(indeps)

        # Clone reconstruction: set independents to correct, propagate
        clone_recon = [0]*n
        for v in indeps:
            clone_recon[v] = correct_val[v]
        for (i,j), is_anti in clone_info.items():
            if i in indeps and clone_recon[i] is not None:
                clone_recon[j] = (1-clone_recon[i]) if is_anti else clone_recon[i]
            elif j in indeps and clone_recon[j] is not None:
                clone_recon[i] = (1-clone_recon[j]) if is_anti else clone_recon[j]
        # Fill remaining
        for v in range(n):
            if clone_recon[v] is None: clone_recon[v] = correct_val[v]

        clone_acc = sum(1 for v in range(n) if clone_recon[v] == correct_val[v]) / n

        # Eigenmode reconstruction
        L = build_signed_laplacian(clauses, n)
        eigenvalues, vectors = power_iteration(L, n, k_clone)

        eigen_recon = [0.0]*n
        for mode in range(min(k_clone, len(vectors))):
            proj = sum(sol_vec[i]*vectors[mode][i] for i in range(n))
            for i in range(n):
                eigen_recon[i] += proj * vectors[mode][i]

        eigen_acc = sum(1 for v in range(n)
                       if (1 if eigen_recon[v] >= 0 else 0) == correct_val[v]) / n

        results['clone'].append(clone_acc)
        results['eigen'].append(eigen_acc)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Same k ≈ n/3 dimensions:")
    print(f"  Clone basis:     {mean(results['clone'])*100:.1f}%")
    print(f"  Eigenmode basis: {mean(results['eigen'])*100:.1f}%")

    diff = abs(mean(results['clone']) - mean(results['eigen'])) * 100
    if diff < 3:
        print(f"  Difference: {diff:.1f}% — EFFECTIVELY THE SAME ★")
    else:
        print(f"  Difference: {diff:.1f}%")


if __name__ == "__main__":
    clone_eigenmode_alignment()
    subspace_overlap()
    basis_comparison()
