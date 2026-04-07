"""
DEEP DIVE: The Gap Field

gap_i = σ_clause(i) - σ_solution(i)

Properties found:
- Spatially correlated at d=1 (+0.006), anti-correlated at d=2 (-0.005)
- Predicts 77% of error lift

Questions:
1. WHY is the gap spatially correlated? What creates coherent mismatch?
2. Can we PREDICT which bits have large gap without knowing solutions?
3. Does the gap field have EIGENMODES? (like vibration modes)
4. What determines the wavelength (≈2 edges)?
5. If we could see the gap field, could we correct errors?
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
# 1. WHY is gap correlated? Decompose into sources
# ============================================================

def decompose_gap_source(clauses, n, solutions):
    """
    gap_i = σ_clause(i) - σ_solution(i)

    σ_clause depends on: clause signs (random)
    σ_solution depends on: solution structure (complex)

    For neighbors i,j sharing clause C:
    - Their σ_clause values share clause C's influence
    - Their σ_solution values are weakly correlated (ρ≈0.015)

    The gap correlation comes from which of these?

    Test: decompose gap = (σ_clause - E[σ_clause]) + (E[σ_clause] - σ_solution)
    = clause_noise + systematic_bias

    If clause_noise is correlated → gap corr from clause structure
    If systematic_bias is correlated → gap corr from solution structure
    """
    if not solutions or len(solutions) < 2: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    sol_signal = [2*p - 1 for p in prob_1]  # σ_solution ∈ [-1,1]

    clause_signal = [bit_tension(clauses, n, v) for v in range(n)]

    gap = [clause_signal[v] - sol_signal[v] for v in range(n)]

    # The "expected" clause signal given the solution:
    # E[σ_clause | solution] ≈ ε × sign(sol_signal) × something
    # Actually: σ_clause has bias ε toward the correct answer,
    # so E[σ_clause] ≈ sign(sol_signal) × 2ε ≈ sign × 1/7
    expected_clause = [2/14 * (1 if sol_signal[v] > 0 else -1) if abs(sol_signal[v]) > 0.01
                       else 0 for v in range(n)]

    clause_noise = [clause_signal[v] - expected_clause[v] for v in range(n)]
    systematic_bias = [expected_clause[v] - sol_signal[v] for v in range(n)]

    # Build adjacency
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a+1, len(vs)):
                adj[vs[a]].add(vs[b])
                adj[vs[b]].add(vs[a])

    # Correlations at d=1
    gap_corr = []
    noise_corr = []
    bias_corr = []
    cross_corr = []

    for i in range(n):
        for j in adj[i]:
            if j > i:
                gap_corr.append(gap[i] * gap[j])
                noise_corr.append(clause_noise[i] * clause_noise[j])
                bias_corr.append(systematic_bias[i] * systematic_bias[j])
                cross_corr.append(clause_noise[i]*systematic_bias[j] +
                                  clause_noise[j]*systematic_bias[i])

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    return {
        'gap_corr': mean(gap_corr),
        'noise_corr': mean(noise_corr),
        'bias_corr': mean(bias_corr),
        'cross_corr': mean(cross_corr),
        # Check: gap_corr ≈ noise_corr + bias_corr + cross_corr
        'sum_check': mean(noise_corr) + mean(bias_corr) + mean(cross_corr),
    }


# ============================================================
# 2. Can we predict large |gap| without solutions?
# ============================================================

def predict_gap(clauses, n, solutions):
    """
    Large |gap_i| = clause signal far from solution signal.
    Can any CLAUSE-ONLY property predict this?

    Candidates:
    - Low |σ| (uncertain clause signal → more room for gap)
    - High flip triggers (fragile → likely wrong → large gap)
    - High clause overlap (shared info → coherent error)
    """
    if not solutions or len(solutions) < 2: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    sol_signal = [2*p - 1 for p in prob_1]
    clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
    gap = [abs(clause_signal[v] - sol_signal[v]) for v in range(n)]

    # Properties
    results = []
    for var in range(n):
        sigma = clause_signal[var]

        # Flip triggers (quick estimate: check 3 random neighbors)
        neighbors = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var: neighbors.add(v)

        flip_count = 0
        base_sign = 1 if sigma >= 0 else -1
        for nb in list(neighbors)[:6]:
            for val in [0, 1]:
                s = bit_tension(clauses, n, var, {nb: val})
                if (1 if s >= 0 else -1) != base_sign:
                    flip_count += 1; break

        frag = flip_count / min(6, len(neighbors)) if neighbors else 0

        results.append({
            'abs_gap': gap[var],
            'abs_sigma': abs(sigma),
            'fragility': frag,
            'degree': sum(1 for cl in clauses if any(v == var for v, s in cl)),
        })

    return results


# ============================================================
# 3. Eigenmodes of the gap field
# ============================================================

def gap_eigenmodes(instances, n):
    """
    Treat the gap field as a vector in R^n.
    Collect many gap vectors across instances.
    Compute the COVARIANCE MATRIX of gap vectors.
    Its eigenvectors = the modes of gap variation.

    If one eigenvalue dominates → gap has low-dimensional structure.
    """
    gap_vectors = []

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        sol_signal = [2*p - 1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        gap = [clause_signal[v] - sol_signal[v] for v in range(n)]
        gap_vectors.append(gap)

    if len(gap_vectors) < 10:
        return None

    # Covariance matrix
    m = len(gap_vectors)
    means = [sum(gv[i] for gv in gap_vectors)/m for i in range(n)]
    cov = [[0.0]*n for _ in range(n)]

    for i in range(n):
        for j in range(i, n):
            c = sum((gap_vectors[k][i]-means[i])*(gap_vectors[k][j]-means[j])
                    for k in range(m)) / m
            cov[i][j] = c
            cov[j][i] = c

    # Power iteration for top eigenvalues
    eigenvalues = []
    residual_cov = [row[:] for row in cov]

    for eig_idx in range(min(5, n)):
        vec = [random.gauss(0,1) for _ in range(n)]
        norm = math.sqrt(sum(v*v for v in vec))
        vec = [v/norm for v in vec]

        for _ in range(200):
            new_vec = [sum(residual_cov[i][j]*vec[j] for j in range(n)) for i in range(n)]
            eigenvalue = math.sqrt(sum(v*v for v in new_vec))
            if eigenvalue > 1e-10:
                vec = [v/eigenvalue for v in new_vec]
            else:
                break

        eigenvalues.append(eigenvalue)

        # Deflate
        for i in range(n):
            for j in range(n):
                residual_cov[i][j] -= eigenvalue * vec[i] * vec[j]

    total_variance = sum(cov[i][i] for i in range(n))

    return eigenvalues, total_variance


# ============================================================
# 4. Does knowing the gap field FIX errors?
# ============================================================

def gap_oracle_test(instances, n):
    """
    If we had an oracle that told us the gap field:
    We could correct σ_clause → σ_clause - gap = σ_solution.
    This would give 88% accuracy (the optimal).

    But what if we only know the SIGN of the gap?
    Or only know WHICH bits have large gap?
    """
    # Test: if we flip tension for bits where |gap| is largest
    results = {
        'tension_baseline': 0,
        'flip_top_1': 0,
        'flip_top_2': 0,
        'flip_top_3': 0,
        'oracle_gap': 0,
    }
    total = 0

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        sol_signal = [2*p - 1 for p in prob_1]
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        gap = [clause_signal[v] - sol_signal[v] for v in range(n)]

        total += 1

        # Baseline
        pred_base = [1 if clause_signal[v] >= 0 else 0 for v in range(n)]
        if pred_base == correct_val:
            results['tension_baseline'] += 1

        # Oracle: correct using gap
        pred_oracle = [1 if (clause_signal[v] - gap[v]) >= 0 else 0 for v in range(n)]
        if pred_oracle == correct_val:
            results['oracle_gap'] += 1

        # Flip top-k by |gap|
        sorted_by_gap = sorted(range(n), key=lambda v: -abs(gap[v]))
        for k in [1, 2, 3]:
            pred = list(pred_base)
            for v in sorted_by_gap[:k]:
                pred[v] = 1 - pred[v]  # flip
            if pred == correct_val:
                results[f'flip_top_{k}'] += 1

    for name in results:
        pct = results[name]/total*100 if total > 0 else 0
        print(f"    {name:>20}: {results[name]}/{total} ({pct:.1f}%)")

    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(300):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")

    # --- 1. Decompose gap source ---
    print("\n" + "=" * 70)
    print("1. DECOMPOSITION: Where does gap correlation come from?")
    print("=" * 70)

    all_results = []
    for clauses, solutions in instances:
        r = decompose_gap_source(clauses, n, solutions)
        if r: all_results.append(r)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Gap correlation (d=1):       {mean([r['gap_corr'] for r in all_results]):.6f}")
    print(f"  = clause_noise correlation:  {mean([r['noise_corr'] for r in all_results]):.6f}")
    print(f"  + systematic_bias corr:      {mean([r['bias_corr'] for r in all_results]):.6f}")
    print(f"  + cross terms:               {mean([r['cross_corr'] for r in all_results]):.6f}")
    print(f"  Sum check:                   {mean([r['sum_check'] for r in all_results]):.6f}")

    # Which dominates?
    nc = abs(mean([r['noise_corr'] for r in all_results]))
    bc = abs(mean([r['bias_corr'] for r in all_results]))
    cc = abs(mean([r['cross_corr'] for r in all_results]))
    total = nc + bc + cc
    if total > 0:
        print(f"\n  Contribution breakdown:")
        print(f"    Clause noise:     {nc/total*100:.1f}%")
        print(f"    Systematic bias:  {bc/total*100:.1f}%")
        print(f"    Cross terms:      {cc/total*100:.1f}%")

    # --- 2. Predict gap ---
    print("\n" + "=" * 70)
    print("2. Can we PREDICT |gap| from clause-only properties?")
    print("=" * 70)

    all_profiles = []
    for clauses, solutions in instances[:100]:
        r = predict_gap(clauses, n, solutions)
        if r: all_profiles.extend(r)

    # Correlation between gap and clause properties
    for prop in ['abs_sigma', 'fragility', 'degree']:
        x = [p[prop] for p in all_profiles]
        y = [p['abs_gap'] for p in all_profiles]
        mx = sum(x)/len(x); my = sum(y)/len(y)
        cov = sum((x[i]-mx)*(y[i]-my) for i in range(len(x)))/len(x)
        sx = math.sqrt(sum((xi-mx)**2 for xi in x)/len(x))
        sy = math.sqrt(sum((yi-my)**2 for yi in y)/len(y))
        corr = cov/(sx*sy) if sx > 0 and sy > 0 else 0
        print(f"  corr(|gap|, {prop:>12}) = {corr:+.4f}")

    # --- 3. Eigenmodes ---
    print("\n" + "=" * 70)
    print("3. EIGENMODES of the gap field")
    print("=" * 70)

    result = gap_eigenmodes(instances, n)
    if result:
        eigenvalues, total_var = result
        print(f"\n  Total variance: {total_var:.4f}")
        print(f"\n  {'mode':>6} | {'eigenvalue':>10} | {'% variance':>10} | {'cumulative':>10}")
        print("  " + "-" * 45)
        cumul = 0
        for i, ev in enumerate(eigenvalues):
            pct = ev/total_var*100 if total_var > 0 else 0
            cumul += pct
            bar = "█" * int(pct / 2)
            print(f"  {i+1:>6} | {ev:>10.4f} | {pct:>9.1f}% | {cumul:>9.1f}% {bar}")

    # --- 4. Gap oracle ---
    print("\n" + "=" * 70)
    print("4. If we KNEW the gap, how much would it help?")
    print("=" * 70)

    gap_oracle_test(instances, n)
