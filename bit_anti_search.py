"""
ANTI-SEARCH: Find things that are RELIABLY WRONG.

Reliably wrong = more useful than randomly right.
If something is 30% accurate → inversion gives 70%.
If 20% → inversion gives 80%.
If 10% → inversion gives 90%.

We need to find methods/signals that are STRONGLY anti-correlated
with the correct answer. Then INVERT.

Search across ALL our knowledge:
- Clause sign balance (32.9% → inverted 67.1%)
- Signed graph (27.5% → inverted 72.5%)
- Clause paths consistent (24.4% → inverted 75.6%)
- What else?
"""

import random
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
    if fixed is None: fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                    sat = True; break
            else: rem.append((v,s))
        if sat: continue
        for v, s in rem:
            if v == var:
                w = 1.0/max(1,len(rem))
                if s==1: p1 += w
                else: p0 += w
    total = p1+p0
    return (p1-p0)/total if total > 0 else 0.0


# ============================================================
# EXHAUSTIVE ANTI-SIGNAL SEARCH
# ============================================================

def anti_search():
    print("=" * 70)
    print("ANTI-SIGNAL SEARCH: What is RELIABLY WRONG?")
    print("=" * 70)

    random.seed(42); n = 12

    # Collect ALL signals and their accuracy
    signals = {
        # Per-bit signals
        'tension': [],
        'anti_tension': [],
        'low_σ_only': [],          # predict ONLY for |σ| < 0.15
        'neighbor_majority': [],    # majority of neighbor tensions
        'anti_neighbor_maj': [],    # OPPOSITE of neighbor majority
        'weakest_clause': [],       # direction of weakest (most critical) clause
        'anti_weakest': [],
        'minority_sign': [],        # minority clause sign direction
        'most_connected_nb': [],    # follow the highest-degree neighbor
        'anti_most_connected': [],
        'clause_need_min': [],      # direction of clause that needs me LEAST
        'anti_clause_need': [],
    }

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Neighbor info
        neighbors = {}
        for var in range(n):
            nbs = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: nbs.add(v)
            neighbors[var] = nbs

        for var in range(n):
            actual = correct_val[var]
            sigma = tensions[var]

            # Standard tension
            pred = 1 if sigma >= 0 else 0
            signals['tension'].append(1 if pred == actual else 0)
            signals['anti_tension'].append(1 if (1-pred) == actual else 0)

            # Only for low-σ bits
            if abs(sigma) < 0.15:
                signals['low_σ_only'].append(1 if pred == actual else 0)

            # Neighbor majority
            nbs = neighbors[var]
            if nbs:
                nb_pos = sum(1 for nb in nbs if tensions[nb] > 0)
                nb_maj = 1 if nb_pos > len(nbs)/2 else 0
                signals['neighbor_majority'].append(1 if nb_maj == actual else 0)
                signals['anti_neighbor_maj'].append(1 if (1-nb_maj) == actual else 0)

                # Most connected neighbor
                nb_degrees = {nb: sum(1 for cl in clauses if any(v==nb for v,s in cl))
                             for nb in nbs}
                most_conn = max(nbs, key=lambda nb: nb_degrees[nb])
                mc_pred = 1 if tensions[most_conn] >= 0 else 0
                signals['most_connected_nb'].append(1 if mc_pred == actual else 0)
                signals['anti_most_connected'].append(1 if (1-mc_pred) == actual else 0)

            # Weakest clause (clause with least satisfied literals)
            weakest_sign = 0; min_sat = 999
            for clause in clauses:
                if not any(v == var for v, s in clause): continue
                n_sat = 0
                my_sign = 0
                for v, s in clause:
                    if v == var: my_sign = s
                    else:
                        if (s==1 and tensions[v] > 0) or (s==-1 and tensions[v] < 0):
                            n_sat += 1
                if n_sat < min_sat:
                    min_sat = n_sat
                    weakest_sign = my_sign

            w_pred = 1 if weakest_sign >= 0 else 0
            signals['weakest_clause'].append(1 if w_pred == actual else 0)
            signals['anti_weakest'].append(1 if (1-w_pred) == actual else 0)

            # Minority sign direction
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            minority_pred = 1 if pos < neg else 0  # MINORITY, not majority
            signals['minority_sign'].append(1 if minority_pred == actual else 0)

            # Clause that needs me LEAST
            max_others_help = -1; least_need_sign = 0
            for clause in clauses:
                if not any(v == var for v, s in clause): continue
                others_help = 0; my_s = 0
                for v, s in clause:
                    if v == var: my_s = s
                    else:
                        if (s==1 and tensions[v] > 0) or (s==-1 and tensions[v] < 0):
                            others_help += 1
                if others_help > max_others_help:
                    max_others_help = others_help
                    least_need_sign = my_s

            ln_pred = 1 if least_need_sign >= 0 else 0
            signals['clause_need_min'].append(1 if ln_pred == actual else 0)
            signals['anti_clause_need'].append(1 if (1-ln_pred) == actual else 0)

    # Results: sorted by distance from 50%
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  {'signal':>25} | {'accuracy':>8} | {'inverted':>8} | {'n':>6} | {'useful?':>10}")
    print("  " + "-" * 70)

    ranked = []
    for name, vals in signals.items():
        if not vals: continue
        acc = mean(vals) * 100
        inv_acc = (1 - mean(vals)) * 100
        best = max(acc, inv_acc)
        dist_from_50 = abs(acc - 50)
        ranked.append((name, acc, inv_acc, len(vals), dist_from_50))

    ranked.sort(key=lambda x: -x[4])

    for name, acc, inv_acc, n_vals, dist in ranked:
        useful = "★★★" if dist > 25 else ("★★" if dist > 15 else ("★" if dist > 5 else ""))
        direction = "as-is" if acc > inv_acc else "INVERT"
        print(f"  {name:>25} | {acc:>7.1f}% | {inv_acc:>7.1f}% | {n_vals:>6} | {useful} {direction}")


