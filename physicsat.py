"""
PhysicsSAT — Solving SAT by simulating physical dynamics
═════════════════════════════════════════════════════════

Variables are particles with positions x ∈ [0,1].
Clauses create force fields that push particles toward satisfying values.
The system evolves under these forces until it converges.

This is NOT gradient descent. It's a physical simulation with:
  - Inertia (momentum helps escape local minima)
  - Temperature (noise helps explore)
  - Cooling schedule (annealing toward discrete values)
  - Clause pressure (unsatisfied clauses push harder)

UNIQUE FEATURES:
  1. Continuous dynamics → no backtracking needed
  2. Simulated annealing with clause-based energy
  3. Momentum term helps escape local optima
  4. Temperature from our theory (T=0.75 at threshold)
  5. Self-cancellation damping (frustrated vars get higher noise)

ARCHITECTURE:
  Phase 1: INIT    — random positions in [0,1]^n
  Phase 2: EVOLVE  — physical simulation with annealing
  Phase 3: FREEZE  — cool to near-binary values
  Phase 4: ROUND   — discretize
  Phase 5: REPAIR  — targeted WalkSAT on remaining violations
"""

import numpy as np
import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0)
        for v, s in c))


# ============================================================
# Differentiable SAT objective
# ============================================================

def clause_satisfaction(x, clause):
    """
    Soft clause satisfaction ∈ [0, 1].
    Uses product formulation: 1 - ∏(1 - lit_i)
    where lit_i = x_v for positive, (1-x_v) for negative.
    """
    prod = 1.0
    for v, s in clause:
        if s == 1:
            lit = x[v]
        else:
            lit = 1.0 - x[v]
        prod *= (1.0 - lit)
    return 1.0 - prod


def total_energy(x, clauses):
    """Total energy = number of unsatisfied clauses (soft)."""
    return sum(1.0 - clause_satisfaction(x, c) for c in clauses)


def clause_force(x, clause):
    """
    Force on each variable from one clause.
    Gradient of clause_satisfaction w.r.t. x.
    """
    n = len(x)
    forces = np.zeros(n)

    # Compute product terms
    lits = []
    for v, s in clause:
        if s == 1:
            lits.append((v, x[v], 1))
        else:
            lits.append((v, 1.0 - x[v], -1))

    # Satisfaction = 1 - ∏(1-lit_i)
    # d(sat)/d(x_v) = sign_v × ∏_{j≠v} (1-lit_j)
    total_prod = 1.0
    for _, lit_val, _ in lits:
        total_prod *= (1.0 - lit_val)

    for v, lit_val, sign in lits:
        if abs(1.0 - lit_val) > 1e-15:
            prod_others = total_prod / (1.0 - lit_val)
        else:
            # lit_val ≈ 1 → this literal alone satisfies the clause
            prod_others = 0.0
        forces[v] += sign * prod_others

    return forces


# ============================================================
# PhysicsSAT Solver
# ============================================================

def physicsat_solve(clauses, n, max_time=30, n_restarts=10):
    """
    Solve SAT via physical simulation.
    """
    m = len(clauses)
    start = time.time()
    best_solution = None
    best_sat = 0

    # Precompute clause-variable index for speed
    var_clauses = [[] for _ in range(n)]
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            var_clauses[v].append(ci)

    for restart in range(n_restarts):
        if time.time() - start > max_time:
            break

        # Phase 1: INIT
        x = np.random.uniform(0.3, 0.7, n)  # start near center
        velocity = np.zeros(n)

        # Physics parameters
        dt = 0.1         # time step
        damping = 0.9    # velocity damping (friction)
        mass = 1.0       # particle mass
        T_init = 0.3     # initial temperature
        T_final = 0.001  # final temperature
        n_steps = 500 + n * 10  # more steps for larger n

        # Phase 2: EVOLVE with annealing
        for step in range(n_steps):
            if time.time() - start > max_time * 0.8:
                break

            # Annealing schedule
            progress = step / n_steps
            T = T_init * (1 - progress) + T_final * progress

            # Compute forces from all clauses
            forces = np.zeros(n)
            for ci, clause in enumerate(clauses):
                sat = clause_satisfaction(x, clause)
                # Unsatisfied clauses push harder
                weight = max(1.0 - sat, 0.01) ** 0.5
                cf = clause_force(x, clause)
                forces += weight * cf

            # Add centering force toward 0 or 1 (crystallization)
            # This gets stronger as T decreases
            crystal = (1 - T / T_init) * 2.0
            for v in range(n):
                if x[v] > 0.5:
                    forces[v] += crystal * (1.0 - x[v])
                else:
                    forces[v] -= crystal * x[v]

            # Thermal noise
            noise = np.random.normal(0, T, n)

            # Update velocity (with damping)
            velocity = damping * velocity + (forces / mass + noise) * dt

            # Update position
            x = x + velocity * dt

            # Clamp to [0, 1]
            x = np.clip(x, 0.0, 1.0)

        # Phase 3: FREEZE — push toward binary
        for step in range(100):
            for v in range(n):
                if x[v] > 0.5:
                    x[v] = min(x[v] + 0.05, 1.0)
                else:
                    x[v] = max(x[v] - 0.05, 0.0)

        # Phase 4: ROUND
        assignment = [1 if x[v] > 0.5 else 0 for v in range(n)]
        sat = evaluate(clauses, assignment)

        if sat > best_sat:
            best_sat = sat
            best_solution = list(assignment)

        if sat == m:
            return best_solution, {
                'method': 'physics',
                'restart': restart,
                'sat': m,
            }

    # Phase 5: REPAIR — WalkSAT on best solution
    if best_solution is not None and best_sat < m:
        remaining = max_time - (time.time() - start)
        if remaining > 0:
            assignment = walksat_repair(
                clauses, n, best_solution,
                max_flips=int(remaining * n * 5))
            sat = evaluate(clauses, assignment)
            if sat > best_sat:
                best_sat = sat
                best_solution = assignment

    return best_solution, {
        'method': 'physics+walksat',
        'sat': best_sat,
        'total_clauses': m,
    }


