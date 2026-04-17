# Карта верификации UNIFIED_METHODOLOGY

> Назначение: свести все утверждения трёх томов к **проверяемым пунктам** с
> указанием *что именно* нужно проверить, *как* (артефакт/код/доказательство),
> и *текущего состояния* (что уже имеется на диске vs отсутствует).
>
> Легенда столбца «Метод проверки»:
> - **[RUN]** — есть готовый скрипт/бинарь в репо, можно перезапустить
> - **[WRITE]** — код нужно написать по спецификации из текста
> - **[PROOF]** — аналитическое доказательство, сверка математики
> - **[EXT]** — требует внешних данных (криптобиблиотеки, GPU, большой CPU)
> - **[DOC]** — сверить внутренние цитаты/номера (П-N, §N, IT-N)
>
> Легенда столбца «Артефакт»:
> - **✓** — файл/результат присутствует в репо
> - **≈** — частично (исходник есть, данные/логов нет или наоборот)
> - **✗** — нет ни кода, ни данных; только описание в тексте
>
> См. [10_verification_priorities.md](10_verification_priorities.md) — что
> взять первым.

## 0. Общий аудит структуры

| # | Проверка | Метод | Артефакт | Примечание |
|---|---|---|---|---|
| 0.1 | Все `П-N` из текстов unified/ встречаются в `methodology_v20 (5) (1).md` | [DOC] | ≈ | источник в корне |
| 0.2 | Все `§N` из Том I корректно ссылаются на `METHODOLOGY.md` | [DOC] | ≈ | 133 секции |
| 0.3 | Все `IT-N` имеют соответствующий `*_REPORT.md` в `research/min_entropy/` | [DOC] | ✓ | 16 отчётов |
| 0.4 | key_numbers.md согласован с главами (нет разночтений) | [DOC] | ✓ | — |
| 0.5 | program_status.md список ✓DOK / ⊘ROLL совпадает с главами | [DOC] | ✓ | — |
| 0.6 | 05_negatives.md покрывает **все** ✗NEG из глав (~41 обещано) | [DOC] | ✓ | — |
| 0.7 | 08_files_index.md — каждый упомянутый файл реально лежит на диске | [DOC] | ≈ | Vol I/II .c — отсутствуют |

**Системное наблюдение по артефактам**:
- `research/min_entropy/` — **136 файлов** (все IT-эксперименты, JSON + `.c` + `.py` + `*_REPORT.md`). Том III **полностью воспроизводим**.
- `superbit/` — 6 файлов Python. Покрывает только SuperBit-движок (Том I §63-79).
- Вне этих двух папок **нет исходного кода**. Все `.c`/`.py`, упомянутые в Томах I и II (`bit_calculus.c`, `bit_homology_sha.c`, `phase_bits.c`, `ebit_pairs.c`, `reversible_bits.c`, `birthday_search_17.c`, каскад-скрипты, Wang-probe и т.д.), **на диск не вынесены** — существуют только как описание в `METHODOLOGY.md` / `methodology_v20*.md`.
- Следствие: Том III = **[RUN]**, Том I = частично **[WRITE]** (кроме SuperBit), Том II = **[WRITE]** сплошь.

## 1. Том I — Математика бита

### 1.1 Эмпирические speedups / измерения (Фазы A-F)

