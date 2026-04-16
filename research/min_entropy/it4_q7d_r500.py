"""
IT-4.Q7d-R500: chain-3 test at R=500 (was R=50).

Tightens empirical p-value resolution: 1/51 → 1/501.
If SHA-256 chain_sum is really −83.10 and RO distribution has std ~22,
then at R=500 we expect to still see p ≈ 0.001-0.005 (z = −3.87 → 2-sided
p ≈ 0.0001 analytically, empirically bounded by 1/(R+1)).

Uses SAME inputs, SAME state1, SAME targets as Q7d. Only R increases.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 500
SEED = 0xA14C500
WORDS = 2048
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_r500_results.json')


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
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    pad = bytearray(64)
    pad[0] = 0x80
    pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8).view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state = ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return ch.compress(state, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def keyed_blake_bit(inputs, key, bit_idx=10):
    N = len(inputs)
    arr = np.zeros(N, dtype=np.uint8)
    byte_idx = bit_idx // 8
    shift = 7 - (bit_idx % 8)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=32).digest()
        arr[i] = (d[byte_idx] >> shift) & 1
    return arr


def pack_bitmask(bits_vec):
    padded = np.zeros(WORDS * 64, dtype=np.uint8)
    padded[:len(bits_vec)] = bits_vec
    pb = np.packbits(padded, bitorder='little')
    return np.frombuffer(pb.tobytes(), dtype=np.uint64)


def write_input_bin(state_bits, f_arr, t_arr, path):
    N = len(f_arr)
    with open(path, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256):
            fp.write(pack_bitmask(state_bits[:, b]).tobytes())
        fp.write(pack_bitmask(f_arr).tobytes())
        fp.write(pack_bitmask(t_arr).tobytes())


def run_c(bin_path):
    res = subprocess.run([C_BIN, bin_path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def main():
    t_total = time.time()
    print(f"# IT-4.Q7d-R500: chain-3 at R={R_RO}")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)

    print("# Computing state1, state2...")
    state1_bits = state_to_bits(state_after_block1(inputs))
    state2_bits = state_to_bits(full_sha256_state(inputs))
    t_sha = state2_bits[:, 10].copy()

    # SHA-256
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        sha_path = tmp.name
    write_input_bin(state1_bits, f_arr, t_sha, sha_path)
    sha = run_c(sha_path)
    os.unlink(sha_path)
    print(f"# SHA: direct_z = {sha['direct_signal_z']:+.3f}  chain_sum = {sha['chain_sum']:+.3f}")

    # RO null
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_chain, ro_direct = [], []
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        ro_path = tmp.name
    try:
        t0_loop = time.time()
        for r, key in enumerate(keys):
            t_ro = keyed_blake_bit(inputs, key, bit_idx=10)
            write_input_bin(state1_bits, f_arr, t_ro, ro_path)
            res = run_c(ro_path)
            ro_chain.append(res['chain_sum'])
            ro_direct.append(res['direct_signal_z'])
            if (r + 1) % 25 == 0:
                el = time.time() - t0_loop
                eta = el / (r + 1) * (R_RO - r - 1)
                print(f"  r={r+1}/{R_RO}  elapsed={el:.0f}s  eta={eta:.0f}s")
    finally:
        os.unlink(ro_path)
    ro_chain = np.asarray(ro_chain)
    ro_direct = np.asarray(ro_direct)

    # Stats
    m_c, s_c = float(ro_chain.mean()), float(ro_chain.std(ddof=1))
    m_d, s_d = float(ro_direct.mean()), float(ro_direct.std(ddof=1))
    z_chain = (sha['chain_sum'] - m_c) / s_c
    z_direct = (sha['direct_signal_z'] - m_d) / s_d
    p_chain = float((np.abs(ro_chain - m_c) >= abs(sha['chain_sum'] - m_c)).sum() + 1) / (R_RO + 1)
    p_direct = float((np.abs(ro_direct - m_d) >= abs(sha['direct_signal_z'] - m_d)).sum() + 1) / (R_RO + 1)

    print(f"\n## RO band (R={R_RO}):")
    print(f"  chain_sum:       mean={m_c:+.3f}  std={s_c:.3f}")
    print(f"  direct_signal_z: mean={m_d:+.3f}  std={s_d:.3f}")
    # additional quantiles
    print(f"  chain_sum:       q05={np.quantile(ro_chain, 0.05):+.2f}  "
          f"q95={np.quantile(ro_chain, 0.95):+.2f}")

    print(f"\n## Verdict at R={R_RO}")
    print(f"  SHA direct:  {sha['direct_signal_z']:+.3f}  z_norm={z_direct:+.2f}  "
          f"p_emp={p_direct:.5f}  (was 0.02 at R=50)")
    print(f"  SHA chain-3: {sha['chain_sum']:+.3f}  z_norm={z_chain:+.2f}  "
          f"p_emp={p_chain:.5f}  (was 0.02 at R=50)")
    # Bonferroni for 3 tests (Q7d-R500 + Q7e + Q7f) gives α_eff = 0.05/3 = 0.0167
    print(f"  Bonferroni-3 threshold p < 0.0167: "
          f"{'PASS' if p_chain < 0.0167 else 'FAIL'} (chain), "
          f"{'PASS' if p_direct < 0.0167 else 'FAIL'} (direct)")

    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'target': 'state2[bit 10]'},
        'sha': sha,
        'ro_chain': {'mean': m_c, 'std': s_c,
                     'q05': float(np.quantile(ro_chain, 0.05)),
                     'q95': float(np.quantile(ro_chain, 0.95)),
                     'values': ro_chain.tolist()},
        'ro_direct': {'mean': m_d, 'std': s_d, 'values': ro_direct.tolist()},
        'z_chain': float(z_chain), 'p_chain': p_chain,
        'z_direct': float(z_direct), 'p_direct': p_direct,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
