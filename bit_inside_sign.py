"""
INSIDE THE SIGN: The atom of computation
════════════════════════════════════════

A sign is +1 or -1. It's a RELATIONSHIP between a variable and a clause.
The sign matrix S[c,v] encodes the ENTIRE instance.
Everything we've built — tension, force, temperature — derives from S.

QUESTION: What is S made of? What structure lives inside?

SIX EXPERIMENTS:

1. SVD of S — singular value decomposition reveals information channels
2. Solution projection — where does the solution live in SVD space?
3. Rank and null space — what dimensions are invisible?
4. The sign as a channel — capacity and noise
5. Minimal computation unit — what is the smallest structure that "computes"?
6. Sign symmetries — what transformations preserve the solution?
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def compute_tension(clauses, n, var):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                w = 1.0 / len(clause)
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def build_sign_matrix(clauses, n):
    """Build the sign matrix S[clause, variable]."""
    m = len(clauses)
    S = np.zeros((m, n))
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            S[ci, v] = s
    return S


# ============================================================
# 1. SVD: The information channels
# ============================================================

def experiment_svd():
    print("=" * 70)
    print("1. SVD OF SIGN MATRIX: Information channels")
    print("=" * 70)

    print("""
    S = U Σ V^T decomposes the sign matrix into:
    - Σ = singular values (channel strengths)
    - V = variable-space basis (how variables group)
    - U = clause-space basis (how clauses group)

    The singular values tell us HOW MANY independent
    information channels exist between clauses and variables.
    """)

    random.seed(42)

    for n in [12, 20, 50]:
        for seed in range(10):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+92000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
                sol = solutions[0]
            elif n <= 50:
                sol = None  # just study S structure
            else:
                continue

            m = len(clauses)
            S = build_sign_matrix(clauses, n)

            # SVD
            U, sigma, Vt = np.linalg.svd(S, full_matrices=False)

            # Rank (number of significant singular values)
            threshold = 0.01 * sigma[0]
            rank = np.sum(sigma > threshold)

            # Information: entropy of normalized singular values
            sigma_norm = sigma / np.sum(sigma)
            info_entropy = -np.sum(sigma_norm * np.log2(sigma_norm + 1e-15))

            # Top singular values
            print(f"\n  n={n}, m={m}, seed={seed}:")
            print(f"    Rank: {rank}/{n}")
            print(f"    Top 10 σ: [{', '.join(f'{s:.2f}' for s in sigma[:10])}]")
            print(f"    σ₁/σₙ (condition): {sigma[0]/sigma[-1]:.1f}")
            print(f"    Information entropy: {info_entropy:.2f} bits "
                  f"(max={np.log2(len(sigma)):.2f})")

            # What fraction of "energy" is in top k singular values?
            sigma_sq = sigma ** 2
            total_energy = np.sum(sigma_sq)
            cumulative = np.cumsum(sigma_sq) / total_energy

            print(f"    Energy in top-k:")
            for k_frac in [0.25, 0.5, 0.75, 0.9]:
                k = np.searchsorted(cumulative, k_frac) + 1
                print(f"      {100*k_frac:.0f}%: k={k} ({100*k/n:.0f}% of n)")

            # Prediction: does the singular value spectrum follow a power law?
            # σ_i ∝ i^(-α)?
            log_i = np.log(np.arange(1, len(sigma)+1))
            log_s = np.log(sigma + 1e-10)
            # Linear fit
            coeffs = np.polyfit(log_i[:n//2], log_s[:n//2], 1)
            alpha = -coeffs[0]
            print(f"    Power law fit: σ_i ~ i^(-{alpha:.3f})")

            break


# ============================================================
# 2. SOLUTION PROJECTION: Where does the solution live in SVD?
# ============================================================

def experiment_solution_projection():
    print("\n" + "=" * 70)
    print("2. SOLUTION IN SVD SPACE: Which channels carry the answer?")
    print("=" * 70)

    print("""
    The solution y = 2*sol - 1 ∈ {-1,+1}^n is a vector.
    Project y onto the right singular vectors V.
    Which singular vectors carry the solution?
    """)

    random.seed(42)

    for n in [12, 16, 20]:
        for seed in range(10):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+93000000)
            if n > 16: continue
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            sol = solutions[0]

            m = len(clauses)
            S = build_sign_matrix(clauses, n)
            U, sigma, Vt = np.linalg.svd(S, full_matrices=False)

            # Solution in ±1 encoding
            y = np.array([2*sol[v] - 1 for v in range(n)], dtype=float)

            # Project solution onto right singular vectors
            # coefficients: c_i = V_i · y
            coeffs = Vt @ y  # shape: (n,)

            # Energy in each channel
            energy = coeffs ** 2
            total = np.sum(energy)

            # Cumulative energy
            sorted_idx = np.argsort(-energy)
            cum_energy = np.cumsum(energy[sorted_idx]) / total

            print(f"\n  n={n}, seed={seed}:")
            print(f"    Solution projection onto SVD channels:")
            print(f"    {'rank':>4} | {'σ_i':>6} | {'|coeff|':>7} | "
                  f"{'energy%':>7} | {'cum%':>5}")
            print("    " + "-" * 40)

            for i in range(min(n, 10)):
                idx = sorted_idx[i]
                print(f"    {idx+1:>4} | {sigma[idx]:>6.2f} | "
                      f"{abs(coeffs[idx]):>7.3f} | "
                      f"{100*energy[idx]/total:>6.1f}% | "
                      f"{100*cum_energy[i]:>4.0f}%")

            # Key question: does solution align with TOP or BOTTOM singular vectors?
            top_half_energy = np.sum(energy[:n//2]) / total
            bot_half_energy = np.sum(energy[n//2:]) / total
            print(f"\n    Energy in top-{n//2} channels: {100*top_half_energy:.1f}%")
            print(f"    Energy in bot-{n//2} channels: {100*bot_half_energy:.1f}%")
            print(f"    → Solution lives {'MOSTLY in top' if top_half_energy > 0.6 else 'SPREAD across' if top_half_energy > 0.4 else 'MOSTLY in bottom'} channels")

            break


# ============================================================
# 3. NULL SPACE: What's invisible?
# ============================================================

def experiment_null_space():
    print("\n" + "=" * 70)
    print("3. NULL SPACE: What directions are invisible to clauses?")
    print("=" * 70)

    print("""
    The null space of S contains vectors z such that S·z = 0.
    These are directions that NO clause can "see."
    If the solution has a component in the null space,
    that component is fundamentally undetectable.
    """)

    random.seed(42)

    for n in [12, 20]:
        for seed in range(10):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+94000000)
            if n > 16: continue
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            sol = solutions[0]

            m = len(clauses)
            S = build_sign_matrix(clauses, n)
            U, sigma, Vt = np.linalg.svd(S, full_matrices=True)

            # Null space = right singular vectors with σ ≈ 0
            null_threshold = 0.01 * sigma[0]
            null_dim = np.sum(sigma < null_threshold)

            # Solution projection onto null space
            y = np.array([2*sol[v] - 1 for v in range(n)], dtype=float)

            if null_dim > 0:
                null_vectors = Vt[-null_dim:]
                null_proj = null_vectors @ y
                null_energy = np.sum(null_proj ** 2) / np.sum(y ** 2)
            else:
                null_energy = 0

            # Also: the "near-null" space (small σ)
            near_null_threshold = 0.1 * sigma[0]
            near_null_dim = np.sum(sigma < near_null_threshold)
            if near_null_dim > 0:
                near_null_vecs = Vt[-near_null_dim:]
                nn_proj = near_null_vecs @ y
                nn_energy = np.sum(nn_proj ** 2) / np.sum(y ** 2)
            else:
                nn_energy = 0

            print(f"\n  n={n}, m={m}, seed={seed}:")
            print(f"    Null space dimension:      {null_dim}")
            print(f"    Near-null dimension (σ<10%): {near_null_dim}")
            print(f"    Solution in null space:     {100*null_energy:.1f}%")
            print(f"    Solution in near-null:      {100*nn_energy:.1f}%")

            if null_dim > 0 or near_null_dim > 0:
                print(f"    → {100*nn_energy:.0f}% of solution is INVISIBLE "
                      f"to the sign matrix!")
            else:
                print(f"    → S has full rank. All directions visible.")
                print(f"    But some are WEAKLY visible "
                      f"(σ_min = {sigma[-1]:.3f})")

            break


# ============================================================
# 4. SIGN AS CHANNEL: Capacity and noise
# ============================================================

def experiment_channel():
    print("\n" + "=" * 70)
    print("4. SIGN MATRIX AS INFORMATION CHANNEL")
    print("=" * 70)

    print("""
    The sign matrix S maps solutions y to clause-satisfaction vectors.
    This is an INFORMATION CHANNEL: input = y, output = S·y.

    The channel capacity tells us the MAXIMUM information
    that can be transmitted from solution to clauses.

    Compare: actual mutual information vs channel capacity.
    """)

    random.seed(42)

    for n in [12, 20]:
        for seed in range(10):
            clauses = random_3sat(n, int(4.27 * n), seed=seed+95000000)
            if n > 16: continue
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            sol = solutions[0]

            m = len(clauses)
            S = build_sign_matrix(clauses, n)
            U, sigma, Vt = np.linalg.svd(S)

            # Channel capacity ≈ Σ log₂(1 + σᵢ²/noise_power)
            # Noise power from our theory: each clause vote has
            # noise ≈ (1-4/7) = 3/7 probability of wrong direction
            noise_power = 3/7

            capacity = sum(math.log2(1 + s**2 / noise_power)
                          for s in sigma if s > 0.01)

            # Actual information: n × MI = n × 0.171
            actual_MI = n * 0.171

            print(f"\n  n={n}, m={m}, seed={seed}:")
            print(f"    Channel capacity:  {capacity:.1f} bits")
            print(f"    Actual MI:         {actual_MI:.1f} bits")
            print(f"    Capacity usage:    {100*actual_MI/capacity:.1f}%")
            print(f"    Excess capacity:   {capacity - actual_MI:.1f} bits")

            # Per-channel breakdown
            print(f"\n    Per-channel capacity:")
            for i in range(min(n, 8)):
                cap_i = math.log2(1 + sigma[i]**2 / noise_power)
                print(f"      Channel {i+1}: σ={sigma[i]:.2f}, "
                      f"capacity={cap_i:.3f} bits")

            break


# ============================================================
# 5. MINIMAL COMPUTATION UNIT
# ============================================================

def experiment_minimal_unit():
    print("\n" + "=" * 70)
    print("5. MINIMAL COMPUTATION UNIT: What's the smallest 'computer'?")
    print("=" * 70)

    print("""
    A single clause (3 signs) is a 3-body interaction.
    A single sign is a 1-body pointer.
    What is the MINIMUM structure needed to "compute"?

    Test: How many clauses does a variable need to be determined?
    With 1 clause: P(correct) = 4/7 = 57%
    With 2 clauses: P(correct) = ?
    With d clauses: P(correct) = ?

    The curve P(d) reveals the "computation threshold."
    """)

    random.seed(42)
    n = 50

    degree_accuracy = {}  # degree -> list of (correct?)

    for seed in range(30):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+96000000)
        if n > 16:
            # Use tension as proxy
            # Compute per-variable degree
            degree = [0] * n
            for clause in clauses:
                for v, s in clause:
                    degree[v] += 1

            tensions = {v: compute_tension(clauses, n, v) for v in range(n)}

            # Group by degree
            for v in range(n):
                d = degree[v]
                if d not in degree_accuracy:
                    degree_accuracy[d] = []
                # We can't know if tension is correct without solution
                # Just measure |tension| as function of degree
                degree_accuracy[d].append(abs(tensions[v]))

    if degree_accuracy:
        print(f"\n  |tension| vs variable degree (n={n}):")
        print(f"  {'degree':>6} | {'avg|t|':>7} | {'n_vars':>6} | "
              f"{'pred acc':>8}")
        print("  " + "-" * 40)

        for d in sorted(degree_accuracy.keys()):
            vals = degree_accuracy[d]
            if len(vals) < 5: continue
            avg_t = sum(vals) / len(vals)
            # Predicted accuracy from normal approx:
            # σ ~ N(ε, 1/d), so |σ| increases with √d
            # P(correct) ≈ Φ(ε√d)
            epsilon = 1/14
            z = epsilon * math.sqrt(d)
            pred_acc = 0.5 * (1 + math.erf(z / math.sqrt(2)))

            print(f"  {d:>6} | {avg_t:>7.4f} | {len(vals):>6} | "
                  f"{100*pred_acc:>7.1f}%")

    # The computation threshold: minimum degree for > 50% accuracy
    # P(correct) > 0.5 when ε√d > 0 → always! But for STRONG signal:
    # P(correct) > 0.7 when ε√d > 0.524 → d > (0.524/ε)² = 53.8
    print(f"\n  Computation thresholds (ε = 1/14):")
    print(f"    d > 0:   P > 50% (always some signal)")
    print(f"    d > 7:   P > 60% (weak computation)")
    print(f"    d > 54:  P > 70% (threshold-level, our measured accuracy)")
    print(f"    d > 384: P > 80% (strong computation)")
    print(f"    Average degree at r=4.27: d = {3*4.27:.1f}")


# ============================================================
# 6. SIGN SYMMETRIES: What transformations preserve the solution?
# ============================================================

def experiment_symmetries():
    print("\n" + "=" * 70)
    print("6. SIGN SYMMETRIES: The hidden symmetry group")
    print("=" * 70)

    print("""
    The sign matrix has symmetries:
    1. VARIABLE FLIP: negate all signs of one variable
       (equivalent to flipping the variable's value)
    2. CLAUSE PERMUTATION: reorder clauses (doesn't change problem)
    3. VARIABLE PERMUTATION: relabel variables (doesn't change structure)

    But are there HIDDEN symmetries? Transformations that change S
    but preserve the solution set?

    Test: For each pair of solutions (if multiple), what is the
    symmetry that maps one to the other?
    """)

    random.seed(42)
    n = 12

    for seed in range(20):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+97000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue

        print(f"\n  n={n}, seed={seed}, {len(solutions)} solutions:")

        # Analyze pairwise relationships between solutions
        for i in range(min(len(solutions), 4)):
            for j in range(i+1, min(len(solutions), 4)):
                s1 = solutions[i]
                s2 = solutions[j]
                hamming = sum(1 for v in range(n) if s1[v] != s2[v])
                flipped = [v for v in range(n) if s1[v] != s2[v]]

                # Check: are the flipped variables a CONNECTED component?
                adj = {v: set() for v in range(n)}
                for clause in clauses:
                    vs = [v for v, s in clause]
                    for a in range(len(vs)):
                        for b in range(a+1, len(vs)):
                            adj[vs[a]].add(vs[b])
                            adj[vs[b]].add(vs[a])

                # BFS from first flipped
                if flipped:
                    visited = set()
                    queue = [flipped[0]]
                    visited.add(flipped[0])
                    while queue:
                        v = queue.pop(0)
                        for u in adj[v]:
                            if u in set(flipped) and u not in visited:
                                visited.add(u)
                                queue.append(u)
                    connected = len(visited) == len(flipped)
                else:
                    connected = True

                # Check: do flipped vars form a "free cluster"?
                print(f"    Sol {i}↔{j}: hamming={hamming}, "
                      f"connected={'yes' if connected else 'no'}, "
                      f"flipped={flipped}")

        # The symmetry: flipping a free cluster produces another solution
        # This is the GAUGE SYMMETRY of SAT
        # The number of solutions = 2^(number of independent free clusters)

        # Count free clusters
        # Two vars are in same cluster if flipping both preserves all solutions
        # Approximate: find groups of vars that ALWAYS flip together
        if len(solutions) >= 4:
            co_flip = np.zeros((n, n))
            for i in range(len(solutions)):
                for j in range(i+1, len(solutions)):
                    s1 = solutions[i]; s2 = solutions[j]
                    flipped = set(v for v in range(n) if s1[v] != s2[v])
                    for v in flipped:
                        for u in flipped:
                            co_flip[v, u] += 1

            # Normalize
            max_cf = np.max(co_flip)
            if max_cf > 0:
                co_flip /= max_cf

            # Find clusters: vars that always flip together
            n_clusters = 0
            assigned = set()
            clusters = []
            for v in range(n):
                if v in assigned: continue
                cluster = [v]
                assigned.add(v)
                for u in range(v+1, n):
                    if u in assigned: continue
                    if co_flip[v, u] > 0.8:  # almost always flip together
                        cluster.append(u)
                        assigned.add(u)
                if len(cluster) > 1:
                    clusters.append(cluster)
                    n_clusters += 1

            print(f"\n    Free clusters (co-flip > 80%): {n_clusters}")
            for ci, cl in enumerate(clusters):
                print(f"      Cluster {ci}: {cl}")
            print(f"    Predicted solutions: 2^{n_clusters} = "
                  f"{2**n_clusters}")
            print(f"    Actual solutions:    {len(solutions)}")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    experiment_svd()
    experiment_solution_projection()
    experiment_null_space()
    experiment_channel()
    experiment_minimal_unit()
    experiment_symmetries()
