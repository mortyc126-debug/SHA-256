"""
CONFIGURATION LEVEL — Pairs, triples, patterns of bits.

45+ single-bit properties can't see the 9% gap.
7 global graph properties can't see it.
The gap must live in JOINT configurations.

If bit A is wrong, is bit B more likely to be wrong too?
Do wrong bits form CLUSTERS? CHAINS? PATTERNS?
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
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True; break
            else: rem.append((v, s))
        if sat: continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


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
                    else: rem.append((v, si));
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
# 1. Do wrong bits CLUSTER together?
# ============================================================

def wrong_bit_clustering(clauses, n, solutions):
    """Are wrong bits more likely to be NEIGHBORS of other wrong bits?"""
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]
    v4_t = tension_v4(clauses, n, {}, 10)

    is_wrong = [0] * n
    for var in range(n):
        pred = 1 if v4_t.get(var, 0) >= 0 else 0
        if pred != correct_val[var]:
            is_wrong[var] = 1

    # Build adjacency
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a+1, len(vs)):
                adj[vs[a]].add(vs[b])
                adj[vs[b]].add(vs[a])

    # For each wrong bit: what fraction of its neighbors are also wrong?
    wrong_neighbor_frac = []
    correct_neighbor_frac = []

    for var in range(n):
        if not adj[var]:
            continue
        frac_wrong_neighbors = sum(is_wrong[nb] for nb in adj[var]) / len(adj[var])
        if is_wrong[var]:
            wrong_neighbor_frac.append(frac_wrong_neighbors)
        else:
            correct_neighbor_frac.append(frac_wrong_neighbors)

    return wrong_neighbor_frac, correct_neighbor_frac


# ============================================================
# 2. Do wrong bits share CLAUSES?
# ============================================================

def wrong_bit_co_occurrence(clauses, n, solutions):
    """How often do two wrong bits appear in the SAME clause?"""
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]
    v4_t = tension_v4(clauses, n, {}, 10)

    is_wrong = set()
    for var in range(n):
        pred = 1 if v4_t.get(var, 0) >= 0 else 0
        if pred != correct_val[var]:
            is_wrong.add(var)

    # Count clause types: how many wrongs per clause
    clause_wrong_counts = []
    for clause in clauses:
        vs = [v for v, s in clause]
        n_wrong = sum(1 for v in vs if v in is_wrong)
        clause_wrong_counts.append(n_wrong)

    return clause_wrong_counts, len(is_wrong)


# ============================================================
# 3. PAIR ANALYSIS: which pairs of bits are JOINTLY wrong?
# ============================================================

def pair_wrongness(clauses, n, solutions):
    """
    For each pair (i,j): how often are BOTH wrong simultaneously
    across many instances?
    """
    pass  # Done across instances below


# ============================================================
# 4. CONDITIONAL wrongness: if bit A is wrong, what about bit B?
# ============================================================

def conditional_wrongness(clauses_list, n):
    """
    Across many instances: P(B wrong | A wrong) vs P(B wrong).
    If wrong bits are correlated, P(B|A) > P(B).
    """
    # Collect per-instance wrongness
    n_instances = len(clauses_list)

    # For each bit position: how often wrong
    wrong_count = [0] * n
    # For each pair: how often both wrong
    both_wrong = [[0]*n for _ in range(n)]
    total_valid = 0

    for clauses, solutions in clauses_list:
        if not solutions:
            continue
        total_valid += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        wrong = set()
        for var in range(n):
            pred = 1 if v4_t.get(var, 0) >= 0 else 0
            if pred != correct_val[var]:
                wrong.add(var)
                wrong_count[var] += 1

        for i in wrong:
            for j in wrong:
                if i != j:
                    both_wrong[i][j] += 1

    return wrong_count, both_wrong, total_valid


# ============================================================
# 5. Is there a WRONG PATTERN — a specific subset that tends to be wrong together?
# ============================================================

def wrong_patterns(clauses_list, n):
    """
    Collect the SET of wrong bits for each instance.
    Are there recurring subsets?
    """
    from collections import Counter
    pattern_counter = Counter()

    for clauses, solutions in clauses_list:
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        wrong = []
        for var in range(n):
            pred = 1 if v4_t.get(var, 0) >= 0 else 0
            if pred != correct_val[var]:
                wrong.append(var)

        # Record pattern size and pairs
        pattern_counter[len(wrong)] += 1

    return pattern_counter


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    # Collect instances
    instances = []
    for seed in range(300):
        clauses = random_3sat(n, int(4.27 * n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} satisfiable instances")

    # ---- Test 1: Wrong bit clustering ----
    print("\n" + "=" * 70)
    print("TEST 1: Do wrong bits cluster together?")
    print("=" * 70)

    all_wrong_nb = []
    all_correct_nb = []

    for clauses, solutions in instances:
        result = wrong_bit_clustering(clauses, n, solutions)
        if result:
            w, c = result
            all_wrong_nb.extend(w)
            all_correct_nb.extend(c)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Wrong bits' neighbors are wrong:   {mean(all_wrong_nb)*100:.1f}%")
    print(f"  Correct bits' neighbors are wrong: {mean(all_correct_nb)*100:.1f}%")
    print(f"  Ratio: {mean(all_wrong_nb)/mean(all_correct_nb):.2f}x"
          if mean(all_correct_nb) > 0 else "")

    # ---- Test 2: Clause co-occurrence ----
    print("\n" + "=" * 70)
    print("TEST 2: Do wrong bits share clauses?")
    print("=" * 70)

    from collections import Counter
    clause_type_counts = Counter()
    total_clauses_counted = 0
    total_wrong_bits = 0

    for clauses, solutions in instances:
        result = wrong_bit_co_occurrence(clauses, n, solutions)
        if result:
            counts, n_wrong = result
            for c in counts:
                clause_type_counts[c] += 1
            total_clauses_counted += len(counts)
            total_wrong_bits += n_wrong

    avg_wrong = total_wrong_bits / len(instances) if instances else 0
    print(f"\n  Average wrong bits per instance: {avg_wrong:.1f} out of {n}")

    print(f"\n  Clauses by number of wrong bits inside:")
    expected_frac = avg_wrong / n
    for k in sorted(clause_type_counts.keys()):
        actual = clause_type_counts[k] / total_clauses_counted
        # Expected if wrong bits distributed randomly
        from math import comb
        expected = comb(3, k) * (expected_frac ** k) * ((1 - expected_frac) ** (3 - k))
        ratio = actual / expected if expected > 0 else 0
        print(f"    {k} wrong bits: {actual*100:.1f}% (expected {expected*100:.1f}%, "
              f"ratio {ratio:.2f})")

    # ---- Test 3: Conditional wrongness ----
    print("\n" + "=" * 70)
    print("TEST 3: Are wrong bits correlated across instances?")
    print("=" * 70)

    wrong_count, both_wrong, total_valid = conditional_wrongness(instances, n)

    # P(B wrong | A wrong) vs P(B wrong)
    marginal_wrong = [wrong_count[v] / total_valid for v in range(n)]
    avg_marginal = sum(marginal_wrong) / n

    conditional_probs = []
    for i in range(n):
        if wrong_count[i] < 5:
            continue
        for j in range(n):
            if i == j:
                continue
            p_j = wrong_count[j] / total_valid
            p_j_given_i = both_wrong[i][j] / wrong_count[i] if wrong_count[i] > 0 else 0
            if p_j > 0:
                lift = p_j_given_i / p_j
                conditional_probs.append(lift)

    avg_lift = mean(conditional_probs)
    print(f"\n  Average P(B wrong | A wrong) / P(B wrong) = {avg_lift:.3f}")
    print(f"  (1.0 = independent, >1 = clustered, <1 = anti-clustered)")

    # ---- Test 4: Wrong pattern sizes ----
    print("\n" + "=" * 70)
    print("TEST 4: Distribution of wrong bit counts per instance")
    print("=" * 70)

    patterns = wrong_patterns(instances, n)
    print(f"\n  {'#wrong':>6} | {'instances':>9} | {'fraction':>8} | visual")
    print("  " + "-" * 50)
    for k in sorted(patterns.keys()):
        frac = patterns[k] / len(instances)
        bar = "█" * int(frac * 50)
        print(f"  {k:>6} | {patterns[k]:>9} | {frac*100:>7.1f}% | {bar}")

    # ---- Test 5: When instance has FEW wrong bits, which are they? ----
    print("\n" + "=" * 70)
    print("TEST 5: Profile of instances with exactly 1-2 wrong bits")
    print("=" * 70)

    for target_wrong in [1, 2]:
        position_counts = Counter()
        total_count = 0

        for clauses, solutions in instances:
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]
            v4_t = tension_v4(clauses, n, {}, 10)

            wrong = []
            for var in range(n):
                pred = 1 if v4_t.get(var, 0) >= 0 else 0
                if pred != correct_val[var]:
                    wrong.append(var)

            if len(wrong) == target_wrong:
                total_count += 1
                for w in wrong:
                    # What's the RANK of this wrong bit by confidence?
                    all_confs = sorted(range(n), key=lambda v: -abs(v4_t.get(v, 0)))
                    rank = all_confs.index(w)
                    position_counts[rank] += 1

        if total_count > 0:
            print(f"\n  Instances with exactly {target_wrong} wrong bit(s): {total_count}")
            print(f"  Where does the wrong bit rank by |σ|?")
            print(f"  {'rank':>6} | {'count':>6} | {'fraction':>8}")
            print("  " + "-" * 30)
            for rank in sorted(position_counts.keys()):
                frac = position_counts[rank] / (total_count * target_wrong)
                print(f"  {rank:>6} | {position_counts[rank]:>6} | {frac*100:>7.1f}%")
