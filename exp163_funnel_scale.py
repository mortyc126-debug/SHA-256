#!/usr/bin/env python3
"""
EXP 163: ★-FUNNEL SCALING + ALL KNOWLEDGE

nP dropped 135→118 over 1000 steps. Scale to 10K-50K steps.
Does nP → 0? (= collision!)

ALSO: Use ALL findings from 162 experiments to IMPROVE the funnel:
  - Thin-tree bits (exp160): modify thin bits → less disturbance
  - Ring transition blind spots (exp161): bit 1 = 65% absorbed
  - Chain spectrum (exp156): low entropy = closer to collision
  - Kill chain (exp146): +27 bits at 4 rounds
  - ★⁻¹ Jacobian (exp127): exact for δ=±1
  - Schedule weak words (exp110): W[13] weakest diffusion

BUILD: Ultimate ★-funnel combining ALL knowledge.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_aligned_map(H):
    """★-Carry-Aligned: construct M to agree with IV."""
    M = [0] * 16
    for w in range(8):
        M[w] = (IV[w] & ~H[w]) | (~IV[w] & H[w]) & MASK
        M[w + 8] = H[w]
    return M

def ultimate_funnel_map(H):
    """ULTIMATE ★-FUNNEL: combines all 162 experiments of knowledge.

    Uses:
    - Carry alignment with IV (exp159: reduce nP)
    - Bit 0 = carry-free, bit 1 = blind spot (exp161)
    - Thin-tree positions (exp160)
    - Schedule-weak words W[13] (exp110)
    - Chain-breaking pattern (exp156: low entropy = good)
    """
    M = [0] * 16

    for w in range(8):
        # Core: agree with IV to minimize P-chains
        base = IV[w]

        # Inject hash info through BLIND SPOTS (bit 1: 65% absorbed)
        # and CARRY-FREE positions (bit 0: 0% absorbed)
        # Strategy: put H info at blind positions → absorbed → less disturbance
        # Put structural info at clear positions → survives → guides trajectory

        # Bits where IV[w] has 1: set M to 1 (→ G, carry determined)
        # Bits where IV[w] has 0: set M to 0 (→ K, carry determined)
        # EXCEPT: inject H at positions 1,2,22 (blind spots)
        blind_mask = (1 << 1) | (1 << 2) | (1 << 22) | (1 << 19) | (1 << 30)
        clear_mask = (1 << 0) | (1 << 5) | (1 << 10) | (1 << 23) | (1 << 28)

        # Base: agree with IV (all G/K)
        M[w] = base
        # Inject H at blind spots (these get absorbed by carry → less effect)
        M[w] = (M[w] & ~blind_mask) | (H[w] & blind_mask)
        # Keep clear spots from IV (these survive → structural)
        M[w] = (M[w] & ~clear_mask) | (base & clear_mask)

    # Second half: use schedule-weak positions
    # W[13] has weakest diffusion (exp110: 507 vs avg 567)
    for w in range(8, 16):
        if w == 13:
            # W[13]: weakest → put most hash info here (least diffusion)
            M[w] = H[w - 8]
        else:
            # Other words: mix of IV-agreement and H-injection
            M[w] = H[w - 8] ^ IV[w - 8]

    return M

def long_walk(f_map, steps, name=""):
    """Walk for many steps, track nP and min_dist."""
    M = random_w16()
    nP_history = []
    chain_ent_history = []

    for step in range(steps):
        H = sha256_compress(M)
        s = sha256_rounds(M, 64)[64]

        # Measure nP
        total_nP = 0
        total_ent = 0
        for w in range(8):
            gkp = carry_gkp_classification(IV[w], s[w])
            total_nP += gkp.count('P')
            # Chain entropy
            chains = []; current = 0
            for c in gkp:
                if c == 'P': current += 1
                else:
                    if current > 0: chains.append(current)
                    current = 0
            if current > 0: chains.append(current)
            total = sum(chains) if chains else 0
            if total > 0:
                probs = [s_val/total for s_val in chains]
                total_ent -= sum(p*math.log2(p) for p in probs if p > 0)

        nP_history.append(total_nP)
        chain_ent_history.append(total_ent)

        M = f_map(H)

    return nP_history, chain_ent_history

def test_long_funnel(N=3):
    """Scale ★-funnel to long walks."""
    print(f"\n{'='*60}")
    print(f"★-FUNNEL LONG WALK (N={N})")
    print(f"{'='*60}")

    walk_lengths = [10000]

    for steps in walk_lengths:
        for name, f_map in [
            ("Standard", lambda H: list(H) + list(H)),
            ("★-Carry-Aligned", carry_aligned_map),
            ("★-ULTIMATE", ultimate_funnel_map),
        ]:
            all_nP = []
            all_ent = []

            t0 = time.time()
            for trial in range(N):
                nPs, ents = long_walk(f_map, steps, name)
                all_nP.append(nPs)
                all_ent.append(ents)
            t1 = time.time()

            avg_nP = np.mean(all_nP, axis=0)
            avg_ent = np.mean(all_ent, axis=0)

            print(f"\n  {name} ({steps} steps, {t1-t0:.1f}s):")
            for s in [0, 100, 500, 1000, 2000, 5000, 9999]:
                if s < steps:
                    print(f"    Step {s:>5}: nP={avg_nP[s]:.1f}, "
                          f"chain_ent={avg_ent[s]:.2f}")

            # Trend: is nP decreasing?
            nP_first_1000 = avg_nP[:1000].mean()
            nP_last_1000 = avg_nP[-1000:].mean()
            trend = nP_last_1000 - nP_first_1000

            print(f"    nP trend: {nP_first_1000:.1f} → {nP_last_1000:.1f} "
                  f"({trend:+.1f})")

            if trend < -2:
                print(f"    ★★★ nP DECREASING! Funnel WORKS!")
                # Extrapolate: when would nP reach 0?
                rate = -trend / (steps - 1000)  # nP decrease per step
                if rate > 0:
                    steps_to_zero = nP_last_1000 / rate
                    print(f"    Rate: {rate:.4f} nP/step")
                    print(f"    Extrapolated nP=0 at: {steps_to_zero:.0f} steps")
                    print(f"    = 2^{math.log2(steps_to_zero):.1f}")
            elif trend > 2:
                print(f"    nP INCREASING (anti-funnel)")
            else:
                print(f"    nP FLAT (no funnel effect at this scale)")

def test_dual_funnel(N=5, steps=5000):
    """Two ★-funnels meeting → collision."""
    print(f"\n{'='*60}")
    print(f"DUAL ★-FUNNEL ({steps} steps, N={N})")
    print(f"{'='*60}")

    for trial in range(N):
        M1 = random_w16()
        M2 = random_w16()

        min_dist = 256
        min_step = -1

        for step in range(steps):
            H1 = sha256_compress(M1)
            H2 = sha256_compress(M2)

            d = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            if d < min_dist:
                min_dist = d
                min_step = step

            if d == 0 and M1 != M2:
                print(f"  Trial {trial}: ★★★ COLLISION at step {step}!")
                break

            # Walk 1: standard
            M1 = list(H1) + list(H1)
            # Walk 2: ultimate funnel
            M2 = ultimate_funnel_map(H2)

        if trial < 5:
            print(f"  Trial {trial}: best dH={min_dist} at step {min_step}")

def test_multi_funnel(N=5, steps=5000, n_walks=10):
    """N parallel walks with different ★-mappings → birthday among them."""
    print(f"\n{'='*60}")
    print(f"MULTI-FUNNEL: {n_walks} parallel walks ({steps} steps)")
    print(f"{'='*60}")

    for trial in range(N):
        walks = []
        for w_idx in range(n_walks):
            M = random_w16()
            walks.append(M)

        # Different f-maps for different walks
        f_maps = [
            lambda H: list(H) + list(H),
            carry_aligned_map,
            ultimate_funnel_map,
            lambda H: [H[w % 8] ^ IV[w % 8] for w in range(16)],
            lambda H: [H[w % 8] for w in range(16)],
            lambda H: [(H[w % 8] + IV[w % 8]) & MASK for w in range(16)],
            lambda H: [H[w % 8] ^ (H[(w+1) % 8]) for w in range(16)],
            lambda H: [(H[w % 8] >> 1) | (H[w % 8] << 31) & MASK for w in range(16)],
            lambda H: [H[7-w % 8] for w in range(16)],
            lambda H: [H[w % 8] ^ 0x5A5A5A5A for w in range(16)],
        ]

        min_dist = 256
        hashes_seen = {}

        for step in range(steps):
            # Advance all walks
            step_hashes = []
            for w_idx in range(n_walks):
                H = sha256_compress(walks[w_idx])
                step_hashes.append(H)

                # Check against ALL other walks' current hashes
                hk = tuple(H)
                if hk in hashes_seen:
                    old_idx = hashes_seen[hk]
                    if old_idx != w_idx:
                        print(f"  Trial {trial}: COLLISION between walk {old_idx} and {w_idx} at step {step}!")

                # Check against recent
                for h_old_key in list(hashes_seen.keys())[-30:]:
                    dd = sum(hw(H[ww] ^ list(h_old_key)[ww]) for ww in range(8))
                    if dd < min_dist: min_dist = dd

                hashes_seen[hk] = w_idx
                walks[w_idx] = f_maps[w_idx % len(f_maps)](H)

        print(f"  Trial {trial}: best dH = {min_dist}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 163: ★-FUNNEL SCALING + ALL KNOWLEDGE")
    print("=" * 60)

    test_long_funnel(N=2)
    test_dual_funnel(N=4, steps=3000)
    test_multi_funnel(N=3, steps=2000, n_walks=8)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
