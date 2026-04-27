"""
Session 18: Direct freestart collision search via z3.

Different from chain criterion:
- Chain: 1-32 bits constrained per round
- Collision: ALL 256 state bits = 0 at end of k rounds

Setup:
- Initial state: IV ⊕ ΔIV where ΔIV = some chosen flip pattern (b-MSB)
- Find W[0..k-1] such that R^k(IV, W_a) = R^k(IV ⊕ ΔIV, W_b) where W_b derived adaptively.
- "Adaptive" W_b means at each round W_b[r] = W_a[r] ⊕ δW(state diff at round r).

Practical: instead of adaptive, just search for (W_a, W_b) pair freely.

Test: max k where z3 finds collision.
- k=3 with f-flip: trivial Pr=1 (Session 13d)
- k=8, 12, 16: ?
- k=20, 24: probably TIMEOUT
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


def search_collision(k, flip_reg, IV=SHA256_IV, timeout_s=300):
    """Find freestart collision: state diff = 0 after k rounds.
    flip_reg: index 0..7 of register to flip MSB initially.
    """
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    # Path A: IV
    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    # Path B: IV with flip
    iv_b = list(IV)
    iv_b[flip_reg] ^= (1 << (N-1))
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, max(k + 16, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    # Two independent message schedules
    Wa_vars = [z3.BitVec(f'Wa_{i}', N) for i in range(min(k, 16))]
    Wb_vars = [z3.BitVec(f'Wb_{i}', N) for i in range(min(k, 16))]
    Wa_full = list(Wa_vars)
    Wb_full = list(Wb_vars)
    for r in range(16, k):
        new_wa = (Z3_sig1_msg(Wa_full[r-2]) + Wa_full[r-7] +
                  Z3_sig0_msg(Wa_full[r-15]) + Wa_full[r-16])
        new_wb = (Z3_sig1_msg(Wb_full[r-2]) + Wb_full[r-7] +
                  Z3_sig0_msg(Wb_full[r-15]) + Wb_full[r-16])
        Wa_full.append(new_wa)
        Wb_full.append(new_wb)

    for r in range(k):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa_full[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_a = T1_a + T2_a; new_b = a; new_c = b; new_d = c
        new_e = d + T1_a; new_f = e; new_g = f; new_h = g

        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb_full[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_a1 = T1_b + T2_b; new_b1 = a1; new_c1 = b1; new_d1 = c1
        new_e1 = d1 + T1_b; new_f1 = e1; new_g1 = f1; new_h1 = g1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    # Final state diff = 0 (collision)
    s.add(a == a1, b == b1, c == c1, d == d1,
          e == e1, f == f1, g == g1, h == h1)
    # Disallow Wa = Wb trivially (must be different to be a real attack)
    s.add(z3.Or([Wa_vars[i] != Wb_vars[i] for i in range(len(Wa_vars))]))

    t0 = time.time()
    return s.check(), time.time() - t0


def main():
    print("=== Session 18: Direct freestart collision via z3 ===\n")
    print("State diff = 0 at end of k rounds. Two free messages Wa, Wb.\n")

    register_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for reg_idx, reg_name in enumerate(register_names):
        print(f"--- {reg_name}-MSB initial flip ---")
        for k in [3, 4, 6, 8, 10, 12, 14, 16]:
            result, elapsed = search_collision(k, reg_idx, timeout_s=180)
            if result == z3.sat:
                print(f"  k={k:>2}: SAT ({elapsed:.1f}s) — collision found")
            elif result == z3.unsat:
                print(f"  k={k:>2}: UNSAT ({elapsed:.1f}s) — no collision possible")
                break
            else:
                print(f"  k={k:>2}: TIMEOUT ({elapsed:.1f}s)")
                break
        print()


if __name__ == "__main__":
    main()
