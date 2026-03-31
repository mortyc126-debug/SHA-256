#!/usr/bin/env python3
"""
EXP 158: CARRY MONOID + ★-THERMODYNAMICS

Two parallel tracks from ★-mathematics:

TRACK A: Carry Monoid M₃ = {G, K, P}
  - Carry = product in M₃
  - P-chains = transparent windows
  - Monoid composition → carry propagation
  - What happens when we compose M₃ across ROUNDS?

TRACK B: ★-Entropy flow
  - Entropy oscillates after round 4 (exp157)
  - Can we find messages where entropy DECREASES systematically?
  - ★-free energy: F = E - T·S (energy vs entropy tradeoff)

UNIFIED: Carry-entropy = entropy of the M₃ sequence.
  The M₃ sequence at each round determines EVERYTHING about carry.
  Its entropy determines collision difficulty.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# TRACK A: CARRY MONOID
# ============================================================

def gkp_sequence(a, b):
    """Convert (a,b) pair to M₃ sequence: list of 'G', 'K', 'P'."""
    return carry_gkp_classification(a, b)

def monoid_product(seq):
    """Compute carry by M₃ product from right to left.
    Returns carry at each position."""
    carries = []
    c = 0  # Initial carry = 0
    for trit in seq:
        if trit == 'G':
            c = 1
        elif trit == 'K':
            c = 0
        # P: c unchanged
        carries.append(c)
    return carries

def monoid_entropy(seq):
    """Entropy of the M₃ sequence itself (not P-chains)."""
    counts = {'G': 0, 'K': 0, 'P': 0}
    for s in seq:
        counts[s] += 1
    n = len(seq)
    ent = 0
    for c in counts.values():
        if c > 0:
            p = c / n
            ent -= p * math.log2(p)
    return ent

def monoid_cross_round(s1_r, s2_r, s1_r1, s2_r1):
    """How does M₃ sequence at round r relate to round r+1?
    Returns correlation between M₃ sequences."""
    # M₃ at round r: GKP of state diff
    # M₃ at round r+1: GKP of next state diff
    gkp_r = []
    gkp_r1 = []
    for w in range(8):
        gkp_r.extend(gkp_sequence(s1_r[w], s2_r[w]))
        gkp_r1.extend(gkp_sequence(s1_r1[w], s2_r1[w]))

    # Convert to numeric: G=2, P=1, K=0
    num_r = [{'G': 2, 'P': 1, 'K': 0}[g] for g in gkp_r]
    num_r1 = [{'G': 2, 'P': 1, 'K': 0}[g] for g in gkp_r1]

    if len(num_r) == len(num_r1):
        return np.corrcoef(num_r, num_r1)[0, 1]
    return 0

def test_monoid_composition(N=300):
    """Track M₃ composition across rounds."""
    print(f"\n{'='*60}")
    print(f"CARRY MONOID M₃ ACROSS ROUNDS")
    print(f"{'='*60}")

    # For a message pair: how does the M₃ sequence evolve?
    print(f"\n  M₃ statistics per round (1-bit diff, N={N}):")
    print(f"  {'Round':>6} | {'nG':>5} | {'nK':>5} | {'nP':>5} | {'M₃-ent':>7} | {'GK-ratio':>8}")
    print(f"  " + "-" * 50)

    for R in range(0, 21):
        nGs = []; nKs = []; nPs = []; m3_ents = []

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            total_G = 0; total_K = 0; total_P = 0
            all_gkp = []
            for w in range(8):
                gkp = gkp_sequence(s1[w], s2[w])
                all_gkp.extend(gkp)
                total_G += gkp.count('G')
                total_K += gkp.count('K')
                total_P += gkp.count('P')

            nGs.append(total_G); nKs.append(total_K); nPs.append(total_P)
            m3_ents.append(monoid_entropy(all_gkp))

        avg_G = np.mean(nGs); avg_K = np.mean(nKs); avg_P = np.mean(nPs)
        avg_ent = np.mean(m3_ents)
        gk_ratio = (avg_G + avg_K) / max(avg_P, 0.01)

        print(f"  {R:>6} | {avg_G:>5.1f} | {avg_K:>5.1f} | {avg_P:>5.1f} | "
              f"{avg_ent:>7.4f} | {gk_ratio:>8.3f}")

    # Cross-round M₃ correlation
    print(f"\n  M₃ cross-round correlation:")
    for r in [1, 2, 3, 4, 5, 8, 12, 16]:
        corrs = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, r+1)
            s2 = sha256_rounds(M2, r+1)

            c = monoid_cross_round(s1[r], s2[r], s1[r+1], s2[r+1])
            if not np.isnan(c):
                corrs.append(c)

        avg_corr = np.mean(corrs) if corrs else 0
        print(f"    Round {r}→{r+1}: M₃ corr = {avg_corr:+.4f}")

# ============================================================
# TRACK B: ★-FREE ENERGY
# ============================================================

def star_free_energy(s1, s2):
    """★-free energy: F = E - T·S
    E = "energy" = hash distance (want low)
    S = chain entropy (high = disordered)
    T = temperature parameter

    Low F = low energy AND/OR high entropy
    Collision: E=0, S=0, F=0
    Random: E=128, S=22.3, F=128-T·22.3
    """
    # Energy = number of differing bits
    E = sum(hw(s1[w] ^ s2[w]) for w in range(8))

    # Entropy of chain spectrum
    S = 0
    for w in range(8):
        spec = []
        gkp = carry_gkp_classification(s1[w], s2[w])
        current = 0
        for c in gkp:
            if c == 'P':
                current += 1
            else:
                if current > 0:
                    spec.append(current)
                current = 0
        if current > 0:
            spec.append(current)

        total = sum(spec) if spec else 0
        if total > 0:
            probs = [s / total for s in spec]
            S -= sum(p * math.log2(p) for p in probs if p > 0)

    return E, S

def test_free_energy_landscape(N=3000):
    """Map the ★-free energy landscape."""
    print(f"\n{'='*60}")
    print(f"★-FREE ENERGY LANDSCAPE")
    print(f"{'='*60}")

    energies = []; entropies = []; dHs = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64)[64]
        s2 = sha256_rounds(M2, 64)[64]
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)

        E, S = star_free_energy(s1, s2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        energies.append(E); entropies.append(S); dHs.append(dH)

    E_arr = np.array(energies); S_arr = np.array(entropies); dH_arr = np.array(dHs)

    # Optimal temperature: minimize correlation of F with dH
    best_T = 0; best_corr = 0
    for T in np.arange(0, 20, 0.5):
        F = E_arr - T * S_arr
        c = np.corrcoef(F, dH_arr)[0, 1]
        if abs(c) > abs(best_corr):
            best_corr = c; best_T = T

    print(f"\n  Optimal temperature: T* = {best_T:.1f}")
    print(f"  corr(F*, dH): {best_corr:+.6f}")
    print(f"  vs corr(E, dH): {np.corrcoef(E_arr, dH_arr)[0,1]:+.6f}")
    print(f"  vs corr(S, dH): {np.corrcoef(S_arr, dH_arr)[0,1]:+.6f}")

    # Free energy of near-collisions
    print(f"\n  Near-collision free energy (T={best_T:.1f}):")
    F_star = E_arr - best_T * S_arr
    near_mask = dH_arr < 108
    rand_mask = dH_arr >= 120

    if np.sum(near_mask) > 5:
        print(f"    Near-coll E: {E_arr[near_mask].mean():.1f}")
        print(f"    Near-coll S: {S_arr[near_mask].mean():.2f}")
        print(f"    Near-coll F: {F_star[near_mask].mean():.1f}")
        print(f"    Random    E: {E_arr[rand_mask].mean():.1f}")
        print(f"    Random    S: {S_arr[rand_mask].mean():.2f}")
        print(f"    Random    F: {F_star[rand_mask].mean():.1f}")

# ============================================================
# UNIFIED: Monoid entropy flow = thermodynamic arrow
# ============================================================

def test_monoid_entropy_arrow(N=300):
    """Does M₃ entropy have a thermodynamic arrow?"""
    print(f"\n{'='*60}")
    print(f"M₃ ENTROPY ARROW (THERMODYNAMIC)")
    print(f"{'='*60}")

    # Track M₃ entropy (not P-chain entropy) through rounds
    print(f"\n  M₃ entropy per round:")
    print(f"  {'Round':>6} | {'M₃-ent':>7} | {'ΔM₃-ent':>9} | {'Direction'}")
    print(f"  " + "-" * 45)

    prev = None
    for R in range(0, 21):
        ents = []
        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            all_gkp = []
            for w in range(8):
                all_gkp.extend(gkp_sequence(s1[w], s2[w]))
            ents.append(monoid_entropy(all_gkp))

        avg = np.mean(ents)
        delta = avg - prev if prev is not None else 0
        direction = "→" if abs(delta) < 0.005 else ("↑" if delta > 0 else "↓")

        print(f"  {R:>6} | {avg:>7.4f} | {delta:>+9.5f} | {direction}")
        prev = avg

    # Maximum possible M₃ entropy = log₂(3) = 1.585 (uniform G,K,P)
    print(f"\n  Maximum M₃ entropy: log₂(3) = {math.log2(3):.4f}")
    print(f"  At equilibrium: nG=nK=8, nP=16 → entropy = ?")

    # Compute equilibrium entropy
    probs = {'G': 8/32, 'K': 8/32, 'P': 16/32}
    eq_ent = -sum(p * math.log2(p) for p in probs.values() if p > 0)
    print(f"  Equilibrium M₃ entropy: {eq_ent:.4f}")

    # Compare with η
    eta = (3 * math.log2(3)) / 4 - 1
    print(f"\n  η = {eta:.6f}")
    print(f"  M₃ entropy at equilibrium = {eq_ent:.6f}")
    print(f"  log₂(3) = {math.log2(3):.6f}")
    print(f"  Ratio: M₃_ent / log₂(3) = {eq_ent / math.log2(3):.6f}")
    print(f"  η / (log₂(3) - 1) = {eta / (math.log2(3) - 1):.6f}")

def test_entropy_flow_as_weapon(N=20, budget=3000):
    """Use ★-free energy to guide collision search."""
    print(f"\n{'='*60}")
    print(f"★-FREE ENERGY WEAPON (N={N})")
    print(f"{'='*60}")

    fe_results = []; rand_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)
        s1 = sha256_rounds(M1, 64)[64]

        # Free energy weapon: select pairs with lowest F
        best_dH = 256
        for _ in range(budget):
            M2 = random_w16()
            s2 = sha256_rounds(M2, 64)[64]
            E, S = star_free_energy(s1, s2)
            F = E - 5.0 * S  # Use T=5.0

            # Only compare hashes for low-F candidates
            if F < E - 50:  # F significantly below E → good entropy structure
                H2 = sha256_compress(M2)
                dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
                best_dH = min(best_dH, dH)
            else:
                # Still compute hash occasionally for budget fairness
                if random.random() < 0.3:
                    H2 = sha256_compress(M2)
                    dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
                    best_dH = min(best_dH, dH)

        fe_results.append(best_dH)

        # Random baseline
        best_rand = 256
        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            best_rand = min(best_rand, dH)
        rand_results.append(best_rand)

    fa = np.array(fe_results); ra = np.array(rand_results)
    gain = ra.mean() - fa.mean()
    print(f"\n  Free energy weapon: avg={fa.mean():.1f}, min={fa.min()}")
    print(f"  Random:             avg={ra.mean():.1f}, min={ra.min()}")
    print(f"  Gain: {gain:+.1f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 158: CARRY MONOID + ★-THERMODYNAMICS")
    print("=" * 60)

    test_monoid_composition(200)
    test_monoid_entropy_arrow(200)
    test_free_energy_landscape(2000)
    test_entropy_flow_as_weapon(N=12, budget=2000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
