"""
Bit Properties Catalog — Block VII: Energy Properties
Treating bits as particles in an energy landscape.
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
# 26. POTENTIAL ENERGY — cost of each bit value
# ============================================================
def potential_energy(clauses, n, var):
    """
    E(var=v) = number of clauses VIOLATED when var=v,
    averaged over all possible states of other variables.

    Approximation: sample random assignments for other vars.
    """
    n_samples = min(500, 2**(n-1))

    energy = {0: 0.0, 1: 0.0}

    for val in [0, 1]:
        total_violated = 0
        for _ in range(n_samples):
            # Random assignment for others
            assignment = [random.randint(0, 1) for _ in range(n)]
            assignment[var] = val
            sat = evaluate(clauses, assignment)
            violated = len(clauses) - sat
            total_violated += violated
        energy[val] = total_violated / n_samples

    return energy[0], energy[1]


# ============================================================
# 27. KINETIC ENERGY — rate of pressure change
# ============================================================
def kinetic_energy(clauses, n, var, n_samples=50):
    """
    Fix random subsets of other variables and measure how much
    pressure on var FLUCTUATES. High fluctuation = high kinetic energy.
    """
    pressures = []

    for _ in range(n_samples):
        # Fix a random subset of other variables
        fixed = {}
        for v in range(n):
            if v != var and random.random() < 0.5:
                fixed[v] = random.randint(0, 1)

        p1, p0 = 0.0, 0.0
        for clause in clauses:
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

        balance = p1 - p0
        pressures.append(balance)

    if len(pressures) < 2:
        return 0.0

    mean = sum(pressures) / len(pressures)
    variance = sum((p - mean)**2 for p in pressures) / len(pressures)
    return math.sqrt(variance)  # "velocity" of pressure changes


# ============================================================
# 28. BINDING ENERGY — cost of "separating" two bits
# ============================================================
def binding_energy(clauses, n, var_i, var_j):
    """
    How much does the system's energy increase if we force
    var_i and var_j to be independent (random relative to each other)
    vs correlated?

    Approximation: compare violations when (i,j) are set together
    optimally vs randomly.
    """
    n_samples = 200

    # Energy when i,j are set to their best joint value
    best_joint_violations = float('inf')
    for vi in [0, 1]:
        for vj in [0, 1]:
            total = 0
            for _ in range(n_samples):
                assignment = [random.randint(0, 1) for _ in range(n)]
                assignment[var_i] = vi
                assignment[var_j] = vj
                sat = evaluate(clauses, assignment)
                total += len(clauses) - sat
            avg = total / n_samples
            if avg < best_joint_violations:
                best_joint_violations = avg

    # Energy when i,j are random
    total_random = 0
    for _ in range(n_samples * 4):
        assignment = [random.randint(0, 1) for _ in range(n)]
        sat = evaluate(clauses, assignment)
        total_random += len(clauses) - sat
    avg_random = total_random / (n_samples * 4)

    return avg_random - best_joint_violations


# ============================================================
# 29. GROUND STATE — bit value at minimum energy
# ============================================================
def ground_state_search(clauses, n):
    """
    Simple gradient descent to find low-energy states.
    Returns the bit values at the best found state.
    """
    # Start from random
    best_assignment = [random.randint(0, 1) for _ in range(n)]
    best_sat = evaluate(clauses, best_assignment)

    for iteration in range(100):
        improved = False
        for var in range(n):
            # Try flipping
            test = list(best_assignment)
            test[var] = 1 - test[var]
            sat = evaluate(clauses, test)
            if sat > best_sat:
                best_assignment = test
                best_sat = sat
                improved = True

        if not improved:
            break

    return best_assignment, best_sat


# ============================================================
# 30. ENERGY BARRIER — cost of transitioning 0→1
# ============================================================
def energy_barrier(clauses, n, var, solutions):
    """
    For each solution: how many clauses break when we flip just this bit?
    This is the "activation energy" for changing this bit.
    """
    if not solutions:
        return 0.0, 0.0

    barriers = []
    for sol in solutions:
        original_sat = evaluate(clauses, sol)
        flipped = list(sol)
        flipped[var] = 1 - flipped[var]
        flipped_sat = evaluate(clauses, flipped)
        barriers.append(original_sat - flipped_sat)

    avg = sum(barriers) / len(barriers)
    max_b = max(barriers)
    return avg, max_b


# ============================================================
# MEASUREMENT
# ============================================================

def measure_energy(clauses, n, solutions):
    random.seed(42)

    print(f"\n--- Energy Properties ---")
    print(f"{'var':>5} | {'E(0)':>6} | {'E(1)':>6} | {'dE':>6} | "
          f"{'kinetic':>7} | {'barrier_avg':>11} | {'barrier_max':>11} | "
          f"{'ground':>6}")
    print("-" * 80)

    # Find ground state
    best_ground, best_sat = None, 0
    for _ in range(10):
        g, s = ground_state_search(clauses, n)
        if s > best_sat:
            best_ground = g
            best_sat = s

    for var in range(n):
        e0, e1 = potential_energy(clauses, n, var)
        ke = kinetic_energy(clauses, n, var)
        b_avg, b_max = energy_barrier(clauses, n, var, solutions)

        print(f"  x{var:>2} | {e0:>6.2f} | {e1:>6.2f} | {e1-e0:>+6.2f} | "
              f"{ke:>7.3f} | {b_avg:>11.2f} | {b_max:>11} | "
              f"{best_ground[var]:>6}")

    # Binding energies for most coupled pairs
    print(f"\n--- Binding Energies (top pairs) ---")
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            # Check if they share clauses
            shared = 0
            for clause in clauses:
                vars_in = [v for v, s in clause]
                if i in vars_in and j in vars_in:
                    shared += 1
            if shared > 0:
                be = binding_energy(clauses, n, i, j)
                pairs.append((i, j, shared, be))

    pairs.sort(key=lambda x: -x[3])
    print(f"{'pair':>8} | {'shared':>6} | {'binding_E':>9}")
    print("-" * 30)
    for i, j, shared, be in pairs[:10]:
        print(f"  x{i}-x{j} | {shared:>6} | {be:>9.3f}")


if __name__ == "__main__":
    print("=" * 80)
    print("BLOCK VII: Energy Properties")
    print("=" * 80)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            random.seed(seed)
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (n=12, ratio={ratio}, {len(solutions)} solutions)")
        measure_energy(clauses, 12, solutions)
