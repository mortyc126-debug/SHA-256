"""
5 RADICAL ATTACKS ON THE FROZEN CORE
═══════════════════════════════════════

The information about wrong bits EXISTS (oracle = 100%).
The question is HOW to extract it without knowing the solution.

Five ideas, tested experimentally:
1. REVERSE PHYSICS — run simulation backwards
2. DOUBLE SIMULATION — compare two independent runs
3. STIFFNESS PROBE — measure resistance to perturbation
4. THERMAL PROBE — local heating reveals wrong bits
5. DIFFERENTIAL — compare neighboring solutions
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def physics_run(clauses, n, steps, seed, x_init=None):
    """Run physics, return (x, vel, assignment)."""
    np.random.seed(seed)
    m = len(clauses)
    if x_init is not None:
        x = x_init.copy()
    else:
        x = np.full(n, 0.5)
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            if p1+p0>0: x[v] = 0.5 + 0.35*(p1-p0)/(p1+p0)
    vel = np.zeros(n)

    for step in range(steps):
        prog = step / steps
        T = 0.25 * math.exp(-4*prog) + 0.0001
        crystal = 3.0 * prog
        forces = np.zeros(n)
        for clause in clauses:
            prod = 1.0; lits = []
            for v, s in clause:
                lit = x[v] if s==1 else (1-x[v])
                lits.append((v, lit, s))
                prod *= max(1-lit, 1e-12)
            if prod < 0.001: continue
            w = math.sqrt(prod)
            for v, lit, s in lits:
                term = max(1-lit, 1e-12)
                forces[v] += s * w * (prod/term)
        for v in range(n):
            if x[v]>0.5: forces[v] += crystal*(1-x[v])
            else: forces[v] -= crystal*x[v]
        noise = np.random.normal(0, T, n)
        vel = 0.93*vel + (forces+noise)*0.05
        x = np.clip(x + vel*0.05, 0, 1)

    assignment = [1 if x[v]>0.5 else 0 for v in range(n)]
    return x, vel, assignment


# ============================================================
# 1. STIFFNESS PROBE: Which bits resist perturbation?
# ============================================================

def experiment_stiffness():
    print("=" * 70)
    print("1. STIFFNESS PROBE: Perturb each bit, measure resistance")
    print("=" * 70)

    random.seed(42)
    n = 14

    stiff_wrong = []
    stiff_right = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+5000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        x, vel, assignment = physics_run(clauses, n, 500, seed=seed+42)
        m = len(clauses)

        for v in range(n):
            is_wrong = (assignment[v] != sol[v])

            # Perturb: push bit toward opposite value
            x_pert = x.copy()
            original = x[v]
            x_pert[v] = 1.0 - original  # flip to opposite extreme

            # Run SHORT physics from perturbed state (50 steps, no noise)
            x_test = x_pert.copy()
            vel_test = np.zeros(n)
            for step in range(50):
                forces = np.zeros(n)
                for clause in clauses:
                    prod = 1.0; lits = []
                    for vi, si in clause:
                        lit = x_test[vi] if si==1 else (1-x_test[vi])
                        lits.append((vi, lit, si))
                        prod *= max(1-lit, 1e-12)
                    if prod < 0.001: continue
                    w = math.sqrt(prod)
                    for vi, lit, si in lits:
                        term = max(1-lit, 1e-12)
                        forces[vi] += si * w * (prod/term)
                for vi in range(n):
                    if x_test[vi]>0.5: forces[vi] += 2*(1-x_test[vi])
                    else: forces[vi] -= 2*x_test[vi]
                vel_test = 0.9*vel_test + forces*0.03
                x_test = np.clip(x_test + vel_test*0.03, 0, 1)

            # Stiffness = how much did the bit bounce back?
            bounced_back = abs(x_test[v] - (1.0 - original))
            # If stiff: bit bounced back to original → bounced_back ≈ 1
            # If soft: bit stayed at flipped value → bounced_back ≈ 0

            if is_wrong:
                stiff_wrong.append(bounced_back)
            else:
                stiff_right.append(bounced_back)

    if stiff_wrong and stiff_right:
        avg_w = sum(stiff_wrong)/len(stiff_wrong)
        avg_r = sum(stiff_right)/len(stiff_right)
        print(f"\n  Wrong bits bounce-back: {avg_w:.4f}")
        print(f"  Right bits bounce-back: {avg_r:.4f}")
        print(f"  Ratio: {avg_w/max(avg_r,0.001):.3f}")
        if avg_w < avg_r * 0.9:
            print(f"  → Wrong bits are SOFTER (less stiff) ← DISCRIMINATIVE!")
        elif avg_w > avg_r * 1.1:
            print(f"  → Wrong bits are STIFFER ← unexpected but discriminative!")
        else:
            print(f"  → Similar stiffness — NOT discriminative")


# ============================================================
# 2. DOUBLE SIMULATION: Compare two independent runs
# ============================================================

def experiment_double():
    print("\n" + "=" * 70)
    print("2. DOUBLE SIMULATION: Bits that DIFFER between two runs")
    print("=" * 70)

    random.seed(42)
    n = 14

    differ_wrong_rate = []
    differ_right_rate = []
    n_solved_by_diff = 0
    n_total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+5100000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        # Two independent physics runs
        _, _, a1 = physics_run(clauses, n, 500, seed=seed*2+1)
        _, _, a2 = physics_run(clauses, n, 500, seed=seed*2+2)

        sat1 = evaluate(clauses, a1)
        sat2 = evaluate(clauses, a2)
        if sat1 == m or sat2 == m:
            n_total += 1
            n_solved_by_diff += 1
            continue

        n_total += 1

        # Find bits that DIFFER between runs
        differ = set(v for v in range(n) if a1[v] != a2[v])
        agree = set(range(n)) - differ

        # Among differing bits: what fraction are wrong in a1?
        for v in range(n):
            is_wrong = (a1[v] != sol[v])
            is_differ = v in differ
            if is_differ:
                if is_wrong:
                    differ_wrong_rate.append(1)
                else:
                    differ_wrong_rate.append(0)
            else:
                if is_wrong:
                    differ_right_rate.append(1)  # wrong but agrees across runs
                else:
                    differ_right_rate.append(0)

        # Try: flip differing bits to match the OTHER run
        # i.e., create hybrid: for agree bits use a1, for differ use a2
        hybrid = list(a1)
        for v in differ:
            hybrid[v] = a2[v]
        if evaluate(clauses, hybrid) == m:
            n_solved_by_diff += 1

    if differ_wrong_rate:
        # P(wrong | differs across runs)
        p_wrong_if_differ = sum(differ_wrong_rate) / len(differ_wrong_rate)
        # P(wrong | agrees across runs)
        p_wrong_if_agree = sum(differ_right_rate) / len(differ_right_rate)

        print(f"\n  P(wrong | bit DIFFERS across runs): {100*p_wrong_if_differ:.1f}%")
        print(f"  P(wrong | bit AGREES across runs):  {100*p_wrong_if_agree:.1f}%")
        print(f"  Lift: {p_wrong_if_differ/max(p_wrong_if_agree, 0.001):.2f}×")

        print(f"\n  Solved by hybrid (a1+a2): {n_solved_by_diff}/{n_total}")


# ============================================================
# 3. THERMAL PROBE: Heat one bit, watch for distant cascades
# ============================================================

def experiment_thermal_probe():
    print("\n" + "=" * 70)
    print("3. THERMAL PROBE: Heat each bit, measure cascade")
    print("=" * 70)

    random.seed(42)
    n = 14

    cascade_wrong = []
    cascade_right = []

    for seed in range(50):
        clauses = random_3sat(n, int(4.267*n), seed=seed+5200000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        x_base, _, assignment = physics_run(clauses, n, 500, seed=seed+42)

        for v in range(n):
            is_wrong = (assignment[v] != sol[v])

            # Heat bit v: add large noise, run short sim, measure GLOBAL change
            x_heated = x_base.copy()
            # Flip the bit and run 30 steps
            x_heated[v] = 1.0 - x_heated[v]
            vel_h = np.zeros(n)

            for step in range(30):
                forces = np.zeros(n)
                for clause in clauses:
                    prod = 1.0; lits = []
                    for vi, si in clause:
                        lit = x_heated[vi] if si==1 else (1-x_heated[vi])
                        lits.append((vi, lit, si))
                        prod *= max(1-lit, 1e-12)
                    if prod < 0.001: continue
                    w = math.sqrt(prod)
                    for vi, lit, si in lits:
                        term = max(1-lit, 1e-12)
                        forces[vi] += si * w * (prod/term)
                for vi in range(n):
                    if x_heated[vi]>0.5: forces[vi] += 2*(1-x_heated[vi])
                    else: forces[vi] -= 2*x_heated[vi]
                vel_h = 0.9*vel_h + forces*0.03
                x_heated = np.clip(x_heated + vel_h*0.03, 0, 1)

            # Measure satisfaction change
            a_heated = [1 if x_heated[vi]>0.5 else 0 for vi in range(n)]
            sat_heated = evaluate(clauses, a_heated)
            sat_base = evaluate(clauses, assignment)
            delta_sat = sat_heated - sat_base

            # Total displacement of OTHER bits
            displacement = sum(abs(x_heated[vi] - x_base[vi])
                              for vi in range(n) if vi != v)

            if is_wrong:
                cascade_wrong.append((delta_sat, displacement))
            else:
                cascade_right.append((delta_sat, displacement))

    if cascade_wrong and cascade_right:
        avg_dsat_w = sum(d for d, _ in cascade_wrong) / len(cascade_wrong)
        avg_dsat_r = sum(d for d, _ in cascade_right) / len(cascade_right)
        avg_disp_w = sum(d for _, d in cascade_wrong) / len(cascade_wrong)
        avg_disp_r = sum(d for _, d in cascade_right) / len(cascade_right)

        print(f"\n  Flipping a WRONG bit then relaxing:")
        print(f"    Δ(sat clauses): {avg_dsat_w:+.3f}")
        print(f"    Other-bit displacement: {avg_disp_w:.4f}")
        print(f"\n  Flipping a RIGHT bit then relaxing:")
        print(f"    Δ(sat clauses): {avg_dsat_r:+.3f}")
        print(f"    Other-bit displacement: {avg_disp_r:.4f}")
        print(f"\n  Δsat ratio (wrong/right): {avg_dsat_w/min(avg_dsat_r,-0.001):.2f}")
        print(f"  Displacement ratio: {avg_disp_w/max(avg_disp_r,0.001):.2f}")

        if avg_dsat_w > avg_dsat_r + 0.1:
            print(f"\n  → Flipping WRONG bits IMPROVES satisfaction!")
            print(f"  → THIS IS THE SIGNAL — thermal probe WORKS!")
        elif avg_dsat_w > avg_dsat_r:
            print(f"\n  → Slight improvement — weak signal")
        else:
            print(f"\n  → No improvement")


# ============================================================
# 4. STIFFNESS-GUIDED SOLVER: Use probe results to solve
# ============================================================

def experiment_stiffness_solver():
    print("\n" + "=" * 70)
    print("4. STIFFNESS SOLVER: Flip softest bits first")
    print("=" * 70)

    random.seed(42)
    n = 16

    solved_base = 0
    solved_stiff = 0
    solved_thermal = 0
    n_total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+5300000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]
        m = len(clauses)

        x_base, vel_base, assignment = physics_run(clauses, n, 500, seed=seed+42)
        base_sat = evaluate(clauses, assignment)
        n_total += 1

        if base_sat == m:
            solved_base += 1; solved_stiff += 1; solved_thermal += 1
            continue

        # Measure stiffness for each variable
        stiffness = np.zeros(n)
        thermal_response = np.zeros(n)

        for v in range(n):
            # Stiffness: flip and measure bounce-back
            x_p = x_base.copy()
            x_p[v] = 1.0 - x_p[v]
            vel_p = np.zeros(n)
            for step in range(30):
                forces = np.zeros(n)
                for clause in clauses:
                    prod=1.0; lits=[]
                    for vi,si in clause:
                        lit=x_p[vi] if si==1 else (1-x_p[vi])
                        lits.append((vi,lit,si))
                        prod*=max(1-lit,1e-12)
                    if prod<0.001: continue
                    w=math.sqrt(prod)
                    for vi,lit,si in lits:
                        term=max(1-lit,1e-12)
                        forces[vi]+=si*w*(prod/term)
                for vi in range(n):
                    if x_p[vi]>0.5: forces[vi]+=2*(1-x_p[vi])
                    else: forces[vi]-=2*x_p[vi]
                vel_p=0.9*vel_p+forces*0.03
                x_p=np.clip(x_p+vel_p*0.03,0,1)

            stiffness[v] = abs(x_p[v] - (1-x_base[v]))

            # Thermal: Δ satisfaction
            a_t = [1 if x_p[vi]>0.5 else 0 for vi in range(n)]
            thermal_response[v] = evaluate(clauses, a_t) - base_sat

        # STIFFNESS SOLVER: flip the SOFTEST bits (lowest stiffness)
        sorted_by_soft = np.argsort(stiffness)
        for k in range(1, min(n, 10)):
            test = list(assignment)
            for v in sorted_by_soft[:k]:
                test[v] = 1 - test[v]
            if evaluate(clauses, test) == m:
                solved_stiff += 1; break

        # THERMAL SOLVER: flip bits with BEST thermal response
        sorted_by_thermal = np.argsort(-thermal_response)
        for k in range(1, min(n, 10)):
            test = list(assignment)
            for v in sorted_by_thermal[:k]:
                test[v] = 1 - test[v]
            if evaluate(clauses, test) == m:
                solved_thermal += 1; break

    print(f"\n  n={n} ({n_total} instances):")
    print(f"    Physics alone:      {solved_base}/{n_total}")
    print(f"    + Stiffness flip:   {solved_stiff}/{n_total} "
          f"(+{solved_stiff-solved_base})")
    print(f"    + Thermal flip:     {solved_thermal}/{n_total} "
          f"(+{solved_thermal-solved_base})")


if __name__ == "__main__":
    experiment_stiffness()
    experiment_double()
    experiment_thermal_probe()
    experiment_stiffness_solver()