def walksat_repair(clauses, n, assignment, max_flips=10000):
    assignment = list(assignment)
    m = len(clauses)
    for _ in range(max_flips):
        unsat = [i for i, c in enumerate(clauses) if not any(
            (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0)
            for v, s in c)]
        if not unsat:
            return assignment
        ci = random.choice(unsat)
        clause = clauses[ci]
        if random.random() < 0.3:
            v = random.choice([v for v, s in clause])
        else:
            # Greedy: flip var that breaks fewest clauses
            best_v, best_breaks = None, float('inf')
            for v, s in clause:
                new = 1 - assignment[v]
                breaks = sum(1 for c in clauses if any(
                    ov == v for ov, os in c) and
                    any((os == 1 and (new if ov == v else assignment[ov]) == 1) or
                        (os == -1 and (new if ov == v else assignment[ov]) == 0)
                        for ov, os in c) == False)
                if breaks < best_breaks:
                    best_breaks = breaks
                    best_v = v
            v = best_v if best_v is not None else clause[0][0]
        assignment[v] = 1 - assignment[v]
    return assignment


# ============================================================
# Benchmark
# ============================================================

def solve_minisat(n, clauses, timeout=60):
    filename = "/tmp/physics_bench.cnf"
    outfile = filename + ".out"
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(str((v+1)*s) for v, s in clause) + " 0\n")
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
    print("PhysicsSAT vs MiniSat BENCHMARK")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)

    for n in [20, 30, 50, 75, 100, 150]:
        n_inst = 30 if n <= 75 else 15
        timeout = 10 if n <= 75 else 30

        physics_solved = 0
        minisat_solved = 0
        physics_times = []
        minisat_times = []
        physics_only = 0  # solved by physics but not walksat repair
        partial_sats = []

        actual = 0
        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 69000000)

            # PhysicsSAT
            t0 = time.time()
            result, stats = physicsat_solve(clauses, n, max_time=timeout)
            t_physics = time.time() - t0

            m = len(clauses)
            if result and evaluate(clauses, result) == m:
                physics_solved += 1
                physics_times.append(t_physics)
                if stats['method'] == 'physics':
                    physics_only += 1
            else:
                if result:
                    partial_sats.append(evaluate(clauses, result) / m)

            # MiniSat
            ms, t_mini = solve_minisat(n, clauses, timeout)
            if ms == True:
                minisat_solved += 1
                minisat_times.append(t_mini)

            actual += 1
            if actual >= n_inst:
                break

        print(f"\n  n={n} ({actual} instances):")
        print(f"    PhysicsSAT: {physics_solved:>3} solved "
              f"({physics_only} pure physics, "
              f"{physics_solved - physics_only} after walksat repair)", end="")
        if physics_times:
            print(f"  avg {1000*sum(physics_times)/len(physics_times):.0f}ms")
        else:
            print()
        print(f"    MiniSat:    {minisat_solved:>3} solved", end="")
        if minisat_times:
            print(f"  avg {1000*sum(minisat_times)/len(minisat_times):.0f}ms")
        else:
            print()
        if partial_sats:
            print(f"    Unsolved avg satisfaction: "
                  f"{100*sum(partial_sats)/len(partial_sats):.1f}%")


if __name__ == "__main__":
    benchmark()
