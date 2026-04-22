"""BLAKE2s round-by-round OTOC for cross-architecture comparison.

BLAKE2s structure:
- 16 × 32-bit state (512 bits total)
- 10 rounds of G-function mixing
- 8 G-calls per round (4 columns + 4 diagonals)
- ARX operations (Add, Rotate, XOR)

G(v, a, b, c, d, m1, m2):
  v[a] = v[a] + v[b] + m1
  v[d] = ROTR32(v[d] ^ v[a], 16)
  v[c] = v[c] + v[d]
  v[b] = ROTR32(v[b] ^ v[c], 12)
  v[a] = v[a] + v[b] + m2
  v[d] = ROTR32(v[d] ^ v[a],  8)
  v[c] = v[c] + v[d]
  v[b] = ROTR32(v[b] ^ v[c],  7)

Measures ||C(r)||_F² for r ∈ {1..10} where r is partial rounds applied.
"""
import json, os, time
import numpy as np


OUT = '/home/user/SHA-256/research/min_entropy/otoc_blake2s_rounds_results.json'


# BLAKE2s IV (first 32 bits of fractional parts of sqrt(2..19))
BLAKE2S_IV = np.array([
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19
], dtype=np.uint32)

# BLAKE2 sigma schedule (10 rows for 10 rounds)
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


def rotr32(x, n):
    n = np.uint32(n & 31)
    return ((x >> n) | (x << (np.uint32(32) - n))).astype(np.uint32)


def G(v, a, b, c, d, x, y):
    """BLAKE2s G function, in-place on v (N x 16)."""
    v[:, a] = (v[:, a] + v[:, b] + x) & 0xFFFFFFFF
    v[:, d] = rotr32(v[:, d] ^ v[:, a], 16)
    v[:, c] = (v[:, c] + v[:, d]) & 0xFFFFFFFF
    v[:, b] = rotr32(v[:, b] ^ v[:, c], 12)
    v[:, a] = (v[:, a] + v[:, b] + y) & 0xFFFFFFFF
    v[:, d] = rotr32(v[:, d] ^ v[:, a], 8)
    v[:, c] = (v[:, c] + v[:, d]) & 0xFFFFFFFF
    v[:, b] = rotr32(v[:, b] ^ v[:, c], 7)


def blake2s_compress_partial(messages_bytes, num_rounds):
    """Apply num_rounds of BLAKE2s compression on 64-byte messages.

    Returns (N, 8) state = final h values (first 8 state words after feed-forward)
    """
    N = len(messages_bytes)
    # Parse messages as 16 uint32 LE
    M_arr = np.zeros((N, 16), dtype=np.uint32)
    for i in range(N):
        m = messages_bytes[i]
        for w in range(16):
            M_arr[i, w] = int.from_bytes(m[4*w:4*(w+1)], 'little')

    # Initialize h = IV
    h = np.broadcast_to(BLAKE2S_IV, (N, 8)).copy()

    # Parameter block XOR (BLAKE2s-256 with no key)
    # digest_length=32, key_length=0, fanout=1, depth=1
    # XOR into h[0]: 0x01010020
    h[:, 0] ^= np.uint32(0x01010020)

    # Initialize v (local work vector, 16 words)
    v = np.zeros((N, 16), dtype=np.uint32)
    v[:, 0:8] = h
    v[:, 8:16] = BLAKE2S_IV
    # XOR t (counter) and f (finalization flag)
    v[:, 12] ^= np.uint32(64)  # counter low: msg length
    v[:, 14] ^= np.uint32(0xFFFFFFFF)  # last block

    # Run num_rounds
    for r in range(num_rounds):
        s = SIGMA[r % 10]
        # Column G's
        G(v, 0, 4,  8, 12, M_arr[:, s[0]], M_arr[:, s[1]])
        G(v, 1, 5,  9, 13, M_arr[:, s[2]], M_arr[:, s[3]])
        G(v, 2, 6, 10, 14, M_arr[:, s[4]], M_arr[:, s[5]])
        G(v, 3, 7, 11, 15, M_arr[:, s[6]], M_arr[:, s[7]])
        # Diagonal G's
        G(v, 0, 5, 10, 15, M_arr[:, s[8]],  M_arr[:, s[9]])
        G(v, 1, 6, 11, 12, M_arr[:, s[10]], M_arr[:, s[11]])
        G(v, 2, 7,  8, 13, M_arr[:, s[12]], M_arr[:, s[13]])
        G(v, 3, 4,  9, 14, M_arr[:, s[14]], M_arr[:, s[15]])

    # Feed-forward
    out = h ^ v[:, 0:8] ^ v[:, 8:16]
    return out


