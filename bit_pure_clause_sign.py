"""
PURE CLAUSE SIGN PREDICTION: Can we reach 85% WITHOUT any sampling?

Current clause-only methods:
  tension_agree: 60.7%
  v4_agree:      73.7%

The gap 73.7% → 85% = 11.3%. Can we close it?

New ideas:
1. V4 agreement WEIGHTED by confidence: high-|σ| pairs more reliable?
2. ITERATIVE sign propagation: if A~B (clone) and B~C (clone),
   can we infer A~C even if we can't see it directly?
3. CLAUSE IMPLICATION: two clauses sharing vars imply sign relationships
4. Second-order v4: run v4 on the SIGN predictions themselves
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


def v4_tensions(clauses, n, n_iter=10):
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
    for _ in range(n_iter):
        new_t = {}
        for var in tensions:
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                rem = []; vs = None
                for v, s in clause: rem.append((v,s));
                for v, s in rem:
                    if v == var: vs = s
                if vs is None: continue
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


def get_real_pairs(solutions, n, threshold=0.85):
    pairs = {}
    for i in range(n):
        for j in range(i+1, n):
            same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
            if same > threshold: pairs[(i,j)] = True
            elif same < (1-threshold): pairs[(i,j)] = False
    return pairs


# ============================================================
# 1. V4 + CONFIDENCE WEIGHTING
# ============================================================

def v4_confidence_sign():
    """
    V4 gives 73.7%. But not all pairs are equally confident.
    If both bits have HIGH |σ_v4|, the sign should be more reliable.

    Measure: accuracy of v4 sign prediction BY confidence bucket.
    """
    print("=" * 70)
    print("1. V4 sign accuracy BY confidence level")
    print("=" * 70)

    random.seed(42); n = 12

    buckets = {}  # (conf_bucket) → [correct, total]

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        v4 = v4_tensions(clauses, n, 10)
        real_pairs = get_real_pairs(solutions, n, 0.85)

        for (i,j), is_clone in real_pairs.items():
            v4_agree = (v4[i] >= 0) == (v4[j] >= 0)
            correct = v4_agree == is_clone

            # Confidence: min |σ| of the pair
            conf = min(abs(v4[i]), abs(v4[j]))
            bucket = round(conf * 5) / 5
            bucket = min(bucket, 0.8)

            if bucket not in buckets:
                buckets[bucket] = [0, 0]
            buckets[bucket][1] += 1
            if correct: buckets[bucket][0] += 1

    print(f"\n  {'min |σ_v4|':>10} | {'accuracy':>8} | {'n':>6}")
    print("  " + "-" * 30)
    for b in sorted(buckets.keys()):
        c, t = buckets[b]
        if t < 10: continue
        print(f"  {b:>10.1f} | {c/t*100:>7.1f}% | {t:>6}")


# ============================================================
# 2. CLAUSE IMPLICATION SIGNS
# ============================================================

def clause_implication_signs():
    """
    Two clauses sharing a variable create an IMPLICATION:
    Clause 1: (a ∨ b ∨ c) with signs (sa, sb, sc)
    Clause 2: (a ∨ d ∨ e) with signs (sa', sd, se)

    If sa ≠ sa' (a has different signs in two clauses):
    This constrains the SIGN relationship between {b,c} and {d,e}.

    Can we extract sign info from these clause implications?
    """
    print("\n" + "=" * 70)
    print("2. CLAUSE IMPLICATION: Sign constraints from clause pairs")
    print("=" * 70)

    random.seed(42); n = 12

    impl_correct = 0; impl_total = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        real_pairs = get_real_pairs(solutions, n, 0.85)

        # For each pair of clauses sharing exactly one variable:
        # The sign of the shared variable tells us something about
        # the relationship between the other variables.
        sign_evidence = {}  # (i,j) → accumulated evidence for clone(+)/anti(-)

        for ci in range(len(clauses)):
            for cj in range(ci+1, len(clauses)):
                vars_i = {v: s for v, s in clauses[ci]}
                vars_j = {v: s for v, s in clauses[cj]}

                shared = set(vars_i.keys()) & set(vars_j.keys())
                if len(shared) != 1: continue  # exactly one shared

                shared_var = list(shared)[0]
                si = vars_i[shared_var]
                sj = vars_j[shared_var]

                # Other vars in each clause
                others_i = [(v, s) for v, s in clauses[ci] if v != shared_var]
                others_j = [(v, s) for v, s in clauses[cj] if v != shared_var]

                # If shared var has SAME sign in both clauses:
                # Both clauses are satisfied when shared_var is "correct"
                # → the other vars are in similar "pressure" environments
                # → they tend to be clones

                # If DIFFERENT signs → opposite environments → tend to be anti

                for vi, si_v in others_i:
                    for vj, sj_v in others_j:
                        key = (min(vi,vj), max(vi,vj))
                        if key not in sign_evidence:
                            sign_evidence[key] = 0

                        # Evidence: same sign of shared → clone evidence for others
                        if si == sj:
                            # Same pressure → same sign evidence
                            if si_v == sj_v:
                                sign_evidence[key] += 1  # clone
                            else:
                                sign_evidence[key] -= 1  # anti
                        else:
                            if si_v == sj_v:
                                sign_evidence[key] -= 1
                            else:
                                sign_evidence[key] += 1

        # Test: does evidence predict real clone sign?
        for (i,j), is_clone in real_pairs.items():
            key = (min(i,j), max(i,j))
            if key in sign_evidence:
                impl_total += 1
                pred_clone = sign_evidence[key] > 0
                if pred_clone == is_clone:
                    impl_correct += 1

    if impl_total > 0:
        print(f"\n  Implication sign accuracy: {impl_correct/impl_total*100:.1f}% (n={impl_total})")
    else:
        print(f"\n  No implication evidence found")


# ============================================================
# 3. ITERATIVE SIGN PROPAGATION on clone graph
# ============================================================

def iterative_sign_prop():
    """
    Start with v4 sign predictions (73.7%).
    For each pair where we're UNCERTAIN:
    Look at TRANSITIVE paths: if A~B (confident clone) and B~C (confident clone),
    then A~C should be clone (with reduced confidence).

    Like BP but on the SIGN GRAPH instead of the clause graph.
    """
    print("\n" + "=" * 70)
    print("3. ITERATIVE SIGN PROPAGATION")
    print("=" * 70)

    random.seed(42); n = 12

    results_by_iter = {}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        v4 = v4_tensions(clauses, n, 10)
        real_pairs = get_real_pairs(solutions, n, 0.85)
        if not real_pairs: continue

        # Initial sign beliefs from v4
        # sign_belief[(i,j)] = P(clone) - P(anti), in [-1, 1]
        sign_belief = {}
        for i in range(n):
            for j in range(i+1, n):
                # v4 agreement as initial belief
                if (v4[i] >= 0) == (v4[j] >= 0):
                    conf = min(abs(v4[i]), abs(v4[j]))
                    sign_belief[(i,j)] = conf  # positive = clone belief
                else:
                    conf = min(abs(v4[i]), abs(v4[j]))
                    sign_belief[(i,j)] = -conf  # negative = anti belief

        # Iterative propagation
        for iteration in range(5):
            new_belief = dict(sign_belief)

            for i in range(n):
                for j in range(i+1, n):
                    # Transitive: for each intermediate k
                    transitive_evidence = 0
                    n_paths = 0
                    for k in range(n):
                        if k == i or k == j: continue
                        ik = (min(i,k), max(i,k))
                        kj = (min(k,j), max(k,j))

                        if ik in sign_belief and kj in sign_belief:
                            # If i~k clone and k~j clone → i~j clone
                            # If i~k clone and k~j anti → i~j anti
                            # sign_ij = sign_ik × sign_kj
                            path_sign = sign_belief[ik] * sign_belief[kj]
                            transitive_evidence += path_sign * 0.1  # damped
                            n_paths += 1

                    if n_paths > 0:
                        new_belief[(i,j)] = 0.7 * sign_belief.get((i,j), 0) + \
                                           0.3 * transitive_evidence / n_paths

            sign_belief = new_belief

            # Measure accuracy at this iteration
            correct = 0; total = 0
            for (i,j), is_clone in real_pairs.items():
                key = (min(i,j), max(i,j))
                if key in sign_belief:
                    total += 1
                    pred_clone = sign_belief[key] > 0
                    if pred_clone == is_clone:
                        correct += 1

            if total > 0:
                acc = correct / total * 100
                if iteration not in results_by_iter:
                    results_by_iter[iteration] = []
                results_by_iter[iteration].append(acc)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'iteration':>9} | {'avg accuracy':>12}")
    print("  " + "-" * 25)
    for it in sorted(results_by_iter.keys()):
        print(f"  {it:>9} | {mean(results_by_iter[it]):>11.1f}%")


# ============================================================
# 4. ALL CLAUSE-ONLY METHODS COMBINED
# ============================================================

def all_combined():
    print("\n" + "=" * 70)
    print("4. BEST CLAUSE-ONLY SIGN PREDICTION (everything combined)")
    print("=" * 70)

    random.seed(42); n = 12

    total = 0; correct = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        v4 = v4_tensions(clauses, n, 10)
        real_pairs = get_real_pairs(solutions, n, 0.85)

        # Build all evidence
        for (i,j), is_clone in real_pairs.items():
            total += 1

            # Evidence 1: v4 agreement (weight by confidence)
            v4_agree = (v4[i] >= 0) == (v4[j] >= 0)
            v4_conf = min(abs(v4[i]), abs(v4[j]))
            e1 = v4_conf if v4_agree else -v4_conf

            # Evidence 2: clause sign pattern
            same_s = 0; diff_s = 0
            for clause in clauses:
                signs = {}
                for v, s in clause:
                    if v == i or v == j: signs[v] = s
                if i in signs and j in signs:
                    if signs[i] == signs[j]: same_s += 1
                    else: diff_s += 1
            e2 = (same_s - diff_s) * 0.05  # weak, often anti-predictive

            # Evidence 3: self-cancellation agreement
            nbs_i = set(); nbs_j = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if i in vs:
                    for v in vs:
                        if v != i: nbs_i.add(v)
                if j in vs:
                    for v in vs:
                        if v != j: nbs_j.add(v)
            nb_avg_i = sum(v4[nb] for nb in nbs_i)/len(nbs_i) if nbs_i else 0
            nb_avg_j = sum(v4[nb] for nb in nbs_j)/len(nbs_j) if nbs_j else 0
            sc_i = v4[i] + nb_avg_i
            sc_j = v4[j] + nb_avg_j
            sc_agree = (sc_i > 0) == (sc_j > 0)
            e3 = 0.3 if sc_agree else -0.3

            # Combined
            combined = e1 + e3  # skip e2 (anti-predictive)
            pred_clone = combined > 0

            if pred_clone == is_clone:
                correct += 1

    if total > 0:
        print(f"\n  Best clause-only combined: {correct/total*100:.1f}%")
        print(f"  (v4 agreement + self-cancellation)")
        print(f"  vs v4 alone: 73.7%")
        print(f"  vs target: 85%")


if __name__ == "__main__":
    v4_confidence_sign()
    clause_implication_signs()
    iterative_sign_prop()
    all_combined()
