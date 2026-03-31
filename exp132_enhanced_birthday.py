#!/usr/bin/env python3
"""
EXP 132: Enhanced Birthday — Combine multi-target with ★-knowledge

V8 gave 9.4 bits. Can we squeeze MORE by combining strategies?

NEW VARIANTS:

V9:  Multi-target + half-match
     Generate families: fix 8 words, vary 8 others.
     Birthday within family + across families.

V10: Pollard's rho (standard, O(1) memory)
     f(x) = SHA256(x) iterated. Detect cycle = collision.

V11: ★-rho (Pollard with ★-enhanced iteration)
     Instead of f(x) = SHA(x), use ★-walk as iteration.

V12: ★-sorted birthday
     Compute N hashes. Sort/bucket by partial hash.
     Look for collision within buckets.

V13: Multi-target with ★-seeded generation
     Generate messages from ★-favorable seeds.
     Half-match + few-word variation + multi-target.

V14: Truncated-hash birthday
     Look for collision on FEWER bits first (easier).
     Then expand to full hash. (Near-collision → collision)
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_dist(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def full_hash(W16):
    return sha256_compress(W16)

def trunc_hash(H, bits=32):
    """Truncate hash to first `bits` bits."""
    result = 0
    for w in range(min(bits // 32 + 1, 8)):
        if w * 32 < bits:
            mask = (1 << min(32, bits - w * 32)) - 1
            result |= (H[w] & mask) << (w * 32)
    return result

# ============================================================
# V8 baseline: Multi-target
# ============================================================
def v8_multi_target(budget):
    hashes = {}
    best = 256
    for i in range(budget):
        M = random_w16()
        H = full_hash(M)
        h_key = tuple(H)
        if h_key in hashes and hashes[h_key] != M:
            return 0  # Exact collision!
        # Check distance to a sample of stored hashes
        if i > 0 and i % 50 == 0:
            for h_stored in list(hashes.keys())[-20:]:
                d = xor_dist(list(h_stored), H)
                if d < best: best = d
        hashes[h_key] = M
    return best

# ============================================================
# V9: Multi-target + half-match families
# ============================================================
def v9_family_birthday(budget):
    """Create families of related messages, birthday across all."""
    hashes = {}  # hash → message
    best = 256
    n_families = 10
    msgs_per_family = budget // n_families

    for fam in range(n_families):
        # Family base: random 8 words
        base = random_w16()
        fixed_words = random.sample(range(16), 8)

        for _ in range(msgs_per_family):
            M = list(base)
            for w in range(16):
                if w not in fixed_words:
                    M[w] = random.randint(0, MASK)

            H = full_hash(M)
            h_key = tuple(H)

            # Check against ALL stored
            if h_key in hashes:
                if hashes[h_key] != M:
                    return 0

            # Sample check
            for h_stored in list(hashes.keys())[-15:]:
                d = xor_dist(list(h_stored), H)
                if d < best: best = d

            hashes[h_key] = M

    return best

# ============================================================
# V10: Pollard's rho (standard)
# ============================================================
def v10_pollard_rho(budget):
    """Standard Pollard's rho for collision.
    f: message → message (hash as message input)."""
    def hash_to_msg(H):
        """Convert 8-word hash to 16-word message."""
        return list(H) + list(H)  # Repeat to fill 16 words

    # Start
    M = random_w16()
    H = full_hash(M)
    tortoise = hash_to_msg(H)
    hare = hash_to_msg(H)

    best = 256

    for step in range(budget // 2):  # Hare moves 2x
        # Tortoise: one step
        H_t = full_hash(tortoise)
        tortoise = hash_to_msg(H_t)

        # Hare: two steps
        H_h = full_hash(hare)
        hare = hash_to_msg(H_h)
        H_h2 = full_hash(hare)
        hare = hash_to_msg(H_h2)

        # Check distance
        d = xor_dist(H_t, H_h2)
        if d < best: best = d
        if d == 0 and tortoise != hare:
            return 0  # Collision!

    return best

# ============================================================
# V11: ★-rho (Pollard with ★-iteration)
# ============================================================
def v11_star_rho(budget):
    """Pollard's rho with ★-enhanced iteration.
    Instead of hash_to_msg, use ★-walk."""
    def star_step(M):
        """★-enhanced step: hash, then mix with ★-structure."""
        H = full_hash(M)
        # Mix hash back into message using ★-operations
        M_new = list(M)
        for w in range(8):
            # ★-mix: XOR hash word with message word,
            # AND determines which words to modify
            M_new[w] = M[w] ^ H[w]  # XOR part of ★
            M_new[w + 8] = (M[w + 8] + H[w]) & MASK  # Add part (★⁻¹)
        return M_new

    M = random_w16()
    tortoise = list(M)
    hare = list(M)
    best = 256

    for step in range(budget // 2):
        tortoise = star_step(tortoise)
        hare = star_step(star_step(hare))

        H_t = full_hash(tortoise)
        H_h = full_hash(hare)

        d = xor_dist(H_t, H_h)
        if d < best: best = d
        if d == 0 and tortoise != hare:
            return 0

    return best

# ============================================================
# V12: ★-sorted birthday (bucket by partial hash)
# ============================================================
def v12_sorted_birthday(budget):
    """Compute hashes, bucket by first K bits, find close pairs in buckets."""
    bucket_bits = 16  # 2^16 = 65536 buckets
    buckets = {}
    best = 256

    for _ in range(budget):
        M = random_w16()
        H = full_hash(M)
        key = H[0] & ((1 << bucket_bits) - 1)  # First 16 bits

        if key in buckets:
            for H_old, M_old in buckets[key]:
                d = xor_dist(H, H_old)
                if d < best:
                    best = d
                if d == 0 and M != M_old:
                    return 0
            buckets[key].append((H, M))
        else:
            buckets[key] = [(H, M)]

    return best

# ============================================================
# V13: Multi-target + ★-seeded
# ============================================================
def v13_star_seeded(budget):
    """Generate messages from a small number of seeds,
    varying 2-3 words per seed. Multi-target across all."""
    hashes = {}
    best = 256
    n_seeds = max(1, budget // 200)

    for seed_idx in range(n_seeds):
        base = random_w16()
        for _ in range(min(200, budget // n_seeds)):
            M = list(base)
            # Change 2-3 words
            for _ in range(random.randint(2, 3)):
                w = random.randint(0, 15)
                M[w] = random.randint(0, MASK)

            H = full_hash(M)
            h_key = tuple(H)

            for h_stored in list(hashes.keys())[-20:]:
                d = xor_dist(list(h_stored), H)
                if d < best: best = d

            hashes[h_key] = M

    return best

# ============================================================
# V14: Truncated birthday (find partial collision first)
# ============================================================
def v14_truncated_birthday(budget):
    """Find collision on first 32 bits, then check full hash."""
    trunc_bits = 20
    buckets = {}
    best = 256
    partial_collisions = 0

    for _ in range(budget):
        M = random_w16()
        H = full_hash(M)
        key = trunc_hash(H, trunc_bits)

        if key in buckets:
            for H_old, M_old in buckets[key][:5]:  # Limit per bucket
                # Partial collision found! Check full distance
                d = xor_dist(H, H_old)
                if d < best:
                    best = d
                    partial_collisions += 1
            buckets[key].append((H, M))
        else:
            buckets[key] = [(H, M)]

    return best

# ============================================================
# COMPARISON
# ============================================================
def run_comparison(N=25, budget=8000):
    print(f"\n--- ENHANCED BIRTHDAY COMPARISON (N={N}, budget={budget}) ---")

    variants = [
        ("V8:  Multi-target", v8_multi_target),
        ("V9:  Family birthday", v9_family_birthday),
        ("V10: Pollard rho", v10_pollard_rho),
        ("V11: ★-rho", v11_star_rho),
        ("V12: Sorted birthday", v12_sorted_birthday),
        ("V13: ★-seeded", v13_star_seeded),
        ("V14: Truncated bday", v14_truncated_birthday),
    ]

    results = {}
    for name, fn in variants:
        t0 = time.time()
        dHs = [fn(budget) for _ in range(N)]
        t1 = time.time()
        arr = np.array(dHs)
        results[name] = arr
        print(f"  {name:>25}: avg={arr.mean():>6.1f}  min={arr.min():>3}  "
              f"med={np.median(arr):>5.0f}  t={t1-t0:.1f}s")

    # Ranking
    print(f"\n  RANKING:")
    ranking = sorted(results.items(), key=lambda x: x[1].mean())
    for i, (name, arr) in enumerate(ranking):
        marker = " ★★★" if i == 0 else (" ★★" if i == 1 else (" ★" if i == 2 else ""))
        delta = results["V8:  Multi-target"].mean() - arr.mean()
        vs_v8 = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
        print(f"    #{i+1}: {name:>25} avg={arr.mean():.1f} min={arr.min()} vs_V8:{vs_v8}{marker}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 132: ENHANCED BIRTHDAY")
    print("Combine multi-target + ★ + Pollard + truncation")
    print("=" * 60)

    run_comparison(N=25, budget=8000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
