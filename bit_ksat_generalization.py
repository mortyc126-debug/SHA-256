"""
k-SAT GENERALIZATION: Does α = T hold for k > 3?

PREDICTION: At k-SAT threshold, DPLL scaling exponent α(k) = T(k)

Known thresholds:
  k=3: r_c ≈ 4.267
  k=4: r_c ≈ 9.931
  k=5: r_c ≈ 21.117

Signal per clause:
  ε(k) = 1 / (2(2^k - 1))
  k=3: ε = 1/14 ≈ 0.0714
  k=4: ε = 1/30 ≈ 0.0333
  k=5: ε = 1/62 ≈ 0.0161

Temperature at threshold:
  T(k) = 1 - E[|2·Bin(d, p_k)/d - 1|]
  p_k = 2^(k-1) / (2^k - 1)

EXPERIMENT: Run MiniSat on k-SAT instances at threshold, measure α(k).
"""

import random
import math
import subprocess
import os


# ============================================================
# k-SAT generation
# ============================================================

def random_ksat(n_vars, n_clauses, k, seed=None):
    """Generate random k-SAT instance."""
    if seed is not None:
        random.seed(seed)
    clauses = []
    for _ in range(n_clauses):
        vs = random.sample(range(n_vars), k)
        signs = [random.choice([1, -1]) for _ in range(k)]
        clauses.append(list(zip(vs, signs)))
    return clauses


def generate_dimacs_ksat(n, ratio, k, seed, filename):
    """Generate DIMACS file for k-SAT."""
    random.seed(seed)
    m = int(ratio * n)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for _ in range(m):
            vs = random.sample(range(1, n+1), k)
            signs = [random.choice([-1, 1]) for _ in range(k)]
            lits = [s * v for s, v in zip(signs, vs)]
            f.write(" ".join(str(l) for l in lits) + " 0\n")


def run_minisat(filename, timeout_sec=120):
    """Run MiniSat and return (solved, decisions, propagations)."""
    outfile = filename + ".out"
    try:
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout_sec
        )
        output = result.stdout + result.stderr
        decisions = 0; propagations = 0; solved = False

        for line in output.split('\n'):
            s = line.strip()
            if s.startswith('decisions'):
                after = s.split(':', 1)[1].strip().split()
                if after:
                    try: decisions = int(after[0])
                    except: pass
            elif s.startswith('propagations'):
                after = s.split(':', 1)[1].strip().split()
                if after:
                    try: propagations = int(after[0])
                    except: pass

        if os.path.exists(outfile):
            with open(outfile) as f:
                r = f.readline().strip()
                if r == "SAT": solved = True
                elif r == "UNSAT": solved = None

        return solved, decisions, propagations

    except subprocess.TimeoutExpired:
        return False, 0, 0
    finally:
        if os.path.exists(outfile):
            if os.path.exists(outfile): os.remove(outfile)


# ============================================================
# Temperature computation
# ============================================================

def compute_temperature(k, ratio, n_samples=200000):
    """Compute T(k) = 1 - E[|2·Bin(d, p_k)/d - 1|]"""
    d = k * ratio  # average clause appearances per variable
    p_k = (2**(k-1)) / (2**k - 1)  # P(clause vote is correct)
    d_int = int(round(d))

    random.seed(42)
    total_margin = 0.0
    for _ in range(n_samples):
        votes = sum(1 for _ in range(d_int) if random.random() < p_k)
        margin = abs(2*votes/d_int - 1) if d_int > 0 else 0
        total_margin += margin
    T = 1.0 - total_margin / n_samples
    return T, d, p_k


def compute_epsilon(k):
    """ε(k) = 1 / (2(2^k - 1))"""
    return 1.0 / (2 * (2**k - 1))


# ============================================================
# 1. Temperature predictions for each k
# ============================================================

