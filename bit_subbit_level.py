"""
SUB-BIT LEVEL: What's inside a single bit's decision?

We treated tension as a single number σ ∈ [-1, +1].
But σ is an AGGREGATE — sum of clause votes.
What if the individual votes carry more info than the sum?

Like: knowing "7 yes, 5 no" (σ=+0.17) is different from
"1 yes, 0 no" (σ=+1.0) even though both predict "1".

The DISTRIBUTION of votes, not just the sum, might matter.
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
# 1. VOTE DECOMPOSITION: break σ into individual clause votes
# ============================================================

def vote_decomposition(clauses, n, var):
    """
    For each clause containing var, compute:
    - sign: does clause want var=1 (+1) or var=0 (-1)?
    - weight: how much does clause depend on var? (1/k where k=free literals)
    - neighbors: who else is in the clause?
    - neighbor tensions: what do they want?

    Return the full vote vector, not just the sum.
    """
    votes = []
    for ci, clause in enumerate(clauses):
        var_sign = None
        others = []
        for v, s in clause:
            if v == var:
                var_sign = s
            else:
                others.append((v, s))

        if var_sign is None:
            continue

        weight = 1.0 / (1 + len(others))

        # Neighbor info
        neighbor_tensions = [(v, bit_tension(clauses, n, v)) for v, s in others]
        neighbor_agreement = sum(1 for v, t in neighbor_tensions if t * var_sign > 0)

        votes.append({
            'clause_idx': ci,
            'sign': var_sign,
            'weight': weight,
            'n_others': len(others),
            'neighbor_tensions': neighbor_tensions,
            'neighbor_agreement': neighbor_agreement / len(others) if others else 0.5,
        })

    return votes


# ============================================================
# 2. VOTE QUALITY: which votes are "reliable"?
# ============================================================

def vote_quality_analysis(clauses, n, solutions):
    """
    For each clause vote on each bit:
    - Is the vote pointing in the correct direction?
    - What makes a vote reliable vs unreliable?
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    reliable_votes = []
    unreliable_votes = []

    for var in range(n):
        votes = vote_decomposition(clauses, n, var)
        correct_dir = 1 if correct_val[var] == 1 else -1

        for vote in votes:
            is_reliable = (vote['sign'] == correct_dir)

            entry = {
                'weight': vote['weight'],
                'neighbor_agreement': vote['neighbor_agreement'],
                'n_others': vote['n_others'],
            }

            if is_reliable:
                reliable_votes.append(entry)
            else:
                unreliable_votes.append(entry)

    return reliable_votes, unreliable_votes


# ============================================================
# 3. WEIGHTED TENSION: can we weight votes by reliability?
# ============================================================

def smart_tension(clauses, n, var):
    """
    Instead of equal weighting, weight each clause's vote by
    how much its neighbors AGREE with the vote direction.

    If neighbors confirm → strong vote.
    If neighbors oppose → weak vote.
    """
    votes = vote_decomposition(clauses, n, var)

    push_1 = 0.0
    push_0 = 0.0

    for vote in votes:
        # Weight by neighbor agreement
        reliability = 0.5 + 0.5 * vote['neighbor_agreement']

        if vote['sign'] == 1:
            push_1 += reliability
        else:
            push_0 += reliability

    total = push_1 + push_0
    return (push_1 - push_0) / total if total > 0 else 0.0


# ============================================================
# 4. VOTE ENTROPY: how diverse are the votes?
# ============================================================

def vote_entropy(clauses, n, var):
    """
    If all votes agree → low entropy → confident.
    If votes are mixed → high entropy → uncertain.

    But also: are strong votes (high weight) agreeing?
    """
    votes = vote_decomposition(clauses, n, var)
    if not votes:
        return 0, 0, 0

    # Raw vote distribution
    pos_votes = sum(1 for v in votes if v['sign'] == 1)
    neg_votes = len(votes) - pos_votes
    total = len(votes)

    p_pos = pos_votes / total
    p_neg = neg_votes / total
    raw_entropy = 0
    if p_pos > 0: raw_entropy -= p_pos * math.log2(p_pos)
    if p_neg > 0: raw_entropy -= p_neg * math.log2(p_neg)

    # Weighted by neighbor agreement
    weighted_pos = sum(v['neighbor_agreement'] for v in votes if v['sign'] == 1)
    weighted_neg = sum(v['neighbor_agreement'] for v in votes if v['sign'] == -1)
    weighted_total = weighted_pos + weighted_neg
    if weighted_total > 0:
        wp = weighted_pos / weighted_total
        wn = weighted_neg / weighted_total
        weighted_entropy = 0
        if wp > 0: weighted_entropy -= wp * math.log2(wp)
        if wn > 0: weighted_entropy -= wn * math.log2(wn)
    else:
        weighted_entropy = 1.0

    # Entropy difference: does weighting reduce entropy?
    entropy_reduction = raw_entropy - weighted_entropy

    return raw_entropy, weighted_entropy, entropy_reduction


