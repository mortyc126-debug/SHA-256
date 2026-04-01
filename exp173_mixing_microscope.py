#!/usr/bin/env python3
"""
EXP 173: MIXING MICROSCOPE — What happens at rounds 21+?

We know: by round 20, avalanche = 0.498 (full mixing).
But HOW does the mixing look at the particle/sub-bit level?

Track rounds 15→30 in EXTREME detail:
- Particle births/deaths per round
- Sub-bit flavor transitions
- Carry organism ecology (species diversity)
- Information flow: which primordial bits still visible?
- The EXACT moment where structure dies
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def particle_census(s1, s2):
    """Count particles and organisms for a state pair."""
    total_G = 0; total_K = 0; total_P = 0
    organisms = []  # List of carry organism lifetimes

    for w in range(8):
        gkp = carry_gkp_classification(s1[w], s2[w])
        total_G += gkp.count('G')
        total_K += gkp.count('K')
        total_P += gkp.count('P')

        # Count organisms (carry chains)
        current_life = 0
        for c in gkp:
            if c == 'P':
                current_life += 1  # Carry could flow here
            elif c == 'G':
                current_life += 1  # Carry born/sustained
            else:  # K
                if current_life > 0:
                    organisms.append(current_life)
                current_life = 0
        if current_life > 0:
            organisms.append(current_life)

    return total_G, total_K, total_P, organisms

def sub_bit_census(s, ref_state):
    """Count sub-bit types relative to reference state."""
    counts = {'0_K': 0, '0_P': 0, '1_P': 0, '1_G': 0}
    for w in range(8):
        for b in range(32):
            s_bit = (s[w] >> b) & 1
            ref_bit = (ref_state[w] >> b) & 1
            h_bit = ((s[w] + ref_state[w]) & MASK >> b) & 1

            if s_bit == 0 and ref_bit == 0:
                counts['0_K'] += 1
            elif s_bit == 1 and ref_bit == 1:
                counts['1_G'] += 1
            elif h_bit == 0:
                counts['0_P'] += 1
            else:
                counts['1_P'] += 1
    return counts

def trace_primordial_visibility(M_base, bit_idx, max_round=40):
    """Track ONE primordial bit: is it still VISIBLE at each round?

    Flip the primordial bit → does the state change at round r?
    If yes → primordial is visible. If no → primordial is hidden."""

    w_msg = bit_idx // 32
    b_msg = bit_idx % 32

    M_flip = list(M_base)
    M_flip[w_msg] ^= (1 << b_msg)

    s_base = sha256_rounds(M_base, max_round)
    s_flip = sha256_rounds(M_flip, max_round)

    visibility = []
    for r in range(max_round + 1):
        # How many state bits changed?
        changed = sum(hw(s_base[r][w] ^ s_flip[r][w]) for w in range(8))
        visibility.append(changed)

    return visibility

def mixing_microscope(N=150):
    """Detailed view of mixing at rounds 15-35."""
    print(f"\n{'='*70}")
    print(f"MIXING MICROSCOPE: Rounds 15→35 (N={N})")
    print(f"{'='*70}")

    # For a 1-bit message difference: track EVERYTHING per round

    print(f"\n  {'Rnd':>3} | {'dH':>4} | {'G':>4} {'K':>4} {'P':>4} | {'#Org':>4} {'MaxL':>4} {'AvgL':>5} | {'Entropy':>7} | {'Phase'}")
    print(f"  " + "-" * 75)

    for R in range(0, 40):
        dHs = []; nGs = []; nKs = []; nPs = []
        n_orgs = []; max_lifes = []; avg_lifes = []; entropies = []

        for _ in range(N):
            M1 = random_w16()
            M2 = list(M1)
            M2[0] ^= (1 << 15)  # Best single-bit diff (exp137)

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            dH = sum(hw(s1[w] ^ s2[w]) for w in range(8))
            dHs.append(dH)

            nG, nK, nP, orgs = particle_census(s1, s2)
            nGs.append(nG); nKs.append(nK); nPs.append(nP)

            n_orgs.append(len(orgs))
            max_lifes.append(max(orgs) if orgs else 0)
            avg_lifes.append(np.mean(orgs) if orgs else 0)

            # Chain entropy
            total = sum(orgs) if orgs else 0
            if total > 0 and len(orgs) > 0:
                probs = [o/total for o in orgs]
                ent = -sum(p*math.log2(p) for p in probs if p > 0)
            else:
                ent = 0
            entropies.append(ent)

        avg_dH = np.mean(dHs)
        avg_G = np.mean(nGs); avg_K = np.mean(nKs); avg_P = np.mean(nPs)
        avg_org = np.mean(n_orgs); avg_maxL = np.mean(max_lifes)
        avg_avgL = np.mean(avg_lifes); avg_ent = np.mean(entropies)

        # Phase determination
        if avg_dH < 5:
            phase = "FROZEN"
        elif avg_dH < 50:
            phase = "MELTING"
        elif avg_dH < 120:
            phase = "MIXING"
        elif avg_dH < 132:
            phase = "CHAOS"
        else:
            phase = "EQUILIBRIUM"

        print(f"  {R:>3} | {avg_dH:>4.0f} | {avg_G:>4.0f} {avg_K:>4.0f} {avg_P:>4.0f} | "
              f"{avg_org:>4.0f} {avg_maxL:>4.1f} {avg_avgL:>5.2f} | {avg_ent:>7.3f} | {phase}")

def transition_detail(N=200):
    """ZOOM into the critical transition rounds 18-25."""
    print(f"\n{'='*70}")
    print(f"ZOOM: Critical transition rounds 18-25")
    print(f"{'='*70}")

    print(f"\n  What CHANGES between round 20 (mixing) and round 25 (chaos)?")
    print(f"\n  {'Rnd':>3} | {'dH':>5} | {'dH_std':>6} | {'P(dH>120)':>10} | {'G/K ratio':>9} | {'OrgDiv':>6}")
    print(f"  " + "-" * 55)

    for R in range(18, 30):
        dHs = []; gk_ratios = []; org_diversities = []

        for _ in range(N):
            M1 = random_w16()
            M2 = list(M1)
            M2[0] ^= (1 << 15)

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            dH = sum(hw(s1[w] ^ s2[w]) for w in range(8))
            dHs.append(dH)

            nG, nK, nP, orgs = particle_census(s1, s2)
            gk_ratio = (nG + nK) / max(nP, 1)
            gk_ratios.append(gk_ratio)

            # Organism diversity
            if orgs:
                unique_lengths = len(set(orgs))
                org_diversities.append(unique_lengths / max(len(orgs), 1))
            else:
                org_diversities.append(0)

        da = np.array(dHs)
        p_high = np.mean(da > 120)

        print(f"  {R:>3} | {da.mean():>5.1f} | {da.std():>6.2f} | {p_high:>10.3f} | "
              f"{np.mean(gk_ratios):>9.4f} | {np.mean(org_diversities):>6.3f}")

def primordial_fade(N=100):
    """Track when primordial message bits FADE from visibility."""
    print(f"\n{'='*70}")
    print(f"PRIMORDIAL BIT FADEOUT")
    print(f"{'='*70}")

    # For selected message bits: when does their influence become ~128 (random)?
    bits_to_track = [
        (0, 15, "M[0]b15 (best schedule)"),
        (0, 0, "M[0]b0 (first bit)"),
        (7, 16, "M[7]b16 (middle)"),
        (15, 31, "M[15]b31 (last word, MSB)"),
    ]

    print(f"\n  {'Bit':>25} | ", end="")
    for r in range(0, 35, 2):
        print(f" r{r:>2}", end="")
    print()
    print(f"  " + "-" * (28 + 4 * 18))

    for w, b, name in bits_to_track:
        print(f"  {name:>25} | ", end="")

        avg_vis = []
        for r in range(0, 35, 2):
            visibilities = []
            for _ in range(N):
                M = random_w16()
                v = trace_primordial_visibility(M, w*32+b, r)
                visibilities.append(v[r] if r < len(v) else 128)
            avg = np.mean(visibilities)
            avg_vis.append(avg)

            # Compact display
            if avg < 1:
                print(f"   .", end="")
            elif avg < 10:
                print(f"  {avg:.0f}", end="")
            elif avg < 100:
                print(f" {avg:.0f}", end="")
            else:
                print(f" {avg:.0f}", end="")
        print()

    print(f"\n  Legend: . = invisible (dH<1), number = bits affected, 128 = random")

def round21_ecology(N=300):
    """Detailed ecology of carry organisms at round 21+."""
    print(f"\n{'='*70}")
    print(f"CARRY ECOLOGY AT ROUNDS 21+ (N={N})")
    print(f"{'='*70}")

    for R in [15, 20, 21, 25, 30, 64]:
        all_orgs = []

        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            _, _, _, orgs = particle_census(s1, s2)
            all_orgs.extend(orgs)

        if not all_orgs:
            continue

        oa = np.array(all_orgs)

        # Organism length distribution
        hist = {}
        for o in all_orgs:
            hist[o] = hist.get(o, 0) + 1

        total = len(all_orgs)
        print(f"\n  Round {R}: {total} organisms across {N} pairs")
        print(f"    Avg length: {oa.mean():.2f}, Max: {oa.max()}, Std: {oa.std():.2f}")
        print(f"    Length distribution:")
        for length in sorted(hist.keys())[:12]:
            count = hist[length]
            pct = count / total * 100
            bar = "█" * min(int(pct), 40)
            print(f"      L={length:>2}: {pct:>5.1f}% {bar}")

def main():
    random.seed(42)
    print("=" * 70)
    print("EXP 173: MIXING MICROSCOPE — Rounds 21+")
    print("=" * 70)

    mixing_microscope(N=100)
    transition_detail(N=150)
    primordial_fade(N=60)
    round21_ecology(N=200)

    print(f"\n{'='*70}")
    print(f"VERDICT: What happens during mixing?")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
