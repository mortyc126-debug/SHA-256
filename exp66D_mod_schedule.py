#!/usr/bin/env python3
"""
EXP 66D: A_MOD Schedule Nullity — Schedule in Z/2^32

Gap D: schedule nullity measured over GF(2) = 2 (exp65).
But schedule operates in Z/2^32, not GF(2).

W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]  (mod 2^32)

Fixed point in Z/2^32: W[16..31] = W[0..15] (mod 2^32).
This is a DIFFERENT equation than GF(2) fixed point.

The carry terms make Z/2^32 nullity potentially DIFFERENT from GF(2).
Could be larger (carry creates extra solutions) or smaller.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def schedule_one_step(W, t):
    """Single schedule step: W[t] from W[t-2], W[t-7], W[t-15], W[t-16]."""
    return (sig1(W[t-2]) + W[t-7] + sig0(W[t-15]) + W[t-16]) & MASK

def is_mod_fixed_point(W16):
    """Check: does W[16..31] = W[0..15] in Z/2^32?"""
    W = schedule(W16)
    for i in range(16):
        if W[16+i] != W16[i]:
            return False
    return True

def mod_fixed_point_residual(W16):
    """How close is W[16..31] to W[0..15]?"""
    W = schedule(W16)
    total_dist = 0
    for i in range(16):
        total_dist += hw(W[16+i] ^ W16[i])
    return total_dist

def test_mod_fixed_points(N=10000):
    """Search for Z/2^32 schedule fixed points."""
    print("\n--- Z/2^32 SCHEDULE FIXED POINT SEARCH ---")

    residuals = []
    best_residual = 999
    best_W = None

    for _ in range(N):
        W16 = random_w16()
        r = mod_fixed_point_residual(W16)
        residuals.append(r)
        if r < best_residual:
            best_residual = r
            best_W = list(W16)

    ra = np.array(residuals)
    print(f"Residual dist(W[16..31], W[0..15]):")
    print(f"  mean={ra.mean():.1f}, std={ra.std():.1f}")
    print(f"  min={ra.min()}, max={ra.max()}")
    print(f"  Expected (random): mean=256, std≈11.3")

    if ra.min() == 0:
        print(f"  *** EXACT FIXED POINT FOUND! ***")
    elif ra.min() < 200:
        print(f"  *** NEAR fixed point: residual={ra.min()} ***")

    # Hill-climb toward fixed point
    print(f"\nHill-climbing toward fixed point...")
    current = list(best_W)
    current_r = best_residual

    for step in range(5000):
        w=random.randint(0,15); b=random.randint(0,31)
        trial = list(current); trial[w] ^= (1<<b)
        r = mod_fixed_point_residual(trial)
        if r < current_r:
            current_r = r; current = trial

    print(f"  After hill-climb: residual={current_r} (from {best_residual})")
    if current_r == 0:
        print(f"  *** EXACT FIXED POINT FOUND BY HILL-CLIMB! ***")

    return current_r, current

def test_mod_period2(N=5000):
    """Search for period-2 points: W[32..47] = W[0..15] in Z/2^32."""
    print(f"\n--- Z/2^32 PERIOD-2 SEARCH ---")

    residuals = []
    for _ in range(N):
        W16 = random_w16()
        W = schedule(W16)

        # W[32..47] computed from further schedule expansion
        # Need W[32..47] = W[0..15]
        W_ext = list(W) + [0]*48
        for t in range(64, 112):
            W_ext.append((sig1(W_ext[t-2])+W_ext[t-7]+sig0(W_ext[t-15])+W_ext[t-16])&MASK)

        # Actually W[32..47] is already in the schedule (if it extends)
        # But standard schedule is only 64 words. We need to extend.
        dist = sum(hw(W_ext[32+i] ^ W16[i]) for i in range(16))
        residuals.append(dist)

    ra = np.array(residuals)
    print(f"Period-2 residual: mean={ra.mean():.1f}, min={ra.min()}")

def test_schedule_eigenvalues_mod(N=100):
    """
    Schedule as LINEAR map over Z/2^32 (not GF(2)).
    W[16..31] = M_mod · W[0..15] where M_mod operates in Z/2^32.

    Eigenvalues of M_mod (as integer matrix) might reveal structure.
    """
    print(f"\n--- SCHEDULE EIGENVALUES OVER Z ---")

    # Build M_mod: 16×16 matrix over Z/2^32
    # M_mod[i][j] = ∂W[16+i]/∂W[j] (numerical, finite differences)

    # Use small perturbation to estimate Jacobian
    W_base = [0]*16
    W_sched_base = schedule(W_base)

    M = np.zeros((16, 16), dtype=np.float64)

    for j in range(16):
        # Perturb W[j] by 1
        W_pert = [0]*16
        W_pert[j] = 1
        W_sched_pert = schedule(W_pert)

        for i in range(16):
            # Derivative ≈ (W_sched_pert[16+i] - W_sched_base[16+i]) / 1
            M[i][j] = (W_sched_pert[16+i] - W_sched_base[16+i]) & MASK
            if M[i][j] > MASK//2:
                M[i][j] -= (MASK+1)  # Signed

    # Eigenvalues
    eigvals = np.linalg.eigvals(M)
    eigvals_abs = np.sort(np.abs(eigvals))[::-1]

    print(f"Schedule Jacobian (at W=0) eigenvalues:")
    print(f"  Top 5 |λ|: {eigvals_abs[:5]}")
    print(f"  Bottom 5 |λ|: {eigvals_abs[-5:]}")

    # Fixed point: eigenvalue = 1
    near_one = [e for e in eigvals if abs(abs(e) - 1) < 0.1]
    print(f"  Eigenvalues near |λ|=1: {len(near_one)}")
    for e in near_one:
        print(f"    λ = {e}")

    # Spectral radius
    print(f"  Spectral radius: {eigvals_abs[0]:.4f}")
    if eigvals_abs[0] > 1:
        print(f"  Schedule is EXPANDING (spectral radius > 1)")
    else:
        print(f"  Schedule is CONTRACTING")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 66D: A_MOD SCHEDULE NULLITY")
    print("="*60)
    test_mod_fixed_points(5000)
    test_mod_period2(3000)
    test_schedule_eigenvalues_mod()

if __name__ == "__main__":
    main()
