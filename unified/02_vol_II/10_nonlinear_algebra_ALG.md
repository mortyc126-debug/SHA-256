# Глава II.10. Нелинейная алгебра (XVII), ALG, Carry-Web, NK Framework

> TL;DR: Серия XVII Нелинейная Алгебра (§154) объясняет hw59=76 барьер статистически; SAA = SHA-Adder Algebra (§154.5); Витт-кольцо как источник нелинейности (§154.6); ALG (Arithmetico-Logical Geometry, §183) — 53 определения, 4 столпа, 7 предсказаний; Carry-Web Theory (§173) с Scaling Law и T_MULTIQUERY_DISTINGUISHER; NK Framework (Nova Cryptarithmetica §215+) — три шумовых источника и 13 закрытых направлений.

## §II.10.1 SAA — SHA-Adder Algebra (§154.5)

**T_SAA_DECOMP** ⚡VER: SHA-адитивный слой разлагается в SAA-элементы.
**T_L0_RANK** ⚡VER: rank L₀-матрицы SAA фиксирован.
**T_GF2_LINEARITY** ⚡VER: GF(2)-линейный остаток после SAA-декомпозиции.

SAA — набор из 6 теорем о разложении `+_{2^32}` как алгебраической структуры.

## §II.10.2 Источник нелинейности (§154.6)

**T_SHA256_FULL_NONLINEAR** ✓DOK: полная нелинейность SHA-256 = Витт-конечная.
**T_SHA_NONLINEARITY_SOURCE** ⚡VER: нелинейность возникает **только** из carry-адджеров (не Ch/Maj).

## §II.10.3 T_COLLISION_EQUATION и 128-bit lower bound (§154.4)

**T_COLLISION_EQUATION** ✓DOK [§154.4.1]: явное уравнение коллизии в терминах schedule + state.
**T_LAST_ROUND_LINEARITY** ✓DOK: последний раунд линеен относительно (a..h).
**T_TRIANGULAR_SOLVE** ✓DOK: систему можно решать треугольным методом (но размер O(2⁵¹²)).
**T_COLLISION_LOWER_BOUND_128** ✓DOK [§154.4.4]: **нижняя граница 2¹²⁸** — независимое от birthday доказательство.

## §II.10.4 Ключевые теоремы серии XVII (§154)

**T_SIG0_LOWER_BOUND_EXACT** ✓DOK: точная нижняя граница Σ₀.
**T_T2_AMPLIFICATION** ⚡VER: T₂ амплифицирует bit-changes.
**T_T2_FIXED_POINT** ★★★★★ ⚡VER: неподвижные точки T₂.
**T_MIXING_PATTERN** ⚡VER: паттерн смешивания.
**T_BARRIER_STATISTICAL** ★★★★★ ⚡VER: **статистический барьер** на hw59 (объяснение через CLT).
**T_HW59_DW_INDEPENDENCE** ★★★★★ ⚡VER: независимость hw59 и DW-параметров.
**T_UNIVERSAL_76_EXPLAINED** ★★★★★ ⚡VER: **hw59 = 76 универсально объяснена** статистически (CLT из 512-битного space).
**T_GEOMETRY_512** ⚡VER: геометрия 512-битной сферы.
**T_FUNNEL_LOCAL** ⚡VER: локальный funnel в landscape.
**T_HW64_INDEPENDENCE** ★★★★★ ⚡VER: независимость hw64 от прочих.

## §II.10.5 Серия XVIII — T_WANG_OPTIMALITY (§155)

**T_BACKWARD_PROPAGATION** ✓DOK [§155.2.1]: backward propagation корректна.
**T_NO_INVARIANT_DP** ⚡VER: нет нетривиального invariant DP.
**T_SCHEDULE_ISLAND_BOUND** ⚡VER: ограничение на schedule-islands.
**T_WANG_OPTIMALITY** ★★★★★ ✓DOK [§155.3.3]: **Wang-цепь оптимальна** в своём классе — не существует cheaper chain с тем же P=1.0.

**T_ONE_ISOLATED_ROUND** ⚡VER [§155.4]: один изолированный раунд.
**T_COMPLEXITY_LOWER_BOUND_NEW** ⚡VER: новая нижняя граница сложности.
**T_DIFFUSION_DECOMP** ⚡VER: диффузия decomposes.
**T_CARRY_MARKOV** ⚡VER: carry ↦ Markov-модель.

## §II.10.6 Серия XX — Multilevel Birthday (§156)

**T_MLB_EXACT** ★★★★★ ✓DOK [§156.2.1]: **точная формула** Multilevel Birthday.
**T_MLB_OPTIMAL_K** ✓DOK: оптимальный k в MLB-схеме.
**T_FIRST_STATE_FORCED** ⚡VER: первое состояние принуждено.
**T_ALT_SC_INFEASIBLE** ✗NEG: альтернативные SC невозможны.
**T_MIDSTATE_ENTROPY** ⚡VER: энтропия midstate.

## §II.10.7 Series XXIII-XXXVI (GPU-верифицированные) (§158)

