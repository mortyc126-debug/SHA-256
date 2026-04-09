"""
INSIDE THE KEYSTONE: What universe lives inside the wall?
═════════════════════════════════════════════════════════

A keystone clause has 3 literals. Each literal is a sign×variable.
The keystone barely satisfies (1/3 correct).
The 2 "wrong" literals FIGHT the solution.

WHAT'S INSIDE:

1. The TENSION FIELD inside a keystone — 3 forces on 3 vars
2. The FRUSTRATION STRUCTURE — which pairs inside fight each other?
3. The CLAUSE'S OWN SOLUTION — what would this clause "want"?
4. The SHADOW — what information does the keystone HIDE?
5. The BRIDGE — what connects the two clusters it separates?
6. The LIFE CYCLE — how does a keystone form and could it dissolve?
7. The RECURSIVE STRUCTURE — are there keystones WITHIN keystones?
8. The DUAL — what is a keystone from the SOLUTION-SPACE perspective?
"""

import numpy as np
import random
import math
from collections import Counter
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def get_frozen(clauses, n, solutions):
    return set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)


def find_keystones(clauses, n, solutions, frozen):
    keystones = []
    for ci in range(len(clauses)):
        reduced = clauses[:ci] + clauses[ci+1:]
        rsols = find_solutions(reduced, n)
        if len(rsols) < 2: continue
        rf = get_frozen(reduced, n, rsols)
        unfrozen = frozen - rf
        if unfrozen:
            keystones.append({
                'idx': ci, 'clause': clauses[ci], 'unfreezes': unfrozen,
                'power': len(unfrozen), 'new_solutions': rsols,
            })
    return keystones


# ============================================================
# 1. THE TENSION FIELD inside a single keystone
# ============================================================

def study_internal_field():
    print("=" * 70)
    print("1. INTERNAL FIELD: The 3 forces inside one keystone")
    print("=" * 70)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]

        print(f"\n  n={n}, seed={seed}:")

        for k in keystones[:3]:
            clause = k['clause']
            ci = k['idx']

            print(f"\n  ── Keystone clause {ci}: {clause} ──")
            print(f"      Power: {k['power']}, unfreezes: {k['unfreezes']}")

            for v, s in clause:
                # This literal's tension
                p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
                p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
                tension = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

                # Is this the "saving" literal?
                saves = (s==1 and sol[v]==1) or (s==-1 and sol[v]==0)

                # What does this literal WANT? (sign direction)
                wants = 1 if s == 1 else 0

                # What does the SOLUTION give?
                has = sol[v]

                frozen_status = "FROZEN" if v in frozen else "free"

                print(f"      var x{v}: sign={s:+d}, sol={has}, "
                      f"wants={wants}, saves={'YES' if saves else 'no'}, "
                      f"tension={tension:+.3f}, {frozen_status}")

            # The internal frustration: which pairs fight?
            print(f"\n      Internal structure:")
            lits = [(v, s, sol[v]) for v, s in clause]
            n_saves = sum(1 for v,s,val in lits
                        if (s==1 and val==1) or (s==-1 and val==0))
            print(f"      Saving literals: {n_saves}/3")
            print(f"      Fighting literals: {3-n_saves}/3")

            # What would satisfy ALL 3 literals?
            ideal = []
            for v, s in clause:
                ideal_val = 1 if s == 1 else 0
                ideal.append((v, ideal_val))
            print(f"      Clause's ideal: {ideal}")
            print(f"      Solution gives:  {[(v, sol[v]) for v,s in clause]}")
            conflicts = sum(1 for (v1,i1),(v2,s2) in zip(ideal, [(v,sol[v]) for v,s in clause])
                          if i1 != s2)
            print(f"      Conflicts: {conflicts}/3")

        break


# ============================================================
# 2. THE SHADOW: What information does the keystone HIDE?
# ============================================================

