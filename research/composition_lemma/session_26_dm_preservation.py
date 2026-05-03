"""
Session 26: DM-aware "preservation" search for two-block collision.

Davies-Meyer feedforward: H_new = H_old + state_T (additive, mod 2^32).

For two-block collision via different chaining values H_1, H_1':
  H_1 - H_1' must equal state_T(H_1', M') - state_T(H_1, M)  (additive)

If both H_1 and H_1' differ only in single MSB of register r, then we need
state_T_diff = ±H_1_diff (depending on sign convention).

In XOR-trail (sufficient for MSB single-bit since no carry crosses bit 31):
  state_T_xor_diff(H_1, M, H_1', M') == H_1_xor_diff

So target search: (Wa, Wb) from (IV, IV ⊕ f-MSB) giving state_64 XOR diff = f-MSB
(NOT zero — preserved input diff).

Compare with theorem (state_64 diff = 0): DM-preservation is different.

Test: for k=3..16, find (Wa, Wb) achieving XOR-preservation. Different from
theorem absorption, possibly achievable at different k values.
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


def search_preservation(k, flip_reg, IV=SHA256_IV, timeout_s=120):
    """Find (Wa, Wb) such that state_k XOR diff equals input XOR diff
    (DM-aware preservation for two-block attack).
    """
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    iv_b = list(IV); iv_b[flip_reg] ^= (1 << (N-1))

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, max(k, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(min(k, 16))]
    Wb = [z3.BitVec(f'Wb_{i}', N) for i in range(min(k, 16))]
    Wa_full = list(Wa); Wb_full = list(Wb)
    for r in range(16, k):
        Wa_full.append((Z3_sig1_msg(Wa_full[r-2]) + Wa_full[r-7] +
                        Z3_sig0_msg(Wa_full[r-15]) + Wa_full[r-16]))
        Wb_full.append((Z3_sig1_msg(Wb_full[r-2]) + Wb_full[r-7] +
                        Z3_sig0_msg(Wb_full[r-15]) + Wb_full[r-16]))

    for r in range(k):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa_full[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        a, b, c, d, e, f, g, h = T1_a + T2_a, a, b, c, d + T1_a, e, f, g
        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb_full[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        a1, b1, c1, d1, e1, f1, g1, h1 = T1_b + T2_b, a1, b1, c1, d1 + T1_b, e1, f1, g1

    # Target: XOR diff at round k equals input XOR diff
    diffs = [(a^a1), (b^b1), (c^c1), (d^d1), (e^e1), (f^f1), (g^g1), (h^h1)]
    target = [0] * 8
    target[flip_reg] = 1 << (N-1)

    for i in range(8):
        s.add(diffs[i] == z3.BitVecVal(target[i], N))

    s.add(z3.Or([Wa[i] != Wb[i] for i in range(min(k, 16))]))

    return s.check()


def main():
    print("=== Session 26: DM-aware preservation search ===\n")
    print("For two-block collision via DM feedforward:")
    print("  state_k XOR diff must EQUAL input XOR diff (preserved, not absorbed)\n")

    register_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    for reg_idx in [5, 6, 7]:  # f, g, h
        name = register_names[reg_idx]
        print(f"--- {name}-MSB flip preservation ---")
        for k in [1, 2, 3, 4, 6, 8, 12, 16]:
            t0 = time.time()
            result = search_preservation(k, reg_idx, timeout_s=120)
            elapsed = time.time() - t0
            verdict = "SAT" if result == z3.sat else ("UNSAT" if result == z3.unsat else "TIMEOUT")
            print(f"  k={k:>2}: {verdict} ({elapsed:.1f}s)")
        print()


if __name__ == "__main__":
    main()