| Claim | Статус в тексте | Метод | Артефакт | Что именно проверить |
|---|---|---|---|---|
| SHA R=1 HDV-guided inversion **1765×** [§4.2] | ⚡VER 98% | [WRITE] | ✗ | воспроизвести `sha256_invert.c`; 49/50 успехов на 50 инстансах; mean 2.43·10⁶ раундов |
| SHA R=1 pairwise-features **646×** [§51] | ⚡VER | [WRITE] | ✗ | скрипт pairwise features 16-bit |
| SHA R=1 pairwise features **4 323 415×** на 32-bit [§51.5] | ⚡VER | [WRITE] | ✗ | это «главный числовой результат» Тома I — нужна независимая репликация |
| R=2 chain inversion через W_1-first: **0/100** [§4.3] | ✗NEG | [WRITE] | ✗ | подтвердить, что стена реальна (30/30 oracle test pass, 0/100 полный) |
| Walsh max\|F̂\| R=1..8 таблица [§4.4] | ⚡VER | [WRITE] | ✗ | `bit_calculus.c` перезапуск; Parseval проверен до 10⁻⁹ |
| Avalanche R=1 → 1.5%, R=8 → 32.8% | ⚡VER | [WRITE] | ✗ | 50 000 инстансов per R |
| PH + Fiedler R=1..64 [§4.6] | ⚡VER, z=−60.4σ на R=1 | [WRITE] | ✗ | `bit_homology_sha.c`; 30 датасетов × 80 state |
| Tropical BF **187×** vs scipy [§36] | ⚡VER | [WRITE] | ✗ | C-level BF на density=0.9 |
| Tropical numpy **6.25×** — артефакт [§34/§35] | ✗NEG-correction | [WRITE] | ✗ | проверить, что против scipy исчезает |
| Нейробит ball-search **176.5×** [§18] | ⚡VER | [WRITE] | ✗ | воспроизвести stream×cost прототип |
| Phase-нейробит **351×** [§19] | ∆EXP conditional | [WRITE] | ✗ | triple-cell, условные параметры |
| HDC triple-relation memory **100%** [§5.4] | ⚡VER | [WRITE] | ✗ | ebit-pairs bundle 1024 |
| DJ 10⁶ кубитов / 0.9с [§48] | ⚡VER | [WRITE] | ✗ | линейный phase-bit метод |
| MPS DJ/BV n=10⁴ / 11 ms [§44] | ⚡VER | [WRITE] | ✗ | phase-MPS contraction |
| CHSH S>2 на phase-bits [§31] | ⚡VER | [WRITE] | ✗ | Bell-эксперимент классически |

**Все артефакты Тома I (кроме superbit/) — отсутствуют.** Для корректной
верификации нужен шаг 0: **импорт** `.c`/`.py` файлов из исходной
`METHODOLOGY.md` в репо, либо написание их заново по описанию.

### 1.2 Аналитические теоремы

| Claim | Статус | Метод | Примечания к проверке |
|---|---|---|---|
| Аксиомы **D1-D5**, 20/20 осей pass [§28] | ✓DOK | [PROOF] | каждая из 20 осей — отдельный witness; сверить Fredkin/Toffoli conservation, reversible full adder, LFSR x⁷+x⁶+1 период 127 |
| **Plurality Theorem** (нет universal framework) [§29] | ✓DOK (neg) | [PROOF] | доказательство от противного через 13 примитивов |
| **Upper bound N=∞** под D1-D5 [§30.3] | ✓DOK | [PROOF] | пересчитать аргумент, зависимость от силы D1-D5 |
| **General Discrimination Theorem** [§45] | ✓DOK, центральный | [PROOF] | poly(n) для задач с групповой симметрией — просмотреть аргумент |
| **Theorem 7 exp. DISCRIM-DETECT** [§67] | ✓DOK, центральный | [PROOF] | separation oracle — формальная конструкция |
| **Z/m phase hierarchy m^(k-1)** [§46] | ✓DOK | [PROOF] | индукция по k |
| **XOR-fragility theorem** [§42] | ✓DOK | [PROOF] | формулировка: XOR неустойчив в некоторых расширениях |
| **No-cloning для phase-bits** [§5.6 L2] | ✓DOK | [PROOF] | линейность + базис |
| **T_PROB<PHASE** (GHZ± prob-неразличимы) [§6.4] | ✓DOK | [PROOF] | прямая проверка marginals |
| **T_GHZ_DISCRIMINATION** [§5.4] | ✓DOK | [PROOF] | ⟨XXX⟩ через phase |
| **Subsumption phase-bit ≺ path-bit** [§84] | ?OPEN-формализация | [PROOF] | нужен строгий separation через signature |
| **Carry = conjugate momentum** [§114] | Ключевой инсайт | [PROOF] | симплектическая структура; проверить что §115 детализирует, какие части выживают |
| **Diagonal conjugacy universal** [§119-C] | ⚡VER | [WRITE]+[PROOF] | эмпирически на real SHA-256 — нужен тест |
| **W-атлас ΔW ∝ 1/N_ADD** [§123] | ⚡VER | [WRITE] | численная подгонка по семейству |
| **ANF early-verify 7.6×** cumulative [§132/§133] | ⚡VER | [WRITE] | критично: §133 ретрактирует часть §130 — перепроверить, что 7.6× устоял после честной валидации recall |

