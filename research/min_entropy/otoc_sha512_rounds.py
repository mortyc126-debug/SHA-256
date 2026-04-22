"""SHA-512 round-by-round OTOC.

SHA-512 is SHA-2 family:
- 64-bit state (8 × 64-bit = 512 bits)
- 80 rounds (20% more than SHA-256's 64)
- Σ₀(a) = ROTR²⁸ ⊕ ROTR³⁴ ⊕ ROTR³⁹
- Σ₁(e) = ROTR¹⁴ ⊕ ROTR¹⁸ ⊕ ROTR⁴¹
- σ₀(x) = ROTR¹ ⊕ ROTR⁸ ⊕ SHR⁷
- σ₁(x) = ROTR¹⁹ ⊕ ROTR⁶¹ ⊕ SHR⁶

Purpose: intra-family comparison with SHA-256.
Expected: similar scaling (SHA-512 scrambles at ~37% of 80 = r=30).
Or different due to 64-bit carries behaving differently than 32-bit.
"""
import json, os, time, hashlib
import numpy as np


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sha512_rounds_results.json'


SHA512_IV = np.array([
    0x6A09E667F3BCC908, 0xBB67AE8584CAA73B, 0x3C6EF372FE94F82B, 0xA54FF53A5F1D36F1,
    0x510E527FADE682D1, 0x9B05688C2B3E6C1F, 0x1F83D9ABFB41BD6B, 0x5BE0CD19137E2179
], dtype=np.uint64)

SHA512_K = np.array([
    0x428A2F98D728AE22, 0x7137449123EF65CD, 0xB5C0FBCFEC4D3B2F, 0xE9B5DBA58189DBBC,
    0x3956C25BF348B538, 0x59F111F1B605D019, 0x923F82A4AF194F9B, 0xAB1C5ED5DA6D8118,
    0xD807AA98A3030242, 0x12835B0145706FBE, 0x243185BE4EE4B28C, 0x550C7DC3D5FFB4E2,
    0x72BE5D74F27B896F, 0x80DEB1FE3B1696B1, 0x9BDC06A725C71235, 0xC19BF174CF692694,
    0xE49B69C19EF14AD2, 0xEFBE4786384F25E3, 0x0FC19DC68B8CD5B5, 0x240CA1CC77AC9C65,
    0x2DE92C6F592B0275, 0x4A7484AA6EA6E483, 0x5CB0A9DCBD41FBD4, 0x76F988DA831153B5,
    0x983E5152EE66DFAB, 0xA831C66D2DB43210, 0xB00327C898FB213F, 0xBF597FC7BEEF0EE4,
    0xC6E00BF33DA88FC2, 0xD5A79147930AA725, 0x06CA6351E003826F, 0x142929670A0E6E70,
    0x27B70A8546D22FFC, 0x2E1B21385C26C926, 0x4D2C6DFC5AC42AED, 0x53380D139D95B3DF,
    0x650A73548BAF63DE, 0x766A0ABB3C77B2A8, 0x81C2C92E47EDAEE6, 0x92722C851482353B,
    0xA2BFE8A14CF10364, 0xA81A664BBC423001, 0xC24B8B70D0F89791, 0xC76C51A30654BE30,
    0xD192E819D6EF5218, 0xD69906245565A910, 0xF40E35855771202A, 0x106AA07032BBD1B8,
    0x19A4C116B8D2D0C8, 0x1E376C085141AB53, 0x2748774CDF8EEB99, 0x34B0BCB5E19B48A8,
    0x391C0CB3C5C95A63, 0x4ED8AA4AE3418ACB, 0x5B9CCA4F7763E373, 0x682E6FF3D6B2B8A3,
    0x748F82EE5DEFB2FC, 0x78A5636F43172F60, 0x84C87814A1F0AB72, 0x8CC702081A6439EC,
    0x90BEFFFA23631E28, 0xA4506CEBDE82BDE9, 0xBEF9A3F7B2C67915, 0xC67178F2E372532B,
    0xCA273ECEEA26619C, 0xD186B8C721C0C207, 0xEADA7DD6CDE0EB1E, 0xF57D4F7FEE6ED178,
    0x06F067AA72176FBA, 0x0A637DC5A2C898A6, 0x113F9804BEF90DAE, 0x1B710B35131C471B,
    0x28DB77F523047D84, 0x32CAAB7B40C72493, 0x3C9EBE0A15C9BEBC, 0x431D67C49C100D4C,
    0x4CC5D4BECB3E42B6, 0x597F299CFC657E2A, 0x5FCB6FAB3AD6FAEC, 0x6C44198C4A475817,
], dtype=np.uint64)


