#!/usr/bin/env python3
"""
EXP 193: DERIVATIVE FINGERPRINTS — Rotation INTERACTIONS

dist=14 = 25-11 (Σ₁ difference). NOT a SHA-256 rotation.
But ranked #3 in correlation strength!

CRITICAL QUESTION: Is σ₁(19) really from schedule?
  Or is it 25-6 = 19 (Σ₁ difference)?
  If so: we've been MISATTRIBUTING fingerprints!

Map ALL derivative distances: i-j mod 32 and i+j mod 32
for all rotation pairs. Are they elevated?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def get_diff_vector(s1, s2):
    vec = np.zeros(64, dtype=int)
    for b in range(32):
        vec[b] = ((s1[0] >> b) & 1) ^ ((s2[0] >> b) & 1)
        vec[32+b] = ((s1[4] >> b) & 1) ^ ((s2[4] >> b) & 1)
    return vec

def compute_all_derivatives():
    """Compute all pairwise sums and differences of SHA-256 rotations."""
    print(f"\n{'='*60}")
    print(f"ALL DERIVATIVE DISTANCES")
    print(f"{'='*60}")

    rotations = {
        'Σ₀': [2, 13, 22],
        'Σ₁': [6, 11, 25],
        'σ₀': [3, 7, 18],
        'σ₁': [10, 17, 19],
    }
    all_rots = [2, 3, 6, 7, 10, 11, 13, 17, 18, 19, 22, 25]

    # All pairwise differences mod 32
    derivative_dists = {}  # dist → list of (r1, r2, source1, source2)

    for s1_name, s1_rots in rotations.items():
        for s2_name, s2_rots in rotations.items():
            for r1 in s1_rots:
                for r2 in s2_rots:
                    if r1 == r2: continue
                    diff = (r1 - r2) % 32
                    summ = (r1 + r2) % 32

                    for d, op in [(diff, '-'), (summ, '+')]:
                        if d not in derivative_dists:
                            derivative_dists[d] = []
                        derivative_dists[d].append(f"{s1_name}({r1}){op}{s2_name}({r2})")

    # Show which distances are PRIMARY (rotation), DERIVATIVE, or NEITHER
    print(f"\n  {'Dist':>4} | {'Type':>10} | {'Sources'}")
    print(f"  " + "-" * 60)

    for d in range(32):
        is_primary = d in all_rots
        is_derivative = d in derivative_dists
        n_sources = len(derivative_dists.get(d, []))

        if is_primary and is_derivative:
            dtype = "BOTH"
        elif is_primary:
            dtype = "PRIMARY"
        elif is_derivative:
            dtype = "DERIVATIVE"
        else:
            dtype = "none"

        sources = derivative_dists.get(d, [])[:3]
        source_str = ", ".join(sources) if sources else "-"

        if dtype != "none":
            print(f"  {d:>4} | {dtype:>10} | {source_str}")

    # KEY: dist=19 — is it σ₁(19) or Σ₁(25)-Σ₁(6)?
    print(f"\n  CRITICAL: dist=19 sources:")
    for s in derivative_dists.get(19, []):
        print(f"    {s}")

    print(f"\n  CRITICAL: dist=14 sources:")
    for s in derivative_dists.get(14, []):
        print(f"    {s}")

    return derivative_dists

def measure_all_correlations(N=400):
    """Measure correlation at every distance, classify by type."""
    print(f"\n{'='*60}")
    print(f"CORRELATION BY TYPE: PRIMARY vs DERIVATIVE vs NONE")
    print(f"{'='*60}")

    X_all = []; Y_all = []
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(30, 63):
            X_all.append(get_diff_vector(s1[r], s2[r]))
            Y_all.append(get_diff_vector(s1[r+1], s2[r+1]))

    X = np.array(X_all, dtype=float); Y = np.array(Y_all, dtype=float)

    all_rots = [2, 3, 6, 7, 10, 11, 13, 17, 18, 19, 22, 25]
    derivatives = compute_all_derivatives()

    dist_corrs = {}
    for dist in range(32):
        corrs = []
        for b in range(32):
            b2 = (b + dist) % 32
            # a-word
            c = np.corrcoef(X[:, b], Y[:, b2])[0, 1]
            if not np.isnan(c): corrs.append(abs(c))
            # e-word
            c = np.corrcoef(X[:, 32+b], Y[:, 32+b2])[0, 1]
            if not np.isnan(c): corrs.append(abs(c))
        dist_corrs[dist] = np.mean(corrs) if corrs else 0

    # Classify
    primary_vals = []
    derivative_only_vals = []
    both_vals = []
    none_vals = []

    for d in range(32):
        is_primary = d in all_rots
        is_derivative = d in derivatives and len(derivatives[d]) > 0
        c = dist_corrs[d]

        if is_primary and is_derivative:
            both_vals.append(c)
        elif is_primary:
            primary_vals.append(c)
        elif is_derivative:
            derivative_only_vals.append(c)
        else:
            none_vals.append(c)

    print(f"\n  Correlation by distance TYPE:")
    print(f"    PRIMARY only (rot, no derivative):  avg = {np.mean(primary_vals):.6f} (n={len(primary_vals)})")
    print(f"    BOTH (rot AND derivative):          avg = {np.mean(both_vals):.6f} (n={len(both_vals)})")
    print(f"    DERIVATIVE only (not a rotation):   avg = {np.mean(derivative_only_vals):.6f} (n={len(derivative_only_vals)})")
    print(f"    NONE (neither rot nor derivative):  avg = {np.mean(none_vals):.6f} (n={len(none_vals)})")

    # Test: BOTH > PRIMARY?
    if both_vals and primary_vals:
        diff = np.mean(both_vals) - np.mean(primary_vals)
        print(f"\n    BOTH - PRIMARY = {diff:+.6f}")
        if diff > 0:
            print(f"    ★ Distances that are BOTH rotation AND derivative are STRONGER!")
            print(f"    → Derivatives REINFORCE primary rotations!")

    # Test: DERIVATIVE > NONE?
    if derivative_only_vals and none_vals:
        diff = np.mean(derivative_only_vals) - np.mean(none_vals)
        print(f"\n    DERIVATIVE - NONE = {diff:+.6f}")
        if diff > 0:
            print(f"    ★ Pure derivatives are stronger than non-rotation distances!")

    # OVERLAP: which distances are BOTH primary rotation AND derivative?
    print(f"\n  OVERLAP — Distances that are BOTH rotation AND derivative:")
    for d in range(32):
        if d in all_rots and d in derivatives and len(derivatives[d]) > 0:
            sources = derivatives[d][:4]
            print(f"    dist={d:>2} (SHA-256 rotation): also = {', '.join(sources)}")

    # THE DEEP QUESTION: is dist=19 from σ₁ or from Σ₁(25)-Σ₁(6)?
    print(f"\n  THE DEEP QUESTION:")
    print(f"    dist=19: correlation = {dist_corrs[19]:.6f}")
    print(f"    Is this from σ₁(19) or from Σ₁(25)-Σ₁(6)?")
    print(f"    Both are distance 19. We CANNOT distinguish!")
    print(f"    The fingerprint exists — its SOURCE is ambiguous.")

def test_second_order_derivatives(N=300):
    """Are there SECOND-ORDER derivatives? (rot₁-rot₂)-(rot₃-rot₄)?"""
    print(f"\n{'='*60}")
    print(f"SECOND-ORDER DERIVATIVES")
    print(f"{'='*60}")

    all_rots = [2, 3, 6, 7, 10, 11, 13, 17, 18, 19, 22, 25]

    # First-order derivatives (already computed)
    first_order = set()
    for r1 in all_rots:
        for r2 in all_rots:
            if r1 != r2:
                first_order.add((r1 - r2) % 32)
                first_order.add((r1 + r2) % 32)

    # Second-order: differences of first-order
    second_order = set()
    first_list = list(first_order)
    for d1 in first_list:
        for d2 in first_list:
            second_order.add((d1 - d2) % 32)
            second_order.add((d1 + d2) % 32)

    # Which distances are NOT covered even at second order?
    uncovered = set(range(32)) - first_order - second_order - set(all_rots)

    print(f"\n  Primary rotations: {len(all_rots)}/32 distances")
    print(f"  First-order derivatives: {len(first_order)}/32")
    print(f"  Second-order derivatives: {len(second_order)}/32")
    print(f"  UNCOVERED: {len(uncovered)}/32 = {uncovered if uncovered else 'NONE'}")

    if not uncovered:
        print(f"\n  ★★★ ALL 32 distances are covered by 2nd-order derivatives!")
        print(f"  Every fingerprint can be EXPLAINED by rotation interactions.")
        print(f"  No distance is truly 'non-architectural'.")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 193: DERIVATIVE FINGERPRINTS")
    print("=" * 60)

    derivatives = compute_all_derivatives()
    measure_all_correlations(N=300)
    test_second_order_derivatives()

    print(f"\n{'='*60}")
    print(f"VERDICT: Level 8 complete")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
