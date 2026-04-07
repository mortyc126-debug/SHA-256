"""
CLAUSE MECHANICS — Studying clauses as fundamental objects.

We studied bits exhaustively (28+ properties, 7 levels).
Now: what if the CLAUSE is the fundamental object?

A clause is NOT just "a constraint on 3 bits."
A clause is an ENTITY with its own:
- Internal state
- Relationships with other clauses
- Dynamics during crystallization
- Role in the solution space

Let's discover clause properties the way we discovered bit properties.
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
# I. STATIC CLAUSE PROPERTIES
# ============================================================

def clause_static(clauses, n, ci, solutions=None):
    """
    Measure everything about one clause WITHOUT fixing anything.
    """
    clause = clauses[ci]
    vars_in = [v for v, s in clause]
    signs = {v: s for v, s in clause}

    # 1. TENSION ALIGNMENT: do the bits' tensions agree with the clause's signs?
    #    If bit v has σ > 0 and appears positive → aligned.
    tensions = {v: bit_tension(clauses, n, v) for v in vars_in}
    aligned = sum(1 for v in vars_in
                  if (signs[v] == 1 and tensions[v] > 0) or
                     (signs[v] == -1 and tensions[v] < 0))
    alignment = aligned / len(vars_in)

    # 2. INTERNAL TENSION: do the clause's own bits agree with each other?
    #    If all tensions point same direction → coherent.
    #    If mixed → frustrated clause.
    tension_signs = [1 if tensions[v] >= 0 else -1 for v in vars_in]
    coherence = abs(sum(tension_signs)) / len(tension_signs)

    # 3. CLAUSE CONFIDENCE: how likely is this clause satisfied by tension?
    #    P(at least one literal true) given tensions as probabilities.
    prob_unsat = 1.0
    for v, s in clause:
        t = tensions[v]
        if s == 1:
            p_true = (1 + t) / 2
        else:
            p_true = (1 - t) / 2
        prob_unsat *= (1 - p_true)
    confidence = 1 - prob_unsat

    # 4. DEGREE: how many OTHER clauses share variables with this one?
    neighbors = set()
    for cj in range(len(clauses)):
        if cj == ci: continue
        vars_j = [v for v, s in clauses[cj]]
        if set(vars_in) & set(vars_j):
            neighbors.add(cj)
    degree = len(neighbors)

    # 5. OVERLAP: how many variables shared with each neighbor?
    overlaps = []
    for cj in neighbors:
        vars_j = [v for v, s in clauses[cj]]
        overlaps.append(len(set(vars_in) & set(vars_j)))
    avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0

    # 6. REDUNDANCY: in how many solutions is this clause satisfied
    #    by MORE than one literal?
    redundancy = 0
    if solutions:
        for sol in solutions:
            n_sat = sum(1 for v, s in clause
                       if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0))
            if n_sat > 1:
                redundancy += 1
        redundancy /= len(solutions)

    # 7. CRITICALITY: in how many solutions is this clause satisfied
    #    by EXACTLY one literal (barely surviving)?
    criticality = 0
    if solutions:
        for sol in solutions:
            n_sat = sum(1 for v, s in clause
                       if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0))
            if n_sat == 1:
                criticality += 1
        criticality /= len(solutions)

    # 8. SIGN PATTERN: all positive, all negative, mixed?
    n_pos = sum(1 for v, s in clause if s == 1)
    sign_pattern = n_pos / len(clause)  # 0=all neg, 1=all pos, 0.5=mixed

    return {
        'alignment': alignment,
        'coherence': coherence,
        'confidence': confidence,
        'degree': degree,
        'avg_overlap': avg_overlap,
        'redundancy': redundancy,
        'criticality': criticality,
        'sign_pattern': sign_pattern,
    }


# ============================================================
# II. CLAUSE TYPES: Can we classify clauses?
# ============================================================

def classify_clauses():
    """
    Classify each clause by its ROLE:
    - EASY: high confidence, high redundancy (everyone can satisfy it)
    - CRITICAL: low redundancy (barely satisfied, crucial constraint)
    - NOISE: tension-misaligned (points bits wrong way)
    - BACKBONE: defines frozen variables (always satisfied same way)
    """
    print("=" * 70)
    print("CLAUSE CLASSIFICATION")
    print("=" * 70)

    random.seed(42); n = 12

    all_props = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        for ci in range(len(clauses)):
            props = clause_static(clauses, n, ci, solutions)
            all_props.append(props)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  Total clauses analyzed: {len(all_props)}")
    print(f"\n  {'property':>15} | {'mean':>8} | {'std':>8} | {'min':>8} | {'max':>8}")
    print("  " + "-" * 55)

    for prop in ['alignment', 'coherence', 'confidence', 'degree',
                 'avg_overlap', 'redundancy', 'criticality', 'sign_pattern']:
        vals = [p[prop] for p in all_props]
        m = mean(vals)
        std = math.sqrt(sum((v-m)**2 for v in vals)/len(vals))
        mn = min(vals)
        mx = max(vals)
        print(f"  {prop:>15} | {m:>8.3f} | {std:>8.3f} | {mn:>8.3f} | {mx:>8.3f}")

    # Classify
    easy = [p for p in all_props if p['redundancy'] > 0.9]
    critical = [p for p in all_props if p['criticality'] > 0.3]
    noise = [p for p in all_props if p['alignment'] < 0.4]
    backbone = [p for p in all_props if p['redundancy'] > 0.95 and p['confidence'] > 0.9]

    print(f"\n  Types:")
    print(f"    EASY (redundancy > 0.9):     {len(easy)} ({len(easy)/len(all_props)*100:.1f}%)")
    print(f"    CRITICAL (criticality > 0.3): {len(critical)} ({len(critical)/len(all_props)*100:.1f}%)")
    print(f"    NOISE (alignment < 0.4):      {len(noise)} ({len(noise)/len(all_props)*100:.1f}%)")
    print(f"    BACKBONE (red>0.95, conf>0.9): {len(backbone)} ({len(backbone)/len(all_props)*100:.1f}%)")


# ============================================================
# III. CLAUSE DYNAMICS: How does a clause change during crystallization?
# ============================================================

def clause_dynamics():
    """
    Track each clause through crystallization:
    - When does it become satisfied (dead)?
    - When does it become critical (1 free literal)?
    - Does it ever become violated (0 free, unsatisfied)?
    """
    print("\n" + "=" * 70)
    print("CLAUSE DYNAMICS: Life of a clause during crystallization")
    print("=" * 70)

    random.seed(42); n = 12

    satisfied_at = []  # step when clause becomes satisfied
    critical_at = []   # step when clause has exactly 1 free literal
    ever_violated = 0
    total_clauses = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        fixed = {}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        clause_state = {ci: {'satisfied': None, 'critical': None, 'violated': False}
                       for ci in range(len(clauses))}

        for step, var in enumerate(order):
            sigma = bit_tension(clauses, n, var, fixed)
            fixed[var] = 1 if sigma >= 0 else 0

            # Check each clause
            for ci, clause in enumerate(clauses):
                if clause_state[ci]['satisfied'] is not None: continue

                satisfied = False; free = 0
                for v, s in clause:
                    if v in fixed:
                        if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                            satisfied = True; break
                    else:
                        free += 1

                if satisfied and clause_state[ci]['satisfied'] is None:
                    clause_state[ci]['satisfied'] = step
                elif not satisfied and free == 1 and clause_state[ci]['critical'] is None:
                    clause_state[ci]['critical'] = step
                elif not satisfied and free == 0:
                    clause_state[ci]['violated'] = True

        for ci in clause_state:
            total_clauses += 1
            if clause_state[ci]['satisfied'] is not None:
                satisfied_at.append(clause_state[ci]['satisfied'])
            if clause_state[ci]['critical'] is not None:
                critical_at.append(clause_state[ci]['critical'])
            if clause_state[ci]['violated']:
                ever_violated += 1

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Total clauses tracked: {total_clauses}")
    print(f"  Avg step satisfied: {mean(satisfied_at):.1f} / {n}")
    print(f"  Avg step critical:  {mean(critical_at):.1f} / {n}")
    print(f"  Ever violated: {ever_violated} ({ever_violated/total_clauses*100:.1f}%)")

    # Distribution of satisfaction time
    print(f"\n  When are clauses satisfied?")
    from collections import Counter
    dist = Counter(satisfied_at)
    for step in range(n+1):
        if dist[step] > 0:
            frac = dist[step] / len(satisfied_at) * 100
            bar = "█" * int(frac)
            print(f"    step {step:>2}: {frac:>5.1f}% {bar}")


# ============================================================
# IV. CLAUSE-CLAUSE INTERACTIONS
# ============================================================

def clause_interactions():
    """
    Two clauses can interact:
    - SUPPORTING: satisfying one helps satisfy the other
    - COMPETING: satisfying one makes the other harder
    - INDEPENDENT: no interaction
    """
    print("\n" + "=" * 70)
    print("CLAUSE-CLAUSE INTERACTIONS")
    print("=" * 70)

    random.seed(42); n = 12

    supporting = 0; competing = 0; independent = 0; total_pairs = 0

    for seed in range(50):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        for ci in range(len(clauses)):
            for cj in range(ci+1, len(clauses)):
                vars_i = set(v for v, s in clauses[ci])
                vars_j = set(v for v, s in clauses[cj])
                shared = vars_i & vars_j

                if not shared:
                    independent += 1
                    total_pairs += 1
                    continue

                total_pairs += 1

                # Do they want shared variables in SAME or OPPOSITE direction?
                signs_i = {v: s for v, s in clauses[ci]}
                signs_j = {v: s for v, s in clauses[cj]}

                agree = 0; disagree = 0
                for v in shared:
                    if signs_i[v] == signs_j[v]:
                        agree += 1
                    else:
                        disagree += 1

                if agree > disagree:
                    supporting += 1
                elif disagree > agree:
                    competing += 1
                else:
                    independent += 1

    print(f"\n  Total clause pairs: {total_pairs}")
    print(f"  Supporting (same signs): {supporting} ({supporting/total_pairs*100:.1f}%)")
    print(f"  Competing (opposite):    {competing} ({competing/total_pairs*100:.1f}%)")
    print(f"  Independent (no shared): {independent} ({independent/total_pairs*100:.1f}%)")

    # Does this predict anything?
    print(f"\n  Interpretation:")
    print(f"  Supporting clauses REINFORCE each other → bit between them is determined.")
    print(f"  Competing clauses FRUSTRATE each other → bit between them is ambiguous.")


# ============================================================
# V. CLAUSE IMPORTANCE: Which clauses matter?
# ============================================================

def clause_importance():
    """
    Remove each clause: does solve rate change?
    Important clause: removing it makes problem easier.
    Redundant clause: removing it changes nothing.
    Essential clause: removing it changes solution set.
    """
    print("\n" + "=" * 70)
    print("CLAUSE IMPORTANCE: Effect of removal")
    print("=" * 70)

    random.seed(42); n = 12

    importance_scores = []

    for seed in range(50):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        n_sol = len(solutions)

        for ci in range(len(clauses)):
            # Remove clause ci
            reduced = clauses[:ci] + clauses[ci+1:]
            reduced_solutions = find_solutions(reduced, n)
            n_sol_reduced = len(reduced_solutions)

            # How many NEW solutions appeared?
            new_solutions = n_sol_reduced - n_sol
            importance = new_solutions  # more new = clause was constraining

            props = clause_static(clauses, n, ci, solutions)
            importance_scores.append({
                'importance': importance,
                'new_sols': new_solutions,
                **props,
            })

    # What correlates with importance?
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    important = [s for s in importance_scores if s['importance'] > 0]
    redundant = [s for s in importance_scores if s['importance'] == 0]

    print(f"\n  Important clauses (removing adds solutions): {len(important)} "
          f"({len(important)/len(importance_scores)*100:.1f}%)")
    print(f"  Redundant (removing changes nothing): {len(redundant)} "
          f"({len(redundant)/len(importance_scores)*100:.1f}%)")

    if important and redundant:
        print(f"\n  {'property':>15} | {'important':>10} | {'redundant':>10} | {'ratio':>7}")
        print("  " + "-" * 50)
        for prop in ['alignment', 'coherence', 'confidence', 'criticality', 'redundancy']:
            imp_val = mean([s[prop] for s in important])
            red_val = mean([s[prop] for s in redundant])
            ratio = imp_val / red_val if red_val > 0 else 0
            sig = "★" if ratio > 1.3 or ratio < 0.77 else ""
            print(f"  {prop:>15} | {imp_val:>10.3f} | {red_val:>10.3f} | {ratio:>7.2f} {sig}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    classify_clauses()
    clause_dynamics()
    clause_interactions()
    clause_importance()
