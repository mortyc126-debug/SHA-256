# Глава III.4. Surgical Decomposition и Ω_k Invariant

> TL;DR: Surgical S1-S4 локализовали bit5_max signal: signal max|z|=22.7
> при r=4, exp(-0.25r) decay, RO-clean при r=20, ОНО SHA-256-only,
> block-2 регенерирует low-order bias из high-order state1. IT-5G даёт
> теорию chain-test (Parseval, NP-оптимальность). IT-5S: round×Walsh-order
> map с фазовым переходом r≈12, низкие порядки затухают быстрее высоких.
> IT-6: новый инвариант **Ω_3=+0.98** — sign-test 240/256 битов, p~10⁻⁴⁰.

## §III.4.1 IT-4 Surgical S1: full output 256 бит

**Метод** ⚡VER [SURG §S1]: расширение с 24 на 256 output bits для
bit5_max на HW=2.

**Результат** [SURG §S1]:
```
Σz² over 256 bits = 284.86  vs RO 255.37 ± 22.55  → z=+1.31 (NS)
max|z| over 256 bits = 3.92 at bit 10  vs RO 3.04 ± 0.37 (q99=4.13) → z=+2.41, p=0.024
```
Сигнал **sparse** — локализован в ~2 битах. **Bit 10** главный, **bit 210**
второй (z=−3.02). Оба в bit-in-byte position 2 (наблюдение).

## §III.4.2 IT-4 Surgical S2: round-by-round emergence

**Reduced-round single-block** ⚡VER [SURG §S2]:
| r | max|z| | Σz² | z_max_vs_RO |
|---|---|---|---|
| 4 | **22.67** | 111 473 | **+55.7** |
| 8 | 19.43 | 60 392 | +46.5 |
| 12 | 14.13 | 24 319 | +31.5 |
| 16 | 9.20 | 4 998 | +17.5 |
| 20 | 3.45 | 306 | +1.3 |
| 24 | 2.99 | 226 | −0.05 |
| 64 | 2.53 | 239 | −1.3 |

**Критические факты** ✓DOK:
1. r=4: max|z|=22.67, ~**2.9 бит MI** (соответствует Том II §106
   T_INFO_BARRIER_R1: MI(W;e_1)=2.5 бит).
2. **Затухание exp(−0.25r)** — каждые 4 раунда ~×2.
3. **K r=20 сигнал затухает до RO** и остаётся до r=64.

**Следствие** ✓DOK: **single-block 64-round SHA-256 = чистый RO** для
bit5_max. Но 2-block standard SHA-256 даёт z=+4.28. Откуда?

## §III.4.3 IT-4 Surgical S3: cross-hash specificity

**Тест 6 хэшей на HW=2 exhaustive** ⚡VER [SURG §S3]:
| hash | n_bits | max|z| | z_max_vs_RO |
|---|---|---|---|
| **sha256** | 256 | 3.92 | **+2.31** |
| sha1 | 160 | 3.30 | +1.05 |
| sha512 | 512 | 3.00 | −0.80 |
| sha3_256 | 256 | 3.42 | +0.93 |
| blake2b | 256 | 2.49 | −1.64 |
| md5 | 128 | 3.09 | +0.71 |

**Сигнал bit5_max ТОЛЬКО у SHA-256**. Не реплицируется на SHA-1, SHA-512.

**Корректировка IT-1.3** ✓DOK:
- χ²-fingerprint (IT-1.3) = **family-level** (SHA-MD).
- bit5_max signal (IT-4 Q-line) = **SHA-256-specific**.

ДВА разных микро-эффекта, разделяются surgical-анализом.

## §III.4.4 IT-4 Surgical S4: block-2 amplification

**Гипотеза**: single-block r=64 = RO, но 2-block = signal ⇒ block-2 даёт
эффект.

**Метод** ⚡VER [SURG §S4]: full block 1 → state1, затем r2 раундов block 2.
| r2 | max|z| | z_max_vs_RO |
|---|---|---|---|
| **0** (=state1) | 2.53 | **−1.46** |
| 4 | 3.24 | +0.47 |
| 8 | 3.43 | +0.99 |
| 32 | 3.62 | +1.50 |
| **64** (=full SHA) | **3.92** | **+2.30** |

