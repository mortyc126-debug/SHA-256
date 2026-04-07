"""
CLONE-SAT EQUIVALENCE: How tight is the reduction?

We showed: oracle(clones) → 100% SAT solve.
And: UP detects 0 clones.

Questions:
1. Is clone detection STRICTLY equivalent to SAT? Or is SAT harder?
   Test: can we solve SAT WITHOUT knowing clones? (Yes — DPLL does.)
   So clone detection → SAT, but SAT does NOT require clone detection.
   The reduction is ONE-WAY: clones ⊂ SAT solutions, not equal.

2. Do PARTIAL clones help? If we detect 50% of clones (not all),
   does solve rate improve proportionally?

3. APPROXIMATE clones: what if we detect pairs with 70% correlation
   (not 90%)? These are "fuzzy clones." Do they help?

4. What is the MINIMUM clone info needed to solve?
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


def get_real_clones(solutions, n, threshold=0.9):
    """Get clone pairs from solutions."""
    pairs = {}
    for i in range(n):
        for j in range(i+1, n):
            same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
            if same > threshold:
                pairs[(i,j)] = ('clone', same)
            elif same < (1-threshold):
                pairs[(i,j)] = ('anti', same)
    return pairs


def clone_solve(clauses, n, clone_pairs, max_combos=100000):
    """Solve using known clone pairs."""
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[a] = b

    clone_info = {}
    for (i,j), (ctype, _) in clone_pairs.items():
        union(i, j)
        clone_info[(i,j)] = (ctype == 'anti')

    clusters = {}
    for v in range(n):
        r = find(v)
        if r not in clusters: clusters[r] = []
        clusters[r].append(v)

    indeps = [min(c) for c in clusters.values()]
    k = len(indeps)

    if 2**k > max_combos:
        return None, False, k

    for combo in range(2**k):
        fixed = {}
        for idx, var in enumerate(indeps):
            fixed[var] = (combo >> idx) & 1

        for (i,j), is_anti in clone_info.items():
            if i in fixed and j not in fixed:
                fixed[j] = (1-fixed[i]) if is_anti else fixed[i]
            elif j in fixed and i not in fixed:
                fixed[i] = (1-fixed[j]) if is_anti else fixed[j]

        for v in range(n):
            if v not in fixed:
                sigma = bit_tension(clauses, n, v, fixed)
                fixed[v] = 1 if sigma >= 0 else 0

        assignment = [fixed.get(v,0) for v in range(n)]
        if evaluate(clauses, assignment) == len(clauses):
            return assignment, True, k

    return None, False, k


# ============================================================
# 1. PARTIAL CLONES: reveal X% of real clones
# ============================================================

def partial_clones():
    print("=" * 70)
    print("1. PARTIAL CLONE INFO: How much do you need?")
    print("=" * 70)

    random.seed(42); n = 12

    print(f"\n  {'% clones':>9} | {'k':>5} | {'solved':>7} | {'rate':>6}")
    print("  " + "-" * 35)

    for reveal_pct in [0, 10, 25, 50, 75, 90, 100]:
        solved = 0; total = 0; k_vals = []

        for seed in range(100):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions or len(solutions) < 2: continue
            total += 1

            all_clones = get_real_clones(solutions, n, 0.9)

            # Reveal only X%
            clone_list = list(all_clones.items())
            random.shuffle(clone_list)
            n_reveal = int(len(clone_list) * reveal_pct / 100)
            revealed = dict(clone_list[:n_reveal])

            _, success, k = clone_solve(clauses, n, revealed)
            k_vals.append(k)
            if success: solved += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        rate = solved/total*100 if total > 0 else 0
        print(f"  {reveal_pct:>8}% | {mean(k_vals):>5.1f} | {solved:>3}/{total} | {rate:>5.1f}%")


# ============================================================
# 2. FUZZY CLONES: lower correlation threshold
# ============================================================

def fuzzy_clones():
    print("\n" + "=" * 70)
    print("2. FUZZY CLONES: Lower threshold = more pairs, less reliable")
    print("=" * 70)

    random.seed(42); n = 12

    print(f"\n  {'threshold':>9} | {'pairs':>6} | {'k':>5} | {'solved':>7} | {'rate':>6}")
    print("  " + "-" * 45)

    for thresh_10 in [10, 9, 8, 7, 6, 5]:
        threshold = thresh_10 / 10
        solved = 0; total = 0; k_vals = []; pair_counts = []

        for seed in range(100):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions or len(solutions) < 2: continue
            total += 1

            clones = get_real_clones(solutions, n, threshold)
            pair_counts.append(len(clones))

            _, success, k = clone_solve(clauses, n, clones)
            k_vals.append(k)
            if success: solved += 1

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        rate = solved/total*100 if total > 0 else 0
        print(f"  {threshold:>9.1f} | {mean(pair_counts):>6.1f} | {mean(k_vals):>5.1f} | "
              f"{solved:>3}/{total} | {rate:>5.1f}%")


# ============================================================
# 3. MINIMUM INFO: What's the least you need to know?
# ============================================================

def minimum_info():
    """
    Instead of clone PAIRS, what if we only know the PARTITION?
    (Which bits are in the same cluster, but not who leads.)

    Or: only know WHICH bits are frozen (value determined)
    without knowing their actual value?
    """
    print("\n" + "=" * 70)
    print("3. MINIMUM INFO: Partition only vs full clone info")
    print("=" * 70)

    random.seed(42); n = 12

    results = {
        'no_info': 0,         # standard tension
        'partition_only': 0,   # know clusters but not clone/anti
        'frozen_set': 0,       # know WHICH bits are frozen but not values
        'full_clones': 0,      # know clone pairs + types
    }
    total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue
        total += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        all_clones = get_real_clones(solutions, n, 0.9)

        # No info: standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['no_info'] += 1

        # Full clones
        _, success, _ = clone_solve(clauses, n, all_clones)
        if success: results['full_clones'] += 1

        # Partition only: know which bits cluster but not clone/anti type
        parent = list(range(n))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            a, b = find(a), find(b)
            if a != b: parent[a] = b

        for (i,j) in all_clones:
            union(i, j)

        clusters = {}
        for v in range(n):
            r = find(v)
            if r not in clusters: clusters[r] = []
            clusters[r].append(v)

        indeps = [min(c) for c in clusters.values()]
        k = len(indeps)

        # Enumerate independent, but DON'T know clone/anti → try all propagations
        found_partition = False
        for combo in range(min(2**k, 50000)):
            fixed = {}
            for idx, var in enumerate(indeps):
                fixed[var] = (combo >> idx) & 1

            # Without clone type, fill others by tension
            for v in range(n):
                if v not in fixed:
                    sigma = bit_tension(clauses, n, v, fixed)
                    fixed[v] = 1 if sigma >= 0 else 0

            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                found_partition = True; break

        if found_partition: results['partition_only'] += 1

        # Frozen set: know which bits have |P-0.5| > 0.4 but not values
        frozen = [v for v in range(n) if abs(prob_1[v] - 0.5) > 0.4]
        unfrozen = [v for v in range(n) if v not in frozen]

        # Try: for unfrozen, enumerate; for frozen, use tension
        if len(unfrozen) <= 12:
            found_frozen = False
            for combo in range(min(2**len(unfrozen), 50000)):
                fixed = {}
                for idx, var in enumerate(unfrozen):
                    fixed[var] = (combo >> idx) & 1
                for v in frozen:
                    sigma = bit_tension(clauses, n, v, fixed)
                    fixed[v] = 1 if sigma >= 0 else 0

                if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                    found_frozen = True; break

            if found_frozen: results['frozen_set'] += 1

    print(f"\n  {'info level':>20} | {'solved':>8} | {'rate':>6}")
    print("  " + "-" * 40)
    for name in ['no_info', 'frozen_set', 'partition_only', 'full_clones']:
        rate = results[name]/total*100 if total > 0 else 0
        print(f"  {name:>20} | {results[name]:>3}/{total} | {rate:>5.1f}%")


# ============================================================
# 4. THE REDUCTION: Formalize
# ============================================================

def formalize():
    print("\n" + "=" * 70)
    print("4. FORMALIZING THE CLONE-SAT RELATIONSHIP")
    print("=" * 70)

    print("""
  THEOREM (Clone-SAT Reduction):

  For random 3-SAT at threshold with n variables:

  1. CLONE ORACLE → SAT (proven above):
     Given: perfect clone partition + clone/anti types
     Then: enumerate O(2^k) combos, k ≈ 0.25n
     Solve rate: 100% (verified at n=12,16)

  2. SAT → CLONE INFO (trivially):
     If you can solve SAT → you have a solution → you can compute
     all clone relationships by comparing bit values.

  3. CLAUSE-ONLY CLONE DETECTION is HARD:
     UP detects 0 clones (verified).
     Structural similarity detects 0 clones (verified).
     No poly-time clause-only method we tested detects clones.

  INTERPRETATION:
  Clone detection is an INTERMEDIATE problem:
     Clauses → [HARD] → Clone info → [EASY] → SAT solution

  The hardness of SAT is CONCENTRATED in the first arrow.
  The second arrow is trivial (2^k enumeration with small k).

  This is NOT a proof of P≠NP because:
  - We haven't proven clause-only clone detection is NP-hard
  - There might be non-UP, non-structural methods that detect clones
  - The reduction is empirical (n=12-16), not asymptotic

  But it IS a precise localization of WHERE hardness lives:
  in the MAPPING from clause structure to solution structure.
  Specifically: in detecting which bits are functionally equivalent.

  CONNECTION TO KNOWN THEORY:
  This is related to "backbone" computation in SAT literature.
  Backbone = set of frozen variables. Computing backbone is coNP-hard.
  Our clones are a GENERALIZATION: not just frozen bits, but frozen
  RELATIONSHIPS between bits. Clone detection ⊇ backbone detection.
    """)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    partial_clones()
    fuzzy_clones()
    minimum_info()
    formalize()
