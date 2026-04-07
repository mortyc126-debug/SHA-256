"""
Exhaustive Local Bit Analysis — Leave nothing behind.

Before going global, verify we've extracted ALL local information.

Categories we've covered:
- Static: tension, frustration, degree, polarity, criticality, freedom
- Relational: coupling, agreement, bridgeness, cliqueness
- Dynamic: sensitivity, elasticity, cascade, brittleness
- Info: entropy, conditional entropy, informativeness, predictability
- Topological: centrality, betweenness, clustering, eccentricity
- Energy: potential, kinetic, binding, mass, barrier
- Wave: oscillation, damping, resonance
- Structural: clause overlap, sign complexity, diversity, redundancy

What we HAVEN'T tried:
1. TEMPORAL patterns: ORDER of clause appearance (does it matter?)
2. SIGN SEQUENCES: not just pos/neg count, but the pattern
3. CONSTRAINT TIGHTNESS: how close is each clause to being violated?
4. VARIABLE SUBSTITUTION: if I replace this bit with another, what happens?
5. DUAL VIEW: look from the CLAUSE perspective, not the bit perspective
6. SECOND-ORDER TENSION: tension of tension (how tension changes with small perturbations)
7. BIT SYMMETRY: is this bit interchangeable with any other?
8. PATH COUNTING: how many distinct paths connect this bit to solutions?
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
        already_sat = False
        remaining = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
            else:
                remaining.append((v, s))
        if already_sat:
            continue
        for v, s in remaining:
            if v == var:
                w = 1.0 / max(1, len(remaining))
                if s == 1:
                    p1 += w
                else:
                    p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None:
        fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                sat = False
                rem = []
                vs = None
                for v, s in clause:
                    if v in fixed:
                        if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                            sat = True; break
                    else:
                        rem.append((v, s))
                        if v == var: vs = s
                if sat or vs is None: continue
                oh = 0.0
                for v, s in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if s == 1 else (1-t)/2
                    oh = 1 - (1-oh)*(1-p)
                need = 1.0 - oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1 + push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# NEW PROPERTY 1: Constraint tightness
# ============================================================
def constraint_tightness(clauses, n, var):
    """
    For each clause containing var: how many OTHER ways can it be satisfied?
    Tight clause = only 1 way (needs var). Loose = many ways.
    Average tightness = how "needed" is this bit overall.
    """
    tightnesses = []
    for clause in clauses:
        has_var = False
        other_count = 0
        for v, s in clause:
            if v == var:
                has_var = True
            else:
                other_count += 1
        if has_var:
            # Each other literal has ~50% chance of satisfying
            # Expected satisfaction without var: 1 - 0.5^other_count
            prob_sat_without = 1.0 - (0.5 ** other_count)
            tightness = 1.0 - prob_sat_without  # how much clause depends on var
            tightnesses.append(tightness)
    return sum(tightnesses) / len(tightnesses) if tightnesses else 0


# ============================================================
# NEW PROPERTY 2: Second-order tension (curvature)
# ============================================================
def tension_curvature(clauses, n, var):
    """
    How does tension CHANGE when we slightly perturb the system?

    Compute tension under many 1-bit perturbations.
    Curvature = variance of tension across perturbations.
    High curvature = tension is unstable (easily influenced).
    Low curvature = tension is robust.
    """
    base = bit_tension(clauses, n, var)
    perturbed = []

    for other in range(n):
        if other == var:
            continue
        for val in [0, 1]:
            t = bit_tension(clauses, n, var, {other: val})
            perturbed.append(t)

    if not perturbed:
        return 0.0

    mean = sum(perturbed) / len(perturbed)
    variance = sum((t - mean)**2 for t in perturbed) / len(perturbed)
    return math.sqrt(variance)


# ============================================================
# NEW PROPERTY 3: Clause perspective — how does this clause VIEW the bit?
# ============================================================
def clause_need_spectrum(clauses, n, var):
    """
    For each clause containing var, compute how desperately it needs var.
    Return the SPECTRUM: min need, max need, spread.

    Some clauses barely need var (loose). Others desperately need it (tight).
    The SPREAD tells us if var's importance is uniform or variable.
    """
    needs = []
    for clause in clauses:
        var_sign = None
        others = []
        for v, s in clause:
            if v == var:
                var_sign = s
            else:
                others.append((v, s))

        if var_sign is None:
            continue

        # How much does this clause need var?
        # Based on other vars' tensions
        prob_others_sat = 0.0
        for v, s in others:
            t = bit_tension(clauses, n, v)
            p = (1+t)/2 if s == 1 else (1-t)/2
            prob_others_sat = 1 - (1-prob_others_sat)*(1-p)

        need = 1.0 - prob_others_sat
        needs.append(need)

    if not needs:
        return 0, 0, 0, 0

    return min(needs), max(needs), max(needs)-min(needs), sum(needs)/len(needs)


# ============================================================
# NEW PROPERTY 4: Bit replaceability
# ============================================================
def replaceability(clauses, n, var):
    """
    If we REMOVE this bit from all its clauses,
    how much harder does the problem become?

    Measured as: change in total tension of remaining bits.
    """
    # Reduced clauses: remove var from all clauses
    reduced = []
    for clause in clauses:
        has_var = any(v == var for v, s in clause)
        if has_var:
            new_clause = [(v, s) for v, s in clause if v != var]
            if new_clause:  # don't add empty clauses
                reduced.append(new_clause)
        else:
            reduced.append(clause)

    # Total tension without var
    total_t_reduced = sum(abs(bit_tension(reduced, n, v))
                          for v in range(n) if v != var)

    # Total tension with var
    total_t_full = sum(abs(bit_tension(clauses, n, v))
                       for v in range(n) if v != var)

    return total_t_full - total_t_reduced  # positive = var helps others


# ============================================================
# NEW PROPERTY 5: Solution-path density
# ============================================================
def solution_path_density(clauses, n, var, n_samples=100):
    """
    Sample random assignments. For each, flip ONLY this bit.
    How often does flipping this bit change sat → unsat or unsat → sat?

    High flip-sensitivity = bit is on the "boundary" of solution space.
    """
    boundary_count = 0

    for _ in range(n_samples):
        assignment = [random.randint(0, 1) for _ in range(n)]
        sat_orig = evaluate(clauses, assignment) == len(clauses)

        assignment[var] = 1 - assignment[var]
        sat_flip = evaluate(clauses, assignment) == len(clauses)

        if sat_orig != sat_flip:
            boundary_count += 1

    return boundary_count / n_samples


# ============================================================
# NEW PROPERTY 6: Tension under RANDOM partial fixation
# ============================================================
def tension_stability(clauses, n, var, n_samples=30):
    """
    Fix random subsets of other bits to random values.
    Measure tension of var each time.

    Stability = how consistent is the DIRECTION of tension?
    If tension always points the same way regardless of context → stable.
    If it flips direction → unstable.
    """
    directions = []  # +1 or -1
    magnitudes = []

    for _ in range(n_samples):
        fixed = {}
        for v in range(n):
            if v != var and random.random() < 0.3:
                fixed[v] = random.randint(0, 1)

        t = bit_tension(clauses, n, var, fixed)
        if abs(t) > 0.01:
            directions.append(1 if t > 0 else -1)
            magnitudes.append(abs(t))

    if not directions:
        return 0, 0

    # Directional consistency: what fraction agree with majority?
    pos = sum(1 for d in directions if d == 1)
    consistency = max(pos, len(directions) - pos) / len(directions)

    avg_magnitude = sum(magnitudes) / len(magnitudes)

    return consistency, avg_magnitude


# ============================================================
# MEASURE ALL AND FIND GAPS
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 80)
    print("EXHAUSTIVE LOCAL SEARCH: 6 new properties")
    print("=" * 80)

    v4_correct = []
    v4_gap = []

    for seed in range(200):
        clauses = random_3sat(12, int(4.27 * 12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        optimal = [max(p, 1-p) for p in prob_1]

        v4_tensions = tension_v4(clauses, 12, {}, 10)

        for var in range(12):
            v4_pred = 1 if v4_tensions.get(var, 0) >= 0 else 0
            actual = correct_val[var]

            tightness = constraint_tightness(clauses, 12, var)
            curvature = tension_curvature(clauses, 12, var)
            need_min, need_max, need_spread, need_avg = clause_need_spectrum(clauses, 12, var)
            replace = replaceability(clauses, 12, var)
            boundary = solution_path_density(clauses, 12, var, 50)
            dir_consistency, ctx_magnitude = tension_stability(clauses, 12, var, 20)

            profile = {
                'tightness': tightness,
                'curvature': curvature,
                'need_spread': need_spread,
                'need_avg': need_avg,
                'replaceability': replace,
                'boundary_sensitivity': boundary,
                'direction_consistency': dir_consistency,
                'context_magnitude': ctx_magnitude,
            }

            if v4_pred == actual:
                v4_correct.append(profile)
            elif optimal[var] > 0.6:
                v4_gap.append(profile)

    print(f"\n  {len(v4_correct)} v4-correct, {len(v4_gap)} v4-gap")

    mean = lambda lst: sum(lst) / len(lst) if lst else 0

    properties = list(v4_correct[0].keys()) if v4_correct else []

    print(f"\n  {'property':>25} | {'CORRECT':>10} | {'GAP':>10} | {'ratio':>7} | sig")
    print("  " + "-" * 75)

    for prop in properties:
        c = mean([p[prop] for p in v4_correct])
        g = mean([p[prop] for p in v4_gap])

        if abs(c) > 0.001:
            ratio = g / c
        elif abs(g) > 0.001:
            ratio = 999
        else:
            ratio = 1.0

        sig = ""
        if ratio > 1.5 or ratio < 0.67:
            sig = "*** STRONG ***"
        elif ratio > 1.2 or ratio < 0.83:
            sig = "* notable *"

        print(f"  {prop:>25} | {c:>10.4f} | {g:>10.4f} | {ratio:>7.2f} | {sig}")

    # Test the best discriminator as a filter
    print("\n" + "=" * 80)
    print("FILTER TEST: Can any new property improve v4?")
    print("=" * 80)

    for prop in properties:
        c_vals = [p[prop] for p in v4_correct]
        g_vals = [p[prop] for p in v4_gap]
        c_mean = mean(c_vals)
        g_mean = mean(g_vals)

        if abs(c_mean - g_mean) < 0.001:
            continue

        # Try using this property as a confidence modifier
        # If gap bits have LOWER value: low value = distrust
        # If gap bits have HIGHER value: high value = distrust
        direction = "low" if g_mean < c_mean else "high"

        all_profiles = v4_correct + v4_gap
        all_vals = [p[prop] for p in all_profiles]
        all_vals.sort()

        # Try filtering at median
        median = all_vals[len(all_vals) // 2]

        if direction == "low":
            trusted = [i for i, p in enumerate(all_profiles) if p[prop] > median]
        else:
            trusted = [i for i, p in enumerate(all_profiles) if p[prop] < median]

        trusted_correct = sum(1 for i in trusted if i < len(v4_correct))
        trusted_total = len(trusted)

        if trusted_total > 0:
            acc = trusted_correct / trusted_total * 100
            baseline_acc = len(v4_correct) / (len(v4_correct) + len(v4_gap)) * 100
            improvement = acc - baseline_acc
            if abs(improvement) > 1:
                print(f"  {prop:>25}: trust {direction} → {acc:.1f}% "
                      f"(baseline {baseline_acc:.1f}%, Δ={improvement:+.1f}%)")
