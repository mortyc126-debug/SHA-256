"""
Session 46: BUG POSTMORTEM + corrected round implementation + critical re-runs.

BUG FOUND in Sessions 38, 41-45:
  `round_eval_with_addchains` (Session 38) called `matvec(S0, a)` where
  S0 = build_sigma_0() returns the matrix in the s-basis (multiplication by
  (1+s)^2 + (1+s)^13 + (1+s)^22 in F_2[s]/(s^32)).

  This matrix when applied to a bit-vector treats those bits as an s-basis
  vector. But the function ALSO uses `a` as an integer (x-basis interpretation),
  feeding the matvec result into integer ADD with x-basis values.

  This MIXES TWO INCOMPATIBLE BASES — the round function being evaluated is
  NOT actual SHA-256 but some hybrid.

This Session:
1. Implements the CORRECT round function with direct ROTR (no matrix games).
2. Re-runs the most critical previous experiments (avalanche, complement-symmetry,
   cycle structure).
3. Reports which previous findings hold/change.
"""
import numpy as np
from collections import Counter


def rotr(x, r):
    """Standard 32-bit ROTR (rotate right by r bits)."""
    return ((x >> r) | (x << (32 - r))) & 0xFFFFFFFF


def Sigma_0(x):
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)


def Sigma_1(x):
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)


def Ch(e, f, g):
    return (e & f) ^ ((~e) & g & 0xFFFFFFFF)


def Maj(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)


def correct_round(state, K=0, W=0):
    """REAL SHA-256 round function (with K=W=0 by default)."""
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sigma_1(e) + Ch(e, f, g) + K + W) & 0xFFFFFFFF
    T2 = (Sigma_0(a) + Maj(a, b, c)) & 0xFFFFFFFF
    return [(T1 + T2) & 0xFFFFFFFF, a, b, c,
            (d + T1) & 0xFFFFFFFF, e, f, g]


def state_to_bits(state):
    out = np.zeros(256, dtype=np.uint8)
    for r in range(8):
        for i in range(32):
            if (state[r] >> i) & 1:
                out[r * 32 + i] = 1
    return out


def bits_to_state(bits):
    state = []
    for r in range(8):
        x = 0
        for i in range(32):
            if bits[r * 32 + i]:
                x |= (1 << i)
        state.append(x)
    return state


def R_correct(bits):
    state = bits_to_state(bits)
    new_state = correct_round(state)
    return state_to_bits(new_state)


# ============================================================================
# RE-RUN 1: AVALANCHE (Session 38)
# ============================================================================

def rerun_avalanche():
    print("\n=== RE-RUN: Session 38 avalanche measurement ===")
    rng = np.random.default_rng(0)
    NUM_TRIALS = 30
    flips = np.zeros(256)
    for _ in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        y = R_correct(x)
        for i in range(256):
            x[i] ^= 1
            y_pert = R_correct(x)
            x[i] ^= 1
            flips[i] += int((y ^ y_pert).sum())
    flips /= NUM_TRIALS

    print(f"  Mean per-flip Hamming distance: {flips.mean():.2f} (ideal 128)")
    print(f"  Std: {flips.std():.2f}")
    print(f"  Min/Max: {flips.min():.2f} / {flips.max():.2f}")
    return flips


# ============================================================================
# RE-RUN 2: COMPLEMENT SYMMETRY (Sessions 42, 43)
# ============================================================================

def rerun_complement():
    print("\n=== RE-RUN: Session 42-43 complement symmetry ===")
    rng = np.random.default_rng(0)
    NUM_TRIALS = 200
    all_ones = np.ones(256, dtype=np.uint8)
    bit_freq = np.zeros(256, dtype=int)
    weights = []
    for _ in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        x_neg = x ^ all_ones
        Rx = R_correct(x)
        Rxneg = R_correct(x_neg)
        not_Rx = Rx ^ all_ones
        diff = Rxneg ^ not_Rx
        bit_freq += diff
        weights.append(int(diff.sum()))

    weights = np.array(weights)
    print(f"  Mean correction weight: {weights.mean():.2f}")
    print(f"  Std: {weights.std():.2f}")
    print(f"  Per-register breakdown:")
    for r_idx, rname in enumerate("abcdefgh"):
        offset = r_idx * 32
        avg = bit_freq[offset:offset + 32].sum() / (NUM_TRIALS * 32)
        bits_dev = sum(1 for i in range(offset, offset + 32) if bit_freq[i] > NUM_TRIALS * 0.05)
        print(f"    {rname}': {bits_dev}/32 bits with >5% dev, avg rate {avg:.4f}")


# ============================================================================
# RE-RUN 3: SHL_1 SYMMETRY TEST (Session 44 most suspicious result)
# ============================================================================

