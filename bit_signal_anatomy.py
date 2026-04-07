"""
Signal Anatomy — WHY 65/35? What determines whether a bit gets
the right or wrong signal? Can we control it?

Key questions:
1. Which bits get wrong signals? What's special about them?
2. Can we PREDICT which signals are wrong?
3. Can we FLIP the odds by changing strategy?
4. Is 65/35 a fundamental constant or tunable?
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
# EXPERIMENT 1: Profile of right vs wrong bits
# ============================================================

def profile_right_vs_wrong(clauses, n, solutions):
    """
    For each bit: is its tension pointing RIGHT or WRONG?
    Measure every property we know and compare the two groups.
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    right_bits = []
    wrong_bits = []

    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0
        predicted = 1 if sigma >= 0 else 0
        is_right = predicted == actual

        # Measure properties
        abs_sigma = abs(sigma)

        # Degree
        degree = sum(1 for clause in clauses
                     if any(v == var for v, s in clause))

        # Frustration
        votes = []
        for clause in clauses:
            for v, s in clause:
                if v == var:
                    votes.append(s)
        frustration = 1.0 - abs(sum(votes) / len(votes)) if votes else 0

        # Number of neighbors
        neighbors = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var:
                        neighbors.add(v)

        # Neighbor agreement: how many neighbors have tension in same direction
        same_dir = 0
        opp_dir = 0
        for nb in neighbors:
            nb_sigma = bit_tension(clauses, n, nb)
            if sigma * nb_sigma > 0:
                same_dir += 1
            elif sigma * nb_sigma < 0:
                opp_dir += 1

        # Contradiction score: how many conflicting clause-pairs
        pos_clauses = 0
        neg_clauses = 0
        for clause in clauses:
            for v, s in clause:
                if v == var:
                    if s == 1:
                        pos_clauses += 1
                    else:
                        neg_clauses += 1

        entry = {
            'var': var,
            'sigma': sigma,
            'abs_sigma': abs_sigma,
            'degree': degree,
            'frustration': frustration,
            'n_neighbors': len(neighbors),
            'same_dir_neighbors': same_dir,
            'opp_dir_neighbors': opp_dir,
            'neighbor_agreement': same_dir / (same_dir + opp_dir) if (same_dir + opp_dir) > 0 else 0.5,
            'pos_clauses': pos_clauses,
            'neg_clauses': neg_clauses,
            'minority_ratio': min(pos_clauses, neg_clauses) / max(pos_clauses, neg_clauses) if max(pos_clauses, neg_clauses) > 0 else 1.0,
        }

        if is_right:
            right_bits.append(entry)
        else:
            wrong_bits.append(entry)

    return right_bits, wrong_bits


def compare_groups(right_bits, wrong_bits, label):
    mean = lambda lst: sum(lst) / len(lst) if lst else 0

    print(f"\n  {label}: {len(right_bits)} right, {len(wrong_bits)} wrong")
    print(f"  {'property':>20} | {'RIGHT':>8} | {'WRONG':>8} | {'diff':>8} | significant?")
    print("  " + "-" * 65)

    properties = ['abs_sigma', 'degree', 'frustration', 'n_neighbors',
                   'neighbor_agreement', 'minority_ratio']

    for prop in properties:
        r_vals = [b[prop] for b in right_bits]
        w_vals = [b[prop] for b in wrong_bits]

        r_mean = mean(r_vals)
        w_mean = mean(w_vals)
        diff = r_mean - w_mean

        # Is difference significant?
        if r_mean + w_mean > 0:
            relative = abs(diff) / ((r_mean + w_mean) / 2) * 100
        else:
            relative = 0

        sig = "**YES**" if relative > 15 else ("maybe" if relative > 5 else "no")

        print(f"  {prop:>20} | {r_mean:>8.3f} | {w_mean:>8.3f} | "
              f"{diff:>+8.3f} | {sig}")


# ============================================================
# EXPERIMENT 2: Can we PREDICT which signals are wrong?
# ============================================================

