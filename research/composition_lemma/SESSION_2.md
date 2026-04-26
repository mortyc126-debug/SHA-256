# Session 2: Φ-manifold candidate — analytic discharge

**Дата**: 2026-04-26
**Статус**: ⊘SCOPED для pre-image/collision; trivial break для distinguishing (уже известно).
**Цель**: проверить Кандидата 4.2 из SESSION_1 — даёт ли 6D Φ-manifold (Том II §II.9.1, П-362) суперлинейную композицию advantage. Без эксперимента, аналитически из данных методички.

**Outcome**: candidate closed после одной сессии — clean closure, не "не нашли", а конкретный механизм блокировки + важное уточнение формулировки самой Composition Lemma.

---

## 1. Recap target

Из SESSION_1 §4.2:
> Φ-manifold 6D — 6 свободных раундов {1, 4, 9, 10, 19, 21} как координаты [П-362, T_PHI_MANIFOLD_6D ⚡VER]. Если advantage attack'а аддитивна по этим 6 свободным раундам, то total advantage ~ 6 · ε вместо ε^64. Это и есть super-linear composition по структурно-привилегированному подмножеству.

Plausibility оценил как высокую — "самый прямой существующий handle".

---

## 2. Полные данные методички (Раздел 107, П-359..П-378)

Извлечено из `methodology_v20 (5) (1).md` стр. 9988-10097.

### 2.1 Структура Φ-multifold

```
SHA-256 carry-пространство (64 раунда):
  ├── ФИКСИРОВАННЫЕ (20 раундов): {2,3,8,16,17,25..29,40..46,61..63}
  │   └── carry ≡ const, P > 0.999
  │
  └── Φ-СВОБОДНЫЕ (6 раундов): {1, 4, 9, 10, 19, 21}
        └── 0.05 < P(carry=1) < 0.95
```

PCA эффективная размерность: 18.9. Φ-многообразие — 6D подпространство.

### 2.2 Энтропия и аттрактор

- **H(Φ) = 2.772 бит из 6.0** (46.2% от uniform). Сильно подсжатое распределение.
- **P(Φ = 111111) = 53.8%** — единственный сильный аттрактор (34.4× от uniform).
- **Запрещённые состояния** (P ≈ 0): {000000, 100000, 001000, 000100, 000010, 000110} — все с ≥4 нулями.
- **Аномалия**: P(110011) = 1.913× от ожидаемого. (Q63: механизм неизвестен.)

### 2.3 Зависимости между координатами

Линейные корреляции (15 пар):
- carry[9] ↔ carry[10]: r = +0.123 (T_CARRY_PAIRS, каскад)
- carry[1] ↔ carry[4]: r = −0.080 (механизм неизвестен, Q63)
- остальные 13 пар: |r| < 0.05.

Нелинейные:
- **Все 15 XOR-пар смещены**: P(carry[i] ⊕ carry[j] = 1) ≈ 0.13–0.21 (vs 0.5 для независимых).
- χ²-тест независимости: χ² = 2358, p = 0.000 → координаты **НЕ независимы**.

### 2.4 Связь с входом (КЛЮЧЕВОЕ для нашей задачи)

**T_PHI_INPUT_DECOUPLED [П-367]** ⚡VER:
```
MI(W[0]; Φ) = 0.00003 бит
```
Φ **декуплировано от входа**. Барьер r=0→r=1 происходит **до** формирования Φ-структуры. Φ — внутреннее свойство round-функции, не функция конкретного W.

Этот результат уточняет правило 107.19 методички:
> "Φ-пространство декуплировано от входа (MI≈0). Барьер r=0→r=1 происходит ДО формирования Φ. Φ — внутренняя структура алгоритма, не функция входа."

### 2.5 Криптографическая интерпретация (П-378)

| Hash | Φ-размерность | Стойкость |
|---|---|---|
| SHA-1 | 0 | сломан (carry collapse) |
| MD5 | 31 | сломан (carry chaos) |
| **SHA-256** | **6** | не сломан (balance) |

T_PHI_CRYPTOGRAPHIC_BALANCE: Φ-размерность — мера "баланса" carry-структуры. SHA-256 находится в режиме баланса.

---

## 3. Анализ для Composition Lemma

### 3.1 Что мы хотели проверить (из SESSION_1)

