"""
IT-6c: Is Ω_3 universally high across different input features, or specific to bit5_max?

Test: for each of 9 single-bit features (bit0..bit8 of max position on HW=2),
compute Ω_3 = corr(direct_z, chain_3) across 256 output bits.

If all features give Ω_3 ≈ 0.98 → 3rd-order dominance is universal.
If only bit5 gives high Ω_3 → it's feature-specific.

Uses chain_3 via C for each (feature, output-bit) pair.
9 features × 256 bits × 2.5s ≈ 96 min. Too slow.

Instead: use the SAME state1 and precomputed data. The chain_3 C program
needs to be called per (feature, output-bit) pair since feature changes.

Faster approach: for each feature, we need to compute 256 chain_3 values.
BUT we can reuse state1 bitmasks (they don't change). Only f_mask changes.
Still 9 × 256 × 2.5s ≈ 96 min.

Compromise: compute only chain_2 (numpy, ~50s per feature) + direct_z.
chain_2 is fast enough and still shows the spectrum pattern.
"""
import json, math, os, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

LENGTH_BITS = 512
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6c_cross_feature.json')

def low_hw2():
    L = 64; inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions: b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b)); pos.append(positions)
    return inputs, pos

def state_after_block1(messages):
    N = len(messages); U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

def full_sha256_state(messages):
    N = len(messages); U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8).view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state = ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return ch.compress(state, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

def state_to_bits(state):
    N = state.shape[0]; bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits

def compute_omega_1_2(Y, sf, st, sqrtN):
    """Return (Ω_1, Ω_2, direct_z) for given signed feature sf."""
    direct_z = (st.T @ sf) / sqrtN
    # chain_1
    z_in_1 = (Y.T @ sf) / sqrtN
    Z_out_1 = (Y.T @ st) / sqrtN
    c1 = (z_in_1 @ Z_out_1) / sqrtN
    o1 = float(np.corrcoef(direct_z, c1)[0, 1])
    # chain_2
    M_in = (Y.T @ (Y * sf[:, None])) / sqrtN
    iu = np.triu_indices(256, k=1)
    M_in_flat = M_in[iu]
    c2 = np.zeros(256, dtype=np.float64)
    for b in range(256):
        st_b = st[:, b]
        M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
        c2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
    o2 = float(np.corrcoef(direct_z, c2)[0, 1])
    return o1, o2, direct_z

def main():
    t_total = time.time()
    print("# IT-6c: Ω_1, Ω_2 cross-feature universality test")
    inputs, pos = low_hw2(); N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    min_p = np.asarray([p[0] for p in pos], dtype=np.int64)

    s1 = state_to_bits(state_after_block1(inputs))
    s2 = state_to_bits(full_sha256_state(inputs))
    sqrtN = math.sqrt(N)
    Y = 2.0 * s1.astype(np.float32) - 1.0
    st = 2.0 * s2.astype(np.float32) - 1.0

    # Features to test
    features = {}
    for b in range(9):
        features[f'bit{b}_max'] = ((max_p >> b) & 1).astype(np.uint8)
    features['bit5_min'] = ((min_p >> 5) & 1).astype(np.uint8)
    features['bit5_xor'] = (((max_p >> 5) & 1) ^ ((min_p >> 5) & 1)).astype(np.uint8)
    features['parity_HW_max'] = np.asarray([bin(int(v)).count('1') & 1 for v in max_p], dtype=np.uint8)

    thresh = 3 / math.sqrt(254)
    print(f"\n## Ω spectrum per feature (3σ threshold = {thresh:.4f})")
    print(f"  {'feature':<16}  {'O_1':>8}  {'sig1':>4}  {'O_2':>8}  {'sig2':>4}  {'max|dz|':>8}  time")
    results = {}
    for fname, f_raw in features.items():
        t0 = time.time()
        sf = 2.0 * f_raw.astype(np.float32) - 1.0
        o1, o2, dz = compute_omega_1_2(Y, sf, st, sqrtN)
        s1f = 'YES' if abs(o1) > thresh else 'no'
        s2f = 'YES' if abs(o2) > thresh else 'no'
        maxdz = float(np.abs(dz).max())
        results[fname] = {'omega_1': o1, 'omega_2': o2, 'max_direct_z': maxdz}
        print(f"  {fname:<16}  {o1:>+8.4f}  {s1f:>4}  {o2:>+8.4f}  {s2f:>4}  {maxdz:>8.2f}  {time.time()-t0:.1f}s")

    out = {'meta': {'N': N, 'thresh_3sig': thresh}, 'features': results}
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t_total:.0f}s")

if __name__ == '__main__': main()
