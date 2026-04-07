"""
THE THIRD SPACE — Gap field as a mathematical universe.

Gap field has:
- Persistence (r=0.88) — it's a slow structural mode
- Conservation (Σ=0 per clause) — constrained
- Diffusion (heat equation on graph) — has dynamics

What ELSE does it have?
1. Does gap have its OWN energy? Eigenmodes? Phase transitions?
2. Does gap contain information NOT in clauses OR solutions alone?
3. Can we define OPERATIONS on gap that produce new objects?
4. Does gap have a second gap? (meta-gap)
5. What's the gap's gap? (fractal structure?)
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


def compute_gap(clauses, n, solutions):
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    sol_signal = [2*p-1 for p in prob_1]
    clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
    return [clause_signal[v] - sol_signal[v] for v in range(n)]


# ============================================================
# 1. GAP ENERGY: define E_gap and look for minima
# ============================================================

def gap_energy():
    """
    Define gap energy as: E_gap = Σ_clause (gap_i + gap_j + gap_k)²

    This measures how much the gap violates per-clause zero-sum.
    We showed Σ per clause ≈ 0 on average, but there's variance.
    E_gap = that variance.

    Is E_gap MINIMIZED for real instances vs random gap fields?
    If yes → gap is in a LOW ENERGY state → gap has thermodynamics.
    """
    print("=" * 70)
    print("1. GAP ENERGY")
    print("=" * 70)

    random.seed(42)
    n = 12

    real_energies = []
    random_energies = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        gap = compute_gap(clauses, n, solutions)

        # Real gap energy
        e_real = 0
        for clause in clauses:
            vs = [v for v, s in clause]
            g_sum = sum(gap[v] for v in vs)
            e_real += g_sum**2
        real_energies.append(e_real)

        # Random gap energy (shuffle gap values)
        for _ in range(5):
            shuffled = list(gap)
            random.shuffle(shuffled)
            e_rand = 0
            for clause in clauses:
                vs = [v for v, s in clause]
                g_sum = sum(shuffled[v] for v in vs)
                e_rand += g_sum**2
            random_energies.append(e_rand)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Real gap energy:   {mean(real_energies):.3f}")
    print(f"  Random gap energy: {mean(random_energies):.3f}")
    print(f"  Ratio: {mean(real_energies)/mean(random_energies):.3f}")

    if mean(real_energies) < mean(random_energies) * 0.9:
        print(f"  → Real gap has LOWER energy than random!")
        print(f"  → Gap field is in a STRUCTURED low-energy state.")
    else:
        print(f"  → Gap energy ≈ random. No thermodynamic structure.")


# ============================================================
# 2. CROSS-INFORMATION: Does gap know something NEITHER space knows?
# ============================================================

def cross_information():
    """
    Gap = clause_signal - solution_signal.

    Can gap predict something that NEITHER tension NOR solution
    marginal can predict alone?

    Test: for each bit, can |gap| predict WHICH crystallization
    orderings will succeed? (This is about the PROCESS, not the answer.)
    """
    print("\n" + "=" * 70)
    print("2. CROSS-INFORMATION: Does gap encode unique knowledge?")
    print("=" * 70)

    random.seed(42)
    n = 12

    # For each instance: does knowing gap help predict which
    # crystallization ordering works?

    gap_ordering_corr = []

    for seed in range(80):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        gap = compute_gap(clauses, n, solutions)
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Run 30 crystallizations with random orderings
        outcomes = []  # (ordering_quality, gap_alignment)
        for run in range(30):
            # Random ordering
            order = list(range(n))
            random.shuffle(order)

            # Gap alignment: how well does this ordering avoid high-gap bits early?
            # Define: gap alignment = -Σ rank(v) × |gap(v)|
            # (low rank = fixed early; high gap early = bad)
            alignment = sum(-(n-rank) * abs(gap[v]) for rank, v in enumerate(order))

            # Crystallize
            fixed = {}
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0

                changed = True
                while changed:
                    changed = False
                    for clause in clauses:
                        satisfied = False; free = []
                        for v, s in clause:
                            if v in fixed:
                                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                    satisfied = True; break
                            else: free.append((v,s))
                        if not satisfied and len(free) == 1:
                            v, s = free[0]
                            if v not in fixed: fixed[v] = 1 if s==1 else 0; changed = True

            assignment = [fixed.get(v,0) for v in range(n)]
            success = evaluate(clauses, assignment) == len(clauses)
            outcomes.append((1 if success else 0, alignment))

        # Correlation: does gap alignment predict success?
        if len(outcomes) > 5:
            succ = [o[0] for o in outcomes]
            align = [o[1] for o in outcomes]
            ms = sum(succ)/len(succ)
            ma = sum(align)/len(align)
            ss = math.sqrt(sum((s-ms)**2 for s in succ)/len(succ))
            sa = math.sqrt(sum((a-ma)**2 for a in align)/len(align))
            if ss > 0.01 and sa > 0.01:
                cov = sum((succ[i]-ms)*(align[i]-ma) for i in range(len(outcomes)))/len(outcomes)
                corr = cov/(ss*sa)
                gap_ordering_corr.append(corr)

    if gap_ordering_corr:
        mean_corr = sum(gap_ordering_corr)/len(gap_ordering_corr)
        print(f"\n  Correlation(gap_alignment, success): {mean_corr:.4f}")
        if mean_corr > 0.1:
            print(f"  → Gap alignment PREDICTS crystallization success!")
            print(f"  → Knowing gap tells you HOW to solve, not just WHAT the answer is.")
            print(f"  → This is UNIQUE info: neither tension nor solution has it.")
        else:
            print(f"  → Weak or no correlation.")


# ============================================================
# 3. GAP FIELD OPERATORS: algebra on gap
# ============================================================

def gap_operators():
    """
    Define operations on gap fields:
    - Gradient: ∇gap_i = max_neighbor(gap_j) - gap_i
    - Curl: around a clause cycle, does gap circulate?
    - Divergence: sum of gap flowing out of a bit

    If gap has gradient AND curl → it's a FULL VECTOR FIELD.
    If only gradient (no curl) → it's a POTENTIAL field (conservative).
    """
    print("\n" + "=" * 70)
    print("3. GAP OPERATORS: gradient, curl, divergence")
    print("=" * 70)

    random.seed(42)
    n = 12

    all_div = []
    all_curl = []
    all_grad_mag = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        gap = compute_gap(clauses, n, solutions)

        # Adjacency
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        # Gradient magnitude per bit
        for v in range(n):
            if adj[v]:
                max_nb = max(gap[j] for j in adj[v])
                min_nb = min(gap[j] for j in adj[v])
                grad = max_nb - min_nb
                all_grad_mag.append(grad)

        # Divergence per bit: gap flowing out
        for v in range(n):
            if adj[v]:
                div = sum(gap[v] - gap[j] for j in adj[v])
                all_div.append(div)

        # Curl: around each clause triangle
        for clause in clauses:
            vs = [v for v, s in clause]
            # "Curl" = gap[v0] → gap[v1] → gap[v2] → gap[v0] asymmetry
            curl = (gap[vs[0]] - gap[vs[1]]) + (gap[vs[1]] - gap[vs[2]]) + (gap[vs[2]] - gap[vs[0]])
            all_curl.append(curl)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    std = lambda lst: math.sqrt(sum((x-mean(lst))**2 for x in lst)/len(lst)) if lst else 0

    print(f"\n  Gradient magnitude: mean={mean(all_grad_mag):.4f}, std={std(all_grad_mag):.4f}")
    print(f"  Divergence: mean={mean(all_div):.4f}, std={std(all_div):.4f}")
    print(f"  Curl: mean={mean(all_curl):.6f}, std={std(all_curl):.4f}")

    if abs(mean(all_curl)) < std(all_curl) * 0.01:
        print(f"\n  → Curl = 0: gap is a POTENTIAL (conservative) field!")
        print(f"  → There exists a potential φ such that gap = ∇φ.")
        print(f"  → Gap is NOT a general vector field — it's SIMPLER.")
    else:
        print(f"\n  → Curl ≠ 0: gap has rotational components.")


# ============================================================
# 4. META-GAP: does gap have its own gap?
# ============================================================

def meta_gap():
    """
    gap = σ_clause - σ_solution

    What if we compute σ_clause using gap-corrected tensions?
    σ_corrected = σ_clause - estimated_gap

    Then: meta_gap = σ_corrected - σ_solution
    = (σ_clause - estimated_gap) - σ_solution
    = gap - estimated_gap

    If estimated_gap ≈ gap, meta_gap ≈ 0.
    But estimated_gap uses only clause info.

    We showed: multi-run variance ≈ gap? No (r=-0.03).
    But: Laplacian predicts Δgap (r=0.22).
    Can we use Laplacian-smoothed tension as estimated_gap?
    """
    print("\n" + "=" * 70)
    print("4. META-GAP: Can we peel off layers of gap?")
    print("=" * 70)

    random.seed(42)
    n = 12

    gap_layers = {'raw_gap': [], 'after_laplacian': [], 'after_2_laplacian': []}

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        gap = compute_gap(clauses, n, solutions)
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Adjacency
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        # Layer 0: raw tension accuracy
        raw_correct = sum(1 for v in range(n)
                         if (1 if bit_tension(clauses, n, v) >= 0 else 0) == correct_val[v])
        gap_layers['raw_gap'].append(raw_correct / n)

        # Layer 1: Laplacian-corrected tension
        clause_signal = [bit_tension(clauses, n, v) for v in range(n)]
        estimated_gap = [0.0] * n
        for v in range(n):
            if adj[v]:
                avg_nb_gap = sum(clause_signal[v] - clause_signal[j] for j in adj[v]) / len(adj[v])
                estimated_gap[v] = avg_nb_gap * 0.3  # damping
        corrected = [clause_signal[v] - estimated_gap[v] for v in range(n)]
        l1_correct = sum(1 for v in range(n)
                        if (1 if corrected[v] >= 0 else 0) == correct_val[v])
        gap_layers['after_laplacian'].append(l1_correct / n)

        # Layer 2: double Laplacian
        estimated_gap2 = [0.0] * n
        for v in range(n):
            if adj[v]:
                avg_nb = sum(corrected[v] - corrected[j] for j in adj[v]) / len(adj[v])
                estimated_gap2[v] = avg_nb * 0.3
        corrected2 = [corrected[v] - estimated_gap2[v] for v in range(n)]
        l2_correct = sum(1 for v in range(n)
                        if (1 if corrected2[v] >= 0 else 0) == correct_val[v])
        gap_layers['after_2_laplacian'].append(l2_correct / n)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Accuracy by gap-peeling layer:")
    print(f"    Raw tension:        {mean(gap_layers['raw_gap'])*100:.1f}%")
    print(f"    After 1 Laplacian:  {mean(gap_layers['after_laplacian'])*100:.1f}%")
    print(f"    After 2 Laplacians: {mean(gap_layers['after_2_laplacian'])*100:.1f}%")


# ============================================================
# 5. GAP FIELD SPECTRUM: what modes carry the gap?
# ============================================================

def gap_spectrum():
    """
    Decompose gap into eigenmodes of the GRAPH LAPLACIAN.
    (Not the covariance eigenmodes we tried before — those were
    across instances. These are per-instance spatial modes.)

    If gap is concentrated in few Laplacian modes → low-dimensional.
    If spread across all modes → high-dimensional noise.
    """
    print("\n" + "=" * 70)
    print("5. GAP SPECTRUM: which graph Laplacian modes carry the gap?")
    print("=" * 70)

    random.seed(42)
    n = 12

    mode_energies = {i: [] for i in range(n)}

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        gap = compute_gap(clauses, n, solutions)

        # Build graph Laplacian
        adj = [[0.0]*n for _ in range(n)]
        degree = [0]*n
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]][vs[b]] = 1
                    adj[vs[b]][vs[a]] = 1
                    degree[vs[a]] += 1
                    degree[vs[b]] += 1

        L = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j: L[i][j] = degree[i]
                else: L[i][j] = -adj[i][j]

        # Power iteration for top eigenvectors of L
        eigenvectors = []
        residual_L = [row[:] for row in L]

        for eig_idx in range(min(6, n)):
            vec = [random.gauss(0,1) for _ in range(n)]
            # Orthogonalize against previous
            for prev in eigenvectors:
                dot = sum(vec[i]*prev[i] for i in range(n))
                vec = [vec[i] - dot*prev[i] for i in range(n)]
            norm = math.sqrt(sum(v*v for v in vec))
            if norm > 0: vec = [v/norm for v in vec]

            for _ in range(200):
                new_vec = [sum(residual_L[i][j]*vec[j] for j in range(n)) for i in range(n)]
                # Orthogonalize
                for prev in eigenvectors:
                    dot = sum(new_vec[i]*prev[i] for i in range(n))
                    new_vec = [new_vec[i] - dot*prev[i] for i in range(n)]
                ev = math.sqrt(sum(v*v for v in new_vec))
                if ev > 1e-10: vec = [v/ev for v in new_vec]

            eigenvectors.append(vec)

            # Project gap onto this eigenvector
            projection = sum(gap[i]*vec[i] for i in range(n))
            mode_energies[eig_idx].append(projection**2)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    total_gap_energy = sum(mean(mode_energies[i]) for i in range(min(6, n)))

    print(f"\n  Gap energy by Laplacian eigenmode:")
    print(f"  {'mode':>6} | {'energy':>8} | {'fraction':>8}")
    print("  " + "-" * 30)
    for i in range(min(6, n)):
        e = mean(mode_energies[i])
        frac = e / total_gap_energy if total_gap_energy > 0 else 0
        bar = "█" * int(frac * 30)
        print(f"  {i:>6} | {e:>8.4f} | {frac*100:>7.1f}% {bar}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    gap_energy()
    cross_information()
    gap_operators()
    meta_gap()
    gap_spectrum()
