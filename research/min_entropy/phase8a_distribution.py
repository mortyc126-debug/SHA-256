"""Phase 8A: Ω_3 distribution — SHA-256 vs RO across 271 features.

Clean statistical characterization of the distinguishing power:
- Compute Ω_3(r=64) for each of 271 features, SHA-256 and 5 RO trials
- Histogram of |Ω| values per source
- Count features above various thresholds
- Compare: how many SHA features exceed any RO feature's max

Provides: clean baseline for published distinguisher claim.
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr
from phase3a_chimera_attribution import compress_partial
from phase7b_wide_feature_search import make_wide_features


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase8a_distribution.json')


def compute_omegas(features, chi_arr_f32, target_pm, sN):
    """Compute Ω_3 for all features. Returns dict name → float."""
    K = len(features)
    z_out = (chi_arr_f32 @ target_pm) / sN
    names = list(features.keys())
    omegas = {}
    for name in names:
        f_pm = features[name].astype(np.float32) * 2 - 1
        z_in = (chi_arr_f32 @ f_pm) / sN
        chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
        direct_z = (f_pm @ target_pm) / sN
        if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
            omegas[name] = 0.0
        else:
            omegas[name] = float(np.corrcoef(direct_z, chain_z)[0, 1])
    return omegas


def ro_target(inputs, N, key):
    target_bytes = np.zeros((N, 32), dtype=np.uint8)
    for i, m in enumerate(inputs):
        target_bytes[i] = np.frombuffer(
            hashlib.blake2b(m, key=key, digest_size=32).digest(),
            dtype=np.uint8)
    bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
    return (bits.astype(np.float32) * 2 - 1)


def histogram_summary(vals, thresholds=(0.1, 0.2, 0.3, 0.5, 0.7, 0.8)):
    """Count |val| above each threshold."""
    abs_vals = np.abs(vals)
    return {f'>{t:.1f}': int((abs_vals > t).sum()) for t in thresholds}


def main():
    t0 = time.time()
    print("# Phase 8A: Ω_3 distribution SHA vs RO")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)

    state_r4 = compress_partial(inputs, 4)
    chi_arr_f32 = build_chi_arr(state_r4, k=3, subset_size=32)[0].astype(np.float32)
    sN = np.float32(np.sqrt(N))

    features = {fn: fa for fn, fa in make_wide_features(pos).items()
                if 100 < fa.sum() < N - 100}
    K = len(features)
    print(f"# K = {K} features")

    # SHA-256 r=64
    print(f"\n## SHA-256 r=64 Ω_3 distribution:")
    target_sha = (compress_partial(inputs, 64).astype(np.float32) * 2 - 1)
    om_sha = compute_omegas(features, chi_arr_f32, target_sha, sN)
    sha_vals = np.array(list(om_sha.values()))
    print(f"  mean = {sha_vals.mean():+.3f}, std = {sha_vals.std():.3f}")
    print(f"  mean|Ω| = {np.abs(sha_vals).mean():.3f}, max|Ω| = {np.abs(sha_vals).max():.3f}")
    print(f"  counts above thresh: {histogram_summary(sha_vals)}")

    # 5 RO trials
    print(f"\n## RO distributions (5 trials):")
    nprng = np.random.default_rng(0xBADF00D)
    ro_summaries = []
    ro_all_vals = []
    for r in range(5):
        key = nprng.bytes(16)
        target_ro = ro_target(inputs, N, key)
        om_ro = compute_omegas(features, chi_arr_f32, target_ro, sN)
        ro_vals = np.array(list(om_ro.values()))
        ro_all_vals.extend(ro_vals.tolist())
        summary = {
            'mean': float(ro_vals.mean()),
            'std': float(ro_vals.std()),
            'mean_abs': float(np.abs(ro_vals).mean()),
            'max_abs': float(np.abs(ro_vals).max()),
            'counts': histogram_summary(ro_vals),
        }
        ro_summaries.append(summary)
        print(f"  RO #{r+1}: max|Ω| = {summary['max_abs']:.3f}, counts = {summary['counts']}")

    # Aggregate RO stats
    ro_all_vals = np.array(ro_all_vals)
    ro_max_abs_aggregate = np.abs(ro_all_vals).max()
    ro_median_abs = float(np.median(np.abs(ro_all_vals)))

    # Discrimination count: SHA features above max RO
    sha_above_ro_max = int((np.abs(sha_vals) > ro_max_abs_aggregate).sum())
    sha_above_3x_ro = int((np.abs(sha_vals) > 3 * ro_median_abs).sum())

    print(f"\n## Aggregate RO (5 × 271 = 1355 values):")
    print(f"  mean|Ω| = {np.abs(ro_all_vals).mean():.3f}")
    print(f"  median|Ω| = {ro_median_abs:.3f}")
    print(f"  max|Ω| (across all 1355) = {ro_max_abs_aggregate:.3f}")

    print(f"\n## Discrimination:")
    print(f"  SHA features with |Ω| > max_RO ({ro_max_abs_aggregate:.3f}): {sha_above_ro_max}/{K}")
    print(f"  SHA features with |Ω| > 3·median_RO ({3*ro_median_abs:.3f}): {sha_above_3x_ro}/{K}")

    # Top SHA feature z-score vs RO
    top_sha = max(abs(v) for v in sha_vals)
    ro_mean_abs = float(np.abs(ro_all_vals).mean())
    ro_std_abs = float(np.abs(ro_all_vals).std())
    z = (top_sha - ro_mean_abs) / ro_std_abs if ro_std_abs > 0 else 0
    print(f"\n## Top SHA feature vs RO pool:")
    print(f"  Top SHA |Ω| = {top_sha:.3f}")
    print(f"  RO pool: mean|Ω| = {ro_mean_abs:.3f}, std|Ω| = {ro_std_abs:.3f}")
    print(f"  z-score: {z:+.2f}σ")

    # Save
    out = {
        'N': N,
        'K_features': K,
        'sha_omegas': {k: float(v) for k, v in om_sha.items()},
        'sha_stats': {
            'mean': float(sha_vals.mean()),
            'std': float(sha_vals.std()),
            'mean_abs': float(np.abs(sha_vals).mean()),
            'max_abs': float(np.abs(sha_vals).max()),
            'counts': histogram_summary(sha_vals),
        },
        'ro_summaries': ro_summaries,
        'ro_aggregate': {
            'mean_abs': ro_mean_abs,
            'std_abs': ro_std_abs,
            'median_abs': ro_median_abs,
            'max_abs': float(ro_max_abs_aggregate),
        },
        'sha_features_above_ro_max': sha_above_ro_max,
        'z_top_sha_vs_ro': float(z),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
