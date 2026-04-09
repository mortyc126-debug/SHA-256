"""
FINDING THE PASS: How to satisfy keystones without knowing the solution
═══════════════════════════════════════════════════════════════════════

Each keystone has 1 saving literal (the "pass") and 2 fighting literals.
If we know WHICH literal is the pass → we satisfy the keystone
→ the wall is transparent → no freezing.

The pass = the literal whose sign matches the solution.

EXPERIMENTS:
1. Can tension identify the saving literal?
2. What properties distinguish saving from fighting literals?
3. If we satisfy ALL keystones' saving literals → does core melt?
4. The PASS SPACE: set of valid passes through all walls
5. Can we enumerate passes without knowing the solution?
6. What is the pass from the CLAUSE's perspective?
"""

import numpy as np
import random
import math
from collections import Counter
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def get_frozen(clauses, n, solutions):
    return set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)


def find_keystones(clauses, n, solutions, frozen):
    keystones = []
    for ci in range(len(clauses)):
        reduced = clauses[:ci] + clauses[ci+1:]
        rsols = find_solutions(reduced, n)
        if len(rsols) < 2: continue
        rf = get_frozen(reduced, n, rsols)
        unfrozen = frozen - rf
        if unfrozen:
            keystones.append({
                'idx': ci, 'clause': clauses[ci], 'unfreezes': unfrozen,
                'power': len(unfrozen),
            })
    return keystones


# ============================================================
# 1. Can tension identify the saving literal?
# ============================================================

def study_tension_identifies_pass():
    print("=" * 70)
    print("1. Can tension find the PASS (saving literal)?")
    print("=" * 70)

    random.seed(42)
    n = 14

    tension_finds_pass = 0
    tension_total = 0
    pass_tension_vals = []
    fight_tension_vals = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]

        # Compute tensions
        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        for k in keystones:
            clause = k['clause']

            # Find the saving literal
            saving_idx = -1
            for j, (v, s) in enumerate(clause):
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                    saving_idx = j
                    break

            if saving_idx < 0: continue  # shouldn't happen
            tension_total += 1

            # Can tension identify it?
            # The saving literal's var should have tension MATCHING the sign
            v_save, s_save = clause[saving_idx]
            tension_matches_save = (tensions[v_save] > 0 and s_save == 1) or \
                                   (tensions[v_save] < 0 and s_save == -1)

            # Score each literal by "agreement with tension"
            scores = []
            for j, (v, s) in enumerate(clause):
                # Agreement: tension direction matches literal sign
                if s == 1:
                    agreement = tensions[v]  # positive = agrees
                else:
                    agreement = -tensions[v]  # negative sign, so flip
                scores.append((agreement, j))

                if j == saving_idx:
                    pass_tension_vals.append(agreement)
                else:
                    fight_tension_vals.append(agreement)

            # The literal with HIGHEST agreement = predicted pass
            predicted_pass = max(scores, key=lambda x: x[0])[1]
            if predicted_pass == saving_idx:
                tension_finds_pass += 1

        if tension_total >= 100: break

    if tension_total > 0:
        print(f"\n  {tension_total} keystones analyzed:")
        print(f"  Tension identifies the pass: {tension_finds_pass}/{tension_total} "
              f"= {100*tension_finds_pass/tension_total:.1f}%")
        print(f"  Random guess would be: 33.3%")
        print(f"  Improvement: {tension_finds_pass/tension_total / (1/3):.2f}×")

    if pass_tension_vals and fight_tension_vals:
        print(f"\n  Tension agreement score:")
        print(f"    PASS (saving):    {np.mean(pass_tension_vals):+.4f}")
        print(f"    FIGHT (blocking): {np.mean(fight_tension_vals):+.4f}")
        print(f"    Difference:       {np.mean(pass_tension_vals)-np.mean(fight_tension_vals):+.4f}")

        # The pass literal has HIGHER agreement with tension
        if np.mean(pass_tension_vals) > np.mean(fight_tension_vals):
            print(f"    → PASS has higher tension agreement ← SIGNAL EXISTS")
        else:
            print(f"    → No clear signal")


