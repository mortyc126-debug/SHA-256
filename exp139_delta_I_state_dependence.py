#!/usr/bin/env python3
"""
EXP 139: Does ΔI Depend on State or Only on δW?

From Theorem ★-7: all invariants die instantly at first δW ≠ 0.
But: if the EFFECT ΔI depends only on δW (not on state S),
then ΔI is PREDICTABLE from the schedule alone.

TEST: Apply same δW to DIFFERENT states S.
  If ΔI(S₁, δW) ≈ ΔI(S₂, δW) for random S₁, S₂ → state-independent
  If ΔI varies widely → state-dependent (self-referential, blocked)

Measure for each of our invariants at the CRITICAL round (first δW).
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_invariants_short(s):
    """Quick invariant computation for a single state (vs IV)."""
    dxor = [s[w] ^ IV[w] for w in range(8)]
    dand = [s[w] & IV[w] for w in range(8)]
    darith = [(s[w] - IV[w]) & MASK for w in range(8)]

    return {
        'HW_dXOR': sum(hw(d) for d in dxor),
        'parity': sum(hw(d) % 2 for d in dxor) % 2,
        'HW_dAND': sum(hw(d) for d in dand),
        'HW_darith': sum(hw(d) for d in darith),
        'mod3': sum(darith) % 3,
        'star_balance': sum(hw(d) for d in dxor) - 2 * sum(hw(d) for d in dand),
        'star_total_HW': hw(dxor[0] ^ dxor[1] ^ dxor[2] ^ dxor[3] ^
                           dxor[4] ^ dxor[5] ^ dxor[6] ^ dxor[7]),
        'nP': carry_gkp_classification(s[0], IV[0]).count('P'),
    }

def test_delta_I_state_dependence(N=500):
    """Apply same δW to different states, measure ΔI variance."""
    print(f"\n{'='*70}")
    print(f"ΔI STATE DEPENDENCE TEST (N={N})")
    print(f"{'='*70}")

    # Fix one δW (single word difference)
    delta_W = random.randint(1, MASK)

    inv_names = ['HW_dXOR', 'parity', 'HW_dAND', 'HW_darith',
                 'mod3', 'star_balance', 'star_total_HW', 'nP']

    # For each invariant: compute ΔI = I(after_round) - I(before_round)
    # across many different states S

    print(f"\n  Test: apply same round with same δW to different random states")
    print(f"  δW = 0x{delta_W:08x}")

    for K_val in [K[0], K[15], K[31], K[63]]:
        delta_I_all = {name: [] for name in inv_names}

        for _ in range(N):
            # Random state
            S = [random.randint(0, MASK) for _ in range(8)]
            W_base = random.randint(0, MASK)
            W_pert = (W_base + delta_W) & MASK

            # One round: same state, two different W values
            S_after_base = sha256_round(list(S), W_base, K_val)
            S_after_pert = sha256_round(list(S), W_pert, K_val)

            # Compute pair invariants BEFORE (S,S) and AFTER (S_base, S_pert)
            # Before: S₁=S₂=S → δXOR=0, all invariants = 0
            # After: S₁=S_after_base, S₂=S_after_pert

            dxor_after = [S_after_base[w] ^ S_after_pert[w] for w in range(8)]
            dand_after = [S_after_base[w] & S_after_pert[w] for w in range(8)]

            delta_I_all['HW_dXOR'].append(sum(hw(d) for d in dxor_after))
            delta_I_all['parity'].append(sum(hw(d) % 2 for d in dxor_after) % 2)
            delta_I_all['HW_dAND'].append(sum(hw(d) for d in dand_after))

            darith = [(S_after_base[w] - S_after_pert[w]) & MASK for w in range(8)]
            delta_I_all['HW_darith'].append(sum(hw(d) for d in darith))
            delta_I_all['mod3'].append(sum(darith) % 3)
            delta_I_all['star_balance'].append(
                sum(hw(d) for d in dxor_after) - 2 * sum(hw(d) for d in dand_after))
            xor_total = 0
            for d in dxor_after:
                xor_total ^= d
            delta_I_all['star_total_HW'].append(hw(xor_total))
            delta_I_all['nP'].append(
                carry_gkp_classification(S_after_base[0], S_after_pert[0]).count('P'))

        print(f"\n  K = 0x{K_val:08x}:")
        print(f"  {'Invariant':>18} | {'Mean':>8} | {'Std':>8} | {'CV':>8} | {'State-dep?'}")
        print(f"  " + "-" * 58)

        for name in inv_names:
            arr = np.array(delta_I_all[name], dtype=float)
            mean = arr.mean()
            std = arr.std()
            cv = std / abs(mean) if abs(mean) > 0.01 else float('inf')
            # State-dependent if CV > 0.1 (std > 10% of mean)
            dep = "NO (constant!)" if cv < 0.01 else (
                  "weak" if cv < 0.1 else "YES (state-dep)")
            print(f"  {name:>18} | {mean:>8.2f} | {std:>8.2f} | {cv:>8.3f} | {dep}")

def test_delta_I_across_rounds(N=300):
    """Does ΔI depend on WHICH ROUND the δW is applied?"""
    print(f"\n{'='*70}")
    print(f"ΔI ACROSS DIFFERENT ROUNDS (N={N})")
    print(f"{'='*70}")

    delta_W = 1  # Simplest: δW = 1

    inv_names = ['HW_dXOR', 'parity', 'HW_darith', 'mod3', 'star_total_HW']

    print(f"  Same δW={delta_W} applied at different rounds to different states")
    print(f"\n  {'Round':>6}", end="")
    for name in inv_names:
        print(f" | {name[:10]:>10}", end="")
    print(f" | {'parity=0%':>9}")
    print(f"  " + "-" * (8 + 13 * len(inv_names) + 12))

    for r in range(64):
        means = {}
        parity_vals = []

        for _ in range(N):
            S = [random.randint(0, MASK) for _ in range(8)]
            W_base = random.randint(0, MASK)
            W_pert = (W_base + delta_W) & MASK

            S_base = sha256_round(list(S), W_base, K[r])
            S_pert = sha256_round(list(S), W_pert, K[r])

            dxor = [S_base[w] ^ S_pert[w] for w in range(8)]
            darith = [(S_base[w] - S_pert[w]) & MASK for w in range(8)]

            means.setdefault('HW_dXOR', []).append(sum(hw(d) for d in dxor))
            p = sum(hw(d) % 2 for d in dxor) % 2
            means.setdefault('parity', []).append(p)
            parity_vals.append(p)
            means.setdefault('HW_darith', []).append(sum(hw(d) for d in darith))
            means.setdefault('mod3', []).append(sum(darith) % 3)
            xor_total = 0
            for d in dxor: xor_total ^= d
            means.setdefault('star_total_HW', []).append(hw(xor_total))

        if r % 8 == 0 or r < 4 or r > 60:
            print(f"  {r:>6}", end="")
            for name in inv_names:
                arr = np.array(means[name], dtype=float)
                print(f" | {arr.mean():>10.3f}", end="")
            p0 = sum(1 for v in parity_vals if v == 0) / N
            print(f" | {p0:>9.4f}")

def test_arithmetic_diff_preservation(N=500):
    """KEY TEST: Is δ_arith = S₁-S₂ preserved through one round?
    From theory: addition preserves it, ROTR doesn't.
    The round has BOTH. What survives?"""
    print(f"\n{'='*70}")
    print(f"ARITHMETIC DIFFERENCE THROUGH ONE ROUND (N={N})")
    print(f"{'='*70}")

    # S₁ and S₂ with known arithmetic difference
    # Apply one round with SAME W,K
    # Check if arithmetic difference is preserved

    for hw_diff in [1, 2, 4, 8, 16]:
        preserved = 0
        arith_diffs_before = []
        arith_diffs_after = []

        for _ in range(N):
            S1 = [random.randint(0, MASK) for _ in range(8)]
            # S2 = S1 + delta on word 0
            delta = random.randint(1, (1 << hw_diff) - 1)
            S2 = list(S1)
            S2[0] = (S2[0] + delta) & MASK

            W = random.randint(0, MASK)

            S1_after = sha256_round(S1, W, K[0])
            S2_after = sha256_round(S2, W, K[0])

            # Arithmetic diff before (word 0)
            d_before = (S2[0] - S1[0]) & MASK
            # Arithmetic diff after — which word?
            # a' = T1+T2 depends on all words
            # Word 0 (a') contains the diff
            d_after_a = (S2_after[0] - S1_after[0]) & MASK
            d_after_e = (S2_after[4] - S1_after[4]) & MASK

            if d_after_a == d_before or d_after_e == d_before:
                preserved += 1

            arith_diffs_before.append(hw(d_before))
            arith_diffs_after.append(hw(d_after_a))

        corr = np.corrcoef(arith_diffs_before, arith_diffs_after)[0, 1]
        print(f"  HW(δ)≤{hw_diff}: preserved={preserved/N:.4f}, "
              f"corr(HW_before, HW_after)={corr:+.4f}")

def test_mod3_special(N=1000):
    """Special test for mod-3: does it connect to η and carry rank?
    Theory: carry rank = 3^5 = 243. η connects binary↔ternary.
    If mod-3 arithmetic diff has structure → η is the key."""
    print(f"\n{'='*70}")
    print(f"MOD-3 ARITHMETIC DIFFERENCE (η CONNECTION) (N={N})")
    print(f"{'='*70}")

    # For same δW, does (S₁-S₂) mod 3 stay constant through rounds?
    delta_W = 1

    mod3_stability = []
    for _ in range(N):
        S = [random.randint(0, MASK) for _ in range(8)]
        W = random.randint(0, MASK)

        S1 = sha256_round(list(S), W, K[0])
        S2 = sha256_round(list(S), (W + delta_W) & MASK, K[0])

        # mod 3 of arithmetic diff per word
        mod3_per_word = [(S1[w] - S2[w]) % 3 for w in range(8)]
        mod3_total = sum(S1[w] - S2[w] for w in range(8)) % 3
        mod3_stability.append(mod3_total)

    vals, counts = np.unique(mod3_stability, return_counts=True)
    print(f"  δW=1, distribution of Σ(S₁-S₂) mod 3:")
    for v, c in zip(vals, counts):
        print(f"    mod 3 = {v}: {c/N:.4f} (uniform = 0.333)")

    # Check across multiple rounds
    print(f"\n  mod-3 through multi-round chain:")
    for n_rounds in [1, 2, 4, 8, 16, 64]:
        mod3_results = []
        for _ in range(N):
            M1 = random_w16()
            M2 = list(M1)
            M2[0] = (M2[0] + 1) & MASK  # δM = +1

            s1 = sha256_rounds(M1, n_rounds)
            s2 = sha256_rounds(M2, n_rounds)

            mod3 = sum(s1[n_rounds][w] - s2[n_rounds][w] for w in range(8)) % 3
            mod3_results.append(mod3)

        vals, counts = np.unique(mod3_results, return_counts=True)
        dist = {v: c/N for v, c in zip(vals, counts)}
        # Check if it's uniform (0.333 each) or biased
        max_dev = max(abs(dist.get(v, 0) - 1/3) for v in [0, 1, 2])
        z = max_dev / math.sqrt(1/3 * 2/3 / N)
        sig = "★★★" if z > 5 else ("★★" if z > 3 else "")
        dominant = max(dist, key=dist.get) if dist else -1
        print(f"    {n_rounds:>2} rounds: {dist} max_dev={max_dev:.4f} Z={z:.1f} {sig}")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 139: ΔI STATE DEPENDENCE")
    print("Does the effect of δW depend on the current state?")
    print("=" * 70)

    test_delta_I_state_dependence(400)
    test_arithmetic_diff_preservation(400)
    test_mod3_special(800)
    test_delta_I_across_rounds(200)

    print(f"\n{'='*70}")
    print(f"VERDICT")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
