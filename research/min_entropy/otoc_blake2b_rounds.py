"""BLAKE2b round-by-round OTOC (64-bit variant).

BLAKE2b structure:
- 16 × 64-bit state (1024 bits total)
- 12 rounds of G-function mixing
- ARX on 64-bit words with different rotation constants (32,24,16,63)
- Block size 128 bytes (1024 bits)

Completes ARX family comparison alongside BLAKE2s (32-bit, 10 rounds).

G(v, a, b, c, d, m1, m2):
  v[a] = v[a] + v[b] + m1
  v[d] = ROTR64(v[d] ^ v[a], 32)
  v[c] = v[c] + v[d]
  v[b] = ROTR64(v[b] ^ v[c], 24)
  v[a] = v[a] + v[b] + m2
  v[d] = ROTR64(v[d] ^ v[a], 16)
  v[c] = v[c] + v[d]
  v[b] = ROTR64(v[b] ^ v[c], 63)
"""
import json, os, time
import numpy as np
import hashlib


OUT = '/home/user/SHA-256/research/min_entropy/otoc_blake2b_rounds_results.json'


BLAKE2B_IV = np.array([
    0x6A09E667F3BCC908, 0xBB67AE8584CAA73B, 0x3C6EF372FE94F82B, 0xA54FF53A5F1D36F1,
    0x510E527FADE682D1, 0x9B05688C2B3E6C1F, 0x1F83D9ABFB41BD6B, 0x5BE0CD19137E2179
], dtype=np.uint64)

# Same SIGMA permutations as BLAKE2s (10 rows; BLAKE2b uses same 10 but cycles through 12 rounds)
SIGMA = np.array([
    [ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15],
    [14, 10,  4,  8,  9, 15, 13,  6,  1, 12,  0,  2, 11,  7,  5,  3],
    [11,  8, 12,  0,  5,  2, 15, 13, 10, 14,  3,  6,  7,  1,  9,  4],
    [ 7,  9,  3,  1, 13, 12, 11, 14,  2,  6,  5, 10,  4,  0, 15,  8],
    [ 9,  0,  5,  7,  2,  4, 10, 15, 14,  1, 11, 12,  6,  8,  3, 13],
    [ 2, 12,  6, 10,  0, 11,  8,  3,  4, 13,  7,  5, 15, 14,  1,  9],
    [12,  5,  1, 15, 14, 13,  4, 10,  0,  7,  6,  3,  9,  2,  8, 11],
    [13, 11,  7, 14, 12,  1,  3,  9,  5,  0, 15,  4,  8,  6,  2, 10],
    [ 6, 15, 14,  9, 11,  3,  0,  8, 12,  2, 13,  7,  1,  4, 10,  5],
    [10,  2,  8,  4,  7,  6,  1,  5, 15, 11,  9, 14,  3, 12, 13,  0],
], dtype=np.int32)


def rotr64(x, n):
    n = np.uint64(n & 63)
    return ((x >> n) | (x << (np.uint64(64) - n))).astype(np.uint64)


def G64(v, a, b, c, d, x, y):
    v[:, a] = (v[:, a] + v[:, b] + x) & 0xFFFFFFFFFFFFFFFF
    v[:, d] = rotr64(v[:, d] ^ v[:, a], 32)
    v[:, c] = (v[:, c] + v[:, d]) & 0xFFFFFFFFFFFFFFFF
    v[:, b] = rotr64(v[:, b] ^ v[:, c], 24)
    v[:, a] = (v[:, a] + v[:, b] + y) & 0xFFFFFFFFFFFFFFFF
    v[:, d] = rotr64(v[:, d] ^ v[:, a], 16)
    v[:, c] = (v[:, c] + v[:, d]) & 0xFFFFFFFFFFFFFFFF
    v[:, b] = rotr64(v[:, b] ^ v[:, c], 63)


