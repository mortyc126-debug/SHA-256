# Глава III.1. Теоретический фреймворк Info-Theory Fingerprinting

> TL;DR: ИТ-инструментарий для хэш-аналитики: min-entropy Ĥ_∞, Rényi, KL,
> Leftover-Hash, RO-модель + инварианты Δ_χ², Δ_I (Ω_k ⊘ROLL as detection tool, см. §III.7) и
> directional chain-test Chain_k. Chain_k — NP-оптимальный детектор
> распределённых сигналов, классический max|z| оптимален только в
> sparse-режиме.

## §III.1.1 Базис: classical IT для хэшей

**Min-entropy Ĥ_∞** ✓DOK [GUIDE §7]:
`Ĥ_∞(Y) = −log₂ max_y P(Y=y)`. Plug-in оценка: `−log₂(max_count/N)`.
Worst-case мера, нижняя граница для KDF/extractor security.

**Rényi H_α** ✓DOK [GUIDE §7]: семейство `H_α = (1/(1−α))·log Σ p_i^α`.
α=2 ⇒ collision entropy H_2 (несмещённая plug-in: `−log₂(Σ c_i(c_i−1)/N(N−1))`).
α=∞ ⇒ Ĥ_∞.

**KL-дивергенция** ✓DOK [GUIDE §4]: `D_KL(p‖q) = Σ p log(p/q)`.
Используется для null-vs-empirical comparison.

**Leftover Hash Lemma** ✓DOK [GUIDE §7]: для 2-универсальных хэшей
выход ε-близок к равномерному при output_len ≤ Ĥ_∞(X) − 2·log(1/ε).
SHA-256 эмпирически удовлетворяет (см. Гл. III.2), хотя 2-универсальность
не доказана.

**Random Oracle (RO) модель** ✓DOK: гипотеза, что h(X) ↔ uniform random
function. База для security proofs. Все наши тесты — измерение
deviation от RO predictions.

## §III.1.2 Birthday-формула для min-entropy конденсатора

⚡VER [IT-1]:
```
Ĥ_∞(SHA(X)↾k) ≈ min(k, H_∞(X)) − Δ(m, k, N)
Δ ≈ 0,                           m ≪ k и m·N ≪ 2^k    (no collisions)
Δ ≈ log₂(max_balls(m,k)),         m ≈ k                (birthday)
Δ ≈ 2 + log_e(N/2^k),            m ≫ k и N > 2^k       (sampling bias)
```
Формула универсальна: SHA-256 ≡ SHA-512 ≡ BLAKE2b при разрешении ±0.1
бит на 10 структурированных классах входов.

## §III.1.3 Новые инварианты: Δ_χ², Δ_I, Ω_k

**Δ_χ²(h, P_X, k)** ⚡VER [IT-1.3]: marginal-uniformity excess.
χ²(h(X)↾k) − E_RO[χ²]. Знак указывает направление: <0 ⇒ хэш
ГИПЕРРАВНОМЕРНЕЕ RO; >0 ⇒ концентрация. Функция от **маргинального**
P(Y_h).

**Δ_I(h, f, k)** ⚡VER [IT-3]: structural information excess.
`Δ_I := I(f(X); h(X)↾k) − E_RO[I(f(X); Y_RO)]`.
Размерность: бит. Аддитивна по независимым проекциям. Функция от
**совместного** P(f, Y_h).

**Дисcоциация** ✓DOK [IT-3]: SHA-256 даёт Δ_χ² ≠ 0 при Δ_I ≈ 0 для всех
тестируемых f (см. Гл. III.2 §2.3). ⇒ marginal и structural — независимые
ИТ-характеристики.

**Ω_k(h, f_in)** ⊘ROLL [IT-6; Phase 8C audit 2026-04]: заявленный k-order
Walsh-dominance invariant. Определение:
```
Ω_k = corr_b∈[output_bits] (direct_z(b), chain_k(b))
```
~~RO: E[Ω_k]=0. SHA-256 на (HW=2, bit5_max): Ω_3 = +0.98~~ ⊘ROLL: RO с same
chi_arr-basis protocol даёт Ω ~ SHA (0.978 vs 0.979). Не invariant.
См. UNIFIED_METHODOLOGY.md §III.7.

## §III.1.4 Directional chain-test Chain_k

