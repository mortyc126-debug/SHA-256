"""
IT-4.S4 (surgical): does the bit5_max signal regenerate in block 2?

From S2: reduced-round single-block SHA-256 at r=64 gives NO bit5_max
signal (z ≈ -1.3). From IT-4 on standard 2-block SHA-256: z ≈ +4.28.

Hypothesis: the padding block (block 2) reintroduces/amplifies the signal.

Test: for each r2 ∈ {0, 8, 16, 24, 32, 48, 64}, run
  full block 1 (64 rounds) → state1
  reduced block 2 (r2 rounds on padding) → state2
Measure max|z| for bit5_max feature against 256-bit state2.

If signal grows monotonically with r2 → confirmed.
If r2=0 (just state1) already shows weak signal → maybe state1 has a
small latent signal that standard Walsh missed at 24 bits but catches at 256.

R=200 RO null (keyed BLAKE2b 32-byte) for reference.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_NULL = 200
SEED = 0xB10CC2
R2_LIST = [0, 4, 8, 12, 16, 20, 24, 32, 48, 64]
OUT = os.path.join(os.path.dirname(__file__), 'it4_s4_block2.json')


def low_hw2():
    L = 64
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def compress_full(state, block):
    """Standard full-64-round SHA-256 compression (vanilla variant)."""
    flags = ch.VARIANTS['V0_vanilla']
    return ch.compress(state, block, flags, ch.K_VANILLA)


def compress_r(state, block, n_rounds):
    """Reduced r-round SHA-256 compression (vanilla variant for r rounds).
    state, block: numpy uint32 arrays.
    """
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    K = ch.K_VANILLA
    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, n_rounds):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(n_rounds):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    new = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new + state) & MASK


def two_block_reduced_b2(messages, r2):
    """Full block 1 (64 rounds), then reduced block 2 (r2 rounds on padding)."""
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)

    pad = bytearray(64)
    pad[0] = 0x80
    pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8) \
        .view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))

    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state = compress_full(state, block1)   # full block 1
    if r2 > 0:
        state = compress_r(state, block2, r2)
    # if r2 == 0, just return state after block 1
    return state


def state_to_bits(state):
    N = state.shape[0]
    # extract MSB-first per word
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def walsh_z_vec(f_arr, out_bits):
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    equal = (out_bits == f_arr[:, None])
    eq = equal.sum(axis=0)
    return (2.0 * eq - N) / N * sqrtN


def keyed_blake_bits(inputs, key):
    N = len(inputs)
    byte_mat = np.empty((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        byte_mat[i] = np.frombuffer(hashlib.blake2b(x, key=key, digest_size=32).digest(), dtype=np.uint8)
    return np.unpackbits(byte_mat, axis=1, bitorder='big')


def main():
    t_total = time.time()
    print("# IT-4.S4: block-2 amplification of bit5_max signal")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, R_null = {R_NULL}")

    # Sanity: r2=64 should match hashlib.sha256 exactly
    state = two_block_reduced_b2(inputs[:3], 64)
    for i in range(3):
        ours = state[i].astype('>u4').tobytes()
        ref = hashlib.sha256(inputs[i]).digest()
        assert ours == ref, f"Mismatch at {i}"
    print("# Sanity: r2=64 matches hashlib ✓")

    per_r2 = {}
    for r2 in R2_LIST:
        print(f"\n## r2 = {r2}")
        t0 = time.time()
        state = two_block_reduced_b2(inputs, r2)
        bits = state_to_bits(state)
        z_vec = walsh_z_vec(f, bits)
        maxz = float(np.abs(z_vec).max())
        max_idx = int(np.argmax(np.abs(z_vec)))
        sumz2 = float((z_vec ** 2).sum())
        top3 = sorted(enumerate(z_vec), key=lambda kv: -abs(kv[1]))[:3]
        per_r2[r2] = {
            'sumz2': sumz2, 'maxz': maxz, 'max_idx': max_idx,
            'max_z_signed': float(z_vec[max_idx]),
            'top3': [{'bit': int(i), 'z': float(v)} for i, v in top3],
        }
        print(f"  Σz² = {sumz2:.1f}  max|z| = {maxz:.2f} at bit {max_idx}  "
              f"(time {time.time()-t0:.1f}s)")
        print(f"  top 3: " + ", ".join(f"bit{i}:{v:+.2f}" for i, v in top3))

    # RO null (same as S1/S2: 32-byte keyed BLAKE2b)
    print(f"\n## RO null with R={R_NULL}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_NULL)]
    ro_sumz2, ro_maxz = [], []
    t0 = time.time()
    for r, key in enumerate(keys):
        bits = keyed_blake_bits(inputs, key)
        z_vec = walsh_z_vec(f, bits)
        ro_sumz2.append(float((z_vec ** 2).sum()))
        ro_maxz.append(float(np.abs(z_vec).max()))
        if (r + 1) % 50 == 0:
            print(f"  r={r+1}/{R_NULL} elapsed={time.time()-t0:.1f}s")
    ro_sumz2 = np.asarray(ro_sumz2); ro_maxz = np.asarray(ro_maxz)
    m_sum, s_sum = float(ro_sumz2.mean()), float(ro_sumz2.std(ddof=1))
    m_max, s_max = float(ro_maxz.mean()), float(ro_maxz.std(ddof=1))
    print(f"  RO Σz²: {m_sum:.1f} ± {s_sum:.2f}")
    print(f"  RO maxz: {m_max:.2f} ± {s_max:.3f}  q99={float(np.quantile(ro_maxz, 0.99)):.2f}")

    # Summary
    print(f"\n## Amplification curve: bit5_max signal vs r2 (block-2 rounds)")
    print(f"  {'r2':>3}  {'Σz²':>7}  {'max|z|':>6}  {'max_bit':>7}  {'z_sum_vs_RO':>12}  {'z_max_vs_RO':>12}")
    for r2 in R2_LIST:
        info = per_r2[r2]
        z_s = (info['sumz2'] - m_sum) / s_sum
        z_m = (info['maxz'] - m_max) / s_max
        print(f"  {r2:>3}  {info['sumz2']:>7.1f}  {info['maxz']:>6.2f}  "
              f"{info['max_idx']:>7d}  {z_s:>+12.2f}  {z_m:>+12.2f}")

    out = {
        'meta': {'N': N, 'R_null': R_NULL, 'r2_list': R2_LIST},
        'per_r2': per_r2,
        'ro_band': {'sumz2': {'mean': m_sum, 'std': s_sum},
                    'maxz':  {'mean': m_max, 'std': s_max}},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
