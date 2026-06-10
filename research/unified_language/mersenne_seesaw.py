"""
Searching for the unifying language: measure the four SHA primitives in THREE
representations and see if any single one tames more than its "home" op.

Representations:
  F2      : bit vector, complexity = max ANF (Zhegalkin) degree
  Z/2^n   : integer mod 2^n, complexity = arithmetic degree (finite-diff test)
  Z/2^n-1 : Mersenne ring, complexity = arithmetic degree mod (2^n - 1)

Primitives (single-argument slices, the honest per-op test):
  XOR c   : x -> x ^ c          (XOR-linear glue)
  ROTR r  : cyclic rotation
  ADD c   : x -> x + c mod 2^n  (the carry op)
  AND c   : x -> x & c          (boolean / pointwise)

Key prediction from the methodology's Mersenne decomposition (§II.7.8):
  in Z/(2^n - 1), ROTR becomes multiplication by 2^r  => arithmetic degree 1.
  ADD stays ~linear (one wrap correction). The IRREDUCIBLE nonlinearity should
  then be the boolean layer (AND / Ch / Maj) only -- a sharper statement than
  "three-way incompatible".
"""

N = 8
M2 = 1 << N          # 2^n
MM = (1 << N) - 1    # 2^n - 1 (Mersenne)


def rotr(x, r):
    return ((x >> r) | (x << (N - r))) & (M2 - 1)


# ---- F2 ANF degree ----------------------------------------------------------

def anf_max_degree(col, nvars):
    a = list(col); size = 1 << nvars; i = 1
    while i < size:
        for j in range(size):
            if j & i:
                a[j] ^= a[j ^ i]
        i <<= 1
    return max((bin(m).count("1") for m in range(size) if a[m]), default=0)


def deg_F2(func, in_bits, out_bits):
    tbl = [func(x) for x in range(1 << in_bits)]
    return max(anf_max_degree([(tbl[x] >> b) & 1 for x in range(len(tbl))], in_bits)
               for b in range(out_bits))


# ---- arithmetic degree over Z/M (finite differences) ------------------------

def arith_degree(values, MOD):
    cur = [v % MOD for v in values]
    for d in range(len(values)):
        if all(v == 0 for v in cur):
            return d - 1
        cur = [(cur[i + 1] - cur[i]) % MOD for i in range(len(cur) - 1)]
        if not cur:
            return d
    return MOD - 1


# ---- build per-op value tables on each domain -------------------------------

def table_mod2n(op):
    return [op(x) for x in range(M2)]


def table_mersenne(op):
    # domain 0..2^n-2 (residues mod 2^n-1); represent value also reduced mod MM
    return [op(x) % MM for x in range(MM)]


OPS = {
    "XOR c": lambda x: x ^ 0x6A,
    "ROTR 3": lambda x: rotr(x, 3),
    "ADD c": lambda x: (x + 0x9E) & (M2 - 1),
    "AND c": lambda x: x & 0x6A,
}


if __name__ == "__main__":
    print(f"n = {N}   (Z/2^n = {M2},  Mersenne Z/2^n-1 = {MM})\n")
    print(f"{'op':<8} {'deg_F2':>7} {'deg_Z/2^n':>10} {'deg_Z/2^n-1':>12}")
    rows = {}
    for name, op in OPS.items():
        df2 = deg_F2(op, N, N)
        dz = arith_degree(table_mod2n(op), M2)
        # for Mersenne, ROTR/ADD interpreted in the Mersenne ring;
        # rotation = mult by 2^(n-r); represent on residues 0..MM-1
        dm = arith_degree(table_mersenne(op), MM)
        rows[name] = (df2, dz, dm)
        print(f"{name:<8} {df2:>7} {dz:>10} {dm:>12}")

    print("\n-- reading the table --")
    print("F2      : XOR/ROTR/AND-mask linear(1); ADD maximal -> carry is the enemy")
    print("Z/2^n   : ADD linear(1); ROTR/XOR/AND high -> rotation+bool are the enemy")
    print("Z/2^n-1 : look at ROTR and ADD columns below")

    # direct check: is ROTR multiplication by a constant mod (2^n - 1)?
    r = 3
    factor = pow(2, N - r, MM)  # ROTR by r == mult by 2^(n-r) mod 2^n-1
    ok = all((rotr(x, r) % MM) == (factor * x) % MM for x in range(MM))
    print(f"\nROTR_{r}(x) == ({factor} * x) mod {MM}  for all x:  {ok}")
    print("  => in the Mersenne ring, rotation IS multiplication by a unit (linear).")

    # how many of the 3 structural ops (XOR, ROTR, ADD) are simultaneously
    # low-degree (<=1 in the chosen sense) in each representation?
    def count_low(rep_idx):
        c = 0
        for nm in ("XOR c", "ROTR 3", "ADD c"):
            if rows[nm][rep_idx] <= 1:
                c += 1
        return c
    print(f"\nstructural ops simultaneously linear(<=1):")
    print(f"  F2:        {count_low(0)}/3   Z/2^n: {count_low(1)}/3   "
          f"Z/2^n-1: {count_low(2)}/3")
    print("\nIf Mersenne shows ROTR+ADD both linear, the irreducible core is the")
    print("boolean Ch/Maj layer alone -- the precise obstruction, not a vague wall.")
