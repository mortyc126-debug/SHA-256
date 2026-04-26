"""
Session 41: Cycle structure of SHA-256 round as a permutation of F_2^256.

The bare round R: F_2^256 → F_2^256 (with K=W=0) is bijective. As an element
of the symmetric group S_{2^256}, it has a CYCLE DECOMPOSITION:

  R = c_1 · c_2 · ... · c_k

where each c_i is a cycle of some length ℓ_i. We have:
  Σ ℓ_i = 2^256
  ord(R) = lcm(ℓ_i)

From Session 25: ord(R) = 448 = 2^6 · 7. So all cycle lengths divide 448.

Question: how many cycles of each length? For random bijection on a set of
size N: expected cycle length distribution follows Erdős-Rényi (Poisson-like
with mean log N).

For our R: lengths ∈ {1, 2, 4, 7, 8, 14, 16, 28, 32, 56, 64, 112, 224, 448}.

Goal:
1. Sample many random states, compute orbit lengths.
2. Build empirical distribution of cycle lengths.
3. Compare to "uniform random bijection of order 448" expectation.
"""
import numpy as np
from session_25_round import build_sigma_0, build_sigma_1
from session_38_avalanche import round_eval_with_addchains


def orbit_length(start, R, max_len=512):
    """Find smallest k > 0 with R^k(start) = start."""
    cur = R(start)
    k = 1
    while not np.array_equal(cur, start) and k <= max_len:
        cur = R(cur)
        k += 1
    if k > max_len:
        return -1
    return k


def main():
    print("=== Session 41: Cycle structure of SHA round permutation ===\n")
    S0 = build_sigma_0()
    S1 = build_sigma_1()

    R = lambda x: round_eval_with_addchains(x, S0, S1)

    # ord(R) = 448, so possible cycle lengths divide 448.
    divisors_of_448 = sorted([d for d in range(1, 449) if 448 % d == 0])
    print(f"  Possible cycle lengths (divisors of 448): {divisors_of_448}")

    # Sample N random states, find orbit lengths
    NUM_TRIALS = 50
    rng = np.random.default_rng(0)
    orbit_lens = []
    print(f"\n  Sampling {NUM_TRIALS} random starting states (each takes up to 448 round applications)...")
    for trial in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        L = orbit_length(x, R, max_len=448 + 1)
        orbit_lens.append(L)
        if (trial + 1) % 10 == 0:
            print(f"    {trial+1}/{NUM_TRIALS} done.")

    print(f"\n  Empirical orbit length distribution:")
    from collections import Counter
    cnt = Counter(orbit_lens)
    for L in sorted(cnt.keys()):
        is_div = "✓" if L in divisors_of_448 else "✗"
        print(f"    length {L:>4}: {cnt[L]:>3} samples  {is_div}")

    print(f"\n  ord(R) = 448 from Session 25.")
    if orbit_lens and max(orbit_lens) <= 448:
        max_ratio = max(orbit_lens) / 448
        print(f"  Longest sampled orbit: {max(orbit_lens)} (= {max_ratio:.4f} · 448)")

    # For uniform random bijection of order 448:
    # Expected cycle length distribution follows divisors of 448 weighted by ...
    # actually for a permutation on N elements with order O, cycle lengths divide O.
    # If random, fraction of elements in cycles of length d is roughly d * f(d) / N where f(d) is the
    # number of d-cycles. For SHA's R on 2^256 states, deviations would indicate structure.

    print("""

  THEORETICAL EXPECTATIONS:
  For a "generic" bijection R with ord(R) = 448 on a set of size N=2^256:
    - Most elements should lie in cycles of MAXIMAL length 448.
    - Smaller cycles (length d | 448, d < 448) should be rare unless R has
      special invariant subspaces.

  IF most sampled orbits are length 448 → R behaves "generically".
  IF smaller cycles dominate → R has hidden structure.
""")


def takeaway(orbit_lens):
    short_count = sum(1 for L in orbit_lens if 0 < L < 448)
    long_count = sum(1 for L in orbit_lens if L == 448)
    print(f"\n=== Theorem 41.1 (empirical) ===")
    print(f"  Of {len(orbit_lens)} sampled orbits:")
    print(f"    {long_count} have full length 448 ({100*long_count/len(orbit_lens):.0f}%)")
    print(f"    {short_count} have shorter length ({100*short_count/len(orbit_lens):.0f}%)")
    if long_count == len(orbit_lens):
        print(f"  → R appears to act with GENERIC cycle structure: all sampled orbits length 448.")
        print(f"    No 'sticky' invariant subspaces with shorter cycles.")
    else:
        print(f"  → R has SHORTER orbits than expected — there exist invariant subspaces")
        print(f"    where R has reduced order. Investigate these.")


if __name__ == "__main__":
    print("=== Session 41: Cycle structure of bare SHA round (with full ADD) ===\n")
    print("""
  CRITICAL CLARIFICATION:
  Theorem 25.1 (ord = 448) was for R_lin (XOR-substituted, fully linear).
  Here we test the ACTUAL bare round R with full integer ADD.
  These are DIFFERENT operators and likely have very different orders.
""")
    S0 = build_sigma_0()
    S1 = build_sigma_1()

    R = lambda x: round_eval_with_addchains(x, S0, S1)

    divisors_of_448 = sorted([d for d in range(1, 449) if 448 % d == 0])
    print(f"  Divisors of 448 (R_lin order from Theorem 25.1): {divisors_of_448}")

    NUM_TRIALS = 30
    MAX_SEARCH = 5000
    rng = np.random.default_rng(0)
    orbit_lens = []
    print(f"\n  Sampling {NUM_TRIALS} random starting states (search up to {MAX_SEARCH} round applications)...")
    for trial in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        L = orbit_length(x, R, max_len=MAX_SEARCH)
        orbit_lens.append(L)
        if (trial + 1) % 5 == 0:
            print(f"    {trial+1}/{NUM_TRIALS} done. Last orbit length: {L}")

    from collections import Counter
    cnt = Counter(orbit_lens)
    print(f"\n  Empirical orbit length distribution:")
    for L in sorted(cnt.keys()):
        marker = " > MAX_SEARCH" if L == -1 else (" (= 448)" if L == 448 else "")
        print(f"    length {L:>5}: {cnt[L]:>3} samples{marker}")

    print(f"\n=== Theorem 41.1 (empirical) ===")
    if cnt.get(-1, 0) == NUM_TRIALS:
        print(f"  ALL {NUM_TRIALS} sampled orbits have length > {MAX_SEARCH}.")
        print(f"  ⇒ Bare round R (with full integer ADD) has order ≫ 448 (R_lin order).")
        print(f"  ⇒ Integer ADD's nonlinearity DESTROYS the periodic structure of R_lin.")
        print(f"  ⇒ Theorem 25.1 applies ONLY to the linear approximation R_lin.")
        print(f"  ⇒ Real R behaves close to a 'random' bijection on F_2^256, with order ~ 2^(N/2)")
        print(f"     by Birthday-bound on the symmetric group S_{{2^256}}.")
    else:
        takeaway(orbit_lens)
