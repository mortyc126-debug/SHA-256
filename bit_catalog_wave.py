"""
Bit Properties Catalog — Block VIII: Wave Properties
What happens when we iteratively update bit pressures?
Do bits oscillate? Stabilize? Resonate?
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            val = assignment[var]
            if (sign == 1 and val == 1) or (sign == -1 and val == 0):
                sat += 1
                break
    return sat


def soft_pressure(clauses, n, beliefs):
    """
    Given current "beliefs" (soft values in [0,1] for each bit),
    compute new pressure for each bit.

    This is like belief propagation but simplified:
    For each clause, estimate probability it's satisfied
    given current beliefs, then update beliefs.
    """
    new_beliefs = [0.0] * n

    for var in range(n):
        push_toward_1 = 0.0
        push_toward_0 = 0.0

        for clause in clauses:
            # Is var in this clause?
            var_sign = None
            other_literals = []
            for v, s in clause:
                if v == var:
                    var_sign = s
                else:
                    other_literals.append((v, s))

            if var_sign is None:
                continue

            # Probability that OTHER literals satisfy this clause
            prob_others_satisfy = 1.0
            for v, s in other_literals:
                if s == 1:
                    prob_lit_true = beliefs[v]
                else:
                    prob_lit_true = 1.0 - beliefs[v]
                prob_others_satisfy *= (1.0 - prob_lit_true)
            # prob_others_satisfy = prob that NO other literal satisfies

            # This is how much this clause "needs" our variable
            need = prob_others_satisfy

            if var_sign == 1:
                push_toward_1 += need
            else:
                push_toward_0 += need

        total = push_toward_1 + push_toward_0
        if total > 0:
            new_beliefs[var] = push_toward_1 / total
        else:
            new_beliefs[var] = 0.5

    return new_beliefs


def simulate_wave(clauses, n, n_steps=50, damping=0.3):
    """
    Iteratively update beliefs and record the trajectory.
    damping: mix old and new beliefs (0=fully new, 1=fully old)

    Returns: trajectory[step][var] = belief value
    """
    # Start with uniform beliefs
    beliefs = [0.5] * n
    trajectory = [list(beliefs)]

    for step in range(n_steps):
        new_beliefs = soft_pressure(clauses, n, beliefs)
        # Apply damping
        beliefs = [damping * old + (1 - damping) * new
                   for old, new in zip(beliefs, new_beliefs)]
        # Clamp to [0.01, 0.99] to avoid log(0)
        beliefs = [max(0.01, min(0.99, b)) for b in beliefs]
        trajectory.append(list(beliefs))

    return trajectory


# ============================================================
# 31. OSCILLATION FREQUENCY
# ============================================================
def oscillation_analysis(trajectory, var):
    """
    Analyze the trajectory of one bit's belief.
    Count zero-crossings of (belief - 0.5) to estimate frequency.
    Also measure amplitude and whether it converges.
    """
    values = [t[var] for t in trajectory]
    centered = [v - 0.5 for v in values]

    # Zero crossings
    crossings = 0
    for i in range(1, len(centered)):
        if centered[i-1] * centered[i] < 0:
            crossings += 1

    frequency = crossings / (len(values) - 1)

    # Amplitude: std of values
    mean = sum(values) / len(values)
    amplitude = math.sqrt(sum((v - mean)**2 for v in values) / len(values))

    # Convergence: compare first half vs second half variance
    half = len(values) // 2
    first_var = sum((v - sum(values[:half])/half)**2 for v in values[:half]) / half
    second_var = sum((v - sum(values[half:])/half)**2 for v in values[half:]) / half

    if first_var > 0:
        damping_ratio = second_var / first_var
    else:
        damping_ratio = 0.0

    # Final value
    final = values[-1]

    return {
        'frequency': frequency,
        'amplitude': amplitude,
        'damping_ratio': damping_ratio,  # <1 = converging, >1 = diverging
        'final_belief': final,
        'trajectory': values,
    }


# ============================================================
# 33. RESONANCE — do pairs of bits oscillate in sync?
# ============================================================
def resonance_analysis(trajectory, n):
    """
    Compute correlation of belief trajectories between pairs.
    High positive correlation = in-phase resonance.
    High negative correlation = anti-phase resonance.
    """
    resonances = []

    for i in range(n):
        traj_i = [t[i] for t in trajectory]
        mean_i = sum(traj_i) / len(traj_i)

        for j in range(i + 1, n):
            traj_j = [t[j] for t in trajectory]
            mean_j = sum(traj_j) / len(traj_j)

            cov = sum((traj_i[k] - mean_i) * (traj_j[k] - mean_j)
                       for k in range(len(traj_i))) / len(traj_i)
            std_i = math.sqrt(sum((v - mean_i)**2 for v in traj_i) / len(traj_i))
            std_j = math.sqrt(sum((v - mean_j)**2 for v in traj_j) / len(traj_j))

            if std_i > 0.001 and std_j > 0.001:
                corr = cov / (std_i * std_j)
            else:
                corr = 0.0

            resonances.append((i, j, corr))

    return resonances


# ============================================================
# MEASUREMENT
# ============================================================

def measure_waves(clauses, n, solutions):
    print(f"\n--- Wave Properties (iterative belief propagation) ---")

    trajectory = simulate_wave(clauses, n, n_steps=50, damping=0.3)

    print(f"\n{'var':>5} | {'freq':>6} | {'ampl':>6} | {'damp_r':>6} | "
          f"{'final':>6} | {'correct?':>8} | trajectory sketch")
    print("-" * 90)

    # Ground truth
    if solutions:
        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    else:
        prob_1 = [0.5] * n

    correct = 0
    for var in range(n):
        osc = oscillation_analysis(trajectory, var)
        predicted = 1 if osc['final_belief'] > 0.5 else 0
        actual = 1 if prob_1[var] > 0.5 else 0
        is_correct = predicted == actual
        if is_correct:
            correct += 1

        # Mini ASCII trajectory
        traj = osc['trajectory']
        sketch = ""
        for i in range(0, len(traj), 5):
            v = traj[i]
            if v > 0.6:
                sketch += "▆"
            elif v > 0.5:
                sketch += "▄"
            elif v > 0.4:
                sketch += "▂"
            else:
                sketch += "_"

        print(f"  x{var:>2} | {osc['frequency']:>6.3f} | {osc['amplitude']:>6.3f} | "
              f"{osc['damping_ratio']:>6.3f} | {osc['final_belief']:>6.3f} | "
              f"{'yes' if is_correct else 'NO':>8} | {sketch}")

    print(f"\n  Wave prediction accuracy: {correct}/{n}")

    # Resonance
    resonances = resonance_analysis(trajectory, n)
    resonances.sort(key=lambda x: -abs(x[2]))

    print(f"\n--- Top Resonant Pairs ---")
    print(f"{'pair':>8} | {'resonance':>9} | {'type':>10} | {'sol_corr':>8}")
    print("-" * 45)

    if solutions and len(solutions) >= 2:
        for i, j, corr in resonances[:10]:
            # Solution correlation for comparison
            vals_i = [s[i] for s in solutions]
            vals_j = [s[j] for s in solutions]
            mi = sum(vals_i) / len(vals_i)
            mj = sum(vals_j) / len(vals_j)
            si = math.sqrt(sum((v-mi)**2 for v in vals_i)/len(vals_i))
            sj = math.sqrt(sum((v-mj)**2 for v in vals_j)/len(vals_j))
            if si > 0 and sj > 0:
                sc = sum((vals_i[k]-mi)*(vals_j[k]-mj) for k in range(len(solutions)))
                sc /= len(solutions) * si * sj
            else:
                sc = 0
            rtype = "in-phase" if corr > 0.3 else ("anti-phase" if corr < -0.3 else "weak")
            print(f"  x{i}-x{j} | {corr:>+9.3f} | {rtype:>10} | {sc:>+8.3f}")


# ============================================================
# BONUS: Does wave converge to a solution?
# ============================================================

def wave_solver(clauses, n, n_steps=100, damping=0.3):
    """
    Run belief propagation and round final beliefs to 0/1.
    Does this find a solution?
    """
    trajectory = simulate_wave(clauses, n, n_steps=n_steps, damping=damping)
    final = trajectory[-1]

    assignment = [1 if b > 0.5 else 0 for b in final]
    sat = evaluate(clauses, assignment)
    return assignment, sat == len(clauses), final


def wave_solver_test(n=12, n_trials=200):
    print(f"\n--- Wave Solver Test ---")
    print(f"Can belief propagation alone find SAT solutions?")

    for ratio in [2.0, 3.0, 3.5, 4.0, 4.27]:
        successes = 0
        total_sat = 0

        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed + 2000)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue
            total_sat += 1

            _, solved, _ = wave_solver(clauses, n)
            if solved:
                successes += 1

        if total_sat > 0:
            print(f"  ratio={ratio:.2f}: {successes}/{total_sat} solved "
                  f"({successes/total_sat*100:.1f}%)")


if __name__ == "__main__":
    random.seed(42)
    print("=" * 90)
    print("BLOCK VIII: Wave Properties")
    print("=" * 90)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (n=12, ratio={ratio}, {len(solutions)} solutions)")
        measure_waves(clauses, 12, solutions)

    wave_solver_test()
