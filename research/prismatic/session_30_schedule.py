"""
Session 30: SHA-256 message schedule as a 512-dim linear operator.

The message schedule extends 16 input words W[0..15] to 64 words W[0..63] via
the recurrence (for i ≥ 16):

  W[i] = σ_1(W[i-2]) + W[i-7] + σ_0(W[i-15]) + W[i-16].

Treat the state s_i = (W[i-15], W[i-14], ..., W[i]) ∈ (F_2^{32})^{16} = F_2^{512}.
The transition s_{i+1} = S · s_i is a 512×512 linear operator over F_2.

Goal:
1. Build S, compute rank, order, min poly degree.
2. Compare to round function R (Session 25, order 448).
3. Characterise the eigenstructure / factorisation.

This complements the round-function analysis: SHA = compression + schedule, and
we have now characterised both linear backbones.
"""
import numpy as np
from session_25_round import (build_sigma_0, build_sigma_1, gf2_rank,
                                find_order, matpow_mod2)
from session_26_sigma_minpoly import (build_sigma_op,
                                        compute_min_poly_coeffs, fmt_poly,
                                        factor_poly_f2)
from session_28_saturation import boolean_matmul

N = 32
NUM_WORDS = 16
DIM = N * NUM_WORDS  # 512


def build_schedule_op():
    """Build 512×512 matrix S for message-schedule transition.

    State convention: s = [W[i-15], W[i-14], ..., W[i]] (oldest-first).
                       indices 0..15 of the 16-word array, each 32 bits.

    After one step: s' = [W[i-14], ..., W[i], W[i+1]]
                       = shift of state, with new W[i+1] appended.

    W[i+1] = σ_1(W[i-1]) + W[i-6] + σ_0(W[i-14]) + W[i-15]
           = σ_1(s[14]) + s[9] + σ_0(s[1]) + s[0]
    """
    sigma_0 = build_sigma_op([7, 18], 3, N)   # ROTR_7 + ROTR_18 + SHR_3
    sigma_1 = build_sigma_op([17, 19], 10, N)  # ROTR_17 + ROTR_19 + SHR_10
    I_n = np.eye(N, dtype=np.uint8)
    Z_n = np.zeros((N, N), dtype=np.uint8)

    # 16x16 grid of 32x32 blocks
    blocks = [[Z_n.copy() for _ in range(NUM_WORDS)] for _ in range(NUM_WORDS)]

    # Shift: new s[k] = old s[k+1] for k = 0..14
    for k in range(NUM_WORDS - 1):
        blocks[k][k + 1] = I_n

    # New s[15] = W[i+1] = σ_1(s[14]) + s[9] + σ_0(s[1]) + s[0]
    blocks[15][0] = I_n
    blocks[15][1] = sigma_0
    blocks[15][9] = I_n
    blocks[15][14] = sigma_1

    S = np.block(blocks).astype(np.uint8) & 1
    assert S.shape == (DIM, DIM)
    return S


def order_search(M, candidates=None):
    """Search M's order among given candidates (powers of 2, primes etc.)."""
    n = M.shape[0]
    I_n = np.eye(n, dtype=np.uint8)
    if candidates is None:
        # Try small candidates first
        candidates = [1, 2, 3, 5, 7, 8, 16, 32, 64, 127, 128, 255, 256, 512]
    found = []
    for c in candidates:
        if np.array_equal(matpow_mod2(M, c), I_n):
            found.append(c)
    return found


def find_order_via_factors(M, max_attempts=2**20):
    """Find order using doubling steps to detect."""
    n = M.shape[0]
    I_n = np.eye(n, dtype=np.uint8)
    # First check: is M^k = I for k powers of 2?
    cur = M.copy() & 1
    for log_k in range(40):
        if np.array_equal(cur, I_n):
            return 2 ** log_k
        cur = (cur @ cur) & 1
    return -1


def krylov_min_poly(M, num_tries=3, seed=42):
    """Compute minimal polynomial of M via Berlekamp-Massey on scalar trace sequence.

    For random projection w and random vector v, build sequence
        s_k = w · M^k v   for k = 0, 1, ..., 2n-1.
    BMA on this sequence gives minimal annihilator polynomial of v under M
    (intersected with row-cyclic of w). For generic random w, v, this equals
    minimal polynomial of M with very high probability.

    Repeat with multiple (w, v) and take LCM of resulting polys for safety.
    """
    n = M.shape[0]
    rng = np.random.default_rng(seed)
    best_coeffs = [1]  # constant 1
    for trial in range(num_tries):
        v = rng.integers(0, 2, size=n, dtype=np.uint8)
        w = rng.integers(0, 2, size=n, dtype=np.uint8)
        # Build sequence s_k for k = 0..2n
        seq = []
        cur = v.copy()
        for k in range(2 * n + 1):
            seq.append(int((w & cur).sum() & 1))
            cur = (M @ cur) & 1
        # Berlekamp-Massey over F_2
        ann = berlekamp_massey_f2(seq)
        # LCM with best_coeffs
        best_coeffs = poly_lcm_f2(best_coeffs, ann)
    return best_coeffs