def study_shadow():
    print("\n" + "=" * 70)
    print("2. THE SHADOW: What does the keystone hide?")
    print("=" * 70)

    print("""
    When a keystone exists, certain solutions are BLOCKED.
    The "shadow" = the set of solutions that WOULD exist without it.
    What do these shadow solutions look like?
    """)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16100000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]

        for k in keystones[:2]:
            ci = k['idx']
            new_sols = k['new_solutions']
            shadow_sols = [s for s in new_sols if s not in solutions]

            print(f"\n  Keystone {ci}: {k['clause']}")
            print(f"    Original solutions: {len(solutions)}")
            print(f"    Shadow solutions:   {len(shadow_sols)}")

            if shadow_sols:
                # How do shadow solutions differ from original?
                for si, shadow in enumerate(shadow_sols[:3]):
                    # Find closest original solution
                    min_h = n
                    closest = None
                    for orig in solutions:
                        h = sum(a != b for a, b in zip(shadow, orig))
                        if h < min_h: min_h = h; closest = orig

                    diff_vars = [v for v in range(n) if shadow[v] != closest[v]]

                    # Are the different vars frozen or free?
                    diff_frozen = [v for v in diff_vars if v in frozen]
                    diff_free = [v for v in diff_vars if v not in frozen]

                    print(f"\n    Shadow {si+1}: hamming={min_h} from nearest original")
                    print(f"      Changed vars: {diff_vars}")
                    print(f"      Of which frozen: {diff_frozen}")
                    print(f"      Of which free: {diff_free}")
                    print(f"      → Shadow flips {len(diff_frozen)} FROZEN + "
                          f"{len(diff_free)} free vars")

                    # Does the shadow violate the keystone?
                    violates = not any(
                        (s==1 and shadow[v]==1) or (s==-1 and shadow[v]==0)
                        for v, s in k['clause'])
                    print(f"      Violates keystone: {'YES' if violates else 'no'}")

        break


# ============================================================
# 3. THE BRIDGE: What connects the two clusters?
# ============================================================

def study_bridge():
    print("\n" + "=" * 70)
    print("3. THE BRIDGE: What's between the clusters?")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16200000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        # Find the strongest keystone
        strongest = max(keystones, key=lambda k: k['power'])
        ci = strongest['idx']
        new_sols = strongest['new_solutions']
        shadow_sols = [s for s in new_sols if s not in solutions]

        if not shadow_sols: continue

        print(f"\n  Strongest keystone {ci}: power={strongest['power']}")
        print(f"  Clusters: {len(solutions)} original + {len(shadow_sols)} shadow")

        # Measure the "bridge" between clusters
        # What's the minimum hamming between original and shadow?
        min_bridge = n
        bridge_pair = None
        for orig in solutions:
            for shadow in shadow_sols:
                h = sum(a != b for a, b in zip(orig, shadow))
                if h < min_bridge:
                    min_bridge = h
                    bridge_pair = (orig, shadow)

        if bridge_pair:
            orig, shadow = bridge_pair
            bridge_vars = [v for v in range(n) if orig[v] != shadow[v]]

            print(f"\n  Minimum bridge: hamming = {min_bridge}")
            print(f"  Bridge variables: {bridge_vars}")
            print(f"    Original: {[orig[v] for v in bridge_vars]}")
            print(f"    Shadow:   {[shadow[v] for v in bridge_vars]}")

            # Are bridge vars frozen?
            bridge_frozen = [v for v in bridge_vars if v in frozen]
            bridge_free = [v for v in bridge_vars if v not in frozen]
            print(f"    Frozen in bridge: {bridge_frozen}")
            print(f"    Free in bridge: {bridge_free}")

            # What's the STRUCTURE of the bridge?
            # Which clauses constrain the bridge vars?
            bridge_clauses = []
            for cj, clause in enumerate(clauses):
                vs = set(v for v, s in clause)
                if vs & set(bridge_vars):
                    # Does this clause distinguish orig from shadow?
                    sat_orig = any((s==1 and orig[v]==1) or (s==-1 and orig[v]==0)
                                  for v, s in clause)
                    sat_shadow = any((s==1 and shadow[v]==1) or (s==-1 and shadow[v]==0)
                                    for v, s in clause)
                    if sat_orig != sat_shadow:
                        bridge_clauses.append(cj)

            print(f"\n  Distinguishing clauses (sat by one but not other): "
                  f"{len(bridge_clauses)}")
            print(f"  Keystone is one of them: "
                  f"{'YES' if ci in bridge_clauses else 'NO'}")
            if bridge_clauses:
                print(f"  Bridge clause indices: {bridge_clauses[:10]}")

        break