MASK64 = np.uint64(0xFFFFFFFFFFFFFFFF)


def rotr64(x, n):
    n = np.uint64(n & 63)
    return ((x >> n) | (x << (np.uint64(64) - n))).astype(np.uint64)


def shr64(x, n):
    return (x >> np.uint64(n)).astype(np.uint64)


def Sigma0_512(a): return rotr64(a, 28) ^ rotr64(a, 34) ^ rotr64(a, 39)
def Sigma1_512(e): return rotr64(e, 14) ^ rotr64(e, 18) ^ rotr64(e, 41)
def sigma0_512(x): return rotr64(x, 1) ^ rotr64(x, 8) ^ shr64(x, 7)
def sigma1_512(x): return rotr64(x, 19) ^ rotr64(x, 61) ^ shr64(x, 6)


def Ch64(e, f, g): return (e & f) ^ ((~e) & g)


def Maj64(a, b, c): return (a & b) ^ (a & c) ^ (b & c)


def state_at_r_sha512(M_arr, r):
    """State at round r for SHA-512."""
    N = M_arr.shape[0]
    W = np.empty((N, 80), dtype=np.uint64)
    W[:, :16] = M_arr
    for t in range(16, 80):
        if t > r + 16: break
        W[:, t] = (sigma1_512(W[:, t-2]) + W[:, t-7]
                   + sigma0_512(W[:, t-15]) + W[:, t-16]) & MASK64

    iv = np.broadcast_to(SHA512_IV, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    for t in range(r):
        T1 = (h + Sigma1_512(e) + Ch64(e, f, g) + SHA512_K[t] + W[:, t]) & MASK64
        T2 = (Sigma0_512(a) + Maj64(a, b, c)) & MASK64
        h = g; g = f; f = e
        e = (d + T1) & MASK64
        d = c; c = b; b = a
        a = (T1 + T2) & MASK64
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint64)


def state_to_bits(state):
    """Pack (N, 8) uint64 → (N, 512) bits, big-endian per word (SHA convention)."""
    N = state.shape[0]
    bytes_be = state.byteswap().view('<u1').reshape(N, 64)
    bits = np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :512]
    return bits


