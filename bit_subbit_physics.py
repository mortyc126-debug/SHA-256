"""
SUB-BIT PHYSICS: What lies beneath the bit?
════════════════════════════════════════════

Five experiments probing the sub-bit world:

1. CLAUSE VOTE ATOMS — the smallest unit of information
2. ENERGY LANDSCAPE — the continuous surface between 0 and 1
3. PARTICLE TRAJECTORIES — paths through continuous space
4. VELOCITY AS HIDDEN VARIABLE — does momentum know the answer?
5. DECISION THRESHOLD — when does a bit "choose"?

From Bit Mechanics theory:
  - A bit is not just 0/1. Before "measurement" it exists in [0,1].
  - Tension σ ∈ [-1,+1] is the sum of clause votes.
  - Each clause vote carries ε = 1/(2(2^k-1)) = 1/14 information.
  - In PhysicsSAT, bits are particles with position AND velocity.
  - The velocity is a HIDDEN VARIABLE — not visible in the solution.
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def compute_tension(clauses, n, var):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                w = 1.0 / len(clause)
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# 1. CLAUSE VOTE ATOMS: The smallest unit of information
# ============================================================

def experiment_clause_votes():
    print("=" * 70)
    print("1. CLAUSE VOTE ATOMS: What is a single vote worth?")
    print("=" * 70)

    print("""
    Theory: each clause contributes ε = 1/14 bits of information
    about each variable it contains.

    Question: Can we MEASURE this? If we add/remove one clause,
    how much does tension accuracy change?
    """)

    random.seed(42)

    for n in [12, 20, 30]:
        vote_values = []  # information gain per clause vote

        for seed in range(100):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+71000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
                sol = solutions[0]
            else:
                continue  # skip n>16 for exact solutions

            m = len(clauses)

            for var in range(min(n, 5)):  # test 5 vars per instance
                # Full tension (all clauses)
                full_tension = compute_tension(clauses, n, var)
                full_correct = (full_tension > 0) == (sol[var] == 1)

                # Remove each clause containing this var, measure impact
                for ci in range(m):
                    has_var = False
                    for v, s in clauses[ci]:
                        if v == var:
                            has_var = True
                            break
                    if not has_var:
                        continue

                    # Tension without this clause
                    reduced = clauses[:ci] + clauses[ci+1:]
                    reduced_tension = compute_tension(reduced, n, var)

                    # Information change
                    delta_t = abs(full_tension) - abs(reduced_tension)
                    vote_values.append(delta_t)

            if len(vote_values) >= 500:
                break

        if vote_values:
            avg_vote = sum(vote_values) / len(vote_values)
            median_vote = sorted(vote_values)[len(vote_values)//2]
            predicted = 1/14  # ε = 1/(2(2^3-1))

            print(f"\n  n={n}: {len(vote_values)} clause votes measured")
            print(f"    Average |Δtension| per vote:  {avg_vote:.4f}")
            print(f"    Median |Δtension| per vote:   {median_vote:.4f}")
            print(f"    Predicted (ε = 1/14):          {predicted:.4f}")
            print(f"    Ratio measured/predicted:       {avg_vote/predicted:.3f}")


# ============================================================
# 2. ENERGY LANDSCAPE: The surface between 0 and 1
# ============================================================

def experiment_energy_landscape():
    print("\n" + "=" * 70)
    print("2. ENERGY LANDSCAPE: What does the surface look like?")
    print("=" * 70)

    print("""
    Fix all vars except one. Sweep that var from 0 to 1.
    Plot the clause satisfaction as function of x ∈ [0,1].
    Is it smooth? Convex? How many local minima?
    """)

    random.seed(42)

    for n in [12, 20]:
        for seed in range(10):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+72000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
                sol = solutions[0]
            else:
                continue

            m = len(clauses)

            # Pick a variable to sweep
            var = 0

            # Fix all others to solution values
            print(f"\n  n={n}, seed={seed}, sweeping var {var} "
                  f"(solution={sol[var]}):")

            # Soft satisfaction as function of x[var]
            print(f"    {'x':>6} | {'soft_sat':>8} | {'discrete_sat':>12} | "
                  f"{'gradient':>8}")
            print("    " + "-" * 45)

            prev_sat = None
            local_mins = 0
            for xi in range(21):
                x_val = xi / 20.0
                # Compute soft satisfaction
                total_soft = 0.0
                total_disc = 0
                for clause in clauses:
                    prod = 1.0
                    disc_sat = False
                    for v, s in clause:
                        if v == var:
                            val = x_val
                        else:
                            val = float(sol[v])
                        lit = val if s == 1 else (1.0 - val)
                        prod *= (1.0 - lit)
                        if (s == 1 and (1 if val > 0.5 else 0) == 1) or \
                           (s == -1 and (1 if val > 0.5 else 0) == 0):
                            disc_sat = True
                    total_soft += (1.0 - prod)
                    if disc_sat: total_disc += 1

                # Numerical gradient
                grad = 0.0
                if prev_sat is not None:
                    grad = (total_soft - prev_sat) / 0.05
                prev_sat = total_soft

                marker = " ←SOL" if abs(x_val - sol[var]) < 0.05 else ""
                print(f"    {x_val:>6.2f} | {total_soft:>8.2f} | "
                      f"{total_disc:>12} | {grad:>+8.2f}{marker}")

            break  # one instance per n


# ============================================================
# 3. PARTICLE TRAJECTORIES: Paths through space
# ============================================================

def experiment_trajectories():
    print("\n" + "=" * 70)
    print("3. PARTICLE TRAJECTORIES: How do bits find the solution?")
    print("=" * 70)

    print("""
    Run physics simulation, track x(t) for each variable.
    Does the particle go straight to the solution?
    Or does it wander, oscillate, get stuck?
    """)

    random.seed(42)
    np.random.seed(42)

    n = 12
    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+73000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        # Physics simulation with trajectory recording
        x = np.array([0.5 + 0.1 * compute_tension(clauses, n, v)
                      for v in range(n)])
        vel = np.zeros(n)

        n_steps = 500
        # Record trajectory at 10 checkpoints
        checkpoints = [int(n_steps * p) for p in
                      [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]]

        trajectories = {v: [] for v in range(min(n, 6))}

        for step in range(n_steps):
            progress = step / n_steps
            T = 0.3 * math.exp(-4.0 * progress) + 0.0001
            crystal = 3.0 * progress

            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0
                lits = []
                for v, s in clause:
                    lit = x[v] if s == 1 else (1.0 - x[v])
                    lits.append((v, lit, s))
                    prod *= max(1.0 - lit, 1e-12)
                if prod < 0.0001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1.0 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)

            for v in range(n):
                if x[v] > 0.5:
                    forces[v] += crystal * (1.0 - x[v])
                else:
                    forces[v] -= crystal * x[v]

            noise = np.random.normal(0, T, n)
            vel = 0.93 * vel + (forces + noise) * 0.05
            x = np.clip(x + vel * 0.05, 0, 1)

            if step in checkpoints:
                for v in range(min(n, 6)):
                    trajectories[v].append((step, x[v], vel[v]))

        print(f"\n  n={n}, seed={seed}:")
        for v in range(min(n, 6)):
            target = sol[v]
            path = trajectories[v]
            positions = [f"{p[1]:.2f}" for p in path]
            final = path[-1][1]
            correct = (final > 0.5) == (target == 1)
            print(f"    x{v:>2} (sol={target}): {' → '.join(positions)} "
                  f"{'✓' if correct else '✗'}")

        break


# ============================================================
# 4. VELOCITY AS HIDDEN VARIABLE
# ============================================================

def experiment_velocity():
    print("\n" + "=" * 70)
    print("4. VELOCITY AS HIDDEN VARIABLE: Does momentum know the answer?")
    print("=" * 70)

    print("""
    At the moment of "measurement" (rounding x to 0/1),
    the velocity carries information:
    - High |v| toward solution → confident
    - High |v| away from solution → about to oscillate back
    - Low |v| → stuck at current position

    Does velocity PREDICT correctness beyond position alone?
    """)

    random.seed(42)
    np.random.seed(42)

    n = 20
    position_correct = []  # (|x - 0.5|, correct)
    velocity_info = []     # (velocity, correct, |x-0.5|)

    for seed in range(50):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+74000000)
        if n <= 16:
            solutions = find_solutions(clauses, n)
        else:
            solutions = None
        if n <= 16 and not solutions:
            continue
        if n <= 16:
            sol = solutions[0]
        else:
            continue

        m = len(clauses)

        # Run physics to near-convergence
        x = np.array([0.5 + 0.1 * compute_tension(clauses, n, v)
                      for v in range(n)])
        vel = np.zeros(n)

        for step in range(300):
            progress = step / 300
            T = 0.25 * math.exp(-4.0 * progress) + 0.0001
            crystal = 3.0 * progress

            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0
                lits = []
                for v, s in clause:
                    lit = x[v] if s == 1 else (1.0 - x[v])
                    lits.append((v, lit, s))
                    prod *= max(1.0 - lit, 1e-12)
                if prod < 0.001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1.0 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)

            for v in range(n):
                if x[v] > 0.5: forces[v] += crystal * (1.0 - x[v])
                else: forces[v] -= crystal * x[v]

            noise = np.random.normal(0, T, n)
            vel = 0.93 * vel + (forces + noise) * 0.05
            x = np.clip(x + vel * 0.05, 0, 1)

        # At this point, measure position and velocity
        for v in range(n):
            predicted = 1 if x[v] > 0.5 else 0
            correct = (predicted == sol[v])
            dist = abs(x[v] - 0.5)  # confidence from position
            # Velocity sign: positive = moving toward 1
            v_sign = 1 if vel[v] > 0 else -1
            v_agrees = (v_sign == 1 and sol[v] == 1) or \
                       (v_sign == -1 and sol[v] == 0)

            position_correct.append((dist, correct))
            velocity_info.append((abs(vel[v]), v_agrees, dist, correct))

    # Analysis
    # Bin by position confidence
    bins = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.5)]
    print(f"\n  {'|x-0.5|':>10} | {'pos acc':>7} | {'vel agrees':>10} | "
          f"{'combined':>8} | {'n':>5}")
    print("  " + "-" * 50)

    for lo, hi in bins:
        subset_pos = [c for d, c in position_correct if lo <= d < hi]
        subset_vel = [va for _, va, d, _ in velocity_info if lo <= d < hi]
        # Combined: position says one thing, velocity agrees or not
        combined = [(c, va) for _, va, d, c in velocity_info if lo <= d < hi]

        if len(subset_pos) >= 10:
            pos_acc = 100 * sum(subset_pos) / len(subset_pos)
            vel_agree = 100 * sum(subset_vel) / len(subset_vel)
            # Combined accuracy: when both position and velocity agree
            both_agree = [c for c, va in combined if va]
            both_disagree = [c for c, va in combined if not va]
            comb_acc = 100 * sum(both_agree) / len(both_agree) if both_agree else 0
            print(f"  [{lo:.1f},{hi:.1f}) | {pos_acc:>6.1f}% | "
                  f"{vel_agree:>9.1f}% | {comb_acc:>7.1f}% | {len(subset_pos):>5}")

    # KEY: Does velocity add information beyond position?
    uncertain = [(abs(vel_v), correct, va)
                 for vel_v, va, d, correct in velocity_info
                 if d < 0.15]  # uncertain positions
    if uncertain:
        pos_only = 100 * sum(c for _, c, _ in uncertain) / len(uncertain)
        vel_pred = 100 * sum(va for _, _, va in uncertain) / len(uncertain)
        print(f"\n  UNCERTAIN BITS (|x-0.5| < 0.15):")
        print(f"    Position accuracy: {pos_only:.1f}%")
        print(f"    Velocity predicts correct sign: {vel_pred:.1f}%")
        print(f"    → Velocity {'ADDS' if vel_pred > 55 else 'does NOT add'} "
              f"information beyond position")


# ============================================================
# 5. DECISION THRESHOLD: When does a bit choose?
# ============================================================

def experiment_decision_point():
    print("\n" + "=" * 70)
    print("5. DECISION THRESHOLD: At what x does a bit 'decide'?")
    print("=" * 70)

    print("""
    In physics simulation, x starts near 0.5 and drifts.
    At some point, x crosses a "point of no return" after which
    it always ends up on the same side. When is this?

    Run same instance with different noise seeds.
    For each var: at what step does the final value become deterministic?
    """)

    random.seed(42)
    np.random.seed(42)

    n = 12
    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+75000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        # Run simulation 20 times with different noise
        n_runs = 20
        final_values = np.zeros((n_runs, n))

        for run in range(n_runs):
            np.random.seed(run * 1000 + seed)
            x = np.array([0.5 + 0.05 * compute_tension(clauses, n, v)
                          for v in range(n)])
            vel = np.zeros(n)

            for step in range(400):
                progress = step / 400
                T = 0.25 * math.exp(-4.0 * progress) + 0.0001
                crystal = 3.0 * progress
                forces = np.zeros(n)
                for clause in clauses:
                    prod = 1.0; lits = []
                    for v, s in clause:
                        lit = x[v] if s == 1 else (1.0 - x[v])
                        lits.append((v, lit, s))
                        prod *= max(1.0 - lit, 1e-12)
                    if prod < 0.001: continue
                    w = math.sqrt(prod)
                    for v, lit, s in lits:
                        term = max(1.0 - lit, 1e-12)
                        forces[v] += s * w * (prod / term)
                for v in range(n):
                    if x[v] > 0.5: forces[v] += crystal * (1.0 - x[v])
                    else: forces[v] -= crystal * x[v]
                noise = np.random.normal(0, T, n)
                vel = 0.93 * vel + (forces + noise) * 0.05
                x = np.clip(x + vel * 0.05, 0, 1)

            final_values[run] = x

        # For each var: what fraction end up >0.5?
        print(f"\n  n={n}, seed={seed}:")
        print(f"  {'var':>5} | {'sol':>3} | {'P(>0.5)':>8} | {'deterministic?':>14} | "
              f"{'correct?':>8}")
        print("  " + "-" * 50)

        deterministic = 0
        correct_det = 0
        for v in range(n):
            p_high = np.mean(final_values[:, v] > 0.5)
            is_det = p_high > 0.9 or p_high < 0.1
            predicted = 1 if p_high > 0.5 else 0
            is_correct = (predicted == sol[v])

            if is_det:
                deterministic += 1
                if is_correct: correct_det += 1

            marker = "DET" if is_det else "RAND"
            print(f"  x{v:>3} | {sol[v]:>3} | {p_high:>8.2f} | "
                  f"{marker:>14} | {'✓' if is_correct else '✗':>8}")

        print(f"\n  Deterministic: {deterministic}/{n} "
              f"({100*deterministic/n:.0f}%)")
        print(f"  Correct among deterministic: {correct_det}/{deterministic} "
              f"({100*correct_det/max(deterministic,1):.0f}%)" if deterministic else "")
        print(f"  Random (noise-dependent): {n-deterministic}/{n}")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    experiment_clause_votes()
    experiment_energy_landscape()
    experiment_trajectories()
    experiment_velocity()
    experiment_decision_point()
