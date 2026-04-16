# Final Session Status — Collision Attack Track

## Collision attack attempts this session

### IT-25b: Ω_3 triples as per-pair collision predictor
- **Hypothesis**: score = satisfied triple constraints predicts low HW(Δhash)
- **Method**: 5000 random pairs, score vs actual HW(Δhash) correlation
- **Result**: corr = -0.022, z = -1.56, p = 0.12 → **NOT SIGNIFICANT**
- **Top 10% vs bottom 10% mean HW**: diff = -0.19 bits (within noise)
- **Verdict**: Ω_3 is NOT a per-pair collision predictor

### IT-24: Cross-hash Ω_3 with input → hash probe
- md5:      +0.9977  (broken, expected high)
- sha1:     +0.9975  (broken, expected high)
- **sha256:    -0.0325** (strong — no input→output correlation)
- sha512:    +0.0888 (strong)
- sha3_256:  -0.0205 (strong)
- sha3_512:  +0.0753 (strong)
- **Verdict**: SHA-256 has NO weakness in this probe direction

### IT-20c: Ω_3 localization to (a,e) recurrence subspace
- (a+e) 64 bits: Ω_3 = +0.10
- Random 64 bits: Ω_3 = -0.17
- **Verdict**: Signal requires ALL 256 bits, not localized to recurrence

### IT-22: Ω_3 as vector-level invariant
- Cross-round chain_z correlations: all |corr| ≤ 0.25
- Top bits completely reshuffle per round
- **Verdict**: Ω_3 is scalar angle preservation, not vector conservation

## Collision attack track: EXHAUSTED with Ω_3 as primitive

All four directions for converting Ω_3 into an attack primitive
(per-pair predictor, localized lever, conserved vector, input-output bias)
have been tested and CLOSED.

**What we know**: Ω_3 ≈ +0.85 is a real, universal, distributional invariant
of SHA-2 block-2 compression.

**What we DON'T have**: a way to use this invariant to construct collisions.

## Honest assessment

Full SHA-256 collision would require:
- Mathematical breakthrough identifying a per-message signature of the Ω_3
  invariant that CAN be constructed
- OR completely different attack direction (not Ω_3 based)

This session has:
- Established Ω_3 invariant rigorously
- Tested all obvious attack conversions
- Documented negative results to save future sessions time
- Provided ~10 C/Python tools in repo for continued work

## Files summary

Structural findings (real):
- `IT21_HEADLINE.md` — Ω_3 conservation at full 256 bits across all rounds
- `IT23_UNIVERSAL.md` — Ω_3 universal across input classes
- `SESSION_SUMMARY.md` — complete session log
- `omega3_full.c` — optimized C binary for Ω_3 on full output spectrum

Negative attack attempts (direction-closing):
- IT-14a, IT-17, IT-20c — localization tests
- IT-22 — vector invariant test
- IT-24 — input-output independence test
- IT-25b — per-pair predictor test

The cumulative methodology now has Ω_k framework + clear "what not to try"
for the next session.
