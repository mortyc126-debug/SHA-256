"""
Bit Forces — Force laws, conservation laws, stress-strain.

Questions:
- What is the FORCE between two bits? How does it scale?
- What quantity IS conserved during crystallization?
- What breaks first under stress?
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


def field_temperature(clauses, n, fixed):
    frustrations = []
    for var in range(n):
        if var in fixed:
            continue
        sigma = bit_tension(clauses, n, var, fixed)
        frustrations.append(1.0 - abs(sigma))
    return sum(frustrations) / len(frustrations) if frustrations else 0.0


# ============================================================
# FORCE BETWEEN BITS
# ============================================================

def force(clauses, n, var_i, var_j):
    """
    Force F(i→j): how much does bit i PUSH bit j toward a value?

    F > 0: i pushes j toward 1
    F < 0: i pushes j toward 0
    |F|: strength of push

    Computed as: σ(j | i=1) - σ(j | i=0)
    (how much j's tension changes when i goes from 0 to 1)
    """
    sigma_j_if_0 = bit_tension(clauses, n, var_j, {var_i: 0})
    sigma_j_if_1 = bit_tension(clauses, n, var_j, {var_i: 1})
    return sigma_j_if_1 - sigma_j_if_0


def force_matrix(clauses, n):
    """Full force matrix F[i][j] = force from i on j."""
    F = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                F[i][j] = force(clauses, n, i, j)
    return F


# ============================================================
# NEWTON'S THIRD LAW: Is F(i→j) = -F(j→i)?
# ============================================================

def test_newton_third(clauses, n):
    """Test if forces are symmetric/antisymmetric."""
    F = force_matrix(clauses, n)
    symmetry_errors = []
    antisymmetry_errors = []

    for i in range(n):
        for j in range(i + 1, n):
            if abs(F[i][j]) > 0.001 or abs(F[j][i]) > 0.001:
                # Test F(i→j) = F(j→i) (symmetric)
                symmetry_errors.append(abs(F[i][j] - F[j][i]))
                # Test F(i→j) = -F(j→i) (antisymmetric, Newton's 3rd)
                antisymmetry_errors.append(abs(F[i][j] + F[j][i]))

    return symmetry_errors, antisymmetry_errors


# ============================================================
# FORCE LAW: How does force scale with coupling?
# ============================================================

def force_vs_coupling(clauses, n):
    """Measure force magnitude vs number of shared clauses."""
    # Count shared clauses
    shared = [[0] * n for _ in range(n)]
    for clause in clauses:
        vs = [v for v, s in clause]
        for a in range(len(vs)):
            for b in range(a + 1, len(vs)):
                shared[vs[a]][vs[b]] += 1
                shared[vs[b]][vs[a]] += 1

    F = force_matrix(clauses, n)
    by_coupling = {}
    for i in range(n):
        for j in range(i + 1, n):
            k = shared[i][j]
            if k not in by_coupling:
                by_coupling[k] = []
            by_coupling[k].append(abs(F[i][j]))

    return by_coupling


# ============================================================
# CONSERVATION LAWS: What doesn't change during crystallization?
# ============================================================

def crystallize_with_tracking(clauses, n):
    """
    Crystallize and track EVERYTHING at each step.
    We'll look for conserved quantities.
    """
    fixed = {}
    steps = []

    for step in range(n):
        # Measure everything
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        tensions = {v: bit_tension(clauses, n, v, fixed) for v in unfixed}
        abs_tensions = [abs(t) for t in tensions.values()]

        # Various candidate conserved quantities
        sum_sigma = sum(tensions.values())
        sum_abs_sigma = sum(abs_tensions)
        sum_sigma_sq = sum(t ** 2 for t in tensions.values())
        max_sigma = max(abs_tensions) if abs_tensions else 0
        product_sigma = 1.0
        for t in abs_tensions:
            product_sigma *= max(abs(t), 0.001)

        temp = field_temperature(clauses, n, fixed)
        n_unfixed = len(unfixed)

        # "Energy" = sum of σ² (like kinetic energy = mv²)
        kinetic = sum_sigma_sq
        # "Momentum" = sum of σ (like momentum = mv)
        momentum = sum_sigma

        # Entropy proxy
        if abs_tensions:
            probs = [a / sum_abs_sigma for a in abs_tensions] if sum_abs_sigma > 0 else [1/len(abs_tensions)] * len(abs_tensions)
            entropy_proxy = -sum(p * math.log2(max(p, 1e-10)) for p in probs)
        else:
            entropy_proxy = 0

        steps.append({
            'step': step,
            'n_unfixed': n_unfixed,
            'sum_sigma': sum_sigma,
            'sum_abs_sigma': sum_abs_sigma,
            'sum_sigma_sq': sum_sigma_sq,
            'max_sigma': max_sigma,
            'temperature': temp,
            'momentum': momentum,
            'kinetic': kinetic,
            'entropy_proxy': entropy_proxy,
            # Normalized versions
            'sigma_per_bit': sum_abs_sigma / n_unfixed if n_unfixed > 0 else 0,
            'energy_per_bit': kinetic / n_unfixed if n_unfixed > 0 else 0,
            'momentum_x_n': momentum * n_unfixed,
            'kinetic_x_n': kinetic * n_unfixed,
            'sigma_x_T': sum_abs_sigma * temp,
        })

        # Fix most confident bit
        best_var = max(unfixed, key=lambda v: abs(tensions[v]))
        best_val = 1 if tensions[best_var] >= 0 else 0
        fixed[best_var] = best_val

    return steps


# ============================================================
# STRESS-STRAIN: What breaks under load?
# ============================================================

def stress_strain(n, seed=42):
    """
    Gradually add clauses and measure system properties.
    Like pulling a material and measuring when it breaks.
    """
    random.seed(seed)
    all_clauses = random_3sat(n, int(6.0 * n), seed=seed)

    results = []
    for m in range(1, len(all_clauses) + 1):
        clauses = all_clauses[:m]
        ratio = m / n

        solutions = find_solutions(clauses, n) if n <= 14 else None
        n_solutions = len(solutions) if solutions else -1

        tensions = [bit_tension(clauses, n, v) for v in range(n)]
        avg_abs_sigma = sum(abs(t) for t in tensions) / n
        temp = field_temperature(clauses, n, {})

        # "Strain" = how much the system is forced from equilibrium
        # Use fraction of unsatisfied clauses at tension-guided assignment
        assignment = [1 if t >= 0 else 0 for t in tensions]
        sat = evaluate(clauses, assignment)
        strain = 1.0 - sat / m if m > 0 else 0

        results.append({
            'ratio': ratio,
            'n_clauses': m,
            'n_solutions': n_solutions,
            'avg_tension': avg_abs_sigma,
            'temperature': temp,
            'strain': strain,
        })

    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    # ---- Force analysis ----
    print("=" * 70)
    print("EXPERIMENT 1: Forces between bits")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (ratio={ratio})")

        # Newton's third law
        sym_err, antisym_err = test_newton_third(clauses, n)
        if sym_err:
            print(f"  Symmetry F(i→j) = F(j→i): "
                  f"avg error = {sum(sym_err)/len(sym_err):.4f}")
            print(f"  Antisymmetry F(i→j) = -F(j→i): "
                  f"avg error = {sum(antisym_err)/len(antisym_err):.4f}")
            # Which is closer to zero?
            sym_total = sum(sym_err)
            antisym_total = sum(antisym_err)
            if sym_total < antisym_total:
                print(f"  → Forces are SYMMETRIC (not Newton's 3rd)")
            else:
                print(f"  → Forces obey NEWTON'S 3RD LAW (antisymmetric)")

        # Force vs coupling
        by_coup = force_vs_coupling(clauses, n)
        print(f"\n  Force magnitude vs shared clauses:")
        print(f"  {'shared':>6} | {'avg |F|':>8} | {'max |F|':>8} | {'n':>4}")
        print("  " + "-" * 35)
        for k in sorted(by_coup.keys()):
            vals = by_coup[k]
            print(f"  {k:>6} | {sum(vals)/len(vals):>8.4f} | "
                  f"{max(vals):>8.4f} | {len(vals):>4}")

    # ---- Conservation laws ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Search for conservation laws")
    print("=" * 70)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(50):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if solutions and 2 < len(solutions) < 100:
                break

        steps = crystallize_with_tracking(clauses, n)
        print(f"\n## {label} (ratio={ratio})")
        print(f"{'step':>4} | {'Σσ':>7} | {'Σ|σ|':>7} | {'Σσ²':>7} | "
              f"{'T':>6} | {'|σ|/bit':>7} | {'σ²/bit':>7} | "
              f"{'Σ|σ|·T':>7} | {'S_proxy':>7}")
        print("-" * 80)

        for s in steps:
            print(f"{s['step']:>4} | {s['sum_sigma']:>+7.3f} | "
                  f"{s['sum_abs_sigma']:>7.3f} | {s['sum_sigma_sq']:>7.3f} | "
                  f"{s['temperature']:>6.3f} | {s['sigma_per_bit']:>7.3f} | "
                  f"{s['energy_per_bit']:>7.3f} | "
                  f"{s['sigma_x_T']:>7.3f} | {s['entropy_proxy']:>7.3f}")

    # Statistical test: which quantity is most conserved?
    print("\n--- Which quantity varies LEAST during crystallization? ---")

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        variations = {
            'Σσ': [], 'Σ|σ|': [], 'Σσ²': [], 'T': [],
            '|σ|/bit': [], 'σ²/bit': [], 'Σ|σ|·T': [],
        }

        for seed in range(100):
            clauses = random_3sat(n, int(ratio * n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions:
                continue

            steps = crystallize_with_tracking(clauses, n)
            if len(steps) < 3:
                continue

            # Use only middle steps (skip first and last where things are trivial)
            mid = steps[1:-2] if len(steps) > 3 else steps

            for key, field in [
                ('Σσ', 'sum_sigma'), ('Σ|σ|', 'sum_abs_sigma'),
                ('Σσ²', 'sum_sigma_sq'), ('T', 'temperature'),
                ('|σ|/bit', 'sigma_per_bit'), ('σ²/bit', 'energy_per_bit'),
                ('Σ|σ|·T', 'sigma_x_T'),
            ]:
                vals = [s[field] for s in mid]
                if vals:
                    mean = sum(vals) / len(vals)
                    if mean != 0:
                        cv = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) / abs(mean)
                    else:
                        cv = 0
                    variations[key].append(cv)

        print(f"\n  {label}: Coefficient of variation (lower = more conserved):")
        ranked = []
        for key, cvs in variations.items():
            if cvs:
                avg_cv = sum(cvs) / len(cvs)
                ranked.append((key, avg_cv))
        ranked.sort(key=lambda x: x[1])
        for key, cv in ranked:
            bar = "█" * int(cv * 30)
            conserved = " ← MOST CONSERVED" if cv == ranked[0][1] else ""
            print(f"    {key:>8}: CV = {cv:.4f} {bar}{conserved}")

    # ---- Stress-strain ----
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Stress-strain curve")
    print("=" * 70)

    results = stress_strain(n, seed=42)
    print(f"{'ratio':>6} | {'#sol':>6} | {'|σ|':>6} | {'T':>6} | "
          f"{'strain':>6} | visual")
    print("-" * 60)

    for r in results:
        if r['ratio'] * 10 % 5 < 1:  # print every 0.5
            bar_strain = "█" * int(r['strain'] * 30)
            nsol = str(r['n_solutions']) if r['n_solutions'] >= 0 else "?"
            print(f"{r['ratio']:>6.1f} | {nsol:>6} | {r['avg_tension']:>6.3f} | "
                  f"{r['temperature']:>6.3f} | {r['strain']:>6.3f} | {bar_strain}")
