"""
ThermoSAT v2 — полностью переработанный
════════════════════════════════════════

Стратегия:
  SIGNAL PHASE: Proper DPLL + tension + UP (для сигнальных переменных)
  NOISE PHASE:  WalkSAT guided by self-cancellation (для шумовых)

  Ключевая инновация: В точке перехода сигнал→шум DPLL ОСТАНАВЛИВАЕТСЯ
  и передаёт управление WalkSAT. Это экономит 2^(n^T) шагов бесполезного
  перебора в зоне, где DPLL accuracy < 50%.

  Вторая инновация: Propagated tension (2 итерации) вместо простого tension.
  Третья: Self-cancellation для WalkSAT фазы.
"""

import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat


# ============================================================
# Core: evaluate, UP, tension
# ============================================================

def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for v, s in clause:
            if (s == 1 and assignment[v] == 1) or \
               (s == -1 and assignment[v] == 0):
                sat += 1
                break
    return sat


def unit_propagate(clauses, n, fixed):
    f = dict(fixed)
    cascade = 0
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; free = []
            for v, s in clause:
                if v in f:
                    if (s == 1 and f[v] == 1) or (s == -1 and f[v] == 0):
                        sat = True; break
                else:
                    free.append((v, s))
            if sat: continue
            if len(free) == 0:
                return f, cascade, True
            if len(free) == 1:
                v, s = free[0]
                if v not in f:
                    f[v] = 1 if s == 1 else 0
                    cascade += 1
                    changed = True
    return f, cascade, False


def compute_tension(clauses, n, var, fixed):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True; break
            else:
                rem.append((v, s))
        if sat: continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# Innovation: Propagated tension (2 hops of message passing)
# ============================================================

def compute_propagated_tension(clauses, n, fixed):
    """
    Two rounds of tension propagation.
    Round 1: standard tension from clauses
    Round 2: average in neighbor tensions (damped)
    """
    # Build adjacency
    adj = {v: set() for v in range(n) if v not in fixed}
    for clause in clauses:
        unfixed_in = [v for v, s in clause if v not in fixed]
        for i in range(len(unfixed_in)):
            for j in range(i + 1, len(unfixed_in)):
                adj[unfixed_in[i]].add(unfixed_in[j])
                adj[unfixed_in[j]].add(unfixed_in[i])

    # Round 1
    t1 = {}
    for v in adj:
        t1[v] = compute_tension(clauses, n, v, fixed)

    # Round 2: propagate
    t2 = {}
    damping = 0.3
    for v in t1:
        neighbors = adj.get(v, set())
        if neighbors:
            nav = sum(t1.get(u, 0) for u in neighbors) / len(neighbors)
            t2[v] = t1[v] + damping * nav
        else:
            t2[v] = t1[v]

    return t2, adj


# ============================================================
# Innovation: Self-cancellation for WalkSAT guidance
# ============================================================

def self_cancel_scores(tensions, adj):
    """Higher score = more coherent with neighborhood = more reliable."""
    scores = {}
    for v in tensions:
        neighbors = adj.get(v, set())
        if neighbors:
            nav = sum(tensions.get(u, 0) for u in neighbors) / len(neighbors)
            scores[v] = abs(tensions[v] + nav)
        else:
            scores[v] = abs(tensions[v])
    return scores


# ============================================================
# PHASE 1: DPLL with tension branching (signal vars only)
# ============================================================

def dpll_signal_phase(clauses, n, fixed, tensions, noise_threshold=0.15,
                      max_calls=100000, stats=None):
    """
    DPLL that STOPS when it runs out of signal variables.
    Returns: (fixed_dict, success_flag, unfixed_noise_vars)
    """
    calls = [0]

    def dpll(fixed, depth):
        calls[0] += 1
        if calls[0] > max_calls:
            return None

        # UP
        fixed, cascade, conflict = unit_propagate(clauses, n, fixed)
        if stats: stats['up_fixes'] += cascade
        if conflict:
            if stats: stats['backtracks'] += 1
            return None

        # Unfixed variables
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            return fixed  # all fixed!

        # Recompute tensions for unfixed vars
        local_tensions = {}
        for v in unfixed:
            local_tensions[v] = compute_tension(clauses, n, v, fixed)

        # Find signal variables (|tension| > threshold)
        signal = [v for v in unfixed if abs(local_tensions[v]) > noise_threshold]

        if not signal:
            # NO MORE SIGNAL VARS — stop DPLL, return partial assignment
            return fixed  # hand off to noise phase

        # Pick the strongest signal variable
        best = max(signal, key=lambda v: abs(local_tensions[v]))
        sigma = local_tensions[best]
        fv = 1 if sigma >= 0 else 0
        if stats: stats['decisions'] += 1

        # Try tension-guided value first
        f = dict(fixed)
        f[best] = fv
        r = dpll(f, depth + 1)
        if r is not None:
            return r

        # Backtrack: try opposite
        f = dict(fixed)
        f[best] = 1 - fv
        return dpll(f, depth + 1)

    result = dpll(dict(fixed), 0)
    return result


