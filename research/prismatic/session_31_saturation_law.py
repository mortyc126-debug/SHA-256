"""
Session 31: Test the hypothesis T_sat = nilp(N_{Σ_1}) (Session 28 observation).

Session 28 reported: bare round R has dependency saturation at T = 11
                    = nilpotency of N_{Σ_1} (Theorem 24.1).

If this is causal (not coincidence), then changing Σ_1's rotation constants
to alter its nilpotency should shift T_sat by the same amount.

Test plan:
1. For several alternative Σ_1' = ROTR_{r1} ⊕ ROTR_{r2} ⊕ ROTR_{r3} with KNOWN
   nilpotencies (computed via Theorem 24.1: ⌈32/d⌉), build the bare round R',
   compute T_sat'.
2. Compare T_sat' vs nilp(N_{Σ_1'}).
3. If T_sat' = nilp(N_{Σ_1'}) for all variants → upgrade Theorem 28.1 to a real
   theorem with proof.
4. If T_sat' ≠ nilp → the original observation was coincidence; revise.
"""
import numpy as np
from session_25_round import (build_sigma_0, gf2_rank, find_order, matpow_mod2,
                                rotr_full, N, NUM_REGS, DIM, block_eye, block_zero)
from session_27_quadratic import build_round_anf, REG_OFFSETS
from session_28_saturation import boolean_matmul, build_dependency_matrix
from session_24_minpoly import smallest_surviving_positive
from math import ceil


def custom_sigma_1(rotations, n=N):
    """Build alternative Σ_1' = sum of ROTR_r for r in rotations (in s-basis)."""
    M = np.zeros((n, n), dtype=np.uint8)
    for r in rotations:
        M ^= rotr_full(r, n)
    return M & 1


def predicted_nilpotency(rotations, n=N):
    """Theorem 24.1: nilp = ⌈n/d⌉ where d = smallest surviving position."""
    if len(rotations) % 2 == 0:
        return None  # |R| even, not unipotent
    d = smallest_surviving_positive(list(rotations), n)
    if d is None:
        return 1
    return ceil(n / d)


def build_round_with_custom_sigma1(S0_mat, S1_mat):
    """Same as build_round_linear but with custom S1.
    But for diffusion we also need ANF (for Ch dependencies).
    Diffusion via nonlinear ANF needs symbolic round; we approximate by
    linear-only diffusion (Ch contributes (e, f, g) inputs to a' and e').
    """
    I = block_eye()
    Z = block_zero()
    blocks = [[Z for _ in range(NUM_REGS)] for _ in range(NUM_REGS)]
    blocks[0][0] = S0_mat        # Σ_0(a) → a'
    blocks[0][4] = S1_mat        # Σ_1(e) → a'
    blocks[0][7] = I             # h → a'
    blocks[1][0] = I
    blocks[2][1] = I
    blocks[3][2] = I
    blocks[4][3] = I
    blocks[4][4] = S1_mat
    blocks[4][7] = I
    blocks[5][4] = I
    blocks[6][5] = I
    blocks[7][6] = I
    R = np.block(blocks).astype(np.uint8) & 1
    return R


def build_dependency_with_custom_sigma1(S0_mat, S1_mat):
    """Boolean dependency matrix for round with custom Σ_1.
    Includes Ch nonlinearity: a' depends on (e, f, g); e' depends on (e, f, g).
    Also depends on a, b, c via Maj.
    """
    # Linear part dependencies
    R_lin = build_round_with_custom_sigma1(S0_mat, S1_mat)
    D_lin = (R_lin != 0).astype(np.uint8)

    # Nonlinear contributions via Ch and Maj (per-bit; diagonal in bit position):
    # a': Maj(a,b,c) adds dependency on a,b,c (bit-i of a' depends on bit-i of a,b,c)
    #     Ch(e,f,g) adds dependency on e,f,g (bit-i)
    # e': Ch(e,f,g) adds dependency on e,f,g (bit-i)
    for i in range(N):
        a_idx = REG_OFFSETS['a'] + i
        b_idx = REG_OFFSETS['b'] + i
        c_idx = REG_OFFSETS['c'] + i
        e_idx = REG_OFFSETS['e'] + i
        f_idx = REG_OFFSETS['f'] + i
        g_idx = REG_OFFSETS['g'] + i
        # a' bit i depends on these
        for src in [a_idx, b_idx, c_idx, e_idx, f_idx, g_idx]:
            D_lin[REG_OFFSETS['a'] + i, src] = 1
        # e' bit i depends on these (Ch)
        for src in [e_idx, f_idx, g_idx]:
            D_lin[REG_OFFSETS['e'] + i, src] = 1
    return D_lin


