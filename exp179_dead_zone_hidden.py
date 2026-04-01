#!/usr/bin/env python3
"""
EXP 179: DEAD ZONE HIDDEN FEATURES

What's LOGICALLY MISSING from our inventory?
Search for hidden structures.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extended_rounds(M, n_rounds):
    W = schedule(M)
    state = list(IV)
    states = [list(state)]
    for r in range(n_rounds):
        state = sha256_round(state, W[r % 64], K[r % 64])
        states.append(list(state))
    return states

# ============================================================
# F: CROSS-BIT CORRELATIONS — σ-CLIQUE?
# ============================================================
def survey_cross_bit(N_rounds=500):
    """Do σ-rotation positions form a correlated clique?"""
    print(f"\n{'='*60}")
    print(f"F: CROSS-BIT CORRELATIONS — σ-CLIQUE?")
    print(f"{'='*60}")

    # σ₀ rotations: 2, 13, 22 → positions 2, 13, 22
    # σ₁ rotations: 6, 11, 25 → positions 6, 11, 25
    # Bit 18 had highest memory (σ₀ uses ROTR_18 in schedule sig0)

    sigma_positions = [2, 6, 10, 11, 13, 14, 18, 22, 25]
    other_positions = [0, 1, 3, 5, 8, 15, 20, 27, 31]

    M = random_w16()
    states = extended_rounds(M, N_rounds)

    # Collect traces for word 0
    traces = np.zeros((N_rounds - 20, 32))
    for r_off in range(N_rounds - 20):
        r = r_off + 20
        for b in range(32):
            traces[r_off, b] = (states[r][0] >> b) & 1

    # Cross-bit correlations among σ-positions
    sigma_corrs = []
    for i in range(len(sigma_positions)):
        for j in range(i + 1, len(sigma_positions)):
            b1 = sigma_positions[i]; b2 = sigma_positions[j]
            c = np.corrcoef(traces[:, b1], traces[:, b2])[0, 1]
            if not np.isnan(c):
                sigma_corrs.append((c, b1, b2))

    other_corrs = []
    for i in range(len(other_positions)):
        for j in range(i + 1, len(other_positions)):
            b1 = other_positions[i]; b2 = other_positions[j]
            c = np.corrcoef(traces[:, b1], traces[:, b2])[0, 1]
            if not np.isnan(c):
                other_corrs.append((c, b1, b2))

    sc = np.array([c for c, _, _ in sigma_corrs])
    oc = np.array([c for c, _, _ in other_corrs])

    sc_max = max(sigma_corrs, key=lambda x: abs(x[0]))
    oc_max = max(other_corrs, key=lambda x: abs(x[0]))
    print(f"\n  σ-position cross-correlations: mean={sc.mean():+.4f}, max={sc_max[0]:+.4f} (b{sc_max[1]}↔b{sc_max[2]})")
    print(f"  Other position cross-correlations: mean={oc.mean():+.4f}, max={oc_max[0]:+.4f} (b{oc_max[1]}↔b{oc_max[2]})")

    if abs(sc.mean()) > abs(oc.mean()) * 1.5:
        print(f"  ★★★ σ-CLIQUE EXISTS! σ-positions are more correlated!")
    else:
        print(f"  No clique (σ-positions ≈ other positions)")

    # Strongest cross-bit pairs overall
    all_corrs = []
    for b1 in range(32):
        for b2 in range(b1 + 1, 32):
            c = np.corrcoef(traces[:, b1], traces[:, b2])[0, 1]
            if not np.isnan(c):
                all_corrs.append((abs(c), c, b1, b2))

    all_corrs.sort(reverse=True)
    print(f"\n  STRONGEST cross-bit pairs (word 0):")
    for ac, c, b1, b2 in all_corrs[:8]:
        s1 = "σ" if b1 in sigma_positions else " "
        s2 = "σ" if b2 in sigma_positions else " "
        print(f"    bit {b1:>2}{s1} ↔ bit {b2:>2}{s2}: corr={c:+.4f}")

# ============================================================
# G: a_new/e_new vs SHIFTED — Where is FRESHNESS born?
# ============================================================
def survey_freshness(N_rounds=300):
    """a_new and e_new are freshly computed. Others are shifted copies.
    How different is the 'fresh' part from the 'stale' part?"""
    print(f"\n{'='*60}")
    print(f"G: FRESHNESS — a_new/e_new vs shifted words")
    print(f"{'='*60}")

    M = random_w16()
    states = extended_rounds(M, N_rounds)

    # Track volatility: how much does each word CHANGE per round?
    word_changes = np.zeros((N_rounds - 21, 8))
    for r_off in range(N_rounds - 21):
        r = r_off + 20
        for w in range(8):
            word_changes[r_off, w] = hw(states[r][w] ^ states[r + 1][w])

    print(f"\n  Per-word volatility (bits changed per round):")
    print(f"  Word | Role     | Volatility | Bar")
    print(f"  " + "-" * 50)
    for w in range(8):
        avg = word_changes[:, w].mean()
        role = {0: "a(FRESH)", 1: "b=a_old", 2: "c=b_old", 3: "d=c_old",
                4: "e(FRESH)", 5: "f=e_old", 6: "g=f_old", 7: "h=g_old"}[w]
        bar = "█" * int(avg)
        print(f"  {w:>4} | {role:<8} | {avg:>10.2f} | {bar}")

    # KEY: ONLY words 0 (a) and 4 (e) should change significantly
    # Words 1-3 and 5-7 are shifted copies → should change by
    # exactly the amount their predecessor changed LAST round

# ============================================================
# H: PHASE RELATION a-branch ↔ e-branch
# ============================================================
def survey_phase_relation(N_rounds=500):
    """Are a-branch and e-branch in phase or out of phase?"""
    print(f"\n{'='*60}")
    print(f"H: PHASE — a-branch ↔ e-branch")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    # Track dH per branch
    a_branch_dH = []
    e_branch_dH = []

    for r in range(20, N_rounds):
        a_dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(4))
        e_dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(4, 8))
        a_branch_dH.append(a_dH)
        e_branch_dH.append(e_dH)

    aa = np.array(a_branch_dH); ea = np.array(e_branch_dH)

    # Cross-correlation
    corr0 = np.corrcoef(aa, ea)[0, 1]
    corr1 = np.corrcoef(aa[:-1], ea[1:])[0, 1]  # a leads e by 1
    corr_neg1 = np.corrcoef(aa[1:], ea[:-1])[0, 1]  # e leads a by 1

    print(f"\n  a-branch ↔ e-branch correlation:")
    print(f"    Lag  0 (simultaneous): {corr0:+.4f}")
    print(f"    Lag +1 (a leads e):    {corr1:+.4f}")
    print(f"    Lag -1 (e leads a):    {corr_neg1:+.4f}")

    if abs(corr1) > abs(corr0) + 0.05:
        print(f"    ★ a-branch LEADS e-branch!")
    elif abs(corr_neg1) > abs(corr0) + 0.05:
        print(f"    ★ e-branch LEADS a-branch!")
    else:
        print(f"    Branches are approximately IN PHASE")

    # Phase in Fourier
    centered_a = aa - aa.mean()
    centered_e = ea - ea.mean()
    fft_a = np.fft.fft(centered_a)
    fft_e = np.fft.fft(centered_e)

    # Phase difference at top frequency
    power = np.abs(fft_a[1:len(fft_a)//2]) * np.abs(fft_e[1:len(fft_e)//2])
    top_freq = np.argmax(power) + 1
    phase_diff = np.angle(fft_a[top_freq]) - np.angle(fft_e[top_freq])

    period = len(centered_a) / top_freq
    print(f"\n    Dominant shared frequency: period = {period:.1f} rounds")
    print(f"    Phase difference: {phase_diff:.4f} rad = {phase_diff*180/math.pi:.1f}°")
    print(f"    (0° = in phase, 180° = anti-phase)")

# ============================================================
# I: dH DIPS — What happens when dH momentarily drops?
# ============================================================
def survey_dh_dips(N_rounds=1000):
    """When dH drops below 115 in dead zone: what's special?"""
    print(f"\n{'='*60}")
    print(f"I: dH DIPS — Structure at low moments ({N_rounds} rounds)")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    dH_trace = []
    nP_at_dip = []; nP_at_peak = []; nP_at_normal = []
    max_chain_at_dip = []; max_chain_at_normal = []

    for r in range(20, N_rounds):
        s1 = s1_all[r]; s2 = s2_all[r]
        dH = sum(hw(s1[w] ^ s2[w]) for w in range(8))
        dH_trace.append(dH)

        # Collect stats
        total_P = 0; max_chain = 0
        for w in range(8):
            gkp = carry_gkp_classification(s1[w], s2[w])
            total_P += gkp.count('P')
            current = 0
            for c in gkp:
                if c != 'K': current += 1
                else:
                    max_chain = max(max_chain, current); current = 0
            max_chain = max(max_chain, current)

        if dH < 115:
            nP_at_dip.append(total_P)
            max_chain_at_dip.append(max_chain)
        elif dH > 140:
            nP_at_peak.append(total_P)
        else:
            nP_at_normal.append(total_P)
            max_chain_at_normal.append(max_chain)

    dt = np.array(dH_trace)
    n_dips = len(nP_at_dip)
    n_peaks = len(nP_at_peak)

    print(f"\n  dH distribution in dead zone:")
    print(f"    Mean: {dt.mean():.1f}, Std: {dt.std():.2f}")
    print(f"    Dips (dH<115): {n_dips}/{len(dt)} ({n_dips/len(dt)*100:.1f}%)")
    print(f"    Peaks (dH>140): {n_peaks}/{len(dt)} ({n_peaks/len(dt)*100:.1f}%)")

    if n_dips > 5:
        print(f"\n  AT DIPS (dH<115):")
        print(f"    nP: {np.mean(nP_at_dip):.1f} (normal: {np.mean(nP_at_normal):.1f})")
        print(f"    max_chain: {np.mean(max_chain_at_dip):.1f} (normal: {np.mean(max_chain_at_normal):.1f})")

        # What happens AFTER a dip? Does dH bounce back or stay low?
        dip_indices = [i for i, d in enumerate(dH_trace) if d < 115]
        after_dip = []
        for idx in dip_indices:
            if idx + 1 < len(dH_trace):
                after_dip.append(dH_trace[idx + 1])

        if after_dip:
            print(f"\n    After dip: E[dH_next] = {np.mean(after_dip):.1f}")
            print(f"    (vs overall mean {dt.mean():.1f})")
            bounce = np.mean(after_dip) - dt.mean()
            print(f"    Bounce: {bounce:+.1f} (positive = bounces UP)")

    # DIP SPACING: how many rounds between dips?
    if len(dip_indices) > 1:
        spacings = [dip_indices[i+1] - dip_indices[i] for i in range(len(dip_indices)-1)]
        sp = np.array(spacings)
        print(f"\n    Dip spacing: mean={sp.mean():.1f}, std={sp.std():.1f}, min={sp.min()}")

        # Is spacing periodic?
        if sp.std() < sp.mean() * 0.5:
            print(f"    ★★★ REGULAR spacing! Dips come every ~{sp.mean():.0f} rounds")

