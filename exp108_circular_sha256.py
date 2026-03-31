#!/usr/bin/env python3
"""
EXP 108: Circular SHA-256 — Full ROTR-Equivariant Hash

From exp107: circular carry is EXACTLY ROTR-equivariant.
From analysis: Ch, Maj, Σ₀, Σ₁ are ALL ROTR-equivariant (bitwise).
The ONLY non-equivariant operation is LINEAR CARRY in additions.

IDEA: Replace EVERY addition in SHA-256 with circular-carry addition.
This gives "circular SHA-256" that is FULLY ROTR-equivariant:
  circ_SHA256(ROTR_k(M)) = ROTR_k(circ_SHA256(M))

QUESTIONS:
1. How different is circ_SHA256 from real SHA-256? (bit diff)
2. Does ROTR-equivariance make the collision equation ALGEBRAICALLY simpler?
3. If circ_collision found: how far from real collision?
4. Does the cascade achieve R > 1 in the FULL circular system?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_bits_circular(a, b, max_iter=4):
    """Circular carry: bit 31 feeds back to bit 0."""
    carries = [0] * 32
    for _ in range(max_iter):
        new_carries = [0] * 32
        c = carries[31]
        for i in range(32):
            ai = (a >> i) & 1; bi = (b >> i) & 1
            c = (ai & bi) | ((ai ^ bi) & c)
            new_carries[i] = c
        if new_carries == carries:
            break
        carries = new_carries
    return carries

def circ_add(a, b):
    """Circular addition: a + b using circular carry."""
    cc = carry_bits_circular(a, b)
    # Result: (a ⊕ b) ⊕ (carry shifted left by 1, with circular wrap)
    # Standard: result[i] = a[i] ⊕ b[i] ⊕ carry[i-1] (carry[-1]=0)
    # Circular: result[i] = a[i] ⊕ b[i] ⊕ carry[(i-1)%32]
    xor_ab = a ^ b
    carry_word = 0
    for i in range(32):
        carry_word |= (cc[i] << i)
    # Shift carry left by 1 with circular wrap
    carry_shifted = ((carry_word << 1) | (carry_word >> 31)) & MASK
    return (xor_ab ^ carry_shifted) & MASK

def circ_round(state, W_r, K_r):
    """SHA-256 round with circular additions."""
    a, b, c, d, e, f, g, h = state
    T1 = circ_add(circ_add(circ_add(circ_add(h, sigma1(e)), ch(e, f, g)), K_r), W_r)
    T2 = circ_add(sigma0(a), maj(a, b, c))
    return [
        circ_add(T1, T2),  # a
        a,                   # b
        b,                   # c
        c,                   # d
        circ_add(d, T1),    # e
        e,                   # f
        f,                   # g
        g,                   # h
    ]

def circ_schedule(W16):
    """Schedule with circular additions."""
    W = list(W16) + [0] * 48
    for t in range(16, 64):
        W[t] = circ_add(circ_add(circ_add(sig1(W[t-2]), W[t-7]), sig0(W[t-15])), W[t-16])
    return W

def circ_sha256_rounds(W16, num_rounds=64, iv=None):
    """Circular SHA-256 rounds."""
    if iv is None:
        iv = list(IV)
    W = circ_schedule(W16)
    states = [list(iv)]
    state = list(iv)
    for r in range(min(num_rounds, 64)):
        state = circ_round(state, W[r], K[r])
        states.append(list(state))
    return states

def circ_sha256_compress(W16, iv=None):
    """Full circular SHA-256 compression."""
    if iv is None:
        iv = list(IV)
    states = circ_sha256_rounds(W16, 64, iv)
    final = states[-1]
    return [circ_add(iv[i], final[i]) for i in range(8)]

def test_equivariance(N=500):
    """Verify: is circular SHA-256 truly ROTR-equivariant?"""
    print(f"\n--- ROTR-EQUIVARIANCE VERIFICATION (N={N}) ---")

    rotations = [1, 2, 6, 11, 13, 22, 25]
    exact = {k: 0 for k in rotations}
    bit_diffs = {k: [] for k in rotations}

    for _ in range(N):
        W16 = random_w16()
        H = circ_sha256_compress(W16)

        for k in rotations:
            W16_rot = [rotr(w, k) for w in W16]
            H_rot = circ_sha256_compress(W16_rot)
            H_expected = [rotr(H[w], k) for w in range(8)]

            diff = sum(hw(H_rot[w] ^ H_expected[w]) for w in range(8))
            bit_diffs[k].append(diff)
            if diff == 0:
                exact[k] += 1

    print(f"circ_SHA256(ROTR_k(M)) =? ROTR_k(circ_SHA256(M)):")
    for k in rotations:
        rate = exact[k] / N
        bd = np.array(bit_diffs[k])
        print(f"  ROTR-{k:>2}: exact={rate:.6f}, mean_diff={bd.mean():.3f}")

    avg = np.mean([exact[k]/N for k in rotations])
    if avg > 0.99:
        print(f"\n  *** CIRCULAR SHA-256 IS EXACTLY ROTR-EQUIVARIANT! ***")
    return avg

def test_distance_from_real(N=1000):
    """How different is circ_SHA256 from real SHA-256?"""
    print(f"\n--- DISTANCE: CIRCULAR vs REAL SHA-256 (N={N}) ---")

    diffs = []
    for _ in range(N):
        W16 = random_w16()
        H_real = sha256_compress(W16)
        H_circ = circ_sha256_compress(W16)
        diff = sum(hw(H_real[w] ^ H_circ[w]) for w in range(8))
        diffs.append(diff)

    da = np.array(diffs)
    print(f"HW(SHA256(M) ⊕ circ_SHA256(M)):")
    print(f"  Mean: {da.mean():.2f}")
    print(f"  Std: {da.std():.2f}")
    print(f"  Min: {da.min()}")
    print(f"  Max: {da.max()}")

    # Round-by-round divergence
    print(f"\nPer-round divergence:")
    for R in [1, 2, 4, 8, 16, 32, 64]:
        round_diffs = []
        for _ in range(min(N, 500)):
            W16 = random_w16()
            sr = sha256_rounds(W16, R)
            sc = circ_sha256_rounds(W16, R)
            diff = sum(hw(sr[R][w] ^ sc[R][w]) for w in range(8))
            round_diffs.append(diff)
        rd = np.array(round_diffs)
        print(f"  Round {R:>2}: mean_diff = {rd.mean():.2f}")

    return da.mean()

def test_wang_in_circular(N=3000):
    """Wang cascade in circular SHA-256: does it work better?"""
    print(f"\n--- WANG CASCADE IN CIRCULAR SHA-256 (N={N}) ---")

    dH_real = []; dH_circ = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)

        # Standard Wang cascade
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1)

        # Real hash difference
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        dh_r = sum(hw(Hn[w] ^ Hf[w]) for w in range(8))
        dH_real.append(dh_r)

        # Circular hash difference (using same Wang messages)
        Hcn = circ_sha256_compress(Wn); Hcf = circ_sha256_compress(Wf)
        dh_c = sum(hw(Hcn[w] ^ Hcf[w]) for w in range(8))
        dH_circ.append(dh_c)

    dr = np.array(dH_real); dc = np.array(dH_circ)

    print(f"Wang cascade δH:")
    print(f"  Real SHA-256:     mean={dr.mean():.2f}, std={dr.std():.2f}, min={dr.min()}")
    print(f"  Circular SHA-256: mean={dc.mean():.2f}, std={dc.std():.2f}, min={dc.min()}")
    print(f"  Correlation: {np.corrcoef(dr, dc)[0,1]:+.6f}")

    # Is circular HARDER or EASIER to collide?
    if dc.mean() < dr.mean():
        print(f"  Circular is {dr.mean() - dc.mean():.1f} bits EASIER")
    else:
        print(f"  Circular is {dc.mean() - dr.mean():.1f} bits HARDER")

    return dc.mean(), dr.mean()

def test_circular_collision_structure(N=2000):
    """Algebraic structure of circular collision equation.

    Key: circ_SHA256 is ROTR-equivariant.
    So: if M collides with M' in circ_SHA256,
    then ROTR_k(M) collides with ROTR_k(M') for ALL k.

    This means: collisions come in ORBITS of size 32.
    Each collision gives 31 more for free!

    Effective collision space: 256/32 = 8 bits smaller.
    Birthday: 2^{(256-8)/2} = 2^{124}?"""
    print(f"\n--- CIRCULAR COLLISION ORBITS (N={N}) ---")

    # Verify: circ_SHA256(ROTR_k(M)) = ROTR_k(circ_SHA256(M))
    # Already verified in test_equivariance, but let's check collisions

    # If M1, M2 give circ_collision:
    # circ(M1) = circ(M2)
    # → circ(ROTR_k(M1)) = ROTR_k(circ(M1)) = ROTR_k(circ(M2)) = circ(ROTR_k(M2))
    # → ROTR_k(M1), ROTR_k(M2) also collide!

    # Orbit size = 32 (rotations 0..31)
    # But: some orbits might be smaller (if message has rotational symmetry)

    # Measure: for random messages, how many distinct ROTR_k(M) are there?
    orbit_sizes = []
    for _ in range(N):
        W16 = random_w16()
        orbit = set()
        for k in range(32):
            W16_rot = tuple(rotr(w, k) for w in W16)
            orbit.add(W16_rot)
        orbit_sizes.append(len(orbit))

    os_arr = np.array(orbit_sizes)
    print(f"Message orbit sizes under Z_32:")
    print(f"  Mean: {os_arr.mean():.2f}")
    print(f"  Min: {os_arr.min()}")
    print(f"  All size 32: {np.sum(os_arr == 32)/N:.6f}")

    if os_arr.mean() > 31.9:
        print(f"\n  Almost all orbits have size 32")
        print(f"  → Each collision gives 31 free collisions")
        print(f"  → Effective search space: 2^{{512}}/32 per pair")
        print(f"  → Birthday: 2^{{(256 - log2(32))/2}} = 2^{{(256-5)/2}} = 2^{{125.5}}")
        print(f"  → Gain: 2.5 bits (from 2^128 to 2^125.5)")

    # But this only applies to circular SHA-256, not real SHA-256!
    # The 2.5-bit gain is in circular space, and the boundary correction
    # might eat it back.

    # Cross-check: if real SHA-256 has NO ROTR equivariance,
    # then the orbit argument doesn't apply
    print(f"\nVerify: does REAL SHA-256 have ROTR equivariance?")
    n_equiv_real = 0
    for _ in range(200):
        W16 = random_w16()
        H = sha256_compress(W16)
        k = random.choice([1, 2, 6, 11])
        W16_rot = [rotr(w, k) for w in W16]
        H_rot = sha256_compress(W16_rot)
        H_expected = [rotr(H[w], k) for w in range(8)]
        if H_rot == H_expected:
            n_equiv_real += 1
    print(f"  Real SHA-256 ROTR-equivariant: {n_equiv_real}/200")

    return os_arr.mean()

def test_circular_cascade_R(N=2000):
    """Measure TRUE inter-round R in circular SHA-256.

    Previous exp107 measured carry persistence = 16/32 = random.
    But that was measuring the WRONG thing (carry_diff between rounds).

    Correct measurement: mutual information between round r and round r+1
    in the FULL circular system."""
    print(f"\n--- TRUE INTER-ROUND R (CIRCULAR) (N={N}) ---")

    # Measure: if we flip 1 bit of W[0], how many state bits change
    # at each round? Compare circular vs real SHA-256.

    for label, rounds_fn in [("Real SHA-256", sha256_rounds), ("Circular SHA-256", circ_sha256_rounds)]:
        print(f"\n  {label}:")
        flips_per_round = []
        for _ in range(N):
            W16 = random_w16()
            base = rounds_fn(W16, 64)

            # Flip bit 0 of W[0]
            W16p = list(W16); W16p[0] ^= 1
            pert = rounds_fn(W16p, 64)

            round_flips = []
            for r in range(1, 65):
                diff = sum(hw(base[r][w] ^ pert[r][w]) for w in range(8))
                round_flips.append(diff)
            flips_per_round.append(round_flips)

        fp = np.array(flips_per_round)
        for r in [1, 2, 4, 8, 16, 32, 48, 64]:
            avg = fp[:, r-1].mean()
            print(f"    Round {r:>2}: {avg:.2f} bits affected")

    # The KEY comparison: does circular SHA-256 diffuse SLOWER?
    # If yes → more structure preserved → easier to control

def test_collision_bridge(N=5000):
    """If we find a circ_collision, how close is it to a real collision?

    circ_SHA256(M) = circ_SHA256(M')
    → real_SHA256(M) ⊕ real_SHA256(M') = boundary_error(M) ⊕ boundary_error(M')

    How many bits is this boundary error?"""
    print(f"\n--- COLLISION BRIDGE: CIRCULAR → REAL (N={N}) ---")

    # We can't find actual circ_collisions (still 2^128).
    # But we can measure: for random pairs, what's the DIFFERENCE
    # between circ_diff and real_diff?

    bridge_dists = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, _, _ = wang_cascade(W0, W1)

        Hr = sha256_compress(Wn); Hr2 = sha256_compress(Wf)
        Hc = circ_sha256_compress(Wn); Hc2 = circ_sha256_compress(Wf)

        dH_real = [Hr[w] ^ Hr2[w] for w in range(8)]
        dH_circ = [Hc[w] ^ Hc2[w] for w in range(8)]

        # Bridge = dH_real ⊕ dH_circ (what you need to correct)
        bridge = sum(hw(dH_real[w] ^ dH_circ[w]) for w in range(8))
        bridge_dists.append(bridge)

    bd = np.array(bridge_dists)
    print(f"Bridge distance (bits to correct circ→real):")
    print(f"  Mean: {bd.mean():.2f}")
    print(f"  Std: {bd.std():.2f}")
    print(f"  Min: {bd.min()}")

    # If bridge = B bits, then:
    # circ_collision cost = 2^{128} (or 2^125.5 with orbits)
    # Bridge correction cost = 2^{B/2} (birthday on bridge bits)
    # Total: max(2^125.5, 2^{B/2})

    B = bd.mean()
    print(f"\n  If circ_collision found:")
    print(f"    Bridge correction: {B:.0f} bits → 2^{B/2:.0f}")
    print(f"    Circ collision (with orbits): 2^125.5")
    print(f"    Total: max(2^125.5, 2^{B/2:.0f}) = 2^{max(125.5, B/2):.0f}")

    if B/2 > 128:
        print(f"    Bridge DOMINATES! Circular doesn't help.")
    elif B/2 < 125:
        print(f"    *** BRIDGE IS CHEAP! Total = 2^125.5 ***")
    else:
        print(f"    Similar to birthday bound.")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 108: CIRCULAR SHA-256")
    print("Full ROTR-equivariant hash function")
    print("=" * 60)

    equiv = test_equivariance(300)
    dist = test_distance_from_real(500)
    test_wang_in_circular(2000)
    test_circular_collision_structure(1000)
    test_circular_cascade_R(500)
    test_collision_bridge(3000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Circular SHA-256")
    print(f"  ROTR-equivariant: {equiv:.6f}")
    print(f"  Distance from real: {dist:.2f} bits")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
