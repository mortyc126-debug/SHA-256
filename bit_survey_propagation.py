"""
Survey Propagation comparison.

SP (Mézard, Parisi, Zecchina, 2002) gets ~90% at threshold.
Our tension gets ~71%, v4 gets ~79%.

KEY DIFFERENCE: SP doesn't compute marginal probability.
It computes "surveys" — probability that a variable is:
  - frozen to 1 (in most solution clusters)
  - frozen to 0
  - free (varies across clusters)

This captures SOLUTION SPACE structure, not just clause structure.
Our tension is blind to solution space (Law L11).
SP is not blind — that's why it's better.

Let's implement SP and understand WHERE the extra info comes from.
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


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None: fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                s = False; rem = []; vs = None
                for v, si in clause:
                    if v in fixed:
                        if (si==1 and fixed[v]==1) or (si==-1 and fixed[v]==0):
                            s = True; break
                    else: rem.append((v,si));
                    if v == var: vs = si
                if s or vs is None: continue
                oh = 0.0
                for v, si in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if si == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# SURVEY PROPAGATION (simplified implementation)
# ============================================================

def survey_propagation(clauses, n, max_iter=100, damping=0.3, epsilon=1e-6):
    """
    SP computes for each variable:
      π+(i) = probability that i is frozen to TRUE in a random cluster
      π-(i) = probability that i is frozen to FALSE
      π0(i) = probability that i is FREE

    Messages: η(a→i) = "survey" from clause a to variable i
      = probability that clause a is "unsatisfied warning" for variable i
      = clause a NEEDS variable i (all other literals are frozen wrong)

    Update:
      η(a→i) = Π_{j∈a, j≠i} [π_contradicting(j)]
      where π_contradicting(j) = prob j is frozen to the value that
      does NOT satisfy literal j in clause a.

    Then:
      π+(i) ∝ Π_{a: i positive} (1 - η(a→i)) × [1 - Π_{a: i negative} (1-η(a→i))]
      (and similar for π-)
    """
    # Build factor graph
    var_clauses = {v: [] for v in range(n)}  # clauses containing var
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            var_clauses[v].append((ci, s))

    clause_vars = []  # variables in each clause
    for ci, clause in enumerate(clauses):
        clause_vars.append([(v, s) for v, s in clause])

    # Initialize surveys randomly
    eta = {}  # eta[(clause_idx, var)] = survey value
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            eta[(ci, v)] = random.random() * 0.1

    # Iterate
    for iteration in range(max_iter):
        max_change = 0

        for ci in range(len(clauses)):
            for v_target, s_target in clause_vars[ci]:
                # Compute new eta(ci → v_target)
                product = 1.0
                for v_other, s_other in clause_vars[ci]:
                    if v_other == v_target:
                        continue
                    # π_contradicting(v_other) for clause ci:
                    # If literal is positive (s=+1), contradiction = v_other frozen to 0
                    # If literal is negative (s=-1), contradiction = v_other frozen to 1
                    # We need π_frozen_wrong(v_other)

                    # Compute π+, π-, π0 for v_other (using current surveys)
                    pos_prod = 1.0
                    neg_prod = 1.0
                    for (cj, sj) in var_clauses[v_other]:
                        if cj == ci:
                            continue
                        e = eta.get((cj, v_other), 0)
                        if sj == 1:  # v_other appears positive in clause cj
                            neg_prod *= (1 - e)
                        else:  # v_other appears negative
                            pos_prod *= (1 - e)

                    # Unnormalized:
                    # π+(v) ∝ (1 - neg_prod) * pos_prod  [positive clauses don't need it, negative need it]
                    # Actually, SP formulas are:
                    # π+(i) ∝ Π_{a∈V+(i)} (1-η(a→i)) - Π_{all a∈V(i)} (1-η(a→i))
                    # where V+(i) = clauses where i appears positive

                    # Simplified: π_contradicting for s_other
                    if s_other == 1:
                        # literal is +v_other, contradiction = v_other frozen to 0
                        pi_contradict = 1 - pos_prod  # prob v_other frozen to 0
                        # (clauses wanting v_other=1 are unsatisfied)
                    else:
                        # literal is ¬v_other, contradiction = v_other frozen to 1
                        pi_contradict = 1 - neg_prod

                    # Normalize roughly
                    total = (1-pos_prod) + (1-neg_prod) + pos_prod * neg_prod
                    if total > 0:
                        pi_contradict = pi_contradict / total
                    else:
                        pi_contradict = 0.0

                    product *= max(pi_contradict, 1e-10)

                new_eta = product
                new_eta = max(0, min(1, new_eta))

                old = eta.get((ci, v_target), 0)
                eta[(ci, v_target)] = damping * old + (1-damping) * new_eta
                max_change = max(max_change, abs(eta[(ci, v_target)] - old))

        if max_change < epsilon:
            break

    # Compute final biases
    biases = {}
    for v in range(n):
        pos_prod = 1.0
        neg_prod = 1.0
        for (ci, s) in var_clauses[v]:
            e = eta.get((ci, v), 0)
            if s == 1:
                neg_prod *= (1 - e)
            else:
                pos_prod *= (1 - e)

        pi_plus = max((1 - neg_prod) * pos_prod, 1e-10)  # frozen to 1
        pi_minus = max((1 - pos_prod) * neg_prod, 1e-10)  # frozen to 0
        pi_zero = max(pos_prod * neg_prod, 1e-10)  # free

        total = pi_plus + pi_minus + pi_zero
        pi_plus /= total
        pi_minus /= total
        pi_zero /= total

        biases[v] = {
            'pi_plus': pi_plus,
            'pi_minus': pi_minus,
            'pi_zero': pi_zero,
            'direction': 1 if pi_plus > pi_minus else 0,
            'confidence': abs(pi_plus - pi_minus),
            'freedom': pi_zero,
        }

    return biases


# ============================================================
# COMPARISON: SP vs tension vs v4 vs optimal
# ============================================================

def compare_all(n=12, ratio=4.27, n_trials=200):
    results = {
        'tension': {'correct': 0, 'total': 0},
        'v4': {'correct': 0, 'total': 0},
        'sp': {'correct': 0, 'total': 0},
        'optimal': {'acc_sum': 0.0, 'total': 0},
    }

    # Also track: WHERE does SP beat tension?
    sp_wins = []  # properties of bits where SP correct, tension wrong
    tension_wins = []  # properties where tension correct, SP wrong

    for seed in range(n_trials):
        clauses = random_3sat(n, int(ratio*n), seed=seed+8000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Tension
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # V4
        v4_t = tension_v4(clauses, n, {}, 10)

        # SP
        sp_biases = survey_propagation(clauses, n)

        for var in range(n):
            actual = correct_val[var]
            optimal_acc = max(prob_1[var], 1 - prob_1[var])

            t_pred = 1 if tensions[var] >= 0 else 0
            v4_pred = 1 if v4_t.get(var, 0) >= 0 else 0
            sp_pred = sp_biases[var]['direction']

            results['tension']['total'] += 1
            results['v4']['total'] += 1
            results['sp']['total'] += 1
            results['optimal']['total'] += 1

            if t_pred == actual: results['tension']['correct'] += 1
            if v4_pred == actual: results['v4']['correct'] += 1
            if sp_pred == actual: results['sp']['correct'] += 1
            results['optimal']['acc_sum'] += optimal_acc

            # Where SP beats tension
            if sp_pred == actual and t_pred != actual:
                sp_wins.append({
                    'freedom': sp_biases[var]['freedom'],
                    'sp_confidence': sp_biases[var]['confidence'],
                    'tension': abs(tensions[var]),
                })
            elif t_pred == actual and sp_pred != actual:
                tension_wins.append({
                    'freedom': sp_biases[var]['freedom'],
                    'sp_confidence': sp_biases[var]['confidence'],
                    'tension': abs(tensions[var]),
                })

    return results, sp_wins, tension_wins


# ============================================================
# WHAT DOES SP SEE THAT TENSION DOESN'T?
# ============================================================

def sp_unique_info(n=12, ratio=4.27, n_trials=100):
    """
    SP computes pi_zero (freedom) — how often a bit is FREE across clusters.
    Tension has no equivalent. Is pi_zero the missing information?
    """
    freedom_correct = []
    freedom_gap = []

    for seed in range(n_trials):
        clauses = random_3sat(n, int(ratio*n), seed=seed+8000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        v4_t = tension_v4(clauses, n, {}, 10)
        sp_biases = survey_propagation(clauses, n)

        for var in range(n):
            v4_pred = 1 if v4_t.get(var, 0) >= 0 else 0
            actual = correct_val[var]
            optimal = max(prob_1[var], 1 - prob_1[var])

            if v4_pred == actual:
                freedom_correct.append(sp_biases[var]['freedom'])
            elif optimal > 0.6:
                freedom_gap.append(sp_biases[var]['freedom'])

    return freedom_correct, freedom_gap


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("SURVEY PROPAGATION vs BIT MECHANICS")
    print("=" * 70)

    # Comparison across ratios
    for ratio in [3.0, 3.5, 4.0, 4.27]:
        results, sp_wins, t_wins = compare_all(12, ratio, 150)

        t_acc = results['tension']['correct']/results['tension']['total']*100
        v4_acc = results['v4']['correct']/results['v4']['total']*100
        sp_acc = results['sp']['correct']/results['sp']['total']*100
        opt_acc = results['optimal']['acc_sum']/results['optimal']['total']*100

        print(f"\n  ratio={ratio}: tension={t_acc:.1f}%, v4={v4_acc:.1f}%, "
              f"SP={sp_acc:.1f}%, optimal={opt_acc:.1f}%")

        if sp_wins:
            mean = lambda lst: sum(lst)/len(lst)
            print(f"    SP wins over tension: {len(sp_wins)} bits")
            print(f"      avg SP confidence: {mean([w['sp_confidence'] for w in sp_wins]):.3f}")
            print(f"      avg tension:       {mean([w['tension'] for w in sp_wins]):.3f}")
            print(f"      avg freedom:       {mean([w['freedom'] for w in sp_wins]):.3f}")
        if t_wins:
            print(f"    Tension wins over SP: {len(t_wins)} bits")
            print(f"      avg SP confidence: {mean([w['sp_confidence'] for w in t_wins]):.3f}")
            print(f"      avg tension:       {mean([w['tension'] for w in t_wins]):.3f}")
            print(f"      avg freedom:       {mean([w['freedom'] for w in t_wins]):.3f}")

    # SP unique info: freedom
    print("\n" + "=" * 70)
    print("SP's UNIQUE INFO: Does 'freedom' predict the gap?")
    print("=" * 70)

    freedom_correct, freedom_gap = sp_unique_info()
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  v4-correct bits: avg freedom = {mean(freedom_correct):.4f}")
    print(f"  v4-gap bits:     avg freedom = {mean(freedom_gap):.4f}")

    if mean(freedom_correct) > 0:
        ratio = mean(freedom_gap) / mean(freedom_correct)
        print(f"  Ratio: {ratio:.2f}")
        if ratio > 1.2 or ratio < 0.83:
            print(f"  → SIGNIFICANT: freedom discriminates gap bits!")
        else:
            print(f"  → Not significant")

    # SP solver
    print("\n" + "=" * 70)
    print("SP-GUIDED SOLVER: crystallize by SP confidence")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        sp_solved = 0
        v4_solved = 0
        total = 0

        for seed in range(150):
            clauses = random_3sat(12, int(ratio*12), seed=seed+8000)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue
            total += 1

            # SP solver
            sp_biases = survey_propagation(clauses, 12)
            fixed = {}
            order = sorted(range(12), key=lambda v: -sp_biases[v]['confidence'])
            for var in order:
                fixed[var] = sp_biases[var]['direction']
            assignment = [fixed.get(v, 0) for v in range(12)]
            if evaluate(clauses, assignment) == len(clauses):
                sp_solved += 1

            # V4 solver
            v4_t = tension_v4(clauses, 12, {}, 10)
            fixed2 = {}
            order2 = sorted(range(12), key=lambda v: -abs(v4_t.get(v, 0)))
            for var in order2:
                sigma = bit_tension(clauses, 12, var, fixed2)
                fixed2[var] = 1 if sigma >= 0 else 0
            assignment2 = [fixed2.get(v, 0) for v in range(12)]
            if evaluate(clauses, assignment2) == len(clauses):
                v4_solved += 1

        print(f"  ratio={ratio}: SP={sp_solved}/{total} ({sp_solved/total*100:.1f}%), "
              f"v4={v4_solved}/{total} ({v4_solved/total*100:.1f}%)")
