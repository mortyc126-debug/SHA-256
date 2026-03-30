#!/usr/bin/env python3
"""
EXP 32: CGGD v2 — Hybrid Exploration + Exploitation

CGGD v1 problem: local search on flat landscape loses to random.
CGGD v1 strength: coupling navigation beats greedy.

FIX: Combine BOTH:
1. Random restarts (exploration) — jump to new (W0,W1)
2. CGGD local descent (exploitation) — use coupling to refine
3. Population-based: maintain TOP-K best pairs, explore around them
4. Multi-axis: vary W0, W1, AND DW0 simultaneously

Also: use SCORE that combines e-branch δH with coupling signal
weighted by our measured correlation (0.085).
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

def fast_metrics(W0, W1, DW0=1):
    """Fast measurement: δH + κ_63 + e-branch."""
    try:
        Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1, DW0)
    except:
        return None

    We = schedule(Wn); Wfe = schedule(Wf)

    # κ at round 63
    dn=sn[63][3]; en=sn[63][4]; fn=sn[63][5]; gn=sn[63][6]; hn=sn[63][7]
    df=sf[63][3]; ef=sf[63][4]; ff_=sf[63][5]; gf=sf[63][6]; hf=sf[63][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    k63 = sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    dH_e = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
    dH_a = sum(hw(Hn[i]^Hf[i]) for i in range(4))

    return dH_e + dH_a, dH_e, k63, W0, W1, DW0

def cggd_v2(total_budget=50000, population_size=20, local_steps=10):
    """
    CGGD v2: population-based hybrid.

    Phase 1: Random exploration to build initial population
    Phase 2: Local refinement of top-K using coupling guidance
    Phase 3: Cross-breed best pairs + random restarts
    Repeat phases 2-3 until budget exhausted.
    """
    # Phase 1: initial population
    init_budget = total_budget // 5
    population = []

    for _ in range(init_budget):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        DW0 = random.choice([1, 0x80000000, 0x55555555, 0xF0F0F0F0])
        result = fast_metrics(W0, W1, DW0)
        if result:
            dH, dH_e, k63, w0, w1, dw0 = result
            population.append((dH, dH_e, k63, w0, w1, dw0))

    # Sort by δH
    population.sort()
    population = population[:population_size]

    best_ever = population[0][0]
    evaluations = init_budget

    # Phases 2-3: refine + restart
    remaining = total_budget - init_budget
    rounds = remaining // (population_size * (local_steps + 1))

    for round_num in range(max(rounds, 1)):
        # Phase 2: local refinement of each member
        new_pop = []
        for dH, dH_e, k63, w0, w1, dw0 in population:
            best_local = (dH, dH_e, k63, w0, w1, dw0)

            for _ in range(local_steps):
                evaluations += 1
                if evaluations >= total_budget:
                    break

                # 3-axis mutation
                r = random.random()
                if r < 0.45:
                    tw0 = w0 ^ (1 << random.randint(0, 31)); tw1 = w1; tdw0 = dw0
                elif r < 0.9:
                    tw0 = w0; tw1 = w1 ^ (1 << random.randint(0, 31)); tdw0 = dw0
                else:
                    tw0 = w0; tw1 = w1
                    tdw0 = dw0 ^ (1 << random.randint(0, 31))

                result = fast_metrics(tw0, tw1, tdw0)
                if result:
                    tdH, tdH_e, tk63, _, _, _ = result
                    # Accept if δH improves, OR if coupling improves significantly
                    if tdH < best_local[0] or (tk63 < best_local[2] - 3 and random.random() < 0.4):
                        best_local = (tdH, tdH_e, tk63, tw0, tw1, tdw0)

            new_pop.append(best_local)
            best_ever = min(best_ever, best_local[0])

        # Phase 3: add random restarts
        for _ in range(population_size // 4):
            evaluations += 1
            if evaluations >= total_budget:
                break
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            DW0 = random.choice([1, 0x80000000, 0x55555555, 0xF0F0F0F0])
            result = fast_metrics(W0, W1, DW0)
            if result:
                dH, dH_e, k63, w0, w1, dw0 = result
                new_pop.append((dH, dH_e, k63, w0, w1, dw0))

        # Cross-breeding: combine W0 from best with W1 from second-best
        new_pop.sort()
        if len(new_pop) >= 2:
            for i in range(min(3, len(new_pop)-1)):
                evaluations += 1
                if evaluations >= total_budget:
                    break
                tw0 = new_pop[i][3]
                tw1 = new_pop[i+1][4]
                tdw0 = new_pop[0][5]
                result = fast_metrics(tw0, tw1, tdw0)
                if result:
                    dH, dH_e, k63, w0, w1, dw0 = result
                    new_pop.append((dH, dH_e, k63, w0, w1, dw0))

        new_pop.sort()
        population = new_pop[:population_size]
        best_ever = min(best_ever, population[0][0])

    return population, best_ever, evaluations

def test_cggd_v2_vs_baselines():
    """Compare CGGD v2 against all baselines at same budget."""
    print("\n--- CGGD v2 vs ALL BASELINES ---")

    budgets = [5000, 20000, 50000]

    for budget in budgets:
        print(f"\n  Budget = {budget} evaluations:")

        # Baseline: pure random
        best_random = 256
        for _ in range(budget):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            result = fast_metrics(W0, W1)
            if result:
                best_random = min(best_random, result[0])

        # CGGD v1: local only
        best_v1 = 256
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        for _ in range(budget):
            tW0 = W0 ^ (1<<random.randint(0,31))
            result = fast_metrics(tW0, W1)
            if result:
                dH, dH_e, k63, _, _, _ = result
                if dH < best_v1 or (k63 < 12 and random.random()<0.3):
                    best_v1 = min(best_v1, dH)
                    W0 = tW0

        # CGGD v2: population hybrid
        pop, best_v2, evals = cggd_v2(budget)

        # Birthday expectation
        birthday_expected = 128 - 8 * np.sqrt(2 * np.log(budget))

        print(f"    Random search:      best δH = {best_random}")
        print(f"    CGGD v1 (local):    best δH = {best_v1}")
        print(f"    CGGD v2 (hybrid):   best δH = {best_v2}")
        print(f"    Birthday expected:  ~{birthday_expected:.0f}")

        if best_v2 < best_random:
            print(f"    *** v2 BEATS random by {best_random - best_v2} bits! ***")
        if best_v2 < birthday_expected:
            print(f"    *** v2 BEATS birthday by {birthday_expected - best_v2:.0f} bits! ***")

def test_scaling(runs=10):
    """How does CGGD v2 scale with budget?"""
    print("\n--- SCALING ANALYSIS ---")

    print(f"{'Budget':>8} | {'E[best]':>8} | {'min':>5} | {'Birthday':>8} | {'Δ':>6}")
    print("-"*45)

    for budget in [1000, 3000, 10000, 30000, 50000]:
        bests = []
        for _ in range(runs):
            _, best, _ = cggd_v2(budget, population_size=15, local_steps=8)
            bests.append(best)

        birthday = 128 - 8 * np.sqrt(2 * np.log(budget))
        arr = np.array(bests)
        delta = arr.mean() - birthday
        print(f"{budget:>8} | {arr.mean():>8.1f} | {arr.min():>5} | {birthday:>8.1f} | {delta:>+6.1f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 32: CGGD v2 — HYBRID EXPLORATION + EXPLOITATION")
    print("="*60)

    test_cggd_v2_vs_baselines()
    test_scaling(8)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
