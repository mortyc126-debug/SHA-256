"""
SPACE CARTOGRAPHY: What spaces exist between/beyond clause and solution?

Known spaces:
1. Clause space: σ_clause (tension) — 71%
2. Solution space: σ_solution (marginal) — 88%
3. Gap space: σ_clause - σ_solution — process info

What OTHER spaces might exist?

4. ENERGY space: how many clauses does assignment satisfy?
   Not binary SAT/UNSAT but continuous 0..m.
5. CONSTRAINT FLOW space: which direction do clauses "pull"?
   Not vote count but FORCE direction.
6. DUAL space: the problem from the CLAUSE perspective, not bit perspective.
   Each clause has a state: how close to being violated?
7. TRAJECTORY space: the path through crystallization.
   Not endpoint (solution) but path itself.
8. COUNTERFACTUAL space: the difference between two possible futures.
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
# SPACE 4: ENERGY LANDSCAPE
# ============================================================

def energy_space():
    """
    For each bit: E(bit=0) vs E(bit=1)
    where E = number of UNSATISFIED clauses for a random completion.

    This is different from tension:
    - Tension: counts clause SIGNS (structural)
    - Energy: counts actual VIOLATIONS (functional)
    """
    print("=" * 70)
    print("SPACE 4: ENERGY LANDSCAPE")
    print("=" * 70)

    random.seed(42); n = 12

    energy_correct = 0; tension_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            total += 1

            # Tension
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                tension_correct += 1

            # Energy: average violations for var=0 vs var=1
            e0 = 0; e1 = 0; n_samples = 30
            for _ in range(n_samples):
                assignment = [random.randint(0,1) for _ in range(n)]
                assignment[var] = 0
                e0 += len(clauses) - evaluate(clauses, assignment)
                assignment[var] = 1
                e1 += len(clauses) - evaluate(clauses, assignment)
            e0 /= n_samples; e1 /= n_samples

            energy_pred = 1 if e1 < e0 else 0  # pick lower energy
            if energy_pred == correct_val[var]:
                energy_correct += 1

    print(f"\n  Tension:         {tension_correct/total*100:.1f}%")
    print(f"  Energy landscape: {energy_correct/total*100:.1f}%")


# ============================================================
# SPACE 6: DUAL SPACE (clause perspective)
# ============================================================

def dual_space():
    """
    Instead of "what does each BIT want", ask:
    "what does each CLAUSE need?"

    For each clause: which of its variables is most CRITICAL?
    The clause's "most needed" variable should be set to satisfy it.

    Clause tension: how desperate is this clause?
    = 1 / (number of ways it can still be satisfied)

    A bit's DUAL signal = sum of clause desperation across its clauses.
    """
    print("\n" + "=" * 70)
    print("SPACE 6: DUAL SPACE (clause perspective)")
    print("=" * 70)

    random.seed(42); n = 12

    dual_correct = 0; tension_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Clause desperation: for each clause, how many literals
        # have tension pointing the RIGHT way (to satisfy)?
        clause_desperation = []
        for ci, clause in enumerate(clauses):
            n_helping = 0
            for v, s in clause:
                sigma = bit_tension(clauses, n, v)
                # Would tension-guided assignment satisfy this literal?
                if (s == 1 and sigma >= 0) or (s == -1 and sigma < 0):
                    n_helping += 1
            desperation = 1.0 / max(n_helping, 0.1)
            clause_desperation.append(desperation)

        # Dual signal per bit: weighted by clause desperation
        for var in range(n):
            total += 1

            # Tension
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                tension_correct += 1

            # Dual signal
            push_1 = 0; push_0 = 0
            for ci, clause in enumerate(clauses):
                for v, s in clause:
                    if v == var:
                        w = clause_desperation[ci]
                        if s == 1: push_1 += w
                        else: push_0 += w

            dual_pred = 1 if push_1 >= push_0 else 0
            if dual_pred == correct_val[var]:
                dual_correct += 1

    print(f"\n  Tension:     {tension_correct/total*100:.1f}%")
    print(f"  Dual signal: {dual_correct/total*100:.1f}%")


# ============================================================
# SPACE 7: TRAJECTORY SPACE
# ============================================================

def trajectory_space():
    """
    During crystallization, each bit's tension EVOLVES.
    The trajectory σ_i(t=0), σ_i(t=1), ... encodes information.

    What patterns in the trajectory predict correctness?
    - Monotonically growing |σ| → confident, probably correct
    - Oscillating σ → uncertain, probably wrong
    - Early plateau → quickly determined, correct
    """
    print("\n" + "=" * 70)
    print("SPACE 7: TRAJECTORY PATTERNS")
    print("=" * 70)

    random.seed(42); n = 12

    correct_monotone = 0; correct_total = 0
    wrong_monotone = 0; wrong_total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Track tension of each bit through crystallization
        trajectories = {v: [] for v in range(n)}
        fixed = {}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        for step_var in order:
            # Record tension of all unfixed bits
            for v in range(n):
                if v not in fixed:
                    trajectories[v].append(bit_tension(clauses, n, v, fixed))

            sigma = bit_tension(clauses, n, step_var, fixed)
            fixed[step_var] = 1 if sigma >= 0 else 0

        # Analyze trajectories
        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 3: continue

            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            # Is trajectory monotonically increasing in |σ|?
            abs_traj = [abs(t) for t in traj]
            monotone = all(abs_traj[i] <= abs_traj[i+1] + 0.05
                          for i in range(len(abs_traj)-1))

            # Sign consistency: does σ stay on the same side?
            if len(traj) > 1:
                sign_changes = sum(1 for i in range(1, len(traj))
                                  if traj[i] * traj[i-1] < 0)
                consistent = sign_changes == 0
            else:
                consistent = True

            if is_correct:
                correct_total += 1
                if monotone: correct_monotone += 1
            else:
                wrong_total += 1
                if monotone: wrong_monotone += 1

    cm = correct_monotone/correct_total*100 if correct_total > 0 else 0
    wm = wrong_monotone/wrong_total*100 if wrong_total > 0 else 0
    print(f"\n  Monotone trajectories:")
    print(f"    Correct bits: {cm:.1f}%")
    print(f"    Wrong bits:   {wm:.1f}%")
    print(f"    Ratio: {cm/wm:.2f}" if wm > 0 else "")


# ============================================================
# SPACE 8: COUNTERFACTUAL GAP
# ============================================================

def counterfactual_space():
    """
    For each bit: compute σ(bit=0 world) and σ(bit=1 world)
    for ALL OTHER bits.

    The DIFFERENCE between the two worlds = counterfactual vector.
    This is a n-dimensional vector for each bit.

    Does the counterfactual vector contain NEW information?
    """
    print("\n" + "=" * 70)
    print("SPACE 8: COUNTERFACTUAL VECTORS")
    print("=" * 70)

    random.seed(42); n = 12

    cf_correct = 0; tension_correct = 0; total = 0

    for seed in range(80):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            total += 1

            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                tension_correct += 1

            # Counterfactual vector: how does fixing var affect EACH other bit?
            cf_vector_0 = [bit_tension(clauses, n, v, {var: 0}) for v in range(n)]
            cf_vector_1 = [bit_tension(clauses, n, v, {var: 1}) for v in range(n)]

            # Difference
            cf_diff = [cf_vector_1[v] - cf_vector_0[v] for v in range(n)]

            # Signal: how much do OTHER bits "prefer" var=1 vs var=0?
            # If fixing var=1 makes neighbors MORE confident → var=1 is better
            conf_boost_1 = sum(abs(cf_vector_1[v]) for v in range(n) if v != var)
            conf_boost_0 = sum(abs(cf_vector_0[v]) for v in range(n) if v != var)

            # Also: do neighbors AGREE more with each other when var=1 vs var=0?
            # Agreement = how many pairs of neighbors have same sign
            agree_1 = sum(1 for i in range(n) for j in range(i+1,n)
                         if i != var and j != var and cf_vector_1[i]*cf_vector_1[j] > 0)
            agree_0 = sum(1 for i in range(n) for j in range(i+1,n)
                         if i != var and j != var and cf_vector_0[i]*cf_vector_0[j] > 0)

            # Combined counterfactual signal
            cf_signal = (conf_boost_1 - conf_boost_0) + 0.01 * (agree_1 - agree_0)
            cf_pred = 1 if cf_signal > 0 else 0

            if cf_pred == correct_val[var]:
                cf_correct += 1

    print(f"\n  Tension:              {tension_correct/total*100:.1f}%")
    print(f"  Counterfactual vector: {cf_correct/total*100:.1f}%")
    print(f"  Improvement:           {(cf_correct-tension_correct)/total*100:+.1f}%")


# ============================================================
# SPACE 9: INTERFERENCE SPACE
# ============================================================

def interference_space():
    """
    Two bits i and j. Their tensions σ_i and σ_j.
    When we fix BOTH: is the result σ_i(fixed j) + σ_j(fixed i)?
    Or is there an INTERFERENCE term?

    interference(i,j) = σ_actual(i,j fixed) - [σ_i(j fixed) + σ_j(i fixed) - σ_base]

    If interference ≠ 0 → the two bits interact NONLINEARLY.
    This is a new space: the space of PAIRWISE INTERFERENCE.
    """
    print("\n" + "=" * 70)
    print("SPACE 9: INTERFERENCE (pairwise nonlinearity)")
    print("=" * 70)

    random.seed(42); n = 12

    interferences_correct = []
    interferences_wrong = []

    for seed in range(80):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            # Measure interference with each neighbor
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            total_interference = 0
            for nb in list(neighbors)[:5]:
                sigma_nb = bit_tension(clauses, n, nb)
                val_var = 1 if sigma >= 0 else 0
                val_nb = 1 if sigma_nb >= 0 else 0

                # Individual effects
                sigma_var_given_nb = bit_tension(clauses, n, var, {nb: val_nb})
                sigma_nb_given_var = bit_tension(clauses, n, nb, {var: val_var})

                # Joint effect (on a third bit)
                for k in neighbors:
                    if k == nb or k == var: continue
                    s_base = bit_tension(clauses, n, k)
                    s_var = bit_tension(clauses, n, k, {var: val_var})
                    s_nb = bit_tension(clauses, n, k, {nb: val_nb})
                    s_both = bit_tension(clauses, n, k, {var: val_var, nb: val_nb})

                    # Interference = actual - predicted (linear superposition)
                    predicted = s_var + s_nb - s_base
                    interference = s_both - predicted
                    total_interference += abs(interference)
                    break  # just one k per (var, nb) pair

            if is_correct:
                interferences_correct.append(total_interference)
            else:
                interferences_wrong.append(total_interference)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg interference:")
    print(f"    Correct bits: {mean(interferences_correct):.4f}")
    print(f"    Wrong bits:   {mean(interferences_wrong):.4f}")
    if mean(interferences_correct) > 0:
        ratio = mean(interferences_wrong)/mean(interferences_correct)
        print(f"    Ratio: {ratio:.2f}")
        if ratio > 1.2:
            print(f"    → Wrong bits have MORE interference!")
        elif ratio < 0.8:
            print(f"    → Wrong bits have LESS interference!")
        else:
            print(f"    → Similar interference for both.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    energy_space()
    dual_space()
    trajectory_space()
    counterfactual_space()
    interference_space()
