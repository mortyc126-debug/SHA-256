"""
Session 31: Monte Carlo probabilistic differential propagation.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, sig0_msg, sig1_msg
N = 32


def sha256_round_pair(IV, W_a, W_b, K, T):
    sa = list(IV); sb = list(IV)
    diffs = []
    for r in range(T):
        sa = list(single_round(tuple(sa), W_a[r], K[r], N))
        sb = list(single_round(tuple(sb), W_b[r], K[r], N))
        diff = tuple(sa[i] ^ sb[i] for i in range(8))
        diffs.append(diff)
    return diffs


def main():
    print("=== Session 31: Monte Carlo differential propagation ===\n")
    print("δM = single-bit flip at W[0][bit 31] (MSB)\n")

    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)
    K = gen_K(N, 64)

    n_samples = 10000
    rng = np.random.default_rng(42)

    hw_at_round = [[] for _ in range(64)]
    diff_counter_per_round = [Counter() for _ in range(64)]

    print(f"Running {n_samples} samples × 64 rounds...")
    for sample in range(n_samples):
        W_base = [int(rng.integers(0, 1 << N)) for _ in range(16)]
        W_a = list(W_base)
        for r in range(16, 64):
            new_w = (sig1_msg(W_a[r-2], N) + W_a[r-7] + sig0_msg(W_a[r-15], N) + W_a[r-16]) & ((1 << N) - 1)
            W_a.append(new_w)
        W_b = list(W_a)
        W_b[0] = W_a[0] ^ (1 << 31)
        for r in range(16, 64):
            new_w = (sig1_msg(W_b[r-2], N) + W_b[r-7] + sig0_msg(W_b[r-15], N) + W_b[r-16]) & ((1 << N) - 1)
            W_b[r] = new_w

        diffs = sha256_round_pair(SHA256_IV, W_a, W_b, K, 64)
        for r, d in enumerate(diffs):
            hw = sum(bin(w).count('1') for w in d)
            hw_at_round[r].append(hw)
            diff_counter_per_round[r][d] += 1

        if (sample + 1) % 2000 == 0:
            print(f"  Progress: {sample+1}/{n_samples}")

    print("\n--- Mean HW(δstate) per round ---")
    print(f"{'r':>3} | {'mean':>6} | {'std':>5} | {'min':>4} | {'max':>4} | top-1 Pr | unique")
    for r in [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, 40, 50, 60, 63]:
        hws = hw_at_round[r]
        mean_hw = np.mean(hws)
        std_hw = np.std(hws)
        min_hw = min(hws)
        max_hw = max(hws)
        most_common = diff_counter_per_round[r].most_common(1)[0]
        top_pr = most_common[1] / n_samples
        unique = len(diff_counter_per_round[r])
        print(f"  {r:>2} | {mean_hw:>6.2f} | {std_hw:>5.2f} | {min_hw:>4} | {max_hw:>4} | {top_pr:.4f} | {unique:>5}")

    print("\n--- Top deltas at key rounds ---")
    for r in [0, 1, 2, 3, 4, 5]:
        most = diff_counter_per_round[r].most_common(3)
        print(f"\nRound {r}:")
        for d, c in most:
            hw = sum(bin(w).count('1') for w in d)
            print(f"  Pr={c/n_samples:.4f}, HW={hw}, δstate={[hex(x) for x in d]}")


if __name__ == "__main__":
    main()
