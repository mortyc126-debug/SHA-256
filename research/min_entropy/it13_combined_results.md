# IT-13 Combined Results: Ω_3 architectural invariance test

## Setup
- HW=2 exhaustive inputs (N=130816)
- Full SHA-256 (block 1 + padding block 2)
- Top-24 output bits ranked by |direct_z| (bit5_max baseline)
- chain_3 via existing it4_q7d_chain3 C binary

## Arm 1: K-scan (feature = bit5_max)

| K | Ω_3 corr | same-sign | p (binom) |
|---|---|---|---|
| 16384 | +0.9987 | 24/24 | 1.19e-07 |
| 32768 | +0.9966 | 22/24 | 3.59e-05 |
| 65536 | +0.9966 | 24/24 | 1.19e-07 |
| 130816 | +0.9982 | 24/24 | 1.19e-07 |

**Verdict**: Ω_3 stable at +0.997±0.001 across 8× range of K.
**N-invariant**: signal does not dilute with sample size.

## Arm 2: feature-scan (K = 130816)

| feature | Ω_3 corr | same-sign | p (binom) |
|---|---|---|---|
| bit5_max (ref) | +0.9982 | 24/24 | 1.19e-07 |
| bit4_max | +0.9868 | 23/24 | 2.98e-06 |
| bit6_max | +0.9768 | 22/24 | 3.59e-05 |
| parity_lsb | +0.9782 | 23/24 | 2.98e-06 |
| mid_bit3 | +0.9779 | 23/24 | 2.98e-06 |

**Verdict**: Ω_3 ∈ [+0.977, +0.998] across 5 structurally different features.
**Feature-invariant**: signal does not depend on input feature choice.

## RO null comparison (from IT-6)

RO null band for Ω_3: mean ≈ 0, std ≈ 0.06.
Observed Ω_3 ≈ +0.98 → **16σ deviation**.
Sign-test 240/256 (full output map, IT-6) → p ≈ 10⁻⁴⁰.

## Interpretation

The block-2 compression F: state1 → state2 viewed as 256 boolean
functions F_b: {0,1}^256 → {0,1} has a Walsh spectrum where the
**3rd-order component dominates the variation across output bits**.

This is independent of:
- Input feature choice (any reasonable function of input position)
- Sample size (architectural, not statistical)

It is specific to:
- SHA-2 family (IT-1.3 showed SHA-3 / BLAKE2 give Ω_3 ≈ 0)
- 3rd-order Walsh subspace (other orders weaker, see IT-6b)
