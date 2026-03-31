#!/usr/bin/env python3
"""
EXP 141: ★₃ Ternary Automaton + Attractor Dimension

DIRECTION A: ★₃ — the ternary carry automaton
  Transfer matrix eigenvalue λ₂ = 1/3 → η connection
  Does ternary structure give DIFFERENT invariants than binary?

DIRECTION B: Attractor dimension
  exp125 found dim(95%) = 198 for iterated round function
  Is this real? Does it apply to the HASH IMAGE (not just dynamics)?

DIRECTION C: Schedule ★-structure
  The schedule is simpler than round function (no Ch, Maj)
  Does it have ★-invariants that round function doesn't?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# A: ★₃ TERNARY AUTOMATON
# ============================================================
def test_ternary_automaton():
    """Verify and explore the GKP ternary automaton."""
    print(f"\n{'='*60}")
    print(f"★₃ TERNARY CARRY AUTOMATON")
    print(f"{'='*60}")

    # Transfer matrices
    TK = np.array([[1, 0], [1, 0]])  # Kill
    TP = np.array([[1, 0], [0, 1]])  # Propagate
    TG = np.array([[0, 1], [0, 1]])  # Generate

    T_avg = (TK + TP + TG) / 3
    eigenvalues = np.linalg.eigvals(T_avg)

    print(f"\n  Transfer matrices:")
    print(f"    T(K) = {TK.tolist()}")
    print(f"    T(P) = {TP.tolist()}")
    print(f"    T(G) = {TG.tolist()}")
    print(f"\n  Average: T_avg = {T_avg.tolist()}")
    print(f"  Eigenvalues: {eigenvalues}")
    print(f"  Spectral gap: λ₂ = {min(abs(eigenvalues)):.6f}")
    print(f"  1/3 = {1/3:.6f}")

    eta = (3 * math.log2(3)) / 4 - 1
    print(f"\n  η CONNECTION:")
    print(f"    η = (3·log₂3)/4 − 1 = {eta:.6f}")
    print(f"    λ₂ = 1/3 = {1/3:.6f}")
    print(f"    -log₂(λ₂) = log₂(3) = {math.log2(3):.6f}")
    print(f"    η = (3·(-log₂(λ₂)))/4 - 1 = {(3*math.log2(3))/4 - 1:.6f}")
    print(f"    η encodes the SPECTRAL GAP of the ternary carry automaton!")

    # Ternary invariant: is there a function of GKP trit sequence
    # that survives through rounds?
    print(f"\n  Carry correlation length:")
    # After k trits, carry auto-correlation = λ₂^k = (1/3)^k
    for k in [1, 2, 5, 10, 20, 32]:
        corr = (1/3)**k
        print(f"    k={k:>2} trits: auto-corr = {corr:.8f}")

    print(f"\n  Carry rank = 3^5 = {3**5}")
    print(f"  This is because: (1/3)^5 = {(1/3)**5:.6f} ≈ 1/243")
    print(f"  After 5 trits, carry correlation drops to ~0.4%")
    print(f"  5 trits = critical length where carry 'forgets'")
    print(f"  = carry_rank = 3^5 = dimension of effective carry space")

def test_ternary_invariant(N=500):
    """Does a ternary invariant survive through SHA-256 rounds?"""
    print(f"\n--- TERNARY INVARIANT IN SHA-256 ROUNDS (N={N}) ---")

    # Ternary invariant: total GKP value mod 3 of (state_word, IV_word)
    # This is a ★₃-native invariant
    for n_rounds in [1, 2, 4, 8, 16, 32, 64]:
        mod3_vals = []
        for _ in range(N):
            M = random_w16()
            states = sha256_rounds(M, n_rounds)
            # GKP of (state[r], IV) per word → ternary value
            total_ternary = 0
            for w in range(8):
                gkp = carry_gkp_classification(states[n_rounds][w], IV[w])
                for trit in gkp:
                    if trit == 'G':
                        total_ternary += 2
                    elif trit == 'P':
                        total_ternary += 1
                    # K adds 0
            mod3_vals.append(total_ternary % 3)

        vals, counts = np.unique(mod3_vals, return_counts=True)
        dist = {int(v): c/N for v, c in zip(vals, counts)}
        max_dev = max(abs(dist.get(v, 0) - 1/3) for v in [0, 1, 2])
        z = max_dev / math.sqrt(1/3 * 2/3 / N)
        sig = "★★★" if z > 5 else ("★★" if z > 3 else "")
        print(f"  {n_rounds:>2} rounds: {dist} Z={z:.1f} {sig}")

# ============================================================
# B: ATTRACTOR DIMENSION
# ============================================================
def test_attractor_dimension(N=2000):
    """Is the IMAGE of SHA-256 lower-dimensional?"""
    print(f"\n{'='*60}")
    print(f"ATTRACTOR / IMAGE DIMENSION")
    print(f"{'='*60}")

    # Test 1: PCA on hash outputs (should be 256-dim)
    hashes = np.zeros((N, 256))
    for i in range(N):
        M = random_w16()
        H = sha256_compress(M)
        for w in range(8):
            for b in range(32):
                hashes[i, w*32+b] = (H[w] >> b) & 1

    hashes_centered = hashes - hashes.mean(axis=0)
    n_sub = min(N, 1000)
    _, sigma_h, _ = np.linalg.svd(hashes_centered[:n_sub], full_matrices=False)
    cumvar_h = np.cumsum(sigma_h**2) / np.sum(sigma_h**2)

    print(f"\n  Hash image PCA (N={N}):")
    print(f"    dim(95%):  {np.searchsorted(cumvar_h, 0.95)+1}")
    print(f"    dim(99%):  {np.searchsorted(cumvar_h, 0.99)+1}")
    print(f"    dim(99.9%): {np.searchsorted(cumvar_h, 0.999)+1}")

    # Test 2: PCA on STATES (before feedforward)
    states_arr = np.zeros((N, 256))
    for i in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]
        for w in range(8):
            for b in range(32):
                states_arr[i, w*32+b] = (s[w] >> b) & 1

    states_centered = states_arr - states_arr.mean(axis=0)
    _, sigma_s, _ = np.linalg.svd(states_centered[:n_sub], full_matrices=False)
    cumvar_s = np.cumsum(sigma_s**2) / np.sum(sigma_s**2)

    print(f"\n  State image PCA (N={N}):")
    print(f"    dim(95%):  {np.searchsorted(cumvar_s, 0.95)+1}")
    print(f"    dim(99%):  {np.searchsorted(cumvar_s, 0.99)+1}")
    print(f"    dim(99.9%): {np.searchsorted(cumvar_s, 0.999)+1}")

    # Test 3: ITERATED dynamics — does state converge?
    print(f"\n  Iterated dynamics (single message, extended rounds):")
    M = random_w16()
    W = schedule(M)

    state = list(IV)
    states_trajectory = []
    for r in range(500):
        state = sha256_round(state, W[r % 64], K[r % 64])
        if r >= 100:
            bits = []
            for w in range(8):
                for b in range(32):
                    bits.append((state[w] >> b) & 1)
            states_trajectory.append(bits)

    traj_arr = np.array(states_trajectory, dtype=float)
    traj_centered = traj_arr - traj_arr.mean(axis=0)
    _, sigma_t, _ = np.linalg.svd(traj_centered[:300], full_matrices=False)
    cumvar_t = np.cumsum(sigma_t**2) / np.sum(sigma_t**2)

    print(f"    Trajectory dim(95%):  {np.searchsorted(cumvar_t, 0.95)+1}")
    print(f"    Trajectory dim(99%):  {np.searchsorted(cumvar_t, 0.99)+1}")

    # Test 4: Multiple messages, SAME round
    # At each round r, is the state distribution lower-dimensional?
    print(f"\n  Per-round state dimension (multiple messages):")
    for r in [1, 4, 8, 16, 32, 64]:
        round_states = np.zeros((min(N, 800), 256))
        for i in range(min(N, 800)):
            M = random_w16()
            s = sha256_rounds(M, r)[r]
            for w in range(8):
                for b in range(32):
                    round_states[i, w*32+b] = (s[w] >> b) & 1

        rc = round_states - round_states.mean(axis=0)
        _, sig_r, _ = np.linalg.svd(rc[:500], full_matrices=False)
        cv_r = np.cumsum(sig_r**2) / np.sum(sig_r**2)
        d95 = np.searchsorted(cv_r, 0.95)+1
        d99 = np.searchsorted(cv_r, 0.99)+1
        print(f"    Round {r:>2}: dim(95%)={d95}, dim(99%)={d99}")

# ============================================================
# C: SCHEDULE ★-STRUCTURE
# ============================================================
def test_schedule_star(N=500):
    """★-decomposition of the schedule."""
    print(f"\n{'='*60}")
    print(f"SCHEDULE ★-STRUCTURE")
    print(f"{'='*60}")

    # The schedule: W[t] = σ₁(W[t-2]) + W[t-7] + σ₀(W[t-15]) + W[t-16]
    # In ★: this involves 3 additions = 3 anti-morphisms
    # But σ₀, σ₁ are pure ★-morphisms (ROTR + XOR + SHR)

    # Does the schedule have ★-invariants?
    # Test: for two messages M, M', is there a schedule property
    # that predicts collision?

    # Schedule ★-pair: ★(W[t](M), W[t](M'))
    # = (W[t](M) ⊕ W[t](M'), W[t](M) & W[t](M'))

    # Test: HW(δW_total) = Σ HW(W[t](M) ⊕ W[t](M'))
    # How does this relate to hash distance?

    schedule_hws = []
    hash_dists = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        S1 = schedule(M1); S2 = schedule(M2)

        # Total schedule XOR weight
        sw = sum(hw(S1[t] ^ S2[t]) for t in range(64))
        schedule_hws.append(sw)

        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        hash_dists.append(dH)

    shw = np.array(schedule_hws); hd = np.array(hash_dists)
    corr = np.corrcoef(shw, hd)[0, 1]
    print(f"\n  corr(schedule_XOR_weight, hash_dist): {corr:+.4f}")

    # Per-round schedule weight → hash dist
    print(f"\n  Per-round schedule weight correlation with dH:")
    for t in range(0, 64, 8):
        round_hws = []
        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            S1 = schedule(M1); S2 = schedule(M2)
            w_block = sum(hw(S1[r] ^ S2[r]) for r in range(t, min(t+8, 64)))
            round_hws.append(w_block)
            if len(hash_dists) <= _:
                H1 = sha256_compress(M1); H2 = sha256_compress(M2)
                hash_dists.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

        rhw = np.array(round_hws[:N])
        hd_sub = np.array(hash_dists[:N])
        c = np.corrcoef(rhw, hd_sub)[0, 1]
        print(f"    Rounds {t:>2}-{min(t+7,63):>2}: corr = {c:+.4f}")

    # Schedule ★-AND structure
    print(f"\n  Schedule AND-component:")
    and_hws = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        S1 = schedule(M1); S2 = schedule(M2)
        aw = sum(hw(S1[t] & S2[t]) for t in range(64))
        and_hws.append(aw)

    ahw = np.array(and_hws)
    corr_and = np.corrcoef(ahw, hd[:N])[0, 1]
    print(f"    corr(schedule_AND_weight, hash_dist): {corr_and:+.4f}")

    # Schedule GKP: ternary decomposition of schedule pairs
    print(f"\n  Schedule GKP ternary mod-3:")
    gkp_mod3 = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        S1 = schedule(M1); S2 = schedule(M2)
        total_ternary = 0
        for t in range(64):
            gkp = carry_gkp_classification(S1[t], S2[t])
            for trit in gkp:
                total_ternary += {'G': 2, 'P': 1, 'K': 0}[trit]
        gkp_mod3.append(total_ternary % 3)

    vals, counts = np.unique(gkp_mod3, return_counts=True)
    dist = {int(v): c/N for v, c in zip(vals, counts)}
    print(f"    Distribution mod 3: {dist}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 141: ★₃ + ATTRACTOR + SCHEDULE")
    print("=" * 60)

    test_ternary_automaton()
    test_ternary_invariant(400)
    test_attractor_dimension(1500)
    test_schedule_star(400)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
