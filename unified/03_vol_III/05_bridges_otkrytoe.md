# Глава III.5. Bridges и Открытые вопросы

> TL;DR: ИТ-результаты Том III связываются с Томами I и II через 6
> мостов: σ₀/σ₁→T_SCHEDULE_SPARSE, round decay→T_INFO_BARRIER_R1,
> Δ_χ²→Oracle Distance, high-order→ANF degree barrier, chain-test→
> max|z| distinguisher, Ω_k→новый design-tool. 4 закрытых ✗NEG, 4
> открытых ?OPEN.

## §III.5.1 BRIDGE-1: σ₀/σ₁ ↔ T_SCHEDULE_SPARSE

**Том II §56 T_SCHEDULE_SPARSE** ✓DOK: при HW=2 расписание SHA-256
содержит **63% нулей** в W[0..15]→W[16..63] expansion.

**Том III §III.2.3 IT-2 attribution** ✓DOK: **σ₀, σ₁ → identity** даёт
**88% reduction** χ²-bias на (HW=2, k=12): z=−2.52 → −0.30.

**Связь** ⚡VER: T_SCHEDULE_SPARSE объясняет, ПОЧЕМУ σ-функции message
schedule — главный носитель χ²-fingerprint. При HW=2 schedule сильно
зависит именно от структуры σ-функций (sparse W ⇒ output жёстко
коррелирован с σ-rotations).

**Новое Том III**: схема T_SCHEDULE_SPARSE имеет **измеримый ИТ-эффект**
(χ²-deviation z=−2.52 на k=12), не только структурное свойство.

## §III.5.2 BRIDGE-2: round decay ↔ T_INFO_BARRIER_R1

**Том II §106 T_INFO_BARRIER_R1** ✓DOK: MI(W; e_r) — взаимная информация
между message word и e_r — падает за 1 раунд. Конкретно MI(W;e_1)=2.5 бит.

**Том III §III.4.2 IT-4.S2** ⚡VER: round-by-round emergence:
- r=4: max|z|=22.67, **~2.9 бит MI** (ИДЕНТИЧНО v20 §106 предсказанию).
- Затухание max|z| ∝ exp(−0.25r).
- К r=20: чистый RO.

**Связь** ✓DOK: единое явление с двух сторон. v20 §106 — Shannon-метрика
на ранних раундах. IT-4.S2 — Walsh-метрика на полном эволюционном профиле
4..64. Численное согласование при r=4 (2.9 vs 2.5 бит) — within 0.5 бит,
очень тесно.

**Новое Том III**: λ ≈ 0.25/round экспоненциальная скорость + r≈20
saturation point. v20 §106 не давало эту динамику явно.

## §III.5.3 BRIDGE-3: Δ_χ² ↔ Oracle Distance 2⁻²⁶

**Том II §174 §6 Oracle Distance** ✓DOK: мультипликативный коэффициент
2⁻²⁶ — единственный измеримый эффект carry-структуры на стоимость
коллизии (RO equivalent up to factor).

**Том III §III.2.4 IT-3 Δ_χ²** ⚡VER: Δ_χ²(SHA-256, low_HW=2, k=12) =
−2.5σ ⇒ marginal-uniformity excess в **bit-level метрике**.

**Связь** ⚡VER: оба измеряют **distance от RO**, но в разных метриках:
- v20 §174: коэффициент в стоимости (мультипликативный, на cost).
- IT-3: bit-метрика на проекции выхода (аддитивная, на distribution).

**Новая интерпретация**: Oracle Distance имеет **bit-level аналог** в
χ²-метрике. SHA-256 — гиперравномернее RO ⇒ Oracle Distance работает
"в пользу защиты" (адверсарий, использующий RO, переоценит cost).

## §III.5.4 BRIDGE-4: high-order Walsh ↔ ANF degree barrier

