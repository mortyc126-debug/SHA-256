# Глава II.9. Практические атаки, Distinguisher v6.0, Bridge-framework

> TL;DR: Chosen-prefix distinguisher (§113), Commit-hiding / Key-bias / Chain-dead (§114), HMAC/Merkle/ECDSA (§115-116), Distinguisher v6.0 φ=+0.414, Z=26.2 (§132). Bridge через barrier (§110-112) верифицирован. Cycle dynamics (§72-78) — T_BARRIER_FUNDAMENTAL подтверждён 9 методами.

## §II.9.1 Φ-Manifold и мостик (§107, §110-112)

**T_PHI_MANIFOLD_6D** ⚡VER [П-362]: **6 свободных раундов** {1, 4, 9, 10, 19, 21} — координаты Φ-multifold.

**T_PHI_CRYPTOGRAPHIC_BALANCE** ⚡VER [П-378]: балансные точки Φ-manifold.

**T_PHI_ATTRACTOR** ⚡VER: Φ-prior сходится к attractor через ≤ 5 раундов.

**T_PHI_XOR_INVARIANT** ⚡VER: Φ-инвариант под XOR-сдвигами.

**T_DOUBLE_BARRIER** ⚡VER: двойной барьер r=17 + r=21 (связь с Φ-manifold).

**T_C62_BRIDGE** ★★★★★ ⚡VER [П-415]: мостик через барьер r=17 построен через carry-62.

**T_STATESUM** ⚡VER [П-436]: state-sum вариант bridge.

**T_HC_ACCEL** ⚡VER: hash-constraint акселерация bridge.

**T_META_PHI** ⚡VER: мета-уровневая Φ-инвариантность.

**T_BRIDGE_CONFIRMED** ★★★★★ ⚡VER [П-456]: мостик **независимо верифицирован** на новых инстансах.

## §II.9.2 Distinguisher v6.0 и эволюция (§113, §126-132)

**T_DISTINGUISHER_FULL** ★★★★★ ⚡VER [П-466-473]: chosen-prefix distinguisher на R=16 с практическим оракулом.

**T_FINAL_DISTINGUISHER** ★★★★★ ⚡VER [П-724]: distinguisher v2.0.

**T_H6_STRONGER** ⚡VER [П-722]: усиленный H[6]-pattern.

**T_ENS_SPEED** ⚡VER [П-725]: ансамблевое ускорение.

**T_CARRY_PATTERN_DUAL** ⚡VER [П-782]: двойственная carry-структура.

**T_CLASSIFIER_V4** ★★★★★ ⚡VER [П-784]: classifier v4.0.

**Distinguisher v4.1** ⚡VER [П-811..П-840]: финал цепочки v4.

**Distinguisher v6.0** ⚡VER [П-1000..П-1035, §132]:
- **AUC = 0.980** (нейросеть, ранее указано).
- **φ = +0.414** — положительный correlation bias относительно RO.
- **Z = 26.2** (σ-статистика) на полный стек.
- Квадратичная математика фичей.

**T_H6_B31** ⚡VER [П-751]: паттерн H[6] bit 31.
**T_H6_PATTERN_4** ⚡VER: 4-битовый паттерн H[6].
**T_CHAIN_Q93** ⚡VER: chain через quadratic Q93.

## §II.9.3 Практические атаки на SHA-производные (§114-116)

**T_COMMIT_HIDING** ★★★★★ ⚡VER [П-482]: hiding-свойство commitment schemes **ломается** для reduced-round SHA-256 (R ≤ 16).

**T_KEY_BIAS** ⚡VER: key-bias attack в scenarios с weak-нонс.

**T_CHAIN_DEAD** ⚡VER [П-490]: определённые chain'ы dead (не достижимы) — исключают варианты hash-based signature schemes.

**T_POW_NEGATIVE** ✗NEG: Proof-of-Work атака не масштабируется (отрицательный результат на реальном SHA-256).

**T_MERKLE_HC** ⚡VER [П-502]: Merkle-tree hash-compression — частичная коллизия с hcollision-преимуществом.

**T_HMAC_OUTER** ⚡VER [П-505]: HMAC outer-compression attack — slip ключа при reduced-R.

**T_ECDSA_LEAK** ⚡VER [П-510]: ECDSA nonce leak через RNG bias.

**T_HNP_BOUND** ⚡VER [П-512]: Hidden Number Problem bound — нижняя оценка объёма известных бит для recovery ключа.

## §II.9.4 Carry-окна и backward (§105, §117, §120-122)

**T_CARRY_WINDOWS** ⚡VER [П-236]: 5 carry-окон с P > 0.15.
**T_CARRY_PAIRS** ⚡VER: 30.8% нулей парами в carry-structure.
**T_CARRY_CASCADE** ⚡VER [П-254]: caskad carry-windows.
**T_PHI_DECAY_FORMULA** ⚡VER [П-260]: точная формула decay Φ.
**T_CARRY_SUM_48** ★ РЕКОРД ⚡VER [П-296]: sum-over-carry достиг **2⁴⁸ barrier**.
**T_BARRIER_48** ⚡VER [П-297]: подтверждение 2⁴⁸ как threshold.
**T_INFO_BARRIER_R1** ★★★★ ⚡VER [П-336]: информационный барьер на R1, MI(W;e₁)=2.5 бит (⇒BRIDGE с Том III IT-4.S2).

**T_CARRY_MAP** ⚡VER [П-530]: map between carry-spaces.
**T_OUTPUT_BARRIER** ⚡VER [П-531]: output barrier structured.
**T_PARTIAL_COLLISION_BOUND** ⚡VER [П-532]: lower bound на partial collision work.

