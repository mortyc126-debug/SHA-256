"""
THE HIDDEN NETWORK: Through what medium do bits "know" the solution?

Facts:
- Bits know correct value (95.3%)
- Attraction field is real (91.5%, 0% wrong minimum)
- Information NOT in tension (70%) or any clause signal (~79%)
- Information IS in full conditional distribution (95%)

The information EXISTS but is NOT in any measurable clause property.
WHERE is it?

Hypothesis: it's in the STRUCTURE OF CONSTRAINTS AS A WHOLE —
not in individual clauses or bits, but in the TOPOLOGY of the
constraint network. Like how gravity is not in any single mass
but in the GEOMETRY of spacetime.

Tests:
1. HOLOGRAPHIC: is the information on the BOUNDARY of the constraint graph?
2. ENTANGLEMENT ENTROPY: does cutting the graph in half lose info?
3. NON-LOCAL CORRELATIONS: do DISTANT bits share solution info?
4. CONSTRAINT GEOMETRY: is the solution encoded in graph SHAPE?
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
# 1. NON-LOCAL: Do distant bits share solution information?
# ============================================================

def nonlocal_info():
    """
    We proved: ξ=1 (correlation length). Transmission = 0 at distance 2.
    But this was for TENSION transmission.

    What about SOLUTION-SPACE correlation at distance?
    Do bits at distance 3+ share correct-value info?
    If yes → information travels through a HIDDEN channel.
    """
    print("=" * 70)
    print("1. NON-LOCAL: Solution correlation at distance")
    print("=" * 70)

    random.seed(42); n = 12

    corr_by_dist = {1: [], 2: [], 3: []}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 3: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        # Build adjacency + BFS distances
        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        for start in range(n):
            dist = {start: 0}
            queue = [start]; idx = 0
            while idx < len(queue):
                curr = queue[idx]; idx += 1
                for nb in adj[curr]:
                    if nb not in dist:
                        dist[nb] = dist[curr] + 1
                        queue.append(nb)

            for end in range(start+1, n):
                d = dist.get(end, 99)
                if d > 3: continue

                # Solution correlation: do they tend to have same/opposite values?
                vals_s = [s[start] for s in solutions]
                vals_e = [s[end] for s in solutions]
                ms = sum(vals_s)/len(vals_s)
                me = sum(vals_e)/len(vals_e)
                ss = math.sqrt(sum((v-ms)**2 for v in vals_s)/len(vals_s))
                se = math.sqrt(sum((v-me)**2 for v in vals_e)/len(vals_e))

                if ss > 0.01 and se > 0.01:
                    cov = sum((vals_s[k]-ms)*(vals_e[k]-me) for k in range(len(solutions)))/len(solutions)
                    corr = abs(cov/(ss*se))
                    corr_by_dist[d].append(corr)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {'distance':>8} | {'|solution corr|':>15} | {'n':>6}")
    print("  " + "-" * 35)
    for d in [1, 2, 3]:
        print(f"  {d:>8} | {mean(corr_by_dist[d]):>15.4f} | {len(corr_by_dist[d]):>6}")

    # Compare with TENSION transmission at same distances
    print(f"\n  Compare with TENSION transmission:")
    print(f"    d=1: tension trans = 0.082, solution corr = {mean(corr_by_dist[1]):.4f}")
    print(f"    d=2: tension trans = 0.000, solution corr = {mean(corr_by_dist[2]):.4f}")
    print(f"    d=3: tension trans = N/A,   solution corr = {mean(corr_by_dist[3]):.4f}")

    if mean(corr_by_dist[2]) > 0.01:
        print(f"\n  ★ Solution correlation at d=2 is NONZERO!")
        print(f"  ★ But tension transmission at d=2 is ZERO.")
        print(f"  ★ Information travels through a HIDDEN CHANNEL.")


# ============================================================
# 2. WHERE is the hidden information?
# ============================================================

def hidden_channel():
    """
    Solution correlation at d=2 is nonzero but tension is zero.
    The info travels THROUGH intermediate bits without them "seeing" it.

    Like quantum entanglement: correlated without local interaction.

    Test: if we REMOVE intermediate bit (cut the path),
    does the correlation vanish? If yes → it travels through path.
    If no → it's truly non-local (holographic).
    """
    print("\n" + "=" * 70)
    print("2. HIDDEN CHANNEL: Does correlation travel through paths?")
    print("=" * 70)

    random.seed(42); n = 12

    via_path = 0; not_via_path = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 3: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        # Find distance-2 pairs with nonzero solution correlation
        for i in range(n):
            for j in range(i+1, n):
                if j in adj[i]: continue  # skip distance-1

                # Find intermediaries
                intermediaries = adj[i] & adj[j]
                if not intermediaries: continue

                # Solution correlation i-j
                vals_i = [s[i] for s in solutions]
                vals_j = [s[j] for s in solutions]
                mi = sum(vals_i)/len(vals_i); mj = sum(vals_j)/len(vals_j)
                si = math.sqrt(sum((v-mi)**2 for v in vals_i)/len(vals_i))
                sj = math.sqrt(sum((v-mj)**2 for v in vals_j)/len(vals_j))
                if si < 0.01 or sj < 0.01: continue

                cov_ij = sum((vals_i[k]-mi)*(vals_j[k]-mj) for k in range(len(solutions)))/len(solutions)
                corr_ij = abs(cov_ij/(si*sj))
                if corr_ij < 0.1: continue  # no significant correlation

                total += 1

                # Remove intermediaries: condition on their values
                # If correlation SURVIVES removal → non-local
                # If it VANISHES → travels through path
                for mid in list(intermediaries)[:1]:
                    # Split solutions by mid's value
                    sols_0 = [s for s in solutions if s[mid] == 0]
                    sols_1 = [s for s in solutions if s[mid] == 1]

                    # Check: is i-j correlated WITHIN each group?
                    surviving_corr = 0
                    for sols in [sols_0, sols_1]:
                        if len(sols) < 2: continue
                        vi = [s[i] for s in sols]; vj = [s[j] for s in sols]
                        mi2 = sum(vi)/len(vi); mj2 = sum(vj)/len(vj)
                        si2 = math.sqrt(sum((v-mi2)**2 for v in vi)/len(vi))
                        sj2 = math.sqrt(sum((v-mj2)**2 for v in vj)/len(vj))
                        if si2 > 0.01 and sj2 > 0.01:
                            cov2 = sum((vi[k]-mi2)*(vj[k]-mj2) for k in range(len(sols)))/len(sols)
                            surviving_corr = max(surviving_corr, abs(cov2/(si2*sj2)))

                    if surviving_corr > corr_ij * 0.5:
                        not_via_path += 1  # correlation SURVIVES → non-local
                    else:
                        via_path += 1  # correlation VANISHES → travels through path

    if total > 0:
        print(f"\n  Distance-2 correlated pairs: {total}")
        print(f"  Correlation travels THROUGH path: {via_path} ({via_path/total*100:.1f}%)")
        print(f"  Correlation is NON-LOCAL:          {not_via_path} ({not_via_path/total*100:.1f}%)")


# ============================================================
# 3. THE BLOCK UNIVERSE TEST
# ============================================================

def block_universe():
    """
    If past-present-future exist simultaneously:
    The solution EXISTS at the moment of clause creation.
    The constraint structure CONTAINS the solution implicitly.

    Test: SCRAMBLE the clause structure (keep the same variables
    and solution, but randomize HOW clauses connect them).
    If scrambled instance is equally solvable → solution is in
    the TOPOLOGY. If harder → solution is in specific wiring.
    """
    print("\n" + "=" * 70)
    print("3. BLOCK UNIVERSE: Is solution in topology or wiring?")
    print("=" * 70)

    random.seed(42); n = 12

    original_acc = 0; scrambled_acc = 0; total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        sol = solutions[0]
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Original tension accuracy
        for var in range(n):
            total += 1
            sigma = bit_tension(clauses, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                original_acc += 1

        # Scramble: keep same variable sets but randomize SIGNS
        scrambled = []
        for clause in clauses:
            new_clause = [(v, random.choice([1, -1])) for v, s in clause]
            # Ensure clause is satisfied by sol (at least one literal true)
            satisfied = False
            for v, s in new_clause:
                if (s==1 and sol[v]==1) or (s==-1 and sol[v]==0):
                    satisfied = True; break
            if not satisfied:
                # Force one literal to match
                v, s = new_clause[0]
                new_s = 1 if sol[v] == 1 else -1
                new_clause[0] = (v, new_s)
            scrambled.append(new_clause)

        # Scrambled tension accuracy (for same solution)
        for var in range(n):
            sigma = bit_tension(scrambled, n, var)
            if (1 if sigma >= 0 else 0) == correct_val[var]:
                scrambled_acc += 1

    print(f"\n  Original tension accuracy:  {original_acc/total*100:.1f}%")
    print(f"  Scrambled tension accuracy: {scrambled_acc/total*100:.1f}%")
    print(f"\n  If same → info is in TOPOLOGY (which vars in which clauses)")
    print(f"  If different → info is in WIRING (specific signs)")


if __name__ == "__main__":
    nonlocal_info()
    hidden_channel()
    block_universe()