def blake2b_compress_partial(messages_bytes, num_rounds, output_bits=512):
    """Apply num_rounds of BLAKE2b compression on 128-byte messages."""
    N = len(messages_bytes)
    M_arr = np.zeros((N, 16), dtype=np.uint64)
    for i in range(N):
        m = messages_bytes[i]
        for w in range(16):
            M_arr[i, w] = int.from_bytes(m[8*w:8*(w+1)], 'little')

    h = np.broadcast_to(BLAKE2B_IV, (N, 8)).copy()
    # Parameter block XOR (BLAKE2b-512 with no key): 0x01010040
    h[:, 0] ^= np.uint64(0x0000000001010040)

    v = np.zeros((N, 16), dtype=np.uint64)
    v[:, 0:8] = h
    v[:, 8:16] = BLAKE2B_IV
    v[:, 12] ^= np.uint64(128)  # counter = msg length
    v[:, 14] ^= np.uint64(0xFFFFFFFFFFFFFFFF)  # last block

    for r in range(num_rounds):
        s = SIGMA[r % 10]
        G64(v, 0, 4,  8, 12, M_arr[:, s[0]], M_arr[:, s[1]])
        G64(v, 1, 5,  9, 13, M_arr[:, s[2]], M_arr[:, s[3]])
        G64(v, 2, 6, 10, 14, M_arr[:, s[4]], M_arr[:, s[5]])
        G64(v, 3, 7, 11, 15, M_arr[:, s[6]], M_arr[:, s[7]])
        G64(v, 0, 5, 10, 15, M_arr[:, s[8]],  M_arr[:, s[9]])
        G64(v, 1, 6, 11, 12, M_arr[:, s[10]], M_arr[:, s[11]])
        G64(v, 2, 7,  8, 13, M_arr[:, s[12]], M_arr[:, s[13]])
        G64(v, 3, 4,  9, 14, M_arr[:, s[14]], M_arr[:, s[15]])

    out = h ^ v[:, 0:8] ^ v[:, 8:16]
    return out[:, :output_bits // 64]


def state_to_bits(state):
    """Pack (N, 8) uint64 → (N, 512) bits, little-endian per word."""
    N = state.shape[0]
    bytes_le = state.view('<u1').reshape(N, 8, 8).reshape(N, 64)
    bits = np.unpackbits(bytes_le, axis=1, bitorder='big')[:, :512]
    return bits


def measure_blake2b_otoc(r, N=200, seed=42, msg_bytes=128):
    rng = np.random.default_rng(seed)
    base_msgs_arr = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)
    base_msgs = [bytes(base_msgs_arr[i]) for i in range(N)]

    state_base = blake2b_compress_partial(base_msgs, r)
    bits_base = state_to_bits(state_base)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 512), dtype=np.float64)
    for i in range(msg_bits):
        byte_idx = i // 8; bit_idx = 7 - (i % 8)
        flip_msgs_arr = base_msgs_arr.copy()
        flip_msgs_arr[:, byte_idx] ^= np.uint8(1 << bit_idx)
        flip_msgs = [bytes(flip_msgs_arr[j]) for j in range(N)]
        state_flip = blake2b_compress_partial(flip_msgs, r)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def verify_blake2b():
    """Check full 12-round against hashlib.blake2b."""
    test_msgs = [b'\x00' * 128, b'x' * 128]
    state = blake2b_compress_partial(test_msgs, 12)
    for i, m in enumerate(test_msgs):
        got = state[i].tobytes()  # LE uint64 → 64 bytes
        expected = hashlib.blake2b(m).digest()
        ok = got == expected
        print(f"  msg={m[:10]!r}...: match={ok}")
        if not ok:
            print(f"    expected: {expected.hex()}")
            print(f"    got:      {got.hex()}")
    return True


def main():
    t0 = time.time()
    print("# BLAKE2b OTOC round-by-round (64-bit variant)")

    print("\n## Sanity check vs hashlib.blake2b:")
    verify_blake2b()

    rounds_to_test = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    N = 200
    msg_bits = 128 * 8  # 1024
    out_bits = 512
    F_inf = msg_bits * out_bits * 0.25 / N

    print(f"\n  N={N}, msg={msg_bits} bits, output={out_bits} bits")
    print(f"  Theoretical RO limit: {F_inf:.2f}")
    print(f"\n{'r':>3}  {'||C||_F²':>10}  {'mean|C|':>10}  {'time':>6}")
    results = {}
    for r in rounds_to_test:
        ts = time.time()
        C = measure_blake2b_otoc(r, N=N)
        F_sq = float((C ** 2).sum())
        mean_abs = float(np.mean(np.abs(C)))
        results[r] = {'frobenius_sq': F_sq, 'mean_abs': mean_abs, 'time': time.time()-ts}
        print(f"{r:>3}  {F_sq:>10.2f}  {mean_abs:>10.4f}  {time.time()-ts:>5.1f}s")

    scrambled_round = None
    for r in rounds_to_test:
        if abs(results[r]['frobenius_sq'] - F_inf) / F_inf < 0.05:
            scrambled_round = r; break

    print(f"\n## BLAKE2b scrambling summary:")
    print(f"  Total rounds: 12, scramble at r = {scrambled_round}")
    if scrambled_round: print(f"  Relative: {scrambled_round/12*100:.0f}% of rounds")

    # Cross-architecture complete table
    print(f"\n## COMPLETE ARX + SHA + Keccak table:")
    print(f"  {'Hash':>10}  {'Total r':>8}  {'Scramble r':>12}  {'% of rounds':>12}")
    print(f"  {'SHA-256':>10}  {64:>8}  {24:>12}  {37:>11}%")
    print(f"  {'SHA-3-256':>10}  {24:>8}  {4:>12}  {17:>11}%")
    print(f"  {'BLAKE2s':>10}  {10:>8}  {2:>12}  {20:>11}%")
    if scrambled_round:
        print(f"  {'BLAKE2b':>10}  {12:>8}  {scrambled_round:>12}  {scrambled_round/12*100:>11.0f}%")

    out = {
        'N': N, 'rounds': rounds_to_test,
        'results': {str(r): v for r, v in results.items()},
        'theoretical_limit': F_inf,
        'scrambled_round': scrambled_round,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
