# Session 17: AND integration — structural analysis

**Дата**: 2026-04-22
**Цель Session 16 переданная**: pick direction — recommend integrate AND.

## Главные observations

### 1. Change-of-basis x ↔ s via Lucas

Rotation ring F_2[x]/(x^n - 1) ≅ F_2[s]/(s^n) via s = x + 1.

Change-of-basis matrix **T** (x-basis → s-basis):
$$T[i, k] = 1 \iff \text{bin}(i) \subseteq \text{bin}(k)$$

(Lucas's theorem in char 2).

T is **upper triangular** (with 1's on diagonal), hence invertible over F_2.

### 2. AND as bilinear map

**x-basis**: AND is **pointwise product** — (x AND y)_i = α_i · α'_i where α_i, α'_i are x-basis coefficients.

In s-basis: compose T · diag(T⁻¹ y) · T⁻¹ for AND-with-fixed-y.

For n=8, sample computations:

| y (s-basis) | y (x-basis) | AND-with-y matrix rank |
|---|---|---|
| [1,0,...] | [1,0,...] | **1** |
| [0,1,0,...] (= s) | [1,1,0,...] | **2** |
| [1,1,0,...] (= 1+s = x) | [0,1,0,...] | **1** |

Note: AND-with-y matrices are **rank-deficient**, not upper triangular, not unipotent.

### 3. Qualitative difference ROTR vs AND

| Property | ROTR | AND-with-y |
|---|---|---|
| Ring op type | Ring automorphism (mult by unit) | Bilinear, projection |
| Matrix over F_2 | Upper triangular, unipotent | Generally rank-deficient |
| Full rank? | Yes (invertible) | No (usually projection) |
| Preserves H¹ structure? | Yes (automorphism) | No (collapses) |
| Action on cohomology | Linear isomorphism | Rank-decreasing linear map |

**Fundamental**: ROTR **rearranges** H¹ classes; AND **projects/eliminates** classes.

This mirrors cryptographic intuition: rotations are "lossless mixing", AND is the "non-linearity" that destroys information.

### 4. Ch, Maj decomposition

SHA uses:
- **Ch(e, f, g)** = (e AND f) XOR (NOT e) AND g = g XOR (e AND (f XOR g))
- **Maj(a, b, c)** = (a AND b) XOR (a AND c) XOR (b AND c) = (a AND (b XOR c)) XOR (b AND c)

Both reduce to **AND с XOR-аргумент + XOR-shift**.

In our framework:
- XOR part = ring addition in rotation ring (handled)
- AND part = bilinear, rank-deficient projection (not handled as automorphism)

Consequence: Ch, Maj cannot be single automorphisms on H¹. They're **compositions of linear + bilinear** operators.

## Теоретическое место AND в framework

### Bialgebra / Hopf structure

Две multiplications на F_2^n:
- **Convolution** (rotation ring): x^i · x^j = x^{(i+j) mod n}
- **Pointwise** (boolean ring = F_2^n product): e_i · e_j = δ_{ij} e_i

Эти dualize через **Fourier transform** (F_2-DFT). Формально, (F_2^n, ·_conv, ·_point) — **bialgebra** с matching unit/counit.

**Для cohomology**: bialgebra structure gives **cup products** + **coproducts** on cohomology. Но для F_2^n как product ring, higher cohomology тривиальна.

### Derived approach

В Bhatt-Scholze absolute prismatic framework, AND could be encoded через **derived** tensor product или **∞-category structures**. Это **specialist territory**, вне session-level work.

### Для SHA analysis

Реальный подход вероятно:
- **Compute cohomology BOTH ways**: rotation-H¹ and boolean-H^0
- **Combine via Fourier duality**: relate rotation eigenvalues to boolean basis
- **Study SHA round as mixing operator**: rearranging both structures simultaneously

Это **substantial research programme**, не single-session work.

## Honest limitation

Session 17 **not a success story**. Мы NOT built integrated framework — мы **confirmed the obstruction**:

- AND doesn't act as ring automorphism → no direct cohomology action
- AND-with-y rank varies → not single invariant
- Ch, Maj inherit this issue

**Conclusion**: to FULLY analyze SHA at cohomology level, нужно либо:
(a) Multi-ring / bialgebra framework combining rotation + boolean
(b) Derived (∞-categorical) framework (Bhatt-Scholze absolute prismatic)
(c) Accept partial framework — rotation cohomology only

## Path forward options для Session 18+

### Option 1: Stay realistic, focus rotation structure
Keep rotation-only framework. Continue exploring Σ_0, Σ_1, σ_0, σ_1 compositions. Produce detailed matrix analysis of full SHA round's ROTATION part.

**Pro**: concrete, computable
**Con**: doesn't capture AND/ADD, limited cryptanalytic relevance

### Option 2: Develop bialgebra framework
Build formal bialgebra structure on F_2^n combining convolution + pointwise. Study cohomology of the bialgebra itself.

**Pro**: captures both structures
**Con**: substantial new math, may be weeks of careful work

### Option 3: Declare completion + summary
Accept that we've built what we can at session-level. Consolidate и document honest limits. Next researcher (human specialist) picks up.

**Pro**: honest, prevents accumulating errors
**Con**: feels incomplete

### Recommendation

Based on realistic scope: **Option 1 или Option 3**.

**Option 1** делает Sessions 18-20: full SHA round rotation composition, Σ_0∘Σ_1, σ-compositions, message schedule rotation parts.

**Option 3** declares programme complete at current stage with PRISMATIC_PROGRAM.md as final product.

Lean toward **Option 1** — продолжаем concrete work.

## Status

- ✓ AND change-of-basis analysis via Lucas
- ✓ AND-with-y matrices computed (rank-deficient, not automorphism)
- ✓ Qualitative difference ROTR vs AND articulated
- ✓ Bialgebra structure identified (not developed)
- → Session 18: concrete Σ composition analysis OR declare completion

## Artifacts

- `session_17_and.py` — AND analysis + Ch/Maj decomposition
- `SESSION_17.md` — this file
