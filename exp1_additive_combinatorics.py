#!/usr/bin/env python3
"""
EXPERIMENT 1: Additive Combinatorics of the Barrier Equation

Barrier at round 17: Da13 + DW16 = 0 (mod 2^32)
Da13 depends on W[0..12], DW16 = sig1(DW14) + DW9 + sig0(DW1) + DW0

We treat A = {Da13(W)} and B = {DW16(W)} as SUMSETS.
Freiman-Ruzsa: if |A+B| <= K|A|, then A has additive structure.

This experiment:
1. Generates Wang cascade pairs, collects Da13 and DW16 values
2. Measures doubling constant |A+B|/max(|A|,|B|)
3. Measures additive energy E(A) = |{(a1,a2,a3,a4) : a1+a2=a3+a4}|
4. Tests for arithmetic progressions in A and B
5. Compares against random baseline
"""

import sys, os, random, math
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def collect_barrier_values(N, DW0=1):
    """Collect Da13 and DW16 values from N random Wang cascades."""
    Da13_vals = []
    DW16_vals = []
    De17_vals = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1, DW0)

        # Da13
        Da13_val = da(states_n, states_f, 13)
        Da13_vals.append(Da13_val)

        # DW16 from schedule
        Wn_sched = schedule(Wn)
        Wf_sched = schedule(Wf)
        DW16_val = (Wf_sched[16] - Wn_sched[16]) & MASK
        DW16_vals.append(DW16_val)

        # De17 = Da13 + DW16 (mod 2^32)
        De17_val = de(states_n, states_f, 17)
        De17_vals.append(De17_val)

    return Da13_vals, DW16_vals, De17_vals

def doubling_constant(A, B):
    """Measure |A+B|/max(|A|,|B|) using sampled sumset."""
    sumset = set()
    for a in A:
        for b in B:
            sumset.add((a + b) & MASK)
    return len(sumset) / max(len(set(A)), len(set(B)))

def doubling_constant_sampled(A, B, samples=100000):
    """Sampled doubling constant for large sets."""
    sumset = set()
    A_list = list(A) if not isinstance(A, list) else A
    B_list = list(B) if not isinstance(B, list) else B
    for _ in range(samples):
        a = random.choice(A_list)
        b = random.choice(B_list)
        sumset.add((a + b) & MASK)
    # Estimate: if truly random, |A+B| should be close to min(|A|*|B|, 2^32)
    return len(sumset), samples

def additive_energy(A, sample_size=5000):
    """Estimate additive energy E(A) = |{(a1,a2,a3,a4): a1+a2=a3+a4}|.
    Normalized: E(A)/|A|^3. For random set: ~1/2^32. For structured: >> 1/2^32."""
    A_list = list(A) if not isinstance(A, list) else A
    if len(A_list) > sample_size:
        A_list = random.sample(A_list, sample_size)

    # Count sum frequencies
    sum_counts = Counter()
    for i in range(len(A_list)):
        for j in range(i, len(A_list)):
            s = (A_list[i] + A_list[j]) & MASK
            sum_counts[s] += 1

    # E(A) = sum of count^2
    energy = sum(c * c for c in sum_counts.values())
    n = len(A_list)
    # Normalized by |A|^3
    normalized = energy / (n ** 3) if n > 0 else 0

    return energy, normalized

