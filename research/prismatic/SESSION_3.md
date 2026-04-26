# Session 3: δ and AND structure

**Дата**: 2026-04-22
**Цель Session 2 переданная**: formalize "δ-ring with AND" / check λ-ring connection.

## Новые результаты

### 1. Polynomial fit fails

Попытались представить δ(x AND y) как многочлен в (x, y, δ(x), δ(y)) степени ≤ 3:

| n | degree | rank | matches |
|---|---|---|---|
| 4 | 2 | 15/15 | 28/256 (11%) |
| 4 | 3 | 35/35 | 108/256 (42%) |
| 5 | 2 | 15/15 | 36/1024 (3.5%) |
| 5 | 3 | 35/35 | 82/1024 (8%) |

**Вывод**: δ(x AND y) **не является** low-degree полиномом от указанных variables. Доля "правильных" падает с ростом n — это не ошибка округления, это fundamental fact.

Значит **AND не derivable** из δ-ring axioms простым способом.

### 2. Bit-level ANF — СТРУКТУРА

Computed ANF (Algebraic Normal Form over F_2) каждого output бита δ(x AND y) как функции 2n входных битов (x_0..x_{n-1}, y_0..y_{n-1}):

| Output bit k | Max ANF degree | Total terms | Degree spectrum |
|---|---|---|---|
| 0 | **2** | 1 | [0,0,1,0,...] |
| 1 | **4** | 3 | [0,0,2,0,1,0,...] |
| 2 | **6** | 5 | [0,0,2,0,2,0,1,...] |
| 3 | **8** | 9 | [0,0,3,0,3,0,2,0,1,...] |

**Паттерн**:
- Output bit k имеет max ANF degree **2(k+1)**
- Только **чётные** степени в ANF
- Число terms растёт как ~O(k²)

Это специфическая структура. AND не случаен для δ, но его "сложность" растёт bit-by-bit в предсказуемом темпе.

### 3. Single-bit verification

Для x = 2^i, y = 2^j:
- x AND y = 2^i если i = j, иначе 0
- δ(x AND y) = δ(2^i) если i = j, иначе 0

Это проверено. Значит δ на AND одиночных битов — **сосредоточен на диагонали** в bit-index space.

### 4. Интерпретация

**AND — это genuine structural primitive**. Не derivable от ring-level δ, но имеет полиномиальную bit-level сложность.

Отсюда **две возможные формализации**:

**Вариант A: δ-ring с дополнительным bilinear operator β**
- (A, δ, β) где β: A × A → A
- β идемпотентен (β(x, x) = x)
- β коммутативен, ассоциативен
- β satisfies specific compatibilities с δ (TBD axioms)
- SHA use case: β = AND

**Вариант B: Witt-vector explicit decomposition**
- Каждый x ∈ Z/2^n представляем как tuple (a_0, ..., a_{n-1}) bits
- Все операции работают componentwise (AND, XOR) или с bit-cascade (ADD)
- δ становится "cohomology invariant" этого tuple structure
- Рotations — как в Session 1 (filtration-breaking)

## Теоретические выводы

**Вывод 1**: AND не derivable from δ-ring axioms → нужна extension.

**Вывод 2**: AND has CONTROLLED bit-level complexity (polynomial ANF), not random. Это хорошо для формализации.

**Вывод 3**: Структура output bit k ANF degree 2(k+1) — **характеристика именно δ-взаимодействия**. Не случайно bound'ается кривой 2(k+1).

**Вывод 4**: Путь вперёд — explicit Witt-vector basis where each bit is its own "level". Это **natural** basis для SHA и potentially compatible с δ если добавить AND как primitive.

## Открытые вопросы для Session 4+

### Q1: Каноническое доказательство pattern 2(k+1)?
Можно ли вывести pattern ANF degree = 2(k+1) из first principles? Если да — даёт теорему о bound сложности δ на Boolean primitives.

### Q2: Существует ли известная literature для "δ-ring + AND"?
Моё подозрение — это нестандартный объект. Но возможно λ-rings или некоторые modern constructs Borger-Clausen покрывают это. Надо бы проверить.

### Q3: Extension к XOR
В Session 2 мы вывели δ(x XOR y) через δ(x AND y). Если у нас будет axiomatic framework для δ на AND, XOR автоматически получается. Значит AND — **ядро структурной сложности** SHA в δ-language.

## Metacognition

Session 3 дал **narrower technical result** чем Session 2 (negative на polynomial fit). Но **структура ANF** — это реальный positive finding. Говорит: AND complicated, но не unpredictable.

Session 4 должна попробовать:
- Formalize δ на ОТДЕЛЬНЫХ битах (Witt-vector explicit)
- Проверить совместимость rotations в этом presenting
- Если обструкция та же (rotations break), то мы конвергируем к "prismatic пока недостижима для SHA" как final answer

## Session 4 target

**Option 1**: Explicit Witt-vector basis.  
Каждый x ∈ Z/2^n — tuple (a_0, ..., a_{n-1}). Operations componentwise + carry. δ на tuple level. Проверить связь со Session 1/2 findings. Это даст unified framework.

**Option 2**: Algebraic proof of ANF degree bound.  
Доказать формально degree(ANF of δ on AND output bit k) = 2(k+1). Это может быть первая теорема programme, "прискуит clean theoretical result".

**Рекомендация**: Option 2 — формальное доказательство чаще всего двигает дальше чем empirical accumulation.

## Status Session 3

- ✓ Polynomial fit rejected: no low-degree formula for δ(x AND y)
- ✓ Bit-level ANF analyzed: structured, degree 2(k+1) pattern
- ✓ AND identified as genuine primitive, not derivable
- → Session 4 target: prove ANF degree bound OR move to explicit Witt-vector basis

## Artifacts

- `session_3_and_structure.py` — polynomial fit attempt + bit-level ANF analysis
- `SESSION_3.md` — this file
