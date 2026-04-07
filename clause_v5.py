"""
V5 TENSION: V4 + inverted clause topology.

V4: weight clause votes by how much clause NEEDS this bit.
New: ALSO account for inverted sign topology between neighbors.

If bit i and neighbor j appear with SAME signs in clause →
they're likely anti-clones → OPPOSITE directions.
If DIFFERENT signs → clone → SAME direction.

V5: adjust tension using neighbor's tension × inverted sign.
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


def v4_tensions(clauses, n, fixed=None, n_iter=10):
    if fixed is None: fixed = {}
    tensions = {v: bit_tension(clauses, n, v, fixed) for v in range(n) if v not in fixed}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                sat = False; rem = []; vs = None
                for v, s in clause:
                    if v in fixed:
                        if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                            sat = True; break
                    else: rem.append((v,s));
                    if v == var: vs = s
                if sat or vs is None: continue
                oh = 0.0
                for v, s in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if s==1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs==1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v,0)
    return tensions


def v5_tensions(clauses, n, fixed=None, n_iter=10, topo_weight=0.15):
    """
    V5 = V4 + topological sign inversion correction.

    For each bit i: v4 gives σ_v4(i).
    Correction: for each neighbor j sharing a clause:
      If same signs in clause → they're likely ANTI-clones
        → if j points positive, i should point NEGATIVE (opposite)
      If diff signs → CLONE → i should follow j (same)

    inverted_signal = Σ_j (sign_relationship × σ_v4(j))
    where sign_relationship = −1 if same signs, +1 if different

    v5(i) = (1-w) × v4(i) + w × inverted_signal(i)
    """
    if fixed is None: fixed = {}

    # Start from v4
    tensions = v4_tensions(clauses, n, fixed, n_iter)

    # Build inverted topology signal
    # For each pair in each clause: sign relationship
    pair_sign = {}  # (i,j) → accumulated inverted sign weight
    for clause in clauses:
        lits = [(v,s) for v,s in clause if v not in fixed]
        for a in range(len(lits)):
            for b in range(a+1, len(lits)):
                vi, si = lits[a]; vj, sj = lits[b]
                # Same signs → anti-clone → inverted relationship (−1)
                # Diff signs → clone → same relationship (+1)
                rel = -1 if si == sj else +1

                key = (vi, vj)
                pair_sign[key] = pair_sign.get(key, 0) + rel
                key2 = (vj, vi)
                pair_sign[key2] = pair_sign.get(key2, 0) + rel

    # Correction for each bit
    corrected = {}
    for var in tensions:
        topo_signal = 0
        n_pairs = 0
        for other in tensions:
            if other == var: continue
            key = (var, other)
            if key in pair_sign:
                # If relationship positive (clone) → neighbor supports same direction
                # If negative (anti) → neighbor supports opposite
                rel = pair_sign[key]
                topo_signal += rel * tensions[other]
                n_pairs += abs(rel)

        if n_pairs > 0:
            topo_signal /= n_pairs

        corrected[var] = (1 - topo_weight) * tensions[var] + topo_weight * topo_signal

    return corrected


# ============================================================
# TEST: V5 vs V4 vs tension
# ============================================================

def test_v5():
    random.seed(42); n = 12

    print("=" * 70)
    print("V5 TENSION: V4 + inverted topology")
    print("=" * 70)

    # Test different topology weights
    for tw in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]:
        correct = 0; total = 0

        for seed in range(200):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue

            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            v5 = v5_tensions(clauses, n, topo_weight=tw)

            for var in range(n):
                total += 1
                if (1 if v5.get(var, 0) >= 0 else 0) == correct_val[var]:
                    correct += 1

        print(f"  topo_weight={tw:.2f}: {correct/total*100:.1f}%")

    # Best V5 as solver
    print(f"\n--- SOLVER COMPARISON ---")

    results = {'tension': 0, 'v4': 0, 'v5_best': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['tension'] += 1

        # V4
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            v4 = v4_tensions(clauses, n, fixed, 10)
            best = max(unfixed, key=lambda v: abs(v4.get(v, 0)))
            fixed[best] = 1 if v4.get(best, 0) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['v4'] += 1

        # V5
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            v5 = v5_tensions(clauses, n, fixed, 10, topo_weight=0.10)
            best = max(unfixed, key=lambda v: abs(v5.get(v, 0)))
            fixed[best] = 1 if v5.get(best, 0) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['v5_best'] += 1

    t = results['total']
    for name in ['tension', 'v4', 'v5_best']:
        pct = results[name]/t*100
        print(f"  {name:>10}: {results[name]}/{t} ({pct:.1f}%)")

    # Sign prediction with V5
    print(f"\n--- SIGN PREDICTION ---")

    for tw in [0.0, 0.10, 0.20]:
        correct = 0; total = 0
        for seed in range(200):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions or len(solutions) < 2: continue

            v5 = v5_tensions(clauses, n, topo_weight=tw)

            for i in range(n):
                for j in range(i+1, n):
                    same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                    if same < 0.85 and same > 0.15: continue
                    is_clone = same > 0.85
                    total += 1

                    v5_agree = (v5.get(i,0) >= 0) == (v5.get(j,0) >= 0)
                    if v5_agree == is_clone: correct += 1

        print(f"  topo_weight={tw:.2f}: sign accuracy {correct/total*100:.1f}%")


if __name__ == "__main__":
    test_v5()
