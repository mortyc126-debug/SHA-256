#!/usr/bin/env python3
"""
EXP 186: HACK THE THERMOSTAT + DEEPER INTO MEAN REVERSION

★-Theorem 16: δ(a,e) reverts to mean with Z=98.4.
The system ACTIVELY maintains δ=32.

TRACK A: HACK THE THERMOSTAT
  The thermostat = negative feedback loop.
  To hack it: break the feedback. HOW?
  Feedback = high δ → many P → carry cascades → compensation.
  Break: choose δM where P-chains DON'T cascade properly.

TRACK B: DEEPER INTO MEAN REVERSION
  WHY does reversion happen? Exact mechanism.
  Is the reversion SPEED constant or variable?
  Can we find spots where reversion is SLOW?

TRACK C: ASYMMETRY
  Reversion from HIGH δ is well-documented.
  What about reversion from LOW δ? Is it SYMMETRIC?
  If LOW δ reverts SLOWER → we can exploit the asymmetry.
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def ae_dist_at(M1, M2, r):
    s1 = sha256_rounds(M1, r)[r]
    s2 = sha256_rounds(M2, r)[r]
    return hw(s1[0] ^ s2[0]) + hw(s1[4] ^ s2[4])

def extended_ae_trajectory(M1, M2, max_r=64):
    s1 = sha256_rounds(M1, max_r)
    s2 = sha256_rounds(M2, max_r)
    return [hw(s1[r][0] ^ s2[r][0]) + hw(s1[r][4] ^ s2[r][4]) for r in range(max_r+1)]

# ============================================================
# TRACK A: HACK THE THERMOSTAT
# ============================================================
def hack_thermostat(N=500):
    """Try to PREVENT mean reversion after a dip."""
    print(f"\n{'='*60}")
    print(f"TRACK A: HACK THE THERMOSTAT")
    print(f"{'='*60}")

    # The thermostat: high δ → more P → carry cascade → δ drops.
    # To hack: need δM where nP stays LOW even when δ is high.
    # nP = HW(a₁⊕a₂) = δa. So nP IS δa. Can't decouple.

    # Alternative hack: make the CARRY CASCADES non-compensating.
    # Carry compensates when carry_diff aligns with XOR_diff.
    # If carry_diff is ORTHOGONAL to XOR_diff → no compensation.

    # Test: after a DIP (low δ), how fast does δ RECOVER?
    # If some messages recover SLOWLY → thermostat is WEAK for them.

    recovery_times = []
    post_dip_trajectories = []

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[random.randint(12,15)] ^= (1 << random.randint(0,31))

        traj = extended_ae_trajectory(M1, M2)

        # Find dips (δ < 25) after round 30
        for r in range(30, 60):
            if traj[r] < 25:
                # Measure recovery: rounds until δ > 30 again
                recovery = 0
                for r2 in range(r+1, min(r+20, 65)):
                    if traj[r2] > 30:
                        recovery = r2 - r
                        break
                if recovery > 0:
                    recovery_times.append(recovery)
                    post_dip_trajectories.append(traj[r:min(r+15,65)])
                break

    if recovery_times:
        rt = np.array(recovery_times)
        print(f"\n  Recovery time after dip (dip=δ<25, recovered=δ>30):")
        print(f"    Mean: {rt.mean():.2f} rounds")
        print(f"    Median: {np.median(rt):.0f}")
        print(f"    Max: {rt.max()}")
        print(f"    Distribution:")
        for t in [1, 2, 3, 4, 5, 8, 10]:
            count = np.sum(rt == t)
            pct = count / len(rt) * 100
            bar = "█" * int(pct)
            print(f"      t={t}: {pct:>5.1f}% {bar}")

        # KEY: how often does δ stay LOW for 3+ rounds?
        slow_recoveries = np.sum(rt >= 3)
        print(f"\n    Slow recoveries (≥3 rounds): {slow_recoveries}/{len(rt)} ({slow_recoveries/len(rt)*100:.1f}%)")

        if slow_recoveries > len(rt) * 0.1:
            print(f"    ★★ THERMOSTAT IS SLOW! {slow_recoveries/len(rt)*100:.0f}% take ≥3 rounds")
    else:
        print(f"  No dips found")

# ============================================================
# TRACK B: REVERSION SPEED — Is it constant?
# ============================================================
def reversion_speed(N=1000):
    """Measure exact reversion speed as function of δ."""
    print(f"\n{'='*60}")
    print(f"TRACK B: REVERSION SPEED vs δ")
    print(f"{'='*60}")

    # For each δ value (20-44): average change at next round
    delta_at = {d: [] for d in range(15, 50)}

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[random.randint(12,15)] ^= (1 << random.randint(0,31))

        traj = extended_ae_trajectory(M1, M2)

        for r in range(30, 64):
            d = traj[r]
            if 15 <= d < 50:
                change = traj[r+1] - d if r < 64 else 0
                delta_at[d].append(change)

    print(f"\n  δ(a,e) → E[Δ at next round] (reversion curve):")
    print(f"  {'δ':>4} | {'E[Δ]':>7} | {'N':>5} | {'Direction':>10} | Visual")
    print(f"  " + "-" * 55)

    for d in range(18, 46):
        if len(delta_at[d]) > 10:
            arr = np.array(delta_at[d])
            mean_change = arr.mean()
            direction = "← PULL" if mean_change < -0.5 else ("→ PUSH" if mean_change > 0.5 else "= NEUTRAL")
            bar_len = int(abs(mean_change) * 5)
            bar = ("◄" * bar_len if mean_change < 0 else "►" * bar_len)
            print(f"  {d:>4} | {mean_change:>+7.2f} | {len(delta_at[d]):>5} | {direction:>10} | {bar}")

    # Find the EQUILIBRIUM POINT (where E[Δ]=0)
    for d in range(20, 40):
        if len(delta_at[d]) > 10 and len(delta_at.get(d+1, [])) > 10:
            m1 = np.mean(delta_at[d])
            m2 = np.mean(delta_at[d+1])
            if m1 > 0 and m2 <= 0:
                eq_point = d + m1 / (m1 - m2)
                print(f"\n  EQUILIBRIUM POINT: δ* = {eq_point:.1f}")
                print(f"  (System pulls δ toward this value)")
                break

# ============================================================
# TRACK C: ASYMMETRY — up vs down
# ============================================================
def reversion_asymmetry(N=800):
    """Is reversion from LOW δ different from HIGH δ?"""
    print(f"\n{'='*60}")
    print(f"TRACK C: REVERSION ASYMMETRY")
    print(f"{'='*60}")

    from_low = []   # δ < 25: how fast back to 32?
    from_high = []  # δ > 39: how fast back to 32?

    for _ in range(N):
        M1 = random_w16(); M2 = list(M1)
        M2[random.randint(12,15)] ^= (1 << random.randint(0,31))

        traj = extended_ae_trajectory(M1, M2)

        for r in range(30, 60):
            if traj[r] < 25:
                # Recovery from LOW
                speed = traj[r+1] - traj[r] if r < 64 else 0
                from_low.append(speed)
            elif traj[r] > 39:
                # Recovery from HIGH
                speed = traj[r+1] - traj[r] if r < 64 else 0
                from_high.append(speed)

    fl = np.array(from_low) if from_low else np.array([0])
    fh = np.array(from_high) if from_high else np.array([0])

    print(f"\n  Reversion from LOW δ (<25): N={len(fl)}")
    print(f"    E[Δ] = {fl.mean():+.2f} (positive = rises back)")
    print(f"    Std = {fl.std():.2f}")

    print(f"\n  Reversion from HIGH δ (>39): N={len(fh)}")
    print(f"    E[Δ] = {fh.mean():+.2f} (negative = drops back)")
    print(f"    Std = {fh.std():.2f}")

    # ASYMMETRY: is |rise speed| = |drop speed|?
    rise_speed = abs(fl.mean())
    drop_speed = abs(fh.mean())
    ratio = rise_speed / drop_speed if drop_speed > 0 else float('inf')

    print(f"\n  ASYMMETRY:")
    print(f"    Rise speed (from low): {rise_speed:.2f}")
    print(f"    Drop speed (from high): {drop_speed:.2f}")
    print(f"    Ratio rise/drop: {ratio:.3f}")

    if ratio < 0.8:
        print(f"    ★★★ ASYMMETRIC! Rise is SLOWER than drop!")
        print(f"    → System spends MORE TIME at low δ")
        print(f"    → Low δ (near-collision) is MORE ACCESSIBLE")
    elif ratio > 1.2:
        print(f"    ★★ ASYMMETRIC! Rise is FASTER than drop.")
        print(f"    → System spends LESS time at low δ")
    else:
        print(f"    Symmetric (rise ≈ drop)")

def thermostat_formula():
    """Derive the thermostat formula."""
    print(f"\n{'='*60}")
    print(f"★-THEOREM 16: THERMOSTAT FORMULA")
    print(f"{'='*60}")

    print(f"""
  From exp185: E[δ(a,e)[r+1] | δ(a,e)[r] = d] = α·d + β

  From exp184: dH[r+1] = 0.694 × dH[r] + 39.15

  For δ(a,e) (64 bits): similar regression
  E[δ(a,e)[r+1]] = α × δ(a,e)[r] + (1-α) × 32

  Where α < 1 = reversion coefficient.
  α = 0.694 from dH regression (exp184).

  This means: δ(a,e) at round r+1 is a WEIGHTED AVERAGE of:
    - Current value (weight α ≈ 0.69)
    - Equilibrium 32 (weight 1-α ≈ 0.31)

  The thermostat PULLS δ toward 32 with force (1-α)·(δ-32)
  per round. This is an ORNSTEIN-UHLENBECK process:

    dδ = -κ(δ - μ)dt + σ·dW

  Where:
    κ = 1-α ≈ 0.31 = reversion rate
    μ = 32 = equilibrium
    σ = noise amplitude ≈ 5.4

  IMPLICATION: The probability of δ dipping to k bits is:
    P(δ < k) ~ exp(-(32-k)²/(2σ²/κ))
             ~ exp(-(32-k)²/188)

  For collision k=0: P(δ=0) ~ exp(-32²/188) ~ exp(-5.4) ~ 0.004

  BUT: this is per-ROUND probability in steady state.
  Over 44 dead-zone rounds: P(any dip to 0) ~ 44 × 0.004 ~ 0.18?!

  WAIT — that's way too optimistic. Let me check...
  exp(-5.4) = 0.0045 — that's P(δ < 0 for Gaussian), not P(δ = 0).
  δ is INTEGER (0-64), and P(δ=0) for binomial(64,0.5) = 2^(-64).
  The Ornstein-Uhlenbeck approximation is WRONG at the tails!
    """)

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 186: THERMOSTAT + REVERSION + ASYMMETRY")
    print("=" * 60)

    hack_thermostat(N=400)
    reversion_speed(N=600)
    reversion_asymmetry(N=600)
    thermostat_formula()

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