# ============================================================
# 4. RECURSIVE: Are there keystones within keystones?
# ============================================================

def study_recursive():
    print("\n" + "=" * 70)
    print("4. RECURSIVE: Keystones within keystones?")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16300000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if len(keystones) < 3: continue

        # Remove strongest keystone → new instance
        strongest = max(keystones, key=lambda k: k['power'])
        ci = strongest['idx']
        reduced = clauses[:ci] + clauses[ci+1:]
        rsols = strongest['new_solutions']
        rfrozen = get_frozen(reduced, len(reduced[0]) if reduced else n, rsols)

        print(f"\n  Level 0: {len(clauses)} clauses, {len(frozen)} frozen, "
              f"{len(keystones)} keystones")

        if len(rfrozen) >= 2 and len(rsols) >= 2:
            # Find keystones in the REDUCED instance
            rkeystones = find_keystones(reduced, n, rsols, rfrozen)

            print(f"  Level 1 (remove ks {ci}): "
                  f"{len(reduced)} clauses, {len(rfrozen)} frozen, "
                  f"{len(rkeystones)} keystones")

            if rkeystones:
                # Go one more level
                strongest2 = max(rkeystones, key=lambda k: k['power'])
                ci2 = strongest2['idx']
                reduced2 = reduced[:ci2] + reduced[ci2+1:]
                rsols2 = strongest2['new_solutions']
                rfrozen2 = get_frozen(reduced2, n, rsols2) if len(rsols2)>=2 else set()

                if rfrozen2 and len(rsols2) >= 2:
                    rkeystones2 = find_keystones(reduced2, n, rsols2, rfrozen2)
                    print(f"  Level 2 (remove ks {ci2}): "
                          f"{len(reduced2)} clauses, {len(rfrozen2)} frozen, "
                          f"{len(rkeystones2)} keystones")
                else:
                    print(f"  Level 2: {len(rfrozen2)} frozen — "
                          f"{'FULLY UNFROZEN' if not rfrozen2 else 'minimal core'}")
            else:
                print(f"  Level 1: no keystones — FULLY UNFROZEN")
        else:
            print(f"  Level 1: {len(rfrozen)} frozen — minimal core")

        break


# ============================================================
# 5. THE DUAL: Keystone from solution-space perspective
# ============================================================