def temperature_predictions():
    print("=" * 70)
    print("1. TEMPERATURE PREDICTIONS FOR k-SAT")
    print("=" * 70)

    thresholds = {
        3: 4.267,
        4: 9.931,
        5: 21.117,
        6: 43.37,
        7: 87.79,
    }

    print(f"\n  {'k':>3} | {'r_c':>7} | {'ε(k)':>8} | {'p_k':>6} | "
          f"{'d':>5} | {'T(k)':>6} | {'predicted α':>10}")
    print("  " + "-" * 60)

    predictions = {}
    for k in sorted(thresholds.keys()):
        r_c = thresholds[k]
        eps = compute_epsilon(k)
        T, d, p_k = compute_temperature(k, r_c)
        predictions[k] = (r_c, T)

        print(f"  {k:>3} | {r_c:>7.3f} | {eps:>8.4f} | {p_k:>6.4f} | "
              f"{d:>5.1f} | {T:>6.3f} | {T:>10.3f}")

    print(f"\n  PREDICTION: As k increases, T → 1 (all noise)")
    print(f"  → α(k) → 1 → search approaches 2^n for large k")

    return predictions


# ============================================================
# 2. MiniSat scaling test for k=3,4,5
# ============================================================

def ksat_scaling_test():
    print("\n" + "=" * 70)
    print("2. MiniSat SCALING TEST: k=3, k=4, k=5")
    print("=" * 70)

    dimacs = "/tmp/ksat_test.cnf"

    configs = [
        (3, 4.267, [20, 30, 50, 75, 100, 150, 200, 300]),
        (4, 9.931, [20, 30, 50, 75, 100, 150, 200]),
        (5, 21.117, [20, 30, 50, 75, 100]),
    ]

    all_results = {}

    for k, r_c, n_values in configs:
        T, d, p_k = compute_temperature(k, r_c)
        print(f"\n  --- k={k}, r_c={r_c:.3f}, T={T:.3f} ---")

        data_points = []

        print(f"  {'n':>5} | {'SAT':>5} | {'avg dec':>10} | {'k':>6} | "
              f"{'k/n^T':>7} | {'k/n^.75':>7}")
        print("  " + "-" * 55)

        for n in n_values:
            n_inst = 20 if n <= 200 else 10
            timeout = 60 if n <= 100 else (180 if n <= 300 else 300)

            solved_dec = []

            for seed in range(n_inst * 3):
                generate_dimacs_ksat(n, r_c, k, seed + 40000000 + k*1000000,
                                    dimacs)
                solved, decisions, _ = run_minisat(dimacs, timeout)

                if solved == True and decisions > 0:
                    solved_dec.append(decisions)

                if len(solved_dec) >= n_inst:
                    break

            if solved_dec:
                avg_d = sum(solved_dec) / len(solved_dec)
                eff_k = math.log2(max(avg_d, 1))
                data_points.append((n, eff_k))

                print(f"  {n:>5} | {len(solved_dec):>2}/{n_inst:>2} | "
                      f"{avg_d:>10.0f} | {eff_k:>6.1f} | "
                      f"{eff_k/n**T:>7.3f} | {eff_k/n**0.75:>7.3f}")
            else:
                print(f"  {n:>5} |  0/{n_inst:>2} | {'timeout':>10}")

        # Fit power law
        valid = [(n, ek) for n, ek in data_points if n >= 30 and ek > 1]
        if len(valid) >= 3:
            log_n = [math.log(n) for n, ek in valid]
            log_k = [math.log(ek) for n, ek in valid]
            m = len(valid)
            mx = sum(log_n)/m; my = sum(log_k)/m
            sxx = sum((x-mx)**2 for x in log_n)
            sxy = sum((log_n[i]-mx)*(log_k[i]-my) for i in range(m))
            alpha = sxy/sxx if sxx > 0 else 0
            all_results[k] = (alpha, T)
            print(f"\n  FIT: α = {alpha:.3f}, T = {T:.3f}, α/T = {alpha/T:.3f}")
        elif len(valid) >= 2:
            # Two-point estimate
            n1, k1 = valid[0]; n2, k2 = valid[-1]
            alpha = (math.log(k2) - math.log(k1)) / (math.log(n2) - math.log(n1))
            all_results[k] = (alpha, T)
            print(f"\n  TWO-POINT: α ≈ {alpha:.3f}, T = {T:.3f}")

    if os.path.exists(dimacs): os.remove(dimacs)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: α(k) vs T(k) across k-SAT")
    print("=" * 70)
    print(f"\n  {'k':>3} | {'α measured':>10} | {'T predicted':>10} | {'α/T':>6} | {'match?':>6}")
    print("  " + "-" * 50)

    for k in sorted(all_results.keys()):
        alpha, T = all_results[k]
        match = "✓" if abs(alpha/T - 1) < 0.15 else "✗"
        print(f"  {k:>3} | {alpha:>10.3f} | {T:>10.3f} | {alpha/T:>6.3f} | {match:>6}")

    return all_results


