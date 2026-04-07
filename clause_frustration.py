"""
CLAUSE FRUSTRATION: The 28/27 balance as source of hardness.

Supporting clauses (28%) pull bits in same direction.
Competing clauses (27%) pull in opposite directions.
Balance ≈ 1:1.

Questions:
1. Does this balance CHANGE with ratio? (easy vs hard instances)
2. Are SPECIFIC bits caught between supporting and competing clauses?
3. Is the balance THE source of clone sign unpredictability?
4. Can we identify the "frustration network" of competing clause pairs?
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
# 1. BALANCE vs RATIO: does it predict hardness?
# ============================================================

def balance_vs_ratio():
    print("=" * 70)
    print("1. Supporting/Competing balance across ratios")
    print("=" * 70)

    random.seed(42); n = 12

    print(f"\n  {'ratio':>6} | {'support%':>8} | {'compete%':>8} | {'indep%':>7} | "
          f"{'S/C ratio':>9} | {'solvable':>8}")
    print("  " + "-" * 60)

    for ratio_10 in range(15, 55, 5):
        ratio = ratio_10 / 10.0
        sup_total = 0; comp_total = 0; ind_total = 0; n_inst = 0
        solvable = 0

        for seed in range(100):
            clauses = random_3sat(n, int(ratio*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions: solvable += 1
            n_inst += 1

            for ci in range(len(clauses)):
                for cj in range(ci+1, len(clauses)):
                    signs_i = {v: s for v, s in clauses[ci]}
                    signs_j = {v: s for v, s in clauses[cj]}
                    shared = set(signs_i.keys()) & set(signs_j.keys())

                    if not shared:
                        ind_total += 1
                        continue

                    agree = sum(1 for v in shared if signs_i[v] == signs_j[v])
                    disagree = len(shared) - agree

                    if agree > disagree: sup_total += 1
                    elif disagree > agree: comp_total += 1
                    else: ind_total += 1

        total = sup_total + comp_total + ind_total
        if total > 0:
            sc_ratio = sup_total / comp_total if comp_total > 0 else float('inf')
            print(f"  {ratio:>6.1f} | {sup_total/total*100:>7.1f}% | {comp_total/total*100:>7.1f}% | "
                  f"{ind_total/total*100:>6.1f}% | {sc_ratio:>9.3f} | {solvable:>8}")


# ============================================================
# 2. PER-BIT FRUSTRATION: bits caught between S and C clauses
# ============================================================

def per_bit_frustration():
    """
    For each bit: how many of its clause-pairs are Supporting vs Competing?
    A bit with balanced S/C is FRUSTRATED — pulled both ways.
    Does frustration predict errors?
    """
    print("\n" + "=" * 70)
    print("2. Per-bit clause frustration: S vs C balance")
    print("=" * 70)

    random.seed(42); n = 12

    correct_frust = []; wrong_frust = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            # Find all clause pairs sharing this bit
            my_clauses = []
            for ci, clause in enumerate(clauses):
                if any(v == var for v, s in clause):
                    my_clauses.append(ci)

            support = 0; compete = 0
            for a in range(len(my_clauses)):
                for b in range(a+1, len(my_clauses)):
                    ci, cj = my_clauses[a], my_clauses[b]
                    signs_i = {v: s for v, s in clauses[ci]}
                    signs_j = {v: s for v, s in clauses[cj]}
                    shared = set(signs_i.keys()) & set(signs_j.keys())
                    shared.discard(var)  # exclude the bit itself

                    if not shared: continue

                    agree = sum(1 for v in shared if signs_i[v] == signs_j[v])
                    disagree = len(shared) - agree
                    if agree > disagree: support += 1
                    elif disagree > agree: compete += 1

            total = support + compete
            if total > 0:
                frustration = min(support, compete) / total  # 0=one-sided, 0.5=balanced
            else:
                frustration = 0

            if is_correct:
                correct_frust.append(frustration)
            else:
                wrong_frust.append(frustration)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correct bits: avg clause frustration = {mean(correct_frust):.4f}")
    print(f"  Wrong bits:   avg clause frustration = {mean(wrong_frust):.4f}")
    ratio = mean(wrong_frust)/mean(correct_frust) if mean(correct_frust) > 0 else 0
    print(f"  Ratio: {ratio:.2f}")


# ============================================================
# 3. DOES FRUSTRATION EXPLAIN CLONE SIGN ERRORS?
# ============================================================

def frustration_vs_sign():
    """
    Clone pairs where sign is WRONG: are they between frustrated bits?
    """
    print("\n" + "=" * 70)
    print("3. Does clause frustration explain clone sign errors?")
    print("=" * 70)

    random.seed(42); n = 12

    correct_sign_frust = []; wrong_sign_frust = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Real clone pairs
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same < 0.85 and same > 0.15: continue
                is_clone = same > 0.85

                # Tension sign agreement = our sign prediction
                pred_clone = (tensions[i] >= 0) == (tensions[j] >= 0)
                sign_correct = pred_clone == is_clone

                # Frustration of the PAIR: how many competing clauses between i and j?
                clauses_i = set()
                clauses_j = set()
                for ci, clause in enumerate(clauses):
                    vs = [v for v, s in clause]
                    if i in vs: clauses_i.add(ci)
                    if j in vs: clauses_j.add(ci)

                shared_clauses = clauses_i & clauses_j

                # In shared clauses: do i and j have same or opposite signs?
                pair_support = 0; pair_compete = 0
                for ci in shared_clauses:
                    signs = {v: s for v, s in clauses[ci]}
                    if signs.get(i, 0) == signs.get(j, 0):
                        pair_support += 1
                    else:
                        pair_compete += 1

                total = pair_support + pair_compete
                if total > 0:
                    pair_frust = min(pair_support, pair_compete) / total
                else:
                    pair_frust = 0

                if sign_correct:
                    correct_sign_frust.append(pair_frust)
                else:
                    wrong_sign_frust.append(pair_frust)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correct sign predictions: avg pair frustration = {mean(correct_sign_frust):.4f}")
    print(f"  Wrong sign predictions:   avg pair frustration = {mean(wrong_sign_frust):.4f}")
    if mean(correct_sign_frust) > 0:
        ratio = mean(wrong_sign_frust) / mean(correct_sign_frust)
        print(f"  Ratio: {ratio:.2f}")


# ============================================================
# 4. FRUSTRATION NETWORK: topology of competing clauses
# ============================================================

def frustration_network():
    """
    Build a graph where CLAUSES are nodes, COMPETING pairs are edges.
    What does this network look like?
    - Are there clusters of competing clauses?
    - Do competing clusters map onto wrong bits?
    """
    print("\n" + "=" * 70)
    print("4. FRUSTRATION NETWORK: Competing clause topology")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        m = len(clauses)
        compete_edges = []

        for ci in range(m):
            for cj in range(ci+1, m):
                signs_i = {v: s for v, s in clauses[ci]}
                signs_j = {v: s for v, s in clauses[cj]}
                shared = set(signs_i.keys()) & set(signs_j.keys())
                if not shared: continue

                disagree = sum(1 for v in shared if signs_i[v] != signs_j[v])
                agree = len(shared) - disagree
                if disagree > agree:
                    compete_edges.append((ci, cj))

        # Network stats
        clause_compete_degree = [0] * m
        for ci, cj in compete_edges:
            clause_compete_degree[ci] += 1
            clause_compete_degree[cj] += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        max_d = max(clause_compete_degree)
        print(f"\n  Instance {seed}: {m} clauses, {len(compete_edges)} competing edges")
        print(f"    Avg competing degree: {mean(clause_compete_degree):.1f}")
        print(f"    Max competing degree: {max_d}")

        # Which BITS are most touched by competition?
        bit_competition = [0] * n
        for ci, cj in compete_edges:
            signs_i = {v: s for v, s in clauses[ci]}
            signs_j = {v: s for v, s in clauses[cj]}
            shared = set(signs_i.keys()) & set(signs_j.keys())
            for v in shared:
                if signs_i[v] != signs_j[v]:
                    bit_competition[v] += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        print(f"    Bit competition vs correctness:")
        for v in range(n):
            sigma = bit_tension(clauses, n, v)
            pred = 1 if sigma >= 0 else 0
            mark = "✓" if pred == correct_val[v] else "✗"
            bar = "█" * bit_competition[v]
            print(f"      x{v:>2} {mark} comp={bit_competition[v]:>3} |{bar}")


if __name__ == "__main__":
    balance_vs_ratio()
    per_bit_frustration()
    frustration_vs_sign()
    frustration_network()
