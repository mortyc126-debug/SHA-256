#!/usr/bin/env python3
"""
EXP 77: Property Collision — Find Collision by Matching PROPERTIES, not Values

ALL 76 experiments searched: H(M) = H(M'). Direct value equality.
NEW: search by PROPERTY equality first, then check hash equality.

If property F(M) has dimension d < 256:
  Birthday on F: 2^{d/2} to find F-matching pairs.
  Among F-matched pairs: P(hash collision) = ???

If P(hash collision | F match) >> P(hash collision | random) = 2^{-256}:
  Total cost = 2^{d/2} / P_boost < 2^128.

PROPERTIES to test (from our 51 theorems):
  1. HW profile: (HW(H[0]), ..., HW(H[7])) — 8 numbers
  2. Carry transparency profile: (T[0], ..., T[7]) — 8 numbers
  3. Internal state signature: partial state info
  4. GKP signature: carry pattern fingerprint
  5. Pipe invariant: (a+e)[64] mod something

KEY: we're not asking "does F predict collision?"
We're asking "do F-matched pairs collide MORE OFTEN than random pairs?"
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def hash_hw_profile(W16):
    """HW profile: 8 numbers (HW of each hash word)."""
    H = sha256_compress(W16)
    return tuple(hw(H[i]) for i in range(8))

def hash_low_bits(W16, n_bits=4):
    """Low bits profile: first n_bits of each hash word."""
    H = sha256_compress(W16)
    mask = (1 << n_bits) - 1
    return tuple(H[i] & mask for i in range(8))

def hash_pipe_value(W16):
    """Pipe invariant at round 64."""
    states = sha256_rounds(W16, 64)
    s = states[64]
    pipe = (s[0] + s[4]) & MASK
    return pipe & 0xFFFF  # Low 16 bits

def hash_word_parity(W16):
    """Parity of each hash word (8 bits total)."""
    H = sha256_compress(W16)
    return tuple(hw(H[i]) % 2 for i in range(8))

def test_property_collision_rate(property_fn, prop_name, N=50000, prop_dim=None):
    """
    For N random messages: compute property F(M).
    Find pairs with F(M1) = F(M2).
    Among those pairs: measure hash distance.
    Compare with random pairs.
    """
    print(f"\n--- PROPERTY: {prop_name} ---")

    properties = {}
    hashes = {}

    for i in range(N):
        W16 = random_w16()
        F = property_fn(W16)
        H = tuple(sha256_compress(W16))

        if F in properties:
            # F-collision found! Check hash distance
            H_prev = hashes[F]
            dH = sum(hw(H[j] ^ H_prev[j]) for j in range(8))

            if dH == 0:
                print(f"  *** HASH COLLISION at i={i}! ***")

            # Store collision info
            if not hasattr(test_property_collision_rate, 'f_collisions'):
                test_property_collision_rate.f_collisions = []
            test_property_collision_rate.f_collisions = \
                getattr(test_property_collision_rate, 'f_collisions', [])
            test_property_collision_rate.f_collisions.append(dH)

        properties[F] = i
        hashes[F] = H

    # Count F-collisions
    f_collisions = getattr(test_property_collision_rate, 'f_collisions', [])

    n_unique = len(properties)
    n_f_collisions = N - n_unique

    print(f"  Messages: {N}")
    print(f"  Unique properties: {n_unique}")
    print(f"  F-collisions: {n_f_collisions}")

    if n_f_collisions > 0:
        fc = np.array(f_collisions[-n_f_collisions:]) if f_collisions else np.array([128])
        print(f"  Among F-matched pairs: E[δH]={fc.mean():.2f}, min={fc.min()}")
        print(f"  Random baseline: E[δH]=128")

        if fc.mean() < 120:
            boost = 128 - fc.mean()
            print(f"  *** F-MATCHED PAIRS CLOSER BY {boost:.1f} BITS! ***")
    else:
        print(f"  No F-collisions found (property space too large for N={N})")
        if prop_dim:
            expected = N**2 / (2 * 2**prop_dim)
            print(f"  Expected F-collisions: {expected:.1f} (property dim ≈ {prop_dim})")

    # Reset
    test_property_collision_rate.f_collisions = []

def test_multi_property(N=100000):
    """Test multiple properties with different dimensions."""
    print(f"\n--- MULTI-PROPERTY COLLISION TEST (N={N}) ---")

    # Property 1: word parities (8 bits → 2^4 birthday)
    test_property_collision_rate(hash_word_parity, "word_parity (8 bits)", N, prop_dim=8)

    # Property 2: low 2 bits of each word (16 bits → 2^8 birthday)
    test_property_collision_rate(
        lambda W: hash_low_bits(W, 2), "low_2_bits (16 bits)", N, prop_dim=16)

    # Property 3: low 3 bits (24 bits → 2^12 birthday)
    test_property_collision_rate(
        lambda W: hash_low_bits(W, 3), "low_3_bits (24 bits)", min(N, 50000), prop_dim=24)

    # Property 4: HW profile (8 numbers ≈ 24 bits effective)
    test_property_collision_rate(hash_hw_profile, "HW_profile", N, prop_dim=24)

    # Property 5: pipe low bits (16 bits)
    test_property_collision_rate(hash_pipe_value, "pipe_low16", N, prop_dim=16)

def test_property_boost(N=200000):
    """
    KEY TEST: among F-matched pairs, is δH LOWER than random?

    If yes → F captures collision-relevant structure.
    If no → F is independent of collision.
    """
    print(f"\n--- PROPERTY BOOST TEST (N={N}) ---")

    # Use word parity (simplest, most collisions)
    f_matched_dH = []
    random_dH = []

    props = {}
    hash_store = {}

    for i in range(N):
        W16 = random_w16()
        H = sha256_compress(W16)
        F = tuple(hw(H[j]) % 2 for j in range(8))

        if F in props:
            # F-collision: measure δH
            H_prev = hash_store[F]
            dH = sum(hw(H[j] ^ H_prev[j]) for j in range(8))
            f_matched_dH.append(dH)

        props[F] = i
        hash_store[F] = H

        # Random pair (with previous message)
        if i > 0:
            W_rand = random_w16()
            H_rand = sha256_compress(W_rand)
            dH_r = sum(hw(H[j] ^ H_rand[j]) for j in range(8))
            random_dH.append(dH_r)

    fm = np.array(f_matched_dH) if f_matched_dH else np.array([128])
    rm = np.array(random_dH[:len(f_matched_dH)]) if random_dH else np.array([128])

    print(f"F-matched pairs (parity): N={len(f_matched_dH)}")
    print(f"  E[δH] = {fm.mean():.4f}")
    print(f"Random pairs: N={len(rm)}")
    print(f"  E[δH] = {rm.mean():.4f}")
    print(f"Boost: {rm.mean() - fm.mean():+.4f} bits")

    if fm.mean() < rm.mean() - 1:
        print(f"*** F-MATCHED PAIRS ARE CLOSER! Boost = {rm.mean()-fm.mean():.1f} bits ***")
    else:
        print(f"No boost: F-matching does not predict hash proximity")

    # Repeat for low 2 bits
    f2_dH = []; props2 = {}; hash2 = {}
    for i in range(N):
        W16 = random_w16()
        H = sha256_compress(W16)
        F = tuple(H[j] & 0x3 for j in range(8))  # Low 2 bits

        if F in props2:
            H_prev = hash2[F]
            dH = sum(hw(H[j]^H_prev[j]) for j in range(8))
            f2_dH.append(dH)

        props2[F] = i
        hash2[F] = H

    if f2_dH:
        f2a = np.array(f2_dH)
        print(f"\nLow-2-bit matched pairs: N={len(f2_dH)}")
        print(f"  E[δH] = {f2a.mean():.4f}")
        print(f"  Boost vs random: {128 - f2a.mean():+.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 77: PROPERTY COLLISION")
    print("Match properties, then check hashes")
    print("="*60)
    test_multi_property(80000)
    test_property_boost(150000)

if __name__ == "__main__":
    main()
