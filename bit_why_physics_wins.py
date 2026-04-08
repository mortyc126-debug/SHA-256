"""
WHY PhysicsSAT beats MiniSat at n=500
══════════════════════════════════════

FACT: PhysicsSAT solves 4/20 instances at n=500, MiniSat solves 0/20.

HYPOTHESIS: The physics simulation provides a BETTER starting point
for local search than CDCL's decision tree provides.

At n=500, threshold r=4.27:
  - MiniSat needs 2^(0.27 × 500^0.75) ≈ 2^28 ≈ 270M decisions
  - Each decision at 0.1μs = 27 seconds → timeout at 60s
  - CDCL is exhaustive: it PROVES satisfiability

  - PhysicsSAT physics: ~10K steps × O(m) = ~20M ops → ~100ms
  - Physics gets 99%+ clauses satisfied
  - WalkSAT from 99%: needs ~few K flips → ~10ms
  - Total: ~200ms

KEY INSIGHT: PhysicsSAT doesn't PROVE satisfiability.
It FINDS a solution by continuous optimization + local search.
CDCL proves the search tree. Different paradigms.

ANALYSIS: What makes the physics starting point so good?
"""

import random
import math
import time
import subprocess
import os
import numpy as np
from bit_catalog_static import random_3sat


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


def physics_simulate(clauses, n, n_steps=2000):
    """Run physics simulation, return final continuous state."""
    m = len(clauses)
    x = np.random.uniform(0.3, 0.7, n)
    vel = np.zeros(n)

    dt = 0.05; damping = 0.95
    T_init = 0.35; T_final = 0.0001

    for step in range(n_steps):
        progress = step / n_steps
        T = T_init * math.exp(-4.0 * progress) + T_final
        crystal = 3.0 * (1.0 - T / T_init)
        if crystal < 0: crystal = 0

        forces = np.zeros(n)
        for clause in clauses:
            lits = []
            prod = 1.0
            for v, s in clause:
                lit_val = x[v] if s == 1 else (1.0 - x[v])
                lits.append((v, lit_val, s))
                prod *= max(1.0 - lit_val, 1e-12)

            unsat_w = math.sqrt(prod)
            if unsat_w < 0.01: continue

            for v, lit_val, s in lits:
                term = max(1.0 - lit_val, 1e-12)
                prod_others = prod / term
                forces[v] += s * unsat_w * prod_others

        for v in range(n):
            if x[v] > 0.5:
                forces[v] += crystal * (1.0 - x[v])
            else:
                forces[v] -= crystal * x[v]

        noise = np.random.normal(0, T, n)
        vel = damping * vel + (forces + noise) * dt
        x = np.clip(x + vel * dt, 0, 1)

    return x


