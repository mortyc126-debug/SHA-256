"""
Fog Clearing — Does fixing correct bits improve signal for neighbors?

The user's insight: "I can try to clear the fog using neighboring bits,
like not walking blind but talking to each other."

Key question: when I fix a CORRECT bit, does ε increase for its neighbors?
If yes → iterative amplification → maybe polynomial
If no → fog is structural → exponential barrier
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


# ============================================================
# EXPERIMENT 1: Does fixing correct bits amplify signal?
# ============================================================

def iterative_amplification(clauses, n, solutions):
    """
    1. Measure ε for all bits (baseline)
    2. Fix the CORRECT value of most confident bit
    3. Re-measure ε for remaining bits
    4. Repeat

    Track: does ε grow, stay flat, or shrink?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    fixed = {}
    trace = []

    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        # Measure accuracy and ε for unfixed bits
        correct_count = 0
        total_count = 0
        epsilons = []

        for var in unfixed:
            sigma = bit_tension(clauses, n, var, fixed)
            predicted = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            if predicted == actual:
                correct_count += 1
            total_count += 1

            # ε for this bit
            pos = 0
            neg = 0
            for clause in clauses:
                # Check if clause still active
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

            total_app = pos + neg
            if total_app > 0:
                if actual == 1:
                    epsilons.append(pos / total_app - 0.5)
                else:
                    epsilons.append(neg / total_app - 0.5)

        accuracy = correct_count / total_count if total_count > 0 else 0
        avg_epsilon = sum(epsilons) / len(epsilons) if epsilons else 0

        trace.append({
            'step': step,
            'n_unfixed': len(unfixed),
            'accuracy': accuracy,
            'epsilon': avg_epsilon,
            'abs_sigma_avg': sum(abs(bit_tension(clauses, n, v, fixed))
                                 for v in unfixed) / len(unfixed),
        })

        # Fix the most confident bit WITH CORRECT VALUE (oracle)
        best_var = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        fixed[best_var] = correct_val[best_var]

    return trace


# ============================================================
# EXPERIMENT 2: Oracle vs greedy — does knowing the answer help?
# ============================================================

def oracle_vs_greedy(clauses, n, solutions):
    """
    Compare:
    A) Fix bits in order of confidence, using CORRECT values (oracle)
    B) Fix bits in order of confidence, using TENSION-predicted values (greedy)

    How fast does accuracy diverge?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    oracle_trace = []
    greedy_trace = []

    fixed_oracle = {}
    fixed_greedy = {}

    for step in range(n):
        unfixed_o = [v for v in range(n) if v not in fixed_oracle]
        unfixed_g = [v for v in range(n) if v not in fixed_greedy]

        if not unfixed_o or not unfixed_g:
            break

        # Oracle accuracy
        o_correct = sum(1 for v in unfixed_o
                        if (1 if bit_tension(clauses, n, v, fixed_oracle) >= 0 else 0) == correct_val[v])
        o_acc = o_correct / len(unfixed_o)

        # Greedy accuracy
        g_correct = sum(1 for v in unfixed_g
                        if (1 if bit_tension(clauses, n, v, fixed_greedy) >= 0 else 0) == correct_val[v])
        g_acc = g_correct / len(unfixed_g)

        oracle_trace.append({'step': step, 'accuracy': o_acc, 'n': len(unfixed_o)})
        greedy_trace.append({'step': step, 'accuracy': g_acc, 'n': len(unfixed_g)})

        # Oracle: fix most confident with CORRECT value
        best_o = max(unfixed_o, key=lambda v: abs(bit_tension(clauses, n, v, fixed_oracle)))
        fixed_oracle[best_o] = correct_val[best_o]

        # Greedy: fix most confident with PREDICTED value
        best_g = max(unfixed_g, key=lambda v: abs(bit_tension(clauses, n, v, fixed_greedy)))
        sigma_g = bit_tension(clauses, n, best_g, fixed_greedy)
        fixed_greedy[best_g] = 1 if sigma_g >= 0 else 0

    return oracle_trace, greedy_trace


# ============================================================
# EXPERIMENT 3: How many correct fixes needed to clear the fog?
# ============================================================

def fog_threshold(clauses, n, solutions):
    """
    Fix 1, 2, 3, ... correct bits. At what point does accuracy
    for remaining bits jump above 90%? 95%?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    fixed = {}
    # Sort by confidence
    order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

    results = []
    for k in range(n):
        # Fix k-th most confident bit correctly
        var = order[k]
        fixed[var] = correct_val[var]

        # Measure accuracy of remaining
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        correct = 0
        for v in unfixed:
            sigma = bit_tension(clauses, n, v, fixed)
            pred = 1 if sigma >= 0 else 0
            if pred == correct_val[v]:
                correct += 1

        acc = correct / len(unfixed)
        results.append({
            'k_fixed': k + 1,
            'n_remaining': len(unfixed),
            'accuracy': acc,
        })

    return results


# ============================================================
# EXPERIMENT 4: Wrong fix POISON — does one mistake ruin everything?
# ============================================================