def state_to_bits256(state):
    """Pack (N, 8) uint32 → (N, 256) bits (little-endian per word for BLAKE2)."""
    N = state.shape[0]
    # BLAKE2 output: little-endian bytes per word
    bytes_le = state.view('<u1').reshape(N, 8, 4).reshape(N, 32)
    bits = np.unpackbits(bytes_le, axis=1, bitorder='big')[:, :256]
    return bits


def measure_blake2s_otoc(r, N=200, seed=42):
    """Compute OTOC matrix for BLAKE2s at r rounds."""
    rng = np.random.default_rng(seed)
    msg_bytes = 64

    base_msgs_arr = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)
    base_msgs = [bytes(base_msgs_arr[i]) for i in range(N)]

    state_base = blake2s_compress_partial(base_msgs, r)
    bits_base = state_to_bits256(state_base)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 256), dtype=np.float64)
    for i in range(msg_bits):
        byte_idx = i // 8; bit_idx = 7 - (i % 8)
        flip_msgs_arr = base_msgs_arr.copy()
        flip_msgs_arr[:, byte_idx] ^= np.uint8(1 << bit_idx)
        flip_msgs = [bytes(flip_msgs_arr[j]) for j in range(N)]
        state_flip = blake2s_compress_partial(flip_msgs, r)
        bits_flip = state_to_bits256(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def verify_blake2s():
    """Sanity check: full 10-round BLAKE2s matches hashlib.blake2s."""
    import hashlib
    test_msgs = [b'\x00' * 64, b'x' * 64]
    msgs = test_msgs
    state = blake2s_compress_partial(msgs, 10)
    for i, m in enumerate(test_msgs):
        # Our output: state[i] little-endian → first 8*4=32 bytes of BLAKE2s-256
        got = state[i].tobytes()  # LE uint32
        expected = hashlib.blake2s(m).digest()
        ok = got == expected
        print(f"  msg={m[:10]!r}...: match={ok}")
        if not ok:
            print(f"    expected: {expected.hex()}")
            print(f"    got:      {got.hex()}")
    return True


def main():
    t0 = time.time()
    print("# BLAKE2s OTOC round-by-round")

    print("\n## Sanity check against hashlib.blake2s:")
    verify_blake2s()

    rounds_to_test = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    N = 200
    F_inf = 512 * 256 * 0.25 / N

    print(f"\n  N={N} messages, msg=512 bits, output=256 bits")
    print(f"\n{'r':>3}  {'||C||_F²':>10}  {'mean|C|':>10}  {'time':>6}")
    results = {}
    for r in rounds_to_test:
        ts = time.time()
        C = measure_blake2s_otoc(r, N=N)
        F_sq = float((C ** 2).sum())
        mean_abs = float(np.mean(np.abs(C)))
        elapsed = time.time() - ts
        results[r] = {'frobenius_sq': F_sq, 'mean_abs': mean_abs, 'time': elapsed}
        print(f"{r:>3}  {F_sq:>10.2f}  {mean_abs:>10.4f}  {elapsed:>5.1f}s")

    # Find scramble round
    scrambled_round = None
    for r in rounds_to_test:
        if abs(results[r]['frobenius_sq'] - F_inf) / F_inf < 0.05:
            scrambled_round = r; break

    print(f"\n## BLAKE2s scrambling summary:")
    print(f"  Total rounds: 10")
    print(f"  Full scramble at r = {scrambled_round}")
    if scrambled_round:
        print(f"  Relative: {scrambled_round/10*100:.0f}% of rounds")

    # Cross-architecture comparison
    print(f"\n## CROSS-ARCHITECTURE COMPARISON:")
    print(f"  {'Hash':>10}  {'Total r':>8}  {'Scramble r':>12}  {'% of rounds':>12}")
    print(f"  {'SHA-256':>10}  {64:>8}  {24:>12}  {37.0:>11.0f}%")
    print(f"  {'SHA-3':>10}  {24:>8}  {4:>12}  {17.0:>11.0f}%")
    if scrambled_round:
        print(f"  {'BLAKE2s':>10}  {10:>8}  {scrambled_round:>12}  {scrambled_round/10*100:>11.0f}%")

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
