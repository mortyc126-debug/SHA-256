# Приложение: Хронология прогресса

Сквозная хронология трёх линий исследования. Только ключевые точки.

## Линия A: Математика бита (METHODOLOGY.md, §1-§133)

### Session 1 — Фазы A-F
- Фаза A: HDC варианты (ternary, quaternary, topological, fibonacci, spectral, clifford) — §3
- Фаза B: SHA-256 R=1 inversion 1765× speedup — §4.2 ⭐
- Фаза C: Phase bits, ebit pairs, GHZ triples, DJ/BV gates, no-cloning — §5
- Фаза D: Reversible, stream, prob, braid, anyonic — §6
- **Capstone v1 (unified_hierarchy) ОШИБОЧНЫЙ** — §6.9
- Фаза E: linear, selfref, church, modal, relational — §7
- Фаза F: Consolidation, axis_dependencies — §8
- **Capstone v2** — hierarchy_v2 честный пересмотр

### Session 2 — Extensions
- Новые оси: cost, causal, quotient, interval, cyclic, branching — §11
- Комбинационные клетки (pairs) — §12
- **Capstone v3/v4** — 17 осей, 4 метагруппы
- Frozen core programme (Molloy theorem) — §15
- Theoretical grounding (poset, DAG) — §16
- Нейробит stream×cost (176.5×) — §18
- Phase-нейробит triple cell (351×) — §19

### Session 3 — Consolidation
- Fuzzy-бит 18-я ось — §21
- Spatial-holonomy 19-я ось (Wilson loops) — §22
- Timed бит 20-я ось (Alur-Dill) — §23
- Hybrid automata 6-я клетка — §24
- **Capstone v5** — 20 осей → 5 клеток — §25
- Dependency matrix 21×21 — §26
- Axioms D1-D5 (20/20 pass) — §28
- **Plurality Theorem** (D3 negative) — §29
- CHSH violation phase-bits (S>2) — §31 ⭐
- GHZ discrimination exp. — §32
- Tropical BF 187× (scipy C-level) — §36
- Chaos-configurable, stochastic resonance — §37-38
- Field bits ✗NEG — §39
- **Capstone v6** bottom-up — §40
- XOR-fragility theorem — §42

### Session 3 extension
- Sparse phase bits, MPS (10K qubits/11ms) — §43-44
- **General Discrimination Theorem** — §45 ⭐⭐⭐ ЦЕНТРАЛЬНЫЙ
- Z/m hierarchy m^(k-1) — §46
- Z/4 unlocks Clifford — §47
- 10⁶ qubits DJ/0.9s — §48
- **Task-Specificity Conjecture** — §49
- SHA-256 full circle (646× pairwise) — §50-51 ⇒BRIDGE
- P-bit Purdue, S-bit synthesis — §53-59
- Σ-bit attempt ✗NEG — §61
- **SuperBit engine** — §63-79
- **Theorem 7 exponential DISCRIM-DETECT** — §67 ⭐

### Session 4 — Foundation layer
- Path-bit (iterated integrals, Hopf) — §80-84
- Wild questions Q1-Q15 — §85-87
- Cosmic-bit raid C1-C5 — §88
- CoordBit universal coordinates — §89
- **Bit-cosmos Platonic multi-axis** — §90-93
- Laplace demon (conservation laws) — §91
- P vs NP через bit-cosmos — §92
- SHA трансформация теста — §94

### Session 5 — Астрономия битов
- Hadamard basis (8 properties) — §98-102, §110 ⭐
- ADD mod 2^L через Walsh — §104
- Triple-products SHA R=2 — §105
- Avalanche wall ✗NEG — §111
- Coordinate equations раунда — §113
- **Carry = conjugate momentum** — §114 ⭐
- Markov theory carry — §116-117
- Spectral basis L=32 ✗NEG — §118
- **Diagonal conjugacy universal ⚡VER** — §119 ⭐⭐
- Moment geometry — §121-122
- **W-атлас ΔW∝1/N_ADD** — §123 ⭐
- **Принцип Макро-Скорости** — §124
- Scalar координаты ✗NEG — §125
- Vector k=32 ✗NEG — §126
- ANF experiment подтверждает §114-A — §127 ⇒BRIDGE
- ANF shortcut окно = 1 раунд — §128
- Backward stepwise — §129
- Φ-disqualifier — §130
- Stacked ✗NEG — §131
- **ANF early-verify 7.6×** — §132 ⭐ (первый backward shortcut)
- Validation correction — §133

