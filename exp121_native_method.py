#!/usr/bin/env python3
"""
EXP 121: Native Collision Method — Built FROM ★-Algebra

We've been applying EXTERNAL math to SHA-256 (GF(2), Z/2^32Z, PCA, Newton).
Each time, ★-native version worked better. Time to build the method
ENTIRELY from ★-algebra, without borrowing from outside.

WHAT ★ GIVES US NATIVELY:
  ★(a,b) = (a⊕b, a&b) — the fundamental split
  π_add: ★-space → Z/2^32Z — the projection (addition)
  Carry cascade: sequential resolution of ★-pairs

KEY INSIGHT FROM EXP 117-120:
  1. Near-collisions have lower ★-AND component (Z=-15)
  2. ★-total across words is biased (Z=-17.66)
  3. ★-Newton reaches dH=29 at 2 rounds (standard: dH=38)

THE NATIVE APPROACH:
  Instead of working in hash space (256 bits, birthday 2^128),
  work in ★-SPACE (512 bits: 256 XOR + 256 AND).

  In ★-space, collision = specific RELATIONSHIP between XOR and AND parts.
  The AND part is SMALLER than XOR part for near-collisions (exp117).

  What if we search for collisions in ★-space directly?
  ★-space has MORE structure than hash space:
    - AND component has carry rank 243 (not 256)
    - XOR component is fully determined by AND + hash
    - The constraint δα = δC is native to ★

METHOD: ★-WALK
  1. Start with random (M₁, M₂)
  2. Compute ★-distance: not hash distance, but ★-distance
  3. Move in ★-space toward ★-collision (not hash-collision)
  4. ★-collision implies hash-collision but may be easier to find
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def star_pair(a, b):
    """★(a,b) = (a⊕b, a&b)."""
    return (a ^ b, a & b)

def star_distance(M1, M2, R=64):
    """★-distance between two messages: distance in ★-space of their states.

    Standard distance: dH = HW(H1 ⊕ H2)
    ★-distance: considers BOTH components of ★(IV, state).
    """
    s1 = sha256_rounds(M1, R)
    s2 = sha256_rounds(M2, R)

    d_xor = 0  # XOR component distance
    d_and = 0  # AND component distance
    d_carry = 0  # Carry component distance

    for w in range(8):
        # ★(IV, s1) and ★(IV, s2)
        xor1, and1 = star_pair(IV[w], s1[R][w])
        xor2, and2 = star_pair(IV[w], s2[R][w])

        d_xor += hw(xor1 ^ xor2)
        d_and += hw(and1 ^ and2)

        c1 = carry_word(IV[w], s1[R][w])
        c2 = carry_word(IV[w], s2[R][w])
        d_carry += hw(c1 ^ c2)

    return d_xor, d_and, d_carry

def hash_distance(M1, M2, R=64):
    """Standard hash distance."""
    H1 = sha256_compress(M1) if R == 64 else [(IV[i] + sha256_rounds(M1, R)[R][i]) & MASK for i in range(8)]
    H2 = sha256_compress(M2) if R == 64 else [(IV[i] + sha256_rounds(M2, R)[R][i]) & MASK for i in range(8)]
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def test_star_vs_hash_distance(N=5000):
    """Is ★-distance more informative than hash distance?"""
    print(f"\n--- ★-DISTANCE vs HASH DISTANCE (N={N}) ---")

    dH_all = []; d_xor_all = []; d_and_all = []; d_carry_all = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        dH = hash_distance(M1, M2)
        dx, da, dc = star_distance(M1, M2)

        dH_all.append(dH)
        d_xor_all.append(dx)
        d_and_all.append(da)
        d_carry_all.append(dc)

    dH = np.array(dH_all)
    dx = np.array(d_xor_all)
    da = np.array(d_and_all)
    dc = np.array(d_carry_all)

    print(f"  E[dH]:      {dH.mean():.2f} ± {dH.std():.2f}")
    print(f"  E[d_xor]:   {dx.mean():.2f} ± {dx.std():.2f}")
    print(f"  E[d_and]:   {da.mean():.2f} ± {da.std():.2f}")
    print(f"  E[d_carry]: {dc.mean():.2f} ± {dc.std():.2f}")

    # Correlations
    print(f"\n  Correlations:")
    print(f"    corr(dH, d_xor):   {np.corrcoef(dH, dx)[0,1]:+.6f}")
    print(f"    corr(dH, d_and):   {np.corrcoef(dH, da)[0,1]:+.6f}")
    print(f"    corr(dH, d_carry): {np.corrcoef(dH, dc)[0,1]:+.6f}")
    print(f"    corr(d_and, d_carry): {np.corrcoef(da, dc)[0,1]:+.6f}")

    # KEY: does d_and predict dH better than d_xor?
    # Collision = dH=0, which means d_xor = 2*d_carry (shifted)
    # In ★-space: collision ⟺ ★-XOR = shift(★-AND)

    # Among pairs with LOW d_and: what's dH?
    p10 = np.percentile(da, 10)
    low_and_mask = da <= p10
    print(f"\n  Low d_and (bottom 10%, d_and ≤ {p10}):")
    print(f"    E[dH | low d_and]:    {dH[low_and_mask].mean():.2f}")
    print(f"    E[dH | random]:       {dH.mean():.2f}")
    print(f"    Gain: {dH.mean() - dH[low_and_mask].mean():.2f} bits")

def star_walk_step(M, target_H, R=64, n_candidates=64):
    """One step of ★-walk: find bit flip that best reduces ★-distance.

    Unlike standard gradient descent (minimize dH),
    ★-walk minimizes a COMBINED ★-metric."""

    H_current = sha256_compress(M) if R == 64 else \
                [(IV[i] + sha256_rounds(M, R)[R][i]) & MASK for i in range(8)]
    dH_current = sum(hw(H_current[w] ^ target_H[w]) for w in range(8))

    s = sha256_rounds(M, R)

    # ★-metric: weighted combination of XOR, AND, carry distances
    def star_metric(M_test):
        H_test = sha256_compress(M_test) if R == 64 else \
                 [(IV[i] + sha256_rounds(M_test, R)[R][i]) & MASK for i in range(8)]
        dH = sum(hw(H_test[w] ^ target_H[w]) for w in range(8))

        s_test = sha256_rounds(M_test, R)
        d_and = sum(hw((IV[w] & s[R][w]) ^ (IV[w] & s_test[R][w])) for w in range(8))
        d_carry = sum(hw(carry_word(IV[w], s[R][w]) ^ carry_word(IV[w], s_test[R][w])) for w in range(8))

        # ★-native metric: hash distance + carry weight (★ sees both)
        return dH + 0.5 * d_carry, dH

    best_metric = star_metric(M)[0]
    best_M = None
    best_dH = dH_current

    for _ in range(n_candidates):
        w_idx = random.randint(0, 15)
        b_idx = random.randint(0, 31)

        M_test = list(M)
        M_test[w_idx] ^= (1 << b_idx)

        metric, dH = star_metric(M_test)
        if metric < best_metric:
            best_metric = metric
            best_M = M_test
            best_dH = dH

    if best_M is not None:
        return best_M, best_dH
    return M, dH_current

def test_star_walk(N=50, max_steps=300, R=4):
    """★-walk: iterative approach using ★-metric."""
    print(f"\n--- ★-WALK ({R} rounds, N={N}, max_steps={max_steps}) ---")

    collisions = 0
    best_global_dH = 256
    dH_trajectories = []

    for trial in range(N):
        M1 = random_w16()
        target_H = [(IV[i] + sha256_rounds(M1, R)[R][i]) & MASK for i in range(8)]

        M2 = random_w16()
        trajectory = []

        for step in range(max_steps):
            M2, dH = star_walk_step(M2, target_H, R, n_candidates=32)
            trajectory.append(dH)

            if dH == 0 and M1 != M2:
                collisions += 1
                break

            if dH < best_global_dH:
                best_global_dH = dH

        dH_trajectories.append(trajectory)

    # Analyze trajectories
    print(f"  Collisions: {collisions}/{N}")
    print(f"  Best dH reached: {best_global_dH}")

    # Average trajectory
    min_len = min(len(t) for t in dH_trajectories)
    avg_traj = [np.mean([t[s] for t in dH_trajectories]) for s in range(min(min_len, 50))]

    print(f"  Trajectory (avg dH per step):")
    for s in [0, 1, 2, 5, 10, 20, 50, 100, 200, 299]:
        if s < len(avg_traj):
            print(f"    Step {s:>3}: dH = {avg_traj[s]:.1f}")

    return collisions, best_global_dH

def test_standard_walk(N=50, max_steps=300, R=4):
    """Standard gradient descent (minimize dH only) for comparison."""
    print(f"\n--- STANDARD WALK ({R} rounds, N={N}) ---")

    collisions = 0
    best_global_dH = 256

    for trial in range(N):
        M1 = random_w16()
        target_H = [(IV[i] + sha256_rounds(M1, R)[R][i]) & MASK for i in range(8)]

        M2 = random_w16()
        dH_current = hash_distance(M2, M1, R)

        for step in range(max_steps):
            best_dH = dH_current
            best_M = None

            for _ in range(32):
                w_idx = random.randint(0, 15)
                b_idx = random.randint(0, 31)
                M_test = list(M2)
                M_test[w_idx] ^= (1 << b_idx)
                dH_test = hash_distance(M_test, M1, R)

                if dH_test < best_dH:
                    best_dH = dH_test
                    best_M = M_test

            if best_M is not None:
                M2 = best_M
                dH_current = best_dH

            if dH_current == 0:
                collisions += 1
                break

            if dH_current < best_global_dH:
                best_global_dH = dH_current

    print(f"  Collisions: {collisions}/{N}")
    print(f"  Best dH reached: {best_global_dH}")
    return collisions, best_global_dH

def test_star_metric_design(N=10000):
    """Design the optimal ★-metric for collision search.

    The ★-metric should:
    1. Equal zero IFF hash collision
    2. Be smoother than hash distance (fewer local minima)
    3. Use ★-native operations only
    """
    print(f"\n--- ★-METRIC DESIGN (N={N}) ---")

    # Collect data: for random pairs, measure various ★-quantities
    # and their correlation with dH

    metrics = {
        'dH': [],
        'd_state_xor': [],      # HW(s1 ⊕ s2) — state XOR diff
        'd_carry_ff': [],       # HW(carry1 ⊕ carry2) — feedforward carry diff
        'd_and_ff': [],         # HW((IV&s1) ⊕ (IV&s2)) — feedforward AND diff
        'd_carry_AND_overlap': [],  # HW(δcarry & δ(IV&s))
        'collision_eq': [],     # |δα - δC| — how close to δα=δC
    }

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)

        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        d_state = sum(hw(s1[64][w] ^ s2[64][w]) for w in range(8))
        d_carry = sum(hw(carry_word(IV[w], s1[64][w]) ^ carry_word(IV[w], s2[64][w])) for w in range(8))
        d_and = sum(hw((IV[w] & s1[64][w]) ^ (IV[w] & s2[64][w])) for w in range(8))

        # Collision equation: δH = δ(state) ⊕ 2·δ(carry)
        # δα = state diff, δC = carry diff
        # For collision: δα = δC (in the carry sense)
        delta_alpha = sum(hw(s1[64][w] ^ s2[64][w]) for w in range(8))
        delta_C = sum(hw(carry_word(IV[w], s1[64][w]) ^ carry_word(IV[w], s2[64][w])) for w in range(8))
        collision_eq = abs(delta_alpha - delta_C)

        # Carry-AND overlap
        overlap = 0
        for w in range(8):
            dc = carry_word(IV[w], s1[64][w]) ^ carry_word(IV[w], s2[64][w])
            da = (IV[w] & s1[64][w]) ^ (IV[w] & s2[64][w])
            overlap += hw(dc & da)

        metrics['dH'].append(dH)
        metrics['d_state_xor'].append(d_state)
        metrics['d_carry_ff'].append(d_carry)
        metrics['d_and_ff'].append(d_and)
        metrics['d_carry_AND_overlap'].append(overlap)
        metrics['collision_eq'].append(collision_eq)

    # Convert to arrays
    for k in metrics:
        metrics[k] = np.array(metrics[k], dtype=float)

    # Correlations with dH
    print(f"  Metric correlations with dH:")
    for k in metrics:
        if k == 'dH': continue
        corr = np.corrcoef(metrics['dH'], metrics[k])[0, 1]
        print(f"    corr(dH, {k:>25}): {corr:+.6f}")

    # COMBINATION: find optimal ★-metric as linear combination
    # dH_pred = a · d_state + b · d_carry + c · d_and + d · collision_eq
    X = np.column_stack([metrics[k] for k in metrics if k != 'dH'])
    y = metrics['dH']

    # Least squares
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        y_pred = X @ coeffs
        corr_combined = np.corrcoef(y, y_pred)[0, 1]

        keys = [k for k in metrics if k != 'dH']
        print(f"\n  Optimal ★-metric (linear combination):")
        for k, c in zip(keys, coeffs):
            print(f"    {c:+.4f} × {k}")
        print(f"  Combined correlation with dH: {corr_combined:+.6f}")

        # How much BETTER is the combined metric?
        # Among pairs with low combined metric, what's dH?
        p5_thresh = np.percentile(y_pred, 5)
        low_mask = y_pred <= p5_thresh
        print(f"\n  Low ★-metric (bottom 5%):")
        print(f"    E[dH]: {y[low_mask].mean():.2f} (vs {y.mean():.2f} overall)")
        print(f"    min(dH): {y[low_mask].min():.0f} (vs {y.min():.0f} overall)")

    except Exception as e:
        print(f"  Least squares failed: {e}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 121: NATIVE ★-METHOD")
    print("Build collision search FROM ★-algebra, not borrowed math")
    print("=" * 60)

    test_star_vs_hash_distance(5000)
    test_star_metric_design(8000)

    # Compare ★-walk vs standard walk at 4 rounds
    star_c, star_best = test_star_walk(N=30, max_steps=200, R=4)
    std_c, std_best = test_standard_walk(N=30, max_steps=200, R=4)

    print(f"\n{'='*60}")
    print(f"COMPARISON: ★-WALK vs STANDARD at 4 rounds")
    print(f"  ★-walk: {star_c} collisions, best dH = {star_best}")
    print(f"  Standard: {std_c} collisions, best dH = {std_best}")

    if star_best < std_best:
        gain = std_best - star_best
        print(f"  ★-WALK IS {gain} BITS BETTER!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
