#!/usr/bin/env python3
"""
EXP 181: SHA-256 = 4th ORDER RECURRENCE ON 2 VARIABLES

The shift register means:
  b=a[-1], c=a[-2], d=a[-3], f=e[-1], g=e[-2], h=e[-3]

SHA-256 round = update rule:
  a_new = f(a, a[-1], a[-2], e, e[-1], e[-2], e[-3], W, K)
  e_new = g(a[-3], e, e[-1], e[-2], e[-3], W, K)

This is a 2-variable, 4th-order nonlinear recurrence.
NOT an 8-variable, 1st-order system!

IMPLICATION: The collision equation is on 2×32 = 64 bits,
not 8×32 = 256 bits. Birthday on 64 bits = 2^32?!

Wait — that can't be right. The 64-bit recurrence has MEMORY
(depends on 4 previous steps), so the effective state IS 256 bits.
But the DYNAMICS are driven by only 64 fresh bits per step.

EXPLORE: Does the recurrence formulation reveal attack angles
that the 8-word formulation hides?
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def verify_recurrence(N=100):
    """Verify: SHA-256 round function = recurrence on (a, e)."""
    print(f"\n{'='*60}")
    print(f"VERIFY: SHA-256 = RECURRENCE ON (a, e)")
    print(f"{'='*60}")

    exact = 0
    for _ in range(N):
        M = random_w16()
        W = schedule(M)
        states = sha256_rounds(M, 10)

        for r in range(4, 10):
            # Extract a-history and e-history
            a_r = states[r][0]; a_r1 = states[r-1][0]
            a_r2 = states[r-2][0]; a_r3 = states[r-3][0]
            e_r = states[r][4]; e_r1 = states[r-1][4]
            e_r2 = states[r-2][4]; e_r3 = states[r-3][4]

            # The recurrence says:
            # b = a[-1], c = a[-2], d = a[-3]
            # f = e[-1], g = e[-2], h = e[-3]
            b = a_r1; c = a_r2; d = a_r3
            f = e_r1; g = e_r2; h = e_r3

            # Verify these match the actual state
            assert states[r][1] == b, f"b mismatch at r={r}"
            assert states[r][2] == c, f"c mismatch"
            assert states[r][3] == d, f"d mismatch"
            assert states[r][5] == f, f"f mismatch"
            assert states[r][6] == g, f"g mismatch"
            assert states[r][7] == h, f"h mismatch"

            # Compute a_new and e_new from recurrence
            T1 = (h + sigma1(e_r) + ch(e_r, f, g) + K[r] + W[r]) & MASK
            T2 = (sigma0(a_r) + maj(a_r, b, c)) & MASK
            a_new_recurrence = (T1 + T2) & MASK
            e_new_recurrence = (d + T1) & MASK

            # Verify
            assert states[r+1][0] == a_new_recurrence
            assert states[r+1][4] == e_new_recurrence
            exact += 1

    print(f"  Verified: {exact}/{exact} — SHA-256 IS a recurrence on (a, e)")
    print(f"\n  RECURRENCE EQUATIONS:")
    print(f"    a[r+1] = (h[r-3] + Σ₁(e[r]) + Ch(e[r], e[r-1], e[r-2]) + K[r] + W[r])")
    print(f"             + (Σ₀(a[r]) + Maj(a[r], a[r-1], a[r-2]))  mod 2^32")
    print(f"    e[r+1] = a[r-3] + h[r-3] + Σ₁(e[r]) + Ch(e[r], e[r-1], e[r-2])")
    print(f"             + K[r] + W[r]  mod 2^32")
    print(f"    (where h[r-3] = e[r-3])")
    print(f"\n    Substituting h = e[-3]:")
    print(f"    a[r+1] = F(a[r], a[r-1], a[r-2], e[r], e[r-1], e[r-2], e[r-3], W[r], K[r])")
    print(f"    e[r+1] = G(a[r-3], e[r], e[r-1], e[r-2], e[r-3], W[r], K[r])")

def analyze_recurrence_jacobian(N=200):
    """Jacobian of the 2-variable recurrence.
    d(a_new, e_new)/d(a, e) — how sensitive are new values to current?"""
    print(f"\n{'='*60}")
    print(f"RECURRENCE JACOBIAN: 64×64 instead of 256×256")
    print(f"{'='*60}")

    # The recurrence has 2 outputs (a_new, e_new) = 64 bits
    # and depends on a[r], a[r-1], a[r-2], a[r-3], e[r], e[r-1], e[r-2], e[r-3]
    # = 8×32 = 256 input bits

    # BUT: the IMMEDIATE inputs are a[r] and e[r] (64 bits)
    # The older values are FIXED (already determined).
    # So the effective Jacobian is 64×64.

    # Compute: d(a_new)/da[r] and d(a_new)/de[r] (32×32 each)
    # = total 64×64 Jacobian

    for r_test in [5, 20, 50]:
        singular_vals = []

        for _ in range(N):
            M = random_w16()
            W = schedule(M)
            states = sha256_rounds(M, r_test + 1)
            s = states[r_test]

            J = np.zeros((64, 64))

            # Perturb a[r] (word 0) bits
            for b in range(32):
                s_pert = list(s); s_pert[0] ^= (1 << b)
                s_next = sha256_round(s_pert, W[r_test % 64], K[r_test % 64])
                s_base = sha256_round(list(s), W[r_test % 64], K[r_test % 64])

                for ob in range(32):
                    J[ob, b] = ((s_next[0] ^ s_base[0]) >> ob) & 1  # da_new/da
                    J[32 + ob, b] = ((s_next[4] ^ s_base[4]) >> ob) & 1  # de_new/da

            # Perturb e[r] (word 4) bits
            for b in range(32):
                s_pert = list(s); s_pert[4] ^= (1 << b)
                s_next = sha256_round(s_pert, W[r_test % 64], K[r_test % 64])
                s_base = sha256_round(list(s), W[r_test % 64], K[r_test % 64])

                for ob in range(32):
                    J[ob, 32 + b] = ((s_next[0] ^ s_base[0]) >> ob) & 1  # da_new/de
                    J[32 + ob, 32 + b] = ((s_next[4] ^ s_base[4]) >> ob) & 1  # de_new/de

            _, sigma, _ = np.linalg.svd(J)
            singular_vals.append(sigma)

        avg_sigma = np.mean(singular_vals, axis=0)
        rank = np.sum(avg_sigma > 0.5)

        print(f"\n  Round {r_test}: 64×64 recurrence Jacobian:")
        print(f"    σ₁={avg_sigma[0]:.3f} σ₂={avg_sigma[1]:.3f} "
              f"σ₅={avg_sigma[4]:.3f} σ₃₂={avg_sigma[31]:.3f} σ₆₄={avg_sigma[63]:.3f}")
        print(f"    Rank: {rank}/64")
        print(f"    Condition: {avg_sigma[0]/avg_sigma[63]:.1f}")

        n_damp = np.sum(avg_sigma < 1.0)
        print(f"    Damping modes (σ<1): {n_damp}/64")

def collision_as_recurrence(N=100):
    """Express collision in recurrence form.
    Collision: a₁[r] = a₂[r] AND e₁[r] = e₂[r] for all r ≥ some R."""
    print(f"\n{'='*60}")
    print(f"COLLISION IN RECURRENCE FORM")
    print(f"{'='*60}")

    print(f"""
  Standard collision: state₆₄(M₁) = state₆₄(M₂)
  = 256-bit condition on 512-bit input

  Recurrence collision: a₆₄(M₁) = a₆₄(M₂) AND e₆₄(M₁) = e₆₄(M₂)
  = 64-bit condition!

  BUT: a₆₄ depends on (a₆₃, a₆₂, a₆₁, a₆₀, e₆₃, e₆₂, e₆₁, e₆₀)
  which are ALL determined by the full history.

  So: matching a₆₄ and e₆₄ AUTOMATICALLY matches b₆₄=a₆₃, etc.
  IF the FULL HISTORY also matches.

  KEY QUESTION: Can we have a₆₄(M₁) = a₆₄(M₂) AND e₆₄(M₁) = e₆₄(M₂)
  WITHOUT the full history matching?

  YES — if a and e CONVERGE at some round R, then for all r > R:
    a₁[r] = a₂[r] and e₁[r] = e₂[r] (deterministic from convergence point).
    But also: b₁[R+1] = a₁[R] = a₂[R] = b₂[R+1] (shift register)
    So: FULL STATE matches at round R+3 (after shift flushes).

  COLLISION = CONVERGENCE of the (a, e) recurrence!
    """)

    # Test: if a[r] and e[r] match at some round r for two messages,
    # does the FULL state match at round r+3?
    print(f"  CONVERGENCE TEST (N={N}):")

    for R in [4, 8, 16]:
        convergences = 0
        full_matches = 0

        for _ in range(N * 100):
            M1 = random_w16(); M2 = random_w16()
            s1 = sha256_rounds(M1, R + 4)
            s2 = sha256_rounds(M2, R + 4)

            # Check if a and e match at round R
            if s1[R][0] == s2[R][0] and s1[R][4] == s2[R][4]:
                convergences += 1
                # Check if FULL state matches at R+3
                if s1[R+3] == s2[R+3]:
                    full_matches += 1

        print(f"  Round {R}: a&e convergences: {convergences}/{N*100}, "
              f"full state at R+3: {full_matches}")

    print(f"\n  ATTACK ANGLE:")
    print(f"    Instead of matching 256 bits at round 64,")
    print(f"    match ONLY 64 bits (a, e) at round 61.")
    print(f"    Shift register handles the rest by round 64.")
    print(f"")
    print(f"    Birthday on 64 bits = 2^32 (instead of 2^128)???")
    print(f"")
    print(f"    NO — because a[61] and e[61] depend on FULL HISTORY.")
    print(f"    Two different messages almost never produce same (a,e).")
    print(f"    The 64-bit match is as hard as 256-bit match.")
    print(f"    BUT: the recurrence formulation gives a DIFFERENT PATH:")
    print(f"    solve the RECURRENCE for convergence, not brute-force match.")

def recurrence_collision_search(N=15, budget=5000):
    """Search for collision by driving the (a,e) recurrence to converge."""
    print(f"\n{'='*60}")
    print(f"RECURRENCE-DRIVEN COLLISION SEARCH")
    print(f"{'='*60}")

    # Strategy: generate M₁, M₂ that have same a[61] and e[61].
    # Then state[64] will match (shift register flushes).
    #
    # We only need to match 64 bits, not 256!
    # But those 64 bits are computed from 64 rounds...
    #
    # Trick: compare only a-word and e-word of the hash
    # (= a[64] + IV[0] and e[64] + IV[4])
    # This is a 64-bit partial hash match.
    # Birthday: 2^32 on 64 bits.

    recurrence_results = []; full_results = []; random_results = []

    for trial in range(N):
        M1 = random_w16()
        H1 = sha256_compress(M1)

        # Recurrence target: match ONLY H[0] and H[4]
        best_ae = 256
        best_full = 256
        best_rand = 256

        ae_hashes = {}  # (H[0], H[4]) → count

        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)

            # a,e match distance (64 bits)
            d_ae = hw(H1[0] ^ H2[0]) + hw(H1[4] ^ H2[4])
            if d_ae < best_ae: best_ae = d_ae

            # Full match distance (256 bits)
            d_full = sum(hw(H1[w] ^ H2[w]) for w in range(8))
            if d_full < best_full: best_full = d_full

            # Multi-target on (a,e) only — 64-bit birthday
            ae_key = (H2[0], H2[4])
            if ae_key in ae_hashes:
                best_ae = 0  # Exact a,e match!

            # Compare with stored a,e
            for ae_old in list(ae_hashes.keys())[-30:]:
                d = hw(H2[0] ^ ae_old[0]) + hw(H2[4] ^ ae_old[1])
                if d < best_ae: best_ae = d
            ae_hashes[ae_key] = 1

        recurrence_results.append(best_ae)
        full_results.append(best_full)

        # Random 64-bit comparison
        best_rand_ae = 256
        for _ in range(budget):
            M2 = random_w16()
            H2 = sha256_compress(M2)
            d = hw(H1[0] ^ H2[0]) + hw(H1[4] ^ H2[4])
            if d < best_rand_ae: best_rand_ae = d
        random_results.append(best_rand_ae)

    ra = np.array(recurrence_results); fa = np.array(full_results)
    rd = np.array(random_results)

    print(f"\n  Results (64-bit a,e match):")
    print(f"    Recurrence (multi-target): avg={ra.mean():.1f}, min={ra.min()}")
    print(f"    Random (direct):           avg={rd.mean():.1f}, min={rd.min()}")
    print(f"    Full 256-bit match:        avg={fa.mean():.1f}, min={fa.min()}")

    gain_ae = rd.mean() - ra.mean()
    print(f"\n    64-bit gain: {gain_ae:+.1f}")

    print(f"\n  THEORETICAL:")
    print(f"    64-bit birthday: 2^32 ≈ 4 billion")
    print(f"    256-bit birthday: 2^128")
    print(f"    Ratio: 2^96 = 10^29 times easier!")
    print(f"    BUT: 64-bit match ≠ full collision (need all 256 bits)")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 181: RECURRENCE ATTACK")
    print("SHA-256 = 4th order recurrence on (a, e)")
    print("=" * 60)

    verify_recurrence(50)
    analyze_recurrence_jacobian(100)
    collision_as_recurrence(50)
    recurrence_collision_search(N=12, budget=3000)

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
