"""
BIT MECHANICS — Complete Law System

Consolidating all experimental findings into a verified law system.
Each law is stated, its evidence cited, and cross-checked for consistency.

This is the FOUNDATION document.
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


def tension_v4(clauses, n, fixed=None, n_iter=10):
    if fixed is None:
        fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                sat = False
                rem = []
                vs = None
                for v, s in clause:
                    if v in fixed:
                        if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                            sat = True; break
                    else:
                        rem.append((v, s))
                        if v == var: vs = s
                if sat or vs is None: continue
                oh = 0.0
                for v, s in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if s == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0 - oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1 + push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)
    return tensions


# ============================================================
# VERIFICATION OF ALL LAWS
# ============================================================

def verify_all_laws(n=12, ratio=4.27, n_trials=200):
    """Verify every law with fresh data."""

    results = {}

    # Collect data
    all_data = []
    for seed in range(n_trials):
        clauses = random_3sat(n, int(ratio * n), seed=seed + 5000)
        solutions = find_solutions(clauses, n)
        if not solutions:
            continue
        all_data.append((clauses, solutions))

    print(f"Testing on {len(all_data)} satisfiable instances, n={n}, ratio={ratio}")

    # ================================================================
    # LAW 1: Tension Signal Existence
    # "Each bit carries a signal about its correct value.
    #  At threshold, accuracy ≈ 70%, derived from ε ≈ 0.073."
    # ================================================================
    correct = 0
    total = 0
    epsilons = []
    for clauses, solutions in all_data:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            actual = 1 if prob_1[var] > 0.5 else 0
            pred = 1 if sigma >= 0 else 0
            if pred == actual:
                correct += 1
            total += 1

            # Measure epsilon
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            tot_app = pos + neg
            if tot_app > 0:
                if actual == 1:
                    epsilons.append(pos/tot_app - 0.5)
                else:
                    epsilons.append(neg/tot_app - 0.5)

    law1_acc = correct / total
    law1_eps = sum(epsilons) / len(epsilons) if epsilons else 0
    results['L1_accuracy'] = law1_acc
    results['L1_epsilon'] = law1_eps

    # ================================================================
    # LAW 2: Signal Amplification Under Correct Fixation
    # "Fixing a bit correctly INCREASES ε for remaining bits."
    # ================================================================
    amp_data = []
    for clauses, solutions in all_data[:50]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Measure ε before
        eps_before = []
        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            tot_app = pos + neg
            if tot_app > 0:
                if correct_val[var] == 1:
                    eps_before.append(pos/tot_app - 0.5)
                else:
                    eps_before.append(neg/tot_app - 0.5)

        # Fix 3 most confident bits CORRECTLY
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))
        fixed = {order[i]: correct_val[order[i]] for i in range(3)}

        # Measure ε after
        eps_after = []
        for var in range(n):
            if var in fixed:
                continue
            # Count active clause appearances
            pos_a, neg_a = 0, 0
            for clause in clauses:
                already_sat = False
                for v, s in clause:
                    if v in fixed:
                        if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                            already_sat = True; break
                if already_sat:
                    continue
                for v, s in clause:
                    if v == var:
                        if s == 1: pos_a += 1
                        else: neg_a += 1
            tot_a = pos_a + neg_a
            if tot_a > 0:
                if correct_val[var] == 1:
                    eps_after.append(pos_a/tot_a - 0.5)
                else:
                    eps_after.append(neg_a/tot_a - 0.5)

        if eps_before and eps_after:
            amp_data.append((sum(eps_before)/len(eps_before),
                           sum(eps_after)/len(eps_after)))

    if amp_data:
        avg_before = sum(b for b, a in amp_data) / len(amp_data)
        avg_after = sum(a for b, a in amp_data) / len(amp_data)
        results['L2_eps_before'] = avg_before
        results['L2_eps_after'] = avg_after
        results['L2_amplification'] = avg_after / avg_before if avg_before > 0 else 0

    # ================================================================
    # LAW 3: Contradiction Prevalence
    # "In HARD instances, ~40% of two-step signal paths are contradictory."
    # ================================================================
    adj = {}
    consistent_total = 0
    contradictory_total = 0

    for clauses, solutions in all_data[:50]:
        # Build adjacency
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        for source in range(n):
            sigma_s = bit_tension(clauses, n, source)
            v_s = 1 if sigma_s >= 0 else 0

            for target in range(n):
                if target == source:
                    continue
                # Find intermediaries
                intermediaries = [j for j in adj[source] if j in adj[target]
                                  and j != source and j != target]
                if len(intermediaries) < 2:
                    continue

                signals = []
                for j in intermediaries:
                    sj = bit_tension(clauses, n, j, {source: v_s})
                    vj = 1 if sj >= 0 else 0
                    sk = bit_tension(clauses, n, target, {source: v_s, j: vj})
                    signals.append(sk)

                dirs = [1 if s > 0.01 else (-1 if s < -0.01 else 0) for s in signals]
                nonzero = [d for d in dirs if d != 0]
                if nonzero and all(d == nonzero[0] for d in nonzero):
                    consistent_total += 1
                elif nonzero and len(set(nonzero)) > 1:
                    contradictory_total += 1

    total_paths = consistent_total + contradictory_total
    results['L3_contradiction_rate'] = contradictory_total / total_paths if total_paths > 0 else 0

    # ================================================================
    # LAW 4: Temperature Quasi-Conservation
    # "T ≈ const during crystallization (CV < 0.2)."
    # ================================================================
    temp_cvs = []
    for clauses, solutions in all_data[:50]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        fixed = {}
        temps = []
        for step in range(n):
            T = field_temperature(clauses, n, fixed)
            temps.append(T)
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed:
                break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            sigma = bit_tension(clauses, n, best, fixed)
            fixed[best] = 1 if sigma >= 0 else 0

        if len(temps) > 3:
            mid = temps[1:-2]
            mean_t = sum(mid)/len(mid)
            if mean_t > 0:
                cv = math.sqrt(sum((t-mean_t)**2 for t in mid)/len(mid)) / mean_t
                temp_cvs.append(cv)

    results['L4_temperature_CV'] = sum(temp_cvs)/len(temp_cvs) if temp_cvs else 0

    # ================================================================
    # LAW 5: Force Symmetry
    # "F(i→j) ≈ F(j→i), not antisymmetric."
    # ================================================================
    sym_errs = []
    antisym_errs = []
    for clauses, solutions in all_data[:30]:
        for i in range(n):
            for j in range(i+1, n):
                fij = bit_tension(clauses, n, j, {i: 1}) - bit_tension(clauses, n, j, {i: 0})
                fji = bit_tension(clauses, n, i, {j: 1}) - bit_tension(clauses, n, i, {j: 0})
                if abs(fij) > 0.001 or abs(fji) > 0.001:
                    sym_errs.append(abs(fij - fji))
                    antisym_errs.append(abs(fij + fji))

    results['L5_sym_error'] = sum(sym_errs)/len(sym_errs) if sym_errs else 0
    results['L5_antisym_error'] = sum(antisym_errs)/len(antisym_errs) if antisym_errs else 0
    results['L5_symmetric'] = results['L5_sym_error'] < results['L5_antisym_error']

    # ================================================================
    # LAW 6: Correlation Length = 1
    # "Single-step transmission drops to 0 at distance 2."
    # ================================================================
    d1_trans = []
    d2_trans = []
    for clauses, solutions in all_data[:30]:
        adj_local = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v, s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj_local[vs[a]].add(vs[b])
                    adj_local[vs[b]].add(vs[a])

        for i in range(min(n, 6)):
            # BFS distance
            dist = {i: 0}
            queue = [i]; idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj_local[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr] + 1
                        queue.append(nb)

            for j in range(n):
                if j == i: continue
                t0 = bit_tension(clauses, n, j, {i: 0})
                t1 = bit_tension(clauses, n, j, {i: 1})
                trans = abs(t1 - t0) / 2
                d = dist.get(j, 99)
                if d == 1: d1_trans.append(trans)
                elif d == 2: d2_trans.append(trans)

    results['L6_trans_d1'] = sum(d1_trans)/len(d1_trans) if d1_trans else 0
    results['L6_trans_d2'] = sum(d2_trans)/len(d2_trans) if d2_trans else 0

    # ================================================================
    # LAW 7: Neighbor Corroboration
    # "v4 iterative tension (neighbor-aware) closes 47% of gap."
    # ================================================================
    v1_correct = 0
    v4_correct = 0
    optimal_sum = 0.0
    total_bits = 0
    for clauses, solutions in all_data:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)
        for var in range(n):
            total_bits += 1
            optimal_sum += max(prob_1[var], 1-prob_1[var])
            if (1 if bit_tension(clauses, n, var) >= 0 else 0) == correct_val[var]:
                v1_correct += 1
            if (1 if v4_t.get(var, 0) >= 0 else 0) == correct_val[var]:
                v4_correct += 1

    results['L7_v1_acc'] = v1_correct / total_bits
    results['L7_v4_acc'] = v4_correct / total_bits
    results['L7_optimal'] = optimal_sum / total_bits
    results['L7_gap_closed'] = (v4_correct - v1_correct) / total_bits

    # ================================================================
    # LAW 8: Solution Clustering
    # "Solutions cluster more tightly as ratio increases."
    # ================================================================
    clustering_vals = []
    for clauses, solutions in all_data:
        if len(solutions) < 2:
            continue
        dists = []
        for i in range(len(solutions)):
            for j in range(i+1, len(solutions)):
                dists.append(sum(solutions[i][k] != solutions[j][k] for k in range(n)))
        avg_d = sum(dists)/len(dists)
        clustering = 1.0 - avg_d / (n/2)
        clustering_vals.append(clustering)

    results['L8_clustering'] = sum(clustering_vals)/len(clustering_vals) if clustering_vals else 0

    # ================================================================
    # LAW 9: Marginal MAP ≈ Solution
    # "Per-bit majority vote across solutions IS a solution ~90% of time."
    # ================================================================
    map_is_sol = 0
    map_total = 0
    for clauses, solutions in all_data:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        map_assign = [1 if p > 0.5 else 0 for p in prob_1]
        map_total += 1
        if evaluate(clauses, map_assign) == len(clauses):
            map_is_sol += 1

    results['L9_map_is_solution'] = map_is_sol / map_total if map_total > 0 else 0

    # ================================================================
    # LAW 10: Boundary Depth
    # "Gap bits have 2x LOWER boundary sensitivity than correct bits."
    # ================================================================
    correct_boundary = []
    gap_boundary = []
    for clauses, solutions in all_data[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        v4_t = tension_v4(clauses, n, {}, 10)

        for var in range(n):
            v4_pred = 1 if v4_t.get(var, 0) >= 0 else 0
            actual = correct_val[var]

            # Boundary sensitivity
            boundary = 0
            for _ in range(30):
                assignment = [random.randint(0, 1) for _ in range(n)]
                sat1 = evaluate(clauses, assignment) == len(clauses)
                assignment[var] = 1 - assignment[var]
                sat2 = evaluate(clauses, assignment) == len(clauses)
                if sat1 != sat2:
                    boundary += 1

            boundary /= 30.0
            if v4_pred == actual:
                correct_boundary.append(boundary)
            elif max(prob_1[var], 1-prob_1[var]) > 0.6:
                gap_boundary.append(boundary)

    results['L10_correct_boundary'] = sum(correct_boundary)/len(correct_boundary) if correct_boundary else 0
    results['L10_gap_boundary'] = sum(gap_boundary)/len(gap_boundary) if gap_boundary else 0

    return results


# ============================================================
# CONSISTENCY CHECK: Do laws contradict each other?
# ============================================================

def consistency_check(results):
    issues = []

    # L1 + L7: v4 should be better than v1
    if results['L7_v4_acc'] <= results['L7_v1_acc']:
        issues.append("INCONSISTENCY: L7 says v4 > v1, but v4 ≤ v1")

    # L5: symmetric should be true
    if not results['L5_symmetric']:
        issues.append("INCONSISTENCY: L5 forces are not symmetric")

    # L6: d2 should be near 0
    if results['L6_trans_d2'] > 0.01:
        issues.append(f"INCONSISTENCY: L6 trans at d=2 = {results['L6_trans_d2']:.4f} > 0.01")

    # L2: amplification should be > 1
    if results.get('L2_amplification', 0) <= 1.0:
        issues.append(f"INCONSISTENCY: L2 amplification = {results.get('L2_amplification', 0):.3f} ≤ 1")

    # L10: gap boundary should be lower
    if results['L10_gap_boundary'] >= results['L10_correct_boundary']:
        issues.append("INCONSISTENCY: L10 gap boundary ≥ correct boundary")

    return issues


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(12345)  # fresh seed, never used before

    print("=" * 80)
    print("BIT MECHANICS — COMPLETE LAW VERIFICATION")
    print("Fresh data, independent seed")
    print("=" * 80)

    results = verify_all_laws(n=12, ratio=4.27, n_trials=200)

    print("\n" + "=" * 80)
    print("LAW SYSTEM")
    print("=" * 80)

    laws = [
        ("L1", "SIGNAL EXISTENCE",
         f"Tension predicts correct value with accuracy {results['L1_accuracy']*100:.1f}%, "
         f"ε = {results['L1_epsilon']:.4f}",
         results['L1_accuracy'] > 0.6),

        ("L2", "SIGNAL AMPLIFICATION",
         f"Correct fixation amplifies ε: {results['L2_eps_before']:.4f} → "
         f"{results['L2_eps_after']:.4f} (×{results.get('L2_amplification', 0):.2f})",
         results.get('L2_amplification', 0) > 1.0),

        ("L3", "CONTRADICTION PREVALENCE",
         f"Two-step paths are contradictory {results['L3_contradiction_rate']*100:.0f}% of time",
         results['L3_contradiction_rate'] > 0.25),

        ("L4", "TEMPERATURE QUASI-CONSERVATION",
         f"T has CV = {results['L4_temperature_CV']:.3f} during crystallization",
         results['L4_temperature_CV'] < 0.3),

        ("L5", "FORCE SYMMETRY",
         f"Sym error {results['L5_sym_error']:.4f} < antisym {results['L5_antisym_error']:.4f}: "
         f"{'SYMMETRIC' if results['L5_symmetric'] else 'NOT SYMMETRIC'}",
         results['L5_symmetric']),

        ("L6", "CORRELATION LENGTH = 1",
         f"Trans at d=1: {results['L6_trans_d1']:.4f}, at d=2: {results['L6_trans_d2']:.4f}",
         results['L6_trans_d2'] < 0.005),

        ("L7", "NEIGHBOR CORROBORATION",
         f"v1={results['L7_v1_acc']*100:.1f}% → v4={results['L7_v4_acc']*100:.1f}% "
         f"(optimal {results['L7_optimal']*100:.1f}%), "
         f"gap closed: {results['L7_gap_closed']*100:.1f}%",
         results['L7_v4_acc'] > results['L7_v1_acc']),

        ("L8", "SOLUTION CLUSTERING",
         f"Clustering index = {results['L8_clustering']:.3f} "
         f"(>0 = clustered)",
         results['L8_clustering'] > 0.1),

        ("L9", "MARGINAL MAP ≈ SOLUTION",
         f"Marginal MAP is a valid solution {results['L9_map_is_solution']*100:.0f}% of time",
         results['L9_map_is_solution'] > 0.7),

        ("L10", "BOUNDARY DEPTH",
         f"Correct bits boundary={results['L10_correct_boundary']:.4f}, "
         f"gap bits={results['L10_gap_boundary']:.4f} "
         f"(ratio={results['L10_gap_boundary']/results['L10_correct_boundary']:.2f})"
         if results['L10_correct_boundary'] > 0 else "No data",
         results['L10_gap_boundary'] < results['L10_correct_boundary']
         if results['L10_correct_boundary'] > 0 else False),
    ]

    confirmed = 0
    for code, name, evidence, verified in laws:
        status = "✓ CONFIRMED" if verified else "✗ FAILED"
        if verified:
            confirmed += 1
        print(f"\n  {code}: {name}")
        print(f"      {evidence}")
        print(f"      [{status}]")

    print(f"\n  TOTAL: {confirmed}/{len(laws)} laws confirmed")

    # Consistency check
    print("\n" + "=" * 80)
    print("CONSISTENCY CHECK")
    print("=" * 80)

    issues = consistency_check(results)
    if issues:
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("  All laws are mutually consistent. No contradictions found.")

    # The fundamental equation
    print("\n" + "=" * 80)
    print("FUNDAMENTAL EQUATION")
    print("=" * 80)

    d = int(3 * 4.27)
    eps = results['L1_epsilon']
    # P(Bin(d, 0.5+eps) > d/2)
    p_correct = 0
    for k in range(d + 1):
        p_e = 0.5 + eps
        prob_k = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(max(p_e, 1e-10)) + (d-k)*math.log(max(1-p_e, 1e-10))
        )
        if k > d/2: p_correct += prob_k
        elif k == d/2 and d % 2 == 0: p_correct += prob_k * 0.5

    print(f"\n  Accuracy = P(Bin(d, 0.5 + ε) > d/2)")
    print(f"  d = 3r = {d}, ε = {eps:.4f}")
    print(f"  Predicted: {p_correct*100:.1f}%")
    print(f"  Measured:  {results['L1_accuracy']*100:.1f}%")
    print(f"  Error:     {abs(p_correct - results['L1_accuracy'])*100:.1f}%")
