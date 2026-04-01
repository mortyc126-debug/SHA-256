#!/usr/bin/env python3
"""
EXP 175: THREE SPECIALIZED INSTRUMENTS FOR THE DEAD ZONE

Not general-purpose stats. CUSTOM instruments for each signal.

INSTRUMENT 1: ★-STETHOSCOPE
  Tuned to the 22.5-round heartbeat.
  Amplifies the periodic component. Shows the WAVEFORM.

INSTRUMENT 2: ★-TRACKER
  Follows INDIVIDUAL GKP positions through dead zone.
  Shows the LIFE STORY of each position across rounds.

INSTRUMENT 3: ★-THREAD
  Magnifies the -0.05 correlation.
  Finds WHICH specific bits are connected dead zone → hash.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

# ============================================================
# INSTRUMENT 1: ★-STETHOSCOPE — Heartbeat detector
# ============================================================
def star_stethoscope(N=500):
    """Listen for the 22.5-round heartbeat."""
    print(f"\n{'='*60}")
    print(f"INSTRUMENT 1: ★-STETHOSCOPE")
    print(f"Tuned to 22.5-round period")
    print(f"{'='*60}")

    # Collect entropy traces at EVERY round from 20 to 64
    rounds = list(range(20, 65))
    traces = np.zeros((N, len(rounds)))

    for trial in range(N):
        M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        for i, r in enumerate(rounds):
            # Compute a SENSITIVE metric: not just entropy but
            # the FULL carry chain signature
            total_alive = 0
            max_chain = 0
            for w in range(8):
                gkp = carry_gkp_classification(s1_all[r][w], s2_all[r][w])
                current = 0
                for c in gkp:
                    if c != 'K':
                        current += 1
                    else:
                        total_alive += current
                        max_chain = max(max_chain, current)
                        current = 0
                total_alive += current
                max_chain = max(max_chain, current)

            traces[trial, i] = total_alive + max_chain * 0.1

    # Average trace
    avg_trace = traces.mean(axis=0)
    std_trace = traces.std(axis=0)

    # Remove DC component (mean)
    signal = avg_trace - avg_trace.mean()

    # DEMODULATION at frequency 1/22.5 = 0.0444
    target_freq = 1.0 / 22.5
    t = np.arange(len(signal))

    # Matched filter: multiply by sin and cos at target frequency
    cos_component = np.sum(signal * np.cos(2 * np.pi * target_freq * t))
    sin_component = np.sum(signal * np.sin(2 * np.pi * target_freq * t))
    amplitude = math.sqrt(cos_component**2 + sin_component**2) / len(t)
    phase = math.atan2(sin_component, cos_component)

    # Also check other frequencies for comparison
    print(f"\n  HEARTBEAT DETECTION:")
    print(f"  {'Period':>8} | {'Amplitude':>10} | {'Phase':>8} | {'Signal'}")
    print(f"  " + "-" * 45)

    for period in [5, 8, 9, 11, 15, 22.5, 30, 45]:
        freq = 1.0 / period
        c = np.sum(signal * np.cos(2 * np.pi * freq * t))
        s = np.sum(signal * np.sin(2 * np.pi * freq * t))
        amp = math.sqrt(c**2 + s**2) / len(t)
        ph = math.atan2(s, c)
        strength = amp / std_trace.mean()
        bar = "█" * min(int(strength * 50), 40)
        print(f"  {period:>8.1f} | {amp:>10.4f} | {ph:>+8.3f} | {bar}")

    # Show the WAVEFORM
    print(f"\n  WAVEFORM (dead zone, rounds 20-64):")
    print(f"  {'Round':>5} | {'Signal':>8} | Visualization")
    print(f"  " + "-" * 50)

    for i, r in enumerate(rounds):
        val = signal[i]
        # Visual bar
        center = 25
        pos = center + int(val * 10)
        pos = max(0, min(50, pos))
        bar = " " * pos + "●"
        print(f"  {r:>5} | {val:>+8.3f} | {bar}")

# ============================================================
# INSTRUMENT 2: ★-TRACKER — Follow individual positions
# ============================================================
def star_tracker(N=200):
    """Follow specific GKP positions through the dead zone."""
    print(f"\n{'='*60}")
    print(f"INSTRUMENT 2: ★-TRACKER")
    print(f"Following individual GKP positions")
    print(f"{'='*60}")

    # For ONE specific message pair: track GKP at each position across rounds
    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = sha256_rounds(M1, 64)
    s2_all = sha256_rounds(M2, 64)

    # Track 4 specific positions across word 0
    positions_to_track = [(0, 0), (0, 7), (0, 15), (0, 31)]

    print(f"\n  Individual position lifecycles (word 0, specific bits):")
    print(f"  {'Round':>5} |", end="")
    for w, b in positions_to_track:
        print(f" w{w}b{b:>2}", end="")
    print(f" | Full word 0 GKP string")
    print(f"  " + "-" * 60)

    for r in range(20, 45):
        gkp = carry_gkp_classification(s1_all[r][0], s2_all[r][0])
        print(f"  {r:>5} |", end="")
        for w, b in positions_to_track:
            g = gkp[b]
            # Color-code: G=↑ K=↓ P=→
            symbol = {'G': ' G↑', 'K': ' K↓', 'P': ' P→'}[g]
            print(f"{symbol}", end="")
        # Show full GKP string for word 0
        gkp_str = ''.join('G' if g == 'G' else ('K' if g == 'K' else '·') for g in gkp)
        print(f"  | {gkp_str}")

    # STATISTICAL: how often does each position change type?
    print(f"\n  Position STABILITY (how often GKP type changes, N={N}):")
    print(f"  {'Word':>4} {'Bit':>4} | {'Changes/round':>13} | {'Most stable':>11} | {'Bar'}")
    print(f"  " + "-" * 50)

    stabilities = np.zeros((8, 32))
    for _ in range(N):
        M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
        s1_all = sha256_rounds(M1, 64)
        s2_all = sha256_rounds(M2, 64)

        for w in range(8):
            for b in range(32):
                changes = 0
                prev = None
                for r in range(20, 64):
                    gkp = carry_gkp_classification(s1_all[r][w], s2_all[r][w])
                    current = gkp[b]
                    if prev is not None and current != prev:
                        changes += 1
                    prev = current
                stabilities[w, b] += changes / 43  # 43 transitions

    stabilities /= N

    # Show most and least stable positions
    flat = [(stabilities[w, b], w, b) for w in range(8) for b in range(32)]
    flat.sort()

    print(f"\n  MOST STABLE (change least in dead zone):")
    for rate, w, b in flat[:8]:
        bar = "█" * int((1 - rate) * 30)
        print(f"  {w:>4} {b:>4} | {rate:>13.4f} | {1-rate:>10.1%} stable | {bar}")

    print(f"\n  LEAST STABLE (change most):")
    for rate, w, b in flat[-5:]:
        bar = "█" * int((1 - rate) * 30)
        print(f"  {w:>4} {b:>4} | {rate:>13.4f} | {1-rate:>10.1%} stable | {bar}")

    return stabilities

# ============================================================
# INSTRUMENT 3: ★-THREAD — Magnify dead zone → hash connection
# ============================================================
def star_thread(N=800):
    """Find the SPECIFIC bits connecting dead zone to hash."""
    print(f"\n{'='*60}")
    print(f"INSTRUMENT 3: ★-THREAD")
    print(f"Dead zone → hash bit-level connections")
    print(f"{'='*60}")

    # For each state bit at round 30: correlate with each hash bit
    # Find the STRONGEST individual connections

    R = 30  # Middle of dead zone
    state_bits = np.zeros((N, 256))
    hash_bits = np.zeros((N, 256))

    for i in range(N):
        M = random_w16()
        s = sha256_rounds(M, R)[R]
        H = sha256_compress(M)

        for w in range(8):
            for b in range(32):
                state_bits[i, w*32+b] = (s[w] >> b) & 1
                hash_bits[i, w*32+b] = (H[w] >> b) & 1

    # Compute correlations (sample to avoid 256×256 = 65536)
    print(f"\n  State[round {R}] → Hash correlations:")
    print(f"  Sampling 1000 random (state_bit, hash_bit) pairs...")

    strong_connections = []
    for _ in range(2000):
        sb = random.randint(0, 255)
        hb = random.randint(0, 255)

        c = np.corrcoef(state_bits[:, sb], hash_bits[:, hb])[0, 1]
        if not np.isnan(c):
            strong_connections.append((abs(c), c, sb, hb))

    strong_connections.sort(reverse=True)

    threshold = 3 / math.sqrt(N)
    n_significant = sum(1 for ac, _, _, _ in strong_connections if ac > threshold)

    print(f"\n  Threshold (3σ): {threshold:.4f}")
    print(f"  Significant connections: {n_significant}/{len(strong_connections)}")
    print(f"  Expected false positives: {len(strong_connections) * 0.003:.0f}")

    if n_significant > len(strong_connections) * 0.003 * 3:
        print(f"  ★★★ EXCESS CONNECTIONS! ({n_significant} vs {len(strong_connections)*0.003:.0f} expected)")

    print(f"\n  TOP 15 STRONGEST THREADS:")
    print(f"  {'State bit':>15} | {'Hash bit':>15} | {'Corr':>8}")
    print(f"  " + "-" * 45)
    for ac, c, sb, hb in strong_connections[:15]:
        sw = sb // 32; sbit = sb % 32
        hw_idx = hb // 32; hbit = hb % 32
        marker = " ★" if ac > threshold else ""
        print(f"  s[{sw}]b{sbit:>2}        | H[{hw_idx}]b{hbit:>2}        | {c:>+8.4f}{marker}")

    # CROSS-ROUND: do the same threads exist at round 25 and round 40?
    print(f"\n  Thread PERSISTENCE across dead zone:")
    top_5 = strong_connections[:5]
    for ac, c, sb, hb in top_5:
        sw = sb // 32; sbit = sb % 32
        hw_idx = hb // 32; hbit = hb % 32

        corrs_per_round = []
        for R_test in [25, 30, 35, 40, 50, 60]:
            s_bits_test = np.zeros(N)
            for i in range(N):
                M = random_w16()
                s = sha256_rounds(M, R_test)[R_test]
                s_bits_test[i] = (s[sw] >> sbit) & 1

            c_test = np.corrcoef(s_bits_test, hash_bits[:, hb])[0, 1]
            corrs_per_round.append(f"{c_test:+.3f}" if not np.isnan(c_test) else "  NaN")

        print(f"  s[{sw}]b{sbit:>2}→H[{hw_idx}]b{hbit:>2}: {' '.join(corrs_per_round)}")
        print(f"  {'':>17} r=25  r=30  r=35  r=40  r=50  r=60")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 175: THREE SPECIALIZED INSTRUMENTS")
    print("=" * 60)

    star_stethoscope(N=400)
    stabilities = star_tracker(N=150)
    star_thread(N=600)

    print(f"\n{'='*60}")
    print(f"VERDICT: What the instruments reveal")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
