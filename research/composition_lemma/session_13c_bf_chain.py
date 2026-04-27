"""
Session 13c: Deep dive into b, f register MSB-flip chains.

Session 13b found: flipping b's (or f's) MSB gives chain with Pr ≈ 0.25 through
T=1, 2, 3 rounds (random W). This is NEW — not in T_67.1 which covered only d, h.

Questions:
1. What specific output delta has Pr ≈ 0.25? Is it consistent across T?
2. With controlled W (not random), can Pr → 1?
3. Compare to Wang-chain (controls e-register through 16 rounds).
"""

import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')

import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K

N = 32
N_TRIALS = 5000

REG_NAMES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']


def flip_reg_msb(reg_idx):
    flip = [0]*8
    flip[reg_idx] = 1 << (N-1)
    return tuple(flip)


def chain_step(reg_idx, T, K, n_trials, rng, return_top_delta=False):
    """Run T rounds, find most common diff."""
    flip_init = flip_reg_msb(reg_idx)
    counter = Counter()
    for trial in range(n_trials):
        x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
        x_flipped = tuple(x[i] ^ flip_init[i] for i in range(8))
        W_seq = [int(rng.integers(0, 1<<N)) for _ in range(T)]
        y0 = x; y1 = x_flipped
        for r in range(T):
            y0 = single_round(y0, W_seq[r], K[r], N)
            y1 = single_round(y1, W_seq[r], K[r], N)
        diff = tuple(y0[i] ^ y1[i] for i in range(8))
        counter[diff] += 1
    return counter


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 6)

    print("=== Session 13c: b/f register chain analysis ===\n")

    for reg_name, reg_idx in [('b', 1), ('f', 5)]:
        print(f"\n--- Register {reg_name} (idx {reg_idx}) ---")
        for T in range(1, 5):
            counter = chain_step(reg_idx, T, K, N_TRIALS, rng)
            top5 = counter.most_common(5)
            total = sum(counter.values())
            print(f"\nT={T}: top-5 deltas (Pr, HW, hex per register):")
            for d, c in top5:
                pr = c / total
                hw = sum(bin(w).count('1') for w in d)
                hex_repr = ', '.join(hex(w) for w in d)
                print(f"  Pr={pr:.4f}, HW={hw}, delta=[{hex_repr}]")


if __name__ == "__main__":
    main()
