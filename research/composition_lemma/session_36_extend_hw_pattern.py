"""
Session 36: Extend HW=2 finding to T=8 and HW=3, HW=4 patterns.

Session 35 found: adjacent bit pairs in W[0] give mean HW(δstate@T=4) = 84-92,
vs scattered pairs ≈ 105. Structural carry cancellation.

Extend:
1. Same bits (30, 31) at T=8: does cancellation persist or wash out?
2. HW=3 patterns: 3 consecutive bits — even better?
3. HW=4 patterns: try.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from itertools import combinations
from mini_sha import single_round, gen_K, sig0_msg, sig1_msg
N = 32


def hw(x):
    return bin(x).count('1')


def state_hw_diff(s_a, s_b):
    return sum(hw(s_a[i] ^ s_b[i]) for i in range(8))


def measure_mean_hw(IV, K, dW0_pattern, T, n_samples, rng):
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
        total += state_hw_diff(s_a, s_b)
    return total / n_samples


def main():
    print("=== Session 36: Extend adjacent-bit finding ===\n")
    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)

    rng = np.random.default_rng(42)
    n_samples = 200

    # ===== Part A: Pattern (30, 31) at various T =====
    print("--- Part A: bits (30, 31) at various T ---")
    pattern = (1 << 30) | (1 << 31)
    K_full = gen_K(N, 64)
    for T in [2, 3, 4, 5, 6, 8, 10, 16, 24, 32, 64]:
        m = measure_mean_hw(SHA256_IV, K_full[:T] if T<64 else K_full, pattern, T, n_samples, rng)
        print(f"  T={T:>3}: mean HW = {m:>6.2f}  (random baseline 128)")

    # ===== Part B: HW=3 consecutive triples =====
    print("\n--- Part B: HW=3 consecutive triples at T=4 ---")
    K = gen_K(N, 16)
    for start_bit in range(0, 30):
        pattern = (1 << start_bit) | (1 << (start_bit+1)) | (1 << (start_bit+2))
        m = measure_mean_hw(SHA256_IV, K, pattern, 4, n_samples, rng)
        bits = [start_bit, start_bit+1, start_bit+2]
        print(f"  bits {bits}: mean HW = {m:>6.2f}")

    # ===== Part C: HW=4 consecutive quadruples =====
    print("\n--- Part C: HW=4 consecutive quadruples at T=4 ---")
    for start_bit in [0, 4, 8, 12, 16, 20, 24, 28]:
        pattern = sum(1 << (start_bit+i) for i in range(4))
        m = measure_mean_hw(SHA256_IV, K, pattern, 4, n_samples, rng)
        bits = [start_bit+i for i in range(4)]
        print(f"  bits {bits}: mean HW = {m:>6.2f}")

    # ===== Part D: HW=2 at top: (30,31) variations across W words =====
    print("\n--- Part D: bits (30, 31) δW at different W indices ---")
    for W_idx in range(8):
        # δW at W[W_idx] only
        # Modify measure_mean_hw approach: place pattern at W[W_idx]
        total = 0
        for _ in range(n_samples):
            W_a = [int(rng.integers(0, 1 << N)) for _ in range(16)]
            W_b = list(W_a)
            if W_idx < 16:
                W_b[W_idx] ^= ((1 << 30) | (1 << 31))
            else:
                continue
            for r in range(16, 4):
                pass  # T=4 < 16 so no schedule expansion
            s_a = SHA256_IV; s_b = SHA256_IV
            for r in range(4):
                s_a = single_round(s_a, W_a[r], K[r], N)
                s_b = single_round(s_b, W_b[r], K[r], N)
            total += state_hw_diff(s_a, s_b)
        m = total / n_samples
        print(f"  W[{W_idx}]: mean HW = {m:>6.2f}")


if __name__ == "__main__":
    main()
