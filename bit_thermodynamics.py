"""
Bit Thermodynamics — treating a bit field as a physical system.

What is "temperature" of a bit field?
What is "pressure"?
How does the system cool?
Is there a phase transition?
"""

import random
import math
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


def energy(clauses, assignment):
    """Energy = number of VIOLATED clauses. Lower is better."""
    return len(clauses) - evaluate(clauses, assignment)


# ============================================================
# TEMPERATURE: measure of disorder / randomness in the system
# ============================================================

def field_temperature(clauses, n, fixed):
    """
    Temperature of bit field given current fixed assignments.

    T = average frustration of unfixed bits.
    High T = bits are confused (hot, disordered).
    Low T = bits know what they want (cold, ordered).

    Also: T relates to how "flat" the energy landscape is
    around the current state.
    """
    frustrations = []
    for var in range(n):
        if var in fixed:
            continue
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
        if total > 0:
            frustrations.append(1.0 - abs(p1 - p0) / total)
        else:
            frustrations.append(0.0)

    if not frustrations:
        return 0.0
    return sum(frustrations) / len(frustrations)


# ============================================================
# PRESSURE: how constrained is the system
# ============================================================

def field_pressure(clauses, n, fixed):
    """
    Pressure = fraction of remaining clauses that are "critical"
    (only one unfixed literal can save them).

    High pressure = system is about to break.
    Low pressure = plenty of slack.
    """
    critical = 0
    active = 0

    for clause in clauses:
        already_sat = False
        free_literals = 0
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
            else:
                free_literals += 1

        if already_sat:
            continue

        active += 1
        if free_literals == 1:
            critical += 1

    return critical / active if active > 0 else 0.0


# ============================================================
# ENTROPY: how many microstates are compatible
# ============================================================

