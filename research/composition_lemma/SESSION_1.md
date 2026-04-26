# Session 1: Composition Lemma — формализация

**Дата**: 2026-04-26
**Статус**: ?OPEN — formalization stage, без экспериментов
**Цель**: превратить informal Composition Lemma из UNIFIED_METHODOLOGY (§ "PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ", стр. ~2829) в точное утверждение, относительно которого можно искать нарушение. Без формального statement'а "поиск суперлинейной композиции" достаточно расплывчат, чтобы любой sampling artefact мог пройти за "break" (ср. IT-6 Ω_k ⊘ROLL).

Программа Prismatic-Program-2 (this lineage) рассчитана на длинный горизонт; result-oriented, не speed-oriented. Продолжение работы по одной сессии.

---

## 1. Что есть сейчас (informal)

**Источник**: UNIFIED_METHODOLOGY.md, секция "PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ", подсекция "COMPOSITION LEMMA":

> Per-round advantage любого классического метода атаки — линейна или сублинейна (per-round bias ≤ 1/4 для Walsh, AI = 1-2 per round, weak channels +1-3 раунда advantage). Per-round разрушение информации — экспоненциально (ANF degree 2^T, trail prob c^T при c < 1 после saturation T ≈ 11).
>
> Поэтому attack cost растёт как 2^(T · log₂(1/p)) где p = per-round trail probability. Подставляя Theorem 34.1 (Walsh worst-case bias = 1/4 → p ≈ 0.25):
>
> AttackCost(T = 64) ≥ 2^(2·64) = 2^128 = exact birthday для коллизий.

**Эмпирическая база**: 9 ортогональных attack frameworks (z3, Boomerang, Rebound, LLL/XL, multi-block random, mod-q invariants, weak states, TDA, joint compression) — все конвергируют на ≤46 раундов с целевым cost ≥ 2^128.

**Проблема**: это meta-claim, не теорема. Нет:
- единой шкалы advantage для разных attack types;
- формального условия "linear/sublinear composition";
- proof'а — только convergence of negative results.

---

## 2. Формальное утверждение (target)

### 2.1 Setup

Пусть H_T = R_T ∘ R_{T-1} ∘ ... ∘ R_1 — T-раундовая итерация compression function (state-update R_i: {0,1}^n → {0,1}^n плюс message-mixing).

Для SHA-256: n = 256 (state) + 512 (message), T = 64.

**Attack-метод** M — алгоритм, который по oracle-доступу к H_T (queries или прямой вычислитель) решает одну из задач:
- **Distinguishing**: H_T vs random oracle.
- **Pre-image**: дано y, найти x с H_T(x) = y.
- **Collision**: найти x ≠ x' с H_T(x) = H_T(x').

**Advantage** Adv_M(T) ∈ [0, 1] определяется относительно random-oracle baseline:
- Distinguishing: Adv = 2·|Pr[M=1 | H_T] − Pr[M=1 | RO]| (TV distance).
- Pre-image: Adv = Pr[M finds pre-image] − 2^{−n} (excess over guessing).
- Collision: Adv = Pr[M finds collision in q queries] / (q²/2^{n+1}) − 1 (ratio over birthday).

**Cost** of M — число elementary operations (gates, queries) needed для достижения Adv ≥ 1/2.

### 2.2 Composition Lemma — формулировка

> **Update Session 2** (2026-04-26): эта формулировка нуждается в split'е по типу атаки (distinguishing/pre-image/collision). Φ-manifold вскрыл что CL-D тривиально нарушена для SHA-256 (любой fingerprint), поэтому "настоящая" CL — только CL-P и CL-C. См. [SESSION_2.md §4](SESSION_2.md).

**Conjecture (Composition Lemma)**:
Для любого классического attack-метода M, нацеленного на T-раундовую SHA-2-подобную ARX hash, существует константа c_M > 0 (зависящая от M, но не от T) такая что:

```
log_2(Cost_M(T)) ≥ c_M · T − O(1)
```

То есть **log(cost) растёт не медленнее линейного по T**.

Эквивалентная форма (advantage): Adv_M(T) = 2^{−Ω(T)} (advantage экспоненциально мал в T).

### 2.3 Что НЕ утверждает Composition Lemma

