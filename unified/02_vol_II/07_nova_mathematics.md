# Глава II.7. Новая математика — ★-Algebra, BTE, Nova, GPK, интенсиональная рамка

> TL;DR: ★-Algebra (18 теорем): ★(a,b)=(a⊕b,a&b), η=0.189, τ★=4, термостат E[Δ]=-(δ-32). BTE Theory (12 теорем): bi-temporal element, layer rank=2R-1, degree Fibonacci, R_full=n_msg+2. Carry = расширитель 512→589 бит, обратное стоит 2^77. M-мир (степень 32) vs c-мир (степень 2). Мерсенн-декомпозиция: 592 бинарных коррекции. Q∩T наивный 2^144.

## §II.7.1 ★-Algebra: определения

**★-определение** ✓DOK [exp95] (5000/5000):
```
★(a, b) = (a ⊕ b, a & b)
a + b = π_add(★(a, b))
```

**Расширения:**
| Operation | Definition |
|-----------|-----------|
| ★(a,b) | (a⊕b, a&b) |
| ★²(a,b,c) | (a⊕b⊕c, Maj(a,b,c)) — Maj = ★²-carry |
| ★₃ | GKP ternary automaton (G→1, K→0, P→carry_in) |
| ★⁻¹ | Dual: (a+b, a&b), δ(SUM)=2·δ(AND) |
| Sub-bits | {0_K, 0_P, 1_P, 1_G} — ниже бинарного уровня |

## §II.7.2 ★-Algebra константы

| Constant | Value | Meaning |
|----------|-------|---------|
| η | 0.18872 = (3·log₂3)/4−1 | Spectral gap GKP (λ₂=1/3) |
| **τ★** | **4 раунда** | Mixing, equilibrium, carry depth |
| Carry rank | 3⁵ = 243 | Тернарная структура |
| α (термостат) | 0.69 | Reversion: δ[r+1]=0.69·δ[r]+9.92 |
| δ* | 32 = 64/2 | Точка равновесия |

## §II.7.3 18 ★-теорем

- **★-1..★-3** ✓DOK [exp136]: Carry-Free Bit Preservation; ROTR Moves Invariant; Ch/Maj Preserve Invariant.
- **★-4** ⚡VER [exp136] Shift Register Cascade: δ_XOR=0 на a[r] → d[r+3]. Слова умирают a@r+2, b@r+3, c@r+4, d@r+5.
- **★-5** ✓DOK [exp123] Three Nonlinearity Sources: carry, Ch, Maj.
- **★-6** ✓DOK [exp138] Incompatibility of + and ROTR.
- **★-7** ✓DOK [exp138] Instant Collapse: ★-инварианты умирают в первом раунде с δW≠0 (corr 1.0→0.0).
- **★-8** ⚡VER [exp136]: |I_r|=256-6.5r для r≤20; затем 128.
- **★-9** ✓DOK + ⚡VER [exp140] (2000/2000): δCh=δe&(f⊕g), δMaj=δa&(b⊕c). α=0.500.
- **★-10** ✓DOK [exp150]: x³²+1=(x+1)³² в GF(2). Σ инвертируемы.
- **★-11** ✓DOK [exp151] Two-Ring Structure: ROTR — автоморфизм Ring 1+2.
- **★-12** ⚡VER [exp156] Chain Spectrum: corr=0.487 с расстоянием.
- **★-13** ✓DOK [exp157] τ★=4 = смерть XOR-канала = M₃ saturation = carry depth.
- **★-14** ⚡VER [exp158] M₃ Equilibrium: GKP G:K:P=1:1:2; M₃ entropy=3/2.
- **★-15** ⚡VER [exp176, exp198] (N=20000) Structural Penalty: P(dH<k|structured) ≤ P(...|random).
- **★-16** ⚡VER [exp185-189] Thermostat: δ[r+1]=0.69·δ[r]+9.92+noise. Noise: 32% δa×δe (corr=-0.568); 68% white σ=4.0.
- **★-17** ⚡VER [exp192]: ротации {2,6,11,13,17,18,19,22,25} → corr≈0.07-0.09 на r=20+, не угасают.
- **★-18** ⚡VER [exp193]: 12 ротаций + суммы/разности покрывают ВСЕ 32 битовых расстояния.

## §II.7.4 7 стен SHA-256 (★-Algebra)

