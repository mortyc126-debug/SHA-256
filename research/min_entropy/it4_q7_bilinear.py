"""
IT-4.Q7 (surgical): 2nd-order Walsh bilinear scan on state1.

From S2 we know: after 64 rounds of block 1, state1 is 1st-order
RO-clean for bit5_max. But S4 showed that block 2 compression extracts
a signal from state1. Our surgical hypothesis: state1 carries the
signal as a 2nd-order correlation — specific PAIRS of bits (a, b) whose
joint XOR correlates with bit5_max.

For f = bit5_max (HW=2 exhaustive), and Y = state1 (256 bits after
full block 1), define the 2nd-order Walsh coefficient of feature f
against bit-pair (a, b):

    W_ab = (1/N) Σ_x (-1)^(f(x) ⊕ Y_a(x) ⊕ Y_b(x))

Under H_0 (RO): W_ab ~ N(0, 1/N), so z_ab = W_ab · √N ~ N(0, 1).

Efficient computation via bilinear form:
    y' = 2Y - 1   (±1 coding)
    g  = 2f - 1
    M = (y' .T @ (y' * g[:, None])) / N    # shape (256, 256)
    z_ab = M[a, b] * sqrt(N)

All 256² = 65536 pairs at once via one matrix product.

Detection thresholds:
    Bonferroni for 256*255/2 = 32640 distinct off-diagonal pairs:
    α/32640 = 1.5e-6 → |z| > 4.81 under Normal approx.
    Empirical null from R RO realizations gives sharper bound.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 100
SEED = 0xB11174EA
OUT = os.path.join(os.path.dirname(__file__), 'it4_q7_bilinear.json')


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


def state_after_block1(messages):
    """Full 64 rounds of block 1 only. Returns (N, 8) uint32."""
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state):
    """(N, 8) uint32 → (N, 256) bits, MSB-first per word."""
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def keyed_blake_bits(inputs, key):
    N = len(inputs)
    byte_mat = np.empty((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        byte_mat[i] = np.frombuffer(hashlib.blake2b(x, key=key, digest_size=32).digest(), dtype=np.uint8)
    return np.unpackbits(byte_mat, axis=1, bitorder='big')


def bilinear_z_matrix(bits, f_arr):
    """Return (256, 256) matrix of z-scores for all bit-pairs.

    z[a, b] = mean((-1)^(f_arr ⊕ bits[:, a] ⊕ bits[:, b])) * sqrt(N)
    """
    N = bits.shape[0]
    y_pm = (2.0 * bits.astype(np.float32) - 1.0)    # (N, 256) in ±1
    g = (2.0 * f_arr.astype(np.float32) - 1.0)      # (N,) in ±1
    weighted = y_pm * g[:, None]                    # (N, 256)
    M = (y_pm.T @ weighted) / N                     # (256, 256)
    z = M * math.sqrt(N)
    return z.astype(np.float32)


def top_k_offdiag(z, k=20):
    """Return top-k (a, b, z_ab) with a < b."""
    out = []
    iu = np.triu_indices_from(z, k=1)
    idx = np.argsort(-np.abs(z[iu]))[:k]
    for i in idx:
        a, b = int(iu[0][i]), int(iu[1][i])
        out.append((a, b, float(z[a, b])))
    return out


def main():
    t_total = time.time()
    print("# IT-4.Q7: 2nd-order Walsh bilinear scan on state1 (bit5_max, HW=2)")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, R_RO = {R_RO}")

    # Compute state1 from block 1
    t0 = time.time()
    state1 = state_after_block1(inputs)
    state1_bits = state_to_bits(state1)
    print(f"# state1 bits: {state1_bits.shape}  ({time.time()-t0:.1f}s)")

    # Verify 1st-order is RO-clean
    def walsh1(bits, f_arr):
        N = bits.shape[0]
        y_pm = (2.0 * bits.astype(np.float32) - 1.0)
        g = (2.0 * f_arr.astype(np.float32) - 1.0)
        z1 = (y_pm.T @ g) / N * math.sqrt(N)
        return z1

    sha_z1 = walsh1(state1_bits, f)
    print(f"# 1st-order Walsh on state1: max|z1| = {np.abs(sha_z1).max():.2f} "
          f"at bit {np.argmax(np.abs(sha_z1))}")
    print(f"# (Expected ≈ RO: mean 0, max ≈ 3 for 256 tests)")

    # Compute 2nd-order bilinear z matrix for SHA-256 state1
    t0 = time.time()
    sha_z2 = bilinear_z_matrix(state1_bits, f)
    print(f"# 2nd-order bilinear scan: {time.time()-t0:.1f}s")
    sha_top = top_k_offdiag(sha_z2, k=30)
    sha_max_abs = float(np.abs(sha_top[0][2]))
    sha_sum_z2 = float((sha_z2[np.triu_indices_from(sha_z2, k=1)] ** 2).sum())
    print(f"# SHA-256 state1 bilinear: max|z_2| = {sha_max_abs:.3f}  Σz² = {sha_sum_z2:.1f}")
    print(f"  top 10 pairs:")
    for a, b, z in sha_top[:10]:
        same_word = (a // 32) == (b // 32)
        same_byte = (a // 8) == (b // 8)
        bit_in_byte_a = a & 7
        bit_in_byte_b = b & 7
        print(f"    ({a:>3}, {b:>3})  z={z:+.3f}  "
              f"word_a={a//32} word_b={b//32}  byte_a={a//8} byte_b={b//8}  "
              f"{'SAME_WORD' if same_word else '         '}  "
              f"{'SAME_BYTE' if same_byte else '         '}  "
              f"bib=({bit_in_byte_a},{bit_in_byte_b})")

    # RO null
    print(f"\n# RO null bilinear scan with R={R_RO}")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_max = []
    ro_sum = []
    t0 = time.time()
    for r, key in enumerate(keys):
        ro_bits = keyed_blake_bits(inputs, key)
        z2 = bilinear_z_matrix(ro_bits, f)
        iu = np.triu_indices_from(z2, k=1)
        ro_max.append(float(np.abs(z2[iu]).max()))
        ro_sum.append(float((z2[iu] ** 2).sum()))
        if (r + 1) % 10 == 0:
            print(f"  r={r+1}/{R_RO}  elapsed={time.time()-t0:.1f}s  "
                  f"max={ro_max[-1]:.2f}  Σz²={ro_sum[-1]:.0f}")
    ro_max = np.asarray(ro_max)
    ro_sum = np.asarray(ro_sum)

    m_max, s_max = float(ro_max.mean()), float(ro_max.std(ddof=1))
    m_sum, s_sum = float(ro_sum.mean()), float(ro_sum.std(ddof=1))

    z_max_norm = (sha_max_abs - m_max) / s_max
    z_sum_norm = (sha_sum_z2 - m_sum) / s_sum

    p_max = float((ro_max >= sha_max_abs).sum() + 1) / (R_RO + 1)
    p_sum = float((np.abs(ro_sum - m_sum) >= abs(sha_sum_z2 - m_sum)).sum() + 1) / (R_RO + 1)

    print(f"\n## Max|z_2| across 32640 pairs")
    print(f"  SHA-256 state1: {sha_max_abs:.3f}")
    print(f"  RO band:        {m_max:.3f} ± {s_max:.3f}  "
          f"q95={float(np.quantile(ro_max, 0.95)):.3f}  q99={float(np.quantile(ro_max, 0.99)):.3f}")
    print(f"  z_norm:         {z_max_norm:+.3f}")
    print(f"  P(RO_max ≥ SHA): {p_max:.4f}")

    print(f"\n## Σz² across 32640 pairs")
    print(f"  SHA-256 state1: {sha_sum_z2:.1f}")
    print(f"  RO band:        {m_sum:.1f} ± {s_sum:.1f}")
    print(f"  z_norm:         {z_sum_norm:+.3f}")
    print(f"  p_emp:          {p_sum:.4f}")

    # Structural locality of top pairs
    print(f"\n## Structural locality analysis of top 30 pairs")
    same_word = sum(1 for a, b, _ in sha_top if a // 32 == b // 32)
    same_byte = sum(1 for a, b, _ in sha_top if a // 8 == b // 8)
    print(f"  Same 32-bit word: {same_word}/30  (expected ≈ {30 * 7/256*32:.1f} under H_0)")
    print(f"  Same 8-bit byte:  {same_byte}/30  (expected ≈ {30 * 7/256*8:.1f} under H_0)")

    # save
    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'feature': 'bit5_max', 'HW': 2},
        'sha_max_abs_z2': sha_max_abs,
        'sha_sum_z2': sha_sum_z2,
        'sha_top30': [{'a': a, 'b': b, 'z': z} for a, b, z in sha_top],
        'ro_max_stats': {'mean': m_max, 'std': s_max,
                         'q95': float(np.quantile(ro_max, 0.95)),
                         'q99': float(np.quantile(ro_max, 0.99))},
        'ro_sum_stats': {'mean': m_sum, 'std': s_sum},
        'z_max_norm': z_max_norm, 'p_max': p_max,
        'z_sum_norm': z_sum_norm, 'p_sum': p_sum,
        'structural': {'same_word_top30': same_word, 'same_byte_top30': same_byte},
        'sha_z1_max': float(np.abs(sha_z1).max()),
        'sha_z1_max_bit': int(np.argmax(np.abs(sha_z1))),
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
