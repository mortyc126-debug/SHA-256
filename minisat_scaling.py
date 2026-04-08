"""
LARGE-N SCALING WITH MINISAT: n = 100 to 30000

Generate random 3-SAT at threshold (4.27), convert to DIMACS,
solve with MiniSat, measure time and decisions.
"""

import random
import subprocess
import time
import os
import math


def generate_dimacs(n, ratio, seed, filename):
    """Generate random 3-SAT in DIMACS format."""
    random.seed(seed)
    m = int(ratio * n)

    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for _ in range(m):
            vars_chosen = random.sample(range(1, n+1), 3)
            signs = [random.choice([-1, 1]) for _ in range(3)]
            lits = [s * v for s, v in zip(signs, vars_chosen)]
            f.write(f"{lits[0]} {lits[1]} {lits[2]} 0\n")


def run_minisat(filename, timeout_sec=300):
    """Run MiniSat, return (solved, time, decisions, conflicts)."""
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

        # Parse MiniSat output
        decisions = 0; conflicts = 0; solved = False
        for line in output.split('\n'):
            if 'decisions' in line.lower():
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == 'decisions':
                        try: decisions = int(parts[i-1])
                        except: pass
            if 'conflicts' in line.lower():
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == 'conflicts':
                        try: conflicts = int(parts[i-1])
                        except: pass
            if 'SATISFIABLE' in line:
                solved = True
            if 'UNSATISFIABLE' in line:
                solved = None  # UNSAT

        # Check result file
        if os.path.exists(outfile):
            with open(outfile) as f:
                first_line = f.readline().strip()
                if first_line == "SAT":
                    solved = True
                elif first_line == "UNSAT":
                    solved = None

        return solved, elapsed, decisions, conflicts

    except subprocess.TimeoutExpired:
        return False, timeout_sec, 0, 0
    finally:
        for f in [outfile]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    print("=" * 75)
    print("MINISAT SCALING: Random 3-SAT at threshold, n = 100 to 30000")
    print("=" * 75)

    print(f"\n{'n':>7} | {'solved':>8} | {'avg time':>10} | {'avg decisions':>13} | "
          f"{'eff k':>7} | {'k/√n':>6}")
    print("-" * 65)

    dimacs_file = "/tmp/test_sat.cnf"

    for n in [100, 200, 500, 1000, 2000, 5000, 10000, 30000]:
        n_inst = 10 if n <= 1000 else (5 if n <= 10000 else 3)
        timeout = 60 if n <= 1000 else (120 if n <= 10000 else 300)

        solved_count = 0; total = 0
        total_time = 0; total_decisions = 0
        solved_times = []; solved_decisions = []

        for seed in range(n_inst):
            generate_dimacs(n, 4.27, seed + 50000000, dimacs_file)
            total += 1

            solved, elapsed, decisions, conflicts = run_minisat(dimacs_file, timeout)

            if solved == True:
                solved_count += 1
                solved_times.append(elapsed)
                solved_decisions.append(decisions)
                total_time += elapsed
                total_decisions += decisions
            elif solved == None:
                pass  # UNSAT — skip
            else:
                total_time += elapsed  # timeout

        if solved_decisions:
            avg_t = sum(solved_times) / len(solved_times)
            avg_d = sum(solved_decisions) / len(solved_decisions)
            eff_k = math.log2(max(avg_d, 1))
            k_sqrtn = eff_k / math.sqrt(n)

            print(f"{n:>7} | {solved_count:>3}/{total:>2} | {avg_t:>8.3f}s | "
                  f"{avg_d:>13.0f} | {eff_k:>7.1f} | {k_sqrtn:>6.2f}")
        else:
            print(f"{n:>7} | {solved_count:>3}/{total:>2} | {'timeout':>10} | "
                  f"{'N/A':>13} | {'N/A':>7} | {'N/A':>6}")

    # Cleanup
    if os.path.exists(dimacs_file):
        os.remove(dimacs_file)
