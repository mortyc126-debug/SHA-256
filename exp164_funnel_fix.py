#!/usr/bin/env python3
"""
EXP 164: FIX THE FUNNEL — Test on Truncated Hash

ERROR DIAGNOSIS: We align M with IV, but state_64 is random.
64 rounds destroy any structure in M.

FIX APPROACH: Test on TRUNCATED hash where we can find REAL cycles.
If ★-funnel creates SHORTER cycles on truncated hash:
  → the principle WORKS, just needs more steps at full scale
  → shorter cycle = faster collision

Test: SHA-256 truncated to K bits. Compare cycle lengths:
  - Random f-map: cycle ≈ 2^(K/2) (birthday)
  - ★-funnel f-maps: cycle = ?

If ★ cycle < random cycle → ★-funnel IS an improvement!
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def truncated_hash(M, bits=32):
    """SHA-256 truncated to first `bits` bits."""
    H = sha256_compress(M)
    if bits <= 32:
        return H[0] & ((1 << bits) - 1)
    elif bits <= 64:
        return (H[0], H[1] & ((1 << (bits - 32)) - 1))
    else:
        # Return tuple
        result = []
        remaining = bits
        for w in range(8):
            if remaining <= 0: break
            take = min(32, remaining)
            result.append(H[w] & ((1 << take) - 1))
            remaining -= take
        return tuple(result)

def hash_to_int(h, bits):
    """Convert truncated hash to integer."""
    if isinstance(h, int):
        return h
    elif isinstance(h, tuple):
        val = 0
        for i, part in enumerate(h):
            val |= (part << (32 * i))
        return val & ((1 << bits) - 1)
    return 0

def find_cycle_length(f_map, bits=20, max_steps=2**22):
    """Find cycle length using Floyd's algorithm."""
    # Start
    M = random_w16()
    h = truncated_hash(M, bits)
    h_int = hash_to_int(h, bits)

    # Tortoise and hare
    tortoise = h_int
    hare = h_int

    # Step function: hash_int → message → hash → hash_int
    def step(h_val):
        # Convert hash int back to message
        M_new = f_map(h_val, bits)
        return hash_to_int(truncated_hash(M_new, bits), bits)

    # Phase 1: Find meeting point
    for i in range(max_steps):
        tortoise = step(tortoise)
        hare = step(step(hare))
        if tortoise == hare:
            # Phase 2: Find cycle start
            tortoise = h_int
            mu = 0
            while tortoise != hare:
                tortoise = step(tortoise)
                hare = step(hare)
                mu += 1

            # Phase 3: Find cycle length
            lam = 1
            hare = step(tortoise)
            while tortoise != hare:
                hare = step(hare)
                lam += 1

            return mu, lam, i + 1  # tail, cycle, steps to detect

    return -1, -1, max_steps  # No cycle found

# ============================================================
# F-MAPS: hash_int → message
# ============================================================

def fmap_standard(h_int, bits):
    """Standard: spread hash bits across message."""
    M = [0] * 16
    for w in range(16):
        M[w] = (h_int * (w + 1) + w * 0x9E3779B9) & MASK  # Mix
    return M

def fmap_carry_aligned(h_int, bits):
    """★-Carry-Aligned: construct M to agree with IV at hash-determined positions."""
    M = [0] * 16
    for w in range(8):
        # Use hash bits to select which IV bits to agree/disagree
        selector = (h_int >> (w * 4)) & 0xF  # 4 bits per word
        # Agree with IV where selector bit = 0, disagree where = 1
        expanded = 0
        for b in range(32):
            if (selector >> (b % 4)) & 1:
                expanded |= (1 << b)
        M[w] = (IV[w] ^ expanded) & MASK
        M[w + 8] = (h_int ^ (IV[w] * (w+1))) & MASK
    return M

def fmap_schedule_weak(h_int, bits):
    """★-Schedule-Weak: put hash info in weakest schedule words."""
    M = [0] * 16
    # W[13] = weakest diffusion (exp110)
    M[13] = h_int & MASK
    # Other words: IV-based (minimal disturbance)
    for w in range(16):
        if w != 13:
            M[w] = (IV[w % 8] + h_int * (w + 7)) & MASK
    return M

