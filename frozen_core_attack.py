"""
FROZEN CORE ATTACK: What makes √n variables impossibly hard?
════════════════════════════════════════════════════════════

We know:
  - Physics reaches 99% satisfaction in O(n²)
  - ~√n clauses remain unsatisfied
  - Fixing them is EXPONENTIAL

QUESTIONS:
  1. WHAT are the frozen variables? Can we identify them beforehand?
  2. WHY are they hard? What structural property makes them resistant?
  3. CAN we crack them with a different approach than WalkSAT?
  4. IS there information about them HIDDEN in the 99% solution?

EXPERIMENTS:
  A. Identify frozen vars by comparing multiple solutions
  B. Measure their tension, degree, self-cancellation, graph position
  C. Test if physics trajectory PREDICTS which vars are frozen
  D. Try targeted attacks: eigenmode projection, cluster detection
  E. The key: can we EXTRACT frozen core info from the 99% state?
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
                if s == 1: p1 += 1/3
                else: p0 += 1/3
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# A. IDENTIFY: Who are the frozen variables?
# ============================================================

def experiment_identify():
    print("=" * 70)
    print("A. IDENTIFY: Which variables are frozen?")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14, 16]:
        frozen_tension = []
        free_tension = []
        frozen_degree = []
        free_degree = []
        frozen_sc = []
        free_sc = []

        n_inst = 0
        for seed in range(300):
            clauses = random_3sat(n, int(4.267 * n), seed=seed + 3000000)
            solutions = find_solutions(clauses, n)
            if len(solutions) < 2:
                continue

            # Frozen = same value in ALL solutions
            frozen = set()
            free = set()
            for v in range(n):
                vals = set(s[v] for s in solutions)
                if len(vals) == 1:
                    frozen.add(v)
                else:
                    free.add(v)

            if not frozen or not free:
                continue

            # Measure properties
            tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
            degrees = {}
            for v in range(n):
                degrees[v] = sum(1 for c in clauses for vi, si in c if vi == v)

            # Adjacency for self-cancellation
            adj = {v: set() for v in range(n)}
            for c in clauses:
                vs = [v for v, s in c]
                for a in vs:
                    for b in vs:
                        if a != b: adj[a].add(b)

            for v in range(n):
                t = abs(tensions[v])
                d = degrees[v]
                neighbors = adj[v]
                if neighbors:
                    nav = sum(tensions.get(u, 0) for u in neighbors) / len(neighbors)
                    sc = abs(tensions[v] + nav)
                else:
                    sc = t

                if v in frozen:
                    frozen_tension.append(t)
                    frozen_degree.append(d)
                    frozen_sc.append(sc)
                else:
                    free_tension.append(t)
                    free_degree.append(d)
                    free_sc.append(sc)

            n_inst += 1
            if n_inst >= 30:
                break

        if frozen_tension and free_tension:
            print(f"\n  n={n} ({n_inst} instances):")
            print(f"    {'property':>15} | {'frozen':>8} | {'free':>8} | {'ratio':>6}")
            print(f"    " + "-" * 45)

            avg_ft = sum(frozen_tension) / len(frozen_tension)
            avg_frt = sum(free_tension) / len(free_tension)
            print(f"    {'|tension|':>15} | {avg_ft:>8.4f} | {avg_frt:>8.4f} | "
                  f"{avg_ft/max(avg_frt,0.001):>6.2f}")

            avg_fd = sum(frozen_degree) / len(frozen_degree)
            avg_frd = sum(free_degree) / len(free_degree)
            print(f"    {'degree':>15} | {avg_fd:>8.1f} | {avg_frd:>8.1f} | "
                  f"{avg_fd/max(avg_frd,0.001):>6.2f}")

            avg_fsc = sum(frozen_sc) / len(frozen_sc)
            avg_frsc = sum(free_sc) / len(free_sc)
            print(f"    {'self-cancel':>15} | {avg_fsc:>8.4f} | {avg_frsc:>8.4f} | "
                  f"{avg_fsc/max(avg_frsc,0.001):>6.2f}")

            print(f"\n    Frozen: {len(frozen_tension)} vars, "
                  f"Free: {len(free_tension)} vars")
            print(f"    Frozen fraction: "
                  f"{len(frozen_tension)/(len(frozen_tension)+len(free_tension)):.2f}")


# ============================================================
# B. WHY HARD: What structural property freezes them?
# ============================================================

def experiment_why_hard():
    print("\n" + "=" * 70)
    print("B. WHY HARD: What makes frozen variables resistant?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 3100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 3:
            continue

        frozen = [v for v in range(n)
                  if len(set(s[v] for s in solutions)) == 1]
        free = [v for v in range(n) if v not in frozen]

        if len(frozen) < 3 or len(free) < 3:
            continue

        sol = solutions[0]

        print(f"\n  n={n}, seed={seed}, {len(solutions)} solutions:")
        print(f"  Frozen: {frozen} (value: {[sol[v] for v in frozen]})")
        print(f"  Free:   {free} (varies across solutions)")

        # Build clause involvement
        # For each clause: how many frozen vs free vars?
        clause_types = {'all_frozen': 0, 'mixed': 0, 'all_free': 0}
        frozen_set = set(frozen)
        for clause in clauses:
            vs = [v for v, s in clause]
            n_frozen = sum(1 for v in vs if v in frozen_set)
            if n_frozen == 3:
                clause_types['all_frozen'] += 1
            elif n_frozen == 0:
                clause_types['all_free'] += 1
            else:
                clause_types['mixed'] += 1

        print(f"\n  Clause types:")
        print(f"    All-frozen: {clause_types['all_frozen']}")
        print(f"    Mixed:      {clause_types['mixed']}")
        print(f"    All-free:   {clause_types['all_free']}")

        # Key insight: frozen vars are LOCKED by the clause network
        # If we flip a frozen var, how many clauses break?
        print(f"\n  Flip impact (clauses broken by flipping one var):")
        print(f"    {'var':>5} | {'type':>6} | {'breaks':>6} | {'% of m':>6}")
        print(f"    " + "-" * 30)

        m = len(clauses)
        frozen_breaks = []
        free_breaks = []

        for v in range(n):
            flipped = list(sol)
            flipped[v] = 1 - flipped[v]
            breaks = m - evaluate(clauses, flipped)
            vtype = "FROZEN" if v in frozen_set else "free"

            if v in frozen_set:
                frozen_breaks.append(breaks)
            else:
                free_breaks.append(breaks)

            if v < 8 or breaks > 3:  # show interesting ones
                print(f"    x{v:>3} | {vtype:>6} | {breaks:>6} | "
                      f"{100*breaks/m:>5.1f}%")

        if frozen_breaks and free_breaks:
            print(f"\n    Avg breaks: frozen={sum(frozen_breaks)/len(frozen_breaks):.1f}"
                  f", free={sum(free_breaks)/len(free_breaks):.1f}")
            print(f"    → Frozen vars break {sum(frozen_breaks)/len(frozen_breaks) / max(sum(free_breaks)/len(free_breaks), 0.01):.1f}× more clauses")

        break


# ============================================================
# C. PREDICT: Can physics trajectory identify frozen vars?
# ============================================================

def experiment_predict():
    print("\n" + "=" * 70)
    print("C. PREDICT: Does the physics trajectory reveal frozen vars?")
    print("=" * 70)

    print("""
    Run physics 20 times with different noise.
    Frozen vars → should be DET (same outcome every time).
    Free vars → should be RAND (varies with noise).
    Does DET/RAND classification MATCH frozen/free?
    """)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 3200000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2:
            continue

        frozen_set = set(v for v in range(n)
                        if len(set(s[v] for s in solutions)) == 1)
        free_set = set(range(n)) - frozen_set

        if len(frozen_set) < 3 or len(free_set) < 2:
            continue

        # Run physics 20 times
        finals = np.zeros((20, n))
        for run in range(20):
            np.random.seed(run * 100 + seed)
            x = np.full(n, 0.5)
            vel = np.zeros(n)
            for step in range(400):
                prog = step / 400
                T = 0.25 * math.exp(-4 * prog) + 0.0001
                crystal = 3.0 * prog
                forces = np.zeros(n)
                for clause in clauses:
                    prod = 1.0; lits = []
                    for v, s in clause:
                        lit = x[v] if s == 1 else (1 - x[v])
                        lits.append((v, lit, s))
                        prod *= max(1 - lit, 1e-12)
                    if prod < 0.001: continue
                    w = math.sqrt(prod)
                    for v, lit, s in lits:
                        term = max(1 - lit, 1e-12)
                        forces[v] += s * w * (prod / term)
                for v in range(n):
                    if x[v] > 0.5: forces[v] += crystal * (1 - x[v])
                    else: forces[v] -= crystal * x[v]
                noise = np.random.normal(0, T, n)
                vel = 0.93 * vel + (forces + noise) * 0.05
                x = np.clip(x + vel * 0.05, 0, 1)
            finals[run] = x

        # Classify DET/RAND
        p_high = np.mean(finals > 0.5, axis=0)
        det_set = set(v for v in range(n) if p_high[v] > 0.9 or p_high[v] < 0.1)
        rand_set = set(range(n)) - det_set

        # Confusion matrix
        tp = len(frozen_set & det_set)   # frozen correctly identified as DET
        fn = len(frozen_set & rand_set)  # frozen missed (classified as RAND)
        fp = len(free_set & det_set)     # free wrongly classified as DET
        tn = len(free_set & rand_set)    # free correctly identified as RAND

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        accuracy = (tp + tn) / n

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Frozen: {len(frozen_set)}, Free: {len(free_set)}")
        print(f"    DET:    {len(det_set)}, RAND: {len(rand_set)}")
        print(f"\n    Confusion matrix:")
        print(f"      {'':>10} | {'DET':>5} | {'RAND':>5}")
        print(f"      {'Frozen':>10} | {tp:>5} | {fn:>5}")
        print(f"      {'Free':>10} | {fp:>5} | {tn:>5}")
        print(f"\n    Precision: {100*precision:.0f}% "
              f"(of DET vars, how many are truly frozen)")
        print(f"    Recall:    {100*recall:.0f}% "
              f"(of frozen vars, how many detected as DET)")
        print(f"    Accuracy:  {100*accuracy:.0f}%")

        break


# ============================================================
# D. CRACK: Can we extract frozen core info from 99% state?
# ============================================================

def experiment_crack():
    print("\n" + "=" * 70)
    print("D. CRACK: Information in the 99% state about frozen vars")
    print("=" * 70)

    print("""
    After physics reaches 99%: the WRONG bits are mostly frozen vars.
    If we can identify WHICH bits are wrong from the 99% state alone,
    we can flip them and solve.

    Test: do wrong bits in the 99% state have distinguishing features?
    """)

    random.seed(42)
    n = 14

    wrong_features = []  # (tension, sat_frac, n_unsat_clauses)
    right_features = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 3300000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue
        sol = solutions[0]
        m = len(clauses)

        # Run physics
        np.random.seed(seed + 42)
        x = np.array([0.5 + 0.1 * compute_tension(clauses, n, v)
                      for v in range(n)])
        vel = np.zeros(n)
        for step in range(500):
            prog = step / 500
            T = 0.25 * math.exp(-4 * prog) + 0.0001
            crystal = 3.0 * prog
            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0; lits = []
                for v, s in clause:
                    lit = x[v] if s == 1 else (1 - x[v])
                    lits.append((v, lit, s))
                    prod *= max(1 - lit, 1e-12)
                if prod < 0.001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)
            for v in range(n):
                if x[v] > 0.5: forces[v] += crystal * (1 - x[v])
                else: forces[v] -= crystal * x[v]
            noise = np.random.normal(0, T, n)
            vel = 0.93 * vel + (forces + noise) * 0.05
            x = np.clip(x + vel * 0.05, 0, 1)

        assignment = [1 if x[v] > 0.5 else 0 for v in range(n)]

        # For each variable: is it wrong?
        for v in range(n):
            is_wrong = (assignment[v] != sol[v])

            # Features of this variable in the 99% state
            confidence = abs(x[v] - 0.5)  # how far from 0.5
            velocity_mag = abs(vel[v])

            # How many of v's clauses are unsatisfied?
            v_unsat = 0
            v_total = 0
            for clause in clauses:
                if any(vi == v for vi, si in clause):
                    v_total += 1
                    if not any((si == 1 and assignment[vi] == 1) or
                              (si == -1 and assignment[vi] == 0)
                              for vi, si in clause):
                        v_unsat += 1

            features = (confidence, velocity_mag, v_unsat / max(v_total, 1))

            if is_wrong:
                wrong_features.append(features)
            else:
                right_features.append(features)

    if wrong_features and right_features:
        print(f"\n  {len(wrong_features)} wrong bits, {len(right_features)} right bits")
        print(f"\n  {'feature':>15} | {'wrong':>8} | {'right':>8} | {'ratio':>6} | {'discriminative?':>15}")
        print(f"  " + "-" * 65)

        for i, name in enumerate(['confidence', '|velocity|', 'unsat_frac']):
            avg_w = sum(f[i] for f in wrong_features) / len(wrong_features)
            avg_r = sum(f[i] for f in right_features) / len(right_features)
            ratio = avg_w / max(avg_r, 0.0001)
            disc = "YES" if abs(ratio - 1) > 0.2 else "no"
            print(f"  {name:>15} | {avg_w:>8.4f} | {avg_r:>8.4f} | "
                  f"{ratio:>6.2f} | {disc:>15}")

        # Can we BUILD a classifier?
        # Simple rule: wrong bits have LOW confidence AND HIGH unsat_frac
        threshold_conf = 0.3
        threshold_unsat = 0.05

        predicted_wrong = 0
        true_positives = 0
        for f in wrong_features:
            if f[0] < threshold_conf or f[2] > threshold_unsat:
                predicted_wrong += 1
                true_positives += 1
        for f in right_features:
            if f[0] < threshold_conf or f[2] > threshold_unsat:
                predicted_wrong += 1

        if predicted_wrong > 0:
            precision = true_positives / predicted_wrong
            recall = true_positives / len(wrong_features)
            print(f"\n  Simple classifier (low confidence OR high unsat):")
            print(f"    Precision: {100*precision:.0f}% "
                  f"(of predicted wrong, how many truly wrong)")
            print(f"    Recall:    {100*recall:.0f}% "
                  f"(of truly wrong, how many detected)")
            print(f"    → {'USEFUL' if precision > 0.3 and recall > 0.5 else 'NOT useful enough'}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    experiment_identify()
    experiment_why_hard()
    experiment_predict()
    experiment_crack()
