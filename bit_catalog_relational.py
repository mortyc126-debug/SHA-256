"""
Bit Properties Catalog — Block II: Relational Properties
Properties of a bit RELATIVE to other bits.
"""

import random
from bit_catalog_static import random_3sat, find_solutions


# ============================================================
# 7. COUPLING — сила связи между двумя битами
# ============================================================
def coupling_matrix(clauses, n):
    """
    coupling[i][j] = сколько клозов содержат И bit i, И bit j.
    Чем больше — тем сильнее связь.
    """
    matrix = [[0] * n for _ in range(n)]
    for clause in clauses:
        vars_in = [v for v, s in clause]
        for i in range(len(vars_in)):
            for j in range(i + 1, len(vars_in)):
                matrix[vars_in[i]][vars_in[j]] += 1
                matrix[vars_in[j]][vars_in[i]] += 1
    return matrix


# ============================================================
# 8. AGREEMENT — хотят ли два связанных бита "одного и того же"
# ============================================================
def agreement_matrix(clauses, n):
    """
    Для каждой пары (i, j) в одном клозе:
    agreement = +1 если оба positive или оба negative (хотят оба быть 1 или оба 0)
    agreement = -1 если один positive, другой negative (хотят разного)

    Среднее по клозам. Показывает, "союзники" ли два бита или "враги".
    """
    sums = [[0.0] * n for _ in range(n)]
    counts = [[0] * n for _ in range(n)]

    for clause in clauses:
        for idx_a in range(len(clause)):
            for idx_b in range(idx_a + 1, len(clause)):
                va, sa = clause[idx_a]
                vb, sb = clause[idx_b]
                # Если оба positive: оба "хотят быть 1" чтобы помочь клозу
                # Если оба negative: оба "хотят быть 0"
                # Если разные: один хочет 1, другой 0
                agree = sa * sb  # +1 если одинаковые знаки, -1 если разные
                sums[va][vb] += agree
                sums[vb][va] += agree
                counts[va][vb] += 1
                counts[vb][va] += 1

    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if counts[i][j] > 0:
                matrix[i][j] = sums[i][j] / counts[i][j]
    return matrix


# ============================================================
# 9. BRIDGENESS — является ли бит мостом между кластерами
# ============================================================
def bridgeness(clauses, n, var):
    """
    Убираем бит var из графа связей.
    Считаем: увеличилось ли число компонент связности?
    Если да — бит является мостом.

    Возвращает: число дополнительных компонент, возникших от удаления.
    """
    # Построить граф соседства без var
    adj = {i: set() for i in range(n) if i != var}

    for clause in clauses:
        vars_in = [v for v, s in clause if v != var]
        for i in range(len(vars_in)):
            for j in range(i + 1, len(vars_in)):
                adj[vars_in[i]].add(vars_in[j])
                adj[vars_in[j]].add(vars_in[i])

    # Считаем компоненты связности без var
    visited = set()
    components_without = 0
    for node in adj:
        if node not in visited:
            components_without += 1
            stack = [node]
            while stack:
                curr = stack.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                for nb in adj[curr]:
                    if nb not in visited:
                        stack.append(nb)

    # Компоненты С var
    adj_full = {i: set() for i in range(n)}
    for clause in clauses:
        vars_in = [v for v, s in clause]
        for i in range(len(vars_in)):
            for j in range(i + 1, len(vars_in)):
                adj_full[vars_in[i]].add(vars_in[j])
                adj_full[vars_in[j]].add(vars_in[i])

    visited2 = set()
    components_with = 0
    for node in adj_full:
        if node not in visited2:
            components_with += 1
            stack = [node]
            while stack:
                curr = stack.pop()
                if curr in visited2:
                    continue
                visited2.add(curr)
                for nb in adj_full[curr]:
                    if nb not in visited2:
                        stack.append(nb)

    return components_without - components_with


# ============================================================
# 10. CLIQUENESS — плотность связей между соседями бита
# ============================================================
def cliqueness(clauses, n, var):
    """
    Кластерный коэффициент: какая доля соседей var
    связаны друг с другом?
    1.0 = все соседи связаны (клика)
    0.0 = никакие соседи не связаны
    """
    # Найти соседей
    neighbors = set()
    for clause in clauses:
        vars_in = [v for v, s in clause]
        if var in vars_in:
            for v in vars_in:
                if v != var:
                    neighbors.add(v)

    if len(neighbors) < 2:
        return 0.0

    # Найти связи между соседями
    neighbor_links = 0
    for clause in clauses:
        vars_in = [v for v, s in clause]
        # Считаем пары соседей, которые встречаются в одном клозе
        neighbors_in_clause = [v for v in vars_in if v in neighbors and v != var]
        for i in range(len(neighbors_in_clause)):
            for j in range(i + 1, len(neighbors_in_clause)):
                neighbor_links += 1

    # Максимально возможное число связей между соседями
    k = len(neighbors)
    max_links = k * (k - 1) / 2

    return neighbor_links / max_links if max_links > 0 else 0.0


