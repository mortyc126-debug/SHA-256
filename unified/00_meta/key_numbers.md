# Ключевые числа программы

Снимок всех численных результатов трёх томов. Сортировка по tome + степени убеждённости.

## Том I — Математика бита (METHODOLOGY.md)

| Результат | Значение | Статус | Источник |
|---|---|---|---|
| R=1 HDV-guided inversion SHA-256 | **1765×** speedup (2.43×10⁶ vs 4.29×10⁹) | ⚡VER (98% success) | §4.2 |
| R=1 pairwise-features inversion | **646×** (2.1× над Hamming) | ⚡VER | §51 |
| Tropical Bellman-Ford vs scipy | **187×** (C-level, dense graph) | ⚡VER | §36 |
| Phase-нейробит гибридный | **351×** speedup | ∆EXP (conditional) | §19 |
| Нейробит ball-search | **176.5×** end-to-end | ⚡VER | §18 |
| Tropical numpy (слабый baseline) | 6.25× | ✗NEG (python artifact) | §34→§35 correction |
| Fiedler ratio (HDV cluster detection) | **30.57×** (λ₁=0.617 vs 0.020) | ⚡VER | §3.7 |
| CHSH violation на phase bits | **S > 2** (Bell) | ⚡VER | §31 |
| Z/m discrimination scaling | **m^(k-1)** | ✓DOK | §46 |
| DJ на ноутбуке | **10⁶ qubit-like / 0.9 сек** | ⚡VER | §48 |
| MPS DJ/BV | **n=10,000 / 11 ms** | ⚡VER | §44 |
| HDC triple-relation memory | **100%** accuracy | ⚡VER | §5.4 |
| ANF early-verify cumulative (SHA) | **7.6×** | ⚡VER (после коррекции §133) | §132 |
| Φ-disqualifier backward shortcut | измеряемый, L=16 T=4 | ∆EXP | §130 |
| Stacked disqualifiers margin | 3-5% (маргинально) | ✗NEG | §131 |
| Число осей бита | **20** базовых + 3 кандидата | мета | §40 (v6) |
| Клеток (X×Y primitives) | **6** (5 пар + 1 triple) | мета | §25 (v5) |
| D-метагрупп | **5** (VAL, OP, REL, TIME, + 5-я) | мета | §40 |

## Том II — Дифф. криптоанализ SHA-256 (methodology_v20)

| Результат | Значение | Статус | Источник |
|---|---|---|---|
| **Нули De (каскад)** | 14/15 за O(2²²) | ✓DOK | П-10 |
| **Нули De (Newton adapted)** | 14/15 за O(1) | ⚡VER | П-84 |
| **Wang-chain (δe2..δe16=0)** | **P=1.0** | ⚡VER (1000/1000) | П-92 |
| **Найденная пара (полный цикл)** | W0 = **c97624c6** | ⚡VER (518 s, 12 CPU, 8685M итер.) | П-97 |
| **\|Sol_17\|** (neutral bits) | ≥ 2⁹⁶ | ∆EXP | П-101 |
| **Birthday bound** | оптимален **2¹²⁸** | ✓DOK | П-27, П-32 |
| **Distinguisher v6.0 (нейросеть)** | **AUC = 0.980** | ⚡VER | П-1000..П-1035 |
| **MITM через state[16]** | O(2⁸⁰) | ∆EXP (теория) | П-210 |
| **MILP наивная стоимость** | ~2¹⁴⁴ | ∆EXP | П-142 |
| **Carry-rank (image)** | **589/592** | ✓DOK | §191 |
| **Spectral gap η** | **0.189** | ⚡VER | §200 ★-Alg |
| **r=17 threshold** | P(δe17=0) = 2⁻³² | ✓DOK | П-30, П-115 |
| **DW⊥ norm advantage** | ~**1500×** больше нелинейных | ⚡VER | П-88 |
| **T_SC_A1 verification** | 100000/100000 | ⚡VER | П-24 |
| **T_WANG_ADAPTIVE** | 50000/50000 | ⚡VER | П-25 |
| **height_2 (p-adic tower)** | **≥ 11** (slope=1.000 до k=24) | ✓DOK | П-53, П-59 |
| **Rank_GF2(J_{5×15})** | **5** (абсолютный инвариант) | ✓DOK | П-58 |
| **GF2 bijection free-start** | rank=r для r=1..64 | ⚡VER | П-61 |
| **Word saturation** | bit 63% → word 94% | ⚡VER | П-79 |
| **σ-bit shortcut окно (ANF)** | единственный раунд (composition) | ⚡VER | П-128 |
| **ANF degree barrier (composition)** | saturate за 2 раунда | ⚡VER | П-128, §128 |
| **δe1 распределение** (геом.) | P(δe1=2ᵏ·0x8000) ≈ 2⁻⁽ᵏ⁺¹⁾ | ⚡VER (N=100) | П-26 |
| **T_DA_SHIFT нарастание δa** | по раундам | ∆EXP | П-26 |
| **k* (critical round)** | 5 | ⚡VER | §4 числа |
| **Serving: разделов** | 230+, экспериментов П-N | мета | v20 |

