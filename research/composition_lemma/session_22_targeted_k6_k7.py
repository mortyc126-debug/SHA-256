"""
Session 22: Targeted k=6, k=7 verification — only test boundary registers.

Session 21 ran out of patience at k=6 (~3h projected for full scan).
Targeted version: only test the boundary register at each k, all 32 bits.
- k=6: test register c (predicted to become first SAT register at k=6)
- k=7: test register b (predicted to become first SAT register at k=7)
- Also test register a at k=7 (should still be UNSAT)

Confirms or refutes linear theorem from THEOREM_SHIFT_DEPTH.
Faster: 32 bits × maybe TIMEOUT 60s × 3 = ~30 min worst case.
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


def search_single_bit(k, reg, bit, IV=SHA256_IV, timeout_s=60):
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


def scan_register(k, reg, name, timeout=60):
    sat_count = 0
    unsat_count = 0
    timeout_count = 0
    start = time.time()
    for bit in range(N):
        r = search_single_bit(k, reg, bit, timeout_s=timeout)
        if r == z3.sat:
            sat_count += 1
        elif r == z3.unsat:
            unsat_count += 1
        else:
            timeout_count += 1
    elapsed = time.time() - start
    print(f"  {name}: SAT={sat_count}, UNSAT={unsat_count}, TIMEOUT={timeout_count} ({elapsed:.0f}s)")
    return sat_count, unsat_count, timeout_count


def main():
    print("=== Session 22: Targeted k=6, k=7 boundary register tests ===\n")
    print("Theorem prediction:")
    print("  k=6: c becomes SAT (32 bits), b/a stay UNSAT")
    print("  k=7: b becomes SAT (32 bits), a stays UNSAT")
    print()

    # k=6: test boundary c (predicted SAT) and b (predicted UNSAT)
    print("--- k=6 ---")
    scan_register(6, 2, 'c', timeout=60)
    scan_register(6, 1, 'b', timeout=60)

    # k=7: test boundary b (predicted SAT) and a (predicted UNSAT)
    print("\n--- k=7 ---")
    scan_register(7, 1, 'b', timeout=60)
    scan_register(7, 0, 'a', timeout=60)

    # k=8: test a (predicted SAT)
    print("\n--- k=8 ---")
    scan_register(8, 0, 'a', timeout=60)


if __name__ == "__main__":
    main()
