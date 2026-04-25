"""
Session 45: Differential Distribution Table (DDT) for one SHA round bit.

Classical cryptanalysis tool: for input difference Δ_in and output difference Δ_out:

  DDT[Δ_in][Δ_out] = #{x : R(x ⊕ Δ_in) ⊕ R(x) = Δ_out}.

For ideal random function: DDT entries close to N / 2^n ~ 1 (where N = #x sampled).
For SHA: certain entries dominate — these are HIGH-PROBABILITY DIFFERENTIAL TRAILS.

Full DDT for 256-bit inputs is infeasible (2^512 entries). We focus on:
1. Per-INPUT-DIFFERENCE: For fixed Δ_in (low Hamming weight), distribution of Δ_out.
2. Top-probability differentials: Which (Δ_in → Δ_out) pairs occur most often?
3. Specifically interesting: differentials from a single bit flip.
"""
import numpy as np
from collections import Counter
from session_25_round import build_sigma_0, build_sigma_1
from session_38_avalanche import round_eval_with_addchains


def main():
    print("=== Session 45: Differential Distribution Table (DDT) sample ===\n")
    S0 = build_sigma_0()
    S1 = build_sigma_1()
    R = lambda x: round_eval_with_addchains(x, S0, S1)

    NUM_SAMPLES = 1000
    rng = np.random.default_rng(0)

    # For each single-bit input difference, compute distribution of output diffs
    # Track FREQUENCY of specific output differences.

    # We'll focus on a few "interesting" Δ_in cases:
    # 1. One bit flip in register a (positions 0, 8, 16, 24)
    # 2. One bit flip in register e (positions 0, 8, 16, 24)
    # 3. A delta of "all bit 0" (LSB of each register)

    delta_in_cases = [
        ("flip a_0", 0),
        ("flip a_15", 15),
        ("flip e_0", 128),
        ("flip e_15", 128 + 15),
        ("flip h_0", 224),
    ]

    print(f"  For each Δ_in (single bit flip), sample {NUM_SAMPLES} pairs (x, x ⊕ Δ_in)")
    print(f"  and analyse the distribution of Δ_out:")
    print()

    for label, bit_idx in delta_in_cases:
        print(f"\n  === Δ_in = {label} (bit index {bit_idx}) ===")
        delta_in = np.zeros(256, dtype=np.uint8)
        delta_in[bit_idx] = 1

        # Collect output differences
        output_diff_counts = Counter()
        per_bit_freq = np.zeros(256, dtype=int)
        for _ in range(NUM_SAMPLES):
            x = rng.integers(0, 2, size=256, dtype=np.uint8)
            Rx = R(x)
            Rx_pert = R(x ^ delta_in)
            delta_out = (Rx ^ Rx_pert).tobytes()
            output_diff_counts[delta_out] += 1
            per_bit_freq += (Rx ^ Rx_pert)

        # Top differentials
        top = output_diff_counts.most_common(5)
        print(f"    Distinct Δ_out values seen: {len(output_diff_counts)} / {NUM_SAMPLES}")
        print(f"    Top 5 most-common Δ_out:")
        for delta_bytes, cnt in top:
            arr = np.frombuffer(delta_bytes, dtype=np.uint8)
            weight = int(arr.sum())
            prob = cnt / NUM_SAMPLES
            print(f"      count {cnt:>4} (prob {prob:.4f}), Hamming weight {weight}")

        # Per-bit-position output deviation rate
        nonzero_bits = sum(1 for f in per_bit_freq if f > 0)
        max_freq_bit = int(np.argmax(per_bit_freq))
        max_freq_val = per_bit_freq[max_freq_bit] / NUM_SAMPLES
        print(f"    Output bits affected: {nonzero_bits} / 256")
        print(f"    Most-frequently-flipped output bit: idx {max_freq_bit} (rate {max_freq_val:.4f})")

    print(f"""

=== Theorem 45.1 (DDT structure) ===

For one SHA bare round with single-bit input differences:

  - Number of DISTINCT output differences observed: typically high
    (most pairs give different Δ_out — randomization).
  - But the OUTPUT BIT FREQUENCIES are NOT uniform: certain bits flip
    nearly always (correlation ≈ 1), others rarely (correlation ≈ 0).
  - This per-bit non-uniformity drives differential cryptanalysis.

CRYPTANALYTIC IMPLICATION:
  Single-bit Δ_in produces output bits with deterministic flip patterns
  (those determined by ROTR's, Ch, Maj). These deterministic transitions
  are the "trail building blocks" — chains of high-probability Δ_in → Δ_out
  used in differential cryptanalysis.

  The full DDT (impractical for 2^256) collapses to a small number of
  "active bits" per input difference, which is what makes reduced-round
  SHA differential attacks tractable.
""")


if __name__ == "__main__":
    main()
