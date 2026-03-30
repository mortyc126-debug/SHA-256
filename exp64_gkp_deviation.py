#!/usr/bin/env python3
"""
EXP 64: GKP Deviation — Bifurcation in Carry Equilibrium

GKP = 25:25:50 is AVERAGE. But for SPECIFIC messages,
GKP can deviate (because Σ0 creates correlated bits).

If GKP deviation is LARGE for some messages:
  → carry ≠ 50% → GF(2) structure partially survives
  → potential exploitation

Questions:
1. How much does GKP deviate per-message? (distribution)
2. Does deviation correlate with δH?
3. Can we CONSTRUCT messages with extreme GKP?
4. At extreme GKP: does carry barrier weaken?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def measure_gkp_per_message(W16):
    """Measure GKP distribution across all additions for one message."""
    states = sha256_rounds(W16, 64)
    W = schedule(W16)
    total_g=0; total_k=0; total_p=0

    per_round_gkp = []

    for r in range(64):
        a,b,c,d,e,f,g_reg,h = states[r]
        sig1_e=sigma1(e); ch_val=ch(e,f,g_reg)
        sig0_a=sigma0(a); maj_val=maj(a,b,c)
        s1=(h+sig1_e)&MASK; s2=(s1+ch_val)&MASK
        s3=(s2+K[r])&MASK; T1=(s3+W[r])&MASK
        T2=(sig0_a+maj_val)&MASK

        additions = [(h,sig1_e),(s1,ch_val),(s2,K[r]),(s3,W[r]),
                     (sig0_a,maj_val),(T1,T2),(d,T1)]

        round_g=0; round_k=0; round_p=0
        for x,y in additions:
            gkp = carry_gkp_classification(x,y)
            round_g += gkp.count('G')
            round_k += gkp.count('K')
            round_p += gkp.count('P')

        total_g += round_g; total_k += round_k; total_p += round_p
        total_round = round_g+round_k+round_p
        per_round_gkp.append((round_g/total_round, round_k/total_round, round_p/total_round))

    total = total_g+total_k+total_p
    return {
        'g_frac': total_g/total,
        'k_frac': total_k/total,
        'p_frac': total_p/total,
        'per_round': per_round_gkp,
        'total_g': total_g,
        'total_k': total_k,
    }

def test_gkp_distribution(N=2000):
    """Measure GKP deviation across random messages."""
    print("\n--- GKP DEVIATION DISTRIBUTION ---")

    g_fracs=[]; k_fracs=[]; p_fracs=[]
    for _ in range(N):
        W16 = random_w16()
        gkp = measure_gkp_per_message(W16)
        g_fracs.append(gkp['g_frac'])
        k_fracs.append(gkp['k_frac'])
        p_fracs.append(gkp['p_frac'])

    ga=np.array(g_fracs); ka=np.array(k_fracs); pa=np.array(p_fracs)

    print(f"G fraction: mean={ga.mean():.6f}, std={ga.std():.6f}, "
          f"range=[{ga.min():.6f}, {ga.max():.6f}]")
    print(f"K fraction: mean={ka.mean():.6f}, std={ka.std():.6f}, "
          f"range=[{ka.min():.6f}, {ka.max():.6f}]")
    print(f"P fraction: mean={pa.mean():.6f}, std={pa.std():.6f}, "
          f"range=[{pa.min():.6f}, {pa.max():.6f}]")

    print(f"\nExpected: G=0.25, K=0.25, P=0.50")
    print(f"Deviation G: ±{ga.std()*100:.2f}%")
    print(f"Deviation K: ±{ka.std()*100:.2f}%")

    # Is deviation larger than expected from binomial?
    n_bits = 7*32*64  # total GKP classifications
    expected_std_g = np.sqrt(0.25*0.75/n_bits)
    print(f"\nBinomial expected std(G): {expected_std_g:.6f}")
    print(f"Actual std(G): {ga.std():.6f}")
    print(f"Ratio: {ga.std()/expected_std_g:.2f}×")

    if ga.std() > 2 * expected_std_g:
        print("*** GKP deviation EXCEEDS binomial — bits NOT independent! ***")

    return ga, ka

def test_gkp_vs_dH(N=3000):
    """Does GKP deviation correlate with collision difficulty?"""
    print(f"\n--- GKP → δH CORRELATION ---")

    g_list=[]; k_list=[]; dH_list=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)

        # GKP of normal message
        Wn = [W0,W1]+[0]*14
        gkp = measure_gkp_per_message(Wn)
        g_list.append(gkp['g_frac'])
        k_list.append(gkp['k_frac'])

        # Wang δH
        Wn_w,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn_w); Hf=sha256_compress(Wf)
        dH_list.append(sum(hw(Hn[i]^Hf[i]) for i in range(8)))

    ga=np.array(g_list); ka=np.array(k_list); dh=np.array(dH_list)
    threshold = 3/np.sqrt(N)

    cg = np.corrcoef(ga,dh)[0,1]
    ck = np.corrcoef(ka,dh)[0,1]
    cg_k = np.corrcoef(ga-ka, dh)[0,1]  # G-K imbalance

    print(f"corr(G_frac, δH) = {cg:+.6f} {'***' if abs(cg)>threshold else ''}")
    print(f"corr(K_frac, δH) = {ck:+.6f} {'***' if abs(ck)>threshold else ''}")
    print(f"corr(G-K imbalance, δH) = {cg_k:+.6f} {'***' if abs(cg_k)>threshold else ''}")

    # Quartile analysis
    gk_imbalance = ga - ka
    high_g = dh[gk_imbalance > np.percentile(gk_imbalance, 75)]
    low_g = dh[gk_imbalance < np.percentile(gk_imbalance, 25)]
    print(f"\nHigh G (G>K): E[δH]={high_g.mean():.4f}")
    print(f"Low G (K>G):  E[δH]={low_g.mean():.4f}")

def test_extreme_gkp_construction(N=1000):
    """Can we CONSTRUCT messages with extreme GKP?"""
    print(f"\n--- EXTREME GKP CONSTRUCTION ---")

    # Hill-climb: maximize G fraction
    best_g = 0; best_W = None

    for trial in range(N):
        W16 = random_w16()
        gkp = measure_gkp_per_message(W16)
        if gkp['g_frac'] > best_g:
            best_g = gkp['g_frac']
            best_W = list(W16)

    print(f"Random search best G: {best_g:.6f} (from {N} messages)")

    # Hill-climb from best
    current_W = list(best_W); current_g = best_g
    for step in range(500):
        w=random.randint(0,15); b=random.randint(0,31)
        trial_W = list(current_W); trial_W[w] ^= (1<<b)
        gkp = measure_gkp_per_message(trial_W)
        if gkp['g_frac'] > current_g:
            current_g = gkp['g_frac']; current_W = trial_W

    print(f"After hill-climb: G = {current_g:.6f}")
    gkp_final = measure_gkp_per_message(current_W)
    print(f"  G={gkp_final['g_frac']:.4f}, K={gkp_final['k_frac']:.4f}, P={gkp_final['p_frac']:.4f}")

    # Test collision for extreme-G message
    try:
        Wn_w,Wf,_,_,_ = wang_cascade(current_W[0], current_W[1])
        Hn=sha256_compress(Wn_w); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        print(f"  Extreme-G δH = {dH}")
    except:
        print(f"  Wang cascade failed for extreme-G message")

    # Also: minimize G (maximize K → more carry killing)
    best_k = 0; best_W_k = None
    for _ in range(N):
        W16 = random_w16()
        gkp = measure_gkp_per_message(W16)
        if gkp['k_frac'] > best_k:
            best_k = gkp['k_frac']; best_W_k = list(W16)

    for step in range(500):
        w=random.randint(0,15); b=random.randint(0,31)
        trial_W = list(best_W_k); trial_W[w] ^= (1<<b)
        gkp = measure_gkp_per_message(trial_W)
        if gkp['k_frac'] > best_k:
            best_k = gkp['k_frac']; best_W_k = trial_W

    print(f"\nExtreme K after hill-climb: K = {best_k:.6f}")
    gkp_k = measure_gkp_per_message(best_W_k)
    print(f"  G={gkp_k['g_frac']:.4f}, K={gkp_k['k_frac']:.4f}, P={gkp_k['p_frac']:.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 64: GKP DEVIATION — BIFURCATION?")
    print("="*60)
    test_gkp_distribution(1500)
    test_gkp_vs_dH(2000)
    test_extreme_gkp_construction(800)

if __name__ == "__main__":
    main()
