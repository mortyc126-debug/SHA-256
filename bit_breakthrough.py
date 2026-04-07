"""
Breaking the 70% barrier — Can we start the cascade without an oracle?

If we can get FIRST FEW bits right with >90% accuracy,
the amplification effect should do the rest.

Strategies to try:
1. Multi-signal voting: combine ALL properties we discovered
2. Contradiction detection: bits with contradictory paths → mark as unreliable
3. Bootstrap: fix confident bits, re-evaluate, fix more, re-evaluate
4. Ensemble: try many random starting points, vote on each bit
5. Backtrack on poison detection: if fixing a bit increases frustration, undo it
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
    if fixed is None:
        fixed = {}
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
    return (p1 - p0) / total if total > 0 else 0.0


def field_temperature(clauses, n, fixed):
    frustrations = []
    for var in range(n):
        if var in fixed:
            continue
        sigma = bit_tension(clauses, n, var, fixed)
        frustrations.append(1.0 - abs(sigma))
    return sum(frustrations) / len(frustrations) if frustrations else 0.0


# ============================================================
# STRATEGY 1: Multi-signal score
# ============================================================

def multi_signal_score(clauses, n, var, fixed=None):
    """
    Combine: |σ|, minority_ratio, neighbor_agreement
    into a single confidence score.
    """
    if fixed is None:
        fixed = {}

    sigma = bit_tension(clauses, n, var, fixed)

    # Minority ratio
    pos = 0
    neg = 0
    for clause in clauses:
        already_sat = False
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
        if already_sat:
            continue
        for v, s in clause:
            if v == var:
                if s == 1:
                    pos += 1
                else:
                    neg += 1

    total = pos + neg
    if total > 0:
        minority_ratio = min(pos, neg) / max(pos, neg) if max(pos, neg) > 0 else 1.0
    else:
        minority_ratio = 1.0

    # Neighbor agreement
    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var and v not in fixed:
                    neighbors.add(v)

    if neighbors:
        same = sum(1 for nb in neighbors
                   if bit_tension(clauses, n, nb, fixed) * sigma > 0)
        agreement = same / len(neighbors)
    else:
        agreement = 0.5

    # Combined confidence: high |σ|, low minority_ratio, high agreement
    confidence = abs(sigma) * (1 - minority_ratio) * (0.5 + agreement)

    return sigma, confidence


# ============================================================
# STRATEGY 2: Contradiction detection
# ============================================================

def contradiction_score(clauses, n, var, fixed=None):
    """
    Check: do different paths give the same signal for this bit?
    Fix each neighbor independently and see if they agree about var.
    """
    if fixed is None:
        fixed = {}

    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var and v not in fixed:
                    neighbors.add(v)

    if not neighbors:
        return 0.0, bit_tension(clauses, n, var, fixed)

    signals = []
    for nb in neighbors:
        nb_sigma = bit_tension(clauses, n, nb, fixed)
        nb_val = 1 if nb_sigma >= 0 else 0
        test_fixed = dict(fixed)
        test_fixed[nb] = nb_val
        var_sigma = bit_tension(clauses, n, var, test_fixed)
        signals.append(var_sigma)

    # Are signals consistent?
    if not signals:
        return 0.0, bit_tension(clauses, n, var, fixed)

    mean_signal = sum(signals) / len(signals)
    # Consistency = 1 - variance/max_variance
    variance = sum((s - mean_signal)**2 for s in signals) / len(signals)
    max_var = 1.0  # maximum possible variance for signals in [-1,1]
    consistency = 1.0 - min(variance / max_var, 1.0)

    return consistency, mean_signal


# ============================================================
# STRATEGY 3: Bootstrap with temperature monitoring
# ============================================================

def bootstrap_solve(clauses, n):
    """
    1. Only fix bits with confidence > threshold
    2. After each fix, re-evaluate everything
    3. If temperature RISES after a fix, UNDO it (poison detected)
    4. Gradually lower threshold
    """
    fixed = {}
    undone = set()  # bits we tried and undid

    for threshold in [0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]:
        changed = True
        while changed:
            changed = False
            T_before = field_temperature(clauses, n, fixed)

            candidates = []
            for var in range(n):
                if var in fixed or var in undone:
                    continue
                sigma = bit_tension(clauses, n, var, fixed)
                if abs(sigma) >= threshold:
                    candidates.append((var, sigma))

            # Sort by confidence
            candidates.sort(key=lambda c: -abs(c[1]))

            for var, sigma in candidates:
                if var in fixed:
                    continue

                val = 1 if sigma >= 0 else 0
                fixed[var] = val

                # Check: did temperature rise?
                T_after = field_temperature(clauses, n, fixed)

                if T_after > T_before + 0.05:  # temperature rose = possible poison
                    del fixed[var]
                    undone.add(var)
                else:
                    T_before = T_after
                    changed = True

    # Fix remaining bits by tension (no choice left)
    for var in range(n):
        if var not in fixed:
            sigma = bit_tension(clauses, n, var, fixed)
            fixed[var] = 1 if sigma >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# STRATEGY 4: Ensemble voting
# ============================================================

def ensemble_solve(clauses, n, n_runs=20):
    """
    Run crystallization many times with slight randomization.
    For each bit, VOTE across all runs.
    """
    votes = [[0, 0] for _ in range(n)]  # votes[var] = [count_0, count_1]

    for run in range(n_runs):
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed:
                break

            candidates = []
            for var in unfixed:
                sigma = bit_tension(clauses, n, var, fixed)
                # Add small noise for diversity
                noise = random.gauss(0, 0.05)
                candidates.append((var, sigma, abs(sigma) + noise))

            candidates.sort(key=lambda c: -c[2])
            best_var, best_sigma, _ = candidates[0]
            best_val = 1 if best_sigma >= 0 else 0
            fixed[best_var] = best_val

        for var in range(n):
            val = fixed.get(var, 0)
            votes[var][val] += 1

    # Final assignment by majority vote
    assignment = [0 if votes[v][0] > votes[v][1] else 1 for v in range(n)]

    # Also compute confidence
    confidences = []
    for v in range(n):
        total = votes[v][0] + votes[v][1]
        conf = max(votes[v][0], votes[v][1]) / total if total > 0 else 0.5
        confidences.append(conf)

    return assignment, evaluate(clauses, assignment) == len(clauses), confidences


# ============================================================
# STRATEGY 5: Smart backtrack
# ============================================================

def smart_backtrack_solve(clauses, n, max_backtracks=3):
    """
    Crystallize, but if we hit a dead clause, backtrack the MOST RECENT
    low-confidence fix (not just the last fix).
    """
    fixed = {}
    history = []  # (var, val, confidence)

    for step in range(n + max_backtracks * n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        # Check for dead clauses
        dead = False
        for clause in clauses:
            satisfied = False
            has_free = False
            for v, s in clause:
                if v in fixed:
                    if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                        satisfied = True
                        break
                else:
                    has_free = True
            if not satisfied and not has_free:
                dead = True
                break

        if dead and history:
            # Backtrack: find least confident fix and flip it
            history.sort(key=lambda h: h[2])
            worst = history[0]
            del fixed[worst[0]]
            fixed[worst[0]] = 1 - worst[1]
            history.remove(worst)
            # Mark with high confidence so we don't undo it again
            history.append((worst[0], 1 - worst[1], 999))
            continue

        # Normal crystallization
        candidates = []
        for var in unfixed:
            sigma = bit_tension(clauses, n, var, fixed)
            candidates.append((var, sigma))

        candidates.sort(key=lambda c: -abs(c[1]))
        best_var, best_sigma = candidates[0]
        best_val = 1 if best_sigma >= 0 else 0

        fixed[best_var] = best_val
        history.append((best_var, best_val, abs(best_sigma)))

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# STRATEGY 6: Multi-signal crystallization
# ============================================================

def multi_signal_solve(clauses, n):
    """Use multi_signal_score + contradiction detection for ordering."""
    fixed = {}

    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        candidates = []
        for var in unfixed:
            sigma, confidence = multi_signal_score(clauses, n, var, fixed)
            consistency, mean_sig = contradiction_score(clauses, n, var, fixed)

            # Combined score: confidence * consistency
            combined = confidence * consistency
            # Direction: use mean_sig if more consistent, sigma otherwise
            if consistency > 0.7:
                direction = mean_sig
            else:
                direction = sigma

            candidates.append((var, direction, combined))

        candidates.sort(key=lambda c: -c[2])
        best_var, best_dir, _ = candidates[0]
        fixed[best_var] = 1 if best_dir >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    return assignment, evaluate(clauses, assignment) == len(clauses)


# ============================================================
# MAIN COMPARISON
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("BREAKING THE 70% BARRIER")
    print("Comparing all strategies for solving SAT")
    print("=" * 70)

    strategies = {
        'baseline (max |σ|)': lambda c, n: crystallize_baseline(c, n),
        'multi-signal': lambda c, n: multi_signal_solve(c, n),
        'bootstrap+T-monitor': lambda c, n: bootstrap_solve(c, n),
        'ensemble (20 runs)': lambda c, n: ensemble_solve(c, n)[:2],
        'smart backtrack (3)': lambda c, n: smart_backtrack_solve(c, n, 3),
        'smart backtrack (10)': lambda c, n: smart_backtrack_solve(c, n, 10),
    }

    def crystallize_baseline(clauses, n):
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed:
                break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            sigma = bit_tension(clauses, n, best, fixed)
            fixed[best] = 1 if sigma >= 0 else 0
        assignment = [fixed.get(v, 0) for v in range(n)]
        return assignment, evaluate(clauses, assignment) == len(clauses)

    for ratio in [3.5, 4.0, 4.27]:
        print(f"\n--- ratio = {ratio} ---")
        results = {name: 0 for name in strategies}
        total = 0

        for seed in range(200):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue
            total += 1

            for name, solver in strategies.items():
                _, success = solver(clauses, 12)
                if success:
                    results[name] += 1

        print(f"  {total} satisfiable instances")
        print(f"\n  {'strategy':>25} | {'solved':>8} | {'rate':>8}")
        print("  " + "-" * 50)
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            r = results[name]
            pct = r / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"  {name:>25} | {r:>8} | {pct:>6.1f}% {bar}")

    # ---- How does ensemble voting accuracy look? ----
    print("\n" + "=" * 70)
    print("ENSEMBLE: Per-bit voting accuracy")
    print("=" * 70)

    for ratio in [4.27]:
        high_conf_correct = 0
        high_conf_total = 0
        low_conf_correct = 0
        low_conf_total = 0

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(12)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            assignment, _, confidences = ensemble_solve(clauses, 12, n_runs=30)

            for v in range(12):
                is_correct = assignment[v] == correct_val[v]
                if confidences[v] > 0.8:
                    high_conf_total += 1
                    if is_correct:
                        high_conf_correct += 1
                else:
                    low_conf_total += 1
                    if is_correct:
                        low_conf_correct += 1

        print(f"\n  ratio={ratio}:")
        if high_conf_total > 0:
            print(f"    High confidence (>80% vote): "
                  f"{high_conf_correct}/{high_conf_total} = "
                  f"{high_conf_correct/high_conf_total*100:.1f}%")
        if low_conf_total > 0:
            print(f"    Low confidence  (<80% vote): "
                  f"{low_conf_correct}/{low_conf_total} = "
                  f"{low_conf_correct/low_conf_total*100:.1f}%")

    # ---- Scale test ----
    print("\n" + "=" * 70)
    print("SCALE TEST: Best strategies at different n")
    print("=" * 70)

    for n in [10, 12, 14, 16]:
        total = 0
        results = {'baseline': 0, 'bootstrap': 0, 'ensemble': 0, 'backtrack10': 0}

        for seed in range(200):
            clauses = random_3sat(n, int(4.27 * n), seed=seed)
            if n <= 14:
                solutions = find_solutions(clauses, n)
                if not solutions:
                    continue
            else:
                # Can't check solutions for n=16, just test if solver finds one
                pass

            total += 1

            _, s1 = crystallize_baseline(clauses, n)
            if s1: results['baseline'] += 1

            _, s2 = bootstrap_solve(clauses, n)
            if s2: results['bootstrap'] += 1

            a3, s3 = ensemble_solve(clauses, n, n_runs=20)[:2]
            if s3: results['ensemble'] += 1

            _, s4 = smart_backtrack_solve(clauses, n, 10)
            if s4: results['backtrack10'] += 1

        if total > 0:
            print(f"\n  n={n} ({total} instances):")
            for name in sorted(results.keys(), key=lambda k: -results[k]):
                pct = results[name] / total * 100
                print(f"    {name:>15}: {results[name]:>4}/{total} ({pct:.1f}%)")
