"""
K-SCALING CROSSOVER: Where does n^0.75 emerge?

At small n (10-20): DPLL barely backtracks, k ≈ log2(n).
At large n (100+): k ≈ 0.28 × n^0.75 (MiniSat confirmed).

QUESTION: Where is the crossover? What drives it?

PREDICTION: crossover at n ≈ 50, where log2(n) ≈ 0.28 × n^0.75.
Below: finite-size regime (too easy for backtracks).
Above: asymptotic regime (backtracks dominate).
"""

import random
import subprocess
import time
import os
import math


def generate_dimacs(n, ratio, seed, filename):
    random.seed(seed)
    m = int(ratio * n)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for _ in range(m):
            vs = random.sample(range(1, n+1), 3)
            signs = [random.choice([-1, 1]) for _ in range(3)]
            lits = [s * v for s, v in zip(signs, vs)]
            f.write(f"{lits[0]} {lits[1]} {lits[2]} 0\n")


def run_minisat(filename, timeout_sec=120):
    outfile = filename + ".out"
    try:
        t0 = time.time()
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout_sec
        )
        t1 = time.time()
        elapsed = t1 - t0

        output = result.stderr + result.stdout
        decisions = 0; conflicts = 0; propagations = 0; solved = False

        def parse_stat(line):
            """Parse 'statname : 123 ...' format."""
            if ':' in line:
                after_colon = line.split(':',1)[1].strip().split()
                if after_colon:
                    try: return int(after_colon[0])
                    except: pass
            return 0

        for line in output.split('\n'):
            stripped = line.strip()
            if stripped.startswith('decisions'):
                decisions = parse_stat(stripped)
            elif stripped.startswith('conflicts') and 'conflict literals' not in stripped:
                conflicts = parse_stat(stripped)
            elif stripped.startswith('propagations'):
                propagations = parse_stat(stripped)
            if 'SATISFIABLE' in line and 'UN' not in line:
                solved = True
            if 'UNSATISFIABLE' in line:
                solved = None

        if os.path.exists(outfile):
            with open(outfile) as f:
                first_line = f.readline().strip()
                if first_line == "SAT": solved = True
                elif first_line == "UNSAT": solved = None

        return solved, elapsed, decisions, conflicts, propagations

    except subprocess.TimeoutExpired:
        return False, timeout_sec, 0, 0, 0
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)


if __name__ == "__main__":
    print("=" * 85)
    print("K-SCALING CROSSOVER: MiniSat at n=20 to 2000, ratio=4.27")
    print("=" * 85)

    dimacs_file = "/tmp/test_crossover.cnf"

    print(f"\n{'n':>6} | {'SAT':>5} | {'avg time':>9} | {'avg dec':>10} | "
          f"{'k':>6} | {'k/n^.75':>8} | {'k/logn':>7} | {'prop/dec':>8}")
    print("-" * 85)

    # Dense sampling from n=20 to n=2000
    n_values = [20, 30, 40, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000]

    all_data = []  # (n, k) pairs for final fit

    for n in n_values:
        n_inst = 20 if n <= 500 else (10 if n <= 1000 else 5)
        timeout = 60 if n <= 500 else (120 if n <= 1000 else 300)

        solved_count = 0; total = 0
        solved_dec = []; solved_times = []; solved_prop = []

        for seed in range(n_inst):
            generate_dimacs(n, 4.27, seed + 70000000, dimacs_file)
            total += 1

            solved, elapsed, decisions, conflicts, propagations = \
                run_minisat(dimacs_file, timeout)

            if solved == True and decisions > 0:
                solved_count += 1
                solved_dec.append(decisions)
                solved_times.append(elapsed)
                solved_prop.append(propagations)
            elif solved == None:
                pass  # UNSAT

        if solved_dec:
            avg_dec = sum(solved_dec) / len(solved_dec)
            avg_t = sum(solved_times) / len(solved_times)
            avg_prop = sum(solved_prop) / len(solved_prop)
            k = math.log2(max(avg_dec, 1))
            k_n75 = k / n**0.75
            k_logn = k / math.log2(n)
            prop_dec = avg_prop / avg_dec if avg_dec > 0 else 0

            all_data.append((n, k))

            print(f"{n:>6} | {solved_count:>2}/{total:>2} | {avg_t:>8.3f}s | "
                  f"{avg_dec:>10.0f} | {k:>6.1f} | {k_n75:>8.3f} | "
                  f"{k_logn:>7.3f} | {prop_dec:>8.1f}")
        else:
            print(f"{n:>6} | {solved_count:>2}/{total:>2} | {'timeout':>9} | "
                  f"{'N/A':>10} | {'N/A':>6} | {'N/A':>8} | {'N/A':>7} | {'N/A':>8}")

    # Fit power law to large-n data (n >= 50)
    large = [(n, k) for n, k in all_data if n >= 50]
    if len(large) >= 3:
        log_n = [math.log(n) for n, k in large]
        log_k = [math.log(k) for n, k in large]
        n_pts = len(log_n)
        mx = sum(log_n)/n_pts; my = sum(log_k)/n_pts
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_k[i]-my) for i in range(n_pts))
        alpha = sxy/sxx if sxx > 0 else 0
        c = math.exp(my - alpha * mx)

        print(f"\n  POWER LAW FIT (n ≥ 50):")
        print(f"    k ≈ {c:.3f} × n^{alpha:.4f}")
        print(f"    Exponent α = {alpha:.4f}")
        print(f"    Temperature T = 0.7467")
        print(f"    |α - T| = {abs(alpha - 0.7467):.4f}")
        print(f"    α / T = {alpha / 0.7467:.4f}")

    # Also fit all data
    if len(all_data) >= 3:
        log_n = [math.log(n) for n, k in all_data]
        log_k = [math.log(k) for n, k in all_data]
        n_pts = len(log_n)
        mx = sum(log_n)/n_pts; my = sum(log_k)/n_pts
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_k[i]-my) for i in range(n_pts))
        alpha_all = sxy/sxx if sxx > 0 else 0
        c_all = math.exp(my - alpha_all * mx)

        print(f"\n  POWER LAW FIT (all data):")
        print(f"    k ≈ {c_all:.3f} × n^{alpha_all:.4f}")

    # Cleanup
    if os.path.exists(dimacs_file):
        os.remove(dimacs_file)
