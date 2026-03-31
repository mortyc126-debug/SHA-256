#!/usr/bin/env python3
"""
EXP 165: Stability Analysis + Blind-Spot Funnel Optimization

TRACK 1: WHY is ★-advantage unstable across hash sizes?
  - Test at every bit size 16-24
  - Check: is f-map IMAGE SIZE different? (degenerate maps → trivial short cycles)
  - Measure: ★-gain OVER standard (not absolute)

TRACK 2: Optimize blind-spot funnel
  - Test variations of blind-spot construction
  - Find the BEST blind-spot pattern
  - Check if it scales consistently
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def truncated_hash_int(M, bits):
    """SHA-256 truncated to first bits, returned as int."""
    H = sha256_compress(M)
    val = 0
    remaining = bits
    shift = 0
    for w in range(8):
        if remaining <= 0: break
        take = min(32, remaining)
        val |= (H[w] & ((1 << take) - 1)) << shift
        shift += take
        remaining -= take
    return val

def find_cycle(f_map, bits, max_steps=None):
    """Floyd's cycle detection."""
    if max_steps is None:
        max_steps = min(2 ** (bits + 1), 2**23)

    start = random.randint(0, (1 << bits) - 1)

    def step(h):
        M = f_map(h, bits)
        return truncated_hash_int(M, bits)

    tortoise = step(start)
    hare = step(step(start))

    for i in range(max_steps):
        if tortoise == hare:
            # Find cycle length
            lam = 1
            hare = step(tortoise)
            while tortoise != hare:
                hare = step(hare)
                lam += 1
            return lam
        tortoise = step(tortoise)
        hare = step(step(hare))

    return -1

def count_image_size(f_map, bits, N=10000):
    """How many DISTINCT messages does f_map produce from N random inputs?"""
    outputs = set()
    for _ in range(N):
        h = random.randint(0, (1 << bits) - 1)
        M = f_map(h, bits)
        outputs.add(tuple(M))
    return len(outputs)

# ============================================================
# F-MAPS
# ============================================================

def fmap_standard(h_int, bits):
    M = [0] * 16
    for w in range(16):
        M[w] = (h_int * (w + 1) * 0x9E3779B9 + w * 0x6a09e667) & MASK
    return M

def fmap_blind_v1(h_int, bits):
    """Original blind-spot (exp164)."""
    M = [0] * 16
    for w in range(16):
        base = (IV[w % 8] * (w + 3)) & MASK
        h_bit = (h_int >> (w % bits)) & 1
        M[w] = (base & ~(1 << 1)) | (h_bit << 1)
        M[w] = (M[w] + h_int * (w * 0x45d9f3b + 1)) & MASK
    return M

def fmap_blind_v2(h_int, bits):
    """Improved: more hash bits at blind positions, IV at clear."""
    M = [0] * 16
    blind_positions = [1, 2, 19, 22, 30]  # High absorption (exp161)
    for w in range(16):
        # Start with IV (max G/K)
        M[w] = IV[w % 8]
        # Inject hash at BLIND positions
        for bp in blind_positions:
            h_bit = (h_int >> ((w * 5 + bp) % bits)) & 1
            M[w] = (M[w] & ~(1 << bp)) | (h_bit << bp)
        # Add hash-based variation
        M[w] ^= ((h_int * (w + 1)) >> 3) & 0xFF  # Low-order mixing
    return M

def fmap_blind_v3(h_int, bits):
    """V3: Use ALL high-absorption positions, minimal clear disturbance."""
    M = [0] * 16
    # Absorption from exp161: bit 1=65%, bit 2=50%, bit 22=49%, bit 19=47%, bit 30=47%
    # Clear: bit 0=0%, bit 5=38%, bit 23=37%, bit 28=37%
    for w in range(16):
        # Base: IV (produces G/K, no P)
        M[w] = IV[w % 8]
        # Inject h at high-absorption bits (these get eaten by carry)
        M[w] ^= ((h_int >> (w % max(bits, 1))) & 1) << 1   # bit 1: 65%
        M[w] ^= ((h_int >> ((w+4) % max(bits, 1))) & 1) << 2   # bit 2: 50%
        M[w] ^= ((h_int >> ((w+8) % max(bits, 1))) & 1) << 22  # bit 22: 49%
        # Add enough variation to avoid degenerate image
        M[w] = (M[w] + (h_int * (0x100 + w))) & MASK
    return M

