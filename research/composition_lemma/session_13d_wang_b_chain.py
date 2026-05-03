"""
Session 13d: Wang-style adaptive δW to extend b-chain past 3 rounds.

Found in 13c: b-MSB flip gives chain b→c→d→e with Pr=0.25 over 3 rounds.
At round 4, e is flipped → Σ1(e) fires → break.

Wang-chain idea: choose δW[r] adaptively to cancel δT1 propagation.
For e-MSB flip at round 3, δΣ1(2^31) = 2^25 ⊕ 2^20 ⊕ 2^6.
δCh(e^flip, f, g) is state-dependent.

Adaptive: δW[3] = δΣ1 ⊕ δCh ⇒ δT1 = 0 ⇒ chain doesn't break (modulo δT2).

Test: with adaptive δW, how far does b-chain extend?
"""

import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')

import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj

N = 32
MASK = (1 << N) - 1

REG_NAMES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']


def flip_reg_msb(reg_idx):
    flip = [0]*8
    flip[reg_idx] = 1 << (N-1)
    return tuple(flip)


def adaptive_round(state0, state1, K_r, n=N):
    """Apply one round to both paths, choosing δW to minimize T1 difference.
    Returns (new_state0, new_state1, dW_chosen).

    δT1 = δh + δΣ1(e) + δCh(e,f,g) + δW
    To make δT1 = 0: δW = δh ⊕ δΣ1 ⊕ δCh

    Then we use SAME W for state0, W ⊕ dW for state1.
    """
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1

    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh

    # Use random W for state0
    W0 = int(np.random.default_rng().integers(0, 1<<N))
    W1 = W0 ^ dW  # for state1

    new0 = single_round(state0, W0, K_r, n)
    new1 = single_round(state1, W1, K_r, n)
    return new0, new1, dW


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 16)

    print("=== Session 13d: Wang-style adaptive δW for b-chain ===\n")
    print("Goal: extend b-MSB chain past 3 rounds via adaptive δW that cancels δT1")
    print(f"K precomputed for 16 rounds; n={N} (real SHA-256)")
    print()

    n_trials = 2000

    for reg_name, reg_idx in [('b', 1), ('f', 5), ('a', 0), ('c', 2)]:
        print(f"\n--- Starting flip: {reg_name}-MSB ---")
        flip_init = flip_reg_msb(reg_idx)

        for max_T in [3, 5, 8, 10, 12, 16]:
            counter = Counter()
            for trial in range(n_trials):
                x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
                x_flip = tuple(x[i] ^ flip_init[i] for i in range(8))

                # Use globally fixed RNG for consistency
                np.random.seed(trial * 1000 + 7)

                y0, y1 = x, x_flip
                for r in range(max_T):
                    y0, y1, _ = adaptive_round(y0, y1, K[r], N)

                diff = tuple(y0[i] ^ y1[i] for i in range(8))
                counter[diff] += 1

            top = counter.most_common(1)[0]
            top_pr = top[1] / n_trials
            top_hw = sum(bin(w).count('1') for w in top[0])
            unique = len(counter)

            verdict = ""
            if top_pr >= 0.99:
                verdict = "★ DETERMINISTIC"
            elif top_pr >= 0.5:
                verdict = "⚡ Strong"
            elif top_pr >= 0.1:
                verdict = "partial"
            elif top_pr >= 0.01:
                verdict = "weak bias"
            else:
                verdict = "⊘ scrambled"

            print(f"  T={max_T:>2}: top Pr={top_pr:.4f} (HW={top_hw:>3}), unique={unique:>4} | {verdict}")


if __name__ == "__main__":
    main()
