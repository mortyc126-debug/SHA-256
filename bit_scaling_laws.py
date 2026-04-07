"""
BIT SCALING LAWS -- Do the constants of Bit Mechanics hold at larger n?

Tests four key constants at n = 10, 14, 20, 30, 50 (ratio=4.27):
  1. epsilon (sign-solution correlation) -- expected ~0.072
  2. tension accuracy                    -- expected ~70%
  3. flip trigger ratio (wrong/correct)  -- expected ~2.0
  4. solution clustering index           -- expected ~0.52

For n <= 16: exact enumeration via find_solutions().
For n >  16: WalkSAT proxy (200 runs per instance).
"""

import random
import math
import time
from bit_catalog_static import random_3sat, find_solutions


# ============================================================
# INLINE HELPERS
# ============================================================

def bit_tension(clauses, n, var, fixed=None):
    """Weighted tension: how strongly clauses push var toward 1 vs 0."""
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


def walksat_fast(clauses, n, max_flips=None):
    """WalkSAT with occurrence-list optimization for speed."""
    if max_flips is None:
        max_flips = 200 * n
    m = len(clauses)

    # Build occurrence lists: var_in_clause[v] = list of clause indices containing v
    var_in_clause = [[] for _ in range(n)]
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            var_in_clause[v].append(ci)

    assignment = [random.randint(0, 1) for _ in range(n)]

    # Compute initial unsat set
    unsat_set = set()
    for ci in range(m):
        satisfied = False
        for v, s in clauses[ci]:
            if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                satisfied = True
                break
        if not satisfied:
            unsat_set.add(ci)

    for flip in range(max_flips):
        if not unsat_set:
            return list(assignment), True

        ci = random.choice(list(unsat_set))

        if random.random() < 0.3:
            # Random walk
            v, s = random.choice(clauses[ci])
            flip_var = v
        else:
            # Greedy: pick var that breaks fewest clauses
            best_var = None
            best_break = float('inf')
            for v, s in clauses[ci]:
                # Count how many currently-sat clauses would become unsat
                new_val = 1 - assignment[v]
                breaks = 0
                for cj in var_in_clause[v]:
                    if cj in unsat_set:
                        continue  # already unsat
                    # Check if flipping v breaks clause cj
                    # Clause cj is currently sat. After flip, is it still sat?
                    still_sat = False
                    for vv, ss in clauses[cj]:
                        val = new_val if vv == v else assignment[vv]
                        if (ss == 1 and val == 1) or (ss == -1 and val == 0):
                            still_sat = True
                            break
                    if not still_sat:
                        breaks += 1
                if breaks < best_break:
                    best_break = breaks
                    best_var = v
            flip_var = best_var if best_var is not None else clauses[ci][0][0]

        # Flip the variable and update unsat_set
        new_val = 1 - assignment[flip_var]
        assignment[flip_var] = new_val
        for cj in var_in_clause[flip_var]:
            satisfied = False
            for v, s in clauses[cj]:
                if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                    satisfied = True
                    break
            if satisfied:
                unsat_set.discard(cj)
            else:
                unsat_set.add(cj)

    return list(assignment), False


def get_solutions(clauses, n, n_walksat=200):
    """Get solutions: exact for n<=16, WalkSAT proxy for n>16."""
    if n <= 16:
        return find_solutions(clauses, n)
    else:
        seen = set()
        solutions = []
        for _ in range(n_walksat):
            assignment, found = walksat_fast(clauses, n)
            if found:
                key = tuple(assignment)
                if key not in seen:
                    seen.add(key)
                    solutions.append(assignment)
        return solutions


def compute_flip_triggers(clauses, n, var, fixed=None):
    """Fraction of neighbors that can flip the sign of tension for var."""
    if fixed is None:
        fixed = {}
    sigma_base = bit_tension(clauses, n, var, fixed)
    base_sign = 1 if sigma_base >= 0 else -1

    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var and v not in fixed:
                    neighbors.add(v)
    if not neighbors:
        return 0.0

    triggers = 0
    for nb in neighbors:
        for val in [0, 1]:
            test_fixed = dict(fixed)
            test_fixed[nb] = val
            s = bit_tension(clauses, n, var, test_fixed)
            if (1 if s >= 0 else -1) != base_sign:
                triggers += 1
                break
    return triggers / len(neighbors)


