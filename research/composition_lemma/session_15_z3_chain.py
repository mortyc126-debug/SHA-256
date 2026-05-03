"""
Session 15: z3 SAT search for b-chain W[0..15] from real SHA-256 IV.

After Session 14 confirmed random W has geometric Pr=0.5 per round, switch to
SAT-targeted search: find W[0..k-1] such that b-flip XOR-trail with adaptive
δW gives δT2[31] = 0 at all rounds 0..k-1.

This is Wang-style condition counting for left-side (b-direction).

Test: for k = 4, 6, 8, 12, 16, 18, 20, 24, ... how long until z3 TIMEOUT?
Expected: chain breaks around r=17 (Wang-barrier), since schedule expansion
locks in W[16..63] and constraints become unsatisfiable.

Also: from IV (or random pseudo-IV), is k=16 always solvable? If yes — we can
construct 16-round b-chain on real IV in seconds via z3.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import time
import z3
from mini_sha import gen_K, sigma_params

N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def Z3_rotr(x, r, n=N):
    return (z3.LShR(x, r)) | (x << (n - r))


def Z3_shr(x, r, n=N):
    return z3.LShR(x, r)


def Z3_Sig0(x, n=N):
    r = sigma_params(n)[0]
    return Z3_rotr(x, r[0]) ^ Z3_rotr(x, r[1]) ^ Z3_rotr(x, r[2])


def Z3_Sig1(x, n=N):
    r = sigma_params(n)[1]
    return Z3_rotr(x, r[0]) ^ Z3_rotr(x, r[1]) ^ Z3_rotr(x, r[2])


def Z3_sig0_msg(x, n=N):
    r = sigma_params(n)[2]
    return Z3_rotr(x, r[0]) ^ Z3_rotr(x, r[1]) ^ Z3_shr(x, r[2])


def Z3_sig1_msg(x, n=N):
    r = sigma_params(n)[3]
    return Z3_rotr(x, r[0]) ^ Z3_rotr(x, r[1]) ^ Z3_shr(x, r[2])


def Z3_Ch(e, f, g):
    return (e & f) ^ (~e & g)


def Z3_Maj(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)


def search_chain(k, IV=SHA256_IV, timeout_s=120):
    """Try to find W[0..k-1] for b-flip k-round chain from IV.

    Constraint: δT2[31] = 0 at each round (b-flip propagates without Maj-noise).
    """
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    # IV state as constants
    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = a, b ^ z3.BitVecVal(1 << (N-1), N), c, d, e, f, g, h

    # Precompute K
    K_vals = gen_K(N, max(k + 16, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    # Schedule: W[0..15] free, W[16..k-1] derived
    W0_vars = [z3.BitVec(f'W0_{i}', N) for i in range(min(k, 16))]
    W0_full = list(W0_vars)
    for r in range(16, k):
        new_w = (Z3_sig1_msg(W0_full[r-2]) + W0_full[r-7] + Z3_sig0_msg(W0_full[r-15]) + W0_full[r-16])
        W0_full.append(new_w)

    # W1 = W0 ^ adaptive δW per round
    # State of path 0 and path 1 evolves; track XOR diffs

    constraints = []
    for r in range(k):
        # Compute δT2[31] for current state diff
        dSig0 = Z3_Sig0(a) ^ Z3_Sig0(a1)
        dMaj = Z3_Maj(a, b, c) ^ Z3_Maj(a1, b1, c1)
        dT2 = dSig0 ^ dMaj
        # MSB constraint
        constraints.append(z3.Extract(N-1, N-1, dT2) == 0)

        # Compute adaptive δW (= δh + δΣ1(e) + δCh)
        dh = h ^ h1
        dSig1 = Z3_Sig1(e) ^ Z3_Sig1(e1)
        dCh = Z3_Ch(e, f, g) ^ Z3_Ch(e1, f1, g1)
        dW = dh ^ dSig1 ^ dCh

        W_path0 = W0_full[r]
        W_path1 = W_path0 ^ dW

        # Apply round to both paths
        T1_0 = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + W_path0
        T2_0 = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_h = g
        new_g = f
        new_f = e
        new_e = d + T1_0
        new_d = c
        new_c = b
        new_b = a
        new_a = T1_0 + T2_0

        T1_1 = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + W_path1
        T2_1 = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_h1 = g1
        new_g1 = f1
        new_f1 = e1
        new_e1 = d1 + T1_1
        new_d1 = c1
        new_c1 = b1
        new_b1 = a1
        new_a1 = T1_1 + T2_1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    s.add(constraints)

    t0 = time.time()
    result = s.check()
    elapsed = time.time() - t0
    return result, elapsed


def main():
    print("=== Session 15: z3 SAT search for b-chain from real IV ===\n")
    print(f"k = number of consecutive rounds with δT2[31] = 0 (b-chain success)")
    print(f"Expected: solvable for k <= 16; may TIMEOUT past schedule barrier r=17\n")

    for k in [2, 4, 6, 8, 10, 12, 14, 16, 17, 18, 20]:
        print(f"k = {k:>2}... ", end='', flush=True)
        result, elapsed = search_chain(k, timeout_s=180)
        if result == z3.sat:
            print(f"SAT in {elapsed:.1f}s — chain solvable")
        elif result == z3.unsat:
            print(f"UNSAT in {elapsed:.1f}s — NO W satisfies chain")
        else:
            print(f"TIMEOUT after {elapsed:.1f}s — too hard for z3")


if __name__ == "__main__":
    main()
