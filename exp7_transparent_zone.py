#!/usr/bin/env python3
"""
EXPERIMENT 7: Transparent Zone Attack — Polynomial Cost on Bits 0-4

Phase transition at k*=5: bits 0-4 are "transparent" (polynomial cost).
Standard Wang uses all 32 bits. What if we confine differential to bits 0-4?

Strategy:
1. Design differential ΔW that only affects bits 0-4 of each word
2. Track De_r restricted to bits 0-4 through all 64 rounds
3. Measure: can we get De[0:4]=0 for more rounds than De[0:31]=0?
4. If yes: bootstrap 5-bit partial collisions to full collision?
"""

import sys, os, random, math
from collections import Counter
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

LOW_MASK = 0x1F       # bits 0-4
MID_MASK = 0x3FF      # bits 0-9
HIGH_MASK = MASK ^ LOW_MASK

def test_transparent_zone_differential(N=5000):
    """Test: differential confined to bits 0-4 — does it propagate slower?"""
    print("\n--- TEST 1: TRANSPARENT ZONE DIFFERENTIAL ---")

    results = {'full': {}, 'low5': {}, 'low10': {}}

    for label, dw0_values in [
        ('full', [1, 0x80000000, 0x12345678]),  # Full 32-bit differentials
        ('low5', [1, 2, 4, 8, 16, 0x1F]),        # Only bits 0-4
        ('low10', [0x3FF, 0x155, 0x2AA]),         # Only bits 0-9
    ]:
        all_de_low = {r: [] for r in range(1, 65)}
        all_de_full = {r: [] for r in range(1, 65)}

        for dw0 in dw0_values:
            for _ in range(N // len(dw0_values)):
                W16 = random_w16()
                W16_f = list(W16)
                W16_f[0] = (W16_f[0] + dw0) & MASK  # Only additive diff in W[0]

                states_n = sha256_rounds(W16, 64)
                states_f = sha256_rounds(W16_f, 64)

                for r in range(1, 65):
                    De_r = (states_f[r][4] - states_n[r][4]) & MASK
                    De_xor = states_f[r][4] ^ states_n[r][4]

                    # HW of low bits vs full
                    all_de_low[r].append(hw(De_xor & LOW_MASK))
                    all_de_full[r].append(hw(De_xor))

        results[label] = {
            'low': {r: np.mean(v) for r, v in all_de_low.items()},
            'full': {r: np.mean(v) for r, v in all_de_full.items()},
            'p_low_zero': {r: sum(1 for v in all_de_low[r] if v == 0) / len(all_de_low[r])
                          for r in all_de_low},
        }

    print(f"\n{'Round':>5} | {'Full ΔW: HW(De_low)':>20} | {'Low5 ΔW: HW(De_low)':>20} | "
          f"{'P(De_low=0) Full':>16} | {'P(De_low=0) Low5':>16}")
    print("-" * 95)

    signals = []
    for r in [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 17, 18, 20, 24, 32, 48, 64]:
        full_hw = results['full']['low'][r]
        low5_hw = results['low5']['low'][r]
        p_zero_full = results['full']['p_low_zero'][r]
        p_zero_low5 = results['low5']['p_low_zero'][r]

        marker = ""
        if p_zero_low5 > p_zero_full * 1.5 and r > 10:
            marker = " ***"
            signals.append((r, p_zero_low5 / max(p_zero_full, 1e-10)))

        print(f"{r:>5} | {full_hw:>20.4f} | {low5_hw:>20.4f} | "
              f"{p_zero_full:>16.6f} | {p_zero_low5:>16.6f}{marker}")

    return signals

def test_partial_collision_bootstrap(N=10000):
    """
    Can 5-bit partial collisions be bootstrapped?

    Strategy: find pairs where De[0:4]=0 at round 64,
    then check if these pairs have any structure in higher bits.
    """
    print("\n--- TEST 2: PARTIAL COLLISION BOOTSTRAP ---")

    partial_collisions = []
    total = 0

    for _ in range(N):
        W16 = random_w16()
        W16_f = list(W16)
        dw = random.randint(1, LOW_MASK)  # Small differential in bits 0-4
        W16_f[0] = (W16_f[0] + dw) & MASK

        H_n = sha256_compress(W16)
        H_f = sha256_compress(W16_f)

        # Check partial collision on low bits
        low_match = all((H_n[i] & LOW_MASK) == (H_f[i] & LOW_MASK) for i in range(8))

        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        total_hw = sum(hw(d) for d in delta_H)

        total += 1

        if low_match:
            partial_collisions.append({
                'total_hw': total_hw,
                'delta_H': delta_H,
                'dw': dw,
            })

    p_partial = len(partial_collisions) / total
    expected = (1/32)**8  # 5 bits × 8 words must all match

    print(f"Partial collisions found: {len(partial_collisions)}/{total}")
    print(f"P(partial collision): {p_partial:.8f}")
    print(f"Expected (random): {expected:.8f} = 2^{math.log2(expected):.1f}")

    if p_partial > 0:
        ratio = p_partial / expected
        print(f"Ratio actual/expected: {ratio:.4f}")

        if ratio > 2:
            print("*** SIGNAL: Partial collisions above birthday! ***")

        # Analyze remaining bits
        hw_remaining = [pc['total_hw'] for pc in partial_collisions]
        if hw_remaining:
            print(f"\nWhen low bits match:")
            print(f"  Avg HW(ΔH remaining): {np.mean(hw_remaining):.2f}")
            print(f"  Expected (random): ~{256 - 40:.0f} * 0.5 = {(256-40)*0.5:.0f}")
    else:
        print(f"\nNeed ~2^{-math.log2(expected):.0f} samples to find partial collision")
        print("Testing with larger differential space...")

    # Alternative: test with XOR differential
    print("\n  Testing XOR partial match (any 5 consecutive bits per word)...")
    for bit_start in [0, 5, 10, 15, 20, 25]:
        mask = 0x1F << bit_start
        matches = 0
        for _ in range(N):
            W16 = random_w16()
            W16_f = list(W16)
            W16_f[0] ^= (1 << bit_start)  # Single bit flip

            H_n = sha256_compress(W16)
            H_f = sha256_compress(W16_f)

            # Check if these 5 bits match in H[0]
            if (H_n[0] & mask) == (H_f[0] & mask):
                matches += 1

        p = matches / N
        expected_p = 1/32
        print(f"  Bits [{bit_start}:{bit_start+4}] of H[0]: P={p:.4f} (expected {expected_p:.4f}, ratio={p/expected_p:.3f})")

def test_transparent_zone_cascade(N=5000):
    """
    Wang cascade but only in the transparent zone (bits 0-4).
    Can we get MORE rounds of De[0:4]=0 than the standard 16 rounds of De=0?
    """
    print("\n--- TEST 3: TRANSPARENT ZONE CASCADE ---")

    max_zeros_standard = []
    max_zeros_lowbits = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # Count consecutive De=0 (standard)
        std_zeros = 0
        for r in range(3, 65):
            if de(states_n, states_f, r) == 0:
                std_zeros += 1
            else:
                break
        max_zeros_standard.append(std_zeros)

        # Count consecutive De[0:4]=0 (low bits only)
        low_zeros = 0
        for r in range(3, 65):
            De_r = de(states_n, states_f, r)
            if (De_r & LOW_MASK) == 0:
                low_zeros += 1
            else:
                break
        max_zeros_lowbits.append(low_zeros)

    avg_std = np.mean(max_zeros_standard)
    avg_low = np.mean(max_zeros_lowbits)
    max_std = max(max_zeros_standard)
    max_low = max(max_zeros_lowbits)

    print(f"Standard cascade De=0:     avg={avg_std:.2f}, max={max_std}")
    print(f"Low-bit cascade De[0:4]=0: avg={avg_low:.2f}, max={max_low}")
    print(f"Extra rounds gained: avg={avg_low - avg_std:.2f}, max={max_low - max_std}")

    if avg_low > avg_std + 1:
        print("*** SIGNAL: Low-bit cascade extends significantly beyond standard! ***")

    # Distribution comparison
    counter_std = Counter(max_zeros_standard)
    counter_low = Counter(max_zeros_lowbits)

    print(f"\nDistribution of cascade length:")
    print(f"{'Length':>6} | {'Standard':>10} | {'Low-bits':>10}")
    print("-" * 35)
    for length in sorted(set(list(counter_std.keys()) + list(counter_low.keys()))):
        if length > 20:
            continue
        print(f"{length:>6} | {counter_std.get(length, 0):>10} | {counter_low.get(length, 0):>10}")

    return avg_low - avg_std

def test_bit_zone_independence(N=3000):
    """
    Test: are bits 0-4 of De truly independent from bits 5-31?
    If not → information leaks between zones → potential exploit.
    """
    print("\n--- TEST 4: BIT ZONE INDEPENDENCE ---")

    correlations_by_round = {}

    for r_target in [17, 18, 20, 24, 32, 48, 64]:
        low_vals = []
        high_vals = []

        for _ in range(N):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

            if r_target <= len(states_n) - 1:
                De_r = de(states_n, states_f, r_target)
                low_vals.append(De_r & LOW_MASK)
                high_vals.append((De_r >> 5) & 0x7FFFFFF)  # bits 5-31

        # Correlation between low and high
        if low_vals and high_vals:
            # Use mutual information proxy: does knowing low predict high?
            low_arr = np.array(low_vals)
            high_arr = np.array(high_vals)

            # HW correlation
            low_hw = np.array([hw(v) for v in low_vals])
            high_hw = np.array([hw(v) for v in high_vals])

            corr = np.corrcoef(low_hw, high_hw)[0, 1]
            correlations_by_round[r_target] = corr

            marker = " ***" if abs(corr) > 0.05 else ""
            print(f"Round {r_target:>2}: corr(HW_low, HW_high) = {corr:+.6f}{marker}")

    return correlations_by_round

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 7: TRANSPARENT ZONE ATTACK (BITS 0-4)")
    print("=" * 70)

    signals = test_transparent_zone_differential(3000)
    test_partial_collision_bootstrap(5000)
    gain = test_transparent_zone_cascade(5000)
    corrs = test_bit_zone_independence(2000)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Transparent zone signals: {len(signals)}")
    print(f"Cascade gain (low-bits vs standard): {gain:+.2f} rounds")
    print(f"Max inter-zone correlation: {max(abs(v) for v in corrs.values()):.6f}")

    if gain > 1:
        print("\n*** Low-bit cascade significantly extends Wang chain! ***")
        print("This could open a sub-exponential path through the transparent zone.")
    else:
        print("\nTransparent zone does not provide significant extension.")

if __name__ == "__main__":
    main()