# ============================================================
# PHASE 2: WalkSAT with self-cancellation guidance
# ============================================================

def walksat_noise_phase(clauses, n, fixed, tensions, adj,
                        max_flips=None, stats=None):
    """
    WalkSAT starting from partial assignment (from signal phase).
    Uses self-cancellation to choose flip targets.
    """
    # Initialize unfixed vars
    unfixed = [v for v in range(n) if v not in fixed]
    if not unfixed:
        assignment = [fixed.get(v, 0) for v in range(n)]
        return assignment if evaluate(clauses, assignment) == len(clauses) else None

    # Initialize noise vars with mild tension bias
    assignment = [0] * n
    for v in range(n):
        if v in fixed:
            assignment[v] = fixed[v]
        else:
            t = tensions.get(v, 0)
            assignment[v] = 1 if random.random() < (0.5 + 0.15 * t) else 0

    if max_flips is None:
        max_flips = max(len(unfixed) * 100, 1000)

    # Self-cancellation scores
    sc = self_cancel_scores(tensions, adj)

    for flip in range(max_flips):
        sat_count = evaluate(clauses, assignment)
        if sat_count == len(clauses):
            return assignment

        # Find unsatisfied clauses
        unsat = []
        for ci, clause in enumerate(clauses):
            ok = False
            for v, s in clause:
                if (s == 1 and assignment[v] == 1) or \
                   (s == -1 and assignment[v] == 0):
                    ok = True; break
            if not ok:
                unsat.append(ci)

        if not unsat:
            return assignment

        # Pick random unsatisfied clause
        ci = random.choice(unsat)
        clause = clauses[ci]

        # Score each var in clause for flipping
        flip_candidates = []
        for v, s in clause:
            # Count how many clauses would BREAK if we flip v
            current_val = assignment[v]
            new_val = 1 - current_val
            breaks = 0
            for other_clause in clauses:
                clause_sat_before = False
                clause_sat_after = False
                for ov, os in other_clause:
                    if ov == v:
                        if (os == 1 and current_val == 1) or \
                           (os == -1 and current_val == 0):
                            clause_sat_before = True
                        if (os == 1 and new_val == 1) or \
                           (os == -1 and new_val == 0):
                            clause_sat_after = True
                    else:
                        if (os == 1 and assignment[ov] == 1) or \
                           (os == -1 and assignment[ov] == 0):
                            clause_sat_before = True
                            clause_sat_after = True

                if clause_sat_before and not clause_sat_after:
                    breaks += 1

            # Combined score: fewer breaks is better
            # Self-cancellation penalty: prefer flipping low-SC vars
            sc_penalty = sc.get(v, 0) * 0.5
            score = -breaks - sc_penalty
            flip_candidates.append((v, score))

        # Noise: with 15% prob pick random (exploration)
        if random.random() < 0.15 or not flip_candidates:
            flip_var = random.choice([v for v, s in clause])
        else:
            # Pick best scoring variable
            flip_var = max(flip_candidates, key=lambda x: x[1])[0]

        assignment[flip_var] = 1 - assignment[flip_var]
        if stats: stats['walk_flips'] += 1

    return assignment


# ============================================================
# ThermoSAT v2: the complete solver
# ============================================================

