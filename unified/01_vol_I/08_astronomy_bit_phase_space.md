# Глава I.8. Астрономия битов, carry phase space, backward shortcut

> TL;DR: Hadamard basis (8 properties verified) — канонический. Carry = сопряжённый импульс (§114). Diagonal conjugacy universal on real SHA (§119-C). W-атлас ΔW∝1/N_ADD (§123). Принцип Макро-Скорости (§124). Scalar/Vector координаты ALL NULL ✗NEG. **ANF early-verify 7.6× cumulative** — первый реальный backward shortcut (§132, validated §133).

## §I.8.1 Астрономия битов — новая дисциплина (§98) ⭐

**Переформулировка**: bit = (observation → measurement → Hilbert space).
- Measurement как central operation.
- Oси = измерительные базисы.
- Bit-cosmos = пространство наблюдаемых.

## §I.8.2 Входы, детерминизм, boost (§99-100)

**Три ключевых вопроса**:
1. **Input encoding**: как задача кодируется в биты?
2. **Determinism vs tractability**: детерминированное решение возможно ли за P?
3. **Speedup mechanisms**: где и как сокращается работа?

**§100**: эти вопросы — каркас Программы далее.

## §I.8.3 Математика определения осей (§101)

**Bijective basis**: правильный способ определить ось = биективное соответствие между T_X и базисом измерительного пространства.

## §I.8.4 Sharp-resolution астрономия + Hadamard (§102, §110) ⭐

**Hadamard basis**: канонический базис для бит-измерений.

**8 свойств verified** [§102, §110]:
1. Orthogonality
2. Completeness
3. Unitary (I/√N factor)
4. Self-duality
5. Walsh-compatibility
6. Fast transform (O(N log N))
7. Reveal parity
8. Additive decomposition

**Hadamard → каноническая основа для всех дальнейших тестов**.

## §I.8.5 Walsh formulas + conservation (§103)

- Walsh Ŵ_S = 2⁻ⁿ Σ_x (-1)^{f(x) ⊕ S·x}
- Parseval: Σ_S Ŵ_S² = 1 (для boolean f).
- Information density через Walsh spectrum.

## §I.8.6 ADD mod 2^L через Walsh (§104)

**Квантитативная нелинейность** ADD:
- Bit-wise ADD представляется как Walsh spectrum с carry-coupling.
- Основа для дальнейшего carry phase space анализа.

## §I.8.7 Triple-products SHA R=2 (§105)

**Non-trivial прогресс**: triple correlations обнаружены на R=2.
- Signal в 3rd-order Walsh coefficients.
- Согласуется с Том III IT-4.Q7C (3rd-order distinguisher).

## §I.8.8 Backward step SHA — wall (§106) ✗NEG

**Фундаментальная стена**: без W-битов обратный раунд SHA не инвертируется.
- Хотя bijective, нет polynomial inverse.

## §I.8.9 Алгебраическая инверсия раунда (§112-113)

**Правильная постановка**: координатные уравнения для раунда и обращения.
- Уравнения существуют в ANF, но degree blow-up.
- **§I.8.19 ANF degree barrier** — следствие.

## §I.8.10 Carry как сопряжённая координата (§114) ⭐⭐

**Ключевой инсайт**: bit = position, **carry = conjugate momentum**.
- Симплектическая структура: (bit, carry) — cotangent bundle.
- Hamiltonian = раунд функция.
- Аналогично quantum operators [X,P] ≠ 0.

## §I.8.11 Уточнение §114 на L=16 (§115)

**Смешанный результат**: два закона выживают, два умирают.
- Выживают: conjugacy relation + Poisson bracket.
- Умирают: strict Hamiltonian preservation + Liouville measure.
- **Honest physical boundary**.

## §I.8.12 Carry как Марковский процесс (§116-117)

**§116** Markov theory: carry → распределение. Граница применимости установлена.

**§117** Spectral basis: **3D Hidden Markov Model, 8 собственных мод**.

## §I.8.13 Spectral на real SHA L=32 (§118) ✗NEG

**Спектральная гипотеза опровергнута**: 8 мод НЕ сохраняются при L=32.
- Real SHA "deflates" spectral structure.
- Честная стена.

## §I.8.14 Diagonal conjugacy универсальна (§119) ⚡VER ⭐⭐

**Прорыв**: Φ-conjugacy diagonal выживает на реальном SHA-256.
- **Open 119-C universal** — справедливо для всех тестированных инстансов.
- Не Φ-inverter работает, но conjugacy relation сохраняется.

## §I.8.15 Φ-inverter fails (§120)

**Честная проверка**: Φ-inverter НЕ работает как шорткат.
- Но Open 119-C держится: diagonal conjugacy — property of function, not instance.

## §I.8.16 Moment geometry carry (§121-122)

**§121**: моменты carry эволюционируют по собственной математике.

**§122**: W-аномалия **неистребима** через моменты.
- Открытия 122-A до 122-F (см. исходный файл детали).
- **Вывод**: W — invariant round function, не данных.

## §I.8.17 W-атлас: ΔW ∝ 1/N_ADD (§123) ⭐

