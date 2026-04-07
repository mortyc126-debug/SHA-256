"""
BitMechanics SAT Solver — Verification prototype.

NOT a final algorithm. A test bed to verify that our discoveries
translate into measurable solver improvement.

Compares:
1. Random baseline (DPLL-like random branching)
2. Standard tension crystallization
3. Enhanced: tension + confidence filtering + cascade amplification
4. Enhanced + lightweight backtrack
"""

import random
import time
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


def bit_tension(clauses, n, var, fixed):
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


def has_dead_clause(clauses, n, fixed):
    for clause in clauses:
        satisfied = False
        free = 0
        for v, s in clause:
            if v in fixed:
                if (s == 1 and fixed[v] == 1) or (s == -1 and fixed[v] == 0):
                    satisfied = True
                    break
            else:
                free += 1
        if not satisfied and free == 0:
            return True
    return False


def unit_propagate(clauses, n, fixed):
    """If any clause has exactly 1 free literal, force it."""
    changed = True
    forced = dict(fixed)
    while changed:
        changed = False
        for clause in clauses:
            satisfied = False
            free_literals = []
            for v, s in clause:
                if v in forced:
                    if (s == 1 and forced[v] == 1) or (s == -1 and forced[v] == 0):
                        satisfied = True
                        break
                else:
                    free_literals.append((v, s))
            if not satisfied and len(free_literals) == 1:
                v, s = free_literals[0]
                val = 1 if s == 1 else 0
                if v not in forced:
                    forced[v] = val
                    changed = True
    return forced


# ============================================================
# SOLVER 1: Random branching (baseline)
# ============================================================

