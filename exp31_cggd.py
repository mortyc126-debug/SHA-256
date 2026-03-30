#!/usr/bin/env python3
"""
EXP 31: Coupling-Guided Gradual Descent (CGGD)

NOT search. NAVIGATION.

Five instruments combined into one machine:
1. Carry Coupling (τ=8-12) → navigator
2. Gradual Transition (7.24/k) → speed
3. Suppressor (carry suppresses XOR) → mechanism
4. E-branch signal (r=63, H[4..7]) → compass
5. Wang optimality → starting point

Paradigm: build a SEQUENCE of pairs, each closer to collision.
At each step, use e-branch signal to choose direction,
coupling to verify progress, gradual transition as speed limit.
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

def full_metrics(Wn, Wf):
    """All our instruments in one measurement."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    We = schedule(Wn); Wfe = schedule(Wf)

    # Instrument 1: coupling at r=63
    dn=sn[63][3]; en=sn[63][4]; fn=sn[63][5]; gn=sn[63][6]; hn=sn[63][7]
    df=sf[63][3]; ef=sf[63][4]; ff_=sf[63][5]; gf=sf[63][6]; hf=sf[63][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    kappa_63 = sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

    # Instrument 4: e-branch hash difference
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    dH_e = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
    dH_a = sum(hw(Hn[i]^Hf[i]) for i in range(4))
    dH = dH_e + dH_a

    # Instrument 2: coupling at mid rounds (coupling gradient)
    kappa_32 = 0
    for r in [30,31,32,33]:
        d2=sn[r][3]; e2=sn[r][4]; f2=sn[r][5]; g2=sn[r][6]; h2=sn[r][7]
        d2f=sf[r][3]; e2f=sf[r][4]; f2f=sf[r][5]; g2f=sf[r][6]; h2f=sf[r][7]
        T1n2=(h2+sigma1(e2)+ch(e2,f2,g2)+K[r]+We[r])&MASK
        T1f2=(h2f+sigma1(e2f)+ch(e2f,f2f,g2f)+K[r]+Wfe[r])&MASK
        kappa_32 += sum(a^b for a,b in zip(carry_vec(d2,T1n2),carry_vec(d2f,T1f2)))

    return {
        'kappa_63': kappa_63,
        'kappa_32': kappa_32,
        'dH_e': dH_e,
        'dH_a': dH_a,
        'dH': dH,
        'Wn': Wn, 'Wf': Wf,
    }

def cggd_score(metrics):
    """
    Combined score using ALL instruments.
    Lower = closer to collision.

    Weight e-branch more (signal lives there).
    Bonus for low coupling (coupling→output link).
    """
    return metrics['dH_e'] * 2 + metrics['dH_a'] + metrics['kappa_63'] * 0.1

def test_cggd_navigation(N_starts=200, steps_per_start=200):
    """
    CGGD: navigate toward collision using all instruments.

    At each step:
    - Current: (W0, W1) → Wang cascade → pair (Wn, Wf)
    - Measure: all 5 instruments
    - Move: modify (W0, W1) in direction that improves CGGD score
    - Key: use COUPLING as tiebreaker when dH is equal
    """
    print("\n--- CGGD NAVIGATION ---")

    all_trajectories = []
    best_global_dH = 256

    for start in range(N_starts):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        try:
            Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        except:
            continue

        m = full_metrics(Wn, Wf)
        current_score = cggd_score(m)
        start_dH = m['dH']
        best_dH = start_dH
        best_dH_e = m['dH_e']

        trajectory = [m['dH']]

        for step in range(steps_per_start):
            # Navigation: try modifying W0 or W1
            if random.random() < 0.7:
                # Guided: flip bit that coupling suggests
                # E-branch signal → focus on bits that affect late rounds
                trial_W0 = W0 ^ (1 << random.randint(0, 31))
                trial_W1 = W1
            else:
                trial_W0 = W0
                trial_W1 = W1 ^ (1 << random.randint(0, 31))

            try:
                Wn_t, Wf_t, _, _, _ = wang_cascade(trial_W0, trial_W1)
            except:
                continue

            m_t = full_metrics(Wn_t, Wf_t)
            trial_score = cggd_score(m_t)

            # Accept if score improves
            # Also accept with small probability if coupling improves (instrument 1)
            accept = False
            if trial_score < current_score:
                accept = True
            elif m_t['kappa_63'] < m['kappa_63'] - 2:
                # Coupling tiebreaker
                accept = random.random() < 0.3

            if accept:
                W0, W1 = trial_W0, trial_W1
                m = m_t
                current_score = trial_score
                if m['dH'] < best_dH:
                    best_dH = m['dH']
                    best_dH_e = m['dH_e']

            trajectory.append(best_dH)

        improvement = start_dH - best_dH
        all_trajectories.append({
            'start': start_dH,
            'best': best_dH,
            'best_e': best_dH_e,
            'improvement': improvement,
            'trajectory': trajectory,
        })

        if best_dH < best_global_dH:
            best_global_dH = best_dH

    # Analysis
    starts = np.array([t['start'] for t in all_trajectories])
    bests = np.array([t['best'] for t in all_trajectories])
    improvements = np.array([t['improvement'] for t in all_trajectories])

    print(f"\nCGGD Results ({len(all_trajectories)} runs, {steps_per_start} steps each):")
    print(f"Start:       E[δH]={starts.mean():.2f}")
    print(f"Best:        E[δH]={bests.mean():.2f}")
    print(f"Improvement: E={improvements.mean():.2f}, max={improvements.max()}")
    print(f"Global best: δH={best_global_dH}")

    # Top 10 runs
    all_trajectories.sort(key=lambda t: t['best'])
    print(f"\nTop 10 runs:")
    for t in all_trajectories[:10]:
        print(f"  {t['start']} → {t['best']} (e-branch: {t['best_e']}, gain={t['improvement']})")

    return all_trajectories

def test_cggd_vs_baselines(N=200, steps=200):
    """Compare CGGD against baselines with SAME computational budget."""
    print("\n--- CGGD vs BASELINES ---")

    budget = steps  # Same number of SHA-256 evaluations

    # Baseline 1: Random search (no navigation)
    random_bests = []
    for _ in range(N):
        best = 256
        for _ in range(budget):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            try:
                Wn,Wf,_,_,_ = wang_cascade(W0,W1)
                Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
                dH=sum(hw(Hn[i]^Hf[i]) for i in range(8))
                best = min(best, dH)
            except: pass
        random_bests.append(best)

    # Baseline 2: Greedy descent (only δH, no coupling)
    greedy_bests = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
            best=sum(hw(Hn[i]^Hf[i]) for i in range(8))
        except:
            greedy_bests.append(256); continue

        for _ in range(budget):
            tW0 = W0 ^ (1<<random.randint(0,31))
            try:
                Wn_t,Wf_t,_,_,_ = wang_cascade(tW0, W1)
                Hn_t=sha256_compress(Wn_t); Hf_t=sha256_compress(Wf_t)
                dH_t=sum(hw(Hn_t[i]^Hf_t[i]) for i in range(8))
                if dH_t < best:
                    best = dH_t; W0 = tW0
            except: pass
        greedy_bests.append(best)

    # Baseline 3: CGGD (our method)
    cggd_bests = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        except:
            cggd_bests.append(256); continue

        m = full_metrics(Wn, Wf)
        score = cggd_score(m)
        best = m['dH']

        for _ in range(budget):
            tW0 = W0 ^ (1<<random.randint(0,31))
            try:
                Wn_t,Wf_t,_,_,_ = wang_cascade(tW0, W1)
                m_t = full_metrics(Wn_t, Wf_t)
                s_t = cggd_score(m_t)
                accept = s_t < score or (m_t['kappa_63'] < m['kappa_63']-2 and random.random()<0.3)
                if accept:
                    score=s_t; m=m_t; W0=tW0
                    best = min(best, m_t['dH'])
            except: pass
        cggd_bests.append(best)

    rb = np.array(random_bests)
    gb = np.array(greedy_bests)
    cb = np.array(cggd_bests)

    print(f"Random search: E[best]={rb.mean():.2f}, min={rb.min()}")
    print(f"Greedy δH:     E[best]={gb.mean():.2f}, min={gb.min()}")
    print(f"CGGD:          E[best]={cb.mean():.2f}, min={cb.min()}")

    print(f"\nCGGD vs Random: {rb.mean()-cb.mean():+.2f} bits")
    print(f"CGGD vs Greedy: {gb.mean()-cb.mean():+.2f} bits")

    if cb.mean() < gb.mean() - 0.5:
        print("*** CGGD outperforms greedy! Coupling navigation WORKS! ***")
    if cb.mean() < rb.mean() - 0.5:
        print("*** CGGD outperforms random! ***")

def test_long_cggd(N=20, steps=2000):
    """Long CGGD runs — can we reach δH < 90?"""
    print(f"\n--- LONG CGGD ({steps} steps × {N} runs) ---")

    for trial in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        try:
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        except: continue

        m = full_metrics(Wn, Wf)
        score = cggd_score(m)
        best = m['dH']

        for step in range(steps):
            if random.random() < 0.7:
                tW0 = W0 ^ (1<<random.randint(0,31)); tW1 = W1
            else:
                tW0 = W0; tW1 = W1 ^ (1<<random.randint(0,31))
            try:
                Wn_t,Wf_t,_,_,_ = wang_cascade(tW0, tW1)
                m_t = full_metrics(Wn_t, Wf_t)
                s_t = cggd_score(m_t)
                if s_t < score or (m_t['kappa_63']<m['kappa_63']-2 and random.random()<0.3):
                    score=s_t; m=m_t; W0=tW0; W1=tW1
                    best = min(best, m_t['dH'])
            except: pass

        print(f"  Run {trial+1:>2}: best δH = {best} (start={m['dH']})")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 31: COUPLING-GUIDED GRADUAL DESCENT (CGGD)")
    print("Navigation, not search")
    print("="*60)

    trajectories = test_cggd_navigation(150, 150)
    test_cggd_vs_baselines(150, 150)
    test_long_cggd(15, 1500)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