def field_entropy_exact(clauses, n, fixed):
    """
    S = log2(number of valid completions of fixed assignment).
    Exact computation (exponential, only for small remaining bits).
    """
    unfixed = [v for v in range(n) if v not in fixed]
    if len(unfixed) > 20:
        return -1  # too large

    count = 0
    for i in range(2 ** len(unfixed)):
        test = dict(fixed)
        for idx, var in enumerate(unfixed):
            test[var] = (i >> idx) & 1

        assignment = [test.get(v, 0) for v in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            count += 1

    return math.log2(count) if count > 0 else float('-inf')


# ============================================================
# COOLING CURVE: what happens as we fix bits one by one
# ============================================================

def cooling_curve(clauses, n, strategy="max_confidence"):
    """
    Fix bits one at a time and measure T, P, S at each step.
    This is the "cooling curve" of the bit field.
    """
    fixed = {}
    curve = []

    # Initial state
    T = field_temperature(clauses, n, fixed)
    P = field_pressure(clauses, n, fixed)
    S = field_entropy_exact(clauses, n, fixed)

    curve.append({
        'step': 0, 'var': -1, 'val': -1,
        'T': T, 'P': P, 'S': S,
        'fixed_count': 0,
        'tension_sum': sum(abs(bit_tension(clauses, n, v, fixed))
                          for v in range(n)),
    })

    for step in range(n):
        # Pick next bit to fix
        candidates = []
        for var in range(n):
            if var in fixed:
                continue
            sigma = bit_tension(clauses, n, var, fixed)
            candidates.append((var, sigma))

        if not candidates:
            break

        if strategy == "max_confidence":
            candidates.sort(key=lambda c: -abs(c[1]))
        elif strategy == "random":
            random.shuffle(candidates)
        elif strategy == "min_confidence":
            candidates.sort(key=lambda c: abs(c[1]))

        best_var, best_sigma = candidates[0]
        best_val = 1 if best_sigma >= 0 else 0
        fixed[best_var] = best_val

        T = field_temperature(clauses, n, fixed)
        P = field_pressure(clauses, n, fixed)
        S = field_entropy_exact(clauses, n, fixed)

        curve.append({
            'step': step + 1,
            'var': best_var,
            'val': best_val,
            'T': T,
            'P': P,
            'S': S,
            'fixed_count': len(fixed),
            'tension_sum': sum(abs(bit_tension(clauses, n, v, fixed))
                              for v in range(n) if v not in fixed),
        })

    # Final check
    assignment = [fixed.get(v, 0) for v in range(n)]
    success = evaluate(clauses, assignment) == len(clauses)

    return curve, success


def bit_tension(clauses, n, var, fixed):
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
    if total == 0:
        return 0.0
    return (p1 - p0) / total


# ============================================================
# HEAT CAPACITY: how much does temperature change per fixation
# ============================================================

def heat_capacity(curve):
    """
    C = -dT/dstep: how much temperature drops per fixation.
    High C = system is efficiently cooling.
    Low C = temperature is stuck (frustrated).
    Negative C = system is HEATING UP (bad sign).
    """
    capacities = []
    for i in range(1, len(curve)):
        dT = curve[i]['T'] - curve[i-1]['T']
        capacities.append(-dT)  # negative because cooling = T decreasing
    return capacities


# ============================================================
# EQUATION OF STATE: T-P-S relationship
# ============================================================

def equation_of_state(clauses, n):
    """
    Sample many partial assignments and measure (T, P, S).
    Look for a functional relationship: P = f(T, S)?
    """
    points = []

    for _ in range(200):
        # Random partial assignment (fix random subset)
        k = random.randint(0, n - 1)
        vars_to_fix = random.sample(range(n), k)
        fixed = {v: random.randint(0, 1) for v in vars_to_fix}

        T = field_temperature(clauses, n, fixed)
        P = field_pressure(clauses, n, fixed)
        S = field_entropy_exact(clauses, n, fixed)

        if S > float('-inf'):
            points.append({'T': T, 'P': P, 'S': S, 'k': k})

    return points


# ============================================================
# MAIN EXPERIMENTS
# ============================================================

def print_cooling_curve(curve, success, label):
    print(f"\n## {label} — {'SOLVED' if success else 'FAILED'}")
    print(f"{'step':>4} | {'var':>4} | {'val':>3} | {'T':>6} | {'P':>6} | "
          f"{'S':>7} | {'Σ|σ|':>6} | visual")
    print("-" * 70)

    for c in curve:
        # Temperature bar
        bar_t = "█" * int(c['T'] * 20)
        var_str = f"x{c['var']}" if c['var'] >= 0 else "   "
        val_str = str(c['val']) if c['val'] >= 0 else " "
        s_str = f"{c['S']:.1f}" if c['S'] > float('-inf') else " -∞"

        print(f"{c['step']:>4} | {var_str:>4} | {val_str:>3} | "
              f"{c['T']:>6.3f} | {c['P']:>6.3f} | "
              f"{s_str:>7} | {c['tension_sum']:>6.2f} | {bar_t}")


if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("BIT THERMODYNAMICS")
    print("=" * 70)

    # Experiment 1: Cooling curves
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Cooling curves")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY ratio=2.0"), (4.27, "HARD ratio=4.27")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        curve, success = cooling_curve(clauses, 12)
        print_cooling_curve(curve, success, label)

        caps = heat_capacity(curve)
        avg_cap = sum(caps) / len(caps) if caps else 0
        neg_caps = sum(1 for c in caps if c < 0)
        print(f"\n  Avg heat capacity: {avg_cap:.4f}")
        print(f"  Negative capacity events (heating): {neg_caps}/{len(caps)}")

    # Experiment 2: Compare cooling strategies
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Cooling strategy comparison")
    print("=" * 70)

    for ratio in [2.0, 3.5, 4.27]:
        print(f"\n  ratio={ratio}:")
        for strategy in ["max_confidence", "random", "min_confidence"]:
            successes = 0
            total = 0
            avg_final_T = []

            for seed in range(150):
                clauses = random_3sat(12, int(ratio * 12), seed=seed)
                solutions = find_solutions(clauses, 12)
                if not solutions:
                    continue
                total += 1

                curve, success = cooling_curve(clauses, 12, strategy=strategy)
                if success:
                    successes += 1
                avg_final_T.append(curve[-1]['T'])

            mean_T = sum(avg_final_T) / len(avg_final_T) if avg_final_T else 0
            print(f"    {strategy:>15}: {successes}/{total} "
                  f"({successes/total*100:.0f}%) | final T={mean_T:.4f}")

    # Experiment 3: Equation of state
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Equation of state T-P-S")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        points = equation_of_state(clauses, 12)

        # Bin by temperature and show P, S
        bins = {}
        for p in points:
            t_bin = round(p['T'] * 10) / 10  # round to 0.1
            if t_bin not in bins:
                bins[t_bin] = {'P': [], 'S': []}
            bins[t_bin]['P'].append(p['P'])
            bins[t_bin]['S'].append(p['S'])

        print(f"\n  {label} (ratio={ratio}):")
        print(f"  {'T':>6} | {'avg P':>8} | {'avg S':>8} | {'n':>4}")
        print("  " + "-" * 35)
        for t in sorted(bins.keys()):
            if len(bins[t]['P']) >= 3:
                avg_p = sum(bins[t]['P']) / len(bins[t]['P'])
                avg_s = sum(bins[t]['S']) / len(bins[t]['S'])
                print(f"  {t:>6.1f} | {avg_p:>8.3f} | {avg_s:>8.2f} | "
                      f"{len(bins[t]['P']):>4}")

    # Experiment 4: Does S predict solvability?
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Entropy during crystallization")
    print("Which step kills solutions?")
    print("=" * 70)

    for ratio in [2.0, 4.27]:
        entropy_at_step = {i: [] for i in range(13)}
        for seed in range(50):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            curve, _ = cooling_curve(clauses, 12)
            for c in curve:
                if c['S'] > float('-inf'):
                    entropy_at_step[c['step']].append(c['S'])

        print(f"\n  ratio={ratio}:")
        print(f"  {'step':>6} | {'avg S':>8} | {'min S':>8} | "
              f"{'S=0 count':>9}")
        for step in range(13):
            vals = entropy_at_step[step]
            if vals:
                avg = sum(vals) / len(vals)
                mn = min(vals)
                zeros = sum(1 for v in vals if v <= 0)
                print(f"  {step:>6} | {avg:>8.2f} | {mn:>8.2f} | {zeros:>9}")
