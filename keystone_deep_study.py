"""
KEYSTONE CLAUSES: Complete study of the objects that CREATE frozen core
═══════════════════════════════════════════════════════════════════════

~10 clauses out of ~51 hold the entire frozen core together.
What ARE they? What makes them special? Can we see them?

STUDY:
 1. OBSERVABLE PROPERTIES — degree, tension, frustration of keystones
 2. TOPOLOGY — where in the graph do keystones sit?
 3. INTERACTIONS — do keystones interact with each other?
 4. HIERARCHY — some keystones unfreeze 9 vars, others 1. Why?
 5. ANTI-KEYSTONES — are there clauses that PREVENT freezing?
 6. WHAT CREATES A KEYSTONE — necessary and sufficient conditions
 7. SPACE — in what space do keystones live?
 8. BEYOND FROZEN — what's on the other side?
"""

import numpy as np
import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def get_frozen(clauses, n, solutions):
    return set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)


def find_keystones(clauses, n, solutions, frozen):
    """Find clauses whose removal unfreezes variables."""
    keystones = []
    for ci in range(len(clauses)):
        reduced = clauses[:ci] + clauses[ci+1:]
        reduced_sols = find_solutions(reduced, n)
        if len(reduced_sols) < 2: continue
        reduced_frozen = get_frozen(reduced, n, reduced_sols)
        unfrozen = frozen - reduced_frozen
        if unfrozen:
            keystones.append({
                'idx': ci, 'clause': clauses[ci],
                'unfreezes': unfrozen, 'power': len(unfrozen),
                'n_new_solutions': len(reduced_sols),
            })
    return keystones


# ============================================================
# 1. OBSERVABLE PROPERTIES of keystones vs normal clauses
# ============================================================

def study_observables():
    print("=" * 70)
    print("1. OBSERVABLE PROPERTIES: What makes keystones visible?")
    print("=" * 70)

    random.seed(42)
    n = 12

    ks_degrees = []; normal_degrees = []
    ks_frozen_count = []; normal_frozen_count = []
    ks_tensions = []; normal_tensions = []
    ks_frustration = []; normal_frustration = []
    ks_unique_vars = []; normal_unique_vars = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        ks_indices = set(k['idx'] for k in keystones)

        sol = solutions[0]
        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        for ci, clause in enumerate(clauses):
            vs = [v for v,s in clause]
            signs = [s for v,s in clause]

            # Degree sum: total degree of vars in clause
            deg_sum = sum(sum(1 for c in clauses for vi,si in c if vi==v)
                         for v in vs)

            # Frozen count: how many vars in this clause are frozen?
            n_frozen = sum(1 for v in vs if v in frozen)

            # Avg absolute tension of vars
            avg_t = np.mean([abs(tensions[v]) for v in vs])

            # Frustration: do the signs agree with solution?
            n_correct_signs = sum(1 for v,s in clause
                                 if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0))

            # How many OTHER clauses share vars with this one?
            shared = set()
            for cj, other in enumerate(clauses):
                if cj == ci: continue
                if set(v for v,s in other) & set(vs):
                    shared.add(cj)
            connectivity = len(shared)

            if ci in ks_indices:
                ks_degrees.append(deg_sum)
                ks_frozen_count.append(n_frozen)
                ks_tensions.append(avg_t)
                ks_frustration.append(n_correct_signs)
                ks_unique_vars.append(connectivity)
            else:
                normal_degrees.append(deg_sum)
                normal_frozen_count.append(n_frozen)
                normal_tensions.append(avg_t)
                normal_frustration.append(n_correct_signs)
                normal_unique_vars.append(connectivity)

        if len(ks_degrees) >= 100: break

    if ks_degrees and normal_degrees:
        print(f"\n  {'property':>25} | {'keystone':>10} | {'normal':>10} | {'ratio':>6}")
        print(f"  " + "-" * 60)

        props = [
            ('degree_sum', ks_degrees, normal_degrees),
            ('frozen_vars_in_clause', ks_frozen_count, normal_frozen_count),
            ('avg |tension|', ks_tensions, normal_tensions),
            ('correct_signs (of 3)', ks_frustration, normal_frustration),
            ('clause_connectivity', ks_unique_vars, normal_unique_vars),
        ]
        for name, ks, nm in props:
            mk = np.mean(ks); mn = np.mean(nm)
            ratio = mk / max(mn, 0.001)
            disc = " ← DIFF" if abs(ratio - 1) > 0.15 else ""
            print(f"  {name:>25} | {mk:>10.3f} | {mn:>10.3f} | "
                  f"{ratio:>6.2f}{disc}")


