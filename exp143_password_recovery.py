#!/usr/bin/env python3
"""
EXP 143: Password Recovery — Apply ALL ★-knowledge

8-char password, SHA-256 hash known.
Can ★-algebra reduce brute-force cost?

TOOLS FROM 142 EXPERIMENTS:
  - Schedule: W[0] weakest diffusion (exp110)
  - ★⁻¹ Jacobian: exact for δ=±1 (exp127)
  - Character structure: password bytes in known positions
  - Near-collision signals in ★-space (exp117)

PRACTICAL APPROACHES:
  V0: Pure brute force (baseline)
  V1: Schedule-aware order (crack weak words first)
  V2: ★-Jacobian guided (local search from near-miss)
  V3: Character-frequency bias (common chars first)
  V4: ★-filtered candidates (skip ★-unfavorable)
  V5: Combined best
"""
import sys, os, random, math, time, string, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# Use real SHA-256 (hashlib) for passwords
def sha256_password(password):
    """SHA-256 hash of password string."""
    return hashlib.sha256(password.encode('ascii')).digest()

def hash_distance(h1, h2):
    """Hamming distance between two hashes."""
    return sum(bin(a ^ b).count('1') for a, b in zip(h1, h2))

# Reduced charset for tractable experiments
CHARSET_FULL = string.printable[:95]  # 95 chars
CHARSET_SMALL = string.ascii_lowercase + string.digits  # 36 chars
CHARSET_TINY = string.ascii_lowercase[:10]  # 10 chars (a-j) for testing

def random_password(length, charset):
    return ''.join(random.choice(charset) for _ in range(length))

# ============================================================
# V0: Pure brute force
# ============================================================
def v0_bruteforce(target_hash, length, charset, budget):
    """Pure random brute force."""
    best_dist = 256; found = False
    for _ in range(budget):
        pw = random_password(length, charset)
        h = sha256_password(pw)
        d = hash_distance(target_hash, h)
        if d < best_dist: best_dist = d
        if d == 0:
            found = True; break
    return best_dist, found

# ============================================================
# V1: Schedule-aware (try variations in "weak" byte positions)
# ============================================================
def v1_schedule_aware(target_hash, target_pw, length, charset, budget):
    """Crack bytes in positions 4-7 first (W[1], weaker diffusion for short msgs),
    then positions 0-3."""
    best_dist = 256; found = False

    # For 8-char password: chars 0-3 → W[0], chars 4-7 → W[1]
    # exp110: W[0] has weakest SCHEDULE diffusion
    # But for password cracking, this means: start from W[1] side

    for _ in range(budget):
        pw = list(target_pw)  # Start from known password
        # Mutate positions 4-7 first (higher byte positions)
        n_changes = random.randint(1, 4)
        positions = random.sample(range(length), n_changes)
        for p in positions:
            pw[p] = random.choice(charset)
        h = sha256_password(''.join(pw))
        d = hash_distance(target_hash, h)
        if d < best_dist: best_dist = d
        if d == 0: found = True; break
    return best_dist, found

# ============================================================
# V2: ★-Jacobian guided (gradient on character changes)
# ============================================================
def v2_jacobian_guided(target_hash, length, charset, budget):
    """Start from random password, use Jacobian-like guidance."""
    pw = list(random_password(length, charset))
    h = sha256_password(''.join(pw))
    best_dist = hash_distance(target_hash, h)
    best_pw = list(pw)

    evals = 0
    while evals < budget:
        improved = False
        # Try changing each position to each character
        for pos in range(length):
            if evals >= budget: break
            original = pw[pos]
            best_char = original
            for c in random.sample(list(charset), min(len(charset), 10)):
                pw[pos] = c
                h = sha256_password(''.join(pw))
                d = hash_distance(target_hash, h)
                evals += 1
                if d < best_dist:
                    best_dist = d
                    best_char = c
                    improved = True
                if d == 0:
                    return 0, True
            pw[pos] = best_char

        if not improved:
            # Restart with random password
            pw = list(random_password(length, charset))
            h = sha256_password(''.join(pw))
            d = hash_distance(target_hash, h)
            if d < best_dist:
                best_dist = d
                best_pw = list(pw)

    return best_dist, False

# ============================================================
# V3: Frequency-biased (common characters first)
# ============================================================
def v3_frequency_biased(target_hash, length, charset, budget):
    """Try common characters more often."""
    # English frequency: e, t, a, o, i, n, s, h, r
    common = 'etaoinshrdlcumwfgypbvkjxqz0123456789'
    weighted_charset = common * 3 + charset  # 3x weight on common

    best_dist = 256
    for _ in range(budget):
        pw = ''.join(random.choice(weighted_charset) for _ in range(length))
        h = sha256_password(pw)
        d = hash_distance(target_hash, h)
        if d < best_dist: best_dist = d
        if d == 0: return 0, True
    return best_dist, False

