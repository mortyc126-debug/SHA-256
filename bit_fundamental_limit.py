"""
Is 70% a fundamental limit?

Three tests:
1. INFORMATION-THEORETIC: How much information about each bit is
   AVAILABLE in the clause structure? Is it exactly 70%?
2. OPTIMAL PREDICTOR: If we had unlimited compute but could only
   look at the clause structure (not solutions), what's the MAX?
3. COMPARISON WITH ORACLE METHODS: Survey propagation, belief propagation
   — do they beat 70%?

If 70% is fundamental, then it IS 100% of available information.
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
# TEST 1: Optimal single-bit predictor (brute force)
# ============================================================

def optimal_predictor(clauses, n, solutions):
    """
    For each bit, compute the BEST POSSIBLE prediction accuracy
    given FULL knowledge of the clause structure.

    The optimal predictor for bit var is:
    P(var=1 | clause_structure) = fraction of solutions with var=1

    If P > 0.5, predict 1. Accuracy = max(P, 1-P).
    This is the INFORMATION-THEORETIC LIMIT — no method can beat this
    without looking at multiple bits simultaneously.
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    optimal_acc = [max(p, 1-p) for p in prob_1]
    return optimal_acc


# ============================================================
# TEST 2: Optimal JOINT predictor (MAP assignment)
# ============================================================

def map_predictor(clauses, n, solutions):
    """
    The MAP (Maximum A Posteriori) predictor: for each bit,
    choose the value that appears in THE MOST solutions.

    This is optimal for the MARGINAL of each bit.
    But the JOINT MAP (most common full assignment) might differ.

    Compute both and compare.
    """
    if not solutions:
        return None

    # Marginal MAP: for each bit, pick majority
    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    marginal_map = [1 if p > 0.5 else 0 for p in prob_1]

    # Is the marginal MAP itself a solution?
    marginal_sat = evaluate(clauses, marginal_map)
    marginal_is_solution = marginal_sat == len(clauses)

    # Joint MAP: find the most common solution
    from collections import Counter
    sol_tuples = [tuple(s) for s in solutions]
    most_common = Counter(sol_tuples).most_common(1)[0][0]

    # How much do marginal MAP and joint MAP disagree?
    disagreements = sum(marginal_map[v] != most_common[v] for v in range(n))

    return {
        'marginal_map_is_solution': marginal_is_solution,
        'joint_most_common': most_common,
        'disagreements': disagreements,
        'marginal_map': marginal_map,
    }


# ============================================================
# TEST 3: Compare methods against theoretical optimum
# ============================================================