**Вердикт** ✓DOK:
- r2=0: state1 RO-clean (z=−1.46).
- r2=64: signal до +2.30, max bit=10 (тот же).

**Механизм** ✓DOK [SURG §S4]: state1 не имеет 1st-order корреляций с
bit5_max, но имеет **high-order** (≥3) корреляции. Block-2 — нелинейная
compression — **читает** эти high-order структуры и **конвертирует** в
1st-order bias выхода.

```
INPUT (HW=2) → block 1 r=4..16 (signal decays exp) → state1 (RO-clean
1st-order, has high-order) → block 2 (compresses high→low order) →
OUTPUT bit5_max signal at z≈+2.3 (bit 10), z=−3.0 (bit 210)
```

Magnitude на выходе: **~8·10⁻⁵ бит MI** — в 35 000× меньше, чем входной
сигнал на r=4 (2.9 бит).

## §III.4.5 IT-5G Theoretical formalisation chain-test

**Setup** ✓DOK [IT-5G §1]: Y:X→{0,1}^n state map, f input feature,
t output target. Chain_k = (1/√N)Σ_{|S|=k} z_S(f)·z_S(t).

**Parseval** ✓DOK [IT-5G §2]: `Z_direct = Σ_k Chain_k`. Direct signal —
сумма всех порядков.

**Variance под H_0** ⚡VER [IT-5G §4]: std[Chain_k] ≈ √(M_k/N), M_k=C(n,k).
Match within 10% по 3 порядкам (см. Гл. III.1 §1.4).

**NP-оптимальность** ✓DOK [IT-5G §5]:
- Chain_k = NP-optimal для **uniform-distributed** alternative.
- max|z_S| = NP-optimal для **sparse** (single S* dominant).
- Symmetric агрегаты strictly dominated Chain_k для distributed.

**Теорема (informal)** ⚡VER [IT-5G §3]: signal ε distributed over M
subsets with coherent sign:
- Chain_k: signal ε√M, σ ~ √M ⇒ detectable.
- max|z|: ε/√M per cell ⇒ undetectable.
- Σz²: ε² total ⇒ обычно undetectable.

**Empirical predictions verified** ⚡VER [IT-5G §7]:
- P1: std growth 1:11.3:104 theoretical, 1:12.5:95 observed. ✓
- P2: signal NOT uniformly distributed (z_3=−3.83, z_4=−6.40 растёт).
- P3: Parseval Σ_k Chain_k = Z_direct ⇒ alternating signs across orders
  (Chain_2≈−2, Chain_3=−83, Chain_4=−5275, higher must sum to +5356
  to give Z_direct=−3.92).

## §III.4.6 IT-5S Round × Walsh-order evolution

**Метод** ⚡VER [IT-5S §1]: chain_k(r) для k=1,2,3 на state_r при
r∈{4,8,12,16,20,24,32,48,64}. RO null R=30 vary state_r.

**Raw chain magnitudes** ⚡VER [IT-5S §2]:
```
r    |chain_1|  |chain_2|  |chain_3|
 4      6.18      890        79 696
 8      6.51      619        46 916
12      0.17        3            110     ← phase transition
16      0.43       19            727
20      0.02        1             88     ← stabilises
64      0.00        2             83     ← saturated
RO band: chain_3 mean=−83.54, std=3.79
```

**Два ключевых наблюдения** ✓DOK:

**1. Сигнал на ВСЕХ порядках при малых r** [IT-5S §3.1]:
r=4: chain_(k+1)/chain_k ≈ 100. Каждый дополнительный Walsh-порядок —
256× больше subset-ов потенциально несущих информацию.

**2. Фазовый переход r≈12** [IT-5S §3.2]:
| r | chain_3 | изменение |
|---|---|---|
| 4 | −79 696 | baseline |
| 8 | −46 916 | ×0.59 |
| **12** | **+110** | ×−0.0023 (резкий + смена знака) |
| 16 | +727 | ×6.6 |
| 20 | −88 | стабилизация |
| 64 | −83 | saturated |

