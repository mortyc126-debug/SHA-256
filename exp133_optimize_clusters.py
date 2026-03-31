#!/usr/bin/env python3
"""
EXP 133: Optimize Cluster Parameters

V13 (★-seeded) won with: few seeds, 2-3 word changes, multi-target.
Now optimize:
  - How many seeds? (1, 5, 10, 50, 200)
  - How many words to change? (1, 2, 3, 4, 8, 16)
  - Which words to change? (random, weak-schedule, first/last)
  - Budget split: seeds vs messages per seed

Also: combine best strategies (V9+V13, V12+V13, etc.)
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_dist(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def clustered_search(budget, n_seeds, n_change_words, word_strategy="random"):
    """Clustered birthday with configurable parameters."""
    msgs_per_seed = budget // max(n_seeds, 1)
    hashes = {}
    best = 256

    for _ in range(n_seeds):
        base = random_w16()

        if word_strategy == "weak":
            # Weak schedule words first (from exp110)
            change_pool = [13, 12, 0, 11, 15, 10, 14, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        elif word_strategy == "first":
            change_pool = list(range(16))
        elif word_strategy == "last":
            change_pool = list(range(15, -1, -1))
        else:
            change_pool = list(range(16))

        for _ in range(msgs_per_seed):
            M = list(base)
            if word_strategy == "random":
                words = random.sample(range(16), min(n_change_words, 16))
            else:
                words = change_pool[:n_change_words]

            for w in words:
                M[w] = random.randint(0, MASK)

            H = sha256_compress(M)
            h_key = tuple(H)

            # Check against recent stored
            for h_stored in list(hashes.keys())[-30:]:
                d = xor_dist(list(h_stored), H)
                if d < best: best = d

            hashes[h_key] = M

    return best

def optimize_n_seeds(N=20, budget=8000):
    """Find optimal number of seeds."""
    print(f"\n--- OPTIMIZE: NUMBER OF SEEDS (budget={budget}) ---")

    for n_seeds in [1, 2, 5, 10, 20, 50, 100, 500, budget]:
        results = [clustered_search(budget, n_seeds, 3) for _ in range(N)]
        arr = np.array(results)
        per_seed = budget // max(n_seeds, 1)
        print(f"  seeds={n_seeds:>5} ({per_seed:>5}/seed): "
              f"avg={arr.mean():.1f}  min={arr.min()}")

def optimize_n_words(N=20, budget=8000):
    """Find optimal number of words to change."""
    print(f"\n--- OPTIMIZE: WORDS TO CHANGE (budget={budget}) ---")

    n_seeds = 20  # Fixed from above optimization
    for n_words in [1, 2, 3, 4, 5, 6, 8, 12, 16]:
        results = [clustered_search(budget, n_seeds, n_words) for _ in range(N)]
        arr = np.array(results)
        print(f"  change {n_words:>2} words: avg={arr.mean():.1f}  min={arr.min()}")

def optimize_word_strategy(N=20, budget=8000):
    """Which words to change?"""
    print(f"\n--- OPTIMIZE: WORD SELECTION STRATEGY (budget={budget}) ---")

    n_seeds = 20; n_words = 3
    for strategy in ["random", "weak", "first", "last"]:
        results = [clustered_search(budget, n_seeds, n_words, strategy) for _ in range(N)]
        arr = np.array(results)
        print(f"  {strategy:>8}: avg={arr.mean():.1f}  min={arr.min()}")

def optimize_combined(N=25, budget=8000):
    """Test optimized combinations."""
    print(f"\n--- OPTIMIZED COMBINATIONS (budget={budget}) ---")

    configs = [
        ("Pure random", lambda: clustered_search(budget, budget, 16)),
        ("1 seed, 3 words", lambda: clustered_search(budget, 1, 3)),
        ("5 seeds, 2 words", lambda: clustered_search(budget, 5, 2)),
        ("10 seeds, 3 words", lambda: clustered_search(budget, 10, 3)),
        ("20 seeds, 3 words", lambda: clustered_search(budget, 20, 3)),
        ("20 seeds, 4 words", lambda: clustered_search(budget, 20, 4)),
        ("50 seeds, 2 words", lambda: clustered_search(budget, 50, 2)),
        ("50 seeds, 3 words", lambda: clustered_search(budget, 50, 3)),
        ("100 seeds, 2 words", lambda: clustered_search(budget, 100, 2)),
        ("√N seeds, 3 words", lambda: clustered_search(budget, int(budget**0.5), 3)),
    ]

    results = {}
    for name, fn in configs:
        dHs = [fn() for _ in range(N)]
        arr = np.array(dHs)
        results[name] = arr
        print(f"  {name:>25}: avg={arr.mean():>6.1f}  min={arr.min():>3}")

    # Ranking
    print(f"\n  RANKING:")
    ranking = sorted(results.items(), key=lambda x: x[1].mean())
    baseline = results["Pure random"].mean()
    for i, (name, arr) in enumerate(ranking):
        gain = baseline - arr.mean()
        marker = " ★★★" if i == 0 else (" ★★" if i == 1 else (" ★" if i == 2 else ""))
        print(f"    #{i+1}: {name:>25} avg={arr.mean():.1f} gain={gain:+.1f}{marker}")

def scaling_test(N=20):
    """How does the best method scale with budget?"""
    print(f"\n--- SCALING TEST ---")

    for budget in [1000, 2000, 5000, 10000, 20000]:
        # Optimal: √N seeds, 3 words
        n_seeds = int(budget**0.5)
        cluster_results = [clustered_search(budget, n_seeds, 3) for _ in range(N)]
        random_results = [clustered_search(budget, budget, 16) for _ in range(N)]

        ca = np.array(cluster_results); ra = np.array(random_results)
        gain = ra.mean() - ca.mean()
        print(f"  budget={budget:>6}: cluster={ca.mean():.1f}  random={ra.mean():.1f}  gain={gain:+.1f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 133: OPTIMIZE CLUSTER PARAMETERS")
    print("=" * 60)

    optimize_n_seeds(N=15, budget=8000)
    optimize_n_words(N=15, budget=8000)
    optimize_word_strategy(N=15, budget=8000)
    optimize_combined(N=20, budget=8000)
    scaling_test(N=15)

    print(f"\n{'='*60}")
    print(f"VERDICT: Cluster optimization")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
