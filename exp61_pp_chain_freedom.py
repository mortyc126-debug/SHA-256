#!/usr/bin/env python3
"""
EXP 61: PP-Chain Differential Freedom — Exact Count

PP positions = 579 (exp47). But TRUE differential freedom =
PP-chains where carry-in difference is NOT determined by predecessor.

Predecessor types:
  GG → diff carry-in = 0 (both carry=1, difference=0)
  KK → diff carry-in = 0 (both carry=0, difference=0)
  Mixed (GP/KP/GK/PG/PK/KG) → diff carry-in = determined
  PP → diff carry-in = INHERITED (free if chain extends back)

TRUE FREEDOM = number of PP-chains where the FIRST PP position
in the chain has a PP predecessor (extending the freedom chain).

If true_freedom > 256 → system is underdetermined → collision solvable.
If true_freedom < 256 → insufficient freedom.

Also: how does true_freedom connect to the 288-bit rank=256 result?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def analyze_pp_chains_detailed(Wn, Wf):
    """
    Detailed PP-chain analysis for one Wang pair.
    Count: PP positions, PP-chains, and chains with free carry-in.
    """
    sn = sha256_rounds(Wn, 64); sf = sha256_rounds(Wf, 64)
    Wn_e = schedule(Wn); Wf_e = schedule(Wf)

    total_pp = 0
    total_pp_chains = 0
    free_carry_in_chains = 0  # Chains where carry-in diff is undetermined
    determined_chains = 0  # Chains where carry-in diff IS determined

    for r in range(64):
        dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
        df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
        T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+Wn_e[r])&MASK
        T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wf_e[r])&MASK

        gkp_n = carry_gkp_classification(dn, T1n)
        gkp_f = carry_gkp_classification(df, T1f)

        # Build differential GKP classification
        diff_gkp = []
        for cn, cf in zip(gkp_n, gkp_f):
            if cn == 'P' and cf == 'P':
                diff_gkp.append('PP')
            elif cn == cf:  # GG or KK
                diff_gkp.append('SAME')  # Carry diff = 0
            else:
                diff_gkp.append('MIXED')  # Carry diff determined

        # Analyze PP chains
        in_pp_chain = False
        chain_start_type = None  # What precedes the chain?

        for i in range(32):
            if diff_gkp[i] == 'PP':
                total_pp += 1
                if not in_pp_chain:
                    # Start new chain
                    total_pp_chains += 1
                    in_pp_chain = True
                    # What's the predecessor?
                    if i == 0:
                        # Bit 0: carry-in = 0 for both → diff = 0 → determined
                        chain_start_type = 'DETERMINED'
                        determined_chains += 1
                    else:
                        prev = diff_gkp[i-1]
                        if prev == 'PP':
                            # Previous was also PP → this extends the chain
                            # (shouldn't happen — we just started a new chain)
                            chain_start_type = 'FREE'
                            free_carry_in_chains += 1
                        elif prev == 'SAME':
                            # GG or KK → carry diff = 0 → determined
                            chain_start_type = 'DETERMINED'
                            determined_chains += 1
                        else:  # MIXED
                            # One G/K, other P → carry diff = 1 or 0 → determined
                            chain_start_type = 'DETERMINED'
                            determined_chains += 1
            else:
                in_pp_chain = False

    return {
        'total_pp': total_pp,
        'pp_chains': total_pp_chains,
        'free_chains': free_carry_in_chains,
        'determined_chains': determined_chains,
    }

def test_pp_freedom_count(N=1000):
    """Count exact PP freedom for many Wang pairs."""
    print(f"\n--- PP-CHAIN FREEDOM COUNT (N={N}) ---")

    results = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        info = analyze_pp_chains_detailed(Wn, Wf)
        results.append(info)

    pp = np.array([r['total_pp'] for r in results])
    chains = np.array([r['pp_chains'] for r in results])
    free = np.array([r['free_chains'] for r in results])
    det = np.array([r['determined_chains'] for r in results])

    print(f"PP positions:      mean={pp.mean():.1f} ± {pp.std():.1f}")
    print(f"PP chains:         mean={chains.mean():.1f} ± {chains.std():.1f}")
    print(f"Free carry-in:     mean={free.mean():.1f} ± {free.std():.1f}")
    print(f"Determined:        mean={det.mean():.1f} ± {det.std():.1f}")
    print(f"Free fraction:     {free.mean()/chains.mean()*100:.1f}%")

    print(f"\nFreedom analysis:")
    print(f"  PP positions: {pp.mean():.0f} (raw, overcounts)")
    print(f"  PP chains: {chains.mean():.0f} (corrected for chain structure)")
    print(f"  Free chains: {free.mean():.0f} (true differential freedom)")
    print(f"  Target: 256 (collision constraint)")

    if free.mean() > 256:
        print(f"  *** FREE > 256: Collision potentially solvable! ***")
    elif chains.mean() > 256:
        print(f"  Chains > 256 but free < 256: freedom exists but constrained")
    else:
        print(f"  Insufficient freedom")

    # What about including ALL 7 additions (not just d+T1)?
    print(f"\n--- EXTENDED: ALL 7 ADDITIONS ---")
    results_full = []
    for _ in range(min(N, 200)):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Wn_e=schedule(Wn); Wf_e=schedule(Wf)

        total_pp_all = 0
        for r in range(64):
            an,bn,cn,dn,en,fn,gn,hn = sn[r]
            af,bf,cf,df,ef,ff_,gf,hf = sf[r]
            sig1n=sigma1(en); ch_n=ch(en,fn,gn)
            sig1f=sigma1(ef); ch_f=ch(ef,ff_,gf)
            sig0n=sigma0(an); maj_n=maj(an,bn,cn)
            sig0f=sigma0(af); maj_f=maj(af,bf,cf)
            s1n=(hn+sig1n)&MASK; s1f=(hf+sig1f)&MASK
            s2n=(s1n+ch_n)&MASK; s2f=(s1f+ch_f)&MASK
            s3n=(s2n+K[r])&MASK; s3f=(s2f+K[r])&MASK
            T1n=(s3n+Wn_e[r])&MASK; T1f=(s3f+Wf_e[r])&MASK
            T2n=(sig0n+maj_n)&MASK; T2f=(sig0f+maj_f)&MASK

            additions = [
                (hn,sig1n,hf,sig1f), (s1n,ch_n,s1f,ch_f),
                (s2n,K[r],s2f,K[r]), (s3n,Wn_e[r],s3f,Wf_e[r]),
                (sig0n,maj_n,sig0f,maj_f), (T1n,T2n,T1f,T2f),
                (dn,T1n,df,T1f),
            ]
            for an_,bn_,af_,bf_ in additions:
                gn_ = carry_gkp_classification(an_,bn_)
                gf_ = carry_gkp_classification(af_,bf_)
                pp_count = sum(1 for c1,c2 in zip(gn_,gf_) if c1=='P' and c2=='P')
                total_pp_all += pp_count

        results_full.append(total_pp_all)

    fa = np.array(results_full)
    print(f"ALL 7 additions: PP positions = {fa.mean():.0f} ± {fa.std():.0f}")
    print(f"Per-addition average: {fa.mean()/7:.0f}")
    print(f"Estimated PP chains (all 7): ~{fa.mean()/1.94:.0f} (using avg chain length 1.94)")

def test_pp_vs_dH(N=1500):
    """Does PP freedom correlate with collision difficulty?"""
    print(f"\n--- PP FREEDOM → δH? ---")

    pp_list=[]; dH_list=[]
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)
        info = analyze_pp_chains_detailed(Wn, Wf)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        pp_list.append(info['total_pp'])
        dH_list.append(dH)

    pp_a=np.array(pp_list); dh_a=np.array(dH_list)
    c = np.corrcoef(pp_a, dh_a)[0,1]
    threshold = 3/np.sqrt(N)

    print(f"corr(PP_count, δH) = {c:+.6f} {'***' if abs(c)>threshold else ''}")

    # High PP → ??? δH
    high_pp = dh_a[pp_a > np.percentile(pp_a, 75)]
    low_pp = dh_a[pp_a < np.percentile(pp_a, 25)]
    print(f"High PP: E[δH]={high_pp.mean():.4f}")
    print(f"Low PP:  E[δH]={low_pp.mean():.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 61: PP-CHAIN DIFFERENTIAL FREEDOM")
    print("="*60)
    test_pp_freedom_count(800)
    test_pp_vs_dH(1200)

if __name__ == "__main__":
    main()
