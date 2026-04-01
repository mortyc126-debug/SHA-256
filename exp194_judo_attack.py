#!/usr/bin/env python3
"""
EXP 194: JUDO ATTACK — Use SHA-256's self-correction against itself

MECHANISM:
  When δa AND δe are BOTH high → δa×δe is large
  → noise = -0.042 × δa×δe (from exp188)
  → δ drops STRONGLY next round

  δa=20, δe=20 → δa×δe=400 → noise≈-16.8 → massive drop!
  vs δa=16, δe=16 → δa×δe=256 → noise≈-10.8 → normal drop

JUDO: Force BALANCED high δ → trigger MAXIMUM self-correction
Step 1: Understand when δa×δe is naturally highest
Step 2: Find δM that creates balanced high δ
Step 3: Chain corrections toward collision
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def extended_ae_data(M1, M2, max_r=64):
    """Collect full (da, de, dae) trajectory."""
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)
    data = []
    for r in range(max_r + 1):
        da = hw(s1[r][0] ^ s2[r][0])
        de = hw(s1[r][4] ^ s2[r][4])
        data.append({'r': r, 'da': da, 'de': de, 'dae': da+de, 'daxde': da*de})
    return data

def step1_understand_mechanism(N=500):
    """When is δa×δe naturally highest? And what follows?"""
    print(f"\n{'='*60}")
    print(f"STEP 1: Understand δa×δe mechanism")
    print(f"{'='*60}")

    # Collect: when δa×δe is high, what happens NEXT round?
    high_balanced = []   # δa>20 AND δe>20 (balanced high)
    high_unbalanced = [] # δa>25 AND δe<12 OR vice versa
    normal = []          # 14<δa<18 AND 14<δe<18

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))
        data = extended_ae_data(M1, M2)

        for i in range(30, 63):
            d = data[i]; d_next = data[i+1]
            da = d['da']; de = d['de']
            change = d_next['dae'] - d['dae']

            if da > 20 and de > 20:
                high_balanced.append({'daxde': da*de, 'change': change,
                                     'da': da, 'de': de, 'dae_next': d_next['dae']})
            elif (da > 25 and de < 12) or (de > 25 and da < 12):
                high_unbalanced.append({'daxde': da*de, 'change': change,
                                       'da': da, 'de': de, 'dae_next': d_next['dae']})
            elif 14 < da < 18 and 14 < de < 18:
                normal.append({'daxde': da*de, 'change': change,
                              'da': da, 'de': de, 'dae_next': d_next['dae']})

    print(f"\n  HIGH BALANCED (δa>20 AND δe>20): N={len(high_balanced)}")
    if high_balanced:
        hb = high_balanced
        print(f"    E[δa×δe] = {np.mean([h['daxde'] for h in hb]):.0f}")
        print(f"    E[change] = {np.mean([h['change'] for h in hb]):+.1f}")
        print(f"    E[δ_next] = {np.mean([h['dae_next'] for h in hb]):.1f}")

    print(f"\n  HIGH UNBALANCED (one>25, other<12): N={len(high_unbalanced)}")
    if high_unbalanced:
        hu = high_unbalanced
        print(f"    E[δa×δe] = {np.mean([h['daxde'] for h in hu]):.0f}")
        print(f"    E[change] = {np.mean([h['change'] for h in hu]):+.1f}")
        print(f"    E[δ_next] = {np.mean([h['dae_next'] for h in hu]):.1f}")

    print(f"\n  NORMAL (14<δa,δe<18): N={len(normal)}")
    if normal:
        nm = normal
        print(f"    E[δa×δe] = {np.mean([h['daxde'] for h in nm]):.0f}")
        print(f"    E[change] = {np.mean([h['change'] for h in nm]):+.1f}")
        print(f"    E[δ_next] = {np.mean([h['dae_next'] for h in nm]):.1f}")

    # KEY: does BALANCED drop MORE than expected from thermostat?
    if high_balanced:
        avg_dae = np.mean([h['da']+h['de'] for h in hb])
        thermostat_pred = 0.69 * avg_dae + 9.92
        actual = np.mean([h['dae_next'] for h in hb])
        excess_drop = thermostat_pred - actual

        print(f"\n  JUDO EFFECT:")
        print(f"    Thermostat predicts δ_next = {thermostat_pred:.1f}")
        print(f"    Actual δ_next = {actual:.1f}")
        print(f"    EXCESS DROP (judo force) = {excess_drop:+.1f} bits")

        if excess_drop > 2:
            print(f"    ★★★ BALANCED HIGH triggers {excess_drop:.1f} bits EXTRA correction!")

def step2_find_balanced_dM(N=500):
    """Find δM that creates BALANCED high δa AND δe."""
    print(f"\n{'='*60}")
    print(f"STEP 2: Find δM creating balanced high δ")
    print(f"{'='*60}")

    # For various δM: measure balance at round 30
    results = []

    patterns = [
        ("W[15]b31", lambda M: (list(M[:15]) + [M[15]^(1<<31)])),
        ("W[14]+W[15]", lambda M: M[:14] + [(M[14]+1)&MASK, (M[15]+1)&MASK]),
        ("W[0]+W[15]", lambda M: [(M[0]+1)&MASK]+M[1:15]+[(M[15]+1)&MASK]),
        ("W[8]+W[15]", lambda M: M[:8]+[(M[8]+1)&MASK]+M[9:15]+[(M[15]+1)&MASK]),
        ("Random 2-bit", lambda M: [M[w]^(1<<random.randint(0,31)) if w in [random.randint(0,15), random.randint(0,15)] else M[w] for w in range(16)]),
    ]

    for name, make_M2 in patterns:
        balances = []; da_vals = []; de_vals = []; products = []

        for _ in range(N):
            M1 = random_w16()
            M2 = make_M2(list(M1))
            if M1 == M2: continue

            s1 = sha256_rounds(M1, 35); s2 = sha256_rounds(M2, 35)

            # Measure at rounds 25, 30, 35
            for r in [25, 30, 35]:
                da = hw(s1[r][0] ^ s2[r][0])
                de = hw(s1[r][4] ^ s2[r][4])
                balance = 1.0 - abs(da - de) / max(da + de, 1)  # 1=perfect balance
                balances.append(balance)
                da_vals.append(da)
                de_vals.append(de)
                products.append(da * de)

        avg_bal = np.mean(balances)
        avg_prod = np.mean(products)
        avg_da = np.mean(da_vals); avg_de = np.mean(de_vals)

        print(f"\n  {name}:")
        print(f"    E[δa]={avg_da:.1f}, E[δe]={avg_de:.1f}")
        print(f"    E[δa×δe]={avg_prod:.0f}, E[balance]={avg_bal:.3f}")

def step3_judo_chain(N=20, budget=3000):
    """Attempt judo chain: trigger balanced high → self-correct → repeat."""
    print(f"\n{'='*60}")
    print(f"STEP 3: JUDO CHAIN ATTACK (N={N})")
    print(f"{'='*60}")

    # Strategy: generate many message pairs.
    # For each: compute trajectory. Find pairs where δ DROPS
    # due to high δa×δe at some round → measure if they end
    # up closer to collision at round 64.

    judo_pairs = []   # Pairs with δa×δe dip
    normal_pairs = [] # Regular pairs

    for _ in range(budget):
        M1 = random_w16(); M2 = list(M1)
        M2[15] ^= (1 << random.randint(0, 31))

        data = extended_ae_data(M1, M2)

        # Find: did any round 30-60 have a judo dip?
        # (δ_next < δ-10 AND δa*δe > 400)
        had_judo = False
        min_dae_after_judo = 64

        for i in range(30, 60):
            d = data[i]
            if d['daxde'] > 400 and data[i+1]['dae'] < d['dae'] - 8:
                had_judo = True
                # Track minimum δ after judo event through round 64
                for j in range(i+1, min(i+10, 65)):
                    min_dae_after_judo = min(min_dae_after_judo, data[j]['dae'])
                break

        H1 = sha256_compress(M1); H2 = sha256_compress(M2)
        dH = sum(hw(H1[w] ^ H2[w]) for w in range(8))

        if had_judo:
            judo_pairs.append({'dH': dH, 'min_after': min_dae_after_judo})
        else:
            normal_pairs.append({'dH': dH})

    if judo_pairs:
        jh = np.array([p['dH'] for p in judo_pairs])
        ja = np.array([p['min_after'] for p in judo_pairs])
    else:
        jh = np.array([256]); ja = np.array([64])

    nh = np.array([p['dH'] for p in normal_pairs])

    print(f"\n  Judo pairs (δa×δe>400 triggered drop): {len(judo_pairs)}")
    print(f"  Normal pairs: {len(normal_pairs)}")

    if len(judo_pairs) > 5:
        print(f"\n  JUDO pairs:")
        print(f"    E[dH_hash] = {jh.mean():.1f}")
        print(f"    E[min δ(a,e) after judo] = {ja.mean():.1f}")
        print(f"    min(dH_hash) = {jh.min()}")

    print(f"\n  NORMAL pairs:")
    print(f"    E[dH_hash] = {nh.mean():.1f}")
    print(f"    min(dH_hash) = {nh.min()}")

    if len(judo_pairs) > 5:
        gain = nh.mean() - jh.mean()
        print(f"\n  JUDO GAIN: {gain:+.1f} bits")
        if gain > 2:
            print(f"  ★★★ JUDO WORKS! Balanced high δa×δe → better hash collision!")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 194: JUDO ATTACK — δa×δe SELF-CORRECTION")
    print("=" * 60)

    step1_understand_mechanism(N=400)
    step2_find_balanced_dM(N=300)
    step3_judo_chain(N=15, budget=5000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Step 1 of bottom-up attack")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
