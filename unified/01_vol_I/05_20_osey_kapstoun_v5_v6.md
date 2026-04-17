# Глава I.5. 20 осей, Capstone v5/v6, аксиомы D1-D5

> TL;DR: 20 базовых осей бита после §21-24 (fuzzy, spatial-holonomy, timed, hybrid-automata клетка). Аксиоматика D1-D5 (20/20 pass, binary fails D5). **Plurality Theorem** — нет universal framework. CHSH violation S>2. Tropical BF 187× vs scipy. XOR-fragility theorem.

## §I.5.1 Три последние базовые оси (§21-23)

**Fuzzy-бит** (18-я ось) [§21]: континуум [0,1], решёточные операции ∧/∨, Łukasiewicz логика. Отличается от классики D4 witness: бесконечно много значений между 0 и 1.

**Spatial-holonomy бит** (19-я ось) [§22]: lattice gauge theory, Wilson loops, связность (connection) как primitive. Измерение — петля в gauge-графе. Проходит D1-D5.

**Timed бит** (20-я ось) [§23]: dense time (Alur-Dill hybrid automata), часовые переменные x∈ℝ≥0, reset/invariant конструкции. Phase space (клетки × clocks).

## §I.5.2 Hybrid automata — 6-я клетка (§24)

**Henzinger 1996 формализм** + энергия:
- **timed × cost** — первая клетка объединяющая две метагруппы (TIME и OP).
- Location-invariant + flow-condition + reset-relation + энергия.
- Слияние двух метагрупп — качественный скачок в структуре.

## §I.5.3 Capstone v5 — consolidation (§25)

**20 осей → 5 клеток**:
1. thermo_reversible (OP×OP)
2. modal_quotient (REL×VAL)
3. causal_cost (REL×OP)
4. stream_linear (TIME×OP)
5. hybrid_automata (TIME×OP)
6. phase-neurobit (triple: phase × stream × cost) — см. §I.4

Обновлённая иерархия закрывает разрыв между bit primitive и composite primitive.

## §I.5.4 Dependency matrix 21×21 (§26)

Структурная математика (не таксономия):
- **Native simulation matrix** [i,j] = true если i эмулируется на j без накладных расходов.
- **Транзитивное замыкание** вычислено.
- **Minimal bases**: несколько базисов покрывают матрицу.
- Depth по poset'у: 4.

## §I.5.5 Category of axes (§27)

Формальная структура:
- **ЧУМ на native simulations** (partial order).
- Antisymmetry: X ≺ Y ∧ Y ≺ X ⇒ X ≈ Y.
- **Hasse-диаграмма** строится, но не unique.
- Глубина 4 (максимум native-простых шагов).

## §I.5.6 Аксиомы D1-D5 (§28) ⭐

Формализация "расширение бита":
- **D1** [forgetful map]: ∃ F: T_X → {0,1}, не инъективный → non-trivial.
- **D2** [Boolean compatibility]: существует embedding {0,1} ↪ T_X, преобразующий AND/OR/NOT через Ch_X.
- **D3** [new primitive op]: ∃ Ch_X, не выражающийся через Boolean gates.
- **D4** [witness]: ∃ task где X даёт native advantage (speedup/resource savings).
- **D5** [non-degeneracy]: X не сводится к подпоследовательности меньшей оси.

**Результат** ✓DOK: **20/20 осей проходят D1-D5**. Classical binary fails D5 (тривиальна).

## §I.5.7 Plurality Theorem (§29) ✓DOK (negative)

**Утверждение**: Нет universal framework, объединяющей все 13+ primitives.

**Но**: 6 sub-frameworks существуют:
1. HDV-based (все HDC-совместимые)
2. phase-based (U(1), Z/m)
3. probabilistic
4. categorical (reversible, causal)
5. continuous (fuzzy, timed, spatial)
6. computational (linear, church, modal)

Следствие: нельзя redукция 13 → 1, но можно 13 → 6.

## §I.5.8 Triple closure — D5, D6 (§30)

**D5 upper bound**: N = ∞ под D1-D5 (нет конечной верхней границы).
**D6 minimal substrate**: нет вычислительно-значимого минимального субстрата (mixed result).

**Вывод**: аксиоматика D1-D5 открыта вверх, что объясняет bottom-up открытия §37-38.

## §I.5.9 CHSH violation на phase bits (§31) ⚡VER ⭐

**Результат**: phase-bits нарушают Bell inequality.
- **S > 2** numerically (классический predел: S ≤ 2).
- Quantum-like поведение без Hilbert space.
- Первый конкретный numerical win phase-оси.

## §I.5.10 GHZ discrimination (§32)

**Результат**: phase-bits различают GHZ entanglement состояния.
- **Экспоненциально с n** (число участников).
- Quantum-like scaling на классической phase-оси.

## §I.5.11 Tropical neurobit — 6-я клетка (§33-36)

**§33**: tropical algebra × cost — 6-я клетка. Численно валидна.

**§34**: tropical numpy — **6.25×** speedup на dense n=1000 (но против pure Python baseline).

**§35** ✗NEG: scipy C-level correction. Против scipy не воспроизводится → 6.25× был **python artifact**.

**§36** ⚡VER: Apples-to-apples Bellman-Ford own C-level. **187× vs scipy** (dense graph). Реальный C-level win.

## §I.5.12 Bottom-up оси (§37-40)

**§37** ∆EXP: parametric chaos-configurable bit (Lyapunov exponents). 21-я ось КАНДИДАТ. **§41 correction**: хрупкий к шуму, но полезен для chaos computing.

**§38** ∆EXP: stochastic resonance bit (noise-driven resonance). 22-я ось кандидат.

**§39** ✗NEG: field bits (reaction-diffusion, memristor). Memristor НЕ примитив (композиция). Tentative 23-я отклонена.

**§40** Capstone v6: bottom-up consolidation. 20 + 3 кандидата. Revised 5-metagroup.

## §I.5.13 XOR-fragility theorem (§42) ✓DOK

**Утверждение**: XOR-операции неустойчивы в некоторых битовых расширениях.

**Следствия**:
- Некоторые расширения (phase, fuzzy) ломают XOR под noise/error.
- Это ≠ failure примитива, это свойство расширения.
- Объясняет почему classical binary особенный: XOR robust.

## Cross-refs

- §45 General Discrimination Theorem — следствие D3+D4 для phase (см. §I.6)
- §28 D1-D5 проверяются на SHA коллизиях как "binary fails D5" (см. §I.8 §111)
- §31 CHSH ↔ §32 GHZ (exp. scaling)
- §39 ✗NEG ↔ §I.8 §126 ALL NULL (связанная методологическая стена)
- §42 XOR-fragility ↔ Том II T_XOR_DIFFERENTIAL ✗NEG (XOR-only даёт null для каскада)
