"""
Session 25: Production phase search — find (M1, M2) giving HW=1 state diff at f-MSB.

Theorem absorption phase covers post-production: given state diff = f-MSB at
round T, can absorb in 3 more rounds to HW=0.

Total attack: T_production + 3 = full SHA rounds = 64 → T_production = 61.

But cost is exponential in T_production. Test: for what T can z3 find
(M1, M2) from fixed IV producing HW=1 at f register MSB at round T?

If T=20+ feasible: we'd have 23+round attack via theorem.
If T=10 only: 13+round attack.
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


def search_production(T, target_diff_pattern, IV=SHA256_IV, timeout_s=180):
    """Find (Wa, Wb) from same IV giving specific state diff after T rounds.
    target_diff_pattern: 8-tuple of 32-bit differences."""
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

    final_states = [a, b, c, d, e, f, g, h]
    final_states_b = [a1, b1, c1, d1, e1, f1, g1, h1]
    targets = [z3.BitVecVal(t, N) for t in target_diff_pattern]
    for i in range(8):
        s.add((final_states[i] ^ final_states_b[i]) == targets[i])
    s.add(z3.Or([Wa[i] != Wb[i] for i in range(min(T, 16))]))

    return s.check(), time.time()


def main():
    print("=== Session 25: Production phase — HW=1 at f-MSB after T rounds ===\n")
    print("Goal: find (M1, M2) from fixed IV with state diff = f-MSB only at round T.\n")

    # Target: state diff = f-MSB only (HW=1 at register f, position 31)
    target = [0, 0, 0, 0, 0, 1 << (N-1), 0, 0]
    print(f"Target diff (after T rounds): f-MSB = 2^31 only, HW = 1\n")

    for T in [3, 4, 6, 8, 10, 14, 18, 22, 28]:
        t0 = time.time()
        result, _ = search_production(T, target, timeout_s=180)
        elapsed = time.time() - t0
        if result == z3.sat:
            print(f"T={T:>2}: SAT ({elapsed:.1f}s) — production possible at {T} rounds")
        elif result == z3.unsat:
            print(f"T={T:>2}: UNSAT ({elapsed:.1f}s) — production impossible")
            break
        else:
            print(f"T={T:>2}: TIMEOUT ({elapsed:.1f}s)")
            break

if __name__ == "__main__":
    main()
