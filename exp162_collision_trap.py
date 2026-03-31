#!/usr/bin/env python3
"""
EXP 162: COLLISION TRAP — Let the collision find US

Not searching — TRAPPING. Create a self-correcting iteration
where SHA-256's own dynamics drive toward collision.

CONCEPT: Define f: hash → message such that iterating
  M₀ → H₀ → M₁ = f(H₀) → H₁ → M₂ = f(H₁) → ...
creates a trajectory that cycles FASTER than random.

If random rho cycle: ~2^128 steps
If ★-guided rho: ~2^(128-k) steps for some k > 0

THREE ★-TRAPS:

Trap 1: ★-Deterministic
  f(H) uses H directly as message words → deterministic, simple
  (= standard rho, baseline)

Trap 2: ★-Carry-Aligned
  f(H) constructs M to minimize P-chains with IV
  → carry is maximally determined → less uncertainty per step
  → tighter trajectory → shorter cycle?

Trap 3: ★-Dual-Walk
  TWO walks: forward and backward. Forward: M→H→M'
  Backward: modify M to push H toward a TARGET.
  When walks MEET → collision.
"""
import sys, os, random, math, time, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def hash_to_message_standard(H):
    """Standard: use hash words directly + repeat."""
    return list(H) + list(H)

def hash_to_message_carry_aligned(H):
    """★-aligned: construct M to minimize P-chains with IV."""
    M = [0] * 16
    for w in range(8):
        # Set M[w] to agree with IV[w] at as many bits as possible
        # while incorporating H[w] information
        # Strategy: M[w] = IV[w] at positions where H[w] bit = 0
        #           M[w] = ~IV[w] at positions where H[w] bit = 1
        # This makes GKP maximally G/K when H has few 1s
        M[w] = (IV[w] & ~H[w]) | (~IV[w] & H[w]) & MASK
        M[w + 8] = H[w]  # Second half = raw hash
    return M

def hash_to_message_chain_min(H):
    """★-chain-minimizing: construct M to minimize P-chain lengths."""
    M = [0] * 16
    for w in range(8):
        # Alternate agreement/disagreement to create short P-chains
        # XOR with pattern that breaks up long P-runs
        pattern = 0x55555555  # Alternating bits → max short chains
        M[w] = H[w] ^ (pattern & IV[w])
        M[w + 8] = H[w] ^ ((pattern >> 1) & IV[w])
    return M

def rho_walk(f_map, budget, detect_cycle=True):
    """Pollard's rho walk with given hash→message mapping.
    Returns: cycle_length or min_distance found."""

    M_start = random_w16()
    H = sha256_compress(M_start)

    # Floyd's cycle detection
    tortoise = list(H)
    hare = list(H)

    min_dist = 256
    steps = 0

    for step in range(budget):
        # Tortoise: one step
        M_t = f_map(tortoise)
        tortoise = sha256_compress(M_t)

        # Hare: two steps
        M_h = f_map(hare)
        hare = sha256_compress(M_h)
        M_h2 = f_map(hare)
        hare = sha256_compress(M_h2)

        # Check for cycle
        d = sum(hw(tortoise[w] ^ hare[w]) for w in range(8))
        if d < min_dist:
            min_dist = d

        if d == 0 and detect_cycle:
            # Verify: are the MESSAGES different?
            M_t_check = f_map(tortoise)
            M_h_check = f_map(hare)
            if M_t_check != M_h_check:
                return step + 1, 0, True  # Real collision!
            # Same message → trivial cycle, continue

        steps = step + 1

    return steps, min_dist, False

def test_rho_comparison(N=15, budget=5000):
    """Compare three ★-traps against standard rho."""
    print(f"\n{'='*60}")
    print(f"★-TRAP COMPARISON (N={N}, budget={budget})")
    print(f"{'='*60}")

    traps = [
        ("Standard rho", hash_to_message_standard),
        ("★-Carry-Aligned", hash_to_message_carry_aligned),
        ("★-Chain-Min", hash_to_message_chain_min),
    ]

    for name, f_map in traps:
        min_dists = []; collisions = 0

        for trial in range(N):
            steps, min_d, found = rho_walk(f_map, budget)
            min_dists.append(min_d)
            if found:
                collisions += 1

        md = np.array(min_dists)
        print(f"\n  {name:>20}:")
        print(f"    Collisions: {collisions}/{N}")
        print(f"    Min dist avg: {md.mean():.1f}")
        print(f"    Min dist min: {md.min()}")

