# Приложение: Отрицательные результаты (ЗАКРЫТО)

Все направления, которые были исчерпаны или опровергнуты. Не повторять.

## Том II — SHA-256 дифференциальный криптоанализ

### Алгебро-аналитические
| Теорема | Что пробовали | Результат | Ссылка |
|---|---|---|---|
| **T_HENSEL_INAPPLICABLE** | 2-адический Hensel lift на SHA | Гладкость нарушена при k≥2, lifting не работает | ✗NEG П-43 |
| **T_NONLINEAR_MATRIX_FAILS** | Исчерпывающий 2D подъём нелинейной матрицы | 0/100 решений | ✗NEG П-44 |
| **T_BOOMERANG_INFEASIBLE** | Boomerang-атака на SHA-256 | HW≈64, нет структуры для склейки | ✗NEG П-29 |
| **T_ROTATIONAL_NEGATIVE** | Rotational differentials | Не дают преимущества над additive | ✗NEG П-35 |
| **T_XOR_DIFFERENTIAL** | XOR-дифференциал как primary | Недостаточен для полного каскада | ✗NEG П-19 |
| **T_MILP_INFEASIBLE_17** | MILP для r=17 | k≤16 мгновенно, k=17 timeout | ✗NEG П-34 |
| **T_HYBRID_CASCADE** | Смешанные XOR+additive цепи | Не складываются когерентно | ✗NEG П-22 |
| **T_2D_BIRTHDAY_NEGATIVE** | 2D birthday на SHA-256 | Эмпирически опровергнут | ✗NEG П-27C |

### Многоблочность
- **Multi-block predict_delta** ✗NEG v8 — дифф. предсказание не переносится через block boundary
- **Wang extension beyond r=17** ✗NEG — stuck at schedule barrier r=17
- **Multiblock Wang-chain** ✗NEG — P=1.0 work только для одного блока

### Структурные негативы
- **Ротационный аттрактор** ✗NEG П-36..П-41 — 571 строк исследований, гипотеза множественных аттракторов не подтвердилась
- **P vs Keccak comparison** — SHA-256 менее диффузен на бит-уровне (⚡VER v8 Гипотеза C подтверждена, но это не атака)

### Отозванные артефакты (⊘ROLL)
| Теорема | Ошибка | Исправление |
|---|---|---|
| T_FREESTART_INFINITE_TOWER | DW=0 тривиально (П-62) | → П-67 корректировка |
| T_FULLSTATE_FREESTART_TOWER | Артефакт (П-63-64) | отозвана |
| T_DA_ODD_BIAS | Stat. fluke (П-106) | → П-108 T_DA_BIAS_ZERO |
| T_HEIGHT_SHA256=6 | Опровергнута (П-52) | → П-53 height_2≥11 |

## Том I — Математика бита

### Оси-кандидаты, НЕ прошедшие D1-D5
- **Memristor** ✗NEG §39 — не примитив, композиция существующих
- **Field bits (reaction-diffusion)** ✗NEG §39 — tentative, не прошла D4 (witness)
- **Σ-bit (super-primitive attempt)** ✗NEG §61 — недостаточно мощен, не превосходит отдельные оси
- **Chaos-configurable bit noise fragility** (§37) — ∆EXP с оговоркой: полезен для chaos computing, но хрупок к шуму

### S-bit на задачах оптимизации
- **S-bit на QUBO/MAX-SAT** ✗NEG §59 — не превосходит классические solvers
- **S-bit на больших n>100** — quantum выигрывает (честное сравнение §58)

### Бенчмарки и артефакты
- **Tropical BF numpy vs pure Python** ✗NEG-correction §34→§35 — 6.25× speedup был python artifact, против scipy исчез
- **Session 3 Platonic "bits не стираются"** — правильная формулировка: трансформируются, не elimintируются §94

### Avalanche wall
- **Direct R=1 real SHA algebraic inversion** ✗NEG §111 — avalanche = real wall, не инвертируется напрямую координатными уравнениями

### Координатный буст
- **Scalar МС-координаты** ✗NEG §125 — все 16 кандидатов NULL (avalanche complete за 1 раунд)
- **Vector валидация k=32** ✗NEG §126 — ALL NULL включая k=32, методологическое открытие
- **Stacked disqualifiers** ✗NEG §131 — statistical filters margins ≈3-5% (маргинально)

### Backward shortcut
- **Φ-prior alone** — ∆EXP §130, ограничен (validation §133 уточнила recall)
- **Linear regression speedup ceiling** — ∆EXP §130-B

### Plurality
- **Universal framework для 13+ primitives** ✗NEG §29 — не существует (но 6 sub-frameworks есть)
- **Минимальный вычислительно-значимый субстрат** ✗NEG §30-D6 — mixed negative

## Том III — Info-Theory Fingerprinting

### Linear methods
- **max\|z\| classical linear distinguisher** ✗NEG IT-5G — недостаточен для distributed signals (signal в high-order only)
- **2nd-order Walsh на state1** ✗NEG IT-4.Q7 — RO-clean по 1st и 2nd order, >99% сигнала в \|S\|≥3

### Hypothesis rejection
- **bit5_max = HW-parity** ✗NEG IT-4.1 — эффект exclusive HW=2, не чётность (exhaustive 130K)
- **bit5 эффект не уникален** ✗NEG IT-4.Q (Q2) — другие биты word не дают signal, bit5=word-parity специфично
- **Q3b HW=4 reproducibility** ✗NEG — был cherry-pick, не воспроизводится
- **χ²-fingerprint = leak** ✗NEG SHARP — на самом деле гиперравномерность SHA-2, не утечка (anti-leak)

### Cross-scope
- **Signal на SHA-1/SHA-512** ✗NEG IT-4.S3 — ТОЛЬКО в SHA-256 (специфичный artefact design)
- **Round resilience** ✗NEG IT-4.S2 — signal decays к r=20 до RO-clean, не проходит polный stack

## Итог по удалённым/закрытым направлениям

**Общее правило**: если направление помечено ✗NEG — в повторной сессии НЕ пытаться reapply. Каждое закрытие — это сэкономленные часы.

**Направлений закрыто**: ~25 (Том II), ~10 (Том I), ~6 (Том III) = **~41 закрытое направление**.

**Важно**: отрицательный результат ≠ бесполезный. Многие из них ограничивают пространство поиска и указывают на структурные свойства SHA-256 (hyperuniformity, schedule barrier, avalanche wall).
