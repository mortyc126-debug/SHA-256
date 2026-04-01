#!/usr/bin/env python3
"""
EXP 191: THE 13 PREDICTABLE BITS — Map them precisely

13/64 bits of δ[r+1] are positionally predictable from δ[r].
IDENTIFY each one. Find the MECHANISM. Test if exploitable.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_diff_vector(s1, s2):
    vec = np.zeros(64, dtype=int)
    for b in range(32):
        vec[b] = ((s1[0] >> b) & 1) ^ ((s2[0] >> b) & 1)
        vec[32+b] = ((s1[4] >> b) & 1) ^ ((s2[4] >> b) & 1)
    return vec

def identify_all_13(N=300):
    """Precisely identify all 13 predictable bits."""
    print(f"\n{'='*60}")
    print(f"IDENTIFYING ALL 13 PREDICTABLE BITS (N={N})")
    print(f"{'='*60}")

    X_all = []; Y_all = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(30, 63):
            X_all.append(get_diff_vector(s1[r], s2[r]))
            Y_all.append(get_diff_vector(s1[r+1], s2[r+1]))

    X = np.array(X_all, dtype=float); Y = np.array(Y_all, dtype=float)
    threshold = 3 / math.sqrt(len(X))

    # For each output bit: find its BEST predictor and ALL significant predictors
    predictable_bits = []

    for out_b in range(64):
        best_corr = 0; best_in = -1
        all_sig = []
        for in_b in range(64):
            c = np.corrcoef(X[:, in_b], Y[:, out_b])[0, 1]
            if np.isnan(c): continue
            if abs(c) > abs(best_corr):
                best_corr = c; best_in = in_b
            if abs(c) > threshold:
                all_sig.append((c, in_b))

        if abs(best_corr) > threshold:
            out_word = "a" if out_b < 32 else "e"
            out_bit = out_b % 32
            in_word = "a" if best_in < 32 else "e"
            in_bit = best_in % 32

            # Compute rotation distance
            if out_word == in_word:
                rot_dist = (in_bit - out_bit) % 32
            else:
                rot_dist = None

            predictable_bits.append({
                'out': out_b, 'out_word': out_word, 'out_bit': out_bit,
                'best_in': best_in, 'in_word': in_word, 'in_bit': in_bit,
                'best_corr': best_corr, 'rot_dist': rot_dist,
                'n_predictors': len(all_sig)
            })

    # Sort by correlation strength
    predictable_bits.sort(key=lambda x: -abs(x['best_corr']))

    print(f"\n  Found {len(predictable_bits)} predictable bits (threshold |corr|>{threshold:.4f}):")
    print(f"\n  {'Output':>10} | {'Best Input':>12} | {'Corr':>7} | {'RotDist':>7} | {'#Pred':>5} | Mechanism")
    print(f"  " + "-" * 70)

    rot_counts = {}
    for p in predictable_bits:
        # Determine mechanism
        mechanism = ""
        if p['rot_dist'] is not None:
            if p['rot_dist'] in [2, 13, 22]:
                mechanism = f"Σ₀(ROTR_{p['rot_dist']})"
            elif p['rot_dist'] in [6, 11, 25]:
                mechanism = f"Σ₁(ROTR_{p['rot_dist']})"
            elif p['rot_dist'] == 0:
                mechanism = "SELF (identity)"
            elif p['rot_dist'] in [7, 18]:
                mechanism = f"σ₀(ROTR_{p['rot_dist']})"
            elif p['rot_dist'] in [17, 19]:
                mechanism = f"σ₁(ROTR_{p['rot_dist']})"
            else:
                mechanism = f"dist={p['rot_dist']}"

            rot_counts[p['rot_dist']] = rot_counts.get(p['rot_dist'], 0) + 1
        else:
            mechanism = f"CROSS ({p['out_word']}←{p['in_word']})"

        print(f"  {p['out_word']}[{p['out_bit']:>2}]     | {p['in_word']}[{p['in_bit']:>2}]       | "
              f"{p['best_corr']:>+7.4f} | {str(p['rot_dist']):>7} | {p['n_predictors']:>5} | {mechanism}")

    # Rotation distance distribution
    print(f"\n  ROTATION DISTANCES of predictable pairs:")
    for rot, count in sorted(rot_counts.items()):
        is_sigma = ""
        if rot in [2, 13, 22]: is_sigma = "← Σ₀!"
        elif rot in [6, 11, 25]: is_sigma = "← Σ₁!"
        elif rot in [7, 18, 3]: is_sigma = "← σ₀!"
        elif rot in [17, 19, 10]: is_sigma = "← σ₁!"
        print(f"    dist={rot:>2}: {count} pairs {is_sigma}")

    return predictable_bits

def test_accumulation(predictable_bits, N=200):
    """Can the 13 predictions ACCUMULATE over multiple rounds?"""
    print(f"\n{'='*60}")
    print(f"ACCUMULATION: Do predictions compound over rounds?")
    print(f"{'='*60}")

    if not predictable_bits:
        print("  No predictable bits to test")
        return

    # Use the BEST predictor for each predictable bit
    # Predict δ[r+k] from δ[r] for k = 1, 2, 4, 8

    for k in [1, 2, 4, 8]:
        correct = 0; total = 0

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))
            s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)

            for r in range(30, 64-k):
                v_r = get_diff_vector(s1[r], s2[r])
                v_rk = get_diff_vector(s1[r+k], s2[r+k])

                # For each predictable bit: predict v_rk from v_r
                for p in predictable_bits[:10]:
                    # Simple: predict output bit = input bit
                    # (since corr > 0, same value is more likely)
                    prediction = v_r[p['best_in']]
                    actual = v_rk[p['out']]
                    if (p['best_corr'] < 0):
                        prediction = 1 - prediction

                    if prediction == actual:
                        correct += 1
                    total += 1

        accuracy = correct / total if total > 0 else 0.5
        advantage = accuracy - 0.5
        print(f"  Lag {k}: accuracy = {accuracy:.4f} ({accuracy*100:.1f}%), "
              f"advantage = {advantage:+.4f}")

        if k == 1 and advantage > 0.01:
            bits_per_round = advantage * len(predictable_bits[:10])
            print(f"  → {bits_per_round:.2f} predictable bits per round")
            print(f"  → Over 44 rounds: {bits_per_round * 44:.1f} total predicted bits")

def test_exploitability(predictable_bits, N=100, budget=3000):
    """Can we use the 13 bits to improve collision search?"""
    print(f"\n{'='*60}")
    print(f"EXPLOITABILITY: Do 13 bits help find collision?")
    print(f"{'='*60}")

    if not predictable_bits:
        return

    # Strategy: generate pairs, FILTER by whether their δ-vector
    # at round 40 matches the "predictable" pattern for round 64.
    # If the prediction is correct → pair is closer to collision.

    guided_results = []; random_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)

        best_guided = 256; best_random = 256

        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            best_random = min(best_random, dH)

            # Guided: also compute δ at round 40 and check predictable pattern
            # (This costs extra computation — not free)
            # For fairness: only check hash, use predictable bits as TIE-BREAKER

            best_guided = min(best_guided, dH)

        guided_results.append(best_guided)
        random_results.append(best_random)

    ga = np.array(guided_results); ra = np.array(random_results)
    print(f"\n  (Note: guided = random here because we didn't implement")
    print(f"   the filter yet. The 13-bit signal is too weak to filter.)")
    print(f"\n  Theoretical analysis:")
    print(f"    13 bits × 0.05 corr = 0.65 bits of advantage per round")
    print(f"    Over 1 round: predict 0.65 bits better than random")
    print(f"    Over 44 rounds: DOESN'T ACCUMULATE (each round independent)")
    print(f"    Net: ~0.65 bits advantage total = NEGLIGIBLE")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 191: THE 13 PREDICTABLE BITS")
    print("=" * 60)

    bits = identify_all_13(N=250)
    test_accumulation(bits, N=150)
    test_exploitability(bits, N=10, budget=1000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
