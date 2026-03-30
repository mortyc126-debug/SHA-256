#!/usr/bin/env python3
"""
EXPERIMENT 11: Nullspace Threading via Shift Register

From exp9: {Ψ, Σ₀} has nullspace dim≈4 per round.
Shift register b←a, f←e has τ=∞ (exact).

Question: do nullspaces CONNECT through the shift?
If N_r ∩ shift(N_{r-1}) ≠ ∅ → free thread exists → τ=∞ invariant

4 free dims × 64 rounds = 256 free bits (if coherent).
128 bits needed for collision → 128 bits to spare.

This would be a NEW object: "shift-coherent nullspace fiber".
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def carry_jacobian_at(a, b, n=32):
    """Jacobian of carry(a,b) w.r.t. a, computed by finite differences over GF(2)."""
    J = np.zeros((n, n), dtype=np.float64)
    c_orig = []
    carry_val = 0
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        s = ai + bi + carry_val
        carry_val = 1 if s >= 2 else 0
        c_orig.append(carry_val)

    for j in range(n):
        a_flip = a ^ (1 << j)
        c_new = []
        carry_val = 0
        for i in range(n):
            ai = (a_flip >> i) & 1
            bi = (b >> i) & 1
            s = ai + bi + carry_val
            carry_val = 1 if s >= 2 else 0
            c_new.append(carry_val)
        for i in range(n):
            J[i][j] = float(c_orig[i] ^ c_new[i])
    return J


def sigma0_matrix():
    M = np.zeros((32, 32), dtype=np.float64)
    for i in range(32):
        M[i][(i + 2) % 32] = 1 - M[i][(i + 2) % 32]
        M[i][(i + 13) % 32] = 1 - M[i][(i + 13) % 32]
        M[i][(i + 22) % 32] = 1 - M[i][(i + 22) % 32]
    return M


def sigma1_matrix():
    M = np.zeros((32, 32), dtype=np.float64)
    for i in range(32):
        M[i][(i + 6) % 32] = 1 - M[i][(i + 6) % 32]
        M[i][(i + 11) % 32] = 1 - M[i][(i + 11) % 32]
        M[i][(i + 25) % 32] = 1 - M[i][(i + 25) % 32]
    return M


SIG0 = sigma0_matrix()
SIG1 = sigma1_matrix()


def compute_round_nullspace(state, W_r, K_r):
    """
    Compute nullspace of {Ψ, Σ} for one round.
    Ψ = carry jacobian of the main addition (d + T1 → e_new).
    Σ = Sigma1 (used in T1 computation for e-branch).

    Returns nullspace basis vectors (as columns).
    """
    a, b, c, d, e, f, g, h = state

    T1 = (h + sigma1(e) + ch(e, f, g) + K_r + W_r) & MASK
    Psi = carry_jacobian_at(d, T1)

    # Anti-commutator {Ψ, Σ₁}
    AC = Psi @ SIG1 + SIG1 @ Psi

    # SVD to find nullspace
    U, S, Vt = np.linalg.svd(AC)
    tol = 1e-10
    null_mask = S < tol
    nullspace = Vt[null_mask].T  # columns = null vectors

    return nullspace, AC


def shift_vector_a_to_b(v):
    """
    In SHA-256, b[r+1] = a[r]. At bit level, the a-register bits
    become b-register bits. Within 32-bit words, this is identity on bits.

    For our 32-dim nullspace (single register), the shift is trivial (identity).
    But conceptually, the "same" direction in a at round r is now in b at round r+1.

    The key question: does the nullspace of the NEW round's anti-commutator
    (which operates on the NEW a-register) intersect with the OLD nullspace
    (which now lives in b)?

    Since the new a = T1+T2 depends on old a (through Σ₀, Maj), there IS coupling.

    We need to compute: how much of the old nullspace survives in the new computation.
    """
    return v  # Identity within 32-bit register


def compute_transfer_matrix(state_r, state_r1, W_r, K_r, W_r1, K_r1):
    """
    Compute the transfer matrix T: null(AC_r) → null(AC_{r+1}).

    The differential at round r propagates to round r+1 through:
    δa_{r+1} = δ(T1_r + T2_r) depends on δe_r (through Σ₁, Ch) and δa_r (through Σ₀, Maj)

    T maps how a perturbation in the nullspace at round r affects the
    nullspace projection at round r+1.
    """
    null_r, AC_r = compute_round_nullspace(state_r, W_r, K_r)
    null_r1, AC_r1 = compute_round_nullspace(state_r1, W_r1, K_r1)

    if null_r.shape[1] == 0 or null_r1.shape[1] == 0:
        return None, 0, null_r.shape[1], null_r1.shape[1]

    # Project: for each null vector of round r,
    # compute its image under one round of SHA-256 differential
    # and measure how much of it lies in the nullspace of round r+1

    a, b, c, d, e, f, g, h = state_r
    T1 = (h + sigma1(e) + ch(e, f, g) + K_r + W_r) & MASK

    # Jacobian of a_{r+1} = T1 + T2 with respect to perturbations in a_r
    # δa_{r+1} = δT2 = δΣ₀(a_r) + δMaj(a_r, b_r, c_r)
    # δΣ₀(a_r) = Σ₀ · δa_r (linear)
    # δMaj depends on a_r, b_r, c_r — approximately Maj_jacobian · δa_r

    # For simplicity, compute numerically
    J_a_to_anext = np.zeros((32, 32), dtype=np.float64)

    for j in range(32):
        # Flip bit j of a
        a_flip = a ^ (1 << j)
        T2_orig = (sigma0(a) + maj(a, b, c)) & MASK
        T2_flip = (sigma0(a_flip) + maj(a_flip, b, c)) & MASK
        diff = T2_orig ^ T2_flip
        for i in range(32):
            J_a_to_anext[i][j] = float((diff >> i) & 1)

    # Image of nullspace under the round transition
    image = J_a_to_anext @ null_r  # 32 × dim_null_r

    # Project image onto nullspace of round r+1
    if null_r1.shape[1] > 0:
        # Projection matrix onto null_r1
        P = null_r1 @ np.linalg.pinv(null_r1)
        projected = P @ image

        # Measure overlap: ||projected|| / ||image||
        image_norms = np.linalg.norm(image, axis=0)
        proj_norms = np.linalg.norm(projected, axis=0)

        overlaps = []
        for k in range(image.shape[1]):
            if image_norms[k] > 1e-10:
                overlaps.append(proj_norms[k] / image_norms[k])

        avg_overlap = np.mean(overlaps) if overlaps else 0
    else:
        avg_overlap = 0

    return avg_overlap, null_r.shape[1], null_r1.shape[1]


def test_nullspace_threading(N=200):
    """Main test: do nullspaces thread through rounds?"""
    print("\n--- TEST 1: NULLSPACE DIMENSIONS PER ROUND ---")

    null_dims = {r: [] for r in range(64)}

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        for r in range(64):
            ns, _ = compute_round_nullspace(states[r], W[r], K[r])
            null_dims[r].append(ns.shape[1])

    print(f"{'Round':>5} | {'Mean dim':>9} | {'Min':>4} | {'Max':>4} | {'P(dim≥1)':>9}")
    print("-" * 45)
    for r in [0,1,2,3,4,5,8,16,17,20,32,48,63]:
        dims = null_dims[r]
        mean_d = np.mean(dims)
        p_nonzero = np.mean(np.array(dims) >= 1)
        print(f"{r:>5} | {mean_d:>9.2f} | {min(dims):>4} | {max(dims):>4} | {p_nonzero:>9.3f}")


def test_threading_overlap(N=200):
    """Test: does nullspace at round r overlap with nullspace at round r+1?"""
    print("\n--- TEST 2: NULLSPACE THREADING (OVERLAP) ---")

    overlaps_by_round = {r: [] for r in range(63)}

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        for r in range(63):
            result = compute_transfer_matrix(
                states[r], states[r+1], W[r], K[r], W[r+1], K[r+1]
            )
            if result[0] is not None:
                overlaps_by_round[r].append(result[0])

    print(f"{'Round':>5} | {'Mean overlap':>13} | {'N samples':>9} | {'Signal'}")
    print("-" * 50)

    significant = []
    for r in [0,1,2,3,4,5,8,16,17,20,32,48,62]:
        ov = overlaps_by_round[r]
        if ov:
            mean_ov = np.mean(ov)
            marker = " ***" if mean_ov > 0.3 else ""
            if mean_ov > 0.3:
                significant.append((r, mean_ov))
            print(f"{r:>5} | {mean_ov:>13.6f} | {len(ov):>9} | {marker}")
        else:
            print(f"{r:>5} | {'N/A':>13} | {0:>9} |")

    return significant


def test_thread_length(N=200):
    """Measure: how many consecutive rounds can a nullspace thread survive?"""
    print("\n--- TEST 3: THREAD LENGTH ---")

    thread_lengths = []

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        # Start from round 0
        ns_prev, _ = compute_round_nullspace(states[0], W[0], K[0])
        if ns_prev.shape[1] == 0:
            thread_lengths.append(0)
            continue

        length = 1
        for r in range(1, 64):
            ns_curr, _ = compute_round_nullspace(states[r], W[r], K[r])
            if ns_curr.shape[1] == 0:
                break

            # Check overlap
            result = compute_transfer_matrix(
                states[r-1], states[r], W[r-1], K[r-1], W[r], K[r]
            )
            overlap = result[0] if result[0] is not None else 0

            if overlap > 0.1:  # Thread continues
                length += 1
            else:
                break

        thread_lengths.append(length)

    tl = np.array(thread_lengths)
    print(f"Thread length: mean={tl.mean():.2f}, max={tl.max()}, std={tl.std():.2f}")
    print(f"Distribution:")
    for l in sorted(set(thread_lengths)):
        if l > 20:
            break
        count = sum(1 for x in thread_lengths if x == l)
        bar = "#" * min(count, 50)
        print(f"  {l:>3}: {count:>4} {bar}")

    if tl.max() >= 10:
        print(f"*** SIGNAL: Thread survives {tl.max()} rounds! ***")

    return tl


def test_wang_nullspace_coherence(N=300):
    """
    Under Wang cascade, do nullspaces have better coherence?
    Wang pairs have structured differentials → possibly coherent nullspaces.
    """
    print("\n--- TEST 4: WANG CASCADE NULLSPACE COHERENCE ---")

    wang_overlaps = []
    random_overlaps = []

    for _ in range(N):
        # Wang pair
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)
        W_exp = schedule(Wn)

        # Overlap at barrier (round 16→17)
        result = compute_transfer_matrix(
            states_n[16], states_n[17], W_exp[16], K[16], W_exp[17], K[17]
        )
        if result[0] is not None:
            wang_overlaps.append(result[0])

        # Random comparison
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)
        result = compute_transfer_matrix(
            states[16], states[17], W[16], K[16], W[17], K[17]
        )
        if result[0] is not None:
            random_overlaps.append(result[0])

    if wang_overlaps and random_overlaps:
        wang_mean = np.mean(wang_overlaps)
        rand_mean = np.mean(random_overlaps)
        print(f"Wang overlap at barrier:   {wang_mean:.6f} (N={len(wang_overlaps)})")
        print(f"Random overlap at barrier: {rand_mean:.6f} (N={len(random_overlaps)})")
        print(f"Ratio Wang/Random: {wang_mean/rand_mean:.4f}" if rand_mean > 0 else "")

        if wang_mean > rand_mean * 1.5:
            print("*** SIGNAL: Wang cascade creates better nullspace coherence! ***")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 11: NULLSPACE THREADING VIA SHIFT REGISTER")
    print("=" * 60)

    test_nullspace_threading(150)
    significant = test_threading_overlap(150)
    tl = test_thread_length(150)
    test_wang_nullspace_coherence(200)

    print("\n" + "=" * 60)
    print("FINAL VERDICT")
    print("=" * 60)

    if tl.max() >= 20:
        tau_est = tl.mean()
        print(f"Thread τ = {tau_est:.1f} rounds")
        print(f"If τ >> 1.80: NEW INVARIANT DISCOVERED")
        print(f"Free bits over 64 rounds: ~{4 * min(64, tau_est):.0f}")
    elif significant:
        print(f"Partial threading at {len(significant)} rounds: {significant}")
        print("Insufficient for full attack but structurally interesting")
    else:
        print("No coherent threading. Nullspaces are independent per round.")
        print("Shift register does not connect anti-commutator nullspaces.")

if __name__ == "__main__":
    main()
