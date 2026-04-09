"""
FROZEN CORE MECHANICS — Block I: Static Properties
═══════════════════════════════════════════════════

Just as Bit Mechanics began with "what can we measure about a bit?",
Frozen Core Mechanics begins with "what can we measure about a frozen structure?"

The frozen core is NOT a set of variables. It's a STRUCTURE —
a pattern of constraints that forces variables into fixed values.

PRIMITIVE OBJECT: not the bit, but the CONSTRAINT PATTERN that freezes bits.

Properties to measure:
 1. SHAPE — the geometry of the frozen subgraph
 2. MASS — how many bits does the core freeze?
 3. DENSITY — constraints per frozen variable
 4. TENSION FIELD — the force field WITHIN the core
 5. PERIMETER — the boundary with the free region
 6. FRAGILITY — how many constraints must break to unfreeze one bit?
 7. DEPTH — how deep inside the core is each frozen bit?
 8. SIGNATURE — what clause-level pattern creates freezing?
 9. SPECTRUM — eigenvalues of the frozen subgraph Laplacian
10. GENERATION — which constraints CREATE the freezing?
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def get_frozen_free(clauses, n, solutions):
    frozen = set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)
    return frozen, set(range(n)) - frozen


def collect_instances(n, n_inst=30, min_solutions=2, min_frozen=3):
    """Collect instances with frozen core for study."""
    instances = []
    for seed in range(n_inst * 10):
        clauses = random_3sat(n, int(4.267 * n), seed=seed + 14000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < min_solutions: continue
        frozen, free = get_frozen_free(clauses, n, solutions)
        if len(frozen) < min_frozen: continue
        instances.append({
            'clauses': clauses, 'n': n, 'solutions': solutions,
            'frozen': frozen, 'free': free, 'seed': seed,
            'sol': solutions[0]
        })
        if len(instances) >= n_inst: break
    return instances


# ============================================================
# 1. SHAPE — geometry of frozen subgraph
# ============================================================

def measure_shape(inst):
    """Measure the geometric shape of the frozen core."""
    clauses, n, frozen, free = inst['clauses'], inst['n'], inst['frozen'], inst['free']

    # Build adjacency within frozen
    adj = {v: set() for v in frozen}
    for clause in clauses:
        vs_in_frozen = [v for v, s in clause if v in frozen]
        for i in range(len(vs_in_frozen)):
            for j in range(i+1, len(vs_in_frozen)):
                adj[vs_in_frozen[i]].add(vs_in_frozen[j])
                adj[vs_in_frozen[j]].add(vs_in_frozen[i])

    # Connected components
    visited = set(); components = []
    for v in frozen:
        if v in visited: continue
        comp = set(); queue = [v]; comp.add(v)
        while queue:
            u = queue.pop()
            for w in adj.get(u, set()):
                if w not in comp: comp.add(w); queue.append(w)
        visited |= comp; components.append(comp)

    # Diameter of largest component
    diameter = 0
    if components:
        largest = max(components, key=len)
        for start in list(largest)[:5]:  # BFS from a few nodes
            dist = {start: 0}; queue = [start]
            while queue:
                u = queue.pop(0)
                for w in adj.get(u, set()):
                    if w in largest and w not in dist:
                        dist[w] = dist[u] + 1; queue.append(w)
            if dist: diameter = max(diameter, max(dist.values()))

    degrees = [len(adj.get(v, set())) for v in frozen]

    return {
        'n_components': len(components),
        'largest_component': max(len(c) for c in components) if components else 0,
        'diameter': diameter,
        'avg_degree': np.mean(degrees) if degrees else 0,
        'max_degree': max(degrees) if degrees else 0,
        'density': sum(degrees) / (2 * max(len(frozen), 1)),
    }


# ============================================================
# 2. MASS — how many bits does the core freeze?
# ============================================================

def measure_mass(inst):
    n, frozen, free = inst['n'], inst['frozen'], inst['free']
    return {
        'frozen_count': len(frozen),
        'free_count': len(free),
        'frozen_fraction': len(frozen) / n,
        'mass': len(frozen),  # in "frozen bit" units
    }


# ============================================================
# 3. DENSITY — constraints per frozen variable
# ============================================================

def measure_density(inst):
    clauses, frozen, free = inst['clauses'], inst['frozen'], inst['free']

    # Count clauses that are ALL-frozen, mixed, ALL-free
    all_frozen = 0; mixed = 0; all_free = 0
    frozen_involved = 0  # clauses touching at least one frozen var

    for clause in clauses:
        vs = set(v for v, s in clause)
        nf = len(vs & frozen)
        if nf == 3: all_frozen += 1
        elif nf == 0: all_free += 1
        else: mixed += 1
        if nf > 0: frozen_involved += 1

    return {
        'clauses_all_frozen': all_frozen,
        'clauses_mixed': mixed,
        'clauses_all_free': all_free,
        'clauses_per_frozen_var': frozen_involved / max(len(frozen), 1),
        'constraint_density': frozen_involved / max(len(frozen), 1),
    }


# ============================================================
# 4. TENSION FIELD within the core
# ============================================================

def measure_tension_field(inst):
    clauses, n, frozen, sol = inst['clauses'], inst['n'], inst['frozen'], inst['sol']

    tensions = {}
    for v in frozen:
        p1, p0 = 0, 0
        for clause in clauses:
            for vi, si in clause:
                if vi == v:
                    if si == 1: p1 += 1/3
                    else: p0 += 1/3
        tensions[v] = (p1 - p0) / (p1 + p0) if (p1 + p0) > 0 else 0

    # Does tension point correctly for frozen vars?
    correct = sum(1 for v in frozen
                  if (tensions[v] > 0) == (sol[v] == 1))

    vals = [abs(tensions[v]) for v in frozen]
    signs_correct = [((tensions[v] > 0) == (sol[v] == 1)) for v in frozen]

    return {
        'mean_abs_tension': np.mean(vals) if vals else 0,
        'std_abs_tension': np.std(vals) if vals else 0,
        'tension_accuracy': correct / max(len(frozen), 1),
        'min_tension': min(vals) if vals else 0,
        'max_tension': max(vals) if vals else 0,
    }


# ============================================================
# 5. PERIMETER — boundary with free region
# ============================================================

def measure_perimeter(inst):
    clauses, frozen, free = inst['clauses'], inst['frozen'], inst['free']

    boundary_frozen = set()
    boundary_free = set()
    cross_edges = 0

    for clause in clauses:
        vs = set(v for v, s in clause)
        has_f = vs & frozen
        has_r = vs & free
        if has_f and has_r:
            boundary_frozen |= has_f
            boundary_free |= has_r
            cross_edges += len(has_f) * len(has_r)

    return {
        'boundary_frozen': len(boundary_frozen),
        'interior_frozen': len(frozen) - len(boundary_frozen),
        'boundary_fraction': len(boundary_frozen) / max(len(frozen), 1),
        'perimeter': cross_edges,  # number of frozen-free edges
        'surface_to_volume': cross_edges / max(len(frozen), 1),
    }


# ============================================================
# 6. FRAGILITY — how many constraints protect each frozen bit?
# ============================================================

def measure_fragility(inst):
    clauses, n, frozen, sol = inst['clauses'], inst['n'], inst['frozen'], inst['sol']
    m = len(clauses)

    fragilities = []
    for v in frozen:
        # Flip v: how many clauses break?
        flipped = list(sol)
        flipped[v] = 1 - flipped[v]
        breaks = m - evaluate(clauses, flipped)
        fragilities.append(breaks)

    return {
        'mean_breaks': np.mean(fragilities) if fragilities else 0,
        'min_breaks': min(fragilities) if fragilities else 0,
        'max_breaks': max(fragilities) if fragilities else 0,
        'zero_break_count': sum(1 for b in fragilities if b == 0),
        'fragilities': fragilities,
    }


# ============================================================
# 7. DEPTH — layers within the frozen core
# ============================================================

def measure_depth(inst):
    clauses, n, frozen, free = inst['clauses'], inst['n'], inst['frozen'], inst['free']

    # BFS from free region into frozen: distance = depth
    adj = {v: set() for v in range(n)}
    for clause in clauses:
        vs = [v for v, s in clause]
        for i in range(len(vs)):
            for j in range(i+1, len(vs)):
                adj[vs[i]].add(vs[j]); adj[vs[j]].add(vs[i])

    # BFS from ALL free vars
    dist = {}
    queue = list(free)
    for v in free: dist[v] = 0
    while queue:
        u = queue.pop(0)
        for w in adj[u]:
            if w not in dist:
                dist[w] = dist[u] + 1; queue.append(w)

    frozen_depths = [dist.get(v, -1) for v in frozen]
    frozen_depths = [d for d in frozen_depths if d > 0]

    return {
        'mean_depth': np.mean(frozen_depths) if frozen_depths else 0,
        'max_depth': max(frozen_depths) if frozen_depths else 0,
        'depth_distribution': frozen_depths,
    }


# ============================================================
# 8. SIGNATURE — what clause pattern creates freezing?
# ============================================================

def measure_signature(inst):
    clauses, n, frozen, free, sol = inst['clauses'], inst['n'], inst['frozen'], inst['free'], inst['sol']

    # For each frozen var: analyze its clause neighborhood
    # What's special about frozen vars' clauses vs free vars' clauses?
    frozen_clause_stats = []
    free_clause_stats = []

    for v in range(n):
        # Count: how many of v's clauses have all-correct signs?
        n_all_correct = 0
        n_total = 0
        for clause in clauses:
            if not any(vi == v for vi, si in clause): continue
            n_total += 1
            all_correct = all(
                (si == 1 and sol[vi] == 1) or (si == -1 and sol[vi] == 0)
                for vi, si in clause)
            if all_correct: n_all_correct += 1

        ratio = n_all_correct / max(n_total, 1)
        if v in frozen:
            frozen_clause_stats.append(ratio)
        else:
            free_clause_stats.append(ratio)

    return {
        'frozen_all_correct_ratio': np.mean(frozen_clause_stats) if frozen_clause_stats else 0,
        'free_all_correct_ratio': np.mean(free_clause_stats) if free_clause_stats else 0,
    }


# ============================================================
# 9. SPECTRUM — eigenvalues of frozen subgraph
# ============================================================

def measure_spectrum(inst):
    clauses, n, frozen = inst['clauses'], inst['n'], inst['frozen']

    if len(frozen) < 3: return {'spectral_gap': 0, 'n_eigenvalues': 0}

    # Build adjacency matrix of frozen subgraph
    frozen_list = sorted(frozen)
    idx = {v: i for i, v in enumerate(frozen_list)}
    nf = len(frozen_list)
    A = np.zeros((nf, nf))

    for clause in clauses:
        vs_in = [(v, s) for v, s in clause if v in frozen]
        for i in range(len(vs_in)):
            for j in range(i+1, len(vs_in)):
                vi, si = vs_in[i]; vj, sj = vs_in[j]
                A[idx[vi], idx[vj]] += si * sj
                A[idx[vj], idx[vi]] += si * sj

    D = np.diag(np.sum(np.abs(A), axis=1))
    L = D - A

    eigenvalues = np.sort(np.linalg.eigvalsh(L))

    return {
        'spectral_gap': eigenvalues[1] if len(eigenvalues) > 1 else 0,
        'max_eigenvalue': eigenvalues[-1],
        'eigenvalues': eigenvalues[:5].tolist(),
        'condition': eigenvalues[-1] / max(eigenvalues[1], 0.001) if len(eigenvalues) > 1 else 0,
    }


# ============================================================
# 10. GENERATION — which constraints CREATE the freezing?
# ============================================================

def measure_generation(inst):
    clauses, n, frozen, free, solutions = (
        inst['clauses'], inst['n'], inst['frozen'], inst['free'], inst['solutions'])

    # Remove clauses one at a time. If removing clause c UNFREEZES a variable,
    # then c is a GENERATING constraint of the frozen core.
    generating = []
    for ci in range(len(clauses)):
        reduced = clauses[:ci] + clauses[ci+1:]
        reduced_sols = find_solutions(reduced, n)
        if len(reduced_sols) < 2: continue

        reduced_frozen, _ = get_frozen_free(reduced, n, reduced_sols)
        unfrozen = frozen - reduced_frozen

        if unfrozen:
            generating.append({
                'clause_idx': ci,
                'clause': clauses[ci],
                'unfreezes': unfrozen,
                'n_unfrozen': len(unfrozen),
            })

    return {
        'n_generating': len(generating),
        'n_total_clauses': len(clauses),
        'generating_fraction': len(generating) / max(len(clauses), 1),
        'generating': generating[:5],
    }


# ============================================================
# FULL CATALOG
# ============================================================

def full_catalog():
    print("=" * 70)
    print("FROZEN CORE MECHANICS — Complete Catalog")
    print("=" * 70)

    random.seed(42)

    for n in [12, 14]:
        instances = collect_instances(n, n_inst=15)
        if not instances:
            print(f"\n  n={n}: no suitable instances")
            continue

        print(f"\n{'═'*70}")
        print(f"  n={n}: {len(instances)} instances with frozen core")
        print(f"{'═'*70}")

        all_measurements = {
            'shape': [], 'mass': [], 'density': [], 'tension': [],
            'perimeter': [], 'fragility': [], 'depth': [],
            'signature': [], 'spectrum': [], 'generation': [],
        }

        for inst in instances:
            all_measurements['shape'].append(measure_shape(inst))
            all_measurements['mass'].append(measure_mass(inst))
            all_measurements['density'].append(measure_density(inst))
            all_measurements['tension'].append(measure_tension_field(inst))
            all_measurements['perimeter'].append(measure_perimeter(inst))
            all_measurements['fragility'].append(measure_fragility(inst))
            all_measurements['depth'].append(measure_depth(inst))
            all_measurements['signature'].append(measure_signature(inst))
            all_measurements['spectrum'].append(measure_spectrum(inst))

        # Generation is slow — run on fewer instances
        for inst in instances[:5]:
            all_measurements['generation'].append(measure_generation(inst))

        # Print summary statistics
        for prop_name, measurements in all_measurements.items():
            if not measurements: continue
            print(f"\n  ── {prop_name.upper()} ──")

            # Collect all numeric fields
            fields = {}
            for m in measurements:
                for k, v in m.items():
                    if isinstance(v, (int, float)):
                        if k not in fields: fields[k] = []
                        fields[k].append(v)

            for k in sorted(fields.keys()):
                vals = fields[k]
                print(f"    {k:>30}: {np.mean(vals):>8.3f} "
                      f"± {np.std(vals):>6.3f}  "
                      f"[{min(vals):.3f}, {max(vals):.3f}]")

        # Print generation details
        if all_measurements['generation']:
            print(f"\n  ── GENERATION (detailed) ──")
            for gi, gen in enumerate(all_measurements['generation']):
                print(f"    Instance {gi}: {gen['n_generating']} generating clauses "
                      f"out of {gen['n_total_clauses']} "
                      f"({100*gen['generating_fraction']:.1f}%)")
                for g in gen.get('generating', []):
                    print(f"      Clause {g['clause_idx']}: "
                          f"unfreezes {g['unfreezes']}")


if __name__ == "__main__":
    full_catalog()
