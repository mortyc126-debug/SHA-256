"""
Session 13b: Per-register MSB-flip chain decay scan.

T_67.1 covers d's MSB and h's MSB (both Pr=1). Question: is there a
register whose MSB-flip chain has SLOWER decay (gives longer deterministic
or near-deterministic chain)?

For each register r ∈ {a,b,c,d,e,f,g,h}, flip MSB и measure top-delta Pr at
T = 1, 2, 3, 4 rounds. Compare decay profiles.

Purpose: maybe d/h are not the SLOWEST register — find better starting
register для potential trail extension.
"""

import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')

import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K

N = 32
N_TRIALS = 3000

REG_NAMES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']


def flip_reg_msb(reg_idx):
    flip = [0]*8
    flip[reg_idx] = 1 << (N-1)
    return tuple(flip)


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 6)

    print("=== Session 13b: Per-register MSB-flip chain decay ===\n")
    print(f"For each register R ∈ a..h, flip R's MSB; measure top-delta Pr at T=1..4")
    print(f"{N_TRIALS} trials per cell. Random baseline = 1/{N_TRIALS} = {1/N_TRIALS:.4f}\n")

    print(f"{'Reg':<4}{'T=1 Pr':<12}{'T=2 Pr':<12}{'T=3 Pr':<12}{'T=4 Pr':<12}{'T=1 HW':<8}{'T=2 HW':<8}")

    for reg_idx, name in enumerate(REG_NAMES):
        flip_init = flip_reg_msb(reg_idx)
        row = [name]
        hw_vals = []
        for T in [1, 2, 3, 4]:
            diff_counter = Counter()
            for trial in range(N_TRIALS):
                x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
                x_flipped = tuple(x[i] ^ flip_init[i] for i in range(8))
                W_seq = [int(rng.integers(0, 1<<N)) for _ in range(T)]
                y0 = x; y1 = x_flipped
                for r in range(T):
                    y0 = single_round(y0, W_seq[r], K[r], N)
                    y1 = single_round(y1, W_seq[r], K[r], N)
                diff = tuple(y0[i] ^ y1[i] for i in range(8))
                diff_counter[diff] += 1
            most = diff_counter.most_common(1)[0]
            top_pr = most[1] / N_TRIALS
            top_hw = sum(bin(w).count('1') for w in most[0])
            row.append(f"{top_pr:.4f}")
            if T <= 2:
                hw_vals.append(top_hw)
        # Print
        line = f"{row[0]:<4}{row[1]:<12}{row[2]:<12}{row[3]:<12}{row[4]:<12}"
        line += f"{hw_vals[0]:<8}{hw_vals[1]:<8}"
        print(line)


if __name__ == "__main__":
    main()