def test_carry_structure_of_walks(N=5, walk_length=1000):
    """Track ★-structure along rho walks. Does carry get more ordered?"""
    print(f"\n{'='*60}")
    print(f"★-STRUCTURE ALONG RHO WALKS")
    print(f"{'='*60}")

    for name, f_map in [
        ("Standard", hash_to_message_standard),
        ("★-Carry-Aligned", hash_to_message_carry_aligned),
    ]:
        print(f"\n  {name} walk:")

        nP_trajectory = []
        chain_ent_trajectory = []

        for trial in range(N):
            M = random_w16()
            nPs = []; ents = []

            for step in range(walk_length):
                H = sha256_compress(M)
                s = sha256_rounds(M, 64)[64]

                # Measure ★-structure
                total_nP = 0
                total_ent = 0
                for w in range(8):
                    gkp = carry_gkp_classification(IV[w], s[w])
                    total_nP += gkp.count('P')

                    # Chain entropy
                    chains = []
                    current = 0
                    for c in gkp:
                        if c == 'P': current += 1
                        else:
                            if current > 0: chains.append(current)
                            current = 0
                    if current > 0: chains.append(current)
                    total = sum(chains) if chains else 0
                    if total > 0:
                        probs = [s_val/total for s_val in chains]
                        total_ent -= sum(p*math.log2(p) for p in probs if p>0)

                nPs.append(total_nP)
                ents.append(total_ent)

                M = f_map(H)

            nP_trajectory.append(nPs)
            chain_ent_trajectory.append(ents)

        # Average trajectory
        avg_nP = np.mean(nP_trajectory, axis=0)
        avg_ent = np.mean(chain_ent_trajectory, axis=0)

        print(f"    Step     0: nP={avg_nP[0]:.1f}, chain_ent={avg_ent[0]:.2f}")
        print(f"    Step   100: nP={avg_nP[100]:.1f}, chain_ent={avg_ent[100]:.2f}")
        print(f"    Step   500: nP={avg_nP[500]:.1f}, chain_ent={avg_ent[500]:.2f}")
        print(f"    Step   999: nP={avg_nP[999]:.1f}, chain_ent={avg_ent[999]:.2f}")

        # Does carry structure CONVERGE?
        nP_std_early = np.std([t[0:100] for t in nP_trajectory])
        nP_std_late = np.std([t[900:1000] for t in nP_trajectory])
        print(f"    nP std early: {nP_std_early:.2f}")
        print(f"    nP std late:  {nP_std_late:.2f}")

        if nP_std_late < nP_std_early * 0.9:
            print(f"    ★★★ TRAJECTORY CONVERGES! (std decreases)")

def test_dual_walk_trap(N=15, budget=5000):
    """Two walks meeting in the middle."""
    print(f"\n{'='*60}")
    print(f"DUAL WALK TRAP (N={N})")
    print(f"{'='*60}")

    # Walk 1: M₁ → H₁ → M₁' → H₁' → ...
    # Walk 2: M₂ → H₂ → M₂' → H₂' → ...
    # Use DIFFERENT f_maps for the two walks
    # Check for collision BETWEEN walks at each step

    collisions = 0
    min_dists = []

    for trial in range(N):
        # Walk 1: standard
        M1 = random_w16()
        walk1_hashes = {}

        # Walk 2: ★-aligned
        M2 = random_w16()

        best = 256

        for step in range(budget):
            H1 = sha256_compress(M1)
            H2 = sha256_compress(M2)

            h1_key = tuple(H1)
            walk1_hashes[h1_key] = step

            # Check H2 against all walk1 hashes (sample)
            d = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            if d < best: best = d
            if d == 0 and M1 != M2:
                collisions += 1
                break

            # Check H2 against recent walk1
            for h_old in list(walk1_hashes.keys())[-20:]:
                dd = sum(hw(list(h_old)[w] ^ H2[w]) for w in range(8))
                if dd < best: best = dd

            # Advance walks with different maps
            M1 = hash_to_message_standard(H1)
            M2 = hash_to_message_carry_aligned(H2)

        min_dists.append(best)

    md = np.array(min_dists)
    print(f"\n  Dual walk: collisions={collisions}/{N}, "
          f"avg_min_dist={md.mean():.1f}, best={md.min()}")

    # Single walk comparison
    single_dists = []
    for trial in range(N):
        _, min_d, found = rho_walk(hash_to_message_standard, budget)
        single_dists.append(min_d)
        if found: collisions += 1  # Doesn't apply here

    sd = np.array(single_dists)
    print(f"  Single walk: avg_min_dist={sd.mean():.1f}, best={sd.min()}")

    gain = sd.mean() - md.mean()
    print(f"  Gain: {gain:+.1f} bits")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 162: COLLISION TRAP")
    print("Let the collision find US")
    print("=" * 60)

    test_rho_comparison(N=12, budget=3000)
    test_carry_structure_of_walks(N=3, walk_length=1000)
    test_dual_walk_trap(N=12, budget=3000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Collision Trap")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
