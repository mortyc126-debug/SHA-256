"""
Session 33: Real differential trail search — δW EARLY, low-HW LATE.

Bug in 32: δW at last round trivially gives HW=2 state at next round.
Real differential trail: introduce δW EARLY (W[0..2]), measure HW(δstate) at LATER round (5-10).

Test: δW restricted to W[0..2] only (W[3..15] same), find pair giving HW(δstate@T) low for various T.
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


def search_early_dW(T, hw_state_at_T, n_early_words, IV=SHA256_IV, timeout_s=120):
    """δW restricted to W[0..n_early_words-1] only.
    Find pair giving HW(δstate@round T) ≤ hw_state_at_T."""
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = a, b, c, d, e, f, g, h

    K_vals = gen_K(N, max(T, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    n_vars = min(T, 16)
    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(n_vars)]
    Wb = []
    for i in range(n_vars):
        if i < n_early_words:
            Wb.append(z3.BitVec(f'Wb_{i}', N))
        else:
            Wb.append(Wa[i])  # δW = 0 для W[n_early_words..]

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
    state_hw = z3.BitVecVal(0, 16)
    for diff in diffs:
        for bit in range(N):
            state_hw = state_hw + z3.ZeroExt(15, z3.Extract(bit, bit, diff))
    s.add(z3.ULE(state_hw, z3.BitVecVal(hw_state_at_T, 16)))

    # Non-trivial: at least one early W differs
    s.add(z3.Or([Wa[i] != Wb[i] for i in range(n_early_words)]))

    return s.check()


def main():
    print("=== Session 33: Real differential trail (δW early, low-HW late) ===\n")
    print("δW restricted to W[0..N-1]; HW(δstate) ≤ B at round T\n")

    print(f"{'T':>3} {'n_early':>8} {'HW≤':>5} {'result':>8} {'time':>8}")
    print("-" * 45)
    for n_early in [1, 2, 3]:
        for T in [4, 5, 6, 8]:
            for hw_target in [2, 4, 8]:
                if hw_target == 2 and n_early > 1:
                    continue  # too tight
                t0 = time.time()
                result = search_early_dW(T, hw_target, n_early, timeout_s=60)
                elapsed = time.time() - t0
                v = "SAT" if result == z3.sat else ("UNSAT" if result == z3.unsat else "TO")
                print(f"{T:>3} {n_early:>8} {hw_target:>5} {v:>8} {elapsed:>6.1f}s")
        print()


if __name__ == "__main__":
    main()
