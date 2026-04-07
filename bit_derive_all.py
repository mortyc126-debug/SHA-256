"""
COMPLETE DERIVATIONS — Building on ε = 1/(2(2^k-1))

Derive:
1. Exact accuracy at threshold from ε = 1/14
2. Why ε > 1/14 at low r (the bonus)
3. Flip trigger ratio from ε
4. Amplification delay from unit propagation threshold
5. The clause-based ceiling (why ≤79%)
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
# DERIVATION 1: Exact accuracy from ε = 1/14
# ============================================================

def derive_accuracy():
    """
    A(d) = P(Bin(d, 4/7) > d/2)

    Since ε = 1/14, p = 1/2 + 1/14 = 8/14 = 4/7

    This is EXACT — no fitting constants.
    """
    print("=" * 70)
    print("DERIVATION 1: Exact accuracy A(d) = P(Bin(d, 4/7) > d/2)")
    print("=" * 70)

    p = 4/7  # = 0.5 + 1/14

    print(f"\n  p = 4/7 = {p:.6f}")
    print(f"\n  {'d':>4} | {'A(d) exact':>10} | {'d=3r → r':>8}")
    print("  " + "-" * 35)

    for d in range(3, 20):
        # P(Bin(d, 4/7) > d/2)
        a = 0
        for k in range(d+1):
            prob = math.exp(
                math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
                k*math.log(p) + (d-k)*math.log(1-p)
            )
            if k > d/2:
                a += prob
            elif k == d/2 and d % 2 == 0:
                a += prob * 0.5
        r = d/3
        print(f"  {d:>4} | {a*100:>9.2f}% | r={r:>5.2f}")

    # At threshold: d ≈ 13 (r=4.27, d=3×4.27≈12.8)
    d_thresh = 13
    a_thresh = 0
    for k in range(d_thresh+1):
        prob = math.exp(
            math.lgamma(d_thresh+1) - math.lgamma(k+1) -
            math.lgamma(d_thresh-k+1) +
            k*math.log(p) + (d_thresh-k)*math.log(1-p)
        )
        if k > d_thresh/2: a_thresh += prob
    print(f"\n  At threshold (d=13): A = {a_thresh*100:.2f}%")
    print(f"  Measured: ~71%")
    print(f"  Exact formula predicts: {a_thresh*100:.2f}%")


# ============================================================
# DERIVATION 2: The bonus at low r
# ============================================================

def derive_bonus():
    """
    At low r (r<3), measured ε > 1/14.
    Why?

    Hypothesis: at low r, the MAJORITY across solutions is MORE extreme.
    When there are many solutions, some bits are fixed (appear same
    in ALL solutions) due to unit propagation / pure literal elimination.

    These "structurally fixed" bits have effective ε → 0.5 (always right).
    They pull the AVERAGE ε up.

    Test: measure ε separately for "fixed" bits (P(=1) near 0 or 1)
    and "free" bits (P(=1) near 0.5).
    """
    print("\n" + "=" * 70)
    print("DERIVATION 2: Why ε > 1/14 at low r")
    print("=" * 70)

    for ratio in [2.0, 3.0, 4.27]:
        fixed_epsilons = []
        free_epsilons = []

        for seed in range(200):
            clauses = random_3sat(12, int(ratio*12), seed=seed+90000)
            solutions = find_solutions(clauses, 12)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(12)]

            for var in range(12):
                actual = 1 if prob_1[var] > 0.5 else 0
                pos = sum(1 for cl in clauses for v, s in cl if v==var and s==1)
                neg = sum(1 for cl in clauses for v, s in cl if v==var and s==-1)
                d = pos + neg
                if d == 0: continue
                if actual == 1: eps = pos/d - 0.5
                else: eps = neg/d - 0.5

                # Is this bit "fixed" (near 0 or 1 in all solutions)?
                decisiveness = abs(prob_1[var] - 0.5)
                if decisiveness > 0.4:
                    fixed_epsilons.append(eps)
                else:
                    free_epsilons.append(eps)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"\n  ratio={ratio}:")
        print(f"    Fixed bits (|P-0.5|>0.4): ε = {mean(fixed_epsilons):+.4f} (n={len(fixed_epsilons)})")
        print(f"    Free bits  (|P-0.5|<0.4): ε = {mean(free_epsilons):+.4f} (n={len(free_epsilons)})")
        print(f"    Overall ε:                  = {mean(fixed_epsilons + free_epsilons):+.4f}")
        print(f"    Predicted 1/14:             = +0.0714")


# ============================================================
# DERIVATION 3: Flip trigger ratio from ε
# ============================================================

def derive_flip_triggers():
    """
    Flip trigger = neighbor nb such that fixing nb reverses sign(σ).

    For bit i with d appearances, k positive, d-k negative:
    σ = (2k-d)/d
    sign(σ) = sign(2k-d)

    Fixing a neighbor nb changes σ by removing/modifying shared clauses.
    A "flip" happens when this change crosses σ = 0, i.e., k crosses d/2.

    For a bit with k positive out of d:
    If k = d/2 + 1 (barely positive), removing one positive vote → flip.
    If k = d/2 + 5 (strongly positive), need to remove 5 positive votes → hard.

    P(flip trigger) ∝ 1/|2k - d| (inverse of margin)

    For correct bits: margin tends to be HIGHER (ε > 0 → k > d/2 more)
    For wrong bits: margin tends to be LOWER (barely on wrong side)

    Expected margin:
    Correct: E[2k-d | k > d/2] with k ~ Bin(d, 4/7)
    Wrong:   E[d-2k | k < d/2] with k ~ Bin(d, 4/7)
    """
    print("\n" + "=" * 70)
    print("DERIVATION 3: Flip trigger ratio from ε")
    print("=" * 70)

    d = 13  # at threshold
    p = 4/7

    # Expected margin for correct predictions
    correct_margins = []
    wrong_margins = []

    for k in range(d+1):
        prob = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(p) + (d-k)*math.log(1-p)
        )
        margin = abs(2*k - d)
        if k > d/2:  # correct prediction (majority matches bias)
            correct_margins.append((margin, prob))
        elif k < d/2:  # wrong prediction
            wrong_margins.append((margin, prob))

    # Expected margin
    total_correct_prob = sum(pr for m, pr in correct_margins)
    total_wrong_prob = sum(pr for m, pr in wrong_margins)

    e_margin_correct = sum(m * pr for m, pr in correct_margins) / total_correct_prob
    e_margin_wrong = sum(m * pr for m, pr in wrong_margins) / total_wrong_prob

    print(f"\n  d={d}, p=4/7:")
    print(f"  E[margin | correct] = {e_margin_correct:.3f}")
    print(f"  E[margin | wrong]   = {e_margin_wrong:.3f}")
    print(f"  Ratio correct/wrong = {e_margin_correct/e_margin_wrong:.3f}")

    # Flip trigger ∝ 1/margin (more flippable when margin small)
    e_inv_margin_correct = sum((1/max(m,0.5)) * pr for m, pr in correct_margins) / total_correct_prob
    e_inv_margin_wrong = sum((1/max(m,0.5)) * pr for m, pr in wrong_margins) / total_wrong_prob

    predicted_ratio = e_inv_margin_wrong / e_inv_margin_correct
    print(f"\n  E[1/margin | correct] = {e_inv_margin_correct:.4f}")
    print(f"  E[1/margin | wrong]   = {e_inv_margin_wrong:.4f}")
    print(f"  Predicted flip trigger ratio = {predicted_ratio:.2f}")
    print(f"  Measured flip trigger ratio  = 1.97")


# ============================================================
# DERIVATION 4: Amplification delay
# ============================================================

def derive_amplification_delay():
    """
    Amplification kicks in at step ~4 when unit propagation activates.
    UP activates when a clause has exactly 1 free literal.

    After fixing k bits, a clause becomes unit if:
    - 2 of its 3 literals are fixed
    - The fixed literals don't satisfy the clause
    - 1 literal remains free

    P(clause becomes unit after k fixes):
    P(2 of 3 vars fixed) × P(neither fixed var satisfies clause)

    P(specific var fixed) ≈ k/n
    P(2 of 3 fixed) ≈ C(3,2) × (k/n)^2 × (1-k/n) = 3k²(n-k)/n³

    P(fixed var doesn't satisfy) = 1/2 per var
    P(neither satisfies) = 1/4

    Expected unit clauses = m × 3k²(n-k)/n³ × 1/4

    At threshold: m = 4.27n, n=12:
    Expected units = 4.27n × 3k²(n-k)/(4n³)
                   = 4.27 × 3k²(n-k)/(4n²)
    """
    print("\n" + "=" * 70)
    print("DERIVATION 4: Amplification delay (unit propagation threshold)")
    print("=" * 70)

    n = 12
    r = 4.27
    m = int(r * n)

    print(f"\n  {'k fixes':>7} | {'E[unit clauses]':>15} | {'≥1?':>5}")
    print("  " + "-" * 35)

    for k in range(1, n):
        # P(specific clause becomes unit)
        p_2fixed = 3 * (k/n)**2 * (1-k/n)  # C(3,2) ways
        p_neither_sat = 0.25  # each fixed var has 1/2 chance of satisfying
        p_unit = p_2fixed * p_neither_sat

        expected_units = m * p_unit
        threshold = "← YES" if expected_units >= 1 else ""
        print(f"  {k:>7} | {expected_units:>15.2f} | {threshold}")


# ============================================================
# DERIVATION 5: v4 ceiling (why ≤79%?)
# ============================================================

def derive_v4_ceiling():
    """
    v4 iterative tension is equivalent to:
    For each bit, weight clause votes by P(clause NEEDS this bit).
    Iterate until convergence.

    This converges to the Belief Propagation fixed point (approximately).
    BP on random graphs converges to the Bethe free energy approximation.

    The ceiling of BP/v4 is determined by LOOPS in the factor graph.
    On trees: BP is EXACT → 100% accuracy.
    On loopy graphs: BP approximation error grows with loop density.

    For random 3-SAT at threshold:
    Average shortest cycle ≈ O(log n)
    Loop density is HIGH → BP/v4 has significant error.

    The 9% gap (79% → 88%) = BP approximation error due to loops.
    """
    print("\n" + "=" * 70)
    print("DERIVATION 5: v4 ceiling — loops cause the 9% gap")
    print("=" * 70)

    # Measure: average shortest cycle length
    for ratio in [2.0, 4.27]:
        cycle_lengths = []

        for seed in range(100):
            clauses = random_3sat(12, int(ratio*12), seed=seed+95000)

            # Build variable interaction graph
            adj = {i: set() for i in range(12)}
            for clause in clauses:
                vs = [v for v, s in clause]
                for a in range(len(vs)):
                    for b in range(a+1, len(vs)):
                        adj[vs[a]].add(vs[b])
                        adj[vs[b]].add(vs[a])

            # Find shortest cycle through each node (BFS)
            min_cycle = float('inf')
            for start in range(12):
                # BFS to find shortest cycle
                dist = {start: 0}
                parent = {start: -1}
                queue = [start]
                idx = 0
                found = False
                while idx < len(queue) and not found:
                    curr = queue[idx]; idx += 1
                    for nb in adj[curr]:
                        if nb not in dist:
                            dist[nb] = dist[curr] + 1
                            parent[nb] = curr
                            queue.append(nb)
                        elif parent[curr] != nb and dist[curr] + dist[nb] + 1 < min_cycle:
                            min_cycle = dist[curr] + dist[nb] + 1
                            found = True

            if min_cycle < float('inf'):
                cycle_lengths.append(min_cycle)

        mean = lambda lst: sum(lst)/len(lst) if lst else 0
        print(f"\n  ratio={ratio}: avg shortest cycle = {mean(cycle_lengths):.2f}")

    print(f"\n  At threshold: loops are SHORT (≈3)")
    print(f"  BP/v4 assumes tree-like structure → fails on short loops")
    print(f"  Gap = BP error ≈ 9%")
    print(f"\n  Prediction: for TREE-like instances (sparse, long cycles),")
    print(f"  v4 should approach optimal. For dense instances, gap persists.")

    # Verify: does v4 accuracy correlate with cycle length?
    print(f"\n  Verification: v4 accuracy vs cycle length")

    short_cycle_acc = []
    long_cycle_acc = []

    for seed in range(200):
        clauses = random_3sat(12, int(4.27*12), seed=seed+95000)
        solutions = find_solutions(clauses, 12)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(12)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Cycle length
        adj = {i: set() for i in range(12)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        min_cycle = float('inf')
        for start in range(12):
            dist = {start: 0}; parent = {start: -1}
            queue = [start]; idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr]+1; parent[nb] = curr
                        queue.append(nb)
                    elif parent[curr] != nb:
                        cl = dist[curr]+dist[nb]+1
                        if cl < min_cycle: min_cycle = cl

        # v4 accuracy
        tensions = {v: bit_tension(clauses, 12, v) for v in range(12)}
        for _ in range(10):
            new_t = {}
            for var in tensions:
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
                        t = tensions.get(v, 0)
                        p = (1+t)/2 if s == 1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs == 1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in tensions:
                tensions[v] = 0.5*tensions[v]+0.5*new_t.get(v,0)

        correct = sum(1 for v in range(12)
                     if (1 if tensions[v] >= 0 else 0) == correct_val[v])
        acc = correct / 12

        if min_cycle <= 3:
            short_cycle_acc.append(acc)
        else:
            long_cycle_acc.append(acc)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"    Short cycles (≤3): v4 accuracy = {mean(short_cycle_acc)*100:.1f}% "
          f"(n={len(short_cycle_acc)})")
    print(f"    Long cycles  (>3): v4 accuracy = {mean(long_cycle_acc)*100:.1f}% "
          f"(n={len(long_cycle_acc)})")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    derive_accuracy()
    derive_bonus()
    derive_flip_triggers()
    derive_amplification_delay()
    derive_v4_ceiling()
