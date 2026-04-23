"""
Session 11: Künneth formula for multi-register SHA rotation ring.

SHA-256 state = 8 registers × 32-bit.
Rotation ring per register = F_2[s_i]/(s_i^16) (Session 9).
Per-register cohomology: H⁰ = Z_2, H¹ = (as computed Session 10), H^≥2 = 0.

Full rotation ring = R = ⊗_{i=1..8} F_2[s_i]/(s_i^16).

KÜNNETH FORMULA (classical, for smooth case over field):
  H^n(R_1 ⊗ R_2) = ⊕_{i+j=n} H^i(R_1) ⊗ H^j(R_2)

For Z_2-module case (with torsion), there are Tor corrections, but for
our SPLIT case (H⁰ free, H¹ torsion, H^≥2 = 0), the formula simplifies.

Over Z_2:
  Z_2 ⊗_{Z_2} Z_2 = Z_2
  Z_2 ⊗_{Z_2} Z/2^a = Z/2^a
  Z/2^a ⊗_{Z_2} Z/2^b = Z/2^min(a,b)

For n copies of (R = F_2[s]/(s^d)):
  H^0(R^⊗n) = Z_2
  H^1(R^⊗n) = ⊕_{i=1..n} (H^1(R) viewed as summand, others contribute H⁰ = Z_2)
             = n · H^1(R)  (direct sum)
  H^2(R^⊗n) = ⊕_{i<j} H^1(R_i) ⊗ H^1(R_j)  (pair choices)
  ...
  H^k(R^⊗n) = ⊕_{I ⊂ {1..n}, |I|=k} ⊗_{i∈I} H^1(R_i)

For SHA-256: n = 8, d = 16. Compute all H^k for k = 0..8.

(Note: real SHA has MORE structure than rotation — ADD, XOR, AND — will add
later. Session 11 focuses on rotation layer only.)
"""

import math


def v_2(k):
    if k == 0: return float('inf')
    count = 0
    while k % 2 == 0:
        k //= 2
        count += 1
    return count


def H1_structure(d):
    """Structure of H¹(F_2[s]/(s^d)) from Session 10 theorem.
    Returns list of exponents a_i such that H¹ = ⊕ Z/2^{a_i}."""
    exponents = []
    for k in range(1, d, 2):  # odd k from 1 to d-1
        exponents.append(v_2(k + 1))
    return exponents


def tensor_product_cyclic_Z2(exponents_1, exponents_2):
    """Tensor product of two finite abelian 2-groups over Z_2.
    Z/2^a ⊗ Z/2^b = Z/2^min(a,b).
    Returns list of exponents for the tensor product."""
    result = []
    for a in exponents_1:
        for b in exponents_2:
            result.append(min(a, b))
    return result


def structure_order(exponents):
    """Total order of cyclic group with given exponents."""
    return sum(exponents)  # log_2 of order


def print_group(name, exponents):
    # Sort and group
    from collections import Counter
    c = Counter(exponents)
    parts = []
    for exp in sorted(c.keys()):
        count = c[exp]
        if count == 1:
            parts.append(f"Z/2^{exp}")
        else:
            parts.append(f"(Z/2^{exp})^{count}")
    if parts:
        summary = " ⊕ ".join(parts)
    else:
        summary = "0"
    print(f"  {name}: {summary}")
    order_exp = structure_order(exponents)
    if exponents:
        print(f"    order = 2^{order_exp}, number of cyclic factors = {len(exponents)}")


def kunneth_sha_cohomology(n_registers=8, d=16):
    """Compute H^k(R^⊗n) for k = 0..n, where R = F_2[s]/(s^d)."""
    print(f"\n=== H*(R^⊗{n_registers}) where R = F_2[s]/(s^{d}) ===")

    H1_exp = H1_structure(d)  # exponents for H¹(R)
    print(f"  Single register H¹: {H1_exp} (sum = {sum(H1_exp)})")
    print(f"  |H¹(R)| = 2^{sum(H1_exp)}")
    print()

    # Each H^k(R^⊗n) for k ≤ n: choose k registers to contribute H¹, rest H⁰
    # For chosen k-subset I: contribute ⊗_{i∈I} H¹(R_i)
    # Tensor product of k copies of H¹ over Z_2
    print(f"  H^k structure:")
    total_log_order = 0
    for k in range(0, min(n_registers, 8) + 1):
        # Number of k-subsets of {1..n}
        num_subsets = math.comb(n_registers, k)
        if k == 0:
            # H⁰ = Z_2 (one copy per tensor factor, Künneth gives Z_2)
            print(f"  H⁰: Z_2 (rank 1 free)")
            continue
        # For each k-subset, compute tensor product of k copies of H¹
        # But they all have same exponents, so single tensor product suffices
        if k == 1:
            tensor_exp = list(H1_exp)
        else:
            # Iterated tensor over Z_2 of k copies of (Z/2^{a_1} ⊕ ... ⊕ Z/2^{a_m})
            tensor_exp = H1_exp.copy()
            for _ in range(k - 1):
                tensor_exp = tensor_product_cyclic_Z2(tensor_exp, H1_exp)

        # Each k-subset contributes same tensor product (indistinguishable)
        all_factors = tensor_exp * num_subsets
        print(f"  H^{k}: {num_subsets} copies of ⊗^{k}(H¹(R))")
        print(f"      per copy: {len(tensor_exp)} factors, sum = {sum(tensor_exp)}")
        total_this = num_subsets * sum(tensor_exp)
        total_log_order += total_this
        print(f"      TOTAL order: 2^{total_this}")

    print(f"\n  GRAND TOTAL cohomology order: 2^{total_log_order}")
    return total_log_order


def compare_to_sha_security():
    total_log = kunneth_sha_cohomology(n_registers=8, d=16)
    print(f"\n=== Comparison to SHA-256 Security ===")
    print(f"  Total cohomology \"size\": 2^{total_log}")
    print(f"  SHA-256 birthday: 2^128")
    print(f"  Difference: 2^{abs(total_log - 128)}")
    if total_log >= 128:
        print(f"  Cohomology CAPTURES ≥ birthday bound. Potentially enough for attack.")
    else:
        print(f"  Cohomology captures 2^{total_log}, shy of 2^128. Need more structure.")


def detailed_H1_for_n_registers():
    """Specifically H¹(R^⊗n) — the 'level-1' cohomology, most accessible."""
    print("\n=== H¹(R^⊗n) — rotation cohomology of n registers ===")
    H1_single = H1_structure(16)
    print(f"  H¹(F_2[s]/(s^16)) per register: {H1_single} (order 2^{sum(H1_single)})")
    for n in [1, 2, 4, 8]:
        # H¹(R^⊗n) = n copies of H¹(R)
        total_exp = H1_single * n
        total_order_log = sum(total_exp)
        print(f"  n = {n} registers:  H¹ = {n} × (per-register) = order 2^{total_order_log}, "
              f"{len(total_exp)} cyclic factors")


if __name__ == "__main__":
    # Review single register
    H1_single = H1_structure(16)
    print("=== SHA-256 per-register rotation cohomology (Session 10 theorem) ===")
    print(f"  H¹(F_2[s]/(s^16)) exponents: {H1_single}")
    print(f"  Order: 2^{sum(H1_single)} = {2**sum(H1_single)}")

    detailed_H1_for_n_registers()

    print("\n")
    compare_to_sha_security()