# ============================================================
# 2. Properties of saving vs fighting literals
# ============================================================

def study_pass_properties():
    print("\n" + "=" * 70)
    print("2. Properties of PASS vs FIGHT literals")
    print("=" * 70)

    random.seed(42)
    n = 14

    pass_data = {'degree': [], 'abs_tension': [], 'is_frozen': []}
    fight_data = {'degree': [], 'abs_tension': [], 'is_frozen': []}

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]
        tensions = {}
        degrees = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0
            degrees[v] = sum(1 for c in clauses for vi,si in c if vi==v)

        for k in keystones:
            for j, (v, s) in enumerate(k['clause']):
                is_pass = (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
                data = pass_data if is_pass else fight_data
                data['degree'].append(degrees[v])
                data['abs_tension'].append(abs(tensions[v]))
                data['is_frozen'].append(v in frozen)

        if len(pass_data['degree']) >= 100: break

    if pass_data['degree']:
        print(f"\n  {'property':>15} | {'PASS':>8} | {'FIGHT':>8} | {'ratio':>6}")
        print(f"  " + "-" * 45)
        for prop in ['degree', 'abs_tension', 'is_frozen']:
            mp = np.mean(pass_data[prop])
            mf = np.mean(fight_data[prop])
            ratio = mp / max(mf, 0.001)
            disc = " ←" if abs(ratio - 1) > 0.15 else ""
            print(f"  {prop:>15} | {mp:>8.3f} | {mf:>8.3f} | {ratio:>6.2f}{disc}")


# ============================================================
# 3. If we give the CORRECT PASS → does core melt?
# ============================================================

def study_oracle_pass():
    print("\n" + "=" * 70)
    print("3. ORACLE PASS: Fix saving literals → core melts?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17200000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]
        m = len(clauses)

        print(f"\n  n={n}, seed={seed}: {len(frozen)} frozen, "
              f"{len(keystones)} keystones")

        # Collect all saving literal vars from all keystones
        pass_vars = {}  # var → value that satisfies the keystone
        for k in keystones:
            for v, s in k['clause']:
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                    pass_vars[v] = sol[v]

        print(f"  Pass variables: {len(pass_vars)} (vars that save keystones)")
        print(f"  Pass vars: {pass_vars}")

        # Fix ONLY pass vars → run UP → count remaining frozen
        fixed = dict(pass_vars)
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                sat = False; free_lits = []
                for v, s in clause:
                    if v in fixed:
                        if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                            sat = True; break
                    else:
                        free_lits.append((v, s))
                if sat: continue
                if len(free_lits) == 1:
                    fv, fs = free_lits[0]
                    fixed[fv] = 1 if fs == 1 else 0
                    changed = True

        n_fixed = len(fixed)
        n_correct = sum(1 for v in fixed if fixed[v] == sol[v])

        # Evaluate
        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)

        print(f"\n  After fixing pass vars + UP cascade:")
        print(f"    Fixed: {n_fixed}/{n} variables")
        print(f"    Correct: {n_correct}/{n_fixed}")
        print(f"    Satisfied: {sat}/{m} clauses")

        if sat == m:
            print(f"    → SOLVED by fixing just {len(pass_vars)} pass variables!")
        else:
            print(f"    → Not solved, but {100*sat/m:.1f}% satisfied")

        # How many pass vars are needed? Try fixing them one at a time
        print(f"\n  Progressive pass fixing:")
        fixed = {}
        pass_list = sorted(pass_vars.items(),
                          key=lambda x: sum(1 for k in keystones
                                           if x[0] in dict(k['clause'])),
                          reverse=True)

        for i, (v, val) in enumerate(pass_list):
            fixed[v] = val
            # UP
            f2 = dict(fixed)
            changed = True
            while changed:
                changed = False
                for clause in clauses:
                    sat = False; free_lits = []
                    for vi, si in clause:
                        if vi in f2:
                            if (si==1 and f2[vi]==1) or (si==-1 and f2[vi]==0):
                                sat = True; break
                        else:
                            free_lits.append((vi, si))
                    if sat: continue
                    if len(free_lits) == 1:
                        fv, fs = free_lits[0]
                        f2[fv] = 1 if fs == 1 else 0
                        changed = True

            a = [f2.get(v2, 0) for v2 in range(n)]
            s = evaluate(clauses, a)
            correct = sum(1 for v2 in f2 if f2[v2] == sol[v2])
            print(f"    Fix {i+1} pass vars → "
                  f"{len(f2)} fixed, {correct} correct, {s}/{m} sat")
            if s == m:
                print(f"    → SOLVED after {i+1} pass variables!")
                break

        break


# ============================================================
# 4. PASS SPACE: The set of valid passes
# ============================================================

def study_pass_space():
    print("\n" + "=" * 70)
    print("4. PASS SPACE: How many valid pass combinations exist?")
    print("=" * 70)

    print("""
    Each keystone has 3 possible "passes" (which literal saves it).
    With K keystones: 3^K possible pass combinations.
    But only SOME are consistent (a var can't be both 0 and 1).

    How constrained is the pass space?
    """)

    random.seed(42)
    n = 12

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17300000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]
        K = len(keystones)

        print(f"\n  n={n}, seed={seed}: {K} keystones")
        print(f"  Total pass combinations: 3^{K} = {3**K}")

        # Enumerate consistent passes
        # A pass = choosing one literal per keystone as the "saving" one
        # Consistent = the implied variable assignments don't conflict
        consistent = 0
        correct_passes = 0

        for mask in range(3**K):
            # Decode: which literal for each keystone?
            choices = []
            m = mask
            for _ in range(K):
                choices.append(m % 3)
                m //= 3

            # Build implied assignments
            implied = {}
            conflict = False
            for ki, choice in enumerate(choices):
                v, s = keystones[ki]['clause'][choice]
                val = 1 if s == 1 else 0  # value that satisfies this literal
                if v in implied and implied[v] != val:
                    conflict = True; break
                implied[v] = val

            if conflict: continue
            consistent += 1

            # Is this the CORRECT pass (matches solution)?
            all_correct = all(implied[v] == sol[v] for v in implied)
            if all_correct:
                correct_passes += 1

        print(f"  Consistent passes: {consistent}/{3**K} "
              f"({100*consistent/3**K:.1f}%)")
        print(f"  Correct passes (match solution): {correct_passes}")
        print(f"  Compression: {3**K} → {consistent} "
              f"({3**K/max(consistent,1):.1f}× reduction)")

        if consistent > 0:
            print(f"  If we pick random consistent pass: "
                  f"P(correct) = {correct_passes}/{consistent} = "
                  f"{100*correct_passes/max(consistent,1):.1f}%")

        break


