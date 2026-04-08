"""
RESIDUAL CLUSTER EXPONENT β(r) vs DPLL SCALING EXPONENT α(r)

KEY QUESTION: Does the UP cascade residual exponent β(r) track the
DPLL scaling exponent α(r) across different ratios?

If β(r) ≈ α(r) + δ for all ratios → the mechanism is confirmed:
  DPLL cost = f(residual clusters) at all ratios

From bit_derive_k_scaling.py:
  r=3.0:  α = 0.22
  r=3.5:  α = 0.35
  r=3.86: α = 0.48
  r=4.0:  α = 0.60
  r=4.27: α = 0.76

EXPERIMENT: For each ratio, measure β(r) = residual exponent from oracle UP.
"""

import random
import math
import subprocess
import os
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


def solve_minisat(n, clauses, timeout=60):
    filename = "/tmp/residual_test.cnf"
    outfile = filename + ".out"
    m = len(clauses)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for clause in clauses:
            lits = [str((v+1)*s) for v,s in clause]
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


def compute_temperature(d, p=4/7, n_samples=100000):
    random.seed(42)
    total = 0.0
    for _ in range(n_samples):
        votes = sum(1 for _ in range(int(round(d))) if random.random() < p)
        margin = abs(2*votes/d - 1)
        total += margin
    return 1.0 - total / n_samples


def measure_residual_exponent(ratio, n_values, n_inst_per_n=15):
    """Measure oracle UP residual at each n, fit power law."""
    data = []

    for n in n_values:
        remaining_counts = []
        noise_counts = []

        for seed in range(n_inst_per_n * 5):
            clauses = random_3sat(n, int(ratio * n), seed=seed+85000000)
            sol = solve_minisat(n, clauses, timeout=30)
            if sol is None: continue

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
            signal = [v for v in range(n) if abs(tensions[v]) > 0.1]
            noise_counts.append(n - len(signal))

            fixed = {v: sol[v] for v in signal}
            fixed_after, cascade, conflict = unit_propagate(clauses, n, fixed)
            if conflict: continue

            remaining = n - len(fixed_after)
            remaining_counts.append(remaining)

            if len(remaining_counts) >= n_inst_per_n:
                break

        if remaining_counts:
            avg_rem = sum(remaining_counts) / len(remaining_counts)
            avg_noise = sum(noise_counts) / len(noise_counts)
            data.append((n, avg_rem, avg_noise, len(remaining_counts)))

    # Fit power law: remaining = c * n^beta
    valid = [(n, r) for n, r, _, _ in data if r > 0.05 and n >= 30]
    beta = None
    if len(valid) >= 3:
        log_n = [math.log(n) for n, r in valid]
        log_r = [math.log(max(r, 0.01)) for n, r in valid]
        m = len(valid)
        mx = sum(log_n)/m; my = sum(log_r)/m
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_r[i]-my) for i in range(m))
        beta = sxy/sxx if sxx > 0 else 0

    return data, beta


if __name__ == "__main__":
    print("=" * 75)
    print("RESIDUAL EXPONENT β(r) vs DPLL EXPONENT α(r)")
    print("=" * 75)

    ratios = [3.0, 3.5, 3.86, 4.0, 4.27]
    n_values = [30, 50, 75, 100, 150, 200, 300]

    # Known DPLL exponents from bit_derive_k_scaling.py
    known_alpha = {3.0: 0.22, 3.5: 0.35, 3.86: 0.48, 4.0: 0.60, 4.27: 0.76}

    results = {}

    for ratio in ratios:
        d = 3 * ratio
        T = compute_temperature(d)
        print(f"\n--- Ratio r={ratio}, T={T:.3f} ---")

        data, beta = measure_residual_exponent(ratio, n_values)

        print(f"  {'n':>5} | {'remain':>7} | {'noise':>5} | {'inst':>4}")
        print("  " + "-" * 35)
        for n, rem, noise, inst in data:
            print(f"  {n:>5} | {rem:>7.1f} | {noise:>5.1f} | {inst:>4}")

        if beta is not None:
            alpha = known_alpha.get(ratio, None)
            results[ratio] = (alpha, beta, T)
            print(f"\n  β = {beta:.3f} (residual exponent)")
            if alpha:
                print(f"  α = {alpha:.3f} (DPLL exponent)")
                print(f"  β - α = {beta - alpha:.3f} (DPLL intelligence)")
                print(f"  T = {T:.3f} (temperature)")

    # Summary table
    print("\n" + "=" * 75)
    print("SUMMARY TABLE: α(r), β(r), T(r)")
    print("=" * 75)
    print(f"\n  {'ratio':>6} | {'α(DPLL)':>7} | {'β(UP)':>7} | {'T':>6} | "
          f"{'β-α':>5} | {'α/T':>5} | {'β/T':>5}")
    print("  " + "-" * 55)

    for ratio in sorted(results.keys()):
        alpha, beta, T = results[ratio]
        if alpha:
            print(f"  {ratio:>6.2f} | {alpha:>7.3f} | {beta:>7.3f} | {T:>6.3f} | "
                  f"{beta-alpha:>+5.3f} | {alpha/T:>5.3f} | {beta/T:>5.3f}")

    print("""
    INTERPRETATION:
    ─────────────
    If β(r) tracks α(r) + constant → the mechanism is:
      1. Signal/noise split at threshold T
      2. UP cascade leaves n^β residual clusters
      3. DPLL searches clusters with intelligence factor δ
      4. k = c × n^(β-δ) = c × n^α

    If β(r) ≈ T(r) → temperature directly controls residual
    If β(r) ≠ T(r) but β(r) tracks α(r) → mechanism is correct
      but the temperature connection is coincidental at threshold
    """)
