#!/usr/bin/env python3
"""
EXP 126: ★⁻¹ Duality Deep Dive — Where Does Linearity Break?

From exp125: In ★⁻¹ dual space, collision equation is:
  δ(SUM) = 2 · δ(AND)  — LINEAR!

This is for ONE addition (feedforward: H[w] = IV[w] + state[w]).
But SHA-256 has ~400 additions across 64 rounds.

KEY QUESTION: If we express EVERY addition in ★⁻¹ form,
does the linearity survive through the entire computation?

The chain:
  Standard: a + b → result (carry is hidden, sequential)
  ★:        a + b → (a⊕b, a&b) → resolve carry → result
  ★⁻¹:     a ⊕ b → (a+b, a&b) → subtract 2·AND → result

In ★⁻¹, the XOR operation is decomposed into SUM and AND.
SHA-256 uses BOTH + and ⊕. In ★⁻¹:
  - Addition (+): is NATIVE (no decomposition needed)
  - XOR (⊕): decomposed as (a+b) - 2(a&b) — needs AND

So in ★⁻¹ space:
  - σ functions (which use ⊕ between ROTRs) become: ROTR₁ + ROTR₂ - 2(ROTR₁ & ROTR₂) + ...
  - Ch, Maj (which use ⊕ and &) become: mixed expressions

WHERE does linearity break? At the AND operations (Ch, Maj, carry).
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

# ★⁻¹ decomposition: a ⊕ b = (a + b) - 2·(a & b)
def dual_xor(a, b):
    """XOR via ★⁻¹: a⊕b = (a+b) - 2(a&b) mod 2^32"""
    return ((a + b) - 2 * (a & b)) & MASK

def test_dual_xor_exact(N=5000):
    """Verify ★⁻¹ XOR decomposition."""
    print(f"\n--- ★⁻¹ XOR VERIFICATION (N={N}) ---")
    exact = sum(1 for _ in range(N)
                for a in [random.randint(0, MASK)]
                for b in [random.randint(0, MASK)]
                if dual_xor(a, b) == (a ^ b))
    print(f"  dual_xor = real_xor: {exact/N:.6f}")

def test_dual_collision_equation(N=5000):
    """Express collision equation in ★⁻¹ and check linearity."""
    print(f"\n--- COLLISION IN ★⁻¹ SPACE ---")

    # Collision: H(M₁) = H(M₂)
    # ⟺ IV + s₁ = IV + s₂ (mod 2^32 per word)
    # ⟺ s₁ = s₂
    #
    # In ★: s₁ = s₂ ⟺ (s₁⊕s₂ = 0 AND carry(IV,s₁) = carry(IV,s₂))
    #   → δXOR = 0 AND δcarry = 0 (coupled, nonlinear)
    #
    # In ★⁻¹: s₁ = s₂ ⟺ s₁ - s₂ = 0
    #   → δSUM = 0 (single equation!)
    #   → In ★⁻¹ terms: δSUM = (s₁+s₂) - 2(s₁&s₂) = s₁⊕s₂ = 0
    #   Wait... that's circular.
    #
    # Let me rethink. The collision equation for feedforward:
    # H[w] = (IV[w] + state[w]) mod 2^32
    # δH[w] = 0 ⟺ (IV[w] + s₁[w]) = (IV[w] + s₂[w]) mod 2^32
    # ⟺ s₁[w] = s₂[w] mod 2^32
    #
    # This is trivial — collision just means states are equal.
    # The REAL question is: two DIFFERENT messages M₁ ≠ M₂ producing
    # the same state s after 64 rounds.
    #
    # So the hardness is in the ROUND FUNCTION, not feedforward.
    # Let's look at one ROUND in ★⁻¹.

    print(f"  Collision = s₁ = s₂ (states equal after 64 rounds)")
    print(f"  Hardness is in round function, not feedforward.")
    print(f"  Analyzing ONE ROUND in ★⁻¹...")

def test_one_round_dual(N=3000):
    """Express one SHA-256 round in ★⁻¹ space.

    Round function:
      T1 = h + Σ₁(e) + Ch(e,f,g) + K + W
      T2 = Σ₀(a) + Maj(a,b,c)
      a' = T1 + T2
      e' = d + T1

    Operations used:
      Addition (+): 7 times — NATIVE in ★⁻¹ (linear!)
      Σ₁(e) = ROTR₆(e) ⊕ ROTR₁₁(e) ⊕ ROTR₂₅(e) — uses XOR
      Σ₀(a) = ROTR₂(a) ⊕ ROTR₁₃(a) ⊕ ROTR₂₂(a) — uses XOR
      Ch(e,f,g) = (e&f) ⊕ (~e&g) — uses XOR and AND
      Maj(a,b,c) = (a&b) ⊕ (a&c) ⊕ (b&c) — uses XOR and AND

    In ★⁻¹, every ⊕ becomes (+ - 2·&). So:
      Σ₁(e) = ROTR₆(e) + ROTR₁₁(e) + ROTR₂₅(e)
               - 2·(ROTR₆(e) & ROTR₁₁(e))
               - 2·((ROTR₆(e)⊕ROTR₁₁(e)) & ROTR₂₅(e))
               ... recursively expanding ⊕
    """
    print(f"\n--- ONE ROUND IN ★⁻¹ (N={N}) ---")

    # Let's count: how many AND operations remain after ★⁻¹ conversion?
    # Original round:
    #   Σ₁: 2 XOR → 2 ANDs (from ★⁻¹ conversion) + 2 additions
    #   Σ₀: 2 XOR → 2 ANDs + 2 additions
    #   Ch: 1 AND + 1 AND + 1 XOR → 2 ANDs + 1 AND (from ⊕) = 3 ANDs
    #   Maj: 3 AND + 2 XOR → 3 ANDs + 2 ANDs = 5 ANDs
    #   T1: 4 additions → 4 additions (native)
    #   T2: 1 addition → 1 addition
    #   a',e': 2 additions → 2 additions
    #
    # Total ANDs in ★⁻¹: 2 + 2 + 3 + 5 = 12 AND operations per round
    # Total additions: ~9 (native, linear in ★⁻¹)

    print(f"  Per-round operation count:")
    print(f"    Standard:  7 additions + 2 XOR(σ) + Ch(3ops) + Maj(5ops)")
    print(f"    In ★⁻¹:   ~9 additions (LINEAR) + 12 ANDs (NONLINEAR)")
    print(f"")
    print(f"  The AND operations are the ONLY nonlinearity in ★⁻¹!")
    print(f"  12 ANDs per round × 64 rounds = 768 AND operations total")
    print(f"  vs ~400 additions (all linear in ★⁻¹)")

    # What if we could LINEARIZE the ANDs?
    # AND(a,b) in ★⁻¹ = (a·b) where · is bitwise multiplication
    # This is degree-2 over GF(2). Can't be linearized.
    #
    # BUT: what about STATISTICAL linearization?
    # If a and b are "random enough", then E[a&b] = a·b/4 + correction
    # For Bernoulli(0.5) bits: E[a_i & b_i] = 0.25

    # Test: how much does AND contribute to the round output?
    # Compare: round with AND vs round with AND replaced by constant

    def round_no_and(state, W_r, K_r):
        """Round with AND operations replaced by zero."""
        a, b, c, d, e, f, g, h = state
        # Σ₁ = ROTR₆ ⊕ ROTR₁₁ ⊕ ROTR₂₅ (keep as-is, it's XOR of rotations)
        S1 = sigma1(e)
        # Ch without AND: Ch = (e&f) ⊕ (~e&g) → 0 ⊕ 0 = 0
        Ch_approx = 0
        S0 = sigma0(a)
        # Maj without AND: 0
        Maj_approx = 0

        T1 = (h + S1 + Ch_approx + K_r + W_r) & MASK
        T2 = (S0 + Maj_approx) & MASK
        return [(T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g]

    # Measure divergence: round with AND vs without
    diffs_per_round = []
    for R in [1, 2, 4, 8, 16, 64]:
        dd = []
        for _ in range(N):
            W16 = random_w16()
            W = schedule(W16)

            s_real = list(IV); s_no_and = list(IV)
            for r in range(R):
                s_real = sha256_round(s_real, W[r], K[r])
                s_no_and = round_no_and(s_no_and, W[r], K[r])

            diff = sum(hw(s_real[w] ^ s_no_and[w]) for w in range(8))
            dd.append(diff)

        avg = np.mean(dd)
        diffs_per_round.append((R, avg))
        print(f"  AND contribution at round {R:>2}: {avg:.1f}/256 bits differ")

    print(f"\n  If AND ≈ 0: round function is LINEAR in ★⁻¹!")
    print(f"  At round 1: {diffs_per_round[0][1]:.1f} bits differ → AND is significant")

def test_dual_differential(N=5000):
    """The key test: is δ(output) a LINEAR function of δ(input) in ★⁻¹?

    For pairs (M₁, M₂), define:
      δM = M₁ - M₂ (arithmetic difference, ★⁻¹ native)
      δH = H₁ - H₂ (arithmetic hash difference)

    If SHA-256 were linear in ★⁻¹: δH = A · δM for some matrix A.
    Test: is this approximately true?
    """
    print(f"\n--- ★⁻¹ DIFFERENTIAL LINEARITY (N={N}) ---")

    # Test: δH(M₁, M₂) ≈ J · δM?
    # where J is the Jacobian and δ is arithmetic difference

    # Pick a base message
    M_base = random_w16()
    H_base = sha256_compress(M_base)

    # Compute Jacobian (arithmetic): perturb each word of M by 1
    J = np.zeros((8, 16), dtype=np.int64)
    for w in range(16):
        M_pert = list(M_base)
        M_pert[w] = (M_pert[w] + 1) & MASK
        H_pert = sha256_compress(M_pert)
        for hw_idx in range(8):
            J[hw_idx, w] = (H_pert[hw_idx] - H_base[hw_idx]) & MASK

    # Test linearity: for random δM, does J·δM predict δH?
    pred_errors = []
    for _ in range(N):
        # Small arithmetic perturbation
        delta_M = [random.randint(0, 255) for _ in range(16)]  # Small δ
        M_test = [(M_base[i] + delta_M[i]) & MASK for i in range(16)]
        H_test = sha256_compress(M_test)

        delta_H_real = [(H_test[w] - H_base[w]) & MASK for w in range(8)]

        # Linear prediction: δH ≈ Σ_w J[·,w] · δM[w]
        delta_H_pred = [0] * 8
        for w in range(16):
            for h in range(8):
                delta_H_pred[h] = (delta_H_pred[h] + J[h, w] * delta_M[w]) & MASK

        # Error
        err = sum(hw((delta_H_real[w] ^ delta_H_pred[w])) for w in range(8))
        pred_errors.append(err)

    pe = np.array(pred_errors)
    print(f"  Linear prediction error (small δM):")
    print(f"    Mean: {pe.mean():.2f} bits (0=linear, 128=random)")
    print(f"    Exact: {np.sum(pe == 0)/N:.6f}")

    # Now with LARGE perturbations
    pred_errors_large = []
    for _ in range(N):
        delta_M = [random.randint(0, MASK) for _ in range(16)]
        M_test = [(M_base[i] + delta_M[i]) & MASK for i in range(16)]
        H_test = sha256_compress(M_test)

        delta_H_real = [(H_test[w] - H_base[w]) & MASK for w in range(8)]
        delta_H_pred = [0] * 8
        for w in range(16):
            for h in range(8):
                delta_H_pred[h] = (delta_H_pred[h] + J[h, w] * delta_M[w]) & MASK

        err = sum(hw((delta_H_real[w] ^ delta_H_pred[w])) for w in range(8))
        pred_errors_large.append(err)

    pl = np.array(pred_errors_large)
    print(f"\n  Linear prediction error (large δM):")
    print(f"    Mean: {pl.mean():.2f} bits")

    # Per-δM-size: how does prediction degrade?
    print(f"\n  Prediction error vs perturbation size:")
    for max_delta in [1, 3, 7, 15, 31, 63, 127, 255, 1023, MASK]:
        errs = []
        for _ in range(1000):
            delta_M = [random.randint(0, max_delta) for _ in range(16)]
            M_test = [(M_base[i] + delta_M[i]) & MASK for i in range(16)]
            H_test = sha256_compress(M_test)
            delta_H_real = [(H_test[w] - H_base[w]) & MASK for w in range(8)]
            delta_H_pred = [0] * 8
            for w in range(16):
                for h in range(8):
                    delta_H_pred[h] = (delta_H_pred[h] + J[h, w] * delta_M[w]) & MASK
            err = sum(hw(delta_H_real[w] ^ delta_H_pred[w]) for w in range(8))
            errs.append(err)

        avg = np.mean(errs)
        bits = math.log2(max_delta + 1)
        print(f"    δM ≤ 2^{bits:>5.1f}: error = {avg:>6.1f}/256")

def test_dual_round_linearity(N=2000):
    """Per-round ★⁻¹ linearity: at which round does it break?"""
    print(f"\n--- PER-ROUND ★⁻¹ LINEARITY (N={N}) ---")

    M_base = random_w16()

    for R in [1, 2, 4, 8, 16, 32, 64]:
        s_base = sha256_rounds(M_base, R)[R]

        # Jacobian at this round
        J = np.zeros((8, 16), dtype=np.int64)
        for w in range(16):
            M_pert = list(M_base)
            M_pert[w] = (M_pert[w] + 1) & MASK
            s_pert = sha256_rounds(M_pert, R)[R]
            for h in range(8):
                J[h, w] = (s_pert[h] - s_base[h]) & MASK

        # Test with small perturbations
        errs = []
        for _ in range(N):
            delta_M = [random.randint(0, 1) for _ in range(16)]
            M_test = [(M_base[i] + delta_M[i]) & MASK for i in range(16)]
            s_test = sha256_rounds(M_test, R)[R]

            delta_s_real = [(s_test[h] - s_base[h]) & MASK for h in range(8)]
            delta_s_pred = [0] * 8
            for w in range(16):
                for h in range(8):
                    delta_s_pred[h] = (delta_s_pred[h] + J[h, w] * delta_M[w]) & MASK

            err = sum(hw(delta_s_real[h] ^ delta_s_pred[h]) for h in range(8))
            errs.append(err)

        avg = np.mean(errs)
        exact = np.sum(np.array(errs) == 0) / N
        print(f"  Round {R:>2}: mean_err = {avg:>6.2f}/256, exact = {exact:.4f}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 126: ★⁻¹ DUALITY DEEP DIVE")
    print("Where does linearity break?")
    print("=" * 60)

    test_dual_xor_exact(3000)
    test_dual_collision_equation()
    test_one_round_dual(1000)
    test_dual_round_linearity(1000)
    test_dual_differential(2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: ★⁻¹ DUALITY")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
