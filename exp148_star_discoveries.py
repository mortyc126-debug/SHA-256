#!/usr/bin/env python3
"""
EXP 148: ★-DISCOVERIES — Four New Mathematical Objects

D1: ★-Channels — How many output bits are XOR-channel-only?
D2: ★-Depth — Carry resolution depth per addition
D3: ★-Fiber — Geometry of projection preimages
D4: ★-Pairing — New coupling measure between messages
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# D1: ★-CHANNELS — XOR vs Carry channel separation
# ============================================================
def star_depth(a, b):
    """★-depth: iterations until carry = 0."""
    x = a ^ b
    c = a & b
    depth = 0
    while c != 0 and depth < 32:
        c_shifted = (c << 1) & MASK
        x_new = x ^ c_shifted
        c_new = x & c_shifted
        x = x_new
        c = c_new
        depth += 1
    return depth

def test_xor_channel(N=500):
    """How many output bits of SHA-256 are determined by XOR-channel?"""
    print(f"\n{'='*60}")
    print(f"D1: ★-XOR CHANNEL REACH")
    print(f"{'='*60}")

    # Build XOR-only SHA-256 (replace + with ⊕)
    def xor_round(state, W_r, K_r):
        a, b, c, d, e, f, g, h = state
        T1 = h ^ sigma1(e) ^ ch(e, f, g) ^ K_r ^ W_r
        T2 = sigma0(a) ^ maj(a, b, c)
        return [T1 ^ T2, a, b, c, d ^ T1, e, f, g]

    # Compare XOR-SHA vs real SHA at each round
    print(f"\n  Bits agreeing between XOR-SHA and real SHA per round:")
    for R in [1, 2, 4, 8, 16, 32, 64]:
        agreements = []
        for _ in range(N):
            M = random_w16()
            W = schedule(M)

            s_real = list(IV); s_xor = list(IV)
            for r in range(R):
                s_real = sha256_round(s_real, W[r], K[r])
                s_xor = xor_round(s_xor, W[r], K[r])

            # Count agreeing bits
            agree = sum(32 - hw(s_real[w] ^ s_xor[w]) for w in range(8))
            agreements.append(agree)

        arr = np.array(agreements)
        xor_bits = arr.mean() - 128  # Subtract random baseline
        print(f"    Round {R:>2}: agree={arr.mean():.1f}/256 "
              f"(above random: {xor_bits:+.1f} bits)")

# ============================================================
# D2: ★-DEPTH — Carry chain depth
# ============================================================
def test_star_depth(N=500):
    """★-depth distribution across SHA-256 additions."""
    print(f"\n{'='*60}")
    print(f"D2: ★-DEPTH DISTRIBUTION")
    print(f"{'='*60}")

    # Random additions
    depths_random = [star_depth(random.randint(0, MASK),
                                random.randint(0, MASK)) for _ in range(N*10)]

    # SHA-256 internal additions
    depths_sha = []
    for _ in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)
        W = schedule(M)
        for r in range(64):
            s = states[r]
            # T1 components: h + Σ₁(e) + ...
            d = star_depth(s[7], sigma1(s[4]))
            depths_sha.append(d)

    dr = np.array(depths_random); ds = np.array(depths_sha)
    print(f"\n  ★-depth distribution:")
    print(f"    {'Depth':>5} | {'Random':>8} | {'SHA-256':>8}")
    print(f"    " + "-" * 30)
    for d in range(8):
        pr = np.sum(dr == d) / len(dr)
        ps = np.sum(ds == d) / len(ds)
        marker = " ★" if abs(pr - ps) > 0.02 else ""
        print(f"    {d:>5} | {pr:>8.4f} | {ps:>8.4f}{marker}")

    print(f"\n    E[depth] random: {dr.mean():.3f}")
    print(f"    E[depth] SHA-256: {ds.mean():.3f}")

    eta = (3 * math.log2(3)) / 4 - 1
    print(f"    η = {eta:.6f}")
    print(f"    E[depth] ≈ 1/(1-2η) = {1/(1-2*eta):.3f}?")
    print(f"    log₃(E[depth]) = {math.log(dr.mean(), 3):.3f}")

# ============================================================
# D3: ★-FIBER — Geometry of projection fibers
# ============================================================
def test_star_fiber(N=300):
    """Study the fiber π_add⁻¹(H): how many ★-pairs project to same sum?"""
    print(f"\n{'='*60}")
    print(f"D3: ★-FIBER GEOMETRY")
    print(f"{'='*60}")

    # For a fixed sum S, the fiber = {(x,c): x + carry_resolve(c) = S}
    # x = S ⊕ carry_contribution, c determines carry

    # Count: for a fixed 32-bit sum, how many (x,c) pairs exist?
    # x is determined by c: x = S ⊕ (carry_chain(c) << 1)
    # But c is constrained: c must be a valid carry word

    # Valid carry words: c where c[i+1] depends on c[i] through GKP
    # Actually, ANY c is a valid AND component for SOME (a,b).
    # Given x and c: a = (x & ~c_shifted) | c, b = x ^ a
    # Wait, this is more complex. Let me think...

    # For sum = a + b:
    # x = a ⊕ b (XOR part)
    # c_word = carry_word(a, b) = ((a+b) ^ (a⊕b)) >> 1
    # a + b = x + 2 * c_word... no, a + b is the sum itself.

    # The fiber: all (a,b) with a+b = S (mod 2^32)
    # This is a 32-dimensional affine subspace (for each a, b = S-a)
    # In ★-space: ★(a, S-a) = (a ⊕ (S-a), a & (S-a))
    # As a varies: this traces a CURVE in ★-space

    S = random.randint(0, MASK)
    xor_components = []
    and_components = []
    depths = []

    for _ in range(N):
        a = random.randint(0, MASK)
        b = (S - a) & MASK  # b = S - a mod 2^32
        xor_components.append(a ^ b)
        and_components.append(a & b)
        depths.append(star_depth(a, b))

    xor_hw = [hw(x) for x in xor_components]
    and_hw = [hw(a) for a in and_components]

    print(f"\n  Fiber of sum S = 0x{S:08x}:")
    print(f"    E[HW(XOR)]: {np.mean(xor_hw):.2f} (random=16)")
    print(f"    E[HW(AND)]: {np.mean(and_hw):.2f} (random=8)")
    print(f"    E[★-depth]: {np.mean(depths):.2f}")
    print(f"    Std[HW(XOR)]: {np.std(xor_hw):.2f}")

    # KEY: is the fiber FLAT (linear) or CURVED?
    # Check: is XOR a linear function of a?
    # XOR = a ⊕ (S-a). Is this linear in a?

    # Test linearity: f(a₁ ⊕ a₂) =? f(a₁) ⊕ f(a₂) ⊕ f(0)
    f_zero = 0 ^ (S & MASK)  # f(0) = 0 ⊕ S = S
    linear_count = 0
    for _ in range(N):
        a1 = random.randint(0, MASK); a2 = random.randint(0, MASK)
        f_a1 = a1 ^ ((S - a1) & MASK)
        f_a2 = a2 ^ ((S - a2) & MASK)
        f_xor = (a1 ^ a2) ^ ((S - (a1 ^ a2)) & MASK)
        if f_xor == (f_a1 ^ f_a2 ^ f_zero):
            linear_count += 1

    lin_rate = linear_count / N
    print(f"\n    Fiber linearity: {lin_rate:.4f}")
    if lin_rate < 0.01:
        print(f"    ★-fiber is NONLINEAR (curved!)")
        print(f"    Curvature comes from carry: (S-a) depends nonlinearly on a")
    else:
        print(f"    ★-fiber is approximately linear")

    # Correlation between XOR and AND components in the fiber
    corr = np.corrcoef(xor_hw, and_hw)[0, 1]
    print(f"    corr(HW(XOR), HW(AND)) in fiber: {corr:+.4f}")

    if abs(corr) > 0.1:
        print(f"    ★-fiber has INTERNAL STRUCTURE (XOR↔AND correlated)")

# ============================================================
# D4: ★-PAIRING — New coupling measure
# ============================================================
def star_pairing(M1, M2):
    """★-pairing: total carry depth across all additions for the pair."""
    s1_all = sha256_rounds(M1, 64)
    s2_all = sha256_rounds(M2, 64)
    W1 = schedule(M1); W2 = schedule(M2)

    total_depth = 0
    for r in range(64):
        s1 = s1_all[r]; s2 = s2_all[r]
        # ★-depth of state difference + schedule difference
        for w in range(8):
            d = star_depth(s1[w] ^ s2[w], s1[w] & s2[w])
            total_depth += d
        # Schedule depth
        d_sched = star_depth(W1[r], W2[r])
        total_depth += d_sched

    return total_depth

def test_star_pairing(N=200):
    """Does ★-pairing predict collision closeness?"""
    print(f"\n{'='*60}")
    print(f"D4: ★-PAIRING — COLLISION PREDICTOR?")
    print(f"{'='*60}")

    pairings = []
    dHs = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        p = star_pairing(M1, M2)
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        pairings.append(p)
        dHs.append(dH)

    pa = np.array(pairings, dtype=float)
    da = np.array(dHs, dtype=float)

    corr = np.corrcoef(pa, da)[0, 1]
    print(f"\n  E[★-pairing]: {pa.mean():.1f}")
    print(f"  E[dH]: {da.mean():.1f}")
    print(f"  corr(★-pairing, dH): {corr:+.6f}")

    # Binned analysis
    p25 = np.percentile(pa, 25); p75 = np.percentile(pa, 75)
    low = da[pa <= p25].mean()
    high = da[pa >= p75].mean()
    print(f"\n  Low ★-pairing (P25): E[dH] = {low:.1f}")
    print(f"  High ★-pairing (P75): E[dH] = {high:.1f}")
    print(f"  Difference: {high - low:+.1f} bits")

    if abs(corr) > 0.05:
        print(f"\n  ★★★ ★-PAIRING CORRELATES WITH HASH DISTANCE!")
        print(f"  → Can be used as NATIVE collision predictor")
    else:
        print(f"\n  ★-pairing does not predict dH at full rounds")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 148: FOUR ★-DISCOVERIES")
    print("=" * 60)

    test_xor_channel(300)
    test_star_depth(300)
    test_star_fiber(200)
    test_star_pairing(150)

    print(f"\n{'='*60}")
    print(f"SUMMARY OF DISCOVERIES")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