def predict_wrong_signals(clauses, n, solutions, n_trials=100):
    """
    Try different "confidence filters":
    - Only trust bits with |σ| > threshold
    - Only trust bits with low frustration
    - Only trust bits where neighbors agree
    - Combination

    For each: what's the accuracy on trusted bits?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    results = {}

    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0
        predicted = 1 if sigma >= 0 else 0
        is_right = predicted == actual

        # Properties for filtering
        abs_sigma = abs(sigma)

        votes = []
        for clause in clauses:
            for v, s in clause:
                if v == var:
                    votes.append(s)
        frustration = 1.0 - abs(sum(votes) / len(votes)) if votes else 0

        neighbors = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var:
                        neighbors.add(v)

        same_dir = sum(1 for nb in neighbors
                       if bit_tension(clauses, n, nb) * sigma > 0)
        agreement = same_dir / len(neighbors) if neighbors else 0.5

        # Test filters
        for name, condition in [
            ('all', True),
            ('|σ|>0.3', abs_sigma > 0.3),
            ('|σ|>0.5', abs_sigma > 0.5),
            ('frust<0.7', frustration < 0.7),
            ('frust<0.5', frustration < 0.5),
            ('agree>0.6', agreement > 0.6),
            ('agree>0.7', agreement > 0.7),
            ('|σ|>0.3 AND agree>0.6', abs_sigma > 0.3 and agreement > 0.6),
            ('|σ|>0.3 AND frust<0.7', abs_sigma > 0.3 and frustration < 0.7),
            ('combo: all 3', abs_sigma > 0.3 and frustration < 0.7 and agreement > 0.6),
        ]:
            if name not in results:
                results[name] = {'total': 0, 'right': 0}
            if condition:
                results[name]['total'] += 1
                if is_right:
                    results[name]['right'] += 1

    return results


# ============================================================
# EXPERIMENT 3: Can we change the 65/35 ratio?
# ============================================================

def try_alternative_tensions(clauses, n, solutions):
    """
    Instead of standard tension (clause-weighted),
    try different formulas and see which gives better signal.
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    formulas = {}

    for var in range(n):
        actual = 1 if prob_1[var] > 0.5 else 0

        # Formula 1: Standard tension
        sigma_std = bit_tension(clauses, n, var)
        pred_std = 1 if sigma_std >= 0 else 0

        # Formula 2: Unweighted vote (just count pos vs neg appearances)
        pos = sum(1 for clause in clauses for v, s in clause if v == var and s == 1)
        neg = sum(1 for clause in clauses for v, s in clause if v == var and s == -1)
        sigma_vote = pos - neg
        pred_vote = 1 if sigma_vote >= 0 else 0

        # Formula 3: Neighbor-weighted tension
        # Weight each clause by how "decided" the other literals are
        sigma_nw = 0
        for clause in clauses:
            for v, s in clause:
                if v == var:
                    # Weight = average |σ| of other vars in clause
                    others = [bit_tension(clauses, n, ov) for ov, os in clause if ov != var]
                    weight = sum(abs(o) for o in others) / len(others) if others else 0.5
                    sigma_nw += s * weight
        pred_nw = 1 if sigma_nw >= 0 else 0

        # Formula 4: Squared tension (amplify strong signals)
        sigma_sq = 0
        for clause in clauses:
            for v, s in clause:
                if v == var:
                    others = [bit_tension(clauses, n, ov) for ov, os in clause if ov != var]
                    certainty = 1.0
                    for o in others:
                        certainty *= (1 - abs(o))  # how uncertain others are
                    # Higher certainty of others = this clause needs US more
                    sigma_sq += s * certainty
        pred_sq = 1 if sigma_sq >= 0 else 0

        # Formula 5: Majority of neighbors
        neighbors = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var:
                        neighbors.add(v)
        nb_tensions = [bit_tension(clauses, n, nb) for nb in neighbors]
        # If my neighbors mostly want 1, maybe I should want 1 too? (or opposite?)
        nb_majority = sum(1 if t > 0 else -1 for t in nb_tensions)
        pred_nb = 1 if nb_majority >= 0 else 0

        # Formula 6: Anti-majority (opposite of neighbors — contrarian)
        pred_anti = 1 - pred_nb

        for name, pred in [
            ('standard', pred_std),
            ('unweighted_vote', pred_vote),
            ('neighbor_weighted', pred_nw),
            ('uncertainty_weighted', pred_sq),
            ('neighbor_majority', pred_nb),
            ('contrarian', pred_anti),
        ]:
            if name not in formulas:
                formulas[name] = {'right': 0, 'total': 0}
            formulas[name]['total'] += 1
            if pred == actual:
                formulas[name]['right'] += 1

    return formulas


# ============================================================
# EXPERIMENT 4: The 65/35 ratio across scales
# ============================================================

def signal_quality_vs_n(n_range=[8, 10, 12, 14, 16], ratio=4.27):
    """Is 65/35 constant or does it change with n?"""
    results = {}
    for n in n_range:
        correct = 0
        total = 0

        for seed in range(200):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            if n <= 14:
                solutions = find_solutions(clauses, n)
            else:
                solutions = None

            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                actual = 1 if prob_1[var] > 0.5 else 0
                predicted = 1 if sigma >= 0 else 0
                if predicted == actual:
                    correct += 1
                total += 1

        results[n] = correct / total if total > 0 else 0

    return results