- Не утверждает что c_M одинакова для всех M. (Walsh c ≈ 2; differential c варьируется.)
- Не утверждает что advantage strictly монотонно убывает в T. (Может быть spike на конкретных T due to резонанса с rotation constants — но cumulative тенденция линейная.)
- Не утверждает что нет квантового speedup (Grover это отдельно; Composition Lemma — про классику).
- Не утверждает что нет side-channel атак (out of scope — атакуют реализацию, не функцию).

### 2.4 Какие операции "разрешены" в M

Это критически важно для precision'а:
- **Классические gates**: AND, OR, NOT, XOR, ADD, ROTR, SHR — на полиномиально-длинных строках.
- **Probabilistic**: random-coin tosses (sampling).
- **Adaptive queries** к oracle.
- **Polynomial-space**: poly(n, T) memory.

**НЕ разрешены**:
- Quantum gates (Grover, QFT, etc.) — отдельный класс.
- Exponential-space algorithms (хотя они и не помогают — birthday уже там).
- Non-uniform advice строк (это другое утверждение, weaker).

---

## 3. Что значит "break" Composition Lemma

**Operational definition**:
Найти метод M такой что для последовательности T_1 < T_2 < ... → ∞:
```
log_2(Cost_M(T_k)) = o(T_k)   (sub-linear)
```

Или, более слабо, найти M и α < 1 такие что:
```
log_2(Cost_M(T)) ≤ T^α + O(1)
```

**Самое сильное опровержение**: Cost_M(T) = poly(T) — полиномиальная атака.

**Промежуточные выигрыши** (которые тоже бы обновили программу):
- (a) **Suboptimal но still exponential**: log Cost ~ √T или T/log T. Не ломает SHA сразу (T=64 даёт ~2^8 если √, что мало), но breaks the lemma качественно.
- (b) **Constant-cost для ограниченного класса входов**: Cost = poly для inputs с особой структурой (weak keys / messages). Это уже было найдено для reduced-round (Wang-chain r=17), но не для full T=64.
- (c) **Phase transition в T**: cost flat до T_crit, exponential после. Если T_crit > 64, это break для SHA-256 specifically.

### 3.1 False positives, которых надо избегать

Из опыта программы:
- **Sampling artefacts** на малых N (T_2CYCLE_ARTIFACT, IT-6 Ω_k chi_arr). **Mitigation**: per-target RO baseline обязателен; replication ≥ 3 разных seeds; проверка scaling в N.
- **Trivial inversions** на reduced T (T ≤ 4 free-start trivial). **Mitigation**: claim только если экстраполяция показывает sub-linearity на T ≥ 8 минимум.
- **Birthday-disguised attacks** (T_BIRTHDAY_ARTIFACT, П-881). **Mitigation**: явное разделение — это generic lower bound, не структурное преимущество.
- **Per-round bias не-композирующийся** (R_lin закрыт в Session 41/46). **Mitigation**: проверять полный round R, не linear approximation.

---

## 4. Каталог кандидатов

Операции / структуры, потенциально дающие super-linear composition. Каждой — оценка plausibility и того, как probe выглядит.

### 4.1 Path-bit / Hopf algebra (Том I §80-84)

**Идея**: bit как iterated integral (Chen). Composition путей в Hopf algebra даёт shuffle product + coproduct + antipode. Free Lie algebra на образующих = phase Hamiltonian (§83).

**Почему может работать**: non-abelian composition path-bits **формально** даёт супер-multiplicative growth signature space (BCH formula expands non-trivially). Если SHA round ↔ некоторый element Hopf algebra с non-trivial higher coefficients — composition T раз даст complexity роста ~ T^k для некоторого k.

**Почему может не работать**: SHA's actual operations (ADD, ROTR, XOR) — abelian/quasi-abelian. Non-abelian структура path-bit'а может быть несовместима с SHA primitives (как rotations с Witt-filtration в D-6).

**Probe (~1-2 сессии)**: на mini-SHA (n=8, T=4) посчитать signature SHA-round'а как path в free Lie algebra. Сравнить growth coefficients vs free random. Если SHA даёт depleted higher-order coefficients — closure'ом подобно D-2 cohomology probe; если нет — open path.

**Plausibility**: средняя. Hopf-algebra методы дают classification results (что классы существуют), редко дают attack speedups напрямую.

