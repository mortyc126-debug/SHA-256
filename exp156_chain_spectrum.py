#!/usr/bin/env python3
"""
EXP 156: P-CHAIN SPECTRUM — True Nonlinear Structure

d_★ = d_H (trivial). But P-chain ARRANGEMENT ≠ Hamming weight.
Same HW, different chain lengths → different carry → different nonlinearity.

NEW OBJECT: ★-Chain Spectrum
  Λ(a,b) = sorted list of P-chain lengths in GKP(a,b)

Example: HW(a⊕b) = 16
  Λ₁ = [16]        → one long cascade (hard)
  Λ₂ = [1,1,...,1]  → 16 short cascades (easy)
  Same HW, DIFFERENT Λ → DIFFERENT carry behavior

TEST:
  1. Does chain spectrum predict hash distance better than HW?
  2. Do near-collisions have specific chain spectra?
  3. Can chain spectrum survive through rounds?
  4. Can we BUILD message pairs with favorable spectra?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def chain_spectrum(a, b):
    """Sorted P-chain lengths in GKP(a,b)."""
    gkp = carry_gkp_classification(a, b)
    chains = []
    current = 0
    for c in gkp:
        if c == 'P':
            current += 1
        else:
            if current > 0:
                chains.append(current)
            current = 0
    if current > 0:
        chains.append(current)
    return sorted(chains, reverse=True)

def spectrum_features(a, b):
    """Extract features from chain spectrum."""
    spec = chain_spectrum(a, b)
    if not spec:
        return 0, 0, 0, 0

    max_chain = spec[0]
    n_chains = len(spec)
    total = sum(spec)  # = HW = nP
    # Entropy of chain length distribution
    probs = [s / total for s in spec] if total > 0 else [1]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    return max_chain, n_chains, total, entropy

def state_spectrum_features(s1, s2):
    """Aggregate spectrum features across all 8 state words."""
    total_max = 0
    total_chains = 0
    total_entropy = 0

    for w in range(8):
        mc, nc, _, ent = spectrum_features(s1[w], s2[w])
        total_max = max(total_max, mc)
        total_chains += nc
        total_entropy += ent

    return total_max, total_chains, total_entropy

def test_spectrum_vs_hash(N=5000):
    """Does chain spectrum predict hash distance?"""
    print(f"\n{'='*60}")
    print(f"CHAIN SPECTRUM vs HASH DISTANCE (N={N})")
    print(f"{'='*60}")

    max_chains = []; n_chains_all = []; entropies = []; hws = []; dHs = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64)[64]
        s2 = sha256_rounds(M2, 64)[64]
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)

        mc, nc, hw_total, ent = 0, 0, 0, 0
        for w in range(8):
            m, n, t, e = spectrum_features(s1[w], s2[w])
            mc = max(mc, m); nc += n; hw_total += t; ent += e

        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        max_chains.append(mc)
        n_chains_all.append(nc)
        entropies.append(ent)
        hws.append(hw_total)
        dHs.append(dH)

    mc_arr = np.array(max_chains); nc_arr = np.array(n_chains_all)
    ent_arr = np.array(entropies); hw_arr = np.array(hws)
    dH_arr = np.array(dHs)

    print(f"\n  Correlations with hash distance dH:")
    print(f"    corr(HW, dH):         {np.corrcoef(hw_arr, dH_arr)[0,1]:+.6f}  [= d_H, baseline]")
    print(f"    corr(max_chain, dH):  {np.corrcoef(mc_arr, dH_arr)[0,1]:+.6f}  [longest P-chain]")
    print(f"    corr(n_chains, dH):   {np.corrcoef(nc_arr, dH_arr)[0,1]:+.6f}  [number of chains]")
    print(f"    corr(entropy, dH):    {np.corrcoef(ent_arr, dH_arr)[0,1]:+.6f}  [chain entropy]")

    # Combined: can spectrum features TOGETHER predict dH better than HW alone?
    X = np.column_stack([hw_arr, mc_arr, nc_arr, ent_arr])
    try:
        coeffs = np.linalg.lstsq(X, dH_arr, rcond=None)[0]
        pred = X @ coeffs
        combined_corr = np.corrcoef(pred, dH_arr)[0, 1]
        print(f"\n    COMBINED correlation: {combined_corr:+.6f}")
        print(f"    Coefficients: HW={coeffs[0]:.3f}, max={coeffs[1]:.3f}, "
              f"n={coeffs[2]:.3f}, ent={coeffs[3]:.3f}")

        if combined_corr > np.corrcoef(hw_arr, dH_arr)[0,1] + 0.01:
            print(f"    ★★★ SPECTRUM PREDICTS BETTER THAN HW ALONE!")
            gain = combined_corr - np.corrcoef(hw_arr, dH_arr)[0,1]
            print(f"    Gain: +{gain:.4f} correlation")
    except:
        pass

def test_near_collision_spectrum(N=3000):
    """Do near-collisions have specific chain spectra?"""
    print(f"\n{'='*60}")
    print(f"NEAR-COLLISION CHAIN SPECTRA (N×100)")
    print(f"{'='*60}")

    near_mc = []; near_nc = []; near_ent = []
    rand_mc = []; rand_nc = []; rand_ent = []

    for _ in range(N * 50):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64)[64]; s2 = sha256_rounds(M2, 64)[64]
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        mc, nc, ent = state_spectrum_features(s1, s2)

        if dH < 108:
            near_mc.append(mc); near_nc.append(nc); near_ent.append(ent)
        elif random.random() < 0.02:
            rand_mc.append(mc); rand_nc.append(nc); rand_ent.append(ent)

    if len(near_mc) < 10:
        print(f"  Not enough near-collisions ({len(near_mc)})")
        return

    print(f"\n  Near-collisions: {len(near_mc)}, Random: {len(rand_mc)}")

    for name, near, rand_vals in [
        ("max_chain", near_mc, rand_mc),
        ("n_chains", near_nc, rand_nc),
        ("entropy", near_ent, rand_ent),
    ]:
        na = np.array(near); ra = np.array(rand_vals)
        diff = na.mean() - ra.mean()
        pooled = math.sqrt((na.std()**2 + ra.std()**2) / 2)
        n = min(len(na), len(ra))
        z = diff / (pooled / math.sqrt(n)) if pooled > 0 else 0
        sig = "★★★" if abs(z) > 5 else ("★★" if abs(z) > 3 else "")
        print(f"    {name:>12}: near={na.mean():.2f} rand={ra.mean():.2f} "
              f"diff={diff:+.2f} Z={z:+.1f} {sig}")

def test_spectrum_through_rounds(N=300):
    """Does chain spectrum survive through rounds?"""
    print(f"\n{'='*60}")
    print(f"CHAIN SPECTRUM THROUGH ROUNDS")
    print(f"{'='*60}")

    print(f"\n  1-bit diff, chain spectrum features per round:")
    print(f"  {'Round':>6} | {'max_chain':>9} | {'n_chains':>8} | {'entropy':>8} | {'d_H':>6}")
    print(f"  " + "-" * 50)

    for R in [0, 1, 2, 3, 4, 5, 6, 8, 12, 16, 20, 32, 64]:
        mcs = []; ncs = []; ents = []; dhs = []

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, R)[R]; s2 = sha256_rounds(M2, R)[R]
            mc, nc, ent = state_spectrum_features(s1, s2)
            dh = sum(hw(s1[w] ^ s2[w]) for w in range(8))

            mcs.append(mc); ncs.append(nc); ents.append(ent); dhs.append(dh)

        avg_mc = np.mean(mcs); avg_nc = np.mean(ncs)
        avg_ent = np.mean(ents); avg_dh = np.mean(dhs)
        print(f"  {R:>6} | {avg_mc:>9.2f} | {avg_nc:>8.2f} | {avg_ent:>8.3f} | {avg_dh:>6.1f}")

def test_controlled_spectrum(N=20, budget=3000):
    """Can we BUILD message pairs with favorable chain spectra?"""
    print(f"\n{'='*60}")
    print(f"CONTROLLED SPECTRUM WEAPON (N={N}, budget={budget})")
    print(f"{'='*60}")

    # Strategy: generate pairs where P-chains are SHORT (scattered diffs)
    # Short chains → predictable carry → better for collision

    spec_results = []; rand_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)

        # Spectrum weapon: choose M2 with scattered differences
        best_dH = 256
        for _ in range(budget):
            M2 = list(M1)
            # Create scattered difference: flip random bits spread across words
            n_flips = random.randint(3, 12)
            for _ in range(n_flips):
                w = random.randint(0, 15)
                # Flip bits that are SPREAD OUT (not consecutive)
                b = random.randint(0, 31)
                M2[w] ^= (1 << b)

            if M1 == M2: continue
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            best_dH = min(best_dH, dH)

        spec_results.append(best_dH)

        # Random baseline
        best_rand = 256
        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            best_rand = min(best_rand, dH)

        rand_results.append(best_rand)

    sa = np.array(spec_results); ra = np.array(rand_results)
    gain = ra.mean() - sa.mean()

    print(f"\n  Spectrum weapon: avg={sa.mean():.1f}, min={sa.min()}")
    print(f"  Random:          avg={ra.mean():.1f}, min={ra.min()}")
    print(f"  Gain: {gain:+.1f} bits")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 156: P-CHAIN SPECTRUM")
    print("True nonlinear structure: not HOW MANY, but HOW ARRANGED")
    print("=" * 60)

    test_spectrum_vs_hash(3000)
    test_near_collision_spectrum(2000)
    test_spectrum_through_rounds(200)
    test_controlled_spectrum(N=15, budget=2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Chain Spectrum")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