| # | Wall | Источник |
|---|------|----------|
| 1 | Schedule Full Rank (1536×512, rank=512) | exp199 |
| 2 | Thermostat (E[Δ]=-(δ-32)) | exp186 |
| 3 | Structural Penalty | exp198 |
| 4 | 20-Round Decorrelation | exp112, exp136 |
| 5 | White Noise Floor (σ=4.0) | exp189 |
| 6 | Carry SNR=1:1 | exp196 |
| 7 | Architectural Saturation (12 ротаций → 32 distances) | exp193 |

## §II.7.5 BTE Theory — Bi-Temporal Element

**Определение** ✓DOK [Раздел 225]: BTE — объект с двумя типами эволюции:
- **Macro-time** (round r=0..R-1)
- **Micro-time** (bit k=0..n-1)

SHA-256 = BTE с n=32, R=64, 8 регистров, ротации {2,6,11,13,22,25}.

## §II.7.6 12 BTE-теорем

**T1 Layer Rank** ✓DOK: rank(Layer(0)) = 2R-1. Универсально для любого 8-register shift со створочным coupling.
- Следствие: 4-layer структура SHA-256: bit 0..3 даёт +127 ранг, bit 4 → +4, итого 512 = 4×127 + 4.

**T2 Quadratic Deficit** ⚡VER: Ch/Maj дают ~0.022 бит/раунд deficit. Для SHA-256: ~1.4 бит. Negligible.

**T3 Carry Nilpotency** ✓DOK: C_y^n(x) = 0 для всех x,y. Доказательство индукцией (или: J_C нижнетреугольная → J^n=0).

**T4 Carry Binomial Rank** ✓DOK + ⚡VER: rank(J_{C_y}|_{x=0}) = HW(y[0..n-2]); |{y: rank=k}| = 2·C(n-1,k).

**T5 Carry Cocycle** ✓DOK: E(a,b,c) = E(a,b) ⊕ E(a+b,c). Carry = 1-cocycle в H¹(Z/2ⁿ; GF(2)ⁿ); H¹=0 (тривиальный).

**T6 Hessian Transition** ⚡VER: R_H ≈ 0.75·n_msg = 6/8 (NL_regs/total). SHA-256: R_H≈12.

**T7 Full Randomization** ⚡VER: R_full = n_msg + 2. SHA-256: R_full=20. Safety margin 64/20 = 3.2×.

**T8 Rotation Necessity** ⚡VER: Rotation = единственный НЕОБХОДИМЫЙ движитель. Ch/Maj и carry взаимозаменяемы. D2@R=16: Full=0.300, No Ch/Maj=0.350, No Rotation=0.000, No Carry=0.310. corr(n_rot, D2)=0.715; corr(Q_min, D2)=-0.659.

**T9, T10** — продолжение T8.

**T11 Degree Fibonacci** ⚡VER: d(r) = Fibonacci(r) ≈ φ^r. Ceiling round 15.

**T12 Monomial Spread** ⚡VER: R_full = max(coverage, n_msg, log_φ(n)) + 2.

## §II.7.7 Carry-rank, GPK-моноид (Раздел 192)

**Carry-rank=589/592** ✓DOK [Раздел 191]:
- Carry-out пространство: 589 бит (ранг)
- Полное число carry-out бит: 592 (нелинейные carry, изолированные)
- M-пространство: 512 бит
- P(случайный c достижим) = 2^{512-589} = 2^{-77}

**Carry = расширитель** ✓DOK: 512 → 589 бит (расширяющее отображение). Обратное = сужающее (589→512). P(обратимость) = 2^{-77}.

**GPK-моноид** ✓DOK [Раздел 192]: Sub-bit алгебра {K, P, G} ассоциативна, тождественна по P. Carry без каскада.

| Операция | Результат | Семантика |
|----------|-----------|-----------|
| K | Kill carry | Тушит |
| P | Propagate | Передаёт |
| G | Generate | Создаёт |

**6 теорем** ✓DOK: GPK ассоциативный, идемпотентный по K, тождественный P.

## §II.7.8 Мерсенн-декомпозиция (Раздел 191)

**T_MERSENNE_DECOMPOSITION** ✓DOK [Раздел 191]:
```
SHA-256 = Мерсенн-вычисление + Ch/Maj (степень 2) + 592 бинарных коррекции
```
В кольце Z/(2^32 − 1): сложение carry-свободное, линейное.

| | Z/2^32 (стандарт) | Z/(2^32−1) (Мерсенн) |
|---|------------------|----------------------|
| Carry | каскадные цепочки ~8000 бит | 592 бита, изолированные |
| Σ_0/Σ_1 | XOR ротаций | XOR ротаций |
| Ch/Maj | степень 2 | степень 2 |
| E[HW(Δcarry_out)] | — | 257/592 ≈ 43% |
| GF(2) ранг Δcarry_out | — | 570/592 |

