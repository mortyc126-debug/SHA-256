#!/usr/bin/env python3
"""
EXP 155: ★-NONLINEAR DISTANCE — Carry Complexity as Native Metric

Linear tools (SVD, rank) fail because SHA-256 is nonlinear.
The nonlinearity IS carry. Carry is a SCANNING automaton.

NEW OBJECT: ★-nonlinear distance
  d_★(a,b) = total P-chain length in GKP(a,b)
  = how COMPLEX is the carry interaction between a and b

This is NOT Hamming distance. It measures CARRY COMPLEXITY.

TEST: Does d_★ correlate with collision difficulty better than d_H?
      Does d_★ survive through rounds (unlike linear invariants)?
      Can d_★ be used to PREDICT or GUIDE collision search?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def p_chain_lengths(a, b):
    """Compute P-chain lengths in GKP(a,b).
    Returns list of chain lengths."""
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
    return chains

def star_nonlinear_distance(a, b):
    """★-nonlinear distance: total P-chain length."""
    chains = p_chain_lengths(a, b)
    return sum(chains)

def star_max_chain(a, b):
    """Maximum P-chain length."""
    chains = p_chain_lengths(a, b)
    return max(chains) if chains else 0

def star_carry_complexity(s1, s2):
    """★-carry complexity of a state pair: sum of d_★ across all words."""
    total = 0
    max_chain = 0
    for w in range(8):
        d = star_nonlinear_distance(s1[w], s2[w])
        mc = star_max_chain(s1[w], s2[w])
        total += d
        max_chain = max(max_chain, mc)
    return total, max_chain

def test_nonlinear_vs_hamming(N=3000):
    """Compare ★-nonlinear distance with Hamming distance."""
    print(f"\n{'='*60}")
    print(f"★-NONLINEAR DISTANCE vs HAMMING")
    print(f"{'='*60}")

    # For random pairs: correlation between d_★ and d_H
    d_nl = []; d_ham = []; dH_hash = []

    for _ in range(N):
        M1 = random_w16(); M2 = random_w16()
        s1 = sha256_rounds(M1, 64)[64]
        s2 = sha256_rounds(M2, 64)[64]
        H1 = sha256_compress(M1); H2 = sha256_compress(M2)

        # State distances
        nl, mc = star_carry_complexity(s1, s2)
        ham = sum(hw(s1[w] ^ s2[w]) for w in range(8))

        # Hash distance
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        d_nl.append(nl)
        d_ham.append(ham)
        dH_hash.append(dH)

    nl_arr = np.array(d_nl); ham_arr = np.array(d_ham); dH_arr = np.array(dH_hash)

    print(f"\n  Statistics:")
    print(f"    E[d_★]:  {nl_arr.mean():.1f} ± {nl_arr.std():.1f}")
    print(f"    E[d_H]:  {ham_arr.mean():.1f} ± {ham_arr.std():.1f}")
    print(f"    E[dH_hash]: {dH_arr.mean():.1f}")

    print(f"\n  Correlations:")
    corr_nl_hash = np.corrcoef(nl_arr, dH_arr)[0, 1]
    corr_ham_hash = np.corrcoef(ham_arr, dH_arr)[0, 1]
    corr_nl_ham = np.corrcoef(nl_arr, ham_arr)[0, 1]

    print(f"    corr(d_★, dH_hash):   {corr_nl_hash:+.6f}")
    print(f"    corr(d_H, dH_hash):   {corr_ham_hash:+.6f}")
    print(f"    corr(d_★, d_H):       {corr_nl_ham:+.6f}")

    if abs(corr_nl_hash) > abs(corr_ham_hash):
        print(f"\n  ★★★ d_★ PREDICTS HASH BETTER THAN HAMMING!")
    else:
        print(f"\n  Hamming predicts hash better (or both equal)")

    # Binned: among low d_★ pairs, is dH lower?
    p10_nl = np.percentile(nl_arr, 10)
    p10_ham = np.percentile(ham_arr, 10)

    low_nl = dH_arr[nl_arr <= p10_nl].mean()
    low_ham = dH_arr[ham_arr <= p10_ham].mean()
    overall = dH_arr.mean()

    print(f"\n  Low d_★ (P10): E[dH] = {low_nl:.1f}")
    print(f"  Low d_H (P10): E[dH] = {low_ham:.1f}")
    print(f"  Overall:       E[dH] = {overall:.1f}")

def test_nonlinear_through_rounds(N=500):
    """Does d_★ survive through rounds better than d_H?"""
    print(f"\n{'='*60}")
    print(f"d_★ SURVIVAL THROUGH ROUNDS")
    print(f"{'='*60}")

    # For 1-bit difference: track d_★ and d_H per round
    print(f"\n  1-bit diff in M[0], tracking d_★ and d_H per round:")
    print(f"  {'Round':>6} | {'d_★':>8} | {'d_H':>8} | {'max_chain':>9} | {'d_★/d_H':>7}")
    print(f"  " + "-" * 50)

    for R in [0, 1, 2, 3, 4, 5, 6, 8, 10, 16, 20, 32, 64]:
        nls = []; hams = []; mcs = []

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[0] ^= (1 << random.randint(0, 31))

            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]

            nl, mc = star_carry_complexity(s1, s2)
            ham = sum(hw(s1[w] ^ s2[w]) for w in range(8))

            nls.append(nl)
            hams.append(ham)
            mcs.append(mc)

        avg_nl = np.mean(nls); avg_ham = np.mean(hams); avg_mc = np.mean(mcs)
        ratio = avg_nl / max(avg_ham, 0.01)

        print(f"  {R:>6} | {avg_nl:>8.1f} | {avg_ham:>8.1f} | {avg_mc:>9.1f} | {ratio:>7.3f}")

def test_carry_of_carry(N=300):
    """CARRY-OF-CARRY: second-order nonlinear effect.
    Does carry from round r affect carry at round r+1?"""
    print(f"\n{'='*60}")
    print(f"CARRY-OF-CARRY: SECOND-ORDER NONLINEARITY")
    print(f"{'='*60}")

    # Track carry CORRELATION between consecutive rounds
    # For a message pair: carry(state_r) vs carry(state_{r+1})

    carry_corrs = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[0] = (M2[0] + 1) & MASK

        s1 = sha256_rounds(M1, 64)
        s2 = sha256_rounds(M2, 64)

        for r in range(1, 20):
            # Carry complexity at round r and r+1
            nl_r, _ = star_carry_complexity(s1[r], s2[r])
            nl_r1, _ = star_carry_complexity(s1[r+1], s2[r+1])
            carry_corrs.append((r, nl_r, nl_r1))

    # Correlation per round
    print(f"\n  Carry complexity correlation between consecutive rounds:")
    for r_target in [1, 2, 3, 4, 5, 8, 12, 16]:
        pairs = [(nl_r, nl_r1) for r, nl_r, nl_r1 in carry_corrs if r == r_target]
        if len(pairs) < 10: continue
        a, b = zip(*pairs)
        corr = np.corrcoef(a, b)[0, 1]
        print(f"    Round {r_target}→{r_target+1}: corr(d_★[r], d_★[r+1]) = {corr:+.4f}")

def test_nonlinear_predictor(N=5000):
    """Can d_★ at intermediate rounds predict final hash distance?"""
    print(f"\n{'='*60}")
    print(f"d_★ AS HASH PREDICTOR AT INTERMEDIATE ROUNDS")
    print(f"{'='*60}")

    # For each round R: compute d_★(state_R), compare with dH(hash)
    for R in [4, 8, 16, 32, 63, 64]:
        nls = []; dHs = []
        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            s1 = sha256_rounds(M1, R)[R]
            s2 = sha256_rounds(M2, R)[R]
            nl, _ = star_carry_complexity(s1, s2)
            nls.append(nl)

            H1 = sha256_compress(M1); H2 = sha256_compress(M2)
            dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            dHs.append(dH)

        corr = np.corrcoef(nls, dHs)[0, 1]
        sig = "★★★" if abs(corr) > 0.05 else ""
        print(f"  Round {R:>2}: corr(d_★, dH_hash) = {corr:+.6f} {sig}")

    # COMPARISON: d_H at same rounds
    print(f"\n  Comparison with d_H at same rounds:")
    for R in [4, 8, 16, 32, 63, 64]:
        hams = []; dHs = []
        for _ in range(N):
            M1 = random_w16(); M2 = random_w16()
            s1 = sha256_rounds(M1, R)[R]; s2 = sha256_rounds(M2, R)[R]
            ham = sum(hw(s1[w] ^ s2[w]) for w in range(8))
            hams.append(ham)
            H1 = sha256_compress(M1); H2 = sha256_compress(M2)
            dHs.append(sum(hw(H1[w] ^ H2[w]) for w in range(8)))

        corr = np.corrcoef(hams, dHs)[0, 1]
        print(f"  Round {R:>2}: corr(d_H, dH_hash) = {corr:+.6f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 155: ★-NONLINEAR DISTANCE")
    print("Carry complexity as native nonlinear metric")
    print("=" * 60)

    test_nonlinear_vs_hamming(2000)
    test_nonlinear_through_rounds(300)
    test_carry_of_carry(200)
    test_nonlinear_predictor(2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★-Nonlinear Distance")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