### 1.3 Отозванные и негативные

| Claim | Статус | Что проверить |
|---|---|---|
| `unified_hierarchy.c` Capstone v1 «6 осей» | ⊘ROLL | что опровержение из §I.3 корректно (5 новых осей действительно добавлены, а не перекрытие) |
| Memristor как primitive [§39] | ✗NEG | провалено D1-D5 — сверить какое именно из D1-D5 не прошло |
| S-bit на QUBO/MAX-SAT [§59] | ✗NEG | бенчмарк против классики |
| Σ-bit супер-примитив [§61] | ✗NEG | не даёт super-poly speedup |
| Scalar МС-координаты (16 кандидатов NULL) [§125] | ✗NEG | проверить все 16 |
| Vector k=32 ALL NULL [§126] | ✗NEG | — |
| Stacked disqualifiers 3-5% marginal [§131] | ✗NEG | — |
| Conservation law SHA-трансформация [§94] | ✗NEG | гипотеза опровергнута на 2R — сверить эксперимент §94.5 |
| Avalanche wall R=1 real SHA [§111] | ✗NEG | не инвертируется координатно |
| p-adic SHA [§4.5] | ✗NEG | mean v_2=0.995 vs теория 1.000 |

### 1.4 Открытые из Тома I

| Вопрос | Приоритет | Зависимость |
|---|---|---|
| Backward shortcut beyond §132 (7.6× потолок) | P1 | требует независимого ortho-shortcut |
| Open 119-C (Φ-inverter fails, но diagonal conj. univ.) | P2 | §120 |
| W-атлас для non-ADD функций [§123] | P3 | — |
| 22+ ось (stochastic resonance, field bits) [§38-39] | P3 | — |
| Path-bit computational separation [§80-84] | P3 | Hopf-формализация |
| Bit-cosmos Platonic multi-axis [§90-93] | P4 | — |
| Upper bound при усилении D1-D5 [§30] | P4 | нужна альтернатива D1-D5 |

## 2. Том II — Дифф. криптоанализ SHA-256

### 2.1 Центральные численные результаты

