"""Phase 8C v2: PROPER audit of IT-6 Ω_3 = +0.98 using full 256-bit triples.

Uses IT-6's C binary (it4_q7d_chain3) for chain_3 over all C(256,3) = 2.76M
triples of state1 bits. This is the same protocol IT-6 used.

Critical: also compute Pearson Ω_3 for RO targets (BLAKE2b output for full
256 bits) and compare to SHA. If RO targets give same Ω as SHA → IT-6
claim is artifact even with full triple basis.

Computational note: chain_3 per output bit takes ~3s in C → 256 bits per
target = ~13 min per trial. Run SHA + 5 RO trials = ~78 min.
"""
import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs


C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3_local')
WORDS = 2048  # bit-packed words per bitmask
N_RO_TRIALS = 2  # Reduced for compute time
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase8c_proper_audit.json')


def state_to_bits(state):
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


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


def compute_full_pearson(state1_bits, f_arr, target_bits, label):
    """For each output bit b, run C binary and compute direct_z + chain_z.

    Returns: Pearson(direct_z, chain_z), same_sign count, raw arrays.
    """
    N = len(f_arr)
    direct_z = np.zeros(256)
    chain_z = np.zeros(256)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        path = tmp.name
    try:
        ts = time.time()
        for b in range(256):
            t_b = target_bits[:, b].copy().astype(np.uint8)
            # direct
            direct_walsh = 1 - 2 * ((f_arr ^ t_b).sum()) / N
            direct_z[b] = direct_walsh * math.sqrt(N)
            # chain via C
            write_input_bin(state1_bits, f_arr, t_b, path)
            res = run_c(path)
            chain_z[b] = res['chain_sum']
            if (b + 1) % 64 == 0:
                el = time.time() - ts
                eta = el / (b + 1) * (256 - b - 1)
                print(f"    [{label}] {b+1}/256  el={el:.0f}s eta={eta:.0f}s")
    finally:
        os.unlink(path)
    omega = float(np.corrcoef(direct_z, chain_z)[0, 1])
    same_sign = int((np.sign(direct_z) == np.sign(chain_z)).sum())
    return omega, same_sign, direct_z, chain_z


def main():
    t0 = time.time()
    print("# Phase 8C v2: proper IT-6 audit using full 256-bit triple chi basis (C binary)")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    pos_arr = np.asarray(pos, dtype=np.int64)
    max_p = pos_arr[:, 1]
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)

    # SHA states
    print("\n## Computing SHA state1, state2...")
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    block = M.view('>u4').reshape(N, 16).astype(ch.U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state1 = ch.compress(state, block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    block2_one = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    block2 = np.broadcast_to(block2_one, (N, 16))
    state2 = ch.compress(state1, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

    state1_bits = state_to_bits(state1)
    state2_bits = state_to_bits(state2)
    print(f"  state1, state2 ready")

    # SHA Pearson
    print("\n## SHA Pearson over 256 bits (full-triple basis):")
    om_sha, ss_sha, dz_sha, cz_sha = compute_full_pearson(
        state1_bits, f_arr, state2_bits, 'SHA')
    print(f"  Ω_3 = {om_sha:+.4f}  same-sign = {ss_sha}/256")
    print(f"  IT-6 reported: 0.9795, 240/256 — match?")

    # RO trials
    print(f"\n## RO trials ({N_RO_TRIALS} BLAKE2b keyed, full 256-bit target):")
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    ro_same_signs = []
    for r in range(N_RO_TRIALS):
        key = nprng.bytes(16)
        target_bytes = np.zeros((N, 32), dtype=np.uint8)
        for i, m in enumerate(inputs):
            target_bytes[i] = np.frombuffer(
                hashlib.blake2b(m, key=key, digest_size=32).digest(),
                dtype=np.uint8)
        target_bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
        om, ss, _, _ = compute_full_pearson(
            state1_bits, f_arr, target_bits, f'RO#{r+1}')
        ro_omegas.append(om)
        ro_same_signs.append(ss)
        print(f"  RO #{r+1}: Ω_3 = {om:+.4f}  same-sign = {ss}/256")

    # Summary
    ro_om_mean = float(np.mean(ro_omegas))
    ro_om_std = float(np.std(ro_omegas, ddof=1))
    z = (om_sha - ro_om_mean) / ro_om_std if ro_om_std > 0 else 0
    print(f"\n## Summary:")
    print(f"  SHA Ω_3 = {om_sha:+.4f}  (IT-6 claimed 0.9795)")
    print(f"  RO mean = {ro_om_mean:+.4f} ± {ro_om_std:.4f}")
    print(f"  z = {z:+.2f}σ")

    print(f"\n## Verdict on IT-6 Ω_3 = +0.98 claim (full-triple basis):")
    if abs(z) > 5:
        print(f"  ✓ IT-6 CLAIM VALID: SHA Ω={om_sha:.3f} significantly different from RO")
    elif abs(om_sha - ro_om_mean) < 0.1:
        print(f"  ✗ IT-6 CLAIM ⊘ROLL: RO gives same Ω_3 ({ro_om_mean:.3f}) as SHA ({om_sha:.3f})")
    else:
        print(f"  ~ PARTIAL: SHA={om_sha:.3f}, RO={ro_om_mean:.3f} ± {ro_om_std:.3f}")

    out = {
        'N': N,
        'sha_omega': float(om_sha),
        'sha_same_sign': int(ss_sha),
        'sha_direct_z': dz_sha.tolist(),
        'sha_chain_z': cz_sha.tolist(),
        'ro_omegas': ro_omegas,
        'ro_same_signs': ro_same_signs,
        'ro_om_mean': ro_om_mean,
        'ro_om_std': ro_om_std,
        'z_score': float(z),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
