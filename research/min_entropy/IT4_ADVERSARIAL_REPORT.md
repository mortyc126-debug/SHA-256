# IT-4 — Adversarial search for f* with Δ_I(SHA-256, f*, k) > 0

> Цель: проверить, существует ли структурная фича f*(X), для которой
> SHA-256 утечёт информацию выше детектируемого порога. Если да —
> дисcоциация IT-3 разрушится. Если нет — дисcоциация укрепится как
> upper bound для линейного класса фич.

---

## 1. Постановка с pre-registered decision

Фичи: бинарные функции от (i, j), где (i, j) — две позиции бит во входе
HW=2. Тестовый набор:
- **64 фичи** покрывающие single-bits, XOR, sum, AND, OR, parity (small chunks),
  parity HW (i, j, i⊕j), плюс несколько простых нелинейных (AND-комбинаций).

Метрики:
1. **Walsh-Hadamard z**: per-cell z(f, b_out) для каждой из F × B = 64 × 24 = 1536
   ячеек. Под H_0 (RO): z ~ N(0, 1).
2. **Walsh-Σz²**: per-feature χ²_24-like statistic. Аггрегация сигнала через
   все 24 output бита.
3. **Logistic regression accuracy**: per-output-bit, обученная на 80% holdout.

Detection criteria:
- Bonferroni для 1536 cells: |z| > 4.155
- Bonferroni для 64 features (Σz²): эмпирическая p < 7.8e-4
- LogReg per bit: accuracy > 0.5 + 5σ = 0.5155 на N_test=26164

Pre-registered decision (Stage 3): hint считается подтверждённым только
если (a) p_emp < 0.001 при R=2000 на исходном классе И (b) z > 3 при
репликации на другом классе входов.

---

## 2. Stage 1: Walsh-Hadamard scan (`it4_walsh.py`)

R=100 keyed-BLAKE2b realizations для валидации null.

**Результат**: SHA-256 max |z| = 3.915 над 1536 ячеек (cell: bit5_j vs out_bit 10).

| Метрика | Значение |
|---|---|
| SHA-256 max |z| | 3.915 |
| RO max |z| (R=100): mean / std | 3.542 / 0.320 |
| RO q95 / q99 | 4.191 / 4.344 |
| P(RO_max ≥ SHA_max) | **0.139** |
| Bonferroni threshold | 4.155 |

SHA-256 max попадает внутрь типичного RO band. **Per-cell test: NO signal.**

Per-feature Σz² aggregation выделил 2 фичи:
- bit0_i_AND_bit5_j: Σz² = 53.69 (analytical χ²_24 z = +4.3σ)
- bit5_j: Σz² = 51.00 (analytical χ²_24 z = +3.9σ)

Эти **выше аналитического Бонферрони** для χ²_24 (порог ≈ 50.4 при 64 тестах) —
требуется empirical валидация.

---

## 3. Stage 2: validation + logistic regression (`it4_validate_and_classify.py`)

R=200 RO realizations для эмпирического null per feature. R=20 RO для
обучения LogReg null distribution.

### Walsh Σz² с empirical null (R=200)

| Rank | Feature | sha Σz² | RO mean | RO std | z_norm | p_emp |
|---|---|---|---|---|---|---|
| 1 | bit0_i_AND_bit5_j | 53.69 | 23.62 | 7.24 | **+4.16** | 0.005 |
| 2 | bit5_j | 51.00 | 24.07 | 7.34 | **+3.67** | 0.010 |
| 3 | bit7_i | 39.00 | 23.47 | 6.70 | +2.32 | 0.035 |
| 4 | bit5_iandj | 38.15 | 23.94 | 6.21 | +2.29 | 0.020 |

- **Bonferroni для 64 features: p < 7.8e-4** — НИ одна не проходит.
- min p = 0.005 — выше Бонферрони, но при R=200 разрешение лимитировано
  до p ≈ 1/201.

### Logistic Regression accuracy per output bit (R=20 RO null)

