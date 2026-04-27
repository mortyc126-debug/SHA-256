"""
Session 25b: Flexible production phase — find ANY absorbable state diff.

Theorem absorbs SINGLE flip in any of f, g, h (k=3) or e (k=4) etc.
Search: from fixed IV, find (M1, M2) producing state diff such that
ONE register has non-zero, others = 0, and the non-zero register is in
absorbable set at given k.

For target round T:
- Theorem absorbs after k_abs more rounds where k_abs = pos(reg) + 3
- Total rounds = T + k_abs

Test: for T = 3, 5, 8, 12, 16, find ANY absorbable diff. No break on UNSAT.
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


def search_production_flexible(T, IV=SHA256_IV, timeout_s=120):
    """Find (Wa, Wb) from same IV producing state diff with HW=1 in some register."""
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

    # Encode "HW(δstate) = 1, located in {f, g, h, e}" via Or
    options = []
    for target_reg in [4, 5, 6, 7]:  # e, f, g, h
        # all other diffs = 0
        clauses = [diffs[i] == 0 for i in range(8) if i != target_reg]
        # target diff is single bit (popcount = 1)
        x = diffs[target_reg]
        # popcount = 1 iff x != 0 and x & (x-1) == 0
        clauses.append(x != 0)
        clauses.append((x & (x - 1)) == 0)
        options.append(z3.And(*clauses))

    s.add(z3.Or(*options))
    s.add(z3.Or([Wa[i] != Wb[i] for i in range(min(T, 16))]))

    return s.check()


def main():
    print("=== Session 25b: Flexible production phase ===\n")
    print("Find (Wa, Wb) with HW=1 state diff at single register e/f/g/h after T rounds.")
    print("If found at round T, total attack = T + (pos(reg)+3) rounds.\n")

    print(f"{'T':>3} | {'k_total (e/f/g/h)':>20} | result | time")
    print("-" * 60)
    results = {}
    for T in [3, 4, 5, 6, 8, 10, 12, 15, 18, 20]:
        t0 = time.time()
        result = search_production_flexible(T, timeout_s=120)
        elapsed = time.time() - t0
        results[T] = result
        # k_total: best case = T + 3 (h-flip absorbs in 3)
        # worst absorbable = T + 6 (e-flip absorbs in 6)
        if result == z3.sat:
            print(f"{T:>3} | {T+3} - {T+6}                | SAT     | {elapsed:.1f}s")
        elif result == z3.unsat:
            print(f"{T:>3} | -                    | UNSAT   | {elapsed:.1f}s")
        else:
            print(f"{T:>3} | -                    | TIMEOUT | {elapsed:.1f}s")

    print("\nResults summary:")
    sat_T = [T for T, r in results.items() if r == z3.sat]
    if sat_T:
        max_T = max(sat_T)
        print(f"Maximum production T with SAT: {max_T}")
        print(f"Total attack rounds achievable: {max_T + 3} to {max_T + 6}")


if __name__ == "__main__":
    main()
