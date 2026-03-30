#!/usr/bin/env python3
"""
EXP 55: Intermediate State Collision — Nonlocal Mathematics

T_CONVERGENCE_RADIUS_ONE: LOCAL methods dead (R=1 in output space).
BUT: R=8 at 4 rounds in STATE space.

Key insight: work in INTERMEDIATE state space, not input/output.

SHA-256 = g ∘ f, where:
  f: input → state[R]    (first R rounds, SMOOTH, radius ~ 2^(7-R/4))
  g: state[R] → output   (last 64-R rounds, R=1)

If we can find PARTIAL state collision at round R:
  π(state[R](M)) = π(state[R](M'))
for some projection π → then check if g preserves this.

NEW METRIC: "state collision depth"
For Wang pairs: how many state WORDS match at each round?
Not δH of full state, but NUMBER OF IDENTICAL WORDS.

If some words match at round R > 16 → that's structure BEYOND Wang.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def state_word_matches(s1, s2):
    """Count how many of the 8 state words are IDENTICAL."""
    return sum(1 for i in range(8) if s1[i] == s2[i])

def state_partial_distance(s1, s2):
    """Per-word Hamming distance."""
    return [hw(s1[i] ^ s2[i]) for i in range(8)]

def test_state_collision_depth(N=2000):
    """
    For Wang pairs: track word-level matches through ALL rounds.
    Wang gives De=0 for rounds 3-16 → e-words match.
    Do ANY words match BEYOND round 16?
    """
    print("\n--- STATE COLLISION DEPTH ---")

    # Per-round: how many state words match (for Wang pairs)
    word_match_counts = {r: [] for r in range(65)}
    zero_word_counts = {r: {w: 0 for w in range(8)} for r in range(65)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        for r in range(65):
            matches = state_word_matches(sn[r], sf[r])
            word_match_counts[r].append(matches)

            for w in range(8):
                if sn[r][w] == sf[r][w]:
                    zero_word_counts[r][w] += 1

    print(f"{'Round':>5} | {'E[matches]':>10} | {'P(any match)':>12} | "
          f"{'Max':>4} | Best word | P(best)")
    print("-"*65)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,24,32,48,60,64]:
        mc = np.array(word_match_counts[r])
        p_any = np.mean(mc > 0)
        best_w = max(range(8), key=lambda w: zero_word_counts[r][w])
        p_best = zero_word_counts[r][best_w] / N

        # Word labels
        labels = ['a','b','c','d','e','f','g','h']
        sig = ""
        if r > 16 and p_any > 0.001:
            sig = " ***BEYOND WANG"

        print(f"{r:>5} | {mc.mean():>10.4f} | {p_any:>12.6f} | "
              f"{mc.max():>4} | {labels[best_w]:>9} ({best_w}) | {p_best:.6f}{sig}")

def test_partial_state_projection(N=2000):
    """
    Instead of FULL state match, look for LOW per-word distance.

    If state[R] word w has HW(Δ) < 4 (not zero, but CLOSE) →
    partial match. How often does this happen beyond Wang zone?
    """
    print(f"\n--- PARTIAL STATE PROXIMITY (HW<4 per word) ---")

    proximity_counts = {r: {w: 0 for w in range(8)} for r in range(65)}

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        for r in range(65):
            for w in range(8):
                if hw(sn[r][w] ^ sf[r][w]) < 4:
                    proximity_counts[r][w] += 1

    print(f"{'Round':>5} |", end="")
    for w in range(8):
        labels=['a','b','c','d','e','f','g','h']
        print(f" {labels[w]:>6}", end="")
    print(f" | {'Total':>6}")
    print("-"*75)

    for r in [0,1,2,3,4,5,8,12,15,16,17,18,20,24,32,48,64]:
        probs = [proximity_counts[r][w]/N for w in range(8)]
        total = sum(probs)
        expected = 8 * sum(1 for k in range(4) for _ in range(1)) * (0.5**32)
        # P(HW<4 for 32 bits) ≈ Σ_{k=0}^{3} C(32,k) / 2^32 ≈ 5.3e-6

        row = f"{r:>5} |"
        for p in probs:
            if p > 0.01:
                row += f" {p:>6.3f}"
            else:
                row += f" {p:>6.4f}"
        row += f" | {total:>6.3f}"

        if r > 16 and total > 0.001:
            row += " ***"

        print(row)

def test_nonlocal_connection(N=3000):
    """
    The nonlocal question: do TWO DIFFERENT Wang pairs that have
    similar state at round R also have similar OUTPUT?

    If yes → state[R] proximity = nonlocal predictor of output.
    This would bypass R=1 in output space.
    """
    print(f"\n--- NONLOCAL: state[R] proximity → output proximity? ---")

    for R_target in [4, 8, 12, 16, 20]:
        # Collect Wang pairs and their state[R] + output
        pairs = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

            state_dist = sum(hw(sn[R_target][i]^sf[R_target][i]) for i in range(8))
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            output_dist = sum(hw(Hn[i]^Hf[i]) for i in range(8))

            pairs.append((state_dist, output_dist))

        sd = np.array([p[0] for p in pairs])
        od = np.array([p[1] for p in pairs])

        c = np.corrcoef(sd, od)[0,1]
        threshold = 3/np.sqrt(N)

        # Conditional: low state distance → low output distance?
        low_sd = od[sd < np.percentile(sd, 25)]
        high_sd = od[sd > np.percentile(sd, 75)]

        sig = "***" if abs(c) > threshold else ""
        print(f"  R={R_target:>2}: corr(state_dist, δH)={c:+.6f}{sig:>4}  "
              f"low_sd E[δH]={low_sd.mean():.2f}, high_sd E[δH]={high_sd.mean():.2f}")

def test_state_hash_for_birthday(N=2000):
    """
    Practical test: use state[R] as a HASH for birthday search.

    Instead of birthday on H(M) (256 bits), birthday on state[R](M) words.
    If some state words have less entropy → birthday is cheaper.

    From Wang: e-branch words at rounds 3-16 = 0 → 0 entropy.
    Beyond round 16: how much entropy does each word have?
    """
    print(f"\n--- STATE ENTROPY FOR BIRTHDAY ---")

    for R in [16, 17, 18, 20, 24, 32, 64]:
        # Collect state[R] for many Wang pairs
        e_words = {w: [] for w in range(4,8)}  # e-branch

        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

            for w in range(4, 8):
                diff_word = sn[R][w] ^ sf[R][w]
                e_words[w].append(diff_word)

        # Measure: how many UNIQUE diff_words per word?
        print(f"  R={R:>2}:", end="")
        for w in range(4, 8):
            unique = len(set(e_words[w]))
            labels = ['e','f','g','h']
            # Entropy ≈ log2(unique)
            entropy = np.log2(unique) if unique > 1 else 0
            print(f"  {labels[w-4]}: {unique:>5} unique ({entropy:.1f} bits)", end="")
        print()

def main():
    random.seed(42)
    print("="*60)
    print("EXP 55: INTERMEDIATE STATE COLLISION")
    print("Nonlocal mathematics in state space")
    print("="*60)

    test_state_collision_depth(1500)
    test_partial_state_projection(1000)
    test_nonlocal_connection(2000)
    test_state_hash_for_birthday(1500)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