**Том II §128 ANF degree barrier** ✓DOK: алгебраическая нормальная форма
выхода r-round SHA-256 имеет монотонно растущую степень; полная диффузия
ANF degree → 256 при r ≥ ~16.

**Том III §III.3.5-III.3.7 IT-4.Q7-line** ⚡VER:
- 1st, 2nd, 3rd order Walsh state1 = RO-clean.
- Сигнал концентрируется в **|S|≥3** Walsh subspace (chain-3 z=−3.83).
- Сигнал растёт с порядком (chain-4 z=−6.40).

**Связь** ⚡VER: ANF degree barrier (компонентно-алгебраическая) даёт тот
же эффект, что Walsh high-order migration (спектрально-аналитическая):
информация **уезжает в высокие порядки** через раунды. Два независимых
способа измерить одно явление.

**Новое Том III**: количественно — chain-k vs r (IT-5S §6) даёт
квантитативное измерение скорости миграции по порядкам Walsh.

## §III.5.5 BRIDGE-5: chain-test ↔ max|z| distinguisher v6.0

**Том II П-1000 max|z| distinguisher v6.0** ✓DOK: classical linear
cryptanalysis tool, ищет single-feature `S*` с максимальным |z_S|, с
Bonferroni поправкой.

**Том III §III.1.5 + III.4.5 IT-5G NP-теорема** ✓DOK:
- max|z| = NP-optimal для **sparse** alternative.
- Chain_k = NP-optimal для **uniform-distributed** alternative.

**Связь** ✓DOK: Chain_k — **минимальное необходимое расширение** linear
cryptanalysis на distributed-coherent сигналы. v6.0 = частный случай
(sparse limit). Том III формализует **где v6.0 неприменим** и **когда
обязательно chain-test**.

**Иллюстрация на наших данных**:
| Tool | (HW=2, bit5_max) signal | Detection |
|---|---|---|
| max|z| (v6.0-style) Walsh-3 | max|z|=4.90, RO=5.21 | ✗NEG |
| Chain_3 (новое) | z_norm=−3.87 | ✓DOK |

## §III.5.6 BRIDGE-6: Ω_k ↔ Новый метод design-анализа хэшей

**Существующие методы** [crypto literature]:
- Differential cryptanalysis: смотрит конкретные input differences.
- Linear cryptanalysis: ищет конкретные linear approximations.
- Algebraic attacks: ANF degree, low-degree representations.

**Том III §III.4.7-III.4.8 Ω_k** ✓DOK: **integral spectral invariant**
для пары (хэш, input feature). Измеряет **k-доминантность** Walsh-спектра
round-функции. Не зависит от выбора S или output bit — суммирует по
всему output space.

**Новое Том III**: Ω_k — первый **purely-spectral integral invariant**,
который:
1. Имеет clean ИТ-интерпретацию (через Parseval).
2. Численно вычислим в 13.5 min на CPU для k=3.
3. Даёт astronomical detection (p~10⁻⁵²) на сигналах, невидимых
   classical bit-by-bit Bonferroni (p>0.05).

**Применение к design-анализу**:
- Compute Ω_k(h, f) для variants хэша → identify, какой компонент даёт
  k-доминантность.
- Compute Ω_k для разных k → spectral profile дизайна.
- Compute Ω_k для разных hash families → distinguishing fingerprint.

## §III.5.7 Сводка закрытых ✗NEG

✗NEG-1 [Q-rep §Q2]: **bit5_max как HW-parity hypothesis** — рефутирована.
HW={2,3,4,5,6,7,8} даёт mean z=−0.29 для всех HW≠2; Mann-Whitney even>odd
p=0.20. Сигнал ЭКСКЛЮЗИВНО HW=2.

✗NEG-2 [Q7 §2]: **2nd-order Walsh на state1 несёт сигнал** — RO-clean.
max|z_2|=4.41, RO=4.31±0.29, z_norm=+0.34. Top-30 пар не кластеризуются.

