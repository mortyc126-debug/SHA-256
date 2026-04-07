"""
BIT SUPERPOSITION: Does observation collapse a bit's state?

Quantum superposition: particle has no definite state until measured.
Measurement "collapses" superposition to a definite value.

In SAT: an unfixed bit has tension σ — a DISTRIBUTION, not a value.
When we fix a neighbor ("observe" the environment), σ changes.
Is this like collapse?

Tests:
1. Before any fix: bit is in "superposition" (both values possible).
   After fixing neighbor: does bit "collapse" to definite value?
2. Does the ORDER of observation matter? (non-commutativity)
3. Is there an "uncertainty principle"? (knowing σ precisely →
   less info about something else?)
4. ENTANGLEMENT: are some bit pairs "entangled" — measuring one
   instantly determines the other?
5. INTERFERENCE: do multiple "paths" (different fixation sequences)
   interfere constructively/destructively?
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
# 1. COLLAPSE: Does fixing a neighbor collapse σ?
# ============================================================

def test_collapse():
    """
    Before: σ has some value. |σ| = confidence.
    After fixing neighbor: σ changes. Does |σ| INCREASE (collapse)?

    In quantum: measurement increases certainty (pure state).
    In SAT: does observation increase |σ|?
    """
    print("=" * 70)
    print("1. COLLAPSE: Does fixing a neighbor increase |σ|?")
    print("=" * 70)

    random.seed(42); n = 12

    sigma_before = []; sigma_after = []
    collapse_events = 0; anti_collapse = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)

        for var in range(n):
            s_before = abs(bit_tension(clauses, n, var))

            # Fix each neighbor, measure |σ| after
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            for nb in list(neighbors)[:3]:
                nb_sigma = bit_tension(clauses, n, nb)
                nb_val = 1 if nb_sigma >= 0 else 0

                s_after = abs(bit_tension(clauses, n, var, {nb: nb_val}))
                total += 1
                sigma_before.append(s_before)
                sigma_after.append(s_after)

                if s_after > s_before + 0.05:
                    collapse_events += 1  # |σ| increased = "collapsed"
                elif s_after < s_before - 0.05:
                    anti_collapse += 1    # |σ| decreased = "decoherence"

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg |σ| before observation: {mean(sigma_before):.4f}")
    print(f"  Avg |σ| after observation:  {mean(sigma_after):.4f}")
    print(f"  Change: {mean(sigma_after)-mean(sigma_before):+.4f}")
    print(f"\n  Collapse events (|σ| increased >0.05):   {collapse_events}/{total} ({collapse_events/total*100:.1f}%)")
    print(f"  Anti-collapse (|σ| decreased >0.05):     {anti_collapse}/{total} ({anti_collapse/total*100:.1f}%)")
    print(f"  Neutral:                                 {total-collapse_events-anti_collapse}/{total}")


# ============================================================
# 2. ORDER MATTERS: Non-commutativity of observations
# ============================================================

def test_noncommutativity():
    """
    Fix A first, then B → bit i has σ₁.
    Fix B first, then A → bit i has σ₂.
    Is σ₁ = σ₂? If not → observations don't commute (quantum-like).
    """
    print("\n" + "=" * 70)
    print("2. NON-COMMUTATIVITY: Does observation ORDER matter?")
    print("=" * 70)

    random.seed(42); n = 12

    commutation_errors = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        for var in range(n):
            neighbors = list(set(v for clause in clauses for v, s in clause
                               if any(vv == var for vv, ss in clause) and v != var))
            if len(neighbors) < 2: continue

            a, b = neighbors[0], neighbors[1]
            va = 1 if tensions[a] >= 0 else 0
            vb = 1 if tensions[b] >= 0 else 0

            # Order 1: fix A first, then B
            sigma_ab = bit_tension(clauses, n, var, {a: va, b: vb})

            # Order 2: fix B first, then A
            sigma_ba = bit_tension(clauses, n, var, {b: vb, a: va})

            # These SHOULD be identical (both fix same set)
            # The question is about INTERMEDIATE σ:
            sigma_after_a = bit_tension(clauses, n, var, {a: va})
            sigma_after_b = bit_tension(clauses, n, var, {b: vb})

            # Non-commutativity: |σ(after A) − σ(after B)|
            commutation_errors.append(abs(sigma_after_a - sigma_after_b))

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg |σ(fix A first) − σ(fix B first)|: {mean(commutation_errors):.4f}")
    if mean(commutation_errors) > 0.05:
        print(f"  → Observations are NON-COMMUTATIVE (intermediate states differ)")
    else:
        print(f"  → Observations approximately commute")

    # Note: FINAL state σ(A,B fixed) is always the same.
    # Only INTERMEDIATE states (σ after A vs after B) differ.
    print(f"  Note: final state σ(A∧B) is path-independent.")
    print(f"  But INTERMEDIATE σ depends on order → process matters.")


# ============================================================
# 3. UNCERTAINTY PRINCIPLE: σ precision vs something else
# ============================================================

def test_uncertainty():
    """
    In quantum: Δx × Δp ≥ ℏ/2.
    In SAT: is there a tradeoff between knowing σ precisely
    and knowing something else?

    Candidate: σ_precision × flip_fragility ≥ constant?
    (More precise σ → more fragile to perturbation?)
    """
    print("\n" + "=" * 70)
    print("3. UNCERTAINTY PRINCIPLE: σ × fragility ≥ const?")
    print("=" * 70)

    random.seed(42); n = 12

    products = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)

        for var in range(n):
            sigma = abs(bit_tension(clauses, n, var))

            # Fragility: how much does σ change with perturbation?
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            deltas = []
            for nb in list(neighbors)[:5]:
                for val in [0, 1]:
                    s_new = bit_tension(clauses, n, var, {nb: val})
                    deltas.append(abs(s_new - bit_tension(clauses, n, var)))

            fragility = max(deltas) if deltas else 0

            products.append({
                'sigma': sigma,
                'fragility': fragility,
                'product': sigma * fragility,
            })

    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    # Is product approximately constant?
    prods = [p['product'] for p in products]
    print(f"\n  Avg |σ|:       {mean([p['sigma'] for p in products]):.4f}")
    print(f"  Avg fragility: {mean([p['fragility'] for p in products]):.4f}")
    print(f"  Avg product:   {mean(prods):.4f}")
    print(f"  Std product:   {math.sqrt(sum((p-mean(prods))**2 for p in prods)/len(prods)):.4f}")

    # Correlation: is σ × fragility actually constant?
    # Check: is correlation(σ, fragility) negative? (tradeoff)
    sigmas = [p['sigma'] for p in products]
    frags = [p['fragility'] for p in products]
    ms = mean(sigmas); mf = mean(frags)
    ss = math.sqrt(sum((s-ms)**2 for s in sigmas)/len(sigmas))
    sf = math.sqrt(sum((f-mf)**2 for f in frags)/len(frags))
    if ss > 0 and sf > 0:
        cov = sum((sigmas[i]-ms)*(frags[i]-mf) for i in range(len(products)))/len(products)
        corr = cov/(ss*sf)
        print(f"  Correlation(|σ|, fragility): {corr:+.4f}")
        if corr < -0.3:
            print(f"  → NEGATIVE: uncertainty principle EXISTS!")
            print(f"  → High confidence σ → low stability (fragile)")
        elif corr > 0.3:
            print(f"  → POSITIVE: confident bits are also stable (no tradeoff)")
        else:
            print(f"  → Near zero: no clear relationship")


# ============================================================
# 4. ENTANGLEMENT: measuring one instantly determines another
# ============================================================

def test_entanglement():
    """
    Two bits are "entangled" if fixing one IMMEDIATELY determines
    the other (through unit propagation or tension collapse).

    How many entangled pairs exist? Does entanglement = clone?
    """
    print("\n" + "=" * 70)
    print("4. ENTANGLEMENT: Does fixing one bit determine another?")
    print("=" * 70)

    random.seed(42); n = 12

    entangled_pairs = 0; total_pairs = 0
    entangled_are_clones = 0; entangled_total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        for i in range(n):
            sigma_i = bit_tension(clauses, n, i)
            vi = 1 if sigma_i >= 0 else 0

            for j in range(i+1, n):
                total_pairs += 1

                # Fix i → does j become determined?
                sigma_j_before = abs(bit_tension(clauses, n, j))
                sigma_j_after = abs(bit_tension(clauses, n, j, {i: vi}))

                # "Entangled" = |σ_j| jumps above 0.8 after fixing i
                if sigma_j_after > 0.8 and sigma_j_before < 0.5:
                    entangled_pairs += 1

                    # Is this pair a real clone?
                    same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                    entangled_total += 1
                    if same > 0.85 or same < 0.15:
                        entangled_are_clones += 1

    print(f"\n  Total pairs: {total_pairs}")
    print(f"  Entangled (|σ| jumps to >0.8): {entangled_pairs} ({entangled_pairs/total_pairs*100:.2f}%)")
    if entangled_total > 0:
        print(f"  Entangled pairs that ARE clones: {entangled_are_clones}/{entangled_total} "
              f"({entangled_are_clones/entangled_total*100:.1f}%)")


# ============================================================
# 5. INTERFERENCE: do paths cancel or reinforce?
# ============================================================

def test_interference():
    """
    Fix bit A in TWO different ways (A=0 and A=1).
    Each creates a different "future" for bit i.
    σ(i|A=0) and σ(i|A=1) are two "amplitudes."

    Interference: σ(i|A=0) + σ(i|A=1) vs σ(i|nothing fixed).
    In quantum: amplitudes add (interference).
    In SAT: do they?

    Constructive: |σ(A=0) + σ(A=1)| > |σ(nothing)|
    Destructive: |σ(A=0) + σ(A=1)| < |σ(nothing)|
    """
    print("\n" + "=" * 70)
    print("5. INTERFERENCE: Do two futures add like amplitudes?")
    print("=" * 70)

    random.seed(42); n = 12

    constructive = 0; destructive = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)

        for var in range(n):
            sigma_base = bit_tension(clauses, n, var)

            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            for nb in list(neighbors)[:3]:
                s0 = bit_tension(clauses, n, var, {nb: 0})
                s1 = bit_tension(clauses, n, var, {nb: 1})

                # "Amplitude sum"
                amp_sum = (s0 + s1) / 2  # average of two futures

                total += 1
                if abs(amp_sum) > abs(sigma_base) + 0.01:
                    constructive += 1
                elif abs(amp_sum) < abs(sigma_base) - 0.01:
                    destructive += 1

    print(f"\n  Constructive (futures reinforce): {constructive}/{total} ({constructive/total*100:.1f}%)")
    print(f"  Destructive (futures cancel):    {destructive}/{total} ({destructive/total*100:.1f}%)")
    print(f"  Neutral:                         {total-constructive-destructive}/{total}")

    # Does interference type predict correctness?
    print(f"\n  What does this mean?")
    print(f"  avg(σ|nb=0, σ|nb=1) vs σ_base:")
    print(f"  If futures CANCEL → averaging loses info → bit harder to predict")
    print(f"  If futures REINFORCE → averaging helps → bit easier")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    test_collapse()
    test_noncommutativity()
    test_uncertainty()
    test_entanglement()
    test_interference()
