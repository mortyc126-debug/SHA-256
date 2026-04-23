"""
Session 13: Compute ROTR action on H¹ of F_2[s]/(s^n).

Key question: does rotation act non-trivially on H¹?
  ROTR_1 on F_2[x]/(x^n-1) = F_2[s]/(s^n) via s = x+1
    = multiplication by x = (1+s)
  ROTR_r = multiplication by x^r = (1+s)^r

Compute action on H¹ generators.

Setup (Session 10 theorem):
  H¹(F_2[s]/(s^n)) has Z_2-basis:
    {[s^k · ds] : k odd, 1 ≤ k ≤ n-1}
  with [s^k · ds] generating Z/2^{v_2(k+1)}.

Action of mult by u ∈ R on H¹:
  u · s^k · ds = (u · s^k) · ds
  mod Im(d) + relations = some linear combination of generators
"""


def v_2(k):
    if k == 0: return float('inf')
    c = 0
    while k % 2 == 0:
        k //= 2; c += 1
    return c


def compute_1_plus_s_action(n):
    """ROTR_1 = multiplication by (1+s).

    Action on [s^k · ds] in H¹:
      (1+s) · s^k · ds = s^k · ds + s^{k+1} · ds
    In H¹: if k+1 EVEN (i.e., k odd), is [s^{k+1} · ds] zero in H¹?

    For even k+1, position is even. Session 10: only odd positions
    contribute to H¹. So [s^{k+1} · ds] = 0 in H¹.

    → Multiplication by (1+s) sends [s^k · ds] to [s^k · ds] (identity!)
    """
    print(f"\n=== ROTR_1 action on H¹(F_2[s]/(s^{n})) ===")
    print("  ROTR_1 = multiplication by (1+s) in F_2[s]/(s^n).")
    print()
    print("  Action on generator [s^k · ds] for k odd:")
    print("    (1+s) · [s^k · ds] = [s^k · ds] + [s^{k+1} · ds]")
    print("    k odd → k+1 even → [s^{k+1} · ds] = 0 in H¹ (Session 10)")
    print()
    print("  THEOREM: Multiplication by (1+s) acts as IDENTITY on H¹.")
    print()
    print("  Generators & action:")
    for k in range(1, n, 2):
        v = v_2(k + 1)
        print(f"    [s^{k:>2} · ds] ∈ Z/2^{v} → (1+s)·[s^{k} · ds] = [s^{k}·ds] + [s^{k+1}·ds]")
        print(f"         = [s^{k}·ds] (since s^{k+1} at even position = 0 in H¹)")


def compute_higher_rotations(n):
    """ROTR_r = mult by (1+s)^r.

    For r power of 2 (r = 2^k):
      (1+s)^{2^k} = 1 + s^{2^k}  (Frobenius in char 2)

    For general r: expand (1+s)^r using char 2 arithmetic.
    """
    print(f"\n=== ROTR_r for r > 1: action on H¹(F_2[s]/(s^{n})) ===")
    print()
    print("  ROTR_r = mult by (1+s)^r.")
    print()
    print("  Power of 2 case: (1+s)^{2^k} = 1 + s^{2^k} in char 2 (Frobenius).")
    print()
    print("  Action of (1 + s^m) on [s^k · ds]:")
    print("    = [s^k · ds] + [s^{k+m} · ds]")
    print()
    print("  For k odd, k+m: parity of k+m depends on parity of m.")
    print("    m odd  → k+m even → [s^{k+m}·ds] = 0 in H¹")
    print("    m even → k+m odd → [s^{k+m}·ds] non-trivial (if k+m ≤ n-1)")
    print()
    print("  So action is identity if m odd, non-trivial if m even.")

    # Specific computation for various r
    print(f"\n  Specific cases for n = {n}:")
    for r in [1, 2, 3, 4, 8, 16]:
        if r >= n: continue
        # (1+s)^r in char 2
        # Represent as integer: (1+x)^r in F_2[x] expansion
        # Non-zero coefficients at positions i where C(r, i) is odd
        # Lucas's theorem: C(r, i) odd iff i in binary is subset of r in binary
        def char2_expansion(r, max_deg):
            """(1+x)^r in F_2[x] truncated at degree max_deg."""
            r_bits = bin(r)[2:]  # binary of r
            # Non-zero coeffs at positions which are subsets of r's bits (Lucas)
            positions = []
            for i in range(max_deg + 1):
                # Check if i's bits are subset of r's bits
                if (i & r) == i:
                    positions.append(i)
            return positions

        positions = char2_expansion(r, n - 1)
        non_id_positions = [p for p in positions if p > 0 and p % 2 == 0]
        if not non_id_positions:
            print(f"    r = {r:>2}: (1+s)^{r} = 1 + s^... (all odd shifts) → IDENTITY on H¹")
        else:
            print(f"    r = {r:>2}: (1+s)^{r} has non-zero coeffs at positions {positions}")
            print(f"         Non-identity contributions from even positions: {non_id_positions}")


