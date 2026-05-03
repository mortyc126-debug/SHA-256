"""
Session 34: Internal differential on SHA-2 — quasi-period detection.

Internal differential (Peyrin 2010, Dinur 2017): instead of comparing two
messages M1, M2, observe single computation for internal symmetries/periods.

For Keccak: slice-symmetry (5×5 plane permutation) preserved partially.
For SHA-2: no obvious symmetry, but maybe quasi-periodicity:
  state[r] ⊕ state[r+k] has biased low HW for some k?

Experiment:
- Random M, 64 rounds, save all 64 states.
- For each k in {1..32}: compute mean HW(state[r] ⊕ state[r+k]).
- Random expectation = 128 (each bit flips with Pr=0.5 in long composition).
- If mean HW significantly < 128: quasi-period detected.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from mini_sha import single_round, gen_K, sig0_msg, sig1_msg
N = 32


def main():
    print("=== Session 34: SHA-2 quasi-period detection ===\n")

    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)
    K = gen_K(N, 64)

    n_samples = 5000
    rng = np.random.default_rng(42)

    # For each k in 1..32, accumulate HW(state[r] ⊕ state[r+k]) over various r and samples
    hw_sums = {k: [] for k in range(1, 33)}

    print(f"Running {n_samples} samples × 64 rounds...")
    for sample in range(n_samples):
        W = [int(rng.integers(0, 1 << N)) for _ in range(16)]
        for r in range(16, 64):
            new_w = (sig1_msg(W[r-2], N) + W[r-7] + sig0_msg(W[r-15], N) + W[r-16]) & ((1 << N) - 1)
            W.append(new_w)

        states = [SHA256_IV]
        s = SHA256_IV
        for r in range(64):
            s = single_round(s, W[r], K[r], N)
            states.append(s)

        # For each k, collect HW(state[r] ⊕ state[r+k]) for r ∈ [10..63-k]
        # (skip first 10 rounds for "warm up", avoid too-early structure)
        for k in range(1, 33):
            for r in range(10, 64 - k):
                diff = tuple(states[r][i] ^ states[r+k][i] for i in range(8))
                hw = sum(bin(w).count('1') for w in diff)
                hw_sums[k].append(hw)

        if (sample + 1) % 1000 == 0:
            print(f"  Progress: {sample+1}/{n_samples}")

    print("\n--- Mean HW(state[r] ⊕ state[r+k]) per k ---")
    print("Random expectation: 128.0\n")
    print(f"{'k':>3} | {'mean':>6} | {'std':>5} | {'min':>4} | {'max':>4} | {'samples':>8}")
    print("-" * 50)
    for k in range(1, 33):
        hws = hw_sums[k]
        mean_hw = np.mean(hws)
        std_hw = np.std(hws)
        min_hw = min(hws)
        max_hw = max(hws)
        deviation = abs(mean_hw - 128)
        marker = " ★" if deviation > 1 else ""
        print(f"{k:>3} | {mean_hw:>6.2f} | {std_hw:>5.2f} | {min_hw:>4} | {max_hw:>4} | {len(hws):>8}{marker}")


if __name__ == "__main__":
    main()
