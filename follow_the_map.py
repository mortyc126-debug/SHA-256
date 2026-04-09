"""
FOLLOW THE MAP: flip_delta_sat points somewhere. WHERE?
══════════════════════════════════════════════════════

flip THE ONE → sat improves. WHY?

The clause structure around THE ONE is DIFFERENT.
Not in obvious ways (degree, tension — we checked).
But in the WAY clauses INTERACT around her.

Let's trace EXACTLY what happens when we flip THE ONE:
- Which clauses BREAK?
- Which clauses GET FIXED?
- What's the NET structure?
- Is there a pattern we can see WITHOUT flipping?

Also: is flip_delta_sat computable from STRUCTURE ALONE
(without actually flipping)?
"""

import numpy as np
import random
from collections import Counter
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def clause_sat_check(clause, assignment):
    return any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
               for v, s in clause)


def get_frozen(clauses, n, solutions):
    return set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)


def find_keystones(clauses, n, solutions, frozen):
    keystones = []
    for ci in range(len(clauses)):
        reduced = clauses[:ci] + clauses[ci+1:]
        rsols = find_solutions(reduced, n)
        if len(rsols) < 2: continue
        rf = get_frozen(reduced, n, rsols)
        if frozen - rf:
            keystones.append({'idx': ci, 'clause': clauses[ci],
                              'unfreezes': frozen - rf, 'power': len(frozen - rf)})
    return keystones


def unit_propagate_from(clauses, n, fixed):
    f = dict(fixed)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; free_lits = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0): sat = True; break
                else: free_lits.append((v, s))
            if sat: continue
            if len(free_lits) == 0: return f, True
            if len(free_lits) == 1:
                fv, fs = free_lits[0]
                if fv not in f: f[fv] = 1 if fs==1 else 0; changed = True
    return f, False


