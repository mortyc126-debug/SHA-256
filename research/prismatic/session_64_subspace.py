"""
Session 64: Subspace mixing — looking for "slow corners" of state space.

INDIRECT HYPOTHESIS: SHA's average mixing rate λ ≈ 1.42 (Session 48), but
maybe specific INPUT SUBSPACES (e.g., all states where bits 128-255 are 0)
have lower local λ. Slow-mixing subspaces give higher near-collision density.

Test:
1. Restrict input states to specific subspaces.
2. Measure local Lyapunov within that subspace.
3. Compare to global (random state) λ.

Subspaces to test:
A. Low Hamming weight (≤ 16 bits set out of 256)
B. Half-state (lower 128 bits free, upper 128 zero)
C. Single-register (only register a free, rest 0)
D. Periodic patterns (state = repeated 32-bit value)
E. Palindromic (bits[i] = bits[255-i])

For each, measure how much faster/slower the mixing is than random.
"""
import numpy as np
from session_46_correct_round import correct_round, R_correct, state_to_bits, bits_to_state


def hamming_state(s1, s2):
    return int((s1 ^ s2).sum())


def measure_subspace_lambda(generator, NUM_PAIRS=20, T_MAX=8):
    """For initial pairs from generator (callable returning state pair),
    measure mean Hamming distance after T rounds.
    """
    growths = []
    for trial in range(NUM_PAIRS):
        x, x_pert = generator()
        cur, cur_pert = x, x_pert
        d_t = []
        for t in range(T_MAX + 1):
            d_t.append(hamming_state(cur, cur_pert))
            cur = R_correct(cur)
            cur_pert = R_correct(cur_pert)
        growths.append(d_t)
    growths = np.array(growths)
    return growths.mean(axis=0)


def make_random_pair(d_0=1):
    """Random state, perturbation by 1 bit."""
    rng = np.random.default_rng()
    def gen():
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        positions = rng.choice(256, size=d_0, replace=False)
        x_pert = x.copy()
        for p in positions:
            x_pert[p] ^= 1
        return x, x_pert
    return gen


def make_low_hw_pair(max_hw=8, d_0=1):
    """Random state with Hamming weight ≤ max_hw, perturbation 1 bit."""
    rng = np.random.default_rng()
    def gen():
        x = np.zeros(256, dtype=np.uint8)
        hw = rng.integers(1, max_hw + 1)
        positions = rng.choice(256, size=hw, replace=False)
        for p in positions:
            x[p] = 1
        x_pert = x.copy()
        flip_pos = rng.choice(256, size=d_0, replace=False)
        for p in flip_pos:
            x_pert[p] ^= 1
        return x, x_pert
    return gen


def make_half_zero_pair(d_0=1):
    """Lower 128 bits free, upper 128 zero, perturbation 1 bit (in lower half)."""
    rng = np.random.default_rng()
    def gen():
        x = np.zeros(256, dtype=np.uint8)
        x[:128] = rng.integers(0, 2, size=128, dtype=np.uint8)
        x_pert = x.copy()
        flip_pos = rng.choice(128, size=d_0, replace=False)  # only flip lower half
        for p in flip_pos:
            x_pert[p] ^= 1
        return x, x_pert
    return gen


def make_single_reg_pair(reg_idx=0, d_0=1):
    """Only one register active, rest zero. Perturb in active register."""
    rng = np.random.default_rng()
    offset = reg_idx * 32
    def gen():
        x = np.zeros(256, dtype=np.uint8)
        x[offset:offset + 32] = rng.integers(0, 2, size=32, dtype=np.uint8)
        x_pert = x.copy()
        flip_pos = rng.choice(32, size=d_0, replace=False)
        for p in flip_pos:
            x_pert[offset + p] ^= 1
        return x, x_pert
    return gen


def make_periodic_pair(period_bits=32, d_0=1):
    """state = period repeated 256/period times."""
    rng = np.random.default_rng()
    def gen():
        x = np.zeros(256, dtype=np.uint8)
        block = rng.integers(0, 2, size=period_bits, dtype=np.uint8)
        for k in range(256 // period_bits):
            x[k*period_bits:(k+1)*period_bits] = block
        x_pert = x.copy()
        flip_pos = rng.choice(256, size=d_0, replace=False)
        for p in flip_pos:
            x_pert[p] ^= 1
        return x, x_pert
    return gen


def main():
    print("=== Session 64: Subspace mixing — slow corners? ===\n")

    print("  Reference (random state, 1-bit perturbation):")
    growth_ref = measure_subspace_lambda(make_random_pair(d_0=1), NUM_PAIRS=30, T_MAX=8)
    for t, d in enumerate(growth_ref):
        print(f"    t={t}: <d_t> = {d:.2f}")

    test_cases = [
        ("Low HW ≤ 4", make_low_hw_pair(max_hw=4)),
        ("Low HW ≤ 16", make_low_hw_pair(max_hw=16)),
        ("Half-state (upper 128 zero)", make_half_zero_pair()),
        ("Single register a only", make_single_reg_pair(reg_idx=0)),
        ("Single register e only", make_single_reg_pair(reg_idx=4)),
        ("Periodic period 32 (registers identical)", make_periodic_pair(32)),
        ("Periodic period 64", make_periodic_pair(64)),
    ]

    print()
    for label, gen in test_cases:
        growth = measure_subspace_lambda(gen, NUM_PAIRS=30, T_MAX=8)
        # Compare with reference
        ratio_t1 = growth[1] / growth_ref[1] if growth_ref[1] > 0 else 0
        print(f"  {label}:")
        print(f"    growth: {' → '.join(f'{d:.1f}' for d in growth)}")
        print(f"    ratio at t=1: {ratio_t1:.3f}")
        if ratio_t1 < 0.5:
            print(f"    ⚠ SUBSPACE MIXING SLOWER than random (potential weak region!)")
        elif ratio_t1 > 1.5:
            print(f"    ⚠ SUBSPACE MIXING FASTER than random")
        else:
            print(f"    similar to random")
        print()

    print("""

=== Theorem 64.1 (subspace mixing, empirical) ===

For each tested subspace, measured Hamming distance growth after 1-bit
perturbation. Compared to random reference.

If any subspace shows mixing rate < 0.5 × random:
  → potential weak input region, exploitable for near-collisions in that
    region.
If all subspaces show similar mixing:
  → SHA is uniformly mixing across subspaces, no exploitable corner.
""")


if __name__ == "__main__":
    main()