def study_dual():
    print("\n" + "=" * 70)
    print("5. THE DUAL: Solution-space view of keystones")
    print("=" * 70)

    random.seed(42)
    n = 12

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16400000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 3: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        m = len(clauses)

        # For each pair of solutions: which clauses SEPARATE them?
        # (satisfied by one but not the other)
        print(f"\n  n={n}, seed={seed}: {len(solutions)} solutions, "
              f"{len(keystones)} keystones")

        # Build solution adjacency graph (hamming distance)
        print(f"\n  Solution space:")
        for i in range(min(len(solutions), 5)):
            for j in range(i+1, min(len(solutions), 5)):
                h = sum(a!=b for a,b in zip(solutions[i], solutions[j]))
                # Clauses that separate these two solutions
                separating = []
                for ci, clause in enumerate(clauses):
                    sat_i = any((s==1 and solutions[i][v]==1) or
                               (s==-1 and solutions[i][v]==0) for v,s in clause)
                    sat_j = any((s==1 and solutions[j][v]==1) or
                               (s==-1 and solutions[j][v]==0) for v,s in clause)
                    if sat_i and not sat_j:
                        separating.append(ci)
                    elif sat_j and not sat_i:
                        separating.append(ci)

                print(f"    sol{i}↔sol{j}: hamming={h}, "
                      f"separating clauses={len(separating)}")

        # Now: for shadow solutions (from keystone removal)
        for k in keystones[:1]:
            shadow_sols = [s for s in k['new_solutions'] if s not in solutions]
            if not shadow_sols: continue

            print(f"\n  Shadow solutions (keystone {k['idx']} removed):")
            for si, shadow in enumerate(shadow_sols[:3]):
                # Distance to each original
                for i in range(min(len(solutions), 3)):
                    h = sum(a!=b for a,b in zip(shadow, solutions[i]))
                    # How many clauses does shadow violate?
                    violations = m - evaluate(clauses, shadow)
                    print(f"    shadow{si}↔sol{i}: hamming={h}, "
                          f"violations={violations}")

        break


# ============================================================
# 6. THE SPECTRUM OF WALLS: Keystone clause as operator
# ============================================================

def study_operator():
    print("\n" + "=" * 70)
    print("6. THE OPERATOR: Each clause as a linear constraint")
    print("=" * 70)

    print("""
    Each clause C = (l1 ∨ l2 ∨ l3) defines a FORBIDDEN REGION
    in {0,1}^n: the single assignment that violates all 3 literals.

    For keystone clause with signs (s1,s2,s3):
      Forbidden point = (1-s1, 1-s2, 1-s3) mapped to the vars.

    The keystone's forbidden point is CLOSE to the solution
    (differs by only 2 bits, since 2/3 signs are "wrong").
    Normal clauses' forbidden points are FAR from solution
    (differ by 0-1 bits, since 2-3/3 signs are "right").
    """)

    random.seed(42)
    n = 14

    for seed in range(100):
        clauses = random_3sat(n, int(4.267*n), seed=seed+16500000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 4: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]
        ks_indices = set(k['idx'] for k in keystones)

        ks_distances = []
        normal_distances = []

        for ci, clause in enumerate(clauses):
            # Compute the forbidden point
            forbidden = {}
            for v, s in clause:
                forbidden[v] = 0 if s == 1 else 1  # value that makes literal false

            # Hamming distance from forbidden point to solution (on clause vars only)
            dist = sum(1 for v in forbidden if forbidden[v] != sol[v])
            # dist = number of clause vars where forbidden ≠ solution
            # = number of "correct" signs (literals that solution satisfies)

            if ci in ks_indices:
                ks_distances.append(dist)
            else:
                normal_distances.append(dist)

        print(f"\n  n={n}, seed={seed}:")
        print(f"  Distance from forbidden point to solution:")
        print(f"    Keystones: avg={np.mean(ks_distances):.2f} "
              f"(dist of {Counter(ks_distances)})")
        print(f"    Normal:    avg={np.mean(normal_distances):.2f} "
              f"(dist of {Counter(normal_distances)})")
        print(f"\n  INTERPRETATION:")
        print(f"    Keystone forbidden point is {np.mean(ks_distances):.1f} "
              f"bits from solution")
        print(f"    Normal forbidden point is {np.mean(normal_distances):.1f} "
              f"bits from solution")
        if np.mean(ks_distances) < np.mean(normal_distances):
            print(f"    → Keystone's WALL is CLOSER to the solution!")
            print(f"    → It forbids a NEARBY region, creating a tight cage")
        else:
            print(f"    → Keystone's wall is farther (unexpected)")

        break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    study_internal_field()
    study_shadow()
    study_bridge()
    study_recursive()
    study_dual()
    study_operator()
