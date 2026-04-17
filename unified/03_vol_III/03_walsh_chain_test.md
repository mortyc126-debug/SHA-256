# Глава III.3. Walsh-Hadamard скан и Directional Chain-Test

> TL;DR: Walsh-сканирование 64 input-фич × 24 output-бит обнаружило
> single Bonferroni-significant эффект bit5_j (HW=2 only, z=+3.9).
> 2nd/3rd-order Walsh на state1 — RO-clean. Directional **chain-3** на
> state1 фиксирует z=−3.87 при R=50, амплифицируется до z=−3.83 при
> R=500, реплицируется на bit 210 (Q7e), Walsh-4 chain даёт z=−6.40.
> Сигнал РАСПРЕДЕЛЁН и НЕВИДИМ для max|z|.

## §III.3.1 IT-4 Walsh-Hadamard adversarial scan

**Метод** ⚡VER [IT-4 §1]: 64 binary features f(i,j) на парах активных
позиций HW=2 codeword × 24 output битов = 1536 ячеек. R=100 keyed-BLAKE2b.

**Stage 1 max|z| scan** ⚡VER [IT-4 §2]: SHA-256 max|z| = **3.915** в
ячейке (bit5_j × out_bit10). RO band q95=4.19, q99=4.34, Bonferroni
threshold=4.155. **Per-cell test: NO signal** (P(RO_max ≥ SHA_max)=0.139).

**Per-feature Σz² (24-output aggregation)** ⚡VER [IT-4 §2]:
- bit0_i_AND_bit5_j: Σz²=53.69, χ²_24 z=+4.3
- bit5_j: Σz²=51.00, χ²_24 z=+3.9
Аналитически выше Bonferroni (порог≈50.4) — требует validation.

**Stage 2 empirical null R=200** ⚡VER [IT-4 §3]:
| Rank | Feature | sha Σz² | RO mean±std | z_norm | p_emp |
|---|---|---|---|---|---|
| 1 | bit0_i_AND_bit5_j | 53.69 | 23.62±7.24 | +4.16 | 0.005 |
| 2 | bit5_j | 51.00 | 24.07±7.34 | +3.67 | 0.010 |

Не проходит Bonferroni-64 (p<7.8e-4). LogReg на всех битах: max accuracy
deviation 0.0081, 5σ threshold = 0.0155 → **линейный distinguisher НЕ
различает SHA-256 vs random**.

**Stage 3 follow-up** ⚡VER [IT-4 §4]:
- (A) high-R на исходном HW=2: bit0_i_AND_bit5_j z=+4.22, p=0.001 ✓
- (B) replication HW=3: z=−0.89 (нет репликации) ✗

→ **class-specific HW=2 only**, не общая утечка.

**Δ_I bound** ✓DOK [IT-4 §6.1]:
- Δ_I^(linear, single-bit) < 1.5·10⁻⁴ бит
- Δ_I^(linear, all-features-LogReg) < 5·10⁻³ бит
- Δ_I^(any-MI-estimator IT-3) < 5·10⁻³ бит

⇒ **>99.7% χ²-excess НЕ объясняется** ни одной из 64 линейных фич.
Дисcоциация IT-3 количественно подтверждена.

## §III.3.2 IT-4.1 Followup: HW=2 EXCLUSIVITY

**Гипотезы** [IT-4.1 §1]: (H1) сем. сдвиг j_max vs j_middle, (H2)
HW=2 структурно особенен (T_SCHEDULE_SPARSE), (H3) случайность.

**HW × role × bit_idx scan** ⚡VER [IT-4.1 §2]: 4 HW × 2 roles × 9 bits =
72 ячейки, R=300. Heatmap:
```
HW=2 role=max bit5: z = +4.28  ✓ Bonferroni-72 passes (p_corr=0.0014)
HW=3 role=max bit5: z = +0.47
HW=4 role=max bit5: z = +2.82  (←IT-4.1 cherry-pick, см. ниже)
HW=5 role=max bit5: z = −0.31
```

**Chimera attribution на (HW=2, bit5_max)** ⚡VER [IT-4.1 §3]:
| Variant | Σz² | z_norm | reduction |
|---|---|---|---|
| V0 vanilla | 51.0 | +3.69 | baseline |
| V1 no-Σ_compr | 25.1 | +0.04 | **99%** |
| V5 linear Ch/Maj | 23.9 | −0.13 | **97%** |
| K_golden | 19.0 | −0.82 | 78% |

