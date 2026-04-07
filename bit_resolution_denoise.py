"""
RESOLUTION DENOISING: Generate non-redundant clauses to amplify ε.

85% of original clauses are redundant noise.
Can we derive NEW clauses (via resolution) that carry more signal?

Resolution: from (A ∨ x) and (B ∨ ¬x), derive (A ∨ B).
The resolvent encodes a REAL constraint — not random noise.

Hypothesis: tension on original + resolvents has higher ε
because resolvents are structurally non-redundant.
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
# RESOLUTION ENGINE
# ============================================================

def resolve(clause1, clause2):
    """
    Try to resolve two clauses. Returns resolvent or None.
    Resolution: find variable that appears positive in one, negative in other.
    Resolvent = union of remaining literals.
    """
    vars1 = {v: s for v, s in clause1}
    vars2 = {v: s for v, s in clause2}

    # Find resolving variable
    for v in vars1:
        if v in vars2 and vars1[v] != vars2[v]:
            # Can resolve on v
            resolvent = set()
            for vv, ss in clause1:
                if vv != v: resolvent.add((vv, ss))
            for vv, ss in clause2:
                if vv != v: resolvent.add((vv, ss))

            # Check for tautology (x and ¬x in resolvent)
            resolvent_vars = {}
            tautology = False
            for vv, ss in resolvent:
                if vv in resolvent_vars and resolvent_vars[vv] != ss:
                    tautology = True; break
                resolvent_vars[vv] = ss

            if tautology: continue
            if len(resolvent) > 5: continue  # skip long clauses

            return list(resolvent)

    return None


def generate_resolvents(clauses, max_new=None):
    """Generate all resolvents from pairs of clauses."""
    if max_new is None: max_new = len(clauses)

    new_clauses = []
    seen = set()

    for i in range(len(clauses)):
        for j in range(i+1, len(clauses)):
            r = resolve(clauses[i], clauses[j])
            if r is not None:
                key = tuple(sorted((v,s) for v,s in r))
                if key not in seen and len(r) >= 2:
                    seen.add(key)
                    new_clauses.append(r)
                    if len(new_clauses) >= max_new:
                        return new_clauses

    return new_clauses


# ============================================================
# TEST: Tension on augmented formula
# ============================================================

def test_resolution_denoising(instances, n):
    """
    Compare:
    1. Tension on original clauses
    2. Tension on original + resolvents
    3. Tension on ONLY resolvents
    """
    results = {
        'original': {'correct': 0, 'total': 0},
        'augmented': {'correct': 0, 'total': 0},
        'resolvents_only': {'correct': 0, 'total': 0},
        'short_resolvents': {'correct': 0, 'total': 0},  # only 2-literal resolvents
    }

    resolvent_stats = {'count': [], 'len2': [], 'len3': [], 'len4': []}

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Generate resolvents
        resolvents = generate_resolvents(clauses, max_new=200)
        resolvent_stats['count'].append(len(resolvents))
        resolvent_stats['len2'].append(sum(1 for r in resolvents if len(r)==2))
        resolvent_stats['len3'].append(sum(1 for r in resolvents if len(r)==3))
        resolvent_stats['len4'].append(sum(1 for r in resolvents if len(r)==4))

        augmented = clauses + resolvents
        short_res = [r for r in resolvents if len(r) == 2]

        for var in range(n):
            actual = correct_val[var]
            results['original']['total'] += 1
            results['augmented']['total'] += 1
            results['resolvents_only']['total'] += 1
            results['short_resolvents']['total'] += 1

            # Original
            if (1 if bit_tension(clauses, n, var) >= 0 else 0) == actual:
                results['original']['correct'] += 1

            # Augmented
            if (1 if bit_tension(augmented, n, var) >= 0 else 0) == actual:
                results['augmented']['correct'] += 1

            # Resolvents only
            if resolvents:
                if (1 if bit_tension(resolvents, n, var) >= 0 else 0) == actual:
                    results['resolvents_only']['correct'] += 1

            # Short resolvents (2-literal = most constrained)
            if short_res:
                t_short = bit_tension(short_res, n, var)
                if abs(t_short) > 0.001:
                    if (1 if t_short >= 0 else 0) == actual:
                        results['short_resolvents']['correct'] += 1

    return results, resolvent_stats


# ============================================================
# MEASURE REDUNDANCY OF RESOLVENTS
# ============================================================

def resolvent_redundancy(instances, n):
    """
    Are resolvents LESS redundant than original clauses?
    This is the key question.
    """
    orig_redundancy = []
    resolvent_red = []

    for clauses, solutions in instances[:40]:
        resolvents = generate_resolvents(clauses, max_new=100)
        if not resolvents: continue

        all_clauses = clauses + resolvents

        for var in range(n):
            # Original clause redundancy
            for ci, clause in enumerate(clauses):
                has_var = any(v == var for v, s in clause)
                if not has_var: continue
                others = [(v,s) for v,s in clause if v != var]
                sat_without = sum(1 for sol in solutions
                                 if any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
                                       for v,s in others))
                orig_redundancy.append(sat_without / len(solutions))

            # Resolvent redundancy
            for clause in resolvents:
                has_var = any(v == var for v, s in clause)
                if not has_var: continue
                others = [(v,s) for v,s in clause if v != var]
                sat_without = sum(1 for sol in solutions
                                 if any((s==1 and sol[v]==1) or (s==-1 and sol[v]==0)
                                       for v,s in others))
                resolvent_red.append(sat_without / len(solutions))

    return orig_redundancy, resolvent_red


# ============================================================
# RESOLUTION-WEIGHTED TENSION
# ============================================================

def resolution_weighted_tension(clauses, n, var, resolvents):
    """
    Weight clause votes: original clauses weight 1, resolvents weight w.
    Find optimal w.
    """
    # Compute separately
    push_1_orig, push_0_orig = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                if s == 1: push_1_orig += 1.0/3
                else: push_0_orig += 1.0/3

    push_1_res, push_0_res = 0.0, 0.0
    for clause in resolvents:
        for v, s in clause:
            if v == var:
                w = 1.0 / len(clause)
                if s == 1: push_1_res += w
                else: push_0_res += w

    return push_1_orig, push_0_orig, push_1_res, push_0_res


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

    # --- Test resolution denoising ---
    print("\n" + "=" * 70)
    print("RESOLUTION DENOISING: Tension on augmented formula")
    print("=" * 70)

    results, stats = test_resolution_denoising(instances[:80], n)

    print(f"\n  Resolvent statistics:")
    print(f"    Avg count: {mean(stats['count']):.1f}")
    print(f"    2-literal: {mean(stats['len2']):.1f}")
    print(f"    3-literal: {mean(stats['len3']):.1f}")
    print(f"    4-literal: {mean(stats['len4']):.1f}")

    print(f"\n  {'method':>20} | {'accuracy':>8} | {'vs original':>11}")
    print("  " + "-" * 45)
    base = results['original']['correct']/results['original']['total']
    for name in ['original', 'augmented', 'resolvents_only', 'short_resolvents']:
        r = results[name]
        acc = r['correct']/r['total'] if r['total'] > 0 else 0
        delta = acc - base
        print(f"  {name:>20} | {acc*100:>7.1f}% | {delta*100:>+10.1f}%")

    # --- Redundancy of resolvents ---
    print("\n" + "=" * 70)
    print("RESOLVENT REDUNDANCY: Are they less redundant?")
    print("=" * 70)

    orig_red, res_red = resolvent_redundancy(instances[:30], n)
    print(f"\n  Original clauses avg redundancy: {mean(orig_red):.4f}")
    print(f"  Resolvent avg redundancy:        {mean(res_red):.4f}")
    if mean(orig_red) > 0:
        print(f"  Ratio: {mean(res_red)/mean(orig_red):.3f}")

    # --- Find optimal weight for resolvents ---
    print("\n" + "=" * 70)
    print("OPTIMAL RESOLVENT WEIGHT")
    print("=" * 70)

    for weight in [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]:
        correct = 0; total = 0
        for clauses, solutions in instances[:60]:
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]
            resolvents = generate_resolvents(clauses, max_new=100)

            for var in range(n):
                total += 1
                p1o, p0o, p1r, p0r = resolution_weighted_tension(clauses, n, var, resolvents)
                combined_1 = p1o + weight * p1r
                combined_0 = p0o + weight * p0r
                pred = 1 if combined_1 >= combined_0 else 0
                if pred == correct_val[var]: correct += 1

        acc = correct/total*100
        print(f"  weight={weight:>5.1f}: {acc:.1f}%")
