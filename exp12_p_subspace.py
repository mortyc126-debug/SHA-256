#!/usr/bin/env python3
"""
EXPERIMENT 12: P-Subspace Linearization

THE CORE IDEA:
SHA-256 is protected because + and ⊕ conflict.
In carry algebra, P-positions (a_i ≠ b_i) are where + ≈ ⊕.
G-positions: carry=1 always. K-positions: carry=0 always.
P-positions: carry depends on carry-in → the ONLY uncertainty.

In the P-subspace, SHA-256 is APPROXIMATELY LINEAR.
If we can work entirely in P-subspace → linear algebra → collision.

METHOD OF ABSTRACTION:
Level -2: Pure P-subspace (+ = ⊕ exactly when carry-in=0)
Level -1: P-subspace with carry noise (+ ≈ ⊕ with probability)
Level  0: Full SHA-256

We solve at Level -2, then lift to Level 0.
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def gkp_classify(a, b, n=32):
    """Classify bit positions: G(both 1), K(both 0), P(differ)."""
    mask_g = a & b          # G positions
    mask_k = ~a & ~b & MASK # K positions
    mask_p = a ^ b          # P positions (XOR=1 means they differ)
    return mask_g, mask_k, mask_p


def p_fraction_addition(a, b):
    """What fraction of bits are P-type in a+b?"""
    _, _, mask_p = gkp_classify(a, b)
    return hw(mask_p) / 32


def add_equals_xor_on_p(a, b):
    """On P-positions, does a+b agree with a⊕b bit-by-bit?"""
    _, _, mask_p = gkp_classify(a, b)
    sum_val = (a + b) & MASK
    xor_val = a ^ b
    # Bits where sum and xor differ
    diff = sum_val ^ xor_val
    # How many P-positions have diff=0?
    agree_on_p = hw(mask_p & ~diff)  # P bits where sum=xor
    total_p = hw(mask_p)
    return agree_on_p, total_p


def test_p_linearity_single_round(N=2000):
    """Test: in P-subspace, does the round function behave linearly?"""
    print("\n--- TEST 1: P-SUBSPACE LINEARITY OF ROUND FUNCTION ---")

    # For each round: compute f(x), f(x+δ), f(x)+f(δ)
    # Linearity means f(x+δ) = f(x) + f(δ) - f(0)
    # In P-subspace: does this hold more often?

    results_by_round = {}

    for r_target in [1, 2, 4, 8, 16, 17, 32, 64]:
        p_linear_scores = []
        full_linear_scores = []

        for _ in range(N):
            W16 = random_w16()
            delta = random.randint(1, 0x1F)  # Small perturbation (bits 0-4)

            W16_d = list(W16)
            W16_d[0] = (W16_d[0] + delta) & MASK

            states_base = sha256_rounds(W16, r_target)
            states_pert = sha256_rounds(W16_d, r_target)

            # Output difference
            e_base = states_base[r_target][4]
            e_pert = states_pert[r_target][4]

            # Actual difference (additive)
            actual_diff = (e_pert - e_base) & MASK

            # XOR difference
            xor_diff = e_pert ^ e_base

            # P-subspace: where do actual_diff and xor_diff agree?
            agree, total_p = add_equals_xor_on_p(e_base, e_pert)
            if total_p > 0:
                p_linear_scores.append(agree / total_p)

            # Full linearity: how close is additive diff to XOR diff?
            full_agree = 32 - hw(actual_diff ^ xor_diff)
            full_linear_scores.append(full_agree / 32)

        mean_p = np.mean(p_linear_scores) if p_linear_scores else 0
        mean_full = np.mean(full_linear_scores) if full_linear_scores else 0
        results_by_round[r_target] = (mean_p, mean_full)

    print(f"{'Rounds':>6} | {'P-linear':>10} | {'Full-linear':>12} | {'Gain':>8} | Signal")
    print("-" * 55)
    for r in sorted(results_by_round.keys()):
        mp, mf = results_by_round[r]
        gain = mp - mf
        marker = " ***" if gain > 0.05 else ""
        print(f"{r:>6} | {mp:>10.6f} | {mf:>12.6f} | {gain:>+8.4f} | {marker}")


def test_p_subspace_rank(N=50):
    """
    Key test: what is the GF(2) rank of SHA-256 restricted to P-subspace?
    If rank < 256 in P-subspace → linear collision exists there.
    """
    print("\n--- TEST 2: P-SUBSPACE RANK OF DIFFERENTIAL MAP ---")

    for num_rounds in [4, 8, 16, 32, 64]:
        ranks = []

        for _ in range(N):
            W16 = random_w16()
            base_states = sha256_rounds(W16, num_rounds)
            base_final = base_states[num_rounds]

            # Build differential matrix restricted to P-subspace
            # For each input bit flip, record output diff ONLY on P-positions
            diff_rows = []

            for word in range(16):
                for bit in range(32):
                    W_pert = list(W16)
                    W_pert[word] ^= (1 << bit)
                    pert_states = sha256_rounds(W_pert, num_rounds)
                    pert_final = pert_states[num_rounds]

                    # Output XOR difference
                    row = []
                    for w in range(8):
                        d = base_final[w] ^ pert_final[w]
                        # Identify P-positions for this output word pair
                        _, _, mask_p = gkp_classify(base_final[w], pert_final[w])

                        for b in range(32):
                            if (mask_p >> b) & 1:
                                row.append((d >> b) & 1)
                            # Skip non-P positions

                    diff_rows.append(row)

            # Variable-length rows (different P-subspace sizes)
            # Pad/truncate to uniform length
            if not diff_rows:
                continue

            max_len = max(len(r) for r in diff_rows)
            min_len = min(len(r) for r in diff_rows)

            if min_len == 0:
                continue

            # Use min_len (intersection of P-subspaces)
            matrix = np.array([r[:min_len] for r in diff_rows], dtype=np.int64)

            # GF(2) rank
            rank = gf2_rank(matrix)
            ranks.append((rank, min_len))

        if ranks:
            avg_rank = np.mean([r for r, _ in ranks])
            avg_dim = np.mean([d for _, d in ranks])
            deficit = avg_dim - avg_rank

            marker = " ***" if deficit > 5 else ""
            print(f"  R={num_rounds:>2}: avg_rank={avg_rank:.1f}, P-dim={avg_dim:.1f}, "
                  f"deficit={deficit:.1f}{marker}")


def gf2_rank(M):
    """GF(2) rank via Gaussian elimination."""
    A = M.copy() % 2
    m, n = A.shape
    rank = 0
    for col in range(n):
        pivot = -1
        for row in range(rank, m):
            if A[row, col] % 2 == 1:
                pivot = row
                break
        if pivot == -1:
            continue
        A[[rank, pivot]] = A[[pivot, rank]]
        for row in range(m):
            if row != rank and A[row, col] % 2 == 1:
                A[row] = (A[row] + A[rank]) % 2
        rank += 1
    return rank


def test_p_subspace_collision(N=5000):
    """
    Search for P-subspace collisions: pairs where the output
    differs ONLY on G/K positions (not on P positions).

    A P-subspace collision means: on the uncertain bits, the outputs match.
    The remaining (G/K) bits are deterministic — potentially fixable.
    """
    print("\n--- TEST 3: P-SUBSPACE COLLISION SEARCH ---")

    p_match_counts = []  # How many P-bits match in output

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)

        # For each output word: identify P-positions and check match
        total_p_match = 0
        total_p_bits = 0

        for w in range(8):
            _, _, mask_p = gkp_classify(H_n[w], H_f[w])
            diff = H_n[w] ^ H_f[w]

            # P-bits that MATCH (diff=0 on P-positions)
            p_match = hw(mask_p & ~diff)
            total_p_match += p_match
            total_p_bits += hw(mask_p)

        if total_p_bits > 0:
            p_match_counts.append(total_p_match / total_p_bits)

    arr = np.array(p_match_counts)
    print(f"P-bit match rate: mean={arr.mean():.6f}, std={arr.std():.6f}")
    print(f"Expected (random): 0.500000")
    print(f"Best P-match: {arr.max():.6f}")

    # Is P-match rate different from 0.5?
    z_score = (arr.mean() - 0.5) / (arr.std() / np.sqrt(len(arr)))
    print(f"Z-score vs random: {z_score:.4f}")

    if abs(z_score) > 3:
        print("*** SIGNAL: P-subspace match rate differs from random! ***")


def test_adaptive_p_subspace(N=2000):
    """
    The P-subspace is MESSAGE-DEPENDENT.
    Can we CHOOSE messages to maximize the P-subspace overlap
    between consecutive rounds?

    Strategy: search for messages where P-fraction is unusually high
    across all 7 additions in each round.
    """
    print("\n--- TEST 4: ADAPTIVE P-SUBSPACE MAXIMIZATION ---")

    p_fractions = []

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        total_p = 0
        total_bits = 0

        for r in range(64):
            a, b, c, d, e, f, g, h = states[r]
            T1 = (h + sigma1(e) + ch(e, f, g) + K[r] + W[r]) & MASK
            T2 = (sigma0(a) + maj(a, b, c)) & MASK

            # P-fraction for each addition
            additions = [
                (h, sigma1(e)),
                ((h + sigma1(e)) & MASK, ch(e, f, g)),
                (((h + sigma1(e) + ch(e, f, g)) & MASK), K[r]),
                ((((h + sigma1(e) + ch(e, f, g) + K[r]) & MASK)), W[r]),
                (sigma0(a), maj(a, b, c)),
                (T1, T2),
                (d, T1),
            ]

            for x, y in additions:
                pf = p_fraction_addition(x, y)
                total_p += pf * 32
                total_bits += 32

        p_fractions.append(total_p / total_bits)

    arr = np.array(p_fractions)
    print(f"Overall P-fraction: mean={arr.mean():.6f}, std={arr.std():.6f}")
    print(f"Expected: 0.500000 (50% P by carry invariant)")
    print(f"Min P-fraction: {arr.min():.6f}")
    print(f"Max P-fraction: {arr.max():.6f}")

    # Hill-climb: find message with highest P-fraction
    best_W = random_w16()
    _, best_p = None, arr.mean()

    for trial in range(1000):
        W_trial = list(best_W)
        word = random.randint(0, 15)
        bit = random.randint(0, 31)
        W_trial[word] ^= (1 << bit)

        states = sha256_rounds(W_trial, 64)
        W_exp = schedule(W_trial)

        total_p = 0
        total_bits = 0
        for r in range(64):
            a, b, c, d, e, f, g, h = states[r]
            T1 = (h + sigma1(e) + ch(e, f, g) + K[r] + W_exp[r]) & MASK
            additions = [(d, T1)]
            for x, y in additions:
                total_p += p_fraction_addition(x, y) * 32
                total_bits += 32

        p = total_p / total_bits
        if p > best_p:
            best_p = p
            best_W = W_trial

    print(f"\nAfter hill-climb: P-fraction = {best_p:.6f}")
    print(f"Gain over mean: {best_p - arr.mean():+.6f}")


def test_level_minus2_collision(N=100):
    """
    Level -2: Pure P-subspace SHA-256.
    Replace every + with ⊕ ONLY on P-positions.
    Keep + on G/K positions (where it's deterministic).

    This is a HYBRID function: linear on P-bits, standard on G/K-bits.
    Compute its rank and check if collision is easier.
    """
    print("\n--- TEST 5: LEVEL -2 HYBRID FUNCTION RANK ---")

    for num_rounds in [4, 8, 16, 32, 64]:
        # Measure: how different is hybrid from real SHA-256?
        diffs = []

        for _ in range(N):
            W16 = random_w16()

            # Real SHA-256
            H_real = sha256_compress(W16)

            # Hybrid: at each addition, replace + with ⊕ on P-positions
            H_hybrid = hybrid_sha256(W16, num_rounds)

            # Distance
            d = sum(hw(H_real[i] ^ H_hybrid[i]) for i in range(8))
            diffs.append(d)

        avg_diff = np.mean(diffs)
        print(f"  R={num_rounds:>2}: dist(real, hybrid) = {avg_diff:.2f}/256 bits "
              f"({avg_diff/256*100:.1f}%)")


def hybrid_sha256(W16, num_rounds=64):
    """
    Hybrid SHA-256: on P-positions of each addition, use ⊕ instead of +.
    On G/K-positions, use normal +.

    This is the Level -2 abstraction where linearity and nonlinearity coexist.
    """
    iv = list(IV)
    W = schedule(W16)  # Schedule uses real + (we could hybridize this too)

    state = list(iv)

    for r in range(min(num_rounds, 64)):
        a, b, c, d, e, f, g, h = state

        # T1 = h + Σ1(e) + Ch(e,f,g) + K[r] + W[r]
        # Each addition: hybridize
        s1 = hybrid_add(h, sigma1(e))
        s2 = hybrid_add(s1, ch(e, f, g))
        s3 = hybrid_add(s2, K[r])
        T1 = hybrid_add(s3, W[r])

        # T2 = Σ0(a) + Maj(a,b,c)
        T2 = hybrid_add(sigma0(a), maj(a, b, c))

        state = [
            hybrid_add(T1, T2),
            a, b, c,
            hybrid_add(d, T1),
            e, f, g,
        ]

    # Add IV
    return [(iv[i] + state[i]) & MASK for i in range(8)]


def hybrid_add(a, b):
    """
    Hybrid addition: ⊕ on P-positions, + on G/K-positions.
    On G: both bits are 1, carry is 1 regardless → + = ⊕ + carry
    On K: both bits are 0, carry is 0 regardless → + = ⊕
    On P: carry depends on carry-in → we use ⊕ (no carry propagation)

    Effect: BREAKS carry chains at P-positions.
    """
    mask_g, mask_k, mask_p = gkp_classify(a, b)

    # Real addition result
    real_sum = (a + b) & MASK

    # XOR result
    xor_sum = a ^ b

    # Hybrid: use XOR on P-positions, real on G/K
    result = (real_sum & ~mask_p) | (xor_sum & mask_p)
    return result & MASK


def test_collision_in_hybrid(N=5000):
    """
    The ultimate test: is it easier to find collisions in the hybrid function?

    If hybrid has lower collision resistance → the P-subspace linearization
    creates an exploitable shortcut. Then we study how to lift hybrid
    collisions to real SHA-256 collisions.
    """
    print("\n--- TEST 6: COLLISION DIFFICULTY IN HYBRID vs REAL ---")

    # Measure via birthday: how many pairs until we see small δH?
    # For efficiency, measure distribution of δH

    hw_real = []
    hw_hybrid = []

    for _ in range(N):
        W1 = random_w16()
        W2 = random_w16()

        H1_real = sha256_compress(W1)
        H2_real = sha256_compress(W2)
        d_real = sum(hw(H1_real[i] ^ H2_real[i]) for i in range(8))
        hw_real.append(d_real)

        H1_hyb = hybrid_sha256(W1)
        H2_hyb = hybrid_sha256(W2)
        d_hyb = sum(hw(H1_hyb[i] ^ H2_hyb[i]) for i in range(8))
        hw_hybrid.append(d_hyb)

    real_arr = np.array(hw_real)
    hyb_arr = np.array(hw_hybrid)

    print(f"Real SHA-256:  E[δH]={real_arr.mean():.2f}, std={real_arr.std():.2f}, min={real_arr.min()}")
    print(f"Hybrid SHA-256: E[δH]={hyb_arr.mean():.2f}, std={hyb_arr.std():.2f}, min={hyb_arr.min()}")

    # Lower min → easier collision
    print(f"\nDifference in mean: {hyb_arr.mean() - real_arr.mean():+.4f}")
    print(f"Difference in std: {hyb_arr.std() - real_arr.std():+.4f}")
    print(f"Difference in min: {hyb_arr.min() - real_arr.min():+d}")

    # Count near-collisions (δH < threshold)
    for threshold in [100, 90, 80, 70]:
        p_real = np.mean(real_arr < threshold)
        p_hyb = np.mean(hyb_arr < threshold)
        ratio = p_hyb / p_real if p_real > 0 else float('inf')
        marker = " ***" if ratio > 2 else ""
        print(f"  P(δH<{threshold}): real={p_real:.6f}, hybrid={p_hyb:.6f}, ratio={ratio:.3f}{marker}")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 12: P-SUBSPACE LINEARIZATION")
    print("Step back: where + and ⊕ don't conflict")
    print("=" * 60)

    test_p_linearity_single_round(1500)
    test_p_subspace_rank(30)
    test_p_subspace_collision(3000)
    test_adaptive_p_subspace(1000)
    test_level_minus2_collision(100)
    test_collision_in_hybrid(3000)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print("If hybrid SHA-256 has lower collision resistance → path exists:")
    print("  Level -2: Find collision in hybrid (linearized P-subspace)")
    print("  Level -1: Perturb to restore carry on P-positions")
    print("  Level  0: Full SHA-256 collision")

if __name__ == "__main__":
    main()
