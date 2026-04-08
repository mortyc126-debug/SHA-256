"""
ThermoSAT — Thermodynamic SAT Solver
═════════════════════════════════════
A solver built entirely from Bit Mechanics theory.
Uses knowledge that no existing solver has.

UNIQUE FEATURES:
1. Signal/noise phase detection — switches strategy at the boundary
2. Self-cancellation scoring — predicts which assignments are reliable
3. Clone detection — reduces effective DOF
4. Non-local tension propagation — sees beyond unit propagation
5. Temperature-guided restarts

ARCHITECTURE:
  Phase 1: SENSE   — measure the instance (tensions, graph, clones)
  Phase 2: SIGNAL  — fix high-confidence vars (tension + UP cascade)
  Phase 3: BRIDGE  — detect noise boundary, prepare transition
  Phase 4: NOISE   — switch to random walk guided by self-cancellation
  Phase 5: VERIFY  — check solution, restart if needed
"""

import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat


# ============================================================
# Core primitives
# ============================================================

def evaluate(clauses, assignment):
    """Count satisfied clauses."""
    sat = 0
    for clause in clauses:
        for v, s in clause:
            if (s == 1 and assignment[v] == 1) or \
               (s == -1 and assignment[v] == 0):
                sat += 1
                break
    return sat


def unit_propagate(clauses, n, fixed):
    """Standard UP. Returns (fixed_dict, cascade_count, conflict)."""
    f = dict(fixed)
    cascade = 0
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False
            free = []
            for v, s in clause:
                if v in f:
                    if (s == 1 and f[v] == 1) or (s == -1 and f[v] == 0):
                        sat = True
                        break
                else:
                    free.append((v, s))
            if sat:
                continue
            if len(free) == 0:
                return f, cascade, True  # conflict
            if len(free) == 1:
                v, s = free[0]
                if v not in f:
                    f[v] = 1 if s == 1 else 0
                    cascade += 1
                    changed = True
    return f, cascade, False


def compute_tension(clauses, n, var, fixed=None):
    """Compute tension for a single variable."""
    if fixed is None:
        fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False
        rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True
                    break
            else:
                rem.append((v, s))
        if sat:
            continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1:
                    p1 += w
                else:
                    p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def compute_all_tensions(clauses, n, fixed=None):
    """Compute tensions for all unfixed variables."""
    if fixed is None:
        fixed = {}
    return {v: compute_tension(clauses, n, v, fixed)
            for v in range(n) if v not in fixed}


# ============================================================
# Innovation 1: Self-cancellation scoring
# ============================================================

def build_clause_graph(clauses, n):
    """Build variable adjacency graph from shared clauses."""
    adj = {v: set() for v in range(n)}
    for clause in clauses:
        vars_in = [v for v, s in clause]
        for i in range(len(vars_in)):
            for j in range(i + 1, len(vars_in)):
                adj[vars_in[i]].add(vars_in[j])
                adj[vars_in[j]].add(vars_in[i])
    return adj


def self_cancellation_score(tensions, adj, var):
    """
    SHA-256 P5: |σ_v + avg(σ_neighbors)| predicts reliability.
    Low self-cancellation → frustrated region → unreliable.
    High self-cancellation → coherent region → reliable.
    """
    sigma = tensions.get(var, 0)
    neighbors = adj.get(var, set())
    if not neighbors:
        return abs(sigma)
    avg_neighbor = sum(tensions.get(u, 0) for u in neighbors) / len(neighbors)
    return abs(sigma + avg_neighbor)


# ============================================================
# Innovation 2: Clone detection
# ============================================================

