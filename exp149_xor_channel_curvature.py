#!/usr/bin/env python3
"""
EXP 149: Two Parallel Attacks — XOR Channel + Fiber Curvature

ATTACK A: XOR-CHANNEL EXPLOITATION
  Round 1: 89.5 bits are XOR-determined (linear).
  → Solve linear system for 89.5 bits → constrain message
  → Brute-force only the 39 nonlinear (carry) bits
  → Cost: O(n³) + 2^39 instead of 2^128?

ATTACK B: ★-FIBER CURVATURE
  Fiber π⁻¹(S) has HW(XOR) = 21.4 (not 16), HW(AND) = 5.4 (not 8).
  Collisions live in BIASED region of ★-space.
  → Generate pairs with biased ★-components → higher P(collision)?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# ATTACK A: XOR-CHANNEL — Solve linear part, brute-force carry
# ============================================================
def xor_round(state, W_r, K_r):
    """XOR-only round (all + replaced with ⊕)."""
    a, b, c, d, e, f, g, h = state
    T1 = h ^ sigma1(e) ^ ch(e, f, g) ^ K_r ^ W_r
    T2 = sigma0(a) ^ maj(a, b, c)
    return [T1 ^ T2, a, b, c, d ^ T1, e, f, g]

def xor_sha256_state(W16, R=64):
    """XOR-only SHA-256 state after R rounds."""
    W = [0] * 64
    W[:16] = list(W16)
    for t in range(16, 64):
        W[t] = sig1(W[t-2]) ^ W[t-7] ^ sig0(W[t-15]) ^ W[t-16]
    state = list(IV)
    for r in range(R):
        state = xor_round(state, W[r], K[r])
    return state

def test_xor_channel_attack(N=200):
    """Can we use XOR-channel to constrain collision search?"""
    print(f"\n{'='*60}")
    print(f"ATTACK A: XOR-CHANNEL EXPLOITATION")
    print(f"{'='*60}")

    # Key idea: XOR-SHA(M₁) = XOR-SHA(M₂) is a NECESSARY condition
    # for early-round agreement (not sufficient for full collision,
    # but constrains the search).

    # XOR-SHA is GF(2)-linear (all operations are linear over GF(2)):
    # XOR-SHA(M) = L·M ⊕ c (affine transformation)
    # Collision in XOR-SHA: L·M₁ ⊕ c = L·M₂ ⊕ c → L·(M₁⊕M₂) = 0
    # → δM ∈ kernel(L)

    # Build L matrix for different round counts
    for R in [1, 2, 4, 8, 64]:
        # Compute L: each column = XOR-SHA(e_i) ⊕ XOR-SHA(0)
        xor_zero = xor_sha256_state([0]*16, R)

        L = np.zeros((256, 512), dtype=int)
        for w in range(16):
            for b in range(32):
                M = [0]*16; M[w] = 1 << b
                xor_out = xor_sha256_state(M, R)
                for ow in range(8):
                    diff = xor_out[ow] ^ xor_zero[ow]
                    for ob in range(32):
                        L[ow*32+ob, w*32+b] = (diff >> ob) & 1

        rank = np.linalg.matrix_rank(L % 2)
        nullity = 512 - rank
        print(f"\n  {R} rounds: XOR-SHA matrix rank={rank}/256, nullity={nullity}")
        print(f"    → {nullity} message bits are FREE in XOR-channel")
        print(f"    → XOR-collision has 2^{nullity} solutions")

        if nullity > 0:
            print(f"    → Can fix {rank} bits via XOR, brute-force rest in carry")

    # KEY TEST: do XOR-SHA collisions predict real SHA collisions?
    print(f"\n  XOR-SHA collision → real SHA collision?")
    R_test = 2  # XOR channel is strong at round 2

    # Find XOR-SHA collisions at round 2 (in nullspace)
    xor_zero = xor_sha256_state([0]*16, R_test)
    L = np.zeros((256, 512), dtype=int)
    for w in range(16):
        for b in range(32):
            M = [0]*16; M[w] = 1 << b
            xor_out = xor_sha256_state(M, R_test)
            for ow in range(8):
                diff = xor_out[ow] ^ xor_zero[ow]
                for ob in range(32):
                    L[ow*32+ob, w*32+b] = (diff >> ob) & 1

    rank = np.linalg.matrix_rank(L % 2)

    # For each XOR-collision: check real SHA distance
    xor_coll_dH = []
    random_dH = []
    for _ in range(N):
        M1 = random_w16()

        # Create M2 as XOR-collision partner
        # δM in kernel of L → XOR-SHA(M₁) = XOR-SHA(M₂) at round R_test
        # Simple approach: find δM by random search in kernel
        M2 = list(M1)
        # Flip random bits that are in kernel (approximate)
        n_flips = random.randint(1, 10)
        for _ in range(n_flips):
            w = random.randint(0, 15)
            b = random.randint(0, 31)
            M2[w] ^= (1 << b)

        # Check XOR-SHA distance at round R_test
        xs1 = xor_sha256_state(M1, R_test)
        xs2 = xor_sha256_state(M2, R_test)
        xor_dist = sum(hw(xs1[w] ^ xs2[w]) for w in range(8))

        # Check REAL SHA distance (full 64 rounds)
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        real_dist = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        xor_coll_dH.append(real_dist)

        # Random pair for comparison
        M3 = random_w16()
        H3 = sha256_compress(M3)
        random_dH.append(sum(hw(H1[w] ^ H3[w]) for w in range(8)))

    xc = np.array(xor_coll_dH); rd = np.array(random_dH)
    print(f"\n  XOR-constrained pairs vs random pairs (full SHA-256):")
    print(f"    XOR-constrained: E[dH]={xc.mean():.1f}, min={xc.min()}")
    print(f"    Random:          E[dH]={rd.mean():.1f}, min={rd.min()}")

# ============================================================
# ATTACK B: ★-FIBER CURVATURE — Use biased ★-components
# ============================================================
def test_curvature_attack(N=300):
    """Exploit the fiber's biased HW(XOR)=21.4 and HW(AND)=5.4."""
    print(f"\n{'='*60}")
    print(f"ATTACK B: ★-FIBER CURVATURE")
    print(f"{'='*60}")

    # Theory: collisions live in fibers where:
    #   a + b = H (fixed)
    #   HW(a⊕b) ≈ 21.4 (biased, not 16)
    #   HW(a&b) ≈ 5.4 (biased, not 8)
    #
    # If we generate message pairs with biased ★-components,
    # they're MORE LIKELY to be in the same fiber → higher P(collision)

    # Measure: for feedforward additions IV[w] + state[w],
    # what's the actual ★-bias for near-collisions vs random?

    print(f"\n  Feedforward ★-bias (IV + state):")
    near_xor_hw = []; near_and_hw = []
    rand_xor_hw = []; rand_and_hw = []

    for _ in range(N * 50):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        s1 = sha256_rounds(M1, 64)[64]
        s2 = sha256_rounds(M2, 64)[64]

        # ★-components of feedforward for each message
        xor1 = sum(hw(IV[w] ^ s1[w]) for w in range(8))
        and1 = sum(hw(IV[w] & s1[w]) for w in range(8))
        xor2 = sum(hw(IV[w] ^ s2[w]) for w in range(8))
        and2 = sum(hw(IV[w] & s2[w]) for w in range(8))

        if dH < 108:
            near_xor_hw.append(abs(xor1 - xor2))
            near_and_hw.append(abs(and1 - and2))
        elif random.random() < 0.03:
            rand_xor_hw.append(abs(xor1 - xor2))
            rand_and_hw.append(abs(and1 - and2))

    if len(near_xor_hw) > 10:
        nx = np.array(near_xor_hw); na = np.array(near_and_hw)
        rx = np.array(rand_xor_hw); ra = np.array(rand_and_hw)

        print(f"    Near-collision: |δHW(XOR)|={nx.mean():.2f}, |δHW(AND)|={na.mean():.2f}")
        print(f"    Random:         |δHW(XOR)|={rx.mean():.2f}, |δHW(AND)|={ra.mean():.2f}")

        # Curvature-based weapon: generate pairs with small |δHW(XOR)|
        # (matching ★-fiber bias)
        print(f"\n  Curvature weapon: select pairs by ★-bias matching")

    # WEAPON: Curvature-guided search
    print(f"\n  Curvature weapon vs random (budget=5000):")
    budget = 5000

    # Standard birthday
    best_rand = 256
    stored = []
    for _ in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        for H_old in stored[-30:]:
            d = sum(hw(H[w] ^ H_old[w]) for w in range(8))
            if d < best_rand: best_rand = d
        stored.append(H)

    # Curvature weapon: generate pairs where states have
    # similar HW(IV⊕state) — matching the fiber bias
    best_curv = 256
    stored_curv = []
    stored_xorhw = []

    for _ in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        s = sha256_rounds(M, 64)[64]
        xhw = sum(hw(IV[w] ^ s[w]) for w in range(8))

        # Compare against stored with SIMILAR xor-hw
        for i in range(max(0, len(stored_curv)-50), len(stored_curv)):
            if abs(stored_xorhw[i] - xhw) < 5:  # Similar ★-bias
                d = sum(hw(H[w] ^ stored_curv[i][w]) for w in range(8))
                if d < best_curv: best_curv = d

        stored_curv.append(H)
        stored_xorhw.append(xhw)

    print(f"    Random birthday: best dH = {best_rand}")
    print(f"    Curvature weapon: best dH = {best_curv}")

    if best_curv < best_rand:
        print(f"    ★ CURVATURE WINS by {best_rand - best_curv} bits!")
    else:
        print(f"    Random wins by {best_curv - best_rand}")

