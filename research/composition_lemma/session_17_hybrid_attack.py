"""
Session 17: Hybrid attack — Wang-chain (right) + Maj-cancellation (left).

Combine two structural mechanisms:
1. Wang-chain: δe = 0 each round (forces δT1=δd, controls right-side)
2. Maj-cancellation: δT2[31..N-n_bits] = 0 each round (controls left-side)

Initial flip: e-MSB (Wang start) + b-MSB (Maj start).
Adaptive δW chosen to satisfy BOTH:
  δT1 = δh + δΣ1(e) + δCh(e,f,g) + δW = -δd (force δe=δd+δT1=0... no this doesn't work for e)

Actually Wang-chain uses adaptive δW such that δe_new = 0.
δe_new = δd + δT1. So δT1 = -δd (over Z) for δe_new = 0.
δT1 = δh + δΣ1(e) + δCh(e,f,g) + δW. So δW = -δd - δh - δΣ1 - δCh.

Combined attack:
- Initial: state diff = (0, 2^31, 0, 0, 2^31, 0, 0, 0) (b and e flipped)
- δW = -δd - δh - δΣ1(e) - δCh (Wang formula for δe=0)
- Constraint: δT2[bits] = 0 (left-side cancellation)
- Search W[0..15] for k rounds. Find max k.
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
from mini_sha import gen_K, sigma_params
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj
)

N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def search_hybrid(k, n_constraint_bits=1, IV=SHA256_IV, timeout_s=120):
    """Hybrid: Wang-chain (δe=0) + Maj-cancellation top n_bits.
    Initial flip: b-MSB + e-MSB.
    """
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    flip = z3.BitVecVal(1 << (N-1), N)
    a1 = a; b1 = b ^ flip; c1 = c; d1 = d
    e1 = e ^ flip; f1 = f; g1 = g; h1 = h

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
        # Maj-cancellation constraint (left-side, top n bits)
        dSig0 = Z3_Sig0(a) ^ Z3_Sig0(a1)
        dMaj = Z3_Maj(a, b, c) ^ Z3_Maj(a1, b1, c1)
        dT2 = dSig0 ^ dMaj
        for bit in range(N - n_constraint_bits, N):
            constraints.append(z3.Extract(bit, bit, dT2) == 0)

        # Wang-style adaptive δW for δe=0 next round
        # δe_new = δd + δT1 (over Z); want = 0 → δT1 = -δd
        # δT1 = δh + δΣ1(e) + δCh + δW → δW = -δd - δh - δΣ1 - δCh
        dd = d ^ d1  # Note: this is XOR diff, not Z diff. For Wang exactness we'd need additive.
        # For SAT we use XOR diff approx (matches XOR-trail framework)
        dh = h ^ h1
        dSig1 = Z3_Sig1(e) ^ Z3_Sig1(e1)
        dCh = Z3_Ch(e, f, g) ^ Z3_Ch(e1, f1, g1)
        dW = dd ^ dh ^ dSig1 ^ dCh  # XOR-version of δW = -δd - δh - δΣ1 - δCh

        W_path0 = W0_full[r]
        W_path1 = W_path0 ^ dW

        T1_0 = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + W_path0
        T2_0 = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_a, new_b, new_c, new_d = T1_0 + T2_0, a, b, c
        new_e, new_f, new_g, new_h = d + T1_0, e, f, g

        T1_1 = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + W_path1
        T2_1 = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_a1, new_b1, new_c1, new_d1 = T1_1 + T2_1, a1, b1, c1
        new_e1, new_f1, new_g1, new_h1 = d1 + T1_1, e1, f1, g1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    s.add(constraints)
    t0 = time.time()
    return s.check(), time.time() - t0


def main():
    print("=== Session 17: Hybrid Wang-Maj attack ===\n")
    print("Initial flip: b-MSB + e-MSB. Adaptive δW for Wang δe=0.")
    print("Plus left-side Maj-cancellation constraint top N bits.\n")

    for n_bits in [1, 4, 8]:
        print(f"--- {n_bits} bits/round Maj cancellation ---")
        for k in [4, 8, 12, 16, 20, 24]:
            result, elapsed = search_hybrid(k, n_bits, timeout_s=120)
            if result == z3.sat:
                print(f"  k={k:>2}: SAT ({elapsed:.1f}s)")
            elif result == z3.unsat:
                print(f"  k={k:>2}: UNSAT ({elapsed:.1f}s) — barrier")
                break
            else:
                print(f"  k={k:>2}: TIMEOUT ({elapsed:.1f}s)")
                break
        print()


if __name__ == "__main__":
    main()
