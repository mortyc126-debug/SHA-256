"""
Witt-vector arithmetic over F_2.

We identify Z/2^n with W_n(F_2) (Witt vectors of length n over F_2).

Elements: tuples (a_0, a_1, ..., a_{n-1}) with a_i ∈ F_2
Correspondence: (a_0, ..., a_{n-1})  ↔  a_0 + 2·a_1 + ... + 2^{n-1}·a_{n-1}  ∈ Z/2^n

Addition: Witt-sum (inductive with carry).
  (a_0, ...) + (b_0, ...) = (S_0, S_1, ...)
  S_0 = a_0 + b_0    (XOR)
  S_1 = a_1 + b_1 + c_1  where c_1 = a_0 · b_0    (carry into level 1)
  S_k = a_k + b_k + c_k  where c_k is cascade function of a_{<k}, b_{<k}

Key observation:
  - Level 0 sum = XOR (no carry)
  - Each higher level = XOR + carry from previous
  - Carry is FULLY DETERMINED by lower levels → cocycle in GF(2)-cohomology

Filtration:
  F_k = {elements whose first k components are 0} = 2^k · Z/2^n
  Ring filtration: F_i · F_j ⊂ F_{i+j}
  Addition: F_k is additively closed
  XOR: respects filtration (since XOR = level-0 sum, level k is preserved by XOR if
       both operands have 0 at level k... wait, XOR mod 2^n is NOT the same as component-wise
       Witt-level XOR — need to think carefully)

Actually let's be precise:
  XOR in SHA means bitwise XOR as integers in Z/2^n.
  In Witt coordinates, XOR: (a_0,...,a_{n-1}) XOR (b_0,...,b_{n-1}) = (a_0+b_0, ..., a_{n-1}+b_{n-1})
  (componentwise sum in F_2)
  This DOES respect filtration: if both operands are in F_k (level <k components = 0),
  output is in F_k.

  Witt-sum = integer addition mod 2^n:
    also respects filtration (F_k is ideal in Z/2^n).

  Rotation ROTR(x, r): cyclic shift of bits.
    Level-wise: ROTR sends level i → level (i - r) mod n  (since bit at position i = 2^i
    goes to position (i-r) mod n after shifting right by r with wrap)
    **Rotation BREAKS filtration**: ROTR doesn't preserve F_k in general.

This is the key structural observation. SHA operations split:
  Filtration-respecting: +, ⊕, &, |, ¬, K (constants), Ch, Maj
  Filtration-breaking: ROTR (Σ, σ are XOR of ROTRs, so also break filtration
                            but in a controlled way)
"""

from typing import Tuple, List


def int_to_witt(x: int, n: int) -> Tuple[int, ...]:
    """Convert integer x ∈ [0, 2^n) to Witt vector (a_0, ..., a_{n-1})."""
    return tuple((x >> i) & 1 for i in range(n))


def witt_to_int(w: Tuple[int, ...]) -> int:
    """Convert Witt vector to integer."""
    return sum(a * (1 << i) for i, a in enumerate(w))


def witt_add(a: Tuple[int, ...], b: Tuple[int, ...]) -> Tuple[int, ...]:
    """Witt-sum over F_2: component-wise with carry cascade."""
    assert len(a) == len(b)
    n = len(a)
    result = [0] * n
    carry = 0
    for i in range(n):
        s = a[i] ^ b[i] ^ carry
        result[i] = s
        # Next carry: majority of (a[i], b[i], carry)
        carry = (a[i] & b[i]) | (a[i] & carry) | (b[i] & carry)
    return tuple(result)


def witt_xor(a: Tuple[int, ...], b: Tuple[int, ...]) -> Tuple[int, ...]:
    """Componentwise XOR in F_2."""
    return tuple((ai ^ bi) & 1 for ai, bi in zip(a, b))


def witt_and(a: Tuple[int, ...], b: Tuple[int, ...]) -> Tuple[int, ...]:
    """Componentwise AND."""
    return tuple((ai & bi) & 1 for ai, bi in zip(a, b))


def witt_not(a: Tuple[int, ...]) -> Tuple[int, ...]:
    return tuple((ai ^ 1) & 1 for ai in a)


def witt_rotr(a: Tuple[int, ...], r: int) -> Tuple[int, ...]:
    """Cyclic rotation right by r. Level i → level (i - r) mod n."""
    n = len(a)
    return tuple(a[(i + r) % n] for i in range(n))


# Filtration analysis: level_k returns the k-th Witt component
def level(a: Tuple[int, ...], k: int) -> int:
    return a[k]


def truncate_above(a: Tuple[int, ...], k: int) -> Tuple[int, ...]:
    """Set all levels ≥ k to 0 (project onto F^{n-k} = Z/2^k)."""
    return tuple(a[i] if i < k else 0 for i in range(len(a)))


def below_filtration(a: Tuple[int, ...], k: int) -> bool:
    """True if a ∈ F_k, i.e., levels 0..k-1 are all 0."""
    return all(a[i] == 0 for i in range(k))


# --- Correctness tests ---
def smoke_test():
    n = 8
    x, y = 123, 200
    wx, wy = int_to_witt(x, n), int_to_witt(y, n)
    assert witt_to_int(witt_add(wx, wy)) == (x + y) % (1 << n), "ADD fail"
    assert witt_to_int(witt_xor(wx, wy)) == x ^ y, "XOR fail"
    assert witt_to_int(witt_and(wx, wy)) == x & y, "AND fail"
    assert witt_to_int(witt_not(wx)) == (~x) & ((1 << n) - 1), "NOT fail"
    for r in range(n):
        expected = ((x >> r) | (x << (n - r))) & ((1 << n) - 1)
        assert witt_to_int(witt_rotr(wx, r)) == expected, f"ROTR fail r={r}"
    print(f"n={n}: all Witt operations match integer semantics ✓")

    # Filtration test
    # Level 0 of a+b is XOR of level 0
    for trial in range(100):
        import random
        random.seed(trial)
        x = random.randint(0, 2**n - 1)
        y = random.randint(0, 2**n - 1)
        wx, wy = int_to_witt(x, n), int_to_witt(y, n)
        sum_w = witt_add(wx, wy)
        xor_w = witt_xor(wx, wy)
        # Level 0 of sum = XOR of level 0
        assert sum_w[0] == (wx[0] ^ wy[0])
        # Level 0 of XOR = XOR of level 0 (trivially)
        assert xor_w[0] == (wx[0] ^ wy[0])
        # Higher levels: ADD and XOR DIFFER (that's exactly carry)
        if x + y < (1 << n):  # no overflow cases
            pass  # differ only where carry is 1

    print(f"Filtration: level 0 of ADD = XOR of level 0 ✓ (carry only affects level ≥ 1)")


if __name__ == "__main__":
    smoke_test()