# ============================================================
# 2. TOPOLOGY: Where do keystones sit in the graph?
# ============================================================

def study_topology():
    print("\n" + "=" * 70)
    print("2. TOPOLOGY: Where are keystones in the graph?")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue
        ks_indices = set(k['idx'] for k in keystones)

        # Clause-clause adjacency (share a variable)
        clause_adj = {ci: set() for ci in range(len(clauses))}
        for ci in range(len(clauses)):
            vs_ci = set(v for v,s in clauses[ci])
            for cj in range(ci+1, len(clauses)):
                vs_cj = set(v for v,s in clauses[cj])
                if vs_ci & vs_cj:
                    clause_adj[ci].add(cj)
                    clause_adj[cj].add(ci)

        # Distance from each keystone to other keystones
        ks_list = sorted(ks_indices)
        ks_distances = []
        for ki in ks_list:
            dist = {ki: 0}; queue = [ki]
            while queue:
                u = queue.pop(0)
                for w in clause_adj[u]:
                    if w not in dist:
                        dist[w] = dist[u] + 1; queue.append(w)
            for kj in ks_list:
                if kj > ki and kj in dist:
                    ks_distances.append(dist[kj])

        # Distance from keystones to non-keystones
        ks_to_normal = []
        for ki in ks_list:
            dist = {ki: 0}; queue = [ki]
            while queue:
                u = queue.pop(0)
                for w in clause_adj[u]:
                    if w not in dist:
                        dist[w] = dist[u] + 1; queue.append(w)
            for ci in range(len(clauses)):
                if ci not in ks_indices and ci in dist:
                    ks_to_normal.append(dist[ci])

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Keystones: {len(keystones)}, "
              f"Normal: {len(clauses)-len(keystones)}")
        if ks_distances:
            print(f"    Keystone-keystone distance: "
                  f"avg={np.mean(ks_distances):.2f}, "
                  f"max={max(ks_distances)}")
        if ks_to_normal:
            print(f"    Keystone-normal distance:   "
                  f"avg={np.mean(ks_to_normal):.2f}")
        print(f"    → Keystones are "
              f"{'CLUSTERED' if np.mean(ks_distances) < np.mean(ks_to_normal) else 'SPREAD OUT'}")

        break


# ============================================================
# 3. HIERARCHY: Power law of keystone strength
# ============================================================

def study_hierarchy():
    print("\n" + "=" * 70)
    print("3. HIERARCHY: Some keystones unfreeze 9 vars, others 1. Why?")
    print("=" * 70)

    random.seed(42)

    all_powers = []

    for n in [12, 14]:
        for seed in range(100):
            clauses = random_3sat(n, int(4.267*n), seed=seed+15200000)
            solutions = find_solutions(clauses, n)
            if len(solutions) < 2: continue
            frozen = get_frozen(clauses, n, solutions)
            if len(frozen) < 3: continue

            keystones = find_keystones(clauses, n, solutions, frozen)
            for k in keystones:
                all_powers.append(k['power'])

            if len(all_powers) >= 100: break

    if all_powers:
        print(f"\n  {len(all_powers)} keystones measured:")
        print(f"    Mean power: {np.mean(all_powers):.2f} vars unfrozen")
        print(f"    Max power:  {max(all_powers)}")
        print(f"    Distribution:")
        from collections import Counter
        dist = Counter(all_powers)
        for power in sorted(dist.keys()):
            bar = '█' * dist[power]
            print(f"      power={power:>2}: {dist[power]:>3} {bar}")

        # Is it a power law?
        if max(all_powers) > 1:
            print(f"\n    Most keystones are WEAK (power 1-2)")
            print(f"    A FEW are STRONG (power {max(all_powers)})")
            n_strong = sum(1 for p in all_powers if p >= 4)
            print(f"    Strong (≥4): {n_strong}/{len(all_powers)} "
                  f"({100*n_strong/len(all_powers):.0f}%)")


