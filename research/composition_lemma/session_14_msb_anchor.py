"""
Session 14: MSB-anchor constraint analysis for b-chain extension.

After Session 13, derived analytically: for b-chain to extend k rounds, need
  a_r[31] = a_0[31] for r = 1..k
This is "MSB-anchor" constraint — keep a's top bit constant through k rounds.

Test: from real SHA-256 IV, count how many rounds a[31] stays constant under
random W. Distribution gives probability of finding k-round chain.

Analytical: each round per-W constraint = 1 bit. Random W → Pr(a_r[31] same) ≈ 0.5
per round, geometric distribution. If observed distribution ≠ geometric, structural
correlation exists.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K
N = 32

SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def measure_msb_stability(initial_state, W_seq, K, max_R=64):
    """Apply rounds; count how many consecutive rounds a[31] = initial_a[31]."""
    initial_a31 = (initial_state[0] >> 31) & 1
    state = initial_state
    streak = 0
    for r in range(max_R):
        state = single_round(state, W_seq[r], K[r], N)
        if (state[0] >> 31) & 1 == initial_a31:
            streak = r + 1
        else:
            break
    return streak


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 64)

    print("=== Session 14: MSB-anchor stability of register a from IV ===\n")

    n_trials = 100_000
    print(f"Running {n_trials} trials with random W from real SHA-256 IV...")
    stabilities = []
    for trial in range(n_trials):
        W_seq = [int(rng.integers(0, 1 << N)) for _ in range(64)]
        s = measure_msb_stability(SHA256_IV, W_seq, K)
        stabilities.append(s)

    counter = Counter(stabilities)
    print(f"\n--- Histogram of streaks (a[31] stable consecutively) ---")
    for k in sorted(counter.keys()):
        c = counter[k]
        pct = c / n_trials
        bar = '#' * min(50, int(pct * 200))
        print(f"  k={k:>2}: {c:>6} ({pct:.5f}) {bar}")

    print(f"\n--- Compare to geometric Pr=0.5 ---")
    for k in range(0, 16):
        observed = counter.get(k, 0) / n_trials
        theory = 0.5 ** (k + 1)
        ratio = observed / theory if theory > 0 else 0
        print(f"  k={k:>2}: obs={observed:.5f} theory={theory:.5f} ratio={ratio:.2f}×")

    # Cumulative for chain finding cost
    print(f"\n--- Pr(streak >= k): cost to find k-round chain ---")
    sorted_keys = sorted(counter.keys())
    for k_target in [4, 8, 12, 16, 20, 24, 32, 64]:
        count_ge = sum(c for k, c in counter.items() if k >= k_target)
        pr_ge = count_ge / n_trials
        cost_log2 = -np.log2(pr_ge) if pr_ge > 0 else float('inf')
        print(f"  k>={k_target:>2}: Pr={pr_ge:.6f}, cost ≈ 2^{cost_log2:.1f} W trials")


if __name__ == "__main__":
    main()
