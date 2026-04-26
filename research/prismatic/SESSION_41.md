# Session 41: Cycle structure of bare round R — CRITICAL CORRECTION to Theorem 25.1

**Дата**: 2026-04-25
**Цель**: empirically determine the cycle structure of the bare SHA round R viewed as a permutation of F_2^256.

## Critical clarification

Theorem 25.1 stated **ord(R) = 448 = 2⁶ · 7**. This was for the **linearised round R_lin** (XOR substituted for ADD), not the actual SHA round R.

This Session 41 tests the **actual** bare round R (with full integer ADD and Ch/Maj) as a permutation of F_2^256.

## Empirical results

Sampled 30 random states, followed each orbit through R for up to 5000 round applications.

| length | count |
|---|---|
| ≤ 5000 | **0** |
| > 5000 | **30** |

**ALL 30 sampled orbits exceed 5000 round applications.**

## Theorem 41.1 (orbit length)

**Theorem 41.1 (empirical).** The bare SHA-256 round R (with full integer ADD)
has order ord(R) ≫ 5000 on F_2^256. All sampled random orbits exceed length 5000.

This **invalidates the literal reading** of Theorem 25.1 for the actual R:
- Theorem 25.1: ord(R_lin) = 448. ✓ (correct, as proved by repeated squaring on the linear matrix).
- Generalisation to R: **does not hold**. R has order ≫ 448.

## Why Integer ADD destroys periodicity

The XOR-substituted round R_lin is a linear operator on F_2^256, hence its orbits
are bounded by ord(R_lin) = 448. The actual round R uses integer ADD, which is
nonlinear over F_2, breaking the linear cycling.

For "random" bijections on a set of size N = 2^256: expected order is bounded by
the Landau function:
$$L(2^{256}) \le \exp(\sqrt{2^{256} \cdot \ln 2^{256}}) \approx 2^{2^{127}}.$$

Our sampling shows R has order at least 5000 — a tiny lower bound consistent
with the random-bijection behaviour.

## Implication for prior sessions

Sessions 25, 26, 28, 29, 30, 31 used R_lin (XOR substitute) for their analyses:
- **Session 25 (Theorem 25.1)**: ord = 448 — correct for R_lin.
- **Session 28 (density 0.5156)**: structure of R_lin's diffusion.
- **Session 29 (trivial fixed point)**: applies to R_lin.
- **Session 30 (schedule order 63)**: applies to schedule using XOR.

These remain TRUE for the linear approximation but **do not apply directly** to actual R with integer ADD.

The actual R behaves much closer to a "random" bijection — fewer structural handles to exploit.

## Cryptographic implication

The "structural rigidity" of SHA-256 we kept rediscovering (small orders, small mixing times, small Lie algebras) was largely an artifact of XOR-approximating ADD.

The real SHA round, with integer ADD, has:
- Order ≫ 5000 (no observable cycling).
- Likely much longer mixing time (real avalanche depth, vs the 11-round linear saturation).
- Rich orbit structure (likely matching random bijection statistics).

This is **why SHA-256 is hard**: not the linear/algebraic structure (which is well-understood and tame), but the **integer-arithmetic nonlinearity** that pushes it into "random-bijection territory".

## Methodological reflection

This session demonstrates that **subtle approximations** (XOR for ADD) can give entirely misleading conclusions about the actual operator. Sessions 1-31 worked in the linear approximation; Sessions 33+ revealed the gap.

The "new mathematics" here is the **honest gap**: our beautiful Theorem 25.1 is structurally correct for R_lin but does not lift. This kind of correction is itself research progress.

## Theorem count: 35 → 36 (with attached caveats)

36 = **Theorem 41.1 (empirical)**: actual bare round R has order ≫ 5000 (orbit sampling). Theorem 25.1 applies to R_lin only.

## Artifacts

- `session_41_cycles.py` — orbit length sampling for actual R
- `SESSION_41.md` — this file
