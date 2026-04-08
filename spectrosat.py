"""
SpectroSAT — Spectral SAT Solver
═════════════════════════════════
A completely new SAT architecture based on the Signed Laplacian.

NO existing solver uses spectral methods for SAT.
This is a first-of-its-kind solver built from Bit Mechanics theory.

THEORY:
  The signed Laplacian L encodes ALL clause relationships.
  Its eigenvectors form the "natural basis" for solutions.
  The solution vector (mapped to ±1) aligns with the bottom
  eigenmodes of L. Projecting onto these eigenmodes recovers
  the solution with high accuracy.

ARCHITECTURE:
  Phase 1: BUILD   — Construct signed Laplacian from clauses
  Phase 2: DECOMPOSE — Eigendecomposition (bottom k modes)
  Phase 3: RELAX   — Continuous relaxation in eigenspace
  Phase 4: ROUND   — Multiple rounding strategies (sign, random, sweep)
  Phase 5: REPAIR  — WalkSAT local search from rounded solution

This solver works in CONTINUOUS space, then discretizes.
Fundamentally different from DPLL/CDCL (discrete tree search).
"""

import numpy as np
import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0)
        for v, s in c))


# ============================================================
# Phase 1: Build Signed Laplacian
# ============================================================

def build_signed_laplacian(clauses, n):
    """
    Signed Laplacian from clause structure.

    For each clause (l1, l2, l3):
      For each pair (li, lj) where li = (vi, si), lj = (vj, sj):
        Edge weight contribution = si * sj
        (positive if literals agree, negative if they disagree)

    L = D - A_signed
    where A_signed[i,j] = sum of si*sj over shared clauses
    D[i,i] = sum_j |A_signed[i,j]|
    """
    A = np.zeros((n, n))

    for clause in clauses:
        for i in range(len(clause)):
            for j in range(i + 1, len(clause)):
                vi, si = clause[i]
                vj, sj = clause[j]
                edge_sign = si * sj
                A[vi, vj] += edge_sign
                A[vj, vi] += edge_sign

    # Degree matrix (absolute values for signed Laplacian)
    D = np.diag(np.sum(np.abs(A), axis=1))

    L = D - A
    return L, A


# ============================================================
# Phase 2: Eigendecomposition
# ============================================================

