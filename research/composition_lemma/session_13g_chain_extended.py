"""
Session 13g: Extended chain test for b-flip — does L=25 cluster reach full 64 rounds?

Surprising finding (13f): 3% of states have chain length L≥25. May actually be
collisions or extend to full 64 rounds.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj
N = 32; MASK = (1 << N) - 1


def adaptive_round_track(state0, state1, K_r, n=N):
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1
    dSig0 = Sig0(a0, n) ^ Sig0(a1, n)
    dMaj = Maj(a0, b0, c0, n) ^ Maj(a1, b1, c1, n)
    dT2 = dSig0 ^ dMaj
    chain_ok_31 = (dT2 >> (n-1)) & 1 == 0
    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh
    W0 = int(np.random.default_rng().integers(0, 1<<N))
    W1 = W0 ^ dW
    return single_round(state0, W0, K_r, n), single_round(state1, W1, K_r, n), chain_ok_31, dT2


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 64)
    print("=== Session 13g: Extended chain — full 64 rounds ===\n")
    n_trials = 5000

    chain_lengths = []
    diff_at_end = []  # state diff at last successful round
    converged_to_zero = 0  # count of trials where diff = 0 throughout

    for trial in range(n_trials):
        x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
        x_flip = (x[0], x[1] ^ (1<<31), x[2], x[3], x[4], x[5], x[6], x[7])
        y0, y1 = x, x_flip
        chain_len = 0
        ever_zero = False
        for r in range(64):
            y0, y1, ok, _ = adaptive_round_track(y0, y1, K[r], N)
            cur_diff = tuple(y0[i] ^ y1[i] for i in range(8))
            cur_hw = sum(bin(w).count('1') for w in cur_diff)
            if cur_hw == 0:
                ever_zero = True
            if ok:
                chain_len = r + 1
            else:
                break
        chain_lengths.append(chain_len)
        if ever_zero:
            converged_to_zero += 1

    print(f"Total trials: {n_trials}, converged to zero diff: {converged_to_zero} ({converged_to_zero/n_trials:.4f})")
    print(f"\nChain length distribution:")
    counter = Counter(chain_lengths)
    for L in sorted(counter.keys()):
        pct = counter[L] / n_trials
        bar = '#' * min(40, int(pct * 200))
        print(f"  L={L:>2}: {counter[L]:>5} ({pct:.4f}) {bar}")

    # Big clusters
    print(f"\nLong chains (L >= 16):")
    long_count = sum(c for L, c in counter.items() if L >= 16)
    print(f"  Total: {long_count} ({long_count/n_trials:.4f})")
    print(f"  L=64 (full success): {counter.get(64, 0)} ({counter.get(64,0)/n_trials:.4f})")


if __name__ == "__main__":
    main()
