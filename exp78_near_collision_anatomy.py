#!/usr/bin/env python3
"""
EXP 78: Near-Collision Anatomy — What Makes Best Pairs Special?

We found pairs with δH=90-95. These are CLOSEST to collision.
What SPECIFIC properties do they have that average pairs don't?

Not statistics. CONCRETE properties of CONCRETE best pairs.
Like a surgeon examining the patient, not reading population studies.

Collect top-100 near-collision pairs.
For EACH: measure EVERYTHING we know.
Find: what do they SHARE that random pairs don't?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def xor_compress(W16, iv=None):
    if iv is None: iv=list(IV)
    W=list(W16)+[0]*48
    for t in range(16,64): W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r]; T2=sigma0(a)^maj(a,b,c)
        s=[T1^T2,a,b,c,d^T1,e,f,g]
    return [iv[i]^s[i] for i in range(8)]

def carry_vec(a,b):
    c_out=[]; c=0
    for i in range(32):
        s=((a>>i)&1)+((b>>i)&1)+c; c=1 if s>=2 else 0; c_out.append(c)
    return c_out

def full_profile(Wn, Wf):
    """EVERYTHING we can measure about one pair."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    We = schedule(Wn); Wfe = schedule(Wf)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    Ln = xor_compress(Wn); Lf = xor_compress(Wf)

    dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
    dH_a = sum(hw(Hn[i]^Hf[i]) for i in range(4))
    dH_e = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
    dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
    dC = sum(hw((Hn[i]^Ln[i])^(Hf[i]^Lf[i])) for i in range(8))

    # Carry transparency
    cf = 0
    for w in range(8):
        for bit in range(32):
            sx=(sn[64][w]^sf[64][w]>>bit)&1
            hx=(Hn[w]^Hf[w]>>bit)&1
            if sx==hx: cf+=1

    # Coupling at r=63
    dn=sn[63][3];en=sn[63][4];fn=sn[63][5];gn=sn[63][6];hn_=sn[63][7]
    df=sf[63][3];ef=sf[63][4];ff_=sf[63][5];gf=sf[63][6];hf=sf[63][7]
    T1n=(hn_+sigma1(en)+ch(en,fn,gn)+K[63]+We[63])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[63]+Wfe[63])&MASK
    kappa = sum(a^b for a,b in zip(carry_vec(dn,T1n),carry_vec(df,T1f)))

    # State distance at Wang barrier
    d17 = sum(hw(sn[17][i]^sf[17][i]) for i in range(8))

    # Schedule difference
    sched_diff = sum(hw((Wfe[t]-We[t])&MASK) for t in range(16,64))

    # Per-word hash diff
    per_word = [hw(Hn[i]^Hf[i]) for i in range(8)]

    # Which bits differ? (bitmap)
    diff_bits = []
    for w in range(8):
        d = Hn[w] ^ Hf[w]
        for b in range(32):
            diff_bits.append((d>>b)&1)

    # Hamming weight of Wn[0], Wn[1]
    hw_w0 = hw(Wn[0])
    hw_w1 = hw(Wn[1])

    return {
        'dH': dH, 'dH_a': dH_a, 'dH_e': dH_e,
        'dL': dL, 'dC': dC, 'carry_free': cf,
        'kappa_63': kappa, 'd17': d17, 'sched_diff': sched_diff,
        'per_word': per_word, 'diff_bits': diff_bits,
        'hw_w0': hw_w0, 'hw_w1': hw_w1,
        'W0': Wn[0], 'W1': Wn[1],
    }

def collect_best_pairs(N=100000, top_k=100):
    """Collect top-k near-collision pairs from N Wang pairs."""
    print(f"\nCollecting {N} Wang pairs, keeping top {top_k}...")

    pairs = []
    for i in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,_,_ = wang_cascade(W0,W1)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH=sum(hw(Hn[j]^Hf[j]) for j in range(8))
        pairs.append((dH, W0, W1, Wn, Wf))

        if i % 20000 == 19999:
            pairs.sort()
            pairs = pairs[:top_k*5]  # Keep buffer

    pairs.sort()
    return pairs[:top_k]

