"""
Rebuilding bit mathematics from scratch.

For a SAT instance, we study each bit (variable) as a rich object
with internal structure: pressure, frustration, influence, coupling.

We ask: can these "bit properties" guide us to a solution
without exponential search?
"""

import random
from itertools import product


def random_3sat(n_vars, n_clauses, seed=None):
    if seed is not None:
        random.seed(seed)
    clauses = []
    for _ in range(n_clauses):
        vs = random.sample(range(n_vars), 3)
        signs = [random.choice([1, -1]) for _ in range(3)]
        clauses.append(list(zip(vs, signs)))
    return clauses


def evaluate(clauses, assignment):
    """Return (satisfied, total) clause counts."""
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            val = assignment[var]
            if (sign == 1 and val == 1) or (sign == -1 and val == 0):
                sat += 1
                break
    return sat, len(clauses)


def find_solutions(clauses, n):
    """Brute force all solutions (small n only)."""
    solutions = []
    for i in range(2**n):
        assignment = [(i >> j) & 1 for j in range(n)]
        s, t = evaluate(clauses, assignment)
        if s == t:
            solutions.append(assignment)
    return solutions


# ============================================================
# BIT PROPERTIES - the "internal structure" of each bit
# ============================================================

def bit_pressure(clauses, n, var_index):
    """
    How much does this bit "want" to be 1 vs 0?

    For each clause containing this variable:
    - If variable appears positive (sign=+1), clause "wants" bit=1
    - If variable appears negative (sign=-1), clause "wants" bit=0

    But weighted by how "desperate" the clause is:
    a clause with fewer other options puts more pressure.

    Returns: float in [-1, 1]. Positive = wants 1, negative = wants 0.
    """
    pressure_toward_1 = 0.0
    pressure_toward_0 = 0.0

    for clause in clauses:
        for var, sign in clause:
            if var == var_index:
                # Weight: 1/k where k = number of literals in clause
                # (all our clauses have 3 literals, but this generalizes)
                weight = 1.0 / len(clause)
                if sign == 1:
                    pressure_toward_1 += weight
                else:
                    pressure_toward_0 += weight

    total = pressure_toward_1 + pressure_toward_0
    if total == 0:
        return 0.0
    return (pressure_toward_1 - pressure_toward_0) / total


def bit_frustration(clauses, n, var_index):
    """
    How conflicted is this bit?

    Frustration = how much the pressures from different clauses DISAGREE.
    High frustration = some clauses want 1, others want 0.
    Low frustration = all clauses agree.

    Returns: float in [0, 1]. 0 = no conflict, 1 = maximum conflict.
    """
    votes = []  # +1 for "wants 1", -1 for "wants 0"

    for clause in clauses:
        for var, sign in clause:
            if var == var_index:
                votes.append(sign)

    if len(votes) == 0:
        return 0.0

    # Frustration = 1 - |mean vote|
    # If all votes agree: mean = ±1, frustration = 0
    # If votes split evenly: mean = 0, frustration = 1
    mean_vote = sum(votes) / len(votes)
    return 1.0 - abs(mean_vote)


def bit_influence(clauses, n, var_index):
    """
    How much does flipping this bit affect other bits' pressure?

    Influence = number of other variables that share a clause with this one.
    (Higher influence = this bit's value constrains more other bits)
    """
    neighbors = set()
    for clause in clauses:
        vars_in_clause = [v for v, s in clause]
        if var_index in vars_in_clause:
            for v in vars_in_clause:
                if v != var_index:
                    neighbors.add(v)
    return len(neighbors) / (n - 1) if n > 1 else 0.0


def bit_criticality(clauses, n, var_index):
    """
    How often is this bit the ONLY way to satisfy a clause?

    For each clause containing this variable:
    count how many other literals could satisfy it.
    If this bit is the only option -> high criticality.

    Returns: average "exclusivity" across clauses containing this var.
    """
    exclusivities = []

    for clause in clauses:
        vars_in_clause = [v for v, s in clause]
        if var_index in vars_in_clause:
            # This is a structural property - how many literals in the clause
            # In 3-SAT it's always 3, but criticality is about:
            # if I DON'T set this variable to satisfy this clause,
            # how many other options remain?
            other_count = len(clause) - 1  # other literals that could help
            exclusivities.append(1.0 / (1 + other_count))

    if not exclusivities:
        return 0.0
    return sum(exclusivities) / len(exclusivities)


