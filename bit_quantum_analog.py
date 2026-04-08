"""
QUANTUM ANALOGY: SAT bits as quantum particles
═══════════════════════════════════════════════

From sub-bit physics we found:
  - 75% deterministic (eigenstate-like), 25% random (superposition-like)
  - Position x ∈ [0,1] ↔ probability amplitude
  - Rounding ↔ wave function collapse
  - Temperature T = 0.75 ↔ quantum/classical boundary

FIVE DEEP EXPERIMENTS:

1. ENTANGLEMENT — Are noise bits correlated across runs?
   (Like EPR: measuring one fixes another)

2. COLLAPSE DYNAMICS — Universal curve x(t) → {0,1}?
   (Like decoherence: smooth transition to classical)

3. BORN RULE — Does P(bit=1) = f(x)? What is f?
   (In QM: P = |ψ|². What's the SAT version?)

4. UNCERTAINTY RELATION — Δx · Δv ≥ const?
   (Heisenberg for computation)

5. MEASUREMENT BACKACTION — Does observing one bit
   change others? (Like quantum measurement disturbance)
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


def run_physics(clauses, n, n_steps, noise_seed):
    """Run physics simulation, return trajectory."""
    np.random.seed(noise_seed)
    m = len(clauses)

    x = np.array([0.5 + 0.05 * compute_tension(clauses, n, v)
                  for v in range(n)])
    vel = np.zeros(n)

    trajectory = [x.copy()]
    vel_trajectory = [vel.copy()]

    for step in range(n_steps):
        progress = step / n_steps
        T = 0.25 * math.exp(-4.0 * progress) + 0.0001
        crystal = 3.0 * progress

        forces = np.zeros(n)
        for clause in clauses:
            prod = 1.0; lits = []
            for v, s in clause:
                lit = x[v] if s == 1 else (1.0 - x[v])
                lits.append((v, lit, s))
                prod *= max(1.0 - lit, 1e-12)
            if prod < 0.001: continue
            w = math.sqrt(prod)
            for v, lit, s in lits:
                term = max(1.0 - lit, 1e-12)
                forces[v] += s * w * (prod / term)

        for v in range(n):
            if x[v] > 0.5: forces[v] += crystal * (1.0 - x[v])
            else: forces[v] -= crystal * x[v]

        noise = np.random.normal(0, T, n)
        vel = 0.93 * vel + (forces + noise) * 0.05
        x = np.clip(x + vel * 0.05, 0, 1)

        if step % 10 == 0:
            trajectory.append(x.copy())
            vel_trajectory.append(vel.copy())

    return np.array(trajectory), np.array(vel_trajectory)


# ============================================================
# 1. ENTANGLEMENT: Are noise bits correlated?
# ============================================================

def experiment_entanglement():
    print("=" * 70)
    print("1. ENTANGLEMENT: Are noise bits correlated across runs?")
    print("=" * 70)

    print("""
    Run same instance 50 times with different noise seeds.
    For 'random' bits (outcome varies): are outcomes CORRELATED?
    If x2 goes to 1, does x5 always go to 0? → ENTANGLED
    If independent → NOT entangled
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+76000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        n_runs = 50
        finals = np.zeros((n_runs, n))

        for run in range(n_runs):
            traj, _ = run_physics(clauses, n, 400, noise_seed=run*997+seed)
            finals[run] = traj[-1]

        # Identify random bits (non-deterministic)
        p_high = np.mean(finals > 0.5, axis=0)
        random_bits = [v for v in range(n) if 0.1 < p_high[v] < 0.9]
        det_bits = [v for v in range(n) if p_high[v] >= 0.9 or p_high[v] <= 0.1]

        if len(random_bits) < 2:
            continue

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Deterministic: {len(det_bits)} bits, "
              f"Random: {len(random_bits)} bits")

        # Correlation matrix among random bits
        # Convert to binary
        binary = (finals > 0.5).astype(float)

        print(f"\n    Correlation matrix (random bits):")
        print(f"    {'':>5}", end="")
        for v in random_bits[:6]:
            print(f"  x{v:>2}", end="")
        print()

        entangled_pairs = 0
        total_pairs = 0

        for i, vi in enumerate(random_bits[:6]):
            print(f"    x{vi:>2} ", end="")
            for j, vj in enumerate(random_bits[:6]):
                if i == j:
                    print(f" 1.00", end="")
                    continue
                # Correlation between outcomes
                bi = binary[:, vi]
                bj = binary[:, vj]
                mean_i = np.mean(bi)
                mean_j = np.mean(bj)
                if np.std(bi) > 0 and np.std(bj) > 0:
                    corr = np.corrcoef(bi, bj)[0, 1]
                else:
                    corr = 0
                print(f" {corr:>+.2f}", end="")

                if j > i:
                    total_pairs += 1
                    if abs(corr) > 0.3:
                        entangled_pairs += 1
            print()

        print(f"\n    Entangled pairs (|corr|>0.3): "
              f"{entangled_pairs}/{total_pairs}")
        if total_pairs > 0:
            print(f"    Entanglement rate: "
                  f"{100*entangled_pairs/total_pairs:.0f}%")

        break