**Новый факт** ⚡VER [IT-5S §6]: **скорость затухания chain_k зависит от
k немонотонно**. К r=64: |chain_3|/|chain_1| ≈ 41 500 (vs 12 900 при r=4).
**chain_1 быстрее затухает чем chain_3** ⇒ информация **мигрирует в
высокие порядки**.

Это квантитативная формулировка миграции through round-функцию SHA-256.
Соответствует S2 (max|z| в 1st-order saturates at r≈20).

## §III.4.7 IT-6 Full output map: новый инвариант Ω_k

**Метод** ⚡VER [IT-6 §1]: для каждого из 256 output битов b:
- direct_z(b) = √N·⟨σ(bit5_max), σ(state2[bit b])⟩
- chain_3(b) = (1/√N)Σ_{|S|=3} z_S(bit5_max) z_S(state2[b])

**Bit-by-bit классификация** [IT-6 §2]:
- Cat 1 (direct ∧ chain |z|>3): 1 (bit 10).
- Cat 2 (direct only): 0.
- Cat 3 (hidden chain only): 0.
- Cat 4 (nothing): 255.

На уровне отдельных битов **выглядит как ничего**.

**Применение нового правила: КОРРЕЛЯЦИЯ паттернов** ✓DOK [IT-6 §4]:
```
ρ(z_direct_norm, z_chain_norm) over 256 bits = +0.9795
Same-sign bits: 240 / 256 = 93.75%
Binomial p (≥240 same-sign | p=0.5) ≈ 10⁻⁴⁰
```

**Самый сильный сигнал из всех IT-1..IT-6**.

**Pattern** ✓DOK [IT-6 §4.3]:
- |z_direct| ≤ 2 для 254/256 битов (классически шум).
- |z_chain| ≤ 3 для 255/256 битов (тоже шум).
- НО sign(z_direct_b) = sign(z_chain_b) для 240/256.

Каждый бит индивидуально в шуме. Но **согласованно** по знаку.

**Интерпретация через Parseval** ✓DOK [IT-6 §5]: corr(direct_z, Chain_3)
= 0.98 ⇒ Chain_3(b) объясняет **96% дисперсии** direct_z(b) по output
битам ⇒ block-2 compression F_b: state1→state2[bit b] имеет Walsh-спектр
**систематически биасированный в 3rd-order подпространство**.

Для идеального RO: corr ≈ √(M_3/2^n) = √(2.76M/2^256) ≈ 0.

## §III.4.8 Определение Ω_k

**Новый ИТ-инвариант** ✓DOK [IT-6 §6]:
```
Ω_k(h, f_in) := corr_b∈[output_bits] (direct_z(b), chain_k(b))
```
Степень k-доминантности Walsh-спектра round-функции.

**Свойства**:
- |Ω_k| ≤ 1 по def.
- RO: E[Ω_k] = 0.
- SHA-256 на (HW=2, bit5_max): **Ω_3 = +0.98**, sign-test p ≈ 10⁻⁴⁰.

**Почему классика не видит** ✓DOK [IT-6 §7]:
- Classical max|z|: max|direct_z|=3.24, Bonferroni-256 требует |z|>3.7.
  **Не проходит**.
- Наш анализ: chain_3 + cross-bit correlation ⇒ p~10⁻⁴⁰.

## §III.4.9 Compound подтверждение IT-4..IT-5

✓DOK [IT-6 §8]: Ω_3=+0.98 — **второе независимое подтверждение** что
сигнал bit5_max→state2 **распределён когерентно** в 3rd-order Walsh.
Q7d/Q7f показали это для bit10 и bit210 индивидуально. IT-6 — для
**ВСЕХ 256 битов выхода** одновременно.

Качественный сдвиг: **единое структурное свойство** SHA-256 block-2
compression на HW=2 inputs, не artefact конкретной (feature, target).

## §III.4.10 Открытые

?OPEN [IT-6 §11]:
- IT-6b: Ω_k для k=1, 2, 4. Ω_4 > Ω_3? Полный спектр Ω_k.
- Ω_k для других input features (не только bit5_max).
- Ω_k for reduced-round SHA: эволюция dominance order vs r (связь с IT-5S).
- Аналитика: ожидаемый Ω_k под H_0 с поправкой на конечный N.

См. Гл. III.5 — bridges с Том I/II, общий статус закрытых вопросов.
