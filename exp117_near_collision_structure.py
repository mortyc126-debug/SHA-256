#!/usr/bin/env python3
"""
EXP 117: Near-Collision Structure — Do close pairs have common features?

We can't find real collisions (dH=0). But we CAN find near-collisions
(dH < 100). If they have shared structure → that structure is the SHADOW
of the collision manifold.

STANDARD METHOD: study near-collisions as random deviations.
★-METHOD: study near-collisions through ★-algebra decomposition.

Look for:
1. Which MESSAGE properties correlate with low dH?
2. Which STATE properties (carry, GKP) correlate with low dH?
3. Do near-collision pairs cluster in ★-space?
4. Is there a "direction" in message space that points toward collision?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def collect_near_collisions(N_pairs=500000, threshold=105):
    """Collect pairs with dH < threshold."""
    print(f"\n--- COLLECTING NEAR-COLLISIONS (N={N_pairs}, thresh={threshold}) ---")

    near = []  # (M1, M2, H1, H2, dH)
    all_dH = []
    t0 = time.time()

    for i in range(N_pairs):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        all_dH.append(dH)

        if dH < threshold:
            near.append((M1, M2, H1, H2, dH))

    t1 = time.time()
    da = np.array(all_dH)
    print(f"  Time: {t1-t0:.1f}s")
    print(f"  E[dH] = {da.mean():.2f}, std = {da.std():.2f}")
    print(f"  Min dH = {da.min()}")
    print(f"  Near-collisions (dH < {threshold}): {len(near)}")

    # Distribution tail
    for t in [120, 115, 110, 105, 100, 95, 90]:
        n = np.sum(da < t)
        if n > 0:
            print(f"    dH < {t}: {n} ({n/N_pairs:.6f})")

    return near, da

def analyze_message_properties(near, control_pairs):
    """What MESSAGE properties correlate with low dH?"""
    print(f"\n--- MESSAGE PROPERTIES OF NEAR-COLLISIONS ---")

    def msg_features(M1, M2):
        """Extract features of a message pair."""
        # XOR distance
        xor_dist = sum(hw(M1[i] ^ M2[i]) for i in range(16))
        # Arithmetic distance (mod 2^32)
        arith_dist = sum(min((M1[i] - M2[i]) & MASK, (M2[i] - M1[i]) & MASK)
                        for i in range(16))
        # Carry similarity in message additions
        carry_sim = sum(hw(carry_word(M1[i], M2[i])) for i in range(16))
        # Schedule diff weight
        S1 = schedule(M1); S2 = schedule(M2)
        sched_diff = sum(hw(S1[t] ^ S2[t]) for t in range(64))
        # GKP propagate count (message word 0 + IV[0])
        gkp1 = carry_gkp_classification(IV[0], M1[0])
        gkp2 = carry_gkp_classification(IV[0], M2[0])
        nP_diff = abs(gkp1.count('P') - gkp2.count('P'))

        return {
            'xor_dist': xor_dist,
            'arith_dist_log': math.log2(arith_dist + 1),
            'carry_sim': carry_sim,
            'sched_diff': sched_diff,
            'nP_diff': nP_diff,
        }

    # Compute features for near-collisions
    near_features = [msg_features(M1, M2) for M1, M2, _, _, _ in near[:500]]
    ctrl_features = [msg_features(M1, M2) for M1, M2, _, _, _ in control_pairs[:500]]

    keys = list(near_features[0].keys())
    print(f"  {'Feature':>20} | {'Near-coll':>10} | {'Random':>10} | {'Diff':>8} | {'Signal?'}")
    print(f"  " + "-" * 65)

    for key in keys:
        near_vals = np.array([f[key] for f in near_features])
        ctrl_vals = np.array([f[key] for f in ctrl_features])
        diff = near_vals.mean() - ctrl_vals.mean()
        pooled_std = math.sqrt((near_vals.std()**2 + ctrl_vals.std()**2) / 2)
        z = diff / (pooled_std / math.sqrt(min(len(near_vals), len(ctrl_vals)))) if pooled_std > 0 else 0
        sig = "***" if abs(z) > 3 else ""
        print(f"  {key:>20} | {near_vals.mean():>10.2f} | {ctrl_vals.mean():>10.2f} | {diff:>+8.2f} | {sig}")

def analyze_star_properties(near, control_pairs):
    """★-algebra properties of near-collisions."""
    print(f"\n--- ★-ALGEBRA PROPERTIES OF NEAR-COLLISIONS ---")

    def star_features(M1, M2, H1, H2):
        """★-space features of a colliding pair."""
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

        # δα = state XOR diff (after 64 rounds, before feedforward)
        delta_alpha = [s1[64][w] ^ s2[64][w] for w in range(8)]
        hw_alpha = sum(hw(d) for d in delta_alpha)

        # δC = carry diff in feedforward
        delta_carry = [carry_word(IV[w], s1[64][w]) ^ carry_word(IV[w], s2[64][w])
                      for w in range(8)]
        hw_carry = sum(hw(d) for d in delta_carry)

        # ★-distance: both components of ★(IV, state)
        star_xor_diff = [((IV[w] ^ s1[64][w]) ^ (IV[w] ^ s2[64][w])) for w in range(8)]
        star_and_diff = [((IV[w] & s1[64][w]) ^ (IV[w] & s2[64][w])) for w in range(8)]
        hw_star_xor = sum(hw(d) for d in star_xor_diff)
        hw_star_and = sum(hw(d) for d in star_and_diff)

        # Collision equation check: δH = δα ⊕ 2·δC (shifted)
        # How close is δα to δC?
        alpha_carry_overlap = sum(hw(delta_alpha[w] & delta_carry[w]) for w in range(8))

        # GKP structure of feedforward
        total_P = 0
        for w in range(8):
            gkp = carry_gkp_classification(IV[w], s1[64][w])
            total_P += gkp.count('P')

        return {
            'hw_delta_alpha': hw_alpha,
            'hw_delta_carry': hw_carry,
            'hw_star_xor': hw_star_xor,
            'hw_star_and': hw_star_and,
            'alpha_carry_overlap': alpha_carry_overlap,
            'feedforward_nP': total_P,
        }

    near_feats = [star_features(M1, M2, H1, H2) for M1, M2, H1, H2, _ in near[:300]]

    # Control: random pairs with dH ≈ 128
    ctrl_feats = []
    for M1, M2, H1, H2, _ in control_pairs[:300]:
        ctrl_feats.append(star_features(M1, M2, H1, H2))

    keys = list(near_feats[0].keys())
    print(f"  {'★-Feature':>25} | {'Near-coll':>10} | {'Random':>10} | {'Diff':>8} | {'Signal?'}")
    print(f"  " + "-" * 70)

    for key in keys:
        near_vals = np.array([f[key] for f in near_feats])
        ctrl_vals = np.array([f[key] for f in ctrl_feats])
        diff = near_vals.mean() - ctrl_vals.mean()
        pooled_std = math.sqrt((near_vals.std()**2 + ctrl_vals.std()**2) / 2)
        n = min(len(near_vals), len(ctrl_vals))
        z = diff / (pooled_std / math.sqrt(n)) if pooled_std > 0 else 0
        sig = "***" if abs(z) > 3 else ""
        print(f"  {key:>25} | {near_vals.mean():>10.2f} | {ctrl_vals.mean():>10.2f} | {diff:>+8.2f} | Z={z:+.1f} {sig}")

def analyze_direction_to_collision(near):
    """Is there a 'direction' in message space pointing toward collision?"""
    print(f"\n--- DIRECTION TO COLLISION IN ★-SPACE ---")

    if len(near) < 20:
        print(f"  Not enough near-collisions ({len(near)})")
        return

    # For each near-collision pair (M1, M2):
    # Compute δM = M1 ⊕ M2 (message XOR difference)
    # If near-collisions share a common δM structure → direction exists

    delta_Ms = []
    dHs = []
    for M1, M2, H1, H2, dH in near[:200]:
        dM = [M1[i] ^ M2[i] for i in range(16)]
        delta_Ms.append(dM)
        dHs.append(dH)

    # Are certain message word differences more common in near-collisions?
    dm_array = np.array(delta_Ms)

    # Per-word Hamming weight of message diff
    per_word_hw = np.array([[hw(dm_array[i, w]) for w in range(16)]
                           for i in range(len(dm_array))])

    print(f"  Per-word HW(δM) for near-collisions (random ≈ 16.0):")
    for w in range(16):
        mean_hw = per_word_hw[:, w].mean()
        print(f"    W[{w:>2}]: {mean_hw:.2f}", end="")
        if abs(mean_hw - 16.0) > 0.5:
            print(f" ← deviation!", end="")
        print()

    # PCA on δM: is there a low-dimensional structure?
    # Flatten δM to bit vectors
    bit_vecs = np.zeros((len(delta_Ms), 512))
    for i, dM in enumerate(delta_Ms):
        for w in range(16):
            for b in range(32):
                bit_vecs[i, w*32 + b] = (dM[w] >> b) & 1

    bit_vecs_centered = bit_vecs - bit_vecs.mean(axis=0)
    try:
        _, sigma, _ = np.linalg.svd(bit_vecs_centered, full_matrices=False)
        cumvar = np.cumsum(sigma**2) / np.sum(sigma**2)
        dim95 = np.searchsorted(cumvar, 0.95) + 1
        dim99 = np.searchsorted(cumvar, 0.99) + 1
        print(f"\n  PCA on δM of near-collisions:")
        print(f"    95% variance: {dim95} dimensions (of 512)")
        print(f"    99% variance: {dim99} dimensions")
        print(f"    σ₁/σ_last: {sigma[0]/sigma[min(len(sigma)-1, 200)]:.2f}")

        if dim95 < 400:
            print(f"    *** LOW-DIMENSIONAL STRUCTURE IN δM! ***")
        else:
            print(f"    No dimensional reduction (δM is unstructured)")
    except:
        print(f"    SVD failed (not enough samples)")

    # Correlation between dH and specific δM bits
    dH_arr = np.array(dHs[:len(bit_vecs)])
    top_corrs = []
    for bit in range(512):
        if bit_vecs[:, bit].std() > 0:
            c = np.corrcoef(bit_vecs[:, bit], dH_arr)[0, 1]
            if not np.isnan(c):
                top_corrs.append((abs(c), bit, c))

    top_corrs.sort(reverse=True)
    print(f"\n  Top message bits correlated with dH:")
    for ac, bit, c in top_corrs[:10]:
        w = bit // 32; b = bit % 32
        print(f"    W[{w}] bit {b}: corr = {c:+.4f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 117: NEAR-COLLISION STRUCTURE")
    print("Do pairs with low dH share hidden properties?")
    print("=" * 60)

    near, all_dH = collect_near_collisions(300000, threshold=108)

    # Generate control pairs (random, dH ≈ 128)
    control = []
    for _ in range(500):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        control.append((M1, M2, H1, H2, dH))

    if len(near) > 10:
        analyze_message_properties(near, control)
        analyze_star_properties(near, control)
        analyze_direction_to_collision(near)
    else:
        print(f"\nNot enough near-collisions. Lowering threshold...")
        near, _ = collect_near_collisions(300000, threshold=115)
        if len(near) > 10:
            analyze_message_properties(near, control)
            analyze_star_properties(near, control)
            analyze_direction_to_collision(near)

    print(f"\n{'='*60}")
    print(f"VERDICT: Near-collision structure")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
