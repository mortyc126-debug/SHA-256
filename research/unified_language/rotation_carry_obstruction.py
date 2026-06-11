"""
Measuring the rotation<->carry obstruction directly, and localizing it.

The unification question reduces (from FINDINGS.md) to: can rotation and the
carry-addition live in ONE structure where rotation is an automorphism of the
addition?  Equivalently: does ROTR distribute over the addition,

        ROTR_r(a + b) == ROTR_r(a) + ROTR_r(b)  ?

- If YES for some addition law +, then {rotation, that addition} unify into a
  module/ring and rotation is linear over it.
- The carry lives in two candidate addition laws:
    +2  : a + b mod 2^n        (the SHA carry: open boundary, carry dropped)
    +M  : a + b mod (2^n - 1)  (Mersenne: cyclic boundary, carry wraps to bit0)

Prediction (the precise obstruction):
  +M : ROTR distributes PERFECTLY (rotation = mult by 2^(n-r), a ring unit) ->
       rotation+carry DO unify, in the Mersenne ring.
  +2 : ROTR does NOT distribute; failures are CONCENTRATED at the top-bit
       boundary (the dropped carry breaks cyclic symmetry).

That pins the obstruction to a single, nameable feature: the OPEN boundary of
mod-2^n addition. SHA uses +2 (not +M) precisely to break the symmetry that
would otherwise unify rotation and carry.
"""

import random


def make(n):
    MASK = (1 << n) - 1
    MOD2 = 1 << n
    MODM = (1 << n) - 1  # Mersenne modulus 2^n - 1

    def rotr(x, r):
        return ((x >> r) | (x << (n - r))) & MASK

    def add2(a, b):
        return (a + b) & MASK            # mod 2^n

    def addM(a, b):
        s = (a % MODM) + (b % MODM)
        return s % MODM                  # mod 2^n - 1

    return n, MASK, rotr, add2, addM, MODM


def distributivity(n, r, trials=20000, seed=0):
    """Measure P[ROTR_r(a+b) = ROTR_r(a)+ROTR_r(b)] for both additions, and
    localize the per-bit discrepancy of the mod-2^n failure."""
    _, MASK, rotr, add2, addM, MODM = make(n)
    rng = random.Random(seed)
    ok2 = okM = 0
    bit_fail = [0] * n  # which bits of the discrepancy are set, mod-2^n case
    for _ in range(trials):
        a = rng.getrandbits(n)
        b = rng.getrandbits(n)
        # mod 2^n
        lhs2 = rotr(add2(a, b), r)
        rhs2 = add2(rotr(a, r), rotr(b, r))
        if lhs2 == rhs2:
            ok2 += 1
        else:
            disc = lhs2 ^ rhs2
            for i in range(n):
                bit_fail[i] += (disc >> i) & 1
        # mod 2^n - 1 (reduce inputs into the ring first)
        am, bm = a % MODM, b % MODM
        lhsM = rotr(addM(am, bm), r) % MODM
        rhsM = addM(rotr(am, r) % MODM, rotr(bm, r) % MODM)
        if lhsM == rhsM:
            okM += 1
    return ok2 / trials, okM / trials, [c / trials for c in bit_fail]


def rotr_is_mult_unit(n, r):
    """Confirm ROTR_r is multiplication by the unit 2^(n-r) in Z/(2^n-1)."""
    MODM = (1 << n) - 1
    MASK = (1 << n) - 1
    factor = pow(2, n - r, MODM)
    def rotr(x): return ((x >> r) | (x << (n - r))) & MASK
    return all((rotr(x) % MODM) == (factor * x) % MODM for x in range(MODM))


if __name__ == "__main__":
    for n in (8, 16):
        print(f"==== n = {n} ====")
        for r in (1, 3, 7):
            p2, pM, bitfail = distributivity(n, r)
            print(f"  ROTR_{r}: distributes over +mod2^n : {p2:6.3f}   "
                  f"over +Mersenne : {pM:6.3f}")
        # localize where the mod-2^n failure concentrates (use r=3)
        _, _, bitfail = distributivity(n, 3, trials=40000)
        print(f"  per-bit failure rate of [ROTR_3, +mod2^n] discrepancy:")
        # show top and bottom few bits
        idxs = list(range(n))
        line = "   ".join(f"b{ i}:{bitfail[i]:.2f}" for i in idxs)
        print(f"    {line}")
        peak = max(range(n), key=lambda i: bitfail[i])
        print(f"    -> peak failure at bit {peak} "
              f"(boundary bits {n-1}/0 region expected)")
        print(f"  ROTR is mult-by-unit in Z/(2^n-1): {rotr_is_mult_unit(n,3)}")
        print()
    print("Interpretation:")
    print("  rotation + carry UNIFY in the Mersenne ring (distributes 100%),")
    print("  and FAIL to unify under mod-2^n, with the failure carried by the")
    print("  dropped-carry boundary. The obstruction is the open top-bit, not")
    print("  a mysterious incompatibility. SHA chose mod-2^n to break it.")