| Claim | Статус | Метод | Что проверить |
|---|---|---|---|
| **T_CASCADE_MAX**: De3..De16=0 за O(2²²) [П-10] | ✓DOK | [WRITE] | реализовать 13-шаговый каскад ΔW[3..15]; Da13=0x7711498a, ΔW16=0x84752d8e, De17=0xfb867718 |
| **T_DE17_LINEAR**: De17 = Da13 + ΔW16 [П-11/12] | ✓DOK | [PROOF]+[WRITE] | аналитическое разложение + численная проверка |
| **T_CASCADE_17**: 15 нулей за 2³² [П-13] | ✓DOK | [WRITE] | 2²² от 2⁵⁴ за счёт T_DW2_FREEDOM |
| **T_BARRIER_16**: 16 нулей = 2⁶⁴ [П-15] | ✓DOK | [WRITE] | SAT k≤16 <1с, k=17 timeout (T_SAT_CASCADE) |
| **T_WANG_CHAIN**: δe[2..16]=0 с **P=1.0** (1000/1000) [П-26/92] | ⚡VER | [WRITE] | перезапустить чистым адаптивным δW_r; верифицировать ровно 1000 попаданий |
| **T_SC_A1**: 100000/100000 [П-24] | ⚡VER | [WRITE] | δa1=0x8000 ⟺ bit15(a1_n)=0 |
| **T_WANG_ADAPTIVE**: 50000/50000 [П-25] | ⚡VER | [WRITE] | 9206 уникальных δW1 |
| **Wang-pair W0=c97624c6** найдена за 518с/12CPU, 8685M итер [П-97] | ⚡VER | [EXT] | бюджет ≥ 1 час × 12 CPU — ре-поиск; проверить валидность δe[2..17]=0 |
| **\|Sol_17\| ≥ 2⁹⁶** neutral bits Wn[12,13,15] [П-101] | ⚡VER | [WRITE] | перебор всех троек нейтральных слов; 96-bit свобода |
| **Distinguisher v6.0 AUC=0.980** [П-1000..1002] | ⚡VER | [WRITE]+[EXT] | НС на (e[60], g[62], Ch[62], e[62]); требует training pipeline + GPU |
| **T_UNIVERSAL_DISTINGUISHER** Δ_AUC +0.35..+0.64 для r=8..64 [П-1036] | ⚡VER | [WRITE] | адаптивный score |
| **MITM O(2⁸⁰)** через state[16] [П-210] | ∆EXP (теория) | [WRITE] | **ЭТО ОТКРЫТОЕ** — runnable code нет |
| **MILP наивный ~2¹⁴⁴** [П-142] | ∆EXP | [WRITE] | сложность в MILP solver |
| **T_BIRTHDAY_COST17**: 2¹²⁸ optimum [П-27A] | ✓DOK | [PROOF] | 6 независимых анализов — сверить логику |
| **height_2 ≥ 32** (slope=1.000 до k=24, потом k=32) [П-59/П-67B] | ⚡VER | [WRITE] | 200 сидов × 24 уровня |
| **T_INFINITE_TOWER** slope=1.000 до k=24 | ⚡VER | [WRITE] | — |
| **T_RANK5_INVARIANT**: rank_GF2(J_{5×15})=5 абс. инвариант [П-58] | ✓DOK | [WRITE]+[PROOF] | 100 сидов: всегда 5 |
| **T_GF2_BIJECTION**: rank(L_r)=r for r=1..64 [П-61] | ⚡VER | [WRITE] | 30 сидов × 15 r |
| **T_CH_INVARIANT** Ch[b30,b31]=0 при carry[63]=0 (0/1M) [П-966] | ✓DOK | [WRITE] | 10⁶ тестов, 0 нарушений |
| **T_DMIN_97** [П-1143] | ⚡VER | [WRITE] | min расстояние ≥97 |
| **Carry-rank=589/592** [§191] | ✓DOK | [WRITE]+[PROOF] | P(обратимость)=2⁻⁷⁷ |
| **η = 0.189** spectral gap [★-Alg §200] | ⚡VER | [WRITE] | (3·log₂3)/4−1 |
| **T_LYAPUNOV λ=4.0** бит/раунд [П-1105] | ✓DOK | [WRITE] | r=4..60 |
| **T_HADAMARD_JACOBI** [П-1142] | ✓DOK | [WRITE] | Jacobian ≈ Hadamard, чувствительность 15.91..16.08 |
| **T_BARRIER_FUNDAMENTAL** r=17 подтверждён 9 методами [П-167] | ⚡VER | [DOC] | перечислить 9 методов и проверить каждый |

### 2.2 Структурные теоремы

| Claim | Статус | Метод | Примечания |
|---|---|---|---|
| **L2-L7** (распространение δ) | ✓DOK или ⚡VER | [PROOF]+[WRITE] | L4 аналитически, L5 SAT N=2, L6 численно |
| **T★3..T★7** (каскад периода 3) | ✓DOK | [PROOF]+[WRITE] | SAT-времена 28s..626s |
| **T_PERIOD3** структурное объяснение | ✓DOK | [PROOF] | — |
| **T_DEP / T_SCHEDULE_DECOUPLING** (1000/0) [П-9] | ✓DOK + ⚡VER | [PROOF] | De_r зависит только от W[0..r-1] |
| **T_ANF** deg(De_2)=16 по W[0], W[1] | ✓DOK | [WRITE] | полная нелинейность с r=2 |
| **T_ADD8** 8 значений, low8=0x81 (200K) | ⚡VER | [WRITE] | — |
| **T_DCH_EXACT** Ch(e⊕δ,f,g)⊕Ch(e,f,g)=δ&(f⊕g) | ✓DOK | [PROOF] | |
| **T_SCHEDULE_FULL_RANK** 512/512 [П-23] | ✓DOK | [PROOF]+[WRITE] | ker(L)={0} |
| **Теорема K** (однобитовая XOR-коллизия невозможна) [v8] 100K | ✓DOK + ⚡VER | [PROOF] | predict_delta LI |
| **T_CARRY_ANALYTIC** P(δe1=2^k) формула [П-22] | ✓DOK | [PROOF] | для всех чётных k=0..30 |
| **T_WANG_OPTIMALITY** [§155.3.3] | ✓DOK | [PROOF] | Wang-цепь оптимальна в классе |
| **T_UNIVERSAL_76_EXPLAINED** (hw59=76 через CLT) | ⚡VER | [WRITE] | статистический аргумент |
| **T_HW64_INDEPENDENCE** | ✓DOK | [PROOF] | hw64 ~ Bin(256, 0.5) |
| **T_MERSENNE_DECOMPOSITION** (Z/(2³²−1) carry-свободно) | ✓DOK | [PROOF] | 592 бинарных коррекции |
| **Carry×NLF два замка** (Full=0, No carry=0, No NLF=0) [§223] | ✓DOK | [WRITE] | N=500 |
| **T_HW_INVARIANT_0_16_23** (W[16]=W[0] pad=0) | ⚡VER | [PROOF] | аналитически |

