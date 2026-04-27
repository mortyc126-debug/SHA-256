"""
Session 13e: Test if state constraint a[31]=c[31] enables b-chain Pr=1.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj
N = 32; MASK = (1 << N) - 1

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
    rng = np.random.default_rng(42)
    K = gen_K(N, 20)
    print("=== Session 13e: State constraint a[31]=c[31] for b-chain ===\n")
    n_trials = 2000

    for constraint_label, constraint_fn in [
        ('NO constraint (baseline 13d)', lambda x: x),
        ('a[31]=c[31] initial only', lambda x: (x[0], x[1], (x[2] & ~(1<<31)) | (x[0] & (1<<31)), x[3], x[4], x[5], x[6], x[7])),
    ]:
        print(f"\n--- {constraint_label} ---")
        for max_T in [1, 2, 3, 5, 8, 10, 12, 16]:
            counter = Counter()
            for trial in range(n_trials):
                x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
                x = constraint_fn(x)
                x_flip = (x[0], x[1] ^ (1<<31), x[2], x[3], x[4], x[5], x[6], x[7])
                y0, y1 = x, x_flip
                for r in range(max_T):
                    y0, y1 = adaptive_round(y0, y1, K[r], N)
                diff = tuple(y0[i] ^ y1[i] for i in range(8))
                counter[diff] += 1
            top = counter.most_common(1)[0]
            top_pr = top[1] / n_trials
            top_hw = sum(bin(w).count('1') for w in top[0])
            unique = len(counter)
            verdict = "Pr=1" if top_pr >= 0.99 else ("strong" if top_pr >= 0.5 else ("partial" if top_pr >= 0.1 else "weak/uniform"))
            print(f"  T={max_T:>2}: Pr={top_pr:.4f} HW={top_hw:>3} unique={unique:>4} | {verdict}")

if __name__ == "__main__":
    main()
