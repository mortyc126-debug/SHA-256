#!/usr/bin/env python3
"""
EXPERIMENT 5: Persistent Homology of Near-Collision Landscape

The collision landscape was shown to be "flat desert with isolated points."
But that analysis was at one scale.

Persistent homology (TDA) analyzes topology at ALL scales simultaneously.
The barcode diagram of near-collisions (δH ≤ t) as t varies can reveal:
- H0: connected components (clusters of near-collisions)
- H1: cycles (loops in near-collision space)
- H2+: higher-dimensional holes

If persistent H1 cycles exist -> navigation paths between near-collisions!

We work in the space of Wang cascade solutions, using various distance metrics.
"""

import sys, os, random, math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def hamming_distance_messages(W1, W2):
    """Hamming distance between two 16-word messages (in bits)."""
    return sum(hw(W1[i] ^ W2[i]) for i in range(min(len(W1), len(W2))))

def hash_distance(H1, H2):
    """Hamming distance between two 8-word hashes."""
    return sum(hw(H1[i] ^ H2[i]) for i in range(8))

def arithmetic_distance(H1, H2):
    """Arithmetic distance: sum of |H1[i] - H2[i]| mod 2^32."""
    return sum(min((H1[i] - H2[i]) & MASK, (H2[i] - H1[i]) & MASK) for i in range(8))

def generate_wang_landscape(N=500):
    """Generate N Wang cascade solutions and their hashes."""
    solutions = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)

        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        hw_delta = sum(hw(d) for d in delta_H)

        solutions.append({
            'Wn': Wn, 'Wf': Wf, 'DWs': DWs,
            'H_n': H_n, 'H_f': H_f,
            'delta_H': delta_H, 'hw_delta': hw_delta,
            'De17': de(states_n, states_f, 17),
            'Da13': da(states_n, states_f, 13),
        })

    return solutions

def compute_distance_matrix(solutions, metric='hash'):
    """Compute pairwise distance matrix."""
    N = len(solutions)
    D = [[0.0] * N for _ in range(N)]

    for i in range(N):
        for j in range(i + 1, N):
            if metric == 'hash':
                d = hash_distance(solutions[i]['H_n'], solutions[j]['H_n'])
            elif metric == 'message':
                d = hamming_distance_messages(solutions[i]['Wn'], solutions[j]['Wn'])
            elif metric == 'delta':
                d = hash_distance(solutions[i]['delta_H'], solutions[j]['delta_H'])
            elif metric == 'barrier':
                # Distance in barrier space: |De17_i - De17_j|
                d = hw(solutions[i]['De17'] ^ solutions[j]['De17'])
            elif metric == 'Da13':
                d = hw(solutions[i]['Da13'] ^ solutions[j]['Da13'])
            else:
                d = hash_distance(solutions[i]['H_n'], solutions[j]['H_n'])

            D[i][j] = d
            D[j][i] = d

    return D

def vietoris_rips_H0(D, threshold):
    """
    Compute H0 (connected components) of Vietoris-Rips complex at given threshold.
    Uses Union-Find.
    """
    N = len(D)
    parent = list(range(N))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
            return True
        return False

    for i in range(N):
        for j in range(i + 1, N):
            if D[i][j] <= threshold:
                union(i, j)

    components = len(set(find(i) for i in range(N)))
    return components

def vietoris_rips_H1_approx(D, threshold, max_triangles=50000):
    """
    Approximate H1 (cycles) of Vietoris-Rips complex.
    Count triangles and edges to estimate β1 = #edges - #vertices + #components - #triangles (approx).
    """
    N = len(D)
    edges = []
    for i in range(N):
        for j in range(i + 1, N):
            if D[i][j] <= threshold:
                edges.append((i, j))

    # Count triangles
    adj = defaultdict(set)
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)

    triangles = 0
    for i, j in edges:
        common = adj[i] & adj[j]
        triangles += len(common)
    triangles //= 3  # Each triangle counted 3 times

    # Euler characteristic approximation
    # β0 - β1 + β2 ≈ V - E + F (where F ≈ triangles)
    V = N
    E = len(edges)
    F = triangles

    # β0 from Union-Find
    beta0 = vietoris_rips_H0(D, threshold)

    # β1 ≈ E - V + β0 - F (from Euler char, assuming β2 ≈ 0 for sparse complex)
    beta1_approx = E - V + beta0 - F

    return max(0, beta1_approx), E, F