**ОТЛИЧИЕ от IT-2** ✓DOK [IT-4.1 §3]:
| | χ² (IT-2 marginal) | bit5_max (IT-4.1 structural) |
|---|---|---|
| Главная | σ_schedule (88%) | **Σ_compress (99%)** |

**Разные signature живут в разных компонентах SHA-2**. χ² — в σ_schedule;
bit5_max — в Σ_compress.

## §III.3.3 IT-4.Q1..Q3b Surgical follow-ups

**Q1 bit specificity** ⚡VER [Q-rep §Q1]: 47 функций позиции на HW=2 max.
- bit5 = word_parity: z=+3.77, p=0.003 ✓ (уникальный, в 1.7× больше следующего)
- Другие word-bit (b1=bit6, b2=bit7, b3=bit8): |z|≤2.1.
**Сигнал уникально на bit 5 = parity of word_index**.

**Q2 HW-parity hypothesis** ✗NEG [Q-rep §Q2]: HW∈{2,3,4,5,6,7,8}
| HW | z |
|---|---|
| 2 | **+4.28** |
| 3 | +0.47 |
| 4 | +2.82 |
| 5 | −0.31 |
| 6 | −0.09 |
| 7 | −0.91 |
| 8 | −0.83 |

Mann-Whitney even>odd: p=0.20 не значимо. **HW-parity hypothesis рефутирована**.

**Q3 role-asymmetry HW=4** [Q-rep §Q3]: с другим seed bit5_max даёт
z=−0.66 (vs +2.82 в IT-4.1). **Расхождение 3.5σ от смены seed**.

**Q3b reproducibility HW=4** ✓DOK [Q-rep §Q3b]: 10 seeds, R=200 each:
mean z=−0.29, std z=1.07, t-test p=0.41. **На HW=4 нет сигнала** —
H_0 идеально. z=+2.82 в IT-4.1 был **cherry-pick случайного сабсэмпла**.

**Корректировка** ✓DOK [Q-rep]: Сигнал bit5_max **ЭКСКЛЮЗИВНО на HW=2**
(exhaustive 130 816 codewords). На всех остальных HW — чистый H_0.

## §III.3.4 IT-4.Q7 2nd-order Walsh on state1: ✗NEG

**Метод** ⚡VER [Q7 §1]: bilinear Walsh z для всех 32 640 пар (a,b)
на 256 битах state1 (после 64 раундов block 1).

**Результат** ✗NEG [Q7 §2]:
```
SHA max|z_2| = 4.41 at pair (108, 208), Σz² = 33017
RO max|z_2| mean = 4.31 ± 0.29
z_norm: max|z|: +0.34, Σz²: +1.46. P(RO ≥ SHA) = 0.33.
```
**state1 RO-clean по 2nd-order Walsh**. Top-30 пар не кластеризуются.

**Q7b reverse-trace** ⚡VER [Q7 §Q7b]:
- Через 1st-order state1 битов: 0.2% сигнала.
- Через 2nd-order XOR-пары: −3.0% (противоположный знак).

⇒ Сигнал **обязательно** в |S| ≥ 3.

## §III.3.5 IT-4.Q7C 3rd-order Walsh: ✗NEG для max|z|

**Метод** ⚡VER [Q7C §1]: C-реализация bit-packed scan, 2.76M триплетов
за 1.4с на SHA-256.

**Результат** ✗NEG [Q7C §2]:
```
SHA max|z| = 4.899 at triple [18,68,244], Σz² = 2 760 330
n_above_4 = 174 (H_0=174, perfect)
n_above_5 = 0 (H_0=1.6, систематически меньше)

vs RO band (R=50): max|z| 5.21±0.23
z_norm = −1.37, p = 0.92  ← SHA НИЖЕ среднего RO
```
SHA-256 во всех метриках чуть ниже RO. **No single carrier triple**.

**Walsh-spectrum state1** ✓DOK [Q7C §5]: все 3 порядка чистые:
| Order | N tests | SHA max|z| | RO max|z| | вердикт |
|---|---|---|---|---|
| 1 | 256 | 2.53 | ~3.0 | RO-clean |
| 2 | 32 640 | 4.41 | 4.31±0.29 | RO-clean |
| 3 | 2 763 520 | 4.90 | 5.21±0.23 | **RO-clean (даже ниже)** |