> Если advantage(Φ-coords) factorizes по координатам, проверить cumulative growth — линейно в 6 (= O(1) в T) или линейно в T?

### 3.2 Главное наблюдение

Composition Lemma в SESSION_1 §2.2 сформулирована **без указания типа атаки**. Применение Φ-manifold вскрывает что **тип атаки критичен**.

**Разделение типов advantage**:

(A) **Distinguishing advantage** — отличить SHA от RO.
Φ-manifold даёт это **по конструкции**: Φ-распределение SHA имеет H = 2.772 бит и аттрактор 111111 (53.8%), что отличается от uniform RO. Distinguishing Adv по Φ-координатам **не decay'ит с T** — Φ это intrinsic свойство.

Это формально нарушает CL для distinguishing: Cost_dist(T) = O(1), не Ω(T).

(B) **Pre-image advantage** — дано y, найти x с H(x) = y.
Чтобы использовать Φ-manifold, нужно из y определить (или ограничить) пригодные x. Связка `x → Φ(x) → y` требует MI(x; Φ) > 0 чтобы Φ помогало навигации.
**MI(W; Φ) ≈ 0.00003 = 0** → Φ не даёт информации о x. Φ-координаты эволюционируют **независимо от выбора W** — нет handle для управления.

(C) **Collision advantage** — найти x ≠ x' с H(x) = H(x').
Аналогично pre-image: collision-attack требует возможности **одновременно** контролировать H(x) и H(x'). Φ отвязано от W, поэтому два разных W приводят к одной и той же Φ-аттрактор-доминированной структуре, но это не помогает синхронизировать сами outputs.

### 3.3 Применение Composition Lemma по типам

**CL_dist**: log_2 Cost_dist(T) ≥ c · T?
- **Тривиально нарушена**. Любая non-RO структура даёт Cost = O(1). Для SHA-256 уже известно: Distinguisher v6.0 AUC=0.980 (П-1000), χ²-fingerprint z≈-2.5 (IT-1.3), OTOC scrambling fingerprint (§III.8). Φ-manifold — ещё один член этого класса.
- **Status**: **НЕ интересно для нашей программы**. Distinguishing — не "взлом SHA-256".

**CL_pre**: log_2 Cost_pre(T) ≥ c · T?
- Для использования Φ-manifold нужен MI(x; Φ) > 0. Эмпирически MI ≈ 0.
- Φ **не помогает** pre-image. Composition Lemma остаётся в силе для pre-image.

**CL_coll**: log_2 Cost_coll(T) ≥ c · T?
- Тот же блок: коллизию ищут парами входов. Φ интринзично, не контролируется парой.
- Composition Lemma остаётся в силе для collision.

### 3.4 Closing reason

**Φ-manifold ⊘SCOPED** для основной программы (CL_pre/CL_coll). Не "factorizes ли advantage" — вопрос даже не возникает, потому что **handle на Φ-координаты из входа отсутствует**.

Это clean closure: конкретный механизм (MI ≈ 0), измеренный (П-367), консистентный с правилом 107.19 методички.

---

## 4. Refinement Composition Lemma (обновление SESSION_1 §2.2)

Session 1 формулировал CL без разделения типов атаки. Это пробел; Φ-manifold его вскрыл.

**Уточнённая формулировка**:

Composition Lemma — это **три отдельных конъюнктуры**:

(CL-D) Distinguishing: для любого классического distinguisher M, log_2(Cost_M(T)) ≥ c · T.
(CL-P) Pre-image: для любой pre-image атаки M, log_2(Cost_M(T)) ≥ c · T.
(CL-C) Collision: для любой collision атаки M, log_2(Cost_M(T)) ≥ c · T.

**Эмпирически**:
- **CL-D ложна** для SHA-256 (тривиально, любой fingerprint даёт Cost = O(1)).
- **CL-P и CL-C** — это **настоящая** Composition Lemma. 69 sessions Prismatic Program давали свидетельства в их пользу. Они и есть target нашей программы.

### Импликация для каталога кандидатов

Каждый кандидат из SESSION_1 §4 должен быть переоценён по тому, нарушает ли он CL-P/CL-C, не CL-D:

| Кандидат | CL-D | CL-P | CL-C | Status |
|---|---|---|---|---|
| 4.1 Path-bit / Hopf | likely break | unknown | unknown | open |
| 4.2 Φ-manifold | break (trivial) | blocked (MI≈0) | blocked (MI≈0) | **⊘SCOPED по pre/coll** |
| 4.3 Witt / prismatic | unknown | open | open | open (long horizon) |
| 4.4 Resonance / cycle | unknown | unknown | unknown | unlikely (Sessions 41,62) |
| 4.5 OTOC higher-order | likely break | unknown | unknown | open |

Φ-manifold снимается с приоритета 1.

### Принцип уточнения

**Любой "break" Composition Lemma должен быть для CL-P или CL-C, не CL-D**. Distinguishing-эффекты не считаются "взломом" SHA-256, методология их и так знает в избытке.

---

## 5. Что это даёт программе

1. **Точность определения цели**: ищем break не "Composition Lemma вообще", а конкретно CL-P или CL-C. Это сужает пространство поиска и устраняет ложные срабатывания на distinguishing-фронте.

2. **Новый критерий для кандидатов**: проверяемый в одну сессию вопрос — есть ли у кандидата handle для **управления** intermediate структурой из входа? Если MI(input; structure) ≈ 0 — кандидат ⊘SCOPED для pre/coll.

3. **Φ-manifold переходит из "перспективного" в "понятого"**: мы знаем точно, почему Φ не даёт атаки на SHA-256. Это не negative result, это **structural understanding**.

---

## 6. Plan Session 3

### Target: Кандидат 4.5 — OTOC higher-order

Почему OTOC, а не Path-bit (4.1)?

**OTOC уже измерен** на 2-point (§III.8): SHA-2 sequential cascade, 40-round design margin. Higher-order (4-point, 6-point) — естественное продолжение, не новый toolchain.

**Конкретный вопрос Session 3**: измеряется ли OTOC^(4) с **зависимостью от W (input)** на rounds 24..64? Если да → handle для control есть → CL-P/CL-C под угрозой. Если нет (как Φ-manifold) → ⊘SCOPED.

Это та же проверка что сделана для Φ — теперь применённая систематически.

### Что НЕ делать

- Не запускать OTOC^(4) measurement сразу. Сначала **аналитика**: каков ожидаемый OTOC^(4) под RO baseline? Какой signal-to-noise? Сколько samples нужно?
- Не повторять Sessions 56-69 closure'ы. Cross-ref с research/prismatic/SESSION_*.md обязателен.

### Альтернатива — Path-bit (4.1)

Если OTOC^(4) тоже окажется blocked-by-MI, переходим к Path-bit. Path-bit имеет более радикальную алгебраическую структуру (non-abelian Hopf), может обходить MI-блок через **non-input-derived** invariants.

---

## 7. Cross-references

- SESSION_1.md §4.2 (исходное описание кандидата) — превзойдено этой сессией.
- UNIFIED_METHODOLOGY.md §II.9.1 (T_PHI_MANIFOLD_6D verbatim).
- UNIFIED_METHODOLOGY.md §II.11.12 (Φ-manifold 6D coordinates additional context).
- methodology_v20 (5) (1).md Раздел 107 (полная П-серия 359-378).
- methodology_v20 (5) (1).md Раздел 110-111 (T_C62_BRIDGE — связанный, но отдельный механизм; не Φ-manifold).
- research/prismatic/SESSION_*.md (предыдущие analytical sessions).

---

## 8. Status и changes upstream

**Session 2 outcome**: Φ-manifold ⊘SCOPED для pre-image/collision (главная программа); тривиально break'ит distinguishing CL (не интересно).

**Update in SESSION_1.md**:
- §2.2 нужна сноска: CL разделяется на CL-D / CL-P / CL-C, см. SESSION_2 §4.
- §4.2 Φ-manifold — отметить ⊘SCOPED.
- §4 catalog — добавить таблицу из §4 этой сессии.

Обновлю минимально (inline notes, не переписывание), чтобы сохранить SESSION_1 как исторический документ.

**Decision points для review при первом эксперименте (Session 4+)**:
- Действительно ли CL-D тривиально нарушена? Возможно есть тонкий контекст где она интересна. Пока статус "trivial break, не интересно".
- Применимо ли MI-критерий к каждому кандидату одинаково? Нужно проверить на Path-bit и OTOC.
