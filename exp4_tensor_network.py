#!/usr/bin/env python3
"""
EXPERIMENT 4: Tensor Network Analysis of SHA-256

SHA-256 as a tensor network:
- Each round = tensor T_r: R^256 -> R^256 (over bits)
- 64 rounds = contraction T_63 o ... o T_0
- Collision condition = specific output constraint

Key questions:
1. What is the effective rank of the round-to-round transfer matrix?
2. Does entanglement entropy between bit groups stay bounded?
3. Is there a low-rank (Matrix Product State) approximation?
4. What are the singular values of the differential propagation matrix?

If entanglement entropy is bounded -> tensor network is compressible
-> there exists a sub-exponential path to collision.
"""

import sys, os, random, math

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def differential_jacobian(W16, round_num, bit_range=32):
    """
    Compute numerical Jacobian of the round function at a given state.
    J[i][j] = ∂(output_bit_i) / ∂(input_bit_j) over GF(2).

    Uses finite differences: flip bit j, observe change in bit i.
    """
    states = sha256_rounds(W16, round_num)
    state_before = states[round_num - 1] if round_num > 0 else list(IV)
    state_after = states[round_num]

    n_bits = 8 * bit_range  # 256 bits
    jacobian = []

    for j in range(n_bits):
        # Flip bit j in state_before
        word_idx = j // bit_range
        bit_idx = j % bit_range

        perturbed = list(state_before)
        perturbed[word_idx] ^= (1 << bit_idx)

        # Apply one round
        W = schedule(W16)
        new_state = sha256_round(perturbed, W[round_num - 1] if round_num > 0 else W[0],
                                  K[round_num - 1] if round_num > 0 else K[0])

        # XOR difference
        diff = []
        for w in range(8):
            d = new_state[w] ^ state_after[w]
            for b in range(bit_range):
                diff.append((d >> b) & 1)

        jacobian.append(diff)

    # jacobian[j] = output diff when input bit j flipped
    # Transpose to get J[i][j]
    J = [[jacobian[j][i] for j in range(n_bits)] for i in range(n_bits)]
    return J

def matrix_rank_gf2(M):
    """Compute rank of binary matrix over GF(2) via Gaussian elimination."""
    m = len(M)
    if m == 0:
        return 0
    n = len(M[0])

    # Copy matrix
    A = [list(row) for row in M]

    rank = 0
    for col in range(n):
        # Find pivot
        pivot = -1
        for row in range(rank, m):
            if A[row][col] == 1:
                pivot = row
                break

        if pivot == -1:
            continue

        # Swap
        A[rank], A[pivot] = A[pivot], A[rank]

        # Eliminate
        for row in range(m):
            if row != rank and A[row][col] == 1:
                A[row] = [(A[row][j] ^ A[rank][j]) for j in range(n)]

        rank += 1

    return rank

def test_single_round_rank(N=50):
    """Test GF(2) rank of single-round Jacobian."""
    print("\n--- TEST 1: SINGLE ROUND JACOBIAN RANK (GF2) ---")

    ranks = []
    for _ in range(N):
        W16 = random_w16()
        for r in [1, 2, 4, 8, 16, 32, 64]:
            if r > 64:
                continue
            J = differential_jacobian(W16, r)
            rnk = matrix_rank_gf2(J)
            ranks.append((r, rnk))

    print(f"{'Round':>5} | {'Avg Rank':>10} | {'Min':>5} | {'Max':>5} | {'Deficit':>8}")
    print("-" * 50)

    for r in [1, 2, 4, 8, 16, 32, 64]:
        r_ranks = [rnk for rr, rnk in ranks if rr == r]
        if not r_ranks:
            continue
        avg = sum(r_ranks) / len(r_ranks)
        mn = min(r_ranks)
        mx = max(r_ranks)
        deficit = 256 - avg
        marker = " ***" if deficit > 10 else ""
        print(f"{r:>5} | {avg:>10.1f} | {mn:>5} | {mx:>5} | {deficit:>8.1f}{marker}")