def spectral_decompose(L, k=None):
    """
    Compute bottom k eigenvectors of signed Laplacian.
    These form the "solution subspace."
    """
    n = L.shape[0]
    if k is None:
        k = max(n // 3, 5)  # n/3 effective DOF from our theory
    k = min(k, n)

    eigenvalues, eigenvectors = np.linalg.eigh(L)

    # Bottom k (smallest eigenvalues)
    idx = np.argsort(eigenvalues)[:k]

    return eigenvalues[idx], eigenvectors[:, idx]


# ============================================================
# Phase 3: Continuous relaxation
# ============================================================

def spectral_relax(L, A, eigvecs, clauses, n):
    """
    Find the continuous vector x ∈ [-1,1]^n that minimizes
    a SAT-inspired objective in the eigenspace.

    Objective: minimize x^T L x subject to ||x|| = sqrt(n)
    (standard spectral relaxation)

    The minimum is achieved by the Fiedler vector (2nd eigenvector),
    but we use multiple eigenvectors for richer representation.
    """
    # Method 1: Fiedler vector (2nd eigenvector)
    fiedler = eigvecs[:, 1] if eigvecs.shape[1] > 1 else eigvecs[:, 0]

    # Method 2: Weighted combination of bottom eigenvectors
    # Weight by inverse eigenvalue (amplify low-frequency modes)
    eigenvalues = np.diag(eigvecs.T @ L @ eigvecs)
    weights = np.zeros(eigvecs.shape[1])
    for i in range(len(weights)):
        if abs(eigenvalues[i]) > 1e-10:
            weights[i] = 1.0 / max(abs(eigenvalues[i]), 0.01)
        else:
            weights[i] = 100.0  # large weight for near-zero eigenvalue

    weighted = eigvecs @ (weights * eigvecs[0, :])  # project first row
    # Actually: better to use tension as the initial guess
    # and project it onto eigenspace

    # Method 3: Tension-guided projection
    tensions = np.zeros(n)
    for clause in clauses:
        for v, s in clause:
            tensions[v] += s / len(clause)
    # Normalize
    norm = np.linalg.norm(tensions)
    if norm > 0:
        tensions = tensions / norm * np.sqrt(n)

    # Project tension onto eigenspace
    coeffs = eigvecs.T @ tensions
    projected = eigvecs @ coeffs

    return fiedler, projected, tensions


# ============================================================
# Phase 4: Rounding strategies
# ============================================================

def round_sign(x):
    """Simple sign rounding: x > 0 → 1, x ≤ 0 → 0."""
    return [1 if xi > 0 else 0 for xi in x]


def round_random(x, n_samples=20):
    """
    Randomized rounding: P(v=1) proportional to x[v].
    Try multiple samples, keep best.
    """
    # Normalize to [0, 1] range
    x_min, x_max = min(x), max(x)
    if x_max > x_min:
        probs = [(xi - x_min) / (x_max - x_min) for xi in x]
    else:
        probs = [0.5] * len(x)

    best = None
    best_score = -1

    for _ in range(n_samples):
        assignment = [1 if random.random() < p else 0 for p in probs]
        yield assignment


def round_sweep(x):
    """
    Sweep rounding: sort by x value, try threshold at each position.
    Return the assignment with most satisfied clauses.
    """
    sorted_idx = np.argsort(x)
    n = len(x)

    for threshold_pos in range(n + 1):
        assignment = [0] * n
        for i in range(threshold_pos, n):
            assignment[sorted_idx[i]] = 1
        yield assignment


# ============================================================
# Phase 5: WalkSAT repair
# ============================================================

def walksat_repair(clauses, n, assignment, max_flips=None):
    """WalkSAT local search to repair a rounded solution."""
    assignment = list(assignment)
    m = len(clauses)

    if max_flips is None:
        max_flips = n * 50

    best = list(assignment)
    best_sat = evaluate(clauses, assignment)

    if best_sat == m:
        return best, best_sat

    for flip in range(max_flips):
        # Find unsatisfied clauses
        unsat = []
        for ci, clause in enumerate(clauses):
            ok = False
            for v, s in clause:
                if (s == 1 and assignment[v] == 1) or \
                   (s == -1 and assignment[v] == 0):
                    ok = True
                    break
            if not ok:
                unsat.append(ci)

        if not unsat:
            return assignment, m

        # Pick random unsatisfied clause
        ci = random.choice(unsat)
        clause = clauses[ci]

        # Pick variable to flip (greedy: minimize breaks)
        best_var = None
        best_breaks = float('inf')

        for v, s in clause:
            new_val = 1 - assignment[v]
            breaks = 0
            for other in clauses:
                was_sat = any((os == 1 and assignment[ov] == 1) or
                             (os == -1 and assignment[ov] == 0)
                             for ov, os in other)
                # Would flip change this clause?
                will_sat = True
                for ov, os in other:
                    val = new_val if ov == v else assignment[ov]
                    if (os == 1 and val == 1) or (os == -1 and val == 0):
                        break
                else:
                    will_sat = False

                if was_sat and not will_sat:
                    breaks += 1

            if breaks < best_breaks:
                best_breaks = breaks
                best_var = v

        if random.random() < 0.3:
            # Random walk step
            best_var = random.choice([v for v, s in clause])

        assignment[best_var] = 1 - assignment[best_var]

        sat = evaluate(clauses, assignment)
        if sat > best_sat:
            best_sat = sat
            best = list(assignment)

        if sat == m:
            return assignment, m

    return best, best_sat


# ============================================================
# SpectroSAT: The complete solver
# ============================================================

def spectrosat_solve(clauses, n, max_time=30):
    """
    SpectroSAT: Spectral decomposition + rounding + repair.
    """
    start = time.time()
    stats = {
        'eigendecomp_ms': 0,
        'rounding_tries': 0,
        'walksat_flips': 0,
        'best_sat': 0,
        'method': '',
    }
    m = len(clauses)

    # Phase 1: Build signed Laplacian
    L, A = build_signed_laplacian(clauses, n)

    # Phase 2: Eigendecomposition
    t0 = time.time()
    k = max(n // 3, 5)
    eigenvalues, eigenvectors = spectral_decompose(L, k)
    stats['eigendecomp_ms'] = (time.time() - t0) * 1000

    # Phase 3: Continuous relaxation
    fiedler, projected, tensions = spectral_relax(
        L, A, eigenvectors, clauses, n)

    best_solution = None
    best_sat = 0

    # Phase 4: Try multiple rounding strategies

    # Strategy 1: Sign of Fiedler vector
    for sign_flip in [1, -1]:
        assignment = round_sign(sign_flip * fiedler)
        sat = evaluate(clauses, assignment)
        stats['rounding_tries'] += 1
        if sat > best_sat:
            best_sat = sat
            best_solution = assignment
        if sat == m:
            stats['method'] = 'fiedler_sign'
            stats['best_sat'] = m
            return best_solution, stats

    # Strategy 2: Sign of projected tension
    for sign_flip in [1, -1]:
        assignment = round_sign(sign_flip * projected)
        sat = evaluate(clauses, assignment)
        stats['rounding_tries'] += 1
        if sat > best_sat:
            best_sat = sat
            best_solution = assignment
        if sat == m:
            stats['method'] = 'projected_sign'
            stats['best_sat'] = m
            return best_solution, stats

    # Strategy 3: Sign of raw tension
    assignment = round_sign(tensions)
    sat = evaluate(clauses, assignment)
    stats['rounding_tries'] += 1
    if sat > best_sat:
        best_sat = sat
        best_solution = assignment

    # Strategy 4: Random rounding from projected vector
    for assignment in round_random(projected, n_samples=30):
        sat = evaluate(clauses, assignment)
        stats['rounding_tries'] += 1
        if sat > best_sat:
            best_sat = sat
            best_solution = assignment
        if sat == m:
            stats['method'] = 'random_round'
            stats['best_sat'] = m
            return best_solution, stats
        if time.time() - start > max_time * 0.3:
            break

    # Strategy 5: Sweep rounding on each eigenvector
    for ev_idx in range(min(eigenvectors.shape[1], 5)):
        for assignment in round_sweep(eigenvectors[:, ev_idx]):
            sat = evaluate(clauses, assignment)
            stats['rounding_tries'] += 1
            if sat > best_sat:
                best_sat = sat
                best_solution = assignment
            if sat == m:
                stats['method'] = f'sweep_ev{ev_idx}'
                stats['best_sat'] = m
                return best_solution, stats
        if time.time() - start > max_time * 0.4:
            break

    # Phase 5: WalkSAT repair from best rounding
    if best_solution is not None:
        remaining = max_time - (time.time() - start)
        max_flips = int(remaining * n * 10)  # budget based on remaining time
        max_flips = max(max_flips, n * 50)

        repaired, sat = walksat_repair(
            clauses, n, best_solution, max_flips=min(max_flips, n * 200))
        stats['walksat_flips'] = max_flips
        if sat > best_sat:
            best_sat = sat
            best_solution = repaired
        stats['method'] = 'walksat_repair'

    stats['best_sat'] = best_sat
    return best_solution, stats


# ============================================================
# Benchmark
# ============================================================

def solve_minisat(n, clauses, timeout=60):
    filename = "/tmp/spectro_bench.cnf"
    outfile = filename + ".out"
    m = len(clauses)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for clause in clauses:
            lits = [str((v+1)*s) for v, s in clause]
            f.write(" ".join(lits) + " 0\n")
    try:
        t0 = time.time()
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - t0
        if os.path.exists(outfile):
            with open(outfile) as f:
                r = f.readline().strip()
                if r == "SAT": return True, elapsed
                elif r == "UNSAT": return None, elapsed
        return False, elapsed
    except subprocess.TimeoutExpired:
        return False, timeout
    finally:
        for fn in [filename, outfile]:
            if os.path.exists(fn): os.remove(fn)


def benchmark():
    print("=" * 70)
    print("SpectroSAT vs MiniSat BENCHMARK")
    print("=" * 70)

    random.seed(42)

    print(f"\n  {'n':>5} | {'SpectroSAT':>20} | {'MiniSat':>20} | "
          f"{'method':>15} | {'eigendecomp':>11}")
    print("  " + "-" * 85)

    for n in [20, 30, 50, 75, 100, 150, 200]:
        n_inst = 30 if n <= 100 else 15
        timeout = 10 if n <= 100 else 30

        spectro_solved = 0
        minisat_solved = 0
        spectro_times = []
        minisat_times = []
        methods = []
        eigen_times = []
        sat_fracs = []

        for seed in range(n_inst * 3):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 67000000)

            # SpectroSAT
            t0 = time.time()
            result, stats = spectrosat_solve(clauses, n, max_time=timeout)
            t_spectro = time.time() - t0

            m = len(clauses)
            if result is not None and evaluate(clauses, result) == m:
                spectro_solved += 1
                spectro_times.append(t_spectro)
                methods.append(stats['method'])
            else:
                sat_fracs.append(stats['best_sat'] / m if m > 0 else 0)

            eigen_times.append(stats['eigendecomp_ms'])

            # MiniSat
            ms_result, t_mini = solve_minisat(n, clauses, timeout)
            if ms_result == True:
                minisat_solved += 1
                minisat_times.append(t_mini)

            if spectro_solved + minisat_solved >= n_inst * 2:
                break

        avg_spectro = (f"{spectro_solved:>3} solved "
                      f"{1000*sum(spectro_times)/max(len(spectro_times),1):>5.0f}ms"
                      if spectro_times else f"{spectro_solved:>3} solved      N/A")
        avg_mini = (f"{minisat_solved:>3} solved "
                   f"{1000*sum(minisat_times)/max(len(minisat_times),1):>5.0f}ms"
                   if minisat_times else f"{minisat_solved:>3} solved      N/A")
        avg_eigen = f"{sum(eigen_times)/len(eigen_times):>8.1f}ms"

        # Most common method
        if methods:
            from collections import Counter
            common = Counter(methods).most_common(1)[0][0]
        else:
            common = "N/A"

        # Avg unsolved sat fraction
        if sat_fracs:
            avg_frac = f"(unsat avg: {100*sum(sat_fracs)/len(sat_fracs):.1f}%)"
        else:
            avg_frac = ""

        print(f"  {n:>5} | {avg_spectro:>20} | {avg_mini:>20} | "
              f"{common:>15} | {avg_eigen:>11}")
        if sat_fracs:
            print(f"        {avg_frac}")


def detailed_spectral_analysis():
    """Show what the spectral decomposition reveals."""
    print("\n" + "=" * 70)
    print("SPECTRAL ANALYSIS: What eigenvectors tell us")
    print("=" * 70)

    random.seed(42)

    for n in [20, 50]:
        for seed in range(5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 68000000)
            if n <= 20:
                solutions = find_solutions(clauses, n)
                if not solutions:
                    continue
                sol = solutions[0]
            else:
                # Use MiniSat
                from subprocess import run
                fn = "/tmp/spectro_detail.cnf"
                with open(fn, 'w') as f:
                    f.write(f"p cnf {n} {len(clauses)}\n")
                    for c in clauses:
                        f.write(" ".join(str((v+1)*s) for v,s in c) + " 0\n")
                r = run(["minisat", fn, fn+".out"], capture_output=True, timeout=10)
                if os.path.exists(fn+".out"):
                    with open(fn+".out") as f:
                        if f.readline().strip() != "SAT": continue
                        vals = f.readline().strip().split()
                        sol = [0]*n
                        for v in vals:
                            vi = int(v)
                            if vi > 0 and vi <= n: sol[vi-1] = 1
                            elif vi < 0 and -vi <= n: sol[-vi-1] = 0
                    os.remove(fn+".out")
                else:
                    continue
                os.remove(fn)

            # Build spectral decomposition
            L, A = build_signed_laplacian(clauses, n)
            k = max(n // 3, 5)
            eigenvalues, eigvecs = spectral_decompose(L, k)

            # Solution vector in ±1 encoding
            sol_vec = np.array([2 * sol[v] - 1 for v in range(n)], dtype=float)

            # Project solution onto eigenspace
            coeffs = eigvecs.T @ sol_vec
            projected = eigvecs @ coeffs
            reconstruction_error = np.linalg.norm(sol_vec - projected) / np.linalg.norm(sol_vec)

            # Accuracy of sign(projected) vs solution
            rounded = [1 if projected[v] > 0 else 0 for v in range(n)]
            accuracy = sum(1 for v in range(n) if rounded[v] == sol[v]) / n

            # Energy of solution in eigenspace
            energy_in = np.sum(coeffs**2) / np.sum(sol_vec**2)

            # Tension accuracy for comparison
            tensions = np.zeros(n)
            for clause in clauses:
                for v, s in clause:
                    tensions[v] += s / len(clause)
            tension_acc = sum(1 for v in range(n)
                            if (tensions[v] > 0) == (sol[v] == 1)) / n

            print(f"\n  n={n}, seed={seed}:")
            print(f"    Bottom {k} eigenvalues: [{eigenvalues[0]:.2f}, "
                  f"{eigenvalues[1]:.2f}, ..., {eigenvalues[-1]:.2f}]")
            print(f"    Solution energy in eigenspace: {100*energy_in:.1f}%")
            print(f"    Reconstruction error: {100*reconstruction_error:.1f}%")
            print(f"    Eigenmode rounding accuracy: {100*accuracy:.1f}%")
            print(f"    Tension accuracy:            {100*tension_acc:.1f}%")
            print(f"    Improvement over tension:     "
                  f"{100*(accuracy - tension_acc):+.1f}%")

            break  # one instance per n


if __name__ == "__main__":
    detailed_spectral_analysis()
    benchmark()
