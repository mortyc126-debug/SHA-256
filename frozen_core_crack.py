"""
CLUSTER FLIP: Crack the frozen core by flipping groups
═══════════════════════════════════════════════════════

After physics: ~√n clauses unsatisfied, ~3√n vars in those clauses.
Among those ~3√n: only ~√n are actually WRONG.

Strategy:
  1. Identify candidate vars (in unsatisfied clauses)
  2. Score candidates by unsat_frac, velocity, confidence
  3. Try flipping TOP-k candidates simultaneously
  4. If k ≈ √n and we score well → 2^√n subsets (still exponential)
     BUT if we narrow to ~10 candidates → 2^10 = 1024 (feasible!)

KEY QUESTION: How many candidates do we need to try?
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def physics_solve_state(clauses, n, seed=42):
    """Run physics, return continuous state and assignment."""
    np.random.seed(seed)
    m = len(clauses)
    x = np.full(n, 0.5)
    vel = np.zeros(n)
    for v in range(n):
        p1 = sum(1/3 for c in clauses for vi, si in c if vi==v and si==1)
        p0 = sum(1/3 for c in clauses for vi, si in c if vi==v and si==-1)
        if p1+p0 > 0:
            x[v] = 0.5 + 0.35 * (p1-p0)/(p1+p0)

    for step in range(500):
        prog = step / 500
        T = 0.25 * math.exp(-4*prog) + 0.0001
        crystal = 3.0 * prog
        forces = np.zeros(n)
        for clause in clauses:
            prod = 1.0; lits = []
            for v, s in clause:
                lit = x[v] if s == 1 else (1-x[v])
                lits.append((v, lit, s))
                prod *= max(1-lit, 1e-12)
            if prod < 0.001: continue
            w = math.sqrt(prod)
            for v, lit, s in lits:
                term = max(1-lit, 1e-12)
                forces[v] += s * w * (prod/term)
        for v in range(n):
            if x[v] > 0.5: forces[v] += crystal*(1-x[v])
            else: forces[v] -= crystal*x[v]
        noise = np.random.normal(0, T, n)
        vel = 0.93*vel + (forces+noise)*0.05
        x = np.clip(x + vel*0.05, 0, 1)

    assignment = [1 if x[v] > 0.5 else 0 for v in range(n)]
    return x, vel, assignment


def experiment_cluster_flip():
    print("=" * 70)
    print("CLUSTER FLIP: Narrowing the candidate set")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14, 16]:
        n_solved_base = 0
        n_solved_cluster = 0
        n_solved_oracle = 0
        n_total = 0
        candidate_sizes = []
        wrong_in_candidates = []

        for seed in range(200):
            clauses = random_3sat(n, int(4.267 * n), seed=seed + 4000000)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue
            sol = solutions[0]
            m = len(clauses)

            # Physics
            x, vel, assignment = physics_solve_state(clauses, n, seed=seed+42)
            base_sat = evaluate(clauses, assignment)
            n_total += 1

            if base_sat == m:
                n_solved_base += 1
                n_solved_cluster += 1
                n_solved_oracle += 1
                continue

            # Find unsatisfied clauses
            unsat_clauses = [i for i, c in enumerate(clauses)
                           if not any((s==1 and assignment[v]==1) or
                                     (s==-1 and assignment[v]==0)
                                     for v, s in c)]

            # Candidate vars: those in unsatisfied clauses
            candidates = set()
            for ci in unsat_clauses:
                for v, s in clauses[ci]:
                    candidates.add(v)

            candidates = sorted(candidates)
            candidate_sizes.append(len(candidates))

            # How many candidates are actually wrong?
            actually_wrong = [v for v in candidates if assignment[v] != sol[v]]
            wrong_in_candidates.append(len(actually_wrong))

            # Score candidates by unsat involvement
            scores = {}
            for v in candidates:
                unsat_count = sum(1 for ci in unsat_clauses
                                if any(vi == v for vi, si in clauses[ci]))
                scores[v] = unsat_count

            # Sort by score descending (most involved in unsat → most likely wrong)
            sorted_candidates = sorted(candidates, key=lambda v: -scores[v])

            # Try cluster flip: top-k candidates
            best_sat = base_sat
            best_k = 0

            for k in range(1, min(len(sorted_candidates) + 1, 13)):
                # Flip top-k candidates
                test = list(assignment)
                for v in sorted_candidates[:k]:
                    test[v] = 1 - test[v]
                sat = evaluate(clauses, test)
                if sat > best_sat:
                    best_sat = sat
                    best_k = k
                if sat == m:
                    n_solved_cluster += 1
                    break

            # Oracle: flip only the wrong ones
            oracle_test = list(assignment)
            for v in actually_wrong:
                oracle_test[v] = 1 - oracle_test[v]
            oracle_sat = evaluate(clauses, oracle_test)
            if oracle_sat == m:
                n_solved_oracle += 1

        if n_total > 0:
            print(f"\n  n={n} ({n_total} instances):")
            print(f"    Physics alone:     {n_solved_base}/{n_total} solved")
            print(f"    + Cluster flip:    {n_solved_cluster}/{n_total} solved "
                  f"(+{n_solved_cluster - n_solved_base})")
            print(f"    + Oracle flip:     {n_solved_oracle}/{n_total} solved "
                  f"(+{n_solved_oracle - n_solved_base})")
            if candidate_sizes:
                print(f"    Candidate set size: {sum(candidate_sizes)/len(candidate_sizes):.1f} "
                      f"(of {n} vars)")
            if wrong_in_candidates:
                print(f"    Wrong in candidates: {sum(wrong_in_candidates)/len(wrong_in_candidates):.1f}")
                # Narrowing ratio
                if candidate_sizes:
                    avg_cand = sum(candidate_sizes)/len(candidate_sizes)
                    avg_wrong = sum(wrong_in_candidates)/len(wrong_in_candidates)
                    print(f"    Narrowing: {n} → {avg_cand:.0f} candidates → "
                          f"{avg_wrong:.0f} actually wrong")


def experiment_exhaustive_cluster():
    print("\n" + "=" * 70)
    print("EXHAUSTIVE CLUSTER: Try ALL subsets of candidates")
    print("=" * 70)

    print("""
    For small candidate sets (≤ 15 vars): try ALL 2^k subsets.
    This is the OPTIMAL cluster flip strategy.
    How often does it solve?
    """)

    random.seed(42)
    n = 16

    results = {'physics': 0, 'cluster_greedy': 0, 'cluster_exhaust': 0,
               'oracle': 0, 'total': 0}

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 4100000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue
        sol = solutions[0]
        m = len(clauses)

        x, vel, assignment = physics_solve_state(clauses, n, seed=seed+42)
        base_sat = evaluate(clauses, assignment)
        results['total'] += 1

        if base_sat == m:
            results['physics'] += 1
            results['cluster_greedy'] += 1
            results['cluster_exhaust'] += 1
            results['oracle'] += 1
            continue

        # Find candidates
        unsat_clauses = [i for i, c in enumerate(clauses)
                        if not any((s==1 and assignment[v]==1) or
                                   (s==-1 and assignment[v]==0)
                                   for v, s in c)]
        candidates = set()
        for ci in unsat_clauses:
            for v, s in clauses[ci]:
                candidates.add(v)
        candidates = sorted(candidates)

        # Greedy: score and flip top-k
        scores = {}
        for v in candidates:
            scores[v] = sum(1 for ci in unsat_clauses
                          if any(vi == v for vi, si in clauses[ci]))
        sorted_cands = sorted(candidates, key=lambda v: -scores[v])

        for k in range(1, min(len(sorted_cands)+1, 13)):
            test = list(assignment)
            for v in sorted_cands[:k]:
                test[v] = 1 - test[v]
            if evaluate(clauses, test) == m:
                results['cluster_greedy'] += 1
                break

        # Exhaustive: try ALL subsets of candidates (if small enough)
        if len(candidates) <= 15:
            solved_exhaust = False
            for mask in range(1, 2**len(candidates)):
                test = list(assignment)
                for i, v in enumerate(candidates):
                    if mask & (1 << i):
                        test[v] = 1 - test[v]
                if evaluate(clauses, test) == m:
                    solved_exhaust = True
                    # Count how many flipped
                    n_flipped = bin(mask).count('1')
                    break
            if solved_exhaust:
                results['cluster_exhaust'] += 1

        # Oracle
        wrong = [v for v in range(n) if assignment[v] != sol[v]]
        test = list(assignment)
        for v in wrong:
            test[v] = 1 - test[v]
        if evaluate(clauses, test) == m:
            results['oracle'] += 1

    print(f"\n  n={n} ({results['total']} instances):")
    for method in ['physics', 'cluster_greedy', 'cluster_exhaust', 'oracle']:
        print(f"    {method:>16}: {results[method]}/{results['total']} "
              f"({100*results[method]/max(results['total'],1):.0f}%)")

    gain = results['cluster_exhaust'] - results['physics']
    print(f"\n    Exhaustive cluster adds: +{gain} solves over pure physics")
    if results['oracle'] > results['cluster_exhaust']:
        print(f"    Gap to oracle: {results['oracle'] - results['cluster_exhaust']} "
              f"(oracle flips vars NOT in unsat clauses)")
    else:
        print(f"    No gap — exhaustive cluster = oracle!")


if __name__ == "__main__":
    experiment_cluster_flip()
    experiment_exhaustive_cluster()