### 2.3 Закрытые / отозванные (проверить, что статус корректен)

| Claim | Статус | Что сверить |
|---|---|---|
| T_HENSEL_INAPPLICABLE [П-43/47] | ✗NEG | гладкость k≥2 |
| T_NONLINEAR_MATRIX_FAILS (0/100) [П-44] | ✗NEG | 2D подъём |
| T_BOOMERANG_INFEASIBLE [П-29] | ✗NEG | HW≈64 |
| T_ROTATIONAL_NEGATIVE [П-35] | ✗NEG | E[dH]=128 |
| T_MILP_INFEASIBLE_17 [П-34] | ✗NEG | SAT k=17 timeout |
| T_XOR_DIFFERENTIAL [П-19] | ✗NEG | Maj/Ch ломают XOR |
| T_HYBRID_CASCADE [П-22] | ✗NEG | ADD+XOR несовместны |
| T_2D_BIRTHDAY_NEGATIVE [П-27C] | ✗NEG | 0/20 separability |
| T_MULTIBLOCK_PREDICT (0/3000) [v8] | ✗NEG | через границу блока 0% |
| c-мир прямой P=2⁻⁷⁷ [§214] | ✗NEG | — |
| c-мир прыжки, масштабирование [§215/218] | ✗NEG | exp(-0.45r) decay |
| Послойный Q∩T [§220] | ✗NEG | эквивалентен обратному вычислению |
| **⊘ROLL: T_FREESTART_INFINITE_TOWER** [П-62] | отозвана | DW=0 тривиально |
| **⊘ROLL: T_HEIGHT_SHA256=6** [П-52] | опровергнута | реальный ≥32 |
| **⊘ROLL: T_DA_ODD_BIAS** [П-107→108] | отозвана | → T_DA_BIAS_ZERO |
| **⊘ROLL: T_2CYCLE_ARTIFACT** [П-228] | N=3000 артефакт | N=10K mean=128.01 |
| **⊘ROLL: T_SHA512_SPECTRAL** [§179] | as-attack ⊘ROLL | остаётся как design invariant — критично **не путать** |

### 2.4 Открытые Тома II

| Вопрос | Приоритет | Примечание |
|---|---|---|
| MITM O(2⁸⁰) реализация [П-210] | P1 | **runnable code отсутствует** |
| Wang extension за r=17 | P1 | schedule barrier |
| \|Sol_17\| точная плотность | P2 | ≥2⁹⁶ доказано, точно — нет |
| Q∩T решатель < 2¹²⁸ [§216] | P1 | «единственное перспективное направление» |
| Lifted polynomials замкнутая форма [Подход 6 §II.3] | P3 | — |
| Biham-Chen-style neutral tree [v12+] | P3 | — |
| Closed form T_DA_CHAIN | P3 | сейчас ∆EXP |
| DW⊥ norm advantage ~1500× аналитика [П-88] | P3 | — |

### 2.5 Специальная верификация — Distinguisher v6.0

v6.0 — самый «дорогой» result Тома II, AUC=0.980. Его проверка требует:
1. Полный training dataset (carry[63]=0 примеры + случайные W).
2. Архитектура НС (не описана в unified/, только ссылки на П-1002).
3. Разбор T_CH_INVARIANT, T_BOTTLENECK_R60 как **pre-filter vs classifier** —
   critical caveat: НС **замкнута** для случайных W[0].
4. Сравнение v5.1/v5.2/v6.0 (AUC 0.914 / 0.960 / 0.980).
5. Универсальный score П-1036 (r=8..64) — отдельный прогон.

## 3. Том III — Info-Theory Fingerprinting

### 3.1 Полностью воспроизводимая серия (скрипты в `research/min_entropy/`)

