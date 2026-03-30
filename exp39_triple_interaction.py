#!/usr/bin/env python3
"""
EXP 39: Triple Interaction in SHA-Ring — δL, δC, δR

SHA-Ring has THREE operations: + (mod), ⊕ (XOR), Σ (rotation).
exp38: δL and δC are independent (corr=-0.003).

BUT: we never isolated the ROTATION component δR.
Rotation interacts with BOTH carry and XOR. The interaction
term δR might correlate with δL or δC EVEN WHEN they don't
correlate with each other.

Analogy: three variables X,Y,Z where corr(X,Y)=0, corr(X,Z)=0,
but corr(Y,Z|X) ≠ 0. Triple interaction invisible to pairwise tests.

FULL S-DECOMPOSITION:
H(M) = L(M) ⊕ C(M) ⊕ R(M)
where:
  L = pure XOR computation (no carry, no rotation effect on carry)
  C = carry correction (carry only, standard rotation)
  R = rotation-carry INTERACTION (how rotation creates/destroys carries)

If δR correlates with δL or δC → effective collision dim < 256.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def sha256_no_rotation_compress(W16, iv=None):
    """SHA-256 with rotations replaced by identity. Isolates rotation contribution."""
    if iv is None: iv = list(IV)
    def no_rot_sigma0(x): return 0  # Σ0 = 0 (no rotation)
    def no_rot_sigma1(x): return 0
    def no_rot_sig0(x): return x >> 3  # Only the SHR part
    def no_rot_sig1(x): return x >> 10

    W = list(W16) + [0]*48
    for t in range(16, 64):
        W[t] = (no_rot_sig1(W[t-2]) + W[t-7] + no_rot_sig0(W[t-15]) + W[t-16]) & MASK

    state = list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h = state
        T1 = (h + no_rot_sigma1(e) + ch(e,f,g) + K[r] + W[r]) & MASK
        T2 = (no_rot_sigma0(a) + maj(a,b,c)) & MASK
        state = [(T1+T2)&MASK, a, b, c, (d+T1)&MASK, e, f, g]
    return [(iv[i]+state[i])&MASK for i in range(8)]

def xor_compress(W16, iv=None):
    """Pure XOR SHA-256 (no carry, standard rotation)."""
    if iv is None: iv = list(IV)
    W = list(W16)+[0]*48
    for t in range(16,64):
        W[t]=sig1(W[t-2])^W[t-7]^sig0(W[t-15])^W[t-16]
    s=list(iv)
    for r in range(64):
        a,b,c,d,e,f,g,h=s
        T1=h^sigma1(e)^ch(e,f,g)^K[r]^W[r]
        T2=sigma0(a)^maj(a,b,c)
        s=[T1^T2,a,b,c,d^T1,e,f,g]
    return [iv[i]^s[i] for i in range(8)]

def triple_decompose(W16):
    """
    Decompose H(M) = L ⊕ C ⊕ R:
    L = XOR-only hash (no carry, with rotation)
    H = real hash (carry + rotation)
    N = no-rotation hash (carry, no rotation)

    Then:
    C_component = H ⊕ L  (what carry adds to XOR)
    R_component = H ⊕ N  (what rotation adds to no-rotation)
    LCR_interaction = L ⊕ N ⊕ H (triple interaction: what needs ALL THREE)
    """
    H = sha256_compress(W16)
    L = xor_compress(W16)
    N = sha256_no_rotation_compress(W16)

    C_comp = [H[i] ^ L[i] for i in range(8)]  # Carry contribution
    R_comp = [H[i] ^ N[i] for i in range(8)]  # Rotation contribution
    LCR = [L[i] ^ N[i] ^ H[i] for i in range(8)]  # Triple interaction

    return H, L, N, C_comp, R_comp, LCR

def test_triple_decomposition(N=2000):
    """Measure the three components and their interactions."""
    print("\n--- TEST 1: TRIPLE DECOMPOSITION ---")

    dL_list=[]; dC_list=[]; dR_list=[]; dLCR_list=[]; dH_list=[]

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        Hn, Ln, Nn, Cn, Rn, LCRn = triple_decompose(Wn)
        Hf, Lf, Nf, Cf, Rf, LCRf = triple_decompose(Wf)

        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dC = sum(hw(Cn[i]^Cf[i]) for i in range(8))
        dR = sum(hw(Rn[i]^Rf[i]) for i in range(8))
        dLCR = sum(hw(LCRn[i]^LCRf[i]) for i in range(8))
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))

        dL_list.append(dL); dC_list.append(dC); dR_list.append(dR)
        dLCR_list.append(dLCR); dH_list.append(dH)

    dL=np.array(dL_list); dC=np.array(dC_list); dR=np.array(dR_list)
    dLCR=np.array(dLCR_list); dH=np.array(dH_list)

    print(f"E[δL] (XOR):        {dL.mean():.2f}")
    print(f"E[δC] (carry):      {dC.mean():.2f}")
    print(f"E[δR] (rotation):   {dR.mean():.2f}")
    print(f"E[δLCR] (triple):   {dLCR.mean():.2f}")
    print(f"E[δH] (total):      {dH.mean():.2f}")

    threshold = 3/np.sqrt(N)

    # ALL pairwise correlations
    print(f"\nPairwise correlations (threshold={threshold:.4f}):")
    pairs = [('δL','δC',dL,dC), ('δL','δR',dL,dR), ('δC','δR',dC,dR),
             ('δL','δLCR',dL,dLCR), ('δC','δLCR',dC,dLCR), ('δR','δLCR',dR,dLCR),
             ('δL','δH',dL,dH), ('δC','δH',dC,dH), ('δR','δH',dR,dH),
             ('δLCR','δH',dLCR,dH)]

    for name1, name2, arr1, arr2 in pairs:
        c = np.corrcoef(arr1, arr2)[0,1]
        sig = " ***" if abs(c) > threshold else ""
        print(f"  corr({name1:>4}, {name2:>4}): {c:+.6f}{sig}")

    # TRIPLE interaction: corr(δL·δC, δR) — does product predict third?
    print(f"\nTriple interactions:")
    prod_LC = dL * dC
    prod_LR = dL * dR
    prod_CR = dC * dR

    for name, prod, target in [('δL·δC→δR', prod_LC, dR),
                                ('δL·δC→δH', prod_LC, dH),
                                ('δL·δR→δC', prod_LR, dC),
                                ('δC·δR→δH', prod_CR, dH),
                                ('δL·δC·δR→δH', dL*dC*dR, dH)]:
        if prod.std() > 0:
            c = np.corrcoef(prod, target)[0,1]
            sig = " ***" if abs(c) > threshold else ""
            print(f"  corr({name}): {c:+.6f}{sig}")

    return dL, dC, dR, dLCR, dH

def test_conditional_triple(N=3000):
    """
    Test: does conditioning on one component reveal structure in others?

    corr(δL, δC) = 0 unconditionally.
    But corr(δL, δC | δR < median) might ≠ 0!
    This is the HIDDEN triple interaction.
    """
    print("\n--- TEST 2: CONDITIONAL TRIPLE INTERACTIONS ---")

    data = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,_,_ = wang_cascade(W0,W1)

        Hn,Ln,Nn,Cn,Rn,LCRn = triple_decompose(Wn)
        Hf,Lf,Nf,Cf,Rf,LCRf = triple_decompose(Wf)

        dL = sum(hw(Ln[i]^Lf[i]) for i in range(8))
        dC = sum(hw(Cn[i]^Cf[i]) for i in range(8))
        dR = sum(hw(Rn[i]^Rf[i]) for i in range(8))
        dH = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        data.append((dL, dC, dR, dH))

    dL=np.array([d[0] for d in data])
    dC=np.array([d[1] for d in data])
    dR=np.array([d[2] for d in data])
    dH=np.array([d[3] for d in data])

    med_R = np.median(dR)
    med_L = np.median(dL)
    med_C = np.median(dC)

    # Conditional correlations
    print(f"Unconditional:")
    print(f"  corr(δL, δC) = {np.corrcoef(dL,dC)[0,1]:+.6f}")
    print(f"  corr(δL, δH) = {np.corrcoef(dL,dH)[0,1]:+.6f}")
    print(f"  corr(δC, δH) = {np.corrcoef(dC,dH)[0,1]:+.6f}")

    print(f"\nConditioned on δR < median ({med_R:.0f}):")
    mask = dR < med_R
    if mask.sum() > 100:
        c_LC = np.corrcoef(dL[mask], dC[mask])[0,1]
        c_LH = np.corrcoef(dL[mask], dH[mask])[0,1]
        c_CH = np.corrcoef(dC[mask], dH[mask])[0,1]
        print(f"  corr(δL, δC | δR low) = {c_LC:+.6f}")
        print(f"  corr(δL, δH | δR low) = {c_LH:+.6f}")
        print(f"  corr(δC, δH | δR low) = {c_CH:+.6f}")

    print(f"\nConditioned on δR > median:")
    mask = dR > med_R
    if mask.sum() > 100:
        c_LC = np.corrcoef(dL[mask], dC[mask])[0,1]
        c_LH = np.corrcoef(dL[mask], dH[mask])[0,1]
        c_CH = np.corrcoef(dC[mask], dH[mask])[0,1]
        print(f"  corr(δL, δC | δR high) = {c_LC:+.6f}")
        print(f"  corr(δL, δH | δR high) = {c_LH:+.6f}")
        print(f"  corr(δC, δH | δR high) = {c_CH:+.6f}")

    # Cross-conditioning
    print(f"\nConditioned on δL < median ({med_L:.0f}):")
    mask = dL < med_L
    if mask.sum() > 100:
        c_CR = np.corrcoef(dC[mask], dR[mask])[0,1]
        c_CH = np.corrcoef(dC[mask], dH[mask])[0,1]
        print(f"  corr(δC, δR | δL low) = {c_CR:+.6f}")
        print(f"  corr(δC, δH | δL low) = {c_CH:+.6f}")

    # Low ALL three simultaneously
    print(f"\nLow ALL three (δL<med AND δC<med AND δR<med):")
    mask = (dL < med_L) & (dC < med_C) & (dR < med_R)
    n_all_low = mask.sum()
    if n_all_low > 10:
        dH_all_low = dH[mask]
        print(f"  N={n_all_low}, E[δH]={dH_all_low.mean():.4f} (vs overall {dH.mean():.4f})")
        print(f"  Difference: {dH_all_low.mean()-dH.mean():+.4f}")

def test_rotation_decomposition_per_word(N=2000):
    """Per-word analysis: which words carry the rotation signal?"""
    print("\n--- TEST 3: PER-WORD ROTATION CONTRIBUTION ---")

    for w in range(8):
        dR_w = []; dH_w = []
        for _ in range(N):
            W0=random.randint(0,MASK); W1=random.randint(0,MASK)
            Wn,Wf,_,_,_ = wang_cascade(W0,W1)
            Hn,_,Nn,_,Rn,_ = triple_decompose(Wn)
            Hf,_,Nf,_,Rf,_ = triple_decompose(Wf)
            dR_w.append(hw(Rn[w]^Rf[w]))
            dH_w.append(hw(Hn[w]^Hf[w]))

        c = np.corrcoef(dR_w, dH_w)[0,1]
        branch = "a" if w < 4 else "e"
        sig = " ***" if abs(c) > 3/np.sqrt(N) else ""
        print(f"  H[{w}]({branch}): E[δR]={np.mean(dR_w):.2f}, corr(δR,δH)={c:+.6f}{sig}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 39: TRIPLE INTERACTION IN SHA-RING")
    print("δL, δC, δR — the full three-component structure")
    print("="*60)

    dL,dC,dR,dLCR,dH = test_triple_decomposition(2000)
    test_conditional_triple(2500)
    test_rotation_decomposition_per_word(1500)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