# ============================================================
# 3. UP residual for k=4
# ============================================================

def ksat_up_residual():
    print("\n" + "=" * 70)
    print("3. UP RESIDUAL for k=4 (does β mechanism generalize?)")
    print("=" * 70)

    k = 4
    r_c = 9.931
    T, d, p_k = compute_temperature(k, r_c)

    print(f"  k={k}, r_c={r_c}, T={T:.3f}")
    print(f"  ε = {compute_epsilon(k):.4f}, p_k = {p_k:.4f}")

    def bit_tension_ksat(clauses, n, var, fixed=None):
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

    def solve_minisat_ksat(n, clauses, timeout=60):
        filename = "/tmp/ksat_up_test.cnf"
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

    # Measure UP residual at different n
    print(f"\n  {'n':>5} | {'signal':>6} | {'noise':>5} | {'remain':>6} | "
          f"{'rem/n':>6}")
    print("  " + "-" * 45)

    all_data = []

    for n in [30, 50, 75, 100, 150]:
        remaining_counts = []
        signal_counts = []

        for seed in range(60):
            clauses = random_ksat(n, int(r_c * n), k, seed=seed+50000000)
            sol = solve_minisat_ksat(n, clauses, timeout=30)
            if sol is None: continue

            tensions = {v: bit_tension_ksat(clauses, n, v) for v in range(n)}
            signal = [v for v in range(n) if abs(tensions[v]) > 0.05]
            signal_counts.append(len(signal))

            fixed = {v: sol[v] for v in signal}
            fixed_after, cascade, conflict = unit_propagate(clauses, n, fixed)
            if conflict: continue

            remaining = n - len(fixed_after)
            remaining_counts.append(remaining)

            if len(remaining_counts) >= 10:
                break

        if remaining_counts:
            avg_sig = sum(signal_counts) / len(signal_counts)
            avg_rem = sum(remaining_counts) / len(remaining_counts)
            all_data.append((n, avg_rem))

            print(f"  {n:>5} | {avg_sig:>6.1f} | {n-avg_sig:>5.1f} | "
                  f"{avg_rem:>6.1f} | {avg_rem/n:>6.3f}")

    # Fit
    valid = [(n, r) for n, r in all_data if r > 0.05 and n >= 30]
    if len(valid) >= 3:
        log_n = [math.log(n) for n, r in valid]
        log_r = [math.log(max(r, 0.01)) for n, r in valid]
        m = len(valid)
        mx = sum(log_n)/m; my = sum(log_r)/m
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_r[i]-my) for i in range(m))
        beta = sxy/sxx if sxx > 0 else 0
        print(f"\n  k=4 UP residual: β = {beta:.3f} (T = {T:.3f})")


if __name__ == "__main__":
    predictions = temperature_predictions()
    results = ksat_scaling_test()
    ksat_up_residual()

    # Final verdict
    print("\n" + "=" * 70)
    print("FINAL VERDICT: Does α = T generalize to k-SAT?")
    print("=" * 70)