# ============================================================
# 2. COLLAPSE DYNAMICS: Universal curve?
# ============================================================

def experiment_collapse():
    print("\n" + "=" * 70)
    print("2. COLLAPSE DYNAMICS: Is there a universal collapse curve?")
    print("=" * 70)

    print("""
    Track |x - 0.5| over time for all bits.
    In QM, decoherence follows exp(-t/T_decoherence).
    What curve does SAT collapse follow?
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+77000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        traj, vel_traj = run_physics(clauses, n, 500, noise_seed=42)
        n_checkpoints = traj.shape[0]

        # Average |x - 0.5| across all bits at each time
        avg_dist = np.mean(np.abs(traj - 0.5), axis=1)

        # Separate deterministic vs random
        # Run multiple times to classify
        p_highs = np.zeros(n)
        for run in range(20):
            t, _ = run_physics(clauses, n, 400, noise_seed=run*100+seed)
            p_highs += (t[-1] > 0.5).astype(float)
        p_highs /= 20
        det_mask = (p_highs > 0.9) | (p_highs < 0.1)
        rand_mask = ~det_mask

        if np.sum(det_mask) > 0:
            avg_det = np.mean(np.abs(traj[:, det_mask] - 0.5), axis=1)
        else:
            avg_det = np.zeros(n_checkpoints)
        if np.sum(rand_mask) > 0:
            avg_rand = np.mean(np.abs(traj[:, rand_mask] - 0.5), axis=1)
        else:
            avg_rand = np.zeros(n_checkpoints)

        print(f"\n  n={n}, seed={seed} ({np.sum(det_mask)} det, "
              f"{np.sum(rand_mask)} rand):")
        print(f"  {'step':>6} | {'all |x-.5|':>10} | {'det |x-.5|':>10} | "
              f"{'rand |x-.5|':>10}")
        print("  " + "-" * 50)

        for i in range(0, n_checkpoints, max(1, n_checkpoints // 12)):
            step = i * 10
            print(f"  {step:>6} | {avg_dist[i]:>10.3f} | "
                  f"{avg_det[i]:>10.3f} | {avg_rand[i]:>10.3f}")

        # Fit: does |x-0.5| follow sigmoid, exponential, or power law?
        # Use late-time data (step > 100)
        late = [(i*10, avg_dist[i]) for i in range(10, n_checkpoints)]
        if late:
            # Sigmoid fit: |x-0.5| = 0.5 / (1 + exp(-a(t-t0)))
            times = [t for t, _ in late]
            vals = [v for _, v in late]
            # Check if it's sigmoid-like
            mid_val = 0.25  # halfway to 0.5
            mid_idx = min(range(len(vals)), key=lambda i: abs(vals[i] - mid_val))
            print(f"\n  Collapse midpoint (|x-.5|=0.25): step ≈ {times[mid_idx]}")
            print(f"  Final |x-.5|: {vals[-1]:.3f} (max = 0.5)")

        break


# ============================================================
# 3. BORN RULE: P(bit=1) = f(x)?
# ============================================================

def experiment_born_rule():
    print("\n" + "=" * 70)
    print("3. BORN RULE ANALOG: P(bit=1) = f(x)?")
    print("=" * 70)

    print("""
    In QM: P(outcome) = |ψ|²
    In SAT: P(bit=1) should relate to continuous position x.
    Measure at DIFFERENT time points during simulation.
    Is P(bit=1 | x at time t) = x? Or x²? Or something else?
    """)

    random.seed(42)
    n = 14

    # Collect data: at various times, record x value and eventual outcome
    data_by_time = {}  # time -> list of (x_value, final_binary)

    for seed in range(30):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+78000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        # Run 20 times to get final outcome statistics
        for run in range(20):
            traj, _ = run_physics(clauses, n, 400, noise_seed=run*50+seed)
            final = traj[-1]

            # Record intermediate x values and final outcomes
            for ti, t_frac in enumerate([0.1, 0.2, 0.3, 0.5, 0.7]):
                t_idx = int(t_frac * (traj.shape[0] - 1))
                t_key = t_frac
                if t_key not in data_by_time:
                    data_by_time[t_key] = []
                for v in range(n):
                    x_at_t = traj[t_idx, v]
                    final_val = 1 if final[v] > 0.5 else 0
                    data_by_time[t_key].append((x_at_t, final_val))

    # Analysis: bin by x, compute P(final=1)
    for t_frac in sorted(data_by_time.keys()):
        data = data_by_time[t_frac]
        bins = [(i/10, (i+1)/10) for i in range(10)]

        print(f"\n  At t={t_frac:.1f} through simulation:")
        print(f"  {'x range':>12} | {'P(final=1)':>10} | {'x_mid':>6} | "
              f"{'P=x?':>5} | {'P=x²?':>6} | {'n':>5}")
        print("  " + "-" * 55)

        for lo, hi in bins:
            subset = [(x, f) for x, f in data if lo <= x < hi]
            if len(subset) < 5:
                continue
            p1 = sum(f for _, f in subset) / len(subset)
            x_mid = (lo + hi) / 2
            p_linear = x_mid
            p_squared = x_mid ** 2

            print(f"  [{lo:.1f}, {hi:.1f}) | {p1:>10.3f} | {x_mid:>6.2f} | "
                  f"{abs(p1 - p_linear):>5.3f} | {abs(p1 - p_squared):>6.3f} | "
                  f"{len(subset):>5}")


# ============================================================
# 4. UNCERTAINTY RELATION: Δx · Δv ≥ const?
# ============================================================

def experiment_uncertainty():
    print("\n" + "=" * 70)
    print("4. UNCERTAINTY RELATION: Δx · Δv ≥ const?")
    print("=" * 70)

    print("""
    Heisenberg: Δx · Δp ≥ ℏ/2
    For SAT bits: Δx = uncertainty in position, Δv = uncertainty in velocity.
    Measure across 50 runs of the same instance.
    Is there a lower bound on Δx · Δv?
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+79000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        n_runs = 50
        # Measure at step 200 (mid-simulation)
        mid_x = np.zeros((n_runs, n))
        mid_v = np.zeros((n_runs, n))

        for run in range(n_runs):
            traj, vtraj = run_physics(clauses, n, 400, noise_seed=run*71+seed)
            mid_idx = traj.shape[0] // 2  # middle of simulation
            mid_x[run] = traj[mid_idx]
            mid_v[run] = vtraj[mid_idx]

        # For each variable: compute Δx and Δv
        print(f"\n  n={n}, seed={seed} (measured at mid-simulation):")
        print(f"  {'var':>5} | {'Δx':>6} | {'Δv':>6} | {'Δx·Δv':>8} | "
              f"{'<x>':>6} | {'type':>6}")
        print("  " + "-" * 50)

        products = []
        det_products = []
        rand_products = []

        for v in range(n):
            dx = np.std(mid_x[:, v])
            dv = np.std(mid_v[:, v])
            product = dx * dv
            mean_x = np.mean(mid_x[:, v])

            # Classify: deterministic or random
            p_high = np.mean(mid_x[:, v] > 0.5)
            is_det = (p_high > 0.9 or p_high < 0.1)
            vtype = "DET" if is_det else "RAND"

            products.append(product)
            if is_det:
                det_products.append(product)
            else:
                rand_products.append(product)

            print(f"  x{v:>3} | {dx:>6.4f} | {dv:>6.4f} | {product:>8.6f} | "
                  f"{mean_x:>6.3f} | {vtype:>6}")

        min_product = min(products) if products else 0
        print(f"\n  Minimum Δx·Δv: {min_product:.6f}")
        if det_products:
            print(f"  DET average:   {sum(det_products)/len(det_products):.6f}")
        if rand_products:
            print(f"  RAND average:  {sum(rand_products)/len(rand_products):.6f}")
        if det_products and rand_products:
            ratio = (sum(rand_products)/len(rand_products)) / \
                    (sum(det_products)/len(det_products))
            print(f"  RAND/DET ratio: {ratio:.1f}×")

        break


# ============================================================
# 5. MEASUREMENT BACKACTION: Fixing one bit changes others
# ============================================================

def experiment_backaction():
    print("\n" + "=" * 70)
    print("5. MEASUREMENT BACKACTION: Does fixing one bit change others?")
    print("=" * 70)

    print("""
    In QM: measuring one entangled particle instantly changes the other.
    In SAT: if we FIX one variable mid-simulation, do other variables
    change their trajectory?

    Experiment: Run physics halfway. Then fix one 'random' bit.
    Compare subsequent trajectories of OTHER bits with/without the fix.
    """)

    random.seed(42)
    n = 14

    for seed in range(10):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+80000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        # First identify random bits
        p_highs = np.zeros(n)
        for run in range(20):
            t, _ = run_physics(clauses, n, 400, noise_seed=run*100+seed)
            p_highs += (t[-1] > 0.5).astype(float)
        p_highs /= 20
        random_bits = [v for v in range(n) if 0.15 < p_highs[v] < 0.85]
        if not random_bits:
            continue

        fix_var = random_bits[0]
        print(f"\n  n={n}, seed={seed}:")
        print(f"    Fixing x{fix_var} (P(>0.5) = {p_highs[fix_var]:.2f})")

        # Run WITHOUT fix
        traj_free, _ = run_physics(clauses, n, 400, noise_seed=42)
        free_final = traj_free[-1]

        # Run WITH fix: force fix_var = sol[fix_var] at step 200
        np.random.seed(42)
        x = np.array([0.5 + 0.05 * compute_tension(clauses, n, v)
                      for v in range(n)])
        vel = np.zeros(n)
        m = len(clauses)

        for step in range(400):
            progress = step / 400
            T = 0.25 * math.exp(-4.0 * progress) + 0.0001
            crystal = 3.0 * progress
            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0; lits = []
                for v, s in clause:
                    lit = x[v] if s == 1 else (1.0 - x[v])
                    lits.append((v, lit, s))
                    prod *= max(1.0 - lit, 1e-12)
                if prod < 0.001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1.0 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)
            for v in range(n):
                if x[v] > 0.5: forces[v] += crystal * (1.0 - x[v])
                else: forces[v] -= crystal * x[v]
            noise = np.random.normal(0, T, n)
            vel = 0.93 * vel + (forces + noise) * 0.05
            x = np.clip(x + vel * 0.05, 0, 1)

            # FIX: at step 200, collapse fix_var
            if step == 200:
                x[fix_var] = float(sol[fix_var])
                vel[fix_var] = 0.0

        fixed_final = x

        # Compare: how much did OTHER variables change?
        print(f"\n    {'var':>5} | {'free':>6} | {'fixed':>6} | {'delta':>6} | "
              f"{'sol':>3} | {'backaction':>10}")
        print("    " + "-" * 50)

        total_backaction = 0
        for v in range(n):
            if v == fix_var:
                continue
            delta = abs(fixed_final[v] - free_final[v])
            total_backaction += delta
            if delta > 0.05:
                ba = "CHANGED" if delta > 0.1 else "slight"
            else:
                ba = ""
            print(f"    x{v:>3} | {free_final[v]:>6.3f} | {fixed_final[v]:>6.3f} | "
                  f"{delta:>6.3f} | {sol[v]:>3} | {ba:>10}")

        print(f"\n    Total backaction: {total_backaction:.3f}")
        print(f"    Average per bit: {total_backaction/(n-1):.4f}")
        print(f"    Affected bits (Δ>0.1): "
              f"{sum(1 for v in range(n) if v != fix_var and abs(fixed_final[v]-free_final[v])>0.1)}")

        break