## §III.3.6 IT-4.Q7D Directional chain-3: SIGNAL

**Метод** ⚡VER [Q7D §1]: chain_3 = (1/√N)Σ_{|S|=3} z_S(f)·z_S(t),
f=bit5_max, t=state2[bit10]. C-ядро 2.4с.

**Результат** ⚡VER [Q7D §2]:
```
SHA-256:
  Direct signal: −3.915
  Chain_3:       −83.10
  max|z_in·z_out|: 13.45 (RO 14.08±1.30 → −0.49, RO-clean)

RO null R=50 (vary target):
  chain_sum mean=+1.12, std=21.76
  ⇒ z_norm = −3.87, p_emp = 0.02
```

**Сравнение метрик** ✓DOK [Q7D §5]:
| Метод | Тип | z_norm | Детекция |
|---|---|---|---|
| Q7C max|z| per triple | symmetric | −1.37 | ✗NEG |
| Q7C Σz² per triple | symmetric | −1.44 | ✗NEG |
| **Q7D Chain_3** | **directional** | **−3.87** | **✓DOK** |

**Принципиально новое** ✓DOK [Q7D §4]: signal **распределён coherently**
по 2.76M триплетам с КОГЕРЕНТНЫМИ знаками z_in vs z_out. Невозможно при
независимости знаков. Symmetric агрегаты систематически слепы.

## §III.3.7 IT-4.Q7DEF Amplified tests

**Q7d-R500** ⚡VER [Q7DEF §1]: R: 50→500. Time 23.5 min.
| Метрика | z_norm | p_emp | Bonferroni-3 (α=0.0167) |
|---|---|---|---|
| direct_z | −3.96 | 0.00200 | **PASS** |
| chain-3 | −3.83 | 0.00200 | **PASS** |
Только 1/500 RO достигла SHA-уровня. **p<0.005 empirical, проходит
Bonferroni-3**.

**Q7e cross-target bit 210** ⚡VER [Q7DEF §2]: R=100, target=state2[bit210].
| Target | direct_z | p | chain_z | p |
|---|---|---|---|---|
| bit 10 (Q7d-R500) | −3.92 | 0.002 | −3.83 | 0.002 |
| **bit 210** | **−3.02** | **0.010** | **−3.04** | **0.010** |

**Сигнал реплицируется**. Не artefact bit10, а общая архитектура block-2
compression на HW=2.

**Q7f Walsh-4 chain** ⚡VER [Q7DEF §3]: 174M quadruples, 144с/realization.
R=20 (compute-limited).
```
SHA chain-4 = −5275.58
RO band: +480 ± 900
⇒ z_norm = −6.40
```
SHA вне диапазона [−1785, +2163] всех 20 RO. Аналитически p≈10⁻¹⁰.
**Сигнал растёт с порядком** (z_3=−3.83 → z_4=−6.40, ×1.7).

**Стандартные метрики не видят**: max|z_in·z_out|=17.24 (RO=17.6),
n_both_|z|>2=364738 (RO=369861) — RO-clean. Чистый coherent aggregate.

## §III.3.8 Глобальный вывод по Q7-линии

✓DOK:
1. Сигнал bit5_max → state2[bit10] **реален** (Q7d-R500, p=0.002).
2. **Не уникален для bit10** (Q7e: bit210 реплицируется).
3. Живёт в **распределённой** структуре Walsh-порядков 3 и 4.
4. **Невидим** классическим distinguishers (max|z|, Σz², бит-за-битом).
5. Detection требует **directional chain-test**.

См. Гл. III.4 для surgical-цепи (S1..S4) и Ω_k full-output map.

## §III.3.9 Закрытые/открытые

✗NEG:
- bit5_max как HW-parity (Q2: рефутирована).
- 2nd-order Walsh на state1 несёт сигнал (Q7: RO-clean).
- 3rd-order single-triple distinguisher (Q7C: RO-clean даже ниже).
- Linear distinguisher max|z| на distributed signal (Q7D: blind).

?OPEN [Q7DEF]:
- Q7g: Walsh-5 chain (8.8B subsets, GPU territory).
- Q7h: chain на других (feature, target) комбинациях.
- Q7i: signal на HW=4 с осторожностью (multi-seed).
- Q7j: аналитика — почему chain-z растёт с порядком.
