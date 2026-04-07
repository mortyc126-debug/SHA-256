"""
Solution Sampling — Approximate the marginal distribution WITHOUT solving.

Key insight: marginal MAP = solution 89% of the time.
If we can approximate marginals, we approximate the answer.

Strategy: generate MANY approximate solutions via noisy crystallization,
vote across them. This is "Monte Carlo bit mechanics."

Also: WalkSAT-style local search generates actual solutions.
Use those as samples for marginal estimation.
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


# ============================================================
# METHOD 1: Noisy crystallization sampling
# ============================================================

def noisy_crystallize(clauses, n, noise=0.1):
    """Crystallize with random perturbation in variable ordering."""
    fixed = {}
    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed: break

        # Compute tensions with noise
        candidates = []
        for v in unfixed:
            sigma = bit_tension(clauses, n, v, fixed)
            score = abs(sigma) + random.gauss(0, noise)
            candidates.append((v, sigma, score))

        candidates.sort(key=lambda c: -c[2])
        best_var, best_sigma, _ = candidates[0]

        # Decide value: follow tension with probability proportional to |σ|
        if random.random() < noise:
            val = random.randint(0, 1)
        else:
            val = 1 if best_sigma >= 0 else 0

        fixed[best_var] = val

    return [fixed.get(v, 0) for v in range(n)]


# ============================================================
# METHOD 2: WalkSAT — local search for actual solutions
# ============================================================

def walksat(clauses, n, max_flips=1000, noise_prob=0.3):
    """WalkSAT: start random, flip bits to satisfy clauses."""
    assignment = [random.randint(0, 1) for _ in range(n)]

    for flip in range(max_flips):
        # Find unsatisfied clauses
        unsat = []
        for ci, clause in enumerate(clauses):
            satisfied = False
            for v, s in clause:
                if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                    satisfied = True; break
            if not satisfied:
                unsat.append(ci)

        if not unsat:
            return assignment, True  # Found solution

        # Pick random unsatisfied clause
        ci = random.choice(unsat)
        clause = clauses[ci]

        if random.random() < noise_prob:
            # Random walk: flip random variable in clause
            v, s = random.choice(clause)
            assignment[v] = 1 - assignment[v]
        else:
            # Greedy: flip variable that breaks fewest OTHER clauses
            best_var = None
            best_break = float('inf')
            for v, s in clause:
                # Count how many currently satisfied clauses would break
                assignment[v] = 1 - assignment[v]
                breaks = 0
                for cj, cl in enumerate(clauses):
                    if cj == ci: continue
                    sat = False
                    for vv, ss in cl:
                        if (ss == 1 and assignment[vv] == 1) or (ss == -1 and assignment[vv] == 0):
                            sat = True; break
                    if not sat:
                        breaks += 1
                assignment[v] = 1 - assignment[v]  # flip back

                if breaks < best_break:
                    best_break = breaks
                    best_var = v

            if best_var is not None:
                assignment[best_var] = 1 - assignment[best_var]

    return assignment, False


# ============================================================
# METHOD 3: Sampling + Voting
# ============================================================

def sample_and_vote(clauses, n, n_samples=50, method="walksat"):
    """Generate many solutions/near-solutions, vote per bit."""
    votes = [[0, 0] for _ in range(n)]
    n_solutions_found = 0

    for _ in range(n_samples):
        if method == "walksat":
            assignment, found = walksat(clauses, n, max_flips=500)
            if found:
                n_solutions_found += 1
                for v in range(n):
                    votes[v][assignment[v]] += 1
        elif method == "noisy":
            assignment = noisy_crystallize(clauses, n, noise=0.15)
            sat = evaluate(clauses, assignment)
            # Weight by how many clauses satisfied
            weight = sat / len(clauses)
            for v in range(n):
                votes[v][assignment[v]] += weight

    # Final prediction
    predictions = {}
    confidences = {}
    for v in range(n):
        total = votes[v][0] + votes[v][1]
        if total > 0:
            predictions[v] = 1 if votes[v][1] > votes[v][0] else 0
            confidences[v] = max(votes[v][0], votes[v][1]) / total
        else:
            predictions[v] = 0
            confidences[v] = 0.5

    return predictions, confidences, n_solutions_found


# ============================================================
# COMPARE EVERYTHING
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    print("=" * 70)
    print("SOLUTION SAMPLING: Approximating marginals")
    print("=" * 70)

    for ratio in [3.5, 4.0, 4.27]:
        print(f"\n--- ratio={ratio} ---")

        methods = {
            'tension': {'correct': 0, 'total': 0},
            'v4': {'correct': 0, 'total': 0},
            'walksat_vote(50)': {'correct': 0, 'total': 0, 'solutions': 0, 'instances': 0},
            'walksat_vote(200)': {'correct': 0, 'total': 0, 'solutions': 0, 'instances': 0},
            'noisy_vote(50)': {'correct': 0, 'total': 0},
            'combined': {'correct': 0, 'total': 0},
            'optimal': {'acc_sum': 0.0, 'total': 0},
        }

        for seed in range(150):
            clauses = random_3sat(n, int(ratio*n), seed=seed+6000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            # Tension
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            # V4 (inline)
            v4_tens = {v: bit_tension(clauses, n, v) for v in range(n)}
            for _it in range(10):
                new_t = {}
                for var2 in v4_tens:
                    p1, p0 = 0.0, 0.0
                    for clause in clauses:
                        rem = []; vs2 = None
                        for v, s in clause:
                            rem.append((v,s))
                            if v == var2: vs2 = s
                        if vs2 is None: continue
                        oh = 0.0
                        for v, s in rem:
                            if v == var2: continue
                            t = v4_tens.get(v, 0)
                            p = (1+t)/2 if s == 1 else (1-t)/2
                            oh = 1-(1-oh)*(1-p)
                        need = 1.0-oh
                        if vs2 == 1: p1 += need
                        else: p0 += need
                    tot = p1+p0
                    new_t[var2] = (p1-p0)/tot if tot > 0 else 0
                for v in v4_tens:
                    v4_tens[v] = 0.5*v4_tens[v] + 0.5*new_t.get(v, 0)
            v4_t = v4_tens

            # WalkSAT vote (50 runs)
            ws_pred_50, ws_conf_50, ws_nsol_50 = sample_and_vote(clauses, n, 50, "walksat")
            methods['walksat_vote(50)']['solutions'] += ws_nsol_50
            methods['walksat_vote(50)']['instances'] += 1

            # WalkSAT vote (200 runs)
            ws_pred_200, ws_conf_200, ws_nsol_200 = sample_and_vote(clauses, n, 200, "walksat")
            methods['walksat_vote(200)']['solutions'] += ws_nsol_200
            methods['walksat_vote(200)']['instances'] += 1

            # Noisy crystallization vote
            nc_pred, nc_conf, _ = sample_and_vote(clauses, n, 50, "noisy")

            for var in range(n):
                actual = correct_val[var]
                optimal_acc = max(prob_1[var], 1 - prob_1[var])

                t_pred = 1 if tensions[var] >= 0 else 0
                v4_pred = 1 if v4_t.get(var, 0) >= 0 else 0

                methods['tension']['total'] += 1
                methods['v4']['total'] += 1
                methods['walksat_vote(50)']['total'] += 1
                methods['walksat_vote(200)']['total'] += 1
                methods['noisy_vote(50)']['total'] += 1
                methods['combined']['total'] += 1
                methods['optimal']['total'] += 1

                if t_pred == actual: methods['tension']['correct'] += 1
                if v4_pred == actual: methods['v4']['correct'] += 1
                if ws_pred_50[var] == actual: methods['walksat_vote(50)']['correct'] += 1
                if ws_pred_200[var] == actual: methods['walksat_vote(200)']['correct'] += 1
                if nc_pred[var] == actual: methods['noisy_vote(50)']['correct'] += 1
                methods['optimal']['acc_sum'] += optimal_acc

                # Combined: v4 + walksat voting
                # Use v4 when confident, walksat when v4 is unsure
                v4_conf = abs(v4_t.get(var, 0))
                if v4_conf > 0.3:
                    combo_pred = v4_pred
                elif ws_nsol_200 > 5:
                    combo_pred = ws_pred_200[var]
                else:
                    combo_pred = v4_pred

                if combo_pred == actual: methods['combined']['correct'] += 1

        print(f"\n  {'method':>20} | {'accuracy':>8} | extra")
        print("  " + "-" * 55)
        for name in ['tension', 'v4', 'noisy_vote(50)',
                      'walksat_vote(50)', 'walksat_vote(200)',
                      'combined']:
            m = methods[name]
            acc = m['correct']/m['total']*100 if m['total'] > 0 else 0
            extra = ""
            if 'solutions' in m and m.get('instances', 0) > 0:
                extra = f"avg {m['solutions']/m['instances']:.1f} solutions found"
            if name == 'optimal' and m['total'] > 0:
                acc = m['acc_sum']/m['total']*100
                extra = "(theoretical max)"
                print(f"  {name:>20} | {acc:>7.1f}% | {extra}")
                continue
            print(f"  {name:>20} | {acc:>7.1f}% | {extra}")

    # ---- Does WalkSAT sampling approximate the marginal? ----
    print("\n" + "=" * 70)
    print("How close does WalkSAT sampling get to true marginals?")
    print("=" * 70)

    for seed in range(5):
        clauses = random_3sat(12, int(4.27*12), seed=seed+6000)
        solutions = find_solutions(clauses, 12)
        if not solutions or len(solutions) < 2: continue

        true_prob = [sum(s[v] for s in solutions)/len(solutions) for v in range(12)]

        # Collect WalkSAT solutions
        ws_solutions = []
        for _ in range(500):
            assignment, found = walksat(clauses, 12, max_flips=1000)
            if found:
                ws_solutions.append(assignment)

        if len(ws_solutions) < 5:
            continue

        ws_prob = [sum(s[v] for s in ws_solutions)/len(ws_solutions) for v in range(12)]

        print(f"\n  Instance (seed={seed+6000}, {len(solutions)} true solutions, "
              f"{len(ws_solutions)} WalkSAT solutions):")
        print(f"  {'var':>5} | {'true P(1)':>9} | {'WS P(1)':>9} | {'error':>7}")
        print("  " + "-" * 40)

        total_error = 0
        for v in range(12):
            err = abs(true_prob[v] - ws_prob[v])
            total_error += err
            print(f"  x{v:>2}  | {true_prob[v]:>9.3f} | {ws_prob[v]:>9.3f} | {err:>7.3f}")

        print(f"  Average error: {total_error/12:.3f}")
