"""
FROZEN CORE: Complete X-Ray — study it as an unknown object
═══════════════════════════════════════════════════════════

We've been trying to CRACK it. Now we STUDY it.
What IS it? What shape? What rules? What symmetries?

10 measurements from 10 different angles:

1. SIZE — how many vars are frozen? How does it scale?
2. TOPOLOGY — what does the frozen subgraph look like?
3. BOUNDARY — where does frozen meet free? What's at the edge?
4. INTERNAL STRUCTURE — are frozen vars all the same or heterogeneous?
5. CORRELATION — how are frozen vars related to each other?
6. RIGIDITY — if we break one frozen var, what cascade follows?
7. INFORMATION — how much info does frozen core carry?
8. BIRTH — when during physics does the core form? In what order?
9. SIGNATURES — what observable features distinguish frozen from free?
10. SYMMETRY — does the frozen core have hidden symmetries?
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
                if s == 1: p1 += 1/3
                else: p0 += 1/3
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def get_frozen_free(clauses, n, solutions):
    """Classify variables as frozen (same in all sols) or free."""
    frozen = set()
    free = set()
    for v in range(n):
        vals = set(s[v] for s in solutions)
        if len(vals) == 1:
            frozen.add(v)
        else:
            free.add(v)
    return frozen, free


# ============================================================
# 1. SIZE: How big is the frozen core?
# ============================================================

def study_size():
    print("=" * 70)
    print("1. SIZE: How many variables are frozen?")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14, 16]:
        frozen_fracs = []
        for seed in range(200):
            clauses = random_3sat(n, int(4.267 * n), seed=seed + 13000000)
            solutions = find_solutions(clauses, n)
            if len(solutions) < 2: continue

            frozen, free = get_frozen_free(clauses, n, solutions)
            frozen_fracs.append(len(frozen) / n)

            if len(frozen_fracs) >= 40: break

        if frozen_fracs:
            print(f"\n  n={n}: {len(frozen_fracs)} instances")
            print(f"    Mean frozen fraction: {np.mean(frozen_fracs):.3f}")
            print(f"    Std:                  {np.std(frozen_fracs):.3f}")
            print(f"    Min:                  {min(frozen_fracs):.3f}")
            print(f"    Max:                  {max(frozen_fracs):.3f}")
            # Distribution
            bins = [0, 0.2, 0.4, 0.6, 0.8, 1.01]
            for i in range(len(bins)-1):
                count = sum(1 for f in frozen_fracs if bins[i] <= f < bins[i+1])
                bar = '█' * count
                print(f"    [{bins[i]:.1f},{bins[i+1]:.1f}): {count:>3} {bar}")


# ============================================================
# 2. TOPOLOGY: What does the frozen subgraph look like?
# ============================================================

def study_topology():
    print("\n" + "=" * 70)
    print("2. TOPOLOGY: Shape of the frozen subgraph")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < 3 or len(free) < 3: continue

        # Build clause graph restricted to frozen vars
        adj_frozen = {v: set() for v in frozen}
        adj_free = {v: set() for v in free}
        frozen_edges = 0
        free_edges = 0
        cross_edges = 0

        for clause in clauses:
            vs = [v for v, s in clause]
            for i in range(len(vs)):
                for j in range(i+1, len(vs)):
                    a, b = vs[i], vs[j]
                    if a in frozen and b in frozen:
                        adj_frozen[a].add(b); adj_frozen[b].add(a)
                        frozen_edges += 1
                    elif a in free and b in free:
                        adj_free[a].add(b); adj_free[b].add(a)
                        free_edges += 1
                    else:
                        cross_edges += 1

        # Connected components of frozen subgraph
        visited = set()
        components = []
        for v in frozen:
            if v in visited: continue
            comp = set()
            queue = [v]
            comp.add(v)
            while queue:
                u = queue.pop()
                for w in adj_frozen.get(u, set()):
                    if w not in comp:
                        comp.add(w); queue.append(w)
            visited |= comp
            components.append(comp)

        avg_frozen_deg = np.mean([len(adj_frozen[v]) for v in frozen]) if frozen else 0
        avg_free_deg = np.mean([len(adj_free[v]) for v in free]) if free else 0

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Frozen: {len(frozen)}, Free: {len(free)}")
        print(f"    Edges: frozen-frozen={frozen_edges}, "
              f"free-free={free_edges}, cross={cross_edges}")
        print(f"    Frozen avg degree (within frozen): {avg_frozen_deg:.1f}")
        print(f"    Free avg degree (within free):     {avg_free_deg:.1f}")
        print(f"    Frozen connected components: {len(components)}")
        for i, comp in enumerate(sorted(components, key=len, reverse=True)):
            if i < 3:
                print(f"      Component {i+1}: size {len(comp)}, vars {sorted(comp)}")

        # Is frozen core a single giant component?
        if components:
            largest = max(len(c) for c in components)
            print(f"    Largest component: {largest}/{len(frozen)} "
                  f"({100*largest/max(len(frozen),1):.0f}%)")
            print(f"    → {'GIANT COMPONENT' if largest > len(frozen)*0.7 else 'FRAGMENTED'}")

        break


# ============================================================
# 3. BOUNDARY: The frozen-free interface
# ============================================================

def study_boundary():
    print("\n" + "=" * 70)
    print("3. BOUNDARY: The frozen-free interface")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13200000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < 3 or len(free) < 2: continue

        # Boundary vars: frozen vars that share a clause with a free var
        boundary_frozen = set()
        boundary_free = set()
        interior_frozen = set()

        for clause in clauses:
            vs = set(v for v, s in clause)
            has_frozen = vs & frozen
            has_free = vs & free
            if has_frozen and has_free:
                boundary_frozen |= has_frozen
                boundary_free |= has_free

        interior_frozen = frozen - boundary_frozen

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Frozen: {len(frozen)}, Free: {len(free)}")
        print(f"    Boundary frozen: {len(boundary_frozen)} "
              f"(share clause with free)")
        print(f"    Interior frozen: {len(interior_frozen)} "
              f"(no direct contact with free)")
        print(f"    Boundary free:   {len(boundary_free)} "
              f"(share clause with frozen)")

        if frozen:
            print(f"    Boundary/frozen ratio: "
                  f"{len(boundary_frozen)/len(frozen):.2f}")

        # Tension at boundary vs interior
        if boundary_frozen and interior_frozen:
            t_boundary = [abs(compute_tension(clauses, n, v))
                         for v in boundary_frozen]
            t_interior = [abs(compute_tension(clauses, n, v))
                         for v in interior_frozen]
            t_free = [abs(compute_tension(clauses, n, v))
                     for v in free]

            print(f"\n    |tension| by zone:")
            print(f"      Interior frozen: {np.mean(t_interior):.4f}")
            print(f"      Boundary frozen: {np.mean(t_boundary):.4f}")
            print(f"      Free vars:       {np.mean(t_free):.4f}")

        break


# ============================================================
# 4. INTERNAL STRUCTURE: Are frozen vars homogeneous?
# ============================================================

def study_internal():
    print("\n" + "=" * 70)
    print("4. INTERNAL STRUCTURE: Heterogeneity within frozen core")
    print("=" * 70)

    random.seed(42)
    n = 16

    for seed in range(200):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13300000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 3: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < 5: continue

        sol = solutions[0]

        # For each frozen var: HOW frozen is it?
        # Measure: if we force it to opposite value, how many solutions survive?
        print(f"\n  n={n}, seed={seed}, {len(solutions)} solutions:")
        print(f"    {'var':>5} | {'val':>3} | {'degree':>6} | {'|t|':>5} | "
              f"{'#clauses if flipped':>18}")
        print(f"    " + "-" * 45)

        for v in sorted(frozen):
            d = sum(1 for c in clauses for vi, si in c if vi == v)
            t = abs(compute_tension(clauses, n, v))

            # How many clauses break if we flip this frozen var?
            flipped = list(sol)
            flipped[v] = 1 - flipped[v]
            breaks = len(clauses) - evaluate(clauses, flipped)

            print(f"    x{v:>3} | {sol[v]:>3} | {d:>6} | {t:>5.3f} | "
                  f"{breaks:>18}")

        break


# ============================================================
# 5. RIGIDITY CASCADE: Break one frozen var, what happens?
# ============================================================

def study_rigidity():
    print("\n" + "=" * 70)
    print("5. RIGIDITY: Break one frozen var → cascade?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13400000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < 4: continue

        sol = solutions[0]

        # For each frozen var: flip it, then run UP.
        # Does UP force OTHER frozen vars to flip too?
        print(f"\n  n={n}, seed={seed}:")
        print(f"    Frozen: {sorted(frozen)}")

        for v in sorted(frozen)[:5]:
            # Fix v to opposite, see what UP does
            fixed = {v: 1 - sol[v]}

            # UP
            changed = True
            while changed:
                changed = False
                for clause in clauses:
                    sat = False; free_lits = []
                    for vi, si in clause:
                        if vi in fixed:
                            if (si==1 and fixed[vi]==1) or (si==-1 and fixed[vi]==0):
                                sat = True; break
                        else:
                            free_lits.append((vi, si))
                    if sat: continue
                    if len(free_lits) == 0:
                        pass # conflict
                    elif len(free_lits) == 1:
                        fv, fs = free_lits[0]
                        val = 1 if fs == 1 else 0
                        if fv not in fixed:
                            fixed[fv] = val
                            changed = True

            # What got forced?
            forced = {k: v for k, v in fixed.items() if k != v}
            forced_frozen = [k for k in fixed if k in frozen and k != v]
            forced_free = [k for k in fixed if k in free]

            n_changed = sum(1 for k in fixed if k != v and fixed[k] != sol[k])

            print(f"\n    Flip x{v} ({sol[v]}→{1-sol[v]}):")
            print(f"      UP forces: {len(fixed)-1} additional vars")
            print(f"      Of which frozen: {len(forced_frozen)}")
            print(f"      Of which free:   {len(forced_free)}")
            print(f"      Vars changed from solution: {n_changed}")

        break


# ============================================================
# 6. BIRTH: When does the frozen core form during physics?
# ============================================================

def study_birth():
    print("\n" + "=" * 70)
    print("6. BIRTH: When does the core crystallize?")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13500000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < 3 or len(free) < 2: continue

        sol = solutions[0]

        # Run physics, track when each frozen var commits
        x = np.full(n, 0.5)
        vel = np.zeros(n)

        commit_time = {}  # var → step when it first commits to final value

        for step in range(500):
            prog = step / 500
            T = 0.25 * math.exp(-4*prog) + 0.0001
            crystal = 3.0 * prog
            forces = np.zeros(n)
            for clause in clauses:
                prod = 1.0; lits = []
                for v, s in clause:
                    lit = x[v] if s == 1 else (1 - x[v])
                    lits.append((v, lit, s))
                    prod *= max(1 - lit, 1e-12)
                if prod < 0.001: continue
                w = math.sqrt(prod)
                for v, lit, s in lits:
                    term = max(1 - lit, 1e-12)
                    forces[v] += s * w * (prod / term)
            for v in range(n):
                if x[v] > 0.5: forces[v] += crystal*(1-x[v])
                else: forces[v] -= crystal*x[v]
            noise = np.random.normal(0, T, n)
            vel = 0.93*vel + (forces+noise)*0.05
            x = np.clip(x + vel*0.05, 0, 1)

            # Check commitments
            for v in range(n):
                if v not in commit_time:
                    committed_val = 1 if x[v] > 0.7 else (0 if x[v] < 0.3 else -1)
                    if committed_val >= 0:
                        commit_time[v] = step

        print(f"\n  n={n}, seed={seed}:")
        print(f"    {'var':>5} | {'type':>6} | {'commit step':>11} | "
              f"{'correct':>7}")
        print(f"    " + "-" * 40)

        frozen_commits = []
        free_commits = []

        for v in sorted(commit_time.keys(), key=lambda v: commit_time[v]):
            vtype = "FROZEN" if v in frozen else "free"
            final = 1 if x[v] > 0.5 else 0
            correct = "✓" if final == sol[v] else "✗"
            step = commit_time[v]
            if v in frozen: frozen_commits.append(step)
            else: free_commits.append(step)

            if len(frozen_commits) + len(free_commits) <= 10:
                print(f"    x{v:>3} | {vtype:>6} | {step:>11} | {correct:>7}")

        if frozen_commits and free_commits:
            print(f"\n    Avg commit step: frozen={np.mean(frozen_commits):.0f}, "
                  f"free={np.mean(free_commits):.0f}")
            print(f"    → {'FROZEN commits FIRST' if np.mean(frozen_commits) < np.mean(free_commits) else 'FREE commits FIRST'}")

        break


# ============================================================
# 7. INFORMATION: How much info does frozen core carry?
# ============================================================

def study_information():
    print("\n" + "=" * 70)
    print("7. INFORMATION: Bits of info in the frozen core")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14, 16]:
        info_frozen = []
        info_free = []

        for seed in range(200):
            clauses = random_3sat(n, int(4.267 * n), seed=seed + 13600000)
            solutions = find_solutions(clauses, n)
            if len(solutions) < 2: continue

            frozen, free = get_frozen_free(clauses, n, solutions)
            if not frozen or not free: continue

            # Frozen vars: entropy = 0 (deterministic across solutions)
            # Free vars: entropy > 0 (varies)
            for v in range(n):
                p1 = sum(s[v] for s in solutions) / len(solutions)
                if p1 == 0 or p1 == 1:
                    entropy = 0
                else:
                    entropy = -p1*math.log2(p1) - (1-p1)*math.log2(1-p1)

                if v in frozen:
                    info_frozen.append(1 - entropy)  # info = 1 - entropy
                else:
                    info_free.append(1 - entropy)

            if len(info_frozen) >= 200: break

        if info_frozen and info_free:
            print(f"\n  n={n}:")
            print(f"    Frozen: info = {np.mean(info_frozen):.4f} bits/var "
                  f"(should be 1.0)")
            print(f"    Free:   info = {np.mean(info_free):.4f} bits/var")
            print(f"    Total frozen info:  {np.mean(info_frozen)*n*np.mean([len(get_frozen_free(random_3sat(n,int(4.267*n),seed=42),n,find_solutions(random_3sat(n,int(4.267*n),seed=42),n))[0]) for _ in [1]])/n:.1f} bits")


# ============================================================
# 8. SYMMETRY: Hidden symmetries in the frozen core
# ============================================================

def study_symmetry():
    print("\n" + "=" * 70)
    print("8. SYMMETRY: Does the frozen core have structure?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(200):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 13700000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 4: continue

        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(free) < 3: continue

        sol = solutions[0]

        # Among FREE variables: do they flip in GROUPS?
        # Compare all pairs of solutions: which free vars flip together?
        coflip = np.zeros((n, n))
        n_pairs = 0

        for i in range(len(solutions)):
            for j in range(i+1, len(solutions)):
                flipped = set(v for v in free if solutions[i][v] != solutions[j][v])
                for a in flipped:
                    for b in flipped:
                        coflip[a][b] += 1
                n_pairs += 1

        if n_pairs == 0: continue

        coflip /= n_pairs

        # Find clusters of co-flipping free vars
        free_list = sorted(free)
        print(f"\n  n={n}, seed={seed}, {len(solutions)} solutions:")
        print(f"    Frozen: {sorted(frozen)} (values: {[sol[v] for v in sorted(frozen)]})")
        print(f"    Free:   {free_list}")

        if len(free_list) <= 8:
            print(f"\n    Co-flip matrix (free vars):")
            print(f"    {'':>5}", end="")
            for v in free_list: print(f" x{v:>2}", end="")
            print()
            for v in free_list:
                print(f"    x{v:>2} ", end="")
                for u in free_list:
                    print(f" {coflip[v][u]:>.2f}"[1:], end="")
                print()

        # Identify flip clusters
        clusters = []
        assigned = set()
        for v in free_list:
            if v in assigned: continue
            cluster = [v]; assigned.add(v)
            for u in free_list:
                if u in assigned: continue
                if coflip[v][u] > 0.8:
                    cluster.append(u); assigned.add(u)
            clusters.append(cluster)

        print(f"\n    Flip clusters: {len(clusters)}")
        for i, cl in enumerate(clusters):
            vals = [sol[v] for v in cl]
            print(f"      Cluster {i+1}: {cl} (values: {vals})")

        print(f"    Free DOF = {len(clusters)} independent flip groups")
        print(f"    Predicted #solutions: 2^{len(clusters)} = {2**len(clusters)}")
        print(f"    Actual #solutions:    {len(solutions)}")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    study_size()
    study_topology()
    study_boundary()
    study_internal()
    study_rigidity()
    study_birth()
    study_information()
    study_symmetry()
