"""
The 19% Gap — What information does tension MISS?

Tension predicts 69%. Optimal is 88%. What's in the gap?

Approach: for each bit where tension is WRONG but optimal is RIGHT,
find what structural feature distinguishes it.
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
# What does the OPTIMAL predictor know that tension doesn't?
# ============================================================

def analyze_gap(clauses, n, solutions):
    """
    For each bit, classify:
    - BOTH RIGHT: tension correct, optimal correct
    - TENSION WRONG: tension wrong, optimal correct (THE GAP)
    - BOTH WRONG: both wrong (truly ambiguous)
    - TENSION RIGHT, OPTIMAL WRONG: impossible by definition

    For GAP bits: what's special?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    gap_bits = []     # tension wrong, optimal would be right
    correct_bits = [] # tension correct

    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0
        predicted = 1 if sigma >= 0 else 0
        optimal_acc = max(prob_1[var], 1 - prob_1[var])

        # Structural features
        pos_count = 0
        neg_count = 0
        clause_sizes = []  # how many free literals in clauses containing var
        neighbor_tensions = []
        co_occurrence = {}  # which other vars appear with this one

        for clause in clauses:
            has_var = False
            var_sign = 0
            others = []
            for v, s in clause:
                if v == var:
                    has_var = True
                    var_sign = s
                else:
                    others.append((v, s))
            if has_var:
                if var_sign == 1:
                    pos_count += 1
                else:
                    neg_count += 1
                clause_sizes.append(len(clause))
                for v, s in others:
                    neighbor_tensions.append(bit_tension(clauses, n, v))
                    co_occurrence[v] = co_occurrence.get(v, 0) + 1

        # Indirect influence: what do neighbors' neighbors say?
        indirect_signal = 0
        for nb, count in co_occurrence.items():
            nb_sigma = bit_tension(clauses, n, nb)
            # If neighbor is confident AND agrees with my direction → good
            # If neighbor is confident AND disagrees → bad
            indirect_signal += nb_sigma * sigma * count

        # Cycle detection: is this var part of a short cycle?
        # (var appears with A in clause 1, A appears with var in clause 2 with opposite sign)
        cycle_conflict = 0
        for clause_i in range(len(clauses)):
            for v_i, s_i in clauses[clause_i]:
                if v_i != var:
                    continue
                # var appears in clause_i with sign s_i
                for clause_j in range(clause_i + 1, len(clauses)):
                    for v_j, s_j in clauses[clause_j]:
                        if v_j != var:
                            continue
                        # var appears in clause_j with sign s_j
                        if s_i != s_j:
                            # Same var appears with opposite signs
                            # Check if clauses share another variable
                            vars_i = {v for v, s in clauses[clause_i] if v != var}
                            vars_j = {v for v, s in clauses[clause_j] if v != var}
                            shared = vars_i & vars_j
                            if shared:
                                cycle_conflict += len(shared)

        entry = {
            'var': var,
            'sigma': sigma,
            'abs_sigma': abs(sigma),
            'prob_1': prob_1[var],
            'optimal_acc': optimal_acc,
            'pos_count': pos_count,
            'neg_count': neg_count,
            'degree': pos_count + neg_count,
            'polarity_imbalance': abs(pos_count - neg_count) / max(pos_count + neg_count, 1),
            'avg_neighbor_tension': sum(neighbor_tensions) / len(neighbor_tensions) if neighbor_tensions else 0,
            'avg_abs_neighbor_tension': sum(abs(t) for t in neighbor_tensions) / len(neighbor_tensions) if neighbor_tensions else 0,
            'n_unique_neighbors': len(co_occurrence),
            'max_co_occurrence': max(co_occurrence.values()) if co_occurrence else 0,
            'indirect_signal': indirect_signal,
            'cycle_conflict': cycle_conflict,
        }

        if predicted != actual and optimal_acc > 0.6:
            gap_bits.append(entry)
        elif predicted == actual:
            correct_bits.append(entry)

    return gap_bits, correct_bits


def compare_gap_vs_correct(gap_bits, correct_bits):
    mean = lambda lst: sum(lst) / len(lst) if lst else 0

    properties = [
        'abs_sigma', 'degree', 'polarity_imbalance',
        'avg_abs_neighbor_tension', 'n_unique_neighbors',
        'max_co_occurrence', 'indirect_signal', 'cycle_conflict',
    ]

    print(f"\n  {'property':>25} | {'CORRECT':>9} | {'GAP':>9} | {'ratio':>7} | flag")
    print("  " + "-" * 70)

    for prop in properties:
        c_val = mean([b[prop] for b in correct_bits])
        g_val = mean([b[prop] for b in gap_bits])

        if c_val > 0:
            ratio = g_val / c_val
        elif g_val > 0:
            ratio = float('inf')
        else:
            ratio = 1.0

        flag = ""
        if ratio > 1.5 or ratio < 0.67:
            flag = " ← SIGNIFICANT"
        elif ratio > 1.2 or ratio < 0.83:
            flag = " ← notable"

        print(f"  {prop:>25} | {c_val:>9.3f} | {g_val:>9.3f} | "
              f"{ratio:>7.2f} | {flag}")


# ============================================================
# Can cycle_conflict PREDICT wrong bits?
# ============================================================

