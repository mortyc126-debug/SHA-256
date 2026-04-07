"""
Bit Properties Catalog — Block III: Dynamic Properties
How bits RESPOND to changes in other bits.
These properties only exist in MOTION — when we fix bits and watch reactions.
"""

import random
from bit_catalog_static import random_3sat, find_solutions


def conditional_pressure(clauses, n, var, fixed):
    """Pressure on var given fixed assignments."""
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


# ============================================================
# 11. SENSITIVITY — как сильно чужая фиксация меняет давление
# ============================================================
def sensitivity(clauses, n, var):
    """
    Для каждого соседа j: фиксируем j=0, измеряем давление на var.
    Потом j=1, измеряем давление. Разница = чувствительность к j.

    Возвращает: среднюю и максимальную чувствительность.
    """
    sensitivities = []

    base_p1, base_p0 = conditional_pressure(clauses, n, var, {})
    base_balance = base_p1 - base_p0

    for j in range(n):
        if j == var:
            continue
        p1_if0, p0_if0 = conditional_pressure(clauses, n, var, {j: 0})
        p1_if1, p0_if1 = conditional_pressure(clauses, n, var, {j: 1})

        balance_if0 = p1_if0 - p0_if0
        balance_if1 = p1_if1 - p0_if1

        sens = abs(balance_if1 - balance_if0)
        sensitivities.append((j, sens))

    sensitivities.sort(key=lambda x: -x[1])
    avg_sens = sum(s for _, s in sensitivities) / len(sensitivities) if sensitivities else 0
    max_sens = sensitivities[0][1] if sensitivities else 0
    max_sens_var = sensitivities[0][0] if sensitivities else -1

    return avg_sens, max_sens, max_sens_var


# ============================================================
# 12. ELASTICITY — сопротивление "неправильной" фиксации
# ============================================================
def elasticity(clauses, n, var):
    """
    Если зафиксировать var в КАЖДОЕ из двух значений:
    сколько клозов остаются невыполненными vs сколько остаются свободными?

    Высокая упругость = обе фиксации примерно одинаково плохи/хороши.
    Низкая упругость = одна фиксация сильно лучше другой.
    """
    results = {}
    for val in [0, 1]:
        dead = 0      # клозы которые точно мертвы
        alive = 0     # клозы которые точно живы
        uncertain = 0 # клозы которые ещё могут быть и так и так

        for clause in clauses:
            clause_has_var = False
            var_satisfies = False
            other_free = 0

            for v, s in clause:
                if v == var:
                    clause_has_var = True
                    if (s == 1 and val == 1) or (s == -1 and val == 0):
                        var_satisfies = True
                else:
                    other_free += 1

            if not clause_has_var:
                uncertain += 1  # clause unaffected
            elif var_satisfies:
                alive += 1
            elif other_free > 0:
                uncertain += 1
            else:
                dead += 1

        results[val] = {'dead': dead, 'alive': alive, 'uncertain': uncertain}

    # Elasticity = how symmetric the two choices are
    diff_dead = abs(results[0]['dead'] - results[1]['dead'])
    diff_alive = abs(results[0]['alive'] - results[1]['alive'])
    total = len(clauses)

    asymmetry = (diff_dead + diff_alive) / (2 * total) if total > 0 else 0
    return 1.0 - asymmetry, results


# ============================================================
# 13. CASCADE DEPTH — как далеко распространяется фиксация
# ============================================================
def cascade_depth(clauses, n, var, val):
    """
    Фиксируем var=val. Смотрим, какие другие биты становятся
    "вынужденными" (давление уходит полностью в одну сторону).
    Фиксируем их. Повторяем. Считаем глубину.

    Это "цепная реакция" кристаллизации.
    """
    fixed = {var: val}
    depth = 0

    while True:
        newly_forced = {}
        for v in range(n):
            if v in fixed:
                continue
            p1, p0 = conditional_pressure(clauses, n, v, fixed)

            # Бит "вынужден" если давление полностью в одну сторону
            if p1 > 0 and p0 == 0:
                newly_forced[v] = 1
            elif p0 > 0 and p1 == 0:
                newly_forced[v] = 0

        if not newly_forced:
            break

        fixed.update(newly_forced)
        depth += 1

    return depth, len(fixed) - 1  # depth and total forced bits


