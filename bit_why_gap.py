"""
WHY does the clause approximation err coherently?

We know: 72% of gap correlation comes from systematic bias.
Systematic bias = E[σ_clause] - σ_solution.

σ_clause uses clause SIGNS to vote.
σ_solution uses SOLUTION MARGINALS.

These are different functions of the same bits.
Where exactly do they diverge?

The clause view: "how many clauses want bit=1 vs bit=0"
The solution view: "what fraction of solutions have bit=1"

These could differ when:
A. Some clauses are REDUNDANT (already satisfied by other bits)
B. Some clauses are CONTRADICTORY (impossible to satisfy jointly)
C. Some clauses are DOMINATED by other variables
D. The clause graph has local structure that biases counting

Let's find which.
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
# A. REDUNDANT CLAUSES: clauses already satisfied by other bits
# ============================================================

def redundancy_analysis(clauses, n, solutions):
    """
    For each clause containing bit i:
    In what fraction of solutions is the clause satisfied
    WITHOUT bit i's help (by other literals only)?

    If clause is usually satisfied by others → it's redundant for i.
    Redundant clauses still vote in tension but don't constrain solutions.
    This creates gap: clause votes count redundant clauses, solutions don't.
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    correct_redundancy = []
    wrong_redundancy = []

    for var in range(n):
        sigma = bit_tension(clauses, n, var)
        pred = 1 if sigma >= 0 else 0
        is_correct = pred == correct_val[var]

        redundant_votes = 0
        total_votes = 0

        for clause in clauses:
            var_in_clause = False
            var_sign = 0
            others = []
            for v, s in clause:
                if v == var:
                    var_in_clause = True
                    var_sign = s
                else:
                    others.append((v, s))

            if not var_in_clause: continue
            total_votes += 1

            # In how many solutions is this clause satisfied WITHOUT var?
            satisfied_without = 0
            for sol in solutions:
                others_satisfy = False
                for v, s in others:
                    if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                        others_satisfy = True; break
                if others_satisfy:
                    satisfied_without += 1

            redundancy = satisfied_without / len(solutions)
            redundant_votes += redundancy

        avg_redundancy = redundant_votes / total_votes if total_votes > 0 else 0

        if is_correct:
            correct_redundancy.append(avg_redundancy)
        else:
            wrong_redundancy.append(avg_redundancy)

    return correct_redundancy, wrong_redundancy


# ============================================================
# B. Does WEIGHTING by non-redundancy improve tension?
# ============================================================

