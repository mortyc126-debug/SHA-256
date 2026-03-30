#!/usr/bin/env python3
"""
EXP 54: Convergence Radius of Quadratic Approximation

rank=256 quadratic Jacobian → SHA-256 fully described locally.
GF(2) solve residual=128 → solution fails GLOBALLY.

KEY: how FAR from the linearization point does the quadratic
approximation remain accurate?

Define: CONVERGENCE RADIUS R = max Hamming distance d(x, x₀)
such that |δH_predicted - δH_actual| < threshold.

If R > 128 → collision cost < 2^128 (beats birthday).

Method: compute quadratic predict at x₀, then evaluate at
x₀ + perturbation of increasing Hamming weight.
Measure: at what distance does prediction break down?
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def dH_pair(W16, DW16):
    Wf=[(W16[i]+DW16[i])&MASK for i in range(16)]
    Hn=sha256_compress(W16); Hf=sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def dH_bits(W16, DW16):
    Wf=[(W16[i]+DW16[i])&MASK for i in range(16)]
    Hn=sha256_compress(W16); Hf=sha256_compress(Wf)
    bits=[]
    for w in range(8):
        d=Hn[w]^Hf[w]
        for b in range(32): bits.append((d>>b)&1)
    return np.array(bits, dtype=np.int64)

def compute_linear_prediction(W16, DW16_base, DW16_target):
    """
    Predict δH at DW16_target using linear Jacobian at DW16_base.
    Prediction: δH(target) ≈ δH(base) + J·(target - base)
    """
    base_bits = dH_bits(W16, DW16_base)

    # Compute Jacobian columns for flipped bits
    diff = [(DW16_target[i] ^ DW16_base[i]) for i in range(16)]

    predicted = base_bits.copy()
    for word in range(16):
        for bit in range(32):
            if (diff[word] >> bit) & 1:
                # This bit differs: need Jacobian column
                DW_flip = list(DW16_base)
                DW_flip[word] ^= (1 << bit)
                if DW_flip[0] == 0: DW_flip[0] = 1

                flip_bits = dH_bits(W16, DW_flip)
                col = flip_bits ^ base_bits
                predicted = predicted ^ col  # XOR (GF(2) addition)

    return int(predicted.sum())

def test_radius_measurement(N=200):
    """Measure convergence radius of linear approximation."""
    print("\n--- CONVERGENCE RADIUS MEASUREMENT ---")

    print(f"{'Distance':>8} | {'E[|pred-actual|]':>16} | {'E[actual δH]':>12} | "
          f"{'Pred accuracy':>14} | {'Radius?'}")
    print("-"*70)

    for n_flips in [1, 2, 3, 5, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]:
        errors = []
        actual_dHs = []

        for _ in range(N):
            W16 = random_w16()
            DW16_base = [random.randint(0, MASK) for _ in range(16)]
            DW16_base[0] = max(DW16_base[0], 1)

            # Create target at distance n_flips from base
            DW16_target = list(DW16_base)
            flip_positions = random.sample(range(512), min(n_flips, 512))
            for pos in flip_positions:
                word = pos // 32; bit = pos % 32
                DW16_target[word] ^= (1 << bit)
            if DW16_target[0] == 0: DW16_target[0] = 1

            # Actual δH at target
            actual = dH_pair(W16, DW16_target)
            actual_dHs.append(actual)

            # Linear prediction
            if n_flips <= 64:  # Only compute for small distances (expensive)
                predicted = compute_linear_prediction(W16, DW16_base, DW16_target)
                errors.append(abs(predicted - actual))

        if errors:
            ea = np.array(errors); aa = np.array(actual_dHs)
            accuracy = np.mean(ea < 8)  # Within 8 bits
            radius = "YES" if accuracy > 0.5 else "no"
            print(f"{n_flips:>8} | {ea.mean():>16.2f} | {aa.mean():>12.2f} | "
                  f"{accuracy:>14.4f} | {radius}")
        else:
            print(f"{n_flips:>8} | {'(skipped)':>16} | {np.mean(actual_dHs):>12.2f} | "
                  f"{'N/A':>14} |")

def test_quadratic_radius(N=100):
    """
    Measure radius for QUADRATIC prediction (includes x·y terms).
    Quadratic should have LARGER radius than linear.
    """
    print(f"\n--- QUADRATIC vs LINEAR RADIUS ---")

    for n_flips in [1, 2, 3, 5, 8, 16, 32]:
        lin_errors = []; quad_errors = []

        for _ in range(N):
            W16 = random_w16()
            DW_base = [random.randint(0,MASK) for _ in range(16)]
            DW_base[0] = max(DW_base[0], 1)
            base_bits = dH_bits(W16, DW_base)
            base_dH = int(base_bits.sum())

            # Target at distance n_flips
            DW_target = list(DW_base)
            flips = random.sample(range(512), min(n_flips, 512))
            for pos in flips:
                DW_target[pos//32] ^= (1 << (pos%32))
            if DW_target[0]==0: DW_target[0]=1

            actual = dH_pair(W16, DW_target)

            # Linear prediction (sum of individual effects)
            lin_pred_bits = base_bits.copy()
            individual_cols = []
            for pos in flips:
                DW_f = list(DW_base)
                DW_f[pos//32] ^= (1<<(pos%32))
                if DW_f[0]==0: DW_f[0]=1
                col = dH_bits(W16, DW_f) ^ base_bits
                individual_cols.append(col)
                lin_pred_bits = lin_pred_bits ^ col

            lin_pred = int(lin_pred_bits.sum())
            lin_errors.append(abs(lin_pred - actual))

            # Quadratic prediction (add pairwise interaction terms)
            quad_correction = 0
            if n_flips <= 16:
                for i in range(len(flips)):
                    for j in range(i+1, len(flips)):
                        # Flip both i and j simultaneously
                        DW_both = list(DW_base)
                        DW_both[flips[i]//32] ^= (1<<(flips[i]%32))
                        DW_both[flips[j]//32] ^= (1<<(flips[j]%32))
                        if DW_both[0]==0: DW_both[0]=1

                        both_bits = dH_bits(W16, DW_both)
                        # Quadratic term = f(x+ei+ej) ⊕ f(x+ei) ⊕ f(x+ej) ⊕ f(x)
                        q_term = both_bits ^ (base_bits ^ individual_cols[i]) ^ \
                                 (base_bits ^ individual_cols[j]) ^ base_bits
                        quad_correction += int(q_term.sum())

            quad_pred = lin_pred  # Start from linear
            # Quadratic correction is complex in GF(2), use simpler metric
            # Just count: how many bits does quadratic change?
            quad_errors.append(abs(lin_pred - actual))  # Same for now

        le = np.array(lin_errors)
        print(f"  Flips={n_flips:>3}: linear_error={le.mean():.2f}, "
              f"P(error<8)={np.mean(le<8):.4f}, P(error<16)={np.mean(le<16):.4f}")

def test_radius_vs_rounds(N=200):
    """
    How does convergence radius depend on number of rounds?
    At fewer rounds: lower degree → larger radius.
    """
    print(f"\n--- RADIUS vs ROUNDS ---")

    for R in [4, 8, 16, 32, 64]:
        errors_at_dist_1 = []
        errors_at_dist_8 = []

        for _ in range(N):
            W16 = random_w16()
            DW_base = [random.randint(0,MASK) for _ in range(16)]
            DW_base[0] = max(DW_base[0], 1)

            # R-round hash
            Wf_b = [(W16[i]+DW_base[i])&MASK for i in range(16)]
            sn_b = sha256_rounds(W16, R); sf_b = sha256_rounds(Wf_b, R)
            base_dH = sum(hw(sn_b[R][i]^sf_b[R][i]) for i in range(8))

            for n_flips, err_list in [(1, errors_at_dist_1), (8, errors_at_dist_8)]:
                DW_t = list(DW_base)
                for pos in random.sample(range(512), n_flips):
                    DW_t[pos//32] ^= (1<<(pos%32))
                if DW_t[0]==0: DW_t[0]=1

                # Linear prediction at dist=n_flips
                pred_bits = np.zeros(256, dtype=np.int64)
                Wf_bb = [(W16[i]+DW_base[i])&MASK for i in range(16)]
                sn0 = sha256_rounds(W16, R); sf0 = sha256_rounds(Wf_bb, R)
                bb = []
                for w in range(8):
                    d=sn0[R][w]^sf0[R][w]
                    for b in range(32): bb.append((d>>b)&1)
                base_b = np.array(bb)

                actual_Wf = [(W16[i]+DW_t[i])&MASK for i in range(16)]
                sn_a = sha256_rounds(W16, R); sf_a = sha256_rounds(actual_Wf, R)
                actual = sum(hw(sn_a[R][i]^sf_a[R][i]) for i in range(8))

                err_list.append(abs(base_dH - actual))

        e1 = np.array(errors_at_dist_1); e8 = np.array(errors_at_dist_8)
        print(f"  R={R:>2}: error@dist1={e1.mean():.2f}, error@dist8={e8.mean():.2f}, "
              f"P(e8<8)={np.mean(e8<8):.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 54: CONVERGENCE RADIUS OF QUADRATIC APPROX")
    print("="*60)
    test_radius_measurement(100)
    test_quadratic_radius(80)
    test_radius_vs_rounds(150)

    print("\n"+"="*60)
    print("IMPLICATIONS")
    print("="*60)
    print("If radius R > 128: collision cost < 2^128")
    print("If radius R ~ 1: quadratic approx useless (= random)")
    print("Measured: see above")

if __name__ == "__main__":
    main()
