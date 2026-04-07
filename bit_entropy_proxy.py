"""
ENTROPY PROXY: Can we estimate solution survival WITHOUT knowing solutions?

Entropy gradient is the strongest signal (2.2× → 61×).
But requires counting solutions.

Proxies to test:
1. Unit propagation count after each fix (more UP = more structure = more solutions?)
2. Number of satisfied clauses (trivial but maybe correlated)
3. Average |σ| increase after fix (more confident remaining = more alive)
4. Number of DEAD clauses after fix (0 free literals = solution killed)
5. Counterfactual branching factor: how many bits become forced?
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


def count_up(clauses, n, fixed):
    """Count how many bits get forced by unit propagation."""
    f = dict(fixed)
    forced = 0
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            satisfied = False; free = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                        satisfied = True; break
                else: free.append((v,s))
            if not satisfied and len(free) == 1:
                v, s = free[0]
                if v not in f:
                    f[v] = 1 if s==1 else 0
                    forced += 1; changed = True
    return forced, f


def count_dead(clauses, n, fixed):
    """Count clauses with 0 free literals and not satisfied = DEAD."""
    dead = 0
    for clause in clauses:
        satisfied = False; free = 0
        for v, s in clause:
            if v in fixed:
                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                    satisfied = True; break
            else: free += 1
        if not satisfied and free == 0:
            dead += 1
    return dead


# ============================================================
# Test ALL proxies against real entropy
# ============================================================

def test_proxies():
    print("=" * 70)
    print("ENTROPY PROXIES: What predicts solution survival?")
    print("=" * 70)

    random.seed(42); n = 12

    # Collect: for each (instance, first_fix), measure proxy AND real entropy
    data = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # For each possible first fix:
        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            val = 1 if sigma >= 0 else 0  # tension-guided value

            fixed = {var: val}

            # Real entropy: count surviving solutions
            surviving = sum(1 for s in solutions if s[var] == val)
            entropy = surviving / len(solutions)  # fraction surviving

            # Proxy 1: UP count
            up_count, _ = count_up(clauses, n, fixed)

            # Proxy 2: satisfied clauses
            assignment = [0]*n
            assignment[var] = val
            sat_count = evaluate(clauses, assignment)

            # Proxy 3: avg |σ| of remaining bits
            remaining_sigma = []
            for v in range(n):
                if v == var: continue
                remaining_sigma.append(abs(bit_tension(clauses, n, v, fixed)))
            avg_sigma = sum(remaining_sigma)/len(remaining_sigma) if remaining_sigma else 0

            # Proxy 4: dead clauses
            dead = count_dead(clauses, n, fixed)

            # Proxy 5: total bits forced (UP + original)
            _, full_fixed = count_up(clauses, n, fixed)
            total_forced = len(full_fixed)

            data.append({
                'entropy': entropy,
                'up_count': up_count,
                'sat_count': sat_count,
                'avg_sigma': avg_sigma,
                'dead': dead,
                'total_forced': total_forced,
                'abs_sigma_self': abs(sigma),
                'is_correct': val == correct_val[var],
            })

    # Compute correlations
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    entropies = [d['entropy'] for d in data]
    me = mean(entropies)
    se = math.sqrt(sum((e-me)**2 for e in entropies)/len(entropies))

    print(f"\n  {'proxy':>15} | {'corr w/ entropy':>15} | {'mean':>8}")
    print("  " + "-" * 45)

    for proxy_name in ['up_count', 'avg_sigma', 'dead', 'total_forced', 'abs_sigma_self']:
        vals = [d[proxy_name] for d in data]
        mv = mean(vals)
        sv = math.sqrt(sum((v-mv)**2 for v in vals)/len(vals))
        if se > 0 and sv > 0:
            cov = sum((entropies[i]-me)*(vals[i]-mv) for i in range(len(data)))/len(data)
            corr = cov/(se*sv)
        else:
            corr = 0
        print(f"  {proxy_name:>15} | {corr:>+15.4f} | {mv:>8.3f}")


# ============================================================
# Use BEST proxy as solver signal
# ============================================================

def proxy_solver():
    """
    For each uncertain bit: fix both ways, measure proxy.
    Pick the value with better proxy score.
    """
    print("\n" + "=" * 70)
    print("PROXY SOLVER: Use entropy proxy for uncertain bits")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'proxy_up': 0, 'proxy_dead': 0,
               'proxy_sigma': 0, 'proxy_combined': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Proxy-guided solvers
        for proxy_name, proxy_fn in [
            ('proxy_up', lambda c, nn, f: count_up(c, nn, f)[0]),
            ('proxy_dead', lambda c, nn, f: -count_dead(c, nn, f)),
            ('proxy_sigma', lambda c, nn, f: sum(abs(bit_tension(c, nn, v, f))
                                                 for v in range(nn) if v not in f)),
            ('proxy_combined', lambda c, nn, f: count_up(c, nn, f)[0] * 10
                                                - count_dead(c, nn, f) * 100
                                                + sum(abs(bit_tension(c, nn, v, f))
                                                     for v in range(nn) if v not in f)),
        ]:
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break

                best_var = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                sigma = bit_tension(clauses, n, best_var, fixed)

                if abs(sigma) > 0.3:
                    # Confident: use tension
                    fixed[best_var] = 1 if sigma >= 0 else 0
                else:
                    # Uncertain: try both, pick by proxy
                    scores = {}
                    for val in [0, 1]:
                        test_fixed = dict(fixed)
                        test_fixed[best_var] = val
                        scores[val] = proxy_fn(clauses, n, test_fixed)
                    fixed[best_var] = 1 if scores[1] >= scores[0] else 0

                # Unit propagation
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

            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                results[proxy_name] += 1

    t = results['total']
    print(f"\n  {'solver':>15} | {'solved':>8} | {'rate':>8} | {'delta':>8}")
    print("  " + "-" * 45)
    base = results['standard']/t*100
    for name in ['standard', 'proxy_up', 'proxy_dead', 'proxy_sigma', 'proxy_combined']:
        pct = results[name]/t*100
        print(f"  {name:>15} | {results[name]:>4}/{t} | {pct:>6.1f}% | {pct-base:>+6.1f}%")


# ============================================================
# LOOKAHEAD: for EVERY bit, evaluate BOTH directions by proxy
# ============================================================

def full_lookahead():
    """
    Not just uncertain bits — for EVERY bit at each step:
    try both values, evaluate by proxy, pick best.

    This is expensive (O(n²)) but might break through.
    """
    print("\n" + "=" * 70)
    print("FULL LOOKAHEAD SOLVER: Every bit, both directions")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'full_lookahead': 0, 'total': 0}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Full lookahead: for each unfixed bit, try both, score by UP+dead+sigma
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break

            best_var = None; best_val = None; best_score = -1e9

            for var in unfixed:
                for val in [0, 1]:
                    tf = dict(fixed); tf[var] = val
                    up, full_f = count_up(clauses, n, tf)
                    dead = count_dead(clauses, n, full_f)
                    if dead > 0:
                        score = -1e6  # dead clause = catastrophe
                    else:
                        # Score: UP propagations + remaining confidence
                        remaining = [v for v in range(n) if v not in full_f]
                        avg_s = sum(abs(bit_tension(clauses, n, v, full_f))
                                   for v in remaining) / max(1, len(remaining))
                        score = up * 2 + avg_s + len(full_f) * 0.1

                    if score > best_score:
                        best_score = score
                        best_var = var
                        best_val = val

            if best_var is not None:
                fixed[best_var] = best_val
                # UP
                _, fixed = count_up(clauses, n, fixed)

        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['full_lookahead'] += 1

    t = results['total']
    std = results['standard']/t*100
    fl = results['full_lookahead']/t*100
    print(f"\n  Standard:       {results['standard']}/{t} ({std:.1f}%)")
    print(f"  Full lookahead: {results['full_lookahead']}/{t} ({fl:.1f}%)")
    print(f"  Improvement:    {fl-std:+.1f}%")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    test_proxies()
    proxy_solver()
    full_lookahead()
