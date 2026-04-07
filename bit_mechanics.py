"""
BIT MECHANICS — A new mathematical framework built from experimental observations.

Core idea: bits are not passive 0/1 values. They are objects in a FIELD
with internal tension, conductivity between them, and phase transitions.

This file defines the formal objects and tests the LAWS we derived from experiments.
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            val = assignment[var]
            if (sign == 1 and val == 1) or (sign == -1 and val == 0):
                sat += 1
                break
    return sat


# ============================================================
# CORE OBJECT: BitField
# ============================================================

class BitField:
    """
    A bit field: n bits with constraints and measurable properties.

    This is the fundamental object of Bit Mechanics.
    """

    def __init__(self, n, clauses):
        self.n = n
        self.clauses = clauses
        self._transmission = None
        self._tension = None

    # --- TENSION (internal state of each bit) ---

    def tension(self, var, fixed=None):
        """
        σ(var) ∈ [-1, +1]: internal tension of bit var.
        Positive = pulled toward 1, negative = pulled toward 0.
        Magnitude = strength of pull.

        With fixed={var: val, ...}, tension is conditional.
        """
        if fixed is None:
            fixed = {}

        p1, p0 = 0.0, 0.0
        for clause in self.clauses:
            already_sat = False
            remaining = []
            for v, s in clause:
                if v in fixed:
                    if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                        already_sat = True
                        break
                else:
                    remaining.append((v, s))
            if already_sat:
                continue
            for v, s in remaining:
                if v == var:
                    w = 1.0 / max(1, len(remaining))
                    if s == 1:
                        p1 += w
                    else:
                        p0 += w

        total = p1 + p0
        if total == 0:
            return 0.0
        return (p1 - p0) / total

    def tension_vector(self, fixed=None):
        """Tension of all bits as a vector."""
        return [self.tension(v, fixed) for v in range(self.n)]

    # --- TRANSMISSION (conductivity between bits) ---

    def transmission(self, var_i, var_j):
        """
        T(i, j) ∈ [0, 1]: how much fixing bit i DETERMINES bit j.

        T = |σ(j | i=1) - σ(j | i=0)| / 2

        T=0: fixing i tells nothing about j
        T=1: fixing i completely determines j
        """
        sigma_j_if_0 = self.tension(var_j, {var_i: 0})
        sigma_j_if_1 = self.tension(var_j, {var_i: 1})
        return abs(sigma_j_if_1 - sigma_j_if_0) / 2.0

    def transmission_matrix(self):
        """Full transmission matrix T[i][j]."""
        if self._transmission is None:
            T = [[0.0] * self.n for _ in range(self.n)]
            for i in range(self.n):
                for j in range(self.n):
                    if i != j:
                        T[i][j] = self.transmission(i, j)
            self._transmission = T
        return self._transmission

    # --- CONDUCTIVITY (global property) ---

    def conductivity(self):
        """
        Global conductivity: average transmission across all pairs.
        Measures how well information flows through the bit field.
        """
        T = self.transmission_matrix()
        total = sum(T[i][j] for i in range(self.n)
                    for j in range(self.n) if i != j)
        pairs = self.n * (self.n - 1)
        return total / pairs if pairs > 0 else 0.0

    def max_transmission_path(self, start, end):
        """
        Find the path from start to end that maximizes
        minimum transmission along the path (bottleneck path).

        Like: what's the best "wire" connecting two bits?
        """
        T = self.transmission_matrix()

        # Dijkstra-like for max-min path
        best = [-1.0] * self.n
        best[start] = 1.0  # transmission to self is perfect
        visited = [False] * self.n
        parent = [-1] * self.n

        for _ in range(self.n):
            # Find unvisited with best transmission
            u = -1
            for v in range(self.n):
                if not visited[v] and (u == -1 or best[v] > best[u]):
                    u = v
            if u == -1 or best[u] <= 0:
                break
            visited[u] = True

            for v in range(self.n):
                if not visited[v] and T[u][v] > 0:
                    new_trans = min(best[u], T[u][v])
                    if new_trans > best[v]:
                        best[v] = new_trans
                        parent[v] = u

        # Reconstruct path
        path = []
        v = end
        while v != -1:
            path.append(v)
            v = parent[v]
        path.reverse()

        return best[end], path

    # --- CRYSTALLIZATION (solving by sequential fixation) ---

    def crystallize(self, strategy="max_tension"):
        """
        Solve by crystallizing bits one at a time.

        Returns: (assignment, success, trace)
        """
        fixed = {}
        trace = []

        for step in range(self.n):
            candidates = []
            for var in range(self.n):
                if var in fixed:
                    continue
                sigma = self.tension(var, fixed)
                candidates.append((var, sigma))

            if not candidates:
                break

            if strategy == "max_tension":
                # Fix the most "certain" bit first
                candidates.sort(key=lambda c: -abs(c[1]))
            elif strategy == "max_transmission":
                # Fix the bit that will most influence remaining bits
                T = self.transmission_matrix()
                unfixed = [v for v in range(self.n) if v not in fixed]

                def influence(var):
                    return sum(T[var][j] for j in unfixed if j != var)

                candidates.sort(key=lambda c: -influence(c[0]))

            best_var, best_sigma = candidates[0]
            best_val = 1 if best_sigma >= 0 else 0

            fixed[best_var] = best_val
            trace.append({
                'var': best_var,
                'tension': best_sigma,
                'val': best_val,
                'step': step,
            })

        assignment = [fixed.get(i, 0) for i in range(self.n)]
        sat = evaluate(self.clauses, assignment)
        success = sat == len(self.clauses)

        return assignment, success, trace

    # --- PHASE ANALYSIS ---

    def phase(self):
        """
        Determine the "phase" of the bit field:
        - CRYSTAL: high conductivity, bits determine each other
        - GLASS: low conductivity, bits are locally constrained but globally frustrated
        - GAS: very low conductivity, bits are nearly independent

        Returns phase name and metrics.
        """
        cond = self.conductivity()
        T = self.transmission_matrix()

        # Distribution of transmissions
        all_t = [T[i][j] for i in range(self.n)
                 for j in range(self.n) if i != j and T[i][j] > 0]

        if not all_t:
            return "GAS", {'conductivity': 0, 'max_t': 0, 'connected': 0}

        max_t = max(all_t)
        avg_t = sum(all_t) / len(all_t)

        # How many pairs have significant transmission?
        significant = sum(1 for t in all_t if t > 0.1)
        total_pairs = self.n * (self.n - 1)
        connectivity = significant / total_pairs if total_pairs > 0 else 0

        # Tension alignment: do neighboring bits agree on direction?
        tensions = self.tension_vector()
        alignment = 0
        count = 0
        for i in range(self.n):
            for j in range(i+1, self.n):
                if T[i][j] > 0.05:
                    # Check if tensions are "compatible"
                    if tensions[i] * tensions[j] > 0:  # same direction
                        alignment += 1
                    count += 1
        alignment_ratio = alignment / count if count > 0 else 0.5

        if cond > 0.15 and connectivity > 0.3:
            phase = "CRYSTAL"
        elif cond > 0.05 and alignment_ratio < 0.6:
            phase = "GLASS"
        else:
            phase = "GAS"

        return phase, {
            'conductivity': cond,
            'max_transmission': max_t,
            'connectivity': connectivity,
            'alignment': alignment_ratio,
        }


# ============================================================
# LAWS OF BIT MECHANICS
# ============================================================

def test_law_1(n=12, n_trials=200):
    """
    LAW 1 (Conservation of Tension):
    The total absolute tension of a bit field is approximately conserved
    during crystallization. Fixing one bit redistributes tension but
    doesn't create or destroy it.
    """
    print("=" * 70)
    print("LAW 1: Conservation of Tension")
    print("Total |σ| before and after fixing bits")
    print("=" * 70)

    for ratio in [2.0, 4.27]:
        deltas = []
        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            bf = BitField(n, clauses)

            # Total tension before
            initial = sum(abs(bf.tension(v)) for v in range(n))

            # Fix the most confident bit
            tensions = [(v, bf.tension(v)) for v in range(n)]
            tensions.sort(key=lambda x: -abs(x[1]))
            fix_var, fix_sigma = tensions[0]
            fix_val = 1 if fix_sigma > 0 else 0

            # Total tension after
            fixed = {fix_var: fix_val}
            after = sum(abs(bf.tension(v, fixed)) for v in range(n) if v != fix_var)

            deltas.append(after - initial)

        avg_delta = sum(deltas) / len(deltas)
        std_delta = math.sqrt(sum((d - avg_delta)**2 for d in deltas) / len(deltas))
        print(f"  ratio={ratio}: avg ΔΣ|σ| = {avg_delta:+.3f} ± {std_delta:.3f}")


def test_law_2(n=12, n_trials=200):
    """
    LAW 2 (Phase Transition):
    There exists a critical conductivity threshold.
    Above it: crystallization succeeds (CRYSTAL phase).
    Below it: crystallization fails (GLASS phase).
    """
    print("\n" + "=" * 70)
    print("LAW 2: Phase Transition")
    print("Conductivity vs solvability")
    print("=" * 70)

    for ratio in [2.0, 3.0, 3.5, 4.0, 4.27]:
        crystal = 0
        glass = 0
        gas = 0
        solved_crystal = 0
        solved_glass = 0
        solved_gas = 0

        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            bf = BitField(n, clauses)
            phase, metrics = bf.phase()
            _, success, _ = bf.crystallize()

            if phase == "CRYSTAL":
                crystal += 1
                if success:
                    solved_crystal += 1
            elif phase == "GLASS":
                glass += 1
                if success:
                    solved_glass += 1
            else:
                gas += 1
                if success:
                    solved_gas += 1

        print(f"\n  ratio={ratio:.2f}:")
        if crystal > 0:
            print(f"    CRYSTAL: {solved_crystal}/{crystal} solved "
                  f"({solved_crystal/crystal*100:.0f}%)")
        if glass > 0:
            print(f"    GLASS:   {solved_glass}/{glass} solved "
                  f"({solved_glass/glass*100:.0f}%)")
        if gas > 0:
            print(f"    GAS:     {solved_gas}/{gas} solved "
                  f"({solved_gas/gas*100:.0f}%)")


def test_law_3(n=12, n_trials=100):
    """
    LAW 3 (Transmission Determines Solvability):
    If max-min transmission path between any two bits > threshold,
    then crystallization succeeds.
    """
    print("\n" + "=" * 70)
    print("LAW 3: Transmission Path ↔ Solvability")
    print("=" * 70)

    for ratio in [2.0, 4.27]:
        solved_paths = []
        failed_paths = []

        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            bf = BitField(n, clauses)
            _, success, _ = bf.crystallize()

            # Average max-min path between all pairs
            paths = []
            for i in range(min(n, 6)):
                for j in range(i+1, min(n, 6)):
                    t, _ = bf.max_transmission_path(i, j)
                    if t > 0:
                        paths.append(t)

            avg_path = sum(paths) / len(paths) if paths else 0

            if success:
                solved_paths.append(avg_path)
            else:
                failed_paths.append(avg_path)

        if solved_paths:
            avg_s = sum(solved_paths) / len(solved_paths)
            print(f"  ratio={ratio}: solved avg path = {avg_s:.4f} "
                  f"(n={len(solved_paths)})")
        if failed_paths:
            avg_f = sum(failed_paths) / len(failed_paths)
            print(f"  ratio={ratio}: failed avg path = {avg_f:.4f} "
                  f"(n={len(failed_paths)})")


def test_strategies(n=12, n_trials=200):
    """
    Compare crystallization strategies:
    1. max_tension: fix most confident bit first
    2. max_transmission: fix most influential bit first
    """
    print("\n" + "=" * 70)
    print("STRATEGY COMPARISON")
    print("=" * 70)

    for ratio in [2.0, 3.0, 4.0, 4.27]:
        results = {'max_tension': 0, 'max_transmission': 0}
        total = 0

        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue
            total += 1

            bf = BitField(n, clauses)
            for strategy in results:
                _, success, _ = bf.crystallize(strategy=strategy)
                if success:
                    results[strategy] += 1

        print(f"  ratio={ratio:.2f} ({total} instances):")
        for strategy, count in results.items():
            print(f"    {strategy:>20}: {count}/{total} "
                  f"({count/total*100:.1f}%)")


if __name__ == "__main__":
    random.seed(42)

    test_law_1()
    test_law_2()
    test_law_3()
    test_strategies()
