# Session 4: Path-bit / Hopf algebra — analytic discharge

**Дата**: 2026-04-26
**Статус**: ⊘SCOPED для CL-P/CL-C. Closure через empirical fact §94.5 ✗NEG: path-bit conservation refuted at R=2.
**Цель**: проверить Кандидата 4.1 из SESSION_1 — даёт ли Path-bit / Hopf algebra (Том I §80-84) суперлинейную композицию advantage. Без эксперимента.

**Outcome**: candidate closed через **fastest-saturation** в каталоге. Path-bit observables thermalize за 2 раунда vs OTOC за 24 — наихудший, не наилучший кандидат. Closure logic пересекается с avalanche wall (Том I §111), что и предсказывала методичка.

---

## 1. Recap target

Из SESSION_1 §4.1, Path-bit как кандидат с потенциалом escape spectral-gap аргументов:
> Non-abelian composition path-bits **формально** даёт супер-multiplicative growth signature space (BCH formula expands non-trivially). Если SHA round ↔ некоторый element Hopf algebra с non-trivial higher coefficients — composition T раз даст complexity роста ~ T^k для некоторого k.

Из SESSION_3 §6, motivation:
> MSS bound и spectral-gap аргументы работают для **scalar observables** на state space. Path-bit operates на **path space** (Chen iterated integrals) — фундаментально different geometry. Free Lie algebra на образующих не имеет finite spectral gap в том же смысле — это infinite-dim. structure.

Гипотеза: path-bit signatures могут расти полиномиально/экспоненциально в T без classical mixing constraint.

---

## 2. Path-bit framework (Том I §80-84)

### 2.1 Определение

**Path-bit** — bit как итерированный интеграл Chen [§I.7.1, §80]:
- Формально: path-bit ∈ tensor algebra T(V) траекторий.
- **Foundational level** в poset осей бита (ниже phase-bit, §I.7.4 §84).
- Сигнатура пути S(γ) ∈ T(V) — Chen 1958 iterated integral.

**Hopf algebra structure** [§I.7.2 §82]:
- Shuffle product (concatenation путей).
- Coproduct (branching).
- Antipode (reversibility).

