"""
SCALING TEST: Does WalkSAT sampling scale?

At n=12: 91% accuracy, ~48 solutions per 50 tries.
Question: what happens at n=20, 30, 50, 100?

If WalkSAT finds solutions in poly(n) flips → approach scales.
If exponential → fundamental barrier remains.
"""

import random
import time
from bit_catalog_static import random_3sat


def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            if (sign == 1 and assignment[var] == 1) or \
               (sign == -1 and assignment[var] == 0):
                sat += 1
                break
    return sat


def walksat(clauses, n, max_flips=None):
    """WalkSAT with configurable max_flips."""
    if max_flips is None:
        max_flips = 10 * n  # default proportional to n

    assignment = [random.randint(0, 1) for _ in range(n)]
    m = len(clauses)

    for flip in range(max_flips):
        # Find unsatisfied clauses
        unsat = []
        for ci in range(m):
            satisfied = False
            for v, s in clauses[ci]:
                if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                    satisfied = True; break
            if not satisfied:
                unsat.append(ci)

        if not unsat:
            return assignment, True, flip

        ci = random.choice(unsat)

        if random.random() < 0.3:
            v, s = random.choice(clauses[ci])
            assignment[v] = 1 - assignment[v]
        else:
            best_var = None
            best_break = float('inf')
            for v, s in clauses[ci]:
                assignment[v] = 1 - assignment[v]
                breaks = 0
                for cj in range(m):
                    sat = False
                    for vv, ss in clauses[cj]:
                        if (ss == 1 and assignment[vv] == 1) or (ss == -1 and assignment[vv] == 0):
                            sat = True; break
                    if not sat:
                        breaks += 1
                assignment[v] = 1 - assignment[v]
                if breaks < best_break:
                    best_break = breaks
                    best_var = v

            if best_var is not None:
                assignment[best_var] = 1 - assignment[best_var]

    return assignment, False, max_flips


def sample_and_vote(clauses, n, n_samples, max_flips_per):
    """Run WalkSAT many times, collect solutions, vote."""
    votes = [[0, 0] for _ in range(n)]
    solutions_found = 0

    for _ in range(n_samples):
        assignment, found, flips = walksat(clauses, n, max_flips_per)
        if found:
            solutions_found += 1
            for v in range(n):
                votes[v][assignment[v]] += 1

    predictions = [1 if votes[v][1] > votes[v][0] else 0 for v in range(n)]
    return predictions, solutions_found


# ============================================================
# TEST 1: WalkSAT success rate vs n
# ============================================================

def test_walksat_scaling():
    print("=" * 70)
    print("TEST 1: WalkSAT success rate vs n (ratio=4.27)")
    print("=" * 70)

    print(f"\n  {'n':>4} | {'flips/try':>9} | {'success%':>8} | "
          f"{'avg_flips':>9} | {'time/try':>8}")
    print("  " + "-" * 55)

    for n in [12, 16, 20, 30, 40, 50, 75, 100]:
        max_flips = 50 * n  # scale flips with n

        successes = 0
        total_flips = 0
        n_tries = 50
        t0 = time.time()

        for seed in range(n_tries):
            random.seed(seed + 10000)
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 10000)
            _, found, flips = walksat(clauses, n, max_flips)
            if found:
                successes += 1
                total_flips += flips

        t1 = time.time()
        avg_flips = total_flips / successes if successes > 0 else max_flips
        time_per = (t1 - t0) / n_tries * 1000

        print(f"  {n:>4} | {max_flips:>9} | {successes/n_tries*100:>7.1f}% | "
              f"{avg_flips:>9.0f} | {time_per:>7.1f}ms")


# ============================================================
# TEST 2: WalkSAT with MORE flips — does it eventually find?
# ============================================================

def test_walksat_with_more_flips():
    print("\n" + "=" * 70)
    print("TEST 2: More flips — can WalkSAT find solutions at larger n?")
    print("=" * 70)

    for n in [20, 30, 50, 75, 100]:
        print(f"\n  n={n}:")
        print(f"  {'max_flips':>12} | {'success%':>8} | {'avg_flips':>9} | {'time':>8}")
        print("  " + "-" * 45)

        for flips_mult in [10, 50, 200, 1000, 5000]:
            max_flips = flips_mult * n
            successes = 0
            total_flips = 0
            n_tries = 30

            t0 = time.time()
            for seed in range(n_tries):
                random.seed(seed + 20000)
                clauses = random_3sat(n, int(4.27 * n), seed=seed + 20000)
                _, found, flips = walksat(clauses, n, max_flips)
                if found:
                    successes += 1
                    total_flips += flips
            t1 = time.time()

            avg_flips = total_flips / successes if successes > 0 else -1
            time_total = (t1 - t0) * 1000

            af_str = f"{avg_flips:>9.0f}" if avg_flips > 0 else "      N/A"
            print(f"  {max_flips:>12} | {successes/n_tries*100:>7.1f}% | "
                  f"{af_str} | {time_total:>7.0f}ms")

            if successes == 0 and flips_mult >= 1000:
                break  # no point trying more


