"""Phase 8C: Audit IT-6 Ω_3 = +0.98 claim with proper per-target RO null.

IT-6 protocol:
- input X (HW=2, N=130816)
- state1 = SHA-256(X) — full hash output (= block 1 compression result)
- state2_at_r=64 = compression(state1, padding_block, 64 rounds)
- chi_arr = triples from state1 (first 32 bits)
- direct_z[b] = corr(bit5_max, state2[b])
- chain_z[b] = sum_S z_in[S] * z_out[S, b]
- Ω_3 = Pearson(direct_z, chain_z) over 256 output bits

IT-6 reported Ω_3 = +0.98, same_sign = 240/256, p ~ 10⁻⁵²
using per-bit RO null band of 50 single-bit BLAKE2b targets.

Phase 8B-style audit: keep chi_arr from SHA state1, vary target between
SHA state2 (real) and BLAKE2b (RO). Compute Ω_3 and same_sign for each.

If RO Ω_3 ≈ 0 across trials → IT-6 claim is real.
If RO Ω_3 ≈ +0.98 → IT-6 was chi_arr artifact like Phase 7B.
"""
import hashlib, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs, build_chi_arr


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase8c_it6_audit.json')


def sha256_block1(inputs):
    """state1 = SHA-256 compression of input block (with feed-forward)."""
    N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    block = M.view('>u4').reshape(N, 16).astype(ch.U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def sha256_state2_r64(state1):
    """state2 = compression(state1, padding_block) at r=64.

    Padding block for 64-byte message: 0x80, zeros, 64-bit length=512.
    """
    N = state1.shape[0]
    pad_block = np.zeros((N, 16), dtype=ch.U32)
    pad_block[:, 0] = 0x80000000
    # length = 512 bits packed in last two words (high+low 32-bit)
    pad_block[:, 14] = 0
    pad_block[:, 15] = 512
    return ch.compress(state1, pad_block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state, n_bits=256):
    """Pack 8-word state into 256-bit big-endian array."""
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :n_bits]


def compute_omega_and_signs(chi_arr_f32, target_bits, f_pm, sN):
    """Compute Ω_3 and same-sign count given chi_arr, target, feature."""
    target_pm = (target_bits.astype(np.float32) * 2 - 1)
    z_in = (chi_arr_f32 @ f_pm) / sN
    z_out = (chi_arr_f32 @ target_pm) / sN
    chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
    direct_z = (f_pm @ target_pm) / sN
    if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
        return 0.0, 128, direct_z, chain_z
    omega = float(np.corrcoef(direct_z, chain_z)[0, 1])
    same_sign = int((np.sign(direct_z) == np.sign(chain_z)).sum())
    return omega, same_sign, direct_z, chain_z


def main():
    t0 = time.time()
    print("# Phase 8C: IT-6 audit with proper RO null")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    pos_arr = np.asarray(pos, dtype=np.int64)
    max_p = pos_arr[:, 1]
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)  # bit5_max feature (IT-6 default)
    f_pm = (f_arr.astype(np.float32) * 2 - 1)

    # Compute SHA state1 and state2_at_r=64
    print(f"\n## Computing SHA state1 (block 1 output)...")
    state1 = sha256_block1(inputs)
    state1_bits = state_to_bits(state1, 256)
    print(f"  state1 shape: {state1.shape}, first sample: {hex(int(state1[0,0]))}")

    print(f"\n## Computing SHA state2 (after padding block, r=64)...")
    state2 = sha256_state2_r64(state1)
    state2_bits = state_to_bits(state2, 256)

    # chi_arr from state1 first 32 bits
    print(f"\n## Building chi_arr from state1[0..31]...")
    chi_arr, _ = build_chi_arr(state1_bits, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)
    sN = np.float32(np.sqrt(N))
    print(f"  M = {chi_arr.shape[0]} triples")

    # SHA Ω_3
    print(f"\n## SHA target (state2_at_r=64):")
    om_sha, ss_sha, dz_sha, cz_sha = compute_omega_and_signs(
        chi_arr_f32, state2_bits, f_pm, sN)
    print(f"  Ω_3 = {om_sha:+.4f}  same-sign = {ss_sha}/256")
    print(f"  IT-6 claimed: Ω_3 = +0.9795, same-sign = 240/256")

    # RO targets: 10 BLAKE2b realizations
    print(f"\n## RO targets (10 BLAKE2b keyed):")
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    ro_same_signs = []
    for r in range(10):
        key = nprng.bytes(16)
        target_bytes = np.zeros((N, 32), dtype=np.uint8)
        for i, m in enumerate(inputs):
            target_bytes[i] = np.frombuffer(
                hashlib.blake2b(m, key=key, digest_size=32).digest(),
                dtype=np.uint8)
        target_bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
        om, ss, _, _ = compute_omega_and_signs(chi_arr_f32, target_bits, f_pm, sN)
        ro_omegas.append(om)
        ro_same_signs.append(ss)
        print(f"  RO #{r+1}: Ω_3 = {om:+.4f}  same-sign = {ss}/256")

    # Stats
    ro_om_mean = float(np.mean(ro_omegas))
    ro_om_std = float(np.std(ro_omegas, ddof=1))
    ro_ss_mean = float(np.mean(ro_same_signs))
    print(f"\n## RO distribution:")
    print(f"  Ω_3: mean = {ro_om_mean:+.4f} ± {ro_om_std:.4f}")
    print(f"  same-sign: mean = {ro_ss_mean:.1f}/256")

    z_om = (om_sha - ro_om_mean) / ro_om_std if ro_om_std > 0 else 0
    print(f"\n## SHA vs RO:")
    print(f"  SHA Ω_3 = {om_sha:+.4f}")
    print(f"  RO mean Ω_3 = {ro_om_mean:+.4f} ± {ro_om_std:.4f}")
    print(f"  z = {z_om:+.2f}σ")

    print(f"\n## Verdict on IT-6 Ω_3 = +0.98 claim:")
    if abs(z_om) > 5:
        print(f"  ✓ IT-6 CLAIM VALID: SHA distinct from RO (z={z_om:.1f}σ)")
    elif abs(om_sha - ro_om_mean) < 0.1:
        print(f"  ✗ IT-6 CLAIM ⊘ROLL: RO gives same Ω_3 as SHA")
        print(f"    Same chi_arr-target alignment artifact as Phase 7B")
    else:
        print(f"  ~ IT-6 CLAIM PARTIAL: significant but smaller than reported")
        print(f"    Real effect ~{om_sha - ro_om_mean:+.2f} (was reported 0.98)")

    out = {
        'N': N,
        'sha_omega': float(om_sha),
        'sha_same_sign': int(ss_sha),
        'ro_omegas': ro_omegas,
        'ro_same_signs': ro_same_signs,
        'ro_omega_mean': ro_om_mean,
        'ro_omega_std': ro_om_std,
        'ro_same_sign_mean': ro_ss_mean,
        'z_score': float(z_om),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
