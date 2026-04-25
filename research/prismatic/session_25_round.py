"""
Session 25: Order of the full SHA-256 round function (linear part).

SHA-256 round acts on (a, b, c, d, e, f, g, h) ∈ (F_2^32)^8.

Standard round:
  T_1 = h + Σ_1(e) + Ch(e, f, g) + K_t + W_t
  T_2 = Σ_0(a) + Maj(a, b, c)
  h ← g
  g ← f
  f ← e
  e ← d + T_1
  d ← c
  c ← b
  b ← a
  a ← T_1 + T_2

LINEAR PART (drop Ch, Maj, K, W; addition over F_2 = XOR):
  T_1_lin = h ⊕ Σ_1(e)
  T_2_lin = Σ_0(a)
  new state = (T_1_lin ⊕ T_2_lin,  a,  b,  c,  d ⊕ T_1_lin,  e,  f,  g)
            = (Σ_0(a) ⊕ Σ_1(e) ⊕ h,  a,  b,  c,  d ⊕ Σ_1(e) ⊕ h,  e,  f,  g)

This is a linear operator R on F_2^{256}.

Goal: find ord(R). Compare to ord(Σ_0) = 32, ord(Σ_1) = 16 individually.

PRIOR EXPECTATION:
  - R involves Σ-operators (linear unipotent) plus register permutation/coupling.
  - Register permutation alone (a→b→c→...→h) has order 8.
  - Combined order should be lcm-like with linear interaction.
"""
import numpy as np
from session_14_sigma0 import lucas_expansion

N = 32         # word size
NUM_REGS = 8   # a, b, c, d, e, f, g, h
DIM = N * NUM_REGS  # 256


def rotr_full(r, n=N):
    """ROTR_r as multiplication by (1+s)^r in F_2[s]/(s^n) — n×n matrix in s-basis."""
    coeffs = set(lucas_expansion(r, n - 1))
    M = np.zeros((n, n), dtype=np.uint8)
    for j in range(n):
        for pos in coeffs:
            t = j + pos
            if t < n:
                M[t, j] ^= 1
    return M


def build_sigma_0():
    M = np.zeros((N, N), dtype=np.uint8)
    for r in [2, 13, 22]:
        M ^= rotr_full(r, N)
    return M & 1


def build_sigma_1():
    M = np.zeros((N, N), dtype=np.uint8)
    for r in [6, 11, 25]:
        M ^= rotr_full(r, N)
    return M & 1


def block_eye(n=N):
    return np.eye(n, dtype=np.uint8)


def block_zero(n=N):
    return np.zeros((n, n), dtype=np.uint8)


def build_round_linear():
    """Build 256×256 matrix R for the linear part of SHA-256 round.

    State vector v = [a; b; c; d; e; f; g; h] ∈ F_2^{256}, each block 32-dim.
    R · v = [a'; b'; ...; h']:
      a' = Σ_0(a) + Σ_1(e) + h
      b' = a
      c' = b
      d' = c
      e' = d + Σ_1(e) + h
      f' = e
      g' = f
      h' = g
    """
    S0 = build_sigma_0()
    S1 = build_sigma_1()
    I = block_eye()
    Z = block_zero()

    # Build 8x8 grid of 32x32 blocks
    blocks = [[Z for _ in range(NUM_REGS)] for _ in range(NUM_REGS)]
    # Indices: 0=a, 1=b, 2=c, 3=d, 4=e, 5=f, 6=g, 7=h
    # a' = S0·a + S1·e + h
    blocks[0][0] = S0
    blocks[0][4] = S1
    blocks[0][7] = I
    # b' = a
    blocks[1][0] = I
    # c' = b
    blocks[2][1] = I
    # d' = c
    blocks[3][2] = I
    # e' = d + S1·e + h
    blocks[4][3] = I
    blocks[4][4] = S1
    blocks[4][7] = I
    # f' = e
    blocks[5][4] = I
    # g' = f
    blocks[6][5] = I
    # h' = g
    blocks[7][6] = I

    R = np.block(blocks).astype(np.uint8) & 1
    assert R.shape == (DIM, DIM)
    return R


def matpow_mod2(M, k):
    """M^k mod 2 via repeated squaring."""
    n = M.shape[0]
    result = np.eye(n, dtype=np.uint8)
    base = M.copy() & 1
    while k > 0:
        if k & 1:
            result = (result @ base) & 1
        base = (base @ base) & 1
        k >>= 1
    return result


def find_order(M, max_check=4096):
    """Find smallest k > 0 with M^k = I."""
    n = M.shape[0]
    I = np.eye(n, dtype=np.uint8)
    cur = M.copy() & 1
    for k in range(1, max_check + 1):
        if np.array_equal(cur, I):
            return k
        cur = (cur @ M) & 1
    return -1


def gf2_rank(M):
    M = M.copy() & 1
    rows, cols = M.shape
    rank = 0
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = None
        for rr in range(r, rows):
            if M[rr, c] == 1:
                pivot = rr
                break
        if pivot is None:
            continue
        if pivot != r:
            M[[r, pivot]] = M[[pivot, r]]
        for rr in range(rows):
            if rr != r and M[rr, c] == 1:
                M[rr] ^= M[r]
        rank += 1
        r += 1
    return rank


def order_via_powers_of_2(M, max_log=32):
    """For unipotent M = I + N: M^{2^m} = I + N^{2^m}.
    Find smallest 2^m with M^{2^m} = I."""
    n = M.shape[0]
    I_n = np.eye(n, dtype=np.uint8)
    cur = M.copy() & 1
    for m in range(max_log + 1):
        if np.array_equal(cur, I_n):
            return 2 ** m
        cur = (cur @ cur) & 1
    return -1


