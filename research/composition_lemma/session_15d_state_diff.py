"""
Session 15d: Analyze final state difference after 20-round b-chain.

z3 found W[0..15] giving 20-round Pr=1 chain (δT2[31]=0 each round).
But this only fixes 1 bit per round — final state diff may still be large.

Test: extract W from SAT, run real round function, plot state HW each round.
If HW stays small (< 64) — meaningful structural advantage.
If HW grows to ~128 (avalanche) — chain criterion is too weak alone.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
from session_15b_extended_search import search_chain_with_model
from mini_sha import single_round, gen_K, sigma_params, Sig0, Sig1, Ch, Maj, sig0_msg, sig1_msg
import z3

N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def trace_chain(W_values, k, IV=SHA256_IV):
    """Run chain, track state HW at each round."""
    K = gen_K(N, max(k + 16, 16))
    a, b, c, d, e, f, g, h = IV
    a1 = a; b1 = b ^ (1 << (N-1)); c1 = c; d1 = d
    e1 = e; f1 = f; g1 = g; h1 = h

    state0 = (a, b, c, d, e, f, g, h)
    state1 = (a1, b1, c1, d1, e1, f1, g1, h1)

    W_full = list(W_values)
    while len(W_full) < k:
        idx = len(W_full)
        new_w = (sig1_msg(W_full[idx-2], N) + W_full[idx-7] +
                 sig0_msg(W_full[idx-15], N) + W_full[idx-16]) & ((1 << N) - 1)
        W_full.append(new_w)

    print(f"  {'r':>3} | {'HW':>4} | per-reg HW (a b c d e f g h)")
    initial_diff = tuple(state0[i] ^ state1[i] for i in range(8))
    initial_hw = sum(bin(d).count('1') for d in initial_diff)
    per_reg_initial = [bin(d).count('1') for d in initial_diff]
    print(f"  IV  | {initial_hw:>4} | {' '.join(f'{x:>2}' for x in per_reg_initial)}")

    for r in range(k):
        a0, b0_, c0, d0, e0, f0, g0, h0 = state0
        a1_, b1_, c1_, d1_, e1_, f1_, g1_, h1_ = state1
        dh = h0 ^ h1_
        dSig1 = Sig1(e0, N) ^ Sig1(e1_, N)
        dCh = Ch(e0, f0, g0, N) ^ Ch(e1_, f1_, g1_, N)
        dW = dh ^ dSig1 ^ dCh
        W0 = W_full[r]
        W1 = W0 ^ dW

        state0 = single_round(state0, W0, K[r], N)
        state1 = single_round(state1, W1, K[r], N)

        diff = tuple(state0[i] ^ state1[i] for i in range(8))
        hw = sum(bin(d).count('1') for d in diff)
        per_reg = [bin(d).count('1') for d in diff]
        print(f"  {r:>3} | {hw:>4} | {' '.join(f'{x:>2}' for x in per_reg)}")

    return state0, state1


def main():
    print("=== Session 15d: State HW trace through b-chain ===\n")
    for k in [16, 20]:
        print(f"\n--- k = {k} ---")
        result, elapsed, W = search_chain_with_model(k, timeout_s=600)
        if result == z3.sat:
            print(f"z3 SAT in {elapsed:.1f}s. State HW per round:")
            trace_chain(W, k)
        else:
            print(f"NOT SAT")


if __name__ == "__main__":
    main()
