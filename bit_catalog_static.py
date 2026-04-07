"""
Bit Properties Catalog — Block I: Static Properties
Properties of a bit that can be measured WITHOUT fixing any other bit.
"""

import random


def random_3sat(n_vars, n_clauses, seed=None):
    if seed is not None:
        random.seed(seed)
    clauses = []
    for _ in range(n_clauses):
        vs = random.sample(range(n_vars), 3)
        signs = [random.choice([1, -1]) for _ in range(3)]
        clauses.append(list(zip(vs, signs)))
    return clauses


def find_solutions(clauses, n):
    solutions = []
    for i in range(2**n):
        assignment = [(i >> j) & 1 for j in range(n)]
        ok = True
        for clause in clauses:
            sat = False
            for var, sign in clause:
                val = assignment[var]
                if (sign == 1 and val == 1) or (sign == -1 and val == 0):
                    sat = True
                    break
            if not sat:
                ok = False
                break
        if ok:
            solutions.append(assignment)
    return solutions


# ============================================================
# 1. PRESSURE — куда бит склоняется
# ============================================================
def pressure(clauses, n, var):
    """
    Сколько клозов хотят var=1 vs var=0.
    Возвращает float в [-1, +1].
    +1 = все хотят 1, -1 = все хотят 0.
    """
    toward_1 = 0
    toward_0 = 0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                if s == 1:
                    toward_1 += 1
                else:
                    toward_0 += 1
    total = toward_1 + toward_0
    if total == 0:
        return 0.0
    return (toward_1 - toward_0) / total


# ============================================================
# 2. FRUSTRATION — насколько противоречивы требования
# ============================================================
def frustration(clauses, n, var):
    """
    0 = все клозы согласны (все хотят 1 или все хотят 0)
    1 = ровно половина хочет 1, половина хочет 0
    """
    votes = []
    for clause in clauses:
        for v, s in clause:
            if v == var:
                votes.append(s)
    if not votes:
        return 0.0
    mean = sum(votes) / len(votes)
    return 1.0 - abs(mean)


# ============================================================
# 3. DEGREE — в скольких ограничениях участвует
# ============================================================
def degree(clauses, n, var):
    """Абсолютное число клозов, содержащих var."""
    count = 0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                count += 1
                break
    return count


# ============================================================
# 4. POLARITY — баланс положительных/отрицательных вхождений
# ============================================================
def polarity(clauses, n, var):
    """
    +1 = всегда появляется как positive literal (x)
    -1 = всегда появляется как negative literal (¬x)
     0 = поровну
    Отличается от pressure тем, что не взвешивается.
    """
    pos = 0
    neg = 0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                if s == 1:
                    pos += 1
                else:
                    neg += 1
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


# ============================================================
# 5. CRITICALITY — как часто бит единственный спаситель клоза
# ============================================================
def criticality(clauses, n, var):
    """
    Для каждого клоза с этим битом: какая доля "ответственности"
    лежит на нём? Если клоз имеет 3 литерала — 1/3.
    Но если другие литералы уже фиксированы и не помогают — больше.

    Здесь: статическая версия (ничего не фиксировано).
    = среднее (1 / число литералов в клозе) по клозам с var.
    """
    scores = []
    for clause in clauses:
        has_var = False
        for v, s in clause:
            if v == var:
                has_var = True
                break
        if has_var:
            scores.append(1.0 / len(clause))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