def measure_sha512_otoc(r, N=150, seed=42, msg_bytes=128):
    """Compute OTOC for SHA-512 at r rounds. msg = 1024 bits."""
    rng = np.random.default_rng(seed)
    base_msgs_arr = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)

    # Parse 128 bytes = 16 × 64-bit big-endian
    M_base = np.zeros((N, 16), dtype=np.uint64)
    for i in range(N):
        m = base_msgs_arr[i].tobytes()
        for w in range(16):
            M_base[i, w] = int.from_bytes(m[8*w:8*(w+1)], 'big')

    state_base = state_at_r_sha512(M_base, r)
    bits_base = state_to_bits(state_base)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 512), dtype=np.float64)
    for i in range(msg_bits):
        byte_idx = i // 8; bit_idx = 7 - (i % 8)
        flip_arr = base_msgs_arr.copy()
        flip_arr[:, byte_idx] ^= np.uint8(1 << bit_idx)
        M_flip = np.zeros((N, 16), dtype=np.uint64)
        for j in range(N):
            m = flip_arr[j].tobytes()
            for w in range(16):
                M_flip[j, w] = int.from_bytes(m[8*w:8*(w+1)], 'big')
        state_flip = state_at_r_sha512(M_flip, r)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def verify_sha512():
    """Full 80-round + feed-forward against hashlib.sha512 (single-block message only)."""
    import hashlib
    # Empty message
    msg = b''
    padded = bytearray(msg)
    padded.append(0x80)
    while len(padded) % 128 != 112:
        padded.append(0)
    # length in bits, 128-bit big-endian
    bit_len = len(msg) * 8
    padded += (0).to_bytes(8, 'big') + bit_len.to_bytes(8, 'big')
    if len(padded) != 128:
        print(f"  (empty msg padding requires 1 block, got {len(padded)} bytes)")
        return False

    # Parse
    M = np.zeros((1, 16), dtype=np.uint64)
    for w in range(16):
        M[0, w] = int.from_bytes(padded[8*w:8*(w+1)], 'big')
    state = state_at_r_sha512(M, 80)
    # Feed-forward
    final = (state[0] + SHA512_IV) & MASK64
    got = b''.join(int(x).to_bytes(8, 'big') for x in final)
    expected = hashlib.sha512(msg).digest()
    ok = got == expected
    print(f"  empty msg: {'match ✓' if ok else '✗ MISMATCH'}")
    if not ok:
        print(f"    expected: {expected.hex()}")
        print(f"    got:      {got.hex()}")
    return ok


def main():
    t0 = time.time()
    print("# SHA-512 OTOC round-by-round (intra-SHA-2 family comparison)")

    print("\n## Sanity: full 80R against hashlib.sha512 empty msg")
    verify_sha512()

    rounds_to_test = [1, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 64, 80]
    N = 150
    msg_bits = 1024
    out_bits = 512
    F_inf = msg_bits * out_bits * 0.25 / N

    print(f"\n  N={N}, msg={msg_bits} bits, output={out_bits} bits")
    print(f"  Theoretical RO limit: {F_inf:.2f}")
    print(f"\n{'r':>3}  {'||C||_F²':>12}  {'mean|C|':>10}  {'time':>6}")

    results = {}
    for r in rounds_to_test:
        ts = time.time()
        C = measure_sha512_otoc(r, N=N)
        F_sq = float((C ** 2).sum())
        mean_abs = float(np.mean(np.abs(C)))
        elapsed = time.time() - ts
        results[r] = {'frobenius_sq': F_sq, 'mean_abs': mean_abs, 'time': elapsed}
        print(f"{r:>3}  {F_sq:>12.2f}  {mean_abs:>10.4f}  {elapsed:>5.1f}s")

    scrambled_round = None
    for r in rounds_to_test:
        if abs(results[r]['frobenius_sq'] - F_inf) / F_inf < 0.05:
            scrambled_round = r; break

    print(f"\n## SHA-512 summary:")
    print(f"  Total rounds: 80, scramble at r = {scrambled_round}")
    if scrambled_round: print(f"  Relative: {scrambled_round/80*100:.0f}% of rounds")

    print(f"\n## SHA-2 intra-family comparison:")
    print(f"  SHA-256: r=24/64 = 37%")
    if scrambled_round:
        print(f"  SHA-512: r={scrambled_round}/80 = {scrambled_round/80*100:.0f}%")

    print(f"\n## Complete cross-architecture table (updated):")
    print(f"  {'Hash':>10}  {'Total':>6}  {'Scramble':>9}  {'%':>5}")
    print(f"  {'SHA-256':>10}  {64:>6}  {24:>9}  {37:>4}%")
    print(f"  {'SHA-512':>10}  {80:>6}  {scrambled_round if scrambled_round else '?':>9}  "
          f"{scrambled_round/80*100 if scrambled_round else 0:>4.0f}%")
    print(f"  {'SHA-3-256':>10}  {24:>6}  {4:>9}  {17:>4}%")
    print(f"  {'BLAKE2s':>10}  {10:>6}  {2:>9}  {20:>4}%")
    print(f"  {'BLAKE2b':>10}  {12:>6}  {3:>9}  {25:>4}%")

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
