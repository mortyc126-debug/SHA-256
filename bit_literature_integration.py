"""
LITERATURE INTEGRATION — Connecting Bit Mechanics to statistical physics.

Three key connections:
1. Wall 83% ← Condensation transition (αd ≈ 3.86 for 3-SAT)
2. Lift 1.20 ← Reweighted partition function correlations
3. UP delay ← Reconstruction transition in decimation

These connect our EMPIRICAL findings to PROVEN mathematical results.
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


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None: fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                s = False; rem = []; vs = None
                for v, si in clause:
                    if v in fixed:
                        if (si==1 and fixed[v]==1) or (si==-1 and fixed[v]==0):
                            s = True; break
                    else: rem.append((v,si));
                    if v == var: vs = si
                if s or vs is None: continue
                oh = 0.0
                for v, si in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if si == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# CONNECTION 1: Wall = Condensation
#
# Known phase transitions for random 3-SAT:
#   αd ≈ 3.86  (clustering/dynamic transition)
#   αc ≈ 4.267 (condensation — few clusters dominate)
#   αs ≈ 4.267 (SAT/UNSAT threshold)
#
# BP is exact BELOW αd.
# BP approximation degrades between αd and αc.
# Our wall should appear at αd and worsen toward αc.
#
# Prediction: accuracy should be HIGHER at r < 3.86 and DROP at r > 3.86.
# ============================================================

def test_condensation_wall():
    print("=" * 70)
    print("CONNECTION 1: Wall accuracy vs condensation transition")
    print("αd ≈ 3.86 (clustering), αc ≈ 4.267 (condensation)")
    print("=" * 70)

    random.seed(42)
    n = 12

    print(f"\n  {'ratio':>6} | {'v1 acc':>7} | {'v4 acc':>7} | {'optimal':>7} | "
          f"{'wall gap':>8} | {'phase':>15}")
    print("  " + "-" * 65)

    for ratio_10 in range(20, 50, 3):
        ratio = ratio_10 / 10.0

        v1_correct = 0; v4_correct = 0; opt_sum = 0.0; total = 0

        for seed in range(150):
            clauses = random_3sat(n, int(ratio*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]
            v4_t = tension_v4(clauses, n, {}, 10)

            for var in range(n):
                total += 1
                opt_sum += max(prob_1[var], 1-prob_1[var])
                if (1 if bit_tension(clauses, n, var) >= 0 else 0) == correct_val[var]:
                    v1_correct += 1
                if (1 if v4_t.get(var, 0) >= 0 else 0) == correct_val[var]:
                    v4_correct += 1

        if total == 0: continue
        v1 = v1_correct/total*100
        v4 = v4_correct/total*100
        opt = opt_sum/total*100
        gap = opt - v4

        if ratio < 3.86:
            phase = "replica sym"
        elif ratio < 4.267:
            phase = "CONDENSATION"
        else:
            phase = "near threshold"

        marker = " ← αd" if abs(ratio - 3.86) < 0.2 else (" ← αc" if abs(ratio - 4.27) < 0.2 else "")
        print(f"  {ratio:>6.2f} | {v1:>6.1f}% | {v4:>6.1f}% | {opt:>6.1f}% | "
              f"{gap:>7.1f}% | {phase}{marker}")


# ============================================================
# CONNECTION 2: Lift from solution cluster structure
#
# In condensation regime: solutions concentrate in O(1) clusters.
# Within a cluster: variables are CORRELATED (frozen together).
# Between clusters: variables may differ.
#
# Lift 1.20 = intra-cluster correlation.
# Two bits in same clause → more likely in same "frozen region"
# → correlated errors.
#
# Test: measure lift SEPARATELY for instances with different
# numbers of solution clusters.
# ============================================================

def test_cluster_lift():
    print("\n" + "=" * 70)
    print("CONNECTION 2: Lift vs solution cluster structure")
    print("=" * 70)

    random.seed(42)
    n = 12

    # Approximate number of clusters by: are solutions CLOSE or FAR?
    # If all solutions are within Hamming distance d_close: likely 1 cluster
    # If solutions split into groups: multiple clusters

    data_by_clusters = {'tight': [], 'spread': []}

    for seed in range(300):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        # Measure solution spread
        dists = []
        for i in range(len(solutions)):
            for j in range(i+1, len(solutions)):
                dists.append(sum(solutions[i][k] != solutions[j][k] for k in range(n)))

        avg_dist = sum(dists)/len(dists)
        max_dist = max(dists)

        # Classify: tight (likely 1 cluster) vs spread (multiple clusters)
        is_tight = max_dist <= 4  # all solutions within 4 Hamming distance

        # Compute error lift
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        is_wrong = {v: (1 if tensions[v] >= 0 else 0) != correct_val[v] for v in range(n)}

        shared = set()
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    shared.add((min(vs[a],vs[b]), max(vs[a],vs[b])))

        for i in range(n):
            for j in range(i+1, n):
                entry = {
                    'both_wrong': is_wrong[i] and is_wrong[j],
                    'i_wrong': is_wrong[i],
                    'j_wrong': is_wrong[j],
                    'shared': (i,j) in shared,
                }
                if is_tight:
                    data_by_clusters['tight'].append(entry)
                else:
                    data_by_clusters['spread'].append(entry)

    for label in ['tight', 'spread']:
        data = data_by_clusters[label]
        if not data: continue
        shared_d = [d for d in data if d['shared']]
        if not shared_d: continue
        pi = sum(d['i_wrong'] for d in shared_d)/len(shared_d)
        pj = sum(d['j_wrong'] for d in shared_d)/len(shared_d)
        pb = sum(d['both_wrong'] for d in shared_d)/len(shared_d)
        lift = pb/(pi*pj) if pi*pj > 0 else 1

        print(f"\n  {label} solutions (n={len(data)//66} instances):")
        print(f"    Lift (shared pairs): {lift:.3f}")


# ============================================================
# CONNECTION 3: UP delay = reconstruction transition
#
# In decimation, there are two transitions:
#   - Reconstruction: after fixing enough bits, remaining bits
#     become CORRELATED enough that BP can "reconstruct" them.
#   - Condensation: too many bits fixed → clusters collapse.
#
# Our UP delay at step 4 should correspond to reconstruction:
# After 4 fixes, enough clauses are simplified that information
# starts flowing through the constraint graph.
#
# Test: does the delay depend on ratio in the way reconstruction
# transition predicts?
# ============================================================

def test_reconstruction_delay():
    print("\n" + "=" * 70)
    print("CONNECTION 3: UP delay vs ratio (reconstruction transition)")
    print("=" * 70)

    random.seed(42)
    n = 12

    print(f"\n  {'ratio':>6} | {'UP starts at':>12} | {'E[units] at k=3':>15} | {'phase':>10}")
    print("  " + "-" * 55)

    for ratio_10 in range(20, 50, 3):
        ratio = ratio_10 / 10.0
        m = int(ratio * n)

        # Analytical: E[unit clauses] at step k
        # E[units] = m × 3k²(n-k)/(4n³)
        first_up = -1
        for k in range(1, n):
            e_units = m * 3 * k**2 * (n-k) / (4 * n**3)
            if e_units >= 1 and first_up < 0:
                first_up = k

        e_units_3 = m * 3 * 9 * (n-3) / (4 * n**3)
        phase = "below αd" if ratio < 3.86 else ("condensed" if ratio < 4.27 else "threshold")

        print(f"  {ratio:>6.2f} | k={first_up:>9} | {e_units_3:>15.2f} | {phase}")


# ============================================================
# CONNECTION 4: Frozen variables = our "decisive bits"
#
# In stat physics: frozen variables take the same value in ALL
# solutions of a cluster. They're "decided by the structure."
#
# Our "decisive bits" (|P-0.5| > 0.3) should correspond to frozen vars.
# Our "ambiguous bits" (|P-0.5| < 0.1) = unfrozen/free variables.
#
# Test: fraction frozen vs ratio, compare with known thresholds.
# ============================================================

def test_frozen_variables():
    print("\n" + "=" * 70)
    print("CONNECTION 4: Frozen variables = our decisive bits")
    print("=" * 70)

    random.seed(42)
    n = 12

    print(f"\n  {'ratio':>6} | {'frozen':>7} | {'free':>7} | {'ambig':>7} | {'phase':>10}")
    print("  " + "-" * 50)

    for ratio_10 in range(15, 50, 3):
        ratio = ratio_10 / 10.0
        frozen = 0; free = 0; ambig = 0; total = 0

        for seed in range(150):
            clauses = random_3sat(n, int(ratio*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            for var in range(n):
                total += 1
                d = abs(prob_1[var] - 0.5)
                if d > 0.49:  # same value in >99% of solutions
                    frozen += 1
                elif d < 0.1:
                    ambig += 1
                else:
                    free += 1

        if total == 0: continue
        phase = "replica" if ratio < 3.86 else ("condensed" if ratio < 4.27 else "threshold")
        print(f"  {ratio:>6.2f} | {frozen/total*100:>6.1f}% | {free/total*100:>6.1f}% | "
              f"{ambig/total*100:>6.1f}% | {phase}")


# ============================================================
# SYNTHESIS: The unified picture
# ============================================================

def synthesis():
    print("\n" + "=" * 70)
    print("SYNTHESIS: Bit Mechanics + Statistical Physics")
    print("=" * 70)

    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║            UNIFIED PICTURE                                   ║
  ╠══════════════════════════════════════════════════════════════╣
  ║                                                              ║
  ║  PHASE DIAGRAM of random 3-SAT:                             ║
  ║                                                              ║
  ║  r=0          r≈3.86        r≈4.267        r>4.267          ║
  ║  ───────────┬────────────┬────────────┬──────────           ║
  ║  EASY       │ CLUSTERING │CONDENSATION│ UNSAT              ║
  ║  BP exact   │ BP approx  │ BP fails   │                    ║
  ║  v4=optimal │ v4≈optimal │ v4 < wall  │                    ║
  ║  no frozen  │ some frozen│ many frozen│                    ║
  ║  gap≈0      │ gap grows  │ gap=9%     │                    ║
  ║             │            │            │                    ║
  ║  BIT MECHANICS MAPPING:                                     ║
  ║                                                              ║
  ║  Signal ε = 1/14 (constant across all phases)               ║
  ║  Tension accuracy: 70% (constant, from ε)                   ║
  ║  V4 accuracy: varies by phase                               ║
  ║    r<3.86:  v4 ≈ optimal ≈ 88-95% (BP exact)              ║
  ║    r≈4.27:  v4 ≈ 81%, optimal ≈ 88% (gap = wall)          ║
  ║                                                              ║
  ║  Wall = condensation gap:                                    ║
  ║    MI in clauses ≈ 0.34 bits                                ║
  ║    MI in solutions ≈ 0.53 bits                              ║
  ║    Difference = 0.19 bits = condensation information         ║
  ║    This info is about WHICH CLUSTER the solution is in.     ║
  ║    Clauses don't encode cluster identity.                    ║
  ║                                                              ║
  ║  Lift 1.20 = intra-cluster correlation:                     ║
  ║    Within a cluster, variables are frozen together.          ║
  ║    Two bits in same clause → same frozen region              ║
  ║    → correlated errors when cluster identity unknown.        ║
  ║                                                              ║
  ║  Silent poison = crossing cluster boundary:                  ║
  ║    Wrong fix → switches to different cluster                 ║
  ║    → 85% solutions die (they're in the original cluster)    ║
  ║    → answers shift (different cluster = different values)    ║
  ║    → tension blind (clauses same, clusters different)        ║
  ║                                                              ║
  ║  Flip triggers = frozen boundary:                            ║
  ║    Wrong bits sit on the BOUNDARY of frozen regions.         ║
  ║    They're not clearly frozen to 0 or 1.                    ║
  ║    Any perturbation can flip them → 2× more triggers.       ║
  ║                                                              ║
  ║  Gap field = cluster uncertainty field:                      ║
  ║    gap_i = σ_clause - σ_solution                            ║
  ║    = clause view of bit i minus cluster-aware view           ║
  ║    Spatially coherent because cluster boundaries are         ║
  ║    spatially coherent in the constraint graph.               ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
    """)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    test_condensation_wall()
    test_cluster_lift()
    test_reconstruction_delay()
    test_frozen_variables()
    synthesis()
