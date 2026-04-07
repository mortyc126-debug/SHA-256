"""
Bit Phases — Phase diagram, magnetism, critical phenomena.

Bits as spins: each bit "wants" to be 0 or 1.
The system has net magnetization.
Near the SAT threshold there should be a phase transition.
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
    if total == 0:
        return 0.0
    return (p1 - p0) / total


# ============================================================
# MAGNETIZATION — net "spin" of the system
# ============================================================

def magnetization(clauses, n):
    """
    M = (1/n) * Σ σ(var)

    If all bits agree on direction → |M| ≈ 1 (ferromagnetic)
    If bits cancel out → M ≈ 0 (paramagnetic/antiferromagnetic)
    """
    tensions = [bit_tension(clauses, n, v) for v in range(n)]
    return sum(tensions) / n


def abs_magnetization(clauses, n):
    """Average of |σ|, not of σ. Measures how "decided" bits are."""
    tensions = [bit_tension(clauses, n, v) for v in range(n)]
    return sum(abs(t) for t in tensions) / n


def magnetization_from_solutions(solutions, n):
    """
    Ground truth magnetization: average bit value across solutions.
    M_true = (1/n) * Σ (2*P(bit=1) - 1)
    """
    if not solutions:
        return 0.0
    m = 0.0
    for var in range(n):
        p1 = sum(s[var] for s in solutions) / len(solutions)
        m += (2 * p1 - 1)
    return m / n


# ============================================================
# SUSCEPTIBILITY — how much M changes with perturbation
# ============================================================

def susceptibility(clauses, n, n_samples=50):
    """
    χ = Var(M) across random partial observations.
    High χ = system is sensitive (near phase transition).
    Low χ = system is stable.
    """
    magnetizations = []
    for _ in range(n_samples):
        # Perturb: fix one random bit, measure M change
        var = random.randint(0, n - 1)
        val = random.randint(0, 1)

        tensions = [bit_tension(clauses, n, v, {var: val}) for v in range(n) if v != var]
        m = sum(tensions) / len(tensions) if tensions else 0
        magnetizations.append(m)

    mean = sum(magnetizations) / len(magnetizations)
    variance = sum((m - mean) ** 2 for m in magnetizations) / len(magnetizations)
    return variance


# ============================================================
# CORRELATION LENGTH — how far does influence propagate
# ============================================================

def correlation_length(clauses, n):
    """
    ξ = average distance at which transmission drops below threshold.

    Build adjacency from clauses, compute distance matrix,
    then measure how transmission decays with distance.
    """
    # Adjacency
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                adj[vs[i]].add(vs[j])
                adj[vs[j]].add(vs[i])

    # BFS distances
    def bfs_dist(start):
        dist = {start: 0}
        queue = [start]
        idx = 0
        while idx < len(queue):
            curr = queue[idx]
            idx += 1
            for nb in adj[curr]:
                if nb not in dist:
                    dist[nb] = dist[curr] + 1
                    queue.append(nb)
        return dist

    # Transmission at each distance
    by_dist = {}
    for i in range(n):
        dists = bfs_dist(i)
        sigma_i_0 = [bit_tension(clauses, n, j, {i: 0}) for j in range(n) if j != i]
        sigma_i_1 = [bit_tension(clauses, n, j, {i: 1}) for j in range(n) if j != i]

        j_idx = 0
        for j in range(n):
            if j == i:
                continue
            d = dists.get(j, 99)
            trans = abs(sigma_i_1[j_idx] - sigma_i_0[j_idx]) / 2
            if d not in by_dist:
                by_dist[d] = []
            by_dist[d].append(trans)
            j_idx += 1

    return by_dist


# ============================================================
# SPECIFIC HEAT — how energy changes with "temperature"
# ============================================================

def specific_heat(clauses, n, n_samples=500):
    """
    Generate random assignments at different "temperatures"
    (controlled by how many bits are random vs guided by tension).

    C_v = dE/dT = variance of energy at given T.
    Peak in C_v → phase transition.
    """
    results = []

    for noise in [i * 0.1 for i in range(11)]:
        # noise=0: all bits follow tension (cold)
        # noise=1: all bits random (hot)
        energies = []
        for _ in range(n_samples):
            assignment = []
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                if random.random() < noise:
                    assignment.append(random.randint(0, 1))
                else:
                    assignment.append(1 if sigma >= 0 else 0)
            e = len(clauses) - evaluate(clauses, assignment)
            energies.append(e)

        mean_e = sum(energies) / len(energies)
        var_e = sum((e - mean_e) ** 2 for e in energies) / len(energies)

        results.append({
            'noise': noise,
            'mean_energy': mean_e,
            'energy_variance': var_e,
            'specific_heat': var_e,  # C_v ∝ Var(E)
        })

    return results


# ============================================================
# MASS — inertia of each bit
# ============================================================

def bit_mass(clauses, n, var):
    """
    Mass = resistance to change.
    How much energy does it cost to flip this bit from its preferred state?

    Heavy bits: deeply embedded, many consequences from flipping.
    Light bits: peripheral, flipping doesn't matter much.
    """
    sigma = bit_tension(clauses, n, var)
    preferred = 1 if sigma >= 0 else 0
    anti = 1 - preferred

    # Energy difference between preferred and anti-preferred
    # averaged over random states of other bits
    diffs = []
    for _ in range(100):
        others = {v: random.randint(0, 1) for v in range(n) if v != var}
        assign_pref = [others.get(v, preferred if v == var else 0) for v in range(n)]
        assign_pref[var] = preferred
        assign_anti = list(assign_pref)
        assign_anti[var] = anti

        e_pref = len(clauses) - evaluate(clauses, assign_pref)
        e_anti = len(clauses) - evaluate(clauses, assign_anti)
        diffs.append(e_anti - e_pref)

    return sum(diffs) / len(diffs)


# ============================================================
# MAIN EXPERIMENTS
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    # ---- Experiment 1: Phase diagram ----
    print("=" * 70)
    print("EXPERIMENT 1: Phase diagram across clause ratio")
    print("=" * 70)
    print(f"\n{'ratio':>6} | {'M':>7} | {'|M|':>7} | {'|σ|_avg':>7} | "
          f"{'χ':>7} | {'solvable':>8} | {'#sol':>6}")
    print("-" * 65)

    for ratio_10 in range(15, 55, 2):
        ratio = ratio_10 / 10.0
        avg_M = []
        avg_absM = []
        avg_absSigma = []
        avg_chi = []
        solvable_count = 0
        total = 0
        avg_nsol = []

        for seed in range(100):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            total += 1

            M = magnetization(clauses, n)
            absM = abs_magnetization(clauses, n)
            chi = susceptibility(clauses, n, n_samples=20)

            avg_M.append(M)
            avg_absM.append(abs(M))
            avg_absSigma.append(absM)
            avg_chi.append(chi)

            if solutions:
                solvable_count += 1
                avg_nsol.append(len(solutions))

        mean = lambda lst: sum(lst) / len(lst) if lst else 0
        print(f"{ratio:>6.1f} | {mean(avg_M):>+7.3f} | {mean(avg_absM):>7.3f} | "
              f"{mean(avg_absSigma):>7.3f} | {mean(avg_chi):>7.4f} | "
              f"{solvable_count:>8} | {mean(avg_nsol):>6.0f}")

    # ---- Experiment 2: Correlation length ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Correlation length (transmission vs distance)")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and len(solutions) < 100:
                break

        by_dist = correlation_length(clauses, n)
        print(f"\n  {label} (ratio={ratio}):")
        print(f"  {'dist':>6} | {'avg_trans':>9} | {'max_trans':>9} | {'n_pairs':>7}")
        print("  " + "-" * 40)
        for d in sorted(by_dist.keys()):
            if d < 5:
                vals = by_dist[d]
                avg = sum(vals) / len(vals)
                mx = max(vals)
                print(f"  {d:>6} | {avg:>9.4f} | {mx:>9.4f} | {len(vals):>7}")

    # ---- Experiment 3: Specific heat ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Specific heat curve")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and len(solutions) < 100:
                break

        results = specific_heat(clauses, n)
        print(f"\n  {label} (ratio={ratio}):")
        print(f"  {'noise':>6} | {'<E>':>8} | {'C_v':>8} | visual")
        print("  " + "-" * 45)
        max_cv = max(r['specific_heat'] for r in results)
        for r in results:
            bar = "█" * int(r['specific_heat'] / max(0.01, max_cv) * 30)
            print(f"  {r['noise']:>6.1f} | {r['mean_energy']:>8.2f} | "
                  f"{r['specific_heat']:>8.3f} | {bar}")

    # ---- Experiment 4: Bit mass spectrum ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Mass spectrum of bits")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and len(solutions) < 100:
                break

        masses = []
        for var in range(n):
            m = bit_mass(clauses, n, var)
            masses.append((var, m))

        masses.sort(key=lambda x: -x[1])
        print(f"\n  {label} (ratio={ratio}):")
        print(f"  {'var':>5} | {'mass':>8} | {'|σ|':>6} | visual")
        print("  " + "-" * 40)
        max_mass = max(m for _, m in masses)
        for var, m in masses:
            sigma = abs(bit_tension(clauses, n, var))
            bar = "█" * int(m / max(0.01, max_mass) * 20)
            print(f"  x{var:>2}  | {m:>8.3f} | {sigma:>6.3f} | {bar}")

        avg_mass = sum(m for _, m in masses) / n
        print(f"\n  Average mass: {avg_mass:.3f}")
