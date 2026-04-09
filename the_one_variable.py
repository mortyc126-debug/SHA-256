"""
THE ONE VARIABLE: Complete profile of the single free var that breaks everything
═════════════════════════════════════════════════════════════════════════════════

After pass selection: 58/59 sat. ONE clause unsatisfied.
That clause has exactly 1 wrong FREE variable.

WHO is this variable? How does it differ from other free vars?
Measure EVERYTHING about it.
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
            keystones.append({'idx': ci, 'clause': clauses[ci],
                              'unfreezes': unfrozen, 'power': len(unfrozen)})
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
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                        sat = True; break
                else: free_lits.append((v, s))
            if sat: continue
            if len(free_lits) == 0: return f, True
            if len(free_lits) == 1:
                fv, fs = free_lits[0]
                if fv not in f: f[fv] = 1 if fs==1 else 0; changed = True
    return f, False


def measure_variable(v, clauses, n, tensions, frozen, sol, adj):
    """Measure EVERY property of variable v."""
    degree = sum(1 for c in clauses for vi,si in c if vi==v)
    t = tensions[v]
    abs_t = abs(t)
    is_frozen = v in frozen

    # Self-cancellation
    neighbors = adj.get(v, set())
    if neighbors:
        nav = sum(tensions.get(u,0) for u in neighbors) / len(neighbors)
        sc = abs(t + nav)
    else:
        sc = abs_t

    # Frustration: how many clauses have conflicting signs for v?
    pos_signs = sum(1 for c in clauses for vi,si in c if vi==v and si==1)
    neg_signs = sum(1 for c in clauses for vi,si in c if vi==v and si==-1)
    frustration = 1 - abs(pos_signs - neg_signs) / max(pos_signs + neg_signs, 1)

    # How many of v's clauses are "barely satisfied" (1 saving literal)?
    barely_sat = 0
    for clause in clauses:
        if not any(vi==v for vi,si in clause): continue
        n_saving = sum(1 for vi,si in clause
                      if (si==1 and sol[vi]==1) or (si==-1 and sol[vi]==0))
        if n_saving == 1: barely_sat += 1

    # Number of frozen neighbors
    n_frozen_neighbors = sum(1 for u in neighbors if u in frozen)
    n_free_neighbors = len(neighbors) - n_frozen_neighbors

    # Clause diversity: how many DISTINCT other vars does v see?
    seen_vars = set()
    for clause in clauses:
        if any(vi==v for vi,si in clause):
            for vi,si in clause:
                if vi != v: seen_vars.add(vi)

    # In how many keystones does v appear?
    # (can't compute without keystones list, skip)

    return {
        'degree': degree,
        'tension': t,
        'abs_tension': abs_t,
        'self_cancel': sc,
        'frustration': frustration,
        'barely_sat_clauses': barely_sat,
        'n_frozen_neighbors': n_frozen_neighbors,
        'n_free_neighbors': n_free_neighbors,
        'frac_frozen_neighbors': n_frozen_neighbors / max(len(neighbors), 1),
        'distinct_vars_seen': len(seen_vars),
        'is_frozen': 1 if is_frozen else 0,
    }


def main():
    print("=" * 70)
    print("THE ONE VARIABLE: Full profile")
    print("=" * 70)

    random.seed(42)
    n = 14

    # Collect data: THE ONE vs all other free vars
    one_profiles = []
    other_free_profiles = []
    correct_free_profiles = []

    for seed in range(1000):
        clauses = random_3sat(n, int(4.267*n), seed=seed+19000000)
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

        adj = {v: set() for v in range(n)}
        for c in clauses:
            vs = [v for v,s in c]
            for a in vs:
                for b in vs:
                    if a != b: adj[a].add(b)

        # Tension-guided pass
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

        if sat != m - 1: continue  # only study exactly 1 miss

        # Find THE ONE wrong free var in the missed clause
        the_one = None
        for ci, clause in enumerate(clauses):
            if any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                  for v,s in clause): continue
            # Unsat clause found
            for v, s in clause:
                if assignment[v] != sol[v] and v not in frozen:
                    the_one = v
                    break

        if the_one is None: continue

        # Measure THE ONE
        profile = measure_variable(the_one, clauses, n, tensions, frozen, sol, adj)
        one_profiles.append(profile)

        # Measure all OTHER free vars (correctly assigned)
        for v in range(n):
            if v == the_one: continue
            if v in frozen: continue
            if assignment[v] != sol[v]:
                other_free_profiles.append(
                    measure_variable(v, clauses, n, tensions, frozen, sol, adj))
            else:
                correct_free_profiles.append(
                    measure_variable(v, clauses, n, tensions, frozen, sol, adj))

        if len(one_profiles) >= 20: break

    if not one_profiles:
        print("  No near-miss instances found")
        return

    print(f"\n  {len(one_profiles)} instances with exactly 1 miss")
    print(f"  THE ONE: the wrong free var that breaks 1 clause")
    print(f"  OTHER WRONG: other wrongly-assigned free vars (not in unsat clause)")
    print(f"  CORRECT: correctly-assigned free vars")

    fields = sorted(one_profiles[0].keys())

    print(f"\n  {'property':>25} | {'THE ONE':>8} | {'OTH.WRONG':>9} | "
          f"{'CORRECT':>8} | {'ONE/COR':>7} | {'filter?':>7}")
    print(f"  " + "-" * 80)

    discriminative = []

    for field in fields:
        if field == 'is_frozen': continue
        vals_one = [p[field] for p in one_profiles]
        vals_other = [p[field] for p in other_free_profiles] if other_free_profiles else [0]
        vals_correct = [p[field] for p in correct_free_profiles]

        m1 = np.mean(vals_one)
        mo = np.mean(vals_other) if vals_other else 0
        mc = np.mean(vals_correct)

        ratio = m1 / max(mc, 0.001) if mc != 0 else 0
        is_disc = abs(ratio - 1) > 0.20

        marker = "← YES" if is_disc else ""
        discriminative.append((field, ratio, is_disc))

        print(f"  {field:>25} | {m1:>8.3f} | {mo:>9.3f} | "
              f"{mc:>8.3f} | {ratio:>7.2f} | {marker:>7}")

    # Summary
    disc_fields = [f for f, r, d in discriminative if d]
    print(f"\n  DISCRIMINATIVE properties ({len(disc_fields)}):")
    for f in disc_fields:
        print(f"    • {f}")

    if not disc_fields:
        print(f"    NONE — THE ONE is indistinguishable from correct free vars!")
    else:
        # Build a simple filter
        print(f"\n  SIMPLE FILTER: can we find THE ONE?")
        # Score each free var by discriminative properties
        # Test: among all free vars, what rank does THE ONE get?
        ranks = []
        for inst_idx in range(len(one_profiles)):
            # Recompute for this instance... just use stored data
            pass

        # Instead: statistics
        print(f"\n  If we filter by the discriminative properties,")
        print(f"  how many candidates remain?")

        # Use threshold: for each discriminative field,
        # keep vars in the range of THE ONE
        for f, r, d in discriminative:
            if not d: continue
            vals_one = [p[f] for p in one_profiles]
            vals_correct = [p[f] for p in correct_free_profiles]
            low = np.percentile(vals_one, 10)
            high = np.percentile(vals_one, 90)
            in_range = sum(1 for v in vals_correct if low <= v <= high)
            frac = in_range / max(len(vals_correct), 1)
            print(f"    {f}: THE ONE range [{low:.3f}, {high:.3f}] "
                  f"→ {100*frac:.0f}% of correct vars also in range")


if __name__ == "__main__":
    main()
