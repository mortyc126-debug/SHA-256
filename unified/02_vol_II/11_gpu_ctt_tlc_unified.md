# Глава II.11. CTT, TLC, Unified Hash Theory, Carry Theory

> TL;DR: Carry Tensor Theory (CTT, §144) с Q(W,ΔW), 568 уравнений/1024 переменных; Three-Layer Collision (TLC, §164) — 39 верифицированных фактов, Theorem 38; Structured Chaos Framework (SCF, §165); Flow Mathematics + a-repair (§166); Oracle Distance Theory (§167); Единая теория хеширования (§170); Carry Theory axioms (§176).

## §II.11.1 CTT — Carry Tensor Theory (§144)

**568 уравнений / 1024 переменных** описывают carry-структуру SHA-256.

**Q(W, ΔW)** — квадратичная форма, контролирующая cascade carry.

**T_CTT_INVARIANT** ⚡VER: инвариант Q сохраняется под GL(32)-действием на schedule.

CTT — новая математическая дисциплина, изучающая SHA как тензорную систему над F₂.

## §II.11.2 TLC — Three-Layer Collision (§164)

**F1-F39**: 39 верифицированных фактов о трёхслойной структуре коллизии.

**Theorem 38** ✓DOK: **декомпозиция коллизии** = schedule layer + state layer + carry layer, каждый с своей сложностью.

Три слоя:
1. **Schedule layer**: работа W[0..63] ≈ 2⁶⁴.
2. **State layer**: работа (a..h) через раунды ≈ 2⁸⁰.
3. **Carry layer**: carry propagation ≈ 2⁴⁸ (меньше всего, поэтому attackable).

TLC даёт **рекурсивный** подход: сначала carry layer, затем state, наконец schedule.

## §II.11.3 SCF — Structured Chaos Framework (§165)

**Закон затухания**: `C(k) = 1.37 · exp(−k/1.80)`.

**τ = 1.80 раунда** — характеристическое время decay коррелированных возмущений.

**Witt degree = 2** — степень нелинейности в Witt-кольце для SHA-256.

SCF объединяет эмпирические наблюдения: chaos в SHA **структурирован**, не случаен.

## §II.11.4 Flow Mathematics и a-repair (§166)

**a-repair** — алгоритм восстановления (a..h) состояний при частичных constraint-violations.

**Break-Convergence-Reboot** (BCR) цикл:
1. **Break**: нарушение constraint на k-м раунде.
2. **Convergence**: попытка расслабиться вокруг k.
3. **Reboot**: если не сошлось, возврат к (k-3), попытка через alternative W.

BCR — **адаптивная Wang-цепь** с backtracking.

## §II.11.5 Oracle Distance Theory (§167)

**Мультипликативный bias на коллизию** = 2⁻²⁶.

**Oracle distance** между SHA-256 и RO измерима в битах Δ_I.

**⇒BRIDGE с Том III**: IT-3 Δ_χ² (marginal) — родственная метрика, но без MI-component.

## §II.11.6 Единая теория хеширования (§170) ⭐

**14 подразделов** — унифицированное описание хеш-функций через геометрические и информационные инварианты.

**Metric Tensor Theorem UNIVERSAL** ✓DOK: для любой хеш-функции H с ADD-gates существует метрический тензор g(H), кодирующий curvature в state-space.

**Pipe Conservation Law** ✓DOK: в "pipe" hash functions (Merkle-Damgård) энтропия сохраняется поэтапно.

**Термодинамика хеш-функций**: каждая round = diffusion step, увеличивающий энтропию до maximum (Шеннон-оптимальность).

**DimHash-256** — гипотетическая dimension-reduced hash с H_total = H(SHA-256) / 2 (теоретическая конструкция).

## §II.11.7 Carry Theory (§176) — аксиоматика

**CA1-CA5**: Carry Axioms — базовые аксиомы carry-операций.
**CG1-CG2**: Carry Group — групповые свойства.
**CN1-CN3**: Carry Norms — норменные свойства.
**CTr1-CTr3**: Carry Transformations — преобразования.
**CC1-CC2**: Carry Compositions — композиции.

Всего **15 аксиом** Carry Theory как самостоятельной алгебры.

## §II.11.8 Carry Operator Calculus и Homotopy (§175)

**Carry operator**: ∂_carry: F₂³² × F₂³² → F₂³³ (сдвиг вправо).

**Homotopy carries**: два carry paths между (W, ΔW) гомотопны ⇔ дают одинаковую вероятность.

## §II.11.9 Собственные законы Z/E/T/P (§161)

Четырёхслойная аксиоматика SHA-256:
- **Z1-Z11** — Zero-order laws (11 базовых свойств).
- **E1-E8** — Entropy-flow laws (8 законов).
- **T1-T8** — Transition laws (8 законов раундов).
- **P1-P10** — Projection laws (10 законов отображений).

Всего **37 законов** — формальная аксиоматизация SHA-256.

## §II.11.10 Beyond the Wall (§171)

**8 фаз анатомии стены r=17**:
1. Pre-wall linear regime (r ≤ 13).
2. Wall approach (r = 14-16).
3. Wall transition (r = 17).
4. Post-wall relaxation (r = 18-20).
5. Diffusion plateau (r = 21-32).
6. Saturation (r = 33-48).
7. Final avalanche (r = 49-62).
8. Fixed-point (r = 63-64).

Каждая фаза имеет собственные invariants и атакуется разными методами.

## §II.11.11 Серия XIII Anatomy of Avalanche (§149) ⭐

**3 фазы** avalanche propagation:
1. **Initial burst**: δ spreads as wave-front (exponential expansion).
2. **Stabilization**: reach HW≈32 (half bits).
3. **Rebound** (Q35): небольшой rebound к HW≈28-30 на late rounds.

**T_DECAY_LAW** ⚡VER: HW-decay подчиняется exp-закону.
**T_OVERBURN** ⚡VER: overburn эффект — HW > 50% кратковременно.
**T_REBOUND** ⚡VER: rebound реален, но narrow (magnitude ~2 бита).

## §II.11.12 Φ-Manifold 6D координаты (§107, уточнение)

**6 свободных раундов**: {1, 4, 9, 10, 19, 21}.

Эти раунды образуют **6D подпространство свободы** в Φ-координатах. Наши атаки чаще всего атакуют именно их.

## §II.11.13 SHA-512 spectral invariant (⊘ROLL as attack)

**T_SHA512_SPECTRAL** ⊘ROLL [§179]:
- Изначально заявлена как **attack vector** (spectral distinguishing).
- После анализа **отозвана как attack**.
- **Остаётся как design invariant** — собственное значение SHA-512.
- **⚠**: не путать с attack claim.

## Cross-refs

- §II.11.1 CTT ↔ §II.7 nova_mathematics (tensor methods)
- §II.11.2 TLC ↔ §II.10.6 MLB (multi-level approach)
- §II.11.3 SCF τ=1.80 ↔ Том III IT-4.S2 round decay τ≈2
- §II.11.5 Oracle distance 2⁻²⁶ ↔ Том III IT-3 Δ_χ² (related)
- §II.11.7 Carry Theory ↔ §II.5 T_RANK5_INVARIANT (carry structure)
- §II.11.9 Z/E/T/P laws ↔ §II.7 ★-Algebra 18 theorems (overlap ~50%)
- §II.11.11 Avalanche 3 phases ↔ Том I §111 avalanche wall
- §II.11.13 SHA-512 spectral ⊘ROLL ↔ §II.8 negatives list
