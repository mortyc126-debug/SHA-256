"""
Bit Nonlinear Physics — Three-body interactions and the long-range paradox.

Two mysteries to solve:
1. 42-50% of bit triplets have nonlinear interactions. What drives them?
2. HARD problems propagate information BETTER at distance 2, but solve WORSE. Why?
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


def build_adj(clauses, n):
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a + 1, len(vs)):
                adj[vs[a]].add(vs[b])
                adj[vs[b]].add(vs[a])
    return adj


def bfs_dist(adj, start, n):
    dist = {start: 0}
    queue = [start]
    idx = 0
    while idx < len(queue):
        curr = queue[idx]; idx += 1
        for nb in adj[curr]:
            if nb not in dist:
                dist[nb] = dist[curr] + 1
                queue.append(nb)
    return dist


def shared_clauses(clauses, i, j):
    count = 0
    for clause in clauses:
        vs = [v for v, s in clause]
        if i in vs and j in vs:
            count += 1
    return count


def in_same_clause(clauses, i, j, k):
    """Do all three appear in at least one common clause?"""
    for clause in clauses:
        vs = [v for v, s in clause]
        if i in vs and j in vs and k in vs:
            return True
    return False


# ============================================================
# EXPERIMENT 1: Anatomy of three-body interactions
# ============================================================

def three_body_anatomy(clauses, n, solutions):
    """
    For each triplet (i, j, k):
    - Compute Δ³ = σ(k|i,j) - σ(k|i) - σ(k|j) + σ(k|∅)
    - Classify: are i,j,k in same clause? How many shared clauses?
    - Does Δ³ help or hurt prediction?
    """
    results = {
        'same_clause': [],      # all three in one clause
        'pair_connected': [],   # at least two pairs share clauses, but not all three
        'chain': [],            # i-j connected, j-k connected, but not i-k
        'disconnected': [],     # no pair shares a clause
    }

    # Ground truth
    prob_1 = None
    if solutions:
        prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    for i in range(n):
        si = bit_tension(clauses, n, i)
        vi = 1 if si >= 0 else 0
        for j in range(i + 1, n):
            sj = bit_tension(clauses, n, j)
            vj = 1 if sj >= 0 else 0

            for k in range(n):
                if k == i or k == j:
                    continue

                s_none = bit_tension(clauses, n, k)
                s_i = bit_tension(clauses, n, k, {i: vi})
                s_j = bit_tension(clauses, n, k, {j: vj})
                s_ij = bit_tension(clauses, n, k, {i: vi, j: vj})

                delta3 = s_ij - s_i - s_j + s_none

                # Classify topology
                ij_shared = shared_clauses(clauses, i, j)
                jk_shared = shared_clauses(clauses, j, k)
                ik_shared = shared_clauses(clauses, i, k)
                all_three = in_same_clause(clauses, i, j, k)

                entry = {
                    'delta3': delta3,
                    'abs_delta3': abs(delta3),
                    'sigma_k_base': s_none,
                    'sigma_k_corrected': s_ij,
                }

                if all_three:
                    results['same_clause'].append(entry)
                elif ij_shared > 0 and (jk_shared > 0 or ik_shared > 0):
                    results['pair_connected'].append(entry)
                elif (ij_shared > 0 and jk_shared > 0) or \
                     (ij_shared > 0 and ik_shared > 0) or \
                     (jk_shared > 0 and ik_shared > 0):
                    results['chain'].append(entry)
                elif ij_shared == 0 and jk_shared == 0 and ik_shared == 0:
                    results['disconnected'].append(entry)
                else:
                    results['pair_connected'].append(entry)

    return results


def print_three_body(results):
    mean = lambda lst: sum(lst) / len(lst) if lst else 0

    print(f"\n  {'topology':>18} | {'n':>5} | {'avg |Δ³|':>9} | "
          f"{'max |Δ³|':>9} | {'>0.05':>6} | {'>0.1':>5}")
    print("  " + "-" * 65)

    for cat in ['same_clause', 'pair_connected', 'chain', 'disconnected']:
        entries = results[cat]
        if not entries:
            continue
        abs_d = [e['abs_delta3'] for e in entries]
        big = sum(1 for d in abs_d if d > 0.05)
        very_big = sum(1 for d in abs_d if d > 0.1)
        print(f"  {cat:>18} | {len(entries):>5} | {mean(abs_d):>9.4f} | "
              f"{max(abs_d):>9.4f} | {big:>6} | {very_big:>5}")


# ============================================================
# EXPERIMENT 2: Does three-body correction improve prediction?
# ============================================================

def three_body_prediction(clauses, n, solutions):
    """
    Compare prediction accuracy:
    1. σ(k) alone (baseline)
    2. σ(k | best_neighbor) (pairwise)
    3. σ(k | best_pair) (three-body corrected)
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]

    correct_base = 0
    correct_pair = 0
    correct_triple = 0

    for k in range(n):
        actual = 1 if prob_1[k] > 0.5 else 0

        # Baseline
        s_base = bit_tension(clauses, n, k)
        pred_base = 1 if s_base >= 0 else 0
        if pred_base == actual:
            correct_base += 1

        # Best pairwise
        best_pair_sigma = s_base
        for i in range(n):
            if i == k:
                continue
            si = bit_tension(clauses, n, i)
            vi = 1 if si >= 0 else 0
            s_cond = bit_tension(clauses, n, k, {i: vi})
            if abs(s_cond) > abs(best_pair_sigma):
                best_pair_sigma = s_cond

        pred_pair = 1 if best_pair_sigma >= 0 else 0
        if pred_pair == actual:
            correct_pair += 1

        # Best triple: fix best pair of other bits
        best_triple_sigma = s_base
        # Try all pairs (expensive but n is small)
        for i in range(n):
            if i == k:
                continue
            si = bit_tension(clauses, n, i)
            vi = 1 if si >= 0 else 0
            for j in range(i + 1, n):
                if j == k:
                    continue
                sj = bit_tension(clauses, n, j)
                vj = 1 if sj >= 0 else 0
                s_cond = bit_tension(clauses, n, k, {i: vi, j: vj})
                if abs(s_cond) > abs(best_triple_sigma):
                    best_triple_sigma = s_cond

        pred_triple = 1 if best_triple_sigma >= 0 else 0
        if pred_triple == actual:
            correct_triple += 1

    return correct_base, correct_pair, correct_triple


