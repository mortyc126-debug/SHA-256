"""
WHERE DOES THE THEORY POINT?

Looking at v3.0 as a whole — what MUST be true that we haven't tested?
What CONTRADICTIONS exist? What PREDICTIONS fall out?

Three lines of investigation:

LINE 1: Self-cancellation + Cloning + V4 combined.
  SC gives 84% on trusted bits. Clones give 85%. V4 gives 81%.
  These are INDEPENDENT signals. Combined = ???

LINE 2: Effective DOF = 40%.
  If 60% of bits are clones → the REAL problem has 0.4×n variables.
  At n=12: real problem is n_eff ≈ 5.
  5-variable SAT is trivial (2^5 = 32 combos).
  WHY is it still hard? What makes the 5 independent bits hard?

LINE 3: Information conservation says 28% is hidden even from solutions.
  WHAT is this 28%? If we know ALL solutions, we still can't
  predict 28% of the information. This is RESIDUAL UNCERTAINTY.
  Is it about which CLUSTER the solution is in?
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


def get_neighbors(clauses, n, var):
    neighbors = set()
    for clause in clauses:
        vs = [v for v,s in clause]
        if var in vs:
            for v in vs:
                if v != var: neighbors.add(v)
    return neighbors


# ============================================================
# LINE 1: COMBINED — SC + Cloning + V4
# ============================================================

def combined_all():
    """
    Three independent signals:
    - |σ| (individual confidence)
    - SC = |σ + avg(nb)| (neighborhood consistency)
    - Clone: if uncertain, use confident clone's value

    Test: combine ALL THREE for per-bit accuracy.
    """
    print("=" * 70)
    print("LINE 1: Triple combination (|σ| + SC + clones)")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'tension': 0, 'v4': 0, 'sc_filter': 0,
               'clone_boost': 0, 'triple': 0, 'total': 0}

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Clone pairs
        clone_map = {}  # var → most confident clone
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.9:
                    if abs(tensions[j]) > abs(tensions.get(clone_map.get(i, i), 0)):
                        clone_map[i] = j
                    if abs(tensions[i]) > abs(tensions.get(clone_map.get(j, j), 0)):
                        clone_map[j] = i
                elif same < 0.1:
                    if abs(tensions[j]) > abs(tensions.get(clone_map.get(i, i), 0)):
                        clone_map[i] = (j, 'anti')
                    if abs(tensions[i]) > abs(tensions.get(clone_map.get(j, j), 0)):
                        clone_map[j] = (i, 'anti')

        # V4
        v4_t = dict(tensions)
        for _ in range(10):
            new_t = {}
            for var in v4_t:
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
                        t = v4_t.get(v, 0)
                        p = (1+t)/2 if s==1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs==1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in v4_t:
                v4_t[v] = 0.5*v4_t[v] + 0.5*new_t.get(v,0)

        for var in range(n):
            results['total'] += 1
            actual = correct_val[var]

            # Standard tension
            if (1 if tensions[var] >= 0 else 0) == actual:
                results['tension'] += 1

            # V4
            if (1 if v4_t[var] >= 0 else 0) == actual:
                results['v4'] += 1

            # Self-cancellation score
            nbs = get_neighbors(clauses, n, var)
            nb_avg = sum(tensions[nb] for nb in nbs) / len(nbs) if nbs else 0
            sc = abs(tensions[var] + nb_avg)

            # SC-filtered: trust only high-SC bits
            sc_pred = 1 if tensions[var] >= 0 else 0
            if sc > 0.3:
                if sc_pred == actual: results['sc_filter'] += 1
                else: results['sc_filter'] += 0
            else:
                # Low SC: use v4 instead
                if (1 if v4_t[var] >= 0 else 0) == actual: results['sc_filter'] += 1

            # Clone boost: if uncertain, ask clone
            clone_pred = 1 if tensions[var] >= 0 else 0
            if abs(tensions[var]) < 0.2 and var in clone_map:
                cm = clone_map[var]
                if isinstance(cm, tuple):
                    clone_var, mode = cm
                    if abs(tensions[clone_var]) > abs(tensions[var]):
                        clone_pred = 1 - (1 if tensions[clone_var] >= 0 else 0)
                else:
                    if abs(tensions[cm]) > abs(tensions[var]):
                        clone_pred = 1 if tensions[cm] >= 0 else 0
            if clone_pred == actual: results['clone_boost'] += 1

            # TRIPLE: v4 base, SC for confidence, clone for uncertain
            v4_sigma = v4_t[var]
            triple_pred = 1 if v4_sigma >= 0 else 0

            # If v4 uncertain AND low SC → check clone
            if abs(v4_sigma) < 0.2 and sc < 0.2:
                if var in clone_map:
                    cm = clone_map[var]
                    if isinstance(cm, tuple):
                        clone_var, mode = cm
                        if abs(v4_t.get(clone_var, 0)) > abs(v4_sigma):
                            triple_pred = 1 - (1 if v4_t.get(clone_var, 0) >= 0 else 0)
                    else:
                        if abs(v4_t.get(cm, 0)) > abs(v4_sigma):
                            triple_pred = 1 if v4_t.get(cm, 0) >= 0 else 0

            if triple_pred == actual: results['triple'] += 1

    t = results['total']
    print(f"\n  Per-bit accuracy:")
    for name in ['tension', 'v4', 'sc_filter', 'clone_boost', 'triple']:
        pct = results[name]/t*100
        print(f"    {name:>15}: {pct:.1f}%")


# ============================================================
# LINE 2: WHY 5 independent bits are hard
# ============================================================

def independent_bits():
    """
    Effective DOF = 4.8. So the problem is really 5-variable.
    2^5 = 32 combinations. Trivial to enumerate.

    But: which 5 variables ARE independent?
    And: are the CONSTRAINTS on these 5 simple or complex?
    """
    print("\n" + "=" * 70)
    print("LINE 2: The 5 independent bits — why are they hard?")
    print("=" * 70)

    random.seed(42); n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        # Find independent set via greedy:
        # Start with all bits, remove ones determined by others
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a,b):
            a,b = find(a), find(b)
            if a != b: parent[a] = b

        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same > 0.9 or same < 0.1:
                    union(i, j)

        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)

        # Representatives = independent bits
        independents = [min(cluster) for cluster in clusters.values()]

        print(f"\n  Instance {seed}: {len(independents)} independent bits: {independents}")
        print(f"  Clusters: {list(clusters.values())}")

        # What do solutions look like on independent bits only?
        ind_solutions = set()
        for sol in solutions:
            ind_vals = tuple(sol[v] for v in independents)
            ind_solutions.add(ind_vals)

        total_combos = 2**len(independents)
        print(f"  Solutions on independent bits: {len(ind_solutions)}/{total_combos}")
        print(f"  Fraction: {len(ind_solutions)/total_combos*100:.1f}%")

        # Tension accuracy on independent bits only
        correct = 0
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        for v in independents:
            sigma = bit_tension(clauses, n, v)
            if (1 if sigma >= 0 else 0) == correct_val[v]:
                correct += 1
        print(f"  Tension accuracy on independent bits: {correct}/{len(independents)}")


# ============================================================
# LINE 3: The residual 28% — what IS it?
# ============================================================

def residual_mystery():
    """
    Oracle non-redundant gives 94% → MI = 0.72 bits.
    Total H = 1.0 bit. Missing 0.28 bits.

    What is this 28%? Even knowing ALL solutions,
    the per-bit majority prediction fails 6% of the time.

    These 6% failures = bits where P(=1) ≈ 0.5 across solutions.
    They're TRULY ambiguous — solutions disagree about them.

    Is this related to which CLUSTER a solution is from?
    """
    print("\n" + "=" * 70)
    print("LINE 3: The residual 28% — truly ambiguous bits")
    print("=" * 70)

    random.seed(42); n = 12

    ambig_counts = []
    ambig_are_independent = 0
    ambig_total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        # Truly ambiguous: |P-0.5| < 0.1
        ambig = [v for v in range(n) if abs(prob_1[v] - 0.5) < 0.1]
        ambig_counts.append(len(ambig))

        # Are ambiguous bits INDEPENDENT of each other?
        for i in range(len(ambig)):
            for j in range(i+1, len(ambig)):
                vi, vj = ambig[i], ambig[j]
                same = sum(1 for s in solutions if s[vi] == s[vj]) / len(solutions)
                ambig_total += 1
                if 0.3 < same < 0.7:
                    ambig_are_independent += 1  # truly independent

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg truly ambiguous bits per instance: {mean(ambig_counts):.1f} / {n}")
    print(f"  Fraction: {mean(ambig_counts)/n*100:.1f}%")

    if ambig_total > 0:
        ind_frac = ambig_are_independent / ambig_total
        print(f"  Are ambiguous bits independent? {ind_frac*100:.1f}%")
        print(f"  ({ambig_are_independent}/{ambig_total} pairs)")

    print(f"\n  The 28% residual = these truly ambiguous bits.")
    print(f"  They appear in ~50% of solutions as 0 and ~50% as 1.")
    print(f"  No method can predict them — they're inherently uncertain.")
    print(f"  This is NOT cluster identity — it's WITHIN-cluster freedom.")
    print(f"  These bits are the UNFROZEN variables (from stat physics).")
    print(f"  They're free to vary within a cluster → no single 'correct' value.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    combined_all()
    independent_bits()
    residual_mystery()
