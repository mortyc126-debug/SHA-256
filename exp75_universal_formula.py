#!/usr/bin/env python3
"""
EXP 75: Universal Formula — S × pipe × λ × fourier = 256?

From exp74: pipe × λ × fourier = 17 (barrier, 0.0% error).
Observation: 256 / 17 ≈ S_degree (15.3, 1.6% error).

HYPOTHESIS: S_degree × pipe × λ × fourier = 256 (output size).
→ collision_cost = S × pipe × λ × fourier / 2 = 128 (birthday!)

If this formula holds AT DIFFERENT ROUND COUNTS:
  R-round collision cost = S(R) × pipe(R) × λ(R) × fourier(R) / 2

And if at some R, one constant is smaller → cost < 128!

Reduced-round data from earlier experiments:
  R=4:  λ varies, S varies, fourier varies
  R=16: different from R=64
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_vec(a,b):
    c_out=[]; c=0
    for i in range(32):
        s=((a>>i)&1)+((b>>i)&1)+c; c=1 if s>=2 else 0; c_out.append(c)
    return c_out

def measure_constants_at_R(R, N=1500):
    """Measure all 4 formula constants at round count R."""

    # S_degree: carry weight per round at this R
    s_degrees = []
    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, R)
        W = schedule(W16)
        total_cw = 0
        for r in range(R):
            a,b,c,d,e,f,g,h = states[r]
            T1 = (h+sigma1(e)+ch(e,f,g)+K[r]+W[r])&MASK
            carry_w = sum(carry_vec(d, T1))  # Main addition carry weight
            total_cw += carry_w
        s_degrees.append(total_cw / R if R > 0 else 0)

    S = np.mean(s_degrees)

    # Transparency + Fourier at this R
    T = np.zeros(32)
    for _ in range(min(N, 800)):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)

        Hn=[(IV[i]+sn[R][i])&MASK for i in range(8)]
        Hf=[(IV[i]+sf[R][i])&MASK for i in range(8)]

        for w in range(4,8):
            for bit in range(32):
                sx=(sn[R][w]^sf[R][w]>>bit)&1
                hx=(Hn[w]^Hf[w]>>bit)&1
                if sx==hx: T[bit]+=1

    T /= (min(N,800)*4)

    # Fourier of T
    T_c = T - T.mean()
    fft = np.fft.fft(T_c)
    power = np.abs(fft)**2
    if power[1:16].max() > 0:
        peak_freq = np.argmax(power[1:16]) + 1
        fourier = 32.0 / peak_freq
    else:
        fourier = 32.0

    # λ_max at this R (simplified: measure from divergence rate)
    div_rates = []
    for _ in range(min(N, 500)):
        W16 = random_w16()
        W_p = list(W16); W_p[0] ^= 1
        s1 = sha256_rounds(W16, R); s2 = sha256_rounds(W_p, R)
        d = sum(hw(s1[R][i]^s2[R][i]) for i in range(8))
        if d > 0:
            div_rates.append(np.log2(d) / R if R > 0 else 0)

    lam = np.mean(div_rates) if div_rates else 0

    # pipe_corr at this R (from Lyapunov pair gap)
    # Simplified: use δH variance ratio e-branch/a-branch
    e_vars = []; a_vars = []
    for _ in range(min(N, 500)):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        Wn,Wf,_,sn,sf = wang_cascade(W0,W1)
        Hn=[(IV[i]+sn[R][i])&MASK for i in range(8)]
        Hf=[(IV[i]+sf[R][i])&MASK for i in range(8)]
        a_d = sum(hw(Hn[i]^Hf[i]) for i in range(4))
        e_d = sum(hw(Hn[i]^Hf[i]) for i in range(4,8))
        a_vars.append(a_d); e_vars.append(e_d)

    # Pipe correlation proxy
    pipe = abs(np.corrcoef(a_vars, e_vars)[0,1]) if len(a_vars)>10 else 0

    return S, pipe, lam, fourier, T

def test_formula_vs_rounds():
    """Test: S × pipe × λ × fourier = output_dimension at each R?"""
    print("\n--- FORMULA: S × pipe × λ × fourier = 256? ---")

    print(f"{'R':>4} | {'S':>6} | {'pipe':>6} | {'λ':>6} | {'four':>6} | "
          f"{'Product':>8} | {'Product/256':>11} | {'Cost=P/2':>9}")
    print("-"*75)

    for R in [4, 8, 12, 16, 20, 24, 32, 48, 64]:
        S, pipe, lam, fourier, T = measure_constants_at_R(R, N=800)

        product = S * pipe * lam * fourier if (pipe>0 and lam>0 and fourier>0) else 0
        ratio = product / 256 if product > 0 else 0
        cost = product / 2 if product > 0 else 0

        print(f"{R:>4} | {S:>6.2f} | {pipe:>6.3f} | {lam:>6.3f} | {fourier:>6.1f} | "
              f"{product:>8.1f} | {ratio:>11.4f} | 2^{np.log2(cost) if cost>0 else 0:>5.1f}")

def test_formula_prediction():
    """Does the formula PREDICT known collision costs?"""
    print(f"\n--- FORMULA PREDICTIONS ---")

    # Known: R=17 Wang barrier, collision at R=17 costs ~2^32
    # Known: R=64 full SHA-256, collision costs 2^128

    print(f"Known collision costs vs formula predictions:")
    print(f"  R=17 (Wang barrier): known cost ≈ 2^32")
    print(f"  R=31 (Li 2024 record): known cost = practical")
    print(f"  R=64 (full): known cost = 2^128")

    for R in [17, 31, 64]:
        S, pipe, lam, fourier, _ = measure_constants_at_R(R, N=600)
        product = S * pipe * lam * fourier if (pipe>0 and lam>0 and fourier>0) else 0
        cost_bits = np.log2(product/2) if product > 2 else 0
        print(f"  R={R}: S={S:.2f}, pipe={pipe:.3f}, λ={lam:.3f}, "
              f"f={fourier:.1f} → product={product:.1f} → cost≈2^{cost_bits:.1f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 75: UNIVERSAL FORMULA")
    print("S × pipe × λ × fourier = 256?")
    print("="*60)
    test_formula_vs_rounds()
    test_formula_prediction()

    print("\n"+"="*60)
    print("IMPLICATIONS")
    print("="*60)
    print("If formula holds: collision = S×pipe×λ×fourier/2")
    print("To beat 128: need to reduce one constant")
    print("All are message-independent at R=64 → birthday fixed")
    print("BUT: at reduced rounds, constants differ → formula predicts cost")

if __name__ == "__main__":
    main()
