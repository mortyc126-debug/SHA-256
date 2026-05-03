"""
Session 20: All single-bit flip k=3 collision search (8 regs × 32 bits = 256 patterns).

Session 18-19 found: only {f, g, h} MSB subset gives k=3 SAT.
Extend: do LOWER bits give different patterns?

Lower bits don't have carry-out (which makes MSB special). Maybe lower-bit
flips of left-side registers SAT where MSB is UNSAT.
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
    names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    print("=== Session 20: All 256 single-bit flips × k=3 collision ===\n")
    print(f"{'reg':<4} | {'SAT bits (decreasing)':<60}")
    print("-" * 70)

    total_sat = 0
    by_reg_sat = {n: [] for n in names}

    for reg in range(8):
        sat_bits = []
        for bit in range(N):
            r = search_single_bit(3, reg, bit, timeout_s=5)
            if r == z3.sat:
                sat_bits.append(bit)
                total_sat += 1
        by_reg_sat[names[reg]] = sat_bits
        bits_str = ', '.join(str(b) for b in sorted(sat_bits, reverse=True))
        print(f"{names[reg]:<4} | {bits_str:<60} (n={len(sat_bits)})")

    print(f"\nTotal SAT: {total_sat} / 256 bits")
    print(f"\nPer-register count:")
    for n in names:
        print(f"  {n}: {len(by_reg_sat[n])} bits")


if __name__ == "__main__":
    main()
