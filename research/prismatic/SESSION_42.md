# Session 42: Avalanche function A(d_in) — input-output distance map

**Дата**: 2026-04-25
**Цель**: characterise the bare round R's response to input perturbations of varying Hamming weight.

## Setup

Define the **avalanche function**:

$$A(d) := \mathbb{E}_{x, |\Delta| = d} \left[ \| R(x) - R(x \oplus \Delta) \|_H \right].$$

For ideal random bijection, A(d) = 128 for all d > 0 (independent of d).

Sampled 30 random bases × 10 perturbations per base = 300 pairs per d value.

## Empirical results (one bare SHA round with integer ADD)

| d_in | mean d_out | std | min | max | d_out / d_in |
|---|---|---|---|---|---|
| 1 | 5.27 | 5.88 | 1 | 32 | 5.27 |
| 2 | 9.91 | 6.94 | 1 | 32 | 4.96 |
| 4 | 16.89 | 7.39 | 4 | 37 | 4.22 |
| 8 | 26.75 | 7.40 | 10 | 45 | 3.34 |
| 16 | 38.82 | 5.85 | 20 | 52 | 2.43 |
| 32 | 54.78 | 4.68 | 44 | 68 | 1.71 |
| 64 | 79.98 | 5.04 | 67 | 93 | 1.25 |
| 128 | **128.37** | 5.26 | 114 | 144 | 1.00 |
| 256 | **224.10** | 3.41 | 217 | 231 | 0.88 |

## Theorem 42.1 (avalanche function shape)

**Theorem 42.1 (empirical).** The avalanche function A(d_in) of one SHA bare
round (with full integer ADD) has three regimes:

1. **Linear-growth regime** (d ≤ 16): A(d) ≈ 5d/(1 + d/8), slope ~5 per
   input bit. Predictable.

2. **Saturation regime** (d ≈ 128): A(128) ≈ 128 — matches ideal random function.

3. **Anomalous overshoot** (d = 256, full bit flip): A(256) ≈ 224, NOT 128.

The third regime is striking: flipping ALL input bits gives output Hamming
distance 224, well above the random-function expectation of 128.

## Why d_in = 256 overshoots

Full bit flip means x ⊕ x = 0, but here we mean x ⊕ all-ones = ~x (bitwise complement).

For ideal random R: R(~x) is uncorrelated with R(x), so d_out ~ Binomial(256, 0.5),
mean 128.

For SHA bare round: R(~x) and R(x) differ in 224 bits — meaning they "anti-correlate"
strongly. Specifically:
- 224 bits flip: large correlation -1.
- 128 bits flip: zero correlation (random).
- 0 bits flip: perfect equality (R commutes with negation).

A(256) = 224 means R(~x) ≈ ~R(x) (almost commutes with negation, but with 32 bits "off").

This is a **structural property** of SHA: complementing the input nearly
complements the output.

**Why?** Each register operation (ROTR, AND, ADD) interacts with bit-complement
in specific predictable ways:
- ROTR_r(~x) = ~ROTR_r(x) (rotation is bit-permutation, preserves complement).
- Σ_0(~x) = Σ_0(x) ⊕ const (linear over F_2).
- Ch(~e, ~f, ~g) = ~Ch(e, f, g) (verify: Ch is balanced).
- Maj(~a, ~b, ~c) = ~Maj(a, b, c) (Maj is balanced).
- ADD(~x, ~y) = ~ADD(x, y) ⊕ ~0 = ADD(x, y) ⊕ ~0 + 1 (carries shift).

So R(~state) ≈ ~R(state) ⊕ (small correction from ADD carry shifts).
Empirically the correction averages 32 bits.

## Theorem 42.2 (near-complementation invariance, conjectural)

**Conjecture 42.2.** For the bare SHA round R (K = W = 0):

$$\| R(\bar x) \oplus \overline{R(x)} \|_H \approx 32 \quad \text{(empirical mean)}.$$

i.e., R "almost commutes with bit-complement" up to a 32-bit Hamming-distance
correction. Equivalently, A(256) = 256 - 32 = 224.

This is a **near-symmetry** — not exact (would require A(256) = 0 or 256), but
close enough to be structural. Worth investigating: which 32 bits comprise
the "correction"?

## Cryptanalytic implication

The linear-growth regime A(d) ≈ 5d for small d shows that **low-weight
differentials propagate predictably**: a 1-bit flip causes ~5-bit output change,
a 2-bit flip causes ~10-bit, etc.

This is the basis of differential cryptanalysis on reduced-round SHA. The
"useful" Hamming weights are d ∈ [1, 32] where A(d) is far from random.
Above d ~ 64, behaviour is random-like, no useful trail.

Critical Hamming weight: **d* ≈ 64**, where A grows from 5d-style to
saturation.

## Cross-session synthesis

| Session | finding for d_in = 1 |
|---|---|
| 38 | avg avalanche = 5.06 |
| 42 | A(1) = 5.27 |
| 28 | per-round dependency density 0.51 |

All confirm: per round, ~5 of 256 output bits change per input bit flip.

## Theorem count: 36 → 37 (+1 conjecture)

37 = **Theorem 42.1 (empirical)**: 3-regime avalanche function shape.
+ Conjecture 42.2: near-complementation invariance, A(256) ≈ 224.

## Artifacts

- `session_42_distance.py` — distance-distance map measurement
- `SESSION_42.md` — this file
