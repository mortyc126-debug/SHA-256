"""
TRAJECTORY SPACE DEEP DIVE

Correct bits gain confidence monotonically (18.9% vs 11.3%).
What else is in the trajectory?

1. Full trajectory SHAPE classification
2. Does trajectory predict WHICH direction is correct?
3. Trajectory as TIME SERIES: autocorrelation, trends, jumps
4. Can trajectory-based ordering beat tension-based?
5. CROSS-TRAJECTORIES: do correct bits' trajectories correlate?
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


def crystallize_with_trajectories(clauses, n, correct_val=None):
    """Record full trajectory of every bit during crystallization."""
    trajectories = {v: [] for v in range(n)}
    fixed = {}
    order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

    for step_var in order:
        for v in range(n):
            if v not in fixed:
                trajectories[v].append(bit_tension(clauses, n, v, fixed))

        sigma = bit_tension(clauses, n, step_var, fixed)
        fixed[step_var] = 1 if sigma >= 0 else 0

        # UP
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False; free = []
                for v, s in clause:
                    if v in fixed:
                        if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                            satisfied = True; break
                    else: free.append((v,s))
                if not satisfied and len(free) == 1:
                    v, s = free[0]
                    if v not in fixed: fixed[v] = 1 if s==1 else 0; changed = True

    return trajectories, fixed


# ============================================================
# 1. TRAJECTORY SHAPE CLASSIFICATION
# ============================================================

def trajectory_shapes():
    print("=" * 70)
    print("1. TRAJECTORY SHAPE CLASSIFICATION")
    print("=" * 70)

    random.seed(42); n = 12

    shapes_correct = {}
    shapes_wrong = {}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        trajectories, fixed = crystallize_with_trajectories(clauses, n, correct_val)

        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 3: continue

            sigma = traj[0]
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            abs_traj = [abs(t) for t in traj]

            # Classify shape
            # Sign changes
            sign_changes = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)

            # Trend: does |σ| grow?
            if len(abs_traj) >= 2:
                first_half = sum(abs_traj[:len(abs_traj)//2]) / (len(abs_traj)//2)
                second_half = sum(abs_traj[len(abs_traj)//2:]) / (len(abs_traj) - len(abs_traj)//2)
                trend = second_half - first_half
            else:
                trend = 0

            # Jump: largest single-step change in |σ|
            max_jump = max(abs(abs_traj[i]-abs_traj[i-1]) for i in range(1, len(abs_traj))) if len(abs_traj) > 1 else 0

            # Early lock: does σ stabilize early?
            if len(traj) >= 4:
                early_stable = all(abs(traj[i] - traj[i+1]) < 0.1 for i in range(min(3, len(traj)-1)))
            else:
                early_stable = False

            # Shape name
            if sign_changes == 0 and trend > 0.1:
                shape = "converging"
            elif sign_changes == 0 and trend <= 0.1:
                shape = "steady"
            elif sign_changes == 1:
                shape = "single_flip"
            elif sign_changes >= 2:
                shape = "oscillating"
            else:
                shape = "other"

            target = shapes_correct if is_correct else shapes_wrong
            target[shape] = target.get(shape, 0) + 1

    print(f"\n  {'shape':>15} | {'correct':>8} | {'wrong':>8} | {'C/(C+W)':>8}")
    print("  " + "-" * 45)

    all_shapes = set(list(shapes_correct.keys()) + list(shapes_wrong.keys()))
    for shape in sorted(all_shapes):
        c = shapes_correct.get(shape, 0)
        w = shapes_wrong.get(shape, 0)
        ratio = c/(c+w)*100 if c+w > 0 else 0
        print(f"  {shape:>15} | {c:>8} | {w:>8} | {ratio:>7.1f}%")


# ============================================================
# 2. TRAJECTORY FEATURES AS PREDICTOR
# ============================================================

def trajectory_predictor():
    """
    Extract features from trajectory, use to predict correctness.
    Run crystallization ONCE, then use trajectory features to
    IDENTIFY which bits are likely wrong and flip them.
    """
    print("\n" + "=" * 70)
    print("2. TRAJECTORY-CORRECTED SOLVER")
    print("=" * 70)

    random.seed(42); n = 12

    std_solved = 0; traj_solved = 0; total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        total += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        trajectories, fixed = crystallize_with_trajectories(clauses, n)

        assignment = [fixed.get(v, 0) for v in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            std_solved += 1

        # Trajectory analysis: find bits most likely wrong
        suspicion = {}
        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 2:
                suspicion[var] = 0
                continue

            abs_traj = [abs(t) for t in traj]
            sign_changes = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)

            # Suspicion score: oscillating + low final confidence
            final_conf = abs_traj[-1] if abs_traj else 0
            suspicion[var] = sign_changes * 2 + (1 - final_conf)

        # Try flipping the most suspicious bits
        sorted_by_suspicion = sorted(range(n), key=lambda v: -suspicion[v])

        best_assignment = list(assignment)
        best_sat = evaluate(clauses, best_assignment)

        # Try flipping top 1, top 2, top 3 suspicious bits
        for k in range(1, 4):
            test = list(assignment)
            for v in sorted_by_suspicion[:k]:
                test[v] = 1 - test[v]
            sat = evaluate(clauses, test)
            if sat > best_sat:
                best_assignment = test
                best_sat = sat

        if best_sat == len(clauses):
            traj_solved += 1

    print(f"\n  Standard:            {std_solved}/{total} ({std_solved/total*100:.1f}%)")
    print(f"  Trajectory-corrected: {traj_solved}/{total} ({traj_solved/total*100:.1f}%)")
    print(f"  Improvement:          {(traj_solved-std_solved)/total*100:+.1f}%")


# ============================================================
# 3. MULTI-RUN TRAJECTORY VOTING
# ============================================================

def multi_trajectory():
    """
    Run crystallization multiple times with noise.
    For each bit: compute trajectory features ACROSS runs.
    Bits with CONSISTENT trajectories → trust them.
    Bits with INCONSISTENT → distrust, flip to majority.
    """
    print("\n" + "=" * 70)
    print("3. MULTI-RUN TRAJECTORY ANALYSIS")
    print("=" * 70)

    random.seed(42); n = 12

    std_acc = 0; multi_traj_acc = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Multiple runs
        all_final_vals = {v: [] for v in range(n)}
        all_traj_stable = {v: [] for v in range(n)}

        for run in range(15):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(bit_tension(clauses, n, v)) + random.gauss(0, 0.2)))

            traj = {v: [] for v in range(n)}
            for step_var in order:
                if step_var in fixed: continue
                for v in range(n):
                    if v not in fixed:
                        traj[v].append(bit_tension(clauses, n, v, fixed))
                sigma = bit_tension(clauses, n, step_var, fixed)
                fixed[step_var] = 1 if sigma >= 0 else 0

                changed = True
                while changed:
                    changed = False
                    for clause in clauses:
                        satisfied = False; free = []
                        for v, s in clause:
                            if v in fixed:
                                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                    satisfied = True; break
                            else: free.append((v,s))
                        if not satisfied and len(free) == 1:
                            v, s = free[0]
                            if v not in fixed: fixed[v] = 1 if s==1 else 0; changed = True

            for v in range(n):
                all_final_vals[v].append(fixed.get(v, 0))

                t = traj[v]
                if len(t) >= 2:
                    sign_changes = sum(1 for i in range(1, len(t)) if t[i]*t[i-1] < 0)
                    all_traj_stable[v].append(1 if sign_changes == 0 else 0)

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Standard tension
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == actual: std_acc += 1

            # Multi-trajectory: vote weighted by stability
            vals = all_final_vals[var]
            stabs = all_traj_stable[var]

            if vals:
                # Weight each run's vote by trajectory stability
                weighted_1 = 0; weighted_0 = 0
                for i, val in enumerate(vals):
                    w = stabs[i] + 0.5 if i < len(stabs) else 0.5
                    if val == 1: weighted_1 += w
                    else: weighted_0 += w

                pred = 1 if weighted_1 > weighted_0 else 0
            else:
                pred = 1 if sigma >= 0 else 0

            if pred == actual: multi_traj_acc += 1

    print(f"\n  Standard tension:      {std_acc/total*100:.1f}%")
    print(f"  Multi-trajectory vote: {multi_traj_acc/total*100:.1f}%")
    print(f"  Improvement:           {(multi_traj_acc-std_acc)/total*100:+.1f}%")


# ============================================================
# 4. TRAJECTORY DIVERGENCE: do correct bits converge FASTER?
# ============================================================

def trajectory_convergence():
    """
    For each bit: at what step does |σ| exceed 0.5?
    (= when does the bit become "decided"?)

    Do correct bits decide EARLIER?
    """
    print("\n" + "=" * 70)
    print("4. CONVERGENCE SPEED: When does each bit 'decide'?")
    print("=" * 70)

    random.seed(42); n = 12

    correct_decide = []; wrong_decide = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        trajectories, fixed = crystallize_with_trajectories(clauses, n)

        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 2: continue

            sigma = traj[0]
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            # When does |σ| first exceed 0.5?
            decide_step = len(traj)  # default: never
            for i, t in enumerate(traj):
                if abs(t) > 0.5:
                    decide_step = i
                    break

            # Normalize by trajectory length
            decide_frac = decide_step / len(traj)

            if is_correct:
                correct_decide.append(decide_frac)
            else:
                wrong_decide.append(decide_frac)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Decision point (fraction of trajectory):")
    print(f"    Correct bits: {mean(correct_decide):.3f}")
    print(f"    Wrong bits:   {mean(wrong_decide):.3f}")
    print(f"    Ratio: {mean(wrong_decide)/mean(correct_decide):.2f}" if mean(correct_decide) > 0 else "")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    trajectory_shapes()
    trajectory_predictor()
    multi_trajectory()
    trajectory_convergence()
