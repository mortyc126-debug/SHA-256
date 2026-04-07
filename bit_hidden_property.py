"""
The Hidden Property — What internal bit property explains the remaining 9%?

We've measured: tension, frustration, degree, mass, polarity, neighbors.
The v4 iterative tension captures neighbor info (+8%).
But 9% remains. It must be something INSIDE the bit's own clause structure.

Systematic search: measure EVERYTHING about how a bit participates
in clauses, and find what correlates with the gap.
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


def tension_v4_iterative(clauses, n, fixed=None, n_iter=10):
    if fixed is None:
        fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for iteration in range(n_iter):
        new_tensions = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
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
                others_help = 0.0
                for v, s in remaining:
                    if v == var:
                        continue
                    t = tensions.get(v, 0)
                    p_lit = (1 + t) / 2 if s == 1 else (1 - t) / 2
                    others_help = 1 - (1 - others_help) * (1 - p_lit)
                need = 1.0 - others_help
                if var_sign == 1:
                    push_1 += need
                else:
                    push_0 += need
            total = push_1 + push_0
            new_tensions[var] = (push_1 - push_0) / total if total > 0 else 0
        for v in tensions:
            tensions[v] = 0.5 * tensions[v] + 0.5 * new_tensions.get(v, 0)
    return tensions


# ============================================================
# MEASURE EVERYTHING WE HAVEN'T MEASURED
# ============================================================

def deep_bit_profile(clauses, n, var):
    """
    Exhaustive measurement of bit's clause structure.
    Looking for the hidden property.
    """
    # Collect all clauses containing var
    my_clauses = []
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            if v == var:
                my_clauses.append((ci, clause, s))
                break

    pos_clauses = [(ci, cl, s) for ci, cl, s in my_clauses if s == 1]
    neg_clauses = [(ci, cl, s) for ci, cl, s in my_clauses if s == -1]

    # 1. CLAUSE OVERLAP: do my clauses share variables with each other?
    clause_neighbors = []  # for each pair of my clauses, how many vars they share
    for i in range(len(my_clauses)):
        vars_i = {v for v, s in my_clauses[i][1] if v != var}
        for j in range(i + 1, len(my_clauses)):
            vars_j = {v for v, s in my_clauses[j][1] if v != var}
            shared = len(vars_i & vars_j)
            clause_neighbors.append(shared)

    clause_overlap = sum(clause_neighbors) / len(clause_neighbors) if clause_neighbors else 0

    # 2. SIGN PATTERN COMPLEXITY: are signs distributed randomly or structured?
    # Sequence of signs: [+1, -1, +1, +1, -1, ...]
    signs = [s for _, _, s in my_clauses]
    if len(signs) > 1:
        # Run-length: how many sign changes?
        changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])
        sign_complexity = changes / (len(signs) - 1)
    else:
        sign_complexity = 0

    # 3. NEIGHBOR DIVERSITY: how many UNIQUE neighbors vs total appearances?
    all_neighbors = []
    unique_neighbors = set()
    for ci, clause, s in my_clauses:
        for v, vs in clause:
            if v != var:
                all_neighbors.append(v)
                unique_neighbors.add(v)
    neighbor_diversity = len(unique_neighbors) / len(all_neighbors) if all_neighbors else 0

    # 4. CLAUSE REDUNDANCY: do multiple clauses impose the SAME constraint?
    # Two clauses are "redundant" if they share the same other variables with same signs
    clause_signatures = []
    for ci, clause, my_sign in my_clauses:
        others = tuple(sorted((v, s) for v, s in clause if v != var))
        clause_signatures.append(others)
    unique_sigs = len(set(clause_signatures))
    redundancy = 1 - unique_sigs / len(clause_signatures) if clause_signatures else 0

    # 5. POSITIVE-NEGATIVE CLAUSE INTERACTION
    # Do pos clauses and neg clauses share neighbors?
    pos_neighbors = set()
    neg_neighbors = set()
    for ci, clause, s in my_clauses:
        for v, vs in clause:
            if v != var:
                if s == 1:
                    pos_neighbors.add(v)
                else:
                    neg_neighbors.add(v)
    if pos_neighbors or neg_neighbors:
        pn_overlap = len(pos_neighbors & neg_neighbors) / len(pos_neighbors | neg_neighbors)
    else:
        pn_overlap = 0

    # 6. CLAUSE CHAIN: are my clauses linked in a chain through shared vars?
    # (cl1 shares with cl2, cl2 shares with cl3, ...)
    # Count connected components among my clauses
    adj = {i: set() for i in range(len(my_clauses))}
    for i in range(len(my_clauses)):
        vars_i = {v for v, s in my_clauses[i][1] if v != var}
        for j in range(i + 1, len(my_clauses)):
            vars_j = {v for v, s in my_clauses[j][1] if v != var}
            if vars_i & vars_j:
                adj[i].add(j)
                adj[j].add(i)

    visited = set()
    components = 0
    for node in adj:
        if node not in visited:
            components += 1
            stack = [node]
            while stack:
                curr = stack.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                for nb in adj[curr]:
                    if nb not in visited:
                        stack.append(nb)
    clause_fragmentation = components / len(my_clauses) if my_clauses else 1

    # 7. LOCAL vs GLOBAL information
    # How concentrated are my neighbors? (entropy of neighbor frequency)
    from collections import Counter
    nb_counts = Counter(all_neighbors)
    total_nb = sum(nb_counts.values())
    if total_nb > 0:
        probs = [c / total_nb for c in nb_counts.values()]
        neighbor_entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(nb_counts)) if len(nb_counts) > 1 else 1
        neighbor_concentration = 1 - neighbor_entropy / max_entropy if max_entropy > 0 else 0
    else:
        neighbor_concentration = 0

    # 8. IMPLICATION DEPTH: if I set this bit, how deep does unit propagation go?
    for test_val in [0, 1]:
        fixed = {var: test_val}
        depth = 0
        while True:
            new_forced = {}
            for clause in clauses:
                satisfied = False
                free = []
                for v, s in clause:
                    if v in fixed:
                        if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                            satisfied = True
                            break
                    else:
                        free.append((v, s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    forced_val = 1 if s == 1 else 0
                    if v not in fixed and v not in new_forced:
                        new_forced[v] = forced_val
            if not new_forced:
                break
            fixed.update(new_forced)
            depth += 1

    implication_depth = depth
    implication_count = len(fixed) - 1

    return {
        'clause_overlap': clause_overlap,
        'sign_complexity': sign_complexity,
        'neighbor_diversity': neighbor_diversity,
        'redundancy': redundancy,
        'pn_overlap': pn_overlap,
        'clause_fragmentation': clause_fragmentation,
        'neighbor_concentration': neighbor_concentration,
        'implication_depth': implication_depth,
        'implication_count': implication_count,
        'degree': len(my_clauses),
        'n_pos': len(pos_clauses),
        'n_neg': len(neg_clauses),
    }


# ============================================================
# FIND THE HIDDEN PROPERTY
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 75)
    print("SEARCHING FOR THE HIDDEN PROPERTY")
    print("What explains the remaining 9% gap?")
    print("=" * 75)

    # Collect profiles for correct, v4-gap (v4 wrong, optimal right), and both-wrong bits
    v4_correct_profiles = []
    v4_gap_profiles = []

    for seed in range(300):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        optimal = [max(p, 1 - p) for p in prob_1]

        v4_tensions = tension_v4_iterative(clauses, 12, {}, n_iter=10)

        for var in range(12):
            v4_pred = 1 if v4_tensions.get(var, 0) >= 0 else 0
            actual = correct_val[var]
            profile = deep_bit_profile(clauses, 12, var)

            if v4_pred == actual:
                v4_correct_profiles.append(profile)
            elif optimal[var] > 0.6:  # v4 wrong, but bit IS predictable
                v4_gap_profiles.append(profile)

    print(f"\n  {len(v4_correct_profiles)} v4-correct bits, "
          f"{len(v4_gap_profiles)} v4-gap bits")

    # Compare every property
    mean = lambda lst: sum(lst) / len(lst) if lst else 0

    properties = [
        'clause_overlap', 'sign_complexity', 'neighbor_diversity',
        'redundancy', 'pn_overlap', 'clause_fragmentation',
        'neighbor_concentration', 'implication_depth', 'implication_count',
        'degree',
    ]

    print(f"\n  {'property':>25} | {'v4-CORRECT':>10} | {'v4-GAP':>10} | "
          f"{'ratio':>7} | significance")
    print("  " + "-" * 75)

    significant = []
    for prop in properties:
        c_val = mean([p[prop] for p in v4_correct_profiles])
        g_val = mean([p[prop] for p in v4_gap_profiles])

        if c_val > 0.001:
            ratio = g_val / c_val
        elif g_val > 0.001:
            ratio = 999
        else:
            ratio = 1.0

        sig = ""
        if ratio > 1.5 or ratio < 0.67:
            sig = "*** STRONG ***"
            significant.append((prop, c_val, g_val, ratio))
        elif ratio > 1.2 or ratio < 0.83:
            sig = "* notable *"
            significant.append((prop, c_val, g_val, ratio))

        print(f"  {prop:>25} | {c_val:>10.4f} | {g_val:>10.4f} | "
              f"{ratio:>7.2f} | {sig}")

    if significant:
        print(f"\n  SIGNIFICANT PROPERTIES:")
        for prop, c, g, r in significant:
            direction = "LOWER in gap" if r < 1 else "HIGHER in gap"
            print(f"    {prop}: {direction} (ratio={r:.2f})")
            print(f"      correct={c:.4f}, gap={g:.4f}")

    # Can we use the best property to improve prediction?
    print("\n" + "=" * 75)
    print("TEST: Can the hidden property improve prediction?")
    print("=" * 75)

    if significant:
        best_prop = significant[0][0]
        print(f"\n  Using: {best_prop}")

        # Split bits by this property and measure accuracy
        for threshold_pct in [25, 50, 75]:
            all_vals = [p[best_prop] for p in v4_correct_profiles + v4_gap_profiles]
            all_vals.sort()
            threshold = all_vals[len(all_vals) * threshold_pct // 100]

            low_correct = sum(1 for p in v4_correct_profiles if p[best_prop] <= threshold)
            low_total = sum(1 for p in v4_correct_profiles + v4_gap_profiles
                          if p[best_prop] <= threshold)
            high_correct = sum(1 for p in v4_correct_profiles if p[best_prop] > threshold)
            high_total = sum(1 for p in v4_correct_profiles + v4_gap_profiles
                           if p[best_prop] > threshold)

            low_acc = low_correct / low_total * 100 if low_total > 0 else 0
            high_acc = high_correct / high_total * 100 if high_total > 0 else 0

            print(f"    threshold={threshold_pct}%ile ({threshold:.3f}):")
            print(f"      low {best_prop}: {low_correct}/{low_total} = {low_acc:.1f}%")
            print(f"      high {best_prop}: {high_correct}/{high_total} = {high_acc:.1f}%")