def test_cycle_predictor(clauses, n, solutions):
    """
    If cycle_conflict predicts which bits are in the gap,
    we can use it to DISTRUST those bits and try the opposite.
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    results = []
    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0
        predicted = 1 if sigma >= 0 else 0

        # Compute cycle_conflict
        cycle_conflict = 0
        for ci in range(len(clauses)):
            has_var_i = False
            sign_i = 0
            for v, s in clauses[ci]:
                if v == var:
                    has_var_i = True
                    sign_i = s
            if not has_var_i:
                continue
            for cj in range(ci + 1, len(clauses)):
                has_var_j = False
                sign_j = 0
                for v, s in clauses[cj]:
                    if v == var:
                        has_var_j = True
                        sign_j = s
                if not has_var_j:
                    continue
                if sign_i != sign_j:
                    vars_i = {v for v, s in clauses[ci] if v != var}
                    vars_j = {v for v, s in clauses[cj] if v != var}
                    cycle_conflict += len(vars_i & vars_j)

        results.append({
            'var': var,
            'cycle_conflict': cycle_conflict,
            'tension_correct': predicted == actual,
            'sigma': sigma,
            'actual': actual,
        })

    return results


# ============================================================
# New solver: tension + cycle distrust
# ============================================================

def solve_cycle_aware(clauses, n):
    """
    Like tension, but DISTRUST bits with high cycle_conflict.
    For those bits: try opposite of tension.
    """
    # Precompute cycle conflicts
    cycle_conflicts = [0] * n
    for var in range(n):
        for ci in range(len(clauses)):
            has_var = False
            sign_i = 0
            for v, s in clauses[ci]:
                if v == var:
                    has_var = True
                    sign_i = s
            if not has_var:
                continue
            for cj in range(ci + 1, len(clauses)):
                has_var_j = False
                sign_j = 0
                for v, s in clauses[cj]:
                    if v == var:
                        has_var_j = True
                        sign_j = s
                if not has_var_j:
                    continue
                if sign_i != sign_j:
                    vars_i = {v for v, s in clauses[ci] if v != var}
                    vars_j = {v for v, s in clauses[cj] if v != var}
                    cycle_conflicts[var] += len(vars_i & vars_j)

    median_cc = sorted(cycle_conflicts)[n // 2]

    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        # Sort by confidence, but deprioritize high-cycle bits
        candidates = []
        for v in unfixed:
            sigma = bit_tension(clauses, n, v, fixed)
            # Penalize high cycle conflict
            effective_conf = abs(sigma)
            if cycle_conflicts[v] > median_cc:
                effective_conf *= 0.5  # deprioritize
            candidates.append((v, sigma, effective_conf))

        candidates.sort(key=lambda c: -c[2])
        best_var, best_sigma, _ = candidates[0]
        fixed[best_var] = 1 if best_sigma >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 75)
    print("THE 19% GAP: What does tension miss?")
    print("=" * 75)

    # Collect gap analysis across many instances
    all_gap = []
    all_correct = []

    for seed in range(300):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue

        result = analyze_gap(clauses, 12, solutions)
        if result:
            gap, correct = result
            all_gap.extend(gap)
            all_correct.extend(correct)

    print(f"\n  Total: {len(all_correct)} correct predictions, "
          f"{len(all_gap)} gap predictions")
    compare_gap_vs_correct(all_gap, all_correct)

    # Test cycle_conflict as predictor
    print("\n" + "=" * 75)
    print("Can CYCLE CONFLICT predict wrong bits?")
    print("=" * 75)

    high_cc_correct = 0
    high_cc_total = 0
    low_cc_correct = 0
    low_cc_total = 0

    for seed in range(300):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue

        results = test_cycle_predictor(clauses, 12, solutions)
        if not results:
            continue

        median_cc = sorted([r['cycle_conflict'] for r in results])[6]

        for r in results:
            if r['cycle_conflict'] > median_cc:
                high_cc_total += 1
                if r['tension_correct']:
                    high_cc_correct += 1
            else:
                low_cc_total += 1
                if r['tension_correct']:
                    low_cc_correct += 1

    print(f"\n  Low cycle conflict:  {low_cc_correct}/{low_cc_total} "
          f"= {low_cc_correct/low_cc_total*100:.1f}% correct")
    print(f"  High cycle conflict: {high_cc_correct}/{high_cc_total} "
          f"= {high_cc_correct/high_cc_total*100:.1f}% correct")
    print(f"  Difference: {(low_cc_correct/low_cc_total - high_cc_correct/high_cc_total)*100:.1f}%")

    # Solver comparison
    print("\n" + "=" * 75)
    print("Cycle-aware solver vs baseline")
    print("=" * 75)

    for ratio in [3.5, 4.0, 4.27]:
        baseline_solved = 0
        cycle_solved = 0
        total = 0

        for seed in range(200):
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
                baseline_solved += 1

            # Cycle-aware
            _, success = solve_cycle_aware(clauses, 12)
            if success:
                cycle_solved += 1

        print(f"\n  ratio={ratio}: baseline={baseline_solved}/{total} "
              f"({baseline_solved/total*100:.1f}%), "
              f"cycle-aware={cycle_solved}/{total} "
              f"({cycle_solved/total*100:.1f}%)")