# ============================================================
# 5. Can we find the pass WITHOUT knowing the solution?
# ============================================================

def study_find_pass():
    print("\n" + "=" * 70)
    print("5. FINDING THE PASS: Tension-guided pass selection")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17400000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]
        m = len(clauses)

        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        print(f"\n  n={n}, seed={seed}: {len(keystones)} keystones")

        # For each keystone: pick the pass by HIGHEST tension agreement
        implied = {}
        conflict = False

        for k in keystones:
            scores = []
            for j, (v, s) in enumerate(k['clause']):
                agreement = tensions[v] * s  # positive = tension agrees with sign
                scores.append((agreement, j, v, s))

            # Pick literal with highest agreement as pass
            best = max(scores, key=lambda x: x[0])
            _, _, v_pass, s_pass = best
            val_pass = 1 if s_pass == 1 else 0

            if v_pass in implied and implied[v_pass] != val_pass:
                conflict = True
            implied[v_pass] = val_pass

        # Evaluate: how many pass vars are correct?
        n_correct = sum(1 for v in implied if implied[v] == sol[v])
        n_total = len(implied)

        print(f"  Tension-guided pass selection:")
        print(f"    Correct: {n_correct}/{n_total} ({100*n_correct/max(n_total,1):.0f}%)")
        print(f"    Conflicts: {'YES' if conflict else 'no'}")

        # Fix these pass vars + UP → evaluate
        fixed = dict(implied)
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                sat = False; free_lits = []
                for v, s in clause:
                    if v in fixed:
                        if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                            sat = True; break
                    else:
                        free_lits.append((v, s))
                if sat: continue
                if len(free_lits) == 1:
                    fv, fs = free_lits[0]
                    if fv not in fixed:
                        fixed[fv] = 1 if fs == 1 else 0
                        changed = True

        a = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, a)
        correct_total = sum(1 for v in fixed if fixed[v] == sol[v])

        print(f"  After fixing + UP:")
        print(f"    Fixed: {len(fixed)}/{n}")
        print(f"    Correct: {correct_total}/{len(fixed)}")
        print(f"    Satisfied: {sat}/{m}")
        if sat == m:
            print(f"    → SOLVED by tension-guided passes!")

        break


