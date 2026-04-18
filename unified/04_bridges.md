# Мосты между томами

Точки, где тома I/II/III встречаются, подкрепляют или опровергают друг друга. Явные ⇒BRIDGE отсылки для AI-понимания.

## Мост 1: SHA full circle (Том I § ↔ Том II)

**Контекст**: Phase-bits теория (Том I §5, §45) применена обратно к SHA-256 R=1 inversion (Том I §4).

- §4.2 (Том I): HDV-guided inversion **1765×** speedup — начальный win без теории
- §45 (Том I): General Discrimination Theorem — теоретическое обоснование
- §50-51 (Том I): **Full circle** — pairwise features = скрытые W-биты, **646×** speedup (2.1× над Hamming)
- **Параллель с Том II**: T_CASCADE_MAX даёт 14/15 нулей за O(2²²) через дифф. каскад [П-10]

**Общее**: оба тома находят структурные shortcut'ы, но разными методами:
- Том I: спектральный (Walsh / phase discrimination)
- Том II: дифференциальный (XOR/additive cascade)

**Следствие**: два независимых direct'ных pathway к R=1 инверсии. Они НЕ конфликтуют, описывают разные симметрии.

## Мост 2: ANF и composition barriers

**Контекст**: ANF degree после композиции раундов.

- **§114-A (Том I)**: предсказание degree роста через ANF
- **§127 (Том I)**: ⇒BRIDGE **эмпирическое подтверждение §114-A** — degrees точно по теории
- **§128 (Том I)**: shortcut окно = **единственный раунд** (composition saturate за 2R)
- **П-128 (Том II)**: саму ту же **ANF composition saturate за 2R** ⚡VER
- **Том III IT-4.Q7**: state1 после 64R имеет **только \|S\|≥3** корреляции — согласуется с high-order saturation

**Единый вывод**: ANF-degree saturate за 2 раунда, после этого информация входа — ТОЛЬКО в high-order Walsh спектре. Это закрывает линейные и low-order атаки на r≥2.

## Мост 3: Schedule structure и χ²-fingerprint

**Контекст**: почему SHA-2 семья ≠ random oracle.

- **Том II §56/T_SCHEDULE_SPARSE**: 63% нулей в schedule при HW=2
- **Том III IT-2**: ⇒BRIDGE **σ₀/σ₁ = 88%** редукции χ²-bias (main contributor)
- **Том III IT-1.3**: SHA-2 z ≈ -2.5, p<10⁻⁷ — результат schedule sparsity
- **Том I §104 (ADD mod 2^L через Walsh)**: объясняет нелинейный характер

**Единый вывод**: **schedule σ₀/σ₁ — источник hyperuniformity SHA-2 family**. Это design artefact, не weakness. Cross-hash тест IT-4.S3 подтверждает: эффект ТОЛЬКО в SHA-2 family.

## Мост 4: Carry phase space и W-invariants

**Контекст**: carry как conjugate momentum.

- **Том I §114**: carry = conjugate momentum (симплектическая структура)
- **Том I §119-C**: **diagonal conjugacy universal** на real SHA ⚡VER
- **Том I §123**: **W-атлас ΔW ∝ 1/N_ADD** — универсальный закон
- **Том II §122**: **W — invariant round function, не данных** — тот же факт с другой стороны
- **Том II carry-rank=589/592** (§191): фиксированная структурная инвариантность

**Единый вывод**: W-функция — свойство ADD-операций раунда, не данных. Это глубокий структурный инвариант, объясняющий устойчивость SHA.

## Мост 5: Max-speed principle и backward shortcut

**Контекст**: можно ли найти shortcut в обратную сторону.

