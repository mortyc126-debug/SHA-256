# Session 11: Multi-register cohomology via Künneth

**Дата**: 2026-04-22
**Цель Session 10 переданная**: multi-variable extension для 8 registers SHA-256.

## Setup

SHA-256 state = (R)^⊗8 где R = F_2[s_i]/(s_i^16) — rotation ring per register.

Per Session 10: H⁰(R) = Z_2, H¹(R) = ⊕ Z/2^{a_i} with exponents [1,2,1,3,1,2,1,4] (order 2^15), H^≥2(R) = 0.

## Künneth formula application

Для tensor product над Z_2 (with splitting since H⁰ = Z_2 free):
$$H^k(R^{\otimes n}) = \bigoplus_{\substack{I \subset \{1..n\} \\ |I| = k}} \bigotimes_{i \in I} H^1(R_i)$$

### H¹ (the main invariant)

$$H^1(R^{\otimes 8}) = \bigoplus_{i=1}^{8} H^1(R_i) \otimes \bigotimes_{j \ne i} H^0(R_j) = 8 \times H^1(R)$$

**Order: 2^15 × 8 = 2^120.**

### H^k для k ≥ 2 (higher cohomology)

- H² = ⊕_{i<j} H¹(R_i) ⊗ H¹(R_j) (C(8,2) = 28 pairs)
- H³ = 56 triples of H¹ tensor products
- ...
- H⁸ = 1 single 8-fold tensor product

Per computation:
| k | Copies | Exponent per copy | Total exp |
|---|---|---|---|
| 0 | 1 | 0 | 0 |
| 1 | 8 | 15 | 120 |
| 2 | 28 | 85 | 2380 |
| 3 | 56 | 585 | 32760 |
| 4 | 70 | 4369 | 305830 |
| 5 | 56 | 33825 | 1894200 |
| 6 | 28 | 266305 | 7456540 |
| 7 | 8 | 2113665 | 16909320 |
| 8 | 1 | 16843009 | 16843009 |

Grand total: ~2^{43.4M}.

## Interpretation — careful reading

**Не следует** интерпретировать 2^{43M} как "cohomology bigger than SHA security". Это **misleading**:

1. **H^k for k ≥ 2 are derived** from H¹ via exterior/tensor products. They don't add independent information, they're determined by H¹.

2. **Cryptanalytic advantage требует invariants that SHA round preserves**. A huge total cohomology doesn't mean an attack — it means our ring is structurally rich.

3. **Fair comparison**: H¹ = 2^120 as "principal invariant". This IS less than 2^128 birthday.

## Honest comparison

**Principal rotation cohomology** (H¹):
- Single register: 2^15
- Full 8-register SHA state: **2^120**
- SHA-256 birthday: 2^128
- Shortfall: **2^8** (256×)

So если этот invariant preserved by SHA round function, мы получаем 2^120 possible "states modulo cohomology". Still short of 2^128.

## What's Missing

Session 11 computes **only rotation** cohomology. Real SHA round includes:
- **Rotations** Σ₀, Σ₁, σ₀, σ₁ — captured by our framework
- **XOR** (Ch, Maj, main equations) — NOT captured (different operation class)
- **AND** (Ch, Maj internal) — NOT captured (primitive from Session 3-4)
- **ADD** mod 2^32 — respects δ but interacts non-trivially with cohomology

**Integrating XOR/AND/ADD** into the cohomology framework — это Session 12+ territory.

## Sub-structures of H¹ that might matter

H¹(R^⊗8) decomposes as:
- 8 copies × [Z/2 ⊕ Z/4 ⊕ Z/2 ⊕ Z/8 ⊕ Z/2 ⊕ Z/4 ⊕ Z/2 ⊕ Z/16]
- Total 64 cyclic factors

Factor type distribution per register: Z/2 (4 times), Z/4 (2), Z/8 (1), Z/16 (1).
Across 8 registers: Z/2 (32), Z/4 (16), Z/8 (8), Z/16 (8).

Filtration by 2-adic depth:
- Z/2-part: order 2^32 — "light" information
- Z/4-part: order 2^32
- Z/8-part: order 2^24
- Z/16-part: order 2^32

Total 2^120.

**Observation**: наибольшее **single torsion class** имеет order Z/16. Mod higher torsion, main invariant — Z/2 → Z/16 spectrum of 2-adic depths.

## Открытые вопросы Session 12+

### Q1: SHA round function acting on cohomology
Ключевой вопрос: SHA round — автоморфизм всей системы? Если да, сохраняет ли cohomology классы?

Intuitively:
- Rotations Σ₀, Σ₁, σ₀, σ₁ — определены algebraically (ROTR matrices)
- They have ACTION on rotation ring R = F_2[s]/(s^{16})
- This action induces action on H¹

Compute what the action is — structural invariant SHA-256.

### Q2: XOR в cohomological framework
XOR не ring operation на R. Но наша Session 2 formula (δ(x⊕y) = ...) suggests XOR has **structural** role.

Possible approach: treat XOR как boundary map в some filtration spectral sequence. Derive its cohomological footprint.

### Q3: Ultimate target: H^*(SHA round) as ring map

Final goal: define R_SHA = ring capturing SHA state + round operations. Compute H*(R_SHA). Round function → morphism on H*. Analyze orbits, fixed points, invariants.

**Realistic estimate**: Sessions 12-15 для XOR integration, 16-20 для AND, 21+ для full SHA.

## Status

- ✓ Künneth formula applied для 8 registers
- ✓ H¹(R^⊗8) = 2^120 computed rigorously
- ✓ Higher H^k computed but interpreted carefully (derived, not new)
- ✓ Honest comparison: 2^120 < 2^128 birthday
- → Session 12 target: integrate XOR via Session 2 formula

## Artifacts

- `session_11_kunneth.py` — Künneth computation
- `SESSION_11.md` — this file
