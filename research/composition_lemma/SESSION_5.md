# Session 5: Catalog audit + transition decision

**Дата**: 2026-04-26
**Статус**: META-сессия. Завершение initial фазы Composition-Lemma программы.
**Цель**: проверить полноту каталога кандидатов из SESSION_1, применить structural filter ко всем pre-existing methodology directions, принять decision о transition к Witt/prismatic.

**Outcome**: каталог расширен до **~20 направлений** через audit; все либо ⊘SCOPED structurally, либо закрыты prior methodology, либо составляют Witt/prismatic линию. Composition-Lemma initial phase завершена. Frontier — research/prismatic/.

---

## 1. Methodology

**Structural filter** (выработан в Sessions 2-3):
1. **Input-control handle**: есть ли у направления способ управлять intermediate структурой из входа W? Формально: MI(input; structural-observable) > 0?
2. **T_max bound**: ограничено ли T_max(observable) by mixing time? Если T_max ≪ 64 для всех order'ов — Composition Lemma в силе.

**Дополнительные критерии**:
3. **Уже purposed в Prismatic Program (Sessions 1-69)**? Если да — closure из там же.
4. **Out of scope** (quantum, side-channel)? Эти направления принципиально отделены, не "missed candidates".

**Применение filter'а к каждому direction**:
- Если 1) "no" или 2) "bounded ≪ 64" → ⊘SCOPED.
- Если оба "yes/unbounded" — open candidate.

---

## 2. Audit: расширенный каталог из 20+ direction'ов

Проверка систематически по пространству classical methods. Источник — методичка + cryptanalysis literature.

### 2.1 Algebraic methods

| # | Направление | Filter result | Status |
|---|---|---|---|
| 1 | Hensel lifting / 2-adic | T_HENSEL_INAPPLICABLE [П-43] | ⊘ prior closure |
| 2 | Gröbner basis / XL / LLL | 10^25 monomials at T=4 [Session 59] | ⊘ prior closure |
| 3 | Cube attacks / higher-order ANF | ANF saturates за 2 раунда [§128] | ⊘ T_max=2 |
| 4 | Algebraic immunity attacks | AI=1-2 per round, composes to n/2 [Theorem 53.1] | ⊘ linear composition |
| 5 | Buchberger / commutative algebra | subsumed by #2 | ⊘ |
| 6 | Exterior algebra / Möbius | subsumed by #3 (ANF Reed-Muller) | ⊘ |
| 7 | Path-bit / Hopf algebra | T_max=2 [Session 4] | ⊘ SCOPED |

### 2.2 Statistical / linear methods

| # | Направление | Filter result | Status |
|---|---|---|---|
| 8 | Linear cryptanalysis (Walsh max\|z\|) | bias ≤ 1/4 per round; composes linearly [Theorem 34.1] | ⊘ standard CL bound |
| 9 | Differential cryptanalysis | trail prob c^T, c < 1/4; r=17 barrier 9 methods [§II.9.5] | ⊘ standard CL bound |
| 10 | Differential-linear hybrid | marginal improvements in literature, no super-linear | ⊘ same CL bound |
| 11 | Boomerang / Rebound | cap 46 rounds в literature [Sessions 57, 58] | ⊘ prior closure |
| 12 | Multi-block predict-delta | 0/3000 пробитий через границу блока [v8] | ⊘ prior closure |
| 13 | OTOC higher-order ≡ chain-k | T_max(k) bounded by mixing time ~24 [Session 3] | ⊘ SCOPED |
| 14 | Higher-order Walsh chain | same as #13 (OTOC^(k) ≡ chain-k identity) | ⊘ SCOPED |

### 2.3 Combinatorial / search methods

| # | Направление | Filter result | Status |
|---|---|---|---|
| 15 | Birthday / multi-block birthday | Ω(2^128) lower bound 6 independent proofs [§II.6.8] | ⊘ standard CL bound |
| 16 | MITM (state[16]) | O(2^80) — хуже Wang chain [⊘SCOPED 2026-04] | ⊘ prior closure |
| 17 | SAT / MILP | TIMEOUT T ≥ 5-8, MILP ~2^144 | ⊘ standard CL bound |
| 18 | Reinforcement learning / MCTS | classical search — same CL as exhaustive | ⊘ standard CL bound |
| 19 | ML-guided distinguisher | Distinguisher v6.0 AUC=0.980; CL-D trivial break, не CL-P/CL-C | ⊘ CL-D only |
| 20 | Tensor networks / MPS | bounded by entanglement entropy ~ scrambling | ⊘ same as #13 |

