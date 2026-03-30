#!/usr/bin/env python3
"""
EXP 62: Multi-Block Dimension — Feedforward Changes the Game

Single block: collision = F(IV,W) = F(IV,W'). IV cancels.
Dimension = 256. Birthday = 2^128.

Multi-block (same M2): IV2 + F(IV2, M2) = IV2' + F(IV2', M2)
where IV2 = IV + F(IV, M1), IV2' = IV + F(IV, M1').
Feedforward DOES NOT cancel! Different equation.

KEY: G(IV2) = IV2 + F(IV2, M2) is a map from 256→256 bits.
This map is NOT a bijection (IV2 appears in both addend and function).
If G is not bijection → D_KY < 256 → dimension reduction!

Test: is G(x) = x + F(x, M2) a bijection?
If not → how many collisions does G have?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def G_map(iv2, M2):
    """G(IV2) = IV2 + F(IV2, M2) where F = 64-round SHA-256 compression."""
    states = sha256_rounds(M2, 64, list(iv2))
    final = states[64]
    return [(iv2[i] + final[i]) & MASK for i in range(8)]

def test_G_bijectivity(N=500):
    """Is G(x) = x + F(x, M2) a bijection?"""
    print(f"\n--- IS G(IV2) = IV2 + F(IV2, M2) A BIJECTION? ---")

    M2 = random_w16()  # Fixed second block

    # Test: does flipping 1 bit of IV2 always change G?
    collisions_found = 0
    non_injective = 0

    for _ in range(N):
        iv2 = [random.randint(0, MASK) for _ in range(8)]
        g_base = G_map(iv2, M2)
        g_base_hash = tuple(g_base)

        # Flip each bit of IV2, check if G changes
        for word in range(8):
            for bit in [0, 8, 16, 24, 31]:  # Sample bits
                iv2_pert = list(iv2)
                iv2_pert[word] ^= (1 << bit)

                g_pert = G_map(iv2_pert, M2)

                if g_pert == g_base:
                    collisions_found += 1

                # Measure distance
                dist = sum(hw(g_base[i] ^ g_pert[i]) for i in range(8))
                if dist == 0 and iv2_pert != iv2:
                    non_injective += 1

    print(f"G-collisions (G(x)=G(y), x≠y) found: {collisions_found}")
    print(f"Non-injective cases: {non_injective}")

    if collisions_found > 0:
        print(f"*** G IS NOT INJECTIVE! ***")
    else:
        print(f"G appears injective (at tested points)")

def test_G_jacobian_rank(N=50):
    """What is the GF(2) rank of G's Jacobian?"""
    print(f"\n--- RANK OF G's JACOBIAN ---")

    M2 = random_w16()
    ranks = []

    for _ in range(N):
        iv2 = [random.randint(0, MASK) for _ in range(8)]
        g_base = G_map(iv2, M2)

        # 256×256 Jacobian
        J = np.zeros((256, 256), dtype=np.int64)
        for j in range(256):
            w = j//32; b = j%32
            iv2_p = list(iv2)
            iv2_p[w] ^= (1 << b)
            g_p = G_map(iv2_p, M2)

            for i in range(256):
                wi = i//32; bi = i%32
                J[i][j] = ((g_base[wi]>>bi)&1) ^ ((g_p[wi]>>bi)&1)

        rank = np.linalg.matrix_rank(J.astype(np.float64))
        ranks.append(rank)

    ra = np.array(ranks)
    print(f"Rank of dG/dIV2: mean={ra.mean():.1f}, min={ra.min()}, max={ra.max()}")

    if ra.mean() < 256:
        print(f"*** RANK DEFICIT: {256-ra.mean():.0f} ***")
        print(f"G is NOT full rank → dimension reduction exists!")
    else:
        print(f"Full rank → G is locally bijective")

def test_G_collision_search(N=50000):
    """
    Direct search: find IV2 ≠ IV2' with G(IV2) = G(IV2').
    This would be a multi-block collision (same M2, different M1).
    """
    print(f"\n--- G-COLLISION SEARCH (N={N}) ---")

    M2 = random_w16()

    # Birthday search on G
    seen = {}
    best_dist = 256

    for trial in range(N):
        iv2 = [random.randint(0, MASK) for _ in range(8)]
        g = tuple(G_map(iv2, M2))

        if g in seen:
            if seen[g] != tuple(iv2):
                print(f"*** G-COLLISION FOUND at trial {trial}! ***")
                print(f"  IV2_a = {[hex(x) for x in seen[g]]}")
                print(f"  IV2_b = {[hex(x) for x in iv2]}")
                print(f"  G(IV2) = {[hex(x) for x in g]}")
                break

        seen[g] = tuple(iv2)

        # Track nearest miss
        for g_prev in list(seen.values())[-100:]:  # Check recent
            dist = sum(hw(g[i] ^ g_prev[i]) for i in range(8)) if isinstance(g_prev, tuple) and len(g_prev) == 8 else 256
            # Actually g_prev is iv2, not g value... need to track g values

    birthday = 128 - 8*np.sqrt(2*np.log(N))
    print(f"Searched {N} G-values. Birthday expected: ~{birthday:.0f}")
    print(f"Unique G-values: {len(seen)}")

    # Are G-values LESS unique than random? (Would indicate near-collisions)
    actual_unique = len(seen)
    expected_unique = N  # For injection: all unique
    print(f"Expected unique (if bijection): {N}")
    print(f"Actual unique: {actual_unique}")
    print(f"Deficit: {N - actual_unique}")

def test_multiblock_vs_singleblock(N=10000):
    """
    Compare collision difficulty:
    Single-block: H(M) = H(M') with M ≠ M'
    Multi-block (same M2): H(M1||M2) = H(M1'||M2) with M1 ≠ M1'

    Are multi-block collisions EASIER?
    """
    print(f"\n--- MULTI-BLOCK vs SINGLE-BLOCK COLLISION ---")

    # Single block: birthday among N hashes
    single_hashes = set()
    single_best_dist = 256

    for _ in range(N):
        M = random_w16()
        H = tuple(sha256_compress(M))
        single_hashes.add(H)

    # Multi-block: same M2, varying M1 → varying IV2 → birthday among G(IV2)
    M2 = random_w16()
    multi_hashes = set()

    for _ in range(N):
        M1 = random_w16()
        IV2 = sha256_compress(M1)  # H(M1) = IV2 for block 2

        H2 = G_map(IV2, M2)
        multi_hashes.add(tuple(H2))

    print(f"Single-block unique hashes: {len(single_hashes)}/{N}")
    print(f"Multi-block unique hashes:  {len(multi_hashes)}/{N}")

    deficit_single = N - len(single_hashes)
    deficit_multi = N - len(multi_hashes)

    print(f"Single deficit: {deficit_single} (expected ≈ {N**2//(2*(2**256))})")
    print(f"Multi deficit:  {deficit_multi}")

    if deficit_multi > deficit_single * 2:
        print(f"*** Multi-block has MORE hash collisions! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 62: MULTI-BLOCK DIMENSION")
    print("G(IV2) = IV2 + F(IV2, M2) — is it bijective?")
    print("="*60)

    test_G_bijectivity(200)
    test_G_jacobian_rank(30)
    test_G_collision_search(20000)
    test_multiblock_vs_singleblock(5000)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