def fmap_maxmix(h_int, bits):
    """Maximum mixing: spread hash bits maximally across message."""
    M = [0] * 16
    # Use hash int to seed a simple PRNG, generate all message words
    state = h_int ^ 0xDEADBEEF
    for w in range(16):
        state = ((state * 1103515245 + 12345) & MASK)
        M[w] = state ^ IV[w % 8]
    return M

# ============================================================
# TRACK 1: STABILITY ANALYSIS
# ============================================================

def test_stability(N_trials=10):
    """Test cycle lengths at every bit size, measure image size."""
    print(f"\n{'='*60}")
    print(f"STABILITY ANALYSIS: CYCLE LENGTH vs HASH SIZE")
    print(f"{'='*60}")

    fmaps = [
        ("Standard", fmap_standard),
        ("Blind-V1", fmap_blind_v1),
        ("Blind-V2", fmap_blind_v2),
        ("Blind-V3", fmap_blind_v3),
        ("MaxMix", fmap_maxmix),
    ]

    # First: check image sizes
    print(f"\n  IMAGE SIZE CHECK (N=5000 inputs):")
    print(f"  {'Map':>12}", end="")
    for bits in [16, 18, 20, 22]:
        print(f" | {bits}b", end="")
    print()

    for name, fmap in fmaps:
        print(f"  {name:>12}", end="")
        for bits in [16, 18, 20, 22]:
            img = count_image_size(fmap, bits, N=5000)
            ratio = img / 5000
            print(f" | {ratio:.3f}", end="")
        print()

    print(f"\n  (1.0 = all distinct = good. <0.5 = degenerate = bad)")

    # Cycle lengths
    print(f"\n  CYCLE LENGTHS (median of {N_trials} trials):")
    print(f"  {'Map':>12}", end="")
    for bits in range(16, 25):
        print(f" | {bits:>5}b", end="")
    print()
    print(f"  {'birthday':>12}", end="")
    for bits in range(16, 25):
        print(f" | {2**(bits//2):>5}", end="")
    print()
    print(f"  " + "-" * (14 + 8 * 9))

    for name, fmap in fmaps:
        print(f"  {name:>12}", end="")
        for bits in range(16, 25):
            cycles = []
            for _ in range(N_trials):
                lam = find_cycle(fmap, bits)
                if lam > 0:
                    cycles.append(lam)

            if cycles:
                med = int(np.median(cycles))
                birthday = 2 ** (bits // 2)
                ratio = np.median(cycles) / birthday
                marker = "*" if ratio < 0.5 else " "
                print(f" | {med:>4}{marker}", end="")
            else:
                print(f" |    -", end="")
        print()

    # Compute ★-gain OVER standard
    print(f"\n  ★-GAIN OVER STANDARD (ratio std/★, >1 = ★ wins):")
    std_cycles = {}
    for bits in range(16, 25):
        cycles = [find_cycle(fmap_standard, bits) for _ in range(N_trials)]
        cycles = [c for c in cycles if c > 0]
        std_cycles[bits] = np.median(cycles) if cycles else 2**(bits//2)

    for name, fmap in fmaps:
        if name == "Standard":
            continue
        print(f"  {name:>12}", end="")
        gains = []
        for bits in range(16, 25):
            cycles = [find_cycle(fmap, bits) for _ in range(N_trials)]
            cycles = [c for c in cycles if c > 0]
            med = np.median(cycles) if cycles else 2**(bits//2)
            gain = std_cycles[bits] / med if med > 0 else 0
            gains.append(gain)
            marker = "★" if gain > 1.5 else " "
            print(f" | {gain:>4.1f}{marker}", end="")

        avg_gain = np.mean(gains)
        print(f" | avg={avg_gain:.2f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 165: STABILITY + BLIND-SPOT OPTIMIZATION")
    print("=" * 60)

    test_stability(N_trials=8)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
