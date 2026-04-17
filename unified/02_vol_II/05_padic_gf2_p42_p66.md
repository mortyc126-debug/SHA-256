# Глава II.5. p-адика, GF(2), Якобиан П-42..П-66

> TL;DR: Hensel lifting не работает для SHA-256 (T_HENSEL_INAPPLICABLE). Якобиан над GF(2) имеет абсолютный инвариант rank=5 (T_RANK5_INVARIANT). Бесконечная башня каскада slope=1.000 до k=24 (T_INFINITE_TOWER). Free-start GF(2) бижекция rank=r. Артефакты T_FREESTART_* отозваны (DW=0 тривиально).

## §II.5.1 T_HENSEL_INAPPLICABLE — конец Hensel-программы

**T_HENSEL_INAPPLICABLE** ✗NEG [П-43, ПОДТВЕРЖДЕНА П-47]: Классический Хенсель-подъём 2-адической гладкости неприменим к SHA-256 — гладкость нарушается на k≥2.

**Корневая причина:** нелинейные carry в Σ1 нарушают 2-адическую гладкость уже на втором уровне.

**T_FREESTART_NONSMOOTH** ✓DOK [П-68]: Hensel-инвариант нарушается на k=2 через Sigma1 carry даже в free-start модели.

**T_HENSEL_NON_SURJECTIVITY** ✓DOK [П-51, П-54]: Проекция π: Sol_{k+1} → Sol_k несюрьективна.

**T_HENSEL_CASCADE_INAPPLICABLE** ✓DOK [П-86]: Hensel-каскад неприменим для k≤7.

**T_NEWTON_INAPPLICABLE_WANG** ✗NEG [П-96] (0/10000): Newton-метод неприменим к Wang.

## §II.5.2 T_NONLINEAR_MATRIX_FAILS — 2D подъём провален

**T_NONLINEAR_MATRIX_FAILS** ✗NEG [П-44] (0/100): Исчерпывающий побитовый подъём {0,1}² для SHA-256 даёт 0 решений.

**T_2D_BARRIER** ✗NEG [П-44]: 2D barrier подтверждён.

## §II.5.3 T_JACOBIAN_RANK и его развитие

**T_JACOBIAN_RANK** ⚡VER [П-42]: Якобиан 15×16 ∂(Da3..Da16,De17)/∂(DW0..DW15) имеет rank=15 (полный).

**T_DE17_IN_IMAGE** ⚡VER [П-42]: De17 в образе якобиана.

**T_JACOBIAN_RANK_DIST** ⚡VER [П-46, П-57]: rank ∈ {14,15}, P(15)≈52%; rank падает на бите 1-2 для DW0.

**T_JACOBIAN_RANK_PREDICTS_SOL1** ✓DOK + ⚡VER [П-57] (1000 сидов): Ранг якобиана предсказывает |Sol_1|. Феномен 9% объяснён (артефакт жадного поиска).

## §II.5.4 T_RANK5_INVARIANT — абсолютный инвариант

**T_RANK5_INVARIANT** ✓DOK + ⚡VER [П-58] (100 сидов): rank_GF(2)(J_{5×15}) = **5** — абсолютный инвариант для всех (W0,W1).

**Следствие:** |Sol_1| = 1024 = 2^10 гарантировано (5 свободных бит → 2^5; через 2 параметра → 2^10).

**T_75_EXPLAINED** ✓DOK [П-60]: Excess P=75% (vs 63% random) объясняется T_JACOBIAN_RANK_PREDICTS_SOL1 + Period-3 структурой SHA-256.

## §II.5.5 T_INFINITE_TOWER — бесконечная башня

**T_CASCADE_UNIQUENESS** ✓DOK [П-53]: Da_{pos+1}(v) линейна с slope=+1. Главная теорема П-53.

**T_INFINITE_TOWER** ⚡VER [П-59, П-67B] (200 сидов × 24 уровня): slope = 1.000. Гипотеза height_2(SHA-256) = ∞.

**Эволюция оценки height_2** (для ясности):
1. [П-52] **T_HEIGHT_SHA256 = 6** ⊘ROLL — **артефакт жадного поиска, ОПРОВЕРГНУТА**.
2. [П-53] **T_GREEDY_BARRIER_ARTIFACT** ✓DOK: height_2 ≥ **11** (пересмотр после опровержения).
3. [П-59] **T_INFINITE_TOWER** ⚡VER: slope=1.000 до k=**24** (200 сидов каскадным методом) → height_2 ≥ 24.
4. [П-67B] Расширено до k=**32** (после исправления freestart артефакта) → height_2 ≥ 32, **финальная оценка**.

```
P(Sol_k ≠ ∅) ≈ 1/2^k
height_2 ≥ 32 (финал)
```

**T_FREESTART_E_COLLISION_ITER** ⚡VER [П-67A] (20/20, ≤3 iter): Free-start e-коллизия за ≤3 итерации.

