"""
Hybrid Solver: crystallize confident bits, brute-force the uncertain tail.

Discovery: wrong bits hide at low confidence ranks (54% in bottom 3).
Strategy: fix top (n-k) bits by tension, enumerate 2^k combos for bottom k.
Cost: O(n * m * 2^k) — polynomial if k is constant.

Key question: does k stay constant as n grows?
"""

import random
import time
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
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    sat = True; break
            else:
                rem.append((v, s))
        if sat:
            continue
        for v, s in rem:
            if v == var:
                w = 1.0 / max(1, len(rem))
                if s == 1: p1 += w
                else: p0 += w
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
                s = False; rem = []; vs = None
                for v, si in clause:
                    if v in fixed:
                        if (si == 1 and fixed[v] == 1) or (si == -1 and fixed[v] == 0):
                            s = True; break
                    else:
                        rem.append((v, si))
                        if v == var: vs = si
                if s or vs is None:
                    continue
                oh = 0.0
                for v, si in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if si == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# THE HYBRID SOLVER
# ============================================================

def solve_hybrid(clauses, n, k_tail):
    """
    1. Compute v4 tensions
    2. Sort bits by |tension|
    3. Fix top (n-k) bits by tension direction
    4. Try all 2^k combinations for bottom k bits
    5. Return first valid solution
    """
    tensions = tension_v4(clauses, n, {}, 10)
    sorted_bits = sorted(range(n), key=lambda v: -abs(tensions.get(v, 0)))

    confident_bits = sorted_bits[:n - k_tail]
    uncertain_bits = sorted_bits[n - k_tail:]

    # Fix confident bits
    fixed = {}
    for var in confident_bits:
        fixed[var] = 1 if tensions.get(var, 0) >= 0 else 0

    # Try all combos for uncertain bits
    for combo in range(2 ** k_tail):
        for idx, var in enumerate(uncertain_bits):
            fixed[var] = (combo >> idx) & 1

        assignment = [fixed.get(v, 0) for v in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            return assignment, True, combo + 1  # combos tried

    return None, False, 2 ** k_tail


# ============================================================
# ITERATIVE HYBRID: crystallize in phases
# ============================================================

def solve_iterative_hybrid(clauses, n, k_tail):
    """
    Phase 1: Fix most confident bits with v4 tension, with unit propagation
    Phase 2: Enumerate uncertain tail
    """
    tensions = tension_v4(clauses, n, {}, 10)
    sorted_bits = sorted(range(n), key=lambda v: -abs(tensions.get(v, 0)))

    confident_bits = sorted_bits[:n - k_tail]
    uncertain_bits = sorted_bits[n - k_tail:]

    # Phase 1: crystallize with unit propagation
    fixed = {}
    for var in confident_bits:
        t = bit_tension(clauses, n, var, fixed)  # recompute with current fixed
        fixed[var] = 1 if t >= 0 else 0

        # Unit propagation
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False
                free = []
                for v, s in clause:
                    if v in fixed:
                        if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                            satisfied = True; break
                    else:
                        free.append((v, s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    val = 1 if s == 1 else 0
                    if v not in fixed:
                        fixed[v] = val
                        changed = True
                        # Remove from uncertain if it was there
                        if v in uncertain_bits:
                            uncertain_bits.remove(v)

    # Phase 2: enumerate remaining uncertain bits
    still_uncertain = [v for v in uncertain_bits if v not in fixed]
    k_actual = len(still_uncertain)

    for combo in range(2 ** k_actual):
        test_fixed = dict(fixed)
        for idx, var in enumerate(still_uncertain):
            test_fixed[var] = (combo >> idx) & 1

        assignment = [test_fixed.get(v, 0) for v in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            return assignment, True, combo + 1, k_actual

    return None, False, 2 ** k_actual, k_actual


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    # Test 1: What k is needed for different solve rates?
    print("=" * 70)
    print("TEST 1: Hybrid solver — solve rate by tail size k")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        print(f"\n  ratio={ratio}:")
        print(f"  {'k':>4} | {'combos':>8} | {'solved':>8} | {'rate':>8}")
        print("  " + "-" * 40)

        for k in [0, 1, 2, 3, 4, 5]:
            solved = 0
            total = 0

            for seed in range(200):
                clauses = random_3sat(12, int(ratio * 12), seed=seed)
                solutions = find_solutions(clauses, 12)
                if not solutions:
                    continue
                total += 1

                _, success, _ = solve_hybrid(clauses, 12, k)
                if success:
                    solved += 1

            rate = solved / total * 100 if total > 0 else 0
            print(f"  {k:>4} | {2**k:>8} | {solved:>8} | {rate:>7.1f}%")

    # Test 2: Iterative hybrid
    print("\n" + "=" * 70)
    print("TEST 2: Iterative hybrid (crystallize + UP + enumerate)")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        print(f"\n  ratio={ratio}:")
        print(f"  {'k_init':>6} | {'k_actual':>8} | {'solved':>8} | "
              f"{'rate':>8} | {'avg_combos':>10}")
        print("  " + "-" * 55)

        for k in [2, 3, 4, 5]:
            solved = 0
            total = 0
            total_combos = 0
            total_k_actual = 0

            for seed in range(200):
                clauses = random_3sat(12, int(ratio * 12), seed=seed)
                solutions = find_solutions(clauses, 12)
                if not solutions:
                    continue
                total += 1

                _, success, combos, k_actual = solve_iterative_hybrid(clauses, 12, k)
                if success:
                    solved += 1
                total_combos += combos
                total_k_actual += k_actual

            rate = solved / total * 100 if total > 0 else 0
            avg_c = total_combos / total if total > 0 else 0
            avg_k = total_k_actual / total if total > 0 else 0
            print(f"  {k:>6} | {avg_k:>8.1f} | {solved:>8} | "
                  f"{rate:>7.1f}% | {avg_c:>10.1f}")

    # Test 3: SCALING — does k_tail grow with n?
    print("\n" + "=" * 70)
    print("TEST 3: SCALING — minimum k for 95% solve rate")
    print("=" * 70)

    print(f"\n  {'n':>4} | {'k=0':>6} | {'k=2':>6} | {'k=3':>6} | "
          f"{'k=4':>6} | {'k=5':>6} | {'k for 95%':>10}")
    print("  " + "-" * 60)

    for n in [10, 12, 14, 16, 18, 20]:
        rates = {}

        for k in [0, 2, 3, 4, 5]:
            if k > n - 2:
                continue
            solved = 0
            total = 0

            n_trials = 100 if n <= 16 else 50

            for seed in range(n_trials):
                clauses = random_3sat(n, int(4.27 * n), seed=seed)

                if n <= 16:
                    solutions = find_solutions(clauses, n)
                    if not solutions:
                        continue

                total += 1

                _, success, _, _ = solve_iterative_hybrid(clauses, n, k)
                if success:
                    solved += 1

            rates[k] = solved / total * 100 if total > 0 else 0

        # Find min k for 95%
        min_k = "?"
        for k in sorted(rates.keys()):
            if rates[k] >= 95:
                min_k = str(k)
                break

        row = f"  {n:>4} |"
        for k in [0, 2, 3, 4, 5]:
            if k in rates:
                row += f" {rates[k]:>5.1f}% |"
            else:
                row += f"    -- |"
        row += f" {min_k:>10}"
        print(row)

    # Test 4: Timing
    print("\n" + "=" * 70)
    print("TEST 4: Timing comparison")
    print("=" * 70)

    for n in [12, 16, 20]:
        print(f"\n  n={n}:")

        for label, solver in [
            ("tension only", lambda c, nn: (solve_iterative_hybrid(c, nn, 0)[0],
                                            solve_iterative_hybrid(c, nn, 0)[1])),
            ("hybrid k=3",  lambda c, nn: (solve_iterative_hybrid(c, nn, 3)[0],
                                            solve_iterative_hybrid(c, nn, 3)[1])),
            ("hybrid k=5",  lambda c, nn: (solve_iterative_hybrid(c, nn, 5)[0],
                                            solve_iterative_hybrid(c, nn, 5)[1])),
        ]:
            solved = 0
            total = 0
            t_total = 0

            for seed in range(50):
                clauses = random_3sat(n, int(4.27 * n), seed=seed)
                total += 1

                t0 = time.time()
                result, success = solver(clauses, n)
                t1 = time.time()
                t_total += (t1 - t0)

                if success and result is not None:
                    if evaluate(clauses, result) == len(clauses):
                        solved += 1

            avg_t = t_total / total * 1000
            print(f"    {label:>15}: {solved}/{total} solved, {avg_t:.1f}ms")