def test_multi_round_propagation(N=100):
    """
    Measure effective rank of differential propagation across multiple rounds.
    Flip each of 256 input bits, observe output difference after R rounds.
    """
    print("\n--- TEST 2: MULTI-ROUND DIFFERENTIAL PROPAGATION RANK ---")

    print(f"{'Rounds':>6} | {'Avg Rank':>10} | {'Rank Deficit':>12} | {'Signal'}")
    print("-" * 55)

    for num_rounds in [1, 2, 3, 4, 5, 6, 8, 10, 16, 20, 32, 64]:
        round_ranks = []

        for _ in range(N):
            W16 = random_w16()

            # Compute base states
            base_states = sha256_rounds(W16, num_rounds)
            base_final = base_states[num_rounds]

            # Build differential matrix: flip each W bit, observe output
            diff_matrix = []

            for word in range(16):
                for bit in range(32):
                    W_pert = list(W16)
                    W_pert[word] ^= (1 << bit)

                    pert_states = sha256_rounds(W_pert, num_rounds)
                    pert_final = pert_states[num_rounds]

                    # XOR difference in output state
                    diff_row = []
                    for w in range(8):
                        d = base_final[w] ^ pert_final[w]
                        for b in range(32):
                            diff_row.append((d >> b) & 1)

                    diff_matrix.append(diff_row)

            # diff_matrix: 512 rows (input bits) × 256 cols (output bits)
            rnk = matrix_rank_gf2(diff_matrix)
            round_ranks.append(rnk)

        avg = sum(round_ranks) / len(round_ranks)
        deficit = 256 - avg  # Max possible rank is 256 (output dim)
        marker = ""
        if deficit > 5:
            marker = f"DEFICIT={deficit:.0f} ***"

        print(f"{num_rounds:>6} | {avg:>10.1f} | {deficit:>12.1f} | {marker}")

def test_entanglement_entropy(N=200):
    """
    Measure entanglement entropy between a-branch (a,b,c,d) and e-branch (e,f,g,h).

    For each input bit flip, measure if output difference is confined to one branch
    or spreads to both. The spread = entanglement.

    Entanglement entropy S = -Σ p_i log p_i where p_i is fraction of diff in branch i.
    """
    print("\n--- TEST 3: ENTANGLEMENT ENTROPY (a-branch vs e-branch) ---")

    print(f"{'Rounds':>6} | {'S_entangle':>12} | {'p(a-only)':>10} | {'p(e-only)':>10} | {'p(both)':>10}")
    print("-" * 65)

    for num_rounds in [1, 2, 3, 4, 5, 8, 16, 32, 64]:
        entropies = []
        a_only = 0
        e_only = 0
        both = 0
        total = 0

        for _ in range(N):
            W16 = random_w16()
            base_states = sha256_rounds(W16, num_rounds)
            base_final = base_states[num_rounds]

            for word in range(16):
                for bit in [0, 8, 16, 24, 31]:  # Sample bits
                    W_pert = list(W16)
                    W_pert[word] ^= (1 << bit)
                    pert_states = sha256_rounds(W_pert, num_rounds)
                    pert_final = pert_states[num_rounds]

                    # a-branch diff (words 0-3)
                    a_diff = sum(hw(base_final[i] ^ pert_final[i]) for i in range(4))
                    # e-branch diff (words 4-7)
                    e_diff = sum(hw(base_final[i] ^ pert_final[i]) for i in range(4, 8))

                    total_diff = a_diff + e_diff
                    if total_diff > 0:
                        p_a = a_diff / total_diff
                        p_e = e_diff / total_diff

                        # Binary entropy
                        if p_a > 0 and p_e > 0:
                            S = -p_a * math.log2(p_a) - p_e * math.log2(p_e)
                        else:
                            S = 0
                        entropies.append(S)

                        if a_diff > 0 and e_diff == 0:
                            a_only += 1
                        elif e_diff > 0 and a_diff == 0:
                            e_only += 1
                        else:
                            both += 1
                        total += 1

        avg_S = sum(entropies) / len(entropies) if entropies else 0
        p_ao = a_only / total if total > 0 else 0
        p_eo = e_only / total if total > 0 else 0
        p_b = both / total if total > 0 else 0

        marker = ""
        if avg_S < 0.9:  # Max entropy = 1.0 for balanced
            marker = f" (bounded!)"

        print(f"{num_rounds:>6} | {avg_S:>12.6f} | {p_ao:>10.4f} | {p_eo:>10.4f} | {p_b:>10.4f}{marker}")