# ============================================================
# MAIN TEST
# ============================================================

def run_scaling_test():
    random.seed(42)

    test_sizes = [10, 14, 20, 30, 50]
    ratio = 4.27
    instances_per_n = {10: 50, 14: 50, 20: 40, 30: 35, 50: 30}
    # For flip triggers, sample fewer vars at large n to keep runtime sane
    ft_vars_per_instance = {10: 10, 14: 14, 20: 12, 30: 10, 50: 8}

    print("=" * 80)
    print("BIT SCALING LAWS -- Do constants hold at larger n?")
    print(f"Ratio = {ratio}, WalkSAT proxy for n > 16 (200 runs)")
    print("=" * 80)

    all_results = {}

    for n in test_sizes:
        n_instances = instances_per_n[n]
        n_clauses = int(ratio * n)
        n_ft_vars = ft_vars_per_instance[n]
        t0 = time.time()

        print(f"\n{'='*60}")
        print(f"  n = {n}  (clauses = {n_clauses}, instances = {n_instances})")
        print(f"{'='*60}", flush=True)

        # Accumulators
        epsilons = []
        tension_correct = 0
        tension_total = 0
        flip_trigger_wrong = []
        flip_trigger_correct = []
        clustering_vals = []
        instances_with_solutions = 0
        total_solutions_found = 0

        for seed in range(n_instances * 5):
            if instances_with_solutions >= n_instances:
                break

            clauses = random_3sat(n, n_clauses, seed=seed + 7000)
            solutions = get_solutions(clauses, n)

            if len(solutions) < 2:
                continue

            instances_with_solutions += 1
            total_solutions_found += len(solutions)

            # Ground truth: probability of each bit being 1
            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            # --- 1. Epsilon: sign-solution correlation ---
            for var in range(n):
                pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
                neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
                tot_app = pos + neg
                if tot_app > 0:
                    if correct_val[var] == 1:
                        epsilons.append(pos / tot_app - 0.5)
                    else:
                        epsilons.append(neg / tot_app - 0.5)

            # --- 2. Tension accuracy ---
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                pred = 1 if sigma >= 0 else 0
                actual = correct_val[var]
                if pred == actual:
                    tension_correct += 1
                tension_total += 1

            # --- 3. Flip trigger ratio (sample subset of vars) ---
            vars_to_test = random.sample(range(n), min(n, n_ft_vars))
            for var in vars_to_test:
                ft = compute_flip_triggers(clauses, n, var)
                sigma = bit_tension(clauses, n, var)
                pred = 1 if sigma >= 0 else 0
                actual = correct_val[var]
                if pred == actual:
                    flip_trigger_correct.append(ft)
                else:
                    flip_trigger_wrong.append(ft)

            # --- 4. Solution clustering ---
            sols_sample = solutions[:50] if len(solutions) > 50 else solutions
            if len(sols_sample) >= 2:
                dists = []
                for i in range(len(sols_sample)):
                    for j in range(i + 1, len(sols_sample)):
                        dists.append(sum(sols_sample[i][k] != sols_sample[j][k] for k in range(n)))
                avg_d = sum(dists) / len(dists)
                clustering = 1.0 - avg_d / (n / 2)
                clustering_vals.append(clustering)

            if instances_with_solutions % 10 == 0:
                print(f"    ... {instances_with_solutions}/{n_instances} instances done "
                      f"({time.time()-t0:.0f}s)", flush=True)

        elapsed = time.time() - t0

        # --- Report ---
        eps = sum(epsilons) / len(epsilons) if epsilons else float('nan')
        acc = tension_correct / tension_total if tension_total > 0 else float('nan')
        ft_wrong_avg = sum(flip_trigger_wrong) / len(flip_trigger_wrong) if flip_trigger_wrong else float('nan')
        ft_correct_avg = sum(flip_trigger_correct) / len(flip_trigger_correct) if flip_trigger_correct else float('nan')
        ft_ratio = ft_wrong_avg / ft_correct_avg if ft_correct_avg > 0 else float('nan')
        clust = sum(clustering_vals) / len(clustering_vals) if clustering_vals else float('nan')

        avg_sols = total_solutions_found / instances_with_solutions if instances_with_solutions > 0 else 0

        print(f"  Instances with solutions: {instances_with_solutions}")
        print(f"  Avg solutions found: {avg_sols:.1f}")
        print(f"  Time: {elapsed:.1f}s")
        print()
        print(f"  1. EPSILON (sign-solution corr):  {eps:.4f}   (expected ~0.072)")
        print(f"  2. TENSION ACCURACY:              {acc*100:.1f}%    (expected ~70%)")
        print(f"  3. FLIP TRIGGER wrong:            {ft_wrong_avg:.3f}")
        print(f"     FLIP TRIGGER correct:          {ft_correct_avg:.3f}")
        print(f"     FLIP TRIGGER RATIO:            {ft_ratio:.2f}x   (expected ~2.0x)")
        print(f"  4. SOLUTION CLUSTERING:           {clust:.3f}   (expected ~0.52)")

        all_results[n] = {
            'epsilon': eps,
            'tension_accuracy': acc,
            'flip_trigger_ratio': ft_ratio,
            'ft_wrong': ft_wrong_avg,
            'ft_correct': ft_correct_avg,
            'clustering': clust,
            'instances': instances_with_solutions,
            'avg_solutions': avg_sols,
            'time': elapsed,
        }

    # ============================================================
    # SUMMARY TABLE
    # ============================================================
    print("\n\n" + "=" * 80)
    print("SUMMARY: SCALING OF BIT MECHANICS CONSTANTS")
    print("=" * 80)
    print(f"{'n':>5} | {'epsilon':>8} | {'tension%':>9} | {'FT ratio':>9} | {'cluster':>8} | {'inst':>5} | {'avg_sol':>8}")
    print("-" * 70)
    for n in test_sizes:
        r = all_results.get(n)
        if r:
            print(f"{n:>5} | {r['epsilon']:>8.4f} | {r['tension_accuracy']*100:>8.1f}% | "
                  f"{r['flip_trigger_ratio']:>8.2f}x | {r['clustering']:>8.3f} | "
                  f"{r['instances']:>5} | {r['avg_solutions']:>8.1f}")

    print("-" * 70)
    print(f"{'exp':>5} | {'~0.072':>8} | {'~70.0%':>9} | {'~2.00x':>9} | {'~0.520':>8} |")
    print()

    # Stability assessment
    print("STABILITY ASSESSMENT:")
    epsilons_all = [all_results[n]['epsilon'] for n in test_sizes if n in all_results]
    accs_all = [all_results[n]['tension_accuracy'] for n in test_sizes if n in all_results]
    ftrs_all = [all_results[n]['flip_trigger_ratio'] for n in test_sizes if n in all_results]

    if epsilons_all:
        eps_mean = sum(epsilons_all) / len(epsilons_all)
        eps_std = math.sqrt(sum((e - eps_mean) ** 2 for e in epsilons_all) / len(epsilons_all))
        if eps_mean > 0:
            print(f"  Epsilon:  mean={eps_mean:.4f}, std={eps_std:.4f}, CV={eps_std/eps_mean:.2f}")
        else:
            print("  Epsilon: no data")

    if accs_all:
        acc_mean = sum(accs_all) / len(accs_all)
        acc_std = math.sqrt(sum((a - acc_mean) ** 2 for a in accs_all) / len(accs_all))
        print(f"  Tension:  mean={acc_mean*100:.1f}%, std={acc_std*100:.1f}%")

    if ftrs_all:
        ftr_vals = [x for x in ftrs_all if not math.isnan(x)]
        if ftr_vals:
            ftr_mean = sum(ftr_vals) / len(ftr_vals)
            ftr_std = math.sqrt(sum((f - ftr_mean) ** 2 for f in ftr_vals) / len(ftr_vals))
            print(f"  FT ratio: mean={ftr_mean:.2f}x, std={ftr_std:.2f}x")

    print("\nDone.")


if __name__ == "__main__":
    run_scaling_test()