def fmap_blind_spot(h_int, bits):
    """★-Blind-Spot: inject hash at carry-absorbed positions."""
    M = [0] * 16
    # Bit 1 = blind spot (65% absorbed, exp161)
    # Put hash info at bit 1 of each word
    for w in range(16):
        base = (IV[w % 8] * (w + 3)) & MASK
        # Inject h_int bit by bit at position 1 of each word
        h_bit = (h_int >> (w % bits)) & 1
        M[w] = (base & ~(1 << 1)) | (h_bit << 1)
        # Add more mixing at non-blind positions
        M[w] = (M[w] + h_int * (w * 0x45d9f3b + 1)) & MASK
    return M

def fmap_xor_iv(h_int, bits):
    """Simple: M = IV ⊕ (h spread)."""
    M = [0] * 16
    for w in range(16):
        M[w] = IV[w % 8] ^ ((h_int + w * 0x6a09e667) & MASK)
    return M

# ============================================================
# CYCLE LENGTH COMPARISON
# ============================================================
def compare_cycle_lengths(N=20, bits=20):
    """Compare cycle lengths for different f-maps."""
    print(f"\n{'='*60}")
    print(f"CYCLE LENGTH COMPARISON ({bits}-bit hash, N={N})")
    print(f"Birthday prediction: 2^{bits/2:.0f} = {2**(bits//2)}")
    print(f"{'='*60}")

    fmaps = [
        ("Standard", fmap_standard),
        ("★-Carry-Aligned", fmap_carry_aligned),
        ("★-Schedule-Weak", fmap_schedule_weak),
        ("★-Blind-Spot", fmap_blind_spot),
        ("★-XOR-IV", fmap_xor_iv),
    ]

    for name, fmap in fmaps:
        tails = []; cycles = []; detect_steps = []

        for trial in range(N):
            mu, lam, steps = find_cycle_length(fmap, bits, max_steps=2**(bits+2))
            if lam > 0:
                tails.append(mu)
                cycles.append(lam)
                detect_steps.append(steps)

        if cycles:
            ca = np.array(cycles)
            ta = np.array(tails)
            da = np.array(detect_steps)
            birthday = 2 ** (bits / 2)

            print(f"\n  {name:>20}:")
            print(f"    Avg cycle: {ca.mean():.0f} (birthday: {birthday:.0f})")
            print(f"    Med cycle: {np.median(ca):.0f}")
            print(f"    Min cycle: {ca.min()}")
            print(f"    Avg tail:  {ta.mean():.0f}")
            print(f"    Ratio vs birthday: {ca.mean()/birthday:.3f}")

            if ca.mean() < birthday * 0.8:
                print(f"    ★★★ SHORTER CYCLES THAN BIRTHDAY!")
                print(f"    Speedup: {birthday/ca.mean():.2f}×")
        else:
            print(f"\n  {name:>20}: no cycles found")

def test_scaling_cycles():
    """Do ★-cycle advantages SCALE with hash size?"""
    print(f"\n{'='*60}")
    print(f"CYCLE LENGTH SCALING")
    print(f"{'='*60}")

    for bits in [16, 18, 20, 22]:
        birthday = 2 ** (bits / 2)
        print(f"\n  {bits}-bit hash (birthday = {birthday:.0f}):")

        for name, fmap in [
            ("Standard", fmap_standard),
            ("★-Carry-Aligned", fmap_carry_aligned),
            ("★-XOR-IV", fmap_xor_iv),
        ]:
            cycles = []
            N = max(5, 30 // (bits // 4))

            for _ in range(N):
                mu, lam, _ = find_cycle_length(fmap, bits, max_steps=2**(bits+1))
                if lam > 0:
                    cycles.append(lam)

            if cycles:
                avg = np.mean(cycles)
                ratio = avg / birthday
                marker = " ★★★" if ratio < 0.8 else ""
                print(f"    {name:>20}: avg_cycle={avg:.0f}, "
                      f"ratio={ratio:.3f}{marker}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 164: FIX THE FUNNEL — TRUNCATED HASH CYCLES")
    print("=" * 60)

    compare_cycle_lengths(N=15, bits=20)
    test_scaling_cycles()

    print(f"\n{'='*60}")
    print(f"VERDICT: Does ★-funnel shorten cycles?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
