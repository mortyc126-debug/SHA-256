"""
SIGNED LAPLACIAN AS HAMILTONIAN

If ground state of signed Laplacian ≈ SAT solution,
then quantum computing (VQE) could break the wall.

Tests:
1. Is SAT solution an EIGENVECTOR of signed Laplacian?
2. Is it the GROUND STATE (lowest eigenvalue)?
3. How big is the spectral GAP (ground state vs first excited)?
4. Does the gap CLOSE with n? (if yes → hard for quantum too)
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


def mat_vec(M, v, n):
    return [sum(M[i][j]*v[j] for j in range(n)) for i in range(n)]


def dot(a, b):
    return sum(a[i]*b[i] for i in range(len(a)))


def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n > 0 else v


def rayleigh_quotient(M, v, n):
    """R(v) = v^T M v / v^T v — energy of state v in Hamiltonian M."""
    Mv = mat_vec(M, v, n)
    return dot(v, Mv) / dot(v, v) if dot(v, v) > 0 else 0


# ============================================================
# 1. IS SOLUTION AN EIGENVECTOR?
# ============================================================

def solution_as_eigenvector():
    print("=" * 70)
    print("1. Is SAT solution an eigenvector of signed Laplacian?")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        L = build_signed_laplacian(clauses, n)
        sol = solutions[0]
        sol_vec = normalize([2*sol[v]-1 for v in range(n)])  # ±1 encoding

        # L × sol_vec
        Lv = mat_vec(L, sol_vec, n)

        # If eigenvector: Lv = λ × sol_vec for some λ
        # Check: is Lv parallel to sol_vec?
        # Residual = |Lv - (Lv·sol/sol·sol) × sol|
        lambda_est = dot(Lv, sol_vec) / dot(sol_vec, sol_vec)
        residual = [Lv[i] - lambda_est * sol_vec[i] for i in range(n)]
        res_norm = math.sqrt(sum(r*r for r in residual))
        lv_norm = math.sqrt(sum(r*r for r in Lv))

        parallelism = 1 - res_norm/lv_norm if lv_norm > 0 else 0

        # Rayleigh quotient = energy of solution
        rq = rayleigh_quotient(L, sol_vec, n)

        print(f"\n  Instance {seed}: λ_est={lambda_est:.3f}, "
              f"parallelism={parallelism:.4f} (1=perfect eigenvector), "
              f"energy={rq:.3f}")


# ============================================================
# 2. IS SOLUTION THE GROUND STATE?
# ============================================================

def solution_energy_rank():
    """
    Compare energy of solution vs random assignments vs tension assignment.
    Ground state = lowest energy.
    """
    print("\n" + "=" * 70)
    print("2. Is solution the GROUND STATE (lowest energy)?")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(8):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        L = build_signed_laplacian(clauses, n)

        # Solution energy
        sol = solutions[0]
        sol_vec = [2*sol[v]-1 for v in range(n)]
        e_sol = rayleigh_quotient(L, sol_vec, n)

        # Tension-guided energy
        from bit_catalog_static import random_3sat as _
        tensions = []
        for var in range(n):
            p1,p0=0.0,0.0
            for clause in clauses:
                for v,s in clause:
                    if v==var:
                        if s==1: p1+=1.0/3
                        else: p0+=1.0/3
            total=p1+p0
            tensions.append((p1-p0)/total if total>0 else 0)

        t_vec = [2*(1 if t>=0 else 0)-1 for t in tensions]
        e_tension = rayleigh_quotient(L, t_vec, n)

        # Random energies
        random_energies = []
        for _ in range(100):
            r_vec = [random.choice([-1,1]) for _ in range(n)]
            random_energies.append(rayleigh_quotient(L, r_vec, n))

        # All solutions' energies
        sol_energies = []
        for sol_i in solutions:
            sv = [2*sol_i[v]-1 for v in range(n)]
            sol_energies.append(rayleigh_quotient(L, sv, n))

        mean_random = sum(random_energies)/len(random_energies)
        min_random = min(random_energies)
        avg_sol = sum(sol_energies)/len(sol_energies)

        print(f"\n  Instance {seed} ({len(solutions)} solutions):")
        print(f"    Solution energy:   {e_sol:>8.3f}")
        print(f"    Avg all solutions: {avg_sol:>8.3f}")
        print(f"    Tension energy:    {e_tension:>8.3f}")
        print(f"    Random mean:       {mean_random:>8.3f}")
        print(f"    Random min:        {min_random:>8.3f}")

        if e_sol < mean_random:
            print(f"    → Solution has LOWER energy than average ✓")
        if e_sol < min_random:
            print(f"    → Solution has LOWER energy than ALL random! ★")
        if e_sol > mean_random:
            print(f"    → Solution has HIGHER energy than average ✗")


# ============================================================
# 3. SPECTRAL GAP
# ============================================================

def spectral_gap():
    """
    Gap between ground state and first excited state.
    Large gap → quantum annealing works well.
    Small gap → even quantum is slow.
    """
    print("\n" + "=" * 70)
    print("3. SPECTRAL GAP of signed Laplacian")
    print("=" * 70)

    random.seed(42); n = 12

    gaps = []

    for seed in range(10):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        L = build_signed_laplacian(clauses, n)

        # Find two lowest eigenvalues via inverse power iteration
        # First: find LARGEST eigenvalue (power iteration)
        vec = normalize([random.gauss(0,1) for _ in range(n)])
        for _ in range(200):
            new = mat_vec(L, vec, n)
            ev = math.sqrt(dot(new, new))
            if ev > 0: vec = [v/ev for v in new]
        lambda_max = ev

        # Shift: M = lambda_max*I - L (now largest of M = smallest of L)
        M = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                M[i][j] = -L[i][j]
            M[i][i] += lambda_max + 0.01

        # Find two largest eigenvalues of M (= two smallest of L)
        eigvals = []
        residual = [row[:] for row in M]

        for eig_idx in range(3):
            vec = normalize([random.gauss(0,1) for _ in range(n)])
            for _ in range(300):
                new = mat_vec(residual, vec, n)
                # Orthogonalize (implicitly via deflation)
                ev = math.sqrt(dot(new, new))
                if ev > 0: vec = [v/ev for v in new]

            eigval_M = dot(mat_vec(residual, vec, n), vec)
            eigval_L = lambda_max + 0.01 - eigval_M
            eigvals.append(eigval_L)

            # Deflate
            for i in range(n):
                for j in range(n):
                    residual[i][j] -= eigval_M * vec[i] * vec[j]

        if len(eigvals) >= 2:
            eigvals.sort()
            gap = eigvals[1] - eigvals[0]
            gaps.append(gap)
            print(f"  Instance {seed}: λ₁={eigvals[0]:.3f}, λ₂={eigvals[1]:.3f}, gap={gap:.3f}")

    if gaps:
        mean = sum(gaps)/len(gaps)
        print(f"\n  Average spectral gap: {mean:.4f}")
        if mean > 1.0:
            print(f"  → LARGE gap: quantum annealing should work well")
        elif mean > 0.1:
            print(f"  → MODERATE gap: quantum feasible but not easy")
        else:
            print(f"  → SMALL gap: quantum annealing faces difficulties too")


# ============================================================
# 4. DOES GAP CLOSE WITH n?
# ============================================================

def gap_vs_n():
    print("\n" + "=" * 70)
    print("4. Does spectral gap CLOSE with n?")
    print("=" * 70)

    random.seed(42)

    print(f"\n  {'n':>5} | {'avg gap':>8} | {'prediction':>10}")
    print("  " + "-" * 30)

    for n in [8, 10, 12, 14, 16]:
        gaps = []
        for seed in range(10):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            L = build_signed_laplacian(clauses, n)

            # Quick: find λ_max
            vec = normalize([random.gauss(0,1) for _ in range(n)])
            for _ in range(200):
                new = mat_vec(L, vec, n)
                ev = math.sqrt(dot(new, new))
                if ev > 0: vec = [v/ev for v in new]
            lmax = ev

            M = [[-L[i][j] for j in range(n)] for i in range(n)]
            for i in range(n): M[i][i] += lmax + 0.01

            eigvals = []
            res = [row[:] for row in M]
            for _ in range(2):
                vec = normalize([random.gauss(0,1) for _ in range(n)])
                for it in range(300):
                    new = mat_vec(res, vec, n)
                    ev2 = math.sqrt(dot(new, new))
                    if ev2 > 0: vec = [v/ev2 for v in new]
                eigval_M = dot(mat_vec(res, vec, n), vec)
                eigvals.append(lmax + 0.01 - eigval_M)
                for i in range(n):
                    for j in range(n):
                        res[i][j] -= eigval_M*vec[i]*vec[j]

            if len(eigvals) >= 2:
                eigvals.sort()
                gaps.append(eigvals[1]-eigvals[0])

        if gaps:
            avg = sum(gaps)/len(gaps)
            trend = "closing" if n > 8 and avg < 1 else "stable"
            print(f"  {n:>5} | {avg:>8.4f} | {trend}")


if __name__ == "__main__":
    solution_as_eigenvector()
    solution_energy_rank()
    spectral_gap()
    gap_vs_n()
