"""
Session 24: SAT search for δW that ABSORBS flip AND has trivial schedule extension.

Theorem says: f-flip can be absorbed in 3 rounds via δW = [0, 0, 2^31]. Then
states are equal for round 4 onwards.

BUT: SHA-256 message schedule expands W[16..63] from W[0..15]. For paths to
remain equal past round 15, need δW[16..63] = 0.

Schedule formula: δW[r] = σ1(δW[r-2]) + δW[r-7] + σ0(δW[r-15]) + δW[r-16]

For δW = [0, 0, 2^31, 0, 0, ..., 0]:
- δW[16] = σ1(0)+0+σ0(0)+0 = 0 ✓
- δW[17] = σ1(0)+0+σ0(2^31)+0 = σ0(2^31) ≠ 0 ✗

Question: is there δW absorbing f-flip in 3 rounds AND giving δW[16..63] = 0?

If yes → full 64-round collision construction. If no → r=17 barrier proven for
this approach via schedule constraint.
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
import z3
from mini_sha import gen_K, sigma_params
from session_15_z3_chain import (
    Z3_rotr, Z3_shr, Z3_Sig0, Z3_Sig1, Z3_sig0_msg, Z3_sig1_msg,
    Z3_Ch, Z3_Maj
)
N = 32
SHA256_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
             0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)


def search(flip_reg, IV=SHA256_IV, k=3, timeout_s=300):
    """Search for δW absorbing flip AND extending zero through schedule."""
    s = z3.Solver()
    s.set('timeout', timeout_s * 1000)

    a, b, c, d, e, f, g, h = [z3.BitVecVal(v, N) for v in IV]
    iv_b = list(IV); iv_b[flip_reg] ^= (1 << (N-1))
    a1, b1, c1, d1, e1, f1, g1, h1 = [z3.BitVecVal(v, N) for v in iv_b]

    K_vals = gen_K(N, 64)
    K_z3 = [z3.BitVecVal(kv, N) for kv in K_vals]

    Wa = [z3.BitVec(f'Wa_{i}', N) for i in range(16)]
    Wb = [z3.BitVec(f'Wb_{i}', N) for i in range(16)]

    # Step 1: Apply k rounds, require state convergence at round k
    for r in range(k):
        T1_a = h + Z3_Sig1(e) + Z3_Ch(e, f, g) + K_z3[r] + Wa[r]
        T2_a = Z3_Sig0(a) + Z3_Maj(a, b, c)
        a, b, c, d, e, f, g, h = T1_a + T2_a, a, b, c, d + T1_a, e, f, g

        T1_b = h1 + Z3_Sig1(e1) + Z3_Ch(e1, f1, g1) + K_z3[r] + Wb[r]
        T2_b = Z3_Sig0(a1) + Z3_Maj(a1, b1, c1)
        a1, b1, c1, d1, e1, f1, g1, h1 = T1_b + T2_b, a1, b1, c1, d1 + T1_b, e1, f1, g1

    # Constraint 1: states equal at round k (collision)
    s.add(a == a1, b == b1, c == c1, d == d1, e == e1, f == f1, g == g1, h == h1)

    # Constraint 2: δW[i] = 0 for i ≥ k (since after states equal, paths must use same W)
    for i in range(k, 16):
        s.add(Wa[i] == Wb[i])

    # Constraint 3: schedule expansion gives zero δW for r >= 16
    # Build δW[16..63] symbolically and require all = 0
    dW0_15 = [Wa[i] ^ Wb[i] for i in range(16)]
    dW = list(dW0_15)
    for r in range(16, 64):
        new_dw = (Z3_sig1_msg(dW[r-2]) + dW[r-7] + Z3_sig0_msg(dW[r-15]) + dW[r-16])
        dW.append(new_dw)
        s.add(new_dw == 0)

    # Constraint 4: at least one δW differs (non-trivial)
    s.add(z3.Or([Wa[i] != Wb[i] for i in range(k)]))

    t0 = time.time()
    return s.check(), time.time() - t0


def main():
    print("=== Session 24: Full 64-round collision via theorem + schedule kernel ===\n")
    print("For each right-side flip (f, g, h), search for δW that:")
    print("  1) Absorbs flip in pos+3 rounds (theorem)")
    print("  2) Has δW[16..63] = 0 from schedule expansion")
    print("If both → FULL 64-round collision from single-bit IV flip\n")

    for reg, name, k in [(5, 'f', 3), (6, 'g', 3), (7, 'h', 3)]:
        print(f"--- {name}-MSB flip, k={k} (theorem absorption) + schedule trivial ---")
        result, elapsed = search(reg, k=k, timeout_s=600)
        print(f"  Result: {result} ({elapsed:.1f}s)")
        if result == z3.sat:
            print(f"  ★★★ FULL 64-ROUND COLLISION CONSTRUCTION FOUND ★★★")
        elif result == z3.unsat:
            print(f"  Barrier: schedule constraint blocks extension")
        else:
            print(f"  Inconclusive")


if __name__ == "__main__":
    main()
