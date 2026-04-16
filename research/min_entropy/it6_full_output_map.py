"""
IT-6: Full output-bit chain-signal map for SHA-256 on HW=2 exhaustive.

For each output bit b in [0, 256), measure:
  direct_z(b) = sqrt(N) · <bit5_max, state2[bit b]>     — classical Walsh-1
  chain_3(b) = Sum over triples T of state1 bits [z(T, bit5_max) · z(T, state2[bit b])] / sqrt(N)

Apply "new rule": use our own amplified tool (chain-3 via C) instead of
classical max|z|, and interpret even sub-threshold signals.

RO null (target-null): R=50 realizations where target = keyed-BLAKE2b
bit 10 (random target). For each RO realization, chain_3 is computed
against the random target. Distribution gives us noise baseline.

Expected: classical analysis (direct_z) flags only ~2 bits (b=10, 210).
Chain-3 might flag many more "hidden" bits where signal is distributed
rather than concentrated.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 50
N_OUT_BITS = 256
WORDS = 2048
SEED = 0x17615CA7
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6_full_output_map.json')


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
    pad = bytearray(64); pad[0] = 0x80
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


def keyed_blake_bit(inputs, key, bit_idx):
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
    print(f"# IT-6: full 256-output-bit chain-signal map")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)

    print("# Computing state1 and state2...")
    state1_bits = state_to_bits(state_after_block1(inputs))
    state2_bits = state_to_bits(full_sha256_state(inputs))

    # SHA side: direct z AND chain_3 for each of 256 output bits
    print(f"\n# SHA side: 256 target bits × chain_3 scan (~2.5s each, ~11 min total)")
    sha_direct = np.zeros(256)
    sha_chain = np.zeros(256)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        sha_path = tmp.name
    try:
        t_loop = time.time()
        for b in range(N_OUT_BITS):
            t_b = state2_bits[:, b].copy()
            # direct z
            direct_walsh = 1 - 2 * ((f_arr ^ t_b).sum()) / N
            sha_direct[b] = direct_walsh * math.sqrt(N)
            # chain_3 via C
            write_input_bin(state1_bits, f_arr, t_b, sha_path)
            res = run_c(sha_path)
            sha_chain[b] = res['chain_sum']
            if (b + 1) % 32 == 0:
                el = time.time() - t_loop
                eta = el / (b + 1) * (N_OUT_BITS - b - 1)
                print(f"  b={b+1}/{N_OUT_BITS}  direct={sha_direct[b]:+6.2f}  "
                      f"chain={sha_chain[b]:+9.1f}  "
                      f"elapsed={el:.0f}s eta={eta:.0f}s")
    finally:
        os.unlink(sha_path)

    # RO null: R=50 realizations of "random target" via keyed BLAKE2b
    print(f"\n# RO null: R={R_RO} realizations of random target")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_direct = np.zeros(R_RO)
    ro_chain = np.zeros(R_RO)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        ro_path = tmp.name
    try:
        t_loop = time.time()
        for r, key in enumerate(keys):
            t_ro = keyed_blake_bit(inputs, key, bit_idx=10)   # arbitrary bit, it's random
            direct_walsh = 1 - 2 * ((f_arr ^ t_ro).sum()) / N
            ro_direct[r] = direct_walsh * math.sqrt(N)
            write_input_bin(state1_bits, f_arr, t_ro, ro_path)
            res = run_c(ro_path)
            ro_chain[r] = res['chain_sum']
            if (r + 1) % 10 == 0:
                el = time.time() - t_loop
                eta = el / (r + 1) * (R_RO - r - 1)
                print(f"  r={r+1}/{R_RO}  chain={ro_chain[r]:+.2f}  "
                      f"elapsed={el:.0f}s eta={eta:.0f}s")
    finally:
        os.unlink(ro_path)

    # Statistics
    m_c = float(ro_chain.mean()); s_c = float(ro_chain.std(ddof=1))
    m_d = float(ro_direct.mean()); s_d = float(ro_direct.std(ddof=1))
    print(f"\n## RO null band:")
    print(f"  direct_z: mean={m_d:+.3f}  std={s_d:.3f}")
    print(f"  chain_3:  mean={m_c:+.3f}  std={s_c:.3f}")

    # z-norm for each output bit
    z_direct_norm = (sha_direct - m_d) / s_d
    z_chain_norm  = (sha_chain  - m_c) / s_c

    # Classify each of 256 bits:
    #   C1: |direct| > 3 AND |chain| > 3   — both detect
    #   C2: |direct| > 3 AND |chain| <= 3  — direct-only (classical see)
    #   C3: |direct| <= 3 AND |chain| > 3  — chain-only (HIDDEN, new rule)
    #   C4: neither                       — nothing

    thresh = 3.0
    c1 = []; c2 = []; c3 = []; c4 = []
    for b in range(N_OUT_BITS):
        zd = z_direct_norm[b]; zc = z_chain_norm[b]
        if abs(zd) > thresh and abs(zc) > thresh:
            c1.append((b, zd, zc))
        elif abs(zd) > thresh:
            c2.append((b, zd, zc))
        elif abs(zc) > thresh:
            c3.append((b, zd, zc))
        else:
            c4.append((b, zd, zc))

    print(f"\n## Classification of 256 output bits (threshold |z|>{thresh}):")
    print(f"  Category 1 (direct+chain both detect): {len(c1)}")
    for b, zd, zc in c1:
        print(f"    bit {b:>3}: direct_z={zd:+.2f}  chain_z={zc:+.2f}")
    print(f"  Category 2 (direct only): {len(c2)}")
    for b, zd, zc in c2:
        print(f"    bit {b:>3}: direct_z={zd:+.2f}  chain_z={zc:+.2f}")
    print(f"  Category 3 (HIDDEN: chain only, invisible to classical): {len(c3)}")
    for b, zd, zc in c3:
        print(f"    bit {b:>3}: direct_z={zd:+.2f}  chain_z={zc:+.2f}")
    print(f"  Category 4 (nothing): {len(c4)}")

    # Expected under H_0 with 256 bits, threshold |z|>3: 256 * 0.0027 = 0.7
    print(f"  Expected under H_0: ~{256 * 0.0027:.1f} per category")

    # Sub-threshold: |z|>2 in chain but |z|<2 in direct
    subthresh_2 = []
    for b in range(N_OUT_BITS):
        zd = z_direct_norm[b]; zc = z_chain_norm[b]
        if abs(zd) <= 2.0 and abs(zc) > 2.0:
            subthresh_2.append((b, zd, zc))
    print(f"\n  Sub-threshold hidden bits (|z_direct|<=2, |z_chain|>2): {len(subthresh_2)}")
    print(f"  (Expected under H_0 at |z|>2 in chain alone: ~{256 * 0.046:.0f})")
    print(f"  Top 20 by |z_chain|:")
    subthresh_2.sort(key=lambda x: -abs(x[2]))
    for b, zd, zc in subthresh_2[:20]:
        print(f"    bit {b:>3}: direct_z={zd:+.2f}  chain_z={zc:+.2f}")

    # Directional bias: is the signal systematically same-sign?
    # If real distributed signal, z_direct and z_chain should correlate across bits
    corr_dir_chain = float(np.corrcoef(z_direct_norm, z_chain_norm)[0, 1])
    print(f"\n## Correlation(z_direct, z_chain) across 256 bits: {corr_dir_chain:+.4f}")
    print(f"   (Expected under H_0: ≈ 0; under coherent signal: > 0)")

    # Count of same-sign pairs
    same_sign = int(np.sum(np.sign(z_direct_norm) == np.sign(z_chain_norm)))
    print(f"   Same-sign bits: {same_sign}/256 (expected 128 under H_0, "
          f"sign-test p = {'significant' if abs(same_sign - 128) > 16 else 'not significant'})")

    # Save
    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'feature': 'bit5_max'},
        'sha_direct': sha_direct.tolist(),
        'sha_chain': sha_chain.tolist(),
        'z_direct_norm': z_direct_norm.tolist(),
        'z_chain_norm': z_chain_norm.tolist(),
        'ro_direct': {'mean': m_d, 'std': s_d, 'values': ro_direct.tolist()},
        'ro_chain':  {'mean': m_c, 'std': s_c, 'values': ro_chain.tolist()},
        'categories': {
            'both': [{'bit': b, 'zd': zd, 'zc': zc} for b, zd, zc in c1],
            'direct_only': [{'bit': b, 'zd': zd, 'zc': zc} for b, zd, zc in c2],
            'chain_only_hidden': [{'bit': b, 'zd': zd, 'zc': zc} for b, zd, zc in c3],
        },
        'subthreshold_chain_2': [{'bit': b, 'zd': zd, 'zc': zc} for b, zd, zc in subthresh_2],
        'corr_direct_chain': corr_dir_chain,
        'same_sign_count': same_sign,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total: {time.time() - t_total:.0f}s")


if __name__ == '__main__':
    main()
