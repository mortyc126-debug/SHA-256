# Приложение: Открытые вопросы

Что НЕ закрыто и требует работы. Упорядочено по приоритету (фронтьерные → далёкие).

## ФРОНТИР (приоритет 1 — ближайшая сессия)

### Backward shortcut extension
- **?OPEN** Beyond ANF early-verify (7.6× cumulative) — пока потолок [§132, §133]
  - Валидация §133 показала: §130 был optimistic, реальная picture более консервативна
  - Нужно: найти второй ortho-shortcut, не коррелированный с ANF и Φ

### MITM реализация
- **?OPEN** MITM O(2⁸⁰) через state[16] — теоретический П-210, нужен runnable code
  - Meeting point: state[16] (середина SHA)
  - Требует: forward/backward search в state space, optimal matching

### Wang beyond r=17
- **?OPEN** Extension Wang-chain через schedule barrier r=17
  - Барьер = T_BARRIER_EQUALS_SCHEDULE (schedule barrier + 1)
  - Sol_17 плотность neutral bits: точно ≥ 2⁹⁶, но стоимость обхода неизвестна [П-101]

### ~~Ω_k cross-hash~~ ⊘ROLL [UNIFIED §III.7]
- ~~?OPEN Применение Ω_k инварианта к SHA-3/BLAKE/Keccak [IT-6]~~
- Phase 8C audit (2026-04) показал IT-6 claim — chi_arr artifact
  (RO same protocol даёт Ω=0.978 vs SHA 0.979). Направление закрыто как
  dead-end. Любая cross-hash extension воспроизведёт artifact.

## ПРИОРИТЕТ 2 — среднесрочные

### Signal block-2 amplification
- **?OPEN** Механизм IT-4.S4 (block2 читает high-order state1 и амплифицирует) можно использовать?
  - Если да → multi-block distinguisher сильнее single-block
  - Требует: тест на >2 блоков, quantifier amplification

### Chain-test vs quantum
- **?OPEN** Directional chain-test против quantum distinguishers [IT-5G]
  - NP-оптимальность доказана для classical, quantum unknown

### P-bit + phase + s-bit synergy
- **?OPEN** Формальная математика supersymmetric combinatoric [§54-55]
  - §55 S-bit unified, но не все комбинации исчерпаны

### Path-bit computational separation
- **?OPEN** Строгое доказательство separation от phase-bit [§80-84]
  - Hopf algebra / rough paths техника работает на small instances
  - Scaling к n>100 unclear

### Открытые теоремы от пользователя (v20)
- **?OPEN** Extension T_WANG_CHAIN на многоблок
- **?OPEN** Closed form T_DA_CHAIN (сейчас ∆EXP)
- **?OPEN** Обобщение T_DE17_UNIFORM на De_r r>17
- **?OPEN** Аналитика DW⊥ norm advantage ~1500× [П-88]

## ПРИОРИТЕТ 3 — структурные

### Bit primitive theory
- **?OPEN** 22+ ось бита — stochastic resonance, field bits кандидаты [§38-39]
- **?OPEN** 5-я метагруппа вне VAL/OP/REL/TIME [§40]
- **?OPEN** Upper bound при усилении D1-D5 — сейчас N=∞ под D1-D5
- **?OPEN** Bit-cosmos Platonic multi-axis формализация [§90-93]
- **?OPEN** P vs NP через bit-cosmos [§92] — эмпирически картирован, формализация нужна

### Carry phase space
- **?OPEN** W-atlas ΔW∝1/N_ADD обобщение на non-ADD функции [§123]
- **?OPEN** Open 119-C — Φ-inverter fails на конкретных instance, но diagonal conjugacy универсальна [§120]
- **?OPEN** Spectral basis carry (3D HMM 8 мод) применимость на real SHA L=32 [§118 ✗NEG opened question]

### Принцип Макро-Скорости
- **?OPEN** Нетривиальные макро-координаты с shortcut [§124-130]
  - Scalar закрыто ✗NEG, vector k=32 закрыто ✗NEG
  - ANF дал shortcut §127 → есть ещё?

## ПРИОРИТЕТ 4 — дальние

### Формальная теория
- **?OPEN** Аксиоматическая теория ★-Algebra и BTE Theory (совместимость) [§190, §225]
- **?OPEN** Category-theoretic формализация осей [§27]
- **?OPEN** GPK-моноид как алгебра без каскада [§192]
- **?OPEN** Интенсиональная рамка {С,П,Н,Д} как decision procedure [§211]

### Superbit frontier
- **?OPEN** SuperBit и P/NP граница [§68] — спекулятивная связь
- **?OPEN** σ vs Free Energy regime detection generalization [§77] — beyond financial time series

### Связь с физикой
- **?OPEN** CHSH violation phase-bits → experimental reproducibility [§31]
- **?OPEN** GHZ discrimination exp. scaling vs decoherence
- **?OPEN** Spatial-holonomy bit (Wilson loops) как gauge primitive [§22]

## Сводка open questions по категориям

| Категория | Количество |
|---|---|
| Backward shortcut / MITM / Wang | 5 |
| Info-theory cross-hash | 3 |
| Bit primitive structure | 5 |
| Carry phase space | 3 |
| Формальная математика | 5 |
| Физические intersection | 3 |
| **ИТОГО** | **~24 открытых** |

## Методологическое правило

Для любого open question: перед повторной атакой проверить, что похожий вопрос не закрыт в `05_negatives.md`. Многие "естественные" идеи уже исчерпаны.
