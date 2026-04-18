"""Phase 7A sanity check: does optimal-feature derivation overfit RO too?

The Phase 7A optimal feature achieved Ω_3 = 0.9986 at r=64 for SHA-256.
The feature was derived BY FITTING to the specific output values.

Critical question: if we apply the same fitting procedure to a RANDOM
ORACLE (BLAKE2b keyed), does it also achieve Ω ~ 1? If yes, the high
Ω is an artifact of fitting capacity, not SHA-256 structure.

Test: use 10 different RO realizations, derive optimal feature for each,
record Ω_3. Compare with SHA-256 Ω = 0.9986.
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase7a_overfit_check.json')


def optimal_feature_omega(chi_arr_f32, target_pm, sN, seed_pm, verbose=False):
    """Analytical optimal feature derivation, returns final Ω_3."""
    def omega(f_pm):
        z_in = (chi_arr_f32 @ f_pm) / sN
        z_out = (chi_arr_f32 @ target_pm) / sN
        chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
        direct_z = (f_pm @ target_pm) / sN
        if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
            return 0.0, direct_z, chain_z
        om = float(np.corrcoef(direct_z, chain_z)[0, 1])
        return om, direct_z, chain_z

    _, _, cz = omega(seed_pm)
    # One-shot
    target_scalar = target_pm @ cz
    f_opt = np.sign(target_scalar).astype(np.float32)
    f_opt[f_opt == 0] = 1.0
    om_opt, _, _ = omega(f_opt)
    if verbose:
        print(f"    one-shot Ω = {om_opt:+.4f}")
    # Iterate
    best_f = f_opt; best_om = om_opt
    for it in range(5):
        _, _, cz = omega(best_f)
        target_scalar = target_pm @ cz
        f_new = np.sign(target_scalar).astype(np.float32)
        f_new[f_new == 0] = 1.0
        om_new, _, _ = omega(f_new)
        om_new_inv, _, _ = omega(-f_new)
        if om_new_inv > om_new:
            f_new, om_new = -f_new, om_new_inv
        if abs(om_new) > abs(best_om):
            best_f = f_new; best_om = om_new
        else:
            break
    return best_om


def main():
    t0 = time.time()
    print("# Phase 7A overfit check: does procedure also give Ω~1 on RO?")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    # Shared chi_arr from SHA state r=4
    print(f"\n## Building chi_arr (SHA state r=4)...")
    state_r4 = compress_partial(inputs, 4)
    chi_arr, _ = build_chi_arr(state_r4, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)
    sN = np.float32(np.sqrt(N))

    # Seed: bit5_max (known weak feature)
    pos_arr = np.asarray(pos, dtype=np.int64)
    max_p = pos_arr[:, 1]
    f_seed = ((max_p >> 5) & 1).astype(np.float32) * 2 - 1

    # Reference: SHA-256 full
    print(f"\n## SHA-256 reference:")
    state_r64 = compress_partial(inputs, 64)
    sha_target_pm = (state_r64.astype(np.float32) * 2 - 1)
    om_sha = optimal_feature_omega(chi_arr_f32, sha_target_pm, sN, f_seed, verbose=True)
    print(f"  SHA-256: Ω_3 = {om_sha:+.4f}")

    # RO baselines: 10 keyed BLAKE2b
    print(f"\n## RO trials (10 BLAKE2b keyed):")
    ts = time.time()
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    for r in range(10):
        key = nprng.bytes(16)
        target_bytes = np.zeros((N, 32), dtype=np.uint8)
        for i, m in enumerate(inputs):
            target_bytes[i] = np.frombuffer(
                hashlib.blake2b(m, key=key, digest_size=32).digest(),
                dtype=np.uint8)
        target_bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
        target_pm = (target_bits.astype(np.float32) * 2 - 1)
        om = optimal_feature_omega(chi_arr_f32, target_pm, sN, f_seed)
        ro_omegas.append(om)
        print(f"  RO #{r+1}: Ω_3 = {om:+.4f}  ({time.time()-ts:.0f}s)")

    ro_mean = float(np.mean(ro_omegas))
    ro_std = float(np.std(ro_omegas, ddof=1))
    ro_max = max(abs(x) for x in ro_omegas)
    print(f"\n## RO optimal-Ω distribution:")
    print(f"  mean = {ro_mean:+.4f}, std = {ro_std:.4f}, max|Ω| = {ro_max:.4f}")

    z = (abs(om_sha) - abs(ro_mean)) / ro_std if ro_std > 0 else 0
    print(f"\n## SHA-256 vs RO (post-overfit):")
    print(f"  SHA-256 optimal Ω = {abs(om_sha):.4f}")
    print(f"  RO optimal Ω mean = {abs(ro_mean):.4f} ± {ro_std:.4f}")
    print(f"  z = {z:+.2f}σ")

    if ro_max > 0.9:
        print(f"\n  ✗ OVERFITTING: RO optimization also reaches high Ω")
        print(f"    Ω=0.9986 for SHA is artifact of fitting, not structural")
    elif abs(om_sha) - ro_max > 0.3:
        print(f"\n  ✓ REAL DISTINGUISHER: SHA clearly separates from RO post-overfit")
        print(f"    Procedure is biased but not enough to explain SHA Ω=0.9986")
    else:
        print(f"\n  ~ Marginal: need more trials to distinguish")

    out = {
        'N': N,
        'sha_omega': float(om_sha),
        'ro_omegas': ro_omegas,
        'ro_mean': ro_mean,
        'ro_std': ro_std,
        'ro_max_abs': ro_max,
        'z_score': float(z),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
