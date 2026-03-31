#!/usr/bin/env python3
"""
EXP 123: Hypothesis H₁ — Carry-Free Bits Form Affine Subspace

THEORY (from session):
  SHA-256 without carry = XOR-SHA-256 = linear over GF(2).
  Linear system → preimage = affine subspace → solvable in O(n³).

  Full SHA-256 has carry rank 243. So 256 - 243 = 13 bits are carry-free.
  These 13 bits should behave LINEARLY.

H₁: The carry-free bits of the hash form a GF(2)-linear function of M.
  If true: 13 constraints on M are LINEAR → solvable.
  Remaining 243 constraints are nonlinear (carry-dependent).

STEP 1: Identify which hash bits are carry-free.
  Carry-free bit = bit whose value doesn't depend on carry propagation.
  In addition H[w] = IV[w] + state[w]:
    Bit 0: H[w]_0 = IV[w]_0 ⊕ state[w]_0 (carry_in = 0, always)
    → Bit 0 of EVERY hash word is carry-free!
    That's 8 carry-free bits (one per word).

  But carry rank = 243 implies 256 - 243 = 13 carry-free dims.
  Where are the other 5?

STEP 2: Test linearity of carry-free bits over GF(2).
  If H[w]_0 = f(M) is linear over GF(2):
    f(M₁ ⊕ M₂) = f(M₁) ⊕ f(M₂)  for all M₁, M₂
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_hash_bit(W16, word, bit):
    """Get specific bit of SHA-256 hash."""
    H = sha256_compress(W16)
    return (H[word] >> bit) & 1

def get_state_bit(W16, word, bit, R=64):
    """Get specific bit of state after R rounds."""
    states = sha256_rounds(W16, R)
    return (states[R][word] >> bit) & 1

def test_bit0_linearity(N=5000):
    """Test: is bit 0 of each hash word linear over GF(2)?

    H[w]_0 = IV[w]_0 ⊕ state[w]_0  (carry_in = 0 for bit 0)

    So H[w]_0 is linear iff state[w]_0 is linear in M.
    state[w]_0 depends on 64 rounds — is it still linear?"""
    print(f"\n--- BIT 0 LINEARITY TEST (N={N}) ---")

    # Test: f(M₁ ⊕ M₂) =? f(M₁) ⊕ f(M₂)
    # For a GF(2)-linear function, this must hold for ALL M₁, M₂.

    for w in range(8):
        linear_count = 0
        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            M_xor = [M1[i] ^ M2[i] for i in range(16)]

            b1 = get_hash_bit(M1, w, 0)
            b2 = get_hash_bit(M2, w, 0)
            b_xor = get_hash_bit(M_xor, w, 0)

            # Linear: b_xor should equal b1 ⊕ b2
            # But wait — linearity means f(M1 ⊕ M2) = f(M1) ⊕ f(M2)
            # This requires f(0) = 0 (homogeneous) or f is AFFINE.
            # SHA-256 has IV ≠ 0, so it's affine at best.
            # Affine: f(M1 ⊕ M2) ⊕ f(0) = f(M1) ⊕ f(M2) ⊕ f(0)
            # Or: f(M1 ⊕ M2) = f(M1) ⊕ f(M2) ⊕ f(0)

            if _ == 0:
                # Compute f(0)
                M_zero = [0] * 16
                b_zero = get_hash_bit(M_zero, w, 0)

            # Test affine linearity
            if b_xor == (b1 ^ b2 ^ b_zero):
                linear_count += 1

        rate = linear_count / N
        expected_random = 0.5
        z = (rate - expected_random) / math.sqrt(expected_random * (1 - expected_random) / N)
        marker = "LINEAR!" if rate > 0.99 else ("partial" if rate > 0.6 else "nonlinear")
        print(f"  H[{w}] bit 0: affine rate = {rate:.6f} (Z={z:+.1f}) → {marker}")

def test_all_bits_linearity(N=3000):
    """Test linearity of ALL 256 hash bits."""
    print(f"\n--- ALL BITS LINEARITY (N={N}) ---")

    # Compute f(0) for all bits
    M_zero = [0] * 16
    H_zero = sha256_compress(M_zero)
    f_zero = []
    for w in range(8):
        for b in range(32):
            f_zero.append((H_zero[w] >> b) & 1)

    # Test each bit
    linear_rates = np.zeros(256)

    for trial in range(N):
        M1 = random_w16(); M2 = random_w16()
        M_xor = [M1[i] ^ M2[i] for i in range(16)]

        H1 = sha256_compress(M1)
        H2 = sha256_compress(M2)
        H_xor = sha256_compress(M_xor)

        for w in range(8):
            for b in range(32):
                b1 = (H1[w] >> b) & 1
                b2 = (H2[w] >> b) & 1
                b_xor = (H_xor[w] >> b) & 1
                fz = f_zero[w * 32 + b]

                # Affine linearity test
                if b_xor == (b1 ^ b2 ^ fz):
                    linear_rates[w * 32 + b] += 1

    linear_rates /= N

    # Sort by linearity rate
    bit_indices = np.argsort(-linear_rates)

    print(f"  Most linear hash bits:")
    print(f"  {'Word':>4} {'Bit':>4} | {'Rate':>8} | {'Status'}")
    print(f"  " + "-" * 35)

    n_linear = 0
    n_partial = 0
    for idx in bit_indices[:30]:
        w = idx // 32; b = idx % 32
        rate = linear_rates[idx]
        status = "LINEAR!" if rate > 0.99 else ("PARTIAL" if rate > 0.55 else "random")
        if rate > 0.55:
            print(f"  {w:>4} {b:>4} | {rate:>8.6f} | {status}")
        if rate > 0.99:
            n_linear += 1
        if rate > 0.55:
            n_partial += 1

    print(f"\n  Summary:")
    print(f"    Fully linear (>0.99): {n_linear} bits")
    print(f"    Partially linear (>0.55): {n_partial} bits")
    print(f"    Expected carry-free: 13 bits")

    # Is bit 0 special?
    bit0_rates = [linear_rates[w * 32] for w in range(8)]
    print(f"\n  Bit 0 rates per word: {[f'{r:.4f}' for r in bit0_rates]}")

    return linear_rates

def test_xor_sha256(N=2000):
    """Build XOR-SHA-256 (all + replaced with ⊕) and verify it's linear."""
    print(f"\n--- XOR-SHA-256: LINEARITY VERIFICATION (N={N}) ---")

    def xor_round(state, W_r, K_r):
        a, b, c, d, e, f, g, h = state
        T1 = h ^ sigma1(e) ^ ch(e, f, g) ^ K_r ^ W_r
        T2 = sigma0(a) ^ maj(a, b, c)
        return [T1 ^ T2, a, b, c, d ^ T1, e, f, g]

    def xor_schedule(W16):
        W = list(W16) + [0] * 48
        for t in range(16, 64):
            W[t] = sig1(W[t-2]) ^ W[t-7] ^ sig0(W[t-15]) ^ W[t-16]
        return W

    def xor_sha256(W16):
        W = xor_schedule(W16)
        state = list(IV)
        for r in range(64):
            state = xor_round(state, W[r], K[r])
        return [IV[i] ^ state[i] for i in range(8)]

    # Test linearity: f(M1 ⊕ M2) ⊕ f(0) = f(M1) ⊕ f(M2) ⊕ f(0)?
    H_zero = xor_sha256([0] * 16)
    linear_pass = 0

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        M_xor = [M1[i] ^ M2[i] for i in range(16)]

        H1 = xor_sha256(M1)
        H2 = xor_sha256(M2)
        H_xor = xor_sha256(M_xor)

        # Affine: H_xor ⊕ H_zero = (H1 ⊕ H_zero) ⊕ (H2 ⊕ H_zero)
        # → H_xor = H1 ⊕ H2 ⊕ H_zero
        expected = [H1[w] ^ H2[w] ^ H_zero[w] for w in range(8)]

        if expected == H_xor:
            linear_pass += 1

    rate = linear_pass / N
    print(f"  XOR-SHA-256 affine linearity: {rate:.6f}")
    if rate > 0.999:
        print(f"  *** XOR-SHA-256 IS PERFECTLY LINEAR! ***")
        print(f"  → Collision in XOR-SHA-256 = solve GF(2) system")

        # Compute rank of XOR-SHA-256 (as GF(2) matrix)
        # Each input bit maps to 256 output bits
        matrix = np.zeros((256, 512), dtype=int)
        for w in range(16):
            for b in range(32):
                M = [0] * 16
                M[w] = 1 << b
                H = xor_sha256(M)
                H_col = [H[i] ^ H_zero[i] for i in range(8)]  # Remove affine offset
                for ow in range(8):
                    for ob in range(32):
                        matrix[ow * 32 + ob, w * 32 + b] = (H_col[ow] >> ob) & 1

        rank = np.linalg.matrix_rank(matrix % 2)
        nullity = 512 - rank
        print(f"\n  XOR-SHA-256 GF(2) matrix:")
        print(f"    Size: 256 × 512")
        print(f"    Rank: {rank}")
        print(f"    Nullity: {nullity}")
        print(f"    → {nullity}-dimensional preimage (affine subspace)")
        print(f"    → XOR-collision: any two elements of null space")
        if nullity > 0:
            print(f"    → XOR-SHA-256 collision found in O({rank}³) = O({rank**3})")

    return rate