# ============================================================
# 14. BRITTLENESS — делает ли фиксация систему хуже
# ============================================================
def brittleness(clauses, n, var):
    """
    После фиксации var: увеличивается ли средняя фрустрация
    оставшихся битов?

    Хрупкость > 0: фиксация усложняет жизнь другим битам.
    Хрупкость < 0: фиксация упрощает (кристаллизация идёт).
    """
    # Базовая средняя фрустрация
    base_frustrations = []
    for v in range(n):
        if v == var:
            continue
        p1, p0 = conditional_pressure(clauses, n, v, {})
        total = p1 + p0
        if total > 0:
            base_frustrations.append(1.0 - abs(p1 - p0) / total)
        else:
            base_frustrations.append(0.0)

    base_avg = sum(base_frustrations) / len(base_frustrations) if base_frustrations else 0

    # Фрустрация после фиксации (пробуем оба значения, берём лучшее)
    best_delta = float('inf')
    for val in [0, 1]:
        frustrations = []
        for v in range(n):
            if v == var:
                continue
            p1, p0 = conditional_pressure(clauses, n, v, {var: val})
            total = p1 + p0
            if total > 0:
                frustrations.append(1.0 - abs(p1 - p0) / total)
            else:
                frustrations.append(0.0)

        after_avg = sum(frustrations) / len(frustrations) if frustrations else 0
        delta = after_avg - base_avg
        if delta < best_delta:
            best_delta = delta

    return best_delta  # negative = reduces frustration (good)


# ============================================================
# 15. FLIP IMPACT — что происходит если перевернуть бит в решении
# ============================================================
def flip_impact(clauses, n, var, solutions):
    """
    Берём каждое решение. Переворачиваем бит var.
    Сколько клозов ломается? Это мера "хрупкости" бита в решении.
    """
    if not solutions:
        return 0.0

    impacts = []
    for sol in solutions:
        # Оригинал
        orig_sat = 0
        for clause in clauses:
            for v, s in clause:
                if (s == 1 and sol[v] == 1) or (s == -1 and sol[v] == 0):
                    orig_sat += 1
                    break

        # Flip
        flipped = list(sol)
        flipped[var] = 1 - flipped[var]
        flip_sat = 0
        for clause in clauses:
            for v, s in clause:
                if (s == 1 and flipped[v] == 1) or (s == -1 and flipped[v] == 0):
                    flip_sat += 1
                    break

        impacts.append(orig_sat - flip_sat)

    return sum(impacts) / len(impacts)


# ============================================================
# MEASUREMENT
# ============================================================

def measure_all_dynamic(clauses, n, solutions=None):
    print(f"\n--- Dynamic Bit Properties ---")

    print(f"\n{'var':>5} | {'avg_sens':>8} | {'max_sens':>8} | {'from':>5} | "
          f"{'elast':>6} | {'cascade0':>8} | {'cascade1':>8} | "
          f"{'brittle':>8} | {'flip_imp':>8}")
    print("-" * 95)

    for var in range(n):
        avg_s, max_s, max_s_var = sensitivity(clauses, n, var)
        elast, _ = elasticity(clauses, n, var)
        depth0, forced0 = cascade_depth(clauses, n, var, 0)
        depth1, forced1 = cascade_depth(clauses, n, var, 1)
        brit = brittleness(clauses, n, var)
        flip = flip_impact(clauses, n, var, solutions) if solutions else 0

        print(f"  x{var:>2} | {avg_s:>8.3f} | {max_s:>8.3f} | "
              f"{'x'+str(max_s_var):>5} | {elast:>6.3f} | "
              f"{f'd{depth0}/f{forced0}':>8} | {f'd{depth1}/f{forced1}':>8} | "
              f"{brit:>+8.4f} | {flip:>8.2f}")


if __name__ == "__main__":
    print("=" * 95)
    print("BLOCK III: Dynamic Bit Properties")
    print("=" * 95)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if 2 < len(solutions) < 100:
                break

        print(f"\n## {label} instance (n=12, ratio={ratio}, "
              f"{len(solutions)} solutions)")
        measure_all_dynamic(clauses, 12, solutions)
