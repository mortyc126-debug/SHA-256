"""
Bit Properties Catalog — Block IV & V: Information-theoretic & Topological
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


# ============================================================
# BLOCK IV: INFORMATION-THEORETIC PROPERTIES
# ============================================================

# 15. ENTROPY — разброс значений бита по всем решениям
def bit_entropy(solutions, var):
    """H(var) = -p*log(p) - (1-p)*log(1-p) where p = P(var=1 in solutions)."""
    if not solutions:
        return 0.0
    p = sum(sol[var] for sol in solutions) / len(solutions)
    if p == 0 or p == 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


# 16. CONDITIONAL ENTROPY — неопределённость бита ЕСЛИ знаем соседа
def conditional_entropy(solutions, var, given_var):
    """H(var | given_var) — сколько неопределённости в var остаётся, зная given_var."""
    if not solutions or len(solutions) < 2:
        return 0.0

    # Split solutions by given_var's value
    sols_given_0 = [s for s in solutions if s[given_var] == 0]
    sols_given_1 = [s for s in solutions if s[given_var] == 1]

    h = 0.0
    for subset, count in [(sols_given_0, len(sols_given_0)), (sols_given_1, len(sols_given_1))]:
        if count == 0:
            continue
        p = sum(s[var] for s in subset) / count
        if p == 0 or p == 1:
            h_cond = 0.0
        else:
            h_cond = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
        h += (count / len(solutions)) * h_cond

    return h


# 17. INFORMATIVENESS — сколько информации о ДРУГИХ битах даёт фиксация этого
def informativeness(solutions, n, var):
    """
    I(var; rest) = H(rest) - H(rest | var)
    Упрощённо: среднее снижение энтропии по другим битам.
    """
    if not solutions or len(solutions) < 2:
        return 0.0

    total_reduction = 0.0
    count = 0
    for other in range(n):
        if other == var:
            continue
        h_other = bit_entropy(solutions, other)
        h_cond = conditional_entropy(solutions, other, var)
        total_reduction += h_other - h_cond
        count += 1

    return total_reduction / count if count > 0 else 0.0


# 18. PREDICTABILITY — можно ли угадать бит зная его "лучшего" соседа
def predictability(solutions, n, var):
    """
    Для каждого соседа j: если знаем j, какова точность предсказания var?
    Возвращает лучшую точность и лучшего предиктора.
    """
    if not solutions or len(solutions) < 2:
        return 0.0, -1

    best_acc = 0.5
    best_predictor = -1

    for j in range(n):
        if j == var:
            continue

        # Simple predictor: var = j (same) or var = 1-j (opposite)
        correct_same = sum(1 for s in solutions if s[var] == s[j])
        correct_opp = sum(1 for s in solutions if s[var] != s[j])

        acc = max(correct_same, correct_opp) / len(solutions)
        if acc > best_acc:
            best_acc = acc
            best_predictor = j

    return best_acc, best_predictor


# ============================================================
# BLOCK V: TOPOLOGICAL PROPERTIES
# ============================================================

def build_adjacency(clauses, n):
    """Build adjacency list from clause structure."""
    adj = {i: set() for i in range(n)}
    for clause in clauses:
        vars_in = [v for v, s in clause]
        for i in range(len(vars_in)):
            for j in range(i + 1, len(vars_in)):
                adj[vars_in[i]].add(vars_in[j])
                adj[vars_in[j]].add(vars_in[i])
    return adj


# 19. CENTRALITY — степенная центральность
def degree_centrality(adj, n, var):
    return len(adj[var]) / (n - 1)


# 20. BETWEENNESS — сколько кратчайших путей проходит через бит
def betweenness_centrality(adj, n, var):
    """Simplified betweenness: fraction of shortest paths through var."""
    total_paths = 0
    paths_through = 0

    for s in range(n):
        if s == var:
            continue
        # BFS from s
        dist = {s: 0}
        parents = {s: []}
        queue = [s]
        idx = 0
        while idx < len(queue):
            curr = queue[idx]
            idx += 1
            for nb in adj[curr]:
                if nb not in dist:
                    dist[nb] = dist[curr] + 1
                    parents[nb] = [curr]
                    queue.append(nb)
                elif dist[nb] == dist[curr] + 1:
                    parents[nb].append(curr)

        for t in range(s + 1, n):
            if t == var or t not in dist:
                continue
            # Count paths from s to t, and how many go through var
            # Simple: does the shortest path go through var?
            if var in dist and dist.get(var, float('inf')) < dist.get(t, float('inf')):
                # var is on SOME shortest path if dist[s][var] + dist[var][t] == dist[s][t]
                # We need dist from var to t
                dist_from_var = {}
                dist_from_var[var] = 0
                q2 = [var]
                i2 = 0
                while i2 < len(q2):
                    c = q2[i2]
                    i2 += 1
                    for nb in adj[c]:
                        if nb not in dist_from_var:
                            dist_from_var[nb] = dist_from_var[c] + 1
                            q2.append(nb)

                if t in dist_from_var and dist[var] + dist_from_var[t] == dist.get(t, float('inf')):
                    paths_through += 1

            total_paths += 1

    return paths_through / total_paths if total_paths > 0 else 0.0


# 21. CLUSTERING COEFFICIENT
def clustering_coeff(adj, var):
    neighbors = list(adj[var])
    if len(neighbors) < 2:
        return 0.0
    links = 0
    possible = len(neighbors) * (len(neighbors) - 1) / 2
    for i in range(len(neighbors)):
        for j in range(i + 1, len(neighbors)):
            if neighbors[j] in adj[neighbors[i]]:
                links += 1
    return links / possible


# 22. ECCENTRICITY — максимальное расстояние до другого бита
def eccentricity(adj, n, var):
    dist = {var: 0}
    queue = [var]
    idx = 0
    while idx < len(queue):
        curr = queue[idx]
        idx += 1
        for nb in adj[curr]:
            if nb not in dist:
                dist[nb] = dist[curr] + 1
                queue.append(nb)
    if len(dist) < n:
        return float('inf')  # disconnected
    return max(dist.values())


# ============================================================
# BLOCK VI: TEMPORAL PROPERTIES (during crystallization)
# ============================================================

def conditional_pressure(clauses, n, var, fixed):
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
    return p1, p0


# 23. CRYSTALLIZATION TIME — когда бит фиксируется в процессе кристаллизации
# 24. CATALYTIC POWER — ускоряет ли его фиксация кристаллизацию
def crystallization_order(clauses, n):
    """
    Run crystallization and record:
    - order in which bits crystallize
    - confidence at moment of crystallization
    - how many other bits become "sure" after each fixation
    """
    fixed = {}
    order = []

    for step in range(n):
        candidates = []
        for var in range(n):
            if var in fixed:
                continue
            p1, p0 = conditional_pressure(clauses, n, var, fixed)
            total = p1 + p0
            if total == 0:
                confidence = 0.0
                direction = random.choice([0, 1])
            else:
                confidence = abs(p1 - p0) / total
                direction = 1 if p1 >= p0 else 0

            candidates.append((var, confidence, direction, p1, p0))

        candidates.sort(key=lambda c: -c[1])
        best = candidates[0]

        # After fixing: how many others become forced?
        test_fixed = dict(fixed)
        test_fixed[best[0]] = best[2]
        catalyzed = 0
        for var, conf, d, p1, p0 in candidates[1:]:
            new_p1, new_p0 = conditional_pressure(clauses, n, var, test_fixed)
            new_total = new_p1 + new_p0
            if new_total > 0:
                new_conf = abs(new_p1 - new_p0) / new_total
                if new_conf > conf + 0.3:  # significantly more confident
                    catalyzed += 1

        fixed[best[0]] = best[2]
        order.append({
            'var': best[0],
            'step': step,
            'confidence': best[1],
            'direction': best[2],
            'catalyzed': catalyzed,
        })

    return order


# 25. ORDER DEPENDENCE — меняется ли результат от порядка фиксации
def order_dependence(clauses, n, var, solutions):
    """
    Фиксируем var ПЕРВЫМ vs ПОСЛЕДНИМ. Находим ли решение в обоих случаях?
    """
    if not solutions:
        return None

    def solve_with_first(first_var, first_val):
        fixed = {first_var: first_val}
        for step in range(n - 1):
            best_var = None
            best_conf = -1
            best_dir = 0
            for v in range(n):
                if v in fixed:
                    continue
                p1, p0 = conditional_pressure(clauses, n, v, fixed)
                total = p1 + p0
                if total == 0:
                    conf = 0
                    d = 0
                else:
                    conf = abs(p1 - p0) / total
                    d = 1 if p1 >= p0 else 0
                if conf > best_conf:
                    best_conf = conf
                    best_dir = d
                    best_var = v
            if best_var is not None:
                fixed[best_var] = best_dir
        assignment = [fixed.get(i, 0) for i in range(n)]
        sat = 0
        for clause in clauses:
            for v, s in clause:
                if (s == 1 and assignment[v] == 1) or (s == -1 and assignment[v] == 0):
                    sat += 1
                    break
        return sat == len(clauses)

    # Try forcing var=0 first, then var=1 first
    r0 = solve_with_first(var, 0)
    r1 = solve_with_first(var, 1)

    return {'first_as_0': r0, 'first_as_1': r1}


# ============================================================
# MEASUREMENT
# ============================================================

def measure_all(clauses, n, solutions):
    adj = build_adjacency(clauses, n)

    print(f"\n--- Information-theoretic Properties ---")
    print(f"{'var':>5} | {'entropy':>7} | {'min_cH':>7} | {'informat':>8} | "
          f"{'predict':>7} | {'pred_by':>7}")
    print("-" * 55)

    for var in range(n):
        h = bit_entropy(solutions, var)

        # Min conditional entropy across neighbors
        min_ch = h
        for j in range(n):
            if j != var:
                ch = conditional_entropy(solutions, var, j)
                if ch < min_ch:
                    min_ch = ch

        info = informativeness(solutions, n, var)
        pred_acc, pred_by = predictability(solutions, n, var)

        print(f"  x{var:>2} | {h:>7.3f} | {min_ch:>7.3f} | {info:>8.4f} | "
              f"{pred_acc:>7.3f} | {'x'+str(pred_by) if pred_by >= 0 else 'none':>7}")

    print(f"\n--- Topological Properties ---")
    print(f"{'var':>5} | {'deg_cent':>8} | {'between':>7} | {'cluster':>7} | {'eccent':>6}")
    print("-" * 50)

    for var in range(n):
        dc = degree_centrality(adj, n, var)
        bc = betweenness_centrality(adj, n, var)
        cc = clustering_coeff(adj, var)
        ec = eccentricity(adj, n, var)

        print(f"  x{var:>2} | {dc:>8.3f} | {bc:>7.3f} | {cc:>7.3f} | {ec:>6}")

    print(f"\n--- Temporal Properties (crystallization order) ---")
    order = crystallization_order(clauses, n)
    print(f"{'step':>5} | {'var':>4} | {'conf':>6} | {'val':>4} | {'catalyzed':>9}")
    print("-" * 40)
    for o in order:
        print(f"  {o['step']+1:>3} | x{o['var']:>2} | {o['confidence']:>6.3f} | "
              f"{o['direction']:>4} | {o['catalyzed']:>9}")

    # Order dependence for first few bits
    print(f"\n--- Order Dependence (does fixing order matter?) ---")
    for var in range(min(n, 6)):
        od = order_dependence(clauses, n, var, solutions)
        if od:
            print(f"  x{var}: first_as_0={'OK' if od['first_as_0'] else 'FAIL'}, "
                  f"first_as_1={'OK' if od['first_as_1'] else 'FAIL'}")


if __name__ == "__main__":
    print("=" * 60)
    print("BLOCKS IV-VI: Info, Topology, Temporal")
    print("=" * 60)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        print(f"\n## {label} (n=12, ratio={ratio}, {len(solutions)} solutions)")
        measure_all(clauses, 12, solutions)
