# Session 43: Structure of R(¬x) ⊕ ¬R(x) — flagged for re-verification (BUG FOUND)

**Дата**: 2026-04-25
**Цель**: decompose 32-bit correction from Conjecture 42.2 by bit position.

## Empirical results (with WRONG round function — see Session 46 postmortem)

Sampled 500 random x:
- Mean Hamming weight of R(¬x) ⊕ ¬R(x): **31.85** (matches Session 42's prediction).
- Std: 3.69, range [22, 43].

Per-register correction analysis:
| register | bits with deviation > 5% | avg deviation rate |
|---|---|---|
| a' | **32 / 32** | 0.496 |
| b' | 0 / 32 | 0.000 |
| c' | 0 / 32 | 0.000 |
| d' | 0 / 32 | 0.000 |
| e' | **32 / 32** | 0.500 |
| f' | 0 / 32 | 0.000 |
| g' | 0 / 32 | 0.000 |
| h' | 0 / 32 | 0.000 |

## Critical interpretation (Session 46 finding)

**The 32-bit correction concentrates ENTIRELY in registers a' and e'** — exactly the two registers where ADD-with-carry happens. The other 6 registers (pure shifts of input registers) anti-commute PERFECTLY with bit-complement.

The mean deviation rate of 0.5 in a'/e' means: each bit of a' (and e') flips with probability ~1/2 between R(¬x) and ¬R(x). This is **random behavior** on these 64 bits — not a structural near-symmetry.

So the apparent "32-bit correction" is just: 192 bits trivially anti-commute + 64 bits behave randomly (giving expected 32 random flips out of 64).

## Theorem 43.1 (revised)

**Theorem 43.1.** For one bare SHA round (with K, W = 0):
- Bits in registers b', c', d', f', g', h' (192 total): **PERFECTLY anti-commute** with bit-complement: R(¬x)_j = ¬R(x)_j.
- Bits in registers a', e' (64 total): random behavior, R(¬x)_j ⊕ ¬R(x)_j flips ~1/2 of the time.

**Consequence.** Conjecture 42.2's "near-symmetry" is not a deep structural fact — it's just the trivial commutation of pure-shift registers. ADD-output registers don't exhibit any complement-symmetry.

## ⚠ Bug discovered (postmortem in Session 46)

After completing this session, found that `round_eval_with_addchains` (the function used here, in 38, 41, 42, 44, 45) uses the **s-basis matrix S0** but applies it to **x-basis bit vectors** — these bases are different! Result: the "round" being computed is NOT the actual SHA round, but a hybrid that mixes representations incoherently.

The qualitative finding (192 bits anti-commute, 64 bits don't) likely **survives** because:
- The pure-shift registers b'..d', f'..h' don't depend on Σ at all (they're identity copies of input registers).
- The 64 bits in a', e' depend on Σ + ADD; whatever Σ does, the ADD-induced randomness dominates.

But quantitative numbers (mean 31.85, std 3.69) **may shift** when re-computed with correct round.

## Status

Conditional acceptance: qualitative result (per-register breakdown) likely correct; quantitative numbers need re-verification.

See Session 46 for full postmortem and corrected re-runs.

## Artifacts

- `session_43_complement.py` — analysis (uses buggy round)
- `SESSION_43.md` — this file
