#!/usr/bin/env python3
"""
EXP 103: Carry Dimension Attack — Can carry_dim=174 beat birthday?

From exp102: carry effective dimension ≈ 174 (vs Hamming 256).
Carry-close pairs: E[d_H] = 122 (vs baseline 128).

PRECISE QUESTION:
1. Generate N hashes, find carry-close PAIRS (birthday on carry space)
2. Among carry-close pairs: what is P(d_H = 0)?
3. If P(d_H=0 | carry_close) > 2^{-256}: fewer total hashes needed

CALCULATION:
  Standard: N² × 2^{-256} ≥ 1 → N ≥ 2^{128}
  ★-approach: N² × 2^{-174} (carry-birthday) × P(dH=0|carry_close) ≥ 1

  If P(dH=0|carry_close) = 2^{-82}: total N² × 2^{-174} × 2^{-82} = N² × 2^{-256}
  → SAME as standard. Conservation again.

  If P(dH=0|carry_close) > 2^{-82}: BETTER. How much?

MEASURE P(dH=0|carry_close) precisely.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def hash_and_carry(W16):
    """Compute hash and carry structure."""
    H = sha256_compress(W16)
    states = sha256_rounds(W16, 64)
    # Carry structure: carry(IV, state) per word
    carries = []
    for w in range(8):
        c = ((IV[w] + states[64][w]) & MASK) ^ (IV[w] ^ states[64][w])
        carries.append(c)
    return H, carries

def carry_distance(c1, c2):
    """Carry distance between two carry structures."""
    return sum(hw(c1[w] ^ c2[w]) for w in range(8))

def hamming_distance(h1, h2):
    """Hamming distance between two hashes."""
    return sum(hw(h1[w] ^ h2[w]) for w in range(8))

def test_conditional_probability(N=30000):
    """Measure P(d_H ≤ t | d_carry ≤ c) for various t, c."""
    print(f"\n--- P(d_H | d_carry) (N={N}) ---")

    hashes = []; carries_list = []
    for _ in range(N):
        W16 = random_w16()
        H, C = hash_and_carry(W16)
        hashes.append(H)
        carries_list.append(C)

    # Sample pairs
    n_pairs = min(N * 50, 500000)
    pair_data = []

    for _ in range(n_pairs):
        i = random.randint(0, N-1); j = random.randint(0, N-1)
        if i == j: continue
        dh = hamming_distance(hashes[i], hashes[j])
        dc = carry_distance(carries_list[i], carries_list[j])
        pair_data.append((dh, dc))

    dh_arr = np.array([p[0] for p in pair_data])
    dc_arr = np.array([p[1] for p in pair_data])

    # Conditional distributions
    print(f"Total pairs: {len(pair_data)}")
    print(f"E[d_H]: {dh_arr.mean():.2f}")
    print(f"E[d_carry]: {dc_arr.mean():.2f}")

    print(f"\n{'Carry threshold':>15} | {'N pairs':>8} | {'E[d_H]':>7} | {'std(d_H)':>8} | {'min d_H':>7}")
    print("-" * 55)

    for c_thresh in [50, 55, 60, 65, 70, 75, 80, 84]:
        mask = dc_arr <= c_thresh
        n = mask.sum()
        if n < 10:
            continue
        dh_sub = dh_arr[mask]
        print(f"d_carry ≤ {c_thresh:>3}     | {n:>8} | {dh_sub.mean():>7.2f} | {dh_sub.std():>8.2f} | {dh_sub.min():>7}")

    # KEY: effective Hamming dimension WITHIN carry-close pairs
    print(f"\nEffective Hamming dimension within carry-close groups:")
    for c_thresh in [60, 70, 80]:
        mask = dc_arr <= c_thresh
        dh_sub = dh_arr[mask]
        if len(dh_sub) < 100:
            continue
        mean = dh_sub.mean(); std = dh_sub.std()
        n_eff = 2 * (mean / std) ** 2 if std > 0 else 256

        # Birthday in this subspace
        birthday_sub = n_eff / 2
        birthday_carry = 174 / 2  # Cost to find carry-close pair

        total = max(birthday_carry, birthday_sub)

        print(f"  d_carry ≤ {c_thresh}: mean_dH={mean:.1f}, std={std:.2f}, "
              f"n_eff={n_eff:.0f}, birthday_sub≈2^{birthday_sub:.0f}")
        print(f"    → total cost: max(2^{birthday_carry:.0f}, 2^{birthday_sub:.0f}) = 2^{total:.0f}")

def test_two_phase_search(N=50000):
    """
    Two-phase collision search:
    Phase 1: Birthday on carry space → find carry-close pairs
    Phase 2: Among carry-close pairs → birthday on remaining Hamming

    Total cost = max(Phase 1, Phase 2)?
    Or = Phase 1 + Phase 2?
    """
    print(f"\n--- TWO-PHASE SEARCH (N={N}) ---")

    hashes = []; carries_list = []
    for _ in range(N):
        W16 = random_w16()
        H, C = hash_and_carry(W16)
        hashes.append(H)
        carries_list.append(C)

    # Phase 1: find carry-close pairs via bucketing
    # Bucket by carry structure (approximate: use first few carry bits)
    carry_buckets = {}
    for idx in range(N):
        # Simple bucket: first 4 bits of each carry word = 32-bit key
        key = tuple((carries_list[idx][w] >> 28) & 0xF for w in range(8))
        if key not in carry_buckets:
            carry_buckets[key] = []
        carry_buckets[key].append(idx)

    # Find pairs within same bucket
    carry_close_pairs = []
    for bucket in carry_buckets.values():
        for i in range(len(bucket)):
            for j in range(i+1, len(bucket)):
                idx_i = bucket[i]; idx_j = bucket[j]
                dc = carry_distance(carries_list[idx_i], carries_list[idx_j])
                dh = hamming_distance(hashes[idx_i], hashes[idx_j])
                carry_close_pairs.append((dh, dc))

    if not carry_close_pairs:
        print("No carry-close pairs found in buckets")
        return

    cc_dh = np.array([p[0] for p in carry_close_pairs])
    cc_dc = np.array([p[1] for p in carry_close_pairs])

    print(f"Carry-bucketed pairs: {len(carry_close_pairs)}")
    print(f"  E[d_carry]: {cc_dc.mean():.2f} (vs random {84:.0f})")
    print(f"  E[d_H]: {cc_dh.mean():.2f} (vs random {128:.0f})")
    print(f"  min(d_H): {cc_dh.min()}")

    # Phase 2: among carry-close pairs, find min d_H
    # Compare with random pairs of same count
    n_random = len(carry_close_pairs)
    random_dHs = []
    for _ in range(min(n_random, 100000)):
        i = random.randint(0, N-1); j = random.randint(0, N-1)
        if i == j: continue
        random_dHs.append(hamming_distance(hashes[i], hashes[j]))

    rd = np.array(random_dHs)

    print(f"\nComparison (same number of pairs):")
    print(f"  Carry-close: min d_H = {cc_dh.min()}, E = {cc_dh.mean():.1f}")
    print(f"  Random:      min d_H = {rd.min()}, E = {rd.mean():.1f}")

    if cc_dh.min() < rd.min():
        gain = rd.min() - cc_dh.min()
        print(f"  ★-approach WINS by {gain} bits!")
    else:
        print(f"  Random wins by {cc_dh.min() - rd.min()}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 103: CARRY DIMENSION ATTACK")
    print("=" * 60)

    test_conditional_probability(15000)
    test_two_phase_search(30000)

    print("\n" + "=" * 60)
    print("VERDICT: Does carry dimension < 256 → collision < 2^128?")
    print("=" * 60)

if __name__ == "__main__":
    main()
