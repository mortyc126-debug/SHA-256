"""
Session 66: Structured multi-bit input differentials.

INDIRECT IDEA: Session 42 measured A(d) for RANDOM d-bit input differences.
What about STRUCTURED differences:
- All-1 byte differential (8 consecutive bits)
- Periodic (every 4-th bit)
- Single byte at MSB / LSB / middle
- Two distant bits

Structured differentials might propagate DIFFERENTLY than random ones, due
to ROTR/Σ resonance with bit positions.

Test:
1. Define structured difference templates.
2. Apply to random base inputs, measure output Hamming distance.
3. Compare to random d-bit difference baseline.

If structured difference gives anomalously LOW output distance, it's a
"weak differential" (good for attacks).
"""
import numpy as np
from session_46_correct_round import correct_round, R_correct, state_to_bits, bits_to_state


def hamming(a, b):
    return int((a ^ b).sum())


def measure_diff(template, NUM_TRIALS=100, T_MAX=4):
    """For diff template (256-bit array), measure output distance after T rounds."""
    rng = np.random.default_rng(0)
    distances_t = [[] for _ in range(T_MAX + 1)]
    for _ in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        x_pert = x ^ template
        cur, cur_pert = x, x_pert
        for t in range(T_MAX + 1):
            distances_t[t].append(hamming(cur, cur_pert))
            cur = R_correct(cur)
            cur_pert = R_correct(cur_pert)
    means = [np.mean(d) for d in distances_t]
    return means


def main():
    print("=== Session 66: Structured multi-bit differentials ===\n")

    templates = {}

    # Single-bit references
    for bit in [0, 31, 64, 128, 224]:
        t = np.zeros(256, dtype=np.uint8)
        t[bit] = 1
        reg = "abcdefgh"[bit // 32]
        i = bit % 32
        templates[f"1-bit at {reg}_{i}"] = t

    # Byte-aligned 8-bit at start of each register
    for r_idx, rname in enumerate("abcdefgh"):
        t = np.zeros(256, dtype=np.uint8)
        t[r_idx*32:r_idx*32 + 8] = 1
        templates[f"low byte of {rname}"] = t

    # Single byte at MSB of register a
    t = np.zeros(256, dtype=np.uint8)
    t[24:32] = 1
    templates["MSB byte of a"] = t

    # Periodic: every 4-th bit
    t = np.zeros(256, dtype=np.uint8)
    for i in range(0, 256, 4):
        t[i] = 1
    templates["every 4th bit"] = t

    # Two distant bits
    t = np.zeros(256, dtype=np.uint8)
    t[0] = 1
    t[128] = 1
    templates["bits 0 and 128"] = t

    # Two close bits
    t = np.zeros(256, dtype=np.uint8)
    t[0] = 1
    t[1] = 1
    templates["bits 0 and 1"] = t

    # All low bytes (LSB of each 32-bit register)
    t = np.zeros(256, dtype=np.uint8)
    for r_idx in range(8):
        t[r_idx*32] = 1
    templates["LSB of each register"] = t

    # All bits in register a
    t = np.zeros(256, dtype=np.uint8)
    t[0:32] = 1
    templates["all of register a"] = t

    print(f"  Measuring output distance after T rounds for each template:")
    print(f"  Random reference: A(1)≈4.7, A(8)≈27 (Session 42).\n")
    print(f"  {'template':<35}  {'HW(Δ)':>5}  {'<d_1>':>6}  {'<d_2>':>6}  {'<d_4>':>6}")
    print(f"  {'-'*70}")

    results = {}
    for name, template in templates.items():
        hw_delta = int(template.sum())
        means = measure_diff(template, NUM_TRIALS=80, T_MAX=4)
        results[name] = (hw_delta, means)
        print(f"  {name:<35}  {hw_delta:>5}  {means[1]:>6.2f}  {means[2]:>6.2f}  {means[4]:>6.2f}")

    print()

    # Compare structured vs random — find anomalously low ones
    print(f"  Anomaly check (structured vs expected by HW):")
    expected_d1_by_hw = {1: 4.7, 8: 27.0, 16: 39.0, 64: 80.0}  # from Session 42 approx

    for name, (hw, means) in results.items():
        exp = None
        for h in expected_d1_by_hw:
            if abs(h - hw) <= 2:
                exp = expected_d1_by_hw[h]
        if exp is not None:
            ratio = means[1] / exp
            if ratio < 0.7:
                print(f"    ⚠ {name}: <d_1> = {means[1]:.2f} vs expected {exp} (ratio {ratio:.2f}) — LOW")
            elif ratio > 1.5:
                print(f"    ⚠ {name}: <d_1> = {means[1]:.2f} vs expected {exp} (ratio {ratio:.2f}) — HIGH")

    print("""

=== Theorem 66.1 (structured differentials, empirical) ===

For each structured input difference template, measured average output
distance after T rounds.

If structured Δ_in gives <d_1> significantly lower than random Δ_in of
same Hamming weight: WEAK DIFFERENTIAL detected, exploitable.

If similar to random: SHA mixes structured patterns the same as random.
""")


if __name__ == "__main__":
    main()
