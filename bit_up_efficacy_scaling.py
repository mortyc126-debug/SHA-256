"""
UP EFFICACY SCALING: How does Unit Propagation cascade degrade with n?

KEY HYPOTHESIS:
  At small n (10-20): UP resolves 90-95% of noise vars → k ≈ O(1)
  At large n (100+):  UP resolves fewer → remaining noise vars ≈ n^T
  This degradation explains k = O(n^T)

EXPERIMENT:
  1. Generate random 3-SAT at threshold (r=4.27)
  2. Solve with MiniSat to get true solution
  3. Compute tensions, classify signal/noise (threshold |t|>0.1)
  4. Fix signal vars to TRUE values (oracle), run UP
  5. Count remaining vars after UP
  6. Measure log(remaining)/log(n) → should converge to T ≈ 0.75

  Also test: fix ALL vars with |t|>0 to oracle values, run UP.
  And: fix k vars (sorted by |t|) to oracle, measure remaining vs k.
"""

import random
import math
import subprocess
import os
import sys
from bit_catalog_static import random_3sat


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
    """Run UP from given fixed assignments. Return new fixed dict and count."""
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
                return f, cascade, True  # conflict
    return f, cascade, False


def solve_minisat(n, clauses, timeout=60):
    """Solve with MiniSat, return solution or None."""
    filename = "/tmp/up_test.cnf"
    outfile = filename + ".out"
    m = len(clauses)

    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for clause in clauses:
            lits = []
            for v, s in clause:
                lits.append(str((v+1) * s))
            f.write(" ".join(lits) + " 0\n")

    try:
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout
        )
        if os.path.exists(outfile):
            with open(outfile) as f:
                line1 = f.readline().strip()
                if line1 == "SAT":
                    vals = f.readline().strip().split()
                    sol = [0] * n
                    for v in vals:
                        vi = int(v)
                        if vi > 0 and vi <= n:
                            sol[vi-1] = 1
                        elif vi < 0 and -vi <= n:
                            sol[-vi-1] = 0
                    return sol
        return None
    except subprocess.TimeoutExpired:
        return None
    finally:
        for fn in [filename, outfile]:
            if os.path.exists(fn): os.remove(fn)


def find_solutions_small(clauses, n):
    """Brute-force for small n."""
    solutions = []
    for i in range(2**n):
        a = [(i >> j) & 1 for j in range(n)]
        ok = True
        for clause in clauses:
            sat = False
            for v, s in clause:
                if (s==1 and a[v]==1) or (s==-1 and a[v]==0):
                    sat = True; break
            if not sat:
                ok = False; break
        if ok:
            solutions.append(a)
    return solutions


# ============================================================
# 1. Oracle UP efficacy: fix signal vars correctly, count remaining
# ============================================================

def oracle_up_efficacy():
    print("=" * 70)
    print("1. ORACLE UP EFFICACY vs n")
    print("=" * 70)

    print(f"\n  {'n':>5} | {'inst':>4} | {'signal':>6} | {'noise':>5} | "
          f"{'UP fix':>6} | {'remain':>6} | {'rem/n':>6} | "
          f"{'log(r)/log(n)':>13} | {'T pred':>6}")
    print("  " + "-" * 85)

    all_data = []  # (n, avg_remaining)

    for n in [10, 14, 20, 30, 50, 75, 100, 150, 200, 300]:
        n_inst = 30 if n <= 50 else (20 if n <= 100 else 10)
        remaining_counts = []
        signal_counts = []
        up_fix_counts = []

        for seed in range(n_inst * 5):
            random.seed(seed + 90000000)
            clauses = random_3sat(n, int(4.27 * n), seed=seed+90000000)

            # Get solution
            if n <= 16:
                sols = find_solutions_small(clauses, n)
                if not sols: continue
                sol = sols[0]
            else:
                sol = solve_minisat(n, clauses, timeout=30)
                if sol is None: continue

            # Compute tensions
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            # Classify: signal = |t| > 0.1
            signal_vars = [v for v in range(n) if abs(tensions[v]) > 0.1]
            signal_counts.append(len(signal_vars))

            # Oracle fix: signal vars get TRUE values
            fixed = {v: sol[v] for v in signal_vars}

            # Run UP
            fixed_after, cascade, conflict = unit_propagate(clauses, n, fixed)
            if conflict:
                continue  # shouldn't happen with oracle values

            up_fixed = len(fixed_after) - len(fixed)
            up_fix_counts.append(up_fixed)
            remaining = n - len(fixed_after)
            remaining_counts.append(remaining)

            if len(remaining_counts) >= n_inst:
                break

        if remaining_counts and len(remaining_counts) >= 3:
            avg_sig = sum(signal_counts) / len(signal_counts)
            avg_up = sum(up_fix_counts) / len(up_fix_counts)
            avg_rem = sum(remaining_counts) / len(remaining_counts)

            log_ratio = (math.log(max(avg_rem, 0.1)) / math.log(n))
            T = 0.747

            all_data.append((n, avg_rem))

            print(f"  {n:>5} | {len(remaining_counts):>4} | {avg_sig:>6.1f} | "
                  f"{n-avg_sig:>5.1f} | {avg_up:>6.1f} | {avg_rem:>6.1f} | "
                  f"{avg_rem/n:>6.3f} | {log_ratio:>13.3f} | {T:>6.3f}")

    # Fit power law to remaining vs n
    if len(all_data) >= 3:
        valid = [(n, r) for n, r in all_data if r > 0.1 and n >= 20]
        if len(valid) >= 3:
            log_n = [math.log(n) for n, r in valid]
            log_r = [math.log(r) for n, r in valid]
            m = len(valid)
            mx = sum(log_n)/m; my = sum(log_r)/m
            sxx = sum((x-mx)**2 for x in log_n)
            sxy = sum((log_n[i]-mx)*(log_r[i]-my) for i in range(m))
            beta = sxy/sxx if sxx > 0 else 0
            c = math.exp(my - beta * mx)
            print(f"\n  POWER LAW FIT (n >= 20): remaining = {c:.3f} × n^{beta:.4f}")
            print(f"  Predicted exponent (T): {0.747:.3f}")
            print(f"  Measured exponent:      {beta:.3f}")

    return all_data


