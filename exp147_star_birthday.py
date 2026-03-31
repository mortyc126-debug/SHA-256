#!/usr/bin/env python3
"""
EXP 147: ★-Birthday — SHA-256-Specific Collision Weapon

NOT generic birthday. A weapon built FROM SHA-256's ★-structure.

PRINCIPLE: Generate messages that are ★-RELATED, not random.
★-related pairs have HIGHER collision probability than random pairs.

THREE WEAPONS:

W1: ★-FUNNEL
    Generate many messages that CONVERGE at intermediate round R.
    If N messages pass through a narrow funnel at round R,
    birthday among them on remaining rounds is cheaper.

W2: ★-SWARM
    Generate FAMILIES of messages sharing schedule properties.
    Within a family: δW is small → kill chain effective.
    Between families: independent.
    Birthday within families (cheap) + across families.

W3: ★-RESONANCE
    Use the σ₁ amplification direction (eigenvalue 3x/round).
    Generate message pairs where δ is ALIGNED with slow eigenvector.
    These pairs are "resonant" — their differences stay coherent longer.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_dist_hash(H1, H2):
    return sum(hw(H1[w] ^ H2[w]) for w in range(8))

def xor_dist_state(s1, s2):
    return sum(hw(s1[w] ^ s2[w]) for w in range(8))

# ============================================================
# WEAPON 0: Standard birthday (baseline)
# ============================================================
def weapon_birthday(budget):
    """Standard birthday: random messages, compare hashes."""
    hashes = {}
    best = 256
    for i in range(budget):
        M = random_w16()
        H = sha256_compress(M)
        hk = tuple(H)
        # Compare to recent
        for h_old in list(hashes.keys())[max(0, len(hashes)-30):]:
            d = xor_dist_hash(H, list(h_old))
            if d < best: best = d
        hashes[hk] = M
    return best

# ============================================================
# WEAPON 1: ★-FUNNEL
# ============================================================
def weapon_funnel(budget):
    """Generate messages optimized to pass through a narrow funnel
    at intermediate round R. Birthday among funneled messages."""
    R_funnel = 8  # Funnel at round 8 (kill chain still effective)
    hashes = {}
    best = 256

    # Step 1: Pick a TARGET state at round R
    M_seed = random_w16()
    target_state = sha256_rounds(M_seed, R_funnel)[R_funnel]

    # Step 2: Generate messages that reach NEAR target at round R
    # Use kill chain to steer toward target
    msgs_per_attempt = budget // 50  # 50 attempts, each with optimization

    for attempt in range(min(50, budget // 100)):
        M = random_w16()

        # Quick kill chain: optimize 4 words to approach target at R
        for w in range(min(4, 16)):
            best_val = M[w]
            best_d = xor_dist_state(sha256_rounds(M, R_funnel)[R_funnel], target_state)
            for _ in range(budget // (50 * 4)):
                val = random.randint(0, MASK)
                M_test = list(M); M_test[w] = val
                d = xor_dist_state(sha256_rounds(M_test, R_funnel)[R_funnel], target_state)
                if d < best_d:
                    best_d = d; best_val = val
            M[w] = best_val

        # Step 3: This message is now funneled. Compute full hash.
        H = sha256_compress(M)
        hk = tuple(H)
        for h_old in list(hashes.keys()):
            d = xor_dist_hash(H, list(h_old))
            if d < best: best = d
        hashes[hk] = M

    return best

# ============================================================
# WEAPON 2: ★-SWARM
# ============================================================
def weapon_swarm(budget):
    """Generate FAMILIES sharing base message, vary few words.
    Birthday within and across families."""
    n_families = int(budget ** 0.4)  # ~20 families
    per_family = budget // n_families
    hashes = {}
    best = 256

    for fam in range(n_families):
        base = random_w16()

        # Within family: change only 2-3 words (small δ → kill chain territory)
        for _ in range(per_family):
            M = list(base)
            n_changes = random.randint(2, 3)
            for _ in range(n_changes):
                w = random.randint(0, 15)
                M[w] = random.randint(0, MASK)

            H = sha256_compress(M)
            hk = tuple(H)
            for h_old in list(hashes.keys())[max(0, len(hashes)-30):]:
                d = xor_dist_hash(H, list(h_old))
                if d < best: best = d
            hashes[hk] = M

    return best

# ============================================================
# WEAPON 3: ★-RESONANCE
# ============================================================
def weapon_resonance(budget):
    """Generate pairs aligned with the slow-decay direction.
    Slow mode: word 0 bit 28 (18 rounds survival).
    Generate messages differing ONLY near the slow mode."""
    hashes = {}
    best = 256

    # Resonant difference: small change in word 0 (slow mode word)
    # specifically near bit 28 (slow bit)
    for _ in range(budget):
        M1 = random_w16()

        # Create M2 with resonant difference
        M2 = list(M1)
        # Perturb word 0, bits 24-31 (near slow mode bit 28)
        delta = random.randint(1, 255) << 24  # Only high bits of word 0
        M2[0] = (M2[0] ^ delta) & MASK

        H1 = sha256_compress(M1)
        H2 = sha256_compress(M2)
        d = xor_dist_hash(H1, H2)
        if d < best: best = d

        hk1 = tuple(H1); hk2 = tuple(H2)
        for h_old in list(hashes.keys())[max(0, len(hashes)-20):]:
            d1 = xor_dist_hash(H1, list(h_old))
            d2 = xor_dist_hash(H2, list(h_old))
            if d1 < best: best = d1
            if d2 < best: best = d2
        hashes[hk1] = M1
        hashes[hk2] = M2

    return best

# ============================================================
# WEAPON 4: ★-SCHEDULE EXPLOIT
# ============================================================
def weapon_schedule(budget):
    """Exploit schedule structure: find M pairs where
    schedule differences are CONCENTRATED in few rounds.
    δW = 0 for most rounds → kill chain effective on those rounds."""
    hashes = {}
    best = 256

    for _ in range(budget):
        M1 = random_w16()
        M2 = list(M1)

        # Change ONLY word 13 (best from exp137: 22 zero rounds in schedule)
        M2[13] = random.randint(0, MASK)

        H1 = sha256_compress(M1)
        H2 = sha256_compress(M2)
        d = xor_dist_hash(H1, H2)
        if d < best: best = d

        hk = tuple(H1)
        for h_old in list(hashes.keys())[max(0, len(hashes)-20):]:
            dd = xor_dist_hash(H1, list(h_old))
            if dd < best: best = dd
        hashes[hk] = M1

    return best

# ============================================================
# WEAPON 5: ★-COMBINED (best of all)
# ============================================================
def weapon_combined(budget):
    """Split budget: 40% swarm, 30% resonance, 30% schedule."""
    hashes = {}
    best = 256

    def add_and_check(H, M):
        nonlocal best
        hk = tuple(H)
        for h_old in list(hashes.keys())[max(0, len(hashes)-40):]:
            d = xor_dist_hash(H, list(h_old))
            if d < best: best = d
        hashes[hk] = M

    # Swarm (40%)
    b1 = int(budget * 0.4)
    n_fam = max(1, b1 // 100)
    for _ in range(n_fam):
        base = random_w16()
        for _ in range(b1 // n_fam):
            M = list(base)
            for _ in range(random.randint(1, 3)):
                M[random.randint(0, 15)] = random.randint(0, MASK)
            add_and_check(sha256_compress(M), M)

    # Resonance (30%)
    b2 = int(budget * 0.3)
    for _ in range(b2):
        M = random_w16()
        add_and_check(sha256_compress(M), M)
        M2 = list(M)
        M2[0] ^= (random.randint(1, 255) << 24)
        add_and_check(sha256_compress(M2), M2)

    # Schedule exploit (30%)
    b3 = budget - b1 - b2
    for _ in range(b3):
        M = random_w16()
        add_and_check(sha256_compress(M), M)

    return best

# ============================================================
# BATTLE ROYALE
# ============================================================
def battle(N=20, budget=8000):
    """Compare all weapons."""
    print(f"\n{'='*60}")
    print(f"★-BIRTHDAY BATTLE ROYALE (N={N}, budget={budget})")
    print(f"{'='*60}")

    weapons = [
        ("W0: Birthday (baseline)", weapon_birthday),
        ("W1: ★-Funnel", weapon_funnel),
        ("W2: ★-Swarm", weapon_swarm),
        ("W3: ★-Resonance", weapon_resonance),
        ("W4: ★-Schedule", weapon_schedule),
        ("W5: ★-Combined", weapon_combined),
    ]

    results = {}
    for name, fn in weapons:
        t0 = time.time()
        dHs = [fn(budget) for _ in range(N)]
        t1 = time.time()
        arr = np.array(dHs)
        results[name] = arr
        print(f"  {name:>25}: avg={arr.mean():.1f} min={arr.min()} "
              f"med={np.median(arr):.0f} ({t1-t0:.1f}s)")

    # Ranking
    print(f"\n  RANKING:")
    ranking = sorted(results.items(), key=lambda x: x[1].mean())
    baseline = results["W0: Birthday (baseline)"].mean()
    for i, (name, arr) in enumerate(ranking):
        gain = baseline - arr.mean()
        marker = " ★★★" if i == 0 else (" ★★" if i == 1 else "")
        print(f"    #{i+1}: {name:>25} avg={arr.mean():.1f} "
              f"gain={gain:+.1f}{marker}")

    # Statistical significance of best vs baseline
    best_name, best_arr = ranking[0]
    base_arr = results["W0: Birthday (baseline)"]
    diff = base_arr.mean() - best_arr.mean()
    pooled = math.sqrt((base_arr.std()**2 + best_arr.std()**2) / 2)
    z = diff / (pooled / math.sqrt(N)) if pooled > 0 else 0

    print(f"\n  Best vs Birthday: diff={diff:.1f} bits, Z={z:.1f}")
    if z > 3:
        print(f"  ★★★ STATISTICALLY SIGNIFICANT! p < 0.001")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 147: ★-BIRTHDAY WEAPONS")
    print("SHA-256-specific collision search")
    print("=" * 60)

    battle(N=20, budget=6000)
    print()
    battle(N=15, budget=15000)

if __name__ == "__main__":
    main()
