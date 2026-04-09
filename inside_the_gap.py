"""
INSIDE THE GAP: The quantum structure of passage through a wall
═══════════════════════════════════════════════════════════════

58/59 clauses satisfied. 1 remains. WHY?
The gap is 1 bit wide. But it's not just ON or OFF.
Inside the gap there is structure.

QUESTIONS:
1. THE LAST CLAUSE — what is the unsatisfied clause? Is it a keystone?
2. THE MISS — tension-guided pass was 78% correct. The 22% wrong =
   wrong passes led to wrong UPs which broke this one clause.
   Trace the CAUSAL CHAIN from wrong pass to last unsat clause.
3. THE INTERFERENCE — do passes interfere? Does satisfying keystone A's
   gap CLOSE keystone B's gap?
4. THE ENTANGLEMENT OF GAPS — are the gaps correlated across keystones?
5. THE GEOMETRY — in [0,1]^n continuous space, what does the gap look like?
6. THE MINIMAL PASS SET — what's the SMALLEST set of passes that works?
7. THE ERROR ANATOMY — when tension gets a pass wrong, what happens?
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


def unit_propagate_from(clauses, n, fixed):
    """UP from given fixed vars. Returns (new_fixed, conflict)."""
    f = dict(fixed)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; free_lits = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                        sat = True; break
                else:
                    free_lits.append((v, s))
            if sat: continue
            if len(free_lits) == 0: return f, True
            if len(free_lits) == 1:
                fv, fs = free_lits[0]
                if fv not in f:
                    f[fv] = 1 if fs == 1 else 0
                    changed = True
    return f, False


# ============================================================
# 1. THE LAST CLAUSE: What is it? Why does it fail?
# ============================================================

def study_last_clause():
    print("=" * 70)
    print("1. THE LAST CLAUSE: Anatomy of the 1 that fails")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(300):
        clauses = random_3sat(n, int(4.267*n), seed=seed+18000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]
        m = len(clauses)
        ks_indices = set(k['idx'] for k in keystones)

        # Tension-guided pass selection
        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        # Pick pass per keystone
        pass_vars = {}
        for k in keystones:
            scores = [(tensions[v]*s, v, s) for v, s in k['clause']]
            best = max(scores, key=lambda x: x[0])
            _, v_pass, s_pass = best
            pass_vars[v_pass] = 1 if s_pass == 1 else 0

        # Fix + UP
        fixed, conflict = unit_propagate_from(clauses, n, pass_vars)
        if conflict: continue

        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)

        if sat >= m - 3 and sat < m:
            # Found a near-miss! Analyze the unsatisfied clauses
            unsat_indices = []
            for ci, clause in enumerate(clauses):
                if not any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                          for v, s in clause):
                    unsat_indices.append(ci)

            print(f"\n  n={n}, seed={seed}: {sat}/{m} satisfied ({m-sat} unsat)")
            print(f"  Keystones: {len(keystones)}")
            print(f"  Pass vars: {len(pass_vars)} ({sum(1 for v in pass_vars if pass_vars[v]==sol[v])}"
                  f"/{len(pass_vars)} correct)")

            for ci in unsat_indices:
                clause = clauses[ci]
                is_ks = ci in ks_indices

                print(f"\n  UNSAT clause {ci}: {clause} "
                      f"{'← KEYSTONE' if is_ks else '← normal'}")

                for v, s in clause:
                    wanted = 1 if s == 1 else 0
                    has = assignment[v]
                    t = tensions[v]
                    f_status = "FROZEN" if v in frozen else "free"
                    correct = has == sol[v]
                    in_pass = v in pass_vars

                    print(f"    x{v}: wants={wanted}, has={has}, sol={sol[v]}, "
                          f"tension={t:+.3f}, {f_status}, "
                          f"{'PASS_VAR' if in_pass else ''}, "
                          f"{'✓' if correct else '✗ WRONG'}")

                # WHY is it unsat? All 3 literals fail.
                # Trace each: where did the wrong value come from?
                print(f"\n    CAUSAL TRACE:")
                for v, s in clause:
                    wanted = 1 if s == 1 else 0
                    has = assignment[v]
                    if has == wanted: continue  # this literal is fine

                    # v has wrong value. Was it a pass var or UP-forced?
                    if v in pass_vars:
                        print(f"    x{v}={has} ← PASS SELECTION (tension={tensions[v]:+.3f})")
                        # Was the pass selection wrong?
                        if pass_vars[v] != sol[v]:
                            print(f"       → WRONG PASS! Tension chose wrong direction")
                    else:
                        # Was it forced by UP? From which clause?
                        print(f"    x{v}={has} ← UP cascade or default")

            if m - sat == 1:
                break  # found the perfect case: 1 unsat clause

    pass  # if no perfect case found, OK


# ============================================================
# 2. INTERFERENCE: Does satisfying one gap close another?
# ============================================================

def study_interference():
    print("\n" + "=" * 70)
    print("2. INTERFERENCE: Do passes interfere with each other?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+18100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 4: continue

        sol = solutions[0]
        m = len(clauses)

        # For each keystone: try each of its 3 passes
        # Check: does fixing this pass affect OTHER keystones' satisfaction?
        print(f"\n  n={n}, seed={seed}: {len(keystones)} keystones")
        print(f"\n  Interference matrix (how fixing one pass affects others):")

        ks_list = keystones[:5]

        # Header
        print(f"  {'fix':>15} |", end="")
        for k in ks_list:
            print(f" ks{k['idx']:>2}", end="")
        print()
        print(f"  " + "-" * (18 + 5*len(ks_list)))

        for ki, k in enumerate(ks_list):
            # Fix the CORRECT pass for this keystone
            saving = None
            for v, s in k['clause']:
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                    saving = (v, 1 if s==1 else 0)
                    break
            if not saving: continue

            fixed = {saving[0]: saving[1]}
            fixed, _ = unit_propagate_from(clauses, n, fixed)

            # Check each other keystone: is it now satisfied?
            print(f"  ks{k['idx']:>2} pass(x{saving[0]}={saving[1]}) |", end="")
            for kj, k2 in enumerate(ks_list):
                clause2 = k2['clause']
                sat2 = any((s==1 and fixed.get(v, sol[v])==1) or
                          (s==-1 and fixed.get(v, sol[v])==0)
                          for v, s in clause2)
                # Was it already satisfied without the fix?
                sat2_base = any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
                               for v, s in clause2)
                if ki == kj:
                    print(f"  SAT", end="")
                elif sat2:
                    print(f"   ok", end="")
                else:
                    print(f"  ---", end="")
            print()

        # Key question: are there CONFLICTS?
        # Can fixing pass A make keystone B unsatisfiable?
        print(f"\n  Conflict check:")
        conflicts_found = 0
        for ki, k in enumerate(ks_list):
            for pass_idx in range(3):
                v_fix, s_fix = k['clause'][pass_idx]
                val_fix = 1 if s_fix == 1 else 0
                fixed, conflict = unit_propagate_from(clauses, n, {v_fix: val_fix})
                if conflict:
                    is_correct = (val_fix == sol[v_fix])
                    print(f"    ks{k['idx']} literal {pass_idx} "
                          f"(x{v_fix}={val_fix}, {'correct' if is_correct else 'WRONG'})"
                          f" → CONFLICT!")
                    conflicts_found += 1

        print(f"\n  Total conflicts: {conflicts_found}")
        print(f"  → {'PASSES INTERFERE' if conflicts_found > 0 else 'PASSES ARE INDEPENDENT'}")

        break


# ============================================================
# 3. ENTANGLEMENT OF GAPS: Are gaps correlated?
# ============================================================

def study_gap_entanglement():
    print("\n" + "=" * 70)
    print("3. ENTANGLEMENT: Are gaps in different walls correlated?")
    print("=" * 70)

    print("""
    If keystone A's pass is at literal 0, does that PREDICT
    where keystone B's pass is?
    """)

    random.seed(42)
    n = 12

    # Collect pass positions across many instances
    pass_positions = []  # list of (instance) lists of (keystone_idx, pass_position)

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+18200000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]

        # For each keystone: which position is the pass?
        positions = []
        for k in keystones:
            for j, (v, s) in enumerate(k['clause']):
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                    positions.append(j)
                    break

        pass_positions.append(positions)
        if len(pass_positions) >= 30: break

    if pass_positions:
        # Count pass position distribution
        all_pos = [p for pp in pass_positions for p in pp]
        dist = Counter(all_pos)
        print(f"\n  Pass position distribution (0, 1, or 2 within clause):")
        for pos in [0, 1, 2]:
            frac = dist.get(pos, 0) / max(len(all_pos), 1)
            print(f"    Position {pos}: {100*frac:.1f}%")

        # Is position uniform? (should be ~33% each for random signs)
        print(f"    Expected: 33.3% each")
        max_dev = max(abs(dist.get(p,0)/max(len(all_pos),1) - 1/3) for p in [0,1,2])
        print(f"    Max deviation: {100*max_dev:.1f}%")
        print(f"    → {'UNIFORM (no correlation)' if max_dev < 0.05 else 'BIASED'}")

        # Within each instance: are positions correlated?
        # Do keystones that share a variable tend to have the pass at the shared var?
        shared_pass = 0; shared_total = 0
        for pp, seed_idx in zip(pass_positions, range(len(pass_positions))):
            clauses = random_3sat(n, int(4.267*n), seed=seed_idx+18200000)
            solutions = find_solutions(clauses, n)
            if len(solutions) < 2: continue
            frozen = get_frozen(clauses, n, solutions)
            keystones = find_keystones(clauses, n, solutions, frozen)

            for i in range(len(keystones)):
                for j in range(i+1, len(keystones)):
                    vs_i = set(v for v, s in keystones[i]['clause'])
                    vs_j = set(v for v, s in keystones[j]['clause'])
                    shared = vs_i & vs_j
                    if shared:
                        shared_total += 1
                        # Is the shared var the pass for both?
                        sol = solutions[0]
                        pass_i = [v for v, s in keystones[i]['clause']
                                 if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)]
                        pass_j = [v for v, s in keystones[j]['clause']
                                 if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)]
                        if pass_i and pass_j and set(pass_i) & shared:
                            shared_pass += 1

        if shared_total > 0:
            print(f"\n  Keystones sharing a variable: {shared_total} pairs")
            print(f"  Shared var IS the pass for both: {shared_pass}/{shared_total} "
                  f"({100*shared_pass/shared_total:.0f}%)")


# ============================================================
# 4. MINIMAL PASS SET: Fewest passes that solve everything
# ============================================================

def study_minimal():
    print("\n" + "=" * 70)
    print("4. MINIMAL PASS SET: Fewest bits to unlock the frozen core")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(200):
        clauses = random_3sat(n, int(4.267*n), seed=seed+18300000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        sol = solutions[0]
        m = len(clauses)

        # Greedy: fix ONE var at a time that satisfies the most unsatisfied keystones
        # Start from empty
        fixed = {}
        solve_log = []

        for step in range(n):
            # Which keystones are currently unsatisfied?
            unsat_ks = []
            for k in keystones:
                sat = any((s==1 and fixed.get(v, -1)==1) or (s==-1 and fixed.get(v, -1)==0)
                         for v, s in k['clause'])
                if not sat: unsat_ks.append(k)

            if not unsat_ks: break

            # Try each unfixed var with each value: which satisfies most keystones?
            best_v, best_val, best_count = -1, 0, 0
            for v in range(n):
                if v in fixed: continue
                for val in [0, 1]:
                    count = 0
                    for k in unsat_ks:
                        for vi, si in k['clause']:
                            if vi == v and ((si==1 and val==1) or (si==-1 and val==0)):
                                count += 1; break
                    if count > best_count:
                        best_count = count; best_v = v; best_val = val

            if best_v < 0: break
            fixed[best_v] = best_val
            correct = (best_val == sol[best_v])
            solve_log.append((best_v, best_val, correct, best_count, len(unsat_ks)))

        # After greedy: UP
        all_fixed, conflict = unit_propagate_from(clauses, n, fixed)
        assignment = [all_fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)
        n_correct = sum(1 for v in fixed if fixed[v] == sol[v])

        print(f"\n  n={n}, seed={seed}: {len(keystones)} keystones")
        print(f"  Greedy minimal pass:")
        for v, val, correct, count, remaining in solve_log:
            print(f"    Fix x{v}={val} {'✓' if correct else '✗'} "
                  f"→ satisfies {count} keystones, {remaining-count} remain")

        print(f"\n  After {len(fixed)} greedy fixes + UP:")
        print(f"    Total fixed: {len(all_fixed)}/{n}")
        print(f"    Pass vars correct: {n_correct}/{len(fixed)}")
        print(f"    Satisfied: {sat}/{m}")

        if sat == m:
            print(f"    → SOLVED with {len(fixed)} pass variables!")
        else:
            print(f"    → {m - sat} unsatisfied")

        # Compare: how many bits does the SOLUTION need to specify?
        print(f"\n  Frozen vars: {len(frozen)} (need to know)")
        print(f"  Greedy pass vars: {len(fixed)} (sufficient to unlock)")
        print(f"  Compression: {len(frozen)} → {len(fixed)} = "
              f"{len(frozen)/max(len(fixed),1):.1f}×")

        break


# ============================================================
# 5. THE LAST 1%: Detailed study of ALL near-misses
# ============================================================

def study_near_misses():
    print("\n" + "=" * 70)
    print("5. NEAR MISSES: When 58/59 succeeds, what's the 1 failure?")
    print("=" * 70)

    random.seed(42)
    n = 14

    miss_is_keystone = 0
    miss_is_normal = 0
    miss_vars_wrong = []  # how many vars in the missed clause are wrong

    for seed in range(500):
        clauses = random_3sat(n, int(4.267*n), seed=seed+18400000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]
        m = len(clauses)
        ks_indices = set(k['idx'] for k in keystones)

        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        # Tension-guided pass
        pass_vars = {}
        for k in keystones:
            scores = [(tensions[v]*s, v, s) for v, s in k['clause']]
            best = max(scores, key=lambda x: x[0])
            _, v_p, s_p = best
            pass_vars[v_p] = 1 if s_p == 1 else 0

        fixed, conflict = unit_propagate_from(clauses, n, pass_vars)
        if conflict: continue

        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)

        if sat == m - 1:  # exactly 1 unsat
            for ci, clause in enumerate(clauses):
                if not any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                          for v, s in clause):
                    if ci in ks_indices:
                        miss_is_keystone += 1
                    else:
                        miss_is_normal += 1

                    n_wrong = sum(1 for v, s in clause if assignment[v] != sol[v])
                    miss_vars_wrong.append(n_wrong)

    total_misses = miss_is_keystone + miss_is_normal
    if total_misses > 0:
        print(f"\n  {total_misses} instances with exactly 1 unsat clause:")
        print(f"    Missed clause is KEYSTONE: {miss_is_keystone} "
              f"({100*miss_is_keystone/total_misses:.0f}%)")
        print(f"    Missed clause is NORMAL:   {miss_is_normal} "
              f"({100*miss_is_normal/total_misses:.0f}%)")

        if miss_vars_wrong:
            print(f"\n  Wrong vars in missed clause:")
            dist = Counter(miss_vars_wrong)
            for nw in sorted(dist.keys()):
                bar = '█' * dist[nw]
                print(f"    {nw} wrong: {dist[nw]} {bar}")


if __name__ == "__main__":
    study_last_clause()
    study_interference()
    study_gap_entanglement()
    study_minimal()
    study_near_misses()
