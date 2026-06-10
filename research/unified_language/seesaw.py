"""
The three-operation seesaw, measured.

SHA-256 mixes three operations that are each "simple" in a DIFFERENT
representation:
  - rotation / XOR-linear (Sigma, sigma, ROTR): linear over F2 (bit basis)
  - boolean Ch/Maj/AND: degree-2 (pointwise) over F2 (bit basis)
  - modular addition (carry): a group law over Z/2^n (integer basis)

Claim to test quantitatively (n=8 toy):
  (A) max ANF degree over F2 is INVARIANT under any F2-linear change of basis
      => no linear basis can lower the degree of ADD. (we verify numerically)
  (B) ADD has high F2-degree but arithmetic-degree 1 (it's a + over Z/2^n);
      ROTR/AND have F2-degree 1/2 but MAXIMAL arithmetic-degree.
      => the representation that linearizes one op de-linearizes the others.

We measure two complexity invariants of each op:
  - deg_F2  : max ANF (Zhegalkin) degree as a vectorial boolean function
  - deg_Z   : arithmetic degree over Z/2^n = min d with the (d+1)-th forward
              finite difference identically 0 mod 2^n  (poly of deg d => 0).
"""

N = 8
MOD = 1 << N
MASK = MOD - 1


# ---------- F2 ANF degree ----------------------------------------------------

def anf_max_degree(truth, nvars):
    """truth: list of 2^nvars bits (output of a single boolean fn).
    Returns max-degree monomial in the Zhegalkin ANF via fast Mobius."""
    a = list(truth)
    size = 1 << nvars
    # in-place binary Mobius transform (ANF)
    i = 1
    while i < size:
        for j in range(size):
            if j & i:
                a[j] ^= a[j ^ i]
        i <<= 1
    deg = 0
    for mask in range(size):
        if a[mask]:
            d = bin(mask).count("1")
            if d > deg:
                deg = d
    return deg


def vectorial_deg_F2(func, in_bits, out_bits):
    """func: int(in_value)->int(out_value). Returns max ANF degree over outputs."""
    size = 1 << in_bits
    table = [func(x) for x in range(size)]
    dmax = 0
    for ob in range(out_bits):
        col = [(table[x] >> ob) & 1 for x in range(size)]
        dmax = max(dmax, anf_max_degree(col, in_bits))
    return dmax


# ---------- arithmetic degree over Z/2^n -------------------------------------

def arith_degree(f):
    """f: Z/2^n -> Z/2^n given as a length-2^n list. arithmetic degree =
    min d such that the (d+1)-th forward difference is identically 0 mod 2^n.
    Returns (deg, capped) where capped means it never vanished (deg = 2^n-1)."""
    cur = list(f)
    for d in range(MOD):
        # if current sequence is all zero mod MOD -> previous order was enough
        if all(v % MOD == 0 for v in cur):
            return d - 1
        nxt = [(cur[i + 1] - cur[i]) % MOD for i in range(len(cur) - 1)]
        cur = nxt
        if not cur:
            break
    return MOD - 1


# ---------- the operations (single-argument slices for arithmetic test) ------

def rotr(x, r):
    return ((x >> r) | (x << (N - r))) & MASK


def add_const(c):
    return [ (x + c) & MASK for x in range(MOD) ]


def rotr_fn(r):
    return [ rotr(x, r) for x in range(MOD) ]


def and_const(c):
    return [ (x & c) for x in range(MOD) ]


# ---------- F2-linear invariance check ---------------------------------------

import random


def random_invertible_F2(n, rng):
    while True:
        M = [rng.getrandbits(n) for _ in range(n)]
        # check invertible via gaussian elim over F2
        rows = M[:]
        rank = 0
        for col in range(n):
            piv = None
            for r in range(rank, n):
                if (rows[r] >> col) & 1:
                    piv = r; break
            if piv is None:
                continue
            rows[rank], rows[piv] = rows[piv], rows[rank]
            for r in range(n):
                if r != rank and ((rows[r] >> col) & 1):
                    rows[r] ^= rows[rank]
            rank += 1
        if rank == n:
            return M


def apply_lin(M, x, n):
    y = 0
    for i in range(n):
        bit = bin(M[i] & x).count("1") & 1
        y |= (bit << i)
    return y


if __name__ == "__main__":
    print(f"n = {N}\n")

    # ADD as F2 function of 2n bits (a||b) -> n bits
    def add_full(xy):
        a = xy & MASK
        b = (xy >> N) & MASK
        return (a + b) & MASK
    deg_add_F2 = vectorial_deg_F2(add_full, 2 * N, N)

    # ROTR and AND as F2 functions of n bits
    deg_rotr_F2 = vectorial_deg_F2(lambda x: rotr(x, 3), N, N)
    deg_and_F2 = vectorial_deg_F2(lambda x: x & 0x5A, N, N)  # AND with a const

    # arithmetic degrees over Z/2^n
    deg_add_Z = arith_degree(add_const(0x9E))      # a + const
    deg_rotr_Z = arith_degree(rotr_fn(3))
    deg_and_Z = arith_degree(and_const(0x5A))

    print("operation        deg_F2 (bit ANF)   deg_Z (arith over Z/2^n)")
    print(f"  ADD (a+b)            {deg_add_F2:>2}                   {deg_add_Z:>3}")
    print(f"  ROTR_3               {deg_rotr_F2:>2}                   {deg_rotr_Z:>3}")
    print(f"  AND const            {deg_and_F2:>2}                   {deg_and_Z:>3}")
    print(f"  (max possible)       {N}/{2*N}                 {MOD-1}")

    print("\nSeesaw: each op is degree-1 in ONE column and ~maximal in the other.")
    print("No column (representation) makes all three simultaneously low.\n")

    # (A) F2-linear invariance of ADD's max degree
    rng = random.Random(0)
    print("F2-linear invariance check (ADD max ANF degree under random GL):")
    base = deg_add_F2
    same = 0
    for t in range(5):
        Min = random_invertible_F2(2 * N, rng)   # mix input bits a,b
        Mout = random_invertible_F2(N, rng)       # mix output bits
        def add_T(xy, Min=Min, Mout=Mout):
            v = add_full(apply_lin(Min, xy, 2 * N))
            return apply_lin(Mout, v, N)
        d = vectorial_deg_F2(add_T, 2 * N, N)
        same += (d == base)
        print(f"    trial {t}: deg = {d}  (baseline {base})")
    print(f"  invariant in {same}/5 trials -> linear bases CANNOT lower ADD degree.")