# ============================================================
# 11. CORRELATION WITH SOLUTIONS — корреляция пар битов в решениях
# ============================================================
def solution_correlation_matrix(solutions, n):
    """
    Для каждой пары (i,j): корреляция их значений по всем решениям.
    +1 = всегда одинаковы
    -1 = всегда противоположны
     0 = независимы
    """
    if len(solutions) < 2:
        return [[0.0] * n for _ in range(n)]

    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        vals_i = [sol[i] for sol in solutions]
        mean_i = sum(vals_i) / len(vals_i)
        for j in range(i, n):
            vals_j = [sol[j] for sol in solutions]
            mean_j = sum(vals_j) / len(vals_j)

            cov = sum((vals_i[k] - mean_i) * (vals_j[k] - mean_j)
                       for k in range(len(solutions))) / len(solutions)

            std_i = (sum((v - mean_i)**2 for v in vals_i) / len(vals_i)) ** 0.5
            std_j = (sum((v - mean_j)**2 for v in vals_j) / len(vals_j)) ** 0.5

            if std_i > 0 and std_j > 0:
                corr = cov / (std_i * std_j)
            else:
                corr = 0.0

            matrix[i][j] = corr
            matrix[j][i] = corr

    return matrix


# ============================================================
# MEASUREMENT
# ============================================================

def measure_all_relational(clauses, n, solutions=None):
    coupling = coupling_matrix(clauses, n)
    agreement = agreement_matrix(clauses, n)
    sol_corr = solution_correlation_matrix(solutions, n) if solutions else None

    print(f"\n--- Bit Relational Properties ---")

    # Per-bit summary
    print(f"\n{'var':>5} | {'neighbors':>9} | {'avg_coup':>8} | {'bridge':>6} | "
          f"{'clique':>6} | {'max_agree':>9} | {'max_disagr':>10}")
    print("-" * 75)

    for var in range(n):
        neighbors = sum(1 for j in range(n) if coupling[var][j] > 0)
        avg_coup = sum(coupling[var]) / max(1, neighbors)
        bridge = bridgeness(clauses, n, var)
        clique = cliqueness(clauses, n, var)

        agrees = [agreement[var][j] for j in range(n) if j != var and coupling[var][j] > 0]
        max_agree = max(agrees) if agrees else 0
        max_disagree = min(agrees) if agrees else 0

        print(f"  x{var:>2} | {neighbors:>9} | {avg_coup:>8.2f} | "
              f"{bridge:>6} | {clique:>6.3f} | {max_agree:>+9.3f} | "
              f"{max_disagree:>+10.3f}")

    # Agreement vs actual correlation
    if sol_corr:
        print(f"\n--- Does structural agreement predict solution correlation? ---")
        print(f"{'pair':>8} | {'coupling':>8} | {'agreement':>9} | {'sol_corr':>8} | {'match':>5}")
        print("-" * 50)

        matches = 0
        total = 0
        for i in range(n):
            for j in range(i+1, n):
                if coupling[i][j] > 0:
                    agree_sign = 1 if agreement[i][j] > 0 else -1
                    corr_sign = 1 if sol_corr[i][j] > 0 else -1
                    match = agree_sign == corr_sign
                    if match:
                        matches += 1
                    total += 1
                    if coupling[i][j] >= 2:  # Show strongly coupled pairs
                        print(f"  x{i}-x{j} | {coupling[i][j]:>8} | "
                              f"{agreement[i][j]:>+9.3f} | "
                              f"{sol_corr[i][j]:>+8.3f} | "
                              f"{'yes' if match else 'NO':>5}")

        print(f"\nAgreement predicts correlation direction: {matches}/{total}")


if __name__ == "__main__":
    print("=" * 75)
    print("BLOCK II: Relational Bit Properties")
    print("=" * 75)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        print(f"\n## {label} instance (n=12, ratio={ratio}, "
              f"{len(solutions)} solutions)")
        measure_all_relational(clauses, 12, solutions)
