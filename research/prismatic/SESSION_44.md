# Session 44: Approximate symmetries — flagged for re-verification (BUG FOUND)

**Дата**: 2026-04-25
**Цель**: search for transformations T such that R(T(x)) ≈ T(R(x)).

## Empirical results (with WRONG round function — see Session 46)

| Transformation T | mean defect | std | class |
|---|---|---|---|
| Bit-complement | 32.16 | 3.44 | strong sym ★ |
| SHL_1 per register | **0.00** | 0.00 | EXACT |
| SHL_4 per register | **0.00** | 0.00 | EXACT |
| SHL_16 per register | **0.00** | 0.00 | EXACT |
| ROTR_1 per register | 19.54 | 9.60 | strong |
| ROTR_2 per register | 21.80 | 8.96 | strong |
| ROTR_8 per register | 32.16 | 3.72 | strong |
| ROTR_16 per register | 31.90 | 3.89 | strong |
| add 1 to register a | 15.98 | 3.04 | strong |
| add 2^16 to a | 10.80 | 2.60 | strong |
| swap registers a ↔ e | 64.18 | 6.97 | weak |
| swap a ↔ b | 48.04 | 4.41 | strong |
| swap b ↔ c | 48.80 | 4.54 | strong |

## ⚠ Suspicious results

The **SHL_1, SHL_4, SHL_16 commutators all give EXACTLY 0** — too clean. Investigation revealed: the "round" function used here was wrong (mixed s-basis matrix with x-basis bits, see Session 46 postmortem).

The "0.00 defect" for SHL_k means the buggy round happens to commute exactly with multiplication by 2^k. This is consistent with the buggy round being **polynomial multiplication in F_2[s]/(s^32) plus integer ADD** — and polynomial multiplication trivially commutes with multiplication by s^k.

So the SHL_k results are **artifacts of the bug**, not properties of real SHA-256.

## What is genuinely real?

After Session 46's correction, the key qualitative findings expected to survive:
1. Bit-complement gives small defect (~32) — true for real SHA, since 192 of 256 bits are pure shifts and trivially anti-commute.
2. Various swaps give moderate defect (~50) — likely true qualitatively.
3. ROTR-per-register defects 20-32 — depends on real round structure; may shift.
4. SHL-per-register defects ≠ 0 for real SHA — almost certainly the case.

## Status

Quantitative table SHOULD NOT be trusted. Re-run with corrected round function in Session 46.

Qualitative conclusion (no exact symmetries except complement-near-symmetry) likely correct.

## Artifacts

- `session_44_symmetries.py` — symmetry tests (uses buggy round)
- `SESSION_44.md` — this file