def theorem_rotation_kernel(n):
    """Summarize: which rotation orders act trivially on H¹?

    For ROTR_r: (1+s)^r acts on H¹ non-trivially iff r has an even bit set
                in binary expansion.

    Equivalently: acts trivially iff r is odd (all bits in binary at odd positions... wait)

    Let me re-derive. (1+s)^r = Σ_{i: i ⊂ r bitwise} s^i (Lucas).

    Action on [s^k ds] (k odd): [s^k · ds] + Σ_{i ⊂ r, i > 0} [s^{k+i} · ds]

    For contribution to be 0 in H¹: need ALL (k+i) with i ⊂ r, i > 0 to have
    k+i EVEN (= i odd, since k odd).

    So need: all i ⊂ r with i > 0 have i odd, i.e., have last bit = 1.

    Equivalently: all non-zero positions in r's binary are at... hmm wait.

    i ⊂ r bitwise means i's binary is subset of r's binary.
    i > 0 means i has at least one bit set.
    i odd means LSB of i is 1.

    For ALL i ⊂ r (i>0) to be odd: every non-empty subset of r's bits contains
    the LSB (bit 0).

    That's only possible if r has ONLY bit 0 set: r = 1.

    For any r with more bits: there's a non-zero subset avoiding bit 0
    (e.g., take just the highest bit alone). That i is even.

    So: ROTR_r acts trivially on H¹ iff r = 1.
    For any other r, ROTR_r acts non-trivially.
    """
    print(f"\n=== Theorem: rotation action on H¹(F_2[s]/(s^{n})) ===")
    print()
    print("  THEOREM: ROTR_r acts as IDENTITY on H¹ if and only if r = 1.")
    print()
    print("  Proof sketch:")
    print("    (1+s)^r expands via Lucas's theorem:")
    print("      (1+s)^r = Σ_{i: binary(i) ⊆ binary(r)} s^i")
    print()
    print("    Action on [s^k · ds] (k odd):")
    print("      shifts to [s^{k+i} · ds] for i ⊆ r bitwise")
    print()
    print("    For identity on H¹: need all [s^{k+i} · ds] (i > 0) to vanish")
    print("      ↔ k+i even for all nonzero i ⊆ r")
    print("      ↔ i odd for all nonzero i ⊆ r (since k odd)")
    print("      ↔ every nonzero subset of r's binary has bit 0 set")
    print("      ↔ r = 1  (only 'bit 0 only' set)")
    print()
    print("  Consequence: {ROTR_r : r = 1} acts trivially; ROTR_r for r ≥ 2 acts non-trivially.")
    print()
    print("  NOTE: this means our H¹ ≠ fully rotation-invariant. ROTR_2, ROTR_3, etc.")
    print("        mix classes. But specific FIXED POINTS under multi-rotation form sublattice.")


def connection_to_sha():
    print(f"\n=== Connection to SHA-256 ===")
    print("""
  SHA-256 uses specific rotation constants in Σ_0, Σ_1, σ_0, σ_1:
    Σ_0(x) = ROTR_2(x) ⊕ ROTR_13(x) ⊕ ROTR_22(x)
    Σ_1(x) = ROTR_6(x) ⊕ ROTR_11(x) ⊕ ROTR_25(x)
    σ_0(x) = ROTR_7(x) ⊕ ROTR_18(x) ⊕ SHR_3(x)
    σ_1(x) = ROTR_17(x) ⊕ ROTR_19(x) ⊕ SHR_10(x)

  These are combinations of ROTR_r for various r, joined by XOR.

  Each ROTR_r (r ≥ 2) acts non-trivially on H¹(F_2[s]/(s^32)).

  Σ_0 action on H¹ = [ROTR_2 + ROTR_13 + ROTR_22] action
                   = sum of three non-trivial actions.

  Computing this explicitly — Session 14 target.

  KEY OBSERVATION: Σ_0, Σ_1 acts as COMPOSITE of multiplications by
  (1+s)^r for different r, XOR'd. This is INDUCED AUTOMORPHISM of R
  if we interpret carefully.

  Actually wait: XOR of three ROTR's is not a single ring operation.
  It's a sum of ROTR's as Z_2-module automorphisms. (+3 maps added).

  So Σ_0 = (+ over 3 maps) where each map is mult-by-unit automorphism
  of R. This is Z_2-LINEAR map on R (as Z_2-module), not ring automorphism.

  For Z_2-linear maps: induced on H¹ is just usual linear. Can compute.
""")


if __name__ == "__main__":
    n = 32
    compute_1_plus_s_action(n)
    compute_higher_rotations(n)
    theorem_rotation_kernel(n)
    connection_to_sha()