def find_saturation_density(D, max_T=64):
    """Iterate D^T over boolean semiring, return (T*, density) where stable."""
    n = D.shape[0]
    cur = D.copy()
    prev_ones = -1
    sat_T = -1
    for t in range(1, max_T + 1):
        ones = int(cur.sum())
        if ones == prev_ones:
            sat_T = t - 1
            break
        if ones == n * n:
            return t, 1.0
        prev_ones = ones
        cur = boolean_matmul(cur, D)
    if sat_T < 0:
        sat_T = max_T
    return sat_T, prev_ones / (n * n)


def main():
    print("=== Session 31: Saturation law T_sat = nilp(N_Σ_1)? ===\n")

    S0 = build_sigma_0()
    nilp_S0 = predicted_nilpotency([2, 13, 22])
    print(f"  Fixed Σ_0 (R={{2,13,22}}): nilp = {nilp_S0}\n")

    test_cases = [
        ("Σ_1 SHA-256",  [6, 11, 25]),     # d=3, nilp=11 — original
        ("alt-1 d=1",    [3, 7, 25]),      # bit 0 from {3,7,25} — let's check
        ("alt-2 d=2",    [6, 13, 22]),
        ("alt-3 d=4",    [4, 8, 24]),
        ("alt-4 d=8",    [8, 16, 24]),
        ("alt-5 d=16",   [16, 17, 19]),
        ("alt-6 d=1",    [1, 2, 3]),
    ]

    label = "nilp(Σ_1prime)"
    print(f"  {'name':<20}  {'rotations':<15}  {label:>14}  {'T_sat':>6}  {'density':>8}")
    print("  " + "-" * 80)
    results = []
    for name, rots in test_cases:
        if len(rots) % 2 == 0:
            print(f"  {name:<20}  {str(rots):<15}  (|R| even — skip)")
            continue
        nilp = predicted_nilpotency(rots)
        if nilp is None:
            continue
        S1_alt = custom_sigma_1(rots)
        D = build_dependency_with_custom_sigma1(S0, S1_alt)
        T_sat, density = find_saturation_density(D, max_T=80)
        match = "✓" if T_sat == nilp else "≠"
        results.append((name, rots, nilp, T_sat, density, match))
        print(f"  {name:<20}  {str(rots):<15}  {nilp:>10}  {T_sat:>6}  {density:>8.4f}  {match}")

    print("\n=== Summary ===")
    matches = sum(1 for _, _, n, t, _, m in results if m == "✓")
    print(f"  T_sat = nilp(N_Σ_1') in {matches} / {len(results)} cases")

    if matches == len(results):
        print("  ✓ HYPOTHESIS CONFIRMED: T_sat = nilp(N_Σ_1') universally")
        print("  ⇒ Theorem 28.1 upgrades to: T_sat = ⌈n / d_{Σ_1}⌉")
    else:
        print("  ✗ HYPOTHESIS REFUTED in some cases — relation is more subtle")
        print("  Differences (T_sat vs nilp):")
        for name, rots, nilp, T_sat, dens, match in results:
            if match != "✓":
                print(f"    {name}: nilp={nilp}, T_sat={T_sat}, diff={T_sat - nilp}")


def takeaway(results=None):
    print("""

=== STRUCTURAL TAKEAWAY (Session 31) ===

Goal: Verify whether the saturation point T_sat of bare-round dependency is
DETERMINED by the nilpotency of N_{Σ_1} (= ⌈n/d⌉, Theorem 24.1).

If YES: Theorem 28.1 acquires a clean structural proof.
If NO:  the T_sat = 11 observation in SHA-256 is partly coincidental.

This single test cleanly separates "structural law" from "numerical accident".
""")


if __name__ == "__main__":
    main()
    takeaway()