# ============================================================
# 2. Gradual fix: fix k vars sorted by |tension|, measure UP cascade
# ============================================================

def gradual_fix_analysis():
    print("\n" + "=" * 70)
    print("2. GRADUAL FIX: How UP cascade grows as more vars are fixed")
    print("=" * 70)

    print("""
    Fix vars one by one (sorted by |tension| desc, oracle values).
    After each fix, run UP and record how many additional vars get fixed.
    This shows the UP "percolation transition" as function of fix fraction.
    """)

    random.seed(42)

    for n in [50, 100, 200]:
        n_inst = 15 if n <= 100 else 8
        fractions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        frac_remaining = {f: [] for f in fractions}

        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+95000000)
            sol = solve_minisat(n, clauses, timeout=30)
            if sol is None: continue

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            for frac in fractions:
                k = int(frac * n)
                fix_vars = sorted_vars[:k]
                fixed = {v: sol[v] for v in fix_vars}

                fixed_after, cascade, conflict = unit_propagate(clauses, n, fixed)
                if not conflict:
                    remaining = n - len(fixed_after)
                    frac_remaining[frac].append(remaining)

            if len(frac_remaining[0.5]) >= n_inst:
                break

        print(f"\n  n={n}: (oracle fix k vars, then UP)")
        print(f"  {'frac fixed':>10} | {'k':>4} | {'remaining':>9} | "
              f"{'UP resolved':>11} | {'total fixed':>11}")
        print("  " + "-" * 55)

        for frac in fractions:
            if frac_remaining[frac]:
                k = int(frac * n)
                avg_rem = sum(frac_remaining[frac]) / len(frac_remaining[frac])
                up_resolved = n - k - avg_rem
                total_fixed = k + up_resolved
                print(f"  {frac:>10.1f} | {k:>4} | {avg_rem:>9.1f} | "
                      f"{up_resolved:>11.1f} | {total_fixed:>11.1f}")


# ============================================================
# 3. THE CRITICAL FRACTION: Where does UP become supercritical?
# ============================================================

def critical_fraction():
    print("\n" + "=" * 70)
    print("3. UP CRITICAL FRACTION: Where does cascade become macroscopic?")
    print("=" * 70)

    print("""
    Theory: UP cascade is supercritical when expected new unit clauses
    per fix > 1. This happens at some critical fix fraction f_c.

    Predict: f_c ≈ 1/(3r) ≈ 0.08 (very early in the fix sequence)

    If supercritical at f = 0.25 (= 1-T):
      → cascade covers most remaining vars
      → only "outliers" survive as independent clusters
    """)

    random.seed(42)

    for n in [100, 200]:
        n_inst = 10

        # Fine-grained fractions
        fracs = [i/20 for i in range(1, 20)]
        cascade_sizes = {f: [] for f in fracs}

        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+97000000)
            sol = solve_minisat(n, clauses, timeout=30)
            if sol is None: continue

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            for frac in fracs:
                k = int(frac * n)
                fixed = {v: sol[v] for v in sorted_vars[:k]}
                fixed_after, cascade, conflict = unit_propagate(clauses, n, fixed)
                if not conflict:
                    cascade_sizes[frac].append(cascade)

            if len(cascade_sizes[0.5]) >= n_inst:
                break

        print(f"\n  n={n}:")
        print(f"  {'frac':>5} | {'k':>4} | {'avg cascade':>11} | "
              f"{'cascade/noise':>13} | {'supercritical':>13}")
        print("  " + "-" * 60)

        for frac in fracs:
            if cascade_sizes[frac]:
                k = int(frac * n)
                noise = n - k
                avg_c = sum(cascade_sizes[frac]) / len(cascade_sizes[frac])
                sc = "YES" if avg_c > 0.5 * noise else ""
                print(f"  {frac:>5.2f} | {k:>4} | {avg_c:>11.1f} | "
                      f"{avg_c/max(noise,1):>13.3f} | {sc:>13}")


