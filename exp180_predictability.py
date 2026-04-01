#!/usr/bin/env python3
"""
EXP 180: PREDICTABILITY MINING — Every percent above 50% counts

From dead zone inventory:
- Bit 18: lag-1 memory = 0.113 → predict at 56%
- Bit 11: highway (80.6% alive) → predict "alive" at 80.6%
- Bit 7: desert (69.2% alive) → predict "alive" at 69.2%
- dH dips: don't bounce → predict next dH from current

GOAL: Build a PREDICTOR for state bits at round r+1 from round r.
Any prediction > 50% = information = potential advantage.

Combine ALL predictable features into one predictor.
Measure: total bits of predictability per round in dead zone.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extended_rounds(M, n_rounds):
    W = schedule(M)
    state = list(IV)
    states = [list(state)]
    for r in range(n_rounds):
        state = sha256_round(state, W[r % 64], K[r % 64])
        states.append(list(state))
    return states

def bit(val, pos):
    return (val >> pos) & 1

def measure_per_bit_predictability(N_msg=20, N_rounds=200):
    """For each of 256 state bits: how predictable is bit[r+1] from state[r]?"""
    print(f"\n{'='*60}")
    print(f"PER-BIT PREDICTABILITY (N_msg={N_msg}, {N_rounds} rounds)")
    print(f"{'='*60}")

    # For each bit position: measure P(bit[r+1]=1 | bit[r]=1) and P(bit[r+1]=1 | bit[r]=0)
    # If these differ → bit is predictable from its own previous value

    counts = np.zeros((256, 2, 2))  # [bit_pos][prev_val][next_val]

    for _ in range(N_msg):
        M = random_w16()
        states = extended_rounds(M, N_rounds)

        for r in range(50, N_rounds):  # Deep in dead zone
            for w in range(8):
                for b in range(32):
                    idx = w * 32 + b
                    prev = bit(states[r][w], b)
                    nxt = bit(states[r+1][w], b)
                    counts[idx, prev, nxt] += 1

    # Compute predictability per bit
    predictabilities = []
    for idx in range(256):
        # P(next=1 | prev=1)
        total_1 = counts[idx, 1, 0] + counts[idx, 1, 1]
        p_11 = counts[idx, 1, 1] / total_1 if total_1 > 0 else 0.5

        # P(next=1 | prev=0)
        total_0 = counts[idx, 0, 0] + counts[idx, 0, 1]
        p_01 = counts[idx, 0, 1] / total_0 if total_0 > 0 else 0.5

        # Best prediction accuracy:
        # If prev=1: predict next=1 if p_11>0.5, else predict 0
        acc_given_1 = max(p_11, 1 - p_11)
        acc_given_0 = max(p_01, 1 - p_01)

        # Overall: P(prev=1) ≈ 0.5
        overall_acc = (acc_given_1 + acc_given_0) / 2
        advantage = overall_acc - 0.5  # Bits of advantage over random

        predictabilities.append({
            'idx': idx, 'w': idx // 32, 'b': idx % 32,
            'p_11': p_11, 'p_01': p_01,
            'accuracy': overall_acc, 'advantage': advantage
        })

    # Sort by advantage
    predictabilities.sort(key=lambda x: -x['advantage'])

    print(f"\n  TOP 20 MOST PREDICTABLE BITS:")
    print(f"  {'Word':>4} {'Bit':>4} | {'P(1|1)':>7} {'P(1|0)':>7} | {'Accuracy':>8} {'Advant':>7} | {'Note'}")
    print(f"  " + "-" * 65)

    total_advantage = 0
    for p in predictabilities[:20]:
        note = ""
        if p['b'] == 18: note = "← MEMORY BIT"
        elif p['b'] == 11: note = "← HIGHWAY"
        elif p['b'] == 7: note = "← DESERT"
        elif p['b'] == 14: note = "← memory#2"
        elif p['b'] == 25: note = "← desert#2"

        print(f"  {p['w']:>4} {p['b']:>4} | {p['p_11']:>7.4f} {p['p_01']:>7.4f} | "
              f"{p['accuracy']:>8.4f} {p['advantage']:>7.4f} | {note}")

    # Total predictability across ALL 256 bits
    for p in predictabilities:
        total_advantage += p['advantage']

    print(f"\n  TOTAL ADVANTAGE ACROSS 256 BITS:")
    print(f"    Sum of per-bit advantages: {total_advantage:.4f}")
    print(f"    = {total_advantage:.2f} effectively predictable bits per round")
    print(f"    (0 = no advantage, 256 = perfect prediction)")

    # Distribution
    advs = np.array([p['advantage'] for p in predictabilities])
    print(f"\n  Distribution of advantages:")
    print(f"    Mean: {advs.mean():.6f}")
    print(f"    Max:  {advs.max():.6f}")
    print(f"    Bits with > 1% advantage: {np.sum(advs > 0.01)}")
    print(f"    Bits with > 2% advantage: {np.sum(advs > 0.02)}")

    return predictabilities

def measure_cross_bit_prediction(N_msg=15, N_rounds=200):
    """Can we predict bit[r+1] from OTHER bits at round r?"""
    print(f"\n{'='*60}")
    print(f"CROSS-BIT PREDICTION (N_msg={N_msg})")
    print(f"{'='*60}")

    # For target bits: can we predict them from NEIGHBOR bits?
    # Target: bit 0 of word 0 (a_new)
    # a_new depends on T1 and T2, which depend on ALL words at round r

    # Collect data: 256 input bits at round r → 1 output bit at round r+1
    target_bits = [(0, 0), (0, 18), (0, 11), (0, 7)]  # word, bit

    for tw, tb in target_bits:
        X = []  # Features: all 256 bits at round r
        y = []  # Target: bit (tw, tb) at round r+1

        for _ in range(N_msg):
            M = random_w16()
            states = extended_rounds(M, N_rounds)

            for r in range(50, N_rounds):
                features = []
                for w in range(8):
                    for b in range(32):
                        features.append(bit(states[r][w], b))
                X.append(features)
                y.append(bit(states[r+1][tw], tb))

        X = np.array(X, dtype=float)
        y = np.array(y, dtype=float)

        # Simple predictor: which SINGLE input bit best predicts the target?
        best_corr = 0; best_predictor = -1
        for j in range(256):
            c = np.corrcoef(X[:, j], y)[0, 1]
            if not np.isnan(c) and abs(c) > abs(best_corr):
                best_corr = c; best_predictor = j

        pred_w = best_predictor // 32; pred_b = best_predictor % 32
        # Prediction accuracy using best single bit
        if best_corr > 0:
            acc = 0.5 + abs(best_corr) / 2
        else:
            acc = 0.5 + abs(best_corr) / 2

        print(f"\n  Target: word {tw} bit {tb}")
        print(f"    Best single predictor: word {pred_w} bit {pred_b} "
              f"(corr={best_corr:+.4f}, accuracy={acc:.4f})")

        # Top 5 predictors
        all_corrs = []
        for j in range(256):
            c = np.corrcoef(X[:, j], y)[0, 1]
            if not np.isnan(c):
                all_corrs.append((abs(c), c, j))
        all_corrs.sort(reverse=True)

        print(f"    Top 5 single-bit predictors:")
        for ac, c, j in all_corrs[:5]:
            pw = j // 32; pb = j % 32
            role = ""
            if pw == tw and pb == tb: role = "(SELF)"
            elif pw == tw: role = f"(same word)"
            print(f"      w{pw}b{pb:>2}: corr={c:+.4f} {role}")

def measure_shift_register_prediction(N_msg=20, N_rounds=200):
    """Use shift register: b[r+1] = a[r] EXACTLY.
    So: we can predict 6/8 words PERFECTLY.
    Only a_new and e_new need prediction."""
    print(f"\n{'='*60}")
    print(f"SHIFT REGISTER PREDICTION")
    print(f"{'='*60}")

    print(f"""
  KNOWN (from shift register, corr=1.000):
    b[r+1] = a[r]   → 32 bits PERFECTLY predicted
    c[r+1] = b[r]   → 32 bits PERFECTLY predicted
    d[r+1] = c[r]   → 32 bits PERFECTLY predicted
    f[r+1] = e[r]   → 32 bits PERFECTLY predicted
    g[r+1] = f[r]   → 32 bits PERFECTLY predicted
    h[r+1] = g[r]   → 32 bits PERFECTLY predicted

    Total FREE predictions: 6 × 32 = 192 bits (75% of state!)

  UNKNOWN (need to predict):
    a_new[r+1] = T1 + T2 = complex function of state[r] + W[r] + K[r]
    e_new[r+1] = d + T1  = complex function of state[r] + W[r] + K[r]

    Total UNKNOWN: 2 × 32 = 64 bits (25% of state)
    """)

    # Verify: are a_new and e_new predictable from state[r]?
    print(f"  Prediction of a_new and e_new (N={N_msg}):")

    for target_word, target_name in [(0, "a_new"), (4, "e_new")]:
        correct = 0; total = 0

        for _ in range(N_msg):
            M = random_w16()
            W = schedule(M)
            states = extended_rounds(M, N_rounds)

            for r in range(50, N_rounds):
                # "Predict" using majority vote of state bits
                # (simplest possible predictor)
                for b in range(32):
                    # Predict: next bit = same as current bit of SAME word
                    prediction = bit(states[r][target_word], b)
                    actual = bit(states[r+1][target_word], b)
                    if prediction == actual:
                        correct += 1
                    total += 1

        acc = correct / total if total > 0 else 0.5
        print(f"    {target_name}: predict(same bit) accuracy = {acc:.4f} ({acc*100:.1f}%)")

    # Now: predict using KNOWN a[r] (which becomes b[r+1], c[r+2], d[r+3])
    # and KNOWN e[r] (f[r+1], g[r+2], h[r+3])
    # In the round function:
    # a_new = T1 + T2
    # T1 = h + Σ₁(e) + Ch(e,f,g) + K[r] + W[r]
    # T2 = Σ₀(a) + Maj(a,b,c)
    # ALL inputs are known at round r (state + W + K)!

    print(f"\n  KEY INSIGHT:")
    print(f"    ALL inputs to a_new and e_new are KNOWN at round r:")
    print(f"      state[r] = known (8 words)")
    print(f"      W[r%64]  = known (from message, pre-computable)")
    print(f"      K[r%64]  = known (constant)")
    print(f"")
    print(f"    Therefore: a_new and e_new are 100% DETERMINISTIC!")
    print(f"    Given state[r], W[r], K[r] → state[r+1] is EXACTLY determined.")
    print(f"")
    print(f"    This means: state[r+1] is 100% predictable from state[r].")
    print(f"    SHA-256 IS deterministic — there's no randomness inside!")
    print(f"")
    print(f"    The 'unpredictability' comes from NOT KNOWING state[r].")
    print(f"    If we know state[r] → we know ALL future states.")
    print(f"    If we DON'T know state[r] → we can't predict anything.")
    print(f"")
    print(f"    PREDICTABILITY = 100% if you know the state")
    print(f"    PREDICTABILITY = 50% if you DON'T know the state")
    print(f"    There's NO middle ground.")

def measure_dh_prediction(N_rounds=1000):
    """Can we predict dH[r+1] from dH[r]?"""
    print(f"\n{'='*60}")
    print(f"dH PREDICTION (lag-1 regression)")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    dH_trace = []
    for r in range(20, N_rounds):
        dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(8))
        dH_trace.append(dH)

    d = np.array(dH_trace)

    # Linear regression: dH[r+1] = a * dH[r] + b
    X = d[:-1]; Y = d[1:]
    slope, intercept = np.polyfit(X, Y, 1)
    Y_pred = slope * X + intercept
    residuals = Y - Y_pred
    r_squared = 1 - np.var(residuals) / np.var(Y)

    print(f"\n  dH[r+1] = {slope:.4f} × dH[r] + {intercept:.2f}")
    print(f"  R² = {r_squared:.4f}")
    print(f"  Prediction error: ±{residuals.std():.2f} (vs dH std={d.std():.2f})")
    print(f"  Error reduction: {(1 - residuals.std()/d.std())*100:.1f}%")

    # At dH DIPS: prediction is better?
    dip_mask = X < 115
    if dip_mask.sum() > 10:
        Y_dip = Y[dip_mask]; X_dip = X[dip_mask]
        pred_dip = slope * X_dip + intercept
        err_dip = np.abs(Y_dip - pred_dip).mean()
        err_all = np.abs(residuals).mean()
        print(f"\n  AT DIPS (dH<115, n={dip_mask.sum()}):")
        print(f"    Prediction error: ±{err_dip:.2f} (overall: ±{err_all:.2f})")
        print(f"    dH after dip: predicted={pred_dip.mean():.1f}, actual={Y_dip.mean():.1f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 180: PREDICTABILITY MINING")
    print("=" * 60)

    preds = measure_per_bit_predictability(N_msg=15, N_rounds=200)
    measure_cross_bit_prediction(N_msg=10, N_rounds=150)
    measure_shift_register_prediction(N_msg=10, N_rounds=150)
    measure_dh_prediction(N_rounds=800)

    print(f"\n{'='*60}")
    print(f"VERDICT: How much is predictable?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
