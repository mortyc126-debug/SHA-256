#!/usr/bin/env python3
"""SVD-only test from Experiment 4 (tensor network)."""

import sys, os, random
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_singular_value_distribution(N=30):
    print("=" * 70)
    print("EXPERIMENT 4b: SVD ANALYSIS OF SHA-256 DIFFERENTIAL PROPAGATION")
    print("=" * 70)

    random.seed(42)

    for num_rounds in [4, 8, 16, 32, 64]:
        all_svs = []

        for _ in range(N):
            W16 = random_w16()
            base_states = sha256_rounds(W16, num_rounds)
            base_final = base_states[num_rounds]

            diff_matrix = []
            for word in range(16):
                for bit in range(32):
                    W_pert = list(W16)
                    W_pert[word] ^= (1 << bit)
                    pert_states = sha256_rounds(W_pert, num_rounds)
                    pert_final = pert_states[num_rounds]

                    row = []
                    for w in range(8):
                        d = base_final[w] ^ pert_final[w]
                        for b in range(32):
                            row.append(float((d >> b) & 1))
                    diff_matrix.append(row)

            M = np.array(diff_matrix, dtype=np.float64)
            svs = np.linalg.svd(M, compute_uv=False)
            all_svs.append(svs)

        avg_svs = np.mean(all_svs, axis=0)
        total_energy = np.sum(avg_svs**2)

        cumulative = np.cumsum(avg_svs**2) / total_energy
        r90 = int(np.searchsorted(cumulative, 0.90)) + 1
        r95 = int(np.searchsorted(cumulative, 0.95)) + 1
        r99 = int(np.searchsorted(cumulative, 0.99)) + 1

        p = avg_svs**2 / total_energy
        p = p[p > 1e-15]
        eff_rank = 2**(-np.sum(p * np.log2(p)))

        # SV decay
        sv_ratio_1_10 = avg_svs[0] / avg_svs[9] if avg_svs[9] > 0 else float('inf')
        sv_ratio_1_50 = avg_svs[0] / avg_svs[49] if len(avg_svs) > 49 and avg_svs[49] > 0 else float('inf')
        sv_ratio_1_last = avg_svs[0] / avg_svs[-1] if avg_svs[-1] > 0 else float('inf')

        # Compare with random binary matrix
        rand_svs = []
        for _ in range(N):
            R = np.random.randint(0, 2, size=(512, 256)).astype(np.float64)
            rand_svs.append(np.linalg.svd(R, compute_uv=False))
        avg_rand_svs = np.mean(rand_svs, axis=0)
        rand_energy = np.sum(avg_rand_svs**2)
        rand_cum = np.cumsum(avg_rand_svs**2) / rand_energy
        rand_r90 = int(np.searchsorted(rand_cum, 0.90)) + 1
        rand_r95 = int(np.searchsorted(rand_cum, 0.95)) + 1
        rand_r99 = int(np.searchsorted(rand_cum, 0.99)) + 1
        rand_p = avg_rand_svs**2 / rand_energy
        rand_p = rand_p[rand_p > 1e-15]
        rand_eff_rank = 2**(-np.sum(rand_p * np.log2(rand_p)))

        print(f"\n--- Rounds={num_rounds} ---")
        print(f"  Top 5 SVs:     {[f'{v:.2f}' for v in avg_svs[:5]]}")
        print(f"  Bottom 5 SVs:  {[f'{v:.4f}' for v in avg_svs[-5:]]}")
        print(f"  SV1/SV10:      {sv_ratio_1_10:.4f}")
        print(f"  SV1/SV50:      {sv_ratio_1_50:.4f}")
        print(f"  SV1/SV_last:   {sv_ratio_1_last:.4f}")
        print(f"  Rank for 90%:  {r90}/256 (random: {rand_r90})")
        print(f"  Rank for 95%:  {r95}/256 (random: {rand_r95})")
        print(f"  Rank for 99%:  {r99}/256 (random: {rand_r99})")
        print(f"  Effective rank: {eff_rank:.1f}/256 (random: {rand_eff_rank:.1f})")

        if eff_rank < rand_eff_rank * 0.9:
            print(f"  *** SIGNAL: Eff rank {eff_rank:.0f} < random {rand_eff_rank:.0f}! ***")
        else:
            print(f"  No signal (eff rank ≈ random)")

if __name__ == "__main__":
    test_singular_value_distribution(30)
