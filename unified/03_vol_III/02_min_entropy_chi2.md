# Глава III.2. Min-Entropy и χ²-fingerprint

> TL;DR: SHA-256 ≡ RO в Ĥ_∞ метрике (IT-1), но χ² на k=8..16 truncations
> систематически НИЖЕ RO band (z≈−2.5, p<10⁻⁷ для SHA-MD-семейства, MD5
> противоположно). σ₀/σ₁ — главный вклад (88% bias reduction). χ²-excess
> существует БЕЗ MI-excess: marginal vs structural — разные ИТ-инварианты.

## §III.2.1 IT-1 Min-entropy на структурированных входах

**Setup** ✓DOK [IT-1 §2]: 10 классов X (uniform, counter, ASCII,
Bernoulli p∈{0.01, 0.1}, low_HW w∈{2,4,8}, coset_{12,18,24}), N=2²²,
truncation k=20.

**Результат** ✓DOK [IT-1 §3]:
```
source        H_inf(X)  Ĥ_∞(Y)   Ĥ_2(Y)   d_TV     max_ct
uniform        512.00   17.83    20.00    0.195    18
counter         22.00   17.91    20.00    0.195    17
biased_p10      77.83   17.91    20.00    0.195    17
low_hw_w2       17.00   14.72    16.83    0.883    155
coset_18        18.00   15.56    17.68    0.779    87
coset_12        12.00   10.92    11.99    0.996    2169
```

**3 режима** ⚡VER [IT-1 §3.1]:
- (A) **Saturation** (H_∞(X) ≫ k): Ĥ_∞ = k − 2.2 ≈ 17.8.
- (B) **Birthday** (H_∞(X) ≈ k): потеря 2.3 бит.
- (C) **Input-bound** (H_∞(X) ≪ k): Ĥ_∞ = H_∞(X). SHA не «создаёт» энтропию.

**Cross-hash t-test** ✓DOK [IT-1 §4]: SHA-256 vs SHA-512 vs BLAKE2b на
5 классах × R=8 — **ни одна разница не значима** (max |Δ|=0.072 бит для
low_hw_w2, p=0.125). Универсальная RO-формула выполняется.

**Главный вывод IT-1** ✓DOK: SHA-256 — **почти оптимальный min-entropy
конденсатор**, статистически неотличим от RO в Ĥ_∞-метрике на разрешении
~0.1 бит. Это закрывает gap методички v20 (только Shannon-метрики).

## §III.2.2 IT-1.1..1.3 SHARP: χ² distinguishing на низких truncations

**Метод** ⚡VER [IT-1.1+ §1]: вместо Ĥ_∞ + t-test — **полный count-вектор**
+ exhaustive enumeration HW=2 (130 816 codewords) + analytic RO null
(R=200 keyed-BLAKE2b).

**Результат IT-1.1** ⚡VER [SHARP §2]: SHA-256 на k=12, χ² = 3871.6 при
RO_band = 4096.4 ± 83.0 → **z = −2.71, p = 0.02**. Знак отрицательный:
SHA-256 **более равномерно** чем RO. Эффект противоположен утечке.

**Результат IT-1.2 replication** ⚡VER [SHARP §3]: 5 разных входных
наборов, **5/5 z отрицательные** → sign-test p=0.031. Сильнее на
структурированных входах (low_hw_w2, ASCII).

**ГЛАВНЫЙ результат IT-1.3** ✓DOK [SHARP §4]: cross-hash z-таблица
k∈[8,16] на 7 хэшах, 200 RO realizations:

| hash | neg/total | sign p | направление |
|---|---|---|---|
| sha256 | 8/9 | 0.039 | hyper-uniform |
| sha512 | 9/9 | 0.002 | hyper-uniform |
| sha1 | 9/9 | 0.002 | hyper-uniform |
| md5 | 0/9 | 0.002 | concentration |
| sha3_256 | 5/9 | 0.500 | noise |
| blake2b | 6/9 | 0.508 | noise |
| blake2s | 7/9 | 0.180 | noise |

**Архитектурное разделение** ✓DOK:
- SHA-MD-семейство (SHA-1/256/512): **26/27 negative**, p = **8·10⁻⁸**.
- Sponge/HAIFA (SHA-3, BLAKE2): 18/27 negative, p ≈ 0.12 (шум).
- MD5: 9/9 positive, p = 0.002 (слабая диффузия → концентрация).

**Интерпретация** ✓DOK [SHARP §5]: SHA-2 семейство — **гиперравномернее
RO** на коротких truncations при структурированных входах. **НЕ утечка**:
адверсарий, полагающийся на RO-модель, может только переоценить cost
атаки. Это микроскопический "отпечаток" SHA-2 family.

## §III.2.3 IT-2 Component attribution: что даёт bias

