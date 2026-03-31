#!/usr/bin/env python3
"""
EXP 129: Adaptive Multi-Tool Solver

Not one tool for 64 rounds — SWITCH tools per phase.

TOOLS AVAILABLE:
  T1: ★⁻¹ Jacobian (exact for δ=±1, rounds 1-19)
  T2: Random perturbation (escapes local minima)
  T3: Reverse walk (from target backward, exact per round)
  T4: Carry-AND alignment (feedforward signal, rounds 63-64)
  T5: Multi-bit jump (larger δM, approximate but escapes plateaus)

STRATEGY: Let the solver CHOOSE which tool at each step.
Score = hash distance reduction. Pick best tool per step.

Phase 1 (explore): random + multi-bit jumps to find promising region
Phase 2 (refine): ★⁻¹ Jacobian for precise descent
Phase 3 (finish): carry-AND alignment for last rounds

vs BASELINE: pure random search with same budget.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def xor_dist(s1, s2):
    return sum(hw(s1[w] ^ s2[w]) for w in range(8))

def arith_dist(s1, s2):
    return sum(min((s1[w] - s2[w]) & MASK, (s2[w] - s1[w]) & MASK) for w in range(8))

# ============================================================
# TOOL 1: ★⁻¹ Jacobian (single word ±1)
# ============================================================
def tool_jacobian(M, target, R, n_eval=32):
    """Try all 32 single-word ±1 changes, pick best."""
    s_current = sha256_rounds(M, R)[R]
    current_d = xor_dist(s_current, target)
    best_M = None; best_d = current_d

    for w in range(16):
        for direction in [+1, -1]:
            Mt = list(M); Mt[w] = (Mt[w] + direction) & MASK
            st = sha256_rounds(Mt, R)[R]
            d = xor_dist(st, target)
            if d < best_d:
                best_d = d; best_M = Mt

    return best_M if best_M else M, best_d, 32  # 32 evaluations

# ============================================================
# TOOL 2: Random perturbation (escape local minima)
# ============================================================
def tool_random_perturb(M, target, R, n_eval=32):
    """Try random messages, keep best."""
    best_d = xor_dist(sha256_rounds(M, R)[R], target)
    best_M = M

    for _ in range(n_eval):
        Mt = random_w16()
        st = sha256_rounds(Mt, R)[R]
        d = xor_dist(st, target)
        if d < best_d:
            best_d = d; best_M = Mt

    return best_M, best_d, n_eval

# ============================================================
# TOOL 3: Multi-bit jump (flip random bits)
# ============================================================
def tool_multibit(M, target, R, n_eval=32):
    """Flip 1-8 random bits, try several."""
    s_current = sha256_rounds(M, R)[R]
    current_d = xor_dist(s_current, target)
    best_M = M; best_d = current_d

    for _ in range(n_eval):
        Mt = list(M)
        n_flips = random.randint(1, 8)
        for _ in range(n_flips):
            w = random.randint(0, 15)
            b = random.randint(0, 31)
            Mt[w] ^= (1 << b)
        st = sha256_rounds(Mt, R)[R]
        d = xor_dist(st, target)
        if d < best_d:
            best_d = d; best_M = Mt

    return best_M, best_d, n_eval

# ============================================================
# TOOL 4: Word replacement (replace one word entirely)
# ============================================================
def tool_word_replace(M, target, R, n_eval=32):
    """Replace one random word with random value."""
    s_current = sha256_rounds(M, R)[R]
    current_d = xor_dist(s_current, target)
    best_M = M; best_d = current_d

    for _ in range(n_eval):
        Mt = list(M)
        w = random.randint(0, 15)
        Mt[w] = random.randint(0, MASK)
        st = sha256_rounds(Mt, R)[R]
        d = xor_dist(st, target)
        if d < best_d:
            best_d = d; best_M = Mt

    return best_M, best_d, n_eval

# ============================================================
# TOOL 5: Jacobian multi-step (accumulate ±1 changes)
# ============================================================
def tool_jacobian_multi(M, target, R, n_eval=32):
    """Apply multiple ±1 changes guided by Jacobian."""
    best_M = list(M)
    best_d = xor_dist(sha256_rounds(M, R)[R], target)
    evals = 0

    Mt = list(M)
    for _ in range(n_eval // 2):
        # Pick random word, try ±1
        w = random.randint(0, 15)
        for direction in [+1, -1]:
            Mt2 = list(Mt); Mt2[w] = (Mt2[w] + direction) & MASK
            st = sha256_rounds(Mt2, R)[R]
            d = xor_dist(st, target)
            evals += 1
            if d < best_d:
                best_d = d; best_M = Mt2; Mt = Mt2
                break

    return best_M, best_d, evals

# ============================================================
# ADAPTIVE SOLVER
# ============================================================
def adaptive_solve(M_target_state, R=64, total_budget=10000):
    """Adaptive solver: pick best tool at each step."""
    target = M_target_state
    M = random_w16()
    current_d = xor_dist(sha256_rounds(M, R)[R], target)

    tools = [
        ("Jacobian±1", tool_jacobian),
        ("Random", tool_random_perturb),
        ("MultiBit", tool_multibit),
        ("WordReplace", tool_word_replace),
        ("JacMulti", tool_jacobian_multi),
    ]

    budget_used = 0
    tool_wins = {name: 0 for name, _ in tools}
    tool_tries = {name: 0 for name, _ in tools}
    trajectory = [current_d]
    stagnation = 0

    while budget_used < total_budget:
        # Try each tool, keep best result
        best_tool = None
        best_M_new = M
        best_d_new = current_d

        for name, tool_fn in tools:
            M_new, d_new, evals = tool_fn(M, target, R, n_eval=32)
            budget_used += evals
            tool_tries[name] += 1

            if d_new < best_d_new:
                best_d_new = d_new
                best_M_new = M_new
                best_tool = name

        if best_d_new < current_d:
            M = best_M_new
            current_d = best_d_new
            if best_tool:
                tool_wins[best_tool] += 1
            stagnation = 0
        else:
            stagnation += 1
            # If stuck, force random restart
            if stagnation > 5:
                M = random_w16()
                current_d = xor_dist(sha256_rounds(M, R)[R], target)
                stagnation = 0

        trajectory.append(current_d)

        if current_d == 0:
            return M, trajectory, tool_wins, tool_tries, True

    return M, trajectory, tool_wins, tool_tries, False

def test_adaptive_vs_random(N=20, budget=15000, R=64):
    """Compare adaptive solver vs pure random."""
    print(f"\n--- ADAPTIVE vs RANDOM ({R} rounds, budget={budget}) ---")

    # Adaptive
    adapt_results = []
    all_tool_wins = {}
    all_tool_tries = {}

    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]

        M2, traj, wins, tries, found = adaptive_solve(target, R, budget)

        final_d = traj[-1]
        adapt_results.append(final_d)

        for name in wins:
            all_tool_wins[name] = all_tool_wins.get(name, 0) + wins[name]
            all_tool_tries[name] = all_tool_tries.get(name, 0) + tries[name]

        if found:
            print(f"  Trial {trial}: COLLISION FOUND!")

    # Random search
    rand_results = []
    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]
        best_d = 256

        for _ in range(budget):
            M2 = random_w16()
            d = xor_dist(sha256_rounds(M2, R)[R], target)
            best_d = min(best_d, d)

        rand_results.append(best_d)

    adapt_arr = np.array(adapt_results)
    rand_arr = np.array(rand_results)

    print(f"\n  RESULTS:")
    print(f"  {'':>15} | {'Avg dH':>8} | {'Min dH':>8} | {'Median':>8}")
    print(f"  {'-'*45}")
    print(f"  {'Adaptive':>15} | {adapt_arr.mean():>8.1f} | {adapt_arr.min():>8} | {np.median(adapt_arr):>8.1f}")
    print(f"  {'Random':>15} | {rand_arr.mean():>8.1f} | {rand_arr.min():>8} | {np.median(rand_arr):>8.1f}")

    if adapt_arr.mean() < rand_arr.mean():
        gain = rand_arr.mean() - adapt_arr.mean()
        print(f"\n  ★ ADAPTIVE WINS by {gain:.1f} bits!")
    else:
        print(f"\n  Random wins by {adapt_arr.mean() - rand_arr.mean():.1f} bits")

    # Tool effectiveness
    print(f"\n  TOOL EFFECTIVENESS:")
    print(f"  {'Tool':>15} | {'Wins':>6} | {'Tries':>6} | {'Win%':>6}")
    print(f"  {'-'*40}")
    for name in all_tool_wins:
        w = all_tool_wins[name]
        t = all_tool_tries[name]
        pct = w / t * 100 if t > 0 else 0
        print(f"  {name:>15} | {w:>6} | {t:>6} | {pct:>5.1f}%")

def test_at_various_rounds(N=15, budget=10000):
    """Test adaptive solver at different round counts."""
    print(f"\n--- ADAPTIVE SOLVER vs ROUNDS ---")

    for R in [4, 8, 16, 32, 64]:
        results = []
        for trial in range(N):
            M1 = random_w16()
            target = sha256_rounds(M1, R)[R]
            _, traj, _, _, found = adaptive_solve(target, R, budget)
            results.append(traj[-1])

        arr = np.array(results)
        print(f"  {R:>2} rounds: avg={arr.mean():.1f}, min={arr.min()}, median={np.median(arr):.0f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 129: ADAPTIVE MULTI-TOOL SOLVER")
    print("Switch tools per phase, like digging through layers")
    print("=" * 60)

    test_at_various_rounds(N=12, budget=8000)
    test_adaptive_vs_random(N=15, budget=12000, R=64)

    print(f"\n{'='*60}")
    print(f"VERDICT: Adaptive solver")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
