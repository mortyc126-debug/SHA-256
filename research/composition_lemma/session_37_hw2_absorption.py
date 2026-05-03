"""
Session 37: HW=2 adjacent δstate absorption via adaptive δW.

Theorem (Sessions 18-22) handles HW=1 single-bit δstate.
Question: Adjacent HW=2 pair (e.g., bits 30,31) — does adaptive δW absorb,
and at what k?

Initial δstate: f register has bits 30, 31 flipped (HW=2).
Adaptive δW per round (Wang-style: δW = δh + δΣ1(e) + δCh(e,f,g)).
Measure HW(δstate) at each round T over Monte Carlo.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj
N = 32


def adaptive_round(state0, state1, K_r, n=N):
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1
    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh
    W0 = int(np.random.default_rng().integers(0, 1<<N))
    W1 = W0 ^ dW
    return single_round(state0, W0, K_r, n), single_round(state1, W1, K_r, n)


def main():
    print("=== Session 37: HW=2 adjacent absorption via adaptive δW ===\n")

    rng = np.random.default_rng(42)
    K = gen_K(N, 32)
    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)

    n_trials = 2000

    # Initial flip patterns to test
    test_flips = [
        ('f bits 30,31 (adjacent MSB)', 5, (1<<30)|(1<<31)),
        ('f bit 31 only (HW=1)', 5, 1<<31),
        ('f bits 0,1 (adjacent LSB)', 5, (1<<0)|(1<<1)),
        ('f bits 15,16 (adjacent middle)', 5, (1<<15)|(1<<16)),
        ('h bits 30,31 (adjacent MSB)', 7, (1<<30)|(1<<31)),
        ('h bit 31 only (HW=1)', 7, 1<<31),
    ]

    for name, reg, flip in test_flips:
        print(f"\n--- {name} ---")
        flip_init = [0]*8; flip_init[reg] = flip
        flip_init = tuple(flip_init)

        # For each T, measure mean HW(δstate) and convergence rate
        for T in [1, 2, 3, 4, 5, 6, 8]:
            mean_hw = 0
            convergent = 0  # how often δstate=0
            for trial in range(n_trials):
                np.random.seed(trial * 1000 + 7)
                x = SHA256_IV
                x_flip = tuple(x[i] ^ flip_init[i] for i in range(8))
                y0, y1 = x, x_flip
                for r in range(T):
                    y0, y1 = adaptive_round(y0, y1, K[r], N)
                diff = tuple(y0[i] ^ y1[i] for i in range(8))
                hw = sum(bin(w).count('1') for w in diff)
                mean_hw += hw
                if hw == 0:
                    convergent += 1
            mean_hw /= n_trials
            conv_rate = convergent / n_trials
            print(f"  T={T}: mean HW={mean_hw:6.2f}, convergent rate={conv_rate:.4f}")


if __name__ == "__main__":
    main()
