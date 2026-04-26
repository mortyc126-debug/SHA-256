"""
Session 61: Local Lyapunov heterogeneity — searching for "weak states".

INVERSE CRYPTANALYSIS HYPOTHESIS:
  If SHA's average Lyapunov is λ ≈ 1.42 (Session 48), maybe the VARIANCE
  is non-trivial — some states have local λ_v ≈ 0.5 (slow mixing, "weak"),
  others λ_v ≈ 2.0 (fast).

  Weak states are CLOSER to collisions: small input differences don't grow
  → many inputs map to nearby outputs → birthday-bound collisions easier.

Test:
1. Sample N random states v.
2. For each v, measure local 1-step avalanche: avg Hamming distance
   over 256 single-bit perturbations of v.
3. Compute distribution of local avalanches.
4. If distribution is wide (some v with avalanche ≪ 5), those are weak states.

If found: search for collisions among weak states (statistically more likely).
"""
import numpy as np
from session_46_correct_round import correct_round, state_to_bits, bits_to_state, R_correct


def local_avalanche(v_bits):
    """For state v, return mean Hamming distance after one round, averaged over
    all 256 single-bit perturbations.
    """
    Rv = R_correct(v_bits)
    distances = np.zeros(256)
    for i in range(256):
        v_pert = v_bits.copy()
        v_pert[i] ^= 1
        Rv_pert = R_correct(v_pert)
        distances[i] = (Rv ^ Rv_pert).sum()
    return distances.mean(), distances.std(), distances.min(), distances.max()


def main():
    print("=== Session 61: Local Lyapunov heterogeneity ===\n")
    rng = np.random.default_rng(0)
    NUM_SAMPLES = 30

    print(f"  Sampling {NUM_SAMPLES} random states, computing local avalanche.\n")
    print(f"  Mean over many random states: ~5 (Session 38).")
    print(f"  Hypothesis: variance is large → weak states exist.\n")

    print(f"  {'v idx':>5}  {'avg avalanche':>14}  {'std':>6}  {'min':>5}  {'max':>5}")
    print(f"  {'-'*55}")

    avg_per_state = []
    min_per_state = []
    for i in range(NUM_SAMPLES):
        v = rng.integers(0, 2, size=256, dtype=np.uint8)
        mean, std, mn, mx = local_avalanche(v)
        avg_per_state.append(mean)
        min_per_state.append(mn)
        print(f"  {i:>5}  {mean:>14.3f}  {std:>6.3f}  {int(mn):>5}  {int(mx):>5}")

    avg_per_state = np.array(avg_per_state)
    min_per_state = np.array(min_per_state)

    print(f"\n  Statistics across {NUM_SAMPLES} random states:")
    print(f"    Average local avalanche: {avg_per_state.mean():.3f} ± {avg_per_state.std():.3f}")
    print(f"    Range: {avg_per_state.min():.2f} – {avg_per_state.max():.2f}")

    print(f"\n  Hypothesis test:")
    if avg_per_state.std() / avg_per_state.mean() < 0.05:
        print(f"  ✗ HYPOTHESIS REFUTED: avalanche is highly UNIFORM across states.")
        print(f"    Coefficient of variation = {avg_per_state.std()/avg_per_state.mean():.3f} < 0.05.")
        print(f"    No 'weak states' detectable — uniform mixing rate per state.")
    else:
        print(f"  ✓ HYPOTHESIS SUPPORTED: avalanche varies across states.")
        print(f"    Coefficient of variation = {avg_per_state.std()/avg_per_state.mean():.3f}.")
        print(f"    Investigate weak states (low avalanche).")

    print(f"\n  Per-bit minimum avalanche (single-bit flips with smallest output change):")
    print(f"    Smallest per-bit avalanche observed: {min_per_state.min()}")
    if min_per_state.min() == 0:
        print(f"    ⚠ FOUND ZERO-AVALANCHE bit! Some single-bit flip has NO output change.")
        print(f"      → potential collision handle (deterministic differential).")
    elif min_per_state.min() <= 1:
        print(f"    ⚠ Very small avalanche found ({min_per_state.min()}). Investigate.")
    else:
        print(f"    All single-bit flips give ≥ {min_per_state.min()} output bits flipped.")

    print(f"""

=== Theorem 61.1 (avalanche heterogeneity, empirical) ===

For SHA-256 bare round, local avalanche at random state has:
- Mean: {avg_per_state.mean():.2f} per single-bit input flip.
- Std: {avg_per_state.std():.2f} (cross-state variance).
- Coefficient of variation: {avg_per_state.std()/avg_per_state.mean():.3f}.

If CV < 0.05: avalanche is essentially UNIFORM across state space —
no exploitable weak states. (This is what we expect for a well-designed
hash: the "weakness" of any state should be statistically uniform.)

If CV > 0.1: weak states exist; exploit potential.

INVERSE CRYPTANALYSIS APPLICATION:
  If weak states exist, they form a region of state space where SHA's mixing
  is degraded. Collisions cluster there. Targeted search in weak region beats
  random search by factor proportional to (uniform_avalanche / weak_avalanche)^T.

  For SHA-256: if weak states found, this could give first collision-attack
  parameter advantage.
""")


if __name__ == "__main__":
    main()
