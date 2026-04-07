"""
BIT ATTRACTION: Does a bit "know" its correct value and "pull" toward it?

Hypothesis: the correct value acts like an ATTRACTOR.
The bit doesn't just have σ — it has a FORCE FIELD
that pulls it toward the solution. We just can't see the force directly.

Tests:
1. ENERGY LANDSCAPE: is the correct value ALWAYS a local minimum?
2. BASIN OF ATTRACTION: how many starting points lead to correct value?
3. GRADIENT TOWARD SOLUTION: does σ consistently point toward correct?
4. ATTRACTION STRENGTH: is the pull STRONGER near the solution?
5. HIDDEN SIGNAL: is there a measurable quantity that ALWAYS
   points to the correct value, even when σ doesn't?
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
# 1. ENERGY LANDSCAPE: Is correct value always a local minimum?
# ============================================================

def energy_landscape():
    """
    For each bit: E(bit=correct) vs E(bit=wrong),
    where E = number of unsatisfied clauses with all OTHER bits
    at their correct values.

    If E(correct) < E(wrong) ALWAYS → solution is always a minimum.
    """
    print("=" * 70)
    print("1. Is the correct value ALWAYS energetically preferred?")
    print("=" * 70)

    random.seed(42); n = 12

    correct_lower = 0; wrong_lower = 0; equal = 0; total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        # Use first solution as "correct"
        sol = solutions[0]

        for var in range(n):
            total += 1

            # Fix all OTHER bits to their correct values
            fixed_correct = {v: sol[v] for v in range(n) if v != var}

            # Energy with var=correct
            a_correct = list(sol)
            e_correct = len(clauses) - evaluate(clauses, a_correct)

            # Energy with var=wrong
            a_wrong = list(sol)
            a_wrong[var] = 1 - sol[var]
            e_wrong = len(clauses) - evaluate(clauses, a_wrong)

            if e_correct < e_wrong: correct_lower += 1
            elif e_wrong < e_correct: wrong_lower += 1
            else: equal += 1

    print(f"\n  Correct value has lower energy: {correct_lower}/{total} ({correct_lower/total*100:.1f}%)")
    print(f"  Wrong value has lower energy:   {wrong_lower}/{total} ({wrong_lower/total*100:.1f}%)")
    print(f"  Equal energy:                   {equal}/{total} ({equal/total*100:.1f}%)")


# ============================================================
# 2. Does the bit "know" even when σ is wrong?
# ============================================================

def hidden_knowledge():
    """
    σ predicts wrong 30% of the time.
    For those WRONG bits: is there ANY signal pointing right?

    Test: for wrong-σ bits, compute various quantities and
    see if ANY of them point to correct value.

    If even ONE quantity always points right → the bit "knows"
    but our measurement (σ) is too crude.
    """
    print("\n" + "=" * 70)
    print("2. HIDDEN KNOWLEDGE: Do wrong-σ bits know their correct value?")
    print("=" * 70)

    random.seed(42); n = 12

    # For wrong-σ bits: what signals point to correct?
    signals = {
        'tension': [],        # σ direction (wrong by definition)
        'energy_diff': [],    # E(val=0) - E(val=1) sign
        'neighbor_vote': [],  # majority of neighbor tensions
        'clause_sat': [],     # which value satisfies more clauses?
        'full_dist': [],      # majority across contexts
        'self_cancel': [],    # σ + avg(nb) direction
    }

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            pred = 1 if tensions[var] >= 0 else 0
            actual = correct_val[var]
            if pred == actual: continue  # only look at WRONG bits

            # Signal 1: tension (wrong by selection)
            signals['tension'].append(0)  # always wrong here

            # Signal 2: energy difference
            a0 = [0]*n; a1 = [0]*n
            for v in range(n):
                val = random.randint(0,1)
                a0[v] = val; a1[v] = val
            a0[var] = 0; a1[var] = 1
            n_samples = 20
            e0_total = 0; e1_total = 0
            for _ in range(n_samples):
                for v in range(n):
                    if v != var:
                        a0[v] = random.randint(0,1)
                        a1[v] = a0[v]
                e0_total += len(clauses) - evaluate(clauses, a0)
                e1_total += len(clauses) - evaluate(clauses, a1)
            energy_pred = 1 if e1_total < e0_total else 0
            signals['energy_diff'].append(1 if energy_pred == actual else 0)

            # Signal 3: neighbor vote
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)
            nb_vote = sum(1 for nb in neighbors if tensions[nb] > 0) > len(neighbors)/2
            nb_pred = 1 if nb_vote else 0
            signals['neighbor_vote'].append(1 if nb_pred == actual else 0)

            # Signal 4: which value satisfies more clauses?
            # Fix all to tension-guided, then flip var
            base = [1 if tensions[v] >= 0 else 0 for v in range(n)]
            base[var] = 0
            sat_0 = evaluate(clauses, base)
            base[var] = 1
            sat_1 = evaluate(clauses, base)
            clause_pred = 1 if sat_1 > sat_0 else 0
            signals['clause_sat'].append(1 if clause_pred == actual else 0)

            # Signal 5: full distribution (from solutions)
            key_nbs = list(neighbors)[:4]
            ctx_votes = {}
            for sol in solutions:
                ctx = tuple(sol[nb] for nb in key_nbs)
                if ctx not in ctx_votes: ctx_votes[ctx] = [0,0]
                ctx_votes[ctx][sol[var]] += 1
            w1 = sum(c0+c1 for ctx,(c0,c1) in ctx_votes.items() if c1 > c0)
            w0 = sum(c0+c1 for ctx,(c0,c1) in ctx_votes.items() if c0 >= c1)
            dist_pred = 1 if w1 > w0 else 0
            signals['full_dist'].append(1 if dist_pred == actual else 0)

            # Signal 6: self-cancellation
            nb_avg = sum(tensions[nb] for nb in neighbors)/len(neighbors) if neighbors else 0
            sc = tensions[var] + nb_avg
            sc_pred = 1 if sc >= 0 else 0
            signals['self_cancel'].append(1 if sc_pred == actual else 0)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  For bits where σ is WRONG (n={len(signals['tension'])}):")
    print(f"  Which signals STILL point to correct value?")
    print(f"\n  {'signal':>15} | {'% correct':>9} | meaning")
    print("  " + "-" * 50)
    for name in ['tension', 'energy_diff', 'neighbor_vote', 'clause_sat',
                 'self_cancel', 'full_dist']:
        pct = mean(signals[name]) * 100
        if pct > 55:
            meaning = "← KNOWS! ★"
        elif pct > 45:
            meaning = "(random)"
        else:
            meaning = "(anti)"
        print(f"  {name:>15} | {pct:>8.1f}% | {meaning}")


# ============================================================
# 3. ATTRACTION STRENGTH: Does the pull get stronger near solution?
# ============================================================

def attraction_strength():
    """
    During crystallization with CORRECT values:
    Does |σ| increase MORE QUICKLY as we approach the solution?

    If yes → there's an attraction field that strengthens near solution.
    Like gravity: stronger as you get closer.
    """
    print("\n" + "=" * 70)
    print("3. ATTRACTION: Does pull strengthen near solution?")
    print("=" * 70)

    random.seed(42); n = 12

    sigma_by_distance = {}  # distance_to_solution → avg |σ|

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        sol = solutions[0]  # reference solution
        correct_val = [sol[v] for v in range(n)]

        # Start from RANDOM assignment, move toward solution
        # At each step: fix one more bit to correct value
        # Measure avg |σ| of unfixed bits → does it grow?

        order = list(range(n))
        random.shuffle(order)

        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break

            distance = len(unfixed)

            # Avg |σ| of unfixed bits, measured with fixed context
            avg_sigma = sum(abs(bit_tension(clauses, n, v, fixed)) for v in unfixed) / len(unfixed)

            # How many unfixed point CORRECTLY?
            correct_dir = sum(1 for v in unfixed
                            if (1 if bit_tension(clauses, n, v, fixed) >= 0 else 0) == correct_val[v])
            acc = correct_dir / len(unfixed)

            if distance not in sigma_by_distance:
                sigma_by_distance[distance] = {'sigma': [], 'accuracy': []}
            sigma_by_distance[distance]['sigma'].append(avg_sigma)
            sigma_by_distance[distance]['accuracy'].append(acc)

            # Fix next bit to CORRECT value
            var = order[step]
            fixed[var] = correct_val[var]

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'distance':>8} | {'avg |σ|':>8} | {'accuracy':>8} | attraction")
    print("  " + "-" * 45)

    for d in sorted(sigma_by_distance.keys(), reverse=True):
        data = sigma_by_distance[d]
        s = mean(data['sigma'])
        a = mean(data['accuracy'])
        bar = "→" * int(a * 20)
        print(f"  {d:>8} | {s:>8.3f} | {a*100:>7.1f}% | {bar}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    energy_landscape()
    hidden_knowledge()
    attraction_strength()
