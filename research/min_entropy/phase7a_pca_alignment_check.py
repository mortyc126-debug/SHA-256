"""Phase 7A check: is SHA-256's high D-PC1·C-PC1=0.81 alignment specific?

If RO targets give similar alignment, the "1-D invariant subspace" claim
is overinterpretation — it's just a feature-space artifact.

If RO gives much lower alignment, the SHA-256 structure is real.
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr
from phase3a_chimera_attribution import compress_partial
from phase7b_wide_feature_search import make_wide_features
from phase7a_pca_subspace import compute_dz_cz_matrices, pca_analysis


def alignment_5x5(D, C):
    Vt_D = pca_analysis(D)[2]
    Vt_C = pca_analysis(C)[2]
    return np.abs(Vt_D[:5] @ Vt_C[:5].T)


def main():
    t0 = time.time()
    print("# Phase 7A: D-C alignment for SHA vs RO")
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
    D_sha, C_sha, _ = compute_dz_cz_matrices(features, chi_arr_f32, target_sha, sN)
    align_sha = alignment_5x5(D_sha, C_sha)
    print(f"  D-PC1 · C-PC1 = {align_sha[0,0]:.3f}")
    print(f"  Top of D-PC1 alignment row: {[f'{a:.2f}' for a in align_sha[0]]}")

    # RO trials
    print(f"\n## RO trials (5 BLAKE2b keyed):")
    nprng = np.random.default_rng(0xCAFEBABE)
    ro_aligns = []
    for r in range(5):
        key = nprng.bytes(16)
        target_bytes = np.zeros((N, 32), dtype=np.uint8)
        for i, m in enumerate(inputs):
            target_bytes[i] = np.frombuffer(
                hashlib.blake2b(m, key=key, digest_size=32).digest(),
                dtype=np.uint8)
        target_bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
        target_ro = (target_bits.astype(np.float32) * 2 - 1)
        D_ro, C_ro, _ = compute_dz_cz_matrices(features, chi_arr_f32, target_ro, sN)
        align_ro = alignment_5x5(D_ro, C_ro)
        ro_aligns.append(align_ro)
        print(f"  RO #{r+1}: D-PC1·C-PC1 = {align_ro[0,0]:.3f}, "
              f"top row: {[f'{a:.2f}' for a in align_ro[0]]}")

    # Aggregate stats
    ro_d1c1 = [a[0,0] for a in ro_aligns]
    print(f"\n## RO D-PC1·C-PC1 distribution:")
    print(f"  values: {[f'{v:.3f}' for v in ro_d1c1]}")
    print(f"  mean = {np.mean(ro_d1c1):.3f}, std = {np.std(ro_d1c1, ddof=1):.3f}")
    print(f"  max = {max(ro_d1c1):.3f}")

    print(f"\n## Verdict:")
    sha_val = align_sha[0,0]
    ro_max = max(ro_d1c1)
    if sha_val > ro_max + 0.1:
        print(f"  ✓ SHA D-PC1·C-PC1 = {sha_val:.3f}")
        print(f"    RO max = {ro_max:.3f}")
        print(f"  ALIGNMENT IS SHA-SPECIFIC — invariant subspace structure real")
    else:
        print(f"  ✗ SHA = {sha_val:.3f}, RO max = {ro_max:.3f}")
        print(f"  No significant SHA-RO difference in alignment")

    out = {
        'N': N,
        'K': K,
        'sha_alignment_5x5': align_sha.tolist(),
        'ro_alignments_5x5': [a.tolist() for a in ro_aligns],
        'sha_d1_c1': float(sha_val),
        'ro_d1_c1_values': ro_d1c1,
        'ro_d1_c1_mean': float(np.mean(ro_d1c1)),
        'ro_d1_c1_max': float(max(ro_d1c1)),
        'runtime_sec': time.time() - t0,
    }
    out_json = '/home/user/SHA-256/research/min_entropy/phase7a_pca_alignment_check.json'
    with open(out_json, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {out_json}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