def persistent_homology_H0(D):
    """
    Compute H0 persistence barcode.
    Returns list of (birth, death) pairs for connected components.
    """
    N = len(D)

    # Get all unique distances sorted
    all_dists = set()
    for i in range(N):
        for j in range(i + 1, N):
            all_dists.add(D[i][j])

    thresholds = sorted(all_dists)

    # Track component merges
    parent = list(range(N))
    birth = [0.0] * N  # Each point born at 0
    barcodes = []

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # Process edges in order of distance
    edges = []
    for i in range(N):
        for j in range(i + 1, N):
            edges.append((D[i][j], i, j))
    edges.sort()

    for dist, i, j in edges:
        pi, pj = find(i), find(j)
        if pi != pj:
            # Merge: younger component dies
            # Convention: higher index dies
            if pi > pj:
                pi, pj = pj, pi
            parent[pj] = pi
            death_time = dist
            barcodes.append((birth[pj], death_time))

    # Infinite barcodes (components that never die)
    remaining = set(find(i) for i in range(N))
    max_dist = max(all_dists) if all_dists else 0
    for r in remaining:
        barcodes.append((0, max_dist * 1.1))  # "infinite"

    return barcodes

def test_landscape_topology(solutions, metric_name, D):
    """Analyze topology of near-collision landscape."""
    N = len(D)

    # Distance statistics
    all_dists = []
    for i in range(N):
        for j in range(i + 1, N):
            all_dists.append(D[i][j])

    avg_dist = sum(all_dists) / len(all_dists)
    min_dist = min(all_dists)
    max_dist = max(all_dists)

    print(f"\n  Distance stats: min={min_dist:.1f}, avg={avg_dist:.1f}, max={max_dist:.1f}")

    # H0 persistence
    barcodes = persistent_homology_H0(D)

    # Persistence = death - birth
    persistences = [d - b for b, d in barcodes if d - b > 0]
    persistences.sort(reverse=True)

    print(f"  H0 barcodes: {len(barcodes)} total")
    if persistences:
        print(f"  Top 5 persistences: {[f'{p:.1f}' for p in persistences[:5]]}")

        # Gap analysis: is there a significant gap in persistence?
        if len(persistences) > 1:
            ratios = [persistences[i] / persistences[i + 1]
                     for i in range(min(10, len(persistences) - 1))
                     if persistences[i + 1] > 0]
            if ratios:
                max_ratio_idx = max(range(len(ratios)), key=lambda i: ratios[i])
                print(f"  Max persistence gap: ratio={ratios[max_ratio_idx]:.2f} at position {max_ratio_idx}")
                if ratios[max_ratio_idx] > 3:
                    print(f"  *** SIGNAL: Significant persistence gap! {max_ratio_idx + 1} persistent features! ***")

    # H1 at various thresholds
    print(f"\n  H1 (cycles) at various thresholds:")
    print(f"  {'Threshold':>10} | {'Components':>10} | {'β1 (approx)':>12} | {'Edges':>8} | {'Triangles':>10}")
    print("  " + "-" * 60)

    for frac in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        thresh = avg_dist * frac
        comp = vietoris_rips_H0(D, thresh)
        beta1, edges, tris = vietoris_rips_H1_approx(D, thresh)
        marker = " ***" if beta1 > 5 else ""
        print(f"  {thresh:>10.1f} | {comp:>10} | {beta1:>12} | {edges:>8} | {tris:>10}{marker}")