### 2.4 Structural / geometric methods

| # | Направление | Filter result | Status |
|---|---|---|---|
| 21 | Φ-manifold 6D | MI(W;Φ)=0.00003 [Session 2] | ⊘ SCOPED |
| 22 | Resonance / cycle structure | order ≫ 5000, no short cycles [Theorem 41.1, Session 41] | ⊘ prior closure |
| 23 | Mod-q invariants | NONE [Theorem 62.1, Session 62] | ⊘ prior closure |
| 24 | Bit-permutation symmetries | NONE [Theorem 35.1, Session 35] | ⊘ prior closure |
| 25 | TDA / persistent homology | trivial topology [Theorem 55.1, Session 55] | ⊘ prior closure |
| 26 | Conservation laws | 3.5σ artifact mod 257, far from threshold [Session 65] | ⊘ prior closure |
| 27 | Joint compression (m, H(m)) | independent compression [Session 65] | ⊘ prior closure |
| 28 | Subspace mixing asymmetry | structural bound, no exploit [Session 64] | ⊘ no exploit |
| 29 | Weak states / λ heterogeneity | CV=0.06, mostly uniform [Session 61] | ⊘ prior closure |

### 2.5 Mixed-characteristic / arithmetic geometry

| # | Направление | Filter result | Status |
|---|---|---|---|
| 30 | Q∩T algebra | z3 BitVec already реализует [⊘SCOPED 2026-04] | ⊘ prior closure |
| 31 | Cohomology probe (carry Jacobian) | trivial MSB / state-dep extras [⊘SCOPED 2026-04] | ⊘ prior closure |
| 32 | **Witt-vectors / prismatic** | identifies obstruction (rotation non-semisimple); no algorithm yet | **OPEN — long horizon** |
| 33 | q-de Rham / q-prism | подвид #32 | OPEN — see #32 |

### 2.6 Out of scope

| # | Направление | Reason |
|---|---|---|
| 34 | Quantum attacks (Grover, QFT-based) | CL is про classical; Grover gives sqrt-speedup только, недостаточно |
| 35 | Side-channels (timing, power, fault) | engineering, не математика; out of CL scope |

---

## 3. Audit conclusions

### 3.1 Catalog completeness