def test_carry_perturbation(N=2000):
    """How far is real SHA-256 from XOR-SHA-256?
    This measures the CARRY CONTRIBUTION to each hash bit."""
    print(f"\n--- CARRY PERTURBATION: SHA-256 vs XOR-SHA-256 (N={N}) ---")

    def xor_round(state, W_r, K_r):
        a, b, c, d, e, f, g, h = state
        T1 = h ^ sigma1(e) ^ ch(e, f, g) ^ K_r ^ W_r
        T2 = sigma0(a) ^ maj(a, b, c)
        return [T1 ^ T2, a, b, c, d ^ T1, e, f, g]

    def xor_schedule(W16):
        W = list(W16) + [0] * 48
        for t in range(16, 64):
            W[t] = sig1(W[t-2]) ^ W[t-7] ^ sig0(W[t-15]) ^ W[t-16]
        return W

    def xor_sha256(W16):
        W = xor_schedule(W16)
        state = list(IV)
        for r in range(64):
            state = xor_round(state, W[r], K[r])
        return [IV[i] ^ state[i] for i in range(8)]

    diffs = []
    for _ in range(N):
        M = random_w16()
        H_real = sha256_compress(M)
        H_xor = xor_sha256(M)
        d = sum(hw(H_real[w] ^ H_xor[w]) for w in range(8))
        diffs.append(d)

    da = np.array(diffs)
    print(f"  HW(SHA256(M) ⊕ XOR-SHA256(M)):")
    print(f"    Mean: {da.mean():.2f} (random=128)")
    print(f"    Std: {da.std():.2f}")
    print(f"    Min: {da.min()}")

    # Per-bit: which bits differ most?
    bit_diffs = np.zeros(256)
    for _ in range(N):
        M = random_w16()
        H_real = sha256_compress(M)
        H_xor = xor_sha256(M)
        for w in range(8):
            d = H_real[w] ^ H_xor[w]
            for b in range(32):
                if (d >> b) & 1:
                    bit_diffs[w * 32 + b] += 1

    bit_diffs /= N
    # Find bits that are MOST SIMILAR between real and XOR
    most_similar = np.argsort(bit_diffs)
    print(f"\n  Bits most SIMILAR to XOR-SHA-256 (carry-free candidates):")
    for idx in most_similar[:20]:
        w = idx // 32; b = idx % 32
        print(f"    H[{w}] bit {b:>2}: diff_rate = {bit_diffs[idx]:.4f}")

    n_carryfree = np.sum(bit_diffs < 0.1)
    n_partial = np.sum(bit_diffs < 0.3)
    print(f"\n  Carry-free (<10% diff): {n_carryfree} bits")
    print(f"  Partially carry-free (<30% diff): {n_partial} bits")

    return bit_diffs

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 123: HYPOTHESIS H₁")
    print("Do carry-free bits form affine subspace?")
    print("=" * 60)

    test_bit0_linearity(3000)
    rates = test_all_bits_linearity(2000)
    xor_rate = test_xor_sha256(1000)
    carry_pert = test_carry_perturbation(1000)

    print(f"\n{'='*60}")
    print(f"H₁ VERDICT")
    print(f"{'='*60}")

    n_linear = np.sum(rates > 0.99)
    n_partial = np.sum(rates > 0.55)

    print(f"  Fully GF(2)-linear hash bits: {n_linear}/256")
    print(f"  Partially linear: {n_partial}/256")
    print(f"  XOR-SHA-256 linearity: {xor_rate:.6f}")

    if n_linear > 0:
        print(f"\n  H₁ PARTIALLY CONFIRMED: {n_linear} carry-free linear bits exist")
        print(f"  These bits form an affine subspace of GF(2)^512")
        print(f"  → {n_linear} free constraints, {256-n_linear} carry-dependent")
    else:
        print(f"\n  H₁ REJECTED: no fully linear bits in full SHA-256")
        print(f"  Carry propagation reaches ALL bits by round 64")

if __name__ == "__main__":
    main()
