"""Phase 7A: analytical derivation of optimal Ω_3 feature.

Problem: Ω_3(f) = Pearson(direct_z[b], chain_z[b]) over output bits b.
  direct_z[b] = √N · ⟨σ(f), σ(state_r64[b])⟩ = (f_pm @ state_r64_pm)[b] / √N
  chain_z[b] = fixed (computed from state_r4 triples)

For Ω_3 to be maximized, direct_z[b] should be ∝ chain_z[b] (up to constant).

Optimal: direct_z[b] = c · chain_z[b] for some c > 0.
This means f_pm @ state_r64_pm[:, b] ∝ chain_z[b] for all b.

In matrix form: f_pm @ M = c · chain_z, where M = state_r64_pm (N × 256).
Solution: f_pm = c · chain_z @ M^T / (M @ M^T)_reg

For ±1-valued f, we threshold: f = sign(c · chain_z @ M^T).

Then measure Ω_3 for this analytical feature. If |Ω_3| > 0.82 (Phase 7B
floor), we've found the subspace maximum and characterized invariant.
Decompose the analytical feature into bit-patterns to find basis.
"""
import hashlib, json, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase7a_optimal_feature.json')


def compute_chain_z(chi_arr_f32, target_pm, sN):
    """chain_z[b] = Σ_S z_S(triple_input) · z_S(target[b]) / √N."""
    # chi_arr: (M_triples, N), target_pm: (N, 256)
    # z_out_matrix[S, b] = chi_arr @ target_pm / √N → (M, 256)
    z_out = (chi_arr_f32 @ target_pm) / sN
    # chain_z per b sums over S weighted by z_in[S]
    # but z_in depends on feature — we want the "target" vector
    # Actually Ω_3 = Pearson(direct_z, chain_z) — they're BOTH vectors over b
    # chain_z[b] = (z_in · z_out_matrix[:, b]) / √N = Σ_S z_in[S] · z_out[S, b] / √N
    # But this requires z_in which depends on feature. Let me reconsider.
    return z_out  # return z_out matrix


def optimal_feature(chi_arr_f32, state_r64_pm, seed_feature_pm, sN):
    """Given a seed feature, iteratively improve toward maximum Ω_3.

    Uses gradient-descent-like update:
      Given feature f, compute direct_z[b] = f_pm @ state_r64_pm / √N
      Compute chain_z[b] = z_in · z_out / √N where z_in = chi_arr @ f_pm
      Ω_3 = corr(direct_z, chain_z)
      Gradient: ∂Ω_3/∂f_i ∝ correlation of f_i with (direct_z - chain_z)_b structure
      Simpler: greedy bit-flip ascent.
    """
    N, D = state_r64_pm.shape

    def omega(f_pm):
        z_in = (chi_arr_f32 @ f_pm) / sN
        z_out = (chi_arr_f32 @ state_r64_pm) / sN
        chain_z = (z_in[:, None] * z_out).sum(axis=0) / sN
        direct_z = (f_pm @ state_r64_pm) / sN
        if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
            return 0.0, direct_z, chain_z
        om = float(np.corrcoef(direct_z, chain_z)[0, 1])
        return om, direct_z, chain_z

    # Try analytical approach: direct_z ∝ chain_z means
    # f_pm @ M = c · chain_z → f_pm = c · chain_z @ (M @ M^T)^(-1) @ M ?
    # But M is N×256, not square. Use pseudo-inverse:
    # We want direct_z[b] = c · chain_z[b]
    # direct_z = f_pm @ M
    # Best f_pm (in L2 sense): f_pm = c · chain_z @ M^T / ||M||²
    # But f_pm must be ±1 valued → threshold.

    om_current, dz, cz = omega(seed_feature_pm)
    print(f"  seed Ω_3 = {om_current:+.4f}")

    # One-shot analytical estimate
    # Compute CURRENT chain_z (depends on current feature but approximately stable)
    # For best f given chain_z:
    target_scalar = state_r64_pm @ cz  # (N,) — real-valued target
    f_opt = np.sign(target_scalar).astype(np.float32)
    f_opt[f_opt == 0] = 1.0  # handle zeros
    om_opt, dz_opt, cz_opt = omega(f_opt)
    print(f"  one-shot analytical Ω_3 = {om_opt:+.4f}")

    # Iterate: recompute chain_z with updated feature, re-derive
    best_f = f_opt.copy()
    best_om = om_opt
    for it in range(10):
        # Use cz from current best
        _, _, cz = omega(best_f)
        target_scalar = state_r64_pm @ cz
        f_new = np.sign(target_scalar).astype(np.float32)
        f_new[f_new == 0] = 1.0
        # Also try inverted
        om_new, _, _ = omega(f_new)
        om_new_inv, _, _ = omega(-f_new)
        if om_new_inv > om_new:
            f_new, om_new = -f_new, om_new_inv
        if abs(om_new) > abs(best_om):
            best_f = f_new.copy()
            best_om = om_new
            print(f"  iter {it}: Ω_3 = {om_new:+.4f}")
        else:
            break
    print(f"  final Ω_3 = {best_om:+.4f}")
    return best_f, best_om