def thermosat_solve(clauses, n, max_time=60, max_tries=50):
    """
    Complete ThermoSAT solver.
    Returns: (solution_or_None, stats_dict)
    """
    stats = {
        'decisions': 0, 'backtracks': 0, 'up_fixes': 0,
        'walk_flips': 0, 'restarts': 0, 'phase_switches': 0,
        'signal_solved': 0, 'walk_solved': 0,
    }

    start = time.time()
    best = None
    best_sat = 0

    for attempt in range(max_tries):
        if time.time() - start > max_time:
            break
        stats['restarts'] = attempt

        # SENSE: compute propagated tensions
        tensions, adj = compute_propagated_tension(clauses, n, {})

        # SIGNAL PHASE: DPLL on signal vars
        # Adjust noise threshold based on attempt (diversification)
        noise_th = 0.15 + attempt * 0.02  # gradually lower the bar
        noise_th = min(noise_th, 0.5)

        remaining_time = max_time - (time.time() - start)
        max_calls = min(50000, int(remaining_time * 10000))

        result = dpll_signal_phase(
            clauses, n, {}, tensions,
            noise_threshold=noise_th,
            max_calls=max_calls,
            stats=stats
        )

        if result is None:
            continue

        # Check if DPLL solved it completely
        unfixed = [v for v in range(n) if v not in result]
        if not unfixed:
            assignment = [result.get(v, 0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                stats['signal_solved'] += 1
                return assignment, stats
        else:
            stats['phase_switches'] += 1

        # NOISE PHASE: WalkSAT on remaining
        remaining_time = max_time - (time.time() - start)
        if remaining_time <= 0:
            break

        max_flips = max(len(unfixed) * 200, 5000)
        assignment = walksat_noise_phase(
            clauses, n, result, tensions, adj,
            max_flips=max_flips,
            stats=stats
        )

        if assignment:
            sat = evaluate(clauses, assignment)
            if sat == len(clauses):
                stats['walk_solved'] += 1
                return assignment, stats
            if sat > best_sat:
                best_sat = sat
                best = list(assignment)

    return best, stats


# ============================================================
# Benchmark
# ============================================================

def solve_minisat(n, clauses, timeout=60):
    filename = "/tmp/thermo2_bench.cnf"
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
    print("ThermoSAT v2 vs MiniSat BENCHMARK")
    print("=" * 70)
    print("  Ratio = 4.27 (threshold), random 3-SAT")

    random.seed(42)

    for n in [20, 30, 50, 75, 100, 150]:
        thermo_solved = 0
        minisat_solved = 0
        thermo_times = []
        minisat_times = []

        n_inst = 30 if n <= 100 else 15
        timeout = 10 if n <= 75 else 30

        actual_inst = 0

        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 62000000)

            # ThermoSAT
            t0 = time.time()
            result, stats = thermosat_solve(clauses, n, max_time=timeout)
            t_thermo = time.time() - t0

            thermo_ok = (result is not None and
                        evaluate(clauses, result) == len(clauses))
            if thermo_ok:
                thermo_solved += 1
                thermo_times.append(t_thermo)

            # MiniSat
            ms_result, t_mini = solve_minisat(n, clauses, timeout)
            if ms_result == True:
                minisat_solved += 1
                minisat_times.append(t_mini)

            actual_inst += 1
            if actual_inst >= n_inst:
                break

        print(f"\n  n={n} ({actual_inst} instances, timeout={timeout}s):")
        print(f"    ThermoSAT: {thermo_solved:>3}/{actual_inst} solved", end="")
        if thermo_times:
            print(f"  avg {1000*sum(thermo_times)/len(thermo_times):>7.0f}ms")
        else:
            print()
        print(f"    MiniSat:   {minisat_solved:>3}/{actual_inst} solved", end="")
        if minisat_times:
            print(f"  avg {1000*sum(minisat_times)/len(minisat_times):>7.0f}ms")
        else:
            print()

        if thermo_solved > 0 and minisat_solved > 0 and thermo_times and minisat_times:
            ratio = sum(minisat_times)/len(minisat_times) / (sum(thermo_times)/len(thermo_times))
            print(f"    Speed ratio (MiniSat/ThermoSAT): {ratio:.2f}×")


# ============================================================
# Below-threshold test (easier instances where ThermoSAT should shine)
# ============================================================

def below_threshold_test():
    print("\n" + "=" * 70)
    print("BELOW-THRESHOLD TEST: r = 3.5 (easier instances)")
    print("=" * 70)

    random.seed(42)

    for n in [50, 100, 200, 300]:
        thermo_solved = 0
        minisat_solved = 0
        thermo_times = []
        minisat_times = []

        n_inst = 20
        timeout = 15

        for seed in range(n_inst * 3):
            clauses = random_3sat(n, int(3.5 * n), seed=seed + 63000000)

            t0 = time.time()
            result, stats = thermosat_solve(clauses, n, max_time=timeout)
            t_thermo = time.time() - t0

            if result and evaluate(clauses, result) == len(clauses):
                thermo_solved += 1
                thermo_times.append(t_thermo)

            ms_result, t_mini = solve_minisat(n, clauses, timeout)
            if ms_result == True:
                minisat_solved += 1
                minisat_times.append(t_mini)

            if thermo_solved >= n_inst and minisat_solved >= n_inst:
                break

        total = max(thermo_solved, minisat_solved, 1)
        print(f"\n  n={n} (r=3.5):")
        print(f"    ThermoSAT: {thermo_solved} solved", end="")
        if thermo_times:
            print(f"  avg {1000*sum(thermo_times)/len(thermo_times):>7.0f}ms")
        else:
            print()
        print(f"    MiniSat:   {minisat_solved} solved", end="")
        if minisat_times:
            print(f"  avg {1000*sum(minisat_times)/len(minisat_times):>7.0f}ms")
        else:
            print()


if __name__ == "__main__":
    benchmark()
    below_threshold_test()