# ============================================================
# V4: Hybrid (random + Jacobian refinement)
# ============================================================
def v4_hybrid(target_hash, length, charset, budget):
    """80% random search, 20% refine best found."""
    best_dist = 256
    best_pw = None

    # Phase 1: random search
    phase1 = int(budget * 0.8)
    for _ in range(phase1):
        pw = random_password(length, charset)
        h = sha256_password(pw)
        d = hash_distance(target_hash, h)
        if d < best_dist:
            best_dist = d
            best_pw = pw
        if d == 0: return 0, True

    # Phase 2: refine around best
    if best_pw:
        pw = list(best_pw)
        phase2 = budget - phase1
        for _ in range(phase2):
            pos = random.randint(0, length - 1)
            old_c = pw[pos]
            pw[pos] = random.choice(charset)
            h = sha256_password(''.join(pw))
            d = hash_distance(target_hash, h)
            if d < best_dist:
                best_dist = d
            else:
                pw[pos] = old_c  # Revert
            if d == 0: return 0, True

    return best_dist, False

# ============================================================
# COMPARISON
# ============================================================
def compare_methods(N=20, pw_length=4, charset=CHARSET_TINY, budget=5000):
    """Compare all methods on small passwords."""
    print(f"\n--- PASSWORD RECOVERY: {pw_length} chars, |charset|={len(charset)}, "
          f"space=2^{math.log2(len(charset)**pw_length):.1f} ---")

    methods = [
        ("V0: Brute force", lambda th, tp: v0_bruteforce(th, pw_length, charset, budget)),
        ("V3: Freq-biased", lambda th, tp: v3_frequency_biased(th, pw_length, charset, budget)),
        ("V2: Jacobian", lambda th, tp: v2_jacobian_guided(th, pw_length, charset, budget)),
        ("V4: Hybrid", lambda th, tp: v4_hybrid(th, pw_length, charset, budget)),
    ]

    results = {name: {'dists': [], 'found': 0} for name, _ in methods}

    for trial in range(N):
        target_pw = random_password(pw_length, charset)
        target_hash = sha256_password(target_pw)

        for name, fn in methods:
            d, found = fn(target_hash, target_pw)
            results[name]['dists'].append(d)
            if found:
                results[name]['found'] += 1

    print(f"\n  {'Method':>20} | {'Found':>5} | {'Avg dH':>7} | {'Min dH':>7}")
    print(f"  " + "-" * 50)
    for name, _ in methods:
        r = results[name]
        arr = np.array(r['dists'])
        print(f"  {name:>20} | {r['found']:>5} | {arr.mean():>7.1f} | {arr.min():>7}")

def test_scaling(charset=CHARSET_TINY):
    """How do methods scale with password length?"""
    print(f"\n--- SCALING WITH PASSWORD LENGTH ---")

    for pw_len in [2, 3, 4, 5]:
        space = len(charset) ** pw_len
        budget = min(space * 2, 50000)  # 2x the space
        N = 15

        found_bf = 0; found_hybrid = 0

        for _ in range(N):
            target_pw = random_password(pw_len, charset)
            target_hash = sha256_password(target_pw)

            _, f1 = v0_bruteforce(target_hash, pw_len, charset, budget)
            _, f2 = v4_hybrid(target_hash, pw_len, charset, budget)
            found_bf += f1
            found_hybrid += f2

        print(f"  len={pw_len}, space=2^{math.log2(space):.1f}, budget={budget}: "
              f"brute={found_bf}/{N}, hybrid={found_hybrid}/{N}")

def test_real_scenario():
    """Realistic test: crack 6-char lowercase password."""
    print(f"\n--- REALISTIC SCENARIO: 6-char lowercase ---")

    charset = string.ascii_lowercase  # 26 chars
    pw_len = 6
    space = 26**6  # ≈ 309M ≈ 2^28.2
    budget = 500000  # 0.16% of space

    print(f"  Space: {space:,} = 2^{math.log2(space):.1f}")
    print(f"  Budget: {budget:,} = 2^{math.log2(budget):.1f}")
    print(f"  Coverage: {budget/space*100:.2f}%")

    target_pw = random_password(pw_len, charset)
    target_hash = sha256_password(target_pw)

    # Race
    for name, fn in [
        ("Brute force", lambda: v0_bruteforce(target_hash, pw_len, charset, budget)),
        ("Hybrid", lambda: v4_hybrid(target_hash, pw_len, charset, budget)),
    ]:
        t0 = time.time()
        d, found = fn()
        t1 = time.time()
        status = f"FOUND!" if found else f"best dH={d}"
        print(f"  {name:>15}: {status} ({t1-t0:.1f}s)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 143: PASSWORD RECOVERY WITH ★-KNOWLEDGE")
    print("=" * 60)

    compare_methods(N=20, pw_length=3, charset=CHARSET_TINY, budget=3000)
    compare_methods(N=15, pw_length=4, charset=CHARSET_TINY, budget=20000)
    test_scaling()
    test_real_scenario()

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