# ============================================================
# 4. KEYSTONE INTERACTIONS: Do keystones depend on each other?
# ============================================================

def study_interactions():
    print("\n" + "=" * 70)
    print("4. INTERACTIONS: Do keystones depend on each other?")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15300000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 3: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        # Remove pairs of keystones: does removing 2 unfreeze MORE than sum?
        print(f"\n  n={n}, seed={seed}, {len(keystones)} keystones:")

        synergy_data = []
        for i in range(min(len(keystones), 5)):
            for j in range(i+1, min(len(keystones), 5)):
                ki, kj = keystones[i]['idx'], keystones[j]['idx']
                pi, pj = keystones[i]['power'], keystones[j]['power']

                # Remove both
                reduced = [c for ci, c in enumerate(clauses) if ci != ki and ci != kj]
                reduced_sols = find_solutions(reduced, n)
                if len(reduced_sols) < 2: continue
                reduced_frozen = get_frozen(reduced, n, reduced_sols)
                pair_unfrozen = len(frozen - reduced_frozen)

                expected = pi + pj  # if independent
                synergy = pair_unfrozen - expected

                synergy_data.append(synergy)
                if abs(synergy) > 0:
                    print(f"    Remove {ki}+{kj}: "
                          f"expected {expected}, actual {pair_unfrozen}, "
                          f"synergy={synergy:+d}")

        if synergy_data:
            avg_synergy = np.mean(synergy_data)
            print(f"\n    Average synergy: {avg_synergy:+.2f}")
            if avg_synergy > 0.5:
                print(f"    → POSITIVE synergy: keystones REINFORCE each other")
            elif avg_synergy < -0.5:
                print(f"    → NEGATIVE synergy: keystones are REDUNDANT")
            else:
                print(f"    → INDEPENDENT: keystones act alone")

        break


# ============================================================
# 5. WHAT CREATES A KEYSTONE — necessary conditions
# ============================================================

def study_creation():
    print("\n" + "=" * 70)
    print("5. CREATION: What makes a clause become a keystone?")
    print("=" * 70)

    random.seed(42)
    n = 14

    ks_all_frozen_lits = []  # all 3 vars frozen?
    ks_mixed = []             # mix of frozen and free?
    ks_sign_pattern = []      # signs relative to solution
    nm_all_frozen_lits = []
    nm_mixed = []
    nm_sign_pattern = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15400000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        ks_indices = set(k['idx'] for k in keystones)
        sol = solutions[0]

        for ci, clause in enumerate(clauses):
            vs = [v for v,s in clause]
            n_frozen = sum(1 for v in vs if v in frozen)
            is_mixed = 0 < n_frozen < 3

            # Sign pattern: how many signs match solution?
            n_match = sum(1 for v,s in clause
                        if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0))

            # Is this the ONLY clause with this exact variable triple?
            # (uniqueness)

            if ci in ks_indices:
                ks_all_frozen_lits.append(n_frozen == 3)
                ks_mixed.append(is_mixed)
                ks_sign_pattern.append(n_match)
            else:
                nm_all_frozen_lits.append(n_frozen == 3)
                nm_mixed.append(is_mixed)
                nm_sign_pattern.append(n_match)

        if len(ks_sign_pattern) >= 80: break

    if ks_sign_pattern:
        print(f"\n  {'property':>25} | {'keystone':>10} | {'normal':>10}")
        print(f"  " + "-" * 50)
        print(f"  {'P(all 3 vars frozen)':>25} | "
              f"{np.mean(ks_all_frozen_lits):>10.3f} | "
              f"{np.mean(nm_all_frozen_lits):>10.3f}")
        print(f"  {'P(mixed frozen+free)':>25} | "
              f"{np.mean(ks_mixed):>10.3f} | "
              f"{np.mean(nm_mixed):>10.3f}")
        print(f"  {'avg correct signs':>25} | "
              f"{np.mean(ks_sign_pattern):>10.3f} | "
              f"{np.mean(nm_sign_pattern):>10.3f}")

        # Key question: what's the MINIMAL condition for being a keystone?
        print(f"\n  Keystone sign distribution:")
        from collections import Counter
        ks_dist = Counter(ks_sign_pattern)
        nm_dist = Counter(nm_sign_pattern)
        for signs in [0, 1, 2, 3]:
            ks_frac = ks_dist.get(signs, 0) / max(len(ks_sign_pattern), 1)
            nm_frac = nm_dist.get(signs, 0) / max(len(nm_sign_pattern), 1)
            marker = " ← DIFFERENT" if abs(ks_frac - nm_frac) > 0.1 else ""
            print(f"    {signs} correct signs: "
                  f"ks={100*ks_frac:.0f}%, normal={100*nm_frac:.0f}%{marker}")