# ============================================================
# SYNTHESIS
# ============================================================

def synthesis():
    print("\n" + "=" * 70)
    print("SYNTHESIS: The Quantum SAT Dictionary")
    print("=" * 70)
    print("""
    Quantum Mechanics          SAT Bit Mechanics
    ─────────────────          ─────────────────
    Wave function ψ        ↔   Position x ∈ [0,1]
    |ψ|² = probability     ↔   P(bit=1) = f(x)
    Measurement → collapse ↔   Rounding x → {0,1}
    Eigenstate             ↔   Deterministic bit (75%)
    Superposition          ↔   Random bit (25%)
    Entanglement           ↔   Correlated noise outcomes
    Decoherence            ↔   Crystallization (x → 0 or 1)
    Heisenberg Δx·Δp≥ℏ/2  ↔   Δx·Δv ≥ ? (to be measured)
    Measurement backaction ↔   Fixing bit changes neighbors
    Born rule P=|ψ|²       ↔   P(1) = ? (linear? quadratic?)
    Planck constant ℏ      ↔   ε = 1/14 (information quantum)
    Temperature             ↔   T = 0.75 (thermal boundary)

    The 75/25 deterministic/random split IS the temperature:
    T = fraction of bits in "superposition" = 0.25 noise fraction
    1-T = fraction in "eigenstates" = 0.75 signal fraction
    """)


if __name__ == "__main__":
    experiment_entanglement()
    experiment_collapse()
    experiment_born_rule()
    experiment_uncertainty()
    experiment_backaction()
    synthesis()
