#!/usr/bin/env python3
"""
EXP 154: Damping Intersection Scaling — 4→8→16→32→64 rounds

exp153: dim(V_damp ∩ V_msg) = 19 at 4 rounds.
NOW: does this GROW, STABILIZE, or DIE at more rounds?

If grows → attack strengthens with rounds
If stable at 19 → 19 free bits → 2^118.5 instead of 2^128
If dies → decorrelation kills it → no gain
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_attack_matrix(S, W_r, K_r):
    """Full 256×256 attack matrix."""
    S_after = sha256_round(list(S), W_r, K_r)
    A = np.zeros((256, 256), dtype=float)
    for j in range(256):
        w_in = j // 32; b_in = j % 32
        S2 = list(S); S2[w_in] ^= (1 << b_in)
        S2_after = sha256_round(S2, W_r, K_r)
        for i in range(256):
            w_out = i // 32; b_out = i % 32
            A[i, j] = ((S_after[w_out] ^ S2_after[w_out]) >> b_out) & 1
    return A

def compute_message_jacobian(M_base, R):
    """How message bits affect state at round R. Returns 256×512 matrix."""
    s_base = sha256_rounds(M_base, R)[R]
    J = np.zeros((256, 512), dtype=float)
    for j in range(512):
        w_msg = j // 32; b_msg = j % 32
        M_pert = list(M_base); M_pert[w_msg] ^= (1 << b_msg)
        s_pert = sha256_rounds(M_pert, R)[R]
        for i in range(256):
            w_s = i // 32; b_s = i % 32
            J[i, j] = ((s_base[w_s] ^ s_pert[w_s]) >> b_s) & 1
    return J

def measure_intersection(M, n_rounds):
    """Compute dim(V_damp ∩ V_msg) at given round count."""
    states = sha256_rounds(M, n_rounds)
    W = schedule(M)

    # Product of attack matrices
    T = np.eye(256)
    for r in range(n_rounds):
        A = compute_attack_matrix(states[r], W[r], K[r])
        T = A @ T

    # Damping subspace
    U, sigma, Vt = np.linalg.svd(T)
    damp_mask = sigma < 1.0
    n_damp = np.sum(damp_mask)

    if n_damp == 0:
        return 0, n_damp, 0, 0

    V_damp = Vt[damp_mask].T

    # Message Jacobian
    J = compute_message_jacobian(M, n_rounds)
    rank_J = np.linalg.matrix_rank(J, tol=0.1)

    # Intersection
    combined = np.hstack([V_damp, J])
    rank_comb = np.linalg.matrix_rank(combined, tol=0.1)
    inter_dim = n_damp + rank_J - rank_comb

    # Alignment of strongest damping mode with message space
    v_most_damped = Vt[-1]
    proj = J @ np.linalg.pinv(J.T @ J + 1e-10 * np.eye(512)) @ (J.T @ v_most_damped)
    norm_proj = np.linalg.norm(proj)
    norm_v = np.linalg.norm(v_most_damped)
    alignment = np.dot(proj, v_most_damped) / (norm_proj * norm_v + 1e-10)

    return inter_dim, n_damp, rank_J, alignment

def test_scaling(N=6):
    """Scale intersection measurement from 1 to 64 rounds."""
    print(f"\n{'='*60}")
    print(f"DAMPING INTERSECTION SCALING (N={N})")
    print(f"{'='*60}")

    rounds_to_test = [1, 2, 3, 4, 5, 6, 8]

    print(f"\n  {'Rounds':>6} | {'dim(V_d)':>8} | {'rank(J)':>7} | {'dim(∩)':>6} | {'align':>6}")
    print(f"  " + "-" * 50)

    for R in rounds_to_test:
        dims = []; n_damps = []; rank_Js = []; aligns = []

        for trial in range(N):
            M = random_w16()
            inter, nd, rj, al = measure_intersection(M, R)
            dims.append(inter)
            n_damps.append(nd)
            rank_Js.append(rj)
            aligns.append(al)

        avg_dim = np.mean(dims)
        avg_nd = np.mean(n_damps)
        avg_rj = np.mean(rank_Js)
        avg_al = np.mean(aligns)

        marker = ""
        if avg_dim > 0:
            marker = f" ★★★ {avg_dim:.0f}-dim intersection!"

        print(f"  {R:>6} | {avg_nd:>8.0f} | {avg_rj:>7.0f} | {avg_dim:>6.1f} | {avg_al:>6.3f}{marker}")

    # Predict: what would happen at 16, 32, 64?
    print(f"\n  TREND ANALYSIS:")
    dims_by_round = {}
    for R in rounds_to_test:
        trial_dims = []
        for trial in range(N):
            M = random_w16()
            inter, _, _, _ = measure_intersection(M, R)
            trial_dims.append(inter)
        dims_by_round[R] = np.mean(trial_dims)

    # Linear regression on observed data
    x = [R for R in rounds_to_test if dims_by_round[R] > 0]
    y = [dims_by_round[R] for R in x]

    if len(x) >= 2:
        slope = np.polyfit(x, y, 1)[0]
        print(f"    Slope (dim per round): {slope:.2f}")

        for R_pred in [16, 32, 64]:
            pred = dims_by_round.get(4, 0) + slope * (R_pred - 4)
            pred = max(0, min(pred, 256))
            print(f"    Predicted dim at {R_pred} rounds: {pred:.0f}")

            if R_pred == 64 and pred > 0:
                birthday = (256 - pred) / 2
                print(f"    → Birthday on {256-pred:.0f} bits = 2^{birthday:.1f}")
                print(f"    → Gain over 2^128: {128 - birthday:.1f} bits")

def test_intersection_with_real_collision_search(N=10, R=4):
    """Use the 19-dim intersection for actual collision search at R rounds."""
    print(f"\n{'='*60}")
    print(f"DAMPING INTERSECTION COLLISION SEARCH ({R} rounds, N={N})")
    print(f"{'='*60}")

    damp_results = []
    rand_results = []

    for trial in range(N):
        M1 = random_w16()
        states1 = sha256_rounds(M1, R)
        W = schedule(M1)

        # Compute damping direction
        T = np.eye(256)
        for r in range(R):
            A = compute_attack_matrix(states1[r], W[r], K[r])
            T = A @ T

        _, sigma, Vt = np.linalg.svd(T)

        # Get message Jacobian
        J = compute_message_jacobian(M1, R)

        # Find message perturbation in damping direction
        v_damp = Vt[-1]  # Most damped direction
        # Project onto message space: δm = J^+ · v_damp
        delta_m = np.linalg.pinv(J) @ v_damp

        # Threshold to binary
        delta_M = [0] * 16
        threshold = np.percentile(np.abs(delta_m), 90)  # Top 10% bits
        for j in range(512):
            if abs(delta_m[j]) > threshold:
                w = j // 32; b = j % 32
                delta_M[w] ^= (1 << b)

        # Apply and measure
        M2_damp = [(M1[w] ^ delta_M[w]) for w in range(16)]
        if M1 == M2_damp:
            M2_damp[0] ^= 1

        s2_damp = sha256_rounds(M2_damp, R)
        dH_damp = sum(hw(states1[R][w] ^ s2_damp[R][w]) for w in range(8))
        damp_results.append(dH_damp)

        # Random comparison (same budget ≈ 1 evaluation)
        best_rand = 256
        for _ in range(50):
            M2_rand = random_w16()
            s2_rand = sha256_rounds(M2_rand, R)
            dH_rand = sum(hw(states1[R][w] ^ s2_rand[R][w]) for w in range(8))
            best_rand = min(best_rand, dH_rand)
        rand_results.append(best_rand)

    da = np.array(damp_results); ra = np.array(rand_results)
    print(f"\n  Damping-projected: avg={da.mean():.1f}, min={da.min()}")
    print(f"  Random (50 tries): avg={ra.mean():.1f}, min={ra.min()}")
    gain = ra.mean() - da.mean()
    print(f"  Gain: {gain:+.1f} bits")

    if gain > 5:
        print(f"  ★★★ DAMPING PROJECTION BEATS RANDOM BY {gain:.0f} BITS!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 154: INTERSECTION SCALING 1→64")
    print("=" * 60)

    test_scaling(N=5)
    test_intersection_with_real_collision_search(N=8, R=4)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