# ============================================================
# 5. CONFLICT PATTERNS within votes
# ============================================================

def vote_conflict_pattern(clauses, n, var):
    """
    Among the votes for var:
    - How many pairs of votes CONTRADICT each other?
      (two clauses: one says +1, other says -1, AND they share a neighbor)
    - Do contradicting votes have different neighbor support?
    """
    votes = vote_decomposition(clauses, n, var)

    conflicts = 0
    confirmations = 0

    for i in range(len(votes)):
        for j in range(i+1, len(votes)):
            # Do they share a neighbor?
            nb_i = {v for v, t in votes[i]['neighbor_tensions']}
            nb_j = {v for v, t in votes[j]['neighbor_tensions']}
            shared = nb_i & nb_j

            if not shared:
                continue

            if votes[i]['sign'] != votes[j]['sign']:
                conflicts += 1
            else:
                confirmations += 1

    total = conflicts + confirmations
    conflict_ratio = conflicts / total if total > 0 else 0

    return conflicts, confirmations, conflict_ratio


# ============================================================
# MAIN: Test all sub-bit properties
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions:
            instances.append((clauses, solutions))

    # --- Vote quality ---
    print("=" * 70)
    print("1. VOTE QUALITY: What makes a clause vote reliable?")
    print("=" * 70)

    all_reliable = []
    all_unreliable = []
    for clauses, solutions in instances:
        r = vote_quality_analysis(clauses, n, solutions)
        if r:
            all_reliable.extend(r[0])
            all_unreliable.extend(r[1])

    print(f"\n  {len(all_reliable)} reliable votes, {len(all_unreliable)} unreliable")
    print(f"\n  {'property':>20} | {'reliable':>10} | {'unreliable':>10} | {'ratio':>7}")
    print("  " + "-" * 55)

    for prop in ['weight', 'neighbor_agreement', 'n_others']:
        r = mean([v[prop] for v in all_reliable])
        u = mean([v[prop] for v in all_unreliable])
        ratio = r / u if u > 0 else 999
        sig = "***" if ratio > 1.2 or ratio < 0.83 else ""
        print(f"  {prop:>20} | {r:>10.4f} | {u:>10.4f} | {ratio:>7.2f} {sig}")

    # --- Smart tension vs standard ---
    print("\n" + "=" * 70)
    print("2. SMART TENSION: Does neighbor-weighted voting help?")
    print("=" * 70)

    std_correct = 0
    smart_correct = 0
    total = 0

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            total += 1
            actual = correct_val[var]

            std_pred = 1 if bit_tension(clauses, n, var) >= 0 else 0
            smart_pred = 1 if smart_tension(clauses, n, var) >= 0 else 0

            if std_pred == actual: std_correct += 1
            if smart_pred == actual: smart_correct += 1

    print(f"\n  Standard tension: {std_correct/total*100:.1f}%")
    print(f"  Smart tension:    {smart_correct/total*100:.1f}%")

    # --- Vote entropy ---
    print("\n" + "=" * 70)
    print("3. VOTE ENTROPY: Does entropy predict correctness?")
    print("=" * 70)

    correct_entropies = []
    wrong_entropies = []
    correct_reductions = []
    wrong_reductions = []

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            raw_e, weighted_e, reduction = vote_entropy(clauses, n, var)

            if pred == actual:
                correct_entropies.append(raw_e)
                correct_reductions.append(reduction)
            else:
                wrong_entropies.append(raw_e)
                wrong_reductions.append(reduction)

    print(f"\n  Raw vote entropy:")
    print(f"    Correct bits: {mean(correct_entropies):.4f}")
    print(f"    Wrong bits:   {mean(wrong_entropies):.4f}")
    print(f"    Ratio: {mean(wrong_entropies)/mean(correct_entropies):.2f}")

    print(f"\n  Entropy reduction from neighbor weighting:")
    print(f"    Correct bits: {mean(correct_reductions):.4f}")
    print(f"    Wrong bits:   {mean(wrong_reductions):.4f}")

    # --- Conflict patterns ---
    print("\n" + "=" * 70)
    print("4. VOTE CONFLICTS: Internal contradictions within a bit's votes")
    print("=" * 70)

    correct_conflicts = []
    wrong_conflicts = []

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            conflicts, confirmations, conflict_ratio = vote_conflict_pattern(clauses, n, var)

            if pred == actual:
                correct_conflicts.append(conflict_ratio)
            else:
                wrong_conflicts.append(conflict_ratio)

    print(f"\n  Conflict ratio (fraction of contradicting vote-pairs):")
    print(f"    Correct bits: {mean(correct_conflicts):.4f}")
    print(f"    Wrong bits:   {mean(wrong_conflicts):.4f}")
    if mean(correct_conflicts) > 0:
        ratio = mean(wrong_conflicts) / mean(correct_conflicts)
        print(f"    Ratio: {ratio:.2f}")
        if ratio > 1.2:
            print(f"    → Wrong bits have MORE internal conflicts")
