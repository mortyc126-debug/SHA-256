#!/usr/bin/env python3
"""
EXP 120: 2-Adic Newton's Method for Collision Equation

The collision equation: δH = δα ⊕ 2·δC = 0 (per word)
Equivalently: IV + s₁ = IV + s₂ mod 2^32 for each word
Which means: s₁ = s₂ mod 2^32 (states must be identical)

STANDARD Newton: works on real/complex numbers. Needs smooth f.
2-ADIC Newton: works on p-adic integers (here p=2).
  Key: mod 2^32 arithmetic IS 2-adic (2-adic integers truncated to 32 digits).

2-ADIC NEWTON FOR SHA-256:
  f(M) = SHA256(M) - target (want f = 0)
  But for collision: f(M, M') = SHA256(M) - SHA256(M') = 0

  Newton step: M_{n+1} = M_n - f(M_n) / f'(M_n)
  In 2-adic: division by f' requires f' to be a 2-adic unit (odd number).

PROBLEM: f' is the Jacobian of SHA-256, which is 512×256 matrix.
  Division = pseudo-inverse = least-squares solution.

★-NATIVE NEWTON: Instead of standard 2-adic Newton, use ★-operations.
  ★-derivative? ★-Newton step? These need to be INVENTED.

Test:
1. Standard 2-adic Newton on reduced-round SHA-256
2. If it fails → build ★-Newton and compare
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def sha256_reduced(W16, R=64):
    """SHA-256 with R rounds, returning hash."""
    states = sha256_rounds(W16, R)
    return [(IV[i] + states[R][i]) & MASK for i in range(8)]

def hash_diff_arith(H1, H2):
    """Arithmetic difference of hashes: (H1[w] - H2[w]) mod 2^32."""
    return [(H1[w] - H2[w]) & MASK for w in range(8)]

def hash_diff_hw(H1, H2):
    """Total HW of arithmetic difference."""
    d = hash_diff_arith(H1, H2)
    return sum(hw(d[w]) for w in range(8))

def padic_newton_1d(target_hash_word, iv_word, R=4, max_iter=100):
    """1D 2-adic Newton: find W[0] such that hash_word = target.

    Only modifies W[0], keeping rest fixed. Only looks at H[0].
    This is a massive simplification but tests the principle."""

    # f(x) = H[0](x, 0, 0, ..., 0) - target mod 2^32
    # Want f(x) = 0

    W16 = [0] * 16
    x = random.randint(0, MASK)
    W16[0] = x

    for iteration in range(max_iter):
        # Compute f(x)
        W16[0] = x
        H = sha256_reduced(W16, R)
        f_x = (H[0] - target_hash_word) & MASK

        if f_x == 0:
            return x, iteration + 1, True  # Found!

        # Compute f'(x) ≈ (f(x+1) - f(x)) / 1 (2-adic derivative)
        W16[0] = (x + 1) & MASK
        H_next = sha256_reduced(W16, R)
        f_x1 = (H_next[0] - target_hash_word) & MASK

        f_prime = (f_x1 - f_x) & MASK

        # 2-adic Newton: x_new = x - f(x) / f'(x) mod 2^32
        # Need f'(x) to be odd (2-adic unit) for division to work
        if f_prime == 0:
            # Derivative is zero — can't continue, perturb
            x = random.randint(0, MASK)
            continue

        # 2-adic division: f(x) / f'(x) mod 2^32
        # This requires f'(x) to be odd. If even, extract factors of 2.
        v2_prime = 0
        fp = f_prime
        while fp > 0 and (fp & 1) == 0:
            fp >>= 1
            v2_prime += 1

        if v2_prime > 0:
            # f' has 2-adic valuation v2_prime
            # Newton only converges if v(f) ≥ 2·v(f')
            v2_f = 0
            ff = f_x
            while ff > 0 and (ff & 1) == 0:
                ff >>= 1
                v2_f += 1

            if v2_f < 2 * v2_prime:
                # Hensel condition fails — try random restart
                x = random.randint(0, MASK)
                continue

        # Compute modular inverse of f'(x) mod 2^32
        # Using extended Euclidean or Fermat
        try:
            fp_inv = pow(f_prime, -1, 1 << 32)
        except (ValueError, ZeroDivisionError):
            x = random.randint(0, MASK)
            continue

        step = (f_x * fp_inv) & MASK
        x = (x - step) & MASK

    return x, max_iter, False

def test_padic_newton_reduced(N=200):
    """Test 2-adic Newton on reduced-round SHA-256."""
    print(f"\n--- 2-ADIC NEWTON: REDUCED ROUNDS (N={N}) ---")

    for R in [1, 2, 3, 4, 8, 16, 32, 64]:
        successes = 0
        total_iters = 0

        for _ in range(N):
            # Random target
            target_W16 = random_w16()
            target_H = sha256_reduced(target_W16, R)

            # Try to find preimage of H[0] using Newton
            _, iters, found = padic_newton_1d(target_H[0], IV[0], R, max_iter=50)
            if found:
                successes += 1
            total_iters += iters

        rate = successes / N
        avg_iter = total_iters / N
        print(f"  {R:>2} rounds: success={rate:.4f}, avg_iter={avg_iter:.1f}")

def test_padic_collision_newton(N=500):
    """2-adic Newton for COLLISION: find M' given M such that H(M')=H(M)."""
    print(f"\n--- 2-ADIC COLLISION NEWTON ---")

    for R in [1, 2, 3, 4]:
        successes = 0
        best_dH = 256

        for trial in range(N):
            M1 = random_w16()
            H_target = sha256_reduced(M1, R)

            # Start with random M2, try to Newton-iterate to H(M2) = H_target
            M2 = random_w16()

            for iteration in range(100):
                H2 = sha256_reduced(M2, R)
                diff = hash_diff_arith(H_target, H2)
                dH = sum(hw(diff[w]) for w in range(8))

                if dH == 0 and M1 != M2:
                    successes += 1
                    break

                if dH < best_dH and M1 != M2:
                    best_dH = dH

                # Newton-like step: perturb M2[0] to reduce diff
                # Compute Jacobian approximation: how does changing M2[0] affect H?
                M2_test = list(M2)
                M2_test[0] = (M2[0] + 1) & MASK
                H2_test = sha256_reduced(M2_test, R)
                J = [(H2_test[w] - H2[w]) & MASK for w in range(8)]

                # Step: M2[0] -= diff[0] / J[0]
                if J[0] != 0:
                    try:
                        J_inv = pow(J[0], -1, 1 << 32)
                        step = (diff[0] * J_inv) & MASK
                        M2[0] = (M2[0] + step) & MASK
                    except:
                        M2[0] = random.randint(0, MASK)
                else:
                    M2[0] = random.randint(0, MASK)

        rate = successes / N
        print(f"  {R} rounds: collisions={successes}/{N}, best_dH={best_dH}")

def test_star_newton(N=500):
    """★-native Newton: use ★-operations instead of standard arithmetic.

    Standard Newton: x_{n+1} = x_n - f(x_n)/f'(x_n)  [in Z/2^32Z]
    ★-Newton: x_{n+1} = x_n ★_subtract ★_div(f(x_n), f'(x_n))

    where ★_subtract(a,b) = π_add(★(a, complement(b)))
    and ★_div needs to be DEFINED natively."""
    print(f"\n--- ★-NATIVE NEWTON (N={N}) ---")

    # ★-Newton step:
    # f(x) = SHA(x) (or reduced rounds)
    # Target: f(M') = f(M) = H
    #
    # In ★-space: f maps ★-pair to ★-pair
    # ★(IV, state) → hash
    #
    # The "★-derivative" at point x:
    # D_★f(x) = lim_{ε→0_★} ★(f(x ★ ε), f(x)) where ε → identity of ★
    #
    # But ★ has no natural "small ε" (it's discrete)!
    # Instead: use BIT-LEVEL ★-derivative
    # D_i f(x) = f(x ⊕ e_i) ⊕ f(x) (flip bit i, measure XOR change)
    # D_i^★ f(x) = ★(f(x ⊕ e_i), f(x)) (flip bit i, measure ★ change)

    for R in [1, 2, 4]:
        successes = 0
        best_dH = 256

        for _ in range(N):
            M1 = random_w16()
            H_target = sha256_reduced(M1, R)
            M2 = random_w16()

            for iteration in range(200):
                H2 = sha256_reduced(M2, R)
                dH_xor = sum(hw(H_target[w] ^ H2[w]) for w in range(8))

                if dH_xor == 0 and M1 != M2:
                    successes += 1
                    break

                if dH_xor < best_dH and M1 != M2:
                    best_dH = dH_xor

                # ★-Newton step: find the bit flip that MAXIMALLY reduces dH
                # This is a ★-gradient descent
                best_bit = -1
                best_improvement = 0

                # Sample random bits (checking all 512 is expensive)
                for _ in range(32):
                    w_idx = random.randint(0, 15)
                    b_idx = random.randint(0, 31)

                    M2_flip = list(M2)
                    M2_flip[w_idx] ^= (1 << b_idx)
                    H2_flip = sha256_reduced(M2_flip, R)
                    dH_flip = sum(hw(H_target[w] ^ H2_flip[w]) for w in range(8))

                    improvement = dH_xor - dH_flip
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_bit = (w_idx, b_idx)

                if best_bit != (-1):
                    # Apply best flip
                    M2[best_bit[0]] ^= (1 << best_bit[1])
                else:
                    # No improvement found — random restart
                    w_idx = random.randint(0, 15)
                    M2[w_idx] = random.randint(0, MASK)

        rate = successes / N
        print(f"  ★-Newton {R} rounds: collisions={successes}/{N}, best_dH={best_dH}")

    # Compare: pure random search
    print(f"\n  Comparison: random search")
    for R in [1, 2, 4]:
        successes = 0
        for _ in range(N):
            M1 = random_w16()
            H_target = sha256_reduced(M1, R)
            for attempt in range(200 * 32):  # Same budget as ★-Newton
                M2 = random_w16()
                H2 = sha256_reduced(M2, R)
                if sum(hw(H_target[w] ^ H2[w]) for w in range(8)) == 0 and M1 != M2:
                    successes += 1
                    break
        print(f"  Random {R} rounds: collisions={successes}/{N}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 120: 2-ADIC & ★-NEWTON")
    print("Standard 2-adic → ★-native Newton for collision")
    print("=" * 60)

    test_padic_newton_reduced(100)
    test_padic_collision_newton(200)
    test_star_newton(100)

    print(f"\n{'='*60}")
    print(f"VERDICT: Newton methods for SHA-256")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
