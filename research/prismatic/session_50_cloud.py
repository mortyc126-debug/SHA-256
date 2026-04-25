"""
Session 50: Hamming distance distribution in SHA digest cloud.

WILD DIRECTION: hash N random messages, get N digests in F_2^256.
Compute pairwise Hamming distances of the digest cloud.
For ideal random function: distances should follow Binomial(256, 1/2).

Test:
1. Sample N digests.
2. Compute O(N²/2) pairwise distances.
3. Compare empirical histogram to Binomial(256, 1/2): mean 128, std 8.

Also test STRUCTURED inputs: e.g., consecutive integers as messages.
For ideal SHA: distances among hash(0), hash(1), ..., hash(N-1) should look like
random pairs. If they cluster or have anomalous distances, structure is detected.

This is a "clustering test" inspired by topological data analysis.
"""
import numpy as np
import hashlib
from collections import Counter


def sha256_digest(msg_int):
    """Return SHA-256 digest of a 32-byte integer message as bytes."""
    msg = msg_int.to_bytes(32, 'little')
    return hashlib.sha256(msg).digest()


def hamming_distance(a, b):
    """Hamming distance between two byte strings."""
    diff = bytes(x ^ y for x, y in zip(a, b))
    return sum(bin(b).count('1') for b in diff)


def main():
    print("=== Session 50: Hamming distance distribution in SHA-256 digest cloud ===\n")
    rng = np.random.default_rng(0)

    # Random messages
    NUM_DIGESTS = 500
    print(f"  Phase 1: Random messages ({NUM_DIGESTS} samples)")
    digests = []
    for _ in range(NUM_DIGESTS):
        msg = int(rng.integers(0, 2**63))
        digests.append(sha256_digest(msg))

    # Pairwise distances (sample for speed)
    print(f"  Computing pairwise Hamming distances...")
    distances = []
    for i in range(NUM_DIGESTS):
        for j in range(i + 1, NUM_DIGESTS):
            distances.append(hamming_distance(digests[i], digests[j]))
    distances = np.array(distances)

    print(f"\n  Pairwise Hamming distance statistics ({len(distances)} pairs):")
    print(f"    Mean: {distances.mean():.4f} (ideal Binomial(256, 0.5) = 128.0)")
    print(f"    Std: {distances.std():.4f} (ideal = √(256·0.25) = 8.0)")
    print(f"    Min/Max: {distances.min()}/{distances.max()}")

    # Compare distribution
    print(f"\n  Distance histogram (count in each bucket):")
    bins = list(range(96, 161, 4))
    cnt = Counter()
    for d in distances:
        b = (d // 4) * 4
        cnt[b] += 1
    expected_total = len(distances)
    for b in bins:
        c = cnt.get(b, 0)
        # Theoretical bin probability: P[d ∈ [b, b+4)] under Binomial(256, 0.5)
        theo = sum(comb_prob(256, d, 0.5) for d in range(b, b + 4))
        theo_count = theo * expected_total
        print(f"    d ∈ [{b}, {b+4}):  empirical = {c:>5},  theoretical = {theo_count:>7.1f}")

    # χ² test
    chi2 = 0
    nz = 0
    for b in bins:
        c = cnt.get(b, 0)
        theo = sum(comb_prob(256, d, 0.5) for d in range(b, b + 4))
        theo_count = theo * expected_total
        if theo_count > 0:
            chi2 += (c - theo_count) ** 2 / theo_count
            nz += 1
    print(f"\n  χ² statistic: {chi2:.2f} (df={nz-1}, ~ random expected if χ² ≈ {nz-1})")

    # Phase 2: Structured inputs (consecutive integers)
    print(f"\n  Phase 2: Consecutive integers (msg = 0, 1, 2, ..., {NUM_DIGESTS-1}):")
    seq_digests = [sha256_digest(i) for i in range(NUM_DIGESTS)]
    seq_distances = []
    for i in range(NUM_DIGESTS):
        for j in range(i + 1, NUM_DIGESTS):
            seq_distances.append(hamming_distance(seq_digests[i], seq_digests[j]))
    seq_distances = np.array(seq_distances)
    print(f"    Mean: {seq_distances.mean():.4f}, std: {seq_distances.std():.4f}")
    print(f"    (Should match random if SHA randomizes sequential inputs.)")

    # Test for closest pair (birthday-paradox-like)
    closest_pair_dist = seq_distances.min()
    print(f"    Closest pair distance: {closest_pair_dist}")
    print(f"    Expected min for {NUM_DIGESTS}*({NUM_DIGESTS}-1)/2 random pairs in F_2^256: ~{ideal_min_dist(NUM_DIGESTS):.1f}")


def comb_prob(n, k, p):
    """Binomial probability."""
    from math import comb
    return comb(n, k) * (p**k) * ((1-p)**(n-k))


def ideal_min_dist(N):
    """Approximate expected min Hamming distance for N random points in F_2^256."""
    # Heuristic: with N(N-1)/2 pairs, prob(min < d) ≈ 1 - exp(-N²/2 · P[X < d])
    # where X ~ Binomial(256, 0.5). The "expected min" is roughly where the prob crosses 1/2.
    # For N=500: 125000 pairs. We need P[X < d] ≈ 1/125000.
    # Tail of Binomial(256, 0.5): P[X ≤ k] ≈ exp(-(128-k)²/128) (Gaussian approx for k far from 128).
    # Solving exp(-(128-d)²/128) = 1/125000: (128-d)² ≈ 128 · ln(125000) ≈ 128 · 11.7 = 1500.
    # 128 - d ≈ √1500 ≈ 39. So d ≈ 89.
    # But for smaller N like 50, need different.
    import math
    target_prob = 1.0 / (N * (N - 1) / 2)
    val = math.sqrt(-128 * math.log(target_prob))
    return 128 - val


def main_2():
    print(f"\n\n=== Theorem 50.1 (digest cloud randomness) ===")
    print(f"""
If the SHA-256 digest cloud's pairwise Hamming distances follow Binomial(256, 0.5):
  → SHA-256 is statistically indistinguishable from a random oracle on this test.
If they deviate:
  → Some structural pattern exists in the digest distribution.

EXPECTED RESULT: SHA-256 (full 64 rounds) should pass this test.
Reduced-round SHA may fail — would be detectable as Hamming distribution skew.

This is a TOPOLOGICAL / GEOMETRIC test of pseudo-randomness.
""")


if __name__ == "__main__":
    main()
    main_2()