def berlekamp_massey_f2(seq):
    """Berlekamp-Massey algorithm over F_2.
    Input: sequence s_0, s_1, ... of bits.
    Output: shortest annihilator poly C(z) (low-to-high coeffs) such that
            s_k + Σ C[i] s_{k-i} = 0 for k ≥ deg C.
    Returns C as list low-to-high, with C[0] = 1 (so length deg+1).
    """
    n = len(seq)
    C = [1]   # current connection
    B = [1]   # backup
    L = 0
    m = 1     # gap
    b_prev = 1
    for k in range(n):
        # Compute discrepancy d = s[k] + Σ C[i] s[k-i] for i=1..L
        d = seq[k]
        for i in range(1, len(C)):
            d ^= C[i] & seq[k - i]
        if d == 0:
            m += 1
        elif 2 * L <= k:
            T = C[:]
            # C ← C - (d/b_prev) z^m B  (in F_2, d/b_prev = d/1 = d if b_prev=1)
            shifted = [0] * m + B[:]
            # Extend C to needed length
            if len(shifted) > len(C):
                C = C + [0] * (len(shifted) - len(C))
            for i in range(len(shifted)):
                C[i] ^= shifted[i]
            L = k + 1 - L
            B = T
            b_prev = d
            m = 1
        else:
            shifted = [0] * m + B[:]
            if len(shifted) > len(C):
                C = C + [0] * (len(shifted) - len(C))
            for i in range(len(shifted)):
                C[i] ^= shifted[i]
            m += 1
    # Trim
    while len(C) > 1 and C[-1] == 0:
        C.pop()
    return C


def poly_lcm_f2(a, b):
    """LCM of two polynomials over F_2."""
    from session_26_sigma_minpoly import poly_divmod
    # gcd via Euclidean
    def gcd(x, y):
        x = x[:]; y = y[:]
        while y and any(c for c in y):
            _, r = poly_divmod(x, y)
            while r and r[-1] == 0:
                r.pop()
            x, y = y, r
        # Trim
        while x and x[-1] == 0:
            x.pop()
        if not x:
            x = [1]
        return x
    g = gcd(a, b)
    # a*b
    prod = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                if bj:
                    prod[i + j] ^= 1
    # divide by g
    q, _ = poly_divmod(prod, g)
    while q and q[-1] == 0:
        q.pop()
    if not q:
        q = [1]
    return q


def solve_f2(A, b):
    """Solve A x = b over F_2 (A is n×k, b is n-vec)."""
    A = A.copy().astype(np.uint8)
    b = b.copy().astype(np.uint8)
    n, k = A.shape
    aug = np.hstack([A, b.reshape(-1, 1)])
    r = 0
    pivot_cols = []
    for c in range(k):
        if r >= n:
            break
        piv = None
        for rr in range(r, n):
            if aug[rr, c] == 1:
                piv = rr
                break
        if piv is None:
            continue
        if piv != r:
            aug[[r, piv]] = aug[[piv, r]]
        for rr in range(n):
            if rr != r and aug[rr, c] == 1:
                aug[rr] ^= aug[r]
        pivot_cols.append(c)
        r += 1
    for rr in range(r, n):
        if aug[rr, -1] == 1:
            return None
    x = np.zeros(k, dtype=np.uint8)
    for i, pc in enumerate(pivot_cols):
        x[pc] = aug[i, -1]
    return x


def order_from_minpoly_factors(factors, max_check=2**16, max_factor_deg=15):
    """Given min poly factorisation [(irr_coeffs, multiplicity), ...],
    compute order of any matrix M satisfying min poly = product of factors.

    Order(M) = lcm over factors of: (order of z mod p^e).
    For irreducible p of degree d: ord(z mod p) divides 2^d - 1.
    For p^e: ord(z mod p^e) = ord(z mod p) · 2^t with 2^{t-1} < e ≤ 2^t.
    """
    from math import gcd
    def lcm(a, b):
        return a * b // gcd(a, b)

    total_order = 1
    for irr, mult in factors:
        d = len(irr) - 1
        if d == 1 and irr[0] == 0 and irr[1] == 1:
            print(f"    factor z (singular) — skip")
            continue
        if d > max_factor_deg:
            print(f"    factor of degree {d} — order divides 2^{d}-1, skipping exact computation")
            continue
        ord_z = ord_z_mod_p(irr, max_k=min(2**d, max_check))
        if ord_z < 0:
            print(f"    factor degree {d}: order > {max_check}, skipping")
            continue
        if mult > 1:
            from math import ceil, log2
            t = ceil(log2(mult))
            ord_z *= 2 ** t
        print(f"    factor degree {d}: ord(z mod p) = {ord_z}")
        total_order = lcm(total_order, ord_z)
    return total_order


