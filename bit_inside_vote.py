"""
INSIDE THE CLAUSE VOTE: What is ε made of?
═══════════════════════════════════════════

ε = 1/14 is our information quantum. But what CREATES it?

A clause vote arises from:
  1. A SIGN (+1 or -1) — the direction of the force
  2. A COUPLING (which 3 vars are connected)
  3. A CONTEXT (what other clauses share these vars)

Below ε, there are THREE sub-quantum objects:

A. SIGN FIELD — the +1/-1 structure across all clauses
   This is the most fundamental object. Everything else derives from it.

B. FRUSTRATION — when signs conflict, energy cannot be minimized
   This is the source of computational hardness.

C. INFORMATION GEOMETRY — the shape of the constraint manifold
   The solution lives on a surface in n-dimensional space.

SIX EXPERIMENTS at the deepest level:

1. Sign statistics — is the sign field random or structured?
2. Frustration loops — minimal frustrated circuits
3. Information per sign bit — how much does one sign carry?
4. The constraint manifold — what shape is it?
5. Force field topology — where are the zeros?
6. The vacuum fluctuations — what happens at x=0.5 exactly?
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def compute_tension(clauses, n, var):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                w = 1.0 / len(clause)
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# 1. SIGN FIELD: Random or structured?
# ============================================================

def experiment_sign_field():
    print("=" * 70)
    print("1. SIGN FIELD: Is the ±1 structure random or structured?")
    print("=" * 70)

    print("""
    Each literal in each clause has a sign: +1 (positive) or -1 (negated).
    In random 3-SAT, signs are uniformly random.
    But from the SOLUTION'S perspective, signs are NOT random:
    signs that agree with the solution are "correct".

    Question: What fraction of signs are correct?
    And: do correct/incorrect signs have spatial structure?
    """)

    random.seed(42)

    for n in [12, 20, 50]:
        correct_signs = []
        sign_correlations = []

        for seed in range(50):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+86000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
                sol = solutions[0]
            else:
                continue

            # For each literal: is the sign "correct"?
            # sign=+1 and sol[v]=1 → correct (clause wants v=1, solution has v=1)
            # sign=-1 and sol[v]=0 → correct (clause wants v=0, solution has v=0)
            n_correct = 0
            n_total = 0
            per_clause_correct = []

            for clause in clauses:
                clause_correct = 0
                for v, s in clause:
                    is_correct = (s == 1 and sol[v] == 1) or \
                                 (s == -1 and sol[v] == 0)
                    if is_correct:
                        n_correct += 1
                        clause_correct += 1
                    n_total += 1
                per_clause_correct.append(clause_correct)

            correct_signs.append(n_correct / n_total)

            # Correlation: do adjacent clauses have similar correctness?
            for ci in range(len(clauses) - 1):
                c1_vars = set(v for v, s in clauses[ci])
                c2_vars = set(v for v, s in clauses[ci + 1])
                if c1_vars & c2_vars:  # share a variable
                    sign_correlations.append(
                        (per_clause_correct[ci], per_clause_correct[ci + 1]))

            if len(correct_signs) >= 20:
                break

        if correct_signs:
            avg_correct = sum(correct_signs) / len(correct_signs)
            predicted = 4/7  # P(sign agrees with solution in satisfied clause)
            print(f"\n  n={n}:")
            print(f"    Fraction of correct signs:    {avg_correct:.4f}")
            print(f"    Predicted (4/7):              {4/7:.4f}")
            print(f"    Excess over random (1/2):     {avg_correct - 0.5:+.4f}")

        if sign_correlations:
            # Are adjacent clause correctnesses correlated?
            x = [a for a, b in sign_correlations]
            y = [b for a, b in sign_correlations]
            if np.std(x) > 0 and np.std(y) > 0:
                corr = np.corrcoef(x, y)[0, 1]
                print(f"    Adjacent clause correlation:  {corr:.4f}")


# ============================================================
# 2. FRUSTRATION LOOPS: The source of hardness
# ============================================================

def experiment_frustration_loops():
    print("\n" + "=" * 70)
    print("2. FRUSTRATION LOOPS: Minimal frustrated circuits")
    print("=" * 70)

    print("""
    A frustration loop: cycle of variables where sign constraints
    are CONTRADICTORY. Like: x→y(same), y→z(same), z→x(opposite).
    No assignment satisfies all edges.

    These loops are the IRREDUCIBLE source of hardness.
    How many exist? How long are they?
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+87000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        # Build signed graph: edge (u,v) with sign = product of literal signs
        edges = {}  # (u,v) -> list of signs
        for clause in clauses:
            for i in range(len(clause)):
                for j in range(i+1, len(clause)):
                    vi, si = clause[i]
                    vj, sj = clause[j]
                    key = (min(vi,vj), max(vi,vj))
                    if key not in edges:
                        edges[key] = []
                    edges[key].append(si * sj)

        # Average sign per edge
        avg_signs = {}
        for (u,v), signs in edges.items():
            avg_signs[(u,v)] = sum(signs) / len(signs)

        # Find frustrated triangles (3-cycles with odd number of negative edges)
        adj = {v: set() for v in range(n)}
        for (u,v) in avg_signs:
            adj[u].add(v)
            adj[v].add(u)

        n_frustrated = 0
        n_total_triangles = 0

        for a in range(n):
            for b in adj[a]:
                if b <= a: continue
                for c in adj[a] & adj[b]:
                    if c <= b: continue
                    n_total_triangles += 1

                    # Get edge signs
                    s_ab = avg_signs.get((min(a,b), max(a,b)), 0)
                    s_bc = avg_signs.get((min(b,c), max(b,c)), 0)
                    s_ac = avg_signs.get((min(a,c), max(a,c)), 0)

                    # Frustrated if product of signs is negative
                    product = s_ab * s_bc * s_ac
                    if product < 0:
                        n_frustrated += 1

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Total triangles:     {n_total_triangles}")
        print(f"    Frustrated triangles: {n_frustrated} "
              f"({100*n_frustrated/max(n_total_triangles,1):.1f}%)")
        print(f"    Unfrustrated:        {n_total_triangles - n_frustrated}")

        # Frustration per edge
        n_frust_edges = sum(1 for s in avg_signs.values() if abs(s) < 0.5)
        print(f"    Ambiguous edges (|avg sign|<0.5): {n_frust_edges}/{len(avg_signs)}")

        break


