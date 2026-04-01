#!/usr/bin/env python3
"""
EXP 196: VECTOR-LEVEL SHIFT REGISTER COUPLING

exp195 FAILED because we used HW (scalar). Shift register
preserves BITS, not HW. The coupling exists at BIT level!

δd = δa[r-3] EXACTLY (bit-for-bit).
δe_new = δ(d+T1) → at BIT 0: δe_new[0] = δd[0] ⊕ δT1[0] (carry-free!)

TEST: Per-bit correlation corr(δa[r][b], δe[r+3][b]).
At bit 0: should be significant (carry-free coupling).
At higher bits: carry may or may not preserve coupling.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def collect_bit_traces(N=300, max_r=64):
    """Collect full bit-level traces of δa and δe."""
    da_bits = []  # [sample][round][bit]
    de_bits = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        s1 = sha256_rounds(M1, max_r)
        s2 = sha256_rounds(M2, max_r)

        da_r = []
        de_r = []
        for r in range(max_r + 1):
            da_vec = [(s1[r][0] >> b) & 1 ^ (s2[r][0] >> b) & 1 for b in range(32)]
            de_vec = [(s1[r][4] >> b) & 1 ^ (s2[r][4] >> b) & 1 for b in range(32)]
            da_r.append(da_vec)
            de_r.append(de_vec)

        da_bits.append(da_r)
        de_bits.append(de_r)

    return da_bits, de_bits

def test_per_bit_coupling(da_bits, de_bits):
    """Per-bit: corr(δa[r][b], δe[r+3][b])."""
    print(f"\n{'='*60}")
    print(f"PER-BIT SHIFT REGISTER COUPLING")
    print(f"corr(δa[r][b], δe[r+3][b]) for each bit b")
    print(f"{'='*60}")

    N = len(da_bits)

    # For each bit: collect (δa[r][b], δe[r+3][b]) pairs
    bit_corrs_lag3 = []

    for b in range(32):
        x_vals = []; y_vals = []
        for sample in range(N):
            for r in range(30, 60):
                x_vals.append(da_bits[sample][r][b])
                y_vals.append(de_bits[sample][r+3][b])

        x = np.array(x_vals, dtype=float)
        y = np.array(y_vals, dtype=float)

        if x.std() > 0 and y.std() > 0:
            c = np.corrcoef(x, y)[0, 1]
        else:
            c = 0

        bit_corrs_lag3.append(c)

    # Display
    print(f"\n  {'Bit':>4} | {'corr(δa→δe lag3)':>16} | {'Signal'}")
    print(f"  " + "-" * 35)

    for b in range(32):
        c = bit_corrs_lag3[b]
        sig = " ★★★" if abs(c) > 0.05 else (" ★★" if abs(c) > 0.03 else "")
        note = ""
        if b == 0: note = " ← CARRY-FREE"
        if b == 1: note = " ← blind spot"
        print(f"  {b:>4} | {c:>+16.6f} | {sig}{note}")

    avg = np.mean(np.abs(bit_corrs_lag3))
    threshold = 3 / math.sqrt(N * 30)
    n_sig = sum(1 for c in bit_corrs_lag3 if abs(c) > threshold)

    print(f"\n  Average |corr|: {avg:.6f}")
    print(f"  Threshold (3σ): {threshold:.6f}")
    print(f"  Significant bits: {n_sig}/32")

    if n_sig > 3:
        print(f"  ★★★ {n_sig} BITS have significant shift-register coupling!")

    return bit_corrs_lag3

def test_all_lags(da_bits, de_bits):
    """Same but for multiple lags: 1, 2, 3, 4, 5."""
    print(f"\n{'='*60}")
    print(f"ALL LAGS: Per-bit δa[r] → δe[r+k] coupling")
    print(f"{'='*60}")

    N = len(da_bits)

    for lag in [1, 2, 3, 4, 5]:
        bit_corrs = []
        for b in range(32):
            x_vals = []; y_vals = []
            for sample in range(N):
                for r in range(30, 64 - lag):
                    x_vals.append(da_bits[sample][r][b])
                    y_vals.append(de_bits[sample][r+lag][b])
            x = np.array(x_vals, dtype=float)
            y = np.array(y_vals, dtype=float)
            c = np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else 0
            bit_corrs.append(c)

        avg = np.mean(np.abs(bit_corrs))
        max_c = max(bit_corrs, key=abs)
        max_b = bit_corrs.index(max_c)
        sig = " ★★★" if abs(max_c) > 0.05 else ""

        print(f"  Lag {lag}: avg|corr|={avg:.6f}, max={max_c:+.6f} at bit {max_b}{sig}")

    # Also: δa[r] → δa[r+k] (self-coupling)
    print(f"\n  SELF-COUPLING: δa[r][b] → δa[r+k][b]:")
    for lag in [1, 2, 3, 4]:
        bit_corrs = []
        for b in range(32):
            x_vals = []; y_vals = []
            for sample in range(N):
                for r in range(30, 64 - lag):
                    x_vals.append(da_bits[sample][r][b])
                    y_vals.append(da_bits[sample][r+lag][b])
            x = np.array(x_vals, dtype=float)
            y = np.array(y_vals, dtype=float)
            c = np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else 0
            bit_corrs.append(c)

        avg = np.mean(np.abs(bit_corrs))
        max_c = max(bit_corrs, key=abs)
        max_b = bit_corrs.index(max_c)
        sig = " ★★★" if abs(max_c) > 0.05 else ""
        print(f"  Lag {lag}: avg|corr|={avg:.6f}, max={max_c:+.6f} at bit {max_b}{sig}")

def test_cross_bit_coupling(da_bits, de_bits):
    """Does δa[r][b1] predict δe[r+3][b2] for b1≠b2? (rotation coupling)"""
    print(f"\n{'='*60}")
    print(f"CROSS-BIT COUPLING: δa[r][b] → δe[r+3][b+rot]")
    print(f"{'='*60}")

    N = len(da_bits)
    lag = 3

    # For each rotation distance: average corr across bits
    for rot in [0, 2, 6, 11, 13, 17, 18, 19, 22, 25]:
        corrs = []
        for b in range(32):
            b2 = (b + rot) % 32
            x_vals = []; y_vals = []
            for sample in range(N):
                for r in range(30, 61):
                    x_vals.append(da_bits[sample][r][b])
                    y_vals.append(de_bits[sample][r+lag][b2])
            x = np.array(x_vals, dtype=float)
            y = np.array(y_vals, dtype=float)
            c = np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else 0
            corrs.append(c)

        avg = np.mean(corrs)
        avg_abs = np.mean(np.abs(corrs))
        sig = " ★★★" if avg_abs > 0.02 else ""
        label = ""
        if rot in [2,13,22]: label = f"(Σ₀)"
        elif rot in [6,11,25]: label = f"(Σ₁)"
        elif rot in [17,19]: label = f"(σ₁)"
        elif rot == 18: label = f"(σ₀)"

        print(f"  rot={rot:>2} {label:>5}: avg_corr={avg:+.6f}, avg|corr|={avg_abs:.6f}{sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 196: VECTOR-LEVEL SHIFT REGISTER COUPLING")
    print("=" * 60)

    print("  Collecting bit-level traces...")
    da_bits, de_bits = collect_bit_traces(N=250, max_r=64)
    print(f"  {len(da_bits)} traces collected")

    corrs = test_per_bit_coupling(da_bits, de_bits)
    test_all_lags(da_bits, de_bits)
    test_cross_bit_coupling(da_bits, de_bits)

    print(f"\n{'='*60}")
    print(f"VERDICT: Does bit-level coupling exist?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
