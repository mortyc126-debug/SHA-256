"""
Session 47: Algorithmic randomness of SHA orbits via compression.

CRAZY DIRECTION: treat the orbit sequence (x, R(x), R²(x), ..., R^T(x)) as
a binary string and compute its gzip compression ratio.

For ideal random data: ratio ≈ 1.0 (incompressible).
For periodic data with period P: ratio ≈ 1/P (highly compressible after P).
For "structured" data: somewhere in between.

For SHA round (which has order ≫ 1000, Session 41/46): orbits don't repeat in
1000 rounds. So compression ratio should be close to 1.0 IF SHA is truly random.

Twist: even if R is "random" as a function, individual orbits might have
INTERNAL structure detectable by gzip (e.g., common substrings).

This empirically measures how "algorithmically random" SHA orbits are.
"""
import numpy as np
import gzip
from session_46_correct_round import correct_round, state_to_bits, bits_to_state


def orbit_to_bytes(start_state, T):
    """Generate orbit (state_0, state_1, ..., state_T) as a byte string."""
    out = bytearray()
    state = list(start_state)
    for _ in range(T + 1):
        for r in state:
            out.extend(int(r).to_bytes(4, 'little'))
        state = correct_round(state)
    return bytes(out)


def main():
    print("=== Session 47: Compression ratio of SHA orbits ===\n")
    rng = np.random.default_rng(0)

    print(f"  Approach: gzip the byte stream of T+1 successive states under R.")
    print(f"  Compare to random control (gzip of i.i.d. uniform bytes).\n")

    for T in [10, 100, 500, 1000, 5000]:
        ratios = []
        for trial in range(5):
            start = [int(rng.integers(0, 2**32)) for _ in range(8)]
            data = orbit_to_bytes(start, T)
            compressed = gzip.compress(data, compresslevel=9)
            ratio = len(compressed) / len(data)
            ratios.append(ratio)

        # Random control
        random_data = rng.integers(0, 256, size=len(data), dtype=np.uint8).tobytes()
        random_compressed = gzip.compress(random_data, compresslevel=9)
        random_ratio = len(random_compressed) / len(random_data)

        print(f"  T = {T:>4}, orbit length = {len(data):>7} bytes:")
        print(f"    SHA orbit gzip ratio: {np.mean(ratios):.4f} ± {np.std(ratios):.4f}")
        print(f"    Random control ratio: {random_ratio:.4f}")
        print(f"    Ratio (SHA/random): {np.mean(ratios)/random_ratio:.4f}")
        print()

    print("""

=== Theorem 47.1 (algorithmic randomness, empirical) ===

If SHA orbits give compression ratio ≈ 1.0 (similar to random):
  → SHA-256 round is "algorithmically random" — orbits indistinguishable from
    random sequences by general-purpose compression.
If ratio < 1.0 significantly:
  → SHA orbits have detectable internal structure.

This is an EMPIRICAL test of SHA's pseudo-randomness using off-the-shelf
compression as an oracle.
""")


if __name__ == "__main__":
    main()