**Определение** ✓DOK [IT-5G §1]:
```
z_S(g) = √N · (1/N) Σ_x σ(g(x)) · σ(χ_S(Y(x))),  σ(z) = 1−2z
Chain_k(Y, f, t) := (1/√N) · Σ_{|S|=k} z_S(f) · z_S(t)
```
Y — внутреннее состояние (state_r), f — input feature, t — output target,
χ_S(y) = ⊕_{b∈S} y_b.

**Parseval identity** ✓DOK [IT-5G §2]:
```
Z_direct = √N·⟨σ(f), σ(t)⟩ = Σ_k Chain_k
```
Direct-сигнал = сумма всех порядков. Decomposes signal into Walsh shells.

**Variance под H_0** ⚡VER [IT-5G §4]:
```
Var[Chain_k] ≈ M_k / N,   M_k = C(n, k)
std[Chain_k] ≈ √(M_k / N)
```
Empirically: std(Chain_1)=0.04, std(Chain_2)=0.50, std(Chain_3)=3.79
для n=256, N=130816. Theoretical 1:11.3:104, observed 1:12.5:95. **Match
within 10%**.

## §III.1.5 NP-оптимальность chain-test

**Теорема** ✓DOK [IT-5G §5]: при альтернативе с **uniform-distributed**
сигналом μ_S = const по 𝒞_k размера M_k:
```
T_NP = Σ_S (μ_S/σ_S²) · Ŵ_S(f)·Ŵ_S(t) ∝ Chain_k
```
⇒ Chain_k = Neyman-Pearson optimal для uniform-distributed alternative.

При sparse alternative (μ_{S*} = μ, others = 0): NP-optimal — `max|z_S|`
с Bonferroni-loss.

**Когда max|z| vs Chain_k** ⚡VER [IT-5G §3]:
- Sparse signal (один S* доминирует): max|z_S| лучше.
- Distributed coherent signal (M субсетов с малыми μ_S, согласованные знаки): Chain_k лучше.
- Symmetric агрегаты (max|z|, Σz²) **strictly dominated** Chain_k для distributed: дискардят знаковую информацию.

**Асимптотика для distributed signal** [IT-5G §3]:
- Chain_k: signal ε·√M против σ √M ⇒ detectable
- max|z|: signal ε/√M на ячейку ⇒ undetectable
- Σz²: signal M·(ε/√M)² = ε² ⇒ обычно undetectable для малого ε

## §III.1.6 Связь со standard ИТ

✓DOK [IT-5G §10]:
- **Parseval-Bessel** на {0,1}^n: Chain_k — частичная Parseval-сумма.
- **Walsh-Hadamard transform**: Chain_k — dot product в Walsh-базисе.
- **Higher-order differential cryptanalysis** (Knudsen, Biham): Chain_k —
  coherent-integral analogue (классический использует one specific S,
  Chain_k суммирует все).
- **Hoeffding decomposition of U-statistics**: Chain_k — signed U-statistic
  порядка 2k на state-битах.

Chain_k = Hoeffding-decomposition-based coherent detector dual to classical
max-based detector.

## §III.1.7 Архитектура IT-фреймворка для SHA-аналитики

```
INPUT (структурированный X) ─────────────────────────┐
                                                      │
[block 1: r=0..64 rounds] ── chain_k(r) evolution ────┤
       │                                              │
       ↓ state_r                                      │
   ┌───┴───┬─────────┬─────────┐                     │
   │ Δ_χ² │  Δ_I    │ chain_k │ Walsh-spectrum probes│
   └───┬───┴─────────┴─────────┘                     │
       │                                              │
[block 2 compression]                                 │
       │                                              │
       ↓                                              │
OUTPUT y = h(X) ─── Ω_k(h, f) — full-output map ─────┘
```

Каждая ИТ-метрика отвечает на собственный вопрос:
- Ĥ_∞ → "сколько worst-case randomness?"
- Δ_χ² → "сколько marginal-deviation от uniform?"
- Δ_I(f) → "сколько структурной инф-и о f протекло?"
- Chain_k → "когерентен ли k-shell input↔output?"
- Ω_k → "доминирует ли k-shell в round-функции?"

## §III.1.8 Открытые теоретические задачи

?OPEN [IT-5G §9]:
- T1: closed form Cov[Chain_k, Chain_{k'}] под H_0 с bit-correlation.
- T2: характеризация signal topology (uniform/sparse) из дизайна хэша.
- T3: lower bound на Chain_k SNR для данного Walsh-спектра.
- T4: universality class — для каких (h, P_X) Chain_k имеет асимпт. форму.

См. Гл. III.5 для bridges с Томами I/II и закрытыми вопросами.
