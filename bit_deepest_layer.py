"""
THE DEEPEST LAYER: What lies beneath the information quantum?
═════════════════════════════════════════════════════════════

We've found:
  ε = 1/14 — information quantum (one clause vote)
  T = 0.75 — temperature (DET/RAND boundary)
  Decoherence — continuous → discrete transition

NOW: What's inside ε? What creates the force?

FIVE EXPERIMENTS:

1. ANATOMY OF A 3-BODY INTERACTION
   A clause connects 3 variables. What happens INSIDE this coupling?
   Is it decomposable into 2-body? Or truly 3-body?

2. SPEED OF INFORMATION
   Fix one variable. How fast does the effect reach distance-d neighbors?
   Is there a "speed of light" for bit information?

3. PHASE SPACE PORTRAIT
   Plot (x, v) for each variable during simulation.
   Are there attractors? Limit cycles? Chaos?

4. CONSERVATION LAWS
   Is anything conserved during the simulation?
   Total energy? Total momentum? Information?

5. ENTROPY FLOW
   System goes from disorder (x≈0.5) to order (x∈{0,1}).
   Entropy decreases. WHERE does it go?
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


def run_physics_detailed(clauses, n, n_steps, seed=42):
    """Run physics with FULL recording of everything."""
    np.random.seed(seed)
    m = len(clauses)

    x = np.array([0.5 + 0.05 * compute_tension(clauses, n, v)
                  for v in range(n)])
    vel = np.zeros(n)

    # Record everything
    record = {
        'x': [x.copy()],
        'v': [vel.copy()],
        'force': [],
        'energy': [],
        'entropy': [],
        'momentum': [],
        'temperature': [],
    }

    for step in range(n_steps):
        progress = step / n_steps
        T = 0.25 * math.exp(-4.0 * progress) + 0.0001
        crystal = 3.0 * progress

        forces = np.zeros(n)
        clause_energies = []

        for clause in clauses:
            prod = 1.0; lits = []
            for v, s in clause:
                lit = x[v] if s == 1 else (1.0 - x[v])
                lits.append((v, lit, s))
                prod *= max(1.0 - lit, 1e-12)
            clause_energies.append(prod)  # unsatisfaction
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

        if step % 5 == 0:
            record['x'].append(x.copy())
            record['v'].append(vel.copy())
            record['force'].append(forces.copy())

            # Energy = sum of clause unsatisfaction
            E = sum(clause_energies)
            record['energy'].append(E)

            # Entropy = -Σ p log p where p = x, 1-p = 1-x
            S = 0
            for v in range(n):
                p = np.clip(x[v], 1e-10, 1-1e-10)
                S -= p * np.log2(p) + (1-p) * np.log2(1-p)
            record['entropy'].append(S)

            # Total momentum
            record['momentum'].append(np.sum(vel))
            record['temperature'].append(T)

    return record


# ============================================================
# 1. ANATOMY OF A 3-BODY INTERACTION
# ============================================================

def experiment_3body():
    print("=" * 70)
    print("1. ANATOMY OF A 3-BODY INTERACTION")
    print("=" * 70)

    print("""
    A clause (l₁ ∨ l₂ ∨ l₃) creates a 3-body coupling.
    Question: is it decomposable into 3 pairwise (2-body) forces?
    Or is there a genuine 3-body component?

    Method: Compute force from a clause on var v.
    Compare with sum of pairwise forces from (v,w) pairs.
    The RESIDUAL = 3-body component.
    """)

    random.seed(42)
    n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+81000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        # Pick a clause and analyze its force decomposition
        for ci in range(min(5, len(clauses))):
            clause = clauses[ci]
            v0, s0 = clause[0]
            v1, s1 = clause[1]
            v2, s2 = clause[2]

            # Sweep x[v0] and compute full 3-body force vs 2-body approximation
            x_test = np.array([float(sol[v]) for v in range(n)])

            three_body_forces = []
            two_body_forces = []

            for xi in np.linspace(0.1, 0.9, 9):
                x_test[v0] = xi

                # Full 3-body force on v0
                lit0 = xi if s0 == 1 else (1.0 - xi)
                lit1 = x_test[v1] if s1 == 1 else (1.0 - x_test[v1])
                lit2 = x_test[v2] if s2 == 1 else (1.0 - x_test[v2])

                prod = (1-lit0) * (1-lit1) * (1-lit2)
                term0 = max(1-lit0, 1e-12)
                f3 = s0 * math.sqrt(max(prod, 0)) * (prod / term0)

                # 2-body approximation: force from (v0,v1) + force from (v0,v2)
                # (v0,v1) pair: treat as 2-SAT clause
                prod_01 = (1-lit0) * (1-lit1)
                f_01 = s0 * math.sqrt(max(prod_01, 0)) * (1-lit1)

                prod_02 = (1-lit0) * (1-lit2)
                f_02 = s0 * math.sqrt(max(prod_02, 0)) * (1-lit2)

                f2 = f_01 + f_02

                three_body_forces.append(f3)
                two_body_forces.append(f2)

            residual = [f3 - f2 for f3, f2 in
                       zip(three_body_forces, two_body_forces)]
            avg_3 = sum(abs(f) for f in three_body_forces) / len(three_body_forces)
            avg_r = sum(abs(r) for r in residual) / len(residual)

            if avg_3 > 0.001:
                ratio = avg_r / avg_3
                print(f"  Clause {ci}: 3-body = {avg_3:.4f}, "
                      f"residual = {avg_r:.4f}, "
                      f"3-body fraction = {100*ratio:.1f}%")

        break

    # Summary
    print(f"\n  If 3-body fraction ≈ 0%: interaction is purely pairwise")
    print(f"  If 3-body fraction > 0%: genuine 3-body coupling exists")


# ============================================================
# 2. SPEED OF INFORMATION
# ============================================================

def experiment_speed():
    print("\n" + "=" * 70)
    print("2. SPEED OF INFORMATION: How fast do effects propagate?")
    print("=" * 70)

    print("""
    Build the clause graph. Measure how quickly a perturbation
    at one variable reaches variables at distance d.

    Method: Run two simulations — identical except one variable
    is perturbed at t=0. Measure when variables at distance d
    first notice the difference.
    """)

    random.seed(42)
    n = 30

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+82000000)

        # Build distance matrix via BFS on clause graph
        adj = {v: set() for v in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for i in range(len(vs)):
                for j in range(i+1, len(vs)):
                    adj[vs[i]].add(vs[j])
                    adj[vs[j]].add(vs[i])

        # BFS distances from var 0
        dist = {0: 0}
        queue = [0]
        while queue:
            v = queue.pop(0)
            for u in adj[v]:
                if u not in dist:
                    dist[u] = dist[v] + 1
                    queue.append(u)

        max_dist = max(dist.values())

        # Run baseline
        rec_base = run_physics_detailed(clauses, n, 200, seed=42)

        # Run with perturbation: var 0 starts at 0.9 instead of 0.5+tension
        np.random.seed(42)
        x_pert = np.array([0.5 + 0.05 * compute_tension(clauses, n, v)
                           for v in range(n)])
        x_pert[0] = 0.9  # PERTURB

        vel = np.zeros(n)
        pert_x = [x_pert.copy()]
        m = len(clauses)

        for step in range(200):
            progress = step / 200
            T = 0.25 * math.exp(-4.0 * progress) + 0.0001
            crystal = 3.0 * progress
            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0; lits = []
                for v, s in clause:
                    lit = x_pert[v] if s == 1 else (1.0 - x_pert[v])
                    lits.append((v, lit, s))
                    prod *= max(1.0 - lit, 1e-12)
                if prod < 0.001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1.0 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)
            for v in range(n):
                if x_pert[v] > 0.5: forces[v] += crystal * (1.0 - x_pert[v])
                else: forces[v] -= crystal * x_pert[v]
            noise = np.random.normal(0, T, n)
            vel = 0.93 * vel + (forces + noise) * 0.05
            x_pert = np.clip(x_pert + vel * 0.05, 0, 1)
            if step % 5 == 0:
                pert_x.append(x_pert.copy())

        base_x = np.array(rec_base['x'])
        pert_x = np.array(pert_x)

        # For each distance d: when does the perturbation first appear?
        print(f"\n  n={n}, seed={seed}, max graph distance={max_dist}")
        print(f"  Perturbed var 0 by +0.4")
        print(f"\n  {'dist':>4} | {'n_vars':>6} | {'first detect (step)':>18} | "
              f"{'max Δx at step 50':>16}")
        print("  " + "-" * 55)

        for d in range(max_dist + 1):
            vars_at_d = [v for v in range(n) if dist.get(v, 99) == d and v != 0]
            if not vars_at_d:
                continue

            # When is perturbation first detectable?
            first_detect = None
            max_delta_50 = 0

            n_steps_rec = min(base_x.shape[0], pert_x.shape[0])
            for ti in range(n_steps_rec):
                deltas = [abs(pert_x[ti, v] - base_x[ti, v]) for v in vars_at_d]
                max_d = max(deltas)
                if ti == 10:  # step 50
                    max_delta_50 = max_d
                if first_detect is None and max_d > 0.01:
                    first_detect = ti * 5  # convert to actual step

            print(f"  {d:>4} | {len(vars_at_d):>6} | "
                  f"{first_detect if first_detect else '>200':>18} | "
                  f"{max_delta_50:>16.4f}")

        break


# ============================================================
# 3. PHASE SPACE PORTRAIT
# ============================================================

def experiment_phase_space():
    print("\n" + "=" * 70)
    print("3. PHASE SPACE PORTRAIT: (x, v) dynamics")
    print("=" * 70)

    print("""
    Plot (x, v) trajectory for each variable.
    Look for: attractors, spirals, chaos, fixed points.
    """)

    random.seed(42)
    n = 12

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+83000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        rec = run_physics_detailed(clauses, n, 300, seed=42)
        xs = np.array(rec['x'])
        vs = np.array(rec['v'])

        print(f"\n  n={n}, seed={seed}:")

        for v in range(min(n, 4)):
            traj_x = xs[:, v]
            traj_v = vs[:, v]

            # Classify trajectory
            # Does it spiral? (x and v change sign?)
            v_sign_changes = sum(1 for i in range(1, len(traj_v))
                                if traj_v[i] * traj_v[i-1] < 0)
            x_crossings = sum(1 for i in range(1, len(traj_x))
                             if (traj_x[i] - 0.5) * (traj_x[i-1] - 0.5) < 0)

            # Final state
            final_x = traj_x[-1]
            final_v = traj_v[-1]

            # Max velocity
            max_v = max(abs(v) for v in traj_v)

            # Is it an attractor (converges) or limit cycle (oscillates)?
            late_var = np.std(traj_x[-10:])
            trajectory_type = "FIXED POINT" if late_var < 0.01 else \
                             "OSCILLATING" if late_var < 0.1 else "CHAOTIC"

            print(f"\n    x{v} (sol={sol[v]}):")
            print(f"      Velocity reversals: {v_sign_changes}")
            print(f"      x=0.5 crossings:    {x_crossings}")
            print(f"      Max |velocity|:     {max_v:.4f}")
            print(f"      Final (x,v):        ({final_x:.3f}, {final_v:.6f})")
            print(f"      Late variance:      {late_var:.6f}")
            print(f"      Type:               {trajectory_type}")
            print(f"      Path: ", end="")
            for i in range(0, len(traj_x), max(1, len(traj_x)//8)):
                print(f"({traj_x[i]:.2f},{traj_v[i]:+.3f})", end=" ")
            print()

        break


# ============================================================
# 4. CONSERVATION LAWS
# ============================================================

def experiment_conservation():
    print("\n" + "=" * 70)
    print("4. CONSERVATION LAWS: What's conserved?")
    print("=" * 70)

    random.seed(42)
    n = 20

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+84000000)

        rec = run_physics_detailed(clauses, n, 300, seed=42)

        energy = rec['energy']
        entropy = rec['entropy']
        momentum = rec['momentum']

        # Check conservation: compute Δ over time
        print(f"\n  n={n}, seed={seed}:")
        print(f"  {'step':>6} | {'energy':>8} | {'entropy':>8} | "
              f"{'momentum':>9} | {'E+S':>8} | {'E×S':>10}")
        print("  " + "-" * 60)

        for i in range(0, len(energy), max(1, len(energy)//10)):
            E = energy[i]
            S = entropy[i]
            M = momentum[i]
            print(f"  {i*5:>6} | {E:>8.2f} | {S:>8.2f} | "
                  f"{M:>+9.3f} | {E+S:>8.2f} | {E*S:>10.2f}")

        # Check if any combination is constant
        E_arr = np.array(energy)
        S_arr = np.array(entropy)
        M_arr = np.array(momentum)

        # Candidates for conservation
        candidates = {
            'E': E_arr,
            'S': S_arr,
            'M': M_arr,
            'E+S': E_arr + S_arr,
            'E-S': E_arr - S_arr,
            'E×S': E_arr * S_arr,
            'E/S': E_arr / np.maximum(S_arr, 0.01),
            'E+2S': E_arr + 2*S_arr,
            'S-E': S_arr - E_arr,
        }

        print(f"\n  Conservation test (lower CV = more conserved):")
        print(f"  {'quantity':>10} | {'mean':>8} | {'std':>8} | {'CV':>8}")
        print("  " + "-" * 40)

        for name, arr in sorted(candidates.items(),
                                key=lambda x: np.std(x[1])/max(abs(np.mean(x[1])),0.001)):
            mean = np.mean(arr)
            std = np.std(arr)
            cv = std / max(abs(mean), 0.001)
            marker = " ← CONSERVED?" if cv < 0.05 else ""
            print(f"  {name:>10} | {mean:>8.3f} | {std:>8.3f} | "
                  f"{cv:>8.4f}{marker}")

        break


# ============================================================
# 5. ENTROPY FLOW: Where does order come from?
# ============================================================

def experiment_entropy():
    print("\n" + "=" * 70)
    print("5. ENTROPY FLOW: Where does the information come from?")
    print("=" * 70)

    print("""
    System starts at max entropy (x ≈ 0.5, S = n bits).
    Ends at zero entropy (x ∈ {0,1}, S = 0 bits).

    The n bits of information must come FROM somewhere.
    Sources: (1) clause forces, (2) crystallization, (3) noise

    Measure entropy budget: ΔS_system + ΔS_environment = 0?
    """)

    random.seed(42)
    n = 20

    for seed in range(5):
        clauses = random_3sat(n, int(4.27 * n), seed=seed+85000000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        sol = solutions[0]

        rec = run_physics_detailed(clauses, n, 300, seed=42)
        entropy = rec['entropy']
        energy = rec['energy']

        # Entropy at start and end
        S_start = entropy[0]
        S_end = entropy[-1]
        E_start = energy[0]
        E_end = energy[-1]

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Entropy: {S_start:.2f} → {S_end:.2f} bits "
              f"(ΔS = {S_end - S_start:+.2f})")
        print(f"    Energy:  {E_start:.2f} → {E_end:.2f} "
              f"(ΔE = {E_end - E_start:+.2f})")
        print(f"    Maximum entropy: {n:.0f} bits (all uncertain)")

        # Where did the information come from?
        # Decompose: which variables lost most entropy?
        xs = np.array(rec['x'])
        x_start = xs[0]
        x_end = xs[-1]

        per_var_dS = []
        for v in range(n):
            p0 = np.clip(x_start[v], 1e-10, 1-1e-10)
            p1 = np.clip(x_end[v], 1e-10, 1-1e-10)
            S0 = -(p0*np.log2(p0) + (1-p0)*np.log2(1-p0))
            S1 = -(p1*np.log2(p1) + (1-p1)*np.log2(1-p1))
            per_var_dS.append(S0 - S1)  # positive = entropy decreased

        # Classify by tension (signal vs noise)
        tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
        signal_dS = [per_var_dS[v] for v in range(n) if abs(tensions[v]) > 0.1]
        noise_dS = [per_var_dS[v] for v in range(n) if abs(tensions[v]) <= 0.1]

        print(f"\n    Entropy decrease per variable:")
        print(f"    Signal vars ({len(signal_dS)}): "
              f"avg ΔS = {sum(signal_dS)/max(len(signal_dS),1):.3f} bits")
        print(f"    Noise vars ({len(noise_dS)}):  "
              f"avg ΔS = {sum(noise_dS)/max(len(noise_dS),1):.3f} bits")
        print(f"    Total extracted: {sum(per_var_dS):.2f} bits from {n} vars")

        # Information sources:
        # 1. Clauses provide directional info (tension)
        # 2. Crystallization forces binary decision
        # 3. Thermal noise adds randomness (entropy IN)
        # The net: clause info wins over noise

        # Measure: information from clauses vs from noise
        # Clause info ≈ n × MI_per_var ≈ n × 0.171
        clause_info = n * 0.171
        print(f"\n    Information budget:")
        print(f"    Available from clauses: {clause_info:.1f} bits "
              f"(n × 0.171)")
        print(f"    Actually extracted:     {sum(per_var_dS):.1f} bits")
        print(f"    Ratio:                  "
              f"{sum(per_var_dS)/clause_info:.2f}")
        print(f"    → Physics extracts "
              f"{100*sum(per_var_dS)/clause_info:.0f}% of available info")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    experiment_3body()
    experiment_speed()
    experiment_phase_space()
    experiment_conservation()
    experiment_entropy()
