"""
Witt-filtration analysis of SHA round operations.

Filtration F_k = set of Witt vectors with levels 0..k-1 = 0 (i.e., divisible by 2^k).

Question for each operation: does it preserve filtration?
  Preserves F_k means: if both inputs in F_k, output in F_k.
  Breaks F_k means: inputs in F_k, output NOT in F_k (levels 0..k-1 leak into).

Key result of pure algebra: filtration-preserving operations form a Rees-algebra
structure. Non-preserving operations break this structure.

For SHA: cataloging which ops preserve tells us where the "hardness" lives.

Additionally, for filtration-breaking ops, we can define OBSTRUCTION class:
  obstr_k(op, inputs) = first level where op(inputs) fails to be in F_k
"""

import random
from witt_vectors import (
    int_to_witt, witt_to_int, witt_add, witt_xor, witt_and, witt_not,
    witt_rotr, level, below_filtration, truncate_above
)


def test_filtration_preservation(op_func, op_name, n=16, k=4, n_trials=1000):
    """For random inputs in F_k, measure how often op output is in F_k."""
    random.seed(42)
    preserves = 0
    breaks = 0
    # Leak level: if output not in F_k, which level is nonzero first?
    leak_levels = {}
    for _ in range(n_trials):
        # Generate random Witt vectors IN F_k (levels 0..k-1 = 0)
        x_int = random.randint(0, 2**(n-k) - 1) << k  # shift to have zero low k bits
        y_int = random.randint(0, 2**(n-k) - 1) << k
        wx = int_to_witt(x_int, n)
        wy = int_to_witt(y_int, n)
        # Sanity: should be in F_k
        assert below_filtration(wx, k) and below_filtration(wy, k)

        # Apply operation
        try:
            if op_func.__code__.co_argcount == 2:
                out = op_func(wx, wy)
            else:
                out = op_func(wx)
        except Exception as e:
            print(f"  {op_name}: error {e}")
            return

        if below_filtration(out, k):
            preserves += 1
        else:
            breaks += 1
            # Find first leaking level
            for i in range(k):
                if out[i] != 0:
                    leak_levels[i] = leak_levels.get(i, 0) + 1
                    break

    percent_preserves = 100 * preserves / n_trials
    print(f"  {op_name:<20} preserves F_{k}: {percent_preserves:5.1f}% ({preserves}/{n_trials})")
    if leak_levels:
        print(f"    leak levels: {dict(sorted(leak_levels.items()))}")


def rotr_with_r(r):
    """Returns closure of ROTR with specific rotation amount."""
    return lambda a: witt_rotr(a, r)


def sigma_like(rotations):
    """Σ-like operation: XOR of rotations."""
    def op(a):
        result = tuple(0 for _ in a)
        for r in rotations:
            rotated = witt_rotr(a, r)
            result = witt_xor(result, rotated)
        return result
    return op


def ch_op(a, b):
    """Assumes we pass a=(e, f) and b=(g) — but we need 3 args.
    Let me redefine."""
    pass


def ch_3arg(e, f, g):
    """Ch(e, f, g) = (e & f) XOR (~e & g)"""
    return witt_xor(witt_and(e, f), witt_and(witt_not(e), g))


def maj_3arg(a, b, c):
    """Maj(a, b, c) = (a & b) XOR (a & c) XOR (b & c)"""
    return witt_xor(witt_xor(witt_and(a, b), witt_and(a, c)), witt_and(b, c))


def test_3arg_filtration(op_func, op_name, n=16, k=4, n_trials=1000):
    random.seed(42)
    preserves = 0
    for _ in range(n_trials):
        x_int = random.randint(0, 2**(n-k) - 1) << k
        y_int = random.randint(0, 2**(n-k) - 1) << k
        z_int = random.randint(0, 2**(n-k) - 1) << k
        wx = int_to_witt(x_int, n)
        wy = int_to_witt(y_int, n)
        wz = int_to_witt(z_int, n)
        out = op_func(wx, wy, wz)
        if below_filtration(out, k):
            preserves += 1
    print(f"  {op_name:<20} preserves F_{k}: {100 * preserves / n_trials:5.1f}%")


def main():
    n = 16
    k = 4

    print(f"=== Filtration analysis (n={n}, F_k with k={k}) ===\n")
    print("For each operation: if inputs ∈ F_k, is output ∈ F_k?\n")

    print("Binary operations:")
    test_filtration_preservation(witt_add, "ADD", n=n, k=k)
    test_filtration_preservation(witt_xor, "XOR", n=n, k=k)
    test_filtration_preservation(witt_and, "AND", n=n, k=k)

    print("\nUnary operations:")
    test_filtration_preservation(witt_not, "NOT", n=n, k=k)

    print("\nRotations:")
    for r in [1, 2, 4, 7, 8, 13]:
        test_filtration_preservation(rotr_with_r(r), f"ROTR_{r}", n=n, k=k)

    print("\nΣ-like (XOR of rotations, like SHA-256 Σ0 or Σ1):")
    sigma_0_style = sigma_like((2, 13, 22)) if n >= 22 else sigma_like((1, 3, 5))
    test_filtration_preservation(sigma_0_style, "Sig0-style", n=n, k=k)

    print("\n3-argument operations:")
    test_3arg_filtration(ch_3arg, "Ch(e,f,g)", n=n, k=k)
    test_3arg_filtration(maj_3arg, "Maj(a,b,c)", n=n, k=k)

    print("\n\n=== Now test with k=8 (deeper filtration) ===")
    k2 = 8
    test_filtration_preservation(witt_add, "ADD", n=n, k=k2)
    test_filtration_preservation(witt_xor, "XOR", n=n, k=k2)
    test_filtration_preservation(rotr_with_r(3), "ROTR_3", n=n, k=k2)
    test_filtration_preservation(rotr_with_r(7), "ROTR_7", n=n, k=k2)


if __name__ == "__main__":
    main()