# ============================================================
# EXPERIMENT 5: Signal quality for bits that MATTER
# ============================================================

def signal_quality_by_entropy(clauses, n, solutions):
    """
    Not all bits matter equally. Bits with P(=1) near 0.5
    are ambiguous — getting them wrong might be OK.
    Bits with P(=1) near 0 or 1 are decisive — must get them right.

    Does signal quality differ for decisive vs ambiguous bits?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    decisive_right = 0
    decisive_total = 0
    ambiguous_right = 0
    ambiguous_total = 0

    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        actual = 1 if prob_1[var] > 0.5 else 0
        predicted = 1 if sigma >= 0 else 0
        is_right = predicted == actual

        # How decisive is this bit?
        decisiveness = abs(prob_1[var] - 0.5)  # 0 = ambiguous, 0.5 = fully determined

        if decisiveness > 0.3:  # decisive
            decisive_total += 1
            if is_right:
                decisive_right += 1
        else:  # ambiguous
            ambiguous_total += 1
            if is_right:
                ambiguous_right += 1

    return {
        'decisive_right': decisive_right,
        'decisive_total': decisive_total,
        'ambiguous_right': ambiguous_right,
        'ambiguous_total': ambiguous_total,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    # ---- Experiment 1 ----
    print("=" * 70)
    print("EXPERIMENT 1: What distinguishes right from wrong bits?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        all_right = []
        all_wrong = []
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            result = profile_right_vs_wrong(clauses, 12, solutions)
            if result:
                all_right.extend(result[0])
                all_wrong.extend(result[1])
        compare_groups(all_right, all_wrong, label)

    # ---- Experiment 2 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Can we filter out wrong signals?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        combined = None
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            result = predict_wrong_signals(clauses, 12, solutions)
            if result:
                if combined is None:
                    combined = {k: {'total': 0, 'right': 0} for k in result}
                for k in result:
                    combined[k]['total'] += result[k]['total']
                    combined[k]['right'] += result[k]['right']

        if combined:
            print(f"\n  {label}:")
            print(f"  {'filter':>30} | {'accuracy':>8} | {'coverage':>8}")
            print("  " + "-" * 55)
            total_all = combined['all']['total']
            for name in combined:
                t = combined[name]['total']
                r = combined[name]['right']
                acc = r / t * 100 if t > 0 else 0
                cov = t / total_all * 100 if total_all > 0 else 0
                print(f"  {name:>30} | {acc:>7.1f}% | {cov:>7.1f}%")

    # ---- Experiment 3 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Alternative tension formulas")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        combined = None
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            result = try_alternative_tensions(clauses, 12, solutions)
            if result:
                if combined is None:
                    combined = {k: {'total': 0, 'right': 0} for k in result}
                for k in result:
                    combined[k]['total'] += result[k]['total']
                    combined[k]['right'] += result[k]['right']

        if combined:
            print(f"\n  {label}:")
            print(f"  {'formula':>25} | {'accuracy':>8}")
            print("  " + "-" * 40)
            for name, vals in sorted(combined.items(), key=lambda x: -x[1]['right']):
                acc = vals['right'] / vals['total'] * 100
                print(f"  {name:>25} | {acc:>7.1f}%")

    # ---- Experiment 4 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Does 65/35 change with n?")
    print("=" * 70)

    results = signal_quality_vs_n()
    print(f"\n  {'n':>4} | {'signal quality':>13}")
    print("  " + "-" * 25)
    for n_val in sorted(results.keys()):
        pct = results[n_val] * 100
        bar = "█" * int(pct) + "░" * int(100 - pct)
        print(f"  {n_val:>4} | {pct:>12.1f}% {bar[:30]}")

    # ---- Experiment 5 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 5: Signal quality for decisive vs ambiguous bits")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        totals = {'d_r': 0, 'd_t': 0, 'a_r': 0, 'a_t': 0}
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            result = signal_quality_by_entropy(clauses, 12, solutions)
            if result:
                totals['d_r'] += result['decisive_right']
                totals['d_t'] += result['decisive_total']
                totals['a_r'] += result['ambiguous_right']
                totals['a_t'] += result['ambiguous_total']

        print(f"\n  {label}:")
        if totals['d_t'] > 0:
            print(f"    Decisive bits (P near 0 or 1): "
                  f"{totals['d_r']}/{totals['d_t']} = "
                  f"{totals['d_r']/totals['d_t']*100:.1f}%")
        if totals['a_t'] > 0:
            print(f"    Ambiguous bits (P near 0.5):   "
                  f"{totals['a_r']}/{totals['a_t']} = "
                  f"{totals['a_r']/totals['a_t']*100:.1f}%")
