#!/usr/bin/env python3
"""
EXP 48: PP Controllability — Can (W0,W1) steer output through PP?

From exp47: 579 PP positions in differential carry (> 256 output bits).
From step-back: freedom is in CHOICE of (W0,W1) → determines PP pattern.

64 bits (W0,W1) → 579 PP positions → 256 output bits.

If controllable: 2^64 search over (W0,W1) covers 256 output bits.
Cost: 2^64 instead of 2^128 (birthday).

KEY TESTS:
1. How much do (W0,W1) affect the PP pattern?
2. Do PP positions influence output bits?
3. Is the mapping (W0,W1) → output through PP SURJECTIVE
   (reaches all possible outputs)?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def count_pp_positions(Wn, Wf):
    """Count PP positions (both normal and faulty have P) for main addition."""
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    Wn_e = schedule(Wn); Wf_e = schedule(Wf)

    pp_total = 0
    per_round = []

    for r in range(64):
        dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
        df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK

        gkp_n=carry_gkp_classification(dn,T1n)
        gkp_f=carry_gkp_classification(df,T1f)

        pp_r = sum(1 for cn,cf in zip(gkp_n,gkp_f) if cn=='P' and cf=='P')
        pp_total += pp_r
        per_round.append(pp_r)

    return pp_total, per_round

def test_w0w1_affects_pp(N=2000):
    """Does changing (W0,W1) at fixed ΔW change PP pattern?"""
    print("\n--- TEST 1: (W0,W1) → PP PATTERN ---")

    # Fix ΔW from one cascade
    W0r=random.randint(0,MASK); W1r=random.randint(0,MASK)
    _,_,DWs,_,_ = wang_cascade(W0r, W1r)

    pp_counts = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn=[W0,W1]+[0]*14
        Wf=[(Wn[i]+DWs[i])&MASK for i in range(16)]

        pp, _ = count_pp_positions(Wn, Wf)
        pp_counts.append(pp)

    pa = np.array(pp_counts)
    print(f"PP at fixed ΔW, varying (W0,W1):")
    print(f"  mean={pa.mean():.1f}, std={pa.std():.1f}, min={pa.min()}, max={pa.max()}")
    print(f"  Range: {pa.max()-pa.min()} PP positions")

    if pa.std() > 10:
        print(f"*** (W0,W1) SIGNIFICANTLY affects PP pattern (std={pa.std():.1f})! ***")

def test_pp_output_influence(N=2000):
    """
    Do PP positions INFLUENCE output bits more than non-PP?

    For each Wang pair: measure correlation between
    PP-count-per-round and output-difference-per-word.
    """
    print("\n--- TEST 2: PP → OUTPUT INFLUENCE ---")

    # For each pair: does high PP at late rounds correlate with output?
    late_pp = []; dH_list = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        pp, per_round = count_pp_positions(Wn, Wf)

        late_pp_val = sum(per_round[r] for r in range(48, 64))

        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        late_pp.append(late_pp_val)
        dH_list.append(dH)

    lp = np.array(late_pp); dh = np.array(dH_list)
    c = np.corrcoef(lp, dh)[0,1]
    threshold = 3/np.sqrt(N)

    print(f"corr(late_PP, δH) = {c:+.6f} {'***' if abs(c)>threshold else ''}")
    print(f"Threshold: {threshold:.4f}")

    # Quartile analysis
    for q_label, mask in [("Low PP", lp < np.percentile(lp, 25)),
                           ("High PP", lp > np.percentile(lp, 75))]:
        subset = dh[mask]
        print(f"  {q_label}: E[δH]={subset.mean():.4f}, N={len(subset)}")

def test_output_rank_through_pp(N=500):
    """
    KEY TEST: What is the RANK of the mapping (W0,W1) → δH?

    If rank > 64: the mapping covers more than 64 bits of output
    → (W0,W1) CAN'T control all 256 bits → 2^64 insufficient.

    If rank ≤ 64: (W0,W1) controls only 64 bits of output
    → but the OTHER 192 bits are DETERMINED → constraint!

    What rank does (W0,W1) → δH have?
    """
    print("\n--- TEST 3: RANK OF (W0,W1) → δH MAPPING ---")

    # Fix ΔW
    W0r=random.randint(0,MASK); W1r=random.randint(0,MASK)
    _,_,DWs,_,_ = wang_cascade(W0r, W1r)

    # Build influence matrix: for each bit of (W0,W1),
    # which bits of δH change?
    W0_base = random.randint(0, MASK)
    W1_base = random.randint(0, MASK)

    Wn_base = [W0_base, W1_base] + [0]*14
    Wf_base = [(Wn_base[i]+DWs[i])&MASK for i in range(16)]
    Hn_base = sha256_compress(Wn_base)
    Hf_base = sha256_compress(Wf_base)
    dH_base_bits = []
    for w in range(8):
        d = Hn_base[w] ^ Hf_base[w]
        for b in range(32):
            dH_base_bits.append((d>>b)&1)

    # Jacobian: 64 (input bits) × 256 (output bits)
    J = np.zeros((64, 256), dtype=np.int64)

    for input_bit in range(64):
        word = input_bit // 32  # 0 or 1
        bit = input_bit % 32

        W0_p = W0_base; W1_p = W1_base
        if word == 0:
            W0_p ^= (1 << bit)
        else:
            W1_p ^= (1 << bit)

        Wn_p = [W0_p, W1_p] + [0]*14
        Wf_p = [(Wn_p[i]+DWs[i])&MASK for i in range(16)]
        Hn_p = sha256_compress(Wn_p)
        Hf_p = sha256_compress(Wf_p)

        for w in range(8):
            d = Hn_p[w] ^ Hf_p[w]
            for b in range(32):
                out_bit = (d>>b)&1
                J[input_bit][w*32+b] = out_bit ^ dH_base_bits[w*32+b]

    rank = np.linalg.matrix_rank(J.astype(np.float64))
    print(f"Jacobian (W0,W1) → δH: {J.shape}")
    print(f"Rank: {rank}/64")

    if rank == 64:
        print(f"FULL RANK: (W0,W1) controls 64 independent output bits")
        print(f"  Remaining 256-64=192 bits UNCONTROLLED by (W0,W1)")
        print(f"  Cost: 2^64 for 64 bits + 2^(192/2)=2^96 birthday for rest")
        print(f"  TOTAL: max(2^64, 2^96) = 2^96")
        print(f"  *** POTENTIAL: 2^96 instead of 2^128! ***")
    else:
        print(f"Rank {rank}: (W0,W1) controls only {rank} output bits")

    # Verify at multiple base points
    print(f"\nVerification at {N} random base points:")
    ranks = []
    for _ in range(N):
        W0_b = random.randint(0, MASK)
        W1_b = random.randint(0, MASK)
        Wn_b = [W0_b, W1_b] + [0]*14
        Wf_b = [(Wn_b[i]+DWs[i])&MASK for i in range(16)]
        Hn_b = sha256_compress(Wn_b); Hf_b = sha256_compress(Wf_b)
        dH_bits = []
        for w in range(8):
            d=Hn_b[w]^Hf_b[w]
            for b in range(32):
                dH_bits.append((d>>b)&1)

        J_local = np.zeros((64, 256), dtype=np.int64)
        for ib in range(64):
            wd=ib//32; bt=ib%32
            W0_t=W0_b; W1_t=W1_b
            if wd==0: W0_t ^= (1<<bt)
            else: W1_t ^= (1<<bt)
            Wn_t=[W0_t,W1_t]+[0]*14
            Wf_t=[(Wn_t[i]+DWs[i])&MASK for i in range(16)]
            Hn_t=sha256_compress(Wn_t); Hf_t=sha256_compress(Wf_t)
            for w in range(8):
                d=Hn_t[w]^Hf_t[w]
                for b in range(32):
                    J_local[ib][w*32+b]=((d>>b)&1)^dH_bits[w*32+b]

        ranks.append(np.linalg.matrix_rank(J_local.astype(np.float64)))

    ra = np.array(ranks)
    print(f"  Rank: mean={ra.mean():.1f}, min={ra.min()}, max={ra.max()}")
    print(f"  Always full rank (64): {np.all(ra==64)}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 48: PP CONTROLLABILITY")
    print("Can (W0,W1) steer output through PP chain?")
    print("="*60)
    test_w0w1_affects_pp(1500)
    test_pp_output_influence(1500)
    test_output_rank_through_pp(200)

    print("\n"+"="*60)
    print("NEXT STEPS")
    print("="*60)

if __name__ == "__main__":
    main()
