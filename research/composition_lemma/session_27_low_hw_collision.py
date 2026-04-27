"""
Session 27: Low-HW δW collision search — actual differential cryptanalysis target.

Standard differential cryptanalysis: find (M, M') with HW(δM) small such that
final state diff = 0 from FIXED IV (real collision target).

For SHA-256 fixed IV (single-block):
- Same IV both paths
- Different W's: W_a vs W_b
- After T rounds, want state diff = 0

Constraint HW(δW) ≤ B for various B and T.
- HW(δW) = 0: trivial (W_a = W_b, no collision)
- HW(δW) ≤ 5: very constrained, should be feasible only at small T
- HW(δW) ≤ 32: moderate
- HW(δW) ≤ 256: full Hamming budget across 16 W words

This is REAL collision target on full SHA-256.
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


def search_low_hw_collision(T, hw_budget, IV=SHA256_IV, timeout_s=180):
    """Find (Wa, Wb) from same IV giving state collision after T rounds,
    with total HW(Wa XOR Wb) ≤ hw_budget."""
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    # Same IV both paths
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

    # State collision
    s.add(a == a1, b == b1, c == c1, d == d1, e == e1, f == f1, g == g1, h == h1)

    # Non-trivial: at least one W differs
    s.add(z3.Or([Wa[i] != Wb[i] for i in range(min(T, 16))]))

    # HW budget on δW
    # Sum of popcounts of (Wa[i] ^ Wb[i]) ≤ hw_budget
    # Use bit-by-bit encoding via Concat trick: extend to 8-bit and add
    # Simpler: enforce specific bits to be equal
    # Actually let me use z3 arithmetic on extracted bits
    total_hw = z3.BitVecVal(0, 16)  # 16-bit accumulator, plenty
    for i in range(min(T, 16)):
        diff = Wa[i] ^ Wb[i]
        for bit in range(N):
            total_hw = total_hw + z3.ZeroExt(15, z3.Extract(bit, bit, diff))
    s.add(z3.ULE(total_hw, z3.BitVecVal(hw_budget, 16)))

    return s.check()


def main():
    print("=== Session 27: Low-HW δW collision search ===\n")
    print("Target: SAME IV, find (M, M') with HW(δM) ≤ B s.t. final state diff = 0\n")

    print(f"{'T':>3} {'HW≤':>5} {'result':>10} {'time':>8}")
    print("-" * 40)
    for T in [4, 6, 8, 12, 16, 20]:
        for hw_budget in [2, 5, 10, 32]:
            t0 = time.time()
            result = search_low_hw_collision(T, hw_budget, timeout_s=120)
            elapsed = time.time() - t0
            verdict = "SAT" if result == z3.sat else ("UNSAT" if result == z3.unsat else "TIMEOUT")
            print(f"{T:>3} {hw_budget:>5} {verdict:>10} {elapsed:>6.1f}s")
        print()


if __name__ == "__main__":
    main()
