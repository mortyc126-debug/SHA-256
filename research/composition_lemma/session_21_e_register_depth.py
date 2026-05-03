"""
Session 21: When does register e become collision-vulnerable?

Session 20: k=3, only f, g, h give collision.
Question: at what k does register e (leftmost right-side) start giving SAT?

Test k = 3, 4, 5, 6, 7 for ALL 32 bits of register e.

Expectation: e flip propagates through Σ1 + Ch with limited δW cancellation.
Maybe k=4 or k=5 first SAT for e bits.
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


def search_single_bit(k, reg, bit, IV=SHA256_IV, timeout_s=10):
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    iv_b = list(IV); iv_b[reg] ^= (1 << bit)
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, max(k, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    Wa_vars = [z3.BitVec(f'Wa_{i}', N) for i in range(k)]
    Wb_vars = [z3.BitVec(f'Wb_{i}', N) for i in range(k)]

    for r in range(k):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa_vars[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_a = T1_a + T2_a; new_b = a; new_c = b; new_d = c
        new_e = d + T1_a; new_f = e; new_g = f; new_h = g

        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb_vars[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_a1 = T1_b + T2_b; new_b1 = a1; new_c1 = b1; new_d1 = c1
        new_e1 = d1 + T1_b; new_f1 = e1; new_g1 = f1; new_h1 = g1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    s.add(a == a1, b == b1, c == c1, d == d1,
          e == e1, f == f1, g == g1, h == h1)
    s.add(z3.Or([Wa_vars[i] != Wb_vars[i] for i in range(len(Wa_vars))]))

    return s.check()


def main():
    print("=== Session 21: e-register depth analysis ===\n")
    print("For k = 3, 4, 5, 6, 7: count bits where collision exists for e-flip")
    print()

    # Test all 8 registers at multiple k values
    print(f"{'k':>3} | a   b   c   d   e   f   g   h | total")
    print("-" * 60)
    names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    for k in [3, 4, 5, 6, 7]:
        timeout = 5 if k <= 4 else (15 if k <= 5 else 30)
        counts = []
        for reg in range(8):
            sat_count = 0
            for bit in range(N):
                r = search_single_bit(k, reg, bit, timeout_s=timeout)
                if r == z3.sat:
                    sat_count += 1
            counts.append(sat_count)
        total = sum(counts)
        line = f"{k:>3} | " + ' '.join(f'{c:>3}' for c in counts) + f" | {total:>3}"
        print(line)


if __name__ == "__main__":
    main()
