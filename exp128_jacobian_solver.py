#!/usr/bin/env python3
"""
EXP 128: ★⁻¹ Jacobian Solver — Exact Gradient Collision Search

From exp127: ★⁻¹ Jacobian is EXACTLY correct for δM=±1 through 19+ rounds.

METHOD:
1. Start with random M₁, M₂
2. Compute δstate = state(M₂) - state(M₁) mod 2^32 (want = 0)
3. Compute Jacobian J: how ±1 on each word of M₂ changes state
4. Find the word change that most reduces |δstate|
5. Apply it. Repeat.

Each step is EXACT (not approximate). The question:
  Does the iterative process CONVERGE to δstate = 0?
  If yes: collision found in O(n) steps where n = state bits.
  If no: what blocks convergence?

Compare with pure random search at same computational budget.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def arith_hash_dist(H1, H2):
    """Sum of |H1[w] - H2[w]| in arithmetic sense (min of +/-)."""
    total = 0
    for w in range(8):
        d = (H1[w] - H2[w]) & MASK
        d_neg = (H2[w] - H1[w]) & MASK
        total += min(d, d_neg)
    return total

def xor_hash_dist(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def compute_jacobian(M, R=64):
    """Compute exact ★⁻¹ Jacobian: how ±1 on each word changes state.
    Returns J_plus[w] and J_minus[w] = δstate for M[w]±1."""
    base = sha256_rounds(M, R)[R]

    J_plus = []   # J_plus[w][h] = (state_h(M+e_w) - state_h(M)) mod 2^32
    J_minus = []

    for w in range(16):
        Mp = list(M); Mp[w] = (Mp[w] + 1) & MASK
        sp = sha256_rounds(Mp, R)[R]
        J_plus.append([(sp[h] - base[h]) & MASK for h in range(8)])

        Mm = list(M); Mm[w] = (Mm[w] - 1) & MASK
        sm = sha256_rounds(Mm, R)[R]
        J_minus.append([(sm[h] - base[h]) & MASK for h in range(8)])

    return base, J_plus, J_minus

def jacobian_step(M_current, target_state, R=64):
    """One step: find ±1 change on one word that best reduces δstate."""
    current_state = sha256_rounds(M_current, R)[R]
    delta = [(target_state[h] - current_state[h]) & MASK for h in range(8)]
    current_dist = sum(min(d, ((-d) & MASK)) for d in delta)

    if current_dist == 0:
        return M_current, 0, True  # Already there!

    _, J_plus, J_minus = compute_jacobian(M_current, R)

    best_dist = current_dist
    best_M = None
    best_w = -1
    best_dir = 0

    for w in range(16):
        for direction, J in [(+1, J_plus[w]), (-1, J_minus[w])]:
            # New state = current + J (from Jacobian, exact for δ=±1)
            new_state = [(current_state[h] + J[h]) & MASK for h in range(8)]
            new_delta = [(target_state[h] - new_state[h]) & MASK for h in range(8)]
            new_dist = sum(min(d, ((-d) & MASK)) for d in new_delta)

            if new_dist < best_dist:
                best_dist = new_dist
                best_w = w
                best_dir = direction
                M_new = list(M_current)
                M_new[w] = (M_new[w] + direction) & MASK
                best_M = M_new

    if best_M is not None:
        return best_M, best_dist, False
    return M_current, current_dist, False

def test_jacobian_solver(N=20, max_steps=500, R=64):
    """Jacobian solver: iterative ±1 steps with exact gradient."""
    print(f"\n--- JACOBIAN SOLVER ({R} rounds, N={N}, max_steps={max_steps}) ---")

    results = []
    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]

        M2 = random_w16()
        initial_dist = sum(min((target[h] - sha256_rounds(M2, R)[R][h]) & MASK,
                              (sha256_rounds(M2, R)[R][h] - target[h]) & MASK)
                          for h in range(8))

        trajectory = [initial_dist]
        collision = False

        for step in range(max_steps):
            M2, dist, found = jacobian_step(M2, target, R)
            trajectory.append(dist)

            if found:
                collision = True
                print(f"  Trial {trial}: COLLISION at step {step+1}!")
                break

            if step > 0 and trajectory[-1] >= trajectory[-2]:
                # Stuck — no improvement
                break

        final_dist = trajectory[-1]
        dH = xor_hash_dist(sha256_rounds(M2, R)[R], target)
        results.append({
            'initial': initial_dist,
            'final': final_dist,
            'steps': len(trajectory) - 1,
            'collision': collision,
            'xor_dist': dH,
        })

        if trial < 5:
            traj_str = [str(trajectory[i]) for i in range(0, min(len(trajectory), 20), max(1, len(trajectory)//10))]
            print(f"  Trial {trial}: {' → '.join(traj_str[:8])}")

    # Summary
    finals = [r['final'] for r in results]
    xors = [r['xor_dist'] for r in results]
    steps = [r['steps'] for r in results]
    n_coll = sum(1 for r in results if r['collision'])

    print(f"\n  Summary:")
    print(f"    Collisions: {n_coll}/{N}")
    print(f"    Mean final arith dist: {np.mean(finals):.0f}")
    print(f"    Min final arith dist: {min(finals)}")
    print(f"    Mean final XOR dist: {np.mean(xors):.1f}")
    print(f"    Min final XOR dist: {min(xors)}")
    print(f"    Mean steps: {np.mean(steps):.0f}")

    return results

def test_reduced_rounds(N=20, max_steps=500):
    """Test solver at various round counts."""
    print(f"\n--- SOLVER vs ROUND COUNT ---")

    for R in [4, 8, 16, 32, 64]:
        results = []
        for trial in range(N):
            M1 = random_w16()
            target = sha256_rounds(M1, R)[R]
            M2 = random_w16()

            for step in range(max_steps):
                M2, dist, found = jacobian_step(M2, target, R)
                if found or dist == 0:
                    break
                # Quick stuck detection
                if step > 20:
                    M2_test, dist_test, _ = jacobian_step(M2, target, R)
                    if dist_test >= dist:
                        break

            final_xor = xor_hash_dist(sha256_rounds(M2, R)[R], target)
            results.append(final_xor)

        avg = np.mean(results); mn = min(results)
        print(f"  {R:>2} rounds: avg_dH = {avg:.1f}, min_dH = {mn}")

def test_vs_random(N=20, budget=10000, R=16):
    """Compare Jacobian solver vs random search at same budget."""
    print(f"\n--- JACOBIAN vs RANDOM ({R} rounds, budget={budget}) ---")

    # Jacobian solver: each step = 32 hash evaluations (16 words × 2 directions)
    jac_steps = budget // 32

    # Jacobian
    jac_best = []
    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]
        M2 = random_w16()
        best_dH = xor_hash_dist(sha256_rounds(M2, R)[R], target)

        for step in range(jac_steps):
            M2, dist, found = jacobian_step(M2, target, R)
            dH = xor_hash_dist(sha256_rounds(M2, R)[R], target)
            best_dH = min(best_dH, dH)
            if found: break
            if step > 5:
                M2_t, d_t, _ = jacobian_step(M2, target, R)
                if d_t >= dist: break

        jac_best.append(best_dH)

    # Random search: budget hash evaluations
    rand_best = []
    for trial in range(N):
        M1 = random_w16()
        target = sha256_rounds(M1, R)[R]
        best_dH = 256

        for _ in range(budget):
            M2 = random_w16()
            dH = xor_hash_dist(sha256_rounds(M2, R)[R], target)
            best_dH = min(best_dH, dH)

        rand_best.append(best_dH)

    print(f"  Jacobian solver: avg best dH = {np.mean(jac_best):.1f}, min = {min(jac_best)}")
    print(f"  Random search:   avg best dH = {np.mean(rand_best):.1f}, min = {min(rand_best)}")

    if np.mean(jac_best) < np.mean(rand_best):
        gain = np.mean(rand_best) - np.mean(jac_best)
        print(f"  ★⁻¹ JACOBIAN WINS by {gain:.1f} bits!")
    else:
        print(f"  Random wins (Jacobian stuck in local minimum)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 128: ★⁻¹ JACOBIAN SOLVER")
    print("Exact gradient descent using ★⁻¹ linearity")
    print("=" * 60)

    test_reduced_rounds(N=15, max_steps=300)
    test_vs_random(N=15, budget=5000, R=8)
    test_jacobian_solver(N=10, max_steps=200, R=64)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★⁻¹ Jacobian Solver")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