# ============================================================
# J: CARRY TOPOLOGY — Highways and deserts
# ============================================================
def survey_carry_topology(N_rounds=500):
    """Which bit positions are ALWAYS in a carry chain vs NEVER?"""
    print(f"\n{'='*60}")
    print(f"J: CARRY TOPOLOGY — Highways & Deserts")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    # For each bit position: fraction of rounds it's "alive" (G or P)
    alive_freq = np.zeros(256)

    for r in range(20, N_rounds):
        for w in range(8):
            gkp = carry_gkp_classification(s1_all[r][w], s2_all[r][w])
            for b in range(32):
                if gkp[b] != 'K':
                    alive_freq[w*32 + b] += 1

    alive_freq /= (N_rounds - 20)

    # Expected: ~0.75 (P=0.5 + G=0.25 = 0.75 alive)
    print(f"\n  Per-position 'alive' frequency:")
    print(f"    Mean: {alive_freq.mean():.4f} (expected ~0.750)")
    print(f"    Std:  {alive_freq.std():.4f}")
    print(f"    Range: {alive_freq.min():.4f} — {alive_freq.max():.4f}")

    # HIGHWAYS (always alive)
    highways = np.argsort(-alive_freq)[:8]
    print(f"\n  HIGHWAYS (most often alive = carry flows through):")
    for idx in highways:
        w = idx // 32; b = idx % 32
        iv_bit = (IV[w] >> b) & 1
        print(f"    Word {w} bit {b:>2} (IV={iv_bit}): alive {alive_freq[idx]:.4f}")

    # DESERTS (least alive)
    deserts = np.argsort(alive_freq)[:8]
    print(f"\n  DESERTS (least alive = carry dies here):")
    for idx in deserts:
        w = idx // 32; b = idx % 32
        iv_bit = (IV[w] >> b) & 1
        print(f"    Word {w} bit {b:>2} (IV={iv_bit}): alive {alive_freq[idx]:.4f}")

    # Is alive_freq correlated with IV?
    iv_bits = np.array([(IV[i//32] >> (i%32)) & 1 for i in range(256)])
    corr_iv = np.corrcoef(alive_freq, iv_bits)[0, 1]
    print(f"\n  corr(alive_freq, IV_bit): {corr_iv:+.4f}")

    if abs(corr_iv) > 0.1:
        print(f"  ★★★ IV CONTROLS CARRY TOPOLOGY even in dead zone!")

# ============================================================
# K: RETURN EVENTS — Does dH revisit old values?
# ============================================================
def survey_returns(N_rounds=1000):
    """Does dH return to previously visited values?"""
    print(f"\n{'='*60}")
    print(f"K: RETURN EVENTS ({N_rounds} rounds)")
    print(f"{'='*60}")

    M1 = random_w16(); M2 = list(M1); M2[0] ^= (1 << 15)
    s1_all = extended_rounds(M1, N_rounds)
    s2_all = extended_rounds(M2, N_rounds)

    dH_trace = []
    for r in range(20, N_rounds):
        dH = sum(hw(s1_all[r][w] ^ s2_all[r][w]) for w in range(8))
        dH_trace.append(dH)

    # Return times: for each dH value, when does it recur?
    value_times = {}
    return_times = []

    for i, dH in enumerate(dH_trace):
        if dH in value_times:
            rt = i - value_times[dH]
            return_times.append(rt)
        value_times[dH] = i

    if return_times:
        rt = np.array(return_times)
        print(f"\n  dH value returns:")
        print(f"    Total returns: {len(rt)}")
        print(f"    Mean return time: {rt.mean():.1f} rounds")
        print(f"    Min return time: {rt.min()} rounds")
        print(f"    Median: {np.median(rt):.0f} rounds")

        # Distribution of return times
        for t in [1, 2, 3, 5, 10, 20, 50]:
            count = np.sum(rt <= t)
            print(f"    Returns ≤ {t:>2} rounds: {count} ({count/len(rt)*100:.1f}%)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 179: DEAD ZONE HIDDEN FEATURES")
    print("=" * 60)

    survey_cross_bit(N_rounds=500)
    survey_freshness(N_rounds=300)
    survey_phase_relation(N_rounds=500)
    survey_dh_dips(N_rounds=1000)
    survey_carry_topology(N_rounds=500)
    survey_returns(N_rounds=1000)

    print(f"\n{'='*60}")
    print(f"COMPLETE DEAD ZONE INVENTORY")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