**Метод** ⚡VER [IT-2 §1]: векторизованная uint32-SHA-256 с переключателями
по компонентам (V0=vanilla, V1=no-Σ_compr, V2=no-σ_sched, V5=linear-Ch/Maj,
V3=no-both, V7=almost-linear). K-вариации: K_vanilla, K_zero, K_golden.
Тот же RO null R=200, тест на low_hw_w2 exhaustive, k=12.

**Атрибуция bias на k=12** ✓DOK [IT-2 §3]:
| Условие | z@k=12 | Δ от vanilla | reduction |
|---|---|---|---|
| V0 vanilla | −2.52 | — | — |
| V2 σ₀,σ₁→identity | **−0.30** | +2.22 | **88%** |
| K_golden | −0.38 | +2.14 | **85%** |
| V1 Σ₀,Σ₁→identity | −0.77 | +1.75 | 70% |
| V5 Ch,Maj→XOR | −0.81 | +1.71 | 68% |
| K_zero | −1.14 | +1.38 | 55% |

**Ранжирование вкладов** ✓DOK [IT-2 §5]:
1. σ₀,σ₁ message schedule diffusion (88%)
2. K_vanilla→K_golden round constants (85%)
3. Σ₀,Σ₁ compress diffusion (70%)
4. Ch, Maj boolean (68%)
5. K_vanilla→K_zero (55%)

**Контр-интуитивно** ⚡VER [IT-2 §5]: K_golden даёт БОЛЬШЕ reduction чем
K_zero. ⇒ bias требует ЛОМКИ симметрии, K=0 не ломает, K_golden ломает
плавно, K_vanilla — резонансно.

**Главный вывод IT-2** ✓DOK: эффект **синергетический**. Никакая одиночная
компонента не объясняет всё. χ²-fingerprint = свойство **всей round-функции
SHA-2 как целого** на структурированных входах.

**Сломанные варианты** [IT-2 §4]: V3 (no Σ AND no σ): z=+499 при k=12
(полный коллапс). Те же компоненты, что отвечают за bias, отвечают за
криптографическую диффузию вообще ⇒ bias = «тень» правильной диффузии.

## §III.2.4 IT-3 Δ-инвариант и dissociation

**Постановка** ⚡VER [IT-3 §1]: ввести Δ_h(f, k) = I(f(X); h(X)↾k) −
E_RO[·] как ИТ-инвариант для пары (хэш, фича).

**Estimator validation** ✓DOK [IT-3 §2]: plug-in MI с Miller-Madow
correction. Sanity-tests: Y⊥f → bias ≈0.89 (после MM); Y=f → I=H(f)
точно; H_0 std at R=200 = **0.0021 бит**. Detection threshold (5σ):
Δ ≥ 0.010 бит при R=200, ≥ 0.005 при R=1000.

**8 структурных фич** [IT-3 §3]: sum_mod16, gap_div32, imod8_jmod8,
iword, imod32, jword, HWi, popxor_ij. Покрывают позицию в слове, байте,
gap, hamming-структуру.

**Результат: 7 хэшей × 8 фич × 4 k, R=200** ⚡VER [IT-3 §4]: **никакой
хэш** не показывает значимого Σz при Bonferroni (224 cells, требует
|z|>3.7). MD5 пограничный sign-test p=0.05 в **отрицательную** сторону
(противоположно χ²-поведению).

**ГЛАВНЫЙ финальный результат: dissociation** ✓DOK [IT-3 §5]:
на R=1000, k=12, low_hw_w2, **те же** RO realizations:
```
χ² metric:    SHA-256=3871.56, RO=4094.16±88.28, z=−2.52, p=0.012
I(f;Y) max:   max |z|=1.42 over 8 features
                                   ─────────────────────
χ²-excess SIGNAL,  MI-excess  NO SIGNAL для любой f.
```

**Интерпретация** ✓DOK [IT-3 §6]: marginal P(Y_h) отклоняется от RO в
сторону большей равномерности (Δ_χ²<0), но это отклонение **ортогонально**
ко всем тестируемым структурным фичам входа.

**Декомпозиция RO-deviations** ✓DOK [IT-3 §8]:
- Чисто маргинальные (наш SHA-2 случай: Δ_χ²≠0, Δ_I=0).
- Чисто структурные (гипотетический backdoor).
- Смешанные (MD5: Δ_χ²>0 marginal, Δ_I<0 structural anti-correlation).

Это **новая таксономия** RO-deviations в крипто-ИТ. См. Гл. III.5
о bridges с Том I/II.

## §III.2.5 Открытые подвопросы

?OPEN [IT-3 §10]:
- Q1: ∃ f* с Δ_I(SHA-256, f*, k) > 0.01 бит? (см. Гл. III.3 для
  частичного ответа: bit5_max даёт ~10⁻⁴ бит, см. §III.3.2)
- Q2: closed-form между Δ_χ² и Δ_I через round-функцию?
- Q3: dissociation для других классов входов (HW=3, ASCII, coset)?
- Q4: закон сохранения Σ_f Δ_I(h, f, k) = const?
- Q5: связь Δ_χ²(h) с энтропийной ёмкостью раунда?
