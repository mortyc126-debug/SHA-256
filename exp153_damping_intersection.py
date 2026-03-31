#!/usr/bin/env python3
"""
EXP 153: DAMPING ∩ MESSAGE — The Critical Intersection

V_damp = 103-dim subspace where differences SHRINK (σ < 1)
V_msg  = 256-dim image of message space in state space

dim(V_damp ∩ V_msg) = ?

If > 0: message differences exist that DAMP through rounds → collision shortcut
If = 0: SHA-256 designed so damping is unreachable → 2^128 is tight

THIS IS THE DECISIVE COMPUTATION.
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

def compute_message_jacobian(M_base, R=1):
    """Jacobian: how message bits affect state at round R.
    Returns 256×512 matrix (state_bits × message_bits)."""
    s_base = sha256_rounds(M_base, R)[R]

    J = np.zeros((256, 512), dtype=float)
    for j in range(512):
        w_msg = j // 32; b_msg = j % 32
        M_pert = list(M_base)
        M_pert[w_msg] ^= (1 << b_msg)
        s_pert = sha256_rounds(M_pert, R)[R]

        for i in range(256):
            w_s = i // 32; b_s = i % 32
            J[i, j] = ((s_base[w_s] ^ s_pert[w_s]) >> b_s) & 1

    return J

def find_intersection(N=10):
    """Find dim(V_damp ∩ V_msg)."""
    print(f"\n{'='*60}")
    print(f"CRITICAL INTERSECTION: V_damp ∩ V_msg")
    print(f"{'='*60}")

    all_intersections = []

    for trial in range(N):
        t0 = time.time()
        M = random_w16()
        states = sha256_rounds(M, 64)
        W = schedule(M)

        # Step 1: Compute attack matrix at round 0
        A = compute_attack_matrix(states[0], W[0], K[0])
        U, sigma, Vt = np.linalg.svd(A)

        # Step 2: Identify damping subspace (σ < 1)
        damp_mask = sigma < 1.0
        n_damp = np.sum(damp_mask)

        # Damping basis vectors (right singular vectors with σ < 1)
        V_damp = Vt[damp_mask].T  # 256 × n_damp

        # Step 3: Compute message Jacobian at round 0
        # How does each message bit affect state at round 1?
        J = compute_message_jacobian(M, R=1)

        # V_msg = column space of J (image of messages in state space)
        # = range(J)
        rank_J = np.linalg.matrix_rank(J)

        # Step 4: Find intersection dimension
        # V_damp ∩ V_msg = ?
        # Method: project V_damp onto V_msg and find rank
        # Intersection dim = rank(V_damp) + rank(V_msg) - rank([V_damp | V_msg])
        combined = np.hstack([V_damp, J])  # 256 × (n_damp + 512)
        rank_combined = np.linalg.matrix_rank(combined, tol=0.1)

        intersection_dim = n_damp + rank_J - rank_combined

        t1 = time.time()
        print(f"\n  Trial {trial} ({t1-t0:.1f}s):")
        print(f"    dim(V_damp) = {n_damp}")
        print(f"    rank(V_msg) = {rank_J}")
        print(f"    rank(combined) = {rank_combined}")
        print(f"    dim(V_damp ∩ V_msg) = {intersection_dim}")

        if intersection_dim > 0:
            print(f"    ★★★ INTERSECTION IS {intersection_dim}-DIMENSIONAL!")

        all_intersections.append(intersection_dim)

    avg_dim = np.mean(all_intersections)
    print(f"\n  SUMMARY:")
    print(f"    Average intersection dimension: {avg_dim:.1f}")
    print(f"    Min: {min(all_intersections)}")
    print(f"    Max: {max(all_intersections)}")

    if avg_dim > 0:
        print(f"\n  ★★★ DAMPING MODES ARE REACHABLE FROM MESSAGE SPACE!")
        print(f"    {avg_dim:.0f}-dimensional intersection")
        print(f"    → {avg_dim:.0f} message-controllable damping directions")
    else:
        print(f"\n  Damping modes are ORTHOGONAL to message space")
        print(f"  SHA-256 blocks this attack by design")

    return all_intersections

def find_damping_messages(N=5):
    """If intersection exists: find ACTUAL message differences in damping subspace."""
    print(f"\n{'='*60}")
    print(f"FINDING DAMPING MESSAGE DIFFERENCES")
    print(f"{'='*60}")

    for trial in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)
        W = schedule(M)

        # Attack matrix
        A = compute_attack_matrix(states[0], W[0], K[0])
        U, sigma, Vt = np.linalg.svd(A)

        # Damping vectors (σ < 0.5 for stronger damping)
        strong_damp = sigma < 0.5
        n_strong = np.sum(strong_damp)

        if n_strong == 0:
            print(f"  Trial {trial}: no strong damping modes")
            continue

        V_damp_strong = Vt[strong_damp].T  # 256 × n_strong

        # Message Jacobian
        J = compute_message_jacobian(M, R=1)

        # Find message direction closest to damping subspace
        # Solve: J · δm ≈ V_damp · α (message diff maps to damping direction)
        # This is: minimize ||J·δm - V_damp·α||

        # Simple approach: for each damping vector, find closest message vector
        best_alignment = 0
        best_damp_idx = -1
        best_msg_dir = None

        for d_idx in range(min(n_strong, 20)):
            v_d = V_damp_strong[:, d_idx]  # One damping vector

            # Project v_d onto column space of J
            # projection = J · (J^T · J)^(-1) · J^T · v_d
            JtJ = J.T @ J
            try:
                JtJ_inv = np.linalg.pinv(JtJ)
                proj_coeffs = JtJ_inv @ (J.T @ v_d)
                projection = J @ proj_coeffs
                alignment = np.dot(projection, v_d) / (np.linalg.norm(projection) * np.linalg.norm(v_d) + 1e-10)

                if alignment > best_alignment:
                    best_alignment = alignment
                    best_damp_idx = d_idx
                    best_msg_dir = proj_coeffs
            except:
                continue

        print(f"\n  Trial {trial}:")
        print(f"    Strong damping modes: {n_strong}")
        print(f"    Best alignment with message space: {best_alignment:.6f}")
        print(f"    (1.0 = perfectly reachable, 0.0 = orthogonal)")

        if best_alignment > 0.5:
            print(f"    ★★★ DAMPING DIRECTION IS {best_alignment*100:.0f}% REACHABLE!")

            # Convert message direction to actual δM
            if best_msg_dir is not None:
                # Threshold to binary
                delta_M = [0] * 16
                for j in range(512):
                    if abs(best_msg_dir[j]) > 0.3:
                        w = j // 32; b = j % 32
                        delta_M[w] ^= (1 << b)

                hw_delta = sum(hw(d) for d in delta_M)
                print(f"    δM weight: {hw_delta} bits")

                # TEST: apply this δM and track through rounds
                M2 = [(M[w] ^ delta_M[w]) for w in range(16)]
                if M2 != M:
                    s1_all = sha256_rounds(M, 64)
                    s2_all = sha256_rounds(M2, 64)

                    print(f"    Differential trajectory:")
                    for r in [1, 2, 4, 8, 16, 32, 64]:
                        dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(8))
                        print(f"      Round {r:>2}: dH = {dH}")

        elif best_alignment > 0.1:
            print(f"    Partial alignment ({best_alignment*100:.0f}%)")
        else:
            print(f"    Damping is unreachable from message space")

def test_multi_round_intersection(N=5):
    """Intersection for multi-round attack matrix product."""
    print(f"\n{'='*60}")
    print(f"MULTI-ROUND DAMPING INTERSECTION")
    print(f"{'='*60}")

    for n_rounds in [1, 2, 4]:
        dims = []
        alignments = []

        for trial in range(N):
            M = random_w16()
            states = sha256_rounds(M, n_rounds)
            W = schedule(M)

            # Product of attack matrices
            T = np.eye(256)
            for r in range(n_rounds):
                A = compute_attack_matrix(states[r], W[r], K[r])
                T = A @ T

            U, sigma, Vt = np.linalg.svd(T)
            damp_mask = sigma < 1.0
            n_damp = np.sum(damp_mask)

            # Message Jacobian at round n_rounds
            J = compute_message_jacobian(M, R=n_rounds)
            rank_J = np.linalg.matrix_rank(J, tol=0.1)

            if n_damp > 0:
                V_damp = Vt[damp_mask].T
                combined = np.hstack([V_damp, J])
                rank_comb = np.linalg.matrix_rank(combined, tol=0.1)
                inter_dim = n_damp + rank_J - rank_comb
            else:
                inter_dim = 0

            dims.append(inter_dim)

            # Alignment
            if n_damp > 0:
                v_d = Vt[-1]  # Most damped
                proj = J @ np.linalg.pinv(J.T @ J) @ (J.T @ v_d)
                align = np.dot(proj, v_d) / (np.linalg.norm(proj) * np.linalg.norm(v_d) + 1e-10)
                alignments.append(align)

        avg_dim = np.mean(dims)
        avg_align = np.mean(alignments) if alignments else 0

        print(f"\n  {n_rounds} rounds:")
        print(f"    Avg dim(V_damp ∩ V_msg) = {avg_dim:.1f}")
        print(f"    Avg alignment = {avg_align:.4f}")

        if avg_dim > 0:
            print(f"    ★★★ {avg_dim:.0f}-dim intersection at {n_rounds} rounds!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 153: THE CRITICAL INTERSECTION")
    print("Can damping be reached from message space?")
    print("=" * 60)

    intersections = find_intersection(N=8)
    find_damping_messages(N=5)
    test_multi_round_intersection(N=5)

    print(f"\n{'='*60}")
    print(f"FINAL VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