**Универсальный закон**:
- ΔW (movement W-функции) **inversely propor** к N_ADD (число ADD операций в раунде).
- Эмпирическое открытие, формализовано.
- ⇒BRIDGE с Том II §122 (W invariant).

## §I.8.18 Принцип Макро-Скорости (§124) ⭐

**MC-принцип**: на макро-уровне shortcut'ы существуют ТОЛЬКО через медленно меняющиеся координаты.
- Micro-avalanche complete за 1R.
- Shortcut = macro-координата с τ > 1R.

## §I.8.19 Scalar координаты ✗NEG (§125)

**Систематический поиск**: 16 кандидатов макро-координат.
- **ALL NULL**: никто не даёт shortcut.
- **Открытие 125-A**: avalanche complete за ОДИН раунд на scalar level.

## §I.8.20 Vector валидация ✗NEG (§126)

**План**: векторные координаты k=32.
- **ALL NULL** включая k=32.
- **Открытие 126-B**: 32-бит R-linear полностью слеп.
- **Методологический сдвиг**: нужен GF(2) regression.

## §I.8.21 ANF эксперимент подтверждает §114-A (§127) ⭐ ⇒BRIDGE

**Эмпирическое подтверждение теории §114-A**:
- ANF degrees ТОЧНО по теоретической formule §114-A.
- **2/16 ≈ 12.5% битов имеют shortcut** (открытие 127-A).
- Cost shortcut по битам (L=16).

## §I.8.22 ANF composition — окно (§128)

**Degrees saturate за 2 раунда** ⚡VER.
- Cost shortcut по T (composition).
- **Открытие 128-A**: SHORTCUT-окно = ЕДИНСТВЕННЫЙ раунд.
- **Открытие 128-B**: ANF mixing time ≤ 2R.
- ⇒BRIDGE с Том II П-128 (то же saturation за 2R).

## §I.8.23 Backward stepwise inversion (§129)

**Правильный протокол**: инверсия по одному шагу с адаптацией.
- **Открытие 129-A**: tree НЕ explode'ит (контролируемый рост).
- Cost анализ для L=16, T=4.

## §I.8.24 Φ-дисквалификатор — первый backward shortcut (§130) ∆EXP

**Эксперимент L=16, T=4**:
- Φ-prior работает: **measured speedup**.
- Экстраполяция на real SHA L=32.
- **Cumulative speedup** для full inversion оценен.
- **Открытие 130-B**: speedup ceiling с linear regression.

**Validation §133**: §130 был optimistic, реальная картина скромнее.

## §I.8.25 Stacked disqualifiers ✗NEG (§131)

**Гипотеза**: ensemble stat. фильтров.
- **Открытие 131-A**: фильтры ≈ 0 сами по себе.
- **Открытие 131-B**: уточнение recall §130.
- **Открытие 131-C**: stacked margins **≈ 3-5%** (маргинально, не масштабируется).

## §I.8.26 ANF early-verify — настоящий shortcut (§132) ⭐ ⚡VER

**Идея**: верифицировать частичный ANF ДО полной chain completion.

**Эксперимент L=16, T=4**:
- **Combined cost** — реальный speedup.
- **Cumulative backward shortcut**: **7.6×**.
- **Открытие 132-B**: ANF и Φ **независимы** (ortho-shortcut).
- Экстраполяция на real SHA L=32.
- **MC-принцип теперь практический**.

**⇒BRIDGE с Том II**: первый реальный backward shortcut. Связь с П-128 (ANF 2R saturate) и П-132 (early verify mechanism).

## §I.8.27 Validation — честное уточнение (§133) ⚡VER

**Программа валидации**:
- **Check A** (HD distribution): как есть.
- **Check B** (истинная recall vs R): **критическая корректировка §130** — recall ниже чем думали.
- **Check C** (full chain, частично): interrupted.
- **Пересмотр §132 с правильным recall**: **7.6× сохраняется**, но не больше.

**Истинная карта shortcut'ов**:
- ANF early-verify: единственный настоящий ortho-shortcut.
- Φ-prior: marginal.
- Stacked stat filters: marginal.

**Уроки методологии**: строгая validation критична, optimism губителен.

## Cross-refs ⇒BRIDGE

- §114 carry = conjugate ↔ Том II §122 W invariant round function
- §123 W-атлас ΔW∝1/N_ADD ↔ Том II carry-rank=589/592
- §127 ANF подтверждает §114-A ↔ Том II П-127 ⚡VER
- §128 2R saturate ↔ Том II П-128 ⚡VER, Том III IT-4.Q7 high-order only
- §132 ANF 7.6× cumulative ↔ Том II MITM O(2⁸⁰) теория — оба — backward shortcuts
- §119-C diagonal conjugacy ↔ Том II T_CARRY_ANALYTIC
- §125-126 ALL NULL ↔ Том III IT-5G: linear max|z| undersufficient для distributed

## Итог Тома I

**20 осей** + 3 кандидата, **5 метагрупп**, **6 клеток**, аксиомы **D1-D5** (20/20 pass), **Plurality Theorem** (6 sub-frameworks, не 1). Центральные теоремы: **§45 General Discrimination**, **§67 Theorem 7**, **§132 ANF 7.6×**. Главная не-решённая задача: backward shortcut beyond §132.
