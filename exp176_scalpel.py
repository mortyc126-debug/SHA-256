#!/usr/bin/env python3
"""
EXP 176: ★-SCALPEL — Precision tool from microscopic advantages

Combine ALL micro-findings into ONE precision instrument:
  - Bit 27 stability (+3%, exp175)
  - IV mask (136 G-positions, exp170)
  - Period 22.5 oscillation (exp174)
  - Temporal correlation 0.75 (exp174)
  - Best schedule δM = W[0]b15 (exp137)
  - τ_★ = 4 fundamental scale (exp157)

SCALPEL PRINCIPLE: Place differences at STABLE positions,
time injections with entropy oscillation, align with IV mask.

Like a laser: tiny individual photons → coherent, powerful beam.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def scalpel_pair_generator(M_base):
    """Generate M₂ using ALL microscopic knowledge.

    1. δM at W[0] bit 15 (best schedule, 20 zero rounds)
    2. Additional δ at bits 27, 26, 10 (most stable positions)
    3. Concentrate changes in words that maximize IV-G overlap
    """
    M2 = list(M_base)

    # Core: W[0] bit 15 (best schedule)
    M2[0] ^= (1 << 15)

    # Precision: add differences at STABLE bit positions
    # Bit 27 = most stable across all words
    # Choose words where IV has 1 at bit 27 (G-territory = stable)
    for w in range(16):
        iv_w = IV[w % 8]
        if (iv_w >> 27) & 1:  # IV bit 27 = 1 → G-territory
            if random.random() < 0.3:
                M2[w] ^= (1 << 27)

    return M2

def scalpel_pair_generator_v2(M_base):
    """V2: Maximally exploit IV mask.
    Place ALL differences at IV=1 positions (G-territory).
    """
    M2 = list(M_base)

    # Only flip bits where IV has 1 (these become G or P, never K)
    n_flips = random.randint(2, 6)
    for _ in range(n_flips):
        w = random.randint(0, 15)
        iv_w = IV[w % 8]
        # Find positions where IV=1
        iv_ones = [b for b in range(32) if (iv_w >> b) & 1]
        if iv_ones:
            b = random.choice(iv_ones)
            M2[w] ^= (1 << b)

    if M2 == M_base:
        M2[0] ^= (1 << 15)  # Fallback

    return M2

def scalpel_pair_generator_v3(M_base):
    """V3: Concentrate on stable bits + IV mask.
    Only flip bits at positions {26, 27, 10} AND where IV=1.
    """
    M2 = list(M_base)
    stable_bits = [27, 26, 10]

    n_flips = random.randint(1, 4)
    for _ in range(n_flips):
        w = random.randint(0, 15)
        b = random.choice(stable_bits)
        iv_w = IV[w % 8]
        if (iv_w >> b) & 1:  # Only at G-positions
            M2[w] ^= (1 << b)

    if M2 == M_base:
        M2[0] ^= (1 << 27)

    return M2

def scalpel_rho(f_scalpel, budget):
    """Pollard rho with scalpel-generated pairs."""
    hashes = {}
    best = 256

    for i in range(budget):
        M1 = random_w16()
        M2 = f_scalpel(M1)

        H1 = sha256_compress(M1)
        H2 = sha256_compress(M2)

        # Direct pair comparison
        d = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        if d < best: best = d

        # Multi-target: compare with stored
        hk = tuple(H1)
        for h_old in list(hashes.keys())[-30:]:
            if h_old != hk:
                dd = sum(hw(H1[w] ^ list(h_old)[w]) for w in range(8))
                if dd < best: best = dd

        hashes[hk] = M1

    return best

def random_baseline(budget):
    """Pure random for comparison."""
    hashes = {}
    best = 256
    for i in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        hk = tuple(H)
        for h_old in list(hashes.keys())[-30:]:
            if h_old != hk:
                dd = sum(hw(H[w] ^ list(h_old)[w]) for w in range(8))
                if dd < best: best = dd
        hashes[hk] = M
    return best

def test_scalpel(N=20, budget=5000):
    """Test all scalpel variants."""
    print(f"\n{'='*60}")
    print(f"★-SCALPEL PRECISION TEST (N={N}, budget={budget})")
    print(f"{'='*60}")

    variants = [
        ("Random (baseline)", lambda b: random_baseline(b)),
        ("Scalpel V1 (schedule+stable)", lambda b: scalpel_rho(scalpel_pair_generator, b)),
        ("Scalpel V2 (IV-mask only)", lambda b: scalpel_rho(scalpel_pair_generator_v2, b)),
        ("Scalpel V3 (stable+IV)", lambda b: scalpel_rho(scalpel_pair_generator_v3, b)),
    ]

    results = {}
    for name, fn in variants:
        t0 = time.time()
        dHs = [fn(budget) for _ in range(N)]
        t1 = time.time()
        arr = np.array(dHs)
        results[name] = arr
        print(f"  {name:>30}: avg={arr.mean():.1f} min={arr.min()} ({t1-t0:.1f}s)")

    # Ranking
    baseline = results["Random (baseline)"]
    print(f"\n  RANKING (gain vs random):")
    for name, arr in sorted(results.items(), key=lambda x: x[1].mean()):
        gain = baseline.mean() - arr.mean()
        print(f"    {name:>30}: gain={gain:+.1f} bits")

def test_scalpel_scaling(N=12):
    """Does scalpel advantage grow with budget?"""
    print(f"\n{'='*60}")
    print(f"SCALPEL SCALING")
    print(f"{'='*60}")

    for budget in [2000, 5000, 10000, 20000]:
        rand_res = [random_baseline(budget) for _ in range(N)]
        scalpel_res = [scalpel_rho(scalpel_pair_generator_v3, budget) for _ in range(N)]

        ra = np.array(rand_res); sa = np.array(scalpel_res)
        gain = ra.mean() - sa.mean()
        print(f"  Budget {budget:>6}: random={ra.mean():.1f} scalpel={sa.mean():.1f} gain={gain:+.1f}")

def test_microscopic_accumulation(N=300):
    """Does the scalpel's advantage ACCUMULATE over observations?

    Key idea: even 0.1 bit advantage per pair, accumulated over
    millions of pairs, becomes significant.

    Measure: for scalpel vs random, what's P(dH < threshold)?
    If P_scalpel > P_random → accumulated advantage."""
    print(f"\n{'='*60}")
    print(f"MICROSCOPIC ACCUMULATION (N={N})")
    print(f"{'='*60}")

    # Generate many pairs, compare P(dH < threshold)
    scalpel_dHs = []
    random_dHs = []

    for _ in range(N):
        M1 = random_w16()

        # Scalpel pair
        M2_s = scalpel_pair_generator_v3(M1)
        H1 = sha256_compress(M1); H2_s = sha256_compress(M2_s)
        scalpel_dHs.append(sum(hw(H1[w] ^ H2_s[w]) for w in range(8)))

        # Random pair
        M2_r = random_w16()
        H2_r = sha256_compress(M2_r)
        random_dHs.append(sum(hw(H1[w] ^ H2_r[w]) for w in range(8)))

    sa = np.array(scalpel_dHs); ra = np.array(random_dHs)

    print(f"\n  Direct pair comparison:")
    print(f"    Scalpel: E[dH]={sa.mean():.2f} ± {sa.std():.2f}")
    print(f"    Random:  E[dH]={ra.mean():.2f} ± {ra.std():.2f}")
    print(f"    Diff: {ra.mean() - sa.mean():+.3f}")

    # P(dH < threshold) for various thresholds
    print(f"\n  P(dH < threshold):")
    print(f"  {'Threshold':>10} | {'Scalpel':>8} | {'Random':>8} | {'Ratio':>8}")
    print(f"  " + "-" * 40)

    for thresh in [120, 115, 110, 105, 100]:
        p_s = np.mean(sa < thresh)
        p_r = np.mean(ra < thresh)
        ratio = p_s / p_r if p_r > 0 else float('inf')
        sig = "★" if ratio > 1.3 else ""
        print(f"  {thresh:>10} | {p_s:>8.4f} | {p_r:>8.4f} | {ratio:>8.2f} {sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 176: ★-SCALPEL")
    print("Precision tool from microscopic advantages")
    print("=" * 60)

    test_microscopic_accumulation(N=500)
    test_scalpel(N=15, budget=5000)
    test_scalpel_scaling(N=10)

    print(f"\n{'='*60}")
    print(f"VERDICT: Does precision beat randomness?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
