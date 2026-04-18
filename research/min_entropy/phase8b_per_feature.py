"""Phase 8B: per-feature SHA vs RO comparison.

Critical check: for SAME feature (pre-committed), is Ω_3 under SHA
distinguishable from RO?

Phase 8A showed RO distributions look like SHA on aggregate (both have
~29 features above 0.7). Need feature-by-feature check:
- For each of 271 features, compute Ω under SHA and under each RO
- If SHA Ω significantly differs from RO mean for most features → real
- If SHA Ω ≈ RO mean for matched features → no structural signal

This is the proper statistical test.
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr
from phase3a_chimera_attribution import compress_partial
from phase7b_wide_feature_search import make_wide_features
from phase8a_distribution import compute_omegas, ro_target


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase8b_per_feature.json')


def main():
    t0 = time.time()
    print("# Phase 8B: per-feature SHA vs RO comparison")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)

    state_r4 = compress_partial(inputs, 4)
    chi_arr_f32 = build_chi_arr(state_r4, k=3, subset_size=32)[0].astype(np.float32)
    sN = np.float32(np.sqrt(N))

    features = {fn: fa for fn, fa in make_wide_features(pos).items()
                if 100 < fa.sum() < N - 100}
    K = len(features)
    print(f"# K = {K} features")

    # SHA
    print(f"\n## SHA-256 r=64:")
    target_sha = (compress_partial(inputs, 64).astype(np.float32) * 2 - 1)
    om_sha = compute_omegas(features, chi_arr_f32, target_sha, sN)

    # RO trials (10 for better stats)
    print(f"\n## RO 10 trials:")
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = {fn: [] for fn in features}
    for r in range(10):
        key = nprng.bytes(16)
        target_ro = ro_target(inputs, N, key)
        om_ro = compute_omegas(features, chi_arr_f32, target_ro, sN)
        for fn in features:
            ro_omegas[fn].append(om_ro[fn])
        print(f"  RO #{r+1} done")

    # Per-feature z-score
    print(f"\n## Per-feature SHA vs RO (z-score):")
    z_scores = {}
    for fn in features:
        sha_v = om_sha[fn]
        ro_vs = np.array(ro_omegas[fn])
        ro_mean = float(ro_vs.mean())
        ro_std = float(ro_vs.std(ddof=1))
        z = (sha_v - ro_mean) / ro_std if ro_std > 0 else 0
        z_scores[fn] = {
            'sha': sha_v,
            'ro_mean': ro_mean,
            'ro_std': ro_std,
            'z': float(z),
        }

    # Top features by |z|
    ranked = sorted(z_scores.items(), key=lambda x: -abs(x[1]['z']))
    print(f"\n## TOP 15 FEATURES BY |z-score|:")
    print(f"{'feature':22s}  {'SHA':>7}  {'RO mean':>7}  {'RO std':>7}  {'z':>7}")
    for fn, info in ranked[:15]:
        print(f"  {fn:22s}  {info['sha']:+.3f}  {info['ro_mean']:+.3f}  "
              f"{info['ro_std']:.3f}  {info['z']:+5.2f}σ")

    # Key question: for min_gt_64 and similar "Phase 7B top" features
    print(f"\n## Phase 7B TOP features (pre-committed, fair comparison):")
    phase7b_top = ['min_gt_64', 'min_in_word2', 'min_in_word1', 'max_in_word0',
                   'max_gt_32', 'max_gt_16', 'min_gt_4', 'max_in_word2',
                   'max_in_word4', 'max_in_word1']
    for fn in phase7b_top:
        if fn in z_scores:
            info = z_scores[fn]
            print(f"  {fn:15s}: SHA={info['sha']:+.3f}  RO mean={info['ro_mean']:+.3f}  "
                  f"RO std={info['ro_std']:.3f}  z={info['z']:+.2f}σ")

    # Summary stats
    abs_zs = [abs(info['z']) for info in z_scores.values()]
    print(f"\n## Overall |z| distribution across {K} features:")
    print(f"  mean|z| = {np.mean(abs_zs):.2f}, median = {np.median(abs_zs):.2f}")
    print(f"  max|z| = {max(abs_zs):.2f}")
    print(f"  features with |z|>3: {sum(1 for z in abs_zs if z > 3)}")
    print(f"  features with |z|>5: {sum(1 for z in abs_zs if z > 5)}")

    # If there's NO consistent SHA-vs-RO difference, |z| should be ~1
    # If structure real, we expect many features with |z|>3
    if sum(1 for z in abs_zs if z > 3) > 20:
        print(f"\n  ✓ Real structural signal: many features show |z|>3")
    else:
        print(f"\n  ✗ No consistent signal: per-feature z distribution ~ null")

    out = {
        'N': N,
        'K': K,
        'sha_omegas': {fn: float(v) for fn, v in om_sha.items()},
        'ro_omegas_per_feature': {fn: [float(x) for x in vs] for fn, vs in ro_omegas.items()},
        'z_scores': z_scores,
        'abs_z_stats': {
            'mean': float(np.mean(abs_zs)),
            'median': float(np.median(abs_zs)),
            'max': float(max(abs_zs)),
            'count_gt_3': int(sum(1 for z in abs_zs if z > 3)),
            'count_gt_5': int(sum(1 for z in abs_zs if z > 5)),
        },
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
