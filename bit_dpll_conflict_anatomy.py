"""
DPLL CONFLICT ANATOMY: Where and why do conflicts arise?

QUESTION: If wrong fixes cause 90% immediate conflict, why does
DPLL need 2^(n^0.75) nodes instead of O(n)?

ANSWER HYPOTHESIS: The 90% conflict rate was measured with ALL signal
vars fixed (oracle) + 1 flipped. In DPLL, at early depths, many vars
are still free → wrong fixes DON'T cause immediate conflicts.

EXPERIMENT: Sequential oracle fix (tension order), track conflict timing.
- Fix vars one at a time, sorted by |tension|
- Some get fixed wrong (use 70% accuracy from tension)
- Measure: when does the first conflict appear?
- Measure: how many UP fixes between decisions?
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


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


def unit_propagate(clauses, n, fixed):
    f = dict(fixed)
    cascade = 0
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; free = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                        sat = True; break
                else:
                    free.append((v, s))
            if not sat and len(free) == 1:
                v, s = free[0]
                if v not in f:
                    f[v] = 1 if s == 1 else 0
                    cascade += 1
                    changed = True
            if not sat and len(free) == 0:
                return f, cascade, True
    return f, cascade, False


# ============================================================
# 1. Sequential fix with tension accuracy — when do conflicts appear?
# ============================================================

def sequential_conflict_timing():
    print("=" * 70)
    print("1. SEQUENTIAL FIX: When do conflicts appear?")
    print("=" * 70)

    random.seed(42)

    for n in [12, 16, 20]:
        first_conflict_depths = []
        total_conflicts = []
        decisions_before_conflict = []

        max_inst = 100 if n <= 16 else 50

        for seed in range(500):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+75000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
                sol = solutions[0]
            else:
                # Use tension-only at n=20 (can't enumerate)
                sol = None
                continue  # skip n=20 for now

            # Compute initial tensions
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            # Fix vars one at a time, using tension sign (70% correct)
            fixed = {}
            first_conflict = None
            n_conflicts = 0
            n_decisions = 0

            for i, v in enumerate(sorted_vars):
                if v in fixed:  # already fixed by UP
                    continue

                # Decision: follow tension sign
                sigma = bit_tension(clauses, n, v, fixed)
                predicted = 1 if sigma >= 0 else 0
                # This has ~70% accuracy
                fixed[v] = predicted
                n_decisions += 1

                # Run UP
                fixed, cascade, conflict = unit_propagate(clauses, n, fixed)

                if conflict:
                    n_conflicts += 1
                    if first_conflict is None:
                        first_conflict = n_decisions
                    break  # in real DPLL, would backtrack

            if first_conflict is not None:
                first_conflict_depths.append(first_conflict)
                total_conflicts.append(n_conflicts)
            else:
                # No conflict = solved in one pass!
                decisions_before_conflict.append(n_decisions)

            if len(first_conflict_depths) + len(decisions_before_conflict) >= max_inst:
                break

        n_total = len(first_conflict_depths) + len(decisions_before_conflict)
        n_no_conflict = len(decisions_before_conflict)

        print(f"\n  n={n}: {n_total} instances")
        print(f"    Solved without conflict: {n_no_conflict}/{n_total} "
              f"({100*n_no_conflict/max(n_total,1):.0f}%)")

        if first_conflict_depths:
            avg_first = sum(first_conflict_depths) / len(first_conflict_depths)
            print(f"    Avg first conflict at decision: {avg_first:.1f} / {n}")
            print(f"    First conflict distribution:")

            # Histogram
            max_d = max(first_conflict_depths)
            for d in range(1, min(max_d+1, n+1)):
                count = sum(1 for x in first_conflict_depths if x == d)
                if count > 0:
                    bar = '#' * (count * 2)
                    print(f"      d={d:>2}: {count:>3} {bar}")


# ============================================================
# 2. Oracle vs tension: fix vars one by one, compare conflict timing
# ============================================================

def oracle_vs_tension_sequential():
    print("\n" + "=" * 70)
    print("2. ORACLE vs TENSION: Sequential fix conflict comparison")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14, 16]:
        oracle_solved = 0
        tension_solved = 0
        oracle_decisions = []
        tension_decisions = []

        for seed in range(200):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+76000000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            sol = solutions[0]

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            # ORACLE sequential fix
            fixed_o = {}
            n_dec_o = 0
            conflict_o = False
            for v in sorted_vars:
                if v in fixed_o: continue
                fixed_o[v] = sol[v]  # TRUE value
                n_dec_o += 1
                fixed_o, _, conflict = unit_propagate(clauses, n, fixed_o)
                if conflict:
                    conflict_o = True; break

            if not conflict_o:
                oracle_solved += 1
                oracle_decisions.append(n_dec_o)

            # TENSION sequential fix
            fixed_t = {}
            n_dec_t = 0
            conflict_t = False
            for v in sorted_vars:
                if v in fixed_t: continue
                sigma = bit_tension(clauses, n, v, fixed_t)
                fixed_t[v] = 1 if sigma >= 0 else 0
                n_dec_t += 1
                fixed_t, _, conflict = unit_propagate(clauses, n, fixed_t)
                if conflict:
                    conflict_t = True; break

            if not conflict_t:
                tension_solved += 1
                tension_decisions.append(n_dec_t)

            if oracle_solved + tension_solved >= 100:
                break

        total = max(oracle_solved, 1)
        print(f"\n  n={n}:")
        print(f"    Oracle solve rate:   {oracle_solved} instances")
        print(f"    Tension solve rate:  {tension_solved} instances")
        if oracle_decisions:
            print(f"    Oracle decisions:    {sum(oracle_decisions)/len(oracle_decisions):.1f}")
        if tension_decisions:
            print(f"    Tension decisions:   {sum(tension_decisions)/len(tension_decisions):.1f}")
        print(f"    UP amplification:    n/{sum(oracle_decisions)/max(len(oracle_decisions),1):.1f} "
              f"= {n/max(sum(oracle_decisions)/max(len(oracle_decisions),1), 1):.1f}× per decision")


# ============================================================
# 3. THE DEPTH-ACCURACY TRADEOFF
# ============================================================

def depth_accuracy_tradeoff():
    print("\n" + "=" * 70)
    print("3. DEPTH-ACCURACY TRADEOFF: How does tension accuracy change?")
    print("=" * 70)

    print("""
    At each sequential decision (tension order), measure:
    - Tension of the chosen variable (updates with context)
    - Whether the tension-guided choice is correct
    - How many vars are already fixed (by decisions + UP)
    """)

    random.seed(42)

    for n in [12, 14, 16]:
        depth_data = {}  # depth -> list of (tension, correct)

        for seed in range(200):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+77000000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            sol = solutions[0]

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            fixed = {}
            decision_num = 0

            for v in sorted_vars:
                if v in fixed: continue
                sigma = bit_tension(clauses, n, v, fixed)
                predicted = 1 if sigma >= 0 else 0
                correct = (predicted == sol[v])

                if decision_num not in depth_data:
                    depth_data[decision_num] = []
                depth_data[decision_num].append({
                    'tension': abs(sigma),
                    'correct': correct,
                    'n_fixed': len(fixed),
                })

                fixed[v] = sol[v]  # Oracle fix to keep going
                decision_num += 1
                fixed, _, conflict = unit_propagate(clauses, n, fixed)
                if conflict: break

            if len(depth_data.get(0, [])) >= 100:
                break

        print(f"\n  n={n}:")
        print(f"  {'dec#':>4} | {'n_obs':>5} | {'avg|t|':>7} | {'accuracy':>8} | "
              f"{'fixed/n':>7}")
        print("  " + "-" * 45)

        for d in sorted(depth_data.keys()):
            entries = depth_data[d]
            if len(entries) < 10: continue
            avg_t = sum(e['tension'] for e in entries) / len(entries)
            acc = 100 * sum(1 for e in entries if e['correct']) / len(entries)
            avg_fixed = sum(e['n_fixed'] for e in entries) / len(entries)
            print(f"  {d:>4} | {len(entries):>5} | {avg_t:>7.3f} | {acc:>7.1f}% | "
                  f"{avg_fixed/n:>7.3f}")


if __name__ == "__main__":
    sequential_conflict_timing()
    oracle_vs_tension_sequential()
    depth_accuracy_tradeoff()
