"""
Session 29b: Fixed single-bit δW pattern map.

Bug in 29: tested W[W_idx] for W_idx >= T which doesn't affect computation,
giving trivial SAT.

Fix: only test (W_idx, bit) where W_idx < T (flip is in active range).
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
from mini_sha import gen_K
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj
)
N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def search_single_bit_dW(T, W_idx, bit_pos, IV=SHA256_IV, timeout_s=60):
    """δW: only W[W_idx] differs in bit bit_pos. Find Wa giving collision.

    PRECONDITION: W_idx < T (flip must be in active range).
    """
    assert W_idx < min(T, 16), f"W_idx {W_idx} not in active range for T={T}"

    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = a, b, c, d, e, f, g, h

    K_vals = gen_K(N, max(T, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    n_vars = min(T, 16)
    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(n_vars)]
    bit_mask = 1 << bit_pos
    Wb = []
    for i in range(n_vars):
        if i == W_idx:
            Wb.append(Wa[i] ^ z3.BitVecVal(bit_mask, N))
        else:
            Wb.append(Wa[i])

    Wa_full = list(Wa); Wb_full = list(Wb)
    for r in range(16, T):
        Wa_full.append((Z3_sig1_msg(Wa_full[r-2]) + Wa_full[r-7] +
                        Z3_sig0_msg(Wa_full[r-15]) + Wa_full[r-16]))
        Wb_full.append((Z3_sig1_msg(Wb_full[r-2]) + Wb_full[r-7] +
                        Z3_sig0_msg(Wb_full[r-15]) + Wb_full[r-16]))

    for r in range(T):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa_full[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        a, b, c, d, e, f, g, h = T1_a + T2_a, a, b, c, d + T1_a, e, f, g
        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb_full[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        a1, b1, c1, d1, e1, f1, g1, h1 = T1_b + T2_b, a1, b1, c1, d1 + T1_b, e1, f1, g1

    s.add(a == a1, b == b1, c == c1, d == d1, e == e1, f == f1, g == g1, h == h1)
    return s.check()


def main():
    print("=== Session 29b: FIXED single-bit δW pattern map ===\n")
    print("Test only (W_idx, bit_pos) where W_idx < T.\n")

    test_bits = [0, 6, 11, 25, 31]

    for T in [5, 6, 8, 10]:
        print(f"--- T = {T} (testing W[0..{min(T,16)-1}]) ---")
        for W_idx in range(min(T, 16)):
            for bit_pos in test_bits:
                t0 = time.time()
                r = search_single_bit_dW(T, W_idx, bit_pos, timeout_s=30)
                elapsed = time.time() - t0
                v = "SAT" if r == z3.sat else ("UNSAT" if r == z3.unsat else "TO")
                marker = " ★" if v == "SAT" else ""
                print(f"  W[{W_idx:>2}][bit{bit_pos:>2}]: {v} ({elapsed:.1f}s){marker}")
        print()


if __name__ == "__main__":
    main()
