"""
MULTI-BIT INFORMATION THEORY: Where does the 70% → 81% come from?

Single-bit: majority = Bayes-optimal = 70% (proven).
V4 gets 81%. The extra 11% comes from INTER-BIT correlations.

But what ARE these correlations? How much information is in them?
Can we derive 81% analytically?

Model: two neighboring bits i,j sharing a clause.
Joint information I(σ_i, σ_j ; C_i) > I(σ_i ; C_i)
The excess = information that j provides about i's correct value.
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


# ============================================================
# 1. JOINT MI: I(σ_i, σ_j ; C_i) for neighbor pairs
# ============================================================

def joint_mi_empirical(instances, n):
    """
    For each bit i and its best neighbor j:
    Compute I(σ_i, σ_j ; C_i) vs I(σ_i ; C_i)
    The difference = information from neighbor.
    """
    # Collect (σ_i, σ_j, C_i) triples
    single_data = []  # (σ_i_bin, C_i)
    pair_data = []    # (σ_i_bin, σ_j_bin, C_i)

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Build adjacency
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        for var in range(n):
            si = tensions[var]
            ci = correct_val[var]

            # Bin σ into 5 levels
            si_bin = min(4, max(0, int((si + 1) / 0.4)))
            single_data.append((si_bin, ci))

            # Best neighbor (highest shared clauses)
            best_nb = None
            best_shared = 0
            for nb in adj[var]:
                shared = sum(1 for cl in clauses
                            if var in [v for v,s in cl] and nb in [v for v,s in cl])
                if shared > best_shared:
                    best_shared = shared
                    best_nb = nb

            if best_nb is not None:
                sj = tensions[best_nb]
                sj_bin = min(4, max(0, int((sj + 1) / 0.4)))
                pair_data.append((si_bin, sj_bin, ci))

    # Compute I(σ_i; C_i)
    def compute_mi_1d(data):
        counts = {}
        n_total = len(data)
        for s, c in data:
            counts[(s,c)] = counts.get((s,c), 0) + 1

        p_s = {}; p_c = {}
        for (s,c), cnt in counts.items():
            p_s[s] = p_s.get(s, 0) + cnt/n_total
            p_c[c] = p_c.get(c, 0) + cnt/n_total

        mi = 0
        for (s,c), cnt in counts.items():
            p_sc = cnt/n_total
            if p_sc > 0 and p_s[s] > 0 and p_c[c] > 0:
                mi += p_sc * math.log2(p_sc / (p_s[s] * p_c[c]))
        return mi

    def compute_mi_2d(data):
        counts = {}
        n_total = len(data)
        for si, sj, c in data:
            counts[(si,sj,c)] = counts.get((si,sj,c), 0) + 1

        p_ss = {}; p_c = {}
        for (si,sj,c), cnt in counts.items():
            p_ss[(si,sj)] = p_ss.get((si,sj), 0) + cnt/n_total
            p_c[c] = p_c.get(c, 0) + cnt/n_total

        mi = 0
        for (si,sj,c), cnt in counts.items():
            p_ssc = cnt/n_total
            if p_ssc > 0 and p_ss[(si,sj)] > 0 and p_c[c] > 0:
                mi += p_ssc * math.log2(p_ssc / (p_ss[(si,sj)] * p_c[c]))
        return mi

    mi_single = compute_mi_1d(single_data)
    mi_pair = compute_mi_2d(pair_data)
    mi_extra = mi_pair - mi_single

    return mi_single, mi_pair, mi_extra


# ============================================================
# 2. HOW MANY NEIGHBORS NEEDED for max info?
# ============================================================

def neighbors_vs_info(instances, n):
    """
    Add neighbors one by one. How much MI does each add?
    1 neighbor, 2 neighbors, ... up to all.
    """
    # For each bit: sort neighbors by shared clauses
    results = {}  # k_neighbors → accuracy

    for k_nb in [0, 1, 2, 3, 5, 8]:
        correct = 0
        total = 0

        for clauses, solutions in instances:
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]
            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            adj = {i: {} for i in range(n)}
            for clause in clauses:
                vs = [v for v, s in clause]
                for a in range(len(vs)):
                    for b in range(a+1, len(vs)):
                        adj[vs[a]][vs[b]] = adj[vs[a]].get(vs[b], 0) + 1
                        adj[vs[b]][vs[a]] = adj[vs[b]].get(vs[a], 0) + 1

            for var in range(n):
                total += 1
                sigma_i = tensions[var]

                if k_nb == 0:
                    pred = 1 if sigma_i >= 0 else 0
                else:
                    # Use top-k neighbors' tensions as VOTES
                    sorted_nbs = sorted(adj[var].items(), key=lambda x: -x[1])
                    selected = sorted_nbs[:k_nb]

                    # Combined signal: σ_i + Σ weight_j × σ_j
                    combined = sigma_i * 2  # own vote counts double
                    for nb, shared in selected:
                        # Weight neighbor by shared clauses and their confidence
                        w = shared / 3  # normalize
                        combined += w * tensions[nb]

                    pred = 1 if combined >= 0 else 0

                if pred == correct_val[var]:
                    correct += 1

        results[k_nb] = correct / total if total > 0 else 0

    return results


# ============================================================
# 3. ANALYTICAL: Information from one neighbor
# ============================================================

def derive_neighbor_info():
    """
    Two bits i,j sharing a clause. Both have d total clauses.
    They share s clauses.

    I(σ_i, σ_j; C_i) - I(σ_i; C_i) = ?

    Model:
    σ_i = (2X_i - d)/d where X_i ~ Bin(d, p_i)
    p_i = 4/7 if C_i=1, else 3/7

    σ_j = (2X_j - d)/d where X_j ~ Bin(d, p_j)
    p_j = 4/7 if C_j=1, else 3/7

    X_i and X_j are CORRELATED because they share s clauses.
    Shared clauses contribute to BOTH X_i and X_j.

    If i and j share s clauses:
    X_i = X_shared_i + X_unique_i
    X_j = X_shared_j + X_unique_j

    where X_shared_i ~ Bin(s, p_i), X_unique_i ~ Bin(d-s, p_i)
    and X_shared_j ~ Bin(s, p_j), X_unique_j ~ Bin(d-s, p_j)

    The correlation comes through: X_shared_i and X_shared_j
    are in the SAME clauses, but with INDEPENDENT signs.

    Wait — signs are independent. So X_shared_i and X_shared_j are independent!
    Then σ_i ⊥ σ_j given (C_i, C_j).

    But C_i and C_j may be correlated through the clause constraint.
    The clause requires: at least one literal true.
    This constrains (C_i, C_j) weakly.

    The extra MI comes through this: knowing σ_j tells us about C_j,
    and C_j is (weakly) correlated with C_i through shared clauses.

    I_extra = I(C_i; C_j) × (information σ_j provides about C_j)
    ≈ I(C_i; C_j) × I(σ_j; C_j)
    """
    print("\n" + "=" * 70)
    print("3. ANALYTICAL: Information from neighbor")
    print("=" * 70)

    eps = 1/14
    d = 13

    # I(σ_j; C_j) = MI from single bit (already computed)
    # At d=13: MI ≈ 0.171 bits

    # I(C_i; C_j) for shared clause:
    # Clause requires: at least one of 3 literals true.
    # If C_i and C_j are in same clause, with random k:
    # P(C_i=1, C_j=1) ≈ P(C_i=1) × P(C_j=1) + δ
    # where δ comes from the clause constraint.

    # For random 3-SAT: solution values are weakly correlated.
    # We measured: ρ ≈ 0.015 for shared pairs.
    # I(C_i; C_j) ≈ ρ²/(2ln2) for bivariate Gaussian ≈ (0.015)²/1.386 ≈ 0.00016 bits

    rho = 0.015
    mi_cij = rho**2 / (2 * math.log(2))
    mi_single = 0.171

    # Each neighbor provides: I_extra ≈ mi_cij × something
    # With ~10 neighbors, total extra ≈ 10 × I_extra

    # But v4 is iterative: it uses σ_j as PROXY for C_j, then refines.
    # In v4: information from j is filtered through σ_j's accuracy.
    # j's σ accuracy = 70%. So j provides:
    # I_from_j ≈ I(C_i; σ_j) = I(C_i; C_j) × channel_capacity(70%)

    # Channel with 70% accuracy: capacity = 1 - H(0.3) ≈ 1 - 0.88 = 0.12 bits
    h_03 = -0.3*math.log2(0.3) - 0.7*math.log2(0.7)
    channel_cap = 1 - h_03

    i_from_one_neighbor = mi_cij * channel_cap
    n_neighbors = 10
    i_from_all = n_neighbors * i_from_one_neighbor

    print(f"\n  I(C_i; C_j) ≈ ρ²/2ln2 = {mi_cij:.6f} bits (tiny)")
    print(f"  Channel capacity at 70%: {channel_cap:.4f} bits")
    print(f"  I from one neighbor: {i_from_one_neighbor:.6f} bits")
    print(f"  I from 10 neighbors: {i_from_all:.5f} bits")
    print(f"\n  This is WAY too small to explain 70% → 81%!")

    print(f"\n  The v4 improvement must come from a DIFFERENT mechanism.")
    print(f"  Not from C_i—C_j correlation (too weak: ρ=0.015).")
    print(f"  But from REDUNDANCY estimation (as we discovered).")
    print(f"  v4 = non-redundant tension. It downweights redundant clauses.")
    print(f"  This is NOT using inter-bit MI — it's using inter-clause structure.")

    # So the 11% improvement of v4 is NOT from inter-bit information.
    # It's from better ESTIMATION of single-bit signal by removing noise.
    # Single-bit MI = 0.171 bits → 70% (with noise from redundant clauses).
    # Cleaned single-bit MI ≈ 0.39 bits → 81% (after removing redundancy).

    mi_81 = 2 * (0.19)**2 * d / math.log(2)  # approximate ε for 81%
    print(f"\n  What ε would give 81%? Solving A(d,ε)=0.81...")

    # Binary search for ε
    lo, hi = 0.01, 0.3
    for _ in range(50):
        mid = (lo+hi)/2
        a = 0
        p = 0.5+mid
        for k in range(d+1):
            prob = math.exp(math.lgamma(d+1)-math.lgamma(k+1)-math.lgamma(d-k+1)+
                           k*math.log(p)+(d-k)*math.log(1-p))
            if k > d/2: a += prob
        if a < 0.81: lo = mid
        else: hi = mid

    eps_81 = (lo+hi)/2
    print(f"  ε for 81% accuracy at d=13: {eps_81:.4f}")
    print(f"  ε from clauses (raw): 1/14 = {1/14:.4f}")
    print(f"  Effective ε after v4 cleanup: {eps_81:.4f}")
    print(f"  Amplification factor: {eps_81/(1/14):.2f}×")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")

    # 1. Joint MI
    print("\n" + "=" * 70)
    print("1. JOINT MI: How much does one neighbor add?")
    print("=" * 70)

    mi_s, mi_p, mi_e = joint_mi_empirical(instances[:80], n)
    print(f"\n  I(σ_i; C_i)       = {mi_s:.4f} bits")
    print(f"  I(σ_i,σ_j; C_i)   = {mi_p:.4f} bits")
    print(f"  Extra from neighbor = {mi_e:.4f} bits ({mi_e/mi_s*100:.1f}% more)")

    # 2. Neighbors vs info
    print("\n" + "=" * 70)
    print("2. ACCURACY vs NUMBER OF NEIGHBORS used")
    print("=" * 70)

    results = neighbors_vs_info(instances[:60], n)
    print(f"\n  {'k neighbors':>11} | {'accuracy':>8} | {'delta':>8}")
    print("  " + "-" * 35)
    base = results.get(0, 0.5)
    for k in sorted(results.keys()):
        acc = results[k]
        delta = acc - base
        print(f"  {k:>11} | {acc*100:>7.1f}% | {delta*100:>+7.1f}%")

    # 3. Analytical
    derive_neighbor_info()