def deep_study():
    print("=" * 70)
    print("FOLLOW THE MAP: What happens EXACTLY when we flip THE ONE?")
    print("=" * 70)

    random.seed(42)
    n = 14

    # Collect structural patterns
    one_clause_structure = []  # clauses that BREAK when flipping ONE
    one_clause_fixes = []      # clauses that GET FIXED
    inn_clause_structure = []
    inn_clause_fixes = []

    # NEW measurements: pre-flip observables that PREDICT flip success
    one_pre = []
    inn_pre = []

    n_found = 0

    for seed in range(2000):
        clauses = random_3sat(n, int(4.267*n), seed=seed+21000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue
        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]
        m = len(clauses)
        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        pass_vars = {}
        for k in keystones:
            scores = [(tensions[v]*s, v, s) for v,s in k['clause']]
            best = max(scores, key=lambda x: x[0])
            _, vp, sp = best
            pass_vars[vp] = 1 if sp==1 else 0

        fixed, conflict = unit_propagate_from(clauses, n, pass_vars)
        if conflict: continue
        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)
        if sat != m - 1: continue

        # Find unsat clause
        unsat_ci = -1
        for ci, clause in enumerate(clauses):
            if not clause_sat_check(clause, assignment):
                unsat_ci = ci; break
        if unsat_ci < 0: continue

        n_found += 1
        clause = clauses[unsat_ci]

        for v, s_in_clause in clause:
            is_one = (assignment[v] != sol[v])
            tag_pre = one_pre if is_one else inn_pre
            tag_breaks = one_clause_structure if is_one else inn_clause_structure
            tag_fixes = one_clause_fixes if is_one else inn_clause_fixes

            # FLIP v
            new_a = list(assignment)
            new_a[v] = 1 - new_a[v]

            # Count what BREAKS and what FIXES
            breaks = 0; fixes = 0
            break_types = []
            for ci2, c2 in enumerate(clauses):
                was_sat = clause_sat_check(c2, assignment)
                now_sat = clause_sat_check(c2, new_a)
                if was_sat and not now_sat:
                    breaks += 1
                    # Classify the broken clause
                    n_saving_before = sum(1 for vi,si in c2
                        if (si==1 and assignment[vi]==1) or (si==-1 and assignment[vi]==0))
                    break_types.append(n_saving_before)
                elif not was_sat and now_sat:
                    fixes += 1

            delta = fixes - breaks
            tag_breaks.append(breaks)
            tag_fixes.append(fixes)

            # ── PRE-FLIP OBSERVABLES ──
            # 1. How many of v's clauses are "critically satisfied"
            #    (only 1 literal saving them, and that literal involves v)?
            critical = 0
            for c2 in clauses:
                if not any(vi==v for vi,si in c2): continue
                n_saving = sum(1 for vi,si in c2
                    if (si==1 and assignment[vi]==1) or (si==-1 and assignment[vi]==0))
                # Is v the ONLY saver?
                v_saves = any(vi==v and ((si==1 and assignment[v]==1) or
                             (si==-1 and assignment[v]==0)) for vi,si in c2)
                if n_saving == 1 and v_saves:
                    critical += 1

            # 2. How many of v's clauses are "bonus satisfied"
            #    (would BECOME satisfied if we flip v)?
            bonus = 0
            for c2 in clauses:
                if not any(vi==v for vi,si in c2): continue
                if clause_sat_check(c2, assignment): continue  # already sat
                # Would flipping v satisfy this clause?
                v_sign_in_c2 = next(si for vi,si in c2 if vi==v)
                new_val = 1 - assignment[v]
                would_save = (v_sign_in_c2==1 and new_val==1) or \
                             (v_sign_in_c2==-1 and new_val==0)
                if would_save: bonus += 1

            # 3. Net = bonus - critical
            net = bonus - critical

            # 4. The SIGN of v in the unsat clause: does flipping
            #    v SATISFY or UNSATISFY the literal?
            new_val = 1 - assignment[v]
            flip_satisfies_unsat = (s_in_clause==1 and new_val==1) or \
                                   (s_in_clause==-1 and new_val==0)

            tag_pre.append({
                'critical': critical,
                'bonus': bonus,
                'net': net,
                'flip_satisfies_unsat': 1 if flip_satisfies_unsat else 0,
                'breaks': breaks,
                'fixes': fixes,
                'delta': delta,
            })

        if n_found >= 30: break

    # ═══ RESULTS ═══
    print(f"\n  {n_found} instances analyzed")

    print(f"\n  ── FLIP ANATOMY ──")
    print(f"  {'':>25} | {'THE ONE':>8} | {'INNOCENT':>8} | {'ratio':>6}")
    print(f"  " + "-" * 55)
    print(f"  {'clauses BROKEN by flip':>25} | "
          f"{np.mean(one_clause_structure):>8.2f} | "
          f"{np.mean(inn_clause_structure):>8.2f} | "
          f"{np.mean(one_clause_structure)/max(np.mean(inn_clause_structure),0.001):>6.2f}")
    print(f"  {'clauses FIXED by flip':>25} | "
          f"{np.mean(one_clause_fixes):>8.2f} | "
          f"{np.mean(inn_clause_fixes):>8.2f} | "
          f"{np.mean(one_clause_fixes)/max(np.mean(inn_clause_fixes),0.001):>6.2f}")

    print(f"\n  ── PRE-FLIP OBSERVABLES (computable WITHOUT flipping!) ──")
    for prop in ['critical', 'bonus', 'net', 'flip_satisfies_unsat']:
        o = [p[prop] for p in one_pre]
        i = [p[prop] for p in inn_pre]
        mo = np.mean(o); mi = np.mean(i)
        r = mo/mi if abs(mi) > 0.001 else (999 if abs(mo) > 0.001 else 1)
        disc = " ← STRONG" if abs(r-1) > 0.3 or abs(mo-mi) > 0.3 else \
               (" ← signal" if abs(r-1) > 0.15 else "")
        print(f"  {prop:>25} | {mo:>8.3f} | {mi:>8.3f} | {r:>6.2f}{disc}")

    # ═══ THE KEY INSIGHT ═══
    print(f"\n  ═══ THE KEY INSIGHT ═══")

    # Can we predict flip_delta_sat from pre-flip observables?
    # net = bonus - critical should equal delta = fixes - breaks
    one_nets = [p['net'] for p in one_pre]
    one_deltas = [p['delta'] for p in one_pre]
    if one_nets and one_deltas:
        corr = np.corrcoef(one_nets, one_deltas)[0,1] if len(one_nets) > 2 else 0
        print(f"\n  Correlation(net, delta) = {corr:.3f}")
        print(f"  → net = bonus - critical {'PREDICTS' if abs(corr)>0.5 else 'does not predict'} flip improvement")

    # THE CRITICAL TEST: can 'bonus' alone identify THE ONE?
    one_bonus = [p['bonus'] for p in one_pre]
    inn_bonus = [p['bonus'] for p in inn_pre]
    one_satisfies = [p['flip_satisfies_unsat'] for p in one_pre]
    inn_satisfies = [p['flip_satisfies_unsat'] for p in inn_pre]

    print(f"\n  BONUS (clauses that become sat if we flip):")
    print(f"    THE ONE:  {np.mean(one_bonus):.3f}")
    print(f"    INNOCENT: {np.mean(inn_bonus):.3f}")

    print(f"\n  FLIP SATISFIES THE UNSAT CLAUSE:")
    print(f"    THE ONE:  {np.mean(one_satisfies):.1%}")
    print(f"    INNOCENT: {np.mean(inn_satisfies):.1%}")

    if np.mean(one_satisfies) > np.mean(inn_satisfies) + 0.1:
        print(f"\n  ╔══════════════════════════════════════════════════╗")
        print(f"  ║  THE ONE's literal in the unsat clause WOULD     ║")
        print(f"  ║  SATISFY it if flipped. Innocents' would NOT.    ║")
        print(f"  ║                                                    ║")
        print(f"  ║  This is TRIVIALLY TRUE by construction:          ║")
        print(f"  ║  THE ONE is wrong → flip → correct → satisfies.  ║")
        print(f"  ║  But CRITICAL is the key:                         ║")
        print(f"  ║  THE ONE has FEWER critical clauses = can be      ║")
        print(f"  ║  flipped without breaking much.                   ║")
        print(f"  ╚══════════════════════════════════════════════════╝")


if __name__ == "__main__":
    deep_study()
