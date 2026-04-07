"""
EIGENMODE OPTIMIZATION: Gradient descent in n/3 dimensional eigenspace.

Instead of: search 2^n bit combinations
Do: optimize n/3 continuous projections to maximize satisfied clauses.

This is a CONTINUOUS OPTIMIZATION in REDUCED space.
n/3 variables instead of n. Polynomial per step.
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


def evaluate_soft(clauses, n, recon):
    """Soft evaluation: P(all clauses satisfied) given continuous recon values."""
    total_log_prob = 0
    for clause in clauses:
        p_unsat = 1.0
        for v, s in clause:
            # P(literal true) = sigmoid(s * recon[v])
            x = s * recon[v] * 3  # amplify
            p_lit = 1 / (1 + math.exp(-max(min(x, 20), -20)))
            p_unsat *= (1 - p_lit)
        p_sat = 1 - p_unsat
        total_log_prob += math.log(max(p_sat, 1e-10))
    return total_log_prob


def bit_tension(clauses, n, var):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                if s == 1: p1 += 1.0/3
                else: p0 += 1.0/3
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


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
# EIGENMODE GRADIENT DESCENT
# ============================================================

def eigenmode_gradient_descent(clauses, n, k_modes=None, n_steps=200, lr=0.5):
    """
    1. Compute eigenmodes
    2. Initialize projections from tension
    3. Gradient descent: adjust projections to maximize soft satisfaction
    4. Binarize final result
    """
    if k_modes is None:
        k_modes = max(3, n // 3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)

    # Initialize projections from tension
    tensions = [bit_tension(clauses, n, v) for v in range(n)]
    projs = [sum(tensions[i]*vectors[m][i] for i in range(n)) for m in range(k_modes)]

    # Gradient descent
    best_projs = list(projs)
    best_score = -float('inf')

    for step in range(n_steps):
        # Reconstruct from current projections
        recon = [0.0]*n
        for m in range(k_modes):
            for i in range(n):
                recon[i] += projs[m] * vectors[m][i]

        # Soft score
        score = evaluate_soft(clauses, n, recon)

        if score > best_score:
            best_score = score
            best_projs = list(projs)

        # Gradient: numerical, per projection
        eps = 0.1
        for m in range(k_modes):
            projs[m] += eps
            recon_plus = [0.0]*n
            for mm in range(k_modes):
                for i in range(n):
                    recon_plus[i] += projs[mm] * vectors[mm][i]
            score_plus = evaluate_soft(clauses, n, recon_plus)
            projs[m] -= eps

            grad = (score_plus - score) / eps
            projs[m] += lr * grad

        # Decay learning rate
        lr *= 0.995

    # Final: use best projections
    recon = [0.0]*n
    for m in range(k_modes):
        for i in range(n):
            recon[i] += best_projs[m] * vectors[m][i]

    assignment = [1 if recon[v] >= 0 else 0 for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses), k_modes


# ============================================================
# EIGENMODE + RANDOM RESTARTS
# ============================================================

def eigenmode_restarts(clauses, n, k_modes=None, n_restarts=10):
    """Multiple random starting points in eigenmode space."""
    if k_modes is None:
        k_modes = max(3, n // 3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)
    tensions = [bit_tension(clauses, n, v) for v in range(n)]

    best_assignment = None
    best_sat = 0

    for restart in range(n_restarts):
        # Random perturbation of tension-based projections
        projs = [sum(tensions[i]*vectors[m][i] for i in range(n)) + random.gauss(0, 0.5)
                for m in range(k_modes)]

        # Quick gradient descent
        lr = 0.3
        for step in range(100):
            recon = [sum(projs[m]*vectors[m][i] for m in range(k_modes)) for i in range(n)]
            score = evaluate_soft(clauses, n, recon)

            for m in range(k_modes):
                projs[m] += 0.1
                recon_p = [sum(projs[mm]*vectors[mm][i] for mm in range(k_modes)) for i in range(n)]
                score_p = evaluate_soft(clauses, n, recon_p)
                projs[m] -= 0.1
                projs[m] += lr * (score_p - score) / 0.1

            lr *= 0.99

        recon = [sum(projs[m]*vectors[m][i] for m in range(k_modes)) for i in range(n)]
        assignment = [1 if recon[v] >= 0 else 0 for v in range(n)]
        sat = evaluate(clauses, assignment)

        if sat > best_sat:
            best_sat = sat
            best_assignment = assignment

        if best_sat == len(clauses):
            break

    return best_assignment, best_sat == len(clauses), k_modes


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    import time

    print("=" * 70)
    print("EIGENMODE OPTIMIZATION: Gradient descent in reduced space")
    print("=" * 70)

    for n in [12, 16, 20, 30]:
        results = {'tension': 0, 'eigen_gd': 0, 'eigen_restart': 0, 'total': 0}
        t_gd = 0; t_restart = 0

        n_inst = 80 if n <= 16 else 40
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+7000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            results['total'] += 1

            # Standard tension
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v)))
                fixed[best] = 1 if bit_tension(clauses, n, best) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                results['tension'] += 1

            # Eigenmode gradient descent
            t0 = time.time()
            _, success, _ = eigenmode_gradient_descent(clauses, n, n_steps=150)
            t_gd += time.time() - t0
            if success: results['eigen_gd'] += 1

            # Eigenmode with restarts
            t0 = time.time()
            _, success, _ = eigenmode_restarts(clauses, n, n_restarts=10)
            t_restart += time.time() - t0
            if success: results['eigen_restart'] += 1

        t = results['total']
        print(f"\n  n={n} ({t} instances):")
        for name in ['tension', 'eigen_gd', 'eigen_restart']:
            pct = results[name]/t*100 if t > 0 else 0
            print(f"    {name:>15}: {results[name]:>3}/{t} ({pct:>5.1f}%)")
        print(f"    GD time: {t_gd/t*1000:.0f}ms, Restart time: {t_restart/t*1000:.0f}ms")
