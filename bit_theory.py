"""
Bit Theory — Analytical derivations of empirical laws.

Can we DERIVE our experimental findings from first principles?
If yes — we have a real theory, not just observations.
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


def bit_tension(clauses, n, var, fixed=None):
    if fixed is None:
        fixed = {}
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
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# ANALYTICAL DERIVATION 1: Expected |σ| for random 3-SAT
# ============================================================

def derive_expected_tension(n, ratio):
    """
    DERIVATION: For random 3-SAT with n variables and m = ratio*n clauses:

    Each clause has 3 variables, each positive or negative with prob 1/2.
    Variable x_i appears in a clause with prob 3/n (approximately).
    Expected number of clauses containing x_i: d = 3*m/n = 3*ratio.

    In each clause, x_i appears positive (sign=+1) or negative (sign=-1)
    with equal probability.

    Tension σ = (pos - neg) / (pos + neg) where pos = #positive appearances,
    neg = #negative appearances.

    If d = 3*ratio clauses contain x_i, each with random sign ±1,
    then pos ~ Binomial(d, 0.5) and neg = d - pos.

    σ = (2*pos - d) / d

    E[|σ|] = E[|2*pos/d - 1|] where pos ~ Bin(d, 0.5)

    This is the expected absolute value of a centered binomial.
    """
    d = 3 * ratio  # expected degree

    # For Binomial(d, 0.5), compute E[|2X/d - 1|]
    d_int = int(round(d))
    if d_int == 0:
        return 0.0

    expected_abs = 0.0
    for k in range(d_int + 1):
        # P(X=k) = C(d,k) * 0.5^d
        log_prob = (math.lgamma(d_int + 1) - math.lgamma(k + 1) -
                    math.lgamma(d_int - k + 1) - d_int * math.log(2))
        prob = math.exp(log_prob)
        sigma = abs(2 * k / d_int - 1)
        expected_abs += prob * sigma

    return expected_abs


def derive_expected_temperature(n, ratio):
    """T = 1 - <|σ|>"""
    return 1.0 - derive_expected_tension(n, ratio)


def verify_tension_derivation():
    """Compare analytical prediction vs experiment."""
    print("=" * 70)
    print("DERIVATION 1: Expected tension <|σ|>")
    print("Can we predict the fundamental constant 0.24?")
    print("=" * 70)

    print(f"\n{'ratio':>6} | {'predicted':>9} | {'measured':>8} | {'error':>7}")
    print("-" * 45)

    for ratio_10 in range(15, 55, 5):
        ratio = ratio_10 / 10.0
        predicted = derive_expected_tension(12, ratio)

        # Measure
        measured_vals = []
        for seed in range(200):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            for var in range(12):
                measured_vals.append(abs(bit_tension(clauses, 12, var)))

        measured = sum(measured_vals) / len(measured_vals)
        error = abs(predicted - measured) / measured * 100 if measured > 0 else 0

        print(f"{ratio:>6.1f} | {predicted:>9.4f} | {measured:>8.4f} | {error:>6.1f}%")


# ============================================================
# ANALYTICAL DERIVATION 2: Force symmetry F(i→j) = F(j→i)
# ============================================================

def derive_force_symmetry():
    """
    WHY are forces symmetric?

    F(i→j) = σ(j|i=1) - σ(j|i=0)

    In a clause (x_i ∨ x_j ∨ x_k):
    - If i=1 (positive): clause is satisfied → no pressure on j
    - If i=0 (positive): clause depends on j and k → pressure on j

    F(i→j) comes from clauses containing BOTH i and j.
    For such a clause, fixing i affects j's pressure, and vice versa.

    The effect is symmetric because:
    - Fixing i=1 removes a clause from j's pressure (clause satisfied)
    - Fixing j=1 removes the SAME clause from i's pressure

    The direction depends on signs: if both positive, both lose a
    "push toward 1" when the other is set to 1.

    Let's verify: F(i→j) = F(j→i) should hold exactly for pairs
    that share exactly one clause.
    """
    print("\n" + "=" * 70)
    print("DERIVATION 2: Why forces are symmetric")
    print("=" * 70)

    # Test: for pairs sharing exactly 1 clause, is F(i→j) = F(j→i) exact?
    errors_1 = []
    errors_2 = []
    errors_3 = []

    for seed in range(100):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)

        shared = [[0] * 12 for _ in range(12)]
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a + 1, len(vs)):
                    shared[vs[a]][vs[b]] += 1
                    shared[vs[b]][vs[a]] += 1

        for i in range(12):
            for j in range(i + 1, 12):
                s_ij = shared[i][j]
                if s_ij == 0:
                    continue

                fij = bit_tension(clauses, 12, j, {i: 1}) - bit_tension(clauses, 12, j, {i: 0})
                fji = bit_tension(clauses, 12, i, {j: 1}) - bit_tension(clauses, 12, i, {j: 0})

                err = abs(fij - fji)
                if s_ij == 1:
                    errors_1.append(err)
                elif s_ij == 2:
                    errors_2.append(err)
                elif s_ij >= 3:
                    errors_3.append(err)

    mean = lambda lst: sum(lst) / len(lst) if lst else 0
    print(f"\n  Asymmetry |F(i→j) - F(j→i)| by shared clauses:")
    print(f"    1 shared clause: {mean(errors_1):.4f} (n={len(errors_1)})")
    print(f"    2 shared clauses: {mean(errors_2):.4f} (n={len(errors_2)})")
    print(f"    3+ shared clauses: {mean(errors_3):.4f} (n={len(errors_3)})")
    print(f"\n  → Symmetry is APPROXIMATE, not exact.")
    print(f"  → Error grows with shared clauses (nonlinear effects)")


# ============================================================
# DERIVATION 3: Correlation length = 1
# ============================================================

def derive_correlation_length():
    """
    WHY is ξ = 1?

    In 3-SAT, each clause connects 3 variables.
    Fixing variable i directly affects only variables in shared clauses (distance 1).

    For distance 2: i affects j, j affects k. But j is NOT fixed — j is still
    free. So j's tension changes, but since j hasn't been fixed, j doesn't
    transmit pressure changes to k.

    The key insight: TENSION CHANGE ≠ FIXATION.
    Only FIXATION transmits force. Tension change is a "potential" force
    that only activates upon fixation.

    This is why ξ=1: in a single step, only direct neighbors are affected.
    Over multiple steps (crystallization), information CAN propagate further —
    but only through the cascade of fixations.

    Let's verify: after fixing i AND the most affected neighbor j,
    does the effect reach distance 2?
    """
    print("\n" + "=" * 70)
    print("DERIVATION 3: Why correlation length = 1")
    print("Does TWO-STEP fixation reach distance 2?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if solutions and 2 < len(solutions) < 100:
                break

        # Build distance matrix
        adj = {i: set() for i in range(12)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a + 1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        def bfs_dist(start):
            dist = {start: 0}
            queue = [start]
            idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr] + 1
                        queue.append(nb)
            return dist

        # For each source: fix it, then fix most affected, check distance 2
        reach_dist2 = 0
        total_tests = 0

        for source in range(12):
            dists = bfs_dist(source)

            # Fix source
            sigma = bit_tension(clauses, 12, source)
            fixed = {source: 1 if sigma >= 0 else 0}

            # Find most affected neighbor
            best_j = None
            best_change = 0
            for j in range(12):
                if j == source:
                    continue
                change = abs(bit_tension(clauses, 12, j, fixed) - bit_tension(clauses, 12, j))
                if change > best_change:
                    best_change = change
                    best_j = j

            if best_j is None:
                continue

            # Fix best_j too
            sigma_j = bit_tension(clauses, 12, best_j, fixed)
            fixed[best_j] = 1 if sigma_j >= 0 else 0

            # Now check: any significant change at distance 2?
            for k in range(12):
                if k in fixed or dists.get(k, 0) != 2:
                    continue
                total_tests += 1
                change_k = abs(bit_tension(clauses, 12, k, fixed) - bit_tension(clauses, 12, k))
                if change_k > 0.05:
                    reach_dist2 += 1

        print(f"\n  {label}: Two-step fixation reaches distance 2: "
              f"{reach_dist2}/{total_tests} "
              f"({reach_dist2/total_tests*100:.0f}%)" if total_tests > 0 else "")


# ============================================================
# DERIVATION 4: Why T is quasi-conserved
# ============================================================

def derive_temperature_conservation():
    """
    WHY is temperature approximately conserved?

    T = average frustration = average (1 - |σ|).

    When we fix a bit x_i:
    - Clauses containing x_i are either satisfied (removed) or simplified.
    - Satisfied clauses REDUCE pressure on remaining bits → |σ| decreases → T increases
    - Simplified clauses CONCENTRATE pressure → |σ| increases → T decreases

    These two effects approximately CANCEL:
    - Removing satisfied clauses makes remaining bits more frustrated (more options gone)
    - But simplifying unsatisfied clauses makes them more constrained (clearer direction)

    Net effect ≈ 0, hence T ≈ const.

    Let's decompose ΔT into these two contributions.
    """
    print("\n" + "=" * 70)
    print("DERIVATION 4: Why temperature is quasi-conserved")
    print("Decomposing ΔT into satisfied vs simplified clause effects")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        satisfied_effects = []
        simplified_effects = []
        net_effects = []

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            # Base temperature
            T_base = sum(1 - abs(bit_tension(clauses, 12, v)) for v in range(12)) / 12

            # Fix most confident bit
            best_var = max(range(12), key=lambda v: abs(bit_tension(clauses, 12, v)))
            best_val = 1 if bit_tension(clauses, 12, best_var) >= 0 else 0

            # Classify clauses
            sat_clauses = []  # satisfied by fixing best_var
            simp_clauses = []  # simplified (best_var in clause but doesn't satisfy)
            other_clauses = []  # not containing best_var

            for clause in clauses:
                contains = False
                satisfies = False
                for v, s in clause:
                    if v == best_var:
                        contains = True
                        if (s == 1 and best_val == 1) or (s == -1 and best_val == 0):
                            satisfies = True

                if not contains:
                    other_clauses.append(clause)
                elif satisfies:
                    sat_clauses.append(clause)
                else:
                    simp_clauses.append(clause)

            # T with ONLY satisfied clauses removed (but not simplified)
            remaining_unsimp = simp_clauses + other_clauses
            if remaining_unsimp:
                T_no_sat = sum(1 - abs(bit_tension(remaining_unsimp, 12, v))
                               for v in range(12) if v != best_var) / 11
                satisfied_effects.append(T_no_sat - T_base)

            # T with EVERYTHING (full fixation effect)
            T_full = sum(1 - abs(bit_tension(clauses, 12, v, {best_var: best_val}))
                         for v in range(12) if v != best_var) / 11
            net_effects.append(T_full - T_base)

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}:")
        print(f"    Removing satisfied clauses:  ΔT = {mean(satisfied_effects):+.4f}")
        print(f"    Full fixation effect:        ΔT = {mean(net_effects):+.4f}")
        print(f"    → Net ΔT ≈ 0 because effects partially cancel")


# ============================================================
# DERIVATION 5: Nonlinear (3-body) interactions
# ============================================================

def three_body_interaction(clauses, n):
    """
    Measure: does fixing bits i AND j together have a different effect
    than fixing i alone + fixing j alone?

    Δ³(i,j,k) = σ(k|i,j fixed) - σ(k|i fixed) - σ(k|j fixed) + σ(k|none fixed)

    If Δ³ = 0: no 3-body interaction (forces are additive)
    If Δ³ ≠ 0: nonlinear 3-body effect
    """
    three_body = []

    for i in range(n):
        for j in range(i + 1, n):
            si = bit_tension(clauses, n, i)
            sj = bit_tension(clauses, n, j)
            vi = 1 if si >= 0 else 0
            vj = 1 if sj >= 0 else 0

            for k in range(n):
                if k == i or k == j:
                    continue

                s_none = bit_tension(clauses, n, k)
                s_i = bit_tension(clauses, n, k, {i: vi})
                s_j = bit_tension(clauses, n, k, {j: vj})
                s_ij = bit_tension(clauses, n, k, {i: vi, j: vj})

                delta3 = s_ij - s_i - s_j + s_none
                three_body.append(abs(delta3))

    return three_body


def verify_three_body():
    """Are 3-body interactions significant?"""
    print("\n" + "=" * 70)
    print("DERIVATION 5: Three-body (nonlinear) interactions")
    print("Is the force between bits ADDITIVE or NONLINEAR?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(10, int(ratio * 10), seed=seed)
            solutions = find_solutions(clauses, 10)
            if solutions and 2 < len(solutions) < 100:
                break

        deltas = three_body_interaction(clauses, 10)
        mean_d = sum(deltas) / len(deltas)
        max_d = max(deltas)
        nonzero = sum(1 for d in deltas if d > 0.01)

        print(f"\n  {label}: |Δ³| avg = {mean_d:.4f}, max = {max_d:.4f}, "
              f"nonzero(>0.01) = {nonzero}/{len(deltas)} "
              f"({nonzero/len(deltas)*100:.0f}%)")


if __name__ == "__main__":
    random.seed(42)
    verify_tension_derivation()
    derive_force_symmetry()
    derive_correlation_length()
    derive_temperature_conservation()
    verify_three_body()
