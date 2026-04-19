"""OTOC-guided MLB at r=8 (earlier, more structure).

Previous at r=16: tied HW=80 for OTOC-guided vs baseline.
Hypothesis: at r=8 structure is stronger (||C||² = 22,396 vs 164 RO);
OTOC-guided might reveal advantage.

Also test the INVERSE hypothesis: LOWEST-OTOC positions might give
better matching because they're closer to "already-scrambled" random
behavior, giving more uniform bucket distribution.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch
from otoc_guided_mlb import (state_at_r_batch, state_to_bits, compute_otoc_r16,
                               rank_state_words_by_otoc, run_mlb)


OUT = '/home/user/SHA-256/research/min_entropy/otoc_guided_mlb_r8_results.json'


def compute_otoc_at_r(r, N=200, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r_batch(base_msgs, r)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_batch(flip_msgs, r)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# OTOC-guided MLB at r=8 and r=12")

    for r in [8, 12]:
        print(f"\n\n## ROUND r={r}")
        C = compute_otoc_at_r(r, N=200)
        print(f"  ||C||_F² at r={r}: {(C**2).sum():.1f}")

        scores = rank_state_words_by_otoc(C)
        word_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        for rank, (w, s) in enumerate(ranked):
            marker = " [top3]" if rank < 3 else (" [bottom3]" if rank >= 5 else "")
            print(f"    word {w} ({word_names[w]}{r}): {s:.1f}{marker}")

        top3 = [w for w, _ in ranked[:3]]
        bot3 = [w for w, _ in ranked[-3:]]
        top_names = [f"{word_names[w]}{r}" for w in top3]
        bot_names = [f"{word_names[w]}{r}" for w in bot3]

        # Run MLB
        K = 20_000_000; T = 2_000_000
        results = {}

        # Baseline (a, e, b)
        print(f"\n  Baseline [a{r},e{r},b{r}]:")
        def base_sel(state): return (state[:, 0], state[:, 4], state[:, 1])
        hw_b, n_b, _ = run_mlb(base_sel, [f'a{r}', f'e{r}', f'b{r}'], K, T, r=r)
        results['baseline'] = {'hw': hw_b, 'n': n_b}

        # OTOC top 3
        print(f"\n  OTOC-top3 {top_names}:")
        def top_sel(state): return tuple(state[:, w] for w in top3)
        hw_t, n_t, _ = run_mlb(top_sel, top_names, K, T, r=r)
        results['otoc_top3'] = {'words': top_names, 'hw': hw_t, 'n': n_t}

        # OTOC bottom 3 (test inverse hypothesis)
        print(f"\n  OTOC-bottom3 {bot_names}:")
        def bot_sel(state): return tuple(state[:, w] for w in bot3)
        hw_bb, n_bb, _ = run_mlb(bot_sel, bot_names, K, T, r=r)
        results['otoc_bottom3'] = {'words': bot_names, 'hw': hw_bb, 'n': n_bb}

        print(f"\n  r={r} summary:")
        print(f"    baseline (a,e,b):  HW={hw_b},  pairs={n_b}")
        print(f"    OTOC-top3:         HW={hw_t},  pairs={n_t}")
        print(f"    OTOC-bottom3:      HW={hw_bb}, pairs={n_bb}")

        # Save per-round
        with open(OUT.replace('.json', f'_r{r}.json'), 'w') as f:
            json.dump({'r': r, 'otoc_frobenius_sq': float((C**2).sum()),
                       'results': results,
                       'word_scores': {word_names[w]: float(scores[w]) for w in range(8)},
                       'K': K, 'T': T}, f, indent=2)

    print(f"\nTotal runtime: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
