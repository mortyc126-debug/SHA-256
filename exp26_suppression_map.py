#!/usr/bin/env python3
"""
EXP 26: Carry Suppression Map

T_CARRY_IS_SUPPRESSOR: carry reduces XOR-diffusion by ~7 bits.
WHERE are these 7 bits concentrated?

If concentrated in H[7] (e-branch bridge) → targeted birthday = 2^112.
If spread across H[0..7] → targeted birthday = 2^124.5 (only 3.5 bit gain).

Also: PER-BIT suppression map. Which bits are most suppressed?
And: does suppression pattern depend on the MESSAGE (predictable)?

OUR TOOLS: TLC decomposition per word, coupling-limited comparison,
e-branch bridge from methodology.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def sha256_coupling_limited_per_word(Wn, Wf, k_max):
    """Coupling-limited SHA-256, returns per-word δH."""
    iv = list(IV)
    Wn_e = schedule(Wn); Wf_e = schedule(Wf)
    sn = list(iv); sf = list(iv)
    for r in range(64):
        an,bn,cn,dn,en,fn,gn,hn = sn
        af,bf,cf,df,ef,ff_,gf,hf = sf
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK
        T2n=(sigma0(an)+maj(an,bn,cn))&MASK
        T2f=(sigma0(af)+maj(af,bf,cf))&MASK
        e_new_n=(dn+T1n)&MASK; e_new_f=(df+T1f)&MASK
        a_new_n=(T1n+T2n)&MASK; a_new_f=(T1f+T2f)&MASK
        diff_e=e_new_n^e_new_f
        if hw(diff_e)>k_max:
            m=0;c=0
            for i in range(32):
                if (diff_e>>i)&1:
                    if c<k_max: m|=(1<<i); c+=1
            e_new_f=e_new_n^(diff_e&m)
        diff_a=a_new_n^a_new_f
        if hw(diff_a)>k_max:
            m=0;c=0
            for i in range(32):
                if (diff_a>>i)&1:
                    if c<k_max: m|=(1<<i); c+=1
            a_new_f=a_new_n^(diff_a&m)
        sn=[a_new_n,an,bn,cn,e_new_n,en,fn,gn]
        sf=[a_new_f,af,bf,cf,e_new_f,ef,ff_,gf]
    Hn=[(iv[i]+sn[i])&MASK for i in range(8)]
    Hf=[(iv[i]+sf[i])&MASK for i in range(8)]
    per_word = [hw(Hn[i]^Hf[i]) for i in range(8)]
    return per_word

def test_per_word_suppression(N=1000):
    """Measure carry suppression per output word H[0..7]."""
    print("\n--- TEST 1: PER-WORD CARRY SUPPRESSION ---")

    # Compare full SHA-256 (k=32) vs coupling-limited (k=4,8,12)
    print(f"{'k_max':>5} | {'H[0]':>6} | {'H[1]':>6} | {'H[2]':>6} | {'H[3]':>6} | "
          f"{'H[4]':>6} | {'H[5]':>6} | {'H[6]':>6} | {'H[7]':>6} | {'Total':>6}")
    print("-"*75)

    for k in [4, 6, 8, 10, 12, 16, 20, 32]:
        per_word_totals = [[] for _ in range(8)]
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            pw = sha256_coupling_limited_per_word(Wn, Wf, k)
            for w in range(8):
                per_word_totals[w].append(pw[w])

        means = [np.mean(per_word_totals[w]) for w in range(8)]
        total = sum(means)
        print(f"{k:>5} | " + " | ".join(f"{m:>6.2f}" for m in means) + f" | {total:>6.2f}")

    # Suppression = full(k=32) - limited(k)
    print(f"\n--- SUPPRESSION = E[δH_word](k=32) - E[δH_word](k) ---")
    # Compute baseline
    baseline = [[] for _ in range(8)]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        pw = sha256_coupling_limited_per_word(Wn, Wf, 32)
        for w in range(8): baseline[w].append(pw[w])
    bl_means = [np.mean(baseline[w]) for w in range(8)]

    print(f"{'k_max':>5} | {'H[0]':>6} | {'H[1]':>6} | {'H[2]':>6} | {'H[3]':>6} | "
          f"{'H[4]':>6} | {'H[5]':>6} | {'H[6]':>6} | {'H[7]':>6} | {'Total':>6}")
    print("-"*75)
    for k in [4, 8, 12]:
        suppression = [[] for _ in range(8)]
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            pw = sha256_coupling_limited_per_word(Wn, Wf, k)
            for w in range(8): suppression[w].append(pw[w])
        supp_means = [bl_means[w] - np.mean(suppression[w]) for w in range(8)]
        total_supp = sum(supp_means)
        print(f"{k:>5} | " + " | ".join(f"{m:>+6.2f}" for m in supp_means) + f" | {total_supp:>+6.2f}")

        # Is suppression concentrated?
        max_supp = max(supp_means)
        max_word = supp_means.index(max_supp)
        concentration = max_supp / total_supp if total_supp > 0 else 0
        print(f"       Max suppression: H[{max_word}] = {max_supp:.2f} ({concentration*100:.1f}% of total)")

def test_per_bit_suppression(N=1500):
    """Per-bit analysis: which bits of which words are most suppressed?"""
    print("\n--- TEST 2: PER-BIT SUPPRESSION MAP ---")

    # Full SHA-256 per-bit flip probability
    full_bits = np.zeros((8, 32))
    limited_bits = np.zeros((8, 32))

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        # Full
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        for w in range(8):
            d = Hn[w] ^ Hf[w]
            for b in range(32):
                full_bits[w][b] += (d >> b) & 1

        # Limited (k=8)
        pw = sha256_coupling_limited_per_word(Wn, Wf, 8)
        iv = list(IV)
        Wn_e=schedule(Wn); Wf_e=schedule(Wf)
        sn=list(iv); sf=list(iv)
        for r in range(64):
            an,bn,cn,dn,en,fn,gn,hn_=sn
            af,bf,cf,df,ef,ff_,gf,hf=sf
            T1n=(hn_+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
            T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK
            T2n=(sigma0(an)+maj(an,bn,cn))&MASK
            T2f=(sigma0(af)+maj(af,bf,cf))&MASK
            e_new_n=(dn+T1n)&MASK; e_new_f=(df+T1f)&MASK
            a_new_n=(T1n+T2n)&MASK; a_new_f=(T1f+T2f)&MASK
            diff_e=e_new_n^e_new_f
            if hw(diff_e)>8:
                m=0;c=0
                for i in range(32):
                    if (diff_e>>i)&1:
                        if c<8: m|=(1<<i); c+=1
                e_new_f=e_new_n^(diff_e&m)
            diff_a=a_new_n^a_new_f
            if hw(diff_a)>8:
                m=0;c=0
                for i in range(32):
                    if (diff_a>>i)&1:
                        if c<8: m|=(1<<i); c+=1
                a_new_f=a_new_n^(diff_a&m)
            sn=[a_new_n,an,bn,cn,e_new_n,en,fn,gn]
            sf=[a_new_f,af,bf,cf,e_new_f,ef,ff_,gf]
        Hn_l=[(iv[i]+sn[i])&MASK for i in range(8)]
        Hf_l=[(iv[i]+sf[i])&MASK for i in range(8)]
        for w in range(8):
            d = Hn_l[w] ^ Hf_l[w]
            for b in range(32):
                limited_bits[w][b] += (d >> b) & 1

    full_bits /= N; limited_bits /= N

    # Suppression per bit
    supp = full_bits - limited_bits

    # Find most suppressed bits
    print(f"Most suppressed bits (k=8 vs k=32):")
    flat_supp = [(supp[w][b], w, b) for w in range(8) for b in range(32)]
    flat_supp.sort(reverse=True)
    for val, w, b in flat_supp[:15]:
        print(f"  H[{w}] bit {b:>2}: suppression = {val:+.4f} (full={full_bits[w][b]:.4f})")

    # Per-word summary
    print(f"\nPer-word total suppression:")
    for w in range(8):
        branch = "a-branch" if w < 4 else "e-branch"
        word_supp = np.sum(supp[w])
        max_bit = np.argmax(np.abs(supp[w]))
        print(f"  H[{w}] ({branch}): total={word_supp:+.2f}, max bit={max_bit} ({supp[w][max_bit]:+.4f})")

def test_additive_vs_xor(N=2000):
    """Compare additive difference ΔH vs XOR difference δH."""
    print("\n--- TEST 3: ADDITIVE vs XOR DIFFERENCE ---")

    add_per_word = [[] for _ in range(8)]
    xor_per_word = [[] for _ in range(8)]

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        for w in range(8):
            add_diff = min((Hn[w]-Hf[w])&MASK, (Hf[w]-Hn[w])&MASK)
            xor_diff = Hn[w] ^ Hf[w]
            add_per_word[w].append(add_diff)
            xor_per_word[w].append(hw(xor_diff))

    # Is additive difference more structured than XOR?
    print(f"{'Word':>6} | {'E[HW(XOR)]':>11} | {'E[ADD]/2^31':>12} | {'std(XOR)':>9} | {'std(ADD)/2^31':>13}")
    print("-"*60)

    for w in range(8):
        xa = np.array(xor_per_word[w])
        aa = np.array(add_per_word[w], dtype=np.float64)
        branch = "a" if w < 4 else "e"
        print(f"H[{w}]({branch}) | {xa.mean():>11.4f} | {aa.mean()/2**31:>12.6f} | "
              f"{xa.std():>9.4f} | {aa.std()/2**31:>13.6f}")

    # Correlation between add and xor per word
    print(f"\nCorrelation ADD vs XOR per word:")
    for w in range(8):
        xa = np.array(xor_per_word[w])
        aa = np.array(add_per_word[w], dtype=np.float64)
        c = np.corrcoef(xa, aa)[0,1]
        print(f"  H[{w}]: corr = {c:+.6f}")

    # Cross-word ADD correlations
    print(f"\nCross-word ADD correlations:")
    for w1 in range(8):
        for w2 in range(w1+1, 8):
            a1 = np.array(add_per_word[w1], dtype=np.float64)
            a2 = np.array(add_per_word[w2], dtype=np.float64)
            c = np.corrcoef(a1, a2)[0,1]
            if abs(c) > 0.05:
                print(f"  H[{w1}]↔H[{w2}]: corr = {c:+.6f} ***")

def test_predictable_suppression(N=2000):
    """Is suppression pattern PREDICTABLE from the message?"""
    print("\n--- TEST 4: PREDICTABLE SUPPRESSION PATTERN ---")

    # For each Wang pair, measure which word has max suppression
    # Does this correlate with message properties?
    max_supp_word = []
    w0_vals = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        # Full hash
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        xor_hw = [hw(Hn[w]^Hf[w]) for w in range(8)]

        # Which word has LOWEST hw (most "matched")?
        min_word = np.argmin(xor_hw)
        max_supp_word.append(min_word)
        w0_vals.append(W0)

    # Distribution of min-word
    from collections import Counter
    dist = Counter(max_supp_word)
    print(f"Which word matches best (lowest HW):")
    for w in range(8):
        count = dist.get(w, 0)
        branch = "a" if w < 4 else "e"
        print(f"  H[{w}]({branch}): {count}/{N} ({count/N*100:.1f}%)")
    print(f"  Expected (random): {N/8:.0f} ({100/8:.1f}%)")

    # Does message W0 predict which word matches best?
    # Use W0 mod 8 as predictor
    w0_mod8 = [w % 8 for w in w0_vals]
    match_rate = sum(1 for a, b in zip(w0_mod8, max_supp_word) if a == b) / N
    print(f"\nW0 mod 8 predicts min-word: {match_rate:.4f} (random: {1/8:.4f})")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 26: CARRY SUPPRESSION MAP")
    print("Where do suppressed bits go?")
    print("="*60)
    test_per_word_suppression(800)
    test_per_bit_suppression(800)
    test_additive_vs_xor(1500)
    test_predictable_suppression(1500)

if __name__ == "__main__":
    main()