def ord_z_mod_p(p_coeffs, max_k=2**20):
    """Smallest k > 0 such that z^k ≡ 1 (mod p) over F_2.
    p_coeffs: list, low-to-high."""
    from session_26_sigma_minpoly import poly_divmod
    d = len(p_coeffs) - 1
    if d == 0:
        return 1
    # z^k mod p via repeated squaring? Just iteratively multiply.
    cur = [0, 1]  # z
    one = [1]
    for k in range(1, max_k + 1):
        _, rem = poly_divmod(cur, p_coeffs)
        # Strip trailing zeros
        while rem and rem[-1] == 0:
            rem.pop()
        if rem == one:
            return k
        # cur = cur · z (mod p)
        cur = [0] + cur  # multiply by z
        _, cur = poly_divmod(cur, p_coeffs)
        while cur and cur[-1] == 0:
            cur.pop()
    return -1


def boolean_dependency_saturate(S, max_T=64):
    """Track diffusion of message schedule."""
    n = S.shape[0]
    D = (S != 0).astype(np.uint8)
    cur = D.copy()
    history = []
    for t in range(1, max_T + 1):
        history.append((t, int(cur.sum()), cur.sum() / (n * n)))
        if cur.sum() == n * n:
            return t, history
        cur = boolean_matmul(cur, D)
    return -1, history


def main():
    print("=== Session 30: SHA-256 message schedule operator analysis ===\n")

    S = build_schedule_op()
    print(f"  S shape: {S.shape}, dim = {DIM}")
    rk = gf2_rank(S.copy())
    print(f"  rank(S) = {rk}")
    print(f"  rank(S - I) = {gf2_rank((S ^ np.eye(DIM, dtype=np.uint8)) & 1)}")

    # Quick order check
    print("\n  Checking if S has small order:")
    small_orders = order_search(S, candidates=[1, 2, 4, 8, 16, 32, 64, 128, 256, 448, 511])
    if small_orders:
        print(f"    S^k = I for k ∈ {small_orders}")
    else:
        print(f"    S^k ≠ I for k ∈ small candidates")

    # Try to find order via repeated squaring (only finds powers of 2)
    print("\n  Repeated squaring (finds power-of-2 orders):")
    pow2_order = find_order_via_factors(S)
    if pow2_order > 0:
        print(f"    S^{pow2_order} = I")
    else:
        print(f"    No power-of-2 order ≤ 2^40")

    # Skip linear order search — too slow for 512×512. Derive from min poly factorisation instead.

    # Min poly via Krylov vector (much faster than flat-matrix Gaussian)
    print("\n  Computing minimal polynomial via Krylov method...")
    coeffs = krylov_min_poly(S)
    if coeffs:
        deg = len(coeffs) - 1
        print(f"  Min poly degree: {deg}")
        # Don't print full min poly (too long)
        # Factor
        print(f"  Factorising minimal polynomial (irreducibles up to deg 12)...")
        factors = factor_poly_f2(coeffs, max_irr_deg=12)
        print(f"  Factorisation:")
        total_check = 0
        for irr, mult in factors:
            d = len(irr) - 1
            irr_str = fmt_poly(irr) if d <= 8 else f"<deg {d} polynomial>"
            print(f"    ({irr_str})^{mult}    (deg {d}, mult {mult}, contributes {d * mult})")
            total_check += d * mult
        print(f"  Sum of factor degrees · mults = {total_check} (should equal min poly degree {deg})")

        # Derive order from factorisation
        order_pred = order_from_minpoly_factors(factors)
        if order_pred > 0:
            print(f"\n  Predicted order from min poly factorisation: {order_pred}")
            print(f"  Factorisation of order: {factor_int(order_pred)}")
        else:
            print(f"\n  Order undefined (z divides min poly, M singular) or > 2^20")
    else:
        print(f"  Min poly degree > {DIM + 5}")

    # Diffusion
    print("\n  Diffusion of message schedule:")
    sat_T, hist = boolean_dependency_saturate(S, max_T=64)
    for t, ones, dens in hist:
        print(f"    T={t:>3}: {ones:>6} 1-entries, density {dens:.4f}")
        if dens >= 1.0:
            break
    if sat_T > 0:
        print(f"  ✓ Schedule FULLY saturates at T = {sat_T}")
    else:
        print(f"  Not fully saturated at T=64 (density = {hist[-1][2]:.4f})")


def factor_int(n):
    """Factor positive integer."""
    fs = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            fs[d] = fs.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        fs[n] = fs.get(n, 0) + 1
    return ' · '.join(f'{p}^{e}' if e > 1 else str(p) for p, e in sorted(fs.items()))


def takeaway():
    print("""

=== STRUCTURAL TAKEAWAY (Session 30) ===

Schedule operator S analysed:
  - 512×512 over F_2
  - Order computed (see above)
  - Min poly factorisation found

Compared to ROUND operator R (Session 25, ord 448 = 2^6 · 7):
  - Both are LFSR-like linear systems
  - Schedule has different structural constants (σ_0, σ_1 with SHR)
  - Order and diffusion characterise schedule's mixing

Cryptographic interpretation:
  Real SHA-256 = ROUND ∘ SCHEDULE composition (per round, schedule provides W).
  The schedule's ORDER bounds how often W cycles.
  The schedule's DIFFUSION bounds how fast input message bits permeate the
  expanded W array.
""")


if __name__ == "__main__":
    main()
    takeaway()