### 4.2 Φ-manifold 6D (Том II §II.9.1) ⊘SCOPED [Session 2]

> **Closure Session 2**: ⊘SCOPED для CL-P и CL-C. MI(W; Φ) ≈ 0.00003 (П-367 T_PHI_INPUT_DECOUPLED) — Φ декуплировано от входа, нет handle для control. Тривиально нарушает CL-D, но distinguishing — не цель программы. См. [SESSION_2.md §3](SESSION_2.md).

**Идея**: 6 свободных раундов {1, 4, 9, 10, 19, 21} образуют 6D подпространство свободы в Φ-координатах [П-362, T_PHI_MANIFOLD_6D ⚡VER].

**Почему может работать**: если advantage attack'а **аддитивна** по этим 6 свободным раундам (а не multiplicative по всем 64), то total advantage ~ 6 · ε вместо ε^64. Это и есть super-linear composition по структурно-привилегированному подмножеству.

**Почему может не работать**: 6 раундов уже учтены в methodology — Φ-disqualifier (§I.8.24, ∆EXP) не дал прорыва, validation §133 урезала ожидания. Возможно advantage **есть**, но он **в пределах** Composition Lemma (т.е. cumulative ~6 · const, не super-linear по T).

**Probe (~1 сессия)**: формально записать advantage attack'а как функцию координат на 6-manifold (а не на 64-cube). Если advantage(Φ-coords) factorizes по координатам, проверить cumulative growth — линейно в 6 (= O(1) в T) или линейно в T?

**Plausibility**: высокая. Это **самый прямой** существующий handle. Φ-manifold уже доказан, нужно только аккуратно посчитать advantage в его координатах.

### 4.3 Witt / prismatic (D-6, research/qt_minimal/CROSS_POLLINATION.md)

**Идея**: prismatic cohomology Bhatt-Scholze (2019) — единственная mathematics, видящая mixed-characteristic structure (F_2 ⊕ Z_2). SHA сидит ровно в этом mixed-char regime: Boolean ops (F_2) + ADD (Z_2).

**Почему может работать**: prismatic cohomology классифицирует **obstructions** к лифтингу. Если SHA-round имеет non-trivial prismatic class, может быть способ накапливать его через композицию super-linearly (как characteristic classes для bundles).

**Почему может не работать**: Session 1 prismatic (research/prismatic/SESSION_1.md) уже нашёл первое препятствие — Boolean ring = F_2[t]/(t²-t) имеет тривиальную δ-structure. Witt-vector reformulation работает, но rotation non-semisimple над F_2 — фундаментальное препятствие.

**Probe (~5-10 сессий, **долгая**)**: продолжить research/prismatic/ от Session 1. Конкретная следующая цель — δ-compatibility SHA-операций на W_n(F_2). Это **уже** target methodology (§II.8.3 ∆EXP Q_WITT_PRISMATIC_LIFT).

**Plausibility**: низкая на коротком горизонте, средняя на длинном. Если работает — даёт fundamentally new math, не просто attack.

### 4.4 Резонансы / cycle structure

**Идея**: SHA round имеет period (в линейной аппроксимации R_lin: ord = 448 = 2^6 · 7, Theorem 25.1). Если actual R имеет orbit structure с period < T, advantage может **осциллировать** не decay.

**Почему может работать**: T=64 specifically — фигурирует в design. Возможно T=64 совпадает с резонансом для какой-то operation, дающим non-decaying advantage. Period 448 не делится на 64, но возможно частичное совпадение фаз.

**Почему может не работать**: Theorem 41.1 — actual R имеет order ≫ 5000 (нет коротких циклов). Session 41 закрыл cycle-structure attack vector. Mod-q invariants closed (Session 62).

**Probe (~1 сессия)**: измерить orbit length distribution **не** R_lin, а full R (с реальными W). Если есть spike в orbit lengths около 64 или его делителей — открыто; если CV continues uniform — закрыто.

**Plausibility**: низкая. Уже плотно проверено в Sessions 41, 62.

### 4.5 OTOC / scrambling-based (§III.8)

**Идея**: OTOC показал (а) Σ драйвит 97% scrambling, (б) SHA-2 sequential cascade с 40-round design margin (r=24..64 post-scramble). Margin = exploitable zone.

