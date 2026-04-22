"""
Hypothesis: R-invariance of carry Jacobian deficit is STATISTICAL, not
pointwise. Specifically — the DISTRIBUTION of per-round kernel dim is
R-invariant across rounds.

Test: at fixed n, compute per-round kernel dim distributions at different
R_total values. Do they coincide?

If yes → statistical conservation law (something SHA-round specific).
If no → R-invariance is just coincidence of means, no deep structure.

This is genuine new exploration — methodology doesn't have this.
"""
import numpy as np
import random, time
from collections import Counter
from persistent_kernel import jacobian_at_round, gf2_left_null_basis
from mini_sha import gen_IV


def kernel_dim_distribution(n, R_total, n_anchors=50, seed=42):
    """For each of R_total rounds, measure kernel dim distribution
    across n_anchors random W_bases.

    Returns: dict {round_idx: Counter(kernel_dim)}.
    """
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)

    per_round_dims = {r: [] for r in range(R_total)}
    for a in range(n_anchors):
        W_base = [random.randint(0, mask) for _ in range(R_total)]
        for r_target in range(R_total):
            J = jacobian_at_round(W_base, H0, r_target, n, R_total)
            ker = gf2_left_null_basis(J)
            per_round_dims[r_target].append(len(ker))

    return {r: Counter(dims) for r, dims in per_round_dims.items()}


def show_dist(label, counter, max_dim=10):
    """Pretty print distribution."""
    total = sum(counter.values())
    items = [f"dim={d}: {counter.get(d, 0)}/{total}" for d in range(max_dim)]
    mean = sum(d * c for d, c in counter.items()) / max(total, 1)
    print(f"  {label:<20} mean={mean:.2f}  {'  '.join(items[:6])}")


def compare_distributions(dist_a, dist_b, label_a, label_b):
    """Chi-square-like comparison of two counters."""
    # Combine all dim keys
    keys = sorted(set(list(dist_a.keys()) + list(dist_b.keys())))
    import math
    total_a = sum(dist_a.values())
    total_b = sum(dist_b.values())
    chi2 = 0
    for k in keys:
        p_a = dist_a.get(k, 0) / max(total_a, 1)
        p_b = dist_b.get(k, 0) / max(total_b, 1)
        exp = (p_a + p_b) / 2
        if exp > 0:
            chi2 += ((p_a - p_b) ** 2) / exp
    return chi2


def run_experiment(n, R_values, n_anchors=40):
    """Main: compare kernel dim distributions across different R_total values.
    """
    print(f"\n=== n={n}: kernel dim distribution vs R_total ===")
    all_distributions = {}
    for R_total in R_values:
        t0 = time.time()
        dist = kernel_dim_distribution(n, R_total, n_anchors=n_anchors)
        dt = time.time() - t0

        # Aggregate across all rounds (since distribution per round should be same if
        # round function is homogeneous)
        combined = Counter()
        for c in dist.values():
            combined.update(c)
        all_distributions[R_total] = combined

        # Show per-round
        print(f"\n  R_total={R_total} (elapsed {dt:.1f}s):")
        for r_target in range(R_total):
            show_dist(f"round r={r_target}", dist[r_target])
        show_dist(f"--- combined ---", combined)

    # Compare combined distributions across R
    print(f"\n  === Comparison of combined distributions ===")
    R_list = sorted(all_distributions.keys())
    baseline = all_distributions[R_list[0]]
    for R in R_list[1:]:
        chi2 = compare_distributions(baseline, all_distributions[R],
                                     f"R={R_list[0]}", f"R={R}")
        # Interpret: chi2 near 0 = same distribution; larger = different
        verdict = "≈same" if chi2 < 0.05 else ("diff-maybe" if chi2 < 0.2 else "DIFF")
        print(f"  R={R_list[0]} vs R={R}: chi2={chi2:.4f}  {verdict}")

    return all_distributions


if __name__ == "__main__":
    print("=== Kernel dim distribution across R_total ===")
    # Key test: n=16 at different R
    for n in [8, 12, 16]:
        try:
            run_experiment(n, R_values=[1, 2, 3, 4], n_anchors=30)
        except Exception as e:
            print(f"ERR n={n}: {e}")
            import traceback; traceback.print_exc()