def conditional_pressure(clauses, n, var_index, fixed_vars):
    """
    Pressure on var_index GIVEN that some variables are already fixed.

    fixed_vars: dict {var_index: value}

    This is the KEY function - it computes how fixing other bits
    changes the pressure on this bit.
    """
    pressure_1 = 0.0
    pressure_0 = 0.0

    for clause in clauses:
        # Check if clause is already satisfied by fixed variables
        already_satisfied = False
        remaining_literals = []

        for var, sign in clause:
            if var in fixed_vars:
                val = fixed_vars[var]
                if (sign == 1 and val == 1) or (sign == -1 and val == 0):
                    already_satisfied = True
                    break
            else:
                remaining_literals.append((var, sign))

        if already_satisfied:
            continue  # This clause is fine, no pressure

        # Clause not yet satisfied. Check if our variable is in remaining literals
        for var, sign in remaining_literals:
            if var == var_index:
                # Pressure is higher when fewer remaining literals
                weight = 1.0 / max(1, len(remaining_literals))
                if sign == 1:
                    pressure_1 += weight
                else:
                    pressure_0 += weight

    if pressure_1 + pressure_0 == 0:
        return 0.0, 0.0  # No pressure either way

    return pressure_1, pressure_0


# ============================================================
# THE ALGORITHM: Sequential Bit Crystallization
# ============================================================

def crystallize(clauses, n, verbose=True):
    """
    Solve SAT by "crystallizing" one bit at a time.

    Strategy:
    1. Compute properties of all unfixed bits
    2. Pick the bit with lowest frustration (most "sure" of itself)
    3. Set it according to its conditional pressure
    4. Repeat

    This is the "password timing attack" idea:
    solve each position using the SIGNAL from the problem structure.
    """
    fixed = {}
    order = []

    if verbose:
        print(f"\n{'Step':>4} | {'Var':>3} | {'Set to':>6} | {'P(1)':>6} | {'P(0)':>6} | "
              f"{'Frust':>6} | {'Reason':>20} | {'Clauses OK':>10}")
        print("-" * 85)

    for step in range(n):
        # Compute conditional pressure and frustration for each unfixed bit
        candidates = []

        for var in range(n):
            if var in fixed:
                continue

            p1, p0 = conditional_pressure(clauses, n, var, fixed)

            # Frustration given current state
            total = p1 + p0
            if total == 0:
                frust = 0.0
                direction = random.choice([0, 1])
                confidence = 0.0
            else:
                frust = 1.0 - abs(p1 - p0) / total
                direction = 1 if p1 >= p0 else 0
                confidence = abs(p1 - p0) / total

            candidates.append({
                'var': var,
                'p1': p1,
                'p0': p0,
                'frustration': frust,
                'confidence': confidence,
                'direction': direction,
            })

        if not candidates:
            break

        # Strategy: pick the MOST CONFIDENT bit (lowest frustration)
        candidates.sort(key=lambda c: (-c['confidence'], c['frustration']))
        best = candidates[0]

        # Fix this bit
        fixed[best['var']] = best['direction']
        order.append(best['var'])

        # Check current state
        partial_assignment = [fixed.get(i, 0) for i in range(n)]
        sat, total = evaluate(clauses, partial_assignment)

        if verbose:
            reason = f"conf={best['confidence']:.3f}"
            print(f"{step+1:>4} | x{best['var']:>2} | {best['direction']:>6} | "
                  f"{best['p1']:>6.2f} | {best['p0']:>6.2f} | "
                  f"{best['frustration']:>6.3f} | {reason:>20} | "
                  f"{sat}/{total}")

    # Final check
    assignment = [fixed.get(i, 0) for i in range(n)]
    sat, total = evaluate(clauses, assignment)

    return assignment, sat == total