def analyze_best_pairs(best_pairs, random_profiles):
    """Compare best pairs against random baseline."""
    print(f"\n--- NEAR-COLLISION ANATOMY ---")

    best_profiles = []
    for dH, W0, W1, Wn, Wf in best_pairs[:50]:
        p = full_profile(Wn, Wf)
        best_profiles.append(p)

    # Compare every measured property
    metrics = ['dH', 'dH_a', 'dH_e', 'dL', 'dC', 'carry_free',
               'kappa_63', 'd17', 'sched_diff', 'hw_w0', 'hw_w1']

    print(f"{'Metric':>15} | {'Best mean':>10} | {'Random mean':>11} | {'Diff':>8} | {'Z-score':>8}")
    print("-"*65)

    signals = []
    for m in metrics:
        best_vals = np.array([p[m] for p in best_profiles])
        rand_vals = np.array([p[m] for p in random_profiles])

        diff = best_vals.mean() - rand_vals.mean()
        z = diff / (rand_vals.std() / np.sqrt(len(best_vals))) if rand_vals.std()>0 else 0

        sig = "***" if abs(z) > 3 else ""
        print(f"{m:>15} | {best_vals.mean():>10.2f} | {rand_vals.mean():>11.2f} | "
              f"{diff:>+8.2f} | {z:>+8.2f} {sig}")

        if abs(z) > 3:
            signals.append((m, diff, z))

    # Per-word analysis
    print(f"\nPer-word δH:")
    for w in range(8):
        best_w = np.array([p['per_word'][w] for p in best_profiles])
        rand_w = np.array([p['per_word'][w] for p in random_profiles])
        branch = "a" if w < 4 else "e"
        diff = best_w.mean() - rand_w.mean()
        print(f"  H[{w}]({branch}): best={best_w.mean():.2f}, random={rand_w.mean():.2f}, "
              f"diff={diff:+.2f}")

    # Which OUTPUT BITS are most often 0 (matching) in best pairs?
    print(f"\nOutput bits most often MATCHING in best pairs:")
    bit_match_rate_best = np.zeros(256)
    bit_match_rate_rand = np.zeros(256)

    for p in best_profiles:
        for i in range(256):
            if p['diff_bits'][i] == 0:
                bit_match_rate_best[i] += 1

    for p in random_profiles:
        for i in range(256):
            if p['diff_bits'][i] == 0:
                bit_match_rate_rand[i] += 1

    bit_match_rate_best /= len(best_profiles)
    bit_match_rate_rand /= len(random_profiles)

    # Find bits where best >> random
    advantage = bit_match_rate_best - bit_match_rate_rand
    top_bits = np.argsort(-advantage)[:15]

    print(f"  Top 15 bits (best match rate - random match rate):")
    for idx in top_bits:
        w = idx // 32; b = idx % 32
        branch = "a" if w < 4 else "e"
        print(f"    H[{w}]({branch}) bit {b:>2}: best={bit_match_rate_best[idx]:.3f}, "
              f"random={bit_match_rate_rand[idx]:.3f}, advantage={advantage[idx]:+.3f}")

    return signals

def main():
    random.seed(42)
    print("="*60)
    print("EXP 78: NEAR-COLLISION ANATOMY")
    print("What makes best pairs special?")
    print("="*60)

    # Collect best pairs
    best = collect_best_pairs(80000, 100)
    print(f"\nTop 10 near-collisions:")
    for i, (dH, W0, W1, _, _) in enumerate(best[:10]):
        print(f"  #{i+1}: δH={dH}, W0=0x{W0:08x}, W1=0x{W1:08x}")

    # Collect random profiles for baseline
    print(f"\nCollecting random baseline profiles...")
    random_profiles = []
    for _ in range(200):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        random_profiles.append(full_profile(Wn, Wf))

    signals = analyze_best_pairs(best, random_profiles)

    print(f"\n{'='*60}")
    print(f"SIGNIFICANT SIGNALS (Z > 3):")
    for m, diff, z in signals:
        print(f"  {m}: diff={diff:+.2f}, Z={z:+.1f}")

if __name__ == "__main__":
    main()