# ============================================================
# 6. The ANATOMY of passing through a wall
# ============================================================

def study_anatomy_of_pass():
    print("\n" + "=" * 70)
    print("6. ANATOMY: What does it mean to 'pass through' a wall?")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+17500000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]

        # Take one keystone
        k = keystones[0]
        clause = k['clause']
        ci = k['idx']

        print(f"\n  Keystone {ci}: {clause}")
        print(f"  Unfreezes: {k['unfreezes']}")

        # The 3 possible passes
        print(f"\n  Three possible passes:")
        for j, (v, s) in enumerate(clause):
            val = 1 if s == 1 else 0
            is_correct = (val == sol[v])
            is_saving = (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)

            # If we fix this literal as the pass: what happens?
            fixed = {v: val}
            # UP
            changed = True; conflict = False
            while changed:
                changed = False
                for cl in clauses:
                    sat = False; free_lits = []
                    for vi, si in cl:
                        if vi in fixed:
                            if (si==1 and fixed[vi]==1) or (si==-1 and fixed[vi]==0):
                                sat = True; break
                        else:
                            free_lits.append((vi, si))
                    if sat: continue
                    if len(free_lits) == 0:
                        conflict = True; break
                    if len(free_lits) == 1:
                        fv, fs = free_lits[0]
                        if fv not in fixed:
                            fixed[fv] = 1 if fs == 1 else 0
                            changed = True
                if conflict: break

            n_forced = len(fixed) - 1
            correct = sum(1 for v2 in fixed if fixed[v2] == sol[v2]) - (1 if is_correct else 0)

            status = "✓ PASS" if is_saving else "✗ WALL"
            print(f"\n    Literal {j}: x{v}={val} (sign={s:+d}) {status}")
            print(f"      Correct: {is_correct}")
            print(f"      UP cascade: {n_forced} additional vars forced")
            print(f"      Of which correct: {correct}/{n_forced}")
            print(f"      Conflict: {'YES' if conflict else 'no'}")

            if conflict:
                print(f"      → This pass leads to CONTRADICTION")
                print(f"      → Wall BLOCKS this direction")
            elif n_forced > 0:
                a = [fixed.get(v2, 0) for v2 in range(n)]
                sat = evaluate(clauses, a)
                print(f"      → Opens path: {len(fixed)} vars determined, {sat}/{len(clauses)} sat")

        break


if __name__ == "__main__":
    study_tension_identifies_pass()
    study_pass_properties()
    study_oracle_pass()
    study_pass_space()
    study_find_pass()
    study_anatomy_of_pass()
