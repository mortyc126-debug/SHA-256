"""
IT-4.Q7d: Walsh-3 CHAIN test wrapper.

Tests whether the 3rd-order Walsh decomposition of state1 explains the
bit5_max → state2[bit 10] signal in SHA-256.

For each state1 bit-triple (a, b, c), compute z_in = correlation of XOR
triple with input feature f (bit5_max), and z_out = correlation with
output target t (state2[bit 10]). Chain sum:
    chain_sum = Σ z_in * z_out / sqrt(N)
should approximate direct signal <f, t> · sqrt(N) if 3rd-order dominates.

Compare to RO null where t = keyed-BLAKE2b output bit 10 (to preserve
the same f, same state1, just randomize the block-2 compression).
Hmm wait — actually under RO, t should be INDEPENDENT of input.
We use R=50 RO realizations of state2 (= full-2-block-keyed-hash).
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 50
SEED = 0xC4A14D
WORDS = 2048
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_results.json')


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
    """Full 2-block SHA-256 (vanilla), return (N, 8) uint32 state."""
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
    """Return 1D array with bit_idx of keyed BLAKE2b 32-byte digest."""
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
    packed_bytes = np.packbits(padded, bitorder='little')
    return np.frombuffer(packed_bytes.tobytes(), dtype=np.uint64)


def write_input_bin(state_bits, f_arr, t_arr, path):
    """Binary format expected by C:
       uint64 N | 256*WORDS uint64 state | WORDS uint64 f_mask | WORDS uint64 t_mask
    """
    N = len(f_arr)
    with open(path, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256):
            mask = pack_bitmask(state_bits[:, b])
            fp.write(mask.tobytes())
        fp.write(pack_bitmask(f_arr).tobytes())
        fp.write(pack_bitmask(t_arr).tobytes())


def run_c(bin_path):
    res = subprocess.run([C_BIN, bin_path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def main():
    t_total = time.time()
    print("# IT-4.Q7d: Walsh-3 CHAIN test — does 3rd-order Walsh of state1 explain signal?")

    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, feature = bit5_max")

    # Compute state1 (block 1 output) — same for SHA and shared with RO
    print("# Computing state1 (block 1 output of SHA-256)...")
    state1 = state_after_block1(inputs)
    state1_bits = state_to_bits(state1)

    # ----- SHA-256: target = state2[bit 10] from full 2-block SHA-256 -----
    print("\n# SHA-256: target = state2[bit 10]")
    state2 = full_sha256_state(inputs)
    state2_bits = state_to_bits(state2)
    t_sha = state2_bits[:, 10].copy()
    print(f"  mean(t_sha) = {t_sha.mean():.4f}")
    # Verify
    direct_walsh_sha = 1 - 2*((f_arr ^ t_sha).sum()) / N
    print(f"  Direct <f, t_sha> * sqrt(N) = {direct_walsh_sha * math.sqrt(N):+.3f}")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        sha_path = tmp.name
    write_input_bin(state1_bits, f_arr, t_sha, sha_path)
    t0 = time.time()
    sha_res = run_c(sha_path)
    os.unlink(sha_path)
    print(f"  C scan in {time.time()-t0:.1f}s:")
    print(f"    max|z_in|  = {sha_res['max_abs_zin']:.3f}")
    print(f"    max|z_out| = {sha_res['max_abs_zout']:.3f}")
    print(f"    max|z_in * z_out| = {sha_res['max_abs_prod']:.3f}")
    print(f"    Best product triple: {sha_res['best_prod']}")
    print(f"    chain_sum = {sha_res['chain_sum']:+.3f}")
    print(f"    direct_signal_z = {sha_res['direct_signal_z']:+.3f}")
    print(f"    chain_sum / direct = {sha_res['chain_fraction']*100:+.1f}%  "
          f"(if 100%, 3rd-order Walsh fully explains signal)")
    print(f"    n_both_|z|>2 = {sha_res['n_both_gt_2']}  (expected under H_0: "
          f"{sha_res['n_triples'] * 0.046**2:.0f})")
    print(f"    n_both_|z|>3 = {sha_res['n_both_gt_3']}  (expected: "
          f"{sha_res['n_triples'] * 0.0027**2:.2f})")

    # ----- RO null: keyed-BLAKE2b as target, SAME state1 -----
    print(f"\n# RO null: R={R_RO} keyed-BLAKE2b targets")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_chain = []
    ro_direct = []
    ro_fraction = []
    ro_max_prod = []
    ro_n_both2 = []

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        ro_path = tmp.name
    t0_loop = time.time()
    try:
        for r, key in enumerate(keys):
            t_ro_bit = keyed_blake_bit(inputs, key, bit_idx=10)
            write_input_bin(state1_bits, f_arr, t_ro_bit, ro_path)
            res = run_c(ro_path)
            ro_chain.append(res['chain_sum'])
            ro_direct.append(res['direct_signal_z'])
            ro_fraction.append(res['chain_fraction'])
            ro_max_prod.append(res['max_abs_prod'])
            ro_n_both2.append(res['n_both_gt_2'])
            el = time.time() - t0_loop
            eta = el / (r + 1) * (R_RO - r - 1)
            print(f"  r={r+1}/{R_RO}  chain={res['chain_sum']:+.2f}  "
                  f"direct={res['direct_signal_z']:+.2f}  "
                  f"frac={res['chain_fraction']*100:+.1f}%  "
                  f"max_prod={res['max_abs_prod']:.1f}  "
                  f"elapsed={el:.0f}s  eta={eta:.0f}s")
    finally:
        os.unlink(ro_path)

    ro_chain = np.asarray(ro_chain)
    ro_direct = np.asarray(ro_direct)
    ro_frac = np.asarray(ro_fraction)
    ro_max_prod = np.asarray(ro_max_prod)
    ro_n_both2 = np.asarray(ro_n_both2)

    print(f"\n## RO band (R={R_RO}):")
    print(f"  chain_sum:       mean={ro_chain.mean():+.3f}  std={ro_chain.std(ddof=1):.3f}")
    print(f"  direct_signal_z: mean={ro_direct.mean():+.3f}  std={ro_direct.std(ddof=1):.3f}")
    print(f"  chain_fraction:  mean={ro_frac.mean()*100:+.2f}%  std={ro_frac.std(ddof=1)*100:.2f}%")
    print(f"  max_abs_prod:    mean={ro_max_prod.mean():.2f}  std={ro_max_prod.std(ddof=1):.2f}")
    print(f"  n_both_|z|>2:    mean={ro_n_both2.mean():.0f}  std={ro_n_both2.std(ddof=1):.1f}")

    # Verdict
    z_chain = (sha_res['chain_sum'] - ro_chain.mean()) / ro_chain.std(ddof=1)
    z_direct = (sha_res['direct_signal_z'] - ro_direct.mean()) / ro_direct.std(ddof=1)
    p_direct_ro = float((np.abs(ro_direct) >= abs(sha_res['direct_signal_z'])).sum() + 1) / (R_RO + 1)
    p_chain_ro = float((np.abs(ro_chain) >= abs(sha_res['chain_sum'])).sum() + 1) / (R_RO + 1)
    print(f"\n## Verdict")
    print(f"  SHA direct signal: {sha_res['direct_signal_z']:+.3f}  "
          f"(z_norm vs RO direct = {z_direct:+.2f}, p = {p_direct_ro:.4f})")
    print(f"  SHA chain (3rd-order): {sha_res['chain_sum']:+.3f}  "
          f"(z_norm vs RO chain = {z_chain:+.2f}, p = {p_chain_ro:.4f})")
    if abs(sha_res['chain_fraction']) > 0.5:
        print(f"  → 3rd-order Walsh EXPLAINS {sha_res['chain_fraction']*100:+.0f}% of signal.")
    elif abs(sha_res['chain_fraction']) < 0.1:
        print(f"  → 3rd-order Walsh explains <10% of signal — carrier is higher-order.")
    else:
        print(f"  → 3rd-order Walsh contributes {sha_res['chain_fraction']*100:+.0f}% — partial.")

    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'feature': 'bit5_max', 'target': 'state2[bit 10]'},
        'sha': sha_res,
        'ro_band': {
            'chain': {'values': ro_chain.tolist(),
                      'mean': float(ro_chain.mean()),
                      'std': float(ro_chain.std(ddof=1))},
            'direct_z': {'values': ro_direct.tolist(),
                         'mean': float(ro_direct.mean()),
                         'std': float(ro_direct.std(ddof=1))},
            'fraction': {'values': ro_frac.tolist(),
                         'mean': float(ro_frac.mean()),
                         'std': float(ro_frac.std(ddof=1))},
            'max_prod': {'mean': float(ro_max_prod.mean()),
                         'std': float(ro_max_prod.std(ddof=1))},
            'n_both_gt_2': {'mean': float(ro_n_both2.mean()),
                            'std': float(ro_n_both2.std(ddof=1))},
        },
        'z_chain': float(z_chain),
        'z_direct': float(z_direct),
        'p_chain_vs_ro': float(p_chain_ro),
        'p_direct_vs_ro': float(p_direct_ro),
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total time: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
