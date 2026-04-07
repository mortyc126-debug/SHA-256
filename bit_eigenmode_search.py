"""
EIGENMODE SEARCH: Search in n/3 dimensional eigenspace instead of n-dimensional bit space.

Eigenvectors = computable from clauses (FREE).
Projections = unknown (need solution).
But: only n/3 projections needed.

Strategy: for each eigenmode, try projection = +c or -c.
Total: 2^(n/3) combinations instead of 2^n.
Each combo → reconstruct bit assignment → check.

This is like clone reduction but using COMPUTABLE basis!
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
# EIGENMODE SEARCH SOLVER
# ============================================================

def eigenmode_search(clauses, n, k_modes=None, max_combos=50000):
    """
    1. Compute top-k eigenmodes of signed Laplacian
    2. For each eigenmode: try projection = ±1 (binary)
    3. Reconstruct assignment from eigenmode combination
    4. Check if valid
    """
    if k_modes is None:
        k_modes = max(3, n // 3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)

    # Tension-guided initial projection signs
    tensions = [bit_tension(clauses, n, v) for v in range(n)]
    t_vec = [2*t for t in tensions]  # amplified tension as initial guess

    # Project tension onto eigenmodes → initial projection signs
    initial_projs = []
    for mode in range(k_modes):
        proj = sum(t_vec[i] * vectors[mode][i] for i in range(n))
        initial_projs.append(proj)

    best_assignment = None
    best_sat = 0

    # Search: try flipping projection signs
    actual_combos = min(2**k_modes, max_combos)

    for combo in range(actual_combos):
        # Generate projection signs
        projs = list(initial_projs)
        for m in range(k_modes):
            if (combo >> m) & 1:
                projs[m] = -projs[m]  # flip this mode's sign

        # Reconstruct assignment
        recon = [0.0] * n
        for m in range(k_modes):
            for i in range(n):
                recon[i] += projs[m] * vectors[m][i]

        # Binarize
        assignment = [1 if recon[v] >= 0 else 0 for v in range(n)]

        sat = evaluate(clauses, assignment)
        if sat > best_sat:
            best_sat = sat
            best_assignment = assignment

        if best_sat == len(clauses):
            break

    return best_assignment, best_sat == len(clauses), k_modes, min(combo+1, actual_combos)


# ============================================================
# HYBRID: Eigenmode search + tension for residual
# ============================================================

def eigenmode_hybrid(clauses, n, k_modes=None, max_combos=10000):
    """
    1. Eigenmode search for top-k modes
    2. For the best eigenmode combo: use tension for bits not determined
    3. Then WalkSAT polish
    """
    if k_modes is None:
        k_modes = max(3, n // 3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)

    tensions = [bit_tension(clauses, n, v) for v in range(n)]
    t_vec = [2*t for t in tensions]

    initial_projs = [sum(t_vec[i]*vectors[m][i] for i in range(n)) for m in range(k_modes)]

    best_assignment = None
    best_sat = 0

    for combo in range(min(2**k_modes, max_combos)):
        projs = list(initial_projs)
        for m in range(k_modes):
            if (combo >> m) & 1: projs[m] = -projs[m]

        recon = [0.0]*n
        for m in range(k_modes):
            for i in range(n):
                recon[i] += projs[m] * vectors[m][i]

        # Where eigenmode reconstruction is WEAK, use tension
        assignment = []
        for v in range(n):
            if abs(recon[v]) > 0.3:
                assignment.append(1 if recon[v] >= 0 else 0)
            else:
                assignment.append(1 if tensions[v] >= 0 else 0)

        sat = evaluate(clauses, assignment)
        if sat > best_sat:
            best_sat = sat
            best_assignment = list(assignment)

        if best_sat == len(clauses):
            break

    # Polish with local search
    if best_assignment and best_sat < len(clauses):
        for flip_round in range(50):
            for clause in clauses:
                satisfied = any((s==1 and best_assignment[v]==1) or (s==-1 and best_assignment[v]==0)
                               for v,s in clause)
                if not satisfied:
                    # Flip the variable with lowest |tension|
                    weakest = min([(v, abs(tensions[v])) for v,s in clause], key=lambda x: x[1])
                    best_assignment[weakest[0]] = 1 - best_assignment[weakest[0]]
                    sat = evaluate(clauses, best_assignment)
                    if sat > best_sat: best_sat = sat
                    if best_sat == len(clauses): break
            if best_sat == len(clauses): break

    return best_assignment, best_sat == len(clauses), k_modes


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("EIGENMODE SEARCH SOLVER")
    print("=" * 70)

    for n in [12, 16, 20]:
        results = {'tension': 0, 'eigenmode': 0, 'hybrid': 0, 'total': 0}
        avg_k = []; avg_combos = []; total_time = 0

        n_inst = 100 if n <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+6000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            results['total'] += 1

            # Standard tension
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                results['tension'] += 1

            # Eigenmode search
            t0 = time.time()
            _, success, k, combos = eigenmode_search(clauses, n)
            total_time += time.time() - t0
            avg_k.append(k); avg_combos.append(combos)
            if success: results['eigenmode'] += 1

            # Hybrid
            _, success, _ = eigenmode_hybrid(clauses, n)
            if success: results['hybrid'] += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        t = results['total']
        avg_t = total_time/t*1000 if t > 0 else 0

        print(f"\n  n={n} ({t} instances):")
        print(f"    tension:   {results['tension']}/{t} ({results['tension']/t*100:.1f}%)")
        print(f"    eigenmode: {results['eigenmode']}/{t} ({results['eigenmode']/t*100:.1f}%)")
        print(f"    hybrid:    {results['hybrid']}/{t} ({results['hybrid']/t*100:.1f}%)")
        print(f"    avg k={mean(avg_k):.1f}, combos={mean(avg_combos):.0f}, time={avg_t:.0f}ms")