def test_nearest_neighbor_structure(solutions, D):
    """Analyze k-NN graph structure for navigation potential."""
    print("\n  Nearest-neighbor analysis:")
    N = len(D)

    # For each point, find k nearest neighbors
    k = 5
    for i in range(N):
        dists = [(D[i][j], j) for j in range(N) if j != i]
        dists.sort()

    # Average k-NN distance vs hw_delta correlation
    nn_dists_low_hw = []
    nn_dists_high_hw = []

    median_hw = sorted(s['hw_delta'] for s in solutions)[N // 2]

    for i in range(N):
        dists = sorted([(D[i][j], j) for j in range(N) if j != i])
        avg_knn = sum(d for d, _ in dists[:k]) / k

        if solutions[i]['hw_delta'] < median_hw:
            nn_dists_low_hw.append(avg_knn)
        else:
            nn_dists_high_hw.append(avg_knn)

    if nn_dists_low_hw and nn_dists_high_hw:
        avg_low = sum(nn_dists_low_hw) / len(nn_dists_low_hw)
        avg_high = sum(nn_dists_high_hw) / len(nn_dists_high_hw)
        print(f"  Avg 5-NN dist (low hw_delta): {avg_low:.2f}")
        print(f"  Avg 5-NN dist (high hw_delta): {avg_high:.2f}")
        print(f"  Ratio: {avg_low / avg_high:.4f}")

        if avg_low < avg_high * 0.9:
            print("  *** SIGNAL: Near-collisions cluster together! ***")

def compare_with_random(N=200):
    """Compare topology of Wang landscape vs random landscape."""
    print("\n--- COMPARISON: WANG vs RANDOM LANDSCAPE ---")

    # Wang landscape
    solutions = generate_wang_landscape(N)
    D_wang = compute_distance_matrix(solutions, 'delta')

    # Random landscape (random message pairs, measure δH)
    random_solutions = []
    for _ in range(N):
        Wn = random_w16()
        Wf = random_w16()
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        random_solutions.append({
            'delta_H': delta_H,
            'hw_delta': sum(hw(d) for d in delta_H),
        })

    D_rand = [[0.0] * N for _ in range(N)]
    for i in range(N):
        for j in range(i + 1, N):
            d = hash_distance(random_solutions[i]['delta_H'], random_solutions[j]['delta_H'])
            D_rand[i][j] = d
            D_rand[j][i] = d

    # Compare H0 persistence
    bc_wang = persistent_homology_H0(D_wang)
    bc_rand = persistent_homology_H0(D_rand)

    pers_wang = sorted([d - b for b, d in bc_wang if d - b > 0], reverse=True)
    pers_rand = sorted([d - b for b, d in bc_rand if d - b > 0], reverse=True)

    print(f"\nWang: top persistences = {[f'{p:.1f}' for p in pers_wang[:5]]}")
    print(f"Rand: top persistences = {[f'{p:.1f}' for p in pers_rand[:5]]}")

    # Average persistence
    avg_pers_wang = sum(pers_wang[:10]) / min(10, len(pers_wang)) if pers_wang else 0
    avg_pers_rand = sum(pers_rand[:10]) / min(10, len(pers_rand)) if pers_rand else 0

    print(f"\nAvg top-10 persistence: Wang={avg_pers_wang:.2f}, Random={avg_pers_rand:.2f}")
    ratio = avg_pers_wang / avg_pers_rand if avg_pers_rand > 0 else float('inf')
    print(f"Ratio Wang/Random: {ratio:.4f}")

    if ratio > 1.2:
        print("*** SIGNAL: Wang landscape has MORE persistent features than random! ***")
    elif ratio < 0.8:
        print("*** SIGNAL: Wang landscape is MORE homogeneous than random! ***")

    return ratio

def main():
    random.seed(42)
    N = 300  # Balance speed and statistical power

    print("=" * 70)
    print("EXPERIMENT 5: PERSISTENT HOMOLOGY OF NEAR-COLLISION LANDSCAPE")
    print("=" * 70)

    print(f"\nGenerating {N} Wang cascade solutions...")
    solutions = generate_wang_landscape(N)

    hw_deltas = [s['hw_delta'] for s in solutions]
    print(f"δH distribution: min={min(hw_deltas)}, avg={sum(hw_deltas)/len(hw_deltas):.1f}, max={max(hw_deltas)}")

    # Test multiple metrics
    for metric in ['delta', 'barrier', 'Da13']:
        print(f"\n{'='*50}")
        print(f"METRIC: {metric}")
        print(f"{'='*50}")

        D = compute_distance_matrix(solutions, metric)
        test_landscape_topology(solutions, metric, D)
        test_nearest_neighbor_structure(solutions, D)

    # Compare with random
    print(f"\n{'='*50}")
    ratio = compare_with_random(200)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("If persistent H1 cycles found -> navigation paths exist between near-collisions")
    print("If Wang landscape differs from random -> exploitable structure present")
    print(f"Wang/Random persistence ratio: {ratio:.4f}")

if __name__ == "__main__":
    main()