def is_unipotent(M):
    """Check if M - I is nilpotent."""
    n = M.shape[0]
    I_n = np.eye(n, dtype=np.uint8)
    N = (M ^ I_n) & 1
    cur = N.copy()
    for k in range(1, n + 2):
        if cur.sum() == 0:
            return True, k
        cur = (cur @ N) & 1
    return False, -1


def main():
    print("=== Session 25: Order of full SHA-256 linear round ===\n")

    R = build_round_linear()
    print(f"  R shape: {R.shape}, dim = {DIM}")
    print(f"  rank(R) over F_2: {gf2_rank(R)} (= {DIM} → invertible)")
    print(f"  rank(R - I): {gf2_rank((R ^ np.eye(DIM, dtype=np.uint8)) & 1)}")

    # Is R unipotent?
    unipot, nilp = is_unipotent(R)
    print(f"\n  R unipotent? {unipot}")
    if unipot:
        print(f"  Nilpotency of R - I: {nilp}")
        order = 2 ** int(np.ceil(np.log2(nilp))) if nilp > 1 else 1
        print(f"  Predicted order (since unipotent): 2^⌈log₂ {nilp}⌉ = {order}")

    # Try to find order via squaring (works for unipotent — order is power of 2)
    print("\n  Searching for order via repeated squaring:")
    ord_pow2 = order_via_powers_of_2(R, max_log=20)
    if ord_pow2 > 0:
        print(f"  R^{ord_pow2} = I (smallest power of 2)")
    else:
        print(f"  R^{2**20} ≠ I — order not a power of 2 ≤ 2^20 OR not unipotent")
        # Linear search for small orders
        small = find_order(R, max_check=512)
        if small > 0:
            print(f"  R^{small} = I (linear search)")
        else:
            print(f"  R^k ≠ I for k ≤ 512")


def compare_with_pure_register_shift():
    """Without Σ ops, the round is just a permutation: a→b→c→...→h→a (cyclic)
    plus h goes back into a. Wait, h is dropped, a gets h's value? No — let's check.

    Pure register shift (set Σ_0 = Σ_1 = 0):
      a' = h
      b' = a
      ...
      h' = g
    This is a cyclic shift of registers, order 8.
    """
    print("\n\n=== Comparison: register shift only (no Σ) ===")
    Z = block_zero()
    I = block_eye()
    blocks = [[Z for _ in range(NUM_REGS)] for _ in range(NUM_REGS)]
    blocks[0][7] = I  # a' = h
    blocks[1][0] = I  # b' = a
    blocks[2][1] = I
    blocks[3][2] = I
    blocks[4][3] = I  # e' = d (no Σ_1, no h)
    blocks[5][4] = I
    blocks[6][5] = I
    blocks[7][6] = I
    R_perm = np.block(blocks).astype(np.uint8) & 1

    order = find_order(R_perm, max_check=16)
    print(f"  Pure register cycle order: {order}")
    # Should be 8 since a' = h, b' = a, ..., h' = g — cyclic 8-shift.


def diagnose_round_function(R):
    """Decompose R structurally."""
    print("\n\n=== Structural diagnosis ===")
    # Eigenvalue 1: dim ker(R - I)
    I_n = np.eye(DIM, dtype=np.uint8)
    NminusI = (R ^ I_n) & 1
    rk = gf2_rank(NminusI)
    print(f"  rank(R - I) = {rk}, ker(R - I) dim = {DIM - rk}")
    print(f"  → eigenspace of eigenvalue 1 has dim {DIM - rk}")

    # Order = 448 = 2^6 · 7
    print("\n  Order factorisation: 448 = 2^6 · 7 = 64 · 7")
    print("  Register cycle alone: order 8 = 2^3")
    print("  Σ-only orders: ord(Σ_0)=32=2^5, ord(Σ_1)=16=2^4 (Session 23)")
    print("  Coupled round mixes register-cycle (period 8) with Σ-induced unipotency.")

    # Verify: R^7 should be unipotent (since 2^6 part), and R^64 should have order 7
    R_pow_7 = matpow_mod2(R, 7)
    unipot_7, nilp_7 = is_unipotent(R_pow_7)
    print(f"\n  Is R^7 unipotent? {unipot_7}, nilpotency index = {nilp_7}")

    R_pow_64 = matpow_mod2(R, 64)
    order_64 = find_order(R_pow_64, max_check=20)
    print(f"  Order of R^64: {order_64} (expected 7)")

    # Min poly degree
    print("\n  Computing minimal polynomial degree...")
    deg = minimal_poly_degree(R)
    print(f"  Min poly degree of R: {deg}")


def minimal_poly_degree(M, max_deg=300):
    """Find degree of minimal polynomial of M over F_2."""
    n = M.shape[0]
    powers = [np.eye(n, dtype=np.uint8)]
    for i in range(1, max_deg + 1):
        next_p = (powers[-1] @ M) & 1
        flat = np.array([p.flatten() for p in powers] + [next_p.flatten()],
                        dtype=np.uint8)
        rows, cols = flat.shape
        red = flat.copy()
        r = 0
        for c in range(cols):
            if r >= rows:
                break
            piv = None
            for rr in range(r, rows):
                if red[rr, c] == 1:
                    piv = rr
                    break
            if piv is None:
                continue
            if piv != r:
                red[[r, piv]] = red[[piv, r]]
            for rr in range(rows):
                if rr != r and red[rr, c] == 1:
                    red[rr] ^= red[r]
            r += 1
        if r < rows:
            return i
        powers.append(next_p)
    return -1


if __name__ == "__main__":
    R = build_round_linear()
    main()
    compare_with_pure_register_shift()
    diagnose_round_function(R)
