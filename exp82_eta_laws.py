#!/usr/bin/env python3
"""
EXP 82: η Laws — Does η = 0.18872 Govern UALRA?

From v20: η = (3ln3 - 4ln2)/(4ln2) = 0.18872 (carry mutual information).

From exp81:
  rotation-carry = 3.1 ≈ 16η = 3.02 (3% error)
  [Γ, Ch] = 5.98 ≈ 32η = 6.04 (1% error)

If these are EXACT → η is the fundamental constant of UALRA.
All SHA-256 structural constants = multiples of η.

HIGH PRECISION test: measure both with N=10000.
Also: search for other η-multiples in our 62 theorems.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

ETA = (3*math.log(3) - 4*math.log(2)) / (4*math.log(2))

def carry_vec(a,b):
    c_out=[]; c=0
    for i in range(32):
        s=((a>>i)&1)+((b>>i)&1)+c; c=1 if s>=2 else 0; c_out.append(c)
    return c_out

def test_rotation_carry_precision(N=10000):
    """High-precision measurement of rotation-carry invariant."""
    print(f"\n--- ROTATION-CARRY INVARIANT (N={N}) ---")
    print(f"η = {ETA:.10f}")
    print(f"16η = {16*ETA:.10f}")

    for k in [2, 6, 7, 11, 13, 17, 18, 19, 22, 25]:
        diffs = []
        for _ in range(N):
            a = random.randint(0, MASK); b = random.randint(0, MASK)
            a_rot = rotr(a, k)
            c_normal = hw(((a+b)&MASK) ^ (a^b))
            c_rotated = hw(((a_rot+b)&MASK) ^ (a_rot^b))
            diffs.append(abs(c_normal - c_rotated))

        measured = np.mean(diffs)
        predicted = 16 * ETA
        error = (measured - predicted) / predicted * 100

        sig = "✓" if abs(error) < 5 else "✗"
        print(f"  ROTR_{k:>2}: measured={measured:.4f}, 16η={predicted:.4f}, "
              f"error={error:+.1f}% {sig}")

def test_commutator_precision(N=10000):
    """High-precision [Γ, Ch] commutator."""
    print(f"\n--- [Γ, Ch] COMMUTATOR (N={N}) ---")
    print(f"32η = {32*ETA:.10f}")

    comms = []
    for _ in range(N):
        e = random.randint(0,MASK); f = random.randint(0,MASK)
        g = random.randint(0,MASK); a = random.randint(0,MASK)
        de = random.randint(1, MASK)

        ch_val = ch(e, f, g)
        ch_pert = ch(e^de, f, g)

        p1 = (a + ch_pert) & MASK
        dch = ch_val ^ ch_pert
        p2 = (a + ch_val) & MASK
        p2_xor = p2 ^ dch

        comms.append(hw(p1 ^ p2_xor))

    measured = np.mean(comms)
    predicted = 32 * ETA
    error = (measured - predicted) / predicted * 100

    print(f"  Measured: {measured:.4f}")
    print(f"  32η:      {predicted:.4f}")
    print(f"  Error:    {error:+.2f}%")

def test_all_eta_multiples():
    """Search all our measured constants for η-multiples."""
    print(f"\n--- η-MULTIPLES IN SHA-256 CONSTANTS ---")

    constants = {
        'rotation_carry': 3.1,
        '[Γ,Ch]': 5.98,
        'S_degree_gap': 16 - 15.3,
        'coupling_rate': 7.24,
        'carry_deficit': 13,
        'fourier_period': 10.7,
        'cascade_depth_e': 4.5,
        'lambda_max': 2.74,
        'pipe_corr': 0.58,
        'T_peak_9_excess': 0.72 - 0.50,
        'T_valley_27': 0.50 - 0.27,
        'coupling_63_mean': 15.8,
        'interaction_deficit': 16 - 15.3,
    }

    print(f"{'Constant':>25} | {'Value':>8} | {'Value/η':>8} | {'Nearest':>8} | {'Error':>7}")
    print("-"*65)

    for name, val in constants.items():
        ratio = val / ETA
        nearest = round(ratio)
        if nearest == 0: nearest = 1
        error = abs(ratio - nearest) / nearest * 100

        sig = "✓" if error < 10 else ""
        print(f"{name:>25} | {val:>8.4f} | {ratio:>8.2f} | {nearest:>8}η | {error:>6.1f}% {sig}")

    # Specifically test: is S-degree gap = 4η?
    print(f"\nSpecific tests:")
    gap = 0.7; predicted = 4*ETA
    print(f"  S-degree gap = {gap} ≈ 4η = {predicted:.4f} ({abs(gap-predicted)/predicted*100:.1f}%)")

    # Is coupling rate = 38η?
    rate = 7.24; predicted = 38*ETA
    print(f"  coupling_rate = {rate} ≈ 38η = {predicted:.4f} ({abs(rate-predicted)/predicted*100:.1f}%)")

    # Is carry deficit = 69η?
    deficit = 13; predicted = 69*ETA
    print(f"  carry_deficit = {deficit} ≈ 69η = {predicted:.4f} ({abs(deficit-predicted)/predicted*100:.1f}%)")

def test_eta_in_lyapunov():
    """Is Lyapunov spectrum related to η?"""
    print(f"\n--- η IN LYAPUNOV SPECTRUM ---")

    # From exp58: top eigenvalues 2.74, 2.49, 2.16, 2.11, 1.60, 1.55, 1.47, 1.44
    lyap = [2.74, 2.49, 2.16, 2.11, 1.60, 1.55, 1.47, 1.44]

    # Differences between consecutive eigenvalues
    print(f"Eigenvalue gaps:")
    for i in range(len(lyap)-1):
        gap = lyap[i] - lyap[i+1]
        ratio = gap / ETA
        print(f"  λ_{i+1}-λ_{i+2} = {gap:.4f} = {ratio:.1f}η")

    # Pipe pair gaps
    print(f"\nPipe pair gaps:")
    for i in range(0, 8, 2):
        gap = lyap[i] - lyap[i+1]
        ratio = gap / ETA
        print(f"  (λ_{i+1}, λ_{i+2}): gap = {gap:.4f} = {ratio:.1f}η")

    # Sum of all 8 / η
    total = sum(lyap)
    print(f"\nΣλ_top8 = {total:.4f} = {total/ETA:.1f}η")
    print(f"Σλ_top8 / 8 = {total/8:.4f} = {total/8/ETA:.1f}η")

def main():
    random.seed(42)
    print("="*60)
    print(f"EXP 82: η LAWS (η = {ETA:.10f})")
    print("="*60)
    test_rotation_carry_precision(5000)
    test_commutator_precision(5000)
    test_all_eta_multiples()
    test_eta_in_lyapunov()

    print("\n"+"="*60)
    print("If η governs UALRA → SHA-256 = function of ONE constant")
    print("="*60)

if __name__ == "__main__":
    main()
