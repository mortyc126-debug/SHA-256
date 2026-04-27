"""
Session 13f: Distribution of b-chain success length под adaptive δW.

For each random trial: apply b-flip + adaptive δW. Track at each round
whether δMaj cancels (state has a[31]=c[31] / similar at that round).
Length of chain = max r where δMaj=0 for all rounds 0..r.

If distribution geometric (Pr ≈ 0.5 each round, independent): mean length ≈ 2.
If correlations exist (longer chains than geometric): exploitable structure.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from collections import Counter
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj
N = 32; MASK = (1 << N) - 1


def adaptive_round_track(state0, state1, K_r, n=N):
    """Apply round; return (new0, new1, dT2_zero).
    dT2_zero = True iff δT2 at MSB position 31 was zero (chain succeeded this round).
    """
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1
    # Compute δT2 = δΣ0(a) + δMaj(a,b,c)
    dSig0 = Sig0(a0, n) ^ Sig0(a1, n)
    dMaj = Maj(a0, b0, c0, n) ^ Maj(a1, b1, c1, n)
    dT2 = dSig0 ^ dMaj
    # Check MSB bit of dT2
    chain_ok_31 = (dT2 >> (n-1)) & 1 == 0
    # Adaptive δW for δT1
    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh
    W0 = int(np.random.default_rng().integers(0, 1<<N))
    W1 = W0 ^ dW
    return single_round(state0, W0, K_r, n), single_round(state1, W1, K_r, n), chain_ok_31, dT2


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 32)
    print("=== Session 13f: b-chain length distribution ===\n")
    n_trials = 5000
    max_R = 25

    # Stats:
    chain_lengths = []  # max consecutive rounds where δT2[31]=0
    dt2_pattern = []  # for each trial, list of bools per round

    for trial in range(n_trials):
        x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
        x_flip = (x[0], x[1] ^ (1<<31), x[2], x[3], x[4], x[5], x[6], x[7])
        y0, y1 = x, x_flip
        chain_len = 0
        all_oks = []
        for r in range(max_R):
            y0, y1, ok, _ = adaptive_round_track(y0, y1, K[r], N)
            all_oks.append(ok)
            if ok:
                chain_len = r + 1  # rounds 0..r all ok so far
            else:
                break
        chain_lengths.append(chain_len)

    # Histogram
    print(f"Distribution of chain length (rounds where δT2[31]=0 consecutively from start):")
    counter = Counter(chain_lengths)
    for L in sorted(counter.keys()):
        pct = counter[L] / n_trials
        bar = '#' * min(50, int(pct * 200))
        print(f"  L={L:>2}: {counter[L]:>5} ({pct:.4f}) {bar}")

    # Theoretical comparison: if Pr=0.5 independent geometric distribution
    # Pr(L >= k) = 0.5^k, Pr(L = k) = 0.5^k - 0.5^{k+1} = 0.5^{k+1}
    print(f"\nGeometric baseline (Pr=0.5 independent):")
    for L in range(0, 8):
        theoretical = 0.5 ** (L + 1)
        observed = counter.get(L, 0) / n_trials
        ratio = observed / theoretical if theoretical > 0 else 0
        print(f"  L={L}: observed={observed:.4f}, theory={theoretical:.4f}, ratio={ratio:.2f}×")


if __name__ == "__main__":
    main()