# ============================================================
# EXPERIMENT 3: The long-range paradox
# ============================================================

def long_range_paradox(clauses, n, solutions):
    """
    HARD problems propagate information better at distance 2.
    But WHY doesn't this help?

    Hypothesis: the propagated information is CONTRADICTORY.
    Different two-step paths to the same bit give OPPOSITE signals.

    Measure: for bit k at distance 2 from source i,
    there may be multiple intermediate bits j₁, j₂, ...
    Does fixing i→j₁→k vs i→j₂→k give the same direction for k?
    """
    if not solutions:
        return None

    adj = build_adj(clauses, n)

    consistent_count = 0
    contradictory_count = 0
    total_k = 0

    for source in range(n):
        dists = bfs_dist(adj, source, n)
        sigma_source = bit_tension(clauses, n, source)
        v_source = 1 if sigma_source >= 0 else 0

        # Find all distance-2 targets
        targets = [k for k in range(n) if dists.get(k, 99) == 2]

        for target in targets:
            # Find all intermediaries (distance 1 from source AND distance 1 from target)
            intermediaries = []
            for j in adj[source]:
                if j in adj[target] and j != target and j != source:
                    intermediaries.append(j)

            if len(intermediaries) < 2:
                continue

            # For each intermediary: fix source, fix intermediary, measure target tension
            target_signals = []
            for j in intermediaries:
                sj = bit_tension(clauses, n, j, {source: v_source})
                vj = 1 if sj >= 0 else 0
                sk = bit_tension(clauses, n, target, {source: v_source, j: vj})
                target_signals.append(sk)

            # Are all signals in the same direction?
            total_k += 1
            directions = [1 if s > 0.01 else (-1 if s < -0.01 else 0) for s in target_signals]
            nonzero = [d for d in directions if d != 0]

            if nonzero and all(d == nonzero[0] for d in nonzero):
                consistent_count += 1
            elif nonzero and len(set(nonzero)) > 1:
                contradictory_count += 1

    return {
        'total': total_k,
        'consistent': consistent_count,
        'contradictory': contradictory_count,
        'ambiguous': total_k - consistent_count - contradictory_count,
    }


# ============================================================
# EXPERIMENT 4: Information quality vs quantity
# ============================================================