def poison_test(clauses, n, solutions):
    """
    Fix k correct bits, then fix 1 WRONG bit.
    How much does accuracy drop?
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

    results = []

    for poison_after in [0, 2, 4, 6, 8]:
        if poison_after >= n - 2:
            continue

        fixed = {}
        # Fix correct bits
        for k in range(min(poison_after, len(order))):
            fixed[order[k]] = correct_val[order[k]]

        # Accuracy before poison
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            continue
        acc_before = sum(1 for v in unfixed
                         if (1 if bit_tension(clauses, n, v, fixed) >= 0 else 0) == correct_val[v]) / len(unfixed)

        # Add ONE wrong bit
        # Pick the next most confident unfixed bit, set it WRONG
        remaining_by_conf = sorted(unfixed, key=lambda v: -abs(bit_tension(clauses, n, v, fixed)))
        poison_var = remaining_by_conf[0]
        fixed[poison_var] = 1 - correct_val[poison_var]  # WRONG value

        # Accuracy after poison
        unfixed2 = [v for v in range(n) if v not in fixed]
        if not unfixed2:
            continue
        acc_after = sum(1 for v in unfixed2
                        if (1 if bit_tension(clauses, n, v, fixed) >= 0 else 0) == correct_val[v]) / len(unfixed2)

        results.append({
            'correct_fixed': poison_after,
            'acc_before': acc_before,
            'acc_after': acc_after,
            'drop': acc_before - acc_after,
        })

    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    # ---- Experiment 1 ----
    print("=" * 70)
    print("EXPERIMENT 1: Does fixing correct bits amplify signal?")
    print("ε and accuracy after each correct fixation (ORACLE)")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        avg_traces = {}

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            trace = iterative_amplification(clauses, 12, solutions)
            if trace:
                for t in trace:
                    s = t['step']
                    if s not in avg_traces:
                        avg_traces[s] = {'acc': [], 'eps': [], 'sigma': []}
                    avg_traces[s]['acc'].append(t['accuracy'])
                    avg_traces[s]['eps'].append(t['epsilon'])
                    avg_traces[s]['sigma'].append(t['abs_sigma_avg'])

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}:")
        print(f"  {'step':>4} | {'ε':>8} | {'accuracy':>8} | {'<|σ|>':>8} | ε trend")
        print("  " + "-" * 55)

        prev_eps = None
        for step in sorted(avg_traces.keys()):
            eps = mean(avg_traces[step]['eps'])
            acc = mean(avg_traces[step]['acc'])
            sig = mean(avg_traces[step]['sigma'])

            if prev_eps is not None:
                trend = "↑" if eps > prev_eps + 0.005 else ("↓" if eps < prev_eps - 0.005 else "→")
            else:
                trend = " "
            prev_eps = eps

            bar = "█" * int(eps * 100)
            print(f"  {step:>4} | {eps:>+8.4f} | {acc*100:>7.1f}% | "
                  f"{sig:>8.3f} | {trend} {bar}")

    # ---- Experiment 2 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Oracle vs Greedy — fog clearing comparison")
    print("=" * 70)

    for ratio, label in [(4.27, "HARD")]:
        oracle_avg = {}
        greedy_avg = {}

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            result = oracle_vs_greedy(clauses, 12, solutions)
            if result:
                o_trace, g_trace = result
                for t in o_trace:
                    s = t['step']
                    if s not in oracle_avg:
                        oracle_avg[s] = []
                    oracle_avg[s].append(t['accuracy'])
                for t in g_trace:
                    s = t['step']
                    if s not in greedy_avg:
                        greedy_avg[s] = []
                    greedy_avg[s].append(t['accuracy'])

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}:")
        print(f"  {'step':>4} | {'oracle':>8} | {'greedy':>8} | {'gap':>8} | visual")
        print("  " + "-" * 55)
        for step in sorted(oracle_avg.keys()):
            o = mean(oracle_avg[step])
            g = mean(greedy_avg.get(step, [0]))
            gap = o - g
            bar_o = "O" * int(o * 20)
            bar_g = "G" * int(g * 20)
            print(f"  {step:>4} | {o*100:>7.1f}% | {g*100:>7.1f}% | "
                  f"{gap*100:>+7.1f}% | {bar_o}")
            if gap > 0.02:
                print(f"       |          |          |          | {bar_g}")

    # ---- Experiment 3 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: How many correct fixes to clear the fog?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        avg_results = {}

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            results = fog_threshold(clauses, 12, solutions)
            if results:
                for r in results:
                    k = r['k_fixed']
                    if k not in avg_results:
                        avg_results[k] = []
                    avg_results[k].append(r['accuracy'])

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}: accuracy of remaining bits after k correct fixes:")
        print(f"  {'k fixed':>7} | {'accuracy':>8} | {'remaining':>9} | visual")
        print("  " + "-" * 50)
        for k in sorted(avg_results.keys()):
            acc = mean(avg_results[k])
            remaining = 12 - k
            bar = "█" * int(acc * 30) + "░" * int((1-acc) * 30)
            marker = " ← 90%" if abs(acc - 0.9) < 0.03 else (" ← 95%" if abs(acc - 0.95) < 0.03 else "")
            print(f"  {k:>7} | {acc*100:>7.1f}% | {remaining:>9} | {bar}{marker}")

    # ---- Experiment 4 ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Poison — one wrong fix ruins how much?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        avg_results = {}

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            results = poison_test(clauses, 12, solutions)
            if results:
                for r in results:
                    k = r['correct_fixed']
                    if k not in avg_results:
                        avg_results[k] = {'before': [], 'after': [], 'drop': []}
                    avg_results[k]['before'].append(r['acc_before'])
                    avg_results[k]['after'].append(r['acc_after'])
                    avg_results[k]['drop'].append(r['drop'])

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}: effect of 1 wrong fix after k correct fixes:")
        print(f"  {'k correct':>9} | {'before':>8} | {'after':>8} | {'damage':>8}")
        print("  " + "-" * 45)
        for k in sorted(avg_results.keys()):
            before = mean(avg_results[k]['before'])
            after = mean(avg_results[k]['after'])
            drop = mean(avg_results[k]['drop'])
            print(f"  {k:>9} | {before*100:>7.1f}% | {after*100:>7.1f}% | "
                  f"{drop*100:>+7.1f}%")