# ============================================================
# 6. FREEDOM — при скольких значениях var ни один клоз не умирает
# ============================================================
def freedom(clauses, n, var):
    """
    Проверяем: если var=1, сколько клозов ТЕРЯЮТ последний шанс?
    То же для var=0.

    freedom = 1 означает: оба значения безопасны (ни один клоз не умрёт).
    freedom = 0 означает: оба значения убивают хотя бы один клоз.
    freedom = 0.5 означает: одно значение безопасно, другое нет.
    """
    def dead_clauses_if(var, val):
        """Сколько клозов станут невыполнимыми если var=val,
        при условии что остальные переменные ещё свободны."""
        # Клоз "умирает" только если var — единственный литерал,
        # который мог его спасти, и мы ставим var не туда.
        # Но статически (ничего не фиксировано) другие литералы
        # ещё свободны, поэтому клоз не может "умереть" от одной фиксации
        # ЕСЛИ в нём есть другие свободные литералы.
        dead = 0
        for clause in clauses:
            contains_var = False
            var_helps = False
            other_literals = 0
            for v, s in clause:
                if v == var:
                    contains_var = True
                    if (s == 1 and val == 1) or (s == -1 and val == 0):
                        var_helps = True
                else:
                    other_literals += 1
            if contains_var and not var_helps and other_literals == 0:
                dead += 1
        return dead

    dead_if_0 = dead_clauses_if(var, 0)
    dead_if_1 = dead_clauses_if(var, 1)

    safe_choices = (1 if dead_if_0 == 0 else 0) + (1 if dead_if_1 == 0 else 0)
    return safe_choices / 2.0


# ============================================================
# MEASUREMENT
# ============================================================

def measure_all_static(clauses, n):
    """Measure all 6 static properties for every bit."""
    results = []
    for var in range(n):
        results.append({
            'var': var,
            'pressure': pressure(clauses, n, var),
            'frustration': frustration(clauses, n, var),
            'degree': degree(clauses, n, var),
            'polarity': polarity(clauses, n, var),
            'criticality': criticality(clauses, n, var),
            'freedom': freedom(clauses, n, var),
        })
    return results


def validate_against_solutions(clauses, n, properties, solutions):
    """Check which properties predict the correct bit value."""
    if not solutions:
        return

    # Ground truth: probability of each bit being 1 across solutions
    prob_1 = []
    for var in range(n):
        count = sum(sol[var] for sol in solutions)
        prob_1.append(count / len(solutions))

    print(f"\n{'var':>5} | {'press':>6} | {'frust':>6} | {'deg':>4} | "
          f"{'polar':>6} | {'crit':>6} | {'free':>5} | "
          f"{'P(=1)':>6} | {'press ok?':>9}")
    print("-" * 80)

    correct_pressure = 0
    correct_polarity = 0

    for p in properties:
        var = p['var']
        actual_majority = 1 if prob_1[var] > 0.5 else 0
        predicted_pressure = 1 if p['pressure'] > 0 else 0
        predicted_polarity = 1 if p['polarity'] > 0 else 0

        press_ok = predicted_pressure == actual_majority
        polar_ok = predicted_polarity == actual_majority

        if press_ok:
            correct_pressure += 1
        if polar_ok:
            correct_polarity += 1

        print(f"  x{var:>2} | {p['pressure']:>+6.3f} | {p['frustration']:>6.3f} | "
              f"{p['degree']:>4} | {p['polarity']:>+6.3f} | "
              f"{p['criticality']:>6.3f} | {p['freedom']:>5.1f} | "
              f"{prob_1[var]:>6.3f} | {'yes' if press_ok else 'NO':>9}")

    print(f"\nPressure predicts: {correct_pressure}/{n}")
    print(f"Polarity predicts: {correct_polarity}/{n}")


if __name__ == "__main__":
    print("=" * 80)
    print("BLOCK I: Static Bit Properties")
    print("=" * 80)

    for ratio, label in [(2.0, "EASY"), (4.27, "HARD")]:
        for seed in range(100):
            clauses = random_3sat(12, int(ratio * 12), seed=seed)
            solutions = find_solutions(clauses, 12)
            if len(solutions) > 0 and len(solutions) < 100:
                break

        print(f"\n## {label} instance (n=12, ratio={ratio}, "
              f"{len(solutions)} solutions, seed={seed})")
        props = measure_all_static(clauses, 12)
        validate_against_solutions(clauses, 12, props, solutions)