def rerun_shl_test():
    print("\n=== RE-RUN: Session 44 SHL_1 commutator (was buggy 0.00) ===")
    rng = np.random.default_rng(0)

    def T_shl(bits):
        state = bits_to_state(bits)
        new_state = [(s << 1) & 0xFFFFFFFF for s in state]
        return state_to_bits(new_state)

    NUM_TRIALS = 50
    defects = []
    for _ in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        Tx = T_shl(x.copy())
        Rx = R_correct(x.copy())
        TRx = T_shl(Rx.copy())
        RTx = R_correct(Tx.copy())
        defect = int((TRx ^ RTx).sum())
        defects.append(defect)
    defects = np.array(defects)
    print(f"  SHL_1 commutator defect (CORRECTED round):")
    print(f"    Mean: {defects.mean():.2f}, std: {defects.std():.2f}")
    print(f"    Min/Max: {defects.min()}/{defects.max()}")
    if defects.mean() < 5:
        print(f"    ⚠ Still very small — investigate further.")
    else:
        print(f"    ✓ Bug confirmed: SHL_1 does NOT commute with correct R as expected.")


# ============================================================================
# RE-RUN 4: CYCLE LENGTH TEST (Session 41)
# ============================================================================

def rerun_cycle_length():
    print("\n=== RE-RUN: Session 41 orbit length test (CORRECTED round) ===")
    rng = np.random.default_rng(0)

    NUM_TRIALS = 10
    MAX_SEARCH = 1000

    print(f"  Sampling {NUM_TRIALS} random orbits, search up to {MAX_SEARCH}...")

    found_lens = []
    for trial in range(NUM_TRIALS):
        x = rng.integers(0, 2, size=256, dtype=np.uint8)
        cur = R_correct(x)
        L = 1
        while not np.array_equal(cur, x) and L <= MAX_SEARCH:
            cur = R_correct(cur)
            L += 1
        if L > MAX_SEARCH:
            L = -1
        found_lens.append(L)
        print(f"    trial {trial+1}: orbit length = {L if L > 0 else '> ' + str(MAX_SEARCH)}")

    if all(L < 0 for L in found_lens):
        print(f"  Conclusion: real R also has order > {MAX_SEARCH} (consistent with Session 41 finding).")
    else:
        print(f"  Found small orbits — may differ from Session 41.")


def main():
    print("=" * 70)
    print("Session 46: BUG POSTMORTEM + CORRECTED RE-RUNS")
    print("=" * 70)
    print("""
BUG SUMMARY:
  Sessions 38, 41-45 used `round_eval_with_addchains` which called
  matvec(S0_matrix, a). But S0_matrix = build_sigma_0() returns the matrix
  for multiplication by (1+s)^2 + (1+s)^13 + (1+s)^22 in F_2[s]/(s^32),
  NOT the standard ROTR-based Σ_0.

  This is because Sessions 13-26 worked in the s-basis (where ROTR_r =
  multiplication by (1+s)^r); the matrices computed there are correct in
  that basis. But Session 38's `round_eval_with_addchains` mixed:
    - s-basis matrix application (matvec(S0, a))
    - x-basis bit interpretation of `a`
    - integer ADD on x-basis values

  This is a basis confusion — the resulting "round" is some hybrid, not
  actual SHA-256.

VERIFICATION:
  For a = 0x80000020:
    matvec(build_sigma_0(), a) = 0x8aa66c60   (s-basis matrix application)
    Σ_0(a) = ROTR_2(a) ⊕ ROTR_13(a) ⊕ ROTR_22(a) = 0x21048208
  Mismatch confirmed.

IMPACT ON THEOREMS:
  - Sessions 13-26 (linear algebra in s-basis): CORRECT in their stated
    basis. Theorem 24.1, 25.1, 26.1 hold.
  - Sessions 38, 41-45 (bit-level computations): WRONG round function.
    Quantitative results (avalanche=5, defect=32 for complement, etc.) are
    about a non-SHA hybrid, not real SHA.

This Session 46 implements correct R and re-runs the critical experiments.
""")

    rerun_avalanche()
    rerun_complement()
    rerun_shl_test()
    rerun_cycle_length()

    print("""

============================================================
CONCLUSIONS
============================================================
After CORRECTED implementation:
- Avalanche: see above values
- Complement symmetry: see above
- SHL_1 commutator: see above (expect ≫ 0)
- Cycle length: see above (expect very long)

Comparing to Sessions 38, 41-45's WRONG values:
  - If similar magnitudes → original conclusions roughly correct, lucky.
  - If very different → original conclusions invalid; need full re-analysis.
""")


if __name__ == "__main__":
    main()
