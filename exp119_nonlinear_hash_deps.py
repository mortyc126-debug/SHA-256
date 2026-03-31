#!/usr/bin/env python3
"""
EXP 119: Nonlinear Dependencies Between Hash Words

STANDARD: PCA showed 256 LINEARLY independent bits. But nonlinear
dependencies (polynomials, Boolean functions) are invisible to PCA.

QUESTION: Does f(H[0], H[1], ..., H[7]) = 0 for some nonlinear f?
If yes → effective hash dimension < 256 → birthday < 2^128.

★-NATIVE METHOD: Test dependencies using ★-native operations:
  - H[i] ⊕ H[j] ⊕ carry(H[i], H[j]) = known pattern?
  - ★(H[i], H[j]) has constrained AND-component?
  - Products, parities, carries between hash words

If standard polynomial detection fails but ★-native detection
finds something → that's the native structure we're looking for.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def test_pairwise_nonlinear(N=20000):
    """Test pairwise nonlinear relations between hash words."""
    print(f"\n--- PAIRWISE NONLINEAR RELATIONS (N={N}) ---")

    # Collect hashes
    hashes = np.zeros((N, 8), dtype=np.int64)
    for i in range(N):
        W16 = random_w16()
        H = sha256_compress(W16)
        for w in range(8):
            hashes[i, w] = H[w]

    # Test 1: H[i] & H[j] — has it nonrandom parity?
    print(f"\n  Test 1: Parity of H[i] & H[j] (random = 0.5)")
    for i in range(8):
        for j in range(i+1, min(i+3, 8)):
            parities = np.array([hw(int(hashes[k,i]) & int(hashes[k,j])) % 2
                                for k in range(N)])
            p = parities.mean()
            z = (p - 0.5) / (0.5 / math.sqrt(N))
            if abs(z) > 3:
                print(f"    H[{i}] & H[{j}] parity: {p:.6f} Z={z:+.2f} ***")

    # Test 2: carry(H[i], H[j]) — any structure?
    print(f"\n  Test 2: HW(carry(H[i], H[j])) (random ≈ 10.67)")
    for i in range(8):
        for j in range(i+1, min(i+3, 8)):
            carry_hws = np.array([hw(carry_word(int(hashes[k,i]), int(hashes[k,j])))
                                 for k in range(N)])
            mean_c = carry_hws.mean()
            # Expected: for random 32-bit words, E[HW(carry)] ≈ 10.67
            z = (mean_c - 10.67) / (carry_hws.std() / math.sqrt(N))
            marker = "***" if abs(z) > 3 else ""
            if abs(z) > 2:
                print(f"    carry(H[{i}], H[{j}]): mean={mean_c:.4f} Z={z:+.2f} {marker}")

    # Test 3: ★(H[i], H[j]) AND component — constrained?
    print(f"\n  Test 3: HW(H[i] & H[j]) (random ≈ 8.0)")
    for i in range(8):
        for j in range(i+1, min(i+3, 8)):
            and_hws = np.array([hw(int(hashes[k,i]) & int(hashes[k,j]))
                               for k in range(N)])
            mean_a = and_hws.mean()
            z = (mean_a - 8.0) / (and_hws.std() / math.sqrt(N))
            marker = "***" if abs(z) > 3 else ""
            if abs(z) > 2:
                print(f"    H[{i}] & H[{j}]: mean={mean_a:.4f} Z={z:+.2f} {marker}")

    # Test 4: XOR of all hash words (should be random)
    print(f"\n  Test 4: ⊕-sum of all hash words")
    xor_all = np.zeros(N, dtype=int)
    for i in range(N):
        x = 0
        for w in range(8):
            x ^= int(hashes[i, w])
        xor_all[i] = x

    xor_hw = np.array([hw(int(x)) for x in xor_all])
    print(f"    E[HW(H[0]⊕...⊕H[7])]: {xor_hw.mean():.4f} (random=16.0)")
    z = (xor_hw.mean() - 16.0) / (xor_hw.std() / math.sqrt(N))
    print(f"    Z = {z:+.2f}")

    # Test 5: +-sum of all hash words (mod 2^32)
    print(f"\n  Test 5: +-sum of all hash words")
    add_all = np.zeros(N, dtype=int)
    for i in range(N):
        s = 0
        for w in range(8):
            s = (s + int(hashes[i, w])) & MASK
        add_all[i] = s

    add_hw = np.array([hw(int(x)) for x in add_all])
    print(f"    E[HW(H[0]+...+H[7])]: {add_hw.mean():.4f} (random=16.0)")
    z = (add_hw.mean() - 16.0) / (add_hw.std() / math.sqrt(N))
    print(f"    Z = {z:+.2f}")

def test_higher_order_boolean(N=30000):
    """Higher-order Boolean functions of hash bits."""
    print(f"\n--- HIGHER-ORDER BOOLEAN FUNCTIONS (N={N}) ---")

    # Collect raw bits
    bits = np.zeros((N, 256), dtype=np.int8)
    for i in range(N):
        W16 = random_w16()
        H = sha256_compress(W16)
        for w in range(8):
            for b in range(32):
                bits[i, w*32+b] = (H[w] >> b) & 1

    # Test quadratic relations: b_i * b_j = b_k + const?
    # Sample random triples
    print(f"  Testing quadratic relations: b_i · b_j ⊕ b_k = const")
    n_tested = 0
    n_significant = 0

    for _ in range(5000):
        i = random.randint(0, 255)
        j = random.randint(0, 255)
        k = random.randint(0, 255)
        if i == j or i == k or j == k:
            continue

        # Test: b_i * b_j ⊕ b_k
        product = (bits[:, i] & bits[:, j]) ^ bits[:, k]
        p = product.mean()
        # For random independent bits: E[b_i * b_j ⊕ b_k] = 0.25*0 + 0.25*1 + 0.25*1 + 0.25*0 = 0.5
        # Hmm, actually: P(b_i·b_j = 1) = 0.25, P(b_k = 1) = 0.5
        # P(b_i·b_j ⊕ b_k = 0) = P(both 0) + P(both 1) = 0.75*0.5 + 0.25*0.5 = 0.5
        expected = 0.5
        z = (p - expected) / math.sqrt(expected * (1-expected) / N)
        n_tested += 1
        if abs(z) > 4:
            n_significant += 1

    print(f"    Tested: {n_tested}")
    print(f"    Significant (|Z|>4): {n_significant}")
    expected_false = n_tested * 0.0000633  # P(|Z|>4) for normal
    print(f"    Expected false positives: {expected_false:.1f}")
    if n_significant > expected_false * 3:
        print(f"    *** EXCESS SIGNIFICANT RELATIONS! ***")
    else:
        print(f"    No excess (consistent with random)")

    # Test degree-3: b_i · b_j · b_k constant?
    print(f"\n  Testing cubic relations: b_i · b_j · b_k = const")
    n_tested = 0; n_significant = 0
    for _ in range(3000):
        i, j, k = random.sample(range(256), 3)
        product = bits[:, i] & bits[:, j] & bits[:, k]
        p = product.mean()
        expected = 0.125  # P(all three = 1) for random
        z = (p - expected) / math.sqrt(expected * (1-expected) / N)
        n_tested += 1
        if abs(z) > 4:
            n_significant += 1

    print(f"    Tested: {n_tested}")
    print(f"    Significant (|Z|>4): {n_significant}")
    expected_false = n_tested * 0.0000633
    print(f"    Expected false positives: {expected_false:.1f}")
    if n_significant > expected_false * 3:
        print(f"    *** EXCESS SIGNIFICANT RELATIONS! ***")
    else:
        print(f"    No excess")

def test_star_native_deps(N=15000):
    """★-native nonlinear dependencies."""
    print(f"\n--- ★-NATIVE NONLINEAR DEPENDENCIES (N={N}) ---")

    # In ★-algebra: ★(a,b) = (a⊕b, a&b)
    # Hash words H[0]..H[7] come from: H[w] = IV[w] + state[w]
    # In ★: H[w] = π_add(★(IV[w], state[w]))
    #
    # The ★-pair (IV[w] ⊕ state[w], IV[w] & state[w]) has MORE info than H[w].
    # Do the ★-pairs across words have dependencies?

    # Since state[w] = H[w] - IV[w] mod 2^32, we can recover state from H:
    states = np.zeros((N, 8), dtype=np.int64)
    hashes = np.zeros((N, 8), dtype=np.int64)

    for i in range(N):
        W16 = random_w16()
        H = sha256_compress(W16)
        s = sha256_rounds(W16, 64)
        for w in range(8):
            hashes[i, w] = H[w]
            states[i, w] = s[64][w]

    # ★-dependency: carry(IV[w], state[w]) across words
    print(f"  Cross-word carry correlations:")
    for w1 in range(4):
        for w2 in range(w1+1, min(w1+3, 8)):
            c1 = np.array([hw(carry_word(IV[w1], int(states[i, w1]))) for i in range(N)])
            c2 = np.array([hw(carry_word(IV[w2], int(states[i, w2]))) for i in range(N)])
            corr = np.corrcoef(c1, c2)[0, 1]
            z = corr * math.sqrt(N)
            marker = "***" if abs(z) > 3 else ""
            if abs(z) > 2:
                print(f"    carry(IV[{w1}],s[{w1}]) vs carry(IV[{w2}],s[{w2}]): "
                      f"corr={corr:+.6f} Z={z:+.1f} {marker}")

    # ★-product: (IV[w1] & state[w1]) has relation to (IV[w2] & state[w2])?
    print(f"\n  Cross-word ★-AND correlations:")
    for w1 in range(4):
        for w2 in range(w1+1, min(w1+3, 8)):
            a1 = np.array([hw(IV[w1] & int(states[i, w1])) for i in range(N)])
            a2 = np.array([hw(IV[w2] & int(states[i, w2])) for i in range(N)])
            corr = np.corrcoef(a1, a2)[0, 1]
            z = corr * math.sqrt(N)
            marker = "***" if abs(z) > 3 else ""
            if abs(z) > 2:
                print(f"    IV[{w1}]&s[{w1}] vs IV[{w2}]&s[{w2}]: "
                      f"corr={corr:+.6f} Z={z:+.1f} {marker}")

    # NATIVE TEST: Does the ★-total (XOR of all AND components) have structure?
    print(f"\n  ★-total: ⊕ of all (IV[w] & state[w]):")
    star_totals = np.zeros(N, dtype=int)
    for i in range(N):
        t = 0
        for w in range(8):
            t ^= IV[w] & int(states[i, w])
        star_totals[i] = t

    star_hw = np.array([hw(int(x)) for x in star_totals])
    print(f"    E[HW]: {star_hw.mean():.4f} (random=16.0)")
    z = (star_hw.mean() - 16.0) / (star_hw.std() / math.sqrt(N))
    print(f"    Z = {z:+.2f}")
    if abs(z) > 3:
        print(f"    *** DEVIATION IN ★-TOTAL! ***")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 119: NONLINEAR HASH DEPENDENCIES")
    print("Standard polynomials → ★-native operations")
    print("=" * 60)

    test_pairwise_nonlinear(15000)
    test_higher_order_boolean(20000)
    test_star_native_deps(10000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
