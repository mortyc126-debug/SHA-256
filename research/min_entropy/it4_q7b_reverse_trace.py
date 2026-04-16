"""
IT-4.Q7b (surgical): reverse-trace state2[bit 10] back to state1.

Q7 found: state1 has NO 1st-order and NO 2nd-order Walsh correlation
with bit5_max input feature. Yet state2[bit 10] DOES correlate at
z=-3.92. So block 2 extracts the signal from 3rd or higher-order
structure of state1.

Surgical question: WHICH state1 bits does state2[bit 10] functionally
depend on? Even though Walsh-order-1/2 analysis missed it, the
deterministic function state2[10] = F(state1) has a specific support.

Two approaches:
  (A) Linear correlation of state1 bits with state2[10]:
      for each state1 bit b, compute corr(state1[b], state2[10])
      over all 130816 inputs. Identifies state1 bits whose value
      linearly influences state2[10].

  (B) Pairwise correlation of (state1[a] ⊕ state1[b]) with state2[10]:
      identifies pairs of state1 bits that LINEARLY influence state2[10]
      via their XOR.

Then for top candidates from (A) and (B), check whether they ALSO
correlate with bit5_max. If so, the chain is:

  bit5_max → state1 bit(s) → state2[10]

with magnitude matching z=-3.92 at state2[10].
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
OUT = os.path.join(os.path.dirname(__file__), 'it4_q7b_reverse_trace.json')


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
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def full_sha256_state(messages):
    """Full 2-block SHA-256, return final state."""
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
    state = ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    state = ch.compress(state, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return state


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def walsh_z_vector(f_arr, bits):
    """f_arr: (N,), bits: (N, K) — return K z-scores against f."""
    N = len(f_arr)
    y_pm = 2.0 * bits.astype(np.float32) - 1.0
    g = 2.0 * f_arr.astype(np.float32) - 1.0
    z1 = (y_pm.T @ g) / N * math.sqrt(N)
    return z1


def bilinear_z(ref, bits):
    """ref: (N,) binary reference (e.g. state2[10]).
    bits: (N, K) binary.
    Return (K, K) z-score matrix for bilinear corr between pairs."""
    N = len(ref)
    y_pm = 2.0 * bits.astype(np.float32) - 1.0
    r_pm = 2.0 * ref.astype(np.float32) - 1.0
    weighted = y_pm * r_pm[:, None]
    M = (y_pm.T @ weighted) / N
    return M.astype(np.float32) * math.sqrt(N)


def main():
    t_total = time.time()
    print("# IT-4.Q7b: reverse-trace state2[bit 10] back to state1")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_input = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, feature = bit5_max, target = state2[bit 10]")

    # Compute state1 (after block 1) and state2 (after block 2)
    t0 = time.time()
    state1 = state_after_block1(inputs)
    state2 = full_sha256_state(inputs)
    s1_bits = state_to_bits(state1)
    s2_bits = state_to_bits(state2)
    print(f"# Computed state1, state2 bits: {time.time()-t0:.1f}s")

    # Sanity check: state2[bit 10] vs f_input
    target = s2_bits[:, 10]
    target_walsh_f = walsh_z_vector(f_input, target[:, None])[0]
    print(f"# state2[bit 10] vs bit5_max: z = {target_walsh_f:+.3f}  (known ≈ -3.92)")

    # (A) Linear correlation of state1 bits with state2[bit 10]
    print("\n## (A) 1st-order Walsh: each state1 bit vs state2[bit 10]")
    z1_s1_vs_t = walsh_z_vector(target, s1_bits)
    # Top absolute correlations
    top_A = sorted(enumerate(z1_s1_vs_t), key=lambda kv: -abs(kv[1]))[:15]
    print(f"  max|z| = {np.abs(z1_s1_vs_t).max():.2f}")
    print(f"  Top 10 state1 bits by |corr with state2[10]|:")
    for b, zv in top_A[:10]:
        word = b // 32; bit_in_word = b % 32
        # Also check: does this state1 bit correlate with bit5_max input?
        s1b_vs_f = walsh_z_vector(f_input, s1_bits[:, b:b+1])[0]
        print(f"    state1 bit {b:>3} (word {word}, bit-in-word {bit_in_word:>2}): "
              f"corr_with_target z = {zv:>+6.2f}  | corr_with_bit5max z = {s1b_vs_f:>+6.2f}")

    # (B) Bilinear XOR of state1 bit-pairs vs state2[bit 10]
    print("\n## (B) 2nd-order XOR: (state1[a] ⊕ state1[b]) vs state2[bit 10]")
    t0 = time.time()
    z2_mat = bilinear_z(target, s1_bits)
    print(f"  bilinear computed in {time.time()-t0:.1f}s")
    iu = np.triu_indices_from(z2_mat, k=1)
    abs_z2 = np.abs(z2_mat[iu])
    top_idx = np.argsort(-abs_z2)[:15]
    print(f"  max|z| bilinear = {abs_z2.max():.2f}")
    print(f"  Top 10 pairs:")
    for ti in top_idx[:10]:
        a = int(iu[0][ti]); b = int(iu[1][ti]); zv = float(z2_mat[a, b])
        # Also: does XOR of (s1[a], s1[b]) correlate with bit5_max input?
        xor_ab = s1_bits[:, a] ^ s1_bits[:, b]
        xor_vs_f = walsh_z_vector(f_input, xor_ab[:, None])[0]
        print(f"    pair ({a:>3}, {b:>3}): corr_with_target z = {zv:>+6.2f}  | "
              f"corr_with_bit5max z = {xor_vs_f:>+6.2f}")

    # Correlation chain verification:
    # If state1 bit b is correlated with target (step 1) AND with bit5_max (step 2),
    # the product of correlations should match total target-bit5_max correlation.
    print("\n## Chain analysis: product of correlations via top state1 bits")
    # Top 10 bits by abs corr with target
    top10_bits = [b for b, _ in top_A[:10]]
    # Sum of products: c_b(target,bit) * c_b(bit,feature)
    products = []
    for b, _ in top_A[:30]:
        c_tb = z1_s1_vs_t[b] / math.sqrt(N)                # corr(target, s1[b])
        c_bf = walsh_z_vector(f_input, s1_bits[:, b:b+1])[0] / math.sqrt(N)   # corr(s1[b], feature)
        products.append(c_tb * c_bf)
    total_via_s1 = sum(products) * math.sqrt(N)
    print(f"  Σ_{{top30 state1 bits}} corr(target, b) · corr(b, feature) · √N = {total_via_s1:+.3f}")
    print(f"  Direct corr(target, feature) · √N = {target_walsh_f:+.3f}")
    print(f"  → Linear-through-state1-bits accounts for "
          f"{100 * total_via_s1 / target_walsh_f:.1f}% of target signal")

    # Similarly through top 100 pairs
    print("\n## Chain analysis: product via top state1 bit-pairs (XOR)")
    top_pairs = []
    for ti in top_idx[:100]:
        a = int(iu[0][ti]); b = int(iu[1][ti])
        top_pairs.append((a, b, float(z2_mat[a, b])))
    products_pair = []
    for a, b, z_tab in top_pairs:
        xor_ab = s1_bits[:, a] ^ s1_bits[:, b]
        c_tab = z_tab / math.sqrt(N)
        c_abf = walsh_z_vector(f_input, xor_ab[:, None])[0] / math.sqrt(N)
        products_pair.append(c_tab * c_abf)
    total_via_pairs = sum(products_pair) * math.sqrt(N)
    print(f"  Σ_{{top100 state1 XOR pairs}} corr(target, a⊕b) · corr(a⊕b, feature) · √N = {total_via_pairs:+.3f}")
    print(f"  → Linear-through-state1-XOR-pairs accounts for "
          f"{100 * total_via_pairs / target_walsh_f:.1f}% of target signal")

    out = {
        'meta': {'N': N, 'feature': 'bit5_max', 'HW': 2, 'target': 'state2[bit 10]'},
        'target_vs_feature_z': float(target_walsh_f),
        'top_state1_bits_A': [
            {'bit': int(b), 'corr_with_target_z': float(z),
             'corr_with_feature_z': float(walsh_z_vector(f_input, s1_bits[:, b:b+1])[0])}
            for b, z in top_A[:30]
        ],
        'top_pair_product_fraction': float(total_via_pairs / target_walsh_f),
        'top_bits_product_fraction': float(total_via_s1 / target_walsh_f),
    }
    with open(OUT, 'w') as f_:
        json.dump(out, f_, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