# ============================================================
# TEST 3: Voting accuracy at different n
# ============================================================

def test_voting_accuracy():
    print("\n" + "=" * 70)
    print("TEST 3: Sampling + Voting accuracy vs n")
    print("(Only instances where WalkSAT finds solutions)")
    print("=" * 70)

    print(f"\n  {'n':>4} | {'n_samples':>9} | {'solutions':>9} | "
          f"{'vote_acc':>8} | {'tension_acc':>11} | {'delta':>7}")
    print("  " + "-" * 60)

    for n in [12, 16, 20, 30]:
        n_samples = 100
        max_flips = 200 * n

        total_vote_correct = 0
        total_tension_correct = 0
        total_bits = 0
        total_solutions = 0
        instances_with_solutions = 0

        for seed in range(50):
            random.seed(seed + 30000)
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 30000)

            # Collect WalkSAT solutions
            ws_solutions = []
            for _ in range(n_samples):
                assignment, found, _ = walksat(clauses, n, max_flips)
                if found:
                    ws_solutions.append(list(assignment))

            if len(ws_solutions) < 3:
                continue

            instances_with_solutions += 1
            total_solutions += len(ws_solutions)

            # Vote
            vote_pred = []
            for v in range(n):
                ones = sum(s[v] for s in ws_solutions)
                vote_pred.append(1 if ones > len(ws_solutions) / 2 else 0)

            # Tension prediction
            tension_pred = []
            for v in range(n):
                sigma = 0
                p1, p0 = 0.0, 0.0
                for clause in clauses:
                    for vv, s in clause:
                        if vv == v:
                            if s == 1: p1 += 1.0/3
                            else: p0 += 1.0/3
                total = p1 + p0
                sigma = (p1 - p0) / total if total > 0 else 0
                tension_pred.append(1 if sigma >= 0 else 0)

            # Check against WalkSAT majority (as proxy for ground truth)
            # This measures CONSISTENCY, not absolute accuracy
            # (we can't compute true solutions for n>16)
            vote_assignment = vote_pred
            tension_assignment = tension_pred

            vote_sat = evaluate(clauses, vote_assignment)
            tension_sat = evaluate(clauses, tension_assignment)

            total_vote_correct += vote_sat
            total_tension_correct += tension_sat
            total_bits += len(clauses)

        avg_sol = total_solutions / instances_with_solutions if instances_with_solutions > 0 else 0
        vote_frac = total_vote_correct / total_bits if total_bits > 0 else 0
        tension_frac = total_tension_correct / total_bits if total_bits > 0 else 0

        print(f"  {n:>4} | {n_samples:>9} | {avg_sol:>9.1f} | "
              f"{vote_frac*100:>7.1f}% | {tension_frac*100:>10.1f}% | "
              f"{(vote_frac-tension_frac)*100:>+6.1f}%")


# ============================================================
# TEST 4: Does vote-assignment SOLVE the instance?
# ============================================================

def test_vote_as_solver():
    print("\n" + "=" * 70)
    print("TEST 4: Does the vote-majority assignment solve the instance?")
    print("=" * 70)

    print(f"\n  {'n':>4} | {'n_samples':>9} | {'instances':>9} | "
          f"{'vote_solves':>11} | {'tension_solves':>14}")
    print("  " + "-" * 65)

    for n in [12, 16, 20, 30, 50]:
        n_samples = min(200, max(50, 500000 // (n * int(4.27 * n))))
        max_flips = 200 * n

        vote_solves = 0
        tension_solves = 0
        instances_tested = 0

        for seed in range(30):
            random.seed(seed + 40000)
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 40000)
            m = len(clauses)

            # Collect solutions
            ws_solutions = []
            for _ in range(n_samples):
                assignment, found, _ = walksat(clauses, n, max_flips)
                if found:
                    ws_solutions.append(list(assignment))

            if len(ws_solutions) < 2:
                continue

            instances_tested += 1

            # Vote prediction
            vote_assignment = []
            for v in range(n):
                ones = sum(s[v] for s in ws_solutions)
                vote_assignment.append(1 if ones > len(ws_solutions) / 2 else 0)

            if evaluate(clauses, vote_assignment) == m:
                vote_solves += 1

            # Tension prediction
            t_assignment = []
            for v in range(n):
                p1, p0 = 0.0, 0.0
                for clause in clauses:
                    for vv, s in clause:
                        if vv == v:
                            if s == 1: p1 += 1
                            else: p0 += 1
                t_assignment.append(1 if p1 >= p0 else 0)

            if evaluate(clauses, t_assignment) == m:
                tension_solves += 1

        if instances_tested > 0:
            print(f"  {n:>4} | {n_samples:>9} | {instances_tested:>9} | "
                  f"{vote_solves}/{instances_tested} "
                  f"({vote_solves/instances_tested*100:>5.1f}%) | "
                  f"{tension_solves}/{instances_tested} "
                  f"({tension_solves/instances_tested*100:>5.1f}%)")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    test_walksat_scaling()
    test_walksat_with_more_flips()
    test_voting_accuracy()
    test_vote_as_solver()