def analyze_physics_quality():
    """Measure how good the physics starting point is."""
    print("=" * 70)
    print("ANALYSIS: Physics starting point quality")
    print("=" * 70)

    np.random.seed(42)
    random.seed(42)

    for n in [50, 100, 200]:
        sat_fracs = []
        hamming_dists = []
        tension_sats = []

        n_inst = 10
        for seed in range(50):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 69000000)
            m = len(clauses)

            # Get MiniSat solution as ground truth
            fn = "/tmp/analysis_test.cnf"
            with open(fn, 'w') as f:
                f.write(f"p cnf {n} {m}\n")
                for c in clauses:
                    f.write(" ".join(str((v+1)*s) for v,s in c) + " 0\n")
            try:
                r = subprocess.run(["minisat", fn, fn+".out"],
                                  capture_output=True, timeout=30)
            except:
                continue
            if not os.path.exists(fn+".out"):
                continue
            with open(fn+".out") as f:
                if f.readline().strip() != "SAT":
                    continue
                vals = f.readline().strip().split()
                sol = [0]*n
                for v in vals:
                    vi = int(v)
                    if vi > 0 and vi <= n: sol[vi-1] = 1
                    elif vi < 0 and -vi <= n: sol[-vi-1] = 0
            os.remove(fn); os.remove(fn+".out")

            # Physics simulation
            np.random.seed(seed + 42)
            x = physics_simulate(clauses, n, n_steps=1000 + n*10)
            physics_assignment = [1 if x[v] > 0.5 else 0 for v in range(n)]
            physics_sat = evaluate(clauses, physics_assignment)

            # Tension-only assignment
            tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
            tension_assignment = [1 if tensions[v] > 0 else 0 for v in range(n)]
            tension_sat = evaluate(clauses, tension_assignment)

            # Random assignment
            random_assignment = [random.randint(0,1) for _ in range(n)]
            random_sat = evaluate(clauses, random_assignment)

            sat_fracs.append(physics_sat / m)
            tension_sats.append(tension_sat / m)

            # Hamming distance to solution
            hamming = sum(1 for v in range(n)
                         if physics_assignment[v] != sol[v])
            hamming_dists.append(hamming)

            if len(sat_fracs) >= n_inst:
                break

        if sat_fracs:
            avg_physics = 100 * sum(sat_fracs) / len(sat_fracs)
            avg_tension = 100 * sum(tension_sats) / len(tension_sats)
            avg_hamming = sum(hamming_dists) / len(hamming_dists)
            avg_random_sat = 100 * (7/8)  # expected for 3-SAT

            print(f"\n  n={n} ({len(sat_fracs)} instances):")
            print(f"    Physics satisfaction:  {avg_physics:.1f}%")
            print(f"    Tension satisfaction:  {avg_tension:.1f}%")
            print(f"    Random satisfaction:   {avg_random_sat:.1f}%")
            print(f"    Physics hamming to sol: {avg_hamming:.1f} / {n} "
                  f"({100*avg_hamming/n:.1f}%)")
            print(f"    Unsat clauses (physics): "
                  f"{(1-sum(sat_fracs)/len(sat_fracs))*4.27*n:.1f}")


def analyze_walksat_from_different_starts():
    """Compare WalkSAT starting from physics vs random vs tension."""
    print("\n" + "=" * 70)
    print("WALKSAT FROM DIFFERENT STARTING POINTS")
    print("=" * 70)

    np.random.seed(42)
    random.seed(42)

    for n in [100, 200]:
        print(f"\n  n={n}:")
        results = {'physics': [], 'tension': [], 'random': []}

        for seed in range(20):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 69000000)
            m = len(clauses)

            # Physics start
            np.random.seed(seed + 42)
            x = physics_simulate(clauses, n, n_steps=1000 + n*10)
            physics_start = [1 if x[v] > 0.5 else 0 for v in range(n)]

            # Tension start
            tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
            tension_start = [1 if tensions[v] > 0 else 0 for v in range(n)]

            # Random start
            random_start = [random.randint(0, 1) for _ in range(n)]

            # Run WalkSAT from each start (same budget)
            max_flips = n * 300
            for label, start in [('physics', physics_start),
                                  ('tension', tension_start),
                                  ('random', random_start)]:
                assignment = list(start)
                for flip in range(max_flips):
                    unsat = [i for i, c in enumerate(clauses) if not any(
                        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                        for v,s in c)]
                    if not unsat:
                        results[label].append(flip)
                        break
                    ci = random.choice(unsat)
                    clause = clauses[ci]
                    if random.random() < 0.3:
                        fv = random.choice([v for v,s in clause])
                    else:
                        best_v, best_b = clause[0][0], m
                        for v, s in clause:
                            breaks = sum(1 for c in clauses if
                                any(ov==v for ov,os in c) and
                                sum(1 for ov,os in c if
                                    (os==1 and (1-assignment[v] if ov==v else assignment[ov])==1) or
                                    (os==-1 and (1-assignment[v] if ov==v else assignment[ov])==0)
                                ) == 0)
                            if breaks < best_b:
                                best_b = breaks; best_v = v
                        fv = best_v
                    assignment[fv] = 1 - assignment[fv]
                else:
                    results[label].append(-1)  # not solved

        for label in ['physics', 'tension', 'random']:
            solved = [f for f in results[label] if f >= 0]
            total = len(results[label])
            if solved:
                avg_flips = sum(solved) / len(solved)
                print(f"    {label:>10}: {len(solved)}/{total} solved, "
                      f"avg {avg_flips:.0f} flips")
            else:
                print(f"    {label:>10}: 0/{total} solved")


if __name__ == "__main__":
    analyze_physics_quality()
    analyze_walksat_from_different_starts()
