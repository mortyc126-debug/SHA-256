"""
Session 13i: For SHA-256 IV (fixed), does adaptive-δW b-chain converge?

Random initial state convergence rate: 2.88-3.25%, requiring a[31]=c[31].
SHA-256 IV: a=0x6A09E667, c=0x3C6EF372 — both have bit 31 = 0. ✓ satisfies.

Test: with x = SHA-256 IV (or close perturbations), how often does b-flip
adaptive δW chain converge over many random W choices?
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj, gen_IV
N = 32


def adaptive_round_with_seed(state0, state1, K_r, W_seed, n=N):
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1
    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh
    W0 = W_seed
    W1 = W0 ^ dW
    return single_round(state0, W0, K_r, n), single_round(state1, W1, K_r, n)


def test_convergence(x, x_flip, W_sequence, K, max_R=64):
    y0, y1 = x, x_flip
    for r in range(max_R):
        y0, y1 = adaptive_round_with_seed(y0, y1, K[r], W_sequence[r])
    diff = tuple(y0[i] ^ y1[i] for i in range(8))
    return sum(bin(w).count('1') for w in diff)


def main():
    print("=== Session 13i: Adaptive δW chain from FIXED SHA-256 IV ===\n")

    K = gen_K(N, 64)
    SHA256_IV = (
        0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
        0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19
    )
    print(f"SHA-256 IV: a={hex(SHA256_IV[0])}, b={hex(SHA256_IV[1])}, c={hex(SHA256_IV[2])}")
    a31 = (SHA256_IV[0] >> 31) & 1
    c31 = (SHA256_IV[2] >> 31) & 1
    print(f"  a[31]={a31}, c[31]={c31}, equal: {a31==c31}\n")

    # Test b-flip from IV
    flip = (1 << 31)
    x = SHA256_IV
    x_flip = (x[0], x[1] ^ flip, x[2], x[3], x[4], x[5], x[6], x[7])

    rng = np.random.default_rng(42)
    n_trials = 30000

    print(f"Running {n_trials} trials with random W sequences from IV...")
    convergent = 0
    hw_counts = Counter()
    for trial in range(n_trials):
        W_seq = [int(rng.integers(0, 1<<N)) for _ in range(64)]
        hw = test_convergence(x, x_flip, W_seq, K)
        hw_counts[hw] += 1
        if hw == 0:
            convergent += 1

    print(f"Convergent (HW=0): {convergent}/{n_trials} ({convergent/n_trials:.6f})")
    print(f"\nHW distribution at end of 64 rounds:")
    for hw in sorted(hw_counts.keys())[:15]:
        print(f"  HW={hw}: {hw_counts[hw]:>5} ({hw_counts[hw]/n_trials:.4f})")
    print(f"  ...")
    largest = max(hw_counts.keys())
    smallest = min(hw_counts.keys())
    print(f"  Min HW: {smallest}, Max HW: {largest}")

    # Compare to truly random output: HW would be Bin(256, 0.5) → mean 128
    mean_hw = sum(hw * c for hw, c in hw_counts.items()) / n_trials
    print(f"  Mean HW: {mean_hw:.2f} (random baseline: 128)")

    # Also test other register flips
    print("\n--- Other initial flips from IV ---")
    for reg_idx, reg_name in [(0,'a'), (3,'d'), (5,'f'), (7,'h')]:
        x_flip = list(x); x_flip[reg_idx] ^= flip; x_flip = tuple(x_flip)
        n_test = 5000
        hw_dist = Counter()
        conv = 0
        for trial in range(n_test):
            W_seq = [int(rng.integers(0, 1<<N)) for _ in range(64)]
            hw = test_convergence(x, x_flip, W_seq, K)
            hw_dist[hw] += 1
            if hw == 0:
                conv += 1
        mean = sum(hw*c for hw,c in hw_dist.items()) / n_test
        print(f"  {reg_name}-flip: convergent {conv}/{n_test} ({conv/n_test:.6f}), mean HW = {mean:.2f}")


if __name__ == "__main__":
    main()