def decompose_feature(f_binary, pos):
    """Try to express feature in terms of bit-position predicates.

    Check correlation with various candidate basis features. If some
    weighted sum of simple features explains f, report that basis.
    """
    pos_arr = np.asarray(pos, dtype=np.int64)
    min_p = pos_arr[:, 0]
    max_p = pos_arr[:, 1]

    # Build basis: 16 min_in_word_i + 16 max_in_word_i + single bits
    basis = []
    names = []
    for i in range(16):
        basis.append((min_p >> 5 == i).astype(np.float32) * 2 - 1)
        names.append(f'min_word{i}')
        basis.append((max_p >> 5 == i).astype(np.float32) * 2 - 1)
        names.append(f'max_word{i}')

    # Linear regression: f ≈ Σ α_i · basis[i]
    B = np.array(basis).T  # (N, n_basis)
    f_float = f_binary.astype(np.float32)
    coef, residuals, rank, _ = np.linalg.lstsq(B, f_float, rcond=None)

    # R² fit quality
    pred = B @ coef
    ss_res = np.sum((f_float - pred) ** 2)
    ss_tot = np.sum((f_float - f_float.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    print(f"\n  basis regression: R² = {r2:.4f}, basis size = {len(basis)}")

    # Top coefficients
    order = np.argsort(-np.abs(coef))
    print(f"  Top 10 coefficients:")
    for i in order[:10]:
        print(f"    {names[i]:15s}: {coef[i]:+.4f}")
    return {'r2': float(r2), 'coeffs': {names[i]: float(coef[i]) for i in order[:20]}}


def main():
    t0 = time.time()
    print("# Phase 7A: analytical derivation of optimal Ω_3 feature")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    # States
    print(f"\n## Computing states r=4 (chi) and r=64 (target)...")
    state_r4 = compress_partial(inputs, 4)
    state_r64 = compress_partial(inputs, 64)

    # χ_S basis
    chi_arr, _ = build_chi_arr(state_r4, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)
    sN = np.float32(np.sqrt(N))
    state_r64_pm = (state_r64.astype(np.float32) * 2 - 1)
    print(f"  chi_arr: {chi_arr.shape}, target: {state_r64_pm.shape}")

    # Seed with best known feature: min_gt_64
    pos_arr = np.asarray(pos, dtype=np.int64)
    min_p = pos_arr[:, 0]
    f_seed = ((min_p > 64).astype(np.float32)) * 2 - 1

    print(f"\n## Analytical optimization from seed 'min_gt_64':")
    f_opt, om_opt = optimal_feature(chi_arr_f32, state_r64_pm, f_seed, sN)

    # Decompose optimal feature
    print(f"\n## Decomposing optimal feature into position-basis:")
    f_binary = ((f_opt + 1) / 2).astype(np.uint8)
    decomp = decompose_feature(f_binary, pos)

    # RO null compare
    ro_null_mean = 0.053
    ro_null_std = 0.074
    z = (om_opt - ro_null_mean) / ro_null_std if ro_null_std else 0
    print(f"\n## Optimal Ω_3 vs RO null:")
    print(f"  Ω_3 = {om_opt:+.4f}, z = {z:+.2f}σ")
    print(f"  Phase 7B asymptote was 0.82; optimal gives {abs(om_opt):.4f}")

    # Quick secondary search: try several seeds to see if different optima exist
    print(f"\n## Test secondary seeds (check for multiple optima):")
    seeds = {
        'max_in_word0': ((np.asarray([p[1] for p in pos]) >> 5) == 0).astype(np.float32) * 2 - 1,
        'max_gt_32':    (np.asarray([p[1] for p in pos]) > 32).astype(np.float32) * 2 - 1,
        'bit8_max':     ((np.asarray([p[1] for p in pos]) >> 8) & 1).astype(np.float32) * 2 - 1,
        'bit5_max':     ((np.asarray([p[1] for p in pos]) >> 5) & 1).astype(np.float32) * 2 - 1,
    }
    secondary = {}
    for name, seed in seeds.items():
        print(f"\n  From seed '{name}':")
        _, om = optimal_feature(chi_arr_f32, state_r64_pm, seed, sN)
        secondary[name] = om
    print(f"\n  Summary of optima reached: {secondary}")

    out = {
        'N': N,
        'primary_seed': 'min_gt_64',
        'optimal_omega_3': float(om_opt),
        'z_vs_ro': float(z),
        'decomposition': decomp,
        'secondary_seeds': secondary,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
