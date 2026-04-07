"""
SOFT MEASUREMENT: More delicate instruments for bits.

Current: σ = single number. Fix = hard collapse (0 or 1).
New: What if we measure MORE GENTLY?

1. FULL DISTRIBUTION: not σ but P(bit=1 | each possible context)
2. SOFT FIX: instead of fixing to 0/1, fix to "probably 0.7"
3. PARTIAL OBSERVATION: fix a bit HALFWAY — weighted constraint
4. INTERFERENCE MEASUREMENT: observe bit through TWO paths simultaneously
5. WEAK MEASUREMENT: nudge without collapsing — does info leak?
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
# 1. FULL DISTRIBUTION: P(bit=1) across ALL possible neighbors
# ============================================================

def full_distribution():
    """
    Instead of σ (one number), compute P(bit=1) for each possible
    state of its direct neighbors.

    A bit with d neighbors has 2^d possible contexts.
    For each: P(bit=1 | context) from solutions.

    Is this distribution RICHER than σ? Does it predict better?
    """
    print("=" * 70)
    print("1. FULL DISTRIBUTION: P(bit=1) across neighbor contexts")
    print("=" * 70)

    random.seed(42); n = 12

    # For small neighborhoods, enumerate all contexts
    sigma_correct = 0; dist_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 3: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            total += 1

            # σ prediction
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                sigma_correct += 1

            # Full distribution: for each solution, what's the context?
            # Context = values of direct neighbors in that solution
            neighbors = []
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var and v not in neighbors:
                            neighbors.append(v)

            # Use only first 4 neighbors (2^4 = 16 contexts)
            key_nbs = neighbors[:4]
            context_votes = {}  # context_tuple → [count_0, count_1]

            for sol in solutions:
                ctx = tuple(sol[nb] for nb in key_nbs)
                if ctx not in context_votes:
                    context_votes[ctx] = [0, 0]
                context_votes[ctx][sol[var]] += 1

            # Distribution prediction: majority PER CONTEXT, then vote
            # Weight by how common each context is
            weighted_1 = 0; weighted_0 = 0
            for ctx, (c0, c1) in context_votes.items():
                if c1 > c0:
                    weighted_1 += c1 + c0  # this context votes 1
                else:
                    weighted_0 += c1 + c0

            dist_pred = 1 if weighted_1 > weighted_0 else 0
            if dist_pred == correct_val[var]:
                dist_correct += 1

    print(f"\n  σ prediction:            {sigma_correct/total*100:.1f}%")
    print(f"  Full distribution pred:  {dist_correct/total*100:.1f}%")
    print(f"  Improvement:             {(dist_correct-sigma_correct)/total*100:+.1f}%")


# ============================================================
# 2. SOFT TENSION: weighted beliefs instead of hard fixation
# ============================================================

def soft_tension():
    """
    Instead of fixing neighbor to 0 or 1 (hard collapse):
    Use neighbor's TENSION as soft belief.

    Standard: fix nb=1 → all nb's clauses resolved.
    Soft: nb is "probably 1 with confidence |σ|" → clauses
          partially resolved, proportional to confidence.

    This is closer to v4, but even softer — v4 uses P(satisfies),
    soft uses continuous beliefs.
    """
    print("\n" + "=" * 70)
    print("2. SOFT TENSION: Continuous beliefs")
    print("=" * 70)

    random.seed(42); n = 12

    # Soft tension: weight each clause by P(neighbor satisfies)
    # using neighbor tensions as probabilities
    soft_correct = 0; hard_correct = 0; total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            total += 1

            # Hard tension
            if (1 if tensions[var] >= 0 else 0) == correct_val[var]:
                hard_correct += 1

            # Soft: for each clause, compute P(var satisfies | neighbor beliefs)
            soft_push_1 = 0; soft_push_0 = 0

            for clause in clauses:
                var_sign = None
                others = []
                for v, s in clause:
                    if v == var: var_sign = s
                    else: others.append((v, s))
                if var_sign is None: continue

                # P(each other literal satisfies) = soft belief
                for v, s in others:
                    t = tensions[v]
                    # P(v=1) = (1+t)/2, P(v=0) = (1-t)/2
                    if s == 1:
                        p_sat = (1 + t) / 2  # literal +v satisfied when v=1
                    else:
                        p_sat = (1 - t) / 2  # literal ¬v satisfied when v=0

                # P(clause needs var) = P(all others fail)
                p_others_fail = 1.0
                for v, s in others:
                    t = tensions[v]
                    p_lit = (1+t)/2 if s==1 else (1-t)/2
                    p_others_fail *= (1 - p_lit)

                # Soft weight = how much clause NEEDS var (continuous)
                need = p_others_fail

                # Second-order: weight also by HOW CONFIDENT the need estimate is
                # confidence of need = product of confidences of neighbors
                need_confidence = 1.0
                for v, s in others:
                    need_confidence *= abs(tensions[v])

                # Combine need × confidence
                weight = need * (0.5 + 0.5 * need_confidence)

                if var_sign == 1: soft_push_1 += weight
                else: soft_push_0 += weight

            soft_total = soft_push_1 + soft_push_0
            soft_sigma = (soft_push_1 - soft_push_0) / soft_total if soft_total > 0 else 0

            if (1 if soft_sigma >= 0 else 0) == correct_val[var]:
                soft_correct += 1

    print(f"\n  Hard tension:     {hard_correct/total*100:.1f}%")
    print(f"  Soft (need×conf): {soft_correct/total*100:.1f}%")
    print(f"  Improvement:      {(soft_correct-hard_correct)/total*100:+.1f}%")


# ============================================================
# 3. WEAK MEASUREMENT: Tiny perturbation, measure response
# ============================================================

def weak_measurement():
    """
    Instead of fixing neighbor to 0 or 1:
    Add a TINY bias to the neighbor (like a weak field).

    Implement: soft-fix neighbor to ε-more-likely-1.
    Measure: how does our bit RESPOND to this tiny push?

    Weak measurement = derivative dσ/d(neighbor_bias).
    Large derivative = bit is SENSITIVE here.
    Small = bit is ROBUST.

    Compare to HARD measurement (fix neighbor, see Δσ).
    Does weak measurement reveal MORE than hard?
    """
    print("\n" + "=" * 70)
    print("3. WEAK MEASUREMENT: Response to tiny perturbation")
    print("=" * 70)

    random.seed(42); n = 12

    # Weak response: numerical derivative dσ/d(neighbor_tension)
    weak_responses_correct = []
    weak_responses_wrong = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            pred = 1 if tensions[var] >= 0 else 0
            is_correct = pred == correct_val[var]

            # Weak response: sensitivity to EACH neighbor
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            # Hard response: Δσ from fixing neighbor
            hard_responses = []
            for nb in list(neighbors)[:5]:
                s0 = bit_tension(clauses, n, var, {nb: 0})
                s1 = bit_tension(clauses, n, var, {nb: 1})
                hard_responses.append(abs(s1 - s0))

            avg_hard = sum(hard_responses)/len(hard_responses) if hard_responses else 0

            # "Weak" response: second derivative (how response CHANGES with another nb)
            weak_second = []
            nb_list = list(neighbors)[:4]
            for a in range(len(nb_list)):
                for b in range(a+1, len(nb_list)):
                    na, nb_b = nb_list[a], nb_list[b]
                    # d²σ/d(na)d(nb) ≈ σ(na=1,nb=1) - σ(na=1,nb=0) - σ(na=0,nb=1) + σ(na=0,nb=0)
                    s00 = bit_tension(clauses, n, var, {na: 0, nb_b: 0})
                    s01 = bit_tension(clauses, n, var, {na: 0, nb_b: 1})
                    s10 = bit_tension(clauses, n, var, {na: 1, nb_b: 0})
                    s11 = bit_tension(clauses, n, var, {na: 1, nb_b: 1})
                    second_deriv = abs(s11 - s10 - s01 + s00)
                    weak_second.append(second_deriv)

            avg_weak = sum(weak_second)/len(weak_second) if weak_second else 0

            if is_correct:
                weak_responses_correct.append({'hard': avg_hard, 'weak': avg_weak})
            else:
                weak_responses_wrong.append({'hard': avg_hard, 'weak': avg_weak})

    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  HARD response (1st derivative):")
    print(f"    Correct: {mean([r['hard'] for r in weak_responses_correct]):.4f}")
    print(f"    Wrong:   {mean([r['hard'] for r in weak_responses_wrong]):.4f}")

    hr_ratio = mean([r['hard'] for r in weak_responses_wrong]) / mean([r['hard'] for r in weak_responses_correct])
    print(f"    Ratio: {hr_ratio:.2f}")

    print(f"\n  WEAK response (2nd derivative = nonlinearity):")
    print(f"    Correct: {mean([r['weak'] for r in weak_responses_correct]):.4f}")
    print(f"    Wrong:   {mean([r['weak'] for r in weak_responses_wrong]):.4f}")

    wr_ratio = mean([r['weak'] for r in weak_responses_wrong]) / mean([r['weak'] for r in weak_responses_correct])
    print(f"    Ratio: {wr_ratio:.2f}")

    if abs(wr_ratio - 1.0) > abs(hr_ratio - 1.0):
        print(f"\n  → Weak (2nd derivative) is MORE discriminative!")
    else:
        print(f"\n  → Hard (1st derivative) is more discriminative.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    full_distribution()
    soft_tension()
    weak_measurement()
