"""Phase 4B: test hypothesis that PURE linear Σ compression preserves Ω_3.

Add variant V_sigma_only: only Σ0/Σ1 kept (nonlinear), everything else
linearized (Ch/Maj → XOR, + → XOR, K still present but it's linear).

If Ω_3 stays high for all r → confirms linear model preserves 3rd-order
correlations, and real SHA's Ω_3 collapse is driven by nonlinearity
(Ch/Maj/carry) ON TOP of Σ mixing, not Σ alone.

Contrast with Phase 3A V_all_linear (no_Sigma + linear_ChMaj + no_carry)
which collapsed at r=32 — without Σ rotations state bits don't MIX.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase4b_sigma_only.json')

ROUNDS = [4, 8, 12, 16, 20, 24, 32, 48, 64]


def main():
    t0 = time.time()
    print("# Phase 4B: Σ-only (pure linear) Ω_3 evolution")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N = {N}, k=3")

    # V_sigma_only: keep Σ, linearize everything else
    # This is the Phase 4A matrix applied to real inputs
    flags = dict(no_Sigma=False, linear_chmaj=True, no_carry=True, no_K=False)
    print(f"# V_sigma_only flags: {flags}")

    # chi_S basis at r=4
    state_chi = compress_partial(inputs, 4, **flags)
    chi_arr, _ = build_chi_arr(state_chi, k=3, subset_size=32)

    results = []
    for r in ROUNDS:
        ts = time.time()
        target_bits = compress_partial(inputs, r, **flags)
        omega, ss, _, _, _ = omega_k_fast(chi_arr, target_bits, fa)
        results.append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        print(f"  r={r:>2}: Ω_3 = {omega:+.4f}  ss={ss:>3}/256  ({time.time()-ts:.0f}s)")

    # Analysis
    max_omega = max(e['omega'] for e in results)
    min_omega = min(e['omega'] for e in results)
    print(f"\n## Range: min={min_omega:+.4f}  max={max_omega:+.4f}")
    if min_omega > 0.8:
        print(f"  ✓ Ω_3 preserved under Σ-only linear dynamics (as predicted)")
        print(f"    → Real-SHA collapse driven by NONLINEARITY on top of Σ mixing")
    else:
        print(f"  ✗ Ω_3 also decays in pure Σ model (unexpected)")

    # Cross-reference with Phase 3A variants for triangulation
    print(f"\n## Cross-reference (Phase 3A Ω_3 at r=24):")
    print(f"  V0 baseline        = 0.069  (full SHA)")
    print(f"  V1 no_Sigma        = 0.742  (no rotations)")
    print(f"  V5 linear_ChMaj    = 0.056  (Σ + carry, XOR Ch/Maj)")
    print(f"  V_no_carry         = 0.048  (Σ + Ch/Maj, XOR add)")
    print(f"  V_all_linear       = 0.869  (no Σ, fully linear)")
    r24 = next(e['omega'] for e in results if e['r'] == 24)
    print(f"  V_sigma_only (NEW) = {r24:.3f}  (Σ only, XOR everywhere else)")

    out = {
        'N': N,
        'flags': flags,
        'rounds': ROUNDS,
        'results': results,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