## §II.7.9 M-мир / c-мир (Раздел 212)

**T_TWO_WORLDS** ✓DOK [Раздел 212]:

| Мир | Параметризация | deg | Геометрия | Стоимость |
|-----|----------------|-----|-----------|-----------|
| **M-мир** | M (512 бит) | 32 (полная) | Хаотична (random oracle) | 2^128 (birthday) |
| **c-мир** | c (448 carry-out бит) | **2** (квадратичная) | Гладкая | ??? |

**c-мир дискретен** ⚡VER [Раздел 213]: степень 32 → 2 (16× сокращение), но обратное — ДИСКРЕТНО. δc ≥ 121 для любого δM. Нельзя плавно двигаться от c к M.

**c-мир закрыт** ✗NEG [Раздел 214]: P(самосогласования) = 2^{-77}. Стоимость 2^77 → итого > 2^128.

**T_DEAD_ZONE** ✓DOK [exp178+, ★-Algebra]: Полное смешивание за 6 раундов, equilibrium r=7. Dead zone = раунды 8-64. δH=128±1 stable.

## §II.7.10 Q∩T Алгебра (Раздел 216)

**Определение** ✓DOK [Раздел 216]: Q∩T = пересечение:
- **Q**: 256 квадратичных GF(2) уравнений (SHA-256 при фикс. carry)
- **T**: 448 пороговых уравнений (carry-out = 1{a+b ≥ 2^32})
- 512 переменных (биты M)

**Текущий лучший наивный Q∩T:** ?OPEN — **2^144** (хуже birthday). Цель: < 2^128.

**Q∩T прототип** ⚡VER [Раздел 217]: На 8 раундах carry-out коллизии δH ≈ 3.3 бит/56 carry-out. Локальное преимущество.

**Масштабирование Q∩T** ✗NEG [Раздел 218]: Выигрыш ЗАТУХАЕТ exp(-0.45r). На полной SHA-256 — не лучше birthday.

## §II.7.11 Интенсиональная рамка {С,П,Н,Д} (Раздел 211)

**Алфавит структуры** ✓DOK [Раздел 211]: {С, П, Н, Д} — описание SHA-256 как **формулы** (не как функции значений).
- С: символьное смешение
- П: позиционное (ротации)
- Н: нелинейное (Ch/Maj)
- Д: дискретное (carry)

**Этапы построения:**
1-5. Алфавит, скелет, грамматика — ✓ построены.
6. Наполнение через carry-out (589 бит) — ✗NEG (расширяющее, P=2^-77).

**Створочное число** ✓DOK + ⚡VER [Раздел 202] (640K тестов, 0/29500 нарушений):
```
e[r] = a[r] + a[r-4] - T2[r-1]   (mod 2^32)
```
Следствие: e-последовательность полностью определяется a-последовательностью. SHA-256 = одна 8-порядковая рекуррентность в {a[r]}.

## §II.7.12 Carry×NLF Theory (Раздел 223)

**Два замка** ✓DOK [Раздел 223] (N=500): carry и NLF — независимые killers. Full=0; No carry=0; No NLF=0; No carry+No NLF=128 ALIVE. Минимальный killer: ЛЮБАЯ degree-2 + carry.

**Self-Cancellation** ✓DOK: Erasure 16/32 бит/round (50%). При c₁[k]=c₂[k]: x[k] DETERMINED; иначе ERASED.

**Deadpool Recovery** ✓DOK: e[r][k] восстанавливается через h на r+3 (100%). Blocker: нужен W[r+3].

**Идентичность** ✓DOK: Ch(x,y,z)⊕Maj(x,y,z) = z·¬y.

**Branching** ⚡VER (N=100K): Ch avg **884**, Maj avg **31**. 884^64 >> 2^128.

**128 = 4 × 32** ✓DOK: shift depth × word size. Первые 4 раунда erasure без Deadpool → architectural birthday.

## §II.7.13 Nova Cryptarithmetica (Раздел 215+)

**Гибридная система Q∩T** ✓DOK [Раздел 215]: c-мир SHA-256 = пересечение Q (квадратичная) ∩ T (пороговая). В M-мире слиты в степень 32; в c-мире РАЗДЕЛЕНЫ.

**Минимальная сложность** ?OPEN: Стандартные методы (birthday, Gröbner, threshold optimization) не предназначены для пересечения Q∩T. Создание решателя Q∩T = открытая задача.

См. §II.6 (carry rank, distinguisher) для эмпирического подтверждения; §II.8 для открытых вопросов.