| Claim | Скрипт | Данные | Статус |
|---|---|---|---|
| **IT-1** Ĥ_∞ соответствует RO | `experiment.py` | `results.json` | ✓ reproducible |
| **IT-1.3** χ²-fingerprint SHA-2 z≈−2.5, p<10⁻⁷ | `sharp_analysis.py`, `cross_hash_k12.py` | `sharp_results.json`, `cross_hash_k12_results.json` | ✓ |
| **IT-1.2** replication 5 входных наборов, 5/5 neg | `replication.py` | `replication_results.json` | ✓ |
| **IT-2** σ₀/σ₁ атрибуция **88%** | `sha256_chimera.py` | `chimera_results.json` | ✓ |
| **IT-3** Δ_χ² vs Δ_I dissociation | `it3_estimator.py`, `it3_main.py`, `it3_unification.py` | `it3_results.json`, `it3_unification.json` | ✓ |
| **IT-4** 64-feature Walsh, bit5_max z=+3.9 | `it4_walsh.py`, `it4_targeted.py`, `it4_validate_and_classify.py` | `it4_walsh.json`, `it4_targeted.json`, `it4_validate.json` | ✓ |
| **IT-4.1** HW=2 exclusivity (130K exhaustive) | `it4_1_hw_scan.py`, `it4_2_chimera_attribution.py` | `it4_1_hw_scan.json`, `it4_2_chimera_attr.json` | ✓ |
| **IT-4.Q1** bit5 uniqueness | `it4_q1_bit_specificity.py` | `it4_q1_bit_specificity.json` | ✓ |
| **IT-4.Q2** HW-parity рефутирована | `it4_q2_hw_parity.py` | `it4_q2_hw_parity.json` | ✓ |
| **IT-4.Q3/Q3b** HW=4 cherry-pick ✗NEG | `it4_q3*.py` | `it4_q3*.json` | ✓ |
| **IT-4.Q7** 2-order Walsh RO-clean | `it4_q7_bilinear.py` | `it4_q7_bilinear.json` | ✓ |
| **IT-4.Q7b** reverse-trace \|S\|≥3 | `it4_q7b_reverse_trace.py` | `it4_q7b_reverse_trace.json` | ✓ |
| **IT-4.Q7C** 3-order max\|z\| ✗NEG | `it4_q7c_walsh3.c` + `it4_q7c_wrapper.py` | `it4_q7c_results.json` | ✓ |
| **IT-4.Q7D** chain-3 z=−3.87 R=50, p=0.02 | `it4_q7d_chain3.c` + wrapper | `it4_q7d_results.json` | ✓ |
| **IT-4.Q7D-R500** p=0.002 Bonferroni-3 | `it4_q7d_r500.py` | `it4_q7d_r500_results.json` | ✓ |
| **IT-4.Q7e** cross-target bit 210 | `it4_q7e_crosstarget.py` | `it4_q7e_results.json` | ✓ |
| **IT-4.Q7f** Walsh-4 chain z=−6.40 | `it4_q7f_chain4.c` + wrapper | `it4_q7f_results.json` | ✓ |
| **IT-4.S1** full 256-bit output | `it4_s1_full_output_scan.py` | `it4_s1_full_output.json` | ✓ |
| **IT-4.S2** round decay exp(−0.25r) | `it4_s2_rounds.py` | `it4_s2_rounds.json` | ✓ |
| **IT-4.S3** cross-hash SHA-256 only | `it4_s3_cross_hash.py` | `it4_s3_cross_hash.json` | ✓ |
| **IT-4.S4** block-2 amplification | `it4_s4_block2_amp.py` | `it4_s4_block2.json` | ✓ |
| **IT-5S** round × Walsh-order map | `it5s_round_order_map.py` | `it5s_results.json` | ✓ |
| **IT-6** **Ω_3 = +0.98**, 240/256 same-sign, p~10⁻⁵² | `it6_full_output_map.py` | `it6_full_output_map.json` | ✓ |
| **IT-6b** Ω_k spectrum | `it6b_fast.py`, `it6b_omega_spectrum.py` | `it6b_omega_spectrum.json` | ✓ |
| **IT-6c** cross-feature | `it6c_cross_feature.py` | `it6c_cross_feature.json` | ✓ |
| **IT-7** collision probes (серия) | `it7_*.py`, `it7_*.c` | `it7*.json`, `it7_cumulative_output.csv` | ✓ |
| **IT-8** carry migration, c-world exploit | `it8a..e*.c` | `.c` бинари скомпилированы | ✓ (нужен повторный запуск) |
| **IT-9** full-SHA, end-to-end, twoblock | `it9_*.c` | бинари присутствуют | ✓ |

