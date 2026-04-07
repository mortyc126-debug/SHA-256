"""
WEAK VALUES FOR SAT BITS

TSVF: weak value = <future| A |past> / <future|past>
= expectation of observable A between two boundary conditions.

In SAT:
|past> = clause structure (what we know)
|future> = solution (what we seek)
A = bit value operator

Weak value of bit i = <solution| bit_i |clauses> / <solution|clauses>

We can't compute this directly (need solution).
But: can we APPROXIMATE it from clause structure alone?

KEY IDEA: In TSVF, weak values can be ANOMALOUS —
outside the normal range [0,1]. These anomalous values
carry the most information about the system.

In SAT: are there bits whose "clause tension" is anomalously
strong or anomalously weak? Do anomalous bits carry extra info?
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


# ============================================================
# 1. COMPUTE "WEAK VALUE" for each bit
# ============================================================

def weak_value_sat(clauses, n, var, solutions):
    """
    Weak value = <future| bit |past> / <future|past>

    Approximation:
    |past> = tension-guided state (what clauses suggest)
    |future> = solution (what's actually correct)

    "Weak value" = bit's value WEIGHTED by how well the
    tension-state OVERLAPS with solutions.

    For each solution: overlap = how many tension-predictions match.
    Weight solution by overlap.
    Weak value = weighted average of bit's value across solutions.
    """
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
    tension_pred = [1 if tensions[v] >= 0 else 0 for v in range(n)]

    # Overlap of tension prediction with each solution
    weighted_sum = 0.0
    weight_total = 0.0

    for sol in solutions:
        overlap = sum(1 for v in range(n) if tension_pred[v] == sol[v]) / n
        # Weight: overlap^power (amplify high-overlap solutions)
        weight = overlap ** 4  # strong amplification
        weighted_sum += sol[var] * weight
        weight_total += weight

    if weight_total > 0:
        wv = weighted_sum / weight_total
    else:
        wv = 0.5

    return wv


def test_weak_values():
    print("=" * 70)
    print("1. WEAK VALUES: Tension-solution overlap weighting")
    print("=" * 70)

    random.seed(42); n = 12

    wv_correct = 0; tension_correct = 0; total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Standard tension
            if (1 if tensions[var] >= 0 else 0) == actual:
                tension_correct += 1

            # Weak value
            wv = weak_value_sat(clauses, n, var, solutions)
            if (1 if wv > 0.5 else 0) == actual:
                wv_correct += 1

    print(f"\n  Tension:     {tension_correct/total*100:.1f}%")
    print(f"  Weak value:  {wv_correct/total*100:.1f}%")


# ============================================================
# 2. ANOMALOUS BITS: where weak value ≠ tension
# ============================================================

def anomalous_bits():
    """
    In TSVF: anomalous weak values (outside [0,1]) carry extra info.
    In SAT: bits where weak_value DISAGREES with tension.

    These are bits where solutions that MATCH tension overall
    give a DIFFERENT answer for THIS specific bit.
    = tension is right on average but wrong for this bit.
    = the bit's "true" value fights against the global trend.
    """
    print("\n" + "=" * 70)
    print("2. ANOMALOUS BITS: Where weak value disagrees with tension")
    print("=" * 70)

    random.seed(42); n = 12

    anomalous_correct = 0; anomalous_total = 0
    normal_correct = 0; normal_total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            actual = correct_val[var]
            t_pred = 1 if tensions[var] >= 0 else 0
            wv = weak_value_sat(clauses, n, var, solutions)
            wv_pred = 1 if wv > 0.5 else 0

            if t_pred != wv_pred:
                # ANOMALOUS: tension and weak value disagree
                anomalous_total += 1
                if wv_pred == actual:
                    anomalous_correct += 1
            else:
                # Normal: they agree
                normal_total += 1
                if t_pred == actual:
                    normal_correct += 1

    if anomalous_total > 0:
        print(f"\n  Anomalous bits (tension ≠ weak value): {anomalous_total}")
        print(f"    Weak value correct: {anomalous_correct/anomalous_total*100:.1f}%")
        print(f"    Tension correct:    {(anomalous_total-anomalous_correct)/anomalous_total*100:.1f}%")
    if normal_total > 0:
        print(f"\n  Normal bits (tension = weak value): {normal_total}")
        print(f"    Both correct: {normal_correct/normal_total*100:.1f}%")


# ============================================================
# 3. SELF-CONSISTENT WEAK VALUE (no solutions needed)
# ============================================================

def self_consistent_weak():
    """
    Can we compute weak values WITHOUT solutions?

    Idea: use MULTIPLE CRYSTALLIZATIONS as "approximate futures."
    Each successful crystallization = one "solution."
    Weight by overlap with tension = weak value.

    This is COMPUTABLE without knowing real solutions!
    """
    print("\n" + "=" * 70)
    print("3. SELF-CONSISTENT WEAK VALUE (no solutions needed)")
    print("=" * 70)

    random.seed(42); n = 12

    tension_correct = 0; scwv_correct = 0; total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        tension_pred = [1 if tensions[v] >= 0 else 0 for v in range(n)]

        # Generate approximate "futures" through noisy crystallization
        futures = []
        for run in range(25):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(tensions[v]) + random.gauss(0, 0.15)))
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0
                changed = True
                while changed:
                    changed = False
                    for clause in clauses:
                        satisfied = False; free = []
                        for v, s in clause:
                            if v in fixed:
                                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                    satisfied = True; break
                            else: free.append((v,s))
                        if not satisfied and len(free) == 1:
                            v, s = free[0]
                            if v not in fixed: fixed[v] = 1 if s==1 else 0; changed = True

            assignment = [fixed.get(v,0) for v in range(n)]
            sat = evaluate(clauses, assignment)
            futures.append((assignment, sat))

        # Compute self-consistent weak values
        for var in range(n):
            total += 1
            actual = correct_val[var]

            if (1 if tensions[var] >= 0 else 0) == actual:
                tension_correct += 1

            # Weak value: weight futures by overlap AND satisfaction
            w_sum = 0; w_total = 0
            for assignment, sat in futures:
                overlap = sum(1 for v in range(n) if tension_pred[v] == assignment[v]) / n
                quality = sat / len(clauses)  # how many clauses satisfied
                weight = (overlap ** 2) * (quality ** 4)  # amplify good, overlapping futures
                w_sum += assignment[var] * weight
                w_total += weight

            if w_total > 0:
                wv = w_sum / w_total
                wv_pred = 1 if wv > 0.5 else 0
            else:
                wv_pred = 1 if tensions[var] >= 0 else 0

            if wv_pred == actual:
                scwv_correct += 1

    print(f"\n  Tension:                    {tension_correct/total*100:.1f}%")
    print(f"  Self-consistent weak value: {scwv_correct/total*100:.1f}%")
    print(f"  Improvement:               {(scwv_correct-tension_correct)/total*100:+.1f}%")


# ============================================================
# 4. TWO-VECTOR FORMALISM: past + future bounds
# ============================================================

def two_vector():
    """
    Full TSVF analogy:
    |past> = tension prediction
    |future> = best crystallization result
    weak_value = <future| bit |past> / <future|past>

    Compute for each bit. Does it predict better than either alone?
    """
    print("\n" + "=" * 70)
    print("4. TWO-VECTOR: Past (tension) + Future (best crystallization)")
    print("=" * 70)

    random.seed(42); n = 12

    tension_acc = 0; future_acc = 0; two_vec_acc = 0; total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        t_pred = [1 if tensions[v] >= 0 else 0 for v in range(n)]

        # "Future": best crystallization (most clauses satisfied)
        best_future = None; best_sat = 0
        for run in range(20):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(tensions[v]) + random.gauss(0, 0.2)))
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0
            assignment = [fixed.get(v,0) for v in range(n)]
            sat = evaluate(clauses, assignment)
            if sat > best_sat:
                best_sat = sat; best_future = assignment

        if best_future is None: continue

        # Overlap between past and future
        overlap = sum(1 for v in range(n) if t_pred[v] == best_future[v]) / n

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Past (tension)
            if t_pred[var] == actual: tension_acc += 1

            # Future (best crystallization)
            if best_future[var] == actual: future_acc += 1

            # Two-vector: weighted combination
            # Where past and future AGREE → very confident
            # Where they DISAGREE → weak value = use weighted combo
            if t_pred[var] == best_future[var]:
                # Agreement → strong prediction
                tv_pred = t_pred[var]
            else:
                # Disagreement → use future if overlap is high (future is good)
                # use past if overlap is low (future is bad)
                if overlap > 0.7:
                    tv_pred = best_future[var]  # trust future
                else:
                    tv_pred = t_pred[var]  # trust past

            if tv_pred == actual: two_vec_acc += 1

    print(f"\n  Past (tension):    {tension_acc/total*100:.1f}%")
    print(f"  Future (best run): {future_acc/total*100:.1f}%")
    print(f"  Two-vector:        {two_vec_acc/total*100:.1f}%")


if __name__ == "__main__":
    test_weak_values()
    anomalous_bits()
    self_consistent_weak()
    two_vector()