## Том III — Info-Theory Fingerprinting (IT-серия)

| Результат | Значение | Статус | Источник |
|---|---|---|---|
| **χ²-fingerprint SHA-2 семьи** | SHA-1/256/512 < RO, **z ≈ -2.5, p < 10⁻⁷** | ⚡VER | IT-1.3, Sharp |
| **MD5 противоположный знак** | SHA-2 ниже RO, MD5 выше | ⚡VER | Sharp |
| **σ₀/σ₁ атрибуция (schedule)** | **88%** редукции χ²-bias | ⚡VER | IT-2 |
| **Δ_χ² vs Δ_I dissociation** | marginal без structural | ⚡VER | IT-3 |
| **Linear distinguisher bit5_max** | **z = +3.9** (HW=2 only) | ∆EXP | IT-4 |
| **HW=2 exclusivity** | HW≥3 чистый H₀ (130K codewords exhaustive) | ⚡VER | IT-4.1 |
| **Directional chain-3 on state1** | **z = -3.87** при R=50 (p=0.02) | ⚡VER | IT-4.Q7d |
| **Q7d amplified R=500** | **p = 0.002** (Bonferroni-3 pass) | ⚡VER | IT-4.Q7DEF |
| **Q7f Walsh-4 signal** | **z = -6.40** | ⚡VER | IT-4.Q7DEF |
| **Cross-hash (S3)** | signal ONLY в SHA-256 (не SHA-1/512) | ⚡VER | IT-4.S3 |
| **Round decay (S2)** | signal ~2× за 4 раунда, RO-clean к r=20 | ⚡VER | IT-4.S2 |
| **chain_3 round evolution** | затухает медленнее chain_1 | ⚡VER | IT-5S |
| **Correlation ρ(direct, chain_3)** | **+0.98** | ⚡VER | IT-6 |
| **Same-sign бит** | **240/256** (p ~ 10⁻⁴⁰) | ⚡VER | IT-6 |
| **bit5_max magnitude** | ~8×10⁻⁵ бит MI | ⚡VER | IT-4 seq |

## Мосты (кросс-томные численные совпадения)

| Том-I | Том-II | Совпадение | Ссылка |
|---|---|---|---|
| §127 ANF эмпир. | §114-A prediction | Совпадение степеней ANF | ⇒BRIDGE |
| §128 shortcut saturate 2R | П-128 ANF composition | То же значение (2 раунда) | ⇒BRIDGE |
| §123 W-atlas ΔW ∝ 1/N_ADD | §122 W invariant round | W = свойство функции, не данных | ⇒BRIDGE |
| §132 ANF early-verify 7.6× | MITM O(2⁸⁰) | Первый реальный backward shortcut | ⇒BRIDGE |

## Мосты Том-III ↔ остальные

| Том-III | Том-II/I | Совпадение |
|---|---|---|
| IT-2 σ₀/σ₁ = 88% | T_SCHEDULE_SPARSE (63% нулей HW=2) | Схема объясняет χ²-fingerprint |
| IT-6 ρ=0.98 | max\|z\| классика недостаточна | Новый инструмент chain-test |
| IT-4.Q7 state1 чист на low-order | ANF degree barrier | Сигнал только в \|S\|≥3 |

## Сводные числа программы

- **Всего теорем** (именованных): ~60+ (~40 ✓DOK, ~15 ⚡VER, ~10 ✗NEG, ~5 ⊘ROLL)
- **Всего экспериментов**: П-1..П-1300+ (Том II), ~130 §§ (Том I), 6 итераций (Том III)
- **Ключевые моменты**: Wang-pair найдена; Distinguisher AUC=0.980; ρ(direct,chain_3)=0.98; axioms D1-D5 (20/20 осей pass)