**T_CARRY_DOMINANT** ★★★★★ ⚡VER: **carry доминирует** нелинейность (GPU).
**T_CT_QUASIGROUP** ★★★★★ ⚡VER: carry-transform = квазигруппа.
**T_SHA_FIXED_POINT_FAMILY** ★★★★★ ⚡VER: семейство фиксированных точек SHA.
**T_SHA_FIXED_POINT_32** ★★★★★ ⚡VER: fixed point на 32-bit SHA.
**T_SHA_RANDOM_DYNAMICAL_SYSTEM** ★★★★★ ⚡VER: SHA ≈ random dynamical system (эмпирическая характеризация).
**T_ORBIT_STRUCTURE_IV** ★★★★★ ⚡VER: структура орбит относительно IV.

**T_W32_FRAMEWORK** ★★★★★ ⚡VER: 32-bit framework.
**T_SHA_CONDITIONAL_LINEARITY** ⚡VER: условная линейность под constraints.
**T_TRAJECTORY_WINDOW** ⚡VER: trajectory window in state-space.
**T_INFORMATION_UNIFORMITY** ⚡VER: uniformity информации.
**T_COLLISION_EQUATION_EXACT** ⚡VER: exact collision equation (версия с GPU проверкой).

## §II.10.8 ALG — Arithmetico-Logical Geometry (§183) ⭐

**53 определения**, **4 столпа**, **7 предсказаний** для SHA-512 и Blake2.

**4 столпа ALG**:
1. **Arithmetic**: сложение, carry-propagation.
2. **Logic**: boolean gates (Ch, Maj, parity).
3. **Geometry**: метрики на (a..h, W) пространстве.
4. **Complexity**: MILP/SAT lower bounds.

**Предсказания для SHA-512**:
- T_SHA512_SPECTRAL ⊘ROLL (изначально как attack, позже **отозвано** как attack vector, остаётся как design invariant).
- Cross-platform invariants (5.1-5.3).
- Scaling laws для SHA-512 vs SHA-256.

**Предсказания для Blake2**:
- Analogue compression function behavior.
- Different nonlinearity fingerprint (ожидается).

## §II.10.9 Carry-Web Theory (§173) ⭐

**T_COPULA_SHA256** ✓DOK: копула-структура SHA-256 carry network.
**T_BRIDGE_THEORY** ✓DOK (2.1-2.5): bridge между carry-blocks.
**T_CASCADE_THEORY** ✓DOK (3.1-3.3): каскад carry-blocks.
**T_AMPLIFICATION_THEORY** ✓DOK (4.1-4.3): amplification факторы.
**T_MULTIQUERY_DISTINGUISHER** ⚡VER: multi-query distinguisher — **новый тип** (не single-sample).

**§9 Scaling Law**: `work ~ 2^f(R)` где f(R) полиномиальна.
**§10 Algebraic Degree**: degree grows как Fibonacci (ANF).
**§11 DFS Preimage — Axis 3, 7-8**: три оси для DFS preimage-атаки.

## §II.10.10 NK Framework (Nova Cryptarithmetica) (§215+, §227)

**Три шумовых источника**:
1. **Intrinsic nonlinearity** (nonlinear gates).
2. **Avalanche diffusion** (mixing through rounds).
3. **Carry chain chaos** (carry propagation nondeterminism).

**13 закрытых направлений** (полный список):
1. Hensel lifting
2. 2D nonlinear matrix
3. Boomerang XOR-only
4. Rotational differentials
5. MILP на R≥17
6. Multi-block Wang predict_delta
7. Rotational attractor (П-36..П-41)
8. S-bit QUBO/MAX-SAT
9. Σ-bit super-primitive
10. Tropical numpy vs scipy
11. Scalar макро-координаты
12. Vector k=32 макро-координаты
13. Stacked statistical disqualifiers

**NK Стена**: консолидированный вывод — SHA-256 имеет фундаментальную стену на r=17 + стену на hw59=76 + стену avalanche — три независимых барьера.

## §II.10.11 SAT Solver Evolution (§227, §6)

**v1**: naive DIMACS encoder.
**v2**: streamlined clauses.
**v3**: heuristic restarts.
**v4 = Q∩T Hybrid** ⭐ ⚡VER: прорыв через Q∩T-intersection method.
**v5**: constant propagation optimization.

**4 параллельных эксперимента** с различными constraint-density.

## §II.10.12 OMEGA Methodology (§224)

**α-kernel формула** ⚡VER: точная формула для α-kernel (ядро оптимизатора).
**V1-V10 solvers**: 10 версий solver с разными trade-offs.
**T_UNIQUE_PREIMAGE_R6** ⚡VER: единственность preimage на R=6.
**Carry Jacobian Near-Full-Rank** ⚡VER: почти полный ранг Jacobian carry.
**128-bit Partial Collision (Free)** ⚡VER: 128-битная частичная коллизия бесплатно при free-start.

## Cross-refs

- §II.10.4 T_UNIVERSAL_76 ↔ §II.9.8 T_BIRTHDAY_ARTIFACT (оба про hw59)
- §II.10.5 T_WANG_OPTIMALITY ↔ §II.4 T_WANG_CHAIN (финальная оптимальность)
- §II.10.6 T_MLB_EXACT ↔ §II.4 T_BIRTHDAY_COST17 (сравнение MLB vs birthday)
- §II.10.8 ALG ↔ §II.7 BTE Theory (две смежные дисциплины)
- §II.10.9 T_MULTIQUERY ↔ Том III IT-4.S4 block-2 amplification (concepts пересекаются)
- §II.10.10 13 закрытых ↔ §05_negatives.md (сверить)