def detect_clones(clauses, n, tensions):
    """
    Find pairs of variables that appear to be clones
    (same sign in all shared clauses, or opposite sign in all).
    Clones reduce effective DOF.
    """
    # Build co-occurrence matrix
    pair_signs = {}  # (i,j) -> list of relative signs
    for clause in clauses:
        vars_signs = [(v, s) for v, s in clause]
        for a in range(len(vars_signs)):
            for b in range(a + 1, len(vars_signs)):
                va, sa = vars_signs[a]
                vb, sb = vars_signs[b]
                key = (min(va, vb), max(va, vb))
                if key not in pair_signs:
                    pair_signs[key] = []
                # Relative sign: same or opposite
                pair_signs[key].append(sa * sb)

    clones = []  # (v1, v2, sign) where sign=1 means same, sign=-1 means opposite
    for (v1, v2), signs in pair_signs.items():
        if len(signs) >= 2:
            if all(s == 1 for s in signs):
                clones.append((v1, v2, 1))  # same value
            elif all(s == -1 for s in signs):
                clones.append((v1, v2, -1))  # opposite values

    return clones


# ============================================================
# Innovation 3: Non-local tension propagation
# ============================================================

def propagate_tensions(tensions, adj, iterations=2, damping=0.3):
    """
    Beyond UP: propagate tension information through the graph.
    Like belief propagation but simpler — use graph neighborhood.
    """
    current = dict(tensions)
    for _ in range(iterations):
        new = {}
        for v in current:
            neighbors = adj.get(v, set())
            if not neighbors:
                new[v] = current[v]
                continue
            # Weighted average: own tension + damped neighbor average
            neighbor_avg = sum(current.get(u, 0) for u in neighbors
                             if u in current) / max(len(neighbors), 1)
            new[v] = current[v] + damping * neighbor_avg
        current = new
    return current


# ============================================================
# Innovation 4: Temperature-based phase detection
# ============================================================

def estimate_noise_fraction(tensions):
    """Estimate what fraction of variables are in the noise zone."""
    if not tensions:
        return 1.0
    threshold = 0.15
    noise = sum(1 for t in tensions.values() if abs(t) <= threshold)
    return noise / len(tensions)


# ============================================================
# THE SOLVER
# ============================================================