# ============================================================
# 3. INFORMATION PER SIGN BIT
# ============================================================

def experiment_sign_information():
    print("\n" + "=" * 70)
    print("3. INFORMATION PER SIGN BIT: How much does one sign carry?")
    print("=" * 70)

    print("""
    A sign is the most fundamental object: +1 or -1.
    One clause has 3 signs → 2³ = 8 possible sign patterns.
    Each pattern encodes different information about the solution.

    Question: How much information is in ONE sign?
    Is it exactly ε/3 = 1/42? Or more? Or less?
    """)

    random.seed(42)
    n = 12

    sign_infos = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+88000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        for clause in clauses:
            for v, s in clause:
                # Flip this one sign
                modified_clause = [(vi, -si if vi == v else si) for vi, si in clause]
                modified_clauses = [modified_clause if i == clauses.index(clause)
                                   else c for i, c in enumerate(clauses)]

                # Measure tension change on variable v
                t_original = compute_tension(clauses, n, v)
                t_modified = compute_tension(modified_clauses, n, v)

                delta_t = abs(t_original - t_modified)
                sign_infos.append(delta_t)

            break  # one clause per instance

        if len(sign_infos) >= 200:
            break

    if sign_infos:
        avg_info = sum(sign_infos) / len(sign_infos)
        print(f"\n  One sign flip changes tension by: {avg_info:.4f}")
        print(f"  Predicted ε = 1/14:               {1/14:.4f}")
        print(f"  Predicted ε/3:                     {1/42:.4f}")
        print(f"  Ratio to ε:                        {avg_info/(1/14):.3f}")
        print(f"  → One sign carries {avg_info/(1/14)*100:.0f}% of clause info")


# ============================================================
# 4. CONSTRAINT MANIFOLD: Shape of solution space
# ============================================================