✗NEG-3 [Q7C §2]: **3rd-order single-triple distinguisher** — RO-clean.
max|z|=4.90, RO=5.21±0.23, z_norm=−1.37 (даже ниже среднего). n_above_5=0
(H_0 ожидает 1.6).

✗NEG-4 [Q7D §5, IT-5G §3]: **linear max|z| для distributed signal** —
strictly dominated chain-test. На (HW=2, bit5_max, state1, |S|=3): max|z|
видит NOTHING, chain_3 видит p=0.002 после R=500.

## §III.5.8 Открытые вопросы Том III

~~?OPEN-A [IT-6 §11]: **Ω_k для других хэш-семейств**.~~ ⊘ROLL [Phase 8C
audit, UNIFIED §III.7]: IT-6 foundation claim artifact. Cross-hash extension
of artifact даст те же artifact values. Направление dead-end, требует
new probe (не chi_arr-from-state1).

?OPEN-B [SURG §S4]: **Signal amplification mechanism в block-2**.
Точный алгебраический механизм, как block-2 compression «читает»
high-order Walsh структуру state1 и конвертирует в 1st-order. Требует
analytical decomposition Σ-функций + Ch/Maj.

?OPEN-C [IT-5G §9]: **Chain-test vs quantum distinguisher**.
Quantum amplitude estimation может дать √-speedup для Chain_k computation.
Связь с QFT? Применение к post-quantum hash analysis. См. GUIDE §8.1
quantum information theory.

?OPEN-D [IT-6 §11, IT-5S §6]: **Полный спектр Ω_k(r)**.
Measure Ω_k for k=1..6 через все r=1..64. Если Ω_k(r)/Ω_{k-1}(r) растёт
с k и убывает с r, это даст **двумерный spectral fingerprint** дизайна
SHA-256.

## §III.5.9 Глобальная сводка статусов

✓DOK 12: birthday formula, IT-1.3 family-fingerprint, IT-2 attribution,
IT-3 dissociation, IT-4 Q7-line completeness, IT-4.S2 round decay, IT-4.S3
SHA-256 specificity, IT-4.S4 block-2 mechanism, IT-5G NP-optimality,
IT-5S phase transition, ~~IT-6 Ω_3=0.98 (p~10⁻⁵²)~~ ⊘ROLL [UNIFIED §III.7], 6 bridges с T-I/II.

⚡VER 8: Ĥ_∞ formula, χ² hyper-uniformity, σ/Σ chimera reduction,
HW-exclusivity, chain-3 R=500 amplification, chain-4 z=-6.40,
round×order map, Ω_k cross-bit correlation.

∆EXP 0.

✗NEG 4: HW-parity, 2nd-order single-pair, 3rd-order single-triple,
max|z| на distributed.

?OPEN 4: Ω_k для SHA-3/BLAKE, block-2 algebraic mechanism, quantum
chain-test, full Ω_k(r) spectrum.

## §III.5.10 Cross-references по главам

| Тема | Гл. III.1 | III.2 | III.3 | III.4 | III.5 |
|---|---|---|---|---|---|
| Min-entropy framework | §1.1-1.2 | §2.1 | | | |
| χ² fingerprint | §1.3 (Δ_χ²) | §2.2-2.3 | | | §5.3 (BRIDGE-3) |
| Component attribution | | §2.3 | §3.2 | | §5.1 (BRIDGE-1) |
| Δ_I dissociation | §1.3 | §2.4 | §3.1 (bound) | | |
| Walsh scan | | | §3.1-3.5 | §4.1-4.4 | §5.4 (BRIDGE-4) |
| Chain-test theory | §1.4-1.5 | | §3.6-3.7 | §4.5 | §5.5 (BRIDGE-5) |
| Round decay | | | | §4.2, §4.6 | §5.2 (BRIDGE-2) |
| Ω_k invariant | §1.3 | | | §4.7-4.8 | §5.6 (BRIDGE-6) |