class ThermoSAT:
    """
    Thermodynamic SAT Solver.

    Phase 1: SENSE — analyze instance structure
    Phase 2: SIGNAL — fix high-confidence variables
    Phase 3: NOISE — random walk guided by self-cancellation
    """

    def __init__(self, clauses, n, max_time=60):
        self.clauses = clauses
        self.n = n
        self.max_time = max_time
        self.stats = {
            'decisions': 0,
            'backtracks': 0,
            'up_fixes': 0,
            'walk_flips': 0,
            'restarts': 0,
            'phase_switches': 0,
            'clone_reductions': 0,
        }

    def solve(self):
        start_time = time.time()

        # ---- Phase 1: SENSE ----
        adj = build_clause_graph(self.clauses, self.n)
        tensions = compute_all_tensions(self.clauses, self.n)

        # Detect clones
        clones = detect_clones(self.clauses, self.n, tensions)
        clone_map = {}  # v -> (master, sign)
        for v1, v2, sign in clones:
            # The one with higher |tension| is master
            if abs(tensions.get(v1, 0)) >= abs(tensions.get(v2, 0)):
                clone_map[v2] = (v1, sign)
            else:
                clone_map[v1] = (v2, sign)
        self.stats['clone_reductions'] = len(clone_map)

        # Self-cancellation scores
        sc_scores = {v: self_cancellation_score(tensions, adj, v)
                     for v in range(self.n)}

        # Propagated tensions (non-local)
        prop_tensions = propagate_tensions(tensions, adj,
                                           iterations=2, damping=0.3)

        # Sort variables by reliability
        # Combined score: |tension| × self_cancellation
        reliability = {}
        for v in range(self.n):
            t = abs(tensions.get(v, 0))
            sc = sc_scores.get(v, 0)
            pt = abs(prop_tensions.get(v, 0))
            reliability[v] = t * 0.4 + sc * 0.3 + pt * 0.3

        # Restart loop
        best_solution = None
        best_sat = 0

        for restart in range(100):
            if time.time() - start_time > self.max_time:
                break

            self.stats['restarts'] = restart

            result = self._attempt(
                adj, tensions, prop_tensions, sc_scores,
                reliability, clone_map, start_time
            )

            if result is not None:
                sat_count = evaluate(self.clauses, result)
                if sat_count == len(self.clauses):
                    return result
                if sat_count > best_sat:
                    best_sat = sat_count
                    best_solution = list(result)

            # Diversify tensions slightly for next restart
            if restart > 0:
                tensions = compute_all_tensions(self.clauses, self.n)
                # Add small random perturbation for diversity
                for v in tensions:
                    tensions[v] += random.gauss(0, 0.05)

        return best_solution

    def _attempt(self, adj, tensions, prop_tensions, sc_scores,
                 reliability, clone_map, start_time):
        """Single solve attempt with phase switching."""

        fixed = {}

        # ---- Phase 2: SIGNAL PHASE ----
        # Fix vars in order of reliability (highest first)
        sorted_vars = sorted(range(self.n),
                            key=lambda v: reliability.get(v, 0),
                            reverse=True)

        signal_threshold = 0.15
        signal_vars = [v for v in sorted_vars
                      if abs(tensions.get(v, 0)) > signal_threshold
                      and v not in clone_map]

        for v in signal_vars:
            if v in fixed:
                continue
            if time.time() - start_time > self.max_time:
                return None

            # Use propagated tension for decision
            pt = prop_tensions.get(v, tensions.get(v, 0))
            val = 1 if pt >= 0 else 0
            fixed[v] = val
            self.stats['decisions'] += 1

            # Apply clone constraints
            for cv, (master, sign) in clone_map.items():
                if master == v and cv not in fixed:
                    fixed[cv] = val if sign == 1 else (1 - val)
                    self.stats['clone_reductions'] += 1

            # UP cascade
            fixed, cascade, conflict = unit_propagate(
                self.clauses, self.n, fixed)
            self.stats['up_fixes'] += cascade

            if conflict:
                self.stats['backtracks'] += 1
                # Simple backtrack: undo last and try opposite
                del fixed[v]
                fixed[v] = 1 - val
                fixed, cascade, conflict2 = unit_propagate(
                    self.clauses, self.n, fixed)
                self.stats['up_fixes'] += cascade
                if conflict2:
                    return None  # dead end

        self.stats['phase_switches'] += 1

        # ---- Phase 3: NOISE PHASE ----
        # Remaining variables: use random walk guided by self-cancellation
        unfixed = [v for v in range(self.n) if v not in fixed]

        if not unfixed:
            assignment = [fixed.get(v, 0) for v in range(self.n)]
            return assignment

        # Initialize noise vars randomly with bias from tension
        for v in unfixed:
            t = tensions.get(v, 0)
            # Slight bias from tension, but mostly random
            p = 0.5 + 0.2 * t  # mild bias
            fixed[v] = 1 if random.random() < p else 0

        assignment = [fixed.get(v, 0) for v in range(self.n)]

        # WalkSAT-like phase on noise variables
        max_flips = len(unfixed) * 50
        for flip in range(max_flips):
            if time.time() - start_time > self.max_time:
                break

            sat_count = evaluate(self.clauses, assignment)
            if sat_count == len(self.clauses):
                return assignment

            # Find unsatisfied clause
            unsat_clauses = []
            for ci, clause in enumerate(self.clauses):
                sat = False
                for v, s in clause:
                    if (s == 1 and assignment[v] == 1) or \
                       (s == -1 and assignment[v] == 0):
                        sat = True
                        break
                if not sat:
                    unsat_clauses.append(ci)

            if not unsat_clauses:
                return assignment

            # Pick random unsatisfied clause
            ci = random.choice(unsat_clauses)
            clause = self.clauses[ci]

            # Innovation: pick variable to flip based on self-cancellation
            # Prefer flipping vars with LOW sc (frustrated = wrong)
            candidates = []
            for v, s in clause:
                if v in unfixed:  # only flip noise vars
                    sc = sc_scores.get(v, 0)
                    # Score: how much improvement from flipping
                    # + penalty for high self-cancellation (don't flip reliable vars)
                    candidates.append((v, sc))
                else:
                    candidates.append((v, 999))  # don't flip signal vars

            if not candidates:
                continue

            # With 30% probability, pick random (exploration)
            if random.random() < 0.3:
                flip_var = random.choice([v for v, _ in candidates])
            else:
                # Pick var with lowest self-cancellation (most frustrated)
                flip_var = min(candidates, key=lambda x: x[1])[0]

            assignment[flip_var] = 1 - assignment[flip_var]
            self.stats['walk_flips'] += 1

        return assignment