def non_redundant_tension(clauses, n, solutions):
    """
    Weight each clause vote by (1 - redundancy).
    Redundant clauses get low weight.
    Does this improve accuracy?
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    # Precompute redundancy for each (clause, var) pair
    clause_redundancy = {}
    for ci, clause in enumerate(clauses):
        for v_target, s_target in clause:
            others = [(v,s) for v,s in clause if v != v_target]
            sat_without = 0
            for sol in solutions:
                if any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0) for v,s in others):
                    sat_without += 1
            clause_redundancy[(ci, v_target)] = sat_without / len(solutions)

    # Standard tension accuracy
    std_correct = 0
    # Non-redundant tension accuracy
    nr_correct = 0
    total = 0

    for var in range(n):
        total += 1
        actual = correct_val[var]

        # Standard
        sigma_std = bit_tension(clauses, n, var)
        if (1 if sigma_std >= 0 else 0) == actual:
            std_correct += 1

        # Non-redundant weighted
        push_1 = 0; push_0 = 0
        for ci, clause in enumerate(clauses):
            for v, s in clause:
                if v == var:
                    red = clause_redundancy.get((ci, var), 0)
                    weight = (1 - red)  # non-redundant weight
                    if s == 1: push_1 += weight
                    else: push_0 += weight

        sigma_nr = (push_1 - push_0) / (push_1 + push_0) if push_1 + push_0 > 0 else 0
        if (1 if sigma_nr >= 0 else 0) == actual:
            nr_correct += 1

    return std_correct / total, nr_correct / total


# ============================================================
# C. CLAUSE IMPORTANCE: which clauses actually constrain solutions?
# ============================================================

def clause_importance(clauses, n, solutions):
    """
    For each clause: how many solutions would we LOSE if we removed it?
    (i.e., how many solutions satisfy all OTHER clauses but not this one)

    Important clauses = necessary for solution structure.
    Unimportant clauses = redundant, solutions satisfy them easily.
    """
    if not solutions: return None

    m = len(clauses)
    importance = []

    for ci in range(m):
        # How many solutions violate ONLY this clause?
        violations = 0
        for sol in solutions:
            # Does sol satisfy clause ci?
            sat_ci = any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
                        for v,s in clauses[ci])
            if not sat_ci:
                violations += 1

        # Actually all solutions satisfy all clauses (they're solutions!)
        # So violations = 0 always.
        # Instead: if we REMOVE clause ci, how many MORE solutions appear?
        # This is expensive. Instead: how TIGHT is this clause?
        # = fraction of solutions where clause is satisfied by EXACTLY 1 literal

        tight_count = 0
        for sol in solutions:
            n_satisfying_literals = sum(
                1 for v, s in clauses[ci]
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
            )
            if n_satisfying_literals == 1:
                tight_count += 1

        tightness = tight_count / len(solutions) if solutions else 0
        importance.append(tightness)

    return importance


# ============================================================
# D. Does tightness predict which clauses CONTRIBUTE to gap?
# ============================================================

def tightness_vs_gap(clauses, n, solutions):
    """
    For each bit: separate its clause votes into tight and loose.
    Does tension from TIGHT clauses only give better accuracy?
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    # Precompute tightness
    tightness = clause_importance(clauses, n, solutions)

    std_correct = 0
    tight_correct = 0
    total = 0

    for var in range(n):
        total += 1
        actual = correct_val[var]

        # Standard tension
        sigma_std = bit_tension(clauses, n, var)
        if (1 if sigma_std >= 0 else 0) == actual: std_correct += 1

        # Tight-only tension
        push_1 = 0; push_0 = 0
        for ci, clause in enumerate(clauses):
            for v, s in clause:
                if v == var:
                    t = tightness[ci]
                    weight = t  # weight by tightness
                    if s == 1: push_1 += weight
                    else: push_0 += weight

        sigma_tight = (push_1-push_0)/(push_1+push_0) if push_1+push_0 > 0 else 0
        if (1 if sigma_tight >= 0 else 0) == actual: tight_correct += 1

    return std_correct/total, tight_correct/total


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    # --- A. Redundancy ---
    print("\n" + "=" * 70)
    print("A. CLAUSE REDUNDANCY: are wrong bits' clauses more redundant?")
    print("=" * 70)

    all_c = []; all_w = []
    for clauses, solutions in instances[:60]:
        r = redundancy_analysis(clauses, n, solutions)
        if r:
            all_c.extend(r[0])
            all_w.extend(r[1])

    print(f"\n  Correct bits: avg clause redundancy = {mean(all_c):.4f}")
    print(f"  Wrong bits:   avg clause redundancy = {mean(all_w):.4f}")
    ratio = mean(all_w)/mean(all_c) if mean(all_c) > 0 else 1
    print(f"  Ratio: {ratio:.3f}")

    # --- B. Non-redundant tension ---
    print("\n" + "=" * 70)
    print("B. NON-REDUNDANT TENSION: does removing redundancy help?")
    print("=" * 70)

    std_accs = []; nr_accs = []
    for clauses, solutions in instances[:40]:
        r = non_redundant_tension(clauses, n, solutions)
        if r:
            std_accs.append(r[0])
            nr_accs.append(r[1])

    print(f"\n  Standard tension:      {mean(std_accs)*100:.1f}%")
    print(f"  Non-redundant tension: {mean(nr_accs)*100:.1f}%")
    print(f"  Improvement:           {(mean(nr_accs)-mean(std_accs))*100:+.1f}%")

    # --- C/D. Tightness ---
    print("\n" + "=" * 70)
    print("C/D. CLAUSE TIGHTNESS: do tight clauses give better signal?")
    print("=" * 70)

    std_accs2 = []; tight_accs = []
    for clauses, solutions in instances[:40]:
        r = tightness_vs_gap(clauses, n, solutions)
        if r:
            std_accs2.append(r[0])
            tight_accs.append(r[1])

    print(f"\n  Standard tension:        {mean(std_accs2)*100:.1f}%")
    print(f"  Tightness-weighted:      {mean(tight_accs)*100:.1f}%")
    print(f"  Improvement:             {(mean(tight_accs)-mean(std_accs2))*100:+.1f}%")

    # --- Summary: what creates the gap? ---
    print("\n" + "=" * 70)
    print("SUMMARY: What creates the clause-solution gap?")
    print("=" * 70)

    print(f"""
  Wrong bits' clauses are {ratio:.1%} as redundant as correct bits' clauses.
  Removing redundancy: {'+' if mean(nr_accs) > mean(std_accs) else ''}{(mean(nr_accs)-mean(std_accs))*100:.1f}%
  Using tightness:     {'+' if mean(tight_accs) > mean(std_accs2) else ''}{(mean(tight_accs)-mean(std_accs2))*100:.1f}%
    """)
