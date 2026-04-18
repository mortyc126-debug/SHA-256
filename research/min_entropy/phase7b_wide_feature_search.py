"""Phase 7B: wide feature search — can we find Ω_3 → 1.0 features?

Phase 6C found bit8_max gives Ω_3 = +0.576 at r=64 (z=7.1σ vs RO).
Question: are there features with |Ω_3| > 0.7, or even ~1.0?

Search ~250 candidate features:
- All single bits of max/min/xor/gap/sum (9 each)
- Pairwise XOR combinations
- Modular position features (p mod 8/16/32)
- Threshold predicates (max > 2^k)
- 2-bit AND/OR of position bits
- Range predicates

Goal: find feature(s) with max |Ω_3(r=64)| — Phase 7A will then
characterize their structure analytically.
"""
import json, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase7b_wide_search.json')


def make_wide_features(pos):
    """~250 candidate features."""
    pos_arr = np.asarray(pos, dtype=np.int64)
    min_p = pos_arr[:, 0]
    max_p = pos_arr[:, 1]
    gap = max_p - min_p
    sum_p = max_p + min_p
    diff_p = max_p - min_p
    xor_p = max_p ^ min_p
    and_p = max_p & min_p
    or_p = max_p | min_p

    features = {}
    # Single bits of various position derivatives
    for x in range(9):
        features[f'bit{x}_max'] = ((max_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_min'] = ((min_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_xor'] = ((xor_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_and'] = ((and_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_or'] = ((or_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_sum'] = ((sum_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_diff'] = ((diff_p >> x) & 1).astype(np.uint8)
        features[f'bit{x}_gap'] = ((gap >> x) & 1).astype(np.uint8)

    # Pairwise XOR of bits within max position
    for x, y in combinations(range(9), 2):
        features[f'maxbit{x}xor{y}'] = (
            ((max_p >> x) ^ (max_p >> y)) & 1).astype(np.uint8)

    # Pairwise XOR of bits within min position
    for x, y in combinations(range(9), 2):
        features[f'minbit{x}xor{y}'] = (
            ((min_p >> x) ^ (min_p >> y)) & 1).astype(np.uint8)

    # max XOR min on pairs of bits
    for x, y in combinations(range(9), 2):
        features[f'xorbit{x}xor{y}'] = (
            ((xor_p >> x) ^ (xor_p >> y)) & 1).astype(np.uint8)

    # Modular features
    for mod in [8, 16, 32, 64]:
        for x in range(min(int(np.log2(mod)), 6)):
            features[f'max_mod{mod}_bit{x}'] = (
                ((max_p % mod) >> x) & 1).astype(np.uint8)
            features[f'min_mod{mod}_bit{x}'] = (
                ((min_p % mod) >> x) & 1).astype(np.uint8)

    # Threshold predicates
    for x in range(2, 9):
        features[f'max_gt_{2**x}'] = (max_p > 2**x).astype(np.uint8)
        features[f'min_gt_{2**x}'] = (min_p > 2**x).astype(np.uint8)
        features[f'gap_gt_{2**x}'] = (gap > 2**x).astype(np.uint8)

    # Range predicates
    features['both_lo'] = ((max_p < 256) & (min_p < 128)).astype(np.uint8)
    features['both_hi'] = ((max_p >= 256) & (min_p >= 128)).astype(np.uint8)
    features['gap_small'] = (gap < 64).astype(np.uint8)
    features['gap_large'] = (gap > 256).astype(np.uint8)

    # Word-level (32-bit groups)
    for w in range(16):
        features[f'max_in_word{w}'] = ((max_p >> 5) == w).astype(np.uint8)
        features[f'min_in_word{w}'] = ((min_p >> 5) == w).astype(np.uint8)

    return features


def main():
    t0 = time.time()
    print("# Phase 7B: wide feature search for max |Ω_3| at r=64")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    features = make_wide_features(pos)
    # Filter degenerate features (constant or near-constant)
    valid = {fn: fa for fn, fa in features.items()
             if 100 < fa.sum() < N - 100}
    print(f"# Total features: {len(features)}, valid (non-degenerate): {len(valid)}")

    # Compute baseline states once
    print(f"\n## Computing baseline states at r ∈ {{4, 24, 64}}...")
    state_r4 = compress_partial(inputs, 4)
    state_r24 = compress_partial(inputs, 24)
    state_r64 = compress_partial(inputs, 64)
    print(f"  done")

    # χ_S basis from r=4
    print(f"\n## Building χ_S basis (k=3, subset=32)...")
    ts = time.time()
    chi_arr, _ = build_chi_arr(state_r4, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)
    print(f"  M={chi_arr.shape[0]} triples ({time.time()-ts:.0f}s)")

    # Pre-cast targets
    ts = time.time()
    target_r24_pm = (state_r24.astype(np.float32) * 2 - 1)
    target_r64_pm = (state_r64.astype(np.float32) * 2 - 1)
    sN = np.float32(np.sqrt(N))
    z_out_r24 = (chi_arr_f32 @ target_r24_pm) / sN
    z_out_r64 = (chi_arr_f32 @ target_r64_pm) / sN
    direct_z_r24 = target_r24_pm  # need to multiply by feature later
    direct_z_r64 = target_r64_pm
    print(f"  precompute: {time.time()-ts:.0f}s")

    # Fast omega computation
    def fast_omega(f_arr, z_out, target_pm):
        f_pm = f_arr.astype(np.float32) * 2 - 1
        z_in = (chi_arr_f32 @ f_pm) / sN
        chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
        direct_z = (f_pm @ target_pm) / sN
        if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
            return 0.0
        return float(np.corrcoef(direct_z, chain_z)[0, 1])

    # Scan all features at r=24 and r=64
    print(f"\n## Scanning {len(valid)} features at r=24 and r=64...")
    ts = time.time()
    results = {}
    for i, (fname, fa) in enumerate(valid.items()):
        omega_24 = fast_omega(fa, z_out_r24, target_r24_pm)
        omega_64 = fast_omega(fa, z_out_r64, target_r64_pm)
        results[fname] = {'r24': omega_24, 'r64': omega_64}
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(valid)} ({time.time()-ts:.0f}s)")
    print(f"  done ({time.time()-ts:.0f}s)")

    # Top features by |Ω_3| at r=64
    ranked = sorted(results.items(), key=lambda x: -abs(x[1]['r64']))

    print(f"\n=== TOP 25 FEATURES BY |Ω_3(r=64)| ===")
    print(f"{'feature':22s}  {'Ω_24':>8}  {'Ω_64':>8}  {'persistence':>12}")
    for fname, om in ranked[:25]:
        pers = abs(om['r64']) / max(abs(om['r24']), 1e-3)
        print(f"  {fname:22s}  {om['r24']:>+8.4f}  {om['r64']:>+8.4f}  {pers:>12.2f}")

    # Find features with |Ω_3| > 0.6 at r=64
    very_strong = [r for r in ranked if abs(r[1]['r64']) > 0.6]
    print(f"\n## Features with |Ω_3(r=64)| > 0.6: {len(very_strong)}")

    # Find features with |Ω_3| > 0.7
    extra_strong = [r for r in ranked if abs(r[1]['r64']) > 0.7]
    print(f"## Features with |Ω_3(r=64)| > 0.7: {len(extra_strong)}")

    near_perfect = [r for r in ranked if abs(r[1]['r64']) > 0.9]
    print(f"## Features with |Ω_3(r=64)| > 0.9 (near-perfect): {len(near_perfect)}")

    if extra_strong:
        print(f"\n## Stronger than Phase 6C bit8_max (0.576):")
        for fname, om in extra_strong[:10]:
            print(f"  {fname:22s}: r64 = {om['r64']:+.4f}")

    out = {
        'N': N,
        'n_features_tested': len(valid),
        'top_25_by_r64': [{'feature': fn, 'omega_r24': om['r24'], 'omega_r64': om['r64']}
                          for fn, om in ranked[:25]],
        'all_results': {fn: om for fn, om in results.items()
                        if abs(om['r64']) > 0.3},
        'count_above_06': len(very_strong),
        'count_above_07': len(extra_strong),
        'count_above_09': len(near_perfect),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
