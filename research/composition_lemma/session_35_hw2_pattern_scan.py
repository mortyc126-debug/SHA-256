"""
Session 35: HW=2 δW pattern scan — Direction (4) Higher-order differential.

For each HW=2 pattern in W[0] (496 = C(32,2) patterns):
- Compute mean HW(δstate) at rounds T=4, 8 over 200 random messages
- Find patterns giving LOWEST mean HW (potential structural advantage)

Random baseline: mean HW(δstate) ≈ 128 (full avalanche).
Pattern with mean HW < 100 = structural finding.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from itertools import combinations
from mini_sha import single_round, gen_K, sig0_msg, sig1_msg
N = 32


def hw(x):
    return bin(x).count('1')


def state_hw(s_a, s_b):
    return sum(hw(s_a[i] ^ s_b[i]) for i in range(8))


def measure_mean_hw(IV, K, dW0_pattern, T, n_samples, rng):
    """For δW = dW0_pattern at W[0], compute mean HW(δstate at round T).
    δW = 0 for W[1..15]."""
    total = 0
    for _ in range(n_samples):
        W_a = [int(rng.integers(0, 1 << N)) for _ in range(16)]
        for r in range(16, T):
            new_w = (sig1_msg(W_a[r-2], N) + W_a[r-7] + sig0_msg(W_a[r-15], N) + W_a[r-16]) & ((1 << N) - 1)
            W_a.append(new_w)
        W_b = list(W_a); W_b[0] ^= dW0_pattern
        for r in range(16, T):
            new_w = (sig1_msg(W_b[r-2], N) + W_b[r-7] + sig0_msg(W_b[r-15], N) + W_b[r-16]) & ((1 << N) - 1)
            W_b[r] = new_w

        s_a = IV; s_b = IV
        for r in range(T):
            s_a = single_round(s_a, W_a[r], K[r], N)
            s_b = single_round(s_b, W_b[r], K[r], N)
        total += state_hw(s_a, s_b)
    return total / n_samples


def main():
    print("=== Session 35: HW=2 δW pattern scan ===\n")
    print("For each HW=2 pattern at W[0]: mean HW(δstate@T=4) over 200 samples\n")

    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)
    K = gen_K(N, 16)
    rng = np.random.default_rng(42)

    n_samples = 200
    results = []

    # Generate all HW=2 patterns in 32-bit
    patterns = []
    for i in range(N):
        for j in range(i+1, N):
            patterns.append((1 << i) | (1 << j))

    print(f"Scanning {len(patterns)} HW=2 patterns × {n_samples} samples × T=4...")

    for idx, p in enumerate(patterns):
        # Identify the two bits
        bits = [i for i in range(N) if (p >> i) & 1]
        mean_hw = measure_mean_hw(SHA256_IV, K, p, 4, n_samples, rng)
        results.append((p, bits, mean_hw))
        if (idx + 1) % 100 == 0:
            print(f"  Progress {idx+1}/{len(patterns)}, current pattern bits {bits}, HW={mean_hw:.2f}")

    # Sort by mean HW
    results.sort(key=lambda x: x[2])
    print("\n--- Top 20 LOWEST mean HW patterns at T=4 ---")
    print(f"{'pattern':>10} | {'bits':>15} | {'mean HW':>8}")
    for p, bits, m in results[:20]:
        print(f"  {hex(p):>10} | {str(bits):>15} | {m:>8.2f}")

    print("\n--- Top 5 HIGHEST mean HW patterns at T=4 (worst, for comparison) ---")
    for p, bits, m in results[-5:]:
        print(f"  {hex(p):>10} | {str(bits):>15} | {m:>8.2f}")

    print(f"\nGlobal mean: {np.mean([r[2] for r in results]):.2f}, std: {np.std([r[2] for r in results]):.2f}")


if __name__ == "__main__":
    main()