# ============================================================
# COMBINE BEST ANTI-SIGNALS WITH TENSION
# ============================================================

def combine_anti():
    print("\n" + "=" * 70)
    print("COMBINING: Best anti-signals (inverted) + tension")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'tension': 0, 'anti_minority': 0, 'anti_weakest': 0,
               'tension+anti_minority': 0, 'tension+anti_weakest': 0,
               'all_combined': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            results['total'] += 1
            actual = correct_val[var]
            sigma = tensions[var]

            # Tension
            t_pred = 1 if sigma >= 0 else 0
            if t_pred == actual: results['tension'] += 1

            # Anti-minority: minority sign → INVERT = majority = tension (same!)
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            minority_pred = 1 if pos < neg else 0
            anti_min = 1 - minority_pred  # inverted minority = majority = tension
            if anti_min == actual: results['anti_minority'] += 1

            # Anti-weakest clause
            weakest_sign = 0; min_sat = 999
            for clause in clauses:
                if not any(v == var for v, s in clause): continue
                n_sat = 0; my_s = 0
                for v, s in clause:
                    if v == var: my_s = s
                    else:
                        if (s==1 and tensions[v] > 0) or (s==-1 and tensions[v] < 0):
                            n_sat += 1
                if n_sat < min_sat:
                    min_sat = n_sat; weakest_sign = my_s

            anti_w = 1 - (1 if weakest_sign >= 0 else 0)
            if anti_w == actual: results['anti_weakest'] += 1

            # Tension + anti-minority (same as tension)
            if t_pred == actual: results['tension+anti_minority'] += 1

            # Tension + anti-weakest
            combined = sigma * abs(sigma) + (1 if anti_w == 1 else -1) * 0.3
            comb_pred = 1 if combined >= 0 else 0
            if comb_pred == actual: results['tension+anti_weakest'] += 1

            # All combined
            score = sigma * abs(sigma)  # tension weighted by confidence
            # Add anti-weakest
            score += (1 if anti_w == 1 else -1) * 0.2
            # Add anti-neighbor-majority
            nbs = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: nbs.add(v)
            if nbs:
                nb_pos = sum(1 for nb in nbs if tensions[nb] > 0)
                anti_nb = 1 if nb_pos <= len(nbs)/2 else 0
                score += (1 if anti_nb == 1 else -1) * 0.15

            all_pred = 1 if score >= 0 else 0
            if all_pred == actual: results['all_combined'] += 1

    t = results['total']
    print(f"\n  {'method':>25} | {'accuracy':>8}")
    print("  " + "-" * 40)
    for name in sorted(results.keys(), key=lambda k: -results.get(k, 0)):
        if name == 'total': continue
        print(f"  {name:>25} | {results[name]/t*100:>7.1f}%")


if __name__ == "__main__":
    anti_search()
    combine_anti()
