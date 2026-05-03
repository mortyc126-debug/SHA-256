"""
Session 23: IV-independence test for Register-Position Collision-Depth Theorem.

Theorem (Sessions 18-22): k-round freestart collision from single-bit IV flip
exists IFF k ≥ pos(register) + 3, where pos(h)=0, pos(g)=1, ..., pos(a)=7.

Verified for SHA-256 IV. Question: does theorem hold for ANY IV?

If yes: theorem gives "many-IV" SFS collision pattern, satisfying two-block
conversion criterion (which requires 2^X IVs work). This makes theorem
applicable to fixed-IV collision construction.

Test: try several random IVs, verify pattern same.
- For each random IV: test k=3 with f/g/h flips (predicted SAT) and a/b/c/d/e (predicted UNSAT)
- Test k=4 with e flip (predicted SAT becomes new register)
- Test k=5 with d flip (predicted SAT)
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
import numpy as np
from mini_sha import gen_K
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj
)

N = 32


def search_collision(k, IV, flip_reg, bit, timeout_s=30):
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    iv_b = list(IV); iv_b[flip_reg] ^= (1 << bit)
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, max(k, 16))
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    Wa_vars = [z3.BitVec(f'Wa_{i}', N) for i in range(k)]
    Wb_vars = [z3.BitVec(f'Wb_{i}', N) for i in range(k)]

    for r in range(k):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa_vars[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        new_a, new_b, new_c, new_d = T1_a + T2_a, a, b, c
        new_e, new_f, new_g, new_h = d + T1_a, e, f, g

        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb_vars[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        new_a1, new_b1, new_c1, new_d1 = T1_b + T2_b, a1, b1, c1
        new_e1, new_f1, new_g1, new_h1 = d1 + T1_b, e1, f1, g1

        a, b, c, d, e, f, g, h = new_a, new_b, new_c, new_d, new_e, new_f, new_g, new_h
        a1, b1, c1, d1, e1, f1, g1, h1 = new_a1, new_b1, new_c1, new_d1, new_e1, new_f1, new_g1, new_h1

    s.add(a == a1, b == b1, c == c1, d == d1, e == e1, f == f1, g == g1, h == h1)
    s.add(z3.Or([Wa_vars[i] != Wb_vars[i] for i in range(len(Wa_vars))]))
    return s.check()


def main():
    rng = np.random.default_rng(42)
    print("=== Session 23: Theorem IV-independence test ===\n")

    n_random_ivs = 4
    print(f"Testing {n_random_ivs} random IVs + real SHA-256 IV...\n")

    SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
                 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)

    test_ivs = [SHA256_IV]
    for _ in range(n_random_ivs):
        iv = tuple(int(rng.integers(0, 1 << N)) for _ in range(8))
        test_ivs.append(iv)

    names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    for iv_idx, IV in enumerate(test_ivs):
        label = "REAL SHA-256 IV" if iv_idx == 0 else f"Random IV #{iv_idx}"
        print(f"--- {label}: IV = {[hex(x) for x in IV[:3]]}... ---")

        # k=3: predict SAT for f, g, h; UNSAT for others
        for reg_idx, name in enumerate(names):
            results = []
            for bit in [0, 31, 15]:  # sample 3 bit positions
                r = search_collision(3, IV, reg_idx, bit, timeout_s=20)
                results.append(str(r).replace('z3.', ''))
            expected = "SAT" if reg_idx >= 5 else "UNSAT"
            actual = " ".join(results)
            match = "✓" if all(r in expected or (expected == "UNSAT" and r in ['unsat', 'unknown']) for r in results) else "?"
            print(f"  k=3, {name}: {actual} (expected {expected}) {match}")
        print()


if __name__ == "__main__":
    main()