**Вывод по Тому III**: все ключевые числа (z, p, AUC, Ω_3, 240/256, τ≈1.80,
88%, chain-4 z=−6.40) **напрямую верифицируемы** — перезапустить скрипт +
сверить JSON с числами в `unified/03_vol_III/*.md`.

### 3.2 Теоретические утверждения (требуют [PROOF])

| Claim | Статус | Метод |
|---|---|---|
| **Parseval**: Z_direct = Σ_k Chain_k [IT-5G §2] | ✓DOK | [PROOF] сверка |
| **NP-оптимальность Chain_k** для uniform-dist alternative | ✓DOK | [PROOF] |
| **max\|z\|** NP-оптимальна для sparse | ✓DOK | [PROOF] |
| **Var[Chain_k] ≈ M_k/N** | ⚡VER (match 10%) | [RUN] + [PROOF] |
| Leftover Hash Lemma для SHA-256 | ✓DOK (общ.) + ⚡VER | — |
| **Ω_k = corr_b(direct_z, chain_k)** definition clean | ✓DOK | [PROOF] |
| E[Ω_k \| H_0] аналитика | ?OPEN | [PROOF] |

### 3.3 Закрытое / ограничения

| Claim | Статус | Проверка |
|---|---|---|
| HW-parity bit5 hypothesis | ✗NEG (Q2) | sign-test; IT-4.Q2 данные |
| 2nd-order Walsh state1 | ✗NEG (Q7) | max\|z_2\|=4.41 vs RO 4.31 |
| 3rd-order single-triple distinguisher | ✗NEG (Q7C) | SHA ниже RO |
| max\|z\| для distributed signal | ✗NEG (Q7D/IT-5G) | chain-3 ловит, max\|z\| нет |
| Signal на SHA-1/512 | ✗NEG (S3) | только SHA-256 |
| Round resilience | ✗NEG (S2) | saturation к r=20 |

### 3.4 Открытые Тома III

| Вопрос | Приоритет | Примечание |
|---|---|---|
| **Ω_k для SHA-3/BLAKE** | P1 | `it6_full_output_map.py` готов — нужно подать другой хэш |
| Signal amplification block-2 механизм | P2 | аналитика Σ-функций + Ch/Maj |
| Chain-test vs quantum distinguisher | P3 | √-speedup через amplitude estimation |
| Полный Ω_k(r), k=1..6, r=1..64 | P2 | двумерный spectral fingerprint |
| Q1-Q5 из IT-3 §10 (closed-form связи) | P3 | аналитика |

## 4. Мосты между томами (каждый — отдельная проверка)

| Мост | Проверить |
|---|---|
| **1** — SHA full circle (§4.2 1765× ↔ §51 646×/4.3M×) | воспроизвести оба speedup |
| **2** — ANF saturate за 2R (§127-128 Том I ↔ П-128 Том II) | сверить ANF degrees на общем тесте |
| **3** — schedule sparse ↔ χ²-fingerprint (Том II §56 T_SCHEDULE_SPARSE ↔ IT-2 88%) | сверить 63% vs 88% cohesion |
| **4** — carry phase space (§114, §123 Том I ↔ §122, §191 Том II) | проверить, что «W invariant round function» — одно и то же |
| **5** — backward shortcut (§125-132 Том I ↔ П-210 MITM) | сверить 7.6× / MITM 2⁸⁰ логику |
| **6** — chain-test vs max\|z\| (Том II v6.0 AUC=0.980 ↔ Том III IT-5G) | формально: один — sparse, другой — distributed |
| **7** — Plurality ↔ Task-Specificity | методологический — только [DOC] |
| **8** — Birthday 2¹²⁸ (Том II) ↔ no bit-leak (Том III) | согласованность интерпретаций |

## 5. Приоритеты верификации (рекомендация)

