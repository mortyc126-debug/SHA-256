"""
HYBRID HAMILTONIAN: Ground state = SAT solution + holographic structure.

H_SAT: ground state = solution, but no structure.
H_signed: has structure, but ground state ≠ solution.

HYBRID: H = α × H_SAT + β × H_signed_projected

The idea: use signed Laplacian eigenmodes to GUIDE
the SAT Hamiltonian toward the solution.

Several constructions to test:
1. H = H_SAT (baseline — standard penalty Hamiltonian)
2. H = H_SAT + λ × H_signed (linear combo)
3. H = H_SAT projected onto top eigenspace of H_signed
4. H = H_SAT in the eigenmode basis
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


def power_iteration(matrix, n, k, n_iter=200):
    vectors = []; eigenvalues = []
    residual = [row[:] for row in matrix]
    for idx in range(k):
        vec = normalize([random.gauss(0,1) for _ in range(n)])
        for _ in range(n_iter):
            new = mat_vec(residual, vec, n)
            for prev in vectors:
                d = dot(new, prev)
                new = [new[i]-d*prev[i] for i in range(n)]
            ev = math.sqrt(dot(new, new))
            if ev > 1e-10: vec = [v/ev for v in new]
        vectors.append(vec); eigenvalues.append(ev)
        for i in range(n):
            for j in range(n):
                residual[i][j] -= ev*vec[i]*vec[j]
    return eigenvalues, vectors


# ============================================================
# H_SAT: Standard SAT penalty Hamiltonian
# ============================================================

def h_sat_energy(clauses, n, state_vec):
    """
    H_SAT = Σ (1 - clause_satisfied).
    For binary ±1 encoding: literal (v,s) is TRUE when s×state[v] > 0.
    Energy = number of unsatisfied clauses.
    """
    assignment = [1 if state_vec[v] > 0 else 0 for v in range(n)]
    return len(clauses) - evaluate(clauses, assignment)


# ============================================================
# CONSTRUCTION 1: H_SAT only (baseline)
# ============================================================

def test_h_sat():
    """Brute force: find ground state of H_SAT = SAT solution."""
    print("=" * 70)
    print("1. H_SAT baseline: energy landscape")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(3):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        # Energy distribution
        energies = {}
        for i in range(2**n):
            assignment = [(i>>v)&1 for v in range(n)]
            e = len(clauses) - evaluate(clauses, assignment)
            energies[e] = energies.get(e, 0) + 1

        print(f"\n  Instance {seed} ({len(solutions)} solutions):")
        print(f"  {'energy':>7} | {'count':>8} | visual")
        print("  " + "-" * 35)
        for e in sorted(energies.keys())[:8]:
            bar = "█" * min(50, energies[e]//10)
            label = " ← SOLUTIONS" if e == 0 else ""
            print(f"  {e:>7} | {energies[e]:>8} | {bar}{label}")


# ============================================================
# CONSTRUCTION 2: Simulated annealing in eigenmode space
# ============================================================

def eigenmode_annealing(clauses, n, k_modes=None):
    """
    Instead of annealing in n-dim bit space:
    Anneal in k-dim eigenmode space.
    Temperature schedule: high → low.
    At each step: perturb one eigenmode projection.
    Accept/reject by H_SAT energy.
    """
    if k_modes is None: k_modes = max(3, n//3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)

    # Initialize from tension
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

    # Initial projections from tension
    projs = [sum(tensions[i]*vectors[m][i] for i in range(n)) for m in range(k_modes)]

    # Reconstruct and evaluate
    def reconstruct_and_eval(projections):
        recon = [0.0]*n
        for m in range(k_modes):
            for i in range(n):
                recon[i] += projections[m] * vectors[m][i]
        assignment = [1 if recon[v] >= 0 else 0 for v in range(n)]
        return assignment, len(clauses) - evaluate(clauses, assignment)

    best_assignment, best_energy = reconstruct_and_eval(projs)
    current_projs = list(projs)
    current_energy = best_energy

    # Annealing
    T = 2.0
    for step in range(2000):
        # Perturb one random projection
        m = random.randint(0, k_modes-1)
        old_val = current_projs[m]
        current_projs[m] += random.gauss(0, 0.5 * T)

        _, new_energy = reconstruct_and_eval(current_projs)

        # Accept/reject
        delta = new_energy - current_energy
        if delta <= 0 or random.random() < math.exp(-delta/max(T, 0.01)):
            current_energy = new_energy
            if new_energy < best_energy:
                best_energy = new_energy
                best_assignment, _ = reconstruct_and_eval(current_projs)
        else:
            current_projs[m] = old_val  # reject

        T *= 0.998  # cool

    return best_assignment, best_energy == 0


# ============================================================
# CONSTRUCTION 3: Eigenmode-guided WalkSAT
# ============================================================

def eigenmode_walksat(clauses, n, k_modes=None):
    """
    WalkSAT but in eigenmode space: instead of flipping a BIT,
    flip an EIGENMODE projection.
    """
    if k_modes is None: k_modes = max(3, n//3)

    L = build_signed_laplacian(clauses, n)
    eigenvalues, vectors = power_iteration(L, n, k_modes)

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

    projs = [sum(tensions[i]*vectors[m][i] for i in range(n)) for m in range(k_modes)]

    def reconstruct(projections):
        recon = [0.0]*n
        for m in range(k_modes):
            for i in range(n):
                recon[i] += projections[m] * vectors[m][i]
        return [1 if recon[v] >= 0 else 0 for v in range(n)]

    best_assignment = reconstruct(projs)
    best_sat = evaluate(clauses, best_assignment)

    for step in range(500):
        assignment = reconstruct(projs)
        sat = evaluate(clauses, assignment)

        if sat == len(clauses):
            return assignment, True

        if sat > best_sat:
            best_sat = sat
            best_assignment = list(assignment)

        # Find unsatisfied clause
        unsat = []
        for ci, clause in enumerate(clauses):
            if not any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                      for v,s in clause):
                unsat.append(ci)

        if not unsat: break
        ci = random.choice(unsat)

        # Instead of flipping a bit: adjust the eigenmode
        # that most affects the unsatisfied clause's variables
        clause_vars = [v for v,s in clauses[ci]]
        best_mode = max(range(k_modes),
                       key=lambda m: sum(abs(vectors[m][v]) for v in clause_vars))

        # Flip this mode's projection
        projs[best_mode] = -projs[best_mode]

    return best_assignment, best_sat == len(clauses)


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    import time

    test_h_sat()

    print("\n" + "=" * 70)
    print("HYBRID HAMILTONIAN SOLVERS")
    print("=" * 70)

    for n in [12, 16]:
        results = {'tension': 0, 'eigen_anneal': 0, 'eigen_walksat': 0, 'total': 0}

        n_inst = 80 if n <= 12 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            results['total'] += 1

            # Tension baseline
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                tensions_local = {v: 0 for v in unfixed}
                for v in unfixed:
                    p1,p0=0.0,0.0
                    for clause in clauses:
                        sat=False;rem=[]
                        for vv,s in clause:
                            if vv in fixed:
                                if (s==1 and fixed[vv]==1) or (s==-1 and fixed[vv]==0): sat=True;break
                            else: rem.append((vv,s))
                        if sat: continue
                        for vv,s in rem:
                            if vv==v:
                                w=1.0/max(1,len(rem))
                                if s==1: p1+=w
                                else: p0+=w
                    total=p1+p0
                    tensions_local[v]=(p1-p0)/total if total>0 else 0
                best=max(unfixed,key=lambda v:abs(tensions_local[v]))
                fixed[best]=1 if tensions_local[best]>=0 else 0
            if evaluate(clauses,[fixed.get(v,0) for v in range(n)])==len(clauses):
                results['tension']+=1

            # Eigenmode annealing
            _, success = eigenmode_annealing(clauses, n)
            if success: results['eigen_anneal'] += 1

            # Eigenmode WalkSAT
            _, success = eigenmode_walksat(clauses, n)
            if success: results['eigen_walksat'] += 1

        t = results['total']
        print(f"\n  n={n} ({t} instances):")
        for name in sorted(results.keys(), key=lambda k: -results.get(k,0)):
            if name=='total': continue
            pct=results[name]/t*100
            print(f"    {name:>15}: {results[name]:>3}/{t} ({pct:>5.1f}%)")