# ============================================================
# 6. WHAT'S BEYOND — remove ALL keystones, what remains?
# ============================================================

def study_beyond():
    print("\n" + "=" * 70)
    print("6. BEYOND: Remove ALL keystones — what's left?")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15500000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        ks_indices = set(k['idx'] for k in keystones)

        # Remove ALL keystones
        reduced = [c for ci, c in enumerate(clauses) if ci not in ks_indices]
        reduced_sols = find_solutions(reduced, n)
        reduced_frozen = get_frozen(reduced, n, reduced_sols) if len(reduced_sols) >= 2 else set()

        print(f"\n  n={n}, seed={seed}:")
        print(f"    Original: {len(clauses)} clauses, "
              f"{len(frozen)} frozen, {len(solutions)} solutions")
        print(f"    Remove {len(keystones)} keystones:")
        print(f"    Remaining: {len(reduced)} clauses, "
              f"{len(reduced_frozen)} frozen, {len(reduced_sols)} solutions")
        print(f"    Unfrozen: {len(frozen) - len(reduced_frozen)} vars")
        print(f"    New solutions: {len(reduced_sols) - len(solutions)}")

        if len(reduced_frozen) == 0:
            print(f"    → COMPLETELY UNFROZEN! All vars free.")
        elif len(reduced_frozen) < len(frozen):
            print(f"    → PARTIALLY unfrozen. Residual core: {reduced_frozen}")
        else:
            print(f"    → Still frozen (keystones are redundant with each other)")

        # What are the remaining clauses like?
        sat_count = evaluate(reduced, solutions[0])
        print(f"    Original solution satisfies {sat_count}/{len(reduced)} "
              f"remaining clauses")

        break


# ============================================================
# 7. SPACE: In what space do keystones live?
# ============================================================

def study_space():
    print("\n" + "=" * 70)
    print("7. SPACE: The keystone lives between clause-space and solution-space")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+15600000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 3: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]

        # For each keystone: what happens in SOLUTION SPACE when it's removed?
        print(f"\n  n={n}, seed={seed}, {len(solutions)} solutions:")

        for k in keystones[:3]:
            ci = k['idx']
            clause = k['clause']
            reduced = clauses[:ci] + clauses[ci+1:]
            rsols = find_solutions(reduced, n)

            # New solutions that VIOLATE the removed clause
            violating = [s for s in rsols
                        if not any((si==1 and s[vi]==1) or (si==-1 and s[vi]==0)
                                  for vi,si in clause)]

            # Hamming distances between old and new solutions
            new_sols = [s for s in rsols if s not in solutions]
            if new_sols and solutions:
                min_hamming = min(
                    sum(a!=b for a,b in zip(new_sols[0], sol))
                    for sol in solutions)
            else:
                min_hamming = -1

            print(f"\n    Keystone clause {ci}: {clause}")
            print(f"      Power: unfreezes {k['power']} vars {k['unfreezes']}")
            print(f"      Old solutions: {len(solutions)}")
            print(f"      New solutions: {len(rsols)} (+{len(rsols)-len(solutions)})")
            print(f"      Violating removed clause: {len(violating)}")
            if min_hamming >= 0:
                print(f"      Min hamming (new→old): {min_hamming}")

        break


if __name__ == "__main__":
    study_observables()
    study_topology()
    study_hierarchy()
    study_interactions()
    study_creation()
    study_beyond()
    study_space()
