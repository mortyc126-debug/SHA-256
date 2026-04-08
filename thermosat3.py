"""
ThermoSAT v3 — Hybrid: Theory-guided preprocessing + MiniSat backend
═══════════════════════════════════════════════════════════════════════

Strategy: Use our Bit Mechanics theory to PREPROCESS the instance,
then let MiniSat (optimized C solver) do the actual search.

INNOVATIONS:
1. Tension-guided initial phase: tell MiniSat which phase to try first
2. Signal var forcing: add unit clauses for highest-confidence vars
3. Clone merging: reduce instance size by merging clone pairs
4. Frustration-based clause ordering: prioritize informative clauses

The key insight: MiniSat's VSIDS heuristic is blind to our signal/noise
structure. By preprocessing, we inject our knowledge into MiniSat's search.
"""

import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat


def compute_tension(clauses, n, var, fixed=None):
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


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def run_minisat(filename, timeout=60):
    outfile = filename + ".out"
    try:
        t0 = time.time()
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - t0
        output = result.stdout + result.stderr
        decisions = 0

        for line in output.split('\n'):
            s = line.strip()
            if s.startswith('decisions'):
                after = s.split(':', 1)[1].strip().split()
                if after:
                    try: decisions = int(after[0])
                    except: pass

        if os.path.exists(outfile):
            with open(outfile) as f:
                r = f.readline().strip()
                if r == "SAT":
                    return True, elapsed, decisions
                elif r == "UNSAT":
                    return None, elapsed, decisions
        return False, elapsed, decisions
    except subprocess.TimeoutExpired:
        return False, timeout, 0
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)


# ============================================================
# Method 1: Tension-guided unit clause injection
# ============================================================

def preprocess_tension_force(clauses, n, strength=0.3):
    """
    Add unit clauses for the top `strength` fraction of highest-|tension| vars.
    This forces MiniSat to start with our predicted assignments.

    If our prediction is wrong, MiniSat will derive a contradiction quickly
    and learn a clause — which is USEFUL information.
    """
    tensions = {v: compute_tension(clauses, n, v) for v in range(n)}

    # Sort by |tension| descending
    sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]), reverse=True)

    # Take top `strength` fraction
    n_force = int(strength * n)
    force_vars = sorted_vars[:n_force]

    # Create new clauses: original + unit clauses
    new_clauses = list(clauses)
    for v in force_vars:
        sign = 1 if tensions[v] >= 0 else -1
        new_clauses.append([(v, sign)])  # unit clause

    return new_clauses


# ============================================================
# Method 2: Clone-based variable elimination
# ============================================================

def preprocess_clone_merge(clauses, n):
    """
    Detect clone pairs and merge them.
    If v1, v2 always appear with same sign → v2 = v1 (add equivalence clauses)
    If opposite signs → v2 = ¬v1 (add equivalence clauses)
    """
    pair_signs = {}
    for clause in clauses:
        for i in range(len(clause)):
            for j in range(i+1, len(clause)):
                v1, s1 = clause[i]
                v2, s2 = clause[j]
                key = (min(v1, v2), max(v1, v2))
                if key not in pair_signs:
                    pair_signs[key] = []
                pair_signs[key].append(s1 * s2)

    # Find consistent pairs
    equiv_clauses = []
    for (v1, v2), signs in pair_signs.items():
        if len(signs) >= 3:  # need enough evidence
            if all(s == 1 for s in signs):
                # v1 = v2: add (v1 OR NOT v2) AND (NOT v1 OR v2)
                equiv_clauses.append([(v1, 1), (v2, -1)])
                equiv_clauses.append([(v1, -1), (v2, 1)])
            elif all(s == -1 for s in signs):
                # v1 = NOT v2: add (v1 OR v2) AND (NOT v1 OR NOT v2)
                equiv_clauses.append([(v1, 1), (v2, 1)])
                equiv_clauses.append([(v1, -1), (v2, -1)])

    return list(clauses) + equiv_clauses, len(equiv_clauses) // 2


# ============================================================
# Method 3: Propagated tension phase hints (via clause ordering)
# ============================================================

def preprocess_clause_ordering(clauses, n):
    """
    Reorder clauses so that high-information clauses come first.
    MiniSat processes clauses in order for initial propagation.
    Putting informative clauses first guides early decisions.
    """
    # Score each clause by average |tension| of its variables
    tensions = {v: compute_tension(clauses, n, v) for v in range(n)}

    scored = []
    for i, clause in enumerate(clauses):
        avg_t = sum(abs(tensions[v]) for v, s in clause) / len(clause)
        scored.append((avg_t, i))

    # Sort: highest information first
    scored.sort(reverse=True)
    return [clauses[i] for _, i in scored]


# ============================================================
# Write DIMACS
# ============================================================

def write_dimacs(filename, clauses, n):
    m = len(clauses)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for clause in clauses:
            lits = [str((v+1) * s) for v, s in clause]
            f.write(" ".join(lits) + " 0\n")


