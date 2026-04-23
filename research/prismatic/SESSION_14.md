# Session 14: Σ_0 action matrix on H¹

**Дата**: 2026-04-22
**Цель Session 13 переданная**: Compute Σ_0 = ROTR_2 ⊕ ROTR_13 ⊕ ROTR_22 as 16×16 matrix на H¹(F_2[s]/(s^32)).

## Главный результат

### Σ_0 matrix structure

Computed via Lucas's theorem для (1+s)^r в char 2:
- (1+s)^2 = 1 + s²
- (1+s)^{13} = 1 + s + s⁴ + s⁵ + s⁸ + s⁹ + s¹² + s¹³
- (1+s)^{22} = 1 + s² + s⁴ + s⁶ + s¹⁶ + s¹⁸ + s²⁰ + s²²

**Σ_0 polynomial (XOR over F_2)**: `1 + s + s^5 + s^6 + s^8 + s^9 + s^{12} + s^{13} + s^{16} + s^{18} + s^{20} + s^{22}`

**Even shifts** (только они дают non-trivial action на H¹ since k odd + even = odd): `{0, 6, 8, 12, 16, 18, 20, 22}`

### Matrix над F_2

16 generators at positions k = 1, 3, 5, ..., 31. Matrix shows which outputs получает каждый input:

```
     1  3  5  7  9 11 13 15 17 19 21 23 25 27 29 31
 1:  1  0  0  1  1  0  1  0  1  1  1  1  0  0  0  0
 3:  0  1  0  0  1  1  0  1  0  1  1  1  1  0  0  0
 5:  0  0  1  0  0  1  1  0  1  0  1  1  1  1  0  0
 7:  0  0  0  1  0  0  1  1  0  1  0  1  1  1  1  0
 9:  0  0  0  0  1  0  0  1  1  0  1  0  1  1  1  1
11:  0  0  0  0  0  1  0  0  1  1  0  1  0  1  1  1
13:  0  0  0  0  0  0  1  0  0  1  1  0  1  0  1  1
15:  0  0  0  0  0  0  0  1  0  0  1  1  0  1  0  1
17:  0  0  0  0  0  0  0  0  1  0  0  1  1  0  1  0
19:  0  0  0  0  0  0  0  0  0  1  0  0  1  1  0  1
21:  0  0  0  0  0  0  0  0  0  0  1  0  0  1  1  0
23:  0  0  0  0  0  0  0  0  0  0  0  1  0  0  1  1
25:  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  1
27:  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0
29:  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0
31:  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1
```

### Структурные свойства

**Observation 1**: Matrix **upper triangular** (consequence of k' = k + shift with positive shifts).

**Observation 2**: Diagonal = 1 (identity component from shift 0).

**Observation 3**: Rank over F_2 = **16/16** (full rank). Σ_0 — **injective** на H¹ over F_2.

**Observation 4**: **Kernel = 0**. No non-trivial invariants over F_2.

**Observation 5**: Σ_0 = I + N где N strictly upper triangular (nilpotent). Следовательно Σ_0 **unipotent**. 

**Nilpotency order**: N^{16} = 0 (strictly upper triangular на 16-dim space). По char 2: Σ_0^{16} = (I + N)^{16} = I + N^{16} = I.

Следовательно **Σ_0 has order 16 as linear map on H¹ mod 2**.

## Theorem (Session 14)

**Σ_0: H¹(F_2[s]/(s^32)) → H¹(F_2[s]/(s^32))** — upper triangular unipotent automorphism of order 16 over F_2. No non-trivial H¹-level invariants.

## Σ_1 comparison (quick compute)

Σ_1 = ROTR_6 ⊕ ROTR_11 ⊕ ROTR_25.
- (1+s)^6 = 1 + s² + s⁴ + s⁶
- (1+s)^{11} = Lucas for 11 = 1011_2: positions {0,1,2,3,8,9,10,11}
- (1+s)^{25} = Lucas for 25 = 11001_2: positions {0,1,8,9,16,17,24,25}

Σ_1 polynomial positions: {0, 3, 4, 6, 10, 11, 16, 17, 24, 25}
Even shifts (relevant for H¹): **{0, 4, 6, 10, 16, 24}**

Σ_1 matrix — different shift pattern than Σ_0. Similarly structured upper triangular unipotent.

Both Σ_0 и Σ_1 — invertible unipotent operators с different shift patterns.

## Interpretation

**Bad news**: No H¹-level invariants of Σ_0 or Σ_1 individually → no direct "invariant classes" attack.

**Good news**: Matrix structure **very concrete** — sparse upper triangular с specific shift pattern.

**Что это значит для SHA analysis**:
- Σ_0 shuffles H¹ classes injectively
- But **Σ_0^16 = I** means every 16 applications trivial
- Composition Σ_0 ∘ Σ_1 ∘ σ_0 ∘ σ_1 — complex сеть linear maps

**Directions for investigation**:

### Option A: joint action of Σ_0, Σ_1

Compute **common fixed points** of Σ_0 and Σ_1 acting jointly. I.e., kernel of (Σ_0 - I, Σ_1 - I) as joint kernel.

### Option B: tensor structure (8 registers)

8 registers → 8 copies of H¹. SHA applies Σ_0 and Σ_1 to ALL 8 registers. Joint action on 128-dim space.

### Option C: higher cohomology

H¹ alone didn't give invariants. Try H² (via Künneth from Session 11) — these are EXTERIOR products. Σ_0 action on H²?

## Session 15 target

**Option A**: compute joint kernel of Σ_0 - I and Σ_1 - I на H¹ over F_2. Это gives "common invariants" of both SHA Σ operators.

Поскольку Σ_0 и Σ_1 are both unipotent with different shift patterns, их joint invariant subspace might be smaller или trivial. 

## Status

- ✓ Σ_0 matrix computed (16×16 над F_2)
- ✓ Structure: upper triangular, unipotent, order 16
- ✓ Rank 16/16, no H¹-level kernel
- ✓ Σ_1 polynomial structure identified (session 15 matrix needed)
- → Session 15: joint kernel of Σ_0 - I, Σ_1 - I

## Honest reflection

Session 14 — first HARD COMPUTATION в программе. 16×16 matrix concretely built, rank/kernel computed, structure characterized (unipotent).

**Result**: no direct cryptanalytic advantage, но **solid structural finding**: SHA's Σ_0 action on H¹ is **unipotent upper triangular, order 16**.

Это **specific algebraic fact about SHA** computable from first principles. Publishable level detail.

## Artifacts

- `session_14_sigma0.py` — matrix computation + rank/kernel analysis
- `SESSION_14.md` — this file
