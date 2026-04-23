# Session 15: Joint invariants of Σ_0 and Σ_1

**Дата**: 2026-04-22
**Цель Session 14 переданная**: compute joint kernel of Σ_0 − I, Σ_1 − I на H¹.

## Главный результат

**Joint kernel dim = 2** на H¹(F_2[s]/(s^32)) over F_2.

Basis invariants:
- [s^{29} · ds]
- [s^{31} · ds]

## Computation

### Σ_1 matrix structure (new for this session)

Σ_1 = ROTR_6 ⊕ ROTR_11 ⊕ ROTR_25

Lucas expansions:
- (1+s)^6 = 1 + s² + s⁴ + s⁶
- (1+s)^{11} = 1 + s + s² + s³ + s⁸ + s⁹ + s¹⁰ + s¹¹
- (1+s)^{25} = 1 + s + s⁸ + s⁹ + s¹⁶ + s¹⁷ + s²⁴ + s²⁵

Σ_1 polynomial positions: {0, 3, 4, 6, 10, 11, 16, 17, 24, 25}
Even shifts (relevant for H¹): **{0, 4, 6, 10, 16, 24}**

### Individual kernels

**Kernel(Σ_0 − I)** — fixed points of Σ_0 on H¹:
- dim = **3**
- Basis: [s^{27}·ds], [s^{29}·ds], [s^{31}·ds]

Structural reason: Σ_0 has shifts ∈ {6, 8, 12, 16, 18, 20, 22}. Minimum shift = 6. For k ≥ 26: k + 6 ≥ 32 > 31 → out of range. So k=27, 29, 31 are all **beyond shift reach**.

Wait but k=25: 25 + 6 = 31 ≤ 31, so k=25 NOT in kernel. Correct.
k=27: 27 + 6 = 33 > 31 ✓ fixed.
k=29: 29 + 6 = 35 > 31 ✓ fixed.
k=31: всегда fixed.

**Kernel(Σ_1 − I)** — fixed points of Σ_1:
- dim = **2**
- Basis: [s^{29}·ds], [s^{31}·ds]

Structural reason: Σ_1 has shifts ∈ {4, 6, 10, 16, 24}. Minimum shift = 4. For k ≥ 28: k + 4 ≥ 32 > 31 → fixed. So k=29, 31 in kernel. But k=27: 27+4=31 ≤ 31, NOT fixed.

### Joint kernel

**Joint kernel = Kernel(Σ_0 − I) ∩ Kernel(Σ_1 − I) = span{[s^{29}·ds], [s^{31}·ds]}**.

These are **common invariants** of Σ_0 and Σ_1 over F_2.

## Structural interpretation

### "Edge" invariants

Joint invariants живут на **TOP positions** H¹ structure (k = 29, 31):
- k = 29: generator of Z/2 (Session 10: v_2(30) = 1)
- k = 31: generator of Z/32 (v_2(32) = 5)

Как cyclic group: joint invariants ≅ Z/2 × Z/32 ≅ Z/2 ⊕ Z/32 (order 64).

### Почему top positions?

Invariance = shift doesn't "reach" the position. Max shifts для Σ_0, Σ_1:
- Σ_0 min shift = 6 → positions k ≥ 26 safe (k + 6 > 31 required → k > 25)
- Σ_1 min shift = 4 → positions k ≥ 28 safe

Joint safe: k ≥ 28. Odd k ≥ 29: {29, 31}. **2 positions → 2-dim joint invariants**.

### Generalizes

**Observation**: joint invariants of multiple Σ operators = positions beyond the smallest min-shift. Можно было бы сделать general theorem.

## Важное limitation

### σ_0, σ_1 не в этом framework

SHA-256 also uses message schedule operations:
- σ_0 = ROTR_7 ⊕ ROTR_18 ⊕ **SHR_3**
- σ_1 = ROTR_{17} ⊕ ROTR_{19} ⊕ **SHR_{10}**

**SHR** (shift right without wrap) — не rotation, не живёт в F_2[x]/(x^n - 1). Ломает cyclic structure.

Для SHR в cohomological framework нужна отдельная constructure — not cyclic group algebra, maybe monoidal semigroup или similar.

**Следствие**: наш H¹-анализ **incomplete для message schedule**. Covers только compression function rotation structure.

## Итог анализа cohomology SHA rotations

Для **single register** с Σ-operations применёнными:
- H¹ dimension: 16 over F_2 (order 2^31 over Z_2)
- Σ_0 invariant subspace: 3 dim
- Σ_1 invariant subspace: 2 dim
- Σ_0 AND Σ_1 jointly invariant: **2 dim**

Для SHA round function (full compression):
- 8 registers each with own cohomology
- Only "a" register gets Σ_0 action, only "e" register gets Σ_1
- Other registers: identity via feed-forward
- Joint analysis всех 8 registers + compression structure — Session 16+ territory

## Что мы теперь знаем

**Factual results** из cohomology direction:
1. Rotation cohomology H¹ = 2^31 per register, 2^248 total (Sessions 10-12)
2. ROTR_1 = identity on H¹, r ≥ 2 non-trivial (Session 13)
3. Σ_0 matrix = 16×16 unipotent, no invariants alone (Session 14)
4. Σ_0 has 3-dim kernel over F_2, Σ_1 has 2-dim, **joint 2-dim** (Session 15)

**Не captures пока**:
- XOR at bit level (different ring structure)
- AND operations (Ch, Maj)
- ADD mod 2^32 (different algebra)
- SHR (non-cyclic operation)
- Full SHA round composition

## Session 16 target

Option 1: **SHA round compression analysis** via our matrix framework для Σ_0 и Σ_1. Look at action of SHA round on full 8-register cohomology (2^248 classes).

Option 2: **Integrate SHR** — add non-cyclic shift to framework.

Option 3: **Step back и do MATHEMATICAL WRITE-UP** of everything. After 15 sessions, consolidate findings as a formal "paper draft" — definitions, theorems, computations. Makes it easier for others (or future sessions) to build on.

**Recommendation**: Option 3. 15 sessions = substantial material. Writing up consolidates understanding and makes future work clearer. Then Session 17+ continues building on clear foundation.

## Honest reflection

Session 15 — clean result (joint invariants = 2-dim). But limitations clear:
- Covers only ROTR-based operations
- Doesn't directly give attack (invariants don't "help" search space)
- H¹-level invariants = "what's fixed under rotation" = essentially TOP bits of word

Real SHA cryptographic complexity lives elsewhere:
- ADD carries (Sessions 2, 4 formulas — not yet integrated with cohomology)
- AND nonlinearity (Sessions 3, 4 — structural primitive)
- Inter-register feed-forward (T1, T2 structure)

Sessions 16-20 должны integrate these. Или мы can consolidate в Session 16 write-up and pick right direction for 17+.

## Status

- ✓ Σ_1 matrix structure computed
- ✓ Individual kernels (3 dim Σ_0, 2 dim Σ_1)
- ✓ Joint kernel = 2 dim (positions 29, 31)
- ✓ Identified SHR limitation
- → Session 16: consolidate findings in write-up OR integrate SHR

## Artifacts

- `session_15_joint.py` — Σ_1 matrix, kernels, joint invariants
- `SESSION_15.md` — this file
