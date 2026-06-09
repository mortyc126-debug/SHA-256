# Vol II reproduction — independent verification

First runnable code for Volume II (the differential-cryptanalysis volume had
no source on disk; everything below was written from scratch, importing
nothing from the methodology). Run: `python3 sha256_core.py && python3
wang_chain.py && python3 barrier_and_mitm.py`.

## What was verified

| Result | Claim | Reproduced | Status |
|---|---|---|---|
| SHA-256 impl | matches FIPS 180-4 | hashlib match on `""` and `"abc"` | ✓ |
| Base constants (§II.1.9 / 11_proof_audit) | C_IV, T2_0, BASE_A1, CONST_e1, Σ0/Σ1(0x8000) | 6/6 exact | ✓ |
| **T_WANG_CHAIN** (П-26/92) | δe₂..δe₁₆ = 0, P = 1.0 | **1000/1000** (both δ=0x80000000 and 0x8000) | ✓ |
| **T_WANG_BARRIER17** (П-26) | δe₁₇ = 0 has P ≈ 2⁻³² | **0/1000** | ✓ |
| **T_DE17_DECOMPOSITION** (П-11/12) | δe₁₇ = Δa₁₃ + ΔW₁₆ (mod 2³²) | **2000/2000** exact | ✓ |
| **T_2D_BIRTHDAY_NEGATIVE** (П-27C) | barrier B(W0,W1) not additively separable | mixed 2nd-difference 0/1000 | ✓ |

## Indexing note (for future re-verification)

`T_DE17_DECOMPOSITION` is stated as `δe₁₇ = Da₁₃ + ΔW₁₆`. The methodology uses
**1-indexed rounds**. The structural fact is: δe₁₇ = (δd entering round 16) +
δW₁₆, and the d-register entering round 16 equals the a-register three rounds
earlier via the shift chain d_r = a_{r−3}. In 0-indexed code this is δa after
round **12**, not 13. A first naive attempt at round 13 gave 0/2000; the
corrected index gives 2000/2000. The theorem is correct — the label is just
1-indexed. Worth making explicit in §II.3.2.

## Bearing on "MITM through state[16] = O(2⁸⁰)" vs "Ω(2¹²⁸) lower bound"

The methodology carries both an unverified, code-less estimate
("MITM through state[16] = O(2⁸⁰)", ∆EXP, П-871..900) and a proven lower
bound (Ω(2¹²⁸), T_COLLISION_LOWER_BOUND_128), plus a *verified* negative
(T_2D_BIRTHDAY_NEGATIVE, T_MITM_IMPOSSIBLE П-591). These can only be
consistent if the 2⁸⁰ figure is **not** a realized sub-birthday attack on the
full function.

The reproduction supports that reading. A meet-in-the-middle that splits the
r=17 barrier over independent message words needs the barrier value to be
(at least block-wise) **separable** at the meeting point. The exact structure
δe₁₇ = Δa₁₃ + ΔW₁₆ looks separable, but Δa₁₃ (carry-saturated, HW≈16) and
ΔW₁₆ (schedule-forced) are both nonlinear functions of the *same* free words —
and the separability probe over (W0,W1) returns 0/1000 (never separable). So
the prerequisite for a 2-parameter MITM split is empirically absent, exactly
as П-27C states. The 2⁸⁰ number should be downgraded to "optimistic estimate,
contradicted by T_2D_BIRTHDAY_NEGATIVE" until a concrete algorithm exists.

## Genuinely open next probe (not yet tried in the corpus)

П-27C only tested separability over the (W0, W1) pair. A natural untried
escalation: search *all* low-dimensional subspaces of the 16 free message
words for one where the barrier function becomes (even approximately)
separable, or where the mixed 2nd-difference is biased away from uniform.
A nonzero bias there would be the first crack toward a MITM split. Cheap to
run; likely null, but it is the honest "try the next wall" move and extends
П-27C rather than repeating it.
