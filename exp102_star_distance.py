#!/usr/bin/env python3
"""
EXP 102: ★-Distance — A Non-Birthday Collision Instrument

Birthday uses HAMMING distance: d_H(h1, h2) = HW(h1 ⊕ h2).
★-algebra has its OWN distance: d★ based on ★-operations.

If d★ ≠ d_H → different metric → different birthday bound.
If d★ has lower effective dimension → collision cheaper in d★.

★-distance: how many ★-operations to transform state1 → state2?

Define: d★(S1, S2) = min{k : ∃ sequence of k ★-ops mapping S1 to S2}

In practice: d★ ≈ "carry distance" = how much carry chain differs.
Two states with SAME carry structure but different XOR → d★ small.
Two states with DIFFERENT carry → d★ large.

KEY: d★ might cluster hashes that d_H treats as far apart!
Two hashes with d_H = 100 might have d★ = 10 → "close" in ★.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def star_distance_carry(h1_words, h2_words):
    """
    ★-distance based on carry structure difference.
    d★ = how much the carry chains DIFFER between two hashes
    when deconstructed via ★.

    For each word: h = π_add(x, a) = x ⊕ carry_shift(x, a).
    Given h, there are 2^32 possible (x, a) pairs.
    The carry structure = a (AND component).

    d★ = min over all (x1,a1), (x2,a2) in fibers of h1, h2:
          HW(a1 ⊕ a2)

    In practice: approximate by ONE canonical (x, a) per hash.
    Canonical: x = h (i.e., a = 0 → zero carry → simplest representation).
    But a=0 → π_add(h, 0) = h (trivially). Every hash is its own simplest.

    Alternative: use the ACTUAL ★-state from SHA-256 computation.
    """
    # We need the ★-states, not just hashes.
    # d★ = HW of AND-component difference
    # For now: approximate via hash-level carry structure
    d_carry = 0
    d_hamming = 0
    for w in range(8):
        d_hamming += hw(h1_words[w] ^ h2_words[w])
        # Carry structure of h: approximate by carry(h, IV)
        # (how much carry would IV+h generate)
        carry1 = ((IV[w] + h1_words[w]) & MASK) ^ (IV[w] ^ h1_words[w])
        carry2 = ((IV[w] + h2_words[w]) & MASK) ^ (IV[w] ^ h2_words[w])
        d_carry += hw(carry1 ^ carry2)

    return d_hamming, d_carry

def star_distance_state(sn1, sn2):
    """★-distance from actual ★-states (full computation)."""
    # XOR-component distance
    d_xor = sum(hw(sn1[64][w] ^ sn2[64][w]) for w in range(8))
    # AND-component distance (via feedforward carry)
    d_and = 0
    for w in range(8):
        and1 = IV[w] & sn1[64][w]
        and2 = IV[w] & sn2[64][w]
        d_and += hw(and1 ^ and2)

    return d_xor, d_and

def test_star_vs_hamming(N=5000):
    """Compare ★-distance with Hamming distance."""
    print(f"\n--- ★-DISTANCE vs HAMMING ---")

    d_ham = []; d_car = []; d_xor = []; d_and = []

    for _ in range(N):
        W1 = random_w16(); W2 = random_w16()
        H1 = sha256_compress(W1); H2 = sha256_compress(W2)
        s1 = sha256_rounds(W1, 64); s2 = sha256_rounds(W2, 64)

        dh, dc = star_distance_carry(H1, H2)
        dx, da = star_distance_state(s1, s2)

        d_ham.append(dh); d_car.append(dc)
        d_xor.append(dx); d_and.append(da)

    ha = np.array(d_ham); ca = np.array(d_car)
    xa = np.array(d_xor); aa = np.array(d_and)

    print(f"Hamming distance:  E={ha.mean():.2f}, std={ha.std():.2f}")
    print(f"Carry distance:    E={ca.mean():.2f}, std={ca.std():.2f}")
    print(f"★-XOR distance:    E={xa.mean():.2f}, std={xa.std():.2f}")
    print(f"★-AND distance:    E={aa.mean():.2f}, std={aa.std():.2f}")

    # Correlation between distances
    c_hc = np.corrcoef(ha, ca)[0, 1]
    c_hx = np.corrcoef(ha, xa)[0, 1]
    c_ha = np.corrcoef(ha, aa)[0, 1]
    c_xa = np.corrcoef(xa, aa)[0, 1]

    print(f"\nCorrelations:")
    print(f"  Hamming ↔ Carry:  {c_hc:+.6f}")
    print(f"  Hamming ↔ ★-XOR: {c_hx:+.6f}")
    print(f"  Hamming ↔ ★-AND: {c_ha:+.6f}")
    print(f"  ★-XOR ↔ ★-AND:  {c_xa:+.6f}")

    # KEY: do pairs with small carry distance have small Hamming?
    print(f"\nCarry-close pairs (bottom 10% by carry distance):")
    carry_close = ha[ca < np.percentile(ca, 10)]
    carry_far = ha[ca > np.percentile(ca, 90)]
    print(f"  E[d_Hamming | d_carry low]:  {carry_close.mean():.2f}")
    print(f"  E[d_Hamming | d_carry high]: {carry_far.mean():.2f}")

    # Do AND-close pairs have small Hamming?
    and_close = ha[aa < np.percentile(aa, 10)]
    and_far = ha[aa > np.percentile(aa, 90)]
    print(f"  E[d_Hamming | d_AND low]:    {and_close.mean():.2f}")
    print(f"  E[d_Hamming | d_AND high]:   {and_far.mean():.2f}")

def test_star_birthday(N=20000):
    """Birthday search using ★-distance instead of Hamming."""
    print(f"\n--- ★-BIRTHDAY (N={N}) ---")

    # Standard birthday: find pair with min Hamming distance
    hashes = []
    states = []
    for _ in range(N):
        W = random_w16()
        H = sha256_compress(W)
        s = sha256_rounds(W, 64)
        hashes.append(H)
        states.append(s)

    # Find min Hamming
    min_ham = 256; min_carry = 256; min_and = 256

    # Sample pairs (full pairwise too expensive)
    n_pairs = min(N * 100, 500000)
    for _ in range(n_pairs):
        i = random.randint(0, N-1); j = random.randint(0, N-1)
        if i == j: continue

        dh = sum(hw(hashes[i][w] ^ hashes[j][w]) for w in range(8))
        min_ham = min(min_ham, dh)

        _, dc = star_distance_carry(hashes[i], hashes[j])
        min_carry = min(min_carry, dc)

        _, da = star_distance_state(states[i], states[j])
        min_and = min(min_and, da)

    birthday_h = 128 - 8 * math.sqrt(2 * math.log(n_pairs))

    print(f"Min Hamming:  {min_ham} (birthday ≈ {birthday_h:.0f})")
    print(f"Min Carry:    {min_carry}")
    print(f"Min AND:      {min_and}")

    # If min_carry < min_hamming → carry distance finds "closer" pairs
    if min_carry < min_ham:
        print(f"*** ★-distance finds CLOSER pairs than Hamming! ***")
        print(f"  Gain: {min_ham - min_carry} bits")

def test_effective_dimension(N=3000):
    """What is the effective dimension of ★-distance space?"""
    print(f"\n--- ★-DISTANCE EFFECTIVE DIMENSION ---")

    # Compute carry distances for N random pairs
    carry_dists = []
    and_dists = []
    ham_dists = []

    for _ in range(N):
        W1 = random_w16(); W2 = random_w16()
        H1 = sha256_compress(W1); H2 = sha256_compress(W2)
        s1 = sha256_rounds(W1, 64); s2 = sha256_rounds(W2, 64)

        dh, dc = star_distance_carry(H1, H2)
        _, da = star_distance_state(s1, s2)

        ham_dists.append(dh); carry_dists.append(dc); and_dists.append(da)

    ha = np.array(ham_dists); ca = np.array(carry_dists); aa = np.array(and_dists)

    # Effective dimension from variance
    # For uniform distribution in n dimensions: std(distance) ∝ √n
    # So: n_eff = (mean / std)² × π / 2 (for Hamming in n-bit space)

    for name, arr in [("Hamming", ha), ("Carry", ca), ("AND", aa)]:
        mean_d = arr.mean(); std_d = arr.std()
        # n_eff approximation
        n_eff = 2 * (mean_d / std_d) ** 2 if std_d > 0 else 0
        birthday = n_eff / 2

        print(f"  {name:>8}: mean={mean_d:.1f}, std={std_d:.2f}, "
              f"n_eff≈{n_eff:.0f}, birthday≈2^{birthday:.0f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 102: ★-DISTANCE")
    print("Non-birthday collision instrument")
    print("=" * 60)
    test_star_vs_hamming(3000)
    test_star_birthday(10000)
    test_effective_dimension(2000)

if __name__ == "__main__":
    main()
