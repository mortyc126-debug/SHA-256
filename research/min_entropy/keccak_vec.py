"""Keccak-f[1600] vectorized for N inputs, supports partial rounds.

Implements SHA-3-256 with round-level state extraction for IT-21-style
Ω_3 conservation probe on internal state.

State shape: (N, 5, 5) of uint64 lanes.
Full SHA-3-256 = 24 Keccak-f rounds after absorb.
"""
import numpy as np

RC = np.array([
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
], dtype=np.uint64)

# Rotation offsets: ROT[x][y] = rotation for lane (x,y), per FIPS 202 Appendix A
ROT = np.array([
    [ 0, 36,  3, 41, 18],   # x=0, y=0..4
    [ 1, 44, 10, 45,  2],   # x=1
    [62,  6, 43, 15, 61],   # x=2
    [28, 55, 25, 21, 56],   # x=3
    [27, 20, 39,  8, 14],   # x=4
], dtype=np.uint64)


def rotl64(x, n):
    n = int(n) & 63
    if n == 0: return x
    return ((x << np.uint64(n)) | (x >> np.uint64(64 - n))) & np.uint64(0xFFFFFFFFFFFFFFFF)


def keccak_f(state, num_rounds=24):
    """Apply num_rounds of Keccak-f[1600] to state (N, 5, 5) uint64. Returns new state."""
    s = state.copy()
    for r in range(num_rounds):
        # θ step
        C = s[:, 0] ^ s[:, 1] ^ s[:, 2] ^ s[:, 3] ^ s[:, 4]  # (N, 5) columns
        D = np.empty_like(C)
        for x in range(5):
            D[:, x] = C[:, (x - 1) % 5] ^ rotl64(C[:, (x + 1) % 5], 1)
        for y in range(5):
            s[:, y] ^= D

        # ρ + π steps combined
        B = np.zeros_like(s)
        for x in range(5):
            for y in range(5):
                # π permutation: B[y][2x+3y mod 5] = rotl(A[x][y], r[x][y])
                new_x = y
                new_y = (2 * x + 3 * y) % 5
                B[:, new_y, new_x] = rotl64(s[:, y, x], ROT[x, y])
        s = B

        # χ step
        T = s.copy()
        for x in range(5):
            for y in range(5):
                s[:, y, x] = T[:, y, x] ^ ((~T[:, y, (x + 1) % 5]) & T[:, y, (x + 2) % 5])

        # ι step
        s[:, 0, 0] ^= RC[r]
    return s


def absorb_sha3_256(messages):
    """Absorb 64-byte messages into Keccak state with SHA-3 padding.

    SHA-3-256: rate=1088 bits (136 bytes), capacity=512 bits.
    Pad: append 0x06 at position len, 0x80 at position 135, zeros between.
    """
    N = len(messages)
    padded = np.zeros((N, 136), dtype=np.uint8)
    for i, m in enumerate(messages):
        L = len(m)
        padded[i, :L] = np.frombuffer(m, dtype=np.uint8)
        padded[i, L] = 0x06
        padded[i, 135] = 0x80

    # View as 17 lanes of uint64 (little-endian)
    lanes = padded.view(dtype='<u8').reshape(N, 17)

    # Place into state[x][y] where lane index = x + 5*y, for x+5y < 17
    state = np.zeros((N, 5, 5), dtype=np.uint64)
    for idx in range(17):
        x = idx % 5
        y = idx // 5
        state[:, y, x] = lanes[:, idx]
    return state


def sha3_256_partial(messages, num_rounds=24):
    """Compute state after absorbing message and applying num_rounds of Keccak-f.

    Returns: state (N, 5, 5) uint64. Output bits = first 256 bits = state[0][0..3] lanes.
    """
    state = absorb_sha3_256(messages)
    return keccak_f(state, num_rounds)


def extract_output_bits(state, n_bits=256):
    """Extract first n_bits of SHA-3 output from state as (N, n_bits) uint8."""
    N = state.shape[0]
    # Output order: lane (x=0,y=0), (x=1,y=0), (x=2,y=0), (x=3,y=0), ... little-endian bytes
    n_lanes = (n_bits + 63) // 64
    lanes_out = np.zeros((N, n_lanes), dtype=np.uint64)
    for idx in range(n_lanes):
        x = idx % 5
        y = idx // 5
        lanes_out[:, idx] = state[:, y, x]
    # Convert to bytes then bits (big-endian per Keccak convention)
    out_bytes = lanes_out.view(dtype='<u1').reshape(N, n_lanes * 8)[:, :n_bits // 8]
    bits = np.unpackbits(out_bytes, axis=1, bitorder='big')[:, :n_bits]
    return bits


def test_correctness():
    import hashlib
    for msg in [b'', b'abc', b'x' * 64, b'The quick brown fox jumps over the lazy dog']:
        expected = hashlib.sha3_256(msg).digest()
        state = sha3_256_partial([msg], 24)
        bits = extract_output_bits(state, 256)
        # bits → bytes
        got = np.packbits(bits[0], bitorder='big').tobytes()[:32]
        ok = got == expected
        print(f"  msg={msg[:20]!r:25s} match={ok}")
        if not ok:
            print(f"    expected {expected.hex()}")
            print(f"    got      {got.hex()}")
            return False
    return True


if __name__ == '__main__':
    print("# Keccak-f[1600] correctness test:")
    ok = test_correctness()
    print(f"\n# Overall: {'PASS' if ok else 'FAIL'}")
