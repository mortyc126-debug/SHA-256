"""
CLOSING THE FLIP TRIGGER GAP: predicted 1.41, measured 1.97

The margin model says: wrong bits have smaller |σ| margin,
so they're easier to flip. Predicted ratio: 1.41.
But measured: 1.97. What's missing?

Hypothesis: the margin model treats all neighbors equally.
But neighbors have DIFFERENT coupling strengths.
A neighbor sharing 3 clauses flips σ more than one sharing 1.

Also: the margin model uses the UNCONDITIONAL distribution.
But flip triggers are about CONDITIONAL: given this specific
bit in this specific clause configuration.

Let's decompose what actually happens when a neighbor flips σ.
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


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


def accuracy_exact(d, p):
    a = 0
    for k in range(d+1):
        prob = math.exp(
            math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
            k*math.log(max(p,1e-15))+(d-k)*math.log(max(1-p,1e-15))
        )
        if k > d/2: a += prob
        elif k == d/2 and d%2==0: a += prob*0.5
    return a


# ============================================================
# Step 1: MEASURE how much each neighbor changes σ
# ============================================================

def neighbor_impact_distribution(clauses, n, solutions):
    """
    For each bit: for each neighbor: how much does fixing neighbor change |σ|?
    Separate by correct/wrong bits.
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    correct_impacts = []  # |Δσ| for correct bits
    wrong_impacts = []

    for var in range(n):
        sigma_base = bit_tension(clauses, n, var)
        pred = 1 if sigma_base >= 0 else 0
        is_correct = pred == correct_val[var]

        # Find neighbors
        neighbors = set()
        shared_count = {}
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var:
                        neighbors.add(v)
                        shared_count[v] = shared_count.get(v, 0) + 1

        for nb in neighbors:
            # Impact of fixing nb
            s0 = bit_tension(clauses, n, var, {nb: 0})
            s1 = bit_tension(clauses, n, var, {nb: 1})
            max_impact = max(abs(s0 - sigma_base), abs(s1 - sigma_base))

            entry = {
                'impact': max_impact,
                'shared': shared_count.get(nb, 0),
                'abs_sigma': abs(sigma_base),
                'can_flip': (s0 * sigma_base < 0 or s1 * sigma_base < 0)
                            if abs(sigma_base) > 0.001 else False,
            }

            if is_correct:
                correct_impacts.append(entry)
            else:
                wrong_impacts.append(entry)

    return correct_impacts, wrong_impacts


# ============================================================
# Step 2: Better flip trigger model
# ============================================================

def improved_flip_model():
    """
    Better model accounting for:
    1. Each neighbor's impact depends on shared clauses
    2. Impact per shared clause ≈ 2/(3d) (removing 1 vote out of d, weighted by 1/3)
    3. Flip happens when total impact > |σ| (margin)

    P(flip) = P(max_nb(impact_nb) > |σ|)
    where impact_nb = shared_nb × 2/(3d) (approximately)
    """
    print("=" * 70)
    print("IMPROVED FLIP TRIGGER MODEL")
    print("=" * 70)

    # At threshold: d ≈ 13, each clause has 3 vars, each pair shares ≈ 3×13/(12) ≈ 3.25 clauses on average
    d = 13
    eps = 1/14
    p = 4/7

    # Distribution of |σ| for correct and wrong bits
    # For Bin(d, p): |σ| = |2k/d - 1|
    print(f"\n  Distribution of margin |σ| and max neighbor impact:")

    print(f"\n  {'k':>3} | {'σ':>7} | {'P(correct)':>11} | {'P(wrong)':>10} | "
          f"{'margin':>7} | {'impact/shared':>13}")
    print("  " + "-" * 65)

    # Probability of each k given correct/wrong
    p_correct = accuracy_exact(d, p)
    p_wrong = 1 - p_correct

    for k in range(d+1):
        prob_k = math.exp(
            math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
            k*math.log(p)+(d-k)*math.log(1-p)
        )
        sigma = (2*k - d) / d
        margin = abs(2*k - d)  # in units of "votes"

        is_correct = k > d/2
        p_given_correct = prob_k / p_correct if is_correct and p_correct > 0 else 0
        p_given_wrong = prob_k / p_wrong if not is_correct and p_wrong > 0 else 0

        # Impact of one neighbor with s shared clauses:
        # Removing s clauses from one side → changes vote count by s
        # Need: change > margin → s > margin
        # So: P(flip by 1 neighbor) = P(shared > margin)

        if margin <= 5:
            print(f"  {k:>3} | {sigma:>+7.3f} | {p_given_correct:>11.4f} | "
                  f"{p_given_wrong:>10.4f} | {margin:>7.0f} | "
                  f"need >{margin:.0f} shared")

    # Expected P(flip) by summing over k
    # For each k: P(flip) = P(∃ neighbor with shared > |2k-d|)
    # Number of neighbors ≈ d × 2 (each clause adds 2 neighbors, with overlap)
    # Shared clauses per neighbor pair ~ Poisson(3d/n) ... at n=12, 3×13/12 ≈ 3.25

    n_eff = 12  # for our experiments
    avg_shared = 3 * d / n_eff  # average shared clauses between connected pair

    print(f"\n  Average shared clauses per neighbor pair: {avg_shared:.1f}")
    print(f"  Average number of neighbors: ~{min(n_eff-1, 2*d//3)}")

    # For a neighbor with s shared clauses, impact in votes ≈ s × (2/3)
    # (each shared clause has 1/3 weight, but fixing neighbor either removes
    #  the clause or changes its weight, net effect ≈ 2/3 per shared clause)

    # P(flip from one neighbor) = P(impact > margin)
    # impact_nb ≈ shared_nb × 2/3
    # flip when shared_nb > margin × 3/2

    for label, prob_fn in [("correct", lambda k: (math.exp(
        math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
        k*math.log(p)+(d-k)*math.log(1-p)) / p_correct) if k > d/2 else 0),
        ("wrong", lambda k: (math.exp(
        math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
        k*math.log(p)+(d-k)*math.log(1-p)) / p_wrong) if k <= d/2 else 0)]:

        total_flip_prob = 0
        for k in range(d+1):
            pk = prob_fn(k)
            if pk <= 0: continue
            margin = abs(2*k - d)
            if margin == 0:
                flip_prob = 1.0  # any neighbor can flip
            else:
                # Need shared > margin × 3/2
                threshold = margin * 1.5
                # P(any neighbor has shared > threshold)
                # shared ~ Poisson(avg_shared) approximately
                # P(shared > threshold) per neighbor
                p_one = 0
                for s in range(int(threshold)+1, 20):
                    p_s = math.exp(-avg_shared + s*math.log(max(avg_shared,0.01)) -
                                   math.lgamma(s+1))
                    p_one += p_s
                # With ~10 neighbors: P(any) = 1 - (1-p_one)^10
                n_neighbors = min(n_eff-1, 10)
                flip_prob = 1 - (1-p_one)**n_neighbors

            total_flip_prob += pk * flip_prob

        print(f"\n  {label}: P(flippable) = {total_flip_prob:.4f}")

    print(f"\n  Predicted ratio: wrong/correct")


