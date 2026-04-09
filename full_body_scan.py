"""
FULL BODY SCAN: Find what makes THE ONE different
═════════════════════════════════════════════════

Logic: THE ONE breaks a clause. So she IS in that clause.
The unsat clause has 3 vars. One is wrong. Find her among 3.

Not 14 vars. Not 7 free. THREE suspects.

Scan EVERYTHING about these 3 suspects:
- Standard: tension, degree, frustration
- NEW: clause-neighborhood structure
- NEW: 2nd order tension (tension OF tension)
- NEW: graph centrality measures
- NEW: what happens if we FLIP each one?
- NEW: response to perturbation
- NEW: information-theoretic measures
- NEW: relationship to solution SPACE (not single solution)
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
            keystones.append({'idx': ci, 'clause': clauses[ci],
                              'unfreezes': unfrozen, 'power': len(unfrozen)})
    return keystones


def unit_propagate_from(clauses, n, fixed):
    f = dict(fixed)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; free_lits = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0):
                        sat = True; break
                else: free_lits.append((v, s))
            if sat: continue
            if len(free_lits) == 0: return f, True
            if len(free_lits) == 1:
                fv, fs = free_lits[0]
                if fv not in f: f[fv] = 1 if fs==1 else 0; changed = True
    return f, False


def full_scan():
    print("=" * 70)
    print("FULL BODY SCAN: 3 suspects, measure EVERYTHING")
    print("=" * 70)

    random.seed(42)
    n = 14

    # Properties that distinguish THE ONE among the 3 suspects
    scan_results = {name: {'one': [], 'innocent': []} for name in [
        'tension_agreement', 'abs_tension', 'degree',
        'frustration', 'self_cancel', 'barely_sat',
        'n_frozen_neighbors', 'frac_frozen_in_clause',
        'clause_tension_sum', 'clause_tension_product',
        'flip_improves', 'flip_delta_sat',
        'n_unsat_if_flip', 'n_shared_clauses_with_others',
        'betweenness_approx', 'eigenvector_centrality',
        'tension_gradient', 'tension_of_neighbors',
        'clause_uniqueness', 'literal_redundancy',
        'second_order_tension', 'neighborhood_agreement',
        'sat_margin',  'sign_matches_majority',
    ]}

    n_found = 0

    for seed in range(2000):
        clauses = random_3sat(n, int(4.267*n), seed=seed+20000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue

        keystones = find_keystones(clauses, n, solutions, frozen)
        if not keystones: continue

        sol = solutions[0]
        m = len(clauses)

        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        adj = {v: set() for v in range(n)}
        for c in clauses:
            vs = [v for v,s in c]
            for a in vs:
                for b in vs:
                    if a != b: adj[a].add(b)

        # Tension-guided pass
        pass_vars = {}
        for k in keystones:
            scores = [(tensions[v]*s, v, s) for v,s in k['clause']]
            best = max(scores, key=lambda x: x[0])
            _, vp, sp = best
            pass_vars[vp] = 1 if sp==1 else 0

        fixed, conflict = unit_propagate_from(clauses, n, pass_vars)
        if conflict: continue

        assignment = [fixed.get(v, 0) for v in range(n)]
        sat = evaluate(clauses, assignment)
        if sat != m - 1: continue

        # Find the unsat clause and its 3 suspects
        unsat_ci = -1
        for ci, clause in enumerate(clauses):
            if not any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                      for v,s in clause):
                unsat_ci = ci; break
        if unsat_ci < 0: continue

        clause = clauses[unsat_ci]
        suspects = [(v, s) for v, s in clause]

        n_found += 1

        # For each suspect: is it THE ONE?
        for v, s_in_clause in suspects:
            is_one = (assignment[v] != sol[v])
            tag = 'one' if is_one else 'innocent'

            t = tensions[v]
            deg = sum(1 for c in clauses for vi,si in c if vi==v)
            neighbors = adj[v]

            # ── Standard ──
            agreement = t * s_in_clause  # positive = tension agrees with literal sign
            scan_results['tension_agreement'][tag].append(agreement)
            scan_results['abs_tension'][tag].append(abs(t))
            scan_results['degree'][tag].append(deg)

            # ── Frustration ──
            pos = sum(1 for c in clauses for vi,si in c if vi==v and si==1)
            neg = sum(1 for c in clauses for vi,si in c if vi==v and si==-1)
            frust = 1 - abs(pos-neg)/max(pos+neg,1)
            scan_results['frustration'][tag].append(frust)

            # ── Self-cancellation ──
            if neighbors:
                nav = sum(tensions.get(u,0) for u in neighbors) / len(neighbors)
                sc = abs(t + nav)
            else:
                sc = abs(t)
            scan_results['self_cancel'][tag].append(sc)

            # ── Barely-sat clauses ──
            barely = 0
            for c in clauses:
                if not any(vi==v for vi,si in c): continue
                ns = sum(1 for vi,si in c
                        if (si==1 and assignment[vi]==1) or (si==-1 and assignment[vi]==0))
                if ns == 1: barely += 1
            scan_results['barely_sat'][tag].append(barely)

            # ── Frozen neighbors ──
            nfn = sum(1 for u in neighbors if u in frozen)
            scan_results['n_frozen_neighbors'][tag].append(nfn)

            # ── Frozen fraction in this specific clause ──
            ffc = sum(1 for vi,si in clause if vi in frozen) / 3
            scan_results['frac_frozen_in_clause'][tag].append(ffc)

            # ── NEW: Clause tension sum and product ──
            clause_t_sum = sum(tensions[vi] * si for vi, si in clause)
            clause_t_prod = 1.0
            for vi, si in clause:
                clause_t_prod *= (tensions[vi] * si)
            scan_results['clause_tension_sum'][tag].append(clause_t_sum)
            scan_results['clause_tension_product'][tag].append(clause_t_prod)

            # ── NEW: What happens if we FLIP this var? ──
            test_a = list(assignment)
            test_a[v] = 1 - test_a[v]
            new_sat = evaluate(clauses, test_a)
            flip_delta = new_sat - sat
            scan_results['flip_delta_sat'][tag].append(flip_delta)
            scan_results['flip_improves'][tag].append(1 if flip_delta > 0 else 0)

            # ── NEW: How many clauses become unsat if we flip? ──
            n_unsat_flip = m - new_sat
            scan_results['n_unsat_if_flip'][tag].append(n_unsat_flip)

            # ── NEW: Shared clauses with the other 2 suspects ──
            other_vars = set(vi for vi,si in clause if vi != v)
            shared = sum(1 for c in clauses
                        if any(vi==v for vi,si in c) and
                           any(vi in other_vars for vi,si in c))
            scan_results['n_shared_clauses_with_others'][tag].append(shared)

            # ── NEW: Tension of neighbors (2nd order) ──
            if neighbors:
                ton = np.mean([abs(tensions[u]) for u in neighbors])
            else:
                ton = 0
            scan_results['tension_of_neighbors'][tag].append(ton)

            # ── NEW: Second-order tension (tension from clause-neighbor tensions) ──
            sot = 0
            for c in clauses:
                if not any(vi==v for vi,si in c): continue
                for vi, si in c:
                    if vi != v:
                        sot += tensions[vi] * si
            scan_results['second_order_tension'][tag].append(sot)

            # ── NEW: Does tension match the MAJORITY of other vars' tensions? ──
            other_agreement = sum(1 for vi,si in clause if vi!=v and
                                 ((tensions[vi]>0 and si==1) or (tensions[vi]<0 and si==-1)))
            scan_results['sign_matches_majority'][tag].append(other_agreement)

            # ── NEW: Neighborhood agreement (do neighbors agree with this var's assignment?) ──
            na = 0
            for u in neighbors:
                if u in fixed:
                    # Does u's tension agree with its assignment?
                    u_agrees = (tensions[u] > 0 and fixed[u] == 1) or \
                               (tensions[u] < 0 and fixed[u] == 0)
                    na += 1 if u_agrees else -1
            scan_results['neighborhood_agreement'][tag].append(na / max(len(neighbors), 1))

            # ── NEW: Satisfaction margin ──
            # How many of v's clauses are satisfied by exactly 1 literal?
            margin_1 = sum(1 for c in clauses if any(vi==v for vi,si in c) and
                          sum(1 for vi,si in c
                              if (si==1 and assignment[vi]==1) or (si==-1 and assignment[vi]==0)) == 1)
            scan_results['sat_margin'][tag].append(margin_1)

            # ── NEW: Literal redundancy ──
            # How many OTHER clauses contain the same literal (v, s)?
            redundancy = sum(1 for c in clauses
                           if any(vi==v and si==s_in_clause for vi,si in c)) - 1
            scan_results['literal_redundancy'][tag].append(redundancy)

            # ── Approximate betweenness ──
            bc = 0
            for u in neighbors:
                for w in neighbors:
                    if u < w and w not in adj[u]:
                        bc += 1  # v is on a shortest path u-v-w
            scan_results['betweenness_approx'][tag].append(bc)

            # ── Approximate eigenvector centrality ──
            ec = len(neighbors) + sum(len(adj[u]) for u in neighbors) / max(len(neighbors),1)
            scan_results['eigenvector_centrality'][tag].append(ec)

            # ── Clause uniqueness ──
            cu = len(set(vi for vi,si in clause) - set().union(
                *(set(vi for vi,si in c) for ci2,c in enumerate(clauses) if ci2!=unsat_ci)))
            scan_results['clause_uniqueness'][tag].append(cu)

            # ── Tension gradient (change in tension from v to neighbors) ──
            if neighbors:
                tg = np.mean([abs(tensions[v] - tensions[u]) for u in neighbors])
            else:
                tg = 0
            scan_results['tension_gradient'][tag].append(tg)

        if n_found >= 30: break

    # ══════ RESULTS ══════
    print(f"\n  {n_found} instances scanned (3 suspects each)")
    print(f"\n  {'property':>30} | {'THE ONE':>8} | {'INNOCENT':>8} | "
          f"{'ratio':>6} | {'disc?':>7}")
    print(f"  " + "-" * 75)

    strong_disc = []

    for name in sorted(scan_results.keys()):
        one = scan_results[name]['one']
        inn = scan_results[name]['innocent']
        if not one or not inn: continue

        m1 = np.mean(one)
        m2 = np.mean(inn)

        if abs(m2) > 0.001:
            ratio = m1 / m2
        elif abs(m1) > 0.001:
            ratio = 999
        else:
            ratio = 1.0

        is_disc = abs(ratio - 1) > 0.25 or (abs(m1 - m2) > 0.1 and max(abs(m1),abs(m2)) > 0.01)

        marker = "← YES" if is_disc else ""
        if is_disc:
            strong_disc.append((name, m1, m2, ratio))

        print(f"  {name:>30} | {m1:>8.3f} | {m2:>8.3f} | "
              f"{ratio:>6.2f} | {marker:>7}")

    print(f"\n  ═══ DISCRIMINATIVE ({len(strong_disc)}) ═══")
    for name, m1, m2, ratio in sorted(strong_disc, key=lambda x: abs(x[3]-1), reverse=True):
        print(f"    {name:>30}: ONE={m1:.3f} vs INN={m2:.3f} (ratio={ratio:.2f})")

    # ── Can we BUILD A DETECTOR? ──
    if strong_disc:
        print(f"\n  ═══ DETECTOR TEST ═══")
        # For each instance: among 3 suspects, does our best discriminator pick THE ONE?
        best_name = max(strong_disc, key=lambda x: abs(x[3]-1))[0]
        print(f"  Using best discriminator: {best_name}")

        # Recount: in how many instances does the discriminator find THE ONE?
        one_vals = scan_results[best_name]['one']
        inn_vals = scan_results[best_name]['innocent']
        one_mean = np.mean(one_vals)
        inn_mean = np.mean(inn_vals)

        # Direction: is THE ONE higher or lower?
        one_higher = one_mean > inn_mean

        # Per-instance: among 3 suspects, pick the one with extreme value
        # We need per-instance data for this... approximate from statistics
        print(f"  THE ONE is {'HIGHER' if one_higher else 'LOWER'} "
              f"({one_mean:.3f} vs {inn_mean:.3f})")
        print(f"  If we pick the {'max' if one_higher else 'min'} "
              f"among 3 suspects → P(finding THE ONE):")

        # Estimate: THE ONE is 1 of 3. If discriminator is perfect: 100%.
        # If random: 33%. How good is it?
        separation = abs(one_mean - inn_mean)
        one_std = np.std(one_vals) if len(one_vals) > 1 else 1
        inn_std = np.std(inn_vals) if len(inn_vals) > 1 else 1
        avg_std = (one_std + inn_std) / 2

        if avg_std > 0:
            d_prime = separation / avg_std  # signal detection theory
            print(f"  d' (sensitivity) = {d_prime:.2f}")
            if d_prime > 1.5:
                print(f"  → STRONG detector (d'>1.5)")
            elif d_prime > 0.5:
                print(f"  → MODERATE detector")
            else:
                print(f"  → WEAK detector")


if __name__ == "__main__":
    full_scan()