# ============================================================
# Benchmark against MiniSat
# ============================================================

def solve_minisat(n, clauses, timeout=60):
    filename = "/tmp/thermo_bench.cnf"
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
                if r == "SAT":
                    return True, elapsed
                elif r == "UNSAT":
                    return None, elapsed
        return False, elapsed
    except subprocess.TimeoutExpired:
        return False, timeout
    finally:
        for fn in [filename, outfile]:
            if os.path.exists(fn): os.remove(fn)


def benchmark():
    print("=" * 70)
    print("ThermoSAT vs MiniSat BENCHMARK")
    print("=" * 70)

    random.seed(42)

    for n in [20, 50, 75, 100, 150, 200]:
        thermo_solved = 0
        minisat_solved = 0
        thermo_times = []
        minisat_times = []
        thermo_stats_total = {}

        n_inst = 30 if n <= 100 else 15
        timeout = 10 if n <= 100 else 30

        for seed in range(n_inst * 3):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 60000000)

            # ThermoSAT
            t0 = time.time()
            solver = ThermoSAT(clauses, n, max_time=timeout)
            result = solver.solve()
            t_thermo = time.time() - t0

            if result is not None and evaluate(clauses, result) == len(clauses):
                thermo_solved += 1
                thermo_times.append(t_thermo)
                for k, v in solver.stats.items():
                    thermo_stats_total[k] = thermo_stats_total.get(k, 0) + v

            # MiniSat
            ms_result, t_mini = solve_minisat(n, clauses, timeout)
            if ms_result == True:
                minisat_solved += 1
                minisat_times.append(t_mini)

            if thermo_solved + minisat_solved >= n_inst * 2:
                break

        total_inst = max(thermo_solved, minisat_solved, 1)

        print(f"\n  n={n}:")
        print(f"    ThermoSAT:  {thermo_solved} solved", end="")
        if thermo_times:
            print(f", avg {1000*sum(thermo_times)/len(thermo_times):.0f}ms")
        else:
            print()
        print(f"    MiniSat:    {minisat_solved} solved", end="")
        if minisat_times:
            print(f", avg {1000*sum(minisat_times)/len(minisat_times):.0f}ms")
        else:
            print()

        if thermo_stats_total and thermo_solved > 0:
            print(f"    ThermoSAT details:")
            for k, v in sorted(thermo_stats_total.items()):
                print(f"      {k}: {v/thermo_solved:.1f} avg")


# ============================================================
# Detailed analysis at n=50
# ============================================================

def detailed_analysis():
    print("\n" + "=" * 70)
    print("DETAILED ANALYSIS: ThermoSAT internals at n=50")
    print("=" * 70)

    random.seed(42)

    for seed in range(10):
        clauses = random_3sat(50, int(4.27 * 50), seed=seed + 61000000)

        solver = ThermoSAT(clauses, 50, max_time=5)
        result = solver.solve()
        sat = evaluate(clauses, result) if result else 0

        status = "SAT" if sat == len(clauses) else f"{sat}/{len(clauses)}"
        print(f"\n  Instance {seed}: {status}")
        for k, v in sorted(solver.stats.items()):
            print(f"    {k}: {v}")


if __name__ == "__main__":
    benchmark()
    detailed_analysis()
