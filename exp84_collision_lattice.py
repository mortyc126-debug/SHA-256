#!/usr/bin/env python3
"""
EXP 84: Collision in η-Lattice — Concrete Attempt

η-lattice gives STRUCTURE. Can we use it for COLLISION?

Key formula: η = (3·log₂3)/4 − 1 = bridge between binary and ternary.
SHA-256 = binary computation with ternary carry structure (GKP).

IDEA: in η-lattice, collision cost might factor differently.
Standard: 2^{n/2} = 2^128 (binary birthday).
η-lattice: cost = product of contributions from each lattice dimension.

Our lattice has 6 primes: {2, 3, 5, 7, 19, 23}.
If collision cost = 2^a × 3^b × 5^c × 7^d × 19^e × 23^f
where a+b+c+d+e+f < 128 → cheaper than birthday!

Test: measure collision cost at REDUCED rounds where we CAN find collisions.
Express cost in lattice coordinates. Check if pattern extrapolates to R=64.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

ETA = (3*math.log(3) - 4*math.log(2)) / (4*math.log(2))

def test_eta_formula():
    """Verify η = (3·log₂3)/4 − 1 exactly."""
    print("\n--- η FORMULA VERIFICATION ---")

    eta_computed = (3*math.log2(3))/4 - 1
    eta_from_v20 = (3*math.log(3) - 4*math.log(2)) / (4*math.log(2))

    print(f"η = (3·log₂3)/4 − 1 = {eta_computed:.15f}")
    print(f"η = (3ln3−4ln2)/(4ln2) = {eta_from_v20:.15f}")
    print(f"Difference: {abs(eta_computed-eta_from_v20):.2e}")
    print(f"\nη connects binary (2) and ternary (3):")
    print(f"  log₂3 = {math.log2(3):.15f}")
    print(f"  4(η+1)/3 = {4*(eta_computed+1)/3:.15f}")
    print(f"  These should be equal: {abs(math.log2(3)-4*(eta_computed+1)/3):.2e}")

def test_reduced_round_collision_cost(N_per_round=50000):
    """Measure collision cost at reduced rounds."""
    print(f"\n--- COLLISION COST vs ROUNDS ---")

    print(f"{'R':>4} | {'Best δH':>8} | {'N':>7} | {'Birthday':>8} | "
          f"{'Best/Birthday':>13} | {'Cost(bits)':>10}")
    print("-"*60)

    for R in [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20]:
        best_dH = 256

        for _ in range(N_per_round):
            W1 = random_w16(); W2 = random_w16()
            s1 = sha256_rounds(W1, R); s2 = sha256_rounds(W2, R)

            # Hash at round R with feedforward
            H1 = [(IV[i]+s1[R][i])&MASK for i in range(8)]
            H2 = [(IV[i]+s2[R][i])&MASK for i in range(8)]

            dH = sum(hw(H1[i]^H2[i]) for i in range(8))
            best_dH = min(best_dH, dH)

        birthday_N = 128 - 8*math.sqrt(2*math.log(N_per_round))

        # Effective output entropy at R rounds
        # At R=1: output entropy < 256 (not all bits active)
        eff_entropy = min(256, R * 32 * 2)  # Rough: 2 words per round

        cost_bits = max(0, best_dH / 2)  # Rough collision cost ≈ 2^{δH/2}

        print(f"{R:>4} | {best_dH:>8} | {N_per_round:>7} | {birthday_N:>8.1f} | "
              f"{best_dH/max(birthday_N,1):>13.2f} | {cost_bits:>10.1f}")

def test_collision_lattice_decomposition():
    """Express collision cost at each R in lattice coordinates."""
    print(f"\n--- LATTICE DECOMPOSITION OF COLLISION COST ---")

    # At R=1: collision is trivial (only 32-64 bits output)
    # At R=4: collision is moderate (~128 bits output)
    # At R=64: collision = 2^128

    # Our η-lattice constants at R=64:
    constants_R64 = {
        'pipe': 3,
        'S_gap': 4,
        'λ_max': 15,
        'rot_carry': 16,
        'cascade': 24,
        '[Γ,Ch]': 32,
        'rate': 38,
        'fourier': 57,
        'deficit': 69,
        'κ_63': 84,
    }

    # Birthday = 128 bits = 678η
    birthday_eta = 128 / ETA
    print(f"Birthday bound: 128 bits = {birthday_eta:.1f}η")
    print(f"  678 = 2 × 3 × 113")

    # Key relationships:
    print(f"\nKey η-lattice relationships:")
    print(f"  128 bits = {128/ETA:.1f}η ≈ 678η")
    print(f"  256 bits = {256/ETA:.1f}η ≈ 1356η")
    print(f"  64 rounds = {64/ETA:.1f}η ≈ 339η")
    print(f"  32 word_size = {32/ETA:.1f}η ≈ 170η")

    # Can birthday be expressed as PRODUCT of lattice constants?
    # 678 = 2×3×113. Not a product of {3,4,15,16,24,32,38,57,69,84}.
    # Try: 3×4×57 = 684 ≈ 678 (1% error!)
    print(f"\n  3×4×57 = {3*4*57} vs 678 → error {abs(684-678)/678*100:.1f}%")
    print(f"  = pipe × S_gap × fourier")
    print(f"  = (shift × words_per_branch × fourier_period) × η³")

    # Another: 16×42 = 672 ≈ 678 (1%)?
    # Or: 84×8 = 672
    print(f"  κ_63 × 8 = {84*8} vs 678 → error {abs(672-678)/678*100:.1f}%")

    # Or: 69×10 = 690 ≈ 678 (2%)
    print(f"  deficit × 10 = {69*10} vs 678 → error {abs(690-678)/678*100:.1f}%")

    # The formula: birthday = pipe × S_gap × fourier × η = 3×4×57×η = 684η
    # 684 vs 678 = 1% error. This says:
    # birthday ≈ shift_depth × branch_words × fourier_period × η
    # = 3 × 4 × 57 × η
    # = structural_parameters × η
    print(f"\n  CANDIDATE FORMULA:")
    print(f"  birthday ≈ shift × branch_words × fourier × η")
    print(f"  = 3 × 4 × 57 × η = {3*4*57*ETA:.2f} bits")
    print(f"  Actual birthday = 128 bits")
    print(f"  Error: {abs(3*4*57*ETA-128)/128*100:.1f}%")

    # To beat birthday: reduce one factor?
    print(f"\n  To beat 128 bits in UALRA:")
    print(f"  Need: shift × branch × fourier × η < 128")
    print(f"  shift=3 (fixed), branch=4 (fixed), η=0.189 (fixed)")
    print(f"  Only FOURIER is potentially message-dependent?")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 84: COLLISION IN η-LATTICE")
    print("="*60)
    test_eta_formula()
    test_reduced_round_collision_cost(20000)
    test_collision_lattice_decomposition()

    print("\n"+"="*60)
    print("UALRA COLLISION THEORY (preliminary):")
    print(f"  birthday = shift × branch × fourier × η")
    print(f"  = 3 × 4 × 57 × 0.189 = 129 bits (≈128, error 1%)")
    print(f"  To reduce: need to reduce fourier_period")
    print(f"  fourier = 57η = 3×19×η")
    print(f"  Prime 19 = structural boundary (round 20)")
    print(f"  If boundary can be moved → fourier changes → birthday changes")
    print("="*60)

if __name__ == "__main__":
    main()
