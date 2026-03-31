#!/usr/bin/env python3
"""
EXP 140: Theorem ★-9 Verification — Autocatalytic Amplification

THEORY:
  α_Ch(r)  = HW(e_{r-1} ⊕ e_{r-2}) / 32
  α_Maj(r) = HW(a_{r-1} ⊕ a_{r-2}) / 32

  α controls how fast δ amplifies.
  Small α → slow amplification → invariant survives longer.
  α is a property of ONE message, not a pair!

TEST 1: Verify δCh = δe & (f⊕g) exactly
TEST 2: Measure α per round for real SHA-256
TEST 3: Do messages with small α produce "softer" landscapes?
TEST 4: Can we FIND messages with small α cheaply?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_differential_formula(N=3000):
    """Verify: δCh = δe & (f⊕g) and δMaj = δa & (b⊕c)."""
    print(f"\n--- VERIFY DIFFERENTIAL FORMULAS (N={N}) ---")

    ch_exact = 0; maj_exact = 0

    for _ in range(N):
        e1 = random.randint(0, MASK); e2 = random.randint(0, MASK)
        f = random.randint(0, MASK); g = random.randint(0, MASK)

        # Actual δCh
        ch1 = ch(e1, f, g); ch2 = ch(e2, f, g)
        delta_ch_actual = ch1 ^ ch2

        # Formula: δe & (f⊕g)
        delta_e = e1 ^ e2
        delta_ch_formula = delta_e & (f ^ g)

        if delta_ch_actual == delta_ch_formula:
            ch_exact += 1

        # Maj
        a1 = random.randint(0, MASK); a2 = random.randint(0, MASK)
        b = random.randint(0, MASK); c = random.randint(0, MASK)

        maj1 = maj(a1, b, c); maj2 = maj(a2, b, c)
        delta_maj_actual = maj1 ^ maj2
        delta_a = a1 ^ a2
        delta_maj_formula = delta_a & (b ^ c)

        if delta_maj_actual == delta_maj_formula:
            maj_exact += 1

    print(f"  δCh  = δe & (f⊕g):   {ch_exact/N:.6f}")
    print(f"  δMaj = δa & (b⊕c):   {maj_exact/N:.6f}")

    if ch_exact == N and maj_exact == N:
        print(f"  *** BOTH FORMULAS EXACTLY VERIFIED! ***")

def measure_alpha_per_round(N=500):
    """Measure α_Ch and α_Maj per round for random messages."""
    print(f"\n--- AMPLIFICATION RATE α PER ROUND (N={N}) ---")

    alpha_ch = np.zeros((N, 64))
    alpha_maj = np.zeros((N, 64))

    for trial in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)

        for r in range(2, 64):
            # α_Ch = HW(e_{r-1} ⊕ e_{r-2}) / 32
            # e is word 4 of state
            e_prev = states[r-1][4]
            e_prev2 = states[r-2][4]
            alpha_ch[trial, r] = hw(e_prev ^ e_prev2) / 32

            # α_Maj = HW(a_{r-1} ⊕ a_{r-2}) / 32
            # a is word 0 of state
            a_prev = states[r-1][0]
            a_prev2 = states[r-2][0]
            alpha_maj[trial, r] = hw(a_prev ^ a_prev2) / 32

    print(f"  {'Round':>6} | {'α_Ch':>8} | {'α_Maj':>8} | {'α_total':>8}")
    print(f"  " + "-" * 40)

    for r in range(2, 64):
        if r < 10 or r % 8 == 0 or r > 60:
            ac = alpha_ch[:, r].mean()
            am = alpha_maj[:, r].mean()
            print(f"  {r:>6} | {ac:>8.4f} | {am:>8.4f} | {(ac+am)/2:>8.4f}")

    # Average over all rounds
    avg_ch = alpha_ch[:, 2:].mean()
    avg_maj = alpha_maj[:, 2:].mean()
    print(f"\n  Average α_Ch:  {avg_ch:.4f}")
    print(f"  Average α_Maj: {avg_maj:.4f}")
    print(f"  (0.5 = full amplification, 0 = no amplification)")

def test_alpha_predicts_landscape(N=200):
    """Does low α → softer landscape (closer near-collisions)?"""
    print(f"\n--- α PREDICTS LANDSCAPE SOFTNESS (N={N}) ---")

    # For each message M: compute average α, then find nearest collision
    msg_data = []

    for trial in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)
        H = sha256_compress(M)

        # Average α for this message
        alphas = []
        for r in range(2, 64):
            ac = hw(states[r-1][4] ^ states[r-2][4]) / 32
            am = hw(states[r-1][0] ^ states[r-2][0]) / 32
            alphas.append((ac + am) / 2)

        avg_alpha = np.mean(alphas)
        early_alpha = np.mean(alphas[:10])  # Rounds 2-11
        late_alpha = np.mean(alphas[-10:])  # Rounds 54-63

        # Find nearest neighbor (hash distance to random messages)
        min_dH = 256
        for _ in range(500):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H[w] ^ H2[w]) for w in range(8))
            min_dH = min(min_dH, dH)

        msg_data.append({
            'avg_alpha': avg_alpha,
            'early_alpha': early_alpha,
            'late_alpha': late_alpha,
            'min_dH': min_dH,
        })

    # Correlation between α and landscape softness (min_dH)
    avg_alphas = np.array([d['avg_alpha'] for d in msg_data])
    early_alphas = np.array([d['early_alpha'] for d in msg_data])
    late_alphas = np.array([d['late_alpha'] for d in msg_data])
    min_dHs = np.array([d['min_dH'] for d in msg_data])

    corr_avg = np.corrcoef(avg_alphas, min_dHs)[0, 1]
    corr_early = np.corrcoef(early_alphas, min_dHs)[0, 1]
    corr_late = np.corrcoef(late_alphas, min_dHs)[0, 1]

    print(f"  corr(avg_α, min_dH):   {corr_avg:+.4f}")
    print(f"  corr(early_α, min_dH): {corr_early:+.4f}")
    print(f"  corr(late_α, min_dH):  {corr_late:+.4f}")
    print(f"  (negative = low α → low dH = softer landscape)")

    # Binned analysis
    p25 = np.percentile(avg_alphas, 25)
    p75 = np.percentile(avg_alphas, 75)
    low_mask = avg_alphas <= p25
    high_mask = avg_alphas >= p75

    print(f"\n  Low-α messages (bottom 25%):  E[min_dH] = {min_dHs[low_mask].mean():.1f}")
    print(f"  High-α messages (top 25%):    E[min_dH] = {min_dHs[high_mask].mean():.1f}")
    print(f"  All messages:                 E[min_dH] = {min_dHs.mean():.1f}")

def test_alpha_variation(N=1000):
    """How much does α vary between messages?
    If all messages have α ≈ 0.5 → no exploitable variation.
    If some have α << 0.5 → those are special."""
    print(f"\n--- α VARIATION ACROSS MESSAGES (N={N}) ---")

    avg_alphas = []
    for _ in range(N):
        M = random_w16()
        states = sha256_rounds(M, 64)
        alphas = []
        for r in range(2, 64):
            ac = hw(states[r-1][4] ^ states[r-2][4]) / 32
            am = hw(states[r-1][0] ^ states[r-2][0]) / 32
            alphas.append((ac + am) / 2)
        avg_alphas.append(np.mean(alphas))

    arr = np.array(avg_alphas)
    print(f"  E[α] = {arr.mean():.6f}")
    print(f"  std(α) = {arr.std():.6f}")
    print(f"  min(α) = {arr.min():.6f}")
    print(f"  max(α) = {arr.max():.6f}")
    print(f"  CV = {arr.std()/arr.mean():.4f}")

    if arr.std() / arr.mean() < 0.01:
        print(f"  α is NEARLY CONSTANT across messages (CV < 1%)")
        print(f"  → No exploitable variation")
    elif arr.std() / arr.mean() > 0.1:
        print(f"  α VARIES significantly (CV > 10%)")
        print(f"  → Some messages have softer landscape!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 140: THEOREM ★-9 — AUTOCATALYTIC AMPLIFICATION")
    print("=" * 60)

    test_differential_formula(2000)
    measure_alpha_per_round(300)
    test_alpha_variation(500)
    test_alpha_predicts_landscape(150)

    print(f"\n{'='*60}")
    print(f"VERDICT: Theorem ★-9")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