# ============================================================
# 4. Wrong fix cascade: how far does a wrong fix propagate?
# ============================================================

def wrong_fix_cascade():
    print("\n" + "=" * 70)
    print("4. WRONG FIX CASCADE: How many vars get wrongly fixed by UP?")
    print("=" * 70)

    print("""
    When a signal var is fixed WRONGLY, UP propagates the error.
    Measure: fix ONE var wrong (rest oracle), count wrongly-fixed by UP.
    This tells us the "damage radius" of a single wrong decision.
    """)

    random.seed(42)

    for n in [50, 100, 200]:
        n_inst = 10
        wrong_cascade = []
        right_cascade = []
        conflict_rate = []

        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+98000000)
            sol = solve_minisat(n, clauses, timeout=30)
            if sol is None: continue

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]),
                                reverse=True)

            # Fix all signal vars oracle, EXCEPT the first one which we flip
            signal_vars = [v for v in sorted_vars if abs(tensions[v]) > 0.1]
            if not signal_vars: continue

            # Wrong fix: flip first signal var
            wrong_var = signal_vars[0]
            fixed_wrong = {v: sol[v] for v in signal_vars}
            fixed_wrong[wrong_var] = 1 - sol[wrong_var]

            # Right fix: all oracle
            fixed_right = {v: sol[v] for v in signal_vars}

            f_w, c_w, conflict_w = unit_propagate(clauses, n, fixed_wrong)
            f_r, c_r, conflict_r = unit_propagate(clauses, n, fixed_right)

            conflict_rate.append(1 if conflict_w else 0)

            if not conflict_w and not conflict_r:
                # Count wrong values in wrong cascade
                n_wrong = sum(1 for v in f_w if v in f_r and f_w[v] != f_r[v])
                wrong_cascade.append(n_wrong)
                right_cascade.append(c_r)

            if len(conflict_rate) >= n_inst:
                break

        if wrong_cascade:
            avg_wrong = sum(wrong_cascade) / len(wrong_cascade)
            avg_right = sum(right_cascade) / len(right_cascade)
            avg_conflict = sum(conflict_rate) / len(conflict_rate)
            print(f"\n  n={n}:")
            print(f"    Conflict from 1 wrong fix: {100*avg_conflict:.0f}%")
            print(f"    Wrongly-fixed by cascade:  {avg_wrong:.1f}")
            print(f"    Correctly-fixed by cascade: {avg_right:.1f}")
            print(f"    Damage radius / n:         {avg_wrong/n:.3f}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    data = oracle_up_efficacy()

    gradual_fix_analysis()

    critical_fraction()

    wrong_fix_cascade()

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY: The α = T Mechanism")
    print("=" * 70)
    print("""
    The scaling law k = O(n^T) arises from:

    1. VARIABLE CLASSIFICATION by temperature T:
       - (1-T)·n signal vars with |tension| > threshold
       - T·n noise vars with |tension| ≤ threshold

    2. UP CASCADE from oracle signal fixes:
       - Supercritical at f = 1-T (branching factor > 1)
       - Resolves MOST noise vars
       - Remaining vars = n^β where β measures cascade incompleteness

    3. WRONG FIX DAMAGE:
       - Each wrong signal decision has damage radius R(n)
       - With 30% wrong rate: effective "wasted" subtree ∝ 2^(0.3 × R(n))
       - R(n) × 0.3 × n_decisions scales as n^T

    4. TOTAL SEARCH:
       k = log₂(nodes) = c × (remaining clusters + wrong fix cost)
         = c × n^T

    The exponent T = temperature because temperature DEFINES the
    signal/noise boundary, and this boundary determines both:
    - How many vars DPLL gets wrong
    - How effective UP is at cleaning up
    """)
