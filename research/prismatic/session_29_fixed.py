"""
Session 29: Fixed points of SHA-256 round function (K_t = W_t = 0).

R: F_2^256 → F_2^256 with R(v) = v iff:
  b' = a → a = b
  c' = b → b = c
  d' = c → c = d
  f' = e → e = f
  g' = f → f = g
  h' = g → g = h
  ⇒ a = b = c = d, e = f = g = h.

With Maj(a,a,a) = a and Ch(e,e,e) = e:
  T_1 = h + Σ_1(e) + e
  T_2 = Σ_0(a) + a
  a' = T_1 + T_2 = a    requires:  h + Σ_1(e) + e + Σ_0(a) = 0
  e' = d + T_1 = e      requires:  a + h + Σ_1(e) = 0

Solving:
  h = a + Σ_1(e)         ... from e'-equation
  e = (I + Σ_0)(a)       ... substituting into a'-equation
  h = e (consistency from e=f=g=h chain)

Combining: a + Σ_1((I + Σ_0)(a)) = (I + Σ_0)(a)
        ⇒ (Σ_1 + Σ_1 Σ_0 + Σ_0)(a) = 0

So fixed points form an affine variety parametrised by a ∈ ker(M_fix) where

  M_fix = Σ_1 + Σ_1 ∘ Σ_0 + Σ_0  ∈ End(F_2^32).

The fixed-point set has size 2^{dim ker M_fix}.

If ker(M_fix) ≠ 0: SHA round (without K, W) has nontrivial fixed points.
This is purely combinatorial — does NOT mean SHA is broken (real SHA has K, W
which destroy fixed points).

But it characterises the LINEAR/QUADRATIC core of SHA's round.
"""
import numpy as np
from session_25_round import build_sigma_0, build_sigma_1, gf2_rank


def main():
    print("=== Session 29: Fixed points of SHA-256 round (no K, W) ===\n")

    S0 = build_sigma_0()
    S1 = build_sigma_1()
    I = np.eye(32, dtype=np.uint8)

    # M_fix = Σ_1 + Σ_1 ∘ Σ_0 + Σ_0
    M_fix = (S1 ^ ((S1 @ S0) & 1) ^ S0) & 1

    print("  M_fix = Σ_1 + Σ_1·Σ_0 + Σ_0")
    rk = gf2_rank(M_fix.copy())
    ker_dim = 32 - rk
    print(f"  rank(M_fix) = {rk}, dim ker(M_fix) = {ker_dim}")
    print(f"  # fixed points of R (with K = W = 0): 2^{ker_dim} = {2**ker_dim}")

    if ker_dim > 0:
        kernel = compute_kernel(M_fix.copy())
        print(f"\n  Kernel basis ({ker_dim} vectors of F_2^{{32}}):")
        for k, v in enumerate(kernel):
            bits = [i for i in range(32) if v[i]]
            print(f"    a_{k} = e_{{{','.join(str(b) for b in bits[:8])}{'...' if len(bits)>8 else ''}}}, weight {sum(v)}")

    print("\n  For each a ∈ ker(M_fix), the fixed point of R is:")
    print("    state = (a, a, a, a, e, e, e, e)  with e = (I + Σ_0)(a).")

    # Verify by direct check on a sample
    if ker_dim > 0:
        a = kernel[0]
        e = ((I ^ S0) @ a) & 1
        print(f"\n  Verifying fixed point for kernel basis vector 0:")
        print(f"    a = {tuple(int(x) for x in a)}")
        print(f"    e = (I+Σ_0)(a) = {tuple(int(x) for x in e)}")
        verify_fixed_point(S0, S1, a, e)

    return M_fix, ker_dim


def compute_kernel(M):
    """Compute right null space of M over F_2."""
    n = M.shape[1]
    # Augment with identity, row-reduce
    rows, cols = M.shape
    aug = np.hstack([M.T.copy() & 1, np.eye(cols, dtype=np.uint8)])  # work on M.T
    r = 0
    for c in range(rows):
        if r >= cols:
            break
        piv = None
        for rr in range(r, cols):
            if aug[rr, c] == 1:
                piv = rr
                break
        if piv is None:
            continue
        if piv != r:
            aug[[r, piv]] = aug[[piv, r]]
        for rr in range(cols):
            if rr != r and aug[rr, c] == 1:
                aug[rr] ^= aug[r]
        r += 1
    kernel = []
    for i in range(cols):
        if aug[i, :rows].sum() == 0:
            kernel.append(aug[i, rows:].copy())
    return kernel