- **Том I §124**: Принцип Макро-Скорости (MC)
- **Том I §125**: Scalar МС-координаты ✗NEG (ВСЕ 16 NULL — avalanche complete за 1R)
- **Том I §126**: Vector k=32 ✗NEG (ВСЕ NULL, методологическое открытие)
- **Том I §127**: ANF эмпирический win — first real shortcut
- **Том I §130**: Φ-disqualifier (validation §133: реально скромнее)
- **Том I §132**: **ANF early-verify 7.6×** — первый подтверждённый ortho-shortcut ⚡VER
- **Том II П-210**: MITM O(2⁸⁰) через state[16] — теоретический шаблон
- **Том II §174 Oracle Distance 2⁻²⁶**: множитель на коллизию — ⇒BRIDGE с Δ_χ² Том III

**Единый вывод**: backward shortcut существует ТОЛЬКО через ANF early-verify (подтверждён). Все остальные кандидаты NULL либо marginal. Это сужает пространство атак.

## Мост 6: Chain-test vs max|z| distinguishers

**Контекст**: что лучше работает против SHA.

- **Том II П-1000-1035**: Distinguisher v6.0 нейросеть, AUC=**0.980** (лучший на тот момент)
- **Том III IT-5G**: **max\|z\| линейный = недостаточен** для распределённых сигналов ✗NEG
- **Том III IT-5G**: **directional chain-test = NP-optimal** для distributed (Parseval)
- **Том III IT-4.Q7D**: chain-3 z=-3.87 на R=50 — невидим для max\|z\|
- ~~**Том III IT-6**: ρ(direct, chain_3)=+0.98~~ ⊘ROLL [Phase 8C audit, UNIFIED §III.7]: RO=+0.978 same protocol, chi_arr artifact

**Единый вывод**: нейросеть (Том II) и chain-test (Том III) — комплементарные инструменты. Chain-test даёт теоретическую гарантию (NP-оптимальность), нейросеть — эмпирический максимум. Комбинация может дать новый фронтир.

## Мост 7: Plurality и Task-Specificity

**Контекст**: нет универсального решения.

- **Том I §29 (Plurality Theorem)**: нет universal framework для 13+ primitives ✗NEG
- **Том I §49 (Task-Specificity Conjecture)**: оптимум = задача-специфичен
- **Том II**: для SHA-256 — **дифференциальная атака** оптимальна (Wang-chain)
- **Том III**: для fingerprinting — **info-theoretic distinguisher** оптимальна (Ω_k)
- **Том I §5**: для discrimination — **phase-bits** оптимальны (Theorem 7)

**Единый вывод**: **подтверждение Task-Specificity**. Три разных тома = три разных оптимальных tool chain под три разные задачи. Никакой silver bullet.

## Мост 8: Birthday и reality check

**Контекст**: нельзя нарушить birthday bound.

- **Том II T_BIRTHDAY_COST17** ✓DOK: оптимум **2¹²⁸** для 256-битного выхода
- **Том II T_STATE17** ⚡VER: state bound 2⁸⁰ via middle meeting
- **Том I**: никакой из 20 осей не даёт collision shortcut против SHA-256
- **Том III**: нет доказательств бит-leakage, только hyperuniformity

**Единый вывод**: **программа НЕ сломала SHA-256**. Достигнуто понимание структуры, distinguishers, shortcuts на R=1-2. Collision остаётся birthday-hard на full 64R.

## Схема мостов (matrix)

|   | Том I | Том II | Том III |
|---|---|---|---|
| **Том I** | — | Мост 1,2,4,5 | Мост 2,6 |
| **Том II** | Мост 1,2,4,5 | — | Мост 3,6,8 |
| **Том III** | Мост 2,6 | Мост 3,6,8 | — |

**Плотность**: наибольшая связь Том I ↔ Том II (5 мостов). Том III — более изолирован (методология), но служит «опровержителем» (chain-test > max|z|) и «подтвердителем» (schedule-sparsity).

## Ключевое наблюдение для AI

**Три тома — НЕ дубли, а ортогональные срезы одного объекта (SHA-256)**:
- Том I: **что может быть битом** (structure)
- Том II: **как ломать** (attack)
- Том III: **чем распознавать** (fingerprint)

Any AI session продолжая работу должна помнить: переход между томами = переход между paradigm'ами, и одна и та же сущность (например, ANF) появляется везде, но с разным акцентом.
