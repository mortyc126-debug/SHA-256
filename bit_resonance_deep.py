"""
RESONANCE DEEP DIVE

Resonance = what neighbors imply about me through shared clauses.
It rescues 40% of σ's errors. WHY?

1. WHEN does resonance rescue? (which bits, what properties)
2. Can we ITERATE resonance like v4?
3. Resonance + v4 + clone = ?
4. Does resonance see the ATTRACTION FIELD we discovered?
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


def resonance(clauses, n, var, tensions):
    """Resonance: what neighbors imply about var through clauses."""
    votes = []
    for clause in clauses:
        signs = {v: s for v, s in clause}
        if var not in signs: continue
        for v, s in clause:
            if v == var: continue
            nb_dir = 1 if tensions[v] >= 0 else -1
            nb_satisfies = (s == 1 and nb_dir == 1) or (s == -1 and nb_dir == -1)
            if nb_satisfies:
                votes.append(0)  # clause helped by neighbor, no pressure on us
            else:
                votes.append(signs[var])  # clause needs US
    if not votes: return 0
    return sum(votes) / len(votes)


# ============================================================
# 1. WHEN does resonance rescue σ?
# ============================================================

def when_resonance_rescues():
    print("=" * 70)
    print("1. WHEN does resonance rescue wrong-σ bits?")
    print("=" * 70)

    random.seed(42); n = 12

    rescued_props = []    # properties of bits resonance saves
    not_rescued_props = []  # properties of bits resonance can't save

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            sigma = tensions[var]
            pred_sigma = 1 if sigma >= 0 else 0
            actual = correct_val[var]
            if pred_sigma == actual: continue  # σ correct, skip

            # Resonance prediction
            res = resonance(clauses, n, var, tensions)
            pred_res = 1 if res >= 0 else 0
            rescued = pred_res == actual

            # Properties
            nbs = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: nbs.add(v)

            # How much do neighbors AGREE with each other?
            if nbs:
                nb_agreement = sum(1 for nb in nbs if tensions[nb] * sigma > 0) / len(nbs)
                nb_confidence = sum(abs(tensions[nb]) for nb in nbs) / len(nbs)
            else:
                nb_agreement = 0.5
                nb_confidence = 0

            entry = {
                'abs_sigma': abs(sigma),
                'nb_agreement': nb_agreement,
                'nb_confidence': nb_confidence,
                'n_neighbors': len(nbs),
            }

            if rescued:
                rescued_props.append(entry)
            else:
                not_rescued_props.append(entry)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Rescued: {len(rescued_props)}, Not rescued: {len(not_rescued_props)}")
    print(f"\n  {'property':>15} | {'rescued':>8} | {'not resc':>8} | {'ratio':>7}")
    print("  " + "-" * 45)

    for prop in ['abs_sigma', 'nb_agreement', 'nb_confidence', 'n_neighbors']:
        r = mean([p[prop] for p in rescued_props])
        nr = mean([p[prop] for p in not_rescued_props])
        ratio = r/nr if nr > 0 else 0
        sig = " ★" if ratio > 1.2 or ratio < 0.83 else ""
        print(f"  {prop:>15} | {r:>8.3f} | {nr:>8.3f} | {ratio:>7.2f}{sig}")


# ============================================================
# 2. ITERATIVE RESONANCE: v4-like but with resonance
# ============================================================

def iterative_resonance():
    """
    v4: iteratively refine tension using neighbor clause needs.
    v_res: iteratively refine using resonance signal.

    Round 0: compute resonance from raw tensions.
    Round 1: recompute tensions, then resonance again.
    Round k: converge.
    """
    print("\n" + "=" * 70)
    print("2. ITERATIVE RESONANCE: Does iteration help?")
    print("=" * 70)

    random.seed(42); n = 12

    for n_iter in [0, 1, 2, 3, 5, 10]:
        correct = 0; total = 0

        for seed in range(200):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            # Start with raw tensions
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            for iteration in range(n_iter):
                # Compute resonance for all bits using current tensions
                new_t = {}
                for var in range(n):
                    res = resonance(clauses, n, var, tensions)
                    # Mix: keep some tension, add resonance
                    new_t[var] = 0.6 * tensions[var] + 0.4 * res
                tensions = new_t

            for var in range(n):
                total += 1
                if (1 if tensions[var] >= 0 else 0) == correct_val[var]:
                    correct += 1

        print(f"  {n_iter:>2} iterations: {correct/total*100:.1f}%")


# ============================================================
# 3. ALL CHANNELS COMBINED: σ + v4 + resonance + clone
# ============================================================

def all_channels():
    """
    Each channel gives independent info. Combine ALL:
    - σ (direct clause votes)
    - v4 (iterative need-weighted)
    - resonance (neighbor-implied)
    - clone (strongest-clone signal)
    """
    print("\n" + "=" * 70)
    print("3. ALL CHANNELS: σ + v4 + resonance + clone")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'σ': 0, 'v4': 0, 'resonance': 0, 'clone': 0,
               'σ+res': 0, 'v4+res': 0, 'all_4': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Raw tensions
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # V4
        v4 = dict(tensions)
        for _ in range(10):
            new_t = {}
            for var in v4:
                push_1, push_0 = 0.0, 0.0
                for clause in clauses:
                    rem = []; vs = None
                    for v, s in clause: rem.append((v,s));
                    for v, s in rem:
                        if v == var: vs = s
                    if vs is None: continue
                    oh = 0.0
                    for v, s in rem:
                        if v == var: continue
                        t = v4.get(v, 0)
                        p = (1+t)/2 if s==1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs==1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in v4:
                v4[v] = 0.5*v4[v] + 0.5*new_t.get(v,0)

        # Multi-run for clones
        assignments = []
        for run in range(10):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(tensions[v]) + random.gauss(0, 0.15)))
            for var in order:
                if var in fixed: continue
                fixed[var] = 1 if bit_tension(clauses, n, var, fixed) >= 0 else 0
            assignments.append([fixed.get(v,0) for v in range(n)])

        for var in range(n):
            results['total'] += 1
            actual = correct_val[var]

            # Individual channels
            s_sigma = tensions[var]
            s_v4 = v4[var]
            s_res = resonance(clauses, n, var, tensions)

            # Clone
            s_clone = tensions[var]
            for other in range(n):
                if other == var: continue
                agree = sum(1 for a in assignments if a[var] == a[other])
                frac = agree / len(assignments)
                if frac > 0.85 and abs(tensions[other]) > abs(s_clone):
                    s_clone = tensions[other]
                elif frac < 0.15 and abs(tensions[other]) > abs(s_clone):
                    s_clone = -tensions[other]

            if (1 if s_sigma >= 0 else 0) == actual: results['σ'] += 1
            if (1 if s_v4 >= 0 else 0) == actual: results['v4'] += 1
            if (1 if s_res >= 0 else 0) == actual: results['resonance'] += 1
            if (1 if s_clone >= 0 else 0) == actual: results['clone'] += 1

            # σ + resonance
            combined_sr = s_sigma * abs(s_sigma) + s_res * 0.5
            if (1 if combined_sr >= 0 else 0) == actual: results['σ+res'] += 1

            # v4 + resonance
            combined_vr = s_v4 * abs(s_v4) + s_res * 0.3
            if (1 if combined_vr >= 0 else 0) == actual: results['v4+res'] += 1

            # All 4 channels
            combined_all = (s_v4 * abs(s_v4) * 2 +
                          s_res * 0.5 +
                          s_clone * abs(s_clone) * 1.5 +
                          s_sigma * abs(s_sigma) * 0.5)
            if (1 if combined_all >= 0 else 0) == actual: results['all_4'] += 1

    t = results['total']
    print(f"\n  {'channel':>15} | {'accuracy':>8}")
    print("  " + "-" * 30)
    base = results['σ']/t*100
    for name in sorted(results.keys(), key=lambda k: -results.get(k, 0)):
        if name == 'total': continue
        acc = results[name]/t*100
        delta = acc - base
        print(f"  {name:>15} | {acc:>7.1f}% ({delta:>+.1f}%)")


# ============================================================
# 4. Does resonance capture the ATTRACTION FIELD?
# ============================================================

def resonance_vs_attraction():
    """
    We showed: bits pull toward correct value (attraction field).
    Does resonance MEASURE this attraction better than σ?

    Test: as we approach solution (fix correct bits one by one),
    does resonance accuracy grow FASTER than σ accuracy?
    """
    print("\n" + "=" * 70)
    print("4. Does resonance measure ATTRACTION better than σ?")
    print("=" * 70)

    random.seed(42); n = 12

    sigma_by_dist = {}
    res_by_dist = {}

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        sol = solutions[0]
        correct_val = list(sol)

        order = list(range(n)); random.shuffle(order)
        fixed = {}

        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if len(unfixed) < 2: break
            distance = len(unfixed)

            tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}

            sigma_correct = sum(1 for v in unfixed
                               if (1 if tensions[v] >= 0 else 0) == correct_val[v])
            sigma_acc = sigma_correct / len(unfixed)

            # Resonance accuracy
            res_correct = 0
            for v in unfixed:
                res = resonance(clauses, n, v, tensions)
                if (1 if res >= 0 else 0) == correct_val[v]:
                    res_correct += 1
            res_acc = res_correct / len(unfixed)

            if distance not in sigma_by_dist:
                sigma_by_dist[distance] = []
                res_by_dist[distance] = []
            sigma_by_dist[distance].append(sigma_acc)
            res_by_dist[distance].append(res_acc)

            var = order[step]
            fixed[var] = correct_val[var]

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'distance':>8} | {'σ acc':>8} | {'res acc':>8} | {'res−σ':>7}")
    print("  " + "-" * 40)
    for d in sorted(sigma_by_dist.keys(), reverse=True):
        s = mean(sigma_by_dist[d])
        r = mean(res_by_dist[d])
        diff = r - s
        print(f"  {d:>8} | {s*100:>7.1f}% | {r*100:>7.1f}% | {diff*100:>+6.1f}%")


if __name__ == "__main__":
    when_resonance_rescues()
    iterative_resonance()
    all_channels()
    resonance_vs_attraction()
