# Session 3: OTOC higher-order — analytic discharge

**Дата**: 2026-04-26
**Статус**: ⊘SCOPED для CL-P/CL-C. Closure через bounded T_max(k) и identity OTOC^(k) ≡ classical Walsh chain-k (уже измеренное).
**Цель**: проверить Кандидата 4.5 из SESSION_1 — даёт ли OTOC higher-order (4-point, 6-point) на rounds 24..64 суперлинейную композицию advantage. Без эксперимента, аналитически из данных методички.

**Outcome**: candidate closed после одной сессии. Вторая ⊘SCOPED по тому же протоколу что Session 2 — applying CL-D/P/C split + check для super-linear T-growth.

---

## 1. Recap target и protocol

Из SESSION_2 §6, target Session 3:
> **OTOC higher-order**. Конкретный вопрос: измеряется ли OTOC^(4) с зависимостью от W (input) на rounds 24..64? Если да → handle для control есть → CL-P/CL-C под угрозой. Если нет (как Φ-manifold) → ⊘SCOPED.

Расширенный фильтр (Session 2 §4 refinement):
1. Есть ли input-control handle? (для OTOC — да тривиально, это differential).
2. Есть ли super-linear T-growth advantage? (новый вопрос).

---

## 2. Фундаментальное наблюдение: OTOC^(k) ≡ classical higher-order differential

Методичка явно фиксирует это в §III.8.7 (Null results):
> **OTOC differential = classical XOR-DDT**: not new tool. T_DOM_DIFF (methodology, additive) ≠ OTOC (XOR). Для additive-DDT нужен separate extension, не сделан.

Расширение этого утверждения на higher-order:

**Тождество**: OTOC^(k)[i_1, ..., i_k; j; r] = E_msg[output[j] flips | input bits i_1..i_k all flip] − baseline. Это **k-th order differential** (Knudsen 1994, Lai 1994), известный как higher-order differential cryptanalysis.

Эквивалентно — это связано с k-th order Walsh coefficient через дискретную производную: ∂_{i_1...i_k} f = Σ_{S⊂{i_1..i_k}} (-1)^{k-|S|} f(x ⊕ ⊕_{i∈S} e_i). Это и есть Walsh-S коэффициент для S = {i_1,...,i_k} с точностью до знака.

**Следовательно**: всё что Том III измерял через `chain_k` framework — это **уже** higher-order OTOC в другой записи. Формально это **известно** (§III.1.6, §III.3.6 explicit references к Knudsen/Biham higher-order differential).

---

## 3. Что уже измерено (Том III IT-5S, §III.4.6)

**Round × Walsh-order evolution** [⚡VER, raw chain magnitudes]:

```
r    |chain_1|   |chain_2|   |chain_3|
 4      6.18      890        79 696    baseline (signal на всех порядках)
 8      6.51      619        46 916
12      0.17        3            110   ← phase transition (sign flip)
16      0.43       19            727
20      0.02        1             88   ← stabilises к RO
64      0.00        2             83   ← saturated (RO band: 83.54 ± 3.79)
```

**Прямой прочёт**:
- 1st-order saturates by r ≈ 20.
- 3rd-order saturates by r ≈ 20-24 (chain_3 = 88 vs RO 83.5 at r=20 — z ≈ 1.2σ, RO-band).
- 4th-order [§III.3.7 Q7f]: измерено только в одной round-конфигурации; chain-4 z=−6.40 при R=20 на full hash output — но это не round-by-round saturation curve.

**Empirical fact** [IT-5S §6]: "к r=64 |chain_3|/|chain_1| ≈ 41 500 (vs 12 900 при r=4). chain_1 быстрее затухает чем chain_3 ⇒ информация мигрирует в высокие порядки."

**Уточнение**: миграция в высокие порядки — это **транзиентное** явление в первых 12-20 раундах. К r=20 даже chain_3 saturated. Миграция не продолжается за r=20.

---

## 4. Анализ Composition Lemma для OTOC^(k)

