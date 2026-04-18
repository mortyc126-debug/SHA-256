"""Phase 6C: phase-locking attack test.

Hypothesis: V_sigma_only shows oscillating Ω_3 (period-2). In baseline SHA
this oscillation is damped by nonlinearity (carry/Ch/Maj) → Ω_3 → 0 fast.

Could specific input features constructively interfere with the Σ rotation
phase, preserving |Ω_3| under baseline SHA at the critical r=20-24 window?

Test protocol:
- Baseline SHA (V0) state at r ∈ {16, 18, 20, 22, 24, 32}
- For each candidate feature f, measure Ω_3 with f as input feature
- Find features that give |Ω_3| > 0.3 at r=24 (where bit5_max gives 0.07)

Candidate features (all on HW=2 inputs, positions p0 < p1):
- bit_X_max for X ∈ {0..8}: bit X of max position
- bit_X_min for X ∈ {0..8}: bit X of min position
- bit_X_xor: XOR of bit X of both positions
- gap_modulo_X: (p1 - p0) mod 2^X
- (max - min) bit ranges
- Various combinations
"""
import json, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase6c_phase_locking.json')

ROUNDS = [16, 18, 20, 22, 24, 32]


def make_features(pos):
    """Generate dictionary of candidate features."""
    pos_arr = np.asarray(pos, dtype=np.int64)
    min_p = pos_arr[:, 0]
    max_p = pos_arr[:, 1]
    gap = max_p - min_p

    features = {}
    # Bit X of max position
    for x in range(9):
        features[f'bit{x}_max'] = ((max_p >> x) & 1).astype(np.uint8)
    # Bit X of min position
    for x in range(9):
        features[f'bit{x}_min'] = ((min_p >> x) & 1).astype(np.uint8)
    # XOR of bit X of both positions
    for x in range(9):
        features[f'bit{x}_xor'] = (((min_p >> x) ^ (max_p >> x)) & 1).astype(np.uint8)
    # Gap parity bits
    for x in range(9):
        features[f'gap_bit{x}'] = ((gap >> x) & 1).astype(np.uint8)
    # Sum parity
    for x in range(6):
        features[f'sum_bit{x}'] = (((min_p + max_p) >> x) & 1).astype(np.uint8)
    return features


def main():
    t0 = time.time()
    print("# Phase 6C: phase-locking via input feature search")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N} HW=2 inputs")

    features = make_features(pos)
    print(f"# {len(features)} candidate features")

    # Compute baseline SHA states at each round (one expensive computation per round)
    print(f"\n## Computing baseline states at r ∈ {ROUNDS}...")
    states = {}
    for r in ROUNDS:
        ts = time.time()
        states[r] = compress_partial(inputs, r)
        print(f"  r={r}: {time.time()-ts:.0f}s")

    # χ_S basis from r=4 state (same as Phase 1+)
    state_r4 = compress_partial(inputs, 4)
    chi_arr, _ = build_chi_arr(state_r4, k=3, subset_size=32)
    print(f"\n## χ_S basis: state at r=4, k=3, M={chi_arr.shape[0]} triples")

    # Measure Ω_3 for each feature × round
    print(f"\n## Scanning features × rounds:")
    results = {}
    for fname, fa in features.items():
        # Skip features with no variation
        if fa.sum() == 0 or fa.sum() == N:
            continue
        per_r = {}
        for r in ROUNDS:
            omega, ss, _, _, _ = omega_k_fast(chi_arr, states[r], fa)
            per_r[r] = {'omega': float(omega), 'ss': int(ss)}
        results[fname] = per_r
        # Verbose for promising features
        omega_24 = per_r[24]['omega']
        omega_32 = per_r[32]['omega']
        if abs(omega_24) > 0.15:
            print(f"  {fname:14s}: " + "  ".join(
                f"r={r}:Ω={per_r[r]['omega']:+.3f}" for r in ROUNDS))

    # Rank features by |Ω_3| at r=24 (where baseline collapses)
    ranked_24 = sorted(results.items(),
                       key=lambda x: -abs(x[1][24]['omega']))
    print(f"\n=== TOP 15 FEATURES BY |Ω_3| AT r=24 (baseline collapse zone) ===")
    print(f"{'feature':14s}  " + "  ".join(f"r={r}" for r in ROUNDS))
    for fname, data in ranked_24[:15]:
        omegas = [data[r]['omega'] for r in ROUNDS]
        print(f"  {fname:14s}: " + "  ".join(f"{o:+.3f}" for o in omegas))

    # Check r=32 to see if "preserved" features stay preserved or collapse later
    print(f"\n=== TOP 5 FEATURES BY |Ω_3| AT r=32 ===")
    ranked_32 = sorted(results.items(),
                       key=lambda x: -abs(x[1][32]['omega']))
    print(f"{'feature':14s}  " + "  ".join(f"r={r}" for r in ROUNDS))
    for fname, data in ranked_32[:5]:
        omegas = [data[r]['omega'] for r in ROUNDS]
        print(f"  {fname:14s}: " + "  ".join(f"{o:+.3f}" for o in omegas))

    # Verdict
    best_24 = ranked_24[0]
    print(f"\n## Verdict:")
    if abs(best_24[1][24]['omega']) > 0.3:
        print(f"  ✓ Phase-locking found: feature '{best_24[0]}' gives "
              f"Ω_3={best_24[1][24]['omega']:+.3f} at r=24 (baseline)")
        print(f"    Compare bit5_max baseline: 0.07")
        print(f"    Attack candidate: structured input distribution preserves Ω_3 under nonlinearity")
    elif abs(best_24[1][24]['omega']) > 0.15:
        print(f"  ~ Marginal phase-locking: feature '{best_24[0]}' gives "
              f"Ω_3={best_24[1][24]['omega']:+.3f}")
    else:
        print(f"  ✗ No phase-locking: all features collapse to |Ω_3| < 0.15 at r=24")
        print(f"    Ω_3 destruction is feature-INDEPENDENT under baseline SHA")

    out = {
        'N': N,
        'rounds': ROUNDS,
        'n_features': len(features),
        'results': results,
        'top_5_at_r24': [(fn, data[24]) for fn, data in ranked_24[:5]],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