# ============================================================
# Benchmark: raw MiniSat vs preprocessed MiniSat
# ============================================================

def benchmark():
    print("=" * 75)
    print("ThermoSAT v3: Theory-Guided Preprocessing + MiniSat")
    print("=" * 75)

    random.seed(42)
    filename_raw = "/tmp/thermo3_raw.cnf"
    filename_pp = "/tmp/thermo3_pp.cnf"

    methods = {
        'raw':       lambda c, n: (c, 0),
        'force_10%': lambda c, n: (preprocess_tension_force(c, n, 0.10), 0),
        'force_20%': lambda c, n: (preprocess_tension_force(c, n, 0.20), 0),
        'force_30%': lambda c, n: (preprocess_tension_force(c, n, 0.30), 0),
        'clones':    lambda c, n: preprocess_clone_merge(c, n),
        'reorder':   lambda c, n: (preprocess_clause_ordering(c, n), 0),
        'force20+clone': lambda c, n: preprocess_clone_merge(
                            preprocess_tension_force(c, n, 0.20), n),
    }

    for n in [50, 100, 200, 300, 500]:
        print(f"\n  n={n}, ratio=4.27:")
        n_inst = 30 if n <= 200 else 15
        timeout = 30 if n <= 200 else 120

        results = {m: {'solved': 0, 'times': [], 'decisions': []}
                   for m in methods}

        for seed in range(n_inst * 3):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 64000000)

            for method_name, method_fn in methods.items():
                pp_clauses, extra_info = method_fn(clauses, n)
                write_dimacs(filename_pp, pp_clauses, n)

                solved, elapsed, decisions = run_minisat(filename_pp, timeout)

                if solved == True:
                    results[method_name]['solved'] += 1
                    results[method_name]['times'].append(elapsed)
                    results[method_name]['decisions'].append(decisions)

            # Check if we have enough instances
            if results['raw']['solved'] >= n_inst:
                break

        print(f"    {'method':>15} | {'solved':>6} | {'avg ms':>8} | "
              f"{'avg dec':>10} | {'speedup':>7}")
        print("    " + "-" * 60)

        raw_time = (sum(results['raw']['times']) / len(results['raw']['times'])
                   if results['raw']['times'] else 999)

        for m in methods:
            r = results[m]
            if r['times']:
                avg_t = sum(r['times']) / len(r['times'])
                avg_d = sum(r['decisions']) / len(r['decisions'])
                speedup = raw_time / avg_t if avg_t > 0 else 0
                print(f"    {m:>15} | {r['solved']:>6} | "
                      f"{1000*avg_t:>7.0f}ms | {avg_d:>10.0f} | "
                      f"{speedup:>6.2f}×")
            else:
                print(f"    {m:>15} | {r['solved']:>6} |      N/A |        N/A |     N/A")

    for fn in [filename_raw, filename_pp]:
        if os.path.exists(fn): os.remove(fn)


# ============================================================
# Below threshold: easier instances (r=3.5)
# ============================================================

def below_threshold():
    print("\n" + "=" * 75)
    print("BELOW THRESHOLD: r=3.5")
    print("=" * 75)

    random.seed(42)
    filename = "/tmp/thermo3_below.cnf"

    for n in [100, 200, 500, 1000]:
        print(f"\n  n={n}, ratio=3.5:")
        n_inst = 20
        timeout = 30

        raw_results = {'solved': 0, 'times': [], 'dec': []}
        pp_results = {'solved': 0, 'times': [], 'dec': []}

        for seed in range(n_inst * 3):
            clauses = random_3sat(n, int(3.5 * n), seed=seed + 65000000)

            # Raw
            write_dimacs(filename, clauses, n)
            s, t, d = run_minisat(filename, timeout)
            if s == True:
                raw_results['solved'] += 1
                raw_results['times'].append(t)
                raw_results['dec'].append(d)

            # Preprocessed (force 20% + reorder)
            pp = preprocess_tension_force(clauses, n, 0.20)
            pp = preprocess_clause_ordering(pp, n)
            write_dimacs(filename, pp, n)
            s, t, d = run_minisat(filename, timeout)
            if s == True:
                pp_results['solved'] += 1
                pp_results['times'].append(t)
                pp_results['dec'].append(d)

            if raw_results['solved'] >= n_inst:
                break

        for label, r in [("Raw MiniSat", raw_results),
                         ("Thermo+MiniSat", pp_results)]:
            if r['times']:
                avg_t = 1000 * sum(r['times']) / len(r['times'])
                avg_d = sum(r['dec']) / len(r['dec'])
                print(f"    {label:>15}: {r['solved']} solved, "
                      f"avg {avg_t:.0f}ms, avg {avg_d:.0f} decisions")
            else:
                print(f"    {label:>15}: {r['solved']} solved")

    if os.path.exists(filename): os.remove(filename)


if __name__ == "__main__":
    benchmark()
    below_threshold()