**Этап 1 — немедленно** (низкая стоимость, высокая отдача):
- **5.1** Прогнать **весь Том III** по готовым скриптам; сверить JSON с числами unified/. Ожидаемое время: несколько часов CPU.
- **5.2** [DOC] аудит секции 0 (цитаты, кросс-ссылки, согласованность key_numbers с главами).
- **5.3** Найти/импортировать исходные `.c`/`.py` для Тома I/II из `METHODOLOGY.md`/`methodology_v20*.md` (если эти файлы были, но не добавлены в git) — до начала ре-имплементации.

**Этап 2 — средняя стоимость**:
- **5.4** Ре-имплементировать и проверить **центральные** результаты Тома II: T_CASCADE_MAX (П-10), T_WANG_CHAIN (П-26/92), T_SC_A1, T_RANK5_INVARIANT, T_CH_INVARIANT, T_INFINITE_TOWER.
- **5.5** Проверить **W0=c97624c6** (П-97) — требует ~1 час на 12 CPU; найти пару и сверить δe[2..17]=0.
- **5.6** Ре-имплементация **Тома I Фазы A-F** измерений (1765×, 176.5×, 187×, Walsh max, PH+Fiedler).

**Этап 3 — дорогостоящие**:
- **5.7** Distinguisher v6.0 training pipeline + AUC=0.980 replication (GPU).
- **5.8** MITM O(2⁸⁰) runnable code (известен как открытый).
- **5.9** Ω_k cross-hash для SHA-3/BLAKE/Keccak.

**Этап 4 — [PROOF]**:
- **5.10** Аудит аналитических теорем: General Discrimination Theorem (§45), Theorem 7 (§67), T_BIRTHDAY_COST17, T_COLLISION_LOWER_BOUND_128, Parseval identity для chain-test, Carry-rank=589/592 аргумент, T_MERSENNE_DECOMPOSITION.
- **5.11** Особо внимательно: **§133 validation** — §130 был optimistic; убедиться, что 7.6× реально устоял.

## 6. Красные флаги (на что обратить внимание)

1. **Vol I/II код отсутствует в репо** — либо импортировать, либо готовиться писать ~100 скриптов/бинарей заново.
2. **§130 → §133 ретракция**: в key_numbers.md стоит «7.6× ⚡VER (после коррекции §133)» — сверить, что действительно после коррекции, а не до.
3. **T_SHA512_SPECTRAL** в двух статусах: ⊘ROLL как attack, но остаётся как design invariant. Легко спутать.
4. **AUC=0.980** — в описании caveat «НЕ применима как pre-filter для случайных W[0]» (замкнутость). Проверить, не используется ли где-то без этого caveat.
5. **height_2**: цифры «6» ⊘ROLL → «≥11» → «≥24» → «≥32» по разным местам в тексте. Убедиться, что key_numbers и главы согласованы на «≥32 (финал)» или что ≥11 и ≥24 — промежуточные вехи.
6. **IT-6 ρ=+0.98**: самый сильный сигнал всей программы (p~10⁻⁵²). Независимая репликация на других random seeds для RO null обязательна.
7. **Wang-pair W0=c97624c6**: единичный инстанс. Желательно найти вторую пару независимо, чтобы подтвердить, что T_WANG_CHAIN выход — не артефакт seed.
8. **IT-4.1 HW=4 cherry-pick** (z=+2.82) — уже отозван в Q3b. Проверить, что этот негативный результат корректно маркирован в 05_negatives.md и не всплывает как positive в других местах.

## 7. Статистика программы для верификации

| Категория | Число утверждений | Из них имеет код | Требует [WRITE] | Требует [PROOF] |
|---|---|---|---|---|
| Том I ⚡VER/∆EXP | ~20 | 1 (SuperBit) | ~19 | ~0 |
| Том I ✓DOK | ~15 | — | — | ~15 |
| Том II ⚡VER | ~40 | 0 | ~40 | ~20 |
| Том II ✓DOK | ~40 | 0 | ~10 | ~40 |
| Том III ⚡VER/✓DOK | ~30 | ~30 | 0 | ~8 |
| ✗NEG (все тома) | ~41 | частично | ~15 | ~5 |
| ⊘ROLL (все тома) | ~15 | — | ~5 (перепроверить) | ~5 |
| ?OPEN (все тома) | ~24 | — | — | — |

**Итого** ~200 утверждений — ~30 воспроизводимы сразу (Том III), остальные
требуют либо кода, либо аудита доказательств.