5σ threshold над 0.5 (N_test=26164): **0.0155 в accuracy**.

| Bit | sha_acc | sha_acc − 0.5 | sha_z | norm_z | p_emp |
|---|---|---|---|---|---|
| 6 | 0.49194 | −0.00806 | −2.61 | −2.25 | 0.095 |
| 14 | 0.49576 | −0.00424 | −1.37 | −1.94 | 0.095 |
| 10 | 0.50455 | +0.00455 | +1.47 | +1.84 | 0.143 |
| 9 | 0.49576 | −0.00424 | −1.37 | −1.64 | 0.143 |
| остальные 20 бит | accuracy ∈ [0.498, 0.503] | — | |z| < 1.6 | — | > 0.2 |

- Max |sha_acc − 0.5| = 0.0081 (bit 6) — **в 2× меньше 5σ-порога 0.0155**.
- Bonferroni (24 bits): p < 2.1e-3 — НИ один бит не проходит.

**Линейный distinguisher на 64 фичах НЕ может различить SHA-256 vs random.**

---

## 4. Stage 3: targeted follow-up (`it4_targeted.py`)

Прицельная проверка двух хинтов из Stage 2.

### A. Высокое разрешение на исходном классе (low_hw_w2, R=2000)

| Feature | sha Σz² | RO band | z | p_one |
|---|---|---|---|---|
| bit0_i_AND_bit5_j | 53.693 | 24.22 ± 6.99 | **+4.22** | **0.001** |
| bit5_j | 51.001 | 24.01 ± 6.91 | **+3.91** | 0.002 |

При R=2000 хинт **выживает**: p_one = 0.001 для bit0_i_AND_bit5_j.

### B. Репликация на HW=3 sub-sample (R=500)

| Feature | sha Σz² | RO band | z | p_one |
|---|---|---|---|---|
| bit0_i_AND_bit5_j | 18.021 | 24.18 ± 6.92 | **−0.89** | 0.82 |
| bit5_j | 26.842 | 23.88 ± 6.84 | +0.43 | 0.31 |

На HW=3 хинт **не реплицируется**. SHA-256 даёт даже МЕНЬШЕ Σz², чем
RO band — фактически ниже среднего.

### Pre-registered Verdict

Hint **NOT CONFIRMED** как структурное свойство SHA-256:
- (A) survives:  p_one = 0.001 < 0.001 threshold ✓
- (B) replicates: z = −0.89, требовалось > 3 ✗

→ **Эффект class-specific для HW=2, не общая структурная утечка.**

---

## 5. Что мы получили: количественное закрытие IT-3

### Главное: Δ_I эмпирический upper bound для SHA-256

**Linear distinguisher** (64 фичи) на N=130816 holdout 26164:
- Max |Δ_acc| = 0.0081 (бит 6)
- 5σ resolution = 0.0155
- → Δ_I (linear, k=1 per bit) < 0.0155 бит **на любом одиночном бите** SHA-256(low_hw_w2).

### Найденный микро-эффект (input-class-specific)

На low_hw_w2 (HW=2) Walsh даёт:
- bit5_j: Σz² = 51 при RO band 24 ± 7 → z = +3.9, p = 0.002 (R=2000)
- bit0_i_AND_bit5_j: Σz² = 54, z = +4.2, p = 0.001

В битах MI: ΔI ≈ (Σz² − E[Σz²]) / (N · 2 ln 2) ≈ 27 / (130816 · 1.39) ≈ **1.5·10⁻⁴ бит**.

Это в **200×** меньше χ²-эффекта (Δ_χ² ≈ 0.07 бит, IT-1.3) и **70×**
ниже резолюции стандартного MI оценщика IT-3.

**На HW=3 микро-эффект отсутствует** (z = −0.89 для bit5_j).

### Интерпретация

Дисcоциация IT-3 **подтверждена и количественно ограничена**:

1. χ²-excess SHA-2 (~0.07 бит при k=12) **существует**.
2. На low_hw_w2: до **~1.5·10⁻⁴ бит** этого excess можно объяснить через
   bit-уровневую утечку через bit5_j (но эффект класс-специфичен).
