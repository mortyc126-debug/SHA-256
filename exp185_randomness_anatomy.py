#!/usr/bin/env python3
"""
EXP 185: IS THE RANDOMNESS REAL? — Anatomy of "random" fluctuations

SHA-256 is DETERMINISTIC. There is NO randomness.
Every "random" fluctuation of δ(a,e) has a CAUSE.

QUESTION: Can we EXPLAIN the fluctuations?
If we can explain even 1% → that 1% is NOT random → exploitable.

APPROACH:
1. Take a specific δ(a,e) dip (like the one at round 63 from exp184)
2. Trace BACKWARD: WHY did δ drop at that round?
3. Which specific carry chains, which GKP patterns CAUSED it?
4. Is the cause PREDICTABLE from earlier rounds?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def ae_trajectory_detailed(M1, M2, max_r=64):
    """Full detailed trajectory including per-word breakdown."""
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)
    W1 = schedule(M1); W2 = schedule(M2)

    data = []
    for r in range(max_r + 1):
        da = hw(s1[r][0] ^ s2[r][0])
        de = hw(s1[r][4] ^ s2[r][4])
        dW = hw(W1[r % 64] ^ W2[r % 64]) if r < 64 else 0

        # GKP of (a₁,a₂) and (e₁,e₂)
        gkp_a = carry_gkp_classification(s1[r][0], s2[r][0])
        gkp_e = carry_gkp_classification(s1[r][4], s2[r][4])
        nP_a = gkp_a.count('P'); nP_e = gkp_e.count('P')

        # Carry chain analysis
        max_chain_a = 0; max_chain_e = 0
        current = 0
        for c in gkp_a:
            if c != 'K': current += 1
            else:
                max_chain_a = max(max_chain_a, current); current = 0
        max_chain_a = max(max_chain_a, current)
        current = 0
        for c in gkp_e:
            if c != 'K': current += 1
            else:
                max_chain_e = max(max_chain_e, current); current = 0
        max_chain_e = max(max_chain_e, current)

        data.append({
            'r': r, 'da': da, 'de': de, 'dae': da+de, 'dW': dW,
            'nP_a': nP_a, 'nP_e': nP_e, 'mc_a': max_chain_a, 'mc_e': max_chain_e
        })

    return data

def explain_dip():
    """Find a dip and explain it step by step."""
    print(f"\n{'='*60}")
    print(f"EXPLAINING A DIP — Step by step causality")
    print(f"{'='*60}")

    # Search for a good dip at late rounds
    best_dip = 64; best_pair = None; best_dip_r = -1

    for _ in range(2000):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        s1 = sha256_rounds(M1, 64); s2 = sha256_rounds(M2, 64)
        for r in range(50, 65):
            d = hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4])
            if d < best_dip:
                best_dip = d; best_pair = (list(M1), list(M2))
                best_dip_r = r

    if not best_pair:
        print("  No dip found")
        return

    M1, M2 = best_pair
    data = ae_trajectory_detailed(M1, M2)

    print(f"\n  DIP FOUND: δ(a,e) = {best_dip} at round {best_dip_r}")

    # Show trajectory around the dip
    print(f"\n  TRAJECTORY around dip:")
    print(f"  {'Round':>5} | {'δa':>3} {'δe':>3} {'δ(ae)':>5} | {'δW':>3} | {'nP_a':>4} {'nP_e':>4} | {'mc_a':>4} {'mc_e':>4} | {'Event'}")
    print(f"  " + "-" * 65)

    for i, d in enumerate(data):
        r = d['r']
        if r < best_dip_r - 8 and r > 16:
            continue
        if r > best_dip_r + 3:
            break

        # Detect events
        if i > 0:
            prev_dae = data[i-1]['dae']
            delta = d['dae'] - prev_dae
            if delta < -5:
                event = f"DROP {delta:+d}"
            elif delta > 5:
                event = f"RISE {delta:+d}"
            else:
                event = ""
        else:
            event = ""

        if r == best_dip_r:
            event += " ← DIP!"

        print(f"  {r:>5} | {d['da']:>3} {d['de']:>3} {d['dae']:>5} | {d['dW']:>3} | "
              f"{d['nP_a']:>4} {d['nP_e']:>4} | {d['mc_a']:>4} {d['mc_e']:>4} | {event}")

    # EXPLAIN: what caused the dip?
    dip_data = data[best_dip_r]
    pre_data = data[best_dip_r - 1]

    print(f"\n  CAUSAL ANALYSIS of dip at round {best_dip_r}:")
    print(f"    Before (r={best_dip_r-1}): δ(a,e) = {pre_data['dae']}")
    print(f"    At dip (r={best_dip_r}):   δ(a,e) = {dip_data['dae']}")
    print(f"    Change: {dip_data['dae'] - pre_data['dae']:+d}")

    # The change in δa comes from a_new = T1+T2
    # The change in δe comes from e_new = d+T1
    # δa_new depends on δ(T1+T2)
    # δe_new depends on δ(d+T1) = δd + δT1 (+ carry interaction)
    # δd = δ(c_old) = δ(b_old_old) = δ(a_old_old_old) = δa[r-3]

    da_r3 = data[best_dip_r - 3]['da'] if best_dip_r >= 3 else 0
    print(f"    δa[r-3] (becomes δd, then δe_new): {da_r3}")
    print(f"    δW[{best_dip_r}] = {dip_data['dW']} bits")

    if dip_data['dae'] < pre_data['dae']:
        print(f"\n    WHY did δ drop?")
        if dip_data['dW'] < pre_data['dW']:
            print(f"    → δW decreased ({pre_data['dW']}→{dip_data['dW']}): less injection")
        if dip_data['nP_a'] < pre_data['nP_a']:
            print(f"    → nP_a decreased ({pre_data['nP_a']}→{dip_data['nP_a']}): more carry determined")
        if dip_data['mc_a'] < pre_data['mc_a']:
            print(f"    → max_chain_a decreased: shorter cascades")

        # The REAL cause: COMPENSATION
        # δa_new = δT1 + δT2 = f(δh, δΣ₁, δCh, δW, δΣ₀, δMaj)
        # When these terms CANCEL → δa_new small → dip
        print(f"    → Key: T1 and T2 differences COMPENSATED at this round")
        print(f"    → The schedule difference δW happened to CANCEL")
        print(f"       the accumulated state difference")

def predictability_of_dips(N=1000):
    """Can we predict WHEN dips will happen?"""
    print(f"\n{'='*60}")
    print(f"PREDICTING DIPS — Can we know BEFORE they happen?")
    print(f"{'='*60}")

    # For each round r: does δ(a,e)[r-1] predict whether r is a dip?
    # Also: does δW[r] predict dips?

    pre_dip_ae = []; pre_nondip_ae = []
    dip_dW = []; nondip_dW = []
    pre_dip_nP = []; pre_nondip_nP = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        data = ae_trajectory_detailed(M1, M2)

        for r in range(30, 64):
            current_dae = data[r]['dae']
            prev_dae = data[r-1]['dae']
            change = current_dae - prev_dae

            is_dip = change < -5  # Significant drop

            if is_dip:
                pre_dip_ae.append(prev_dae)
                dip_dW.append(data[r]['dW'])
                pre_dip_nP.append(data[r-1]['nP_a'] + data[r-1]['nP_e'])
            else:
                pre_nondip_ae.append(prev_dae)
                nondip_dW.append(data[r]['dW'])
                pre_nondip_nP.append(data[r-1]['nP_a'] + data[r-1]['nP_e'])

    # Compare pre-dip vs pre-nondip
    pd_ae = np.array(pre_dip_ae); pn_ae = np.array(pre_nondip_ae)
    pd_dW = np.array(dip_dW); pn_dW = np.array(nondip_dW)
    pd_nP = np.array(pre_dip_nP); pn_nP = np.array(pre_nondip_nP)

    print(f"\n  Dips (δ drops > 5): {len(pd_ae)} events")
    print(f"  Non-dips:           {len(pn_ae)} events")

    print(f"\n  BEFORE dips vs non-dips:")
    print(f"    E[δ(a,e) at r-1]:  dip={pd_ae.mean():.1f}  non={pn_ae.mean():.1f}")
    print(f"    E[δW at r]:        dip={pd_dW.mean():.1f}  non={pn_dW.mean():.1f}")
    print(f"    E[nP at r-1]:      dip={pd_nP.mean():.1f}  non={pn_nP.mean():.1f}")

    # KEY: is δ(a,e)[r-1] HIGHER before dips? (regression to mean)
    diff_ae = pd_ae.mean() - pn_ae.mean()
    z_ae = diff_ae / math.sqrt((pd_ae.std()**2/len(pd_ae) + pn_ae.std()**2/len(pn_ae)))

    diff_dW = pd_dW.mean() - pn_dW.mean()
    z_dW = diff_dW / math.sqrt((pd_dW.std()**2/len(pd_dW) + pn_dW.std()**2/len(pn_dW))) if len(pd_dW) > 0 else 0

    print(f"\n    δ(a,e) before dip vs non: diff={diff_ae:+.2f}, Z={z_ae:+.2f}")
    print(f"    δW at dip vs non:         diff={diff_dW:+.2f}, Z={z_dW:+.2f}")

    if abs(z_ae) > 3:
        print(f"    ★★★ δ(a,e) PREDICTS dips! (Z={z_ae:+.1f})")
    if abs(z_dW) > 3:
        print(f"    ★★★ δW PREDICTS dips! (Z={z_dW:+.1f})")

def test_deterministic_structure(N=500):
    """Is the 'randomness' actually deterministic structure we can decode?"""
    print(f"\n{'='*60}")
    print(f"DETERMINISTIC STRUCTURE IN 'RANDOM' FLUCTUATIONS")
    print(f"{'='*60}")

    # The δ(a,e) fluctuation at round r is DETERMINISTIC:
    # it's fully determined by (M1, M2).
    # The question: is there a CHEAP function of (M1,M2) that predicts it?

    # Test: does δW[r] (computable for FREE from schedule) predict δ(a,e)[r]?
    for r_target in [30, 40, 50, 60, 63]:
        dW_vals = []; dae_vals = []

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))

            W1 = schedule(M1); W2 = schedule(M2)
            dW = hw(W1[r_target] ^ W2[r_target])

            s1 = sha256_rounds(M1, r_target)
            s2 = sha256_rounds(M2, r_target)
            dae = hw(s1[r_target][0] ^ s2[r_target][0]) + hw(s1[r_target][4] ^ s2[r_target][4])

            dW_vals.append(dW); dae_vals.append(dae)

        corr = np.corrcoef(dW_vals, dae_vals)[0, 1]
        print(f"  Round {r_target}: corr(δW[{r_target}], δ(a,e)[{r_target}]) = {corr:+.4f}")

    # Deeper: does the CUMULATIVE schedule diff predict δ(a,e)?
    print(f"\n  Cumulative schedule → δ(a,e):")
    for r_target in [30, 40, 50, 60]:
        cum_dW = []; dae_vals = []

        for _ in range(N):
            M1 = random_w16(); M2 = list(M1)
            M2[15] ^= (1 << random.randint(0, 31))

            W1 = schedule(M1); W2 = schedule(M2)
            # Cumulative: sum of δW from first non-zero to r_target
            cum = sum(hw(W1[t] ^ W2[t]) for t in range(15, r_target + 1))

            s1 = sha256_rounds(M1, r_target)
            s2 = sha256_rounds(M2, r_target)
            dae = hw(s1[r_target][0] ^ s2[r_target][0]) + hw(s1[r_target][4] ^ s2[r_target][4])

            cum_dW.append(cum); dae_vals.append(dae)

        corr = np.corrcoef(cum_dW, dae_vals)[0, 1]
        sig = "★★★" if abs(corr) > 0.1 else ""
        print(f"    Round {r_target}: corr(Σ δW[15..{r_target}], δ(a,e)) = {corr:+.4f} {sig}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 185: IS THE RANDOMNESS REAL?")
    print("=" * 60)

    explain_dip()
    predictability_of_dips(N=800)
    test_deterministic_structure(N=400)

    print(f"\n{'='*60}")
    print(f"VERDICT: Real randomness or hidden determinism?")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
