"""
Session 18b: Extract concrete 6-round freestart collision pair.

z3 found SAT for k=6 f-flip (Session 18). Extract W_a, W_b values, verify
on real round function (mini_sha.single_round).
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
from mini_sha import single_round, gen_K
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj
)

N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def find_and_extract(k, flip_reg, IV=SHA256_IV, timeout_s=300):
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    iv_b = list(IV); iv_b[flip_reg] ^= (1 << (N-1))
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, 16)
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

    if s.check() == z3.sat:
        m = s.model()
        Wa = [m.eval(v).as_long() for v in Wa_vars]
        Wb = [m.eval(v).as_long() for v in Wb_vars]
        return Wa, Wb
    return None, None


def verify(IV, IV_flip, Wa, Wb, k):
    K = gen_K(N, k)
    sa = IV
    sb = IV_flip
    for r in range(k):
        sa = single_round(sa, Wa[r], K[r], N)
        sb = single_round(sb, Wb[r], K[r], N)
    diff = tuple(sa[i] ^ sb[i] for i in range(8))
    hw = sum(bin(d).count('1') for d in diff)
    return sa, sb, hw


def main():
    print("=== Session 18b: Extract & verify 6-round freestart collision ===\n")

    register_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for reg_idx in [5, 6, 7]:  # f, g, h
        for k in [3, 4, 6]:
            print(f"--- {register_names[reg_idx]}-MSB flip, k={k} ---")
            Wa, Wb = find_and_extract(k, reg_idx)
            if Wa is None:
                print("  No collision found")
                continue

            iv_b = list(SHA256_IV); iv_b[reg_idx] ^= (1 << (N-1))
            sa, sb, hw = verify(SHA256_IV, tuple(iv_b), Wa, Wb, k)
            print(f"  Wa = {[hex(w) for w in Wa]}")
            print(f"  Wb = {[hex(w) for w in Wb]}")
            print(f"  δW = {[hex(Wa[i]^Wb[i]) for i in range(k)]}")
            print(f"  state_a after k rounds: {[hex(s) for s in sa]}")
            print(f"  state_b after k rounds: {[hex(s) for s in sb]}")
            print(f"  HW(diff) = {hw} {'★ COLLISION VERIFIED' if hw == 0 else 'NOT collision'}")
            print()


if __name__ == "__main__":
    main()
