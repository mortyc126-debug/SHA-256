# Глава I.4. Расширения после Capstone v2, клетки, нейробит

> TL;DR: 6 новых осей (cost/causal/quotient/interval/cyclic/branching), 5 комбинационных клеток X×Y, hierarchy_v3/v4 (17 осей, 4 метагруппы VAL/OP/REL/TIME). Нейробит даёт 176.5×, phase-нейробит 351× (гибрид). Phase-нейробитный SHA R=1 НЕ превзошёл §4.2 (1765×).

## §I.4.1 Новые оси после Capstone v2 (§11)

**cost-bit** [§11.2] — ось OPERATION: энергия как primitive (работа/диссипация).
**causal-bit** [§11.3] — ось RELATION: направленные ацикличные связи (DAG).
**quotient-bit** [§11.4] — ось VALUE: классы эквивалентности, канонические представители.
**interval-bit** [§11.5] — ось TIME: временная протяжённость (длительности).
**cyclic-bit** [§11.6] — ось TIME: периодическое время Z/P.
**branching-bit** [§11.7] — ось TIME: CTL path quantifiers (AX/EX/AF/EG).

Итог §11: 11 осей → 17 осей, балансирование по 4 метагруппам.

## §I.4.2 Комбинационные клетки X×Y (§12)

**Концепция** [§12.1]: X×Y как самостоятельный primitive (не просто пара), когда композиция даёт новые свойства, не сводимые к X и Y отдельно.

**thermo_reversible** [§12.2]: reversible × cost. Landauer-совместимая обратимость.
**modal_quotient** [§12.3]: modal × quotient. Канонический представитель в Kripke-мире.
**causal_cost** [§12.4]: causal × cost. Энергия через DAG (conserved potentials).
**stream_linear** [§12.5]: stream × linear. Поток ресурсного типа (типы для каналов).
**triple-cell** [§12.5+]: phase × stream × cost (нейробит, см. §18).

## §I.4.3 hierarchy_v3 и v4 (§13)

**v3**: 14 осей, 4 метагруппы.
**v4**: 17 осей, баланс 5/5/4/4 (VAL/OP/REL/TIME).

Метагруппы:
- **VAL** (value-space): binary, fuzzy, prob, quotient, interval
- **OP** (operation): reversible, linear, cost, cyclic, phase
- **REL** (relation): relational, modal, causal, braid
- **TIME**: stream, interval, cyclic, branching

## §I.4.4 Каталог клеток (§14)

Покрытие клетками: **4 из 10 пар метагрупп** (C(5,2)=10 возможных).
- OP×OP (thermo_reversible)
- REL×VAL (modal_quotient)
- REL×OP (causal_cost)
- TIME×OP (stream_linear)

6 пар метагрупп — ПОКА БЕЗ КЛЕТОК (открытый вопрос для расширения).

## §I.4.5 Frozen core programme (§15)

**Molloy theorem** ⚡VER: frozen core ⊂ 2-core факторграфа; применимо к SAT phase transition (3-SAT).

7 файлов:
- `frozen_core.c` — детектор frozen core
- `mean_field.c` — MF approximation
- `bp_solver.c` — Belief Propagation
- `sp_solver.c` — Survey Propagation
- `probSAT.c` — пробабилистический solver
- `test_critical.c` — тест при α critical
- `mn_criterium.c` — Mézard-Montanari критерий

Результат: signals of frozen core detectable before SAT failure, но не дают polynomial shortcut.

## §I.4.6 Theoretical grounding (§16)

Формализация независимости осей:
- **poset** (partial order): X ≺ Y если X эмулируется на Y без потерь
- **DAG зависимостей**: native simulations, не circular
- **antisymmetry**: X ≺ Y ∧ Y ≺ X ⇒ X ≈ Y
- Глубина (depth) = **4** для известных осей

Основное утверждение: оси НЕ образуют total order, только poset.

## §I.4.7 Финальное состояние Part I (§17)

**Метрики после Session 2**:
- 17 осей (к v4)
- 5 клеток (включая triple)
- 2 capstone'а (v1 ошибочный → v2 корректный)
- Plurality: нет universal framework (см. §29 Том I гл. 5)

Открытые вопросы: верхняя граница осей, упругость клеток к композиции.

## §I.4.8 Нейробит — клетка stream×cost (§18)

**Определение**: temporal coding (spike timing) + dynamic cost (energy per spike); neuromorphic-like primitive.

**Эксперимент** ⚡VER [§18]: ball-search задача.
- Baseline (классический): N шагов grid-search.
- Нейробит: **176.5× end-to-end speedup** на реалистичных параметрах.
- Механизм: temporal binding через phase-coupling.

## §I.4.9 Phase-нейробит (§19)

**Концепция**: phase × stream × cost — triple cell.

**Эксперимент** ⚡VER [§19]: 3 нейробита с phase correlation.
- Гибридный **351× speedup** vs baseline.
- Quantum-like coherence через classical spikes + phase.

## §I.4.10 Phase-нейробит на SHA-256 R=1 (§20)

**Эксперимент** ✗NEG [§20]: смешанный результат.
- Phase-нейробит валиден как primitive.
- **НЕ превзошёл** §4.2 (HDV 1765×) на R=1 inversion.
- Значит: triple cell не доминирует simpler HDV для этой задачи.

**Следствие для §49 Task-Specificity Conjecture**: разные задачи — разные оптимумы.

## Cross-refs

- §28 аксиомы D1-D5 проверяют все 17+ осей (см. §I.5)
- §45 General Discrimination Theorem — результат phase-оси (см. §I.6)
- §50-51 SHA full circle — возврат к §4.2 через §45 (см. §I.6)
- §123 W-атлас — связь с Томом II carry (см. §I.8, мост 4)
