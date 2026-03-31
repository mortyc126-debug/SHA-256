#!/usr/bin/env python3
"""
EXP 100: Self-Reference Correlation — The 38.3% Signal

corr(δα, δC) = 0.383 AVERAGE. For near-collision → higher?

If corr → 1.0 for near-collision: the self-referential structure
TIGHTENS as we approach collision. This would mean:
collision pairs are at the point where self-reference = PERFECT.

Also: PER-BIT correlation. Which bits have highest δα↔δC correlation?
Those bits are where collision is "easiest" (self-reference strongest).

The 38.3% IS the new signal. From ★-algebra.
Not discovered in 98 prior experiments because we never decomposed
δH into δα and δC.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def decompose_dH(W0, W1, DW0=1):
    """Decompose δH into δα and δC components."""
    Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1, DW0)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

    delta_alpha = [sn[64][w] ^ sf[64][w] for w in range(8)]
    delta_C = [((IV[w]+sn[64][w])&MASK)^(IV[w]^sn[64][w]) ^
               ((IV[w]+sf[64][w])&MASK)^(IV[w]^sf[64][w]) for w in range(8)]
    delta_H = [Hn[w] ^ Hf[w] for w in range(8)]

    hw_da = sum(hw(delta_alpha[w]) for w in range(8))
    hw_dc = sum(hw(delta_C[w]) for w in range(8))
    hw_dh = sum(hw(delta_H[w]) for w in range(8))

    return delta_alpha, delta_C, delta_H, hw_da, hw_dc, hw_dh

def test_correlation_vs_dH(N=10000):
    """Does corr(δα, δC) INCREASE for near-collision pairs?"""
    print(f"\n--- corr(δα, δC) vs δH (N={N}) ---")

    data = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        da, dc, dh, hw_da, hw_dc, hw_dh = decompose_dH(W0, W1)

        # Per-bit correlation for this pair
        # Count matching bits between δα and δC
        match_bits = 0
        for w in range(8):
            match_bits += 32 - hw(da[w] ^ dc[w])  # bits where δα = δC

        data.append((hw_dh, hw_da, hw_dc, match_bits))

    dh_arr = np.array([d[0] for d in data])
    da_arr = np.array([d[1] for d in data])
    dc_arr = np.array([d[2] for d in data])
    match_arr = np.array([d[3] for d in data])

    # Overall correlation
    c_overall = np.corrcoef(da_arr, dc_arr)[0, 1]
    print(f"Overall corr(HW(δα), HW(δC)): {c_overall:+.6f}")

    # Bit-match rate
    match_rate = match_arr / 256
    print(f"Overall bit-match rate δα=δC: {match_rate.mean():.6f} (random=0.5)")

    # Correlation between match_rate and δH
    c_match_dh = np.corrcoef(match_arr, dh_arr)[0, 1]
    print(f"corr(match_rate, δH): {c_match_dh:+.6f}")

    if abs(c_match_dh) > 0.1:
        print(f"*** STRONG: higher match rate → lower δH! ***")

    # Binned by δH
    print(f"\ncorr(δα, δC) by δH bin:")
    print(f"{'δH range':>15} | {'N':>6} | {'match_rate':>10} | {'corr_HW':>8}")
    print("-" * 50)

    for lo, hi in [(90, 105), (105, 115), (115, 125), (125, 135), (135, 160)]:
        mask = (dh_arr >= lo) & (dh_arr < hi)
        n = mask.sum()
        if n < 20:
            continue
        mr = match_arr[mask].mean() / 256
        c = np.corrcoef(da_arr[mask], dc_arr[mask])[0, 1] if n > 30 else 0
        print(f"{'δH='+str(lo)+'-'+str(hi):>15} | {n:>6} | {mr:>10.6f} | {c:>+8.4f}")

def test_per_bit_self_reference(N=5000):
    """Which output BITS have strongest δα↔δC correlation?"""
    print(f"\n--- PER-BIT δα↔δC CORRELATION ---")

    # For each bit position: corr(δα_bit, δC_bit) across messages
    da_bits = np.zeros((N, 256), dtype=np.int64)
    dc_bits = np.zeros((N, 256), dtype=np.int64)
    dh_vals = np.zeros(N)

    for idx in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        da, dc, dh, _, _, hw_dh = decompose_dH(W0, W1)
        dh_vals[idx] = hw_dh

        for w in range(8):
            for b in range(32):
                da_bits[idx, w*32+b] = (da[w] >> b) & 1
                dc_bits[idx, w*32+b] = (dc[w] >> b) & 1

    # Per-bit correlation
    bit_corrs = []
    for i in range(256):
        c = np.corrcoef(da_bits[:, i], dc_bits[:, i])[0, 1]
        if np.isnan(c):
            c = 0
        bit_corrs.append(c)

    bc = np.array(bit_corrs)
    print(f"Per-bit corr(δα, δC):")
    print(f"  Mean: {bc.mean():.6f}")
    print(f"  Std: {bc.std():.6f}")
    print(f"  Min: {bc.min():.6f}")
    print(f"  Max: {bc.max():.6f}")

    # Top 15 bits with HIGHEST correlation
    top = np.argsort(-bc)[:15]
    print(f"\nTop 15 bits (strongest δα↔δC self-reference):")
    for idx in top:
        w = idx // 32; b = idx % 32
        branch = "a" if w < 4 else "e"
        print(f"  H[{w}]({branch}) bit {b:>2}: corr={bc[idx]:+.6f}")

    # Do these match transparency pattern (exp72)?
    print(f"\nCorrelation with transparency pattern:")
    transparency = [1.000, 0.635, 0.313, 0.536, 0.355, 0.520, 0.466, 0.486,
                    0.542, 0.719, 0.652, 0.381, 0.633, 0.514, 0.692, 0.379,
                    0.423, 0.400, 0.479, 0.282, 0.469, 0.596, 0.422, 0.571,
                    0.394, 0.342, 0.401, 0.267, 0.482, 0.627, 0.587, 0.455]

    # Compare bit 0-31 of first e-branch word (w=4)
    self_ref_w4 = bc[4*32:5*32]
    c_with_T = np.corrcoef(self_ref_w4, transparency)[0, 1]
    print(f"  corr(self_ref_pattern, transparency_pattern) = {c_with_T:+.6f}")

def test_match_rate_predicts_collision(N=10000):
    """Can δα=δC match rate be used as collision predictor?"""
    print(f"\n--- MATCH RATE AS PREDICTOR ---")

    matches = []; dHs = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        da, dc, _, _, _, hw_dh = decompose_dH(W0, W1)

        match = sum(32 - hw(da[w] ^ dc[w]) for w in range(8))
        matches.append(match)
        dHs.append(hw_dh)

    ma = np.array(matches); da = np.array(dHs)
    c = np.corrcoef(ma, da)[0, 1]

    print(f"corr(δα=δC match count, δH) = {c:+.6f}")

    # This is the DIRECT predictor: more δα=δC matching → lower δH
    # Top 1% by match count
    top1_thresh = np.percentile(ma, 99)
    top1 = da[ma >= top1_thresh]
    bottom1 = da[ma <= np.percentile(ma, 1)]

    print(f"\nTop 1% match count (≥{top1_thresh:.0f}/256):")
    print(f"  E[δH] = {top1.mean():.2f}, min = {top1.min()}")
    print(f"Bottom 1% match count:")
    print(f"  E[δH] = {bottom1.mean():.2f}, min = {bottom1.min()}")
    print(f"Average: E[δH] = {da.mean():.2f}")

    # Collision = match = 256/256. How close do we get?
    print(f"\nMax match count: {ma.max()}/256")
    print(f"At max match: δH = {da[np.argmax(ma)]}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 100: SELF-REFERENCE CORRELATION")
    print("The 38.3% signal from ★-algebra")
    print("=" * 60)

    test_correlation_vs_dH(8000)
    test_per_bit_self_reference(4000)
    test_match_rate_predicts_collision(8000)

    print("\n" + "=" * 60)
    print("100th EXPERIMENT!")
    print("=" * 60)

if __name__ == "__main__":
    main()
