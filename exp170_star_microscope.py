#!/usr/bin/env python3
"""
EXP 170: ★-MICROSCOPE — Below Particles: The Probability Field

Level 4: For each of 16,384 bit-positions in SHA-256,
compute the PROBABILITY of being K, P, or G.

This is the ★-FIELD: the probability landscape that generates particles.

If the field is UNIFORM (P(K)=1/4, P(P)=1/2, P(G)=1/4 everywhere):
  → SHA-256 is truly random → no structure to exploit.

If the field has HOTSPOTS (positions where P(G) > 1/4):
  → carry is more likely at those positions → predictable → exploitable.

ALSO: Correlations between positions.
If P(G at pos i) correlates with P(G at pos j):
  → "force" between positions → carry organisms are not independent.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_gkp_field(N=300):
    """Compute P(K), P(P), P(G) at every bit position in SHA-256."""

    # For each round and word: track GKP of the TWO additions
    # Addition 1: T1 components (h + Σ₁ + Ch + K + W) — 4 additions
    # Addition 2: T2 = Σ₀ + Maj — 1 addition
    # Addition 3: a_new = T1 + T2
    # Addition 4: e_new = d + T1

    # Focus on the TWO main additions: T1+T2→a_new and d+T1→e_new
    # Each has 32 bit positions × 64 rounds = 2048 positions per word

    # Simplified: track GKP of (state_before_feedforward, IV) at round 64
    # = the FEEDFORWARD addition. 32 bits × 8 words = 256 positions.

    print(f"\n{'='*70}")
    print(f"★-PROBABILITY FIELD: FEEDFORWARD (N={N})")
    print(f"{'='*70}")

    # P(G), P(K), P(P) at each of 256 feedforward positions
    pG = np.zeros((8, 32))
    pK = np.zeros((8, 32))
    pP = np.zeros((8, 32))

    for _ in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]

        for w in range(8):
            for b in range(32):
                iv_bit = (IV[w] >> b) & 1
                s_bit = (s[w] >> b) & 1

                if iv_bit == 1 and s_bit == 1:
                    pG[w, b] += 1
                elif iv_bit == 0 and s_bit == 0:
                    pK[w, b] += 1
                else:
                    pP[w, b] += 1

    pG /= N; pK /= N; pP /= N

    # Display field
    print(f"\n  Probability field P(G) - expected 0.250:")
    deviations = []
    for w in range(8):
        print(f"\n  Word {w} (IV[{w}]=0x{IV[w]:08x}):")
        line_g = "  G: "
        line_p = "  P: "
        line_k = "  K: "
        hotspots = []

        for b in range(32):
            # Color coding: deviation from expected
            dev_g = pG[w, b] - 0.25
            dev_p = pP[w, b] - 0.50
            deviations.append((abs(dev_g), abs(dev_p), w, b))

            # IV bit determines expected: if IV[w][b]=1 → P(G) biased
            iv_b = (IV[w] >> b) & 1

            if abs(dev_g) > 0.05:
                hotspots.append((b, pG[w,b], pP[w,b], pK[w,b], iv_b))

        if hotspots:
            for b, pg, pp, pk, iv_b in hotspots[:5]:
                marker = "★" if abs(pg - 0.25) > 0.08 else ""
                print(f"    Bit {b:>2} (IV={iv_b}): G={pg:.3f} P={pp:.3f} K={pk:.3f} {marker}")

    # GLOBAL STATISTICS
    print(f"\n  GLOBAL FIELD STATISTICS:")
    print(f"    E[P(G)]: {pG.mean():.4f} (expected 0.250)")
    print(f"    E[P(K)]: {pK.mean():.4f} (expected 0.250)")
    print(f"    E[P(P)]: {pP.mean():.4f} (expected 0.500)")
    print(f"    Std[P(G)]: {pG.std():.4f}")
    print(f"    Max|P(G)-0.25|: {np.max(np.abs(pG - 0.25)):.4f}")

    # Are deviations RANDOM or STRUCTURED?
    # If structured: IV bit determines the bias
    print(f"\n  IV BIT → PARTICLE BIAS:")
    for iv_val in [0, 1]:
        g_vals = []; k_vals = []; p_vals = []
        for w in range(8):
            for b in range(32):
                if ((IV[w] >> b) & 1) == iv_val:
                    g_vals.append(pG[w, b])
                    k_vals.append(pK[w, b])
                    p_vals.append(pP[w, b])

        print(f"    IV bit = {iv_val} ({len(g_vals)} positions):")
        print(f"      P(G) = {np.mean(g_vals):.4f}")
        print(f"      P(K) = {np.mean(k_vals):.4f}")
        print(f"      P(P) = {np.mean(p_vals):.4f}")

    return pG, pK, pP

def compute_correlation_field(N=500):
    """Correlations between GKP states at different positions."""
    print(f"\n{'='*70}")
    print(f"★-CORRELATION FIELD (N={N})")
    print(f"{'='*70}")

    # For each pair of positions: is P(G at pos i) correlated with P(G at pos j)?
    # This reveals "forces" between positions.

    # Collect GKP states
    gkp_states = np.zeros((N, 256))  # 1 if G, 0 otherwise

    for idx in range(N):
        M = random_w16()
        s = sha256_rounds(M, 64)[64]

        for w in range(8):
            for b in range(32):
                iv_bit = (IV[w] >> b) & 1
                s_bit = (s[w] >> b) & 1
                is_G = 1 if (iv_bit == 1 and s_bit == 1) else 0
                gkp_states[idx, w*32+b] = is_G

    # Sample correlations (256×256 = 65536 pairs is too many)
    # Focus on INTRA-WORD and INTER-WORD correlations

    print(f"\n  INTRA-WORD G-correlations (same word, different bits):")
    for w in range(8):
        intra_corrs = []
        for b1 in range(0, 32, 4):
            for b2 in range(b1+4, 32, 4):
                c = np.corrcoef(gkp_states[:, w*32+b1],
                               gkp_states[:, w*32+b2])[0, 1]
                if not np.isnan(c):
                    intra_corrs.append(c)

        if intra_corrs:
            avg = np.mean(intra_corrs)
            mx = max(intra_corrs, key=abs)
            sig = "★" if abs(avg) > 0.02 else ""
            print(f"    Word {w}: avg_corr={avg:+.4f}, max={mx:+.4f} {sig}")

    print(f"\n  INTER-WORD G-correlations (different words, same bit):")
    for b in range(0, 32, 8):
        inter_corrs = []
        for w1 in range(8):
            for w2 in range(w1+1, 8):
                c = np.corrcoef(gkp_states[:, w1*32+b],
                               gkp_states[:, w2*32+b])[0, 1]
                if not np.isnan(c):
                    inter_corrs.append((c, w1, w2))

        if inter_corrs:
            avg = np.mean([c for c,_,_ in inter_corrs])
            best = max(inter_corrs, key=lambda x: abs(x[0]))
            sig = "★★" if abs(best[0]) > 0.1 else ("★" if abs(avg) > 0.02 else "")
            print(f"    Bit {b:>2}: avg={avg:+.4f}, "
                  f"max={best[0]:+.4f} (w{best[1]}↔w{best[2]}) {sig}")

    # ADJACENT-BIT correlations (carry chain neighbors)
    print(f"\n  ADJACENT-BIT G-correlations (bit i ↔ bit i+1):")
    adj_corrs = []
    for w in range(8):
        for b in range(31):
            c = np.corrcoef(gkp_states[:, w*32+b],
                           gkp_states[:, w*32+b+1])[0, 1]
            if not np.isnan(c):
                adj_corrs.append(c)

    avg_adj = np.mean(adj_corrs) if adj_corrs else 0
    print(f"    Average adjacent-bit corr: {avg_adj:+.4f}")
    print(f"    (Nonzero → carry chain positions are correlated)")
    print(f"    (Zero → carry chain is memoryless at particle level)")

def compute_per_round_field(N=200):
    """Track probability field THROUGH rounds — where do hotspots form?"""
    print(f"\n{'='*70}")
    print(f"★-FIELD EVOLUTION THROUGH ROUNDS (N={N})")
    print(f"{'='*70}")

    # For rounds 0, 1, 2, 4, 8, 16, 32, 64:
    # Compute P(G) field for the state
    # (GKP relative to IV)

    for R in [0, 1, 2, 4, 8, 16, 32, 64]:
        pG = np.zeros(256)
        for _ in range(N):
            M = random_w16()
            s = sha256_rounds(M, R)[R]
            for w in range(8):
                for b in range(32):
                    if ((IV[w] >> b) & 1) == 1 and ((s[w] >> b) & 1) == 1:
                        pG[w*32+b] += 1
        pG /= N

        # How uniform is the field?
        uniformity = pG.std()
        max_dev = np.max(np.abs(pG - 0.25))
        # Count hotspots
        n_hot = np.sum(np.abs(pG - 0.25) > 0.05)

        print(f"  Round {R:>2}: std(P(G))={uniformity:.4f}, "
              f"max_dev={max_dev:.4f}, hotspots={n_hot}/256")

    print(f"\n  INTERPRETATION:")
    print(f"    Round 0: P(G) is DETERMINISTIC (state = IV)")
    print(f"      → P(G at bit i) = (IV[w] bit i)² = IV[w] bit i")
    print(f"    By round 4: field should approach uniform (0.25)")
    print(f"    If hotspots PERSIST beyond round 4 → sub-particle structure!")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 170: ★-MICROSCOPE — THE PROBABILITY FIELD")
    print("What's below K, P, G?")
    print("=" * 70)

    pG, pK, pP = compute_gkp_field(N=500)
    compute_correlation_field(N=400)
    compute_per_round_field(N=200)

    print(f"\n{'='*70}")
    print(f"VERDICT: ★-Probability Field")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