def compare_against_optimum(clauses, n, solutions):
    """
    For each bit, compare:
    1. Tension prediction accuracy
    2. Theoretical optimal (marginal) accuracy
    3. Gap = how much info tension MISSES
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    results = []
    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0

        # Tension prediction
        tension_pred = 1 if sigma >= 0 else 0
        tension_correct = tension_pred == actual

        # Optimal accuracy
        optimal = max(prob_1[var], 1 - prob_1[var])

        # Is bit "ambiguous" (near 50/50 in solutions)?
        ambiguity = 1.0 - 2 * abs(prob_1[var] - 0.5)  # 0=fully determined, 1=fully ambiguous

        results.append({
            'var': var,
            'tension_correct': tension_correct,
            'optimal_acc': optimal,
            'ambiguity': ambiguity,
            'prob_1': prob_1[var],
        })

    return results


# ============================================================
# TEST 4: How much information is IN the clause structure?
# ============================================================

def mutual_information_bit(clauses, n, var, solutions):
    """
    Compute I(var ; clause_structure).

    In practice: H(var) - H(var | knowing the solution exists)

    H(var) for uniform prior = 1 bit
    H(var | solutions) = -p*log(p) - (1-p)*log(1-p) where p = fraction of 1s in solutions

    The mutual information tells us: how many bits of info about var
    does the clause structure provide?
    """
    if not solutions:
        return 0.0

    p = sum(s[var] for s in solutions) / len(solutions)
    if p == 0 or p == 1:
        h_given = 0.0
    else:
        h_given = -p * math.log2(p) - (1-p) * math.log2(1-p)

    h_prior = 1.0  # uniform prior
    mi = h_prior - h_given

    return mi


# ============================================================
# TEST 5: Belief propagation (proper implementation)
# ============================================================

def belief_propagation_predict(clauses, n, max_iter=100, damping=0.5):
    """
    Proper belief propagation on factor graph.
    Returns predicted assignment and per-bit confidence.
    """
    # Messages: variable-to-clause and clause-to-variable
    # v2c[var][clause_idx] = message from var to clause (log-likelihood ratio)
    # c2v[clause_idx][var] = message from clause to var

    clause_of = {v: [] for v in range(n)}  # clauses containing each var
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            clause_of[v].append(ci)

    # Initialize
    v2c = {}
    c2v = {}
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            v2c[(v, ci)] = 0.0  # log-likelihood ratio, 0 = no preference
            c2v[(ci, v)] = 0.0

    for iteration in range(max_iter):
        # Update clause-to-variable messages
        new_c2v = {}
        for ci, clause in enumerate(clauses):
            for v_target, s_target in clause:
                # Product of (1 - tanh(incoming/2)) for other variables
                # that would make the clause unsatisfied
                product = 1.0
                for v_other, s_other in clause:
                    if v_other == v_target:
                        continue
                    msg = v2c.get((v_other, ci), 0.0)
                    # Adjust for sign
                    effective_msg = msg * s_other
                    product *= math.tanh(effective_msg / 2) if abs(effective_msg) < 20 else (1.0 if effective_msg > 0 else -1.0)

                # Message from clause to target
                val = s_target * 2 * math.atanh(max(min(product, 0.9999), -0.9999))
                new_c2v[(ci, v_target)] = val

        # Update variable-to-clause messages
        new_v2c = {}
        for v in range(n):
            total_incoming = sum(new_c2v.get((ci, v), 0.0) for ci in clause_of[v])
            for ci in clause_of[v]:
                # Message to clause ci = sum of all OTHER incoming messages
                msg = total_incoming - new_c2v.get((ci, v), 0.0)
                new_v2c[(v, ci)] = damping * v2c.get((v, ci), 0.0) + (1 - damping) * msg

        v2c = new_v2c
        c2v = new_c2v

    # Final beliefs
    beliefs = []
    for v in range(n):
        total = sum(c2v.get((ci, v), 0.0) for ci in clause_of[v])
        # Convert log-likelihood to probability
        p1 = 1.0 / (1.0 + math.exp(-max(min(total, 20), -20)))
        beliefs.append(p1)

    assignment = [1 if b > 0.5 else 0 for b in beliefs]
    confidences = [abs(b - 0.5) * 2 for b in beliefs]

    return assignment, confidences


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("IS 70% A FUNDAMENTAL LIMIT?")
    print("=" * 70)

    # Test across ratios
    print(f"\n{'ratio':>6} | {'tension':>8} | {'optimal':>8} | {'gap':>6} | "
          f"{'MI bits':>7} | {'ambig':>6} | {'BP':>8}")
    print("-" * 65)

    for ratio_10 in range(20, 55, 5):
        ratio = ratio_10 / 10.0

        tension_accs = []
        optimal_accs = []
        mis = []
        ambiguities = []
        bp_accs = []

        for seed in range(200):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            results = compare_against_optimum(clauses, 12, solutions)
            if not results:
                continue

            for r in results:
                tension_accs.append(1.0 if r['tension_correct'] else 0.0)
                optimal_accs.append(r['optimal_acc'])
                ambiguities.append(r['ambiguity'])
                mis.append(mutual_information_bit(clauses, 12, r['var'], solutions))

            # BP prediction
            bp_assign, bp_conf = belief_propagation_predict(clauses, 12)
            for v in range(12):
                bp_correct = bp_assign[v] == correct_val[v]
                bp_accs.append(1.0 if bp_correct else 0.0)

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        gap = mean(optimal_accs) - mean(tension_accs)

        print(f"{ratio:>6.1f} | {mean(tension_accs)*100:>7.1f}% | "
              f"{mean(optimal_accs)*100:>7.1f}% | {gap*100:>5.1f}% | "
              f"{mean(mis):>7.3f} | {mean(ambiguities):>6.3f} | "
              f"{mean(bp_accs)*100:>7.1f}%")

    # Detailed comparison at threshold
    print("\n" + "=" * 70)
    print("DETAILED: At ratio=4.27, per-bit analysis")
    print("=" * 70)

    all_tension_correct = 0
    all_tension_total = 0
    all_optimal_sum = 0.0
    all_bp_correct = 0
    ambig_tension = 0
    ambig_total = 0
    decis_tension = 0
    decis_total = 0
    ambig_optimal = 0.0
    decis_optimal = 0.0

    for seed in range(300):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        bp_assign, _ = belief_propagation_predict(clauses, 12)

        for var in range(12):
            sigma = bit_tension(clauses, 12, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]
            optimal = max(prob_1[var], 1 - prob_1[var])
            ambiguity = 1.0 - 2 * abs(prob_1[var] - 0.5)

            all_tension_total += 1
            if is_correct:
                all_tension_correct += 1
            all_optimal_sum += optimal
            if bp_assign[var] == correct_val[var]:
                all_bp_correct += 1

            if ambiguity > 0.5:
                ambig_total += 1
                if is_correct:
                    ambig_tension += 1
                ambig_optimal += optimal
            else:
                decis_total += 1
                if is_correct:
                    decis_tension += 1
                decis_optimal += optimal

    print(f"\n  ALL BITS:")
    print(f"    Tension accuracy:     {all_tension_correct/all_tension_total*100:.1f}%")
    print(f"    Optimal (marginal):   {all_optimal_sum/all_tension_total*100:.1f}%")
    print(f"    Belief propagation:   {all_bp_correct/all_tension_total*100:.1f}%")
    print(f"    Gap (optimal-tens):   {(all_optimal_sum/all_tension_total - all_tension_correct/all_tension_total)*100:.1f}%")

    if ambig_total > 0:
        print(f"\n  AMBIGUOUS BITS (near 50/50 in solutions): {ambig_total} bits")
        print(f"    Tension accuracy:   {ambig_tension/ambig_total*100:.1f}%")
        print(f"    Optimal accuracy:   {ambig_optimal/ambig_total*100:.1f}%")
        print(f"    Gap:                {(ambig_optimal/ambig_total - ambig_tension/ambig_total)*100:.1f}%")

    if decis_total > 0:
        print(f"\n  DECISIVE BITS (strongly biased): {decis_total} bits")
        print(f"    Tension accuracy:   {decis_tension/decis_total*100:.1f}%")
        print(f"    Optimal accuracy:   {decis_optimal/decis_total*100:.1f}%")
        print(f"    Gap:                {(decis_optimal/decis_total - decis_tension/decis_total)*100:.1f}%")

    # Is marginal MAP a solution?
    print(f"\n  Is the marginal MAP (vote per bit) itself a solution?")
    map_is_sol = 0
    map_total = 0
    for seed in range(300):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue
        map_total += 1
        result = map_predictor(clauses, 12, solutions)
        if result and result['marginal_map_is_solution']:
            map_is_sol += 1

    print(f"    {map_is_sol}/{map_total} ({map_is_sol/map_total*100:.1f}%)")
