"""
CLAUSES AS HYPEREDGES: Oriented triangles in bit space.

Static properties don't discriminate. Frustration is constant.
What if the key is in the TOPOLOGY of how clauses CONNECT bits?

Each clause = oriented triangle: 3 bits with signs (+/−).
The PATTERN of signs within a clause = its orientation.
8 possible orientations: +++, ++−, +−+, +−−, −++, −+−, −−+, −−−.

Does the distribution of orientations around a bit predict its value?
Does the CYCLE STRUCTURE of clause orientations encode clone signs?
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


# ============================================================
# 1. CLAUSE ORIENTATION around each bit
# ============================================================

def clause_orientations():
    """
    For each bit i in a clause (i, j, k) with signs (si, sj, sk):
    The "view from i" = (sj, sk) = what the OTHER two signs are.

    If sj=sk (both same) → COHERENT clause for i
    If sj≠sk (different) → MIXED clause for i

    Does the ratio coherent/mixed predict correctness?
    """
    print("=" * 70)
    print("1. CLAUSE ORIENTATION: view from each bit")
    print("=" * 70)

    random.seed(42); n = 12

    correct_coherent = []; wrong_coherent = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            coherent = 0; mixed = 0
            for clause in clauses:
                signs = {v: s for v, s in clause}
                if var not in signs: continue
                others = [(v, s) for v, s in clause if v != var]
                if len(others) == 2:
                    if others[0][1] == others[1][1]:
                        coherent += 1
                    else:
                        mixed += 1

            total = coherent + mixed
            ratio = coherent / total if total > 0 else 0.5

            if is_correct:
                correct_coherent.append(ratio)
            else:
                wrong_coherent.append(ratio)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correct bits: avg coherent fraction = {mean(correct_coherent):.4f}")
    print(f"  Wrong bits:   avg coherent fraction = {mean(wrong_coherent):.4f}")
    print(f"  Ratio: {mean(wrong_coherent)/mean(correct_coherent):.3f}" if mean(correct_coherent) > 0 else "")


# ============================================================
# 2. SIGN PRODUCT per clause: does parity matter?
# ============================================================

def sign_parity():
    """
    Each clause has 3 signs. Product = +1 or −1.
    +1 = even number of negations (+++, +−−, −+−, −−+)
    −1 = odd number of negations (++−, +−+, −++, −−−)

    Does the parity distribution around a bit predict anything?
    """
    print("\n" + "=" * 70)
    print("2. SIGN PARITY: product of signs per clause")
    print("=" * 70)

    random.seed(42); n = 12

    correct_parity = []; wrong_parity = []

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            pos_parity = 0; neg_parity = 0
            for clause in clauses:
                if not any(v == var for v, s in clause): continue
                product = 1
                for v, s in clause:
                    product *= s
                if product > 0: pos_parity += 1
                else: neg_parity += 1

            total = pos_parity + neg_parity
            frac_pos = pos_parity / total if total > 0 else 0.5

            if is_correct:
                correct_parity.append(frac_pos)
            else:
                wrong_parity.append(frac_pos)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correct bits: avg positive parity fraction = {mean(correct_parity):.4f}")
    print(f"  Wrong bits:   avg positive parity fraction = {mean(wrong_parity):.4f}")


# ============================================================
# 3. CLAUSE PATHS: oriented paths between clone pairs
# ============================================================

def clause_paths():
    """
    For clone pair (i,j): trace ALL clause-paths from i to j.
    Each path = sequence of clauses connecting i to j.
    Each clause has signs → the path has an ACCUMULATED SIGN.

    If all paths give same accumulated sign → deterministic (clone or anti).
    If paths give mixed signs → ambiguous.

    Does path-sign consistency predict actual clone sign?
    """
    print("\n" + "=" * 70)
    print("3. CLAUSE PATHS: Sign consistency between clone pairs")
    print("=" * 70)

    random.seed(42); n = 12

    consistent_correct = 0; consistent_total = 0
    inconsistent_correct = 0; inconsistent_total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Build adjacency with sign info
        # For each pair (i,j) sharing a clause: what sign does the clause imply?
        pair_signs = {}  # (i,j) → list of implied signs
        for clause in clauses:
            lits = [(v, s) for v, s in clause]
            for a in range(len(lits)):
                for b in range(a+1, len(lits)):
                    vi, si = lits[a]
                    vj, sj = lits[b]
                    key = (min(vi,vj), max(vi,vj))
                    if key not in pair_signs:
                        pair_signs[key] = []
                    # If si=sj → clause wants them same → clone sign
                    # If si≠sj → clause wants them different → anti sign
                    pair_signs[key].append(si == sj)

        # Real clone pairs
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same < 0.85 and same > 0.15: continue
                is_clone = same > 0.85

                # Direct path signs
                key = (i, j)
                if key in pair_signs:
                    signs = pair_signs[key]
                    clone_votes = sum(1 for s in signs if s)
                    anti_votes = len(signs) - clone_votes

                    # Consistency: do all paths agree?
                    if clone_votes == 0 or anti_votes == 0:
                        # Perfectly consistent
                        pred = clone_votes > anti_votes
                        consistent_total += 1
                        if pred == is_clone: consistent_correct += 1
                    else:
                        # Mixed: use majority
                        pred = clone_votes > anti_votes
                        inconsistent_total += 1
                        if pred == is_clone: inconsistent_correct += 1

                # 2-hop paths: i→k→j
                for k in range(n):
                    if k == i or k == j: continue
                    ik = (min(i,k), max(i,k))
                    kj = (min(k,j), max(k,j))
                    if ik in pair_signs and kj in pair_signs:
                        # Path sign = ik_sign XOR kj_sign
                        # (clone × clone = clone, clone × anti = anti, etc.)
                        for s_ik in pair_signs[ik]:
                            for s_kj in pair_signs[kj]:
                                # s_ik=True means "same", s_kj=True means "same"
                                # path says: same×same=same, same×diff=diff
                                path_clone = s_ik == s_kj
                                key2 = (i, j)
                                if key2 not in pair_signs:
                                    pair_signs[key2] = []
                                # Don't add — just count for this analysis
                                break
                            break

    if consistent_total > 0:
        print(f"\n  Consistent paths (all agree):")
        print(f"    Accuracy: {consistent_correct/consistent_total*100:.1f}% (n={consistent_total})")
    if inconsistent_total > 0:
        print(f"  Inconsistent paths (mixed signs):")
        print(f"    Accuracy: {inconsistent_correct/inconsistent_total*100:.1f}% (n={inconsistent_total})")

    if consistent_total > 0 and inconsistent_total > 0:
        cons_acc = consistent_correct/consistent_total
        incons_acc = inconsistent_correct/inconsistent_total
        print(f"\n  Consistent paths: {cons_acc*100:.1f}% — vs — Inconsistent: {incons_acc*100:.1f}%")
        if cons_acc > incons_acc + 0.05:
            print(f"  → Consistent paths ARE more reliable! ★")


# ============================================================
# 4. THE SIGN CHAIN: does sign propagate through clause chains?
# ============================================================

def sign_chains():
    """
    Build a SIGNED GRAPH: bits = nodes, edges weighted by clause sign.
    Edge weight = #(same_sign_clauses) − #(diff_sign_clauses).
    Positive weight → clone evidence. Negative → anti evidence.

    Then: for pairs WITHOUT direct edge, can we infer sign
    from the SHORTEST SIGNED PATH?
    """
    print("\n" + "=" * 70)
    print("4. SIGNED GRAPH: Inferring clone signs from paths")
    print("=" * 70)

    random.seed(42); n = 12

    path_correct = 0; path_total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        # Build signed graph
        edge_weight = [[0]*n for _ in range(n)]  # positive=clone, negative=anti
        for clause in clauses:
            lits = [(v, s) for v, s in clause]
            for a in range(len(lits)):
                for b in range(a+1, len(lits)):
                    vi, si = lits[a]; vj, sj = lits[b]
                    if si == sj:
                        edge_weight[vi][vj] += 1; edge_weight[vj][vi] += 1
                    else:
                        edge_weight[vi][vj] -= 1; edge_weight[vj][vi] -= 1

        # For each real clone pair: does signed graph predict correctly?
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same < 0.85 and same > 0.15: continue
                is_clone = same > 0.85

                # Direct weight
                w = edge_weight[i][j]
                if w != 0:
                    path_total += 1
                    if (w > 0) == is_clone: path_correct += 1

    if path_total > 0:
        print(f"\n  Direct signed-edge prediction: {path_correct/path_total*100:.1f}% (n={path_total})")
        print(f"  (Positive weight → clone, negative → anti)")

    # Compare with tension agreement
    tension_correct = 0; tension_total = 0
    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        for i in range(n):
            for j in range(i+1, n):
                same = sum(1 for s in solutions if s[i] == s[j]) / len(solutions)
                if same < 0.85 and same > 0.15: continue
                is_clone = same > 0.85
                tension_total += 1
                if ((tensions[i] >= 0) == (tensions[j] >= 0)) == is_clone:
                    tension_correct += 1

    if tension_total > 0:
        print(f"  Tension agreement prediction:  {tension_correct/tension_total*100:.1f}% (n={tension_total})")
        print(f"  Improvement: {(path_correct/path_total - tension_correct/tension_total)*100:+.1f}%"
              if path_total > 0 else "")


if __name__ == "__main__":
    clause_orientations()
    sign_parity()
    clause_paths()
    sign_chains()
