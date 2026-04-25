"""
Session 60: Multi-block collision differential structure.

WANG'S APPROACH (2005, MD5 → 2017 SHA-1 collision):
  Single-block collisions are HARD because the entire 512-bit message must
  satisfy collision constraint at end.

  Multi-block: split message into 2+ blocks. After block 1, internal state
  has some difference; block 2 compensates this difference.

  Key insight: choose specific message DIFFERENTIAL patterns that give
  predictable internal state differentials, then design block 2 to cancel.

For SHA-256: NO published full-round collision via multi-block. Best
academic results are reduced-round (~33-46 rounds) under various models.

This Session: FRAME the multi-block setup formally.

Setup:
  M_1 ⊕ M_1' = Δ_M1 (message difference, hand-chosen)
  After block 1: internal state diff = Δ_S1 (computed from Δ_M1 + propagation)
  M_2 ⊕ M_2' = Δ_M2 (must cancel Δ_S1 + propagate)
  After block 2: internal state diff = 0 (collision)

Constraints:
  - Δ_M1, Δ_M2 must be valid 512-bit differences
  - Internal state after block 2 must equal between (M_1, M_2) and (M_1', M_2')

For full SHA-256: this is open. We can SIMULATE on REDUCED-ROUND SHA.
"""
import hashlib
import numpy as np


def reduced_sha256(IV, message_blocks, rounds_per_block=64):
    """Simplified SHA-256 with arbitrary round count per block.
    For rounds=64 it's standard SHA-256 (with proper schedule).
    For rounds<64, truncated.

    For demonstration only — uses standard schedule but stops early.
    """
    K = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
        0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
        0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ]

    def rotr(x, r):
        return ((x >> r) | (x << (32 - r))) & 0xFFFFFFFF

    state = list(IV)
    for block in message_blocks:
        # Build W[0..63] from block (16 32-bit words)
        W = list(block)
        for i in range(16, 64):
            s0 = rotr(W[i - 15], 7) ^ rotr(W[i - 15], 18) ^ (W[i - 15] >> 3)
            s1 = rotr(W[i - 2], 17) ^ rotr(W[i - 2], 19) ^ (W[i - 2] >> 10)
            W.append((W[i - 16] + s0 + W[i - 7] + s1) & 0xFFFFFFFF)

        a, b, c, d, e, f, g, h = state
        for t in range(rounds_per_block):
            S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
            ch = (e & f) ^ ((~e) & g & 0xFFFFFFFF)
            T1 = (h + S1 + ch + K[t] + W[t]) & 0xFFFFFFFF
            S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
            mj = (a & b) ^ (a & c) ^ (b & c)
            T2 = (S0 + mj) & 0xFFFFFFFF
            h, g, f = g, f, e
            e = (d + T1) & 0xFFFFFFFF
            d, c, b = c, b, a
            a = (T1 + T2) & 0xFFFFFFFF
        # Add to state
        state = [(state[i] + v) & 0xFFFFFFFF for i, v in enumerate([a, b, c, d, e, f, g, h])]
    return state


def hex_state(s):
    return ''.join(f"{x:08x}" for x in s)


def main():
    print("=== Session 60: Multi-block collision framework ===\n")

    IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

    # Test 1: standard SHA on a 1-block message (verify our implementation)
    msg = [0x80] + [0]*55 + [0, 0, 0, 0, 0, 0, 0, 0]  # padding for empty
    block = []
    for i in range(0, 64, 4):
        word = (msg[i] << 24) | (msg[i+1] << 16) | (msg[i+2] << 8) | msg[i+3]
        block.append(word)
    digest = reduced_sha256(IV, [block], rounds_per_block=64)
    expected = hashlib.sha256(b"").hexdigest()
    actual = hex_state(digest)
    print(f"  Empty message digest:")
    print(f"    Our:      {actual}")
    print(f"    Expected: {expected}")
    print(f"    Match: {actual == expected}")

    # Test 2: try to find 2-block collision in REDUCED-ROUND SHA (e.g., 16 rounds per block)
    print(f"\n  Multi-block collision search (reduced rounds):")
    for rounds in [4, 8, 16, 24]:
        print(f"\n    Trying {rounds} rounds/block, random 2-block search...")
        rng = np.random.default_rng(0)
        digests_seen = {}
        collision_found = False
        for trial in range(100000):
            blocks = []
            for _ in range(2):
                blocks.append([int(rng.integers(0, 2**32)) for _ in range(16)])
            d = tuple(reduced_sha256(IV, blocks, rounds_per_block=rounds))
            if d in digests_seen:
                if digests_seen[d] != blocks:
                    collision_found = True
                    print(f"      ✓ COLLISION found at trial {trial}!")
                    print(f"        Blocks A: {blocks[0][:4]}...")
                    print(f"        Blocks B: {digests_seen[d][0][:4]}...")
                    break
            else:
                digests_seen[d] = blocks
        if not collision_found:
            print(f"      ✗ No collision in 10^5 random trials at {rounds} rounds/block.")
            print(f"        Birthday-bound expectation: 2^(256/2) = 2^128 ≫ 10^5.")
            print(f"        Random search is FUTILE without differential structure.")

    print(f"""

=== Theorem 60.1 (multi-block collision search infeasibility) ===

For full SHA-256 (64 rounds × 2 blocks = 128 round applications):
  - Random search: birthday bound 2^128. Beyond reach.
  - Wang-style differential: requires hand-crafted message differentials
    for which the internal state difference can be cancelled in next block.
  - For SHA-256, no published full-round multi-block collision.

For reduced-round SHA-256 (e.g., 38-46 rounds): published attacks exist
under specific cost models, using rebound + multi-block + differential
construction.

THE PROBLEM:
  Wang's MD5 attack found message differentials α with high differential
  probability through 64 rounds of MD5. SHA-256's stronger structure means:
    - No high-probability differentials through 64 rounds.
    - Best known differentials drop to <2^-128 around round 50.
  So multi-block extension cannot help: the differential is gone.

FUTURE PATH:
  Finding a SHA-256 multi-block collision would require either:
    (a) New differential analysis revealing high-prob trail through 64 rounds.
    (b) Quantum algorithm (Grover-like for collisions: 2^128 → 2^85, still bad).
    (c) Side channel / fault injection (out of scope for cryptanalysis).

  Currently NO known algorithm reduces 2^128 collision search below brute force.
""")


if __name__ == "__main__":
    main()
