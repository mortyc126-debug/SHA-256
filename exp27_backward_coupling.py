#!/usr/bin/env python3
"""
EXP 27: Backward SHA-256 Coupling

SHA-256 round function is INVERTIBLE. Forward τ_coupling=8-12.
Does BACKWARD computation have different τ?

Forward:  a_new = T1+T2 (complex), e_new = d+T1 (complex)
Backward: a_old = b_new (trivial shift!), d_old = e_new - T1

The asymmetry means backward coupling might be VERY DIFFERENT.

If backward τ >> 12:
  Forward zone: rounds 0-24 (coupling preserved)
  Backward zone: rounds X-64 (coupling preserved)
  If zones overlap → collision feasible through coupling bridge

OUR TOOLS: invertible round function + carry coupling measurement
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a, b):
    c_out = []
    c = 0
    for i in range(32):
        s = ((a>>i)&1)+((b>>i)&1)+c
        c = 1 if s>=2 else 0
        c_out.append(c)
    return c_out

def sha256_round_inverse(state_next, W_r, K_r):
    """Invert one SHA-256 round. Given state[r+1], recover state[r]."""
    a_next, b_next, c_next, d_next, e_next, f_next, g_next, h_next = state_next

    # From shift: a_old = b_next, b_old = c_next, c_old = d_next
    # e_old = f_next, f_old = g_next, g_old = h_next
    a_old = b_next
    b_old = c_next
    c_old = d_next
    e_old = f_next
    f_old = g_next
    g_old = h_next

    # T2 = Σ0(a_old) + Maj(a_old, b_old, c_old)
    T2 = (sigma0(a_old) + maj(a_old, b_old, c_old)) & MASK

    # a_next = T1 + T2 → T1 = a_next - T2
    T1 = (a_next - T2) & MASK

    # d_old = e_next - T1
    d_old = (e_next - T1) & MASK

    # h_old = T1 - Σ1(e_old) - Ch(e_old, f_old, g_old) - K_r - W_r
    h_old = (T1 - sigma1(e_old) - ch(e_old, f_old, g_old) - K_r - W_r) & MASK

    return [a_old, b_old, c_old, d_old, e_old, f_old, g_old, h_old]

def sha256_backward(state_final, W16, num_rounds=64):
    """Run SHA-256 BACKWARD from state_final to state_0."""
    W = schedule(W16)
    states = [None] * (num_rounds + 1)
    states[num_rounds] = list(state_final)

    for r in range(num_rounds - 1, -1, -1):
        states[r] = sha256_round_inverse(states[r + 1], W[r], K[r])

    return states

def test_backward_verification(N=500):
    """Verify backward computation is correct."""
    print("\n--- TEST 0: BACKWARD VERIFICATION ---")
    correct = 0
    for _ in range(N):
        W16 = random_w16()
        fwd = sha256_rounds(W16, 64)
        bwd = sha256_backward(fwd[64], W16, 64)

        if all(fwd[0][i] == bwd[0][i] for i in range(8)):
            correct += 1

    print(f"Backward verification: {correct}/{N}")
    return correct == N

def kappa_at_round_from_states(sn, sf, We, Wfe, r):
    """Coupling κ at round r from precomputed states."""
    dn=sn[r][3]; en=sn[r][4]; fn=sn[r][5]; gn=sn[r][6]; hn=sn[r][7]
    df=sf[r][3]; ef=sf[r][4]; ff_=sf[r][5]; gf=sf[r][6]; hf=sf[r][7]
    T1n=(hn+sigma1(en)+ch(en,fn,gn)+K[r]+We[r])&MASK
    T1f=(hf+sigma1(ef)+ch(ef,ff_,gf)+K[r]+Wfe[r])&MASK
    cv_n=carry_vec(dn,T1n); cv_f=carry_vec(df,T1f)
    return sum(a^b for a,b in zip(cv_n,cv_f))

def test_backward_coupling(N=1000):
    """
    Measure coupling in BACKWARD direction.

    Strategy: start from SAME final state (collision target),
    two different messages M, M'. Go backward.
    Measure κ at each round going backward.
    """
    print("\n--- TEST 1: BACKWARD COUPLING PROFILE ---")

    # Generate pairs that share final state (artificial)
    # Use one message, compute state[64], then go backward with different W
    bwd_kappa = {r: [] for r in range(64)}

    for _ in range(N):
        W16_n = random_w16()
        fwd_n = sha256_rounds(W16_n, 64)
        target_state = fwd_n[64]  # Shared target

        # Second message: slightly different
        W16_f = list(W16_n)
        W16_f[0] = (W16_f[0] + 1) & MASK

        # Go backward from SAME target with both messages
        bwd_n = sha256_backward(target_state, W16_n, 64)
        bwd_f = sha256_backward(target_state, W16_f, 64)

        We_n = schedule(W16_n); We_f = schedule(W16_f)

        for r in range(64):
            k = kappa_at_round_from_states(bwd_n, bwd_f, We_n, We_f, r)
            bwd_kappa[r].append(k)

    print(f"{'Round':>5} | {'E[κ] backward':>14} | Signal")
    print("-"*35)
    for r in [63,62,61,60,56,52,48,40,32,24,16,8,4,2,1,0]:
        arr = np.array(bwd_kappa[r])
        sig = ""
        if arr.mean() < 12: sig = " LOW"
        if arr.mean() < 8: sig = " VERY LOW"
        print(f"{r:>5} | {arr.mean():>14.4f} | {sig}")

    return bwd_kappa

def test_backward_autocorrelation(N=500):
    """Autocorrelation of backward coupling."""
    print("\n--- TEST 2: BACKWARD COUPLING AUTOCORRELATION ---")

    all_kappas = []
    for _ in range(N):
        W16_n = random_w16()
        fwd_n = sha256_rounds(W16_n, 64)
        target = fwd_n[64]

        W16_f = list(W16_n)
        W16_f[0] = (W16_f[0] + 1) & MASK

        bwd_n = sha256_backward(target, W16_n, 64)
        bwd_f = sha256_backward(target, W16_f, 64)
        We_n = schedule(W16_n); We_f = schedule(W16_f)

        kv = [kappa_at_round_from_states(bwd_n, bwd_f, We_n, We_f, r)
              for r in range(64)]
        all_kappas.append(kv)

    K = np.array(all_kappas)

    # Autocorrelation going BACKWARD (from round 63 toward 0)
    print("Backward autocorrelation (from round 63 toward 0):")
    for lag in [1,2,3,4,5,8,12,16]:
        corrs = []
        for i in range(N):
            for r in range(63, lag - 1, -1):
                corrs.append((K[i,r], K[i,r-lag]))
        x = np.array([c[0] for c in corrs])
        y = np.array([c[1] for c in corrs])
        c = np.corrcoef(x,y)[0,1]
        sig = " ***" if abs(c) > 0.05 else ""
        print(f"  Lag {lag:>2} (backward): {c:+.6f}{sig}")

    # Compare with FORWARD autocorrelation (from exp16B data)
    print("\nForward autocorrelation (for comparison, from Wang pairs):")
    fwd_kappas = []
    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        We=schedule(Wn); Wfe=schedule(Wf)
        kv = [kappa_at_round_from_states(sn, sf, We, Wfe, r) for r in range(64)]
        fwd_kappas.append(kv)

    Kf = np.array(fwd_kappas)
    for lag in [1,2,3,4,5,8,12,16]:
        corrs = []
        for i in range(N):
            for r in range(64-lag):
                corrs.append((Kf[i,r], Kf[i,r+lag]))
        x = np.array([c[0] for c in corrs])
        y = np.array([c[1] for c in corrs])
        c = np.corrcoef(x,y)[0,1]
        sig = " ***" if abs(c) > 0.05 else ""
        print(f"  Lag {lag:>2} (forward):  {c:+.6f}{sig}")

def test_bidirectional_overlap(N=500):
    """
    Can forward and backward coupling zones OVERLAP?

    Forward: Wang cascade → low κ for rounds 0-16, decaying to random by ~24.
    Backward: from shared target → low κ for rounds 52-64?, decaying backward.

    If forward zone extends to round X and backward to round Y,
    and X ≥ Y → zones overlap → coupling bridge complete!
    """
    print("\n--- TEST 3: BIDIRECTIONAL COUPLING OVERLAP ---")

    # For each pair: measure where forward κ > threshold AND backward κ > threshold
    # The GAP between them = cost of bridging

    gap_sizes = []

    for _ in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,DWs,sn_fwd,sf_fwd = wang_cascade(W0,W1)
        We_n=schedule(Wn); We_f=schedule(Wf)

        # Forward coupling
        fwd_k = [kappa_at_round_from_states(sn_fwd,sf_fwd,We_n,We_f,r) for r in range(64)]

        # Backward from shared final state
        target_n = sn_fwd[64]
        target_f = sf_fwd[64]

        # For backward: we use the SAME messages, going back from DIFFERENT final states
        # This measures how far backward the coupling persists
        bwd_n = sha256_backward(target_n, Wn, 64)
        bwd_f = sha256_backward(target_f, Wf, 64)

        bwd_k = [kappa_at_round_from_states(bwd_n,bwd_f,We_n,We_f,r) for r in range(64)]

        # Forward "edge": last round where κ < 12
        fwd_edge = 0
        for r in range(64):
            if fwd_k[r] < 12:
                fwd_edge = r

        # Backward "edge": first round (from end) where κ < 12
        bwd_edge = 63
        for r in range(63, -1, -1):
            if bwd_k[r] < 12:
                bwd_edge = r

        gap = bwd_edge - fwd_edge
        gap_sizes.append(gap)

    gaps = np.array(gap_sizes)
    print(f"Gap between forward and backward coupling zones:")
    print(f"  Mean gap: {gaps.mean():.2f} rounds")
    print(f"  Min gap: {gaps.min()} rounds")
    print(f"  Max gap: {gaps.max()} rounds")
    print(f"  P(gap ≤ 0): {np.mean(gaps <= 0):.6f} (= overlap probability)")

    if gaps.min() <= 0:
        print("*** SIGNAL: Forward and backward coupling zones OVERLAP! ***")
    elif gaps.min() < 16:
        bridging_cost = gaps.min() * 8  # ~8 bits per round
        print(f"  Minimum bridging cost: ~2^{bridging_cost} (for {gaps.min()}-round gap)")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 27: BACKWARD SHA-256 COUPLING")
    print("Does backward have different τ?")
    print("="*60)

    if not test_backward_verification(200):
        print("BACKWARD VERIFICATION FAILED!")
        return

    bwd_kappa = test_backward_coupling(800)
    test_backward_autocorrelation(400)
    test_bidirectional_overlap(500)

    print("\n" + "="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
