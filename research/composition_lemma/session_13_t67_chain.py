"""
Session 13: Empirical test of Theorem 67.1 chain extension.

T_67.1 (Prismatic Sessions 67-69): for SHA round R,
  Pr[R(x ⊕ e_{d,31}) ⊕ R(x) = e_{e',31}] = 1.
Single-round deterministic. Question: does this chain to multi-round?

Method:
- For random states x and random W/K, compute R^T(x ⊕ flip) ⊕ R^T(x) for T=1..8.
- For each T, count distribution of differences.
- If T-round all map to single delta with Pr=1 → chain works (CL violation candidate).
- If T-round gives uniform distribution → chain breaks.

Run on real SHA-256 (n=32).
"""

import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')

import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, sigma_params

N = 32
MASK = (1 << N) - 1
N_TRIALS = 5000  # random states


def random_state(rng):
    return tuple(int(rng.integers(0, 1 << N)) for _ in range(8))


def random_W(rng):
    return int(rng.integers(0, 1 << N))


def apply_T_rounds(state, W_list, K_list, n=N):
    """Apply T rounds with given W, K sequences."""
    for r in range(len(W_list)):
        state = single_round(state, W_list[r], K_list[r], n)
    return state


def state_xor(s1, s2):
    return tuple(s1[i] ^ s2[i] for i in range(8))


def main():
    rng = np.random.default_rng(42)

    print("=== Session 13: T_67.1 chain extension test ===\n")
    print(f"Testing on real SHA-256 (n={N}), {N_TRIALS} random trials per T")
    print(f"Initial difference: flip d register MSB (bit 31)\n")

    K = gen_K(N, 8)  # 8 rounds of K

    flip_d_msb = (0, 0, 0, 1 << (N-1), 0, 0, 0, 0)

    for T in range(1, 9):
        print(f"--- T = {T} rounds ---")
        diff_counter = Counter()
        for trial in range(N_TRIALS):
            x = random_state(rng)
            x_flipped = state_xor(x, flip_d_msb)
            # Same W for both paths (so attack is over data)
            W_seq = [random_W(rng) for _ in range(T)]
            y0 = apply_T_rounds(x, W_seq, K[:T])
            y1 = apply_T_rounds(x_flipped, W_seq, K[:T])
            diff = state_xor(y0, y1)
            diff_counter[diff] += 1

        # Statistics
        total = sum(diff_counter.values())
        most_common = diff_counter.most_common(5)
        unique = len(diff_counter)
        max_count = most_common[0][1]
        max_diff = most_common[0][0]
        max_pr = max_count / total

        # Hamming weight of most common diff
        hw_most_common = sum(bin(w).count('1') for w in max_diff)

        print(f"  Unique deltas: {unique} / {N_TRIALS} samples")
        print(f"  Most common delta has Pr = {max_pr:.4f} ({max_count}/{total})")
        print(f"  HW(most common delta) = {hw_most_common}")

        # Check if it matches T_67.1 prediction (only at T=1)
        if T == 1:
            expected = (0, 0, 0, 0, 1 << (N-1), 0, 0, 0)
            matches_67 = sum(1 for d in [diff_counter[expected]])
            print(f"  T_67.1 expected delta {expected[:5]}...: {diff_counter.get(expected, 0)}/{total}")
            if diff_counter.get(expected, 0) == total:
                print(f"  ✓ T_67.1 confirmed: 1-round Pr=1 deterministic")
            else:
                print(f"  ⚠ T_67.1 not confirmed (review code)")

        if max_pr >= 0.99:
            print(f"  ★ PR≥0.99 — deterministic chain at T={T}")
        elif max_pr >= 0.5:
            print(f"  ⚡ Strong bias at T={T}")
        elif max_pr <= 1.5 / N_TRIALS:
            # essentially uniform
            print(f"  ⊘ Uniform — chain broken at T={T}")
        else:
            print(f"  partial bias — diff Pr ≈ {max_pr:.3f}")

        # Show top deltas
        if T <= 3:
            print(f"  Top 3 deltas (HW shown):")
            for d, c in most_common[:3]:
                hw = sum(bin(w).count('1') for w in d)
                print(f"    Pr={c/total:.4f}, HW={hw}, delta_e={hex(d[4])}")
        print()


if __name__ == "__main__":
    main()
