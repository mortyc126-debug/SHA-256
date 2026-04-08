"""
IS THE EXPONENT EXACTLY 3/4?

Measured: α ≈ 0.756 (MiniSat, n=20-300)
Question: is α = 3/4 = 0.750 exactly?

Strategy: high-precision measurement with many instances at each n.
Use 100+ instances per n for good statistics.
"""

import random
import math
import subprocess
import os


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
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout_sec
        )
        output = result.stdout + result.stderr
        decisions = 0

        for line in output.split('\n'):
            s = line.strip()
            if s.startswith('decisions'):
                after = s.split(':', 1)[1].strip().split()
                if after:
                    try: decisions = int(after[0])
                    except: pass

        if os.path.exists(outfile):
            with open(outfile) as f:
                r = f.readline().strip()
                if r == "SAT": return True, decisions
                elif r == "UNSAT": return None, decisions

        return False, 0

    except subprocess.TimeoutExpired:
        return False, 0
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)


def precision_measurement():
    print("=" * 70)
    print("HIGH-PRECISION α MEASUREMENT")
    print("=" * 70)

    dimacs = "/tmp/precision_test.cnf"

    # Many instances at each n for good statistics
    configs = [
        (30,  100, 30),
        (50,  100, 30),
        (75,   80, 60),
        (100,  80, 60),
        (150,  60, 90),
        (200,  50, 120),
        (300,  40, 180),
        (400,  30, 240),
        (500,  20, 300),
    ]

    all_data = []

    print(f"\n  {'n':>5} | {'SAT':>6} | {'avg dec':>10} | {'median':>10} | "
          f"{'k':>6} | {'k/n^.75':>8} | {'k/n^.76':>8} | {'k/n^.74':>8}")
    print("  " + "-" * 80)

    for n, max_inst, timeout in configs:
        solved_dec = []

        for seed in range(max_inst * 5):
            generate_dimacs(n, 4.267, seed + 55000000, dimacs)
            solved, decisions = run_minisat(dimacs, timeout)

            if solved == True and decisions > 0:
                solved_dec.append(decisions)

            if len(solved_dec) >= max_inst:
                break

        if solved_dec:
            avg_d = sum(solved_dec) / len(solved_dec)
            sorted_d = sorted(solved_dec)
            median_d = sorted_d[len(sorted_d)//2]

            k_avg = math.log2(max(avg_d, 1))
            k_med = math.log2(max(median_d, 1))

            all_data.append((n, k_avg, k_med, len(solved_dec)))

            print(f"  {n:>5} | {len(solved_dec):>3}/{max_inst:>3} | "
                  f"{avg_d:>10.0f} | {median_d:>10.0f} | "
                  f"{k_avg:>6.1f} | {k_avg/n**0.75:>8.3f} | "
                  f"{k_avg/n**0.76:>8.3f} | {k_avg/n**0.74:>8.3f}")
        else:
            print(f"  {n:>5} |   0/{max_inst:>3} | {'timeout':>10}")

    if os.path.exists(dimacs): os.remove(dimacs)

    # Fit exponent precisely
    valid = [(n, k) for n, k, _, _ in all_data if n >= 50]
    if len(valid) >= 4:
        log_n = [math.log(n) for n, k in valid]
        log_k = [math.log(k) for n, k in valid]
        m = len(valid)
        mx = sum(log_n)/m; my = sum(log_k)/m
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_k[i]-my) for i in range(m))
        alpha = sxy/sxx if sxx > 0 else 0
        c = math.exp(my - alpha * mx)

        # Residuals
        print(f"\n  BEST FIT: k = {c:.4f} × n^{alpha:.4f}")
        print(f"  3/4 hypothesis: α = 0.7500")
        print(f"  Measured:       α = {alpha:.4f}")
        print(f"  Difference:     {alpha - 0.75:+.4f}")

        # Test specific exponents
        for test_exp, label in [(0.74, "0.74"), (0.75, "3/4"),
                                (0.76, "0.76"), (0.77, "0.77")]:
            residuals = [(k - c * n**test_exp)**2 for n, k in valid]
            rmse = math.sqrt(sum(residuals) / len(residuals))
            ratios = [k / n**test_exp for n, k in valid]
            cv = (max(ratios) - min(ratios)) / (sum(ratios)/len(ratios))
            print(f"    α={test_exp} ({label:>4}): RMSE={rmse:.4f}, "
                  f"coefficient variation={cv:.4f}")

    # Also fit using median (more robust to outliers)
    valid_med = [(n, km) for n, _, km, _ in all_data if n >= 50]
    if len(valid_med) >= 4:
        log_n = [math.log(n) for n, k in valid_med]
        log_k = [math.log(k) for n, k in valid_med]
        m = len(valid_med)
        mx = sum(log_n)/m; my = sum(log_k)/m
        sxx = sum((x-mx)**2 for x in log_n)
        sxy = sum((log_n[i]-mx)*(log_k[i]-my) for i in range(m))
        alpha_med = sxy/sxx if sxx > 0 else 0
        print(f"\n  MEDIAN FIT:     α = {alpha_med:.4f}")


if __name__ == "__main__":
    precision_measurement()
