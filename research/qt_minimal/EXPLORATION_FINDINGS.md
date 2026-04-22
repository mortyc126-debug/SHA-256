# True research exploration — findings (2026-04)

**Дата**: 2026-04-22
**Отправная точка**: R-инвариантность Jacobian carry deficit, найденная в cohomology probe.
**Вопрос**: есть ли structural handle на carry kernel, который методичка пропустила?

## TL;DR

Обнаружено **чистое алгебраическое соотношение**, которое методичка знает имплицитно, но не формализовала так:

> **Any input flip `v ∈ ker(J_carry)` at last round W produces deterministic output flip of exactly 2 output registers (a + e) at the same bit position k.**

Это **переформулировка Wang-chain структуры** на языке линейной алгебры carry-map. Не новый handle атаки, но более прозрачная формулировка известного механизма.

## Проведённые эксперименты

### 1. Persistent kernel probe
Для n=8,12,16, R=1..3 интерсектировали ker(J_r) across rounds.
- Результат: intersection ≈ 1-3 dim, но **≥90% в содержимом** = MSB последнего W-слова (тривиальная арифметика mod 2^n)
- State-dependent extras варьируются anchor-to-anchor

**Вывод**: персистентный kernel — в основном тривиален (MSB effect). Не структурный handle.

### 2. Kernel dim distribution vs R_total
Paттерн: `kernel_dim(round r, R_total=T) ≈ n·(T-r-1) + intrinsic_const`.

Объяснение: W[r+1..T-1] бит flip не могут affect carries at round r (каузальность). Эти n·(T-r-1) бит автоматически в kernel. Intrinsic (state-dependent) ≈ 3 для n=16, 2 для n=8 — тот же паттерн что §II.8.3 Jacobian deficit.

**Вывод**: "R-инвариантность" — это просто intrinsic kernel на последнем раунде, не некий глобальный инвариант.

### 3. Output invariants probe  
Проверили: existуют ли v ∈ ker(J_carry) такие что v ∈ ker(J_output)?
- Результат: **0 total invariants** среди всех тестов. Все carry-kernel вектора меняют output.

**Вывод**: total round-function invariants отсутствуют. Хорошая news для SHA (security), bad news для attack.

### 4. Linear invariant test (ключевое открытие)
Для W_A, W_B различных anchors, нашли **shared kernel vectors** v ∈ ker(J_carry[A]) ∩ ker(J_carry[B]).
Для каждого такого v проверили: v·J_out[A] == v·J_out[B]?

- **100% state-independent** (50/50, 33/33, 36/36, 55/55, 39/39 во всех тестах)
- **Универсальный паттерн**: flip W_last[bit k] → output flip (register 0, bit k) + (register 4, bit k)

## Интерпретация паттерна

SHA round: `a' = T1 + T2`, `e' = d + T1`.
- T2 не зависит от W
- T1 содержит W как последний аргумент additive цепочки
- Если flip W[bit k] с сохранением carry (v ∈ ker) → T1 меняется только bit k
- → a' и e' оба меняются bit k → ровно эти 2 бита output изменяются

Это **фундаментальная линейная симметрия** SHA round function. Методичка знает это как:
- T_DCH_EXACT (§II.2.4): δCh = δe & (f⊕g)
- Wang-chain P=1.0 уравнения (§II.4)
- T_STATE17_STRUCTURE (§II.4.11): δstate после Wang имеет вид (δa, 0, 0, 0, δe, 0, 0, 0)

Наша формулировка БОЛЕЕ АБСТРАКТНАЯ: любой input flip, лежащий в carry-kernel, даёт чистую линейную diff. Это **общий принцип, объединяющий Wang-chain и T_DCH_EXACT** в одно утверждение.

## Почему это не новый attack vector

1. **Carry-kernel ограничен 1-5 bits** на anchor (MSB + state-dep extras)
2. **Intersection across anchors = MSB только** (тривиально)
3. **Применение Wang-chain exactly exploits this**: находит W такие, что specific flips остаются в carry-kernel
4. **r=17 barrier** — это ровно momento, когда carry-kernel на всех регистрах одновременно исчерпан для non-trivial flips

## Новое достижение (методологическое)

Мы связали:
- R-инвариантность deficit (наша находка §II.8.3)
- T_CH_INVARIANT / T_DCH_EXACT (методичка §II.2)
- Wang-chain механизм (§II.4)
- T_STATE17_STRUCTURE (§II.4.11)

В **ОДНУ линию рассуждений**: всё это — проявления одного и того же facta, что feed-forward регистры (a, e) shares T1, и carry-preserving input flips создают детерминированный bit-level diff.

## Решение по направлению

**⊘SCOPED Q_CARRY_LINEAR_INVARIANT**: "Structural linear invariant from carry kernel" — мы его формализовали, но это переформулировка известного. Новая math не получится на этом направлении. Если кому-то хочется формально писать теорему "ker(J_carry) → fixed output diff (registers a+e, same bit position)" — это чистое следствие feed-forward + carry-chain additive структуры.

## Что действительно новое осталось

После ЭТОГО раунда тоже закрыто. Подведём итог:

| Направление | Судьба |
|---|---|
| ~~Q∩T framework~~ | ⊘SCOPED |
| ~~Cohomology probe~~ | ⊘SCOPED (нашли R-инвариантность) |
| ~~MITM O(2⁸⁰)~~ | ⊘SCOPED |
| ~~ANF early-verify ext~~ | ⊘SCOPED |
| ~~Persistent kernel~~ | ⊘SCOPED (причина: causality, не invariant) |
| ~~Carry-linear-invariant formulation~~ | ⊘SCOPED (reformulates known Wang structure) |

**Остались открытые**:
- Wang extension за r=17 — методичка 1300+ экспериментов не пробила
- Block-2 signal amplification [IT-4.S4]

Наше exploration подтверждает: SHA-256 round function НЕ имеет скрытых структурных симметрий сверх уже известных. R-инвариантность carry kernel — это причина, почему Wang-chain существует как атака, а также почему она не расширяется за r=17 (кернел исчерпан).

## Artifacts

- `persistent_kernel.py` — intersection of per-round kernels
- `kernel_distribution.py` — distribution analysis
- `output_invariants.py` — total-invariant search
- `linear_invariant.py` — state-independence test
- `EXPLORATION_FINDINGS.md` — этот отчёт
