"""
Silent Poison — HOW does a wrong fix corrupt invisibly?

Wrong fixes don't flip neighbor directions (1.08 vs 1.14 for right).
Yet they destroy solvability. WHAT changes?

Hypothesis candidates:
A. Magnitude: wrong fix WEAKENS tensions without flipping them
B. Consistency: wrong fix makes tensions less reliable (right answer shifts)
C. Landscape: wrong fix distorts the energy surface
D. Solution erasure: wrong fix eliminates solutions without visible signal
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
# A. Does wrong fix change MAGNITUDE of neighbor tensions?
# ============================================================

def magnitude_change(clauses, n, solutions):
    if not solutions: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    right_mag_changes = []
    wrong_mag_changes = []

    for var in range(n):
        base_mags = {v: abs(bit_tension(clauses, n, v)) for v in range(n) if v != var}

        for fix_val, label, target_list in [
            (correct_val[var], "right", right_mag_changes),
            (1 - correct_val[var], "wrong", wrong_mag_changes),
        ]:
            new_mags = {v: abs(bit_tension(clauses, n, v, {var: fix_val}))
                       for v in range(n) if v != var}

            for v in base_mags:
                delta = new_mags[v] - base_mags[v]
                target_list.append(delta)

    return right_mag_changes, wrong_mag_changes


# ============================================================
# B. Does wrong fix reduce ACCURACY of remaining tensions?
# ============================================================

def accuracy_after_fix(clauses, n, solutions):
    if not solutions: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    right_accs = []
    wrong_accs = []

    for var in range(n):
        for fix_val, target_list in [
            (correct_val[var], right_accs),
            (1 - correct_val[var], wrong_accs),
        ]:
            # Accuracy of remaining bits after fixing var
            correct = 0
            total = 0
            for v in range(n):
                if v == var: continue

                # Recompute correct_val given fixation
                # (some solutions may be eliminated)
                remaining_solutions = [
                    s for s in solutions
                    if s[var] == fix_val
                ]
                if not remaining_solutions:
                    # All solutions eliminated — this is catastrophic
                    target_list.append(0.0)
                    break

                new_prob_1 = sum(s[v] for s in remaining_solutions) / len(remaining_solutions)
                new_correct = 1 if new_prob_1 > 0.5 else 0

                sigma = bit_tension(clauses, n, v, {var: fix_val})
                pred = 1 if sigma >= 0 else 0
                if pred == new_correct:
                    correct += 1
                total += 1
            else:
                if total > 0:
                    target_list.append(correct / total)

    return right_accs, wrong_accs


# ============================================================
# C. Does wrong fix shift WHERE the correct answer IS?
# ============================================================

def answer_shift(clauses, n, solutions):
    """
    After fixing var=right: do remaining bits' correct values stay the same?
    After fixing var=wrong: do they SHIFT?

    If wrong fix shifts the correct answer without changing tension direction,
    THAT's the silent poison — tension points where the OLD answer was,
    but the answer MOVED.
    """
    if not solutions or len(solutions) < 2: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    right_shifts = []
    wrong_shifts = []

    for var in range(n):
        for fix_val, target_list in [
            (correct_val[var], right_shifts),
            (1 - correct_val[var], wrong_shifts),
        ]:
            remaining = [s for s in solutions if s[var] == fix_val]
            if not remaining:
                target_list.append(n)  # catastrophic shift
                continue

            new_prob_1 = [sum(s[v] for s in remaining)/len(remaining) for v in range(n)]
            new_correct = [1 if p > 0.5 else 0 for p in new_prob_1]

            # How many bits' correct value changed?
            shifts = sum(1 for v in range(n) if v != var and new_correct[v] != correct_val[v])
            target_list.append(shifts)

    return right_shifts, wrong_shifts


# ============================================================
# D. Solution count after fixation
# ============================================================

def solution_survival(clauses, n, solutions):
    if not solutions: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    right_survivals = []
    wrong_survivals = []

    for var in range(n):
        for fix_val, target_list in [
            (correct_val[var], right_survivals),
            (1 - correct_val[var], wrong_survivals),
        ]:
            remaining = sum(1 for s in solutions if s[var] == fix_val)
            target_list.append(remaining / len(solutions))

    return right_survivals, wrong_survivals


# ============================================================
# E. The INVISIBLE DISTORTION: tension accuracy vs shifted ground truth
# ============================================================

def invisible_distortion(clauses, n, solutions):
    """
    After wrong fix:
    1. Tension points in direction D
    2. ORIGINAL correct value was C_old
    3. NEW correct value (given remaining solutions) is C_new
    4. Was tension pointing at C_old or C_new?

    If tension → C_old but C_new ≠ C_old: SILENT POISON
    Tension looks "correct" by old standards but is wrong by new standards.
    """
    if not solutions or len(solutions) < 2: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    results = {
        'tension_tracks_old': 0,
        'tension_tracks_new': 0,
        'old_equals_new': 0,
        'old_differs_new': 0,
        'total': 0,
    }

    for var in range(n):
        wrong_val = 1 - correct_val[var]
        remaining = [s for s in solutions if s[var] == wrong_val]

        if not remaining:
            continue

        for v in range(n):
            if v == var: continue
            results['total'] += 1

            sigma = bit_tension(clauses, n, v, {var: wrong_val})
            tension_dir = 1 if sigma >= 0 else 0

            new_prob = sum(s[v] for s in remaining) / len(remaining)
            new_correct = 1 if new_prob > 0.5 else 0
            old_correct = correct_val[v]

            if old_correct == new_correct:
                results['old_equals_new'] += 1
            else:
                results['old_differs_new'] += 1

            if tension_dir == old_correct:
                results['tension_tracks_old'] += 1
            if tension_dir == new_correct:
                results['tension_tracks_new'] += 1

    return results


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

    print(f"Working with {len(instances)} instances (≥2 solutions each)")
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    # --- A: Magnitude ---
    print("\n" + "=" * 70)
    print("A. MAGNITUDE CHANGE after fixation")
    print("=" * 70)

    all_right_mag, all_wrong_mag = [], []
    for clauses, solutions in instances:
        r = magnitude_change(clauses, n, solutions)
        if r:
            all_right_mag.extend(r[0])
            all_wrong_mag.extend(r[1])

    print(f"\n  Right fix: avg Δ|σ| = {mean(all_right_mag):+.4f}")
    print(f"  Wrong fix: avg Δ|σ| = {mean(all_wrong_mag):+.4f}")

    # --- B: Accuracy ---
    print("\n" + "=" * 70)
    print("B. ACCURACY OF REMAINING after fixation")
    print("=" * 70)

    all_right_acc, all_wrong_acc = [], []
    for clauses, solutions in instances[:80]:
        r = accuracy_after_fix(clauses, n, solutions)
        if r:
            all_right_acc.extend(r[0])
            all_wrong_acc.extend(r[1])

    print(f"\n  Right fix: remaining accuracy = {mean(all_right_acc)*100:.1f}%")
    print(f"  Wrong fix: remaining accuracy = {mean(all_wrong_acc)*100:.1f}%")
    print(f"  Difference: {(mean(all_right_acc)-mean(all_wrong_acc))*100:+.1f}%")

    # --- C: Answer shift ---
    print("\n" + "=" * 70)
    print("C. ANSWER SHIFT: how many bits' correct value changes?")
    print("=" * 70)

    all_right_shift, all_wrong_shift = [], []
    for clauses, solutions in instances:
        r = answer_shift(clauses, n, solutions)
        if r:
            all_right_shift.extend(r[0])
            all_wrong_shift.extend(r[1])

    print(f"\n  Right fix: avg {mean(all_right_shift):.2f} bits shift answer")
    print(f"  Wrong fix: avg {mean(all_wrong_shift):.2f} bits shift answer")
    print(f"  Ratio: {mean(all_wrong_shift)/mean(all_right_shift):.2f}x"
          if mean(all_right_shift) > 0 else "")

    # --- D: Solution survival ---
    print("\n" + "=" * 70)
    print("D. SOLUTION SURVIVAL after fixation")
    print("=" * 70)

    all_right_surv, all_wrong_surv = [], []
    for clauses, solutions in instances:
        r = solution_survival(clauses, n, solutions)
        if r:
            all_right_surv.extend(r[0])
            all_wrong_surv.extend(r[1])

    print(f"\n  Right fix: {mean(all_right_surv)*100:.1f}% solutions survive")
    print(f"  Wrong fix: {mean(all_wrong_surv)*100:.1f}% solutions survive")

    # --- E: Invisible distortion ---
    print("\n" + "=" * 70)
    print("E. INVISIBLE DISTORTION: does tension track old or new answer?")
    print("=" * 70)

    combined = {
        'tension_tracks_old': 0, 'tension_tracks_new': 0,
        'old_equals_new': 0, 'old_differs_new': 0, 'total': 0,
    }

    for clauses, solutions in instances[:80]:
        r = invisible_distortion(clauses, n, solutions)
        if r:
            for k in combined:
                combined[k] += r[k]

    t = combined['total']
    if t > 0:
        print(f"\n  After WRONG fixation:")
        print(f"    Answer unchanged (old=new): "
              f"{combined['old_equals_new']/t*100:.1f}%")
        print(f"    Answer SHIFTED (old≠new):   "
              f"{combined['old_differs_new']/t*100:.1f}%")
        print(f"    Tension tracks OLD answer:   "
              f"{combined['tension_tracks_old']/t*100:.1f}%")
        print(f"    Tension tracks NEW answer:   "
              f"{combined['tension_tracks_new']/t*100:.1f}%")

        # The key question: when answer shifts, does tension follow?
        # Need to compute this specifically for shifted bits
        print(f"\n  WHEN ANSWER SHIFTS (the {combined['old_differs_new']} cases):")

    # Recompute for shifted cases only
    shifted_tracks_new = 0
    shifted_tracks_old = 0
    shifted_total = 0

    for clauses, solutions in instances[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            wrong_val = 1 - correct_val[var]
            remaining = [s for s in solutions if s[var] == wrong_val]
            if not remaining: continue

            for v in range(n):
                if v == var: continue
                new_prob = sum(s[v] for s in remaining)/len(remaining)
                new_correct = 1 if new_prob > 0.5 else 0
                old_correct = correct_val[v]

                if old_correct != new_correct:
                    shifted_total += 1
                    sigma = bit_tension(clauses, n, v, {var: wrong_val})
                    tension_dir = 1 if sigma >= 0 else 0
                    if tension_dir == new_correct: shifted_tracks_new += 1
                    if tension_dir == old_correct: shifted_tracks_old += 1

    if shifted_total > 0:
        print(f"    Tension follows to NEW answer: "
              f"{shifted_tracks_new/shifted_total*100:.1f}%")
        print(f"    Tension stuck on OLD answer:   "
              f"{shifted_tracks_old/shifted_total*100:.1f}%")
        print(f"    (Neither):                     "
              f"{(shifted_total-shifted_tracks_new-shifted_tracks_old)/shifted_total*100:.1f}%")