def experiment_crystallization():
    """Test the crystallization algorithm on various SAT instances."""

    print("=" * 85)
    print("BIT CRYSTALLIZATION ALGORITHM")
    print("Solving SAT by 'listening to each bit's signal'")
    print("=" * 85)

    # Test 1: Easy instance (low clause ratio)
    print("\n## TEST 1: Easy 3-SAT (n=10, ratio=2.0)")
    n = 10
    clauses = random_3sat(n, int(2.0 * n), seed=42)
    solutions = find_solutions(clauses, n)
    print(f"   {len(solutions)} solutions exist out of {2**n}")
    assignment, success = crystallize(clauses, n)
    print(f"   Result: {'SUCCESS' if success else 'FAILED'}")

    # Test 2: Hard instance (threshold ratio)
    print("\n## TEST 2: Hard 3-SAT (n=10, ratio=4.27)")
    clauses = random_3sat(n, int(4.27 * n), seed=100)
    solutions = find_solutions(clauses, n)
    print(f"   {len(solutions)} solutions exist out of {2**n}")
    if solutions:
        assignment, success = crystallize(clauses, n)
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        if not success and solutions:
            print(f"   (A solution exists: {solutions[0]})")
    else:
        print("   (No solutions exist — skipping)")

    # Test 3: Statistical test - how often does crystallization work?
    print("\n" + "=" * 85)
    print("STATISTICAL TEST: Success rate of crystallization")
    print("=" * 85)

    for ratio in [2.0, 3.0, 3.5, 4.0, 4.27]:
        successes = 0
        total_satisfiable = 0
        total_tested = 200

        for seed in range(total_tested):
            clauses = random_3sat(n, int(ratio * n), seed=seed + 1000)
            solutions = find_solutions(clauses, n)

            if not solutions:
                continue

            total_satisfiable += 1
            _, success = crystallize(clauses, n, verbose=False)
            if success:
                successes += 1

        if total_satisfiable > 0:
            rate = successes / total_satisfiable * 100
            print(f"  ratio={ratio:.2f}: {successes}/{total_satisfiable} "
                  f"satisfiable instances solved ({rate:.1f}%)")

    # Test 4: Compare with ENHANCED crystallization (with backtracking)
    print("\n" + "=" * 85)
    print("ENHANCED: Crystallization with 1-step lookahead")
    print("=" * 85)

    for ratio in [2.0, 3.0, 3.5, 4.0, 4.27]:
        successes = 0
        total_satisfiable = 0

        for seed in range(200):
            clauses = random_3sat(n, int(ratio * n), seed=seed + 1000)
            solutions = find_solutions(clauses, n)

            if not solutions:
                continue

            total_satisfiable += 1
            _, success = crystallize_with_lookahead(clauses, n)
            if success:
                successes += 1

        if total_satisfiable > 0:
            rate = successes / total_satisfiable * 100
            print(f"  ratio={ratio:.2f}: {successes}/{total_satisfiable} "
                  f"satisfiable instances solved ({rate:.1f}%)")


def crystallize_with_lookahead(clauses, n):
    """
    Enhanced crystallization: before fixing a bit, simulate BOTH choices
    and pick the one that leaves the remaining bits least frustrated.
    """
    fixed = {}

    for step in range(n):
        best_var = None
        best_val = None
        best_score = -1

        for var in range(n):
            if var in fixed:
                continue

            for val in [0, 1]:
                # Simulate fixing var=val
                test_fixed = dict(fixed)
                test_fixed[var] = val

                # Check: does this cause any clause to become unsatisfiable?
                dead_clause = False
                total_remaining_pressure = 0

                for clause in clauses:
                    satisfied = False
                    remaining = 0

                    for v, s in clause:
                        if v in test_fixed:
                            if (s == 1 and test_fixed[v] == 1) or \
                               (s == -1 and test_fixed[v] == 0):
                                satisfied = True
                                break
                        else:
                            remaining += 1

                    if not satisfied and remaining == 0:
                        dead_clause = True
                        break

                    if not satisfied:
                        total_remaining_pressure += 1.0 / remaining

                if dead_clause:
                    continue

                # Score: lower remaining pressure = better
                # (means remaining bits have more freedom)
                score = -total_remaining_pressure

                if best_var is None or score > best_score:
                    best_var = var
                    best_val = val
                    best_score = score

        if best_var is None:
            break

        fixed[best_var] = best_val

    assignment = [fixed.get(i, 0) for i in range(n)]
    sat, total = evaluate(clauses, assignment)
    return assignment, sat == total


