"""
Session 32: Number-theoretic analysis of SHA-256's 64 round constants K_t.

K_t = ⌊2^32 · {p_t^{1/3}}⌋ where p_t is the t-th prime (p_0 = 2, p_1 = 3, ...)
and {·} is fractional part.

These are 64 specific 32-bit values. We've NEVER analyzed them in any
previous session. Question: do they have hidden algebraic structure beyond
their cube-root construction?

Investigations:
1. Bit-statistics: balance, Hamming weights, run lengths.
2. Linear span of {K_t} as F_2^32 vectors — what dimension?
3. Algebraic relations: K_i ⊕ K_j patterns, K_i + K_j (mod 2^32).
4. Lucas-XOR analysis: do the K_t have specific bit-coverage patterns?
5. Statistical tests: are they distinguishable from random 32-bit values?
6. Connections to other constants (e, π, golden ratio).
7. Modular structure: K_t mod small primes.
"""
import numpy as np
from session_25_round import gf2_rank


SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]


def to_bits(x, n=32):
    """Convert int to bit vector (LSB first)."""
    return np.array([(x >> i) & 1 for i in range(n)], dtype=np.uint8)


def hamming_weight(x):
    return bin(x).count('1')


def runs(bits):
    """Count of maximal runs in bit pattern."""
    if len(bits) == 0:
        return 0
    cnt = 1
    for i in range(1, len(bits)):
        if bits[i] != bits[i - 1]:
            cnt += 1
    return cnt


def bit_statistics():
    print("=== Bit statistics of K_t ===")
    weights = [hamming_weight(k) for k in SHA256_K]
    runs_list = [runs(to_bits(k)) for k in SHA256_K]
    print(f"  Hamming weights: min={min(weights)}, max={max(weights)}, mean={sum(weights)/len(weights):.2f}, expected={32/2}")
    print(f"  Run counts: min={min(runs_list)}, max={max(runs_list)}, mean={sum(runs_list)/len(runs_list):.2f}, expected≈16")
    print(f"  Histogram of weights: {sorted(set(weights))}")

    # Per-bit-position bias
    bit_counts = np.zeros(32, dtype=int)
    for k in SHA256_K:
        for i in range(32):
            if (k >> i) & 1:
                bit_counts[i] += 1
    print(f"\n  Per-bit-position 1-counts (out of 64):")
    for i in range(32):
        bar = '#' * int(bit_counts[i] * 30 / 64)
        print(f"    bit {i:>2}: {bit_counts[i]:>2}/64  {bar}")
    expected = 32
    chi2 = sum((c - expected) ** 2 / expected for c in bit_counts)
    print(f"\n  χ² statistic for per-bit balance: {chi2:.2f} (df=31, critical at 0.05: 44.99)")
    if chi2 < 45:
        print(f"    → bits look balanced (no per-position bias)")
    else:
        print(f"    → SIGNIFICANT bias — investigate")


def linear_span_analysis():
    print("\n=== Linear span of {K_t} in F_2^32 ===")
    M = np.array([to_bits(k) for k in SHA256_K], dtype=np.uint8)  # 64 × 32
    rk = gf2_rank(M.copy())
    print(f"  rank({{K_0..K_63}}) = {rk}")
    print(f"  Span fills {rk}/32 dimensions")
    if rk == 32:
        print(f"  → K_t span ALL of F_2^32 — they're linearly 'generic'")
    else:
        print(f"  → Linear dependencies exist (codim {32-rk})")

    # Look at first 32, then check if K_32..K_63 are dependent on first 32
    M32 = M[:32]
    rk32 = gf2_rank(M32.copy())
    print(f"\n  rank(K_0..K_31) = {rk32}")
    if rk32 == 32:
        # Express each K_t (t≥32) as linear comb of K_0..K_31
        deps_count = 0
        for t in range(32, 64):
            if linearly_dependent(M32, M[t]):
                deps_count += 1
        print(f"  K_32..K_63 dependent on K_0..K_31 in {deps_count}/32 cases")


def linearly_dependent(basis, v):
    """Check if v is in span of basis (over F_2)."""
    M = np.vstack([basis, v]).copy()
    rk_basis = gf2_rank(basis.copy())
    rk_aug = gf2_rank(M)
    return rk_aug == rk_basis