### 4.1 Обозначим T_max(k)

Пусть T_max(k) := round, после которого chain_k (или OTOC^(k)) неотличим от RO.

Из IT-5S и §III.8.4:
- T_max(1) ≈ 20 (max|z| Walsh-1 reaches RO; OTOC 2-point reaches RO)
- T_max(2) ≈ 20 (chain_2 reaches RO)
- T_max(3) ≈ 20-24 (chain_3 reaches RO)
- T_max(4) ≈ 24-30? (interpolation — full data ?OPEN)

### 4.2 Required для break CL: T_max(k) → ∞

Для break CL-P/CL-C через OTOC^(k) нужно:
- T_max(k) > 64 для какого-то k, ИЛИ
- T_max(k) → ∞ as k → ∞

Это дало бы: cost атаки на full SHA с k-th order observable < 2^(c · T_eff) где T_eff < 64.

### 4.3 Почему это не выполняется (теоретический аргумент)

**MSS bound** (§III.8.2, Maldacena-Shenker-Stanford 2016):
λ_L ≤ 2π/β — universal scrambling bound из quantum chaos. Для SHA-256 классический analog работает: existence фиксированного maximum Lyapunov rate для round-функции.

**Spectral gap** (Том II §II.7.2, ★-Algebra constants):
η = 0.18872. Mixing time T_mix ~ 1/η ~ 5 rounds для GKP carry-структуры.

**Следствие**: ВСЕ observables thermalize за O(T_mix) раундов, regardless of order k. Higher-order observables могут scramble чуть медленнее (k-point correlations physically thermalize позже 2-point), но **bounded** на конечной системе. Для SHA 2^256 state space — конечно, mixing time bounded.

**Эмпирически подтверждено**: Cross-architecture full-output OTOC (§III.8.6):
| Hash | Measured ||C||² | Theoretical RO |
|---|---|---|
| MD5 | 81.32 | 81.92 (0.7% off) |
| SHA-256 | 163.48 | 163.84 (0.2% off) |
| BLAKE2b | 163.89 | 163.84 (0.03% off) |

Все 8 семейств — RO-like at full output. **Даже сломанная MD5 indistinguishable от RO под OTOC at full output.** OTOC measures scrambling rate, не cryptographic hardness — методичка явно это говорит (§III.8.6, §III.8.11).

### 4.4 Quantitative bound

Если T_max(k) ≤ T_max,∞ для всех k (bounded), то для SHA-256 с T = 64 ≫ T_max,∞ ≈ 24:
- Для всех k, advantage observable стирается за первые ~24 раунда.
- Оставшиеся 40 раундов — RO-like для всех порядков.
- Composition советует cost ≥ 2^(c · 64) для full attack — линейно в T.

**Нет super-linear regime**.

### 4.5 Применение типовой шкалы CL-D/CL-P/CL-C

| Тип | Status OTOC^(k) | Reason |
|---|---|---|
| CL-D | break (trivial) | OTOC fingerprint существует на reduced T (r ≤ 24); не цель программы |
| CL-P | not broken | T_eff < 64 при bounded T_max(k); cost ≥ 2^(c · 64) |
| CL-C | not broken | то же |

### 4.6 Closing reason

**OTOC higher-order ⊘SCOPED для CL-P/CL-C**. 

Mechanism: T_max(k) bounded for all k by mixing time of round function (≈ 24 rounds). SHA-256 design margin (40 post-saturation rounds) ≫ T_max,∞. Higher-order observables не дают super-linear advantage.

Это consistent с:
- Том III IT-5S round×order map (chain_3 saturates by r=20).
- §III.8.6 cross-architecture full-output verification (все RO-like).
- Theoretical MSS-bound + finite spectral gap.

---

## 5. Что это даёт каталогу кандидатов

После Sessions 2-3 закрыты два высокоранжированных кандидата (4.2 Φ-manifold и 4.5 OTOC higher-order). Обновлённый каталог:

