#!/usr/bin/env python3
"""
EXP 138: 10 ★-Invariant Candidates — Decay Rate Measurement

From Theorem ★-6: exact invariants impossible (+ vs ROTR incompatibility).
But APPROXIMATE invariants may survive. Test all 10 candidates.

For each: measure ε_r (error per round) for 1-bit difference pairs.
If ε_r < 1 bit/round → invariant survives beyond round 35 barrier.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def compute_all_invariants(s1, s2):
    """Compute all 10 invariant candidates for a state pair."""
    vals = {}

    # Per-word quantities
    dxor = [s1[w] ^ s2[w] for w in range(8)]
    dand = [s1[w] & s2[w] for w in range(8)]
    darith = [(s1[w] - s2[w]) & MASK for w in range(8)]

    # I1: HW(δXOR)
    vals['I1_HW_dXOR'] = sum(hw(d) for d in dxor)

    # I2: parity(δXOR) — XOR of all bits of all δXOR words
    p = 0
    for d in dxor:
        p ^= hw(d) % 2  # parity of each word
    vals['I2_parity_dXOR'] = p

    # I3: HW(δAND)
    vals['I3_HW_dAND'] = sum(hw(d) for d in dand)

    # I4: HW(δ_arith)
    vals['I4_HW_darith'] = sum(hw(d) for d in darith)

    # I5: Σ(S1-S2) mod 3
    total_arith = sum(darith[w] for w in range(8))
    vals['I5_darith_mod3'] = total_arith % 3

    # I6: HW(δXOR & δAND) — carry-AND overlap
    vals['I6_overlap'] = sum(hw(dxor[w] & dand[w]) for w in range(8))

    # I7: HW(δXOR) - 2·HW(δAND) — ★-balance
    vals['I7_star_balance'] = vals['I1_HW_dXOR'] - 2 * vals['I3_HW_dAND']

    # I8: ★-total = XOR of all δXOR words
    star_total = 0
    for d in dxor:
        star_total ^= d
    vals['I8_star_total_HW'] = hw(star_total)

    # I9: P-chain count (number of P bits in GKP of s1[0] with s2[0])
    # Use first word as representative
    gkp = carry_gkp_classification(s1[0], s2[0])
    vals['I9_nP'] = gkp.count('P')

    # I10: δXOR mod 3 (sum of trit values)
    mod3_sum = 0
    for d in dxor:
        mod3_sum += d % 3
    vals['I10_dXOR_mod3'] = mod3_sum % 3

    return vals

def measure_decay_rates(N=300):
    """Measure decay of all 10 invariants through 64 rounds."""
    print(f"\n{'='*70}")
    print(f"10 ★-INVARIANT CANDIDATES: DECAY MEASUREMENT (N={N})")
    print(f"{'='*70}")

    inv_names = ['I1_HW_dXOR', 'I2_parity_dXOR', 'I3_HW_dAND',
                 'I4_HW_darith', 'I5_darith_mod3', 'I6_overlap',
                 'I7_star_balance', 'I8_star_total_HW', 'I9_nP',
                 'I10_dXOR_mod3']

    # For each round, collect invariant values
    rounds_to_check = list(range(0, 21)) + [24, 28, 32, 40, 48, 56, 60, 62, 63, 64]
    data = {name: {r: [] for r in rounds_to_check} for name in inv_names}

    for trial in range(N):
        M1 = random_w16()
        M2 = list(M1)
        # 1-bit difference in W[15] (latest possible → max invariant lifetime)
        M2[15] ^= (1 << random.randint(0, 31))

        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        for r in rounds_to_check:
            vals = compute_all_invariants(s1_all[r], s2_all[r])
            for name in inv_names:
                data[name][r].append(vals[name])

    # Compute statistics
    print(f"\n  1-bit diff in W[15] (latest first-affected round = 15)")
    print(f"\n  MEAN VALUES PER ROUND:")
    print(f"  {'Round':>5}", end="")
    for name in inv_names:
        short = name.split('_', 1)[0]
        print(f" | {short:>7}", end="")
    print()
    print(f"  " + "-" * (7 + 10 * len(inv_names)))

    for r in [0, 1, 5, 10, 14, 15, 16, 17, 18, 19, 20, 32, 64]:
        if r not in rounds_to_check:
            continue
        print(f"  {r:>5}", end="")
        for name in inv_names:
            arr = np.array(data[name][r])
            print(f" | {arr.mean():>7.2f}", end="")
        print()

    # DECAY ANALYSIS: for each invariant, compute correlation between
    # value at round 0 and value at round r
    print(f"\n  CORRELATION WITH ROUND-0 VALUE (persistence):")
    print(f"  {'Round':>5}", end="")
    for name in inv_names:
        short = name.split('_', 1)[0]
        print(f" | {short:>7}", end="")
    print()
    print(f"  " + "-" * (7 + 10 * len(inv_names)))

    for r in [5, 10, 14, 15, 16, 17, 18, 20, 32, 64]:
        if r not in rounds_to_check:
            continue
        print(f"  {r:>5}", end="")
        for name in inv_names:
            v0 = np.array(data[name][0], dtype=float)
            vr = np.array(data[name][r], dtype=float)
            if v0.std() > 0 and vr.std() > 0:
                corr = np.corrcoef(v0, vr)[0, 1]
                if np.isnan(corr):
                    corr = 0
            else:
                corr = 1.0 if np.array_equal(v0, vr) else 0.0
            print(f" | {corr:>+7.3f}", end="")
        print()

    # STABILITY SCORE: at which round does correlation drop below 0.1?
    print(f"\n  STABILITY: round where corr(I₀, I_r) < 0.1")
    stability = {}
    for name in inv_names:
        v0 = np.array(data[name][0], dtype=float)
        death_round = 0
        for r in sorted(rounds_to_check):
            if r == 0:
                continue
            vr = np.array(data[name][r], dtype=float)
            if v0.std() > 0 and vr.std() > 0:
                corr = np.corrcoef(v0, vr)[0, 1]
                if np.isnan(corr):
                    corr = 0
            else:
                corr = 1.0 if np.array_equal(v0, vr) else 0.0
            if abs(corr) < 0.1:
                death_round = r
                break
        else:
            death_round = 65  # Survived all rounds!

        stability[name] = death_round
        short = name.split('_', 1)[0]
        status = "★★★ SURVIVES!" if death_round > 35 else (
                 "★★ LONG" if death_round > 20 else (
                 "★ MEDIUM" if death_round > 15 else "dies"))
        print(f"    {name:>20}: dies at round {death_round:>2} — {status}")

    # NEAR-COLLISION TEST: do invariants differ for near-collision pairs?
    print(f"\n  NEAR-COLLISION SIGNAL (random pairs, check at round 64):")
    near_data = {name: [] for name in inv_names}
    rand_data = {name: [] for name in inv_names}

    for _ in range(N * 50):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        dH = sum(hw(s1[64][w] ^ s2[64][w]) for w in range(8))

        vals = compute_all_invariants(s1[64], s2[64])

        if dH < 108:
            for name in inv_names:
                near_data[name].append(vals[name])
        elif random.random() < 0.02:
            for name in inv_names:
                rand_data[name].append(vals[name])

    print(f"  Near-collisions: {len(near_data[inv_names[0]])}")
    for name in inv_names:
        if len(near_data[name]) < 5:
            continue
        na = np.array(near_data[name], dtype=float)
        ra = np.array(rand_data[name], dtype=float)
        if len(ra) < 5:
            continue
        diff = na.mean() - ra.mean()
        pooled = math.sqrt((na.std()**2 + ra.std()**2) / 2)
        n = min(len(na), len(ra))
        z = diff / (pooled / math.sqrt(n)) if pooled > 0 else 0
        short = name.split('_', 1)[0]
        sig = "★★★" if abs(z) > 5 else ("★★" if abs(z) > 3 else "")
        print(f"    {name:>20}: near={na.mean():.2f} rand={ra.mean():.2f} Z={z:+.1f} {sig}")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 138: 10 ★-INVARIANT CANDIDATES")
    print("=" * 70)

    measure_decay_rates(N=250)

    print(f"\n{'='*70}")
    print(f"VERDICT: Which invariant survives longest?")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
