"""
Session 13h: Structure of convergent initial states for b-chain.

Found: 2.88% of random states give L=64 chain (freestart collision via adaptive δW).
Question: do these convergent states have predictable bit structure?

If structured (e.g., specific bits constrained): real efficiency gain.
If pseudo-random: just freestart collisions, known.

Test:
1. For each of 8 register × 32 bit positions, compute Pr(bit=1 | convergent) vs unconditional 0.5.
2. If any bit has |Pr - 0.5| > 0.05, it's structurally relevant.
3. Compute pairwise correlations between bits in convergent states.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import numpy as np
from mini_sha import single_round, gen_K, Sig0, Sig1, Ch, Maj
N = 32


def adaptive_round_simple(state0, state1, K_r, n=N):
    a0,b0,c0,d0,e0,f0,g0,h0 = state0
    a1,b1,c1,d1,e1,f1,g1,h1 = state1
    dh = h0 ^ h1
    dSig1 = Sig1(e0, n) ^ Sig1(e1, n)
    dCh = Ch(e0, f0, g0, n) ^ Ch(e1, f1, g1, n)
    dW = dh ^ dSig1 ^ dCh
    dSig0 = Sig0(a0, n) ^ Sig0(a1, n)
    dMaj = Maj(a0, b0, c0, n) ^ Maj(a1, b1, c1, n)
    dT2 = dSig0 ^ dMaj
    ok = ((dT2 >> (n-1)) & 1) == 0
    W0 = int(np.random.default_rng().integers(0, 1<<N))
    W1 = W0 ^ dW
    return single_round(state0, W0, K_r, n), single_round(state1, W1, K_r, n), ok


def main():
    rng = np.random.default_rng(42)
    K = gen_K(N, 64)

    print("=== Session 13h: Bit-pattern of convergent states ===\n")

    # Run many trials, collect convergent ones
    n_trials = 30000
    convergent = []
    for trial in range(n_trials):
        x = tuple(int(rng.integers(0, 1<<N)) for _ in range(8))
        x_flip = (x[0], x[1] ^ (1<<31), x[2], x[3], x[4], x[5], x[6], x[7])
        y0, y1 = x, x_flip
        all_ok = True
        for r in range(64):
            y0, y1, ok = adaptive_round_simple(y0, y1, K[r], N)
            if not ok:
                all_ok = False
                break
        if all_ok:
            convergent.append(x)

    print(f"Trials: {n_trials}, convergent: {len(convergent)} ({len(convergent)/n_trials:.4f})")

    if len(convergent) < 50:
        print("Too few for stats")
        return

    # Bit statistics: for each (register, bit_position), Pr(bit=1 | convergent)
    print("\n--- Per-bit statistics for convergent states ---")
    print("Looking for bits with |Pr - 0.5| > 0.05 (structurally relevant)")

    significant = []
    for reg_idx in range(8):
        for bit_pos in range(N):
            bit_vals = [(s[reg_idx] >> bit_pos) & 1 for s in convergent]
            pr1 = sum(bit_vals) / len(bit_vals)
            if abs(pr1 - 0.5) > 0.05:
                significant.append((reg_idx, bit_pos, pr1))

    if significant:
        print(f"\nFound {len(significant)} significantly biased bits:")
        for reg, bit, pr in sorted(significant, key=lambda x: -abs(x[2]-0.5))[:20]:
            reg_name = ['a','b','c','d','e','f','g','h'][reg]
            bias = pr - 0.5
            print(f"  {reg_name}[{bit:>2}]: Pr(=1) = {pr:.4f} (bias {bias:+.4f})")
    else:
        print("  No bit significantly biased (random structure within convergent set)")

    # Pairwise XOR statistics — find equality-like constraints
    print("\n--- Pairwise XOR (looking for a[i] = b[i] type constraints) ---")
    eq_pairs = []
    for r1 in range(8):
        for r2 in range(r1+1, 8):
            for bit in range(N):
                xor_vals = [((s[r1] ^ s[r2]) >> bit) & 1 for s in convergent]
                pr_eq = 1 - sum(xor_vals) / len(xor_vals)  # Pr(equal)
                if abs(pr_eq - 0.5) > 0.05:
                    eq_pairs.append((r1, r2, bit, pr_eq))

    print(f"Found {len(eq_pairs)} significantly biased XOR pairs (top 20 by bias):")
    for r1, r2, bit, pr_eq in sorted(eq_pairs, key=lambda x: -abs(x[3]-0.5))[:20]:
        names = ['a','b','c','d','e','f','g','h']
        bias = pr_eq - 0.5
        print(f"  {names[r1]}[{bit:>2}] = {names[r2]}[{bit:>2}]: Pr={pr_eq:.4f} (bias {bias:+.4f})")


if __name__ == "__main__":
    main()
