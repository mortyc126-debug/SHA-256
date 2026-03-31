#!/usr/bin/env python3
"""
EXP 146: ★-Kill Chain Scaling — From 4 to 64 Rounds

exp145: kill chain gave δXOR=67 vs random=95 at 4 rounds (+28 bits).
NOW: scale up. Does the advantage GROW or SHRINK with rounds?

IMPROVED KILL CHAIN:
  - Use ALL 16 message words as degrees of freedom
  - At each word position: try many values, pick one that
    MINIMIZES δXOR at the target round
  - Greedy word-by-word optimization
  - Compare: random, greedy-serial, greedy-parallel

ALSO: exploit the SLOW MODE (word 0 bit 28, 18 rounds survival)
  - Start differences near slow modes
  - Steer through slow directions
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_state_dist(s1, s2):
    return sum(hw(s1[w] ^ s2[w]) for w in range(8))

def kill_chain_greedy(R, budget_per_word=200):
    """Greedy kill chain: optimize M₂ word by word to minimize δXOR at round R.

    M₁ = random. M₂ starts as copy of M₁.
    For each word w = 0..15: try budget_per_word values for M₂[w],
    keep the one that gives smallest δXOR at round R.
    """
    M1 = random_w16()
    M2 = list(M1)

    # Initial difference: change word 0 by +1
    M2[0] = (M2[0] + 1) & MASK

    best_dxor = xor_state_dist(sha256_rounds(M1, R)[R], sha256_rounds(M2, R)[R])

    # Optimize each word sequentially
    for w in range(1, 16):
        best_val = M2[w]
        for _ in range(budget_per_word):
            val = random.randint(0, MASK)
            M2_test = list(M2)
            M2_test[w] = val
            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2_test, R)[R]
            dxor = xor_state_dist(s1, s2)

            if dxor < best_dxor:
                best_dxor = dxor
                best_val = val

        M2[w] = best_val

    return M1, M2, best_dxor

def kill_chain_multi_pass(R, budget_per_word=100, passes=3):
    """Multi-pass kill chain: iterate over words multiple times."""
    M1 = random_w16()
    M2 = list(M1)
    M2[0] = (M2[0] + 1) & MASK

    best_dxor = xor_state_dist(sha256_rounds(M1, R)[R], sha256_rounds(M2, R)[R])

    for pass_num in range(passes):
        for w in range(16):
            best_val = M2[w]
            for _ in range(budget_per_word):
                val = random.randint(0, MASK)
                M2_test = list(M2)
                M2_test[w] = val
                dxor = xor_state_dist(sha256_rounds(M1, R)[R],
                                      sha256_rounds(M2_test, R)[R])
                if dxor < best_dxor:
                    best_dxor = dxor
                    best_val = val
            M2[w] = best_val

    return M1, M2, best_dxor

def kill_chain_targeted(R, budget=3000):
    """Targeted kill chain: focus budget on IMPACTFUL words.
    From exp110: words have different schedule diffusion.
    From slow modes: word 0 matters most."""
    M1 = random_w16()
    M2 = list(M1)
    M2[0] = (M2[0] + 1) & MASK

    best_dxor = xor_state_dist(sha256_rounds(M1, R)[R], sha256_rounds(M2, R)[R])

    # Phase 1: heavy budget on early words (most rounds affected)
    for w in range(min(R, 16)):
        word_budget = budget // min(R, 16)
        best_val = M2[w]
        for _ in range(word_budget):
            val = random.randint(0, MASK)
            M2_test = list(M2); M2_test[w] = val
            dxor = xor_state_dist(sha256_rounds(M1, R)[R],
                                  sha256_rounds(M2_test, R)[R])
            if dxor < best_dxor:
                best_dxor = dxor
                best_val = val
        M2[w] = best_val

    return M1, M2, best_dxor

def pure_random_search(R, budget):
    """Baseline: pure random pair search."""
    best_dxor = 256
    M1 = random_w16()
    s1_target = sha256_rounds(M1, R)[R]

    for _ in range(budget):
        M2 = random_w16()
        dxor = xor_state_dist(s1_target, sha256_rounds(M2, R)[R])
        if dxor < best_dxor:
            best_dxor = dxor

    return best_dxor

def test_scaling(N=15):
    """Scale kill chain from 4 to 64 rounds."""
    print(f"\n{'='*60}")
    print(f"★-KILL CHAIN SCALING (N={N})")
    print(f"{'='*60}")

    total_budget = 3200  # Same total budget for all methods

    for R in [4, 8, 16, 32, 64]:
        # Kill chain: greedy
        kc_results = []
        for _ in range(N):
            _, _, dxor = kill_chain_greedy(R, budget_per_word=total_budget // 16)
            kc_results.append(dxor)

        # Kill chain: multi-pass
        kc_mp_results = []
        for _ in range(N):
            _, _, dxor = kill_chain_multi_pass(R,
                         budget_per_word=total_budget // 48, passes=3)
            kc_mp_results.append(dxor)

        # Random
        rand_results = []
        for _ in range(N):
            dxor = pure_random_search(R, total_budget)
            rand_results.append(dxor)

        kc = np.array(kc_results)
        mp = np.array(kc_mp_results)
        rd = np.array(rand_results)

        gain_kc = rd.mean() - kc.mean()
        gain_mp = rd.mean() - mp.mean()

        print(f"\n  {R} rounds (budget={total_budget}):")
        print(f"    {'Method':>20} | {'Avg dXOR':>8} | {'Min':>5} | {'Gain vs rand':>12}")
        print(f"    {'-'*50}")
        print(f"    {'Kill chain (1-pass)':>20} | {kc.mean():>8.1f} | {kc.min():>5} | {gain_kc:>+12.1f}")
        print(f"    {'Kill chain (3-pass)':>20} | {mp.mean():>8.1f} | {mp.min():>5} | {gain_mp:>+12.1f}")
        print(f"    {'Pure random':>20} | {rd.mean():>8.1f} | {rd.min():>5} | {'baseline':>12}")

        if gain_kc > 5:
            print(f"    ★★★ KILL CHAIN WINS BY {gain_kc:.0f} BITS!")

def test_collision_at_reduced_rounds(N=10):
    """Can kill chain actually FIND collisions at reduced rounds?"""
    print(f"\n{'='*60}")
    print(f"★-KILL CHAIN: COLLISION SEARCH")
    print(f"{'='*60}")

    for R in [4, 8, 16]:
        successes = 0
        best_overall = 256
        budget = 6400

        for trial in range(N):
            _, _, dxor = kill_chain_multi_pass(R,
                         budget_per_word=budget // 48, passes=3)
            if dxor < best_overall:
                best_overall = dxor
            if dxor == 0:
                successes += 1
                print(f"  {R}r trial {trial}: COLLISION FOUND!")

        print(f"  {R} rounds: collisions={successes}/{N}, "
              f"best δXOR={best_overall}")

def test_hash_collision_kill_chain(N=10):
    """Kill chain on full SHA-256 HASH (with feedforward)."""
    print(f"\n{'='*60}")
    print(f"★-KILL CHAIN: FULL HASH COLLISION (64 rounds + feedforward)")
    print(f"{'='*60}")

    budget = 6400

    kc_results = []; rand_results = []

    for trial in range(N):
        # Kill chain
        M1 = random_w16(); M2 = list(M1)
        M2[0] = (M2[0] + 1) & MASK

        H1 = sha256_compress(M1)
        best_dH = sum(hw(H1[w] ^ sha256_compress(M2)[w]) for w in range(8))

        for p in range(3):
            for w in range(16):
                best_val = M2[w]
                for _ in range(budget // 48):
                    val = random.randint(0, MASK)
                    M2_test = list(M2); M2_test[w] = val
                    H2 = sha256_compress(M2_test)
                    dH = sum(hw(H1[w2] ^ H2[w2]) for w2 in range(8))
                    if dH < best_dH:
                        best_dH = dH
                        best_val = val
                M2[w] = best_val

        kc_results.append(best_dH)

        # Random (same budget)
        best_rand = 256
        for _ in range(budget):
            M2r = random_w16()
            H2 = sha256_compress(M2r)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            if dH < best_rand: best_rand = dH
        rand_results.append(best_rand)

    kc = np.array(kc_results); rd = np.array(rand_results)
    gain = rd.mean() - kc.mean()

    print(f"\n  Full SHA-256 hash collision:")
    print(f"    Kill chain: avg={kc.mean():.1f}, min={kc.min()}")
    print(f"    Random:     avg={rd.mean():.1f}, min={rd.min()}")
    print(f"    Gain: {gain:+.1f} bits")

    if gain > 0:
        print(f"    ★★★ KILL CHAIN BEATS RANDOM ON FULL SHA-256!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 146: ★-KILL CHAIN — SCALE TO 64 ROUNDS")
    print("=" * 60)

    test_scaling(N=12)
    test_collision_at_reduced_rounds(N=8)
    test_hash_collision_kill_chain(N=8)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