| Кандидат | CL-D | CL-P | CL-C | Status |
|---|---|---|---|---|
| 4.1 Path-bit / Hopf | unknown | open | open | **→ Session 4 target** |
| ~~4.2 Φ-manifold~~ | break | blocked (MI≈0) | blocked | ⊘SCOPED [Session 2] |
| ~~4.5 OTOC higher-order~~ | break | bounded T_max(k) | bounded | ⊘SCOPED [Session 3] |
| 4.3 Witt / prismatic | unknown | open | open | open (long horizon, отдельная линия research/prismatic/) |
| 4.4 Resonance / cycle | unknown | unlikely | unlikely | postpone (Sessions 41, 62 уже закрыли variant'ы) |

Session 4 target: **Path-bit / Hopf algebra**. Это самый радикально-алгебраический кандидат — non-abelian структура, отличная от Markov/spectral-gap картины.

---

## 6. Plan Session 4 (Path-bit)

**Target**: Кандидат 4.1 — Path-bit / Hopf algebra (Том I §80-84).

**Почему Path-bit может escape MSS / spectral-gap аргументы**:

MSS bound и spectral-gap аргументы работают для **scalar observables** на state space. Path-bit operates на **path space** (Chen iterated integrals) — фундаментально different geometry. Free Lie algebra на образующих не имеет finite spectral gap в том же смысле — это infinite-dim. structure.

В принципе, observable signatures путей могут расти с длиной пути (T) полиномиально или экспоненциально, без classical mixing constraint.

**Конкретный вопрос Session 4**: можно ли определить "advantage" attack'а на SHA в Hopf-algebra signature space так что log(Cost) ≤ T^α для α < 1?

**Подвопросы для analytic Session 4** (без эксперимента):

(a) Что такое "round function R" в Hopf algebra terms? R as element of free Lie algebra или как automorphism of Hopf algebra?
(b) Composition of T rounds = product in Hopf algebra. Что говорит BCH formula о log(R^T)?
(c) Есть ли input-control handle? (Path-bit input — это путь, derived from message; control structure?)
(d) Есть ли saturation в signature growth? Если нет — потенциал для super-linear.

**Не делать**:
- Не пытаться сразу строить attack. Сначала разобрать математическую структуру.
- Не запускать experiments. Analytic session.

**Файл результата**: `research/composition_lemma/SESSION_4.md`.

---

## 7. Обновления upstream

**SESSION_1.md**:
- §4.5 OTOC higher-order — отметить ⊘SCOPED [Session 3], reason — bounded T_max(k).

**README.md**:
- Обновить таблицу кандидатов: 4.5 OTOC higher-order ⊘SCOPED.
- Session 4 target: Path-bit.

**UNIFIED_METHODOLOGY.md**:
- Не трогаем (по договорённости — обновлять только при появлении нового результата, не closure'ов).

---

## 8. Cross-references

- SESSION_1.md §4.5 (исходное описание OTOC higher-order кандидата) — superseded.
- SESSION_2.md §4 (CL-D/CL-P/CL-C split) — применено здесь.
- UNIFIED_METHODOLOGY.md §III.4.6 IT-5S (round×Walsh-order data verbatim).
- UNIFIED_METHODOLOGY.md §III.8 OTOC framework (2-point measurements).
- UNIFIED_METHODOLOGY.md §III.8.7 (OTOC ≡ XOR-DDT identity).
- UNIFIED_METHODOLOGY.md §II.7.2 (★-Algebra spectral gap η = 0.189).

## 9. Decision points для review

- §4.4 quantitative bound предполагает T_max,∞ ≤ ~24. Это extrapolation из chain_1, chain_2, chain_3 saturation patterns. **Если** будущий experiment покажет T_max(k) растёт с k неограниченно (e.g., chain_5, chain_6 surviving past r=30) — closure нуждается в re-audit.
- §2 OTOC^(k) ≡ Walsh chain-k identity — proven через definition. Не subject to experimental falsification.
- Path-bit (Session 4) использует другую геометрию — этот аргумент НЕ применим, нужен новый.