def collision_count(vals):
    """Count collisions (identical values) in a list."""
    c = Counter(vals)
    collisions = sum(v * (v - 1) // 2 for v in c.values())
    return collisions, len(c)

def arithmetic_progression_test(vals, max_d=1000, min_len=5):
    """Search for arithmetic progressions in the set."""
    val_set = set(vals)
    found = []
    vals_sample = random.sample(list(val_set), min(500, len(val_set)))

    for start in vals_sample:
        for d in range(1, max_d):
            length = 1
            current = start
            while True:
                current = (current + d) & MASK
                if current in val_set:
                    length += 1
                else:
                    break
            if length >= min_len:
                found.append((start, d, length))

    return found

def bit_distribution(vals):
    """Analyze per-bit distribution (bias from 0.5)."""
    n = len(vals)
    biases = []
    for bit in range(32):
        ones = sum(1 for v in vals if (v >> bit) & 1)
        bias = ones / n - 0.5
        biases.append(bias)
    return biases

def random_baseline(N):
    """Generate random baseline for comparison."""
    return [random.randint(0, MASK) for _ in range(N)]

def main():
    random.seed(42)
    N = 5000

    print("=" * 70)
    print("EXPERIMENT 1: ADDITIVE COMBINATORICS OF SHA-256 BARRIER")
    print("=" * 70)
    print(f"\nGenerating {N} Wang cascade pairs...")

    Da13_vals, DW16_vals, De17_vals = collect_barrier_values(N)
    rand_A = random_baseline(N)
    rand_B = random_baseline(N)

    # --- Test 1: Collision count (uniqueness) ---
    print("\n--- TEST 1: COLLISION COUNT (uniqueness) ---")
    col_da, uniq_da = collision_count(Da13_vals)
    col_dw, uniq_dw = collision_count(DW16_vals)
    col_de, uniq_de = collision_count(De17_vals)
    col_ra, uniq_ra = collision_count(rand_A)

    print(f"Da13:  {uniq_da}/{N} unique, {col_da} collisions")
    print(f"DW16:  {uniq_dw}/{N} unique, {col_dw} collisions")
    print(f"De17:  {uniq_de}/{N} unique, {col_de} collisions")
    print(f"Random: {uniq_ra}/{N} unique, {col_ra} collisions")
    print(f"Expected collisions (birthday): ~{N*(N-1)//(2*(2**32))} for N={N}")

    # --- Test 2: Bit distribution ---
    print("\n--- TEST 2: PER-BIT BIAS ---")
    bias_da = bit_distribution(Da13_vals)
    bias_dw = bit_distribution(DW16_vals)
    bias_rand = bit_distribution(rand_A)

    max_bias_da = max(abs(b) for b in bias_da)
    max_bias_dw = max(abs(b) for b in bias_dw)
    max_bias_rand = max(abs(b) for b in bias_rand)
    avg_bias_da = sum(abs(b) for b in bias_da) / 32
    avg_bias_dw = sum(abs(b) for b in bias_dw) / 32
    avg_bias_rand = sum(abs(b) for b in bias_rand) / 32

    print(f"Da13:   max_bias={max_bias_da:.6f}, avg_bias={avg_bias_da:.6f}")
    print(f"DW16:   max_bias={max_bias_dw:.6f}, avg_bias={avg_bias_dw:.6f}")
    print(f"Random: max_bias={max_bias_rand:.6f}, avg_bias={avg_bias_rand:.6f}")
    expected_bias = 1 / (2 * math.sqrt(N))
    print(f"Expected (1/(2√N)): {expected_bias:.6f}")

    # Da13 per-bit biases detail
    notable_da = [(i, bias_da[i]) for i in range(32) if abs(bias_da[i]) > 3 * expected_bias]
    if notable_da:
        print(f"\nDa13 notable biases (>3σ):")
        for bit, bias in notable_da:
            print(f"  bit {bit}: bias={bias:+.6f} ({abs(bias)/expected_bias:.1f}σ)")

    notable_dw = [(i, bias_dw[i]) for i in range(32) if abs(bias_dw[i]) > 3 * expected_bias]
    if notable_dw:
        print(f"\nDW16 notable biases (>3σ):")
        for bit, bias in notable_dw:
            print(f"  bit {bit}: bias={bias:+.6f} ({abs(bias)/expected_bias:.1f}σ)")

    # --- Test 3: Additive energy ---
    print("\n--- TEST 3: ADDITIVE ENERGY ---")
    sample = 2000
    e_da, en_da = additive_energy(Da13_vals, sample)
    e_dw, en_dw = additive_energy(DW16_vals, sample)
    e_rand, en_rand = additive_energy(rand_A, sample)

    print(f"Da13:   E={e_da:,}, E/|A|^3 = {en_da:.10f}")
    print(f"DW16:   E={e_dw:,}, E/|A|^3 = {en_dw:.10f}")
    print(f"Random: E={e_rand:,}, E/|A|^3 = {en_rand:.10f}")
    print(f"Expected E/|A|^3 for random: ~{1/2**32:.10f}")

    ratio_da = en_da / en_rand if en_rand > 0 else float('inf')
    ratio_dw = en_dw / en_rand if en_rand > 0 else float('inf')
    print(f"\nRatio Da13/random: {ratio_da:.4f}")
    print(f"Ratio DW16/random: {ratio_dw:.4f}")
    if ratio_da > 2.0 or ratio_dw > 2.0:
        print("*** SIGNAL: Additive energy significantly above random! ***")

    # --- Test 4: Sampled doubling constant ---
    print("\n--- TEST 4: DOUBLING CONSTANT (sampled) ---")
    n_sample = min(1000, N)
    Da_sample = Da13_vals[:n_sample]
    DW_sample = DW16_vals[:n_sample]
    rand_sA = rand_A[:n_sample]
    rand_sB = rand_B[:n_sample]

    dc_real = doubling_constant(Da_sample, [(-x) & MASK for x in DW_sample])
    dc_rand = doubling_constant(rand_sA, rand_sB)

    print(f"DC(Da13, -DW16):  {dc_real:.4f}")
    print(f"DC(random, random): {dc_rand:.4f}")
    print(f"Theoretical max (random): ~{min(n_sample**2, 2**32)/n_sample:.1f}")

    if dc_real < dc_rand * 0.9:
        print(f"*** SIGNAL: Doubling constant {(1-dc_real/dc_rand)*100:.1f}% below random! ***")

    # --- Test 5: Arithmetic progressions ---
    print("\n--- TEST 5: ARITHMETIC PROGRESSIONS ---")
    aps_da = arithmetic_progression_test(Da13_vals, max_d=500, min_len=4)
    aps_rand = arithmetic_progression_test(rand_A, max_d=500, min_len=4)

    print(f"APs found in Da13 (len≥4): {len(aps_da)}")
    print(f"APs found in random (len≥4): {len(aps_rand)}")
    if aps_da:
        max_ap = max(aps_da, key=lambda x: x[2])
        print(f"Longest AP in Da13: start=0x{max_ap[0]:08x}, d={max_ap[1]}, len={max_ap[2]}")

    # --- Test 6: Cross-correlation Da13 vs DW16 ---
    print("\n--- TEST 6: CROSS-CORRELATION Da13 vs DW16 ---")
    # Do they share more common values than random?
    da_set = set(Da13_vals)
    dw_neg_set = set((-x) & MASK for x in DW16_vals)
    intersection = da_set & dw_neg_set

    rand_set_a = set(rand_A)
    rand_set_b = set(rand_B)
    rand_intersection = rand_set_a & rand_set_b

    print(f"|Da13 ∩ (-DW16)|: {len(intersection)}")
    print(f"|rand_A ∩ rand_B|: {len(rand_intersection)}")
    expected_int = len(da_set) * len(dw_neg_set) / 2**32
    print(f"Expected (birthday): {expected_int:.1f}")

    if len(intersection) > 2 * expected_int:
        print("*** SIGNAL: Intersection significantly above birthday! ***")
        print("These are near-collision candidates at round 17!")
        for val in list(intersection)[:5]:
            print(f"  Da13=DW16=0x{val:08x}")

    # --- Test 7: Fourier concentration ---
    print("\n--- TEST 7: FOURIER CONCENTRATION ---")
    # Measure if Da13 values cluster in Fourier space
    # Using small Fourier coefficients mod small primes
    for p in [251, 509, 1021]:
        counts_da = Counter(v % p for v in Da13_vals)
        counts_rand = Counter(v % p for v in rand_A)

        # Chi-squared statistic
        chi2_da = sum((counts_da.get(i, 0) - N/p)**2 / (N/p) for i in range(p))
        chi2_rand = sum((counts_rand.get(i, 0) - N/p)**2 / (N/p) for i in range(p))

        print(f"  mod {p}: χ²(Da13)={chi2_da:.1f}, χ²(rand)={chi2_rand:.1f}, "
              f"ratio={chi2_da/max(chi2_rand,1):.3f}")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    signals = []
    if ratio_da > 1.5:
        signals.append(f"Additive energy Da13: {ratio_da:.2f}x random")
    if ratio_dw > 1.5:
        signals.append(f"Additive energy DW16: {ratio_dw:.2f}x random")
    if dc_real < dc_rand * 0.9:
        signals.append(f"Doubling constant: {dc_real:.2f} < {dc_rand:.2f}")
    if len(intersection) > 2 * expected_int:
        signals.append(f"Intersection: {len(intersection)} > {2*expected_int:.0f}")
    if notable_da:
        signals.append(f"Da13 bit biases: {len(notable_da)} bits above 3σ")

    if signals:
        print("SIGNALS DETECTED:")
        for s in signals:
            print(f"  * {s}")
    else:
        print("NO SIGNALS: Da13 and DW16 appear random (additive structure absent)")

    print(f"\nVerdict: Doubling constant {'BELOW' if dc_real < dc_rand * 0.9 else 'AT'} random level")

if __name__ == "__main__":
    main()
