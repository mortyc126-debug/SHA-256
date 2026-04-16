"""
IT-6b (fast): Ω_1 and Ω_2 via numpy (seconds). Ω_3 from IT-6. Skip Ω_4.
"""
import json, math, os, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

LENGTH_BITS = 512
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6b_omega_spectrum.json')

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

def main():
    t0 = time.time()
    print("# IT-6b (fast): Ω_1, Ω_2 spectrum")
    inputs, pos = low_hw2(); N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)
    s1 = state_to_bits(state_after_block1(inputs))
    s2 = state_to_bits(full_sha256_state(inputs))
    sqrtN = math.sqrt(N)
    Y = 2.0 * s1.astype(np.float32) - 1.0
    sf = 2.0 * f_arr.astype(np.float32) - 1.0
    st = 2.0 * s2.astype(np.float32) - 1.0

    # direct_z per output bit
    direct_z = (st.T @ sf) / sqrtN

    # chain_1 per output bit
    z_in_1 = (Y.T @ sf) / sqrtN
    Z_out_1 = (Y.T @ st) / sqrtN
    chain_1 = (z_in_1 @ Z_out_1) / sqrtN
    omega_1 = float(np.corrcoef(direct_z, chain_1)[0, 1])
    ss1 = int(np.sum(np.sign(direct_z) == np.sign(chain_1)))
    print(f"  Ω_1 = {omega_1:+.4f}  same-sign={ss1}/256  ({time.time()-t0:.1f}s)")

    # chain_2 per output bit
    t1 = time.time()
    M_in = (Y.T @ (Y * sf[:, None])) / sqrtN
    iu = np.triu_indices(256, k=1)
    M_in_flat = M_in[iu]
    chain_2 = np.zeros(256, dtype=np.float64)
    for b in range(256):
        st_b = 2.0 * s2[:, b].astype(np.float32) - 1.0
        M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
        chain_2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
    omega_2 = float(np.corrcoef(direct_z, chain_2)[0, 1])
    ss2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2)))
    print(f"  Ω_2 = {omega_2:+.4f}  same-sign={ss2}/256  ({time.time()-t1:.1f}s)")

    # Ω_3 from IT-6
    try:
        it6 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6_full_output_map.json')))
        omega_3 = it6['corr_direct_chain']; ss3 = it6['same_sign_count']
    except: omega_3 = None; ss3 = None
    print(f"  Ω_3 = {omega_3:+.4f}  same-sign={ss3}/256  (from IT-6)")

    # Summary
    print(f"\n## Ω_k spectrum (3σ threshold = {3/math.sqrt(254):.4f}):")
    thresh = 3 / math.sqrt(254)
    for k, om, ss in [(1, omega_1, ss1), (2, omega_2, ss2), (3, omega_3, ss3)]:
        if om is None: continue
        sig = 'YES' if abs(om) > thresh else 'no'
        print(f"  k={k}: Ω = {om:+.4f}  same-sign = {ss}/256  significant = {sig}")

    out = {'omega_1': omega_1, 'omega_2': omega_2, 'omega_3': omega_3,
           'same_sign': {'k1': ss1, 'k2': ss2, 'k3': ss3},
           'direct_z': direct_z.tolist(), 'chain_1': chain_1.tolist(), 'chain_2': chain_2.tolist()}
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t0:.0f}s")

if __name__ == '__main__': main()