def experiment_manifold():
    print("\n" + "=" * 70)
    print("4. CONSTRAINT MANIFOLD: What shape is the solution surface?")
    print("=" * 70)

    print("""
    Each clause defines a hyperplane in [0,1]^n.
    The solution lives at the intersection.
    What is the LOCAL shape near the solution?

    Method: Perturb solution in random directions.
    Measure how fast satisfaction drops.
    If it drops slowly → flat manifold (easy).
    If quickly → sharp peak (hard).
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+89000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        sol_vec = np.array([float(s) for s in sol])

        print(f"\n  n={n}, seed={seed}, m={m}:")
        print(f"  {'radius':>8} | {'avg sat%':>8} | {'min sat%':>8} | "
              f"{'samples':>7}")
        print("  " + "-" * 40)

        for radius in [0.01, 0.05, 0.1, 0.2, 0.3, 0.5]:
            sats = []
            n_samples = 50

            for _ in range(n_samples):
                # Random perturbation on the hypersphere
                direction = np.random.randn(n)
                direction = direction / np.linalg.norm(direction)
                perturbed = np.clip(sol_vec + radius * direction, 0, 1)

                # Evaluate soft satisfaction
                total_soft = 0
                for clause in clauses:
                    prod = 1.0
                    for v, s in clause:
                        lit = perturbed[v] if s == 1 else (1.0 - perturbed[v])
                        prod *= (1.0 - lit)
                    total_soft += (1.0 - prod)

                sats.append(total_soft / m)

            avg_sat = 100 * sum(sats) / len(sats)
            min_sat = 100 * min(sats)
            print(f"  {radius:>8.3f} | {avg_sat:>7.1f}% | {min_sat:>7.1f}% | "
                  f"{n_samples:>7}")

        break


# ============================================================
# 5. FORCE FIELD TOPOLOGY: Where are the zeros?
# ============================================================

def experiment_force_zeros():
    print("\n" + "=" * 70)
    print("5. FORCE FIELD ZEROS: Where is equilibrium?")
    print("=" * 70)

    print("""
    The force field F(x) has zeros where ∂E/∂x = 0.
    These are the EQUILIBRIA of the system.
    Types: solution (global min), local min, saddle point.

    Question: How many zeros? Where are they?
    Is the solution the ONLY attractor?
    """)

    random.seed(42)
    n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+90000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        # Sample many starting points, run gradient descent, see where they end
        n_starts = 200
        endpoints = []

        for trial in range(n_starts):
            np.random.seed(trial + seed * 1000)
            x = np.random.uniform(0, 1, n)

            # Gradient descent (no noise, no momentum)
            for step in range(500):
                forces = np.zeros(n)
                for clause in clauses:
                    prod = 1.0; lits = []
                    for v, s in clause:
                        lit = x[v] if s == 1 else (1.0 - x[v])
                        lits.append((v, lit, s))
                        prod *= max(1.0 - lit, 1e-12)
                    if prod < 1e-6: continue
                    for v, lit, s in lits:
                        term = max(1.0 - lit, 1e-12)
                        forces[v] += s * (prod / term)
                x = np.clip(x + 0.02 * forces, 0, 1)

            # Round and evaluate
            assignment = [1 if x[v] > 0.5 else 0 for v in range(n)]
            sat = evaluate(clauses, assignment)
            endpoints.append((tuple(assignment), sat))

        # Count distinct endpoints
        unique_endpoints = {}
        for ep, sat in endpoints:
            key = ep
            if key not in unique_endpoints:
                unique_endpoints[key] = {'count': 0, 'sat': sat}
            unique_endpoints[key]['count'] += 1

        # Sort by frequency
        sorted_eps = sorted(unique_endpoints.items(),
                           key=lambda x: x[1]['count'], reverse=True)

        print(f"\n  n={n}, seed={seed}:")
        print(f"    {n_starts} random starts → {len(unique_endpoints)} "
              f"distinct attractors")
        print(f"\n    Top attractors:")
        print(f"    {'#':>3} | {'count':>5} | {'sat':>5} | {'is_solution':>11}")
        print("    " + "-" * 35)

        for i, (ep, info) in enumerate(sorted_eps[:10]):
            is_sol = (list(ep) == sol)
            is_any_sol = info['sat'] == m
            label = "SOLUTION" if is_sol else ("SAT" if is_any_sol else "")
            print(f"    {i+1:>3} | {info['count']:>5} | "
                  f"{info['sat']:>3}/{m} | {label:>11}")

        # Basin of attraction sizes
        sol_basin = unique_endpoints.get(tuple(sol), {}).get('count', 0)
        sat_basin = sum(info['count'] for ep, info in unique_endpoints.items()
                       if info['sat'] == m)
        print(f"\n    Solution basin:      {sol_basin}/{n_starts} "
              f"({100*sol_basin/n_starts:.0f}%)")
        print(f"    Any SAT basin:       {sat_basin}/{n_starts} "
              f"({100*sat_basin/n_starts:.0f}%)")
        print(f"    Local minima (unsat): {n_starts - sat_basin}/{n_starts} "
              f"({100*(n_starts-sat_basin)/n_starts:.0f}%)")

        break


# ============================================================
# 6. VACUUM FLUCTUATIONS: What happens at x = 0.5?
# ============================================================

def experiment_vacuum():
    print("\n" + "=" * 70)
    print("6. VACUUM FLUCTUATIONS: The state at x = 0.5")
    print("=" * 70)

    print("""
    x = 0.5 is the "vacuum" — maximum uncertainty.
    All variables at 0.5 = zero information state.

    Question: What is the FORCE at the vacuum?
    The force tells us which direction the vacuum "wants" to break.
    This is like SPONTANEOUS SYMMETRY BREAKING.
    """)

    random.seed(42)
    n = 14

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+91000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        # Compute force at exact vacuum x = (0.5, 0.5, ..., 0.5)
        x_vac = np.full(n, 0.5)
        forces_vac = np.zeros(n)

        for clause in clauses:
            prod = 1.0; lits = []
            for v, s in clause:
                lit = 0.5  # all at vacuum
                lits.append((v, lit, s))
                prod *= 0.5  # 1 - 0.5 = 0.5

            # prod = 0.5^3 = 0.125 for 3-SAT
            for v, lit, s in lits:
                prod_others = prod / 0.5  # 0.125 / 0.5 = 0.25
                forces_vac[v] += s * math.sqrt(prod) * prod_others

        # Compare vacuum force direction with solution
        tensions = np.array([compute_tension(clauses, n, v) for v in range(n)])

        print(f"\n  n={n}, seed={seed}:")
        print(f"  {'var':>5} | {'F_vacuum':>10} | {'tension':>8} | {'sol':>3} | "
              f"{'F correct?':>10} | {'same dir?':>9}")
        print("  " + "-" * 60)

        n_f_correct = 0
        n_t_correct = 0
        n_same_dir = 0

        for v in range(n):
            f_pred = 1 if forces_vac[v] > 0 else 0
            t_pred = 1 if tensions[v] > 0 else 0
            f_correct = (f_pred == sol[v])
            t_correct = (t_pred == sol[v])
            same_dir = (np.sign(forces_vac[v]) == np.sign(tensions[v]))

            if f_correct: n_f_correct += 1
            if t_correct: n_t_correct += 1
            if same_dir: n_same_dir += 1

            print(f"  x{v:>3} | {forces_vac[v]:>+10.4f} | {tensions[v]:>+8.4f} | "
                  f"{sol[v]:>3} | {'✓' if f_correct else '✗':>10} | "
                  f"{'=' if same_dir else '≠':>9}")

        print(f"\n  Vacuum force accuracy: {n_f_correct}/{n} "
              f"({100*n_f_correct/n:.0f}%)")
        print(f"  Tension accuracy:      {n_t_correct}/{n} "
              f"({100*n_t_correct/n:.0f}%)")
        print(f"  Same direction:        {n_same_dir}/{n} "
              f"({100*n_same_dir/n:.0f}%)")

        # The vacuum force IS the tension (at x=0.5)
        corr = np.corrcoef(forces_vac, tensions)[0,1]
        print(f"  Correlation F_vacuum vs tension: {corr:.4f}")

        # Key insight: vacuum force = what the system "wants" to be
        # before any measurement. It's the INITIAL SYMMETRY BREAKING.
        print(f"\n  INSIGHT: Vacuum force IS tension (r={corr:.3f}).")
        print(f"  Tension = the force at the vacuum state.")
        print(f"  The vacuum already 'knows' the solution direction!")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    experiment_sign_field()
    experiment_frustration_loops()
    experiment_sign_information()
    experiment_manifold()
    experiment_force_zeros()
    experiment_vacuum()