def test_singular_value_distribution(N=50):
    """
    Compute singular value distribution of the differential propagation matrix.
    If SVD decays fast -> low-rank approximation exists -> compression possible.
    """
    print("\n--- TEST 4: SINGULAR VALUE DISTRIBUTION (real-valued) ---")

    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False
        print("NumPy not available. Skipping SVD analysis.")
        return

    for num_rounds in [4, 8, 16, 32, 64]:
        all_svs = []

        for _ in range(N):
            W16 = random_w16()
            base_states = sha256_rounds(W16, num_rounds)
            base_final = base_states[num_rounds]

            # Build real-valued differential matrix (Hamming distances)
            diff_matrix = []
            for word in range(16):
                for bit in range(32):
                    W_pert = list(W16)
                    W_pert[word] ^= (1 << bit)
                    pert_states = sha256_rounds(W_pert, num_rounds)
                    pert_final = pert_states[num_rounds]

                    row = []
                    for w in range(8):
                        d = base_final[w] ^ pert_final[w]
                        for b in range(32):
                            row.append(float((d >> b) & 1))
                    diff_matrix.append(row)

            M = np.array(diff_matrix, dtype=np.float64)
            svs = np.linalg.svd(M, compute_uv=False)
            all_svs.append(svs)

        # Average SVD profile
        avg_svs = np.mean(all_svs, axis=0)
        total_energy = np.sum(avg_svs**2)

        # How many SVs capture 90%, 95%, 99% of energy?
        cumulative = np.cumsum(avg_svs**2) / total_energy
        r90 = np.searchsorted(cumulative, 0.90) + 1
        r95 = np.searchsorted(cumulative, 0.95) + 1
        r99 = np.searchsorted(cumulative, 0.99) + 1

        # Effective rank (Shannon entropy of normalized SVs)
        p = avg_svs**2 / total_energy
        p = p[p > 0]
        eff_rank = 2**(-np.sum(p * np.log2(p)))

        print(f"\nRounds={num_rounds}:")
        print(f"  Top 5 SVs: {avg_svs[:5].tolist()}")
        print(f"  Rank for 90% energy: {r90}/256")
        print(f"  Rank for 95% energy: {r95}/256")
        print(f"  Rank for 99% energy: {r99}/256")
        print(f"  Effective rank (Shannon): {eff_rank:.1f}/256")
        print(f"  SV decay ratio (sv1/sv10): {avg_svs[0]/avg_svs[9]:.2f}")

        if eff_rank < 200:
            print(f"  *** SIGNAL: Effective rank {eff_rank:.0f} << 256! Compressible! ***")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 4: TENSOR NETWORK ANALYSIS OF SHA-256")
    print("=" * 70)

    # Test 1: Single round rank
    test_single_round_rank(20)

    # Test 2: Multi-round propagation rank
    test_multi_round_propagation(20)

    # Test 3: Entanglement entropy
    test_entanglement_entropy(100)

    # Test 4: SVD
    test_singular_value_distribution(20)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("If rank deficit persists at 64 rounds -> tensor compression possible")
    print("If entanglement entropy < 1.0 at 64R -> MPS approximation exists")
    print("If SVD effective rank << 256 -> low-rank collision shortcut")

if __name__ == "__main__":
    main()
