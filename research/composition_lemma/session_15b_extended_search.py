"""
Session 15b: Extended b-chain search + W extraction + verification.

Session 15 found b-chain SAT for k up to 20 (no r=17 barrier!).
Now: extend k=22..32, extract concrete W from SAT, verify on real single_round.

Verification: with W returned by z3, run mini_sha and check actual chain length
matches. If yes → genuine 20+ round chain on real SHA-256 (XOR-trail Pr=1).
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
from mini_sha import single_round, gen_K, sigma_params, Sig0, Sig1, Ch, Maj
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj, search_chain
)

N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def search_chain_with_model(k, IV=SHA256_IV, timeout_s=600):
    """Same as search_chain but returns model (W values) on SAT."""
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1 = a; b1 = b ^ z3.BitVecVal(1 << (N-1), N); c1 = c; d1 = d
    e1 = e; f1 = f; g1 = g; h1 = h

    K_vals = gen_K(N, max(k + 16, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    W0_vars = [z3.BitVec(f'W0_{i}', N) for i in range(min(k, 16))]
    W0_full = list(W0_vars)
    for r in range(16, k):
        new_w = (Z3_sig1_msg(W0_full[r-2]) + W0_full[r-7] +
                 Z3_sig0_msg(W0_full[r-15]) + W0_full[r-16])
        W0_full.append(new_w)

    constraints = []
    for r in range(k):
        dSig0 = Z3_Sig0(a) ^ Z3_Sig0(a1)
        dMaj = Z3_Maj(a, b, c) ^ Z3_Maj(a1, b1, c1)
        dT2 = dSig0 ^ dMaj
        constraints.append(z3.Extract(N-1, N-1, dT2) == 0)

        dh = h ^ h1
        dSig1 = Z3_Sig1(e) ^ Z3_Sig1(e1)
        dCh = Z3_Ch(e, f, g) ^ Z3_Ch(e1, f1, g1)
        dW = dh ^ dSig1 ^ dCh

        W_path0 = W0_full[r]
        W_path1 = W_path0 ^ dW

        T1_0 = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + W_path0
        T2_0 = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_h = g; new_g = f; new_f = e
        new_e = d + T1_0; new_d = c; new_c = b; new_b = a
        new_a = T1_0 + T2_0

        T1_1 = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + W_path1
        T2_1 = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_h1 = g1; new_g1 = f1; new_f1 = e1
        new_e1 = d1 + T1_1; new_d1 = c1; new_c1 = b1; new_b1 = a1
        new_a1 = T1_1 + T2_1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    s.add(constraints)

    t0 = time.time()
    result = s.check()
    elapsed = time.time() - t0

    if result == z3.sat:
        m = s.model()
        W_values = []
        for var in W0_vars:
            v = m.eval(var, model_completion=True).as_long()
            W_values.append(v)
        return result, elapsed, W_values
    return result, elapsed, None


def verify_chain(W_values, k, IV=SHA256_IV):
    """Run real single_round with W_values + adaptive δW; check chain holds k rounds."""
    K = gen_K(N, max(k + 16, 16))
    a, b, c, d, e, f, g, h = IV
    a1 = a; b1 = b ^ (1 << (N-1)); c1 = c; d1 = d
    e1 = e; f1 = f; g1 = g; h1 = h

    state0 = (a, b, c, d, e, f, g, h)
    state1 = (a1, b1, c1, d1, e1, f1, g1, h1)

    # Schedule expansion
    W_full = list(W_values)
    while len(W_full) < k:
        from mini_sha import sig0_msg, sig1_msg
        idx = len(W_full)
        new_w = (sig1_msg(W_full[idx-2], N) + W_full[idx-7] +
                 sig0_msg(W_full[idx-15], N) + W_full[idx-16]) & ((1 << N) - 1)
        W_full.append(new_w)

    chain_ok = True
    for r in range(k):
        # Compute adaptive dW for path 1
        a0, b0_, c0, d0, e0, f0, g0, h0 = state0
        a1_, b1_, c1_, d1_, e1_, f1_, g1_, h1_ = state1
        dh = h0 ^ h1_
        dSig1 = Sig1(e0, N) ^ Sig1(e1_, N)
        dCh = Ch(e0, f0, g0, N) ^ Ch(e1_, f1_, g1_, N)
        dW = dh ^ dSig1 ^ dCh
        W0 = W_full[r]
        W1 = W0 ^ dW

        # Verify δT2[31] = 0
        dSig0 = Sig0(a0, N) ^ Sig0(a1_, N)
        dMaj = Maj(a0, b0_, c0, N) ^ Maj(a1_, b1_, c1_, N)
        dT2 = dSig0 ^ dMaj
        if (dT2 >> (N-1)) & 1 != 0:
            return False, r

        state0 = single_round(state0, W0, K[r], N)
        state1 = single_round(state1, W1, K[r], N)

    return True, k


def main():
    print("=== Session 15b: Extended b-chain SAT search + verification ===\n")
    print(f"Continuing from Session 15: k=20 SAT in 173s. Test k=22, 24, 28, 32.\n")

    for k in [22, 24, 28, 32]:
        print(f"k = {k}... ", end='', flush=True)
        result, elapsed, W = search_chain_with_model(k, timeout_s=900)
        if result == z3.sat:
            print(f"SAT in {elapsed:.1f}s. Verifying...")
            ok, actual_k = verify_chain(W, k)
            if ok:
                print(f"  ✓ Verified: chain holds {actual_k} rounds on real SHA-256")
            else:
                print(f"  ✗ Verification failed at round {actual_k}")
            print(f"  W[0..15] = {[hex(w) for w in W[:8]]}...")
        elif result == z3.unsat:
            print(f"UNSAT in {elapsed:.1f}s — barrier reached at k={k}")
            break
        else:
            print(f"TIMEOUT after {elapsed:.1f}s — practical barrier")
            break

if __name__ == "__main__":
    main()
