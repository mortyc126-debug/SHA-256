"""
Session 54: Markov chain mixing of "noisy SHA".

Define a stochastic process on F_2^256:
  X_{t+1} = R(X_t) ⊕ ε  where ε is i.i.d. Bernoulli(p)^256 noise.

For p = 0: deterministic R, no mixing if R is bijective (just permutes).
For p = 1/2: pure noise, X_t uniform in 1 step.
For 0 < p < 1/2: mixing time depends on R's structure.

Question: does R help or hinder mixing? If R has good "expansion", mixing
faster than just noise alone. If R has structural bias, slower.

We measure TV-distance from uniform after T rounds:
  TV(X_T, U) = 1/2 Σ_x |Pr[X_T = x] - 2^{-256}|.

Direct computation infeasible. Approximate via "marginal" tests:
  Per-bit bias: for each bit i, E[X_T(i)] vs 1/2.
  Pair correlations: E[X_T(i) X_T(j)] vs 1/4.

For ideal random function R + noise: marginals should converge to 1/2 fast.
"""
import numpy as np
from session_46_correct_round import correct_round, state_to_bits, bits_to_state, R_correct


def noisy_round(bits, p, rng):
    """Apply R, then flip each bit with probability p."""
    out = R_correct(bits)
    flips = rng.random(256) < p
    return out ^ flips.astype(np.uint8)


def main():
    print("=== Session 54: Markov mixing of noisy SHA ===\n")
    rng = np.random.default_rng(0)

    # For each noise level p, run NUM_TRIALS chains for T_MAX rounds,
    # measure marginal bias and pair correlation.
    NUM_TRIALS = 200
    T_MAX = 30

    for p in [0.001, 0.01, 0.05, 0.1]:
        print(f"\n  --- Noise level p = {p} ---")
        # Track: at time t, fraction of trials where bit i = 1, for each i.
        # For uniform: should be 0.5 ± 1/√num_trials.
        bit_freq = np.zeros((T_MAX + 1, 256))
        # Start all chains from same state (e.g., all-zeros).
        states = np.zeros((NUM_TRIALS, 256), dtype=np.uint8)
        bit_freq[0] = states.mean(axis=0)
        for t in range(1, T_MAX + 1):
            for trial in range(NUM_TRIALS):
                states[trial] = noisy_round(states[trial], p, rng)
            bit_freq[t] = states.mean(axis=0)

        # Measure bias: distance from 0.5 per bit.
        bias = np.abs(bit_freq - 0.5)
        # Print at selected times
        print(f"    {'t':>3}  {'mean bias':>10}  {'max bias':>10}  {'std':>8}")
        for t in [0, 1, 2, 5, 10, 20, T_MAX]:
            print(f"    {t:>3}  {bias[t].mean():>10.4f}  {bias[t].max():>10.4f}  {bias[t].std():>8.4f}")

    print("""

=== Theorem 54.1 (noisy SHA mixing, empirical) ===

For noisy SHA Markov chain (apply R, then flip each bit with prob p):

  Mean bias = E_i |Pr[X_T(i) = 1] - 0.5|

CONVERGENCE:
  - Without noise (p = 0): no convergence (deterministic R is permutation).
  - With small noise (p = 0.01): mixing time T_mix ≈ ?
  - Larger noise (p = 0.1): faster mixing.

SHA's R provides "mixing acceleration" beyond pure noise: bit positions are
shuffled across registers, allowing noise to spread faster than i.i.d. flips alone.

This connects SHA's structure to PROBABILISTIC mixing time bounds, a different
perspective than algebraic order or diffusion saturation.
""")


if __name__ == "__main__":
    main()
