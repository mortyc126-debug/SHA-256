#!/usr/bin/env python3
"""
EXP 33: Coherent Pair Ensemble — Third Path

NOT stronger channel (ceiling 0.085).
NOT longer lifetime (ceiling τ=12).
NEW: amplify through COHERENT ENSEMBLE of pairs.

Idea: K messages → K(K-1)/2 pairs. Each pair has coupling signal 0.085.
If signals are CORRELATED (shared messages) → total signal grows as √K.
If signals are INDEPENDENT → total signal stays 0.085 (no gain).

The key: ARE coupling signals between (M1,M2) and (M1,M3) correlated?
If M1 is shared → the coupling at round 63 depends on M1's state →
both pairs see the SAME coupling landscape → signals ADD.

This is a MULTI-TARGET collision: instead of H(M)=H(M') for one pair,
find M₁,...,Mₖ where SOME pair (Mᵢ,Mⱼ) has unusually low δH.
Birthday on K messages gives K²/2 pairs → cost √(2^256/K²).

If coupling coherence adds √K factor → total cost = 2^128 / K^{3/2}.
At K=2^20 → cost = 2^128 / 2^30 = 2^98. First sub-2^128 result!

BUT: need to verify coupling coherence first.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    c_out = []; c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        c_out.append(c)
    return c_out

def kappa_63_for_pair(Wn, Wf):
    """Quick κ_63 measurement."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    We = schedule(Wn); Wfe = schedule(Wf)
    dn=sn[63][3]; en=sn[63][4]; fn=sn[63][5]; gn=sn[63][6]; hn=sn[63][7]
    df=sf[63][3]; ef=sf[63][4]; ff_=sf[63][5]; gf=sf[63][6]; hf=sf[63][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    return sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

def dH_for_pair(Wn, Wf):
    """Quick δH measurement."""
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def test_coupling_coherence(N_messages=100, N_trials=50):
    """
    KEY TEST: Are coupling signals between shared-message pairs CORRELATED?

    For message M₁: compute κ(M₁,M₂) and κ(M₁,M₃).
    If corr(κ₁₂, κ₁₃) > 0 → coherence exists → signals add up.
    """
    print("\n--- TEST 1: COUPLING COHERENCE (shared messages) ---")

    coherence_corrs = []

    for _ in range(N_trials):
        # Generate one "hub" message
        M_hub = random_w16()

        # Generate N "spoke" messages as Wang pairs from hub
        kappas = []
        dHs = []

        for _ in range(N_messages):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            # Create variation: M_spoke = M_hub with different W[0..1]
            M_spoke = list(M_hub)
            M_spoke[0] = W0
            M_spoke[1] = W1

            k = kappa_63_for_pair(M_hub, M_spoke)
            dh = dH_for_pair(M_hub, M_spoke)
            kappas.append(k)
            dHs.append(dh)

        # Coherence: corr between κ values sharing the same hub
        # If coherent: κ values should be MORE similar than random
        k_arr = np.array(kappas)
        dh_arr = np.array(dHs)

        # Measure: std of κ within this ensemble vs expected
        coherence_corrs.append(k_arr.std())

    # Compare intra-hub std vs inter-hub std
    intra_std = np.mean(coherence_corrs)

    # Random baseline: κ between unrelated pairs
    random_kappas = []
    for _ in range(N_messages * N_trials):
        M1 = random_w16(); M2 = random_w16()
        random_kappas.append(kappa_63_for_pair(M1, M2))
    inter_std = np.std(random_kappas)

    print(f"Intra-hub κ std:  {intra_std:.4f} (shared M_hub)")
    print(f"Inter-random std: {inter_std:.4f} (unrelated pairs)")
    print(f"Ratio: {intra_std/inter_std:.4f}")

    if intra_std < inter_std * 0.9:
        print("*** SIGNAL: Shared hub REDUCES κ variance → COHERENT! ***")
        print(f"Coherence factor: {inter_std/intra_std:.4f}")
    else:
        print("No coherence: shared hub doesn't reduce variance")

    return intra_std, inter_std

def test_ensemble_collision_search(K_values=[10, 30, 100, 300]):
    """
    Multi-target collision search using ensembles.

    For each K: generate K messages, compute K(K-1)/2 pairs,
    find minimum δH. Compare with birthday expectation.
    """
    print("\n--- TEST 2: ENSEMBLE COLLISION SEARCH ---")

    N_trials = 30

    print(f"{'K':>5} | {'E[min δH]':>10} | {'Birthday':>9} | {'Δ':>6} | {'#pairs':>8}")
    print("-"*50)

    for K in K_values:
        min_dHs = []

        for _ in range(N_trials):
            # Generate K random messages
            messages = [random_w16() for _ in range(K)]

            # Compute hashes
            hashes = [sha256_compress(m) for m in messages]

            # Find minimum δH among all pairs
            min_dh = 256
            for i in range(K):
                for j in range(i+1, K):
                    dh = sum(hw(hashes[i][w]^hashes[j][w]) for w in range(8))
                    min_dh = min(min_dh, dh)

            min_dHs.append(min_dh)

        arr = np.array(min_dHs)
        n_pairs = K*(K-1)//2
        birthday = 128 - 8 * np.sqrt(2 * np.log(n_pairs))
        delta = arr.mean() - birthday

        print(f"{K:>5} | {arr.mean():>10.2f} | {birthday:>9.1f} | {delta:>+6.1f} | {n_pairs:>8}")

def test_wang_ensemble(K_values=[10, 30, 100]):
    """
    Ensemble of WANG PAIRS sharing the same M_hub.

    All pairs (M_hub, M_hub+ΔWᵢ) where ΔWᵢ are different Wang cascades.
    These pairs SHARE the hub → coupling may be coherent.
    """
    print("\n--- TEST 3: WANG ENSEMBLE (shared hub) ---")

    N_trials = 30

    print(f"{'K':>5} | {'E[min δH]':>10} | {'Random K':>9} | {'Δ':>6}")
    print("-"*40)

    for K in K_values:
        wang_min_dHs = []
        random_min_dHs = []

        for _ in range(N_trials):
            # Wang ensemble: one hub, K different cascades
            hub_W0 = random.randint(0, MASK)
            hub_W1 = random.randint(0, MASK)

            wang_hashes = []
            for _ in range(K):
                W0 = random.randint(0, MASK)
                W1 = random.randint(0, MASK)
                try:
                    Wn, Wf, _, _, _ = wang_cascade(W0, W1)
                    wang_hashes.append(sha256_compress(Wf))
                except:
                    pass

            if len(wang_hashes) < 2:
                continue

            # All Wang hashes should be near-random but created through cascade
            min_dh = 256
            for i in range(len(wang_hashes)):
                for j in range(i+1, len(wang_hashes)):
                    dh = sum(hw(wang_hashes[i][w]^wang_hashes[j][w]) for w in range(8))
                    min_dh = min(min_dh, dh)
            wang_min_dHs.append(min_dh)

            # Random baseline with same K
            rand_hashes = [sha256_compress(random_w16()) for _ in range(K)]
            min_dh_r = 256
            for i in range(K):
                for j in range(i+1, K):
                    dh = sum(hw(rand_hashes[i][w]^rand_hashes[j][w]) for w in range(8))
                    min_dh_r = min(min_dh_r, dh)
            random_min_dHs.append(min_dh_r)

        wa = np.array(wang_min_dHs)
        ra = np.array(random_min_dHs)
        delta = wa.mean() - ra.mean()

        print(f"{K:>5} | {wa.mean():>10.2f} | {ra.mean():>9.2f} | {delta:>+6.2f}")

        if delta < -2:
            print(f"       *** Wang ensemble {abs(delta):.1f} bits better than random! ***")

def test_coupling_guided_ensemble(K=50, N_trials=30):
    """
    COMBINE coupling guidance with ensemble:
    1. Generate K Wang pairs
    2. Measure κ_63 for each
    3. Select top-√K by low coupling
    4. Compare inter-selected δH vs random selection
    """
    print(f"\n--- TEST 4: COUPLING-GUIDED ENSEMBLE (K={K}) ---")

    guided_mins = []
    random_mins = []

    for _ in range(N_trials):
        # Generate K Wang pairs with their hashes and κ
        pairs = []
        for _ in range(K):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            try:
                Wn,Wf,_,_,_ = wang_cascade(W0,W1)
                Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
                k63 = kappa_63_for_pair(Wn, Wf)
                pairs.append((Hn, Hf, k63))
            except: pass

        if len(pairs) < 10:
            continue

        # Guided selection: pick pairs with lowest κ
        pairs.sort(key=lambda p: p[2])
        n_select = max(int(len(pairs)**0.5), 5)
        selected = pairs[:n_select]
        rest = pairs[n_select:]

        # Min δH among selected faulty hashes
        min_dh_guided = 256
        for i in range(len(selected)):
            for j in range(i+1, len(selected)):
                dh = sum(hw(selected[i][1][w]^selected[j][1][w]) for w in range(8))
                min_dh_guided = min(min_dh_guided, dh)
        guided_mins.append(min_dh_guided)

        # Random selection of same size
        random_sel = random.sample(pairs, min(n_select, len(pairs)))
        min_dh_random = 256
        for i in range(len(random_sel)):
            for j in range(i+1, len(random_sel)):
                dh = sum(hw(random_sel[i][1][w]^random_sel[j][1][w]) for w in range(8))
                min_dh_random = min(min_dh_random, dh)
        random_mins.append(min_dh_random)

    ga = np.array(guided_mins); ra = np.array(random_mins)
    print(f"Coupling-guided: E[min δH]={ga.mean():.2f}")
    print(f"Random selection: E[min δH]={ra.mean():.2f}")
    print(f"Difference: {ga.mean()-ra.mean():+.2f}")

    if ga.mean() < ra.mean() - 1:
        print("*** SIGNAL: Coupling-guided ensemble outperforms random! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 33: COHERENT PAIR ENSEMBLE — THIRD PATH")
    print("Amplify through shared-message coherence")
    print("="*60)

    test_coupling_coherence(80, 40)
    test_ensemble_collision_search([10, 30, 100])
    test_wang_ensemble([10, 30, 100])
    test_coupling_guided_ensemble(50, 25)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