## Линия B: SHA-256 дифф. криптоанализ (methodology_v20, П-1..П-1300+, март-апрель 2026)

### Март 2026 — базовая серия П-1..П-9
- T_ANF, T_LIFT-1/2, T_ADD8, T_IMG2, T_CASCADE, T_SCHEDULE_DECOUPLING
- Установлены базовые леммы L1-L7

### Конец марта — Каскад П-10..П-22
- **T_CASCADE_MAX** (14 нулей за O(2²²)) — П-10 ⭐
- T_DE17_DECOMPOSITION = Da13 + ΔW16 — П-11/12
- T_CASCADE_17, T_DE18_DECOMPOSITION — П-13/15
- T_BARRIER_16, T_DE18_INDEPENDENCE — П-15/16
- **Барьер r=17** — T_SAT_CASCADE, T_STRUCTURED_SAT
- T_GENERALIZED_CASCADE — П-19
- T_MIXED_DIFF, T_DOM_DIFF, T_IV_BIT0 — П-20/21
- T_CARRY_ANALYTIC, T_SUFFICIENT_R1 — П-22

### Апрель 2026 начало — XOR + Wang П-23..П-26
- T_SCHEDULE_FULL_RANK, T_PERIOD3_CASCADE — П-23
- T_DCH_EXACT, T_ANALYTIC_TRAIL — П-22/23
- **T_SC_A1** (100000/100000) — П-24 ⚡VER
- **T_JOINT_SC, T_WANG_ADAPTIVE** (50000/50000) — П-24/25 ⭐
- T_WANG_CHAIN (P=1.0) — П-25/26

### П-27 — Birthday & State
- **T_BIRTHDAY_COST17** — П-27A
- T_STATE17 — П-27B
- T_2D_BIRTHDAY_NEGATIVE ✗NEG — П-27C

### П-28..П-35 — Carry-каскад, неудачные направления
- П-28: CARRY-КАСКАД (512→589 бит) ⭐
- П-29: T_BOOMERANG_INFEASIBLE ✗NEG
- П-30-32: birthday-поиск, T_STATE17 ⚡VER
- П-33: T_DELTA_CH_EXACT
- П-34: T_MILP_INFEASIBLE_17 ✗NEG
- П-35: T_ROTATIONAL_NEGATIVE ✗NEG

### П-36..П-53 — Многоаттрактор, решётки, p-адика
- П-36-41: Ротационный аттрактор ✗NEG (571 строк разочарования)
- П-42-44: T_HENSEL_INAPPLICABLE, T_NONLINEAR_MATRIX_FAILS ✗NEG
- П-45-48: Якобиан, Hensel — исчерпаны
- П-49-52: **p-адическая башня** — T_HEIGHT_SHA256=6 ⊘ROLL
- П-53: **height_2≥11** (slope=1.000 до k=24) ✓DOK ⭐

### П-54..П-66 — GF(2), биекция
- П-57: **T_RANK5_INVARIANT = 5** абсолютный ✓DOK ⭐
- П-59: **T_INFINITE_TOWER** slope=1 до k=24 ⭐
- П-61: T_GF2_BIJECTION
- П-62-64: ⊘ROLL (freestart артефакты) → П-67

### П-67..П-101 — Wang-chain эпопея ⭐⭐⭐
- П-70: T_FREESTART_E_GF2_NONTRIVIAL
- П-79: T_WORD_SATURATION (63%→94%)
- П-81-92: диагностика, исправление, верификация Wang-chain
- **П-92: T_WANG_CHAIN 1000/1000** ⚡VER
- **П-97: Пара найдена W0=c97624c6** (518s, 12 CPU, 8685M итер.) ⭐⭐⭐
- П-101: \|Sol_17\|≥2⁹⁶ neutral bits Λ=32

