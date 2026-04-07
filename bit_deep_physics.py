"""
Bit Deep Physics — tunneling, diffusion, fundamental constants.

Final layer of physical experiments before synthesis.
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
    if fixed is None:
        fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        already_sat = False
        remaining = []
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    already_sat = True
                    break
            else:
                remaining.append((v, s))
        if already_sat:
            continue
        for v, s in remaining:
            if v == var:
                w = 1.0 / max(1, len(remaining))
                if s == 1:
                    p1 += w
                else:
                    p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


# ============================================================
# TUNNELING: Can the system escape a local minimum?
# ============================================================

def find_local_minimum(clauses, n):
    """Hill climb to a local minimum of energy (max satisfied clauses)."""
    assignment = [random.randint(0, 1) for _ in range(n)]
    sat = evaluate(clauses, assignment)

    while True:
        improved = False
        for var in range(n):
            assignment[var] = 1 - assignment[var]
            new_sat = evaluate(clauses, assignment)
            if new_sat > sat:
                sat = new_sat
                improved = True
            else:
                assignment[var] = 1 - assignment[var]  # flip back
        if not improved:
            break

    return list(assignment), sat


def tunneling_analysis(clauses, n, solutions):
    """
    From a local minimum that's NOT a solution:
    1. What's the minimum number of bits to flip to reach a solution?
    2. Does flipping those bits require going through HIGHER energy states?
       (If yes → energy barrier → tunneling needed)
    """
    if not solutions:
        return None

    results = []
    for trial in range(20):
        local_min, local_sat = find_local_minimum(clauses, n)

        if local_sat == len(clauses):
            results.append({'is_solution': True})
            continue

        # Find nearest solution (Hamming distance)
        min_dist = n + 1
        nearest_sol = None
        for sol in solutions:
            dist = sum(local_min[i] != sol[i] for i in range(n))
            if dist < min_dist:
                min_dist = dist
                nearest_sol = sol

        if nearest_sol is None:
            continue

        # Find which bits differ
        diff_bits = [i for i in range(n) if local_min[i] != nearest_sol[i]]

        # Walk from local_min to nearest_sol, flipping one bit at a time
        # Try all orderings of diff_bits and find the one with minimum max-energy
        # (For efficiency, just try: greedy best-first, and worst-first)

        current = list(local_min)
        current_sat = local_sat
        path_energies = [len(clauses) - current_sat]

        # Greedy: flip the bit that improves energy most (or hurts least)
        remaining = list(diff_bits)
        for _ in range(len(diff_bits)):
            best_bit = None
            best_sat_after = -1
            for bit in remaining:
                current[bit] = 1 - current[bit]
                s = evaluate(clauses, current)
                if s > best_sat_after:
                    best_sat_after = s
                    best_bit = bit
                current[bit] = 1 - current[bit]  # flip back

            current[best_bit] = 1 - current[best_bit]
            current_sat = evaluate(clauses, current)
            path_energies.append(len(clauses) - current_sat)
            remaining.remove(best_bit)

        max_energy = max(path_energies)
        start_energy = path_energies[0]
        barrier = max_energy - start_energy

        results.append({
            'is_solution': False,
            'distance': min_dist,
            'barrier': barrier,
            'path_energies': path_energies,
            'start_energy': start_energy,
            'end_energy': path_energies[-1],
        })

    return results


# ============================================================
# DIFFUSION: How does information spread from a "source"?
# ============================================================

def information_diffusion(clauses, n, source_var, source_val):
    """
    Fix source_var=source_val. Measure tension change of ALL other bits.
    Then fix the MOST affected bit. Measure again. Repeat.

    This traces how information "diffuses" from the source.
    Track: at each step, how far (in graph distance) is the affected bit?
    """
    # Build adjacency for distance
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a + 1, len(vs)):
                adj[vs[a]].add(vs[b])
                adj[vs[b]].add(vs[a])

    # BFS distance from source
    dist = {source_var: 0}
    queue = [source_var]
    idx = 0
    while idx < len(queue):
        curr = queue[idx]
        idx += 1
        for nb in adj[curr]:
            if nb not in dist:
                dist[nb] = dist[curr] + 1
                queue.append(nb)

    # Diffusion process
    fixed = {source_var: source_val}
    diffusion_trace = []

    # Base tensions
    base_tensions = {v: bit_tension(clauses, n, v) for v in range(n) if v != source_var}

    for step in range(min(n - 1, 8)):
        # Measure tension changes
        changes = []
        for v in range(n):
            if v in fixed:
                continue
            new_tension = bit_tension(clauses, n, v, fixed)
            old_tension = base_tensions.get(v, 0)
            change = abs(new_tension - old_tension)
            changes.append((v, change, dist.get(v, 99)))

        if not changes:
            break

        # Most affected bit
        changes.sort(key=lambda x: -x[1])
        affected_var, affected_change, affected_dist = changes[0]

        diffusion_trace.append({
            'step': step,
            'affected_var': affected_var,
            'change': affected_change,
            'distance': affected_dist,
        })

        # Fix it according to new tension
        new_t = bit_tension(clauses, n, affected_var, fixed)
        fixed[affected_var] = 1 if new_t >= 0 else 0

    return diffusion_trace


# ============================================================
# FUNDAMENTAL CONSTANTS: Are there universal ratios?
# ============================================================

def measure_constants(n_range=[8, 10, 12, 14], ratio=4.27, n_trials=100):
    """
    Measure various quantities at the SAT threshold for different n.
    Look for UNIVERSAL ratios that don't depend on n.
    """
    results = {}

    for n in n_range:
        avg_tension = []
        avg_frustration = []
        solve_rate = []
        avg_cascade = []

        for seed in range(n_trials):
            clauses = random_3sat(n, int(ratio * n), seed=seed)

            # Quick solvability check (small n only)
            if n <= 14:
                solutions = find_solutions(clauses, n)
                if not solutions:
                    continue

            tensions = [bit_tension(clauses, n, v) for v in range(n)]
            avg_tension.append(sum(abs(t) for t in tensions) / n)
            avg_frustration.append(sum(1 - abs(t) for t in tensions) / n)

            # Crystallization success
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed:
                    break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                sigma = bit_tension(clauses, n, best, fixed)
                fixed[best] = 1 if sigma >= 0 else 0

            assignment = [fixed.get(v, 0) for v in range(n)]
            success = evaluate(clauses, assignment) == len(clauses)
            solve_rate.append(1 if success else 0)

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        results[n] = {
            'avg_tension': mean(avg_tension),
            'avg_frustration': mean(avg_frustration),
            'solve_rate': mean(solve_rate),
            'tension_x_n': mean(avg_tension) * n,
            'frustration_x_n': mean(avg_frustration) * n,
        }

    return results


# ============================================================
# SYMMETRY BREAKING: Does the system prefer specific patterns?
# ============================================================

def symmetry_analysis(clauses, n, solutions):
    """
    Across all solutions: are there hidden symmetries?
    - Is the average number of 1s always ~n/2 or skewed?
    - Are solutions clustered or spread uniformly?
    """
    if not solutions or len(solutions) < 2:
        return None

    # Average fraction of 1s per solution
    fractions_1 = [sum(s) / n for s in solutions]
    avg_frac = sum(fractions_1) / len(fractions_1)

    # Hamming distances between all pairs of solutions
    distances = []
    for i in range(len(solutions)):
        for j in range(i + 1, len(solutions)):
            d = sum(solutions[i][k] != solutions[j][k] for k in range(n))
            distances.append(d)

    avg_dist = sum(distances) / len(distances) if distances else 0
    min_dist = min(distances) if distances else 0
    max_dist = max(distances) if distances else 0

    # Clustering: are solutions close together or spread out?
    # Expected Hamming distance for random binary strings: n/2
    clustering = 1.0 - (avg_dist / (n / 2)) if n > 0 else 0

    return {
        'avg_fraction_1': avg_frac,
        'n_solutions': len(solutions),
        'avg_hamming': avg_dist,
        'min_hamming': min_dist,
        'max_hamming': max_dist,
        'clustering': clustering,  # >0 = clustered, <0 = spread
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    # ---- Tunneling ----
    print("=" * 70)
    print("EXPERIMENT 1: Tunneling through energy barriers")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if solutions and 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (ratio={ratio}, {len(solutions)} solutions)")
        results = tunneling_analysis(clauses, 12, solutions)

        landed_on_solution = sum(1 for r in results if r.get('is_solution'))
        stuck = [r for r in results if not r.get('is_solution')]

        print(f"  Local search found solution: {landed_on_solution}/{len(results)}")
        if stuck:
            avg_dist = sum(r['distance'] for r in stuck) / len(stuck)
            avg_barrier = sum(r['barrier'] for r in stuck) / len(stuck)
            max_barrier = max(r['barrier'] for r in stuck)
            print(f"  Stuck cases: avg distance to solution = {avg_dist:.1f} bits")
            print(f"  Avg barrier height = {avg_barrier:.1f} clauses")
            print(f"  Max barrier height = {max_barrier} clauses")

            # Show some paths
            for r in stuck[:3]:
                path = " → ".join(str(e) for e in r['path_energies'])
                print(f"    path: {path} (dist={r['distance']}, barrier={r['barrier']})")

    # ---- Diffusion ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Information diffusion")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if solutions and 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (ratio={ratio})")
        print(f"  {'step':>4} | {'affected':>8} | {'Δtension':>9} | {'distance':>8}")
        print("  " + "-" * 40)

        # Average over multiple sources
        all_dists = []
        for source in range(12):
            trace = information_diffusion(clauses, 12, source, 1)
            for t in trace:
                all_dists.append((t['step'], t['distance'], t['change']))

        # Group by step
        by_step = {}
        for step, dist, change in all_dists:
            if step not in by_step:
                by_step[step] = {'dists': [], 'changes': []}
            by_step[step]['dists'].append(dist)
            by_step[step]['changes'].append(change)

        for step in sorted(by_step.keys()):
            avg_dist = sum(by_step[step]['dists']) / len(by_step[step]['dists'])
            avg_change = sum(by_step[step]['changes']) / len(by_step[step]['changes'])
            print(f"  {step:>4} | {'':>8} | {avg_change:>9.4f} | {avg_dist:>8.2f}")

    # ---- Fundamental constants ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Fundamental constants (scaling with n)")
    print("=" * 70)

    results = measure_constants(n_range=[8, 10, 12, 14], ratio=4.27)

    print(f"\n{'n':>4} | {'<|σ|>':>7} | {'<T>':>7} | {'solve%':>7} | "
          f"{'<|σ|>*n':>8} | {'<T>*n':>8}")
    print("-" * 55)
    for n_val in sorted(results.keys()):
        r = results[n_val]
        print(f"{n_val:>4} | {r['avg_tension']:>7.4f} | {r['avg_frustration']:>7.4f} | "
              f"{r['solve_rate']*100:>6.1f}% | "
              f"{r['tension_x_n']:>8.3f} | {r['frustration_x_n']:>8.3f}")

    # ---- Symmetry ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Solution space symmetry")
    print("=" * 70)

    for ratio in [2.0, 3.0, 3.5, 4.0, 4.27]:
        clusterings = []
        avg_fracs = []
        avg_dists = []

        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if not solutions or len(solutions) < 2:
                continue

            sym = symmetry_analysis(clauses, 12, solutions)
            if sym:
                clusterings.append(sym['clustering'])
                avg_fracs.append(sym['avg_fraction_1'])
                avg_dists.append(sym['avg_hamming'])

        if clusterings:
            mean = lambda lst: sum(lst) / len(lst)
            print(f"  ratio={ratio:.2f}: clustering={mean(clusterings):+.3f}, "
                  f"avg_frac_1={mean(avg_fracs):.3f}, "
                  f"avg_hamming={mean(avg_dists):.1f}/12")
