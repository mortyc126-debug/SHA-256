# Session 45: Differential Distribution Table — flagged for re-verification (BUG FOUND)

**Дата**: 2026-04-25
**Цель**: compute single-bit-input-difference DDT for one round.

## Empirical results (with WRONG round function — see Session 46)

For 5 single-bit input differences Δ_in, sampled 1000 pairs each:

| Δ_in | distinct Δ_out | output bits affected |
|---|---|---|
| flip a_0 | 995 / 1000 | 33 / 256 |
| flip a_15 | 813 / 1000 | 18 / 256 |
| flip e_0 | 1000 / 1000 | 65 / 256 |
| flip e_15 | 988 / 1000 | 35 / 256 |
| **flip h_0** | **51 / 1000** | 24 / 256 |

The h_0 case is striking: only 51 distinct Δ_out values, with the most common one occurring 25.5% of the time, Hamming weight 2. This indicates h_0 has very predictable differential behavior.

## ⚠ Bug — same issue as Sessions 38, 41-44

The round function used the s-basis Σ_0 matrix applied to x-basis bits. Results are about a **non-SHA hybrid function**, not actual SHA round.

## What's likely real

For h_0: in real SHA round, h_0 enters BOTH T_1 (linearly via h) and a' (via T_1) and e' (via T_1). So flipping h_0 affects:
- a'_0 deterministically (linear contribution).
- e'_0 deterministically.
- Higher bits via carry propagation.

So real SHA's h_0 differential should also have low Hamming weight Δ_out (probably 2-5 bits), but the specific values may differ.

Pattern recognition (low distinct Δ_out, high frequency of certain Δ_out) likely **survives qualitatively** for any "linear bit input" (one whose flip propagates only via deterministic linear paths).

For e_0 (input to nonlinear Ch + Σ_1 + ADD chain): **highly variable** Δ_out — confirmed in real SHA semantically.

## Status

Quantitative DDT entries: not trustworthy. Qualitative pattern (linear-input bits give predictable Δ_out, nonlinear-input bits give random) likely correct.

## Artifacts

- `session_45_ddt.py` — DDT sampler (uses buggy round)
- `SESSION_45.md` — this file