### П-102..П-144 — Диффузия, distinguisher
- П-102: T_DIFFUSION_SPECTRAL
- П-106 → П-108: T_DA_ODD_BIAS ⊘ROLL → T_DA_BIAS_ZERO
- П-114: **T_BARRIER_EQUALS_SCHEDULE** ✓DOK
- П-115: T_DE18_UNIFORM ⚡VER
- П-129: T_WANG_IS_SUBTRACTION
- П-142: MILP ~2¹⁴⁴ naive

### П-149..П-226 — Новая математика
- П-210: **MITM O(2⁸⁰)** через state[16] (теория)
- Carry×NLF, OMEGA, BTE Theory
- GPK-моноид, интенсиональная рамка, два мира (M/c)
- ★-Algebra 18 теорем (Dead Zone)
- Мерсенн-декомпозиция, многоблочность
- carry-rank=589/592, η=0.189, τ★=4

### П-966 — strict Ch invariant
- **T_CH_INVARIANT** ✓DOK — Ch[b30,b31]=0 при carry[63]=0 (0/1M)

### П-1000..П-1035 — Distinguisher v6.0
- **AUC=0.980** нейросеть ⚡VER

### П-1300+ — финальная синтез фазы
- Журнал, закрытые направления, 27 файлов

## Линия C: Info-Theory Fingerprinting (IT-1..IT-6)

### IT-1 — Base
- Min-entropy Ĥ_∞ соответствует RO ✓
- Birthday коллизии корректные

### IT-1.1..1.3 — SHARP_FINDINGS ⭐
- χ² на k=8-16: **SHA-2 family z≈-2.5, p<10⁻⁷** под uniform
- MD5 противоположный знак
- **Key insight**: SHA-2 ГИПЕРРАВНОМЕРНЕЕ RO, не утечка

### IT-2 — Attribution
- **σ₀/σ₁ = 88% редукции χ²-bias** ⭐
- K_golden + Σ-compress вторичные

### IT-3 — Delta invariants
- **Δ_χ² vs Δ_I dissociation** ⭐
- marginal ≠ structural

### IT-4 — Adversarial
- 64-feature Walsh, bit5_max z=+3.9 (HW=2)
- IT-4.1: HW=2 exclusive, не чётность ⚡VER 130K exhaustive

### IT-4.Q (Q1-Q3b)
- bit5 уникален, Q3b cherry-pick ✗NEG

### IT-4.Q7-Q7F — Chain-test epiphany
- Q7: 2nd-order Walsh state1 RO-clean ✗NEG
- Q7C: 3rd-order max\|z\| ниже RO
- **Q7D: directional chain-3 z=-3.87 @ R=50** ⭐⭐⭐
- Q7DEF: **R=500 p=0.002 Bonferroni**, Walsh-4 z=-6.40

### IT-4.Surgical S1-S4
- S2: round decay ~2× per 4R, RO к r=20
- S3: **ONLY SHA-256** (cross-hash)
- S4: block-2 амплификация high-order

### IT-5G — Theory
- **Parseval, NP-оптимальность chain-test**
- max\|z\| только для sparse

### IT-5S — Round×Order evolution
- chain_3 затухает медленнее chain_1

### IT-6 — Full-output map
- **ρ(direct, chain_3) = +0.98** ⭐⭐⭐
- Same-sign 240/256 (p~10⁻⁴⁰)
- **Ω_k инвариант** по output битам

## Ключевые кросс-томные моменты

| Дата/фаза | Событие | Значимость |
|---|---|---|
| §4.2 (Session 1) | SHA R=1 1765× | Первый численный win |
| §28 (Session 3) | Аксиомы D1-D5 | Формализация программы |
| §45 (Session 3 ext) | General Discrimination Theorem | Центральная теорема Том I |
| §50-51 | Full circle SHA 646× | Том I → Том II мост |
| §67 | Theorem 7 DISCRIM-DETECT | Exponential speedup SuperBit |
| §114-§123 | Carry phase space + W-atlas | Мост к §127 ANF |
| §132 | ANF early-verify 7.6× | Первый backward shortcut |
| П-26/П-92 | T_WANG_CHAIN P=1.0 | Центральный Том II |
| П-97 | Пара W0=c97624c6 | Практическая реализация |
| IT-4.Q7D | Chain-3 z=-3.87 | Центральная Том III |
| IT-6 | ρ=0.98, Ω_k | Новый инструмент |