# ============================================================
# DEEPER: Bit interaction map
# ============================================================

def bit_interaction_matrix(clauses, n):
    """
    For each pair of bits (i, j), compute how strongly they interact.

    Interaction = how much fixing bit i changes the pressure on bit j.
    This is the "derivative" of bit j's state with respect to bit i.
    """
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        # Pressure on all other bits when i is unfixed
        base_pressures = {}
        for j in range(n):
            if j == i:
                continue
            p1, p0 = conditional_pressure(clauses, n, j, {})
            base_pressures[j] = (p1, p0)

        # Pressure on all other bits when i = 1
        for j in range(n):
            if j == i:
                continue
            p1_given_1, p0_given_1 = conditional_pressure(clauses, n, j, {i: 1})
            p1_given_0, p0_given_0 = conditional_pressure(clauses, n, j, {i: 0})

            # Interaction = how much i's value changes j's pressure balance
            base_p1, base_p0 = base_pressures[j]
            base_balance = base_p1 - base_p0
            balance_if_1 = p1_given_1 - p0_given_1
            balance_if_0 = p1_given_0 - p0_given_0

            interaction = abs(balance_if_1 - balance_if_0)
            matrix[i][j] = interaction

    return matrix


def show_bit_xray(clauses, n, solutions=None):
    """Show the complete 'X-ray' of all bits."""
    print(f"\n{'Var':>5} | {'Press':>6} | {'Frust':>6} | {'Influ':>6} | {'Crit':>6} | ", end="")
    if solutions:
        print(f"{'P(=1 in solutions)':>18}", end="")
    print()
    print("-" * 70)

    # Compute probability of each bit being 1 across all solutions
    if solutions:
        prob_1 = []
        for var in range(n):
            count_1 = sum(sol[var] for sol in solutions)
            prob_1.append(count_1 / len(solutions))

    for var in range(n):
        p = bit_pressure(clauses, n, var)
        f = bit_frustration(clauses, n, var)
        i = bit_influence(clauses, n, var)
        c = bit_criticality(clauses, n, var)

        print(f"  x{var:>2} | {p:>+6.3f} | {f:>6.3f} | {i:>6.3f} | {c:>6.3f} | ", end="")
        if solutions:
            print(f"{prob_1[var]:>18.3f}", end="")
            # Mark if pressure direction matches majority solution
            predicted = 1 if p > 0 else 0
            actual_majority = 1 if prob_1[var] > 0.5 else 0
            match = "✓" if predicted == actual_majority else "✗"
            print(f"  {match}", end="")
        print()


def experiment_xray():
    """Deep look at bit structure."""
    print("\n" + "=" * 70)
    print("BIT X-RAY: Internal structure of each variable")
    print("=" * 70)

    n = 10

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        # Find a satisfiable instance
        for seed in range(100):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if len(solutions) > 0:
                break

        print(f"\n## {label} instance (ratio={ratio}, {len(solutions)} solutions)")
        show_bit_xray(clauses, n, solutions)

        # Does pressure predict the right answer?
        if solutions:
            correct = 0
            for var in range(n):
                p = bit_pressure(clauses, n, var)
                predicted = 1 if p > 0 else 0
                # Check against majority across solutions
                count_1 = sum(sol[var] for sol in solutions)
                actual = 1 if count_1 > len(solutions) / 2 else 0
                if predicted == actual:
                    correct += 1
            print(f"\n  Pressure predicts correct value for {correct}/{n} bits")


if __name__ == "__main__":
    random.seed(42)

    experiment_xray()
    print("\n")
    experiment_crystallization()