def difference_analysis():
    print("\n=== Pairwise XOR differences K_i ⊕ K_j ===")
    diffs = set()
    for i in range(len(SHA256_K)):
        for j in range(i + 1, len(SHA256_K)):
            diffs.add(SHA256_K[i] ^ SHA256_K[j])
    print(f"  Distinct XOR differences: {len(diffs)} / {64*63//2} = {len(diffs)/(64*63//2):.4f}")
    if len(diffs) == 64*63//2:
        print(f"  → all pairwise differences DISTINCT")
    else:
        coll = 64*63//2 - len(diffs)
        print(f"  → {coll} collisions — investigate")

    # Hamming weight distribution of differences
    weights = [hamming_weight(d) for d in list(diffs)[:200]]
    print(f"  XOR difference Hamming weights (sample): mean={sum(weights)/len(weights):.2f}, expected≈16")


def modular_structure():
    print("\n=== K_t modulo small primes ===")
    for m in [3, 5, 7, 11, 13, 257, 65537]:
        residues = [k % m for k in SHA256_K]
        # Test uniformity via χ²
        from collections import Counter
        cnt = Counter(residues)
        expected = 64 / m
        chi2 = sum((cnt.get(r, 0) - expected) ** 2 / expected for r in range(m))
        print(f"  mod {m:>5}: residues span {len(set(residues))}/{m}, χ² = {chi2:.2f}")


def cube_root_verification():
    """Check that K_t = ⌊2^32 · {p_t^{1/3}}⌋ exactly."""
    print("\n=== Verify K_t = floor(2^32 · frac(p_t^(1/3))) ===")
    primes = []
    n = 2
    while len(primes) < 64:
        is_prime = True
        for p in primes:
            if p * p > n:
                break
            if n % p == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(n)
        n += 1
    # Use high-precision arithmetic
    from decimal import Decimal, getcontext
    getcontext().prec = 100
    mismatches = 0
    for t in range(64):
        p = Decimal(primes[t])
        # Cube root via Newton or binary search
        cube_root = p ** (Decimal(1) / Decimal(3))
        frac = cube_root - int(cube_root)
        K_predicted = int(frac * (Decimal(2) ** 32))
        if K_predicted != SHA256_K[t]:
            mismatches += 1
            if mismatches <= 3:
                print(f"  K_{t}: expected 0x{SHA256_K[t]:08x}, computed 0x{K_predicted:08x} (Δ={K_predicted - SHA256_K[t]})")
    if mismatches == 0:
        print(f"  ✓ All 64 K_t verified as floor(2^32 · frac(p_t^(1/3)))")
    else:
        print(f"  {mismatches} mismatches (likely precision rounding)")


def lucas_xor_of_constants():
    """For each K_t, compute its 'Lucas-XOR support' as if used in a ROTR-like operator."""
    print("\n=== Lucas-XOR-style analysis of K_t bit patterns ===")
    # This is speculative: we treat each K_t as a polynomial in F_2[s]/(s^32) and ask its
    # smallest nonzero position.
    smallest_set_bits = []
    for t, k in enumerate(SHA256_K):
        bits = [i for i in range(32) if (k >> i) & 1]
        if bits:
            smallest_set_bits.append(min(bits))
    from collections import Counter
    print(f"  Smallest set-bit position distribution:")
    cnt = Counter(smallest_set_bits)
    for pos in sorted(cnt.keys()):
        print(f"    bit {pos}: {cnt[pos]:>2} of 64 K_t values  {'#' * cnt[pos]}")


def main():
    print("=== Session 32: Number-theoretic analysis of K_t ===\n")

    cube_root_verification()
    bit_statistics()
    linear_span_analysis()
    difference_analysis()
    modular_structure()
    lucas_xor_of_constants()

    print("""

=== STRUCTURAL TAKEAWAY (Session 32) ===

This session is the FIRST in our program to look at SHA's number-theoretic
side: the 64 round constants K_t derived from cube roots of primes.

Findings (see above):
- Linear span: do K_t fill F_2^32?
- Bit balance: per-position bias?
- Pairwise differences: all distinct?
- Modular residues: uniform mod small primes?

If K_t pass all "randomness" tests → the cube-root construction is
cryptographically clean: no exploitable algebraic structure.
If they FAIL any test → there's a hidden bias that could be exploited.

This is genuinely NEW DIRECTION — completely independent of all 31 prior sessions.
""")


if __name__ == "__main__":
    main()
