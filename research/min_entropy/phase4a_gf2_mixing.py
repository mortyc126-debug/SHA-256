"""Phase 4A: analytical GF(2) bit-mixing count from Σ rotations.

Models SHA-256 compression round as 256×256 GF(2) linear operator
(linearized: + → XOR, Ch/Maj → XOR, ignore K/W additive constants).

Round:
  T1 = h ⊕ Σ1(e) ⊕ e ⊕ f ⊕ g
  T2 = Σ0(a) ⊕ a ⊕ b ⊕ c
  a_new = T1 ⊕ T2
  e_new = d ⊕ T1
  b_new = a; c_new = b; d_new = c
  f_new = e; g_new = f; h_new = g

State = (a, b, c, d, e, f, g, h) packed as 256 bits.

Questions:
1. When does M^r have full column density (every output bit depends on all inputs)?
2. When does the 3rd-order Walsh subspace "spread" enough to lose structure?

Output: density of M^r over rounds, comparison with Phase 3A V_all_linear
(Ω_3=0.87 at r=24, 0.19 at r=32) and baseline (collapse at r=20).
"""
import json, os, time
import numpy as np


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase4a_gf2_mixing.json')


def rotr_matrix(n, shift):
    """32×32 GF(2) matrix for ROTR(x, shift) on n-bit x (n=32)."""
    M = np.zeros((n, n), dtype=np.uint8)
    for i in range(n):
        # Bit i of output = bit (i + shift) mod n of input
        M[i, (i + shift) % n] = 1
    return M


def sigma_matrix(rotations):
    """32×32 GF(2) matrix for ⊕ of ROTR by given amounts. E.g., Σ0 = [2,13,22]."""
    n = 32
    M = np.zeros((n, n), dtype=np.uint8)
    for r in rotations:
        M ^= rotr_matrix(n, r)
    return M


def shr_matrix(n, shift):
    """32×32 for SHR(x, shift)."""
    M = np.zeros((n, n), dtype=np.uint8)
    for i in range(n):
        src = i + shift
        if src < n: M[i, src] = 1
    return M


# Σ0 = ROTR(·,2) ⊕ ROTR(·,13) ⊕ ROTR(·,22)
# Σ1 = ROTR(·,6) ⊕ ROTR(·,11) ⊕ ROTR(·,25)
SIGMA0 = sigma_matrix([2, 13, 22])
SIGMA1 = sigma_matrix([6, 11, 25])


def build_round_matrix():
    """Build 256×256 GF(2) matrix for one linearized compression round.

    Bit layout: state[0..31]=a, [32..63]=b, ..., [224..255]=h.
    Each 32-bit word is packed MSB-first (bit 0 = MSB of a).

    Linearized:
      a_new = T1 ⊕ T2 = h ⊕ Σ1(e) ⊕ e ⊕ f ⊕ g ⊕ Σ0(a) ⊕ a ⊕ b ⊕ c
      e_new = d ⊕ h ⊕ Σ1(e) ⊕ e ⊕ f ⊕ g
      b_new = a_old; c_new = b_old; d_new = c_old
      f_new = e_old; g_new = f_old; h_new = g_old
    """
    n = 32
    N = 8 * n  # 256
    M = np.zeros((N, N), dtype=np.uint8)
    I = np.eye(n, dtype=np.uint8)

    def put(row_start, col_start, block):
        M[row_start:row_start+n, col_start:col_start+n] ^= block

    # Register offsets
    a, b, c, d, e, f, g, h = 0, 32, 64, 96, 128, 160, 192, 224

    # a_new: Σ0(a) ⊕ a ⊕ b ⊕ c ⊕ Σ1(e) ⊕ e ⊕ f ⊕ g ⊕ h
    put(a, a, SIGMA0 ^ I)
    put(a, b, I)
    put(a, c, I)
    put(a, e, SIGMA1 ^ I)
    put(a, f, I)
    put(a, g, I)
    put(a, h, I)

    # b_new = a_old
    put(b, a, I)
    # c_new = b_old
    put(c, b, I)
    # d_new = c_old
    put(d, c, I)

    # e_new = d ⊕ h ⊕ Σ1(e) ⊕ e ⊕ f ⊕ g
    put(e, d, I)
    put(e, h, I)
    put(e, e, SIGMA1 ^ I)
    put(e, f, I)
    put(e, g, I)

    # f_new = e_old
    put(f, e, I)
    # g_new = f_old
    put(g, f, I)
    # h_new = g_old
    put(h, g, I)

    return M


def gf2_matpow(M, r):
    """M^r over GF(2) via repeated squaring."""
    n = M.shape[0]
    result = np.eye(n, dtype=np.uint8)
    base = M.copy()
    while r > 0:
        if r & 1:
            result = (result @ base) % 2
        base = (base @ base) % 2
        r >>= 1
    return result


def density(M):
    """Fraction of nonzero entries."""
    return float(M.sum() / M.size)


def gf2_rank(M):
    """Rank of M over GF(2)."""
    A = M.copy().astype(np.uint8)
    rows, cols = A.shape
    rank = 0
    for c in range(cols):
        pivot = None
        for r in range(rank, rows):
            if A[r, c]:
                pivot = r; break
        if pivot is None: continue
        A[[rank, pivot]] = A[[pivot, rank]]
        for r in range(rows):
            if r != rank and A[r, c]:
                A[r] ^= A[rank]
        rank += 1
    return rank


def main():
    t0 = time.time()
    print("# Phase 4A: GF(2) linearized compression round mixing analysis")

    M = build_round_matrix()
    print(f"# Round matrix 256×256 built, density = {density(M):.3f}, rank = {gf2_rank(M)}")

    # Compute M^r for r=1..64, track density and rank
    rounds = [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 17, 18, 19, 20, 22, 24, 28, 32, 40, 48, 56, 64]
    M_pow = M.copy()
    results = []
    prev_r = 1
    for r in rounds:
        for _ in range(r - prev_r):
            M_pow = (M_pow @ M) % 2
        prev_r = r
        d = density(M_pow)
        rk = gf2_rank(M_pow)
        results.append({'r': r, 'density': d, 'rank': rk})
        print(f"  r={r:>2}: density = {d:.4f}  rank = {rk}/256")

    # Find when full mixing (density ≥ 0.49 ≈ random)
    full_mixing = None
    for e in results:
        if e['density'] > 0.45:
            full_mixing = e['r']; break
    print(f"\n## Full density mixing (density > 0.45): r = {full_mixing}")

    # Compare with empirical collapse
    print(f"\n## Comparison with Phase 3A:")
    print(f"  V0 baseline (full SHA)   collapses at r=20")
    print(f"  V_all_linear (linearized) collapses at r=32")
    print(f"  GF(2) full density mixing: r={full_mixing}")

    # Compute rank-deficient direction count
    for e in results:
        if e['r'] in [4, 8, 16, 20, 24, 32]:
            ker = 256 - e['rank']
            e['kernel_dim'] = ker

    out = {
        'round_matrix_density': density(M),
        'round_matrix_rank': gf2_rank(M),
        'evolution': results,
        'full_density_round': full_mixing,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}")


if __name__ == '__main__':
    main()
