"""Phase 7A revised: PCA characterization of Walsh-3 invariant subspace.

For each of 271 Phase 7B features, compute (direct_z[256], chain_z[256])
at r=64 baseline SHA. Stack as matrices, do SVD.

Key questions:
1. Singular value spectrum of direct_z matrix — effective dimension?
2. Do dominant PCs of direct_z align with dominant PCs of chain_z?
3. What simple features best span top PCs?
4. How many dimensions are needed to capture all features with |Ω|>0.7?

Compare with RO baseline: do RO targets give same SVD spectrum, or
does SHA-256 have characteristic spectrum?
"""
import hashlib, json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial
from phase7b_wide_feature_search import make_wide_features


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase7a_pca_subspace.json')


def compute_dz_cz_matrices(features, chi_arr_f32, target_pm, sN):
    """For each feature, compute (direct_z, chain_z) vectors over 256 output bits.

    Returns: D[K, 256] direct_z matrix, C[K, 256] chain_z matrix, names list.
    """
    K = len(features)
    D = np.zeros((K, 256), dtype=np.float32)
    C = np.zeros((K, 256), dtype=np.float32)
    names = list(features.keys())
    z_out = (chi_arr_f32 @ target_pm) / sN  # shape (M, 256)
    for i, name in enumerate(names):
        f_pm = features[name].astype(np.float32) * 2 - 1
        z_in = (chi_arr_f32 @ f_pm) / sN
        chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
        direct_z = (f_pm @ target_pm) / sN
        D[i] = direct_z
        C[i] = chain_z
    return D, C, names


def pca_analysis(M, top_k=10):
    """SVD of M (K × 256). Returns singular values, top-k right singular vectors."""
    # Center each column? No, raw direct_z has no inherent centering.
    U, S, Vt = np.linalg.svd(M, full_matrices=False)
    return U, S, Vt