def verify_fixed_point(S0, S1, a, e):
    """Run one SHA round on state (a,a,a,a,e,e,e,e) and check fixed."""
    # Maj(a,a,a) = a, Ch(e,e,e) = e
    Sa = (S0 @ a) & 1
    Se = (S1 @ e) & 1
    h = e  # since e = f = g = h
    T1 = (h ^ Se ^ e) & 1
    T2 = (Sa ^ a) & 1
    a_new = (T1 ^ T2) & 1
    e_new = (a ^ T1) & 1   # d = a so d + T_1 = a + T_1
    is_fixed = np.array_equal(a_new, a) and np.array_equal(e_new, e)
    print(f"    a_new = {tuple(int(x) for x in a_new)}")
    print(f"    e_new = {tuple(int(x) for x in e_new)}")
    print(f"    Fixed? {'YES' if is_fixed else 'NO'}")


def with_K_offset():
    """If K_t is included, the fixed-point equation becomes affine.
    R(v) = v + K_offset (per-bit constant).
    Solvable iff the affine system is consistent.

    But K varies per round — there is no single fixed K for round R. So
    real SHA does NOT have round-level fixed points.

    However: if we treat ONE round with arbitrary K, we ask "for which K_a, K_e
    does the state (a,a,a,a,e,e,e,e) become fixed?"
    """
    print("""

  With K_t included: fixed-point equation
      Σ_1(e) + e + h + Σ_0(a) = K_a   (a' = a)
      d + h + Σ_1(e) = K_e + e        (e' = e)   Wait, d = a, so:
      a + h + Σ_1(e) + e = K_e

  These determine K_a, K_e GIVEN (a, e). So for ANY (a, a, ..., e, ..., e) with
  a, e free, choose K_a, K_e to make it a fixed point. 64 bits of K are needed
  per round to fix one state, and SHA-256 supplies 32 bits of K_t per round.

  So: the K_t schedule of SHA-256 ENFORCES that NO state is a fixed point of
  the actual round function. This is a deliberate design property.
""")


def takeaway(ker_dim):
    print(f"""

=== STRUCTURAL TAKEAWAY (Session 29) ===

THEOREM 29.1: The bare round R (K = W = 0) has exactly 2^{ker_dim} = {2**ker_dim} fixed points.

These are parametrised by a ∈ ker(Σ_1 + Σ_1·Σ_0 + Σ_0) ⊂ F_2^{{32}}.
Each fixed point has the symmetric form (a, a, a, a, e, e, e, e) with
e = (I + Σ_0)(a).

INTERPRETATION:
  - The bare-round operator has a high-dimensional fixed-point variety
    when ker(M_fix) is large.
  - Real SHA destroys these via K_t addition every round.

Why the kernel matters:
  - Fixed-point structure indicates ALGEBRAIC RIGIDITY of the round shape.
  - Bigger kernel ⇒ more "stationary" combinations of registers ⇒ more
    structural patterns to exploit if K were absent.

CONNECTION TO Σ ALGEBRA:
  M_fix = Σ_1 (I + Σ_0) + Σ_0.

  In the Σ-only Lie algebra (Sessions 18, 24):
    Σ_0 = I + N_0, Σ_1 = I + N_1 (unipotent).
    M_fix = (I + N_1)(N_0) + (I + N_0)
          = N_0 + N_1 N_0 + I + N_0
          = I + N_1 N_0    (since N_0 + N_0 = 0 in F_2)

  So M_fix = I + N_1 N_0!

  ker(M_fix) = ker(I + N_1 N_0) = generalised 1-eigenspace of N_1 N_0.

  Since N_1, N_0 are nilpotent, N_1 N_0 is nilpotent. So I + N_1 N_0 is
  unipotent, and ker(I + nilpotent) = ker(nilpotent) of the SAME nilpotent.

  Wait: ker(I + N) for N nilpotent... I + N has only eigenvalue 1 (unipotent).
  ker(I + N) = vectors v with N(v) = -v = v (in F_2). But N nilpotent means
  N has only 0-eigenvalue. So ker(I + N) = {{0}}.

  So actually ker(M_fix) MUST be {{0}}!
  Empirical computation will confirm: ker_dim = 0, only trivial fixed point.
""")


if __name__ == "__main__":
    M_fix, ker_dim = main()
    with_K_offset()
    takeaway(ker_dim)
