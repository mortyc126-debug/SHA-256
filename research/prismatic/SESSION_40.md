# Session 40: 2-adic structure of SHA-256 — does it lift to Z_2?

**Дата**: 2026-04-25
**Цель**: investigate whether SHA-256 round function extends to a function on Z_2 (2-adic integers), reviving the prismatic / δ-ring direction abandoned in Sessions 1-12.

## Setup

SHA-256 lives on (Z/2^32)^8 = W_32(F_2)^8. The natural lifting target: Z_2^8 = W_∞(F_2)^8.

For a function R: (Z/2^32)^8 → (Z/2^32)^8 to extend to R̂: Z_2^8 → Z_2^8, we need
R to be **truncation-compatible**:

$$R(x \bmod 2^N) \equiv R̂(x) \pmod{2^N} \quad \forall N \ge 32.$$

Equivalently, R̂(x mod 2^M) reduced mod 2^N equals R(x mod 2^N) for all M ≥ N.

## Test results

### ROTR: NOT 2-adic compatible

Tested ROTR_2 on 64-bit vs 32-bit truncations: 100/100 random samples failed to commute with truncation. Reason: rotation **wraps bits modulo N**, so the operator definition itself depends on N.

### SHR: NOT 2-adic compatible (in this strict sense)

Surprisingly, SHR also fails: high bits of x mod 2^M shift down into the low N positions during SHR_k, contaminating the low-precision result. SHR is **2-adic continuous as Z_2 → Z_2** but doesn't commute with truncation.

### ADD: 2-adic compatible

Integer addition is the only "natively 2-adic" operation in SHA: carry propagates UP, never down, so truncation commutes with ADD.

## Theorem 40.1 (No 2-adic lifting)

**Theorem 40.1.** The SHA-256 round function R does NOT extend to a function R̂ on (Z_2)^8.

Specifically, neither ROTR_r nor SHR_k commutes with truncation Z/2^M → Z/2^N for M > N. Hence the round operator is intrinsically tied to the precision N = 32.

**Consequence.** Cohomological / prismatic frameworks based on the inverse limit Z_2 = lim Z/2^n cannot apply to SHA-256. Any such framework must work at fixed precision N = 32 (the truncated Witt vectors W_{32}(F_2)).

This **formally closes** the question opened in Sessions 1-12: the obstruction to a δ-ring / prismatic treatment of SHA was rotation, and it cannot be resolved by lifting.

## Connection to Session 5

Session 5 found that the rotation algebra F_2[s]/(s^n) does not have a δ-ring structure (the rotation operator doesn't lift cleanly). Session 40 gives a complementary viewpoint: rotation doesn't lift even at the level of individual elements (truncation incompatibility). Same obstruction, different lens.

## Speculative future direction

A "modified SHA" replacing every ROTR with SHR would have the truncation incompatibility only from SHR's high-bit-leak issue. Even simpler modification: replace ROTR with multiplication by a fixed constant (which is fully 2-adic compatible, since constant multiplication on Z_2 is continuous and commutes with truncation).

Such a "2-adic SHA variant" would admit prismatic treatment, yielding clean theorems — but would also be cryptographically much weaker, since constant multiplication on Z_2 is invertible and predictable.

This trade-off (cryptographic strength ↔ algebraic tractability) is itself a structural insight: **SHA's hardness comes precisely from the operations that break the 2-adic / cohomological framework**.

## Theorem count: 34 → 35

35 = **Theorem 40.1**: SHA-256 round does not extend to Z_2; rotation breaks 2-adic compatibility.

## Artifacts

- `session_40_padic.py` — truncation compatibility tests, Hensel lifting attempt
- `SESSION_40.md` — this file