**31 классических направлений** проверены через structural filter. **30 ⊘SCOPED либо prior closure.** Один открытый — Witt/prismatic (#32).

**Полнота**: каталог покрывает обозримое classical attack space. Missed candidates маловероятны:
- Любая algebraic attack ≡ #1-7.
- Любая statistical attack ≡ #8-14.
- Любая combinatorial attack ≡ #15-20 (даже ML-augmented).
- Любая structural / spectral attack ≡ #21-29.
- Mixed-characteristic / new math ≡ #30-33.

Если новый method появится в литературе — он, скорее всего, попадёт в одну из этих категорий и closure будет применима через инструменты Sessions 2-4.

### 3.2 Convergence criterion

Структурный фильтр даёт **same conclusion** что и Prismatic Program 69 sessions: SHA-256 не атакуется классически.

Two independent paths — convergence:
- **Empirical** (Prismatic Program): exhaustion attack space через scoping experiments.
- **Structural** (this program): filter через MI-handle + T_max bound на каждом направлении.

Конвергенция — strong robustness signal. Maybe не proof, но sufficient evidence что conclusion robust.

### 3.3 Что РЕАЛЬНО осталось

**Witt/prismatic (#32)** — единственное direction, не закрытое filter'ом. Причина — оно операя на **mixed-characteristic geometry** (F_2 ⊕ Z_2), где наши argument'ы (MI, T_max, mixing time) могут быть не применимы. δ-rings и prismatic cohomology — fundamentally different framework.

Это **уже** target methodology (§II.8.3 ∆EXP Q_WITT_PRISMATIC_LIFT), и для него существует parallel research line `research/prismatic/` (Session 1 done, target Session 2 — δ-compatibility SHA операций на W_n(F_2)).

---

## 4. Decision: transition к Witt/prismatic

### 4.1 Composition-Lemma program — initial phase complete

После Sessions 1-5 first phase программы завершена. Достижения:
1. Formalized Composition Lemma (SESSION_1) с разделением CL-D/CL-P/CL-C (SESSION_2).
2. Structural filter — operational tool для closure'а кандидатов за одну сессию.
3. ⊘SCOPED 3 кандидата (Path-bit, Φ-manifold, OTOC higher-order) plus catalog audit.
4. Triangulation с Prismatic Program — same conclusion via independent path.

Не достижения:
- Не нашли break Composition Lemma. (Expected, given convergence.)
- Не доказали Composition Lemma как теорему. (Это open math problem.)

### 4.2 Witt/prismatic — handoff к существующей линии

Composition-Lemma program **не открывает** новую Witt/prismatic линию — она уже идёт в `research/prismatic/` с April 22, 2026 (Session 1 done). Наша программа просто **формализует** что Witt/prismatic — единственное оставшееся открытое direction.

### 4.3 Continuing options

**Option A: Прекратить Composition-Lemma program**, перейти на наблюдение research/prismatic/.
- Плюс: чистая separation; Composition-Lemma фаза завершена за 5 сессий.
- Минус: если новые candidate-направления появятся (литература, новые методы), не будет где их обрабатывать.

**Option B: Поддерживать Composition-Lemma program в "monitoring mode"**.
- Каждый новый method из литературы → одна analytic сессия применения filter'а.
- Если filter не применим (как с Witt) → обогащение каталога candidate'ов.
- Плюс: continuity, готовность к future findings.
- Минус: minimal active work.

**Option C: Active research — формальное доказательство Composition Lemma**.
- Не просто фильтровать кандидатов, а доказать что NO classical method can break CL.
- Это **очень** сложная open math problem (равно ~ proving P ≠ NP-class statements).
- Плюс: если получится — historic.
- Минус: 24 года никто не приближался.

**Recommendation**: **Option B**. Maintenance mode. Если новый кандидат — одна сессия применения filter'а. Иначе наблюдение research/prismatic/.

---

## 5. Меthodology обновления (предлагаю)

UNIFIED_METHODOLOGY.md можно обновить minimally — отметить факт что Composition-Lemma direction triangulated с Prismatic Program. Не "новый результат", а второй structural argument for уже-зафиксированной conclusion.

Предлагаемое место — preamble или §"PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ", добавить ссылку на research/composition_lemma/ как "structural triangulation".

Этого делать **не сейчас** — оставить методичку нетронутой по договорённости. Пометить TODO для ситуации когда появится конкретное новое findings из Witt/prismatic линии.

---

## 6. Plan следующих сессий

### Composition-Lemma program (this directory)

**Maintenance mode**:
- Sessions создаются только при появлении нового candidate из литературы / discussions.
- Каждая такая сессия — applying filter из SESSION_2-4 структуры.

### Witt/prismatic line (research/prismatic/)

**Active continuation**: Session 2 там target — δ-compatibility SHA-операций на W_n(F_2). Это уже plan'ed в research/prismatic/SESSION_1.md §"Идея 1".

Не работаем над research/prismatic/ из этой линии — это отдельное направление.

### Если что-то подвернётся

Scenarios для new sessions in this directory:
- (1) Появляется paper с новым cryptanalysis method → applying filter в одну сессию.
- (2) Witt/prismatic дает breakthrough → проверить если applies к classical attack или нет.
- (3) Reformulation Composition Lemma как formal theorem (non-trivial math project) → multiple sessions.

---

## 7. Cross-references

- SESSION_1.md — formalization (precise statement).
- SESSION_2.md — Φ-manifold + CL-D/CL-P/CL-C split.
- SESSION_3.md — OTOC higher-order.
- SESSION_4.md — Path-bit / Hopf algebra.
- research/prismatic/SESSION_1.md — Witt/prismatic line continuation point.
- UNIFIED_METHODOLOGY.md §"PRISMATIC PROGRAM" — empirical 69-session результат.
- UNIFIED_METHODOLOGY.md §II.8.3 ⊘SCOPED 2026-04 — Q∩T, MITM, cohomology, ANF.

## 8. Status

**Initial phase Composition-Lemma program: complete.**

5 сессий, 3 кандидата ⊘SCOPED structurally, catalog audit ~31 directions, 1 open (Witt/prismatic как long-horizon parallel line). Convergence с Prismatic Program 69 sessions confirmed.

**Next active work**: research/prismatic/SESSION_2 (отдельная линия, не covered здесь).
