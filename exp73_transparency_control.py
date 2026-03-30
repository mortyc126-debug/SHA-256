#!/usr/bin/env python3
"""
EXP 73: Transparency Control — Can T(bit) be Message-Optimized?

T(bit) is average over messages. How much does it VARY per message?
If high variance → some messages have high T → more transparent → exploit.

For each of the 32 bits:
1. Measure T(bit) for 5000 individual Wang pairs
2. Compute variance and range
3. Find: maximum simultaneous transparency across ALL bits

If "max transparency message" exists with T >> average:
that message's collision is easier by (T_max - 0.5) × 256 bits.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def per_message_transparency(Wn, Wf):
    """Measure transparency of ALL 32 bits × 8 words for one pair."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

    T = np.zeros((8, 32))  # 8 words × 32 bits
    for w in range(8):
        for bit in range(32):
            s_xor = (sn[64][w] ^ sf[64][w] >> bit) & 1
            h_xor = (Hn[w] ^ Hf[w] >> bit) & 1
            T[w][bit] = 1 if s_xor == h_xor else 0

    return T  # Binary: 1 = transparent, 0 = not

def test_per_bit_variance(N=3000):
    """How much does T(bit) vary across messages?"""
    print(f"\n--- PER-BIT TRANSPARENCY VARIANCE (N={N}) ---")

    all_T = []  # N × 8 × 32

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        T = per_message_transparency(Wn, Wf)
        all_T.append(T)

    A = np.array(all_T)  # N × 8 × 32

    # Per-bit statistics across messages
    # Focus on e-branch (words 4-7)
    print(f"\nE-branch bit transparency (mean ± std across messages):")
    print(f"{'Bit':>4} | {'Mean':>6} | {'Std':>6} | {'Min':>4} | {'Max':>4} | {'P(T=1)':>7}")
    print("-"*45)

    total_transparent_per_msg = np.zeros(N)

    for bit in range(32):
        # Average over e-branch words
        vals = A[:, 4:8, bit].mean(axis=1)  # N values, average over 4 words
        mean_v = vals.mean()
        std_v = vals.std()

        # P(all 4 e-branch words transparent at this bit)
        all_4 = np.all(A[:, 4:8, bit] == 1, axis=1)
        p_all = all_4.mean()

        total_transparent_per_msg += A[:, 4:8, bit].sum(axis=1)

        if bit in [0,1,2,3,5,9,10,14,19,25,27,29,31]:
            print(f"{bit:>4} | {mean_v:>6.3f} | {std_v:>6.3f} | {vals.min():>4.2f} | "
                  f"{vals.max():>4.2f} | {p_all:>7.4f}")

    # TOTAL transparent bits per message
    print(f"\nTotal transparent bits (e-branch, 4×32=128 possible):")
    print(f"  Mean: {total_transparent_per_msg.mean():.1f}")
    print(f"  Std: {total_transparent_per_msg.std():.1f}")
    print(f"  Max: {total_transparent_per_msg.max():.0f}")
    print(f"  Min: {total_transparent_per_msg.min():.0f}")

    return A, total_transparent_per_msg

def test_max_transparency_messages(A, total_t, N_top=20):
    """Examine messages with MAXIMUM transparency."""
    print(f"\n--- MAX TRANSPARENCY MESSAGES ---")

    N = len(total_t)
    top_indices = np.argsort(-total_t)[:N_top]

    print(f"Top {N_top} by total e-branch transparency:")
    for rank, idx in enumerate(top_indices[:10]):
        T = A[idx, 4:8, :]  # 4×32
        n_transparent = int(T.sum())
        # Which bits are transparent in ALL 4 words?
        all_4 = np.all(T == 1, axis=0)
        n_all4 = int(all_4.sum())
        transparent_bits = list(np.where(all_4)[0])

        print(f"  #{rank+1}: {n_transparent}/128 bits, "
              f"all-4-words: {n_all4}/32 bits: {transparent_bits[:10]}...")

def test_transparency_correlates_dH(N=4000):
    """Does per-message transparency predict δH?"""
    print(f"\n--- TRANSPARENCY → δH (per message) ---")

    t_scores = []; dH_list = []; dH_sub_list = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        T = per_message_transparency(Wn, Wf)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)

        t_score = T[4:8, :].sum()  # Total e-branch transparency
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        dH_e = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))

        t_scores.append(t_score)
        dH_list.append(dH)
        dH_sub_list.append(dH_e)

    ts=np.array(t_scores); dh=np.array(dH_list); dhe=np.array(dH_sub_list)
    threshold = 3/np.sqrt(N)

    c_full = np.corrcoef(ts, dh)[0,1]
    c_e = np.corrcoef(ts, dhe)[0,1]

    print(f"corr(transparency_score, δH_full) = {c_full:+.6f} {'***' if abs(c_full)>threshold else ''}")
    print(f"corr(transparency_score, δH_e)    = {c_e:+.6f} {'***' if abs(c_e)>threshold else ''}")

    # Quartile analysis
    for label, mask in [("Top 25% transparent", ts > np.percentile(ts, 75)),
                         ("Bottom 25%", ts < np.percentile(ts, 25))]:
        dh_sub = dh[mask]; dhe_sub = dhe[mask]
        print(f"  {label}: E[δH]={dh_sub.mean():.4f}, E[δH_e]={dhe_sub.mean():.4f}")

def test_hill_climb_transparency(N=30, steps=500):
    """Hill-climb for maximum transparency message."""
    print(f"\n--- HILL-CLIMB MAX TRANSPARENCY ---")

    best_global = 0; best_global_dH = 256

    for trial in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        T = per_message_transparency(Wn, Wf)
        current_score = T[4:8,:].sum()
        best_score = current_score

        for step in range(steps):
            # Flip random bit in W0 or W1
            if random.random()<0.5:
                tW0=W0^(1<<random.randint(0,31)); tW1=W1
            else:
                tW0=W0; tW1=W1^(1<<random.randint(0,31))

            try:
                tWn,tWf,_,_,_ = wang_cascade(tW0,tW1)
                tT = per_message_transparency(tWn, tWf)
                ts = tT[4:8,:].sum()
                if ts > current_score:
                    current_score = ts; W0=tW0; W1=tW1; Wn=tWn; Wf=tWf
                    best_score = max(best_score, ts)
            except: pass

        # Measure δH for best
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        if best_score > best_global:
            best_global = best_score; best_global_dH = dH

        if trial < 5:
            print(f"  Trial {trial}: transparency {best_score:.0f}/128, δH={dH}")

    print(f"\nBest: transparency={best_global:.0f}/128, δH={best_global_dH}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 73: TRANSPARENCY CONTROL")
    print("="*60)
    A, total_t = test_per_bit_variance(2500)
    test_max_transparency_messages(A, total_t)
    test_transparency_correlates_dH(3000)
    test_hill_climb_transparency(20, 300)

if __name__ == "__main__":
    main()