**T_REGISTER_SHIFT_CHAIN** ✓DOK [П-67]: 3-сдвиговый регистр в Wang/cascade-режимах.

## §II.5.6 T_GF2_BIJECTION

**T_GF2_BIJECTION** ⚡VER [П-61] (30 сидов × 15 значений r): В free-start XOR/GF(2) модели rank(L_r) = r для r=1..64.

**T_GF2_SATURATION** ⚡VER [П-61]: GF(2)-насыщение.

**T_FREESTART_E_GF2_NONTRIVIAL** ⚡VER [П-70B] (500/500): Free-start E-GF(2) даёт нетривиальные решения для r=16, 32.

## §II.5.7 T_WORD_SATURATION — бит vs слово

**T_WORD_SATURATION** ⚡VER [П-79]: На уровне битов 63%, на уровне слов **94%**. Разрыв GF(2)/Z_{2^32} измерен.

**Следствие (Правило 11):** свойство верное на уровне битов (37% нулей) может давать P≈1 на уровне слов из-за насыщения. Проверять на уровне слов перед практическим применением.

**T_BIT_DEAD_ZONE** ⚡VER [П-80] (P=0.999): Битовые мёртвые зоны структурно реальны.

**Правило 12 (П-80):** бит-уровневые свойства реальны и структурны, могут не давать преимущества на уровне слов напрямую, но открывают гибридные алгоритмы.

## §II.5.8 Битовая структура (П-77, П-78)

**T_BIT_LINEAR_R1** ⚡VER [П-77]: e_1[b] = W[0][b] (бит-линейность раунда 1).

**T_SCHEDULE_CLUSTER** ⚡VER [П-77]: Schedule clustering структура.

**T_SCHEDULE_SPARSE** ⚡VER [П-78]: Schedule sparse-структура.

**T_CARRY_INDEPENDENCE** ⚡VER [П-78]: Carry-зоны независимы.

## §II.5.9 Отозванные артефакты

**T_FREESTART_INFINITE_TOWER** ⊘ROLL [П-62]: Артефакт DW=0 тривиально (De_r(0)=0). Исправлена в П-67/П-70.

**T_FULLSTATE_FREESTART** ⊘ROLL [П-63..П-64]: Артефакт.

**Замена:** T_STANDARD_SELFMAP (П-65, исправление T_STANDARD_FULLSTATE_TOWER) и T_STANDARD_COLLISION_BARRIER (П-66): P = 2^{16-8r}, стандартная модель.

## §II.5.10 T_CASCADE_DW_CORRECT, T_GF2_DW_TRIANGULAR

**T_CASCADE_DW_CORRECT** ✓DOK [П-84]: Корректировка каскада DW: 14 нулей De2..De16=0 за O(1).

**T_GF2_DW_TRIANGULAR** ⚡VER [П-85]: rank=14 в треугольной GF(2)-структуре DW.

**T_64BIT_CASCADE_NEGATIVE** ✗NEG [П-87]: 64-битный каскад невозможен.

## §II.5.11 mod-8 каскад

**T_MOD8_CASCADE_EXISTS** ⚡VER [П-51]: Sol_3 ≠ ∅ (P≈25%). Жадный mod-8 каскад существует.

## §II.5.12 Аудит чистоты теорем (П-69)

| Теорема | Статус | Замечание |
|---------|--------|-----------|
| T_RANK5_INVARIANT (П-58) | ✓ Чист | DW[0]=1 фиксирован |
| T_GF2_BIJECTION (П-61) | ✓ Чист (ранг) | |
| T_JACOBIAN_RANK_PREDICTS_SOL1 (П-57) | ✓ Чист | |
| T_INFINITE_TOWER (П-59) | ✗ Артефакт d=0 | Исправлен П-67B |
| T_FREESTART_INFINITE_TOWER (П-62) | ✗ Артефакт | De_r(0)=0 тривиально |

**Чистые теоремы (П-69):** T_RANK5_INVARIANT, T_GF2_BIJECTION (ранг), T_GLOBAL_BARRIER, T_REGISTER_SHIFT_CHAIN, П-13 (15 нулей), T_STANDARD_COLLISION_BARRIER, T_FREESTART_NONSMOOTH.

## §II.5.13 Сводная классификация подходов

| Класс | Башня | Теорема |
|-------|-------|---------|
| Аддитивный, 1D | Нет (height=∞) | T_INFINITE_TOWER |
| XOR/GF(2), free-start | Нет (rank=r) | T_GF2_BIJECTION |
| Hensel/Newton | Несюрьектива | T_HENSEL_NON_SURJECTIVITY |
| 2D нелинейный | Барьер | T_2D_BARRIER |

См. §II.3 для каскада (P-13: 15 нулей за 2^32); §II.4 для Wang-цепочки; §II.6 для MILP/SAT, нейросетевого подхода.
