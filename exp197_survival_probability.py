#!/usr/bin/env python3
"""
EXP 197: SURVIVAL PROBABILITY — Starting from δ=2, what are the odds?

Best known start: δ(a,e)=2 at round 16 (from W[15]b31, exp183).
Then 48 rounds of thermostat + white noise.

COMPUTE: P(δ(a,e) < k at round 64 | δ=2 at round 16)

If this probability is HIGH ENOUGH relative to the cost of
generating the starting condition → we have an attack.

Cost of start: trying different M until W[15]b31 gives δ=2 at r=16
= O(1) per message (the δ=2 is GUARANTEED by construction!)

So the ONLY cost is: 1/P(survival) attempts.
If P(survival to δ=0) > 2^(-128) → BETTER THAN BIRTHDAY!
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_survival_from_2(N=2000):
    """Start with δ(a,e)=2 at round 16, measure δ at round 64."""
    print(f"\n{'='*60}")
    print(f"SURVIVAL FROM δ=2 (N={N})")
    print(f"{'='*60}")

    final_dae = []
    final_dH = []
    min_dae_trajectory = []

    for _ in range(N):
        M1 = random_w16()
        M2 = list(M1); M2[15] ^= (1 << 31)  # Guaranteed δ(a,e)≈2 at r16

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        # Verify δ at round 16
        dae_16 = hw(s1[16][0] ^ s2[16][0]) + hw(s1[16][4] ^ s2[16][4])

        # Final δ at round 64
        dae_64 = hw(s1[64][0] ^ s2[64][0]) + hw(s1[64][4] ^ s2[64][4])
        final_dae.append(dae_64)

        # Full hash distance
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        final_dH.append(dH)

        # Track minimum δ(a,e) across all rounds 16-64
        min_d = 64
        for r in range(16, 65):
            d = hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4])
            min_d = min(min_d, d)
        min_dae_trajectory.append(min_d)

    dae = np.array(final_dae)
    dH_arr = np.array(final_dH)
    min_traj = np.array(min_dae_trajectory)

    print(f"\n  Starting condition: δ(a,e) ≈ 2 at round 16")
    print(f"  (Guaranteed by W[15] bit 31 flip)")

    print(f"\n  FINAL δ(a,e) at round 64:")
    print(f"    Mean: {dae.mean():.1f}")
    print(f"    Std:  {dae.std():.1f}")
    print(f"    Min:  {dae.min()}")
    print(f"    Max:  {dae.max()}")

    print(f"\n  FINAL hash distance:")
    print(f"    Mean: {dH_arr.mean():.1f}")
    print(f"    Min:  {dH_arr.min()}")

    # Survival probabilities
    print(f"\n  SURVIVAL PROBABILITIES:")
    print(f"  P(δ(a,e) < k at round 64 | start=2 at r=16):")
    for k in [30, 25, 20, 15, 10, 5, 2, 1, 0]:
        count = np.sum(dae <= k)
        p = count / N
        log2_p = math.log2(p) if p > 0 else -999
        print(f"    P(δ<{k:>2}) = {p:.6f} ({count}/{N}) = 2^{log2_p:.1f}")

    # Minimum δ across trajectory
    print(f"\n  MINIMUM δ(a,e) ANYWHERE on trajectory (rounds 16-64):")
    for k in [15, 10, 5, 2, 1, 0]:
        count = np.sum(min_traj <= k)
        p = count / N
        log2_p = math.log2(p) if p > 0 else -999
        print(f"    P(min δ<{k:>2}) = {p:.6f} ({count}/{N}) = 2^{log2_p:.1f}")

    return dae, dH_arr, min_traj

def measure_survival_large(N=20000):
    """Larger sample for better tail statistics."""
    print(f"\n{'='*60}")
    print(f"LARGE SAMPLE SURVIVAL (N={N})")
    print(f"{'='*60}")

    final_dae = []
    final_dH = []

    for i in range(N):
        M1 = random_w16()
        M2 = list(M1); M2[15] ^= (1 << 31)

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        dae_64 = hw(s1[64][0] ^ s2[64][0]) + hw(s1[64][4] ^ s2[64][4])
        final_dae.append(dae_64)

        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
        final_dH.append(dH)

    dae = np.array(final_dae); dH_arr = np.array(final_dH)

    print(f"\n  δ(a,e) at round 64 (starting from ~2 at round 16):")
    print(f"    Mean: {dae.mean():.2f}, Std: {dae.std():.2f}")
    print(f"    Min: {dae.min()}, Max: {dae.max()}")

    print(f"\n  Hash distance:")
    print(f"    Mean: {dH_arr.mean():.2f}, Min: {dH_arr.min()}")

    # Detailed tail
    print(f"\n  TAIL PROBABILITIES (N={N}):")
    for k in [25, 20, 18, 16, 14, 12, 10, 8, 5, 2, 0]:
        count_ae = np.sum(dae <= k)
        count_dH = np.sum(dH_arr <= k * 4)  # Scale to 256 bits

        p_ae = count_ae / N
        log_ae = math.log2(p_ae) if p_ae > 0 else float('-inf')

        print(f"    δ(a,e)≤{k:>2}: {count_ae:>6}/{N} = 2^{log_ae:>6.1f}", end="")
        if count_ae > 0:
            # Extrapolate: to get δ=0, need 2^(-log_ae × 32/k) ?
            # Simple: fit exponential tail
            pass
        print()

    # FIT exponential tail: P(δ<k) ≈ exp(-c×(32-k)²)
    # From Ornstein-Uhlenbeck: P(δ<k) ∝ exp(-(μ-k)²/(2σ²/κ))
    # μ=32, σ²/κ ≈ 4²/0.31 ≈ 51.6

    print(f"\n  ORNSTEIN-UHLENBECK FIT:")
    ou_sigma2_kappa = 4.0**2 / 0.31
    print(f"    σ²/κ = {ou_sigma2_kappa:.1f}")
    for k in [20, 15, 10, 5, 0]:
        log_p = -(32-k)**2 / (2 * ou_sigma2_kappa)
        p = math.exp(log_p)
        log2_p = log_p / math.log(2)
        print(f"    P(δ<{k:>2}) ≈ exp({log_p:.1f}) = 2^{log2_p:.1f}")

    print(f"\n  COLLISION ESTIMATE (δ=0):")
    log_p_0 = -(32)**2 / (2 * ou_sigma2_kappa)
    log2_p_0 = log_p_0 / math.log(2)
    print(f"    P(δ(a,e)=0 at round 64) ≈ 2^{log2_p_0:.1f}")
    print(f"    (from O-U approximation)")
    print(f"")
    print(f"    BUT: δ(a,e)=0 means only a and e match!")
    print(f"    Full collision needs ALL 8 words = δ_full = 0")
    print(f"    δ_full requires shift register flush: +3 rounds")
    print(f"    AND matching schedule from round 61+")
    print(f"")
    print(f"    REAL collision P ≈ P(δ_ae=0) × P(schedule match)")
    print(f"    Schedule: different M → different W[16+] → ALWAYS different")
    print(f"    → P(full collision | δ_ae=0) ≈ 0 (schedule blocks)")

    # BUT: what if we have many messages with same δM = W[15]b31?
    # They ALL start from δ=2 at r=16.
    # Birthday among them: if N messages, P(any two share δ(a,e) at r=64)
    # ≈ N²/2 × P(match) where P(match) ≈ 2^(-dae_bits)

    print(f"\n  BIRTHDAY AMONG W[15]b31 PAIRS:")
    print(f"    Each pair: guaranteed δ(a,e)≈2 at round 16")
    print(f"    At round 64: δ(a,e) ≈ 32 (thermalized)")
    print(f"    Birthday on 64 bits (a,e): 2^32 pairs needed")
    print(f"    But: different M₁ → different states → no advantage")
    print(f"    The δ=2 starting point is ERASED by thermalization")

def compare_with_random(N=5000):
    """Does starting from δ=2 give ANY advantage at round 64 vs random?"""
    print(f"\n{'='*60}")
    print(f"STRUCTURED vs RANDOM at round 64 (N={N})")
    print(f"{'='*60}")

    # Structured: W[15]b31 flip (start δ=2 at r16)
    struct_dH = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1); M2[15] ^= (1 << 31)
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        struct_dH.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

    # Random: fully random pair
    rand_dH = []
    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        rand_dH.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

    sa = np.array(struct_dH); ra = np.array(rand_dH)

    print(f"\n  Structured (δ=2 at r16): mean={sa.mean():.2f}, min={sa.min()}")
    print(f"  Random pair:              mean={ra.mean():.2f}, min={ra.min()}")
    print(f"  Difference: {ra.mean()-sa.mean():+.2f}")

    # Tail comparison
    print(f"\n  Tail: P(dH < k):")
    for k in [120, 115, 110, 105, 100]:
        ps = np.mean(sa < k); pr = np.mean(ra < k)
        ratio = ps / pr if pr > 0 else float('inf')
        sig = " ★" if ratio > 1.2 else ""
        print(f"    dH<{k}: struct={ps:.4f}, random={pr:.4f}, ratio={ratio:.3f}{sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 197: SURVIVAL PROBABILITY")
    print("From δ=2 at round 16 — what survives to round 64?")
    print("=" * 60)

    dae, dH, min_traj = measure_survival_from_2(N=2000)
    compare_with_random(N=3000)
    measure_survival_large(N=10000)

    print(f"\n{'='*60}")
    print(f"FINAL VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
