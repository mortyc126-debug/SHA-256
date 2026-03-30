#!/usr/bin/env python3
"""
EXP 66B: Non-Polynomial Representation — Walsh-Hadamard over Z/2^32

Gap A: polynomial (ANF) representation has degree 32, R=1.
Need: NON-POLYNOMIAL representation where SHA-256 is simpler.

Walsh-Hadamard Transform: f_hat(s) = Σ_x (-1)^{<s,x>} f(x)
In Walsh domain: XOR = pointwise multiply, but MOD-ADD = convolution.

If SHA-256 has SPARSE Walsh spectrum → collision = finding
cancellation in Walsh domain → potentially cheaper.

Also: Carry Transform from methodology:
CT[f](a) = Σ_x f(x)·(-1)^{overflow(a,x)}
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def partial_walsh(W16_base, output_bit_w, output_bit_b, n_samples=1000):
    """
    Estimate Walsh coefficient for one output bit.
    f_hat(s) ≈ (1/N) Σ (-1)^{<s,x> ⊕ f(x)[bit]}

    For specific s-vectors (sparse).
    """
    base_H = sha256_compress(W16_base)
    base_bit = (base_H[output_bit_w] >> output_bit_b) & 1

    # Test sparse Walsh coefficients: s = e_i (single input bit)
    coefficients = []
    for input_bit in range(512):
        w = input_bit // 32; b = input_bit % 32
        # Estimate: correlation between input bit and output bit
        agree = 0
        for _ in range(n_samples):
            x = random_w16()
            H = sha256_compress(x)
            out_bit = (H[output_bit_w] >> output_bit_b) & 1
            in_bit = (x[w] >> b) & 1
            if out_bit == in_bit:
                agree += 1
        bias = (2*agree/n_samples - 1)  # Walsh coefficient
        coefficients.append(bias)

    return np.array(coefficients)

def test_walsh_sparsity(N=200):
    """Is SHA-256 Walsh spectrum sparse?"""
    print("\n--- WALSH SPARSITY TEST ---")

    # For one output bit: how many Walsh coefficients are non-negligible?
    coeffs = partial_walsh([0]*16, 0, 0, n_samples=N)

    non_zero = np.sum(np.abs(coeffs) > 3/np.sqrt(N))
    max_coeff = np.max(np.abs(coeffs))

    print(f"Output bit H[0] bit 0:")
    print(f"  Non-zero Walsh coefficients (>3σ): {non_zero}/512")
    print(f"  Max |coefficient|: {max_coeff:.6f}")
    print(f"  Expected (random): ~{512*0.003:.1f} non-zero, max≈{3/np.sqrt(N):.4f}")

    if non_zero < 50:
        print(f"  *** SPARSE: only {non_zero} non-zero! ***")
    else:
        print(f"  Dense (≈ random function)")

    return coeffs

def test_carry_transform_spectrum(N=500):
    """Carry Transform spectrum of SHA-256."""
    print(f"\n--- CARRY TRANSFORM SPECTRUM ---")

    # CT[f](a) = Σ_x f(x)·(-1)^{overflow(a,x)}
    # overflow(a,x) = 1 if a+x ≥ 2^32 (word overflow)

    # For one output bit: estimate CT for sparse a-values
    print("Computing carry transform for H[0] bit 0...")
    ct_values = []

    for trial in range(min(N, 100)):
        a = random.randint(0, MASK)

        # Estimate CT[f](a) = E[(-1)^{overflow(a,x)} · (-1)^{f(x)}]
        total = 0
        for _ in range(N):
            x = random_w16()
            H = sha256_compress(x)
            f_bit = (H[0] >> 0) & 1

            # Overflow of a + x[0]
            overflow = 1 if (a + x[0]) >= (1 << 32) else 0

            sign = (-1)**(overflow ^ f_bit)
            total += sign

        ct_val = total / N
        ct_values.append(ct_val)

    ct = np.array(ct_values)
    print(f"CT spectrum: mean={ct.mean():.6f}, std={ct.std():.6f}")
    print(f"Max |CT|: {np.max(np.abs(ct)):.6f}")
    print(f"Expected (random): mean≈0, std≈{1/np.sqrt(N):.4f}")

    if np.max(np.abs(ct)) > 5/np.sqrt(N):
        print(f"*** CARRY TRANSFORM has non-trivial structure! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 66B: NON-POLYNOMIAL REPRESENTATION")
    print("="*60)
    test_walsh_sparsity(150)
    test_carry_transform_spectrum(200)

if __name__ == "__main__":
    main()
