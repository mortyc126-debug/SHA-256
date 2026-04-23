# Session 6: Truncation framework + first prism

**Дата**: 2026-04-22
**Цель Session 5 переданная**: rewrite findings в truncation framework + start prism exploration.

## Достигнуто

### 1. Truncation framework formalized

**Корректное утверждение**:
- Z_2 — это δ-ring (стандартное определение)
- δ: Z_2 → Z_2 с δ(x) = (x-x²)/2
- φ: Z_2 → Z_2 = identity (since φ(x) = x² + 2δ(x) = x² + (x-x²) = x)
- Z/2^n = Z_2 / 2^n Z_2 — quotient ring (NOT a δ-ring, by Kedlaya 2.2.6)
- δ **descends** to truncation map: x mod 2^n → δ(x) mod 2^{n-1}

**Verified empirically**: для n = 4, 8, 16, 32 проверено что δ(x + k·2^n) ≡ δ(x) (mod 2^{n-1}) для random x, k. Descent well-defined.

### 2. Session 2-4 findings restated correctly

| Old (incorrect) framing | Correct framing |
|---|---|
| "δ axioms verified on Z/2^n" | "δ on Z_2 descends well-defined to Z/2^n → Z/2^{n-1}" |
| "ADD respects δ-ring structure" | "ADD on Z_2 satisfies D2 → descends compatibly" |
| "XOR has discrepancy formula" | "XOR on Z_2 (bit-level) has δ-discrepancy formula derived from D2" |
| "AND not derivable" | "AND not expressible as polynomial in (+, ·, δ) on Z_2" |
| "ROTR breaks δ" | "ROTR doesn't extend to ring endomorphism of Z_2; its δ-image not predictable" |

Empirical verification re-run: все findings consistent, formulas held.

### 3. Crystalline prism (Z_2, (2)) verified

**Definition** (prism = (A, I) with conditions):
- A = δ-ring
- I ⊆ A — Cartier divisor (locally principal)
- A is (p, I)-complete
- I is **distinguished**: contains generator d с δ(d) = unit

**For (Z_2, (2))**:
- A = Z_2 ✓ (standard δ-ring)
- I = (2) — principal ideal of Z_2 ✓
- (2)-complete: Z_2 by definition ✓
- δ(2) = (2-4)/2 = -1 ∈ Z_2× (unit) ✓

**(Z_2, (2)) — valid prism**, конкретно "crystalline prism for p=2".

### 4. Critical insight — Frobenius is trivial on Z_2

**φ = identity on Z_2.** Это значит:
- На самом standard prism (Z_2, (2)) **нет нетривиального Frobenius**
- Прismatic cohomology over (Z_2, (2)) для тривиальных rings будет тривиальной
- Для **interesting** prismatic, нужны **larger δ-rings** где φ нетривиальна

Кандидаты для non-trivial φ:
- **Z_2[ζ_n]** для n взаимно простого с 2: φ(ζ_n) = ζ_n² (Galois действие)
- **W(F_{2^k})** для k > 1: φ — лифт Frobenius на F_{2^k}
- **R[[q-1]]** (q-Witt): φ — q-twist

## Концептуальное переосмысление

Наша исходная цель "применить prismatic к SHA" подразумевала что мы возьмём ring "связанный с SHA" и посчитаем prismatic cohomology. Но:

1. **Bool ring trivially**: Z_2 не ring с интересной prismatic cohomology по себе
2. **На (Z_2, (2)) prism — Frobenius тривиален**: attacks через φ-action не получится

**Правильная трактовка цели**: мы должны:
- Либо построить **larger δ-ring extension** Z_2 → R, где SHA имеет естественную форму, и φ_R нетривиально
- Либо использовать **другой prism** — не (Z_2, (2)), а что-то с богатой структурой

## Кандидаты для Session 7

### Option A: q-Witt / q-de Rham prism

Prism (Z_p[[q-1]], ([p]_q)) где [p]_q = (q^p - 1)/(q - 1) — q-аналог p. Это даёт q-de Rham cohomology — связь с rotations через q-numbers.

**Возможная связь**: rotations в SHA — циклические permutations. Если переписать в q-language, rotations могут стать q-twists (умножение на корень из единицы). Тогда δ-структура q-Witt может видеть rotations естественно.

### Option B: ramified Witt extension

Взять prism (W(F_2)[T]/(T² - 2), (T)) где T — uniformizer. δ(T) выбирается так чтобы δ-аксиомы выполнялись. Это даёт более богатую структуру.

### Option C: концептуальная пауза

Изучить более тщательно ATTEMPTED applications prismatic to non-arithmetic problems (если есть в литературе), посмотреть что у них работало.

**Рекомендация Session 7**: Option A (q-Witt). Причина: rotation = cyclic = q-related наиболее естественная.

## Что мы понимаем теперь

После 6 sessions:
- ✓ δ-ring framework solid и applied правильно
- ✓ Naive "SHA on Bool ring" → trivial (Kedlaya forces it)
- ✓ Z/2^n как quotient — корректное место для SHA
- ✓ ADD compatible, XOR derivable, AND/ROTR — не respect δ (consistent across approaches)
- ✓ Crystalline prism (Z_2, (2)) — well-defined но Frobenius trivial
- → Need richer prism / larger δ-ring для non-trivial structure

## Status Session 6

- ✓ Truncation framework formalized
- ✓ δ-descent well-defined проверено (n=4..32)
- ✓ φ = id on Z_2 verified
- ✓ (Z_2, (2)) verified as prism
- ✓ Sessions 2-4 reformulated correctly
- → Session 7 target: q-Witt prism exploration

## Artifacts

- `session_6_framework.py` — truncation framework + prism verification
- `SESSION_6.md` — this file