**Free Lie algebra = phase Hamiltonian** [§I.7.3 §83 ⭐]:
- Free Lie на образующих ↔ Hamiltonian phase space.
- BCH formula: log(R^T) = T·X_R + (T^2/2)·[X_R, X_R'] + ...

**Subsumption** [§I.7.4]: phase-bit ≺ path-bit в poset (path-bit строго сильнее на non-abelian signatures).

### 2.2 Гипотетический attack pathway

(a) Trajectory γ_W = (state_0, state_1, ..., state_T) для входа W.
(b) Signature S(γ_W) ∈ T(V) — coordinate в Banach space (§84).
(c) Использовать структуру S как distinguishing/inversion handle.
(d) Если S(γ_W) растёт полиномиально в T (Hall basis dim ~ T^a) и SHA's specific R оставляет non-trivial signature deviation — потенциально полиномиальная атака.

---

## 3. Decisive empirical fact: §94.5 ✗NEG

**§I.7.12 (Том I §94)** — exact section addressing path-bit conservation на SHA:

> §94.5 ✗NEG: гипотеза [bits трансформируются, не стираются] в общем случае **ОПРОВЕРГНУТА через 2 rounds SHA**. Попарное распределение bit-trajectories сильно рассыпается.
>
> §94.7: сохраняется ТОЛЬКО на single operations (R=1) и через triple-products — последняя линия защиты.
>
> §94.8 HONEST answer: conservation НЕ универсален; Bit-cosmos conservation law (§91) — локальное свойство, не глобальное.

**⇒BRIDGE с avalanche wall** (§I.7.12 cross-ref):
> ⇒BRIDGE с Том II: это ОБЪЯСНЯЕТ avalanche wall (§I.8 §111) — информация о входе распыляется за 2R.

**Перевод на язык SESSION_2 фильтра**:

T_max(path-bit) = **2 раунда**. После r=2 path-bit observables (signature, conservation invariants) рассыпаются — bit-trajectory pair distributions неотличимы от random.

Сравнение с другими кандидатами:

| Кандидат | T_max (saturation) |
|---|---|
| Path-bit (signature conservation) | **2** |
| Walsh chain_3 / OTOC^(3) | 20 |
| OTOC 2-point (scrambling) | 24 |
| ANF degree | 2 (saturate) — но это про algebraic degree, не signal |

Path-bit — **самый быстро-затухающий** observable в каталоге.

---

## 4. Анализ Composition Lemma для Path-bit

### 4.1 Теоретическая гипотеза vs эмпирика

**Теоретически**: path-bit signature живёт в infinite-dim Hopf algebra. Spectral-gap аргументы не применимы напрямую — нет "matrix dimension" для bound mixing time.

**Эмпирически**: signature SHA-trajectory thermalizes за 2 раунда (§94.5). Infinite-dim ambient space НЕ помогает — конкретный observable (pair-distribution conservation) рассыпается.

**Согласование**: signature ambient space infinite-dim, но information content конечен (state space 2^256). Конечность state space ограничивает any observable, включая path-bit signatures.

### 4.2 Почему signature в SHA саd быстрее всего?

Mechanism (из §I.7.12, §I.8.16b avalanche wall):
- Path-bit чувствителен к local trajectory details (Chen integral буквально интегрирует along path).
- SHA per-round avalanche **explicitly destroys** local trajectory structure (T_DA_FULL_AVALANCHE [П-106]: HW(δa[17])=16 при ЛЮБОМ флипе Wn[r]).
- 2 раунда SHA достаточно чтобы trajectory structure стала псевдослучайной → signature (function of trajectory) — псевдослучайной.

Обратно к §94.7: conservation сохраняется на R=1 (без avalanche) и через triple-products (специфические algebraic identities). Эти invariants НЕ композируются на T раундов — они attached к single round.

### 4.3 Применение CL-D/CL-P/CL-C split

**CL-D**: SHA-trajectory signature ≠ random signature на R ≤ 1 → break CL-D. Тривиально, как и для всех других кандидатов.

**CL-P/CL-C**: для атаки на full SHA (T=64) нужен path-bit observable surviving до r=64. Эмпирически saturate at r=2. **Не работает**.

Cost атаки через path-bit signature: Cost ≥ 2^(c · 64) — Composition Lemma в силе. Path-bit не даёт даже мaргинального reduction в expected cost.

### 4.4 Hopf algebra composition argument

SESSION_1 §4.1 предполагал что BCH formula log(R^T) = ... может дать polynomial-in-T complexity. Это **формально верно** для signature dimension (Hall basis grows polynomially in T) — но это **dimension ambient space**, не signal-to-noise ratio.

Конкретнее:
- Hall basis в degree ≤ k dimension = O(2^k / k) — экспоненциально в k, но for fixed k и varying T — фиксировано.
- Чтобы получить super-linear cost reduction, нужна **shaped signature deviation** — конкретная structure SHA в Hall coefficients.

§94.5 ✗NEG говорит: shaped structure исчезает за 2 раунда. Так что signal в Hall coefficients есть только при T ≤ 2.

### 4.5 Closing reason

**Path-bit ⊘SCOPED для CL-P/CL-C.**

Mechanism: T_max(path-bit) = 2 (§94.5 ✗NEG). Avalanche destroys local trajectory structure → signature thermalizes в первые 2 раунда. SHA 64 ≫ 2.

Это **более жёсткое** закрытие чем для OTOC (T_max = 24): path-bit saturation в 12× быстрее. Hopf algebra ambient infinity не помогает — finite information content конечного state space ограничивает signal.

---

## 5. Метa-наблюдение: каталог почти исчерпан

После Sessions 2-4 обновлённый статус:

| Кандидат | Status | Closure Session |
|---|---|---|
| ~~4.1 Path-bit / Hopf~~ | ⊘SCOPED (T_max=2) | Session 4 |
| ~~4.2 Φ-manifold 6D~~ | ⊘SCOPED (MI≈0) | Session 2 |
| 4.3 Witt / prismatic | open | parallel line research/prismatic/ (5-10 сессий) |
| 4.4 Resonance / cycle | postpone | Sessions 41, 62 уже закрыли variants |
| ~~4.5 OTOC higher-order~~ | ⊘SCOPED (T_max(k) bounded ~24) | Session 3 |

**3 из 5 closed structurally** за 3 analytic сессии. 1 (4.4) closed prior methodology. 1 (4.3) — long-horizon parallel line.

### 5.1 Triangulation: совпадение с Prismatic Program

Prismatic Program (Sessions 1-69) пришла к выводу "SHA unbreakable классически" через empirical exhaustion 9 attack frameworks. Наша Composition-Lemma программа за 4 analytic session приходит к **тому же результату через структурный фильтр**:

**Структурный критерий**: для каждого кандидата проверить
1. Есть ли input-control handle? (MI(input;structure) > 0?)
2. Есть ли super-linear T_max? (T_max(observable) → ∞ as observable order → ∞?)

Если оба ответа "нет" — ⊘SCOPED. 

Триангуляция:
- 69-session empirical exhaustion → SHA unbreakable.
- 4-session structural filter → SHA unbreakable.
- Convergence — strong signal что conclusion robust.

### 5.2 Что осталось (4.3 Witt/prismatic)

Только Witt/prismatic выходит за рамки structural filter — он адресует **fundamentally different obstruction** (mixed-characteristic geometry F_2 ⊕ Z_2). Это уже отдельная исследовательская линия `research/prismatic/`, начатая Session 1 там же.

**Не новый Composition-Lemma кандидат, а separate research direction.**

---

## 6. Plan Session 5 — META-сессия

Не закрытие конкретного кандидата, а **review and decision**:

### Target Session 5: catalog completeness audit

**Вопросы**:
(a) Каталог 5 кандидатов полон? Есть ли пропущенные направления (tensor networks, exterior algebra, semidefinite programming, ML-guided cryptanalysis)?
(b) Структурный фильтр (MI handle + T_max(k) bound) применим к каждому потенциальному новому кандидату — если новых нет, программа эффективно завершена.
(c) Witt/prismatic transition: формально перевести Composition-Lemma program в `research/prismatic/` или поддерживать обе линии параллельно?

### Не делать в Session 5

- Не закрывать Witt/prismatic — это long-horizon parallel line, отдельная задача.
- Не объявлять программу полностью завершённой до catalog audit.

---

## 7. Cross-references

- SESSION_1.md §4.1 (path-bit candidate description) — superseded.
- SESSION_2.md §4 (CL-D/CL-P/CL-C split) — applied here.
- SESSION_3.md §4.6 (T_max bounded for OTOC) — analogous argument structure.
- UNIFIED_METHODOLOGY.md §I.7.12 (§94.5 ✗NEG) — decisive closure citation.
- UNIFIED_METHODOLOGY.md §I.8.16b (avalanche wall §111) — bridge to mechanism.
- UNIFIED_METHODOLOGY.md §I.7.1-§I.7.4 (path-bit framework definition).
- UNIFIED_METHODOLOGY.md §II.6.3 T_DA_FULL_AVALANCHE (per-round avalanche).
- research/prismatic/SESSION_1.md (Witt/prismatic parallel line, Session 4.3 in catalog).

## 8. Status и changes upstream

**Session 4 outcome**:
- 4.1 Path-bit ⊘SCOPED для CL-P/CL-C через T_max(path-bit) = 2.
- 3 из 5 кандидатов закрыты structurally; программа sub-stantially close to plateau.

**SESSION_1.md update**: §4.1 — отметить ⊘SCOPED [Session 4].
**README.md update**: таблица кандидатов; Session 5 = META-audit.

**Decision points для review**:
- §3 closure relies on §94.5 ✗NEG. Если будущая re-examination этого результата покажет conservation **сохраняется** дольше при специфических conditions — closure нужно audit'ить.
- §4.4 Hopf algebra argument — formalsignificantly under-developed. Если кто-то сделает rigorous Hopf-formalization SHA → возможны новые observations. Но эмпирика §94.5 robust.
- §5.1 triangulation — convergence two independent paths, не proof. Witt/prismatic может ещё сюрпризнуть.