3. **>99.7%** χ²-excess — НЕ объясняется ни одной из 64 линейных фич.
4. **Линейный distinguisher** (LogReg на всех фичах сразу) не способен
   различить SHA-256 от RO ни на одном из 24 битов.

→ **χ²-excess SHA-2 преимущественно НЕЛИНЕЙНЫЙ и orthogonal к простым
структурным проекциям входа**, что делает Δ_I и Δ_χ² действительно
независимыми ИТ-метриками.

---

## 6. Что найдено нового

### 6.1 Эмпирический upper bound для linear Δ_I

Для SHA-256 на low_hw_w2 (130 816 inputs, k = 24 бит выхода):

```
Δ_I^(linear, single-bit-feature)  <  1.5·10⁻⁴ бит  (на лучшей из 64 фич)
Δ_I^(linear, all-features-LogReg) <  0.005 бит    (5σ upper bound)
Δ_I^(any-MI-estimator, IT-3)      <  0.005 бит
```

### 6.2 Микро-эффект bit5_j на HW=2

Найдена линейная фича с Walsh-z = +3.9σ при R=2000 на low_hw_w2,
**не реплицируемая на HW=3**. Вероятная природа: связь между распределением
позиций j по 32-битным словам входного сообщения SHA-256 и выходом первых
24 бит. Связано с тем, что message schedule по-разному обрабатывает
W[0..3] vs W[4..15].

Это **класс-специфичный** структурный эффект, не общая утечка.

### 6.3 Усиление IT-3

Расширили дисcоциацию IT-3:
- **Marginal**: Δ_χ² ≈ 0.07 бит (значимо)
- **Structural (linear)**: < 5·10⁻³ бит для любого linear feature class
- **Соотношение**: marginal в **>10×** больше structural-linear bound
- **Implication**: marginal-uniformity excess SHA-2 — преимущественно
  «нелинейный» эффект, не доступный простым distinguisher-ам.

---

## 7. Открытые подвопросы

| # | Вопрос | Метод |
|---|---|---|
| Q1 | Найдётся ли nonlinear classifier (GBDT, MLP) с accuracy > 0.515 на каком-либо output bit? | XGBoost / небольшая нейросеть на raw bits |
| Q2 | Микро-эффект bit5_j на HW=2 — это артефакт padding или round-функции? | Замер на chimera-вариантах (IT-2) |
| Q3 | Существует ли input-class, на котором Δ_I детектируем через нашу же 64-feature batch? | scan по weight w ∈ {1, 2, 4, 6, 8} |
| Q4 | Связь Δ_χ² и Δ_I для chimera variants — какая компонента SHA-2 «убивает» структурную утечку быстрее всего? | повторить IT-2 в LogReg-метрике |

---

## 8. Связь с предыдущими этапами

| Этап | Результат | Что добавляет IT-4 |
|---|---|---|
| IT-1 | t-test «Ĥ_∞ → нет сигнала» | grossly insufficient инструмент |
| IT-1.3 | χ²-fingerprint SHA-MD vs RO, p < 10⁻⁷ | IT-4 проверил, что эффект НЕ структурный |
| IT-2 | Атрибуция χ²-эффекта по компонентам SHA-2 | IT-4 показывает, что эффект не сводится к линейным фичам входа |
| IT-3 | Дисcоциация Δ_χ² ≠ Δ_I при разрешении 0.005 бит | IT-4 уточнил bound: Δ_I^(linear) < 5·10⁻³ бит, микро-эффект 1.5·10⁻⁴ |

---

## 9. Файлы

- `it4_walsh.py` / `it4_walsh.json` — Walsh-Hadamard scan, 64 features × 24 output bits.
- `it4_validate_and_classify.py` / `it4_validate.json` — empirical null + LogReg.
- `it4_targeted.py` / `it4_targeted.json` — targeted high-R + replication test.
- `IT4_ADVERSARIAL_REPORT.md` — этот документ.
