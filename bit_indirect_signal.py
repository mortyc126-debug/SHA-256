"""
Indirect Signal — Using neighbor corroboration to close the 19% gap.

Key insight: gap bits have indirect_signal 8x weaker than correct bits.
Can we COMPUTE a better tension by incorporating neighbor evidence?

This is "asking neighbors" — the user's original intuition.
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
# ENHANCED TENSION: incorporate neighbor evidence
# ============================================================

def tension_v2(clauses, n, var, fixed=None, all_tensions=None):
    """
    Enhanced tension: direct signal + indirect corroboration.

    For each clause containing var:
    - Direct: does the clause want var=1 or var=0?
    - Indirect: do the OTHER variables in the clause SUPPORT that direction?

    If var appears positive in clause (x_i ∨ x_j ∨ x_k):
      Direct: pushes var toward 1
      Indirect: if x_j and x_k are ALSO likely to be satisfied
        (their tension says they'll help), then this clause is
        LESS dependent on var → weaker push.
        If x_j and x_k are unlikely to help → clause NEEDS var → stronger push.
    """
    if fixed is None:
        fixed = {}
    if all_tensions is None:
        all_tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}

    push_1 = 0.0
    push_0 = 0.0

    for clause in clauses:
        already_sat = False
        remaining = []
        var_sign = None

        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
            else:
                remaining.append((v, s))
                if v == var:
                    var_sign = s

        if already_sat or var_sign is None:
            continue

        # How likely are OTHER literals to satisfy this clause?
        others_help_prob = 0.0
        for v, s in remaining:
            if v == var:
                continue
            t = all_tensions.get(v, 0)
            # Probability that literal (v, s) is true:
            # If s=+1: prob = (1 + t) / 2  (t>0 means likely 1)
            # If s=-1: prob = (1 - t) / 2  (t>0 means likely 1, so ¬t likely 0)
            if s == 1:
                p_lit = (1 + t) / 2
            else:
                p_lit = (1 - t) / 2
            others_help_prob = 1 - (1 - others_help_prob) * (1 - p_lit)

        # Clause's NEED for var: higher when others are unlikely to help
        need = 1.0 - others_help_prob

        if var_sign == 1:
            push_1 += need
        else:
            push_0 += need

    total = push_1 + push_0
    if total == 0:
        return 0.0
    return (push_1 - push_0) / total


def tension_v3(clauses, n, var, fixed=None, all_tensions=None):
    """
    V3: Iterative refinement.
    Compute v2 tensions for all bits, then recompute using the v2 tensions.
    Like one step of belief propagation but using our tension framework.
    """
    if fixed is None:
        fixed = {}

    # Start with v1 tensions
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}

    # One round of v2 refinement
    new_tensions = {}
    for v in tensions:
        new_tensions[v] = tension_v2(clauses, n, v, fixed, tensions)

    # Another round using refined tensions
    final_tensions = {}
    for v in new_tensions:
        final_tensions[v] = tension_v2(clauses, n, v, fixed, new_tensions)

    return final_tensions.get(var, 0.0)


def tension_v4_iterative(clauses, n, fixed=None, n_iter=5):
    """
    V4: Multiple rounds of refinement.
    Each round uses previous round's tensions.
    """
    if fixed is None:
        fixed = {}

    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}

    for iteration in range(n_iter):
        new_tensions = {}
        for v in tensions:
            new_tensions[v] = tension_v2(clauses, n, v, fixed, tensions)

        # Damping: mix old and new
        for v in tensions:
            tensions[v] = 0.5 * tensions[v] + 0.5 * new_tensions[v]

    return tensions


# ============================================================
# TEST: Does v2/v3/v4 beat v1?
# ============================================================

def test_accuracy(clauses, n, solutions):
    """Compare prediction accuracy of all tension versions."""
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    # V1: standard tension
    v1_correct = 0
    v1_tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

    # V2: neighbor-aware
    v2_correct = 0
    v2_tensions = {v: tension_v2(clauses, n, v, {}, v1_tensions) for v in range(n)}

    # V3: double refined
    v3_correct = 0

    # V4: iterative (5 rounds)
    v4_tensions = tension_v4_iterative(clauses, n, {}, n_iter=5)
    v4_correct = 0

    # V4-10: iterative (10 rounds)
    v4_10_tensions = tension_v4_iterative(clauses, n, {}, n_iter=10)
    v4_10_correct = 0

    for var in range(n):
        actual = correct_val[var]

        if (1 if v1_tensions[var] >= 0 else 0) == actual:
            v1_correct += 1
        if (1 if v2_tensions[var] >= 0 else 0) == actual:
            v2_correct += 1

        v3_t = tension_v3(clauses, n, var, {}, v1_tensions)
        if (1 if v3_t >= 0 else 0) == actual:
            v3_correct += 1

        if (1 if v4_tensions.get(var, 0) >= 0 else 0) == actual:
            v4_correct += 1

        if (1 if v4_10_tensions.get(var, 0) >= 0 else 0) == actual:
            v4_10_correct += 1

    return {
        'v1': v1_correct,
        'v2': v2_correct,
        'v3': v3_correct,
        'v4_5': v4_correct,
        'v4_10': v4_10_correct,
        'total': n,
    }


# ============================================================
# SOLVER using enhanced tension
# ============================================================

def solve_v4(clauses, n, n_iter=5):
    """Crystallization using v4 iterative tension."""
    fixed = {}
    for step in range(n):
        tensions = tension_v4_iterative(clauses, n, fixed, n_iter=n_iter)
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break
        best = max(unfixed, key=lambda v: abs(tensions.get(v, 0)))
        fixed[best] = 1 if tensions.get(best, 0) >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("INDIRECT SIGNAL: Enhanced tension versions")
    print("=" * 70)

    # Accuracy comparison
    totals = {'v1': 0, 'v2': 0, 'v3': 0, 'v4_5': 0, 'v4_10': 0, 'n': 0}

    for ratio in [3.5, 4.0, 4.27]:
        ratio_totals = {'v1': 0, 'v2': 0, 'v3': 0, 'v4_5': 0, 'v4_10': 0, 'n': 0}

        for seed in range(150):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            result = test_accuracy(clauses, 12, solutions)
            if result:
                for key in result:
                    ratio_totals[key] = ratio_totals.get(key, 0) + result[key]
                    totals[key] = totals.get(key, 0) + result[key]

        t = ratio_totals.get('total', 0)
        if t > 0:
            print(f"\n  ratio={ratio}:")
            print(f"    v1 (standard):       {ratio_totals['v1']/t*100:.1f}%")
            print(f"    v2 (neighbor-aware):  {ratio_totals['v2']/t*100:.1f}%")
            print(f"    v3 (double-refined):  {ratio_totals['v3']/t*100:.1f}%")
            print(f"    v4 (5 iterations):   {ratio_totals['v4_5']/t*100:.1f}%")
            print(f"    v4 (10 iterations):  {ratio_totals['v4_10']/t*100:.1f}%")

    t = totals.get('total', 0)
    if t > 0:
        print(f"\n  OVERALL:")
        print(f"    v1: {totals['v1']/t*100:.1f}%")
        print(f"    v2: {totals['v2']/t*100:.1f}%")
        print(f"    v3: {totals['v3']/t*100:.1f}%")
        print(f"    v4(5): {totals['v4_5']/t*100:.1f}%")
        print(f"    v4(10): {totals['v4_10']/t*100:.1f}%")

    # Solver comparison
    print("\n" + "=" * 70)
    print("SOLVER: v4-tension crystallization vs baseline")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        baseline = 0
        v4_solved = 0
        total = 0

        for seed in range(150):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            total += 1

            # Baseline
            fixed = {}
            for step in range(12):
                unfixed = [v for v in range(12) if v not in fixed]
                if not unfixed:
                    break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, 12, v, fixed)))
                sigma = bit_tension(clauses, 12, best, fixed)
                fixed[best] = 1 if sigma >= 0 else 0
            assignment = [fixed.get(v, 0) for v in range(12)]
            if evaluate(clauses, assignment) == len(clauses):
                baseline += 1

            # V4 solver
            _, success = solve_v4(clauses, 12, n_iter=5)
            if success:
                v4_solved += 1

        print(f"\n  ratio={ratio}: baseline={baseline}/{total} "
              f"({baseline/total*100:.1f}%), "
              f"v4={v4_solved}/{total} ({v4_solved/total*100:.1f}%)")

    # What happens to the gap with v4?
    print("\n" + "=" * 70)
    print("GAP ANALYSIS: Does v4 close the 19% gap?")
    print("=" * 70)

    for ratio in [4.27]:
        v1_acc_sum = 0
        v4_acc_sum = 0
        optimal_sum = 0
        total_bits = 0

        for seed in range(200):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            v1_t = {v: bit_tension(clauses, 12, v) for v in range(12)}
            v4_t = tension_v4_iterative(clauses, 12, {}, n_iter=10)

            for var in range(12):
                total_bits += 1
                optimal_sum += max(prob_1[var], 1 - prob_1[var])
                if (1 if v1_t[var] >= 0 else 0) == correct_val[var]:
                    v1_acc_sum += 1
                if (1 if v4_t.get(var, 0) >= 0 else 0) == correct_val[var]:
                    v4_acc_sum += 1

        print(f"\n  ratio={ratio}:")
        print(f"    v1 (tension):    {v1_acc_sum/total_bits*100:.1f}%")
        print(f"    v4 (iterative):  {v4_acc_sum/total_bits*100:.1f}%")
        print(f"    optimal:         {optimal_sum/total_bits*100:.1f}%")
        print(f"    v1 gap:          {(optimal_sum/total_bits - v1_acc_sum/total_bits)*100:.1f}%")
        print(f"    v4 gap:          {(optimal_sum/total_bits - v4_acc_sum/total_bits)*100:.1f}%")
        print(f"    gap CLOSED:      {(v4_acc_sum - v1_acc_sum)/total_bits*100:.1f}%")