**Почему может работать**: post-scramble раунды (24..64) предположительно "mixed" но возможно имеют структуру, **которой не было** в раундах 0..24. Если эта структура даёт per-round advantage **растущий** в r — composition будет super-linear.

**Почему может не работать**: post-scramble = full RO behaviour by definition OTOC. Если что-то и есть, то ниже OTOC sensitivity.

**Probe (~2 сессии)**: измерить higher-order OTOC (4-point, 6-point) на rounds 24..64. 2-point OTOC saturated; высшие могут не быть.

**Plausibility**: средняя. OTOC framework чистый и расширяемый.

---

## 5. Methodological pitfalls

### 5.1 Опасность повторения IT-6 Ω_k

IT-6 был "breakthrough" 5 месяцев. Корень — chi_arr-basis artefact, неверный null hypothesis. Уроки:
- Любое claim |Adv| > 0.3 без per-target RO baseline = suspect.
- Replication на ≥ 3 independent seeds, ≥ 2 different probe protocols.
- Если SHA → "signal" и RO под same protocol → "signal" same magnitude — это artefact protocol'а, не SHA.

### 5.2 Опасность Sessions 56-69 повторения

69 sessions уже искали super-linear composition, не находя. Чтобы не повторять:
- Каждый кандидат должен иметь **новый** angle (не reapply existing toolchain).
- Если probe дублирует Session N — закрыт автоматически.
- Cross-reference с research/prismatic/SESSION_*.md обязателен.

### 5.3 Stopping criterion

Программа **должна** иметь явный stopping criterion для каждого направления, чтобы не зависнуть в бесконечном scoping'е. Предлагаемое:
- Кандидат живёт ≤ 5 сессий до первого ⚡VER signal или ⊘SCOPED.
- ⊘SCOPED закрытие должно быть как §II.8.3 (mini-SHA validation + reasoning), не просто "не нашли".

---

## 6. План Session 2

**Target**: Кандидат 4.2 (Φ-manifold 6D) — самый прямой и дешёвый.

**Конкретные шаги**:
1. Поднять definition Φ-coordinates из методички (§II.9.1, П-362, П-378).
2. Записать advantage любого распознавателя как функцию (φ_1, φ_4, φ_9, φ_10, φ_19, φ_21).
3. Проверить: factorizes ли advantage по координатам? Или есть cross-terms?
4. Если factorizes — cumulative advantage = sum of 6 contributions = O(1) в T → **break Composition Lemma по конструкции**.
5. Если не factorizes — closing reason должна быть явной (cross-terms ~ T-multiplicative, восстанавливают линейность).

**Не делать в Session 2**:
- Не пытаться сразу строить attack. Сначала разобрать структуру advantage'а.
- Не запускать big experiments. Это analytic session, как эта.

**Файл результата**: `research/composition_lemma/SESSION_2.md`.

---

## Cross-references

- UNIFIED_METHODOLOGY.md § "PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ" (informal lemma source)
- UNIFIED_METHODOLOGY.md §II.9.1 (Φ-manifold definition)
- UNIFIED_METHODOLOGY.md §III.7 (CORRIGENDUM Ω_k — пример того, как НЕ надо)
- research/prismatic/SESSION_1.md (predecessor analytical session, δ-rings)
- research/qt_minimal/CROSS_POLLINATION.md (Witt-vectors target framework)

## Status

- §1 (informal source): зафиксировано, ✓
- §2 (formal statement): первый draft, требует review при первом эксперименте
- §3 (break definition): operational, готова к применению
- §4 (candidate catalog): 5 кандидатов, упорядочены по plausibility/cost
- §5 (pitfalls): зафиксировано
- §6 (Session 2 plan): targeted, готов к выполнению

**Decision points для review**:
- §2.2 формула `log Cost ≥ c_M · T − O(1)` — корректна ли? Проверить против Wang-chain (16 раундов P=1.0 → log Cost ≈ 0, нелинейно). Ответ: Wang работает только до r=17, далее P=2^{-32} per step, что и даёт линейный rate. Lemma не нарушена. Но edge case — стоит вернуться когда будет первая experimental session.
- §3.1 "false positives" — список не закрыт; добавлять по мере появления.
