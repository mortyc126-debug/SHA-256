"""
Combo Solver: Multi-crystal voting + WalkSAT hybrid.

Strategy 1: Use multi-crystal votes for confident bits, WalkSAT for uncertain.
Strategy 2: Use multi-crystal voted assignment as seed for WalkSAT.

Test scaling at n=12, 16, 20, 30 with ratio=4.27.
"""

import random
import time


# ============================================================
# Core SAT functions (inline, self-contained)
# ============================================================

def random_3sat(n_vars, n_clauses, seed=None):
    if seed is not None:
        random.seed(seed)
    clauses = []
    for _ in range(n_clauses):
        vs = random.sample(range(n_vars), 3)
        signs = [random.choice([1, -1]) for _ in range(3)]
        clauses.append(list(zip(vs, signs)))
    return clauses


def find_solutions(clauses, n):
    """Brute-force all solutions (only feasible for small n)."""
    solutions = []
    for i in range(2**n):
        assignment = [(i >> j) & 1 for j in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            solutions.append(assignment)
    return solutions


def evaluate(clauses, assignment):
    """Count satisfied clauses."""
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            if (sign == 1 and assignment[var] == 1) or \
               (sign == -1 and assignment[var] == 0):
                sat += 1
                break
    return sat


def bit_tension(clauses, n, var, fixed=None):
    """Weighted tension: how much does the formula want var=1 vs var=0."""
    if fixed is None:
        fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False
        rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True
                    break
            else:
                rem.append((v, s))
        if sat:
            continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1:
                    p1 += w
                else:
                    p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# Multi-crystal: crystallize with random ordering, vote
# ============================================================

def crystallize_one(clauses, n, rng):
    """Single crystallization run with random variable ordering."""
    order = list(range(n))
    rng.shuffle(order)
    fixed = {}
    for var in order:
        sigma = bit_tension(clauses, n, var, fixed)
        fixed[var] = 1 if sigma >= 0 else 0
    return [fixed[v] for v in range(n)]


def multi_crystal(clauses, n, n_runs=15, seed=None):
    """
    Run crystallization n_runs times with different random orderings.
    Return per-bit votes (counts of 0 and 1), voted assignment, and confidences.
    """
    votes = [[0, 0] for _ in range(n)]
    rng = random.Random(seed)

    for run in range(n_runs):
        assignment = crystallize_one(clauses, n, rng)
        sat = evaluate(clauses, assignment)
        # Weight by fraction of clauses satisfied
        weight = sat / len(clauses)
        for v in range(n):
            votes[v][assignment[v]] += weight

    predictions = {}
    confidences = {}
    for v in range(n):
        total = votes[v][0] + votes[v][1]
        if total > 0:
            predictions[v] = 1 if votes[v][1] > votes[v][0] else 0
            confidences[v] = max(votes[v][0], votes[v][1]) / total
        else:
            predictions[v] = 0
            confidences[v] = 0.5

    voted_assignment = [predictions[v] for v in range(n)]
    return voted_assignment, confidences


# ============================================================
# WalkSAT
# ============================================================

def walksat(clauses, n, max_flips=10000, noise_prob=0.3, init=None):
    """WalkSAT local search. Optionally seed with init assignment."""
    if init is not None:
        assignment = list(init)
    else:
        assignment = [random.randint(0, 1) for _ in range(n)]

    for flip in range(max_flips):
        unsat = []
        for ci, clause in enumerate(clauses):
            satisfied = False
            for v, s in clause:
                if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                    satisfied = True
                    break
            if not satisfied:
                unsat.append(ci)

        if not unsat:
            return assignment, True, flip

        ci = random.choice(unsat)
        clause = clauses[ci]

        if random.random() < noise_prob:
            v, s = random.choice(clause)
            assignment[v] = 1 - assignment[v]
        else:
            best_var = None
            best_break = float('inf')
            for v, s in clause:
                assignment[v] = 1 - assignment[v]
                breaks = 0
                for cj, cl in enumerate(clauses):
                    if cj == ci:
                        continue
                    sat = False
                    for vv, ss in cl:
                        if (ss == 1 and assignment[vv] == 1) or \
                           (ss == -1 and assignment[vv] == 0):
                            sat = True
                            break
                    if not sat:
                        breaks += 1
                assignment[v] = 1 - assignment[v]

                if breaks < best_break:
                    best_break = breaks
                    best_var = v

            if best_var is not None:
                assignment[best_var] = 1 - assignment[best_var]

    return assignment, False, max_flips


# ============================================================
# Strategy 1: Crystal-confident bits + WalkSAT for uncertain
# ============================================================

def combo_crystal_walksat(clauses, n, confidence_threshold=0.7,
                          n_crystal_runs=15, max_flips=10000, n_ws_tries=10):
    """
    1. Multi-crystal to get per-bit votes and confidences.
    2. Fix confident bits, use WalkSAT to search over uncertain bits.
    """
    voted, confidences = multi_crystal(clauses, n, n_crystal_runs)

    # Identify confident vs uncertain bits
    confident_bits = {v: voted[v] for v in range(n) if confidences[v] >= confidence_threshold}
    uncertain_bits = [v for v in range(n) if confidences[v] < confidence_threshold]

    best_assignment = None
    best_sat = 0

    for _ in range(n_ws_tries):
        # Start from voted assignment, let WalkSAT improve
        init = list(voted)
        # Randomize uncertain bits
        for v in uncertain_bits:
            init[v] = random.randint(0, 1)

        result, found, flips = walksat(clauses, n, max_flips, init=init)
        sat = evaluate(clauses, result)

        if sat > best_sat:
            best_sat = sat
            best_assignment = list(result)

        if found:
            return best_assignment, True, flips

    return best_assignment, best_sat == len(clauses), -1


# ============================================================
# Strategy 2: Crystal seed for WalkSAT
# ============================================================

def crystal_seeded_walksat(clauses, n, n_crystal_runs=15,
                           max_flips=10000, n_ws_tries=10):
    """
    Use multi-crystal voted assignment as WalkSAT starting point.
    """
    voted, _ = multi_crystal(clauses, n, n_crystal_runs)

    best_assignment = None
    best_sat = 0
    total_flips = 0

    for _ in range(n_ws_tries):
        result, found, flips = walksat(clauses, n, max_flips, init=voted)
        total_flips += flips if flips >= 0 else max_flips
        sat = evaluate(clauses, result)

        if sat > best_sat:
            best_sat = sat
            best_assignment = list(result)

        if found:
            return best_assignment, True, total_flips

    return best_assignment, best_sat == len(clauses), total_flips


# ============================================================
# Baseline: Pure WalkSAT (random init)
# ============================================================

def pure_walksat(clauses, n, max_flips=10000, n_tries=10):
    """Multiple WalkSAT attempts with random initialization."""
    best_assignment = None
    best_sat = 0
    total_flips = 0

    for _ in range(n_tries):
        result, found, flips = walksat(clauses, n, max_flips)
        total_flips += flips if flips >= 0 else max_flips
        sat = evaluate(clauses, result)

        if sat > best_sat:
            best_sat = sat
            best_assignment = list(result)

        if found:
            return best_assignment, True, total_flips

    return best_assignment, best_sat == len(clauses), total_flips


# ============================================================
# Main experiment
# ============================================================

if __name__ == "__main__":
    RATIO = 4.27
    N_INSTANCES = 30  # per size
    N_CRYSTAL_RUNS = 15
    MAX_FLIPS = 10000
    N_WS_TRIES = 10

    print("=" * 80)
    print("COMBO SOLVER: Multi-Crystal + WalkSAT Hybrid")
    print(f"ratio={RATIO}, {N_CRYSTAL_RUNS} crystal runs, "
          f"{MAX_FLIPS} max flips, {N_WS_TRIES} WalkSAT tries")
    print("=" * 80)

    sizes = [12, 16, 20, 30]

    for n in sizes:
        n_clauses = int(RATIO * n)
        print(f"\n{'='*70}")
        print(f"  n={n}, clauses={n_clauses}")
        print(f"{'='*70}")

        stats = {
            'pure_walksat':      {'solved': 0, 'flips': 0, 'time': 0.0, 'tested': 0},
            'crystal_seed':      {'solved': 0, 'flips': 0, 'time': 0.0, 'tested': 0},
            'combo_confident':   {'solved': 0, 'flips': 0, 'time': 0.0, 'tested': 0},
        }

        # For small n, also track bit accuracy against ground truth
        if n <= 20:
            accuracy_stats = {
                'multi_crystal': {'correct': 0, 'total': 0},
                'pure_walksat':  {'correct': 0, 'total': 0},
                'combo':         {'correct': 0, 'total': 0},
            }
        else:
            accuracy_stats = None

        instances_with_solutions = 0

        for seed in range(N_INSTANCES):
            clauses = random_3sat(n, n_clauses, seed=seed + 7000)

            # Ground truth for small n
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions:
                    continue
                has_solution = True
            else:
                # For n>16, can't brute force; just run solvers
                has_solution = None  # unknown
                solutions = None

            instances_with_solutions += 1

            # --- Pure WalkSAT ---
            t0 = time.time()
            pw_assign, pw_found, pw_flips = pure_walksat(
                clauses, n, MAX_FLIPS, N_WS_TRIES)
            t1 = time.time()
            stats['pure_walksat']['tested'] += 1
            stats['pure_walksat']['time'] += t1 - t0
            if pw_found:
                stats['pure_walksat']['solved'] += 1
                stats['pure_walksat']['flips'] += pw_flips

            # --- Crystal-seeded WalkSAT ---
            t0 = time.time()
            cs_assign, cs_found, cs_flips = crystal_seeded_walksat(
                clauses, n, N_CRYSTAL_RUNS, MAX_FLIPS, N_WS_TRIES)
            t1 = time.time()
            stats['crystal_seed']['tested'] += 1
            stats['crystal_seed']['time'] += t1 - t0
            if cs_found:
                stats['crystal_seed']['solved'] += 1
                stats['crystal_seed']['flips'] += cs_flips

            # --- Combo: confident crystal + WalkSAT ---
            t0 = time.time()
            co_assign, co_found, co_flips = combo_crystal_walksat(
                clauses, n, confidence_threshold=0.7,
                n_crystal_runs=N_CRYSTAL_RUNS, max_flips=MAX_FLIPS,
                n_ws_tries=N_WS_TRIES)
            t1 = time.time()
            stats['combo_confident']['tested'] += 1
            stats['combo_confident']['time'] += t1 - t0
            if co_found:
                stats['combo_confident']['solved'] += 1
                stats['combo_confident']['flips'] += co_flips if co_flips >= 0 else 0

            # --- Bit accuracy (small n only) ---
            if accuracy_stats is not None and solutions:
                prob_1 = [sum(s[v] for s in solutions) / len(solutions)
                          for v in range(n)]
                correct_val = [1 if p > 0.5 else 0 for p in prob_1]

                # Multi-crystal accuracy
                voted, confs = multi_crystal(clauses, n, N_CRYSTAL_RUNS, seed=seed)
                for v in range(n):
                    accuracy_stats['multi_crystal']['total'] += 1
                    if voted[v] == correct_val[v]:
                        accuracy_stats['multi_crystal']['correct'] += 1

                # Pure WalkSAT final assignment accuracy
                if pw_found:
                    for v in range(n):
                        accuracy_stats['pure_walksat']['total'] += 1
                        if pw_assign[v] == correct_val[v]:
                            accuracy_stats['pure_walksat']['correct'] += 1

                # Combo accuracy
                if co_found:
                    for v in range(n):
                        accuracy_stats['combo']['total'] += 1
                        if co_assign[v] == correct_val[v]:
                            accuracy_stats['combo']['correct'] += 1

        # --- Report ---
        print(f"\n  Instances tested: {instances_with_solutions}")
        print(f"\n  {'method':>20} | {'solved':>8} | {'solve%':>7} | "
              f"{'avg flips':>10} | {'total time':>10}")
        print("  " + "-" * 70)

        for name in ['pure_walksat', 'crystal_seed', 'combo_confident']:
            s = stats[name]
            tested = s['tested']
            if tested == 0:
                continue
            solved = s['solved']
            pct = solved / tested * 100
            avg_flips = s['flips'] / solved if solved > 0 else float('inf')
            print(f"  {name:>20} | {solved:>8} | {pct:>6.1f}% | "
                  f"{avg_flips:>10.0f} | {s['time']:>9.2f}s")

        if accuracy_stats:
            print(f"\n  Bit accuracy (vs ground truth majority):")
            for name in ['multi_crystal', 'pure_walksat', 'combo']:
                a = accuracy_stats[name]
                if a['total'] > 0:
                    acc = a['correct'] / a['total'] * 100
                    print(f"    {name:>20}: {acc:.1f}% ({a['correct']}/{a['total']})")

    # ============================================================
    # Detailed view for n=12: confidence distribution
    # ============================================================
    print("\n" + "=" * 80)
    print("DETAILED: n=12 confidence distribution and combo effect")
    print("=" * 80)

    n = 12
    n_clauses = int(RATIO * n)
    conf_buckets = {'high': [0, 0], 'medium': [0, 0], 'low': [0, 0]}

    for seed in range(50):
        clauses = random_3sat(n, n_clauses, seed=seed + 8000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue

        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        voted, confs = multi_crystal(clauses, n, N_CRYSTAL_RUNS, seed=seed)

        for v in range(n):
            c = confs[v]
            correct = 1 if voted[v] == correct_val[v] else 0
            if c >= 0.8:
                bucket = 'high'
            elif c >= 0.6:
                bucket = 'medium'
            else:
                bucket = 'low'
            conf_buckets[bucket][0] += correct
            conf_buckets[bucket][1] += 1

    print(f"\n  {'confidence':>15} | {'accuracy':>10} | {'count':>6}")
    print("  " + "-" * 40)
    for bucket in ['high', 'medium', 'low']:
        correct, total = conf_buckets[bucket]
        if total > 0:
            print(f"  {bucket:>15} | {correct/total*100:>9.1f}% | {total:>6}")
        else:
            print(f"  {bucket:>15} | {'N/A':>10} | {0:>6}")

    # ============================================================
    # Head-to-head: crystal seed vs random seed for WalkSAT at n=30
    # ============================================================
    print("\n" + "=" * 80)
    print("HEAD-TO-HEAD: Crystal seed vs random seed WalkSAT (n=30)")
    print("=" * 80)

    n = 30
    n_clauses = int(RATIO * n)
    crystal_wins = 0
    random_wins = 0
    ties = 0

    for seed in range(20):
        clauses = random_3sat(n, n_clauses, seed=seed + 9000)

        # Crystal-seeded
        cs_assign, cs_found, cs_flips = crystal_seeded_walksat(
            clauses, n, N_CRYSTAL_RUNS, MAX_FLIPS, N_WS_TRIES)
        cs_sat = evaluate(clauses, cs_assign)

        # Random-seeded
        pw_assign, pw_found, pw_flips = pure_walksat(
            clauses, n, MAX_FLIPS, N_WS_TRIES)
        pw_sat = evaluate(clauses, pw_assign)

        marker = ""
        if cs_sat > pw_sat:
            crystal_wins += 1
            marker = " << crystal better"
        elif pw_sat > cs_sat:
            random_wins += 1
            marker = " << random better"
        else:
            ties += 1

        print(f"  seed={seed+9000}: crystal={cs_sat}/{n_clauses}"
              f"{'(SOL)' if cs_found else ''}, "
              f"random={pw_sat}/{n_clauses}"
              f"{'(SOL)' if pw_found else ''}{marker}")

    print(f"\n  Crystal wins: {crystal_wins}, "
          f"Random wins: {random_wins}, Ties: {ties}")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