def info_quality(clauses, n, solutions):
    """
    At each step of crystallization, measure:
    - QUANTITY: how much does tension change? (Δσ magnitude)
    - QUALITY: does the change point in the RIGHT direction?
      (Does it bring σ closer to the correct answer?)
    """
    if not solutions:
        return None

    prob_1 = [sum(s[v] for s in solutions) / len(solutions) for v in range(n)]
    correct_dir = [1 if p > 0.5 else -1 for p in prob_1]  # +1 = should be 1, -1 = should be 0

    fixed = {}
    trace = []

    for step in range(n):
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        # Quality: for each unfixed bit, is tension pointing right?
        quantities = []
        qualities = []
        for v in unfixed:
            sigma = bit_tension(clauses, n, v, fixed)
            quantities.append(abs(sigma))

            # Quality: does sigma agree with correct direction?
            if correct_dir[v] == 1:
                qualities.append(sigma)  # positive is good
            else:
                qualities.append(-sigma)  # negative sigma is good for bits that should be 0

        avg_quantity = sum(quantities) / len(quantities)
        avg_quality = sum(qualities) / len(qualities)
        good_fraction = sum(1 for q in qualities if q > 0) / len(qualities)

        trace.append({
            'step': step,
            'n_unfixed': len(unfixed),
            'avg_quantity': avg_quantity,
            'avg_quality': avg_quality,
            'good_fraction': good_fraction,
        })

        # Fix most confident
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        fixed[best] = 1 if sigma >= 0 else 0

    return trace


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 10  # slightly smaller for 3-body computation

    print("=" * 70)
    print("EXPERIMENT 1: Anatomy of three-body interactions")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (ratio={ratio}, {len(solutions)} solutions)")
        results = three_body_anatomy(clauses, n, solutions)
        print_three_body(results)

    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Does 3-body correction improve prediction?")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        base_totals = []
        pair_totals = []
        triple_totals = []

        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            result = three_body_prediction(clauses, n, solutions)
            if result:
                base_totals.append(result[0])
                pair_totals.append(result[1])
                triple_totals.append(result[2])

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"\n  {label}: prediction accuracy (out of {n}):")
        print(f"    Baseline (σ alone):     {mean(base_totals):.1f}/{n} "
              f"({mean(base_totals)/n*100:.0f}%)")
        print(f"    Pairwise (best σ|i):    {mean(pair_totals):.1f}/{n} "
              f"({mean(pair_totals)/n*100:.0f}%)")
        print(f"    Triple (best σ|i,j):    {mean(triple_totals):.1f}/{n} "
              f"({mean(triple_totals)/n*100:.0f}%)")

    print("\n" + "=" * 70)
    print("EXPERIMENT 3: The long-range paradox — contradictory signals")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        all_results = {'total': 0, 'consistent': 0,
                       'contradictory': 0, 'ambiguous': 0}

        for seed in range(50):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            r = long_range_paradox(clauses, 12, solutions)
            if r:
                for key in all_results:
                    all_results[key] += r[key]

        total = all_results['total']
        if total > 0:
            print(f"\n  {label}: distance-2 signal consistency:")
            print(f"    Consistent:    {all_results['consistent']:>5} "
                  f"({all_results['consistent']/total*100:.0f}%)")
            print(f"    Contradictory: {all_results['contradictory']:>5} "
                  f"({all_results['contradictory']/total*100:.0f}%)")
            print(f"    Ambiguous:     {all_results['ambiguous']:>5} "
                  f"({all_results['ambiguous']/total*100:.0f}%)")

    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Information quality during crystallization")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        all_traces = {}

        for seed in range(80):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions:
                continue

            trace = info_quality(clauses, 12, solutions)
            if trace:
                for t in trace:
                    step = t['step']
                    if step not in all_traces:
                        all_traces[step] = {'qty': [], 'qlt': [], 'good': []}
                    all_traces[step]['qty'].append(t['avg_quantity'])
                    all_traces[step]['qlt'].append(t['avg_quality'])
                    all_traces[step]['good'].append(t['good_fraction'])

        print(f"\n  {label}:")
        print(f"  {'step':>4} | {'quantity':>8} | {'quality':>8} | "
              f"{'%correct':>8} | direction")
        print("  " + "-" * 50)

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        for step in sorted(all_traces.keys()):
            qty = mean(all_traces[step]['qty'])
            qlt = mean(all_traces[step]['qlt'])
            good = mean(all_traces[step]['good'])
            bar = "+" * int(good * 20) + "-" * int((1 - good) * 20)
            print(f"  {step:>4} | {qty:>8.3f} | {qlt:>+8.3f} | "
                  f"{good*100:>7.0f}% | {bar}")