**T_BACKWARD_EXACT** ⚡VER [П-571]: exact backward analytical step.
**T_H7_DIRECT** ⚡VER [П-572]: direct H[7] inference.

**T_MITM_IMPOSSIBLE** ★★★★★ ⚡VER [П-591]: naive MITM невозможен (state[16] bottleneck) — объясняет почему требуется O(2⁸⁰) архитектура, не O(2⁴⁰).

**T_PHI_INTRINSIC** ⚡VER: Φ-свойство свойство схемы, не инстанса.
**T_SCHEDULE_COUPLING** ⚡VER [П-592]: schedule coupling анализ.

## §II.9.5 Cycle dynamics (§72-78) ⭐

**T_CYCLE_ANOMALY** ⚡VER [П-144]: аномалии cycle-структуры.
**T_CYCLE_INVERSION** ⚡VER: инверсия cycle возможна в reduced-R.
**T_PROJECTION_DEGENERATION** ⚡VER: degeneration projection.
**T_REAL_PADDING_ANOMALY** ⚡VER: real padding создаёт anomaly.
**T_ZERO_SCHEDULE_MECHANISM** ⚡VER: zero-schedule mechanism.
**T_CHOSEN_PREFIX_32** ⚡VER [П-159]: chosen-prefix на 32-bit.
**T_GROVER_CATALOG** ∆EXP (квантовая): каталог Grover-atomic операций.
**T_ALGEBRAIC_ROUNDS** ⚡VER: алгебраические раунды.
**T_BRIDGE_CONSTRUCTION** ⚡VER: конструктивный bridge.

**T_BARRIER_FUNDAMENTAL** ★★★★★ ⚡VER [П-167]: **r=17 barrier подтверждён 9 независимыми методами** — фундаментальная стена SHA-256.

**T_NO_RESONANT_DELTA** ⚡VER [П-168]: нет резонансных δ за r=17.
**T_G64_ANOMALY** ⚡VER [П-169]: g64 anomaly.
**T_G64_CHOSEN_PREFIX** ⚡VER [П-170]: chosen-prefix через g64.

## §II.9.6 HW-инварианты и chain-асимметрия (§108-109)

**T_HW_INVARIANT_0_16_23** ★★★★★ ⚡VER [П-396-397]: **HW-инвариант** W[16]=W[0] при pad=0 (аналитически доказан).

**T_HW_INVARIANTS_MAP** ⚡VER: карта HW-инвариантов по раундам.
**T_CHAIN_INDEPENDENCE** ⚡VER: chain-независимость определённых позиций.
**T_HW_BARRIER** ⚡VER: HW-барьер (связан с r=17).
**T_PARITY_INVARIANT** ⚡VER: parity-инвариант.

## §II.9.7 WCC и геометрия мостика (§119, §151-152)

**T_PHASE_SHARP** ⚡VER [§151]: острая phase-граница.
**T_PHI_STRONG** ⚡VER: strong Φ-bound.
**T_LAG_15_DOM** ⚡VER: lag-15 доминирует.
**T_RANK_24** ★ ⚡VER: **rank 24 (WCC = Wang Carry Code)** — основной результат серии XIV.
**T_GROUP_SCHEDULE** ⚡VER: group-structure schedule.
**T_CARRY0_ZERO** ⚡VER: carry[0]=0 соблюдается.
**T_CARRY_BIAS** ⚡VER: bias в carry-dynamics.

**T_RANK_PROGRESSION** ⚡VER [§152]: прогрессия rank по раундам.
**T_CONSTRAINT_EXPLOSION** ⚡VER: exploзия ограничений при r→17.
**T_WCC_FAMILIES** ⚡VER: семейства WCC-кодов.
**T_JACOBIAN_FULL** ⚡VER: full-rank Jacobian в WCC.
**T_WCC_SA_MIXED** ⚡VER (60M итераций): mixed simulated annealing на WCC.

**T_ISOLATED_WELLS** ⚡VER [П-564]: изолированные потенциальные wells.
**T_BIAS_STABLE2** ⚡VER: stable bias второго порядка.
**T_CORR_GEOMETRY** ⚡VER: correlation geometry.
**T_HW_CARRY_BIAS** ⚡VER: HW-carry bias.

## §II.9.8 Landscape and birthday artefacts (§131, §153)

**T_LANDSCAPE_SYMMETRY** ⚡VER [П-872]: симметрия landscape.
**T_BIRTHDAY_ARTIFACT** ★★★★★ ⚡VER [П-881]: **ключевое опровержение** — многие "анти-SHA" наблюдения оказались birthday-артефактами.
**T_HW_ASYMMETRY** ⚡VER: HW-асимметрия.

**T_DSC_UNIQUE** ⚡VER [§153]: уникальность DSC-decomposition.
**T_DSC_LEVELS** ⚡VER: уровни DSC.
**T_WANG_BARRIER** ⚡VER (hw59 ≈ 76): Wang-барьер на hw59.
**T_RANDOM_DW** ⚡VER (hw59 ≈ 79): random DW baseline.

## Cross-refs

- §II.9.1 bridge ↔ §II.3 barrier r=17 (мост через стену)
- §II.9.2 Distinguisher v6.0 ↔ Том III IT-5G (chain-test комплементарен)
- §II.9.3 ECDSA leak ↔ внешние приложения SHA-256
- §II.9.4 T_INFO_BARRIER_R1 ↔ Том III IT-4.S2 round decay
- §II.9.5 T_BARRIER_FUNDAMENTAL ↔ Том I §111 avalanche wall
- §II.9.7 WCC rank=24 ↔ §II.5 T_RANK5_INVARIANT (другой context)