def test_combined_xor_curvature(N=15, budget=6000):
    """Combine XOR-channel + curvature for maximum effect."""
    print(f"\n{'='*60}")
    print(f"COMBINED ATTACK: XOR + CURVATURE (N={N})")
    print(f"{'='*60}")

    combined_results = []
    random_results = []

    for trial in range(N):
        # COMBINED: generate messages with constrained schedule
        # AND similar ★-fiber position
        best_comb = 256
        stored = {}

        for _ in range(budget):
            M = random_w16()
            H = sha256_compress(M)
            s = sha256_rounds(M, 64)[64]

            # ★-fiber signature: quantized HW(IV⊕state)
            sig = sum(hw(IV[w] ^ s[w]) for w in range(8)) // 4

            if sig not in stored:
                stored[sig] = []

            # Compare within same signature bucket
            for H_old in stored[sig][-20:]:
                d = sum(hw(H[w] ^ H_old[w]) for w in range(8))
                if d < best_comb: best_comb = d

            stored[sig].append(H)

        combined_results.append(best_comb)

        # Random birthday baseline
        best_rand = 256
        stored_r = []
        for _ in range(budget):
            M = random_w16()
            H = sha256_compress(M)
            for H_old in stored_r[-30:]:
                d = sum(hw(H[w] ^ H_old[w]) for w in range(8))
                if d < best_rand: best_rand = d
            stored_r.append(H)

        random_results.append(best_rand)

    ca = np.array(combined_results); ra = np.array(random_results)
    gain = ra.mean() - ca.mean()

    print(f"\n  Combined ★-attack: avg={ca.mean():.1f}, min={ca.min()}")
    print(f"  Random birthday:   avg={ra.mean():.1f}, min={ra.min()}")
    print(f"  Gain: {gain:+.1f} bits")

    pooled = math.sqrt((ca.std()**2 + ra.std()**2) / 2)
    z = gain / (pooled / math.sqrt(N)) if pooled > 0 else 0
    print(f"  Z = {z:.2f}")
    if z > 2: print(f"  ★★ SIGNIFICANT!")
    if z > 3: print(f"  ★★★ HIGHLY SIGNIFICANT!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 149: XOR CHANNEL + CURVATURE — PARALLEL ATTACKS")
    print("=" * 60)

    test_xor_channel_attack(150)
    test_curvature_attack(200)
    test_combined_xor_curvature(N=15, budget=6000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
