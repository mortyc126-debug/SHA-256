"""
C3: HYBRID BASIS — Interpolate between eigenmode and bit basis.

Eigenmode: best for understanding (86% from 4 modes)
Bit: best for search (DPLL 100%)

Can we find an INTERMEDIATE basis that balances both?

Method: ROTATE bit basis toward eigenmode basis by angle θ.
θ = 0: pure bit basis
θ = π/2: pure eigenmode basis
θ = optimal: best of both?

Implementation: for each bit, its "rotated" representation is:
rotated_i = cos(θ) × bit_i + sin(θ) × eigenmode_component_i

Search in rotated space: fix "rotated bits" one at a time.
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
        vec = [random.gauss(0,1)/math.sqrt(n) for _ in range(n)]
        nm = math.sqrt(sum(v*v for v in vec))
        vec = [v/nm for v in vec]
        for _ in range(n_iter):
            new = [sum(residual[i][j]*vec[j] for j in range(n)) for i in range(n)]
            for prev in vectors:
                d = sum(new[i]*prev[i] for i in range(n))
                new = [new[i]-d*prev[i] for i in range(n)]
            ev = math.sqrt(sum(v*v for v in new))
            if ev > 1e-10: vec = [v/ev for v in new]
        vectors.append(vec); eigenvalues.append(ev)
        for i in range(n):
            for j in range(n):
                residual[i][j] -= ev*vec[i]*vec[j]
    return eigenvalues, vectors


# ============================================================
# ROTATED TENSION: blend bit-tension with eigenmode signal
# ============================================================

def rotated_tension(clauses, n, var, theta, tensions, eigvecs, eigen_signal):
    """
    Rotated signal = cos(θ) × tension + sin(θ) × eigenmode_signal.

    tension = raw bit signal (0-local, surgical)
    eigenmode_signal = projection of tension onto eigenmode basis,
    reconstructed back to this bit (non-local, structural).
    """
    bit_signal = tensions[var]
    eigen_part = eigen_signal[var]

    return math.cos(theta) * bit_signal + math.sin(theta) * eigen_part


def compute_eigen_signal(tensions, eigvecs, n, k):
    """
    Project tension vector onto top-k eigenmodes, reconstruct.
    This is the "eigenmode-filtered" tension.
    """
    t_vec = [tensions[v] for v in range(n)]

    # Project
    projs = [sum(t_vec[i]*eigvecs[m][i] for i in range(n)) for m in range(k)]

    # Reconstruct
    recon = [0.0]*n
    for m in range(k):
        for i in range(n):
            recon[i] += projs[m] * eigvecs[m][i]

    return recon


# ============================================================
# BENCHMARK: accuracy by rotation angle
# ============================================================

def test_rotation():
    print("=" * 70)
    print("C3: HYBRID BASIS — Accuracy by rotation angle θ")
    print("=" * 70)

    random.seed(42); n = 12

    results = {}

    for theta_deg in range(0, 100, 10):
        theta = theta_deg * math.pi / 180
        correct = 0; total = 0

        for seed in range(150):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            L = build_signed_laplacian(clauses, n)
            k = 4
            eigenvalues, eigvecs = power_iteration(L, n, k)
            eigen_signal = compute_eigen_signal(tensions, eigvecs, n, k)

            for var in range(n):
                total += 1
                rot_sig = rotated_tension(clauses, n, var, theta, tensions, eigvecs, eigen_signal)
                if (1 if rot_sig >= 0 else 0) == correct_val[var]:
                    correct += 1

        acc = correct/total*100 if total > 0 else 0
        results[theta_deg] = acc

    print(f"\n  {'θ (degrees)':>11} | {'accuracy':>8} | visual")
    print("  " + "-" * 45)

    best_theta = max(results.keys(), key=lambda k: results[k])
    for theta_deg in sorted(results.keys()):
        acc = results[theta_deg]
        bar = "█" * int(acc/2)
        marker = " ← BEST" if theta_deg == best_theta else ""
        print(f"  {theta_deg:>11}° | {acc:>7.1f}% | {bar}{marker}")


# ============================================================
# ROTATED SOLVER: crystallize in rotated basis
# ============================================================

def rotated_solver():
    print("\n" + "=" * 70)
    print("ROTATED SOLVER: Crystallize with hybrid signal")
    print("=" * 70)

    random.seed(42); n = 12

    for theta_deg in [0, 10, 20, 30, 45, 60, 90]:
        theta = theta_deg * math.pi / 180
        solved = 0; total = 0

        for seed in range(150):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            total += 1

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            L = build_signed_laplacian(clauses, n)
            eigenvalues, eigvecs = power_iteration(L, n, 4)
            eigen_signal = compute_eigen_signal(tensions, eigvecs, n, 4)

            # Crystallize with rotated signal
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break

                # Recompute tensions with fixed context
                local_tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}
                local_eigen = compute_eigen_signal(local_tensions, eigvecs, n, 4)

                # Best by rotated |signal|
                scores = {v: rotated_tension(clauses, n, v, theta, local_tensions, eigvecs, local_eigen)
                         for v in unfixed}
                best = max(unfixed, key=lambda v: abs(scores[v]))
                fixed[best] = 1 if scores[best] >= 0 else 0

            assignment = [fixed.get(v,0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                solved += 1

        pct = solved/total*100 if total > 0 else 0
        marker = ""
        if theta_deg == 0: marker = " (pure tension)"
        elif theta_deg == 90: marker = " (pure eigenmode)"
        print(f"  θ={theta_deg:>3}°: {solved}/{total} ({pct:.1f}%){marker}")


if __name__ == "__main__":
    test_rotation()
    rotated_solver()
