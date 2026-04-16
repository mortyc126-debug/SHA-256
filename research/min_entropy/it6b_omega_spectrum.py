"""
IT-6b: Full Ω_k spectrum for SHA-256 on (HW=2, bit5_max).

Ω_k := corr_b( direct_z(b), chain_k(b) )    for b in output bits 0..255

Measure Ω_1, Ω_2, Ω_3, Ω_4.
  k=1, 2:  numpy (fast, all 256 bits)
  k=3:     reuse from IT-6 (computed via C, all 256 bits) → Ω_3 = 0.9795
  k=4:     C scan, subsample of 30 output bits (~75 min)

Null hypothesis:
  Under H_0 (random target bits), 256 direct_z and chain_k values are
  approximately iid with means 0. Correlation has std ≈ 1/sqrt(n-2).
  For n=256: std ≈ 0.063. Rejection |Ω| > 3·0.063 = 0.19.
  For n=30: std ≈ 0.19. Rejection |Ω| > 0.57.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
WORDS = 2048
K4_SUBSAMPLE = 30          # output-bit subsample for k=4 (compute-limited)
SEED = 0x0E6A4E            # for choosing subsample
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6b_omega_spectrum.json')


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


def compute_direct_z_all(f_arr, state2_bits, N):
    """direct_z(b) = sqrt(N) * <sigma(f), sigma(state2[b])> for each b."""
    sqrtN = math.sqrt(N)
    sigma_f = 2.0 * f_arr.astype(np.float32) - 1.0                 # (N,)
    sigma_t = 2.0 * state2_bits.astype(np.float32) - 1.0           # (N, 256)
    return (sigma_t.T @ sigma_f) / sqrtN                           # (256,)


def compute_chain_1_all(state1_bits, f_arr, state2_bits, N):
    """chain_1(b) for all 256 output bits. Vectorised.
    chain_1(b) = (1/sqrt(N)) · Σ over state bits b_s of z_in(b_s) · z_out_b(b_s)
    """
    sqrtN = math.sqrt(N)
    Y = 2.0 * state1_bits.astype(np.float32) - 1.0                 # (N, 256) state1
    sigma_f = 2.0 * f_arr.astype(np.float32) - 1.0
    sigma_t = 2.0 * state2_bits.astype(np.float32) - 1.0           # (N, 256)
    z_in_per_state = (Y.T @ sigma_f) / sqrtN                       # (256,)
    Z_out = (Y.T @ sigma_t) / sqrtN                                # (256, 256): state × out
    return (z_in_per_state @ Z_out) / sqrtN                        # (256,) output bits


def compute_chain_2_all(state1_bits, f_arr, state2_bits, N):
    """chain_2(b) for all 256 output bits. Loops over output bits, each matmul."""
    sqrtN = math.sqrt(N)
    Y = 2.0 * state1_bits.astype(np.float32) - 1.0
    sigma_f = 2.0 * f_arr.astype(np.float32) - 1.0
    M_in = (Y.T @ (Y * sigma_f[:, None])) / sqrtN                  # (256, 256)
    iu = np.triu_indices(256, k=1)
    M_in_flat = M_in[iu]                                           # upper triangle

    out = np.zeros(256, dtype=np.float64)
    for b in range(256):
        sigma_t_b = 2.0 * state2_bits[:, b].astype(np.float32) - 1.0
        M_out_b = (Y.T @ (Y * sigma_t_b[:, None])) / sqrtN
        out[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
    return out


def pack_bitmask(bits_vec):
    padded = np.zeros(WORDS * 64, dtype=np.uint8)
    padded[:len(bits_vec)] = bits_vec
    pb = np.packbits(padded, bitorder='little')
    return np.frombuffer(pb.tobytes(), dtype=np.uint64)


def write_chain3_bin(state_bits, f_arr, t_arr, path):
    N = len(f_arr)
    with open(path, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256):
            fp.write(pack_bitmask(state_bits[:, b]).tobytes())
        fp.write(pack_bitmask(f_arr).tobytes())
        fp.write(pack_bitmask(t_arr).tobytes())


def chain_k_via_c(state_bits, f_arr, t_arr, k):
    """k must be 3 (chain3) or 4 (chain4). Returns chain_sum."""
    if k == 3:
        binary = C_BIN
    elif k == 4:
        binary = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7f_chain4')
    else:
        raise ValueError(k)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        path = tmp.name
    try:
        write_chain3_bin(state_bits, f_arr, t_arr, path)
        res = subprocess.run([binary, path], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)['chain_sum']
    finally:
        os.unlink(path)


def main():
    t_total = time.time()
    print("# IT-6b: full Ω_k spectrum")

    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)

    print("# Computing state1, state2...")
    s1 = state_to_bits(state_after_block1(inputs))
    s2 = state_to_bits(full_sha256_state(inputs))

    # Direct z for all 256 output bits
    print("\n# Direct z per output bit (all 256)...")
    direct_z = compute_direct_z_all(f_arr, s2, N)
    print(f"  max|direct_z| = {np.abs(direct_z).max():.3f}")

    # Ω_1
    print("\n# chain_1 all 256 output bits (numpy)...")
    t0 = time.time()
    chain_1_vec = compute_chain_1_all(s1, f_arr, s2, N)
    print(f"  time: {time.time()-t0:.1f}s")
    omega_1 = float(np.corrcoef(direct_z, chain_1_vec)[0, 1])
    same_sign_1 = int(np.sum(np.sign(direct_z) == np.sign(chain_1_vec)))
    print(f"  Ω_1 = {omega_1:+.4f}  (same-sign bits: {same_sign_1}/256)")

    # Ω_2
    print("\n# chain_2 all 256 output bits (numpy, 256 matmul)...")
    t0 = time.time()
    chain_2_vec = compute_chain_2_all(s1, f_arr, s2, N)
    print(f"  time: {time.time()-t0:.1f}s")
    omega_2 = float(np.corrcoef(direct_z, chain_2_vec)[0, 1])
    same_sign_2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2_vec)))
    print(f"  Ω_2 = {omega_2:+.4f}  (same-sign bits: {same_sign_2}/256)")

    # Ω_3 — from IT-6 (already computed)
    print("\n# Ω_3: reading from IT-6 (all 256 bits already computed)")
    try:
        it6 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it6_full_output_map.json')))
        omega_3 = it6['corr_direct_chain']
        same_sign_3 = it6['same_sign_count']
        print(f"  Ω_3 = {omega_3:+.4f}  (same-sign bits: {same_sign_3}/256)")
        chain_3_vec = np.asarray(it6['sha_chain'])
    except Exception as e:
        print(f"  Could not load IT-6: {e}")
        omega_3 = None; same_sign_3 = None; chain_3_vec = None

    # Ω_4 — subsample
    print(f"\n# Ω_4: chain_4 subsample of {K4_SUBSAMPLE} output bits (~{K4_SUBSAMPLE*144/60:.0f} min)")
    rng = np.random.default_rng(SEED)
    # Include bits known to be interesting + random
    interesting = [10, 210]
    available = [b for b in range(256) if b not in interesting]
    chosen = list(interesting) + list(rng.choice(available, size=K4_SUBSAMPLE - len(interesting), replace=False))
    chosen.sort()
    print(f"  Output bits sampled: {chosen[:10]} ... ({len(chosen)} total)")

    t0_loop = time.time()
    chain_4_sub = np.zeros(len(chosen))
    direct_z_sub = np.zeros(len(chosen))
    for i, b in enumerate(chosen):
        direct_z_sub[i] = direct_z[b]
        t_bits = s2[:, b].copy()
        t0 = time.time()
        chain_4_sub[i] = chain_k_via_c(s1, f_arr, t_bits, k=4)
        el = time.time() - t0_loop
        eta = el / (i + 1) * (len(chosen) - i - 1)
        print(f"  {i+1}/{len(chosen)} bit={b:>3}  direct_z={direct_z[b]:+6.2f}  "
              f"chain_4={chain_4_sub[i]:+10.1f}  iter={time.time()-t0:.0f}s  eta={eta:.0f}s")

    omega_4 = float(np.corrcoef(direct_z_sub, chain_4_sub)[0, 1])
    same_sign_4 = int(np.sum(np.sign(direct_z_sub) == np.sign(chain_4_sub)))
    print(f"\n  Ω_4 = {omega_4:+.4f}  (same-sign bits: {same_sign_4}/{len(chosen)})")

    # Full spectrum table
    print("\n## Ω_k spectrum summary")
    print(f"  {'k':>2}  {'Ω_k':>+8}  {'n_bits':>7}  {'3σ thresh':>10}  {'significant':>12}")
    for k, omega, n in [(1, omega_1, 256), (2, omega_2, 256), (3, omega_3, 256), (4, omega_4, len(chosen))]:
        if omega is None: continue
        thresh = 3 / math.sqrt(n - 2)
        sig = 'YES' if abs(omega) > thresh else 'no'
        print(f"  {k:>2}  {omega:>+8.4f}  {n:>7}  {thresh:>10.4f}  {sig:>12}")

    out = {
        'meta': {'N': N, 'n_subsample': K4_SUBSAMPLE},
        'omega_spectrum': {
            '1': {'value': omega_1, 'same_sign': same_sign_1, 'n_bits': 256},
            '2': {'value': omega_2, 'same_sign': same_sign_2, 'n_bits': 256},
            '3': {'value': omega_3, 'same_sign': same_sign_3, 'n_bits': 256},
            '4': {'value': omega_4, 'same_sign': same_sign_4, 'n_bits': len(chosen)},
        },
        'direct_z_all': direct_z.tolist(),
        'chain_1': chain_1_vec.tolist(),
        'chain_2': chain_2_vec.tolist(),
        'chain_4_sub': {'bits': chosen, 'direct_z': direct_z_sub.tolist(), 'chain_4': chain_4_sub.tolist()},
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total: {time.time() - t_total:.0f}s")


if __name__ == '__main__':
    main()