def main():
    t0 = time.time()
    print("# Phase 7A revised: PCA of Walsh-3 invariant subspace")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    # Build chi_arr from state_r=4
    state_r4 = compress_partial(inputs, 4)
    chi_arr, _ = build_chi_arr(state_r4, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)
    sN = np.float32(np.sqrt(N))

    # Features (filter degenerate)
    features_full = make_wide_features(pos)
    features = {fn: fa for fn, fa in features_full.items()
                if 100 < fa.sum() < N - 100}
    K = len(features)
    print(f"# Features: {K}")

    # SHA-256 r=64
    print(f"\n## SHA-256 r=64 PCA:")
    state_r64 = compress_partial(inputs, 64)
    target_sha = (state_r64.astype(np.float32) * 2 - 1)
    ts = time.time()
    D_sha, C_sha, names = compute_dz_cz_matrices(features, chi_arr_f32, target_sha, sN)
    print(f"  D, C computed: {time.time()-ts:.0f}s")

    U_sha, S_sha, Vt_sha = pca_analysis(D_sha)
    print(f"  D singular values (top 15): {[f'{s:.2f}' for s in S_sha[:15]]}")

    # Cumulative variance
    var_cum = np.cumsum(S_sha**2) / np.sum(S_sha**2)
    rank_99 = int(np.searchsorted(var_cum, 0.99) + 1)
    rank_95 = int(np.searchsorted(var_cum, 0.95) + 1)
    rank_90 = int(np.searchsorted(var_cum, 0.90) + 1)
    print(f"  Effective dim 90% var: {rank_90}, 95%: {rank_95}, 99%: {rank_99}")

    # Same for chain_z
    Uc_sha, Sc_sha, Vct_sha = pca_analysis(C_sha)
    print(f"  C singular values (top 15): {[f'{s:.2f}' for s in Sc_sha[:15]]}")

    # Alignment: top PCs of D vs C
    print(f"\n## Alignment between top D-PCs and C-PCs (cosine similarity):")
    align = np.abs(Vt_sha[:5] @ Vct_sha[:5].T)
    for i in range(5):
        for j in range(5):
            print(f"  D-PC{i+1} · C-PC{j+1}: {align[i,j]:.3f}", end='  ')
        print()

    # Per-feature Ω_3 + projection onto top PCs
    print(f"\n## Top features by |Ω_3|, with PC projection:")
    omegas = []
    for i in range(K):
        if np.std(D_sha[i]) < 1e-10 or np.std(C_sha[i]) < 1e-10:
            omegas.append(0.0); continue
        om = float(np.corrcoef(D_sha[i], C_sha[i])[0, 1])
        omegas.append(om)
    omegas = np.array(omegas)
    order = np.argsort(-np.abs(omegas))
    print(f"  Top 10 features and their projection onto first 3 PCs of D:")
    for i in order[:10]:
        proj = D_sha[i] @ Vt_sha[:3].T  # (3,)
        proj_norm = proj / np.linalg.norm(D_sha[i]) if np.linalg.norm(D_sha[i]) > 0 else proj
        print(f"  {names[i]:22s}: Ω={omegas[i]:+.3f}  "
              f"PC1={proj_norm[0]:+.2f}  PC2={proj_norm[1]:+.2f}  PC3={proj_norm[2]:+.2f}")

    # RO comparison
    print(f"\n## RO baseline (1 BLAKE2b realization) PCA:")
    nprng = np.random.default_rng(0xDEADBEEF)
    key = nprng.bytes(16)
    target_bytes = np.zeros((N, 32), dtype=np.uint8)
    for i, m in enumerate(inputs):
        target_bytes[i] = np.frombuffer(
            hashlib.blake2b(m, key=key, digest_size=32).digest(),
            dtype=np.uint8)
    target_bits = np.unpackbits(target_bytes, axis=1, bitorder='big')[:, :256]
    target_ro = (target_bits.astype(np.float32) * 2 - 1)
    D_ro, C_ro, _ = compute_dz_cz_matrices(features, chi_arr_f32, target_ro, sN)
    U_ro, S_ro, Vt_ro = pca_analysis(D_ro)
    print(f"  D singular values (top 15): {[f'{s:.2f}' for s in S_ro[:15]]}")
    var_cum_ro = np.cumsum(S_ro**2) / np.sum(S_ro**2)
    rank_99_ro = int(np.searchsorted(var_cum_ro, 0.99) + 1)
    rank_95_ro = int(np.searchsorted(var_cum_ro, 0.95) + 1)
    print(f"  RO effective dim 95%: {rank_95_ro}, 99%: {rank_99_ro}")

    Uc_ro, Sc_ro, _ = pca_analysis(C_ro)
    print(f"  C singular values (top 15): {[f'{s:.2f}' for s in Sc_ro[:15]]}")

    # Compare SHA vs RO singular value spectra
    print(f"\n## SHA vs RO singular value RATIOS (D matrix top 10):")
    for i in range(10):
        ratio = S_sha[i] / S_ro[i] if S_ro[i] > 0 else float('inf')
        print(f"  σ_{i+1}: SHA={S_sha[i]:.2f}  RO={S_ro[i]:.2f}  ratio={ratio:.2f}")

    out = {
        'N': N,
        'K_features': K,
        'sha': {
            'singular_values_D': S_sha[:30].tolist(),
            'singular_values_C': Sc_sha[:30].tolist(),
            'rank_95_D': rank_95,
            'rank_99_D': rank_99,
        },
        'ro': {
            'singular_values_D': S_ro[:30].tolist(),
            'singular_values_C': Sc_ro[:30].tolist(),
            'rank_95_D': rank_95_ro,
            'rank_99_D': rank_99_ro,
        },
        'top_features_omega_pc_proj': [
            {'name': names[i], 'omega': float(omegas[i]),
             'pc_projection': (D_sha[i] @ Vt_sha[:3].T).tolist()}
            for i in order[:10]
        ],
        'd_c_alignment_5x5': align.tolist(),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
