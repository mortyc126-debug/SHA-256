"""
Session 25c: Relaxed production phase — δstate non-zero ONLY in target register.

Drop HW=1 constraint (z3 can't decide it efficiently on full 32-bit BV).
Instead: δstate restricted to single register (any value within), other regs = 0.

This is "near-collision" target — concentrating differential into single register.
If found: combine with theorem absorption gives partial collision.

Plus: just check existence, no popcount.
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


def search_register_concentration(T, target_reg, IV=SHA256_IV, timeout_s=60):
    """Find (Wa, Wb) such that after T rounds, δstate is non-zero only in
    register target_reg (no constraint on which bits)."""
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = a, b, c, d, e, f, g, h

    K_vals = gen_K(N, max(T, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(min(T, 16))]
    Wb = [z3.BitVec(f'Wb_{i}', N) for i in range(min(T, 16))]
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

    diffs = [(a^a1), (b^b1), (c^c1), (d^d1), (e^e1), (f^f1), (g^g1), (h^h1)]
    for i in range(8):
        if i == target_reg:
            s.add(diffs[i] != 0)  # target reg has SOME diff
        else:
            s.add(diffs[i] == 0)  # other regs = 0

    s.add(z3.Or([Wa[i] != Wb[i] for i in range(min(T, 16))]))
    return s.check()


def main():
    print("=== Session 25c: Relaxed register concentration search ===\n")
    print("Find (Wa,Wb) producing δstate with non-zero ONLY in single register r.")
    print("(No HW constraint — any non-zero value OK in r.)\n")

    register_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    for T in [2, 3, 4, 5, 6, 8, 10, 12]:
        print(f"--- T = {T} rounds ---")
        for reg_idx, name in enumerate(register_names):
            t0 = time.time()
            result = search_register_concentration(T, reg_idx, timeout_s=30)
            elapsed = time.time() - t0
            if result == z3.sat:
                print(f"  {name}: SAT ({elapsed:.1f}s)")
            elif result == z3.unsat:
                print(f"  {name}: UNSAT ({elapsed:.1f}s)")
            else:
                print(f"  {name}: TIMEOUT ({elapsed:.1f}s)")
        print()


if __name__ == "__main__":
    main()
