"""
Session 32b: Extract concrete HW=2 intermediate pair at T=4 with δW HW≤4.

Session 32 found this as SAT in 18.5s. Get the actual values,
verify on real round function, see structural pattern.
"""
import sys
import time
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


def find_and_extract(T, hw_state, hw_W, IV=SHA256_IV, timeout_s=120):
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    a1, b1, c1, d1, e1, f1, g1, h1 = a, b, c, d, e, f, g, h

    K_vals = gen_K(N, max(T, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    n_vars = min(T, 16)
    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(n_vars)]
    Wb = [z3.BitVec(f'Wb_{i}', N) for i in range(n_vars)]
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
    s.add(z3.ULE(state_hw, z3.BitVecVal(hw_state, 16)))

    s.add(z3.Or([Wa[i] != Wb[i] for i in range(n_vars)]))

    w_hw = z3.BitVecVal(0, 16)
    for i in range(n_vars):
        d = Wa[i] ^ Wb[i]
        for bit in range(N):
            w_hw = w_hw + z3.ZeroExt(15, z3.Extract(bit, bit, d))
    s.add(z3.ULE(w_hw, z3.BitVecVal(hw_W, 16)))

    if s.check() == z3.sat:
        m = s.model()
        Wa_v = [m.eval(v).as_long() for v in Wa]
        Wb_v = [m.eval(v).as_long() for v in Wb]
        return Wa_v, Wb_v
    return None, None


def verify(IV, Wa, Wb, T):
    K = gen_K(N, T)
    sa = list(IV); sb = list(IV)
    for r in range(T):
        sa = list(single_round(tuple(sa), Wa[r], K[r], N))
        sb = list(single_round(tuple(sb), Wb[r], K[r], N))
    diffs = [sa[i] ^ sb[i] for i in range(8)]
    hws = [bin(d).count('1') for d in diffs]
    total_hw = sum(hws)
    return diffs, hws, total_hw


def main():
    print("=== Session 32b: Extract concrete intermediate state ===\n")

    for T, hw_target, hw_W in [(3, 2, 4), (4, 2, 4), (4, 4, 4)]:
        print(f"--- T={T}, HW(δstate)≤{hw_target}, HW(δW)≤{hw_W} ---")
        Wa, Wb = find_and_extract(T, hw_target, hw_W, timeout_s=120)
        if Wa is None:
            print("  Not found")
            continue
        diffs, hws, total_hw = verify(SHA256_IV, Wa, Wb, T)
        print(f"  Wa = {[hex(w) for w in Wa]}")
        print(f"  Wb = {[hex(w) for w in Wb]}")
        print(f"  δW = {[hex(Wa[i]^Wb[i]) for i in range(len(Wa))]}")
        delta_W_hw = sum(bin(Wa[i]^Wb[i]).count('1') for i in range(len(Wa)))
        print(f"  HW(δW) = {delta_W_hw}")
        print(f"  After {T} rounds: δstate per register HW = {hws}")
        print(f"  Total HW(δstate) = {total_hw}")
        print(f"  δstate = {[hex(d) for d in diffs]}")
        print()


if __name__ == "__main__":
    main()
