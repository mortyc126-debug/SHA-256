"""
Session 16: Calibrate constraint strength vs barrier round.

Session 15d showed: 1-bit constraint (δT2[31]=0) per round → solvable to k=20+
                    but state avalanche complete (HW≈128).

Wang-chain: 32-bit constraint (δe=0) per round → barrier at r=17.

Question: linear relationship between bits-per-round and barrier?
- 1 bit:  k=20+ (Session 15)
- 4 bits: k=?
- 8 bits: k=?
- 16 bits: k=?
- 32 bits: k=17 (Wang)

Test for each constraint strength: max k achievable.
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


def search_with_strength(k, n_constraint_bits, IV=SHA256_IV, timeout_s=60):
    """δT2 has n_constraint_bits bits constrained to 0 at each round.
    Constrained bits are the top n_constraint_bits bits (positions N-1..N-n).
    """
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
        # Constrain top n_constraint_bits bits
        for bit in range(N - n_constraint_bits, N):
            constraints.append(z3.Extract(bit, bit, dT2) == 0)

        dh = h ^ h1
        dSig1 = Z3_Sig1(e) ^ Z3_Sig1(e1)
        dCh = Z3_Ch(e, f, g) ^ Z3_Ch(e1, f1, g1)
        dW = dh ^ dSig1 ^ dCh

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
    result = s.check()
    return result, time.time() - t0


def find_max_k(n_constraint_bits, k_start=4, k_max=22, timeout_each=60):
    """Find largest k with SAT (binary search-ish)."""
    last_sat = 0
    for k in range(k_start, k_max + 1, 2):
        result, elapsed = search_with_strength(k, n_constraint_bits, timeout_s=timeout_each)
        if result == z3.sat:
            last_sat = k
            print(f"    k={k:>2}: SAT ({elapsed:.1f}s)")
        elif result == z3.unsat:
            print(f"    k={k:>2}: UNSAT ({elapsed:.1f}s) — barrier")
            return last_sat, "UNSAT"
        else:
            print(f"    k={k:>2}: TIMEOUT ({elapsed:.1f}s)")
            return last_sat, "TIMEOUT"
    return last_sat, "MAX_K"


def main():
    print("=== Session 16: Constraint strength vs barrier calibration ===\n")
    print("For each n bits constrained per round, find max k SAT achievable.\n")

    for n_bits in [1, 2, 4, 8, 16, 24, 32]:
        print(f"--- {n_bits} bits/round ---")
        max_k, status = find_max_k(n_bits, k_start=4, k_max=22, timeout_each=60)
        print(f"  Max k = {max_k} ({status})\n")


if __name__ == "__main__":
    main()