def solve_random(clauses, n, max_backtracks=1000):
    """Simple DPLL with random variable/value selection."""
    calls = [0]

    def dpll(fixed):
        calls[0] += 1
        if calls[0] > max_backtracks:
            return None

        fixed = unit_propagate(clauses, n, fixed)

        if has_dead_clause(clauses, n, fixed):
            return None

        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            assignment = [fixed.get(v, 0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                return assignment
            return None

        var = random.choice(unfixed)
        for val in [random.randint(0, 1), None]:
            if val is None:
                val = 1 - (random.randint(0, 1))  # try other value
            new_fixed = dict(fixed)
            new_fixed[var] = val
            result = dpll(new_fixed)
            if result is not None:
                return result

        return None

    return dpll({}), calls[0]


# ============================================================
# SOLVER 2: Tension crystallization (our basic method)
# ============================================================

def solve_tension(clauses, n):
    """Fix bits by tension, no backtracking."""
    fixed = {}
    calls = 0

    for step in range(n):
        fixed = unit_propagate(clauses, n, fixed)
        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break
        calls += 1

        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        fixed[best] = 1 if sigma >= 0 else 0

    assignment = [fixed.get(v, 0) for v in range(n)]
    success = evaluate(clauses, assignment) == len(clauses)
    return assignment if success else None, calls


# ============================================================
# SOLVER 3: Enhanced tension + confidence filter
# ============================================================

def solve_enhanced(clauses, n):
    """
    Phase 1: Fix only high-confidence bits (|σ| > 0.4)
    Phase 2: After cascade, fix remaining by tension
    Uses unit propagation aggressively.
    """
    fixed = {}
    calls = 0

    # Phase 1: confident bits only
    for threshold in [0.5, 0.4, 0.3, 0.2, 0.1, 0.0]:
        changed = True
        while changed:
            changed = False
            fixed = unit_propagate(clauses, n, fixed)
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed:
                break

            candidates = []
            for v in unfixed:
                calls += 1
                sigma = bit_tension(clauses, n, v, fixed)
                if abs(sigma) >= threshold:
                    candidates.append((v, sigma))

            if candidates:
                candidates.sort(key=lambda c: -abs(c[1]))
                best_var, best_sigma = candidates[0]
                fixed[best_var] = 1 if best_sigma >= 0 else 0
                changed = True

    assignment = [fixed.get(v, 0) for v in range(n)]
    success = evaluate(clauses, assignment) == len(clauses)
    return assignment if success else None, calls


# ============================================================
# SOLVER 4: Enhanced + backtrack on dead clauses
# ============================================================

def solve_enhanced_bt(clauses, n, max_bt=20):
    """Enhanced with lightweight backtracking."""
    history = []
    fixed = {}
    calls = 0
    backtracks = 0

    while True:
        fixed = unit_propagate(clauses, n, fixed)

        if has_dead_clause(clauses, n, fixed):
            if not history or backtracks >= max_bt:
                return None, calls
            # Backtrack: undo last low-confidence fix
            history.sort(key=lambda h: h[2])  # sort by confidence
            worst = history[0]
            # Remove all fixes after worst
            new_fixed = {}
            for var, val, conf, order in history:
                if order < worst[3]:
                    new_fixed[var] = val
            fixed = new_fixed
            # Flip worst
            fixed[worst[0]] = 1 - worst[1]
            history = [(v, val, c, o) for v, val, c, o in history
                       if o < worst[3]]
            history.append((worst[0], 1 - worst[1], 999, worst[3]))
            backtracks += 1
            continue

        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            break

        calls += 1
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        val = 1 if sigma >= 0 else 0
        fixed[best] = val
        history.append((best, val, abs(sigma), len(history)))

    assignment = [fixed.get(v, 0) for v in range(n)]
    success = evaluate(clauses, assignment) == len(clauses)
    return assignment if success else None, calls


# ============================================================
# SOLVER 5: DPLL with tension-guided branching
# ============================================================

def solve_dpll_tension(clauses, n, max_calls=5000):
    """Full DPLL but use tension to choose variable AND value."""
    calls = [0]

    def dpll(fixed):
        calls[0] += 1
        if calls[0] > max_calls:
            return None

        fixed = unit_propagate(clauses, n, fixed)

        if has_dead_clause(clauses, n, fixed):
            return None

        unfixed = [v for v in range(n) if v not in fixed]
        if not unfixed:
            assignment = [fixed.get(v, 0) for v in range(n)]
            if evaluate(clauses, assignment) == len(clauses):
                return assignment
            return None

        # Choose variable by tension (most confident first)
        best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
        sigma = bit_tension(clauses, n, best, fixed)
        first_val = 1 if sigma >= 0 else 0

        # Try tension-guided value first
        new_fixed = dict(fixed)
        new_fixed[best] = first_val
        result = dpll(new_fixed)
        if result is not None:
            return result

        # Try other value
        new_fixed = dict(fixed)
        new_fixed[best] = 1 - first_val
        return dpll(new_fixed)

    return dpll({}), calls[0]


# ============================================================
# BENCHMARK
# ============================================================

def benchmark(n_range, ratio=4.27, n_instances=100):
    solvers = {
        'random DPLL': lambda c, n: solve_random(c, n, max_backtracks=5000),
        'tension': lambda c, n: solve_tension(c, n),
        'enhanced': lambda c, n: solve_enhanced(c, n),
        'enhanced+BT': lambda c, n: solve_enhanced_bt(c, n, max_bt=20),
        'DPLL+tension': lambda c, n: solve_dpll_tension(c, n, max_calls=5000),
    }

    print(f"{'n':>4} | ", end="")
    for name in solvers:
        print(f"{name:>15} | ", end="")
    print()
    print("-" * (6 + 18 * len(solvers)))

    for n in n_range:
        row = f"{n:>4} | "
        for name, solver in solvers.items():
            solved = 0
            total = 0
            total_calls = 0
            total_time = 0

            for seed in range(n_instances):
                clauses = random_3sat(n, int(ratio * n), seed=seed)

                # Quick check: is it satisfiable? (only for small n)
                if n <= 16:
                    solutions = find_solutions(clauses, n)
                    if not solutions:
                        continue
                total += 1

                t0 = time.time()
                result, calls = solver(clauses, n)
                t1 = time.time()

                total_calls += calls
                total_time += (t1 - t0)

                if result is not None:
                    solved += 1

            if total > 0:
                rate = solved / total * 100
                avg_calls = total_calls / total
                avg_time = total_time / total * 1000  # ms
                row += f"{rate:>5.0f}%/{avg_calls:>5.0f}c | "
            else:
                row += f"{'N/A':>15} | "

        print(row)


if __name__ == "__main__":
    random.seed(42)

    print("=" * 100)
    print("BITMECHANICS SAT SOLVER — VERIFICATION BENCHMARK")
    print("=" * 100)

    print("\n## Ratio = 4.27 (SAT threshold)")
    print("Format: solve_rate% / avg_calls")
    benchmark([10, 12, 14, 16], ratio=4.27, n_instances=100)

    print("\n## Ratio = 3.5 (medium difficulty)")
    benchmark([10, 12, 14, 16, 18, 20], ratio=3.5, n_instances=100)

    print("\n## Ratio = 3.0 (easier)")
    benchmark([10, 12, 14, 16, 18, 20], ratio=3.0, n_instances=100)

    # Timing comparison for larger n
    print("\n" + "=" * 100)
    print("TIMING: Larger instances (ratio=3.5)")
    print("=" * 100)

    for n in [20, 25, 30]:
        print(f"\nn={n}:")
        for name, solver in [
            ('tension', lambda c, nn: solve_tension(c, nn)),
            ('enhanced+BT', lambda c, nn: solve_enhanced_bt(c, nn, 50)),
            ('DPLL+tension', lambda c, nn: solve_dpll_tension(c, nn, 50000)),
        ]:
            solved = 0
            total = 0
            t_total = 0

            for seed in range(50):
                clauses = random_3sat(n, int(3.5 * n), seed=seed)
                total += 1

                t0 = time.time()
                result, calls = solver(clauses, n)
                t1 = time.time()
                t_total += (t1 - t0)

                if result is not None:
                    # Verify
                    if evaluate(clauses, result) == len(clauses):
                        solved += 1

            avg_t = t_total / total * 1000
            print(f"  {name:>15}: {solved}/{total} solved, {avg_t:.1f}ms avg")
