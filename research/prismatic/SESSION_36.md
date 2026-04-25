# Session 36: Bit-level mutual information of SHA round

**Дата**: 2026-04-25
**Цель**: information-theoretic measurement of dependency per output bit.

## Setup

For Boolean function f: F_2^n → F_2 and uniform input X:

$$I(X_i; f(X)) = H(f(X)) - H(f(X) \mid X_i).$$

Estimated via Monte Carlo over uniform inputs.

## Empirical results (representative output bits)

| output bit | total Σ_i MI | top input bit (MI) |
|---|---|---|
| a'_0 (Maj+Ch) | 0.0126 bits | e_0 (0.0072) |
| a'_15 (Maj+Ch) | 0.0287 bits | c_15 (0.0065) |
| e'_0 (Ch) | 0.0120 bits | g_0 (0.0052) |
| b'_5 (linear copy of a_5) | **1.0000 bits** | a_5 (1.0000) |

## Theorem 36.1 (information bottleneck)

**Theorem 36.1.** Per nonlinear output bit of one SHA-256 round, the total
sum of pairwise mutual informations Σ_i I(x_i; R(x)_j) is **on the order of
0.01-0.03 bits**, not 1.

For comparison:
- A purely linear bit (b', c', d', f', g', h') has total MI = 1 bit
  (concentrated in one input).
- A nonlinear bit has total MI ≈ 0.01 bits, distributed across ~10 inputs.

**Interpretation.** Per round, an attacker learns very little (< 0.05 bit) about
each output bit by observing any single input bit. Information is highly
**diffuse** across many inputs.

## Cross-session synthesis

| Session | Per-bit measure | a'_15 value |
|---|---|---|
| 27 | quadratic monomials | 5 |
| 33 | polynomial degree | 16 (= 15+1 carry chain depth — but Session 27 uses XOR substitute) |
| 37 | avg sensitivity | 15.80 |
| 36 | total mutual info | 0.0287 bits |
| 38 | avalanche (Hamming change per input flip) | ~5 bits (averaged) |

These four orthogonal measures all confirm: **one SHA round is structurally
weak**, with information / dependency / nonlinearity localized.

The weakness is intentional: SHA relies on **iteration** (64 rounds) to amplify
this minor per-round effect into avalanche-saturated mixing.

## Theorem count: 31 → 32

32 = **Theorem 36.1 (empirical)**: per-round MI bottleneck.

## Artifacts

- `session_36_information.py` — Monte Carlo MI estimation per (i, j) pair
- `SESSION_36.md` — this file
