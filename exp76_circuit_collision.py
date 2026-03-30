#!/usr/bin/env python3
"""
EXP 76: Circuit Collision — Algorithmic, not Algebraic

75 experiments used algebra, statistics, dynamics.
SHA-256 is an ALGORITHM (448 deterministic operations), not a function.

KEY INSIGHT: SHA-256 has circuit complexity O(n) ≈ 20000 gates.
Random oracle has circuit complexity 2^n.
SHA-256 is 2^n / 20000 = 2^240 times SIMPLER than random oracle.

Question: does circuit simplicity → collision simplicity?

For a circuit with G gates: can we find collision in O(G^k) for some k?
If k=2: collision = O(G^2) = O(20000^2) = O(4×10^8) = trivial!
If k=n/2: collision = O(G^{n/2}) = same as birthday.

What determines k? The CIRCUIT STRUCTURE.

OUR DATA tells us about circuit structure:
  - 6/8 state words = copies (shift register) → 75% of gates = IDENTITY
  - Only 2 nonlinear operations per round (a, e) → gate depth = 2/round
  - Carry chains = 32-long sequential dependencies → depth per round = 32
  - Total circuit depth = 64 × 32 = 2048 (not 64 × 256 = 16384)

If depth determines collision cost: cost = 2^{depth/something}

Test: measure EFFECTIVE circuit depth of SHA-256 collision condition.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_circuit_depth_per_bit(W16, output_word, output_bit, R=64):
    """
    Measure: how many rounds does it take for input bit perturbation
    to reach this output bit?

    = DEPTH of the circuit path from any input to this output.
    """
    states = sha256_rounds(W16, R)
    base_bit = (states[R][output_word] >> output_bit) & 1

    # For each input bit: at which round does the output first change?
    min_depth = R  # Maximum possible
    depths = []

    for iw in range(16):
        for ib in range(32):
            W_p = list(W16); W_p[iw] ^= (1 << ib)

            # Check output at each round
            for r in range(1, R+1):
                s_p = sha256_rounds(W_p, r)
                pert_bit = (s_p[r][output_word] >> output_bit) & 1
                ref_s = sha256_rounds(W16, r)
                ref_bit = (ref_s[r][output_word] >> output_bit) & 1

                if pert_bit != ref_bit:
                    depths.append(r)
                    break
            else:
                depths.append(R)  # Never reached

    return np.array(depths)

def test_effective_depth(N=20):
    """Effective circuit depth for collision condition."""
    print("\n--- EFFECTIVE CIRCUIT DEPTH ---")

    # For each output bit: what's the minimum depth from any input?
    for ow, ob in [(4, 0), (4, 15), (4, 31), (0, 0), (7, 0)]:
        all_depths = []
        for _ in range(N):
            W16 = random_w16()
            depths = measure_circuit_depth_per_bit(W16, ow, ob, R=64)
            all_depths.append(depths.min())

        branch = "a" if ow < 4 else "e"
        print(f"  H[{ow}]({branch}) bit {ob:>2}: min_depth={np.mean(all_depths):.1f}, "
              f"range=[{min(all_depths)}, {max(all_depths)}]")

def test_dependency_count(N=50):
    """
    For collision: H(M) = H(M'). This requires ALL 256 output bits to match.
    How many INPUT BITS does each output bit ACTUALLY depend on?

    If an output bit depends on only k < 512 input bits:
    collision on that bit = birthday on k bits = 2^{k/2}.
    If all bits share the SAME k inputs: collision = 2^{k/2}.
    """
    print(f"\n--- DEPENDENCY COUNT PER OUTPUT BIT ---")

    for R in [8, 16, 32, 64]:
        dep_counts = []

        for _ in range(N):
            W16 = random_w16()
            states = sha256_rounds(W16, R)

            # Count: how many input bits affect H[4] bit 0?
            base_bit = (states[R][4] >> 0) & 1
            count = 0
            for iw in range(16):
                for ib in range(32):
                    W_p = list(W16); W_p[iw] ^= (1 << ib)
                    s_p = sha256_rounds(W_p, R)
                    if ((s_p[R][4] >> 0) & 1) != base_bit:
                        count += 1

            dep_counts.append(count)

        da = np.array(dep_counts)
        print(f"  R={R:>2}: E[deps]={da.mean():.1f}/512, "
              f"min={da.min()}, max={da.max()}")

def test_collision_as_sat():
    """
    Collision as SAT: f(x) ⊕ f(y) = 0 for all 256 output bits.
    This is a SAT instance with 1024 variables and 256 clauses.

    How many OPERATIONS does the SAT circuit have?
    Each SHA-256 evaluation = ~20000 gates. Two evaluations = 40000.
    XOR of outputs = 256 gates. Total: ~40256 gates.

    SAT solving: for random circuit with G gates and n variables:
    cost ≈ 2^{c·n} where c depends on gate density.

    For SHA-256 collision circuit:
    G = 40256, n = 1024, density = G/n ≈ 39.
    """
    print(f"\n--- COLLISION AS CIRCUIT ---")

    # Count operations in SHA-256
    ops_per_round = 7  # additions
    carry_per_add = 32  # bit-level carry operations
    boolean_per_round = 2  # Ch, Maj (each ~96 gates for 32 bits)
    rotation_per_round = 4  # Σ0, Σ1, and sometimes σ0, σ1

    total_additions = 64 * ops_per_round  # = 448
    total_carry_ops = total_additions * carry_per_add  # = 14336
    total_boolean = 64 * boolean_per_round * 96  # ≈ 12288
    total_rotation = 64 * rotation_per_round * 96  # ≈ 24576

    total_gates = total_carry_ops + total_boolean + total_rotation

    print(f"SHA-256 circuit size:")
    print(f"  Carry operations: {total_carry_ops}")
    print(f"  Boolean (Ch, Maj): {total_boolean}")
    print(f"  Rotation (Σ, σ): {total_rotation}")
    print(f"  TOTAL gates: {total_gates}")
    print(f"  = {total_gates:.0f} gates for ONE evaluation")
    print(f"  Collision circuit: 2 × {total_gates} + 256 = {2*total_gates+256}")

    # Circuit depth (sequential dependencies)
    depth_per_round = carry_per_add + 5  # carry chain + boolean
    total_depth = 64 * depth_per_round

    print(f"\nCircuit DEPTH:")
    print(f"  Per round: {depth_per_round} (carry chain 32 + overhead 5)")
    print(f"  Total: {total_depth}")
    print(f"  = {total_depth} sequential steps")

    # SHA-256 parallelism
    width = total_gates / total_depth
    print(f"\nParallelism (width = gates/depth): {width:.1f}")
    print(f"  SHA-256 is {width:.0f}-way parallel")

    # Comparison with random oracle
    print(f"\nComparison:")
    print(f"  SHA-256 circuit: {total_gates} gates, depth {total_depth}")
    print(f"  Random oracle: 2^256 gates (lookup table)")
    print(f"  Ratio: 2^256 / {total_gates} = 2^{256 - np.log2(total_gates):.0f}")
    print(f"  SHA-256 is 2^{256 - np.log2(total_gates):.0f}× SIMPLER than random")

    # What this implies for collision
    print(f"\n  If collision cost ∝ circuit_size^α:")
    for alpha in [0.5, 1, 1.5, 2]:
        cost = total_gates ** alpha
        print(f"    α={alpha}: cost = {total_gates}^{alpha} = {cost:.0e} = 2^{np.log2(cost):.1f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 76: CIRCUIT COLLISION")
    print("Algorithmic, not algebraic")
    print("="*60)
    test_effective_depth(10)
    test_dependency_count(30)
    test_collision_as_sat()

if __name__ == "__main__":
    main()
