#!/usr/bin/env python3
"""
EXP 85: Per-Message Fourier Period — Does It Vary?

From exp84: birthday = 3 × 4 × fourier × η ≈ 128.
If fourier varies per message → birthday varies per message.
If some messages have fourier < 57 → birthday < 128 for those.

fourier = Fourier peak of per-message transparency T(bit).
T(bit) is BINARY per message (0 or 1 for each bit×word).

Measure: fourier period for EACH Wang pair.
Distribution: mean, std, min.
If min << 57 → those messages have lower collision cost.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

ETA = (3*math.log(3) - 4*math.log(2)) / (4*math.log(2))

def per_message_fourier(Wn, Wf):
    """Compute Fourier period of transparency for one pair."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

    # Per-bit transparency (averaged over e-branch words 4-7)
    T = np.zeros(32)
    for w in range(4, 8):
        for bit in range(32):
            sx = (sn[64][w] ^ sf[64][w] >> bit) & 1
            hx = (Hn[w] ^ Hf[w] >> bit) & 1
            if sx == hx:
                T[bit] += 0.25  # Average over 4 words

    # FFT
    T_centered = T - T.mean()
    fft = np.fft.fft(T_centered)
    power = np.abs(fft) ** 2

    # Peak frequency (exclude DC)
    peak_freq = np.argmax(power[1:16]) + 1
    period = 32.0 / peak_freq

    # Also: total power and spectral entropy
    power_norm = power[1:16] / (power[1:16].sum() + 1e-30)
    spectral_entropy = -np.sum(power_norm * np.log2(power_norm + 1e-30))

    return period, peak_freq, spectral_entropy, T

def test_fourier_distribution(N=3000):
    """Distribution of per-message Fourier period."""
    print(f"\n--- PER-MESSAGE FOURIER PERIOD (N={N}) ---")

    periods = []; freqs = []; entropies = []; dHs = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, _, _ = wang_cascade(W0, W1)

        period, freq, entropy, T = per_message_fourier(Wn, Wf)
        periods.append(period)
        freqs.append(freq)
        entropies.append(entropy)

        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        dHs.append(sum(hw(Hn[i] ^ Hf[i]) for i in range(8)))

    pa = np.array(periods); fa = np.array(freqs)
    ea = np.array(entropies); da = np.array(dHs)

    print(f"Fourier period: mean={pa.mean():.2f}, std={pa.std():.2f}, "
          f"min={pa.min():.1f}, max={pa.max():.1f}")
    print(f"Peak frequency: mean={fa.mean():.2f}, mode={np.bincount(fa.astype(int)).argmax()}")
    print(f"Spectral entropy: mean={ea.mean():.2f}")

    # Frequency distribution
    print(f"\nPeak frequency distribution:")
    freq_counts = np.bincount(fa.astype(int), minlength=17)
    for f in range(1, 17):
        if freq_counts[f] > 0:
            period = 32.0 / f
            fourier_eta = period / ETA
            birthday_formula = 3 * 4 * fourier_eta * ETA
            pct = freq_counts[f] / N * 100
            print(f"  freq={f:>2} (period={period:>5.1f}, fourier={fourier_eta:>5.1f}η): "
                  f"{freq_counts[f]:>5} ({pct:>5.1f}%) → birthday≈{birthday_formula:.0f}")

    # Correlation: period → δH?
    threshold = 3 / np.sqrt(N)
    c = np.corrcoef(pa, da)[0, 1]
    print(f"\ncorr(fourier_period, δH) = {c:+.6f} {'***' if abs(c)>threshold else ''}")

    # Messages with LOWEST period → lowest birthday
    low_period = da[pa < np.percentile(pa, 10)]
    high_period = da[pa > np.percentile(pa, 90)]
    print(f"\nLow period (bottom 10%): E[δH]={low_period.mean():.2f}")
    print(f"High period (top 10%):   E[δH]={high_period.mean():.2f}")

    return pa, da

def test_formula_per_message(N=2000):
    """Test: birthday_message = 3×4×fourier_message×η for each message."""
    print(f"\n--- FORMULA PER MESSAGE ---")

    predictions = []; actuals = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, _, _ = wang_cascade(W0, W1)

        period, freq, _, _ = per_message_fourier(Wn, Wf)
        fourier_eta = period / ETA

        # Predicted birthday for this message
        predicted_birthday = 3 * 4 * fourier_eta * ETA
        predictions.append(predicted_birthday)

        # Actual δH (proxy for collision difficulty)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        dH = sum(hw(Hn[i] ^ Hf[i]) for i in range(8))
        actuals.append(dH)

    pa = np.array(predictions); aa = np.array(actuals)

    print(f"Predicted birthday: mean={pa.mean():.2f}, std={pa.std():.2f}")
    print(f"Actual δH:          mean={aa.mean():.2f}, std={aa.std():.2f}")
    print(f"corr(predicted, actual) = {np.corrcoef(pa, aa)[0,1]:+.6f}")

    # Distribution of predicted birthday
    print(f"\nPredicted birthday distribution:")
    for threshold in [100, 110, 120, 128, 140, 150]:
        pct = np.mean(pa < threshold) * 100
        if pct > 0:
            print(f"  P(birthday < {threshold}): {pct:.1f}%")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 85: PER-MESSAGE FOURIER PERIOD")
    print(f"birthday = 3×4×fourier×η. Does fourier vary?")
    print("="*60)
    pa, da = test_fourier_distribution(2500)
    test_formula_per_message(2000)

if __name__ == "__main__":
    main()