# ============================================================
# Step 3: EMPIRICAL decomposition
# ============================================================

def empirical_decomposition():
    """Measure the actual components that drive flip triggers."""
    print("\n" + "=" * 70)
    print("EMPIRICAL: What actually drives the 1.97 ratio?")
    print("=" * 70)

    random.seed(42)
    instances = []
    for seed in range(150):
        clauses = random_3sat(12, int(4.27*12), seed=seed)
        solutions = find_solutions(clauses, 12)
        if solutions:
            instances.append((clauses, solutions))

    all_correct = []
    all_wrong = []

    for clauses, solutions in instances:
        result = neighbor_impact_distribution(clauses, 12, solutions)
        if result:
            all_correct.extend(result[0])
            all_wrong.extend(result[1])

    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    print(f"\n  {len(all_correct)} correct-bit neighbors, {len(all_wrong)} wrong-bit neighbors")

    # Compare distributions
    print(f"\n  {'property':>15} | {'correct':>10} | {'wrong':>10} | {'ratio':>7}")
    print("  " + "-" * 50)

    for prop in ['impact', 'shared', 'abs_sigma']:
        c = mean([e[prop] for e in all_correct])
        w = mean([e[prop] for e in all_wrong])
        r = w/c if c > 0 else 0
        print(f"  {prop:>15} | {c:>10.4f} | {w:>10.4f} | {r:>7.2f}")

    # The key: what fraction can flip?
    c_flip = mean([1 if e['can_flip'] else 0 for e in all_correct])
    w_flip = mean([1 if e['can_flip'] else 0 for e in all_wrong])
    print(f"\n  Flip fraction: correct={c_flip:.4f}, wrong={w_flip:.4f}, ratio={w_flip/c_flip:.2f}")

    # Decompose: is it |σ| or impact that drives flipping?
    # For low-|σ| bits (margin < 3)
    c_low = [e for e in all_correct if e['abs_sigma'] < 0.3]
    w_low = [e for e in all_wrong if e['abs_sigma'] < 0.3]

    c_flip_low = mean([1 if e['can_flip'] else 0 for e in c_low]) if c_low else 0
    w_flip_low = mean([1 if e['can_flip'] else 0 for e in w_low]) if w_low else 0

    c_high = [e for e in all_correct if e['abs_sigma'] >= 0.3]
    w_high = [e for e in all_wrong if e['abs_sigma'] >= 0.3]

    c_flip_high = mean([1 if e['can_flip'] else 0 for e in c_high]) if c_high else 0
    w_flip_high = mean([1 if e['can_flip'] else 0 for e in w_high]) if w_high else 0

    print(f"\n  CONTROLLING FOR |σ|:")
    print(f"    Low |σ| (<0.3):  correct flip={c_flip_low:.4f} (n={len(c_low)}), "
          f"wrong flip={w_flip_low:.4f} (n={len(w_low)}), "
          f"ratio={w_flip_low/c_flip_low:.2f}" if c_flip_low > 0 else "")
    print(f"    High |σ| (≥0.3): correct flip={c_flip_high:.4f} (n={len(c_high)}), "
          f"wrong flip={w_flip_high:.4f} (n={len(w_high)}), "
          f"ratio={w_flip_high/c_flip_high:.2f}" if c_flip_high > 0 else "")

    # Controlling for |σ|: is there STILL a difference?
    # If ratio ≈ 1 when controlling for |σ| → the 1.97 is entirely from |σ|
    # If ratio > 1 → something beyond |σ| matters


if __name__ == "__main__":
    improved_flip_model()
    empirical_decomposition()
