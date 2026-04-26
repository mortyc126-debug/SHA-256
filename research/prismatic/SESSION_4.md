# Session 4: Structural derivation of ANF degree bound for δ

**Дата**: 2026-04-22
**Цель Session 3 переданная**: доказать pattern ANF degree = 2(k+1) для δ(x AND y).

## Главный результат

**Theorem (Session 4)**: δ(z) над Z для z ∈ Z_{≥0} имеет точную формулу
$$
\delta(z) = \sum_{i \geq 1} 2^{i-1}(1 - 2^i) z_i - \sum_{i < j} 2^{i+j} z_i z_j
$$
где z_i = bits of z. **Это квадратичный полином в z-bits над Z**. Верифицирован exact для z ∈ [0, 32).

**Corollary**: бит k числа δ(z) имеет ANF degree exactly **k+1** в z-переменных.

**Corollary**: в (x, y) переменных (где z_i = x_i·y_i), бит k имеет ANF degree **2(k+1)** — подтверждает Session 3 observation.

## Вывод формулы

Начинаем с δ(z) = (z − z²)/2 над Z.

Записываем z = Σ 2^i z_i где z_i ∈ {0, 1}.

z² = (Σ 2^i z_i)² = Σ 2^{2i} z_i² + 2·Σ_{i<j} 2^{i+j} z_i z_j

Используя z_i² = z_i (т.к. z_i ∈ {0,1}):
z² = Σ 2^{2i} z_i + 2·Σ_{i<j} 2^{i+j} z_i z_j

z − z² = Σ 2^i z_i − Σ 2^{2i} z_i − 2·Σ_{i<j} 2^{i+j} z_i z_j
       = Σ (2^i − 2^{2i}) z_i − 2·Σ_{i<j} 2^{i+j} z_i z_j

Деление на 2:
δ(z) = Σ 2^{i-1}(1 − 2^i) z_i − Σ_{i<j} 2^{i+j} z_i z_j

(Для i=0: (2^0 − 2^0)/2 = 0, т.е. z_0 не входит в δ(z)).

**Empirically verified** для z ∈ [0, 32), n = 5.

## Почему бит k имеет ANF degree k+1

δ(z) = linear_part + quadratic_part над Z. Оба — integer-valued.

Бит k числа δ(z) mod 2^{n-1} = k-й бит integer значения.

Integer выражение есть сумма terms с coeff'ами 2^{...}. Бит k суммы зависит от:
- Прямого вклада terms с coefficient bit k set
- **Carry cascade** от lower bits

Linear term c_i z_i contributes к bit k если bit k of c_i = 1. c_i = 2^{i-1}(1 − 2^i) = 2^{i-1} − 2^{2i-1}.
Quadratic term -2^{i+j} z_i z_j contributes к bit k если k = i+j (прямо).

**Carry cascade**: bit k суммы = bit_k(sum of lower bits + carries). Каждый carry — это AND двух битов (degree 2 в z-переменных).

После **k layers** carry cascade, effective ANF degree = **k + 1** (linear × k carries = degree k+1; quadratic + carries can reach same).

**В (x, y) variables**, z_i = x_i y_i (degree 2), так что degree in (x, y) = 2·(k+1). QED (informal).

## Что это значит для δ-ring extension

**Structural consequence**: операция AND совместима с δ в следующем precise смысле:
- δ(x AND y) имеет **bounded ANF complexity**: degree ≤ 2(k+1) per output bit
- Total ANF size: сумма по output битам, при этом bits от (n-1)/2 могут иметь до degree n
- Всё: δ(x AND y) — **polynomial in (x-bits, y-bits) of maximum degree 2n**

Это **controlled complexity**, не unbounded. Формализация возможна.

## Теоретический framework для "δ-ring + AND"

Назовём **"enhanced δ-ring"** структуру (A, δ, β):
- A — commutative ring (у нас Z/2^n)
- δ: A → A — δ-ring structure (axioms D1-D3)
- β: A × A → A — additional BILINEAR idempotent operation (у нас AND)

**Compatibility axioms** (выводимо из наших результатов):
- β(x, x) = x (idempotence)
- β(x, y) = β(y, x) (commutativity)
- β(β(x, y), z) = β(x, β(y, z)) (associativity)
- δ(β(x, y)) имеет bounded ANF complexity: degree ≤ 2(k+1) per bit k. Это **unified axiom** выражающий что δ "compatible" с β.

**Примечание**: существует ли такая структура в литературе? Не уверен. Возможные аналогии:
- **Boolean rings** (идемпотентная мультипликация), но без δ
- **λ-rings** (дополнительные operations λ^i), иная структура
- **Borger's big Witt**: generalized Witt framework

Если "enhanced δ-ring" — реально новая структура, это **mathematically interesting** само по себе.

## Открытые вопросы

### Q1: Доказать formula строго
Мой вывод неформален — использует "carry cascade degree analysis", но без precise bound statement. Нужно formal theorem с proof.

### Q2: ROTR в enhanced δ-ring
Наш framework говорит как AND вписывается в δ. А как rotations? Rotations не являются ring operations и не идемпотентны. Вероятно нужна **третья дополнительная axiom** для rotations — или признать что rotations ломают структуру.

### Q3: Existing literature
Нужен human expert в arithmetic geometry чтобы проверить: известен ли "enhanced δ-ring" в литературе? Если да — использовать существующие инструменты.

## Session 5 target

**Option A**: Formal proof theorem (ANF degree = k+1 for δ(z) bit k).  
Написать formal statement + proof строгий. Это даёт "published-quality" result.

**Option B**: Investigate ROTR in enhanced δ-ring framework.  
Существует ли расширение, совместимое с rotations? Вероятно нет (we saw rotation obstruction before), но давайте проверим формально.

**Option C**: Move to categorical formulation.  
Прыгнуть уровень абстракции: enhanced δ-ring как функтор из category of "AND-sets" в δ-rings. Подключить возможные existing frameworks.

**Рекомендация**: **Option A + B в комбинации**. Formal proof бита-degree pattern + ROTR analysis в том же framework. Это завершает "characterization of SHA в δ-language" на теоретическом уровне.

## Status

- ✓ Explicit formula для δ(z) as quadratic poly over Z in z-bits
- ✓ Verified on [0, 32) for n=5
- ✓ Understanding carry cascade → explains ANF degree 2(k+1) pattern
- ✓ Proposed "enhanced δ-ring" structure (A, δ, β)
- → Session 5 target: formal theorem OR ROTR in enhanced framework

## Artifacts

- `session_4_anf_proof.py` — ANF verification + formula derivation
- `SESSION_4.md` — this file
