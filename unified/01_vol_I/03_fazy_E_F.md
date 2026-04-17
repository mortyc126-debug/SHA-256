# Глава I.3. Фазы E и F — Новые оси + Граф зависимостей

> TL;DR: Фаза E добавляет 5 новых осей (linear=РЕСУРС, selfref=РЕКУРСИЯ, church=ПОВЕДЕНИЕ, modal=МИРЫ, relational=СВЯЗЬ) — гипотеза «6 осей» опровергнута. Фаза F: hierarchy_v2 (12 осей, 12/12 witnesses) + axis_dependencies 12×12 граф (8 нативно независимых, базис {stream}).

## §I.3.1 Фаза E: 5 новых осей [§7]

**Поворот** [§7.1]: «найди то, что не учёл». 3 вопроса для каждого кандидата: новое свойство? конкретный witness? не маскировка?

**linear_bits.c — 7-я ось РЕСУРС** ⚡VER [§7.2]: Girard 1987 linear logic.
- Примитив: {value, budget, consumed}
- read декрементирует budget; drop забирает использование (нет weakening); clone — ЯВНЫЙ гейт (нет contraction); !A = budget=∞ = обычный бит
- **5 экспериментов** (все чистые): single-use ✓, !A 5/5 ✓, CLONE с зарядом ✓, linear tensor A⊗B (AND потребляет оба), resource conservation reads+drops=initial+clone_charges
- **Связь**: квантовый no-cloning из линейности гильбертова пространства; здесь то же через **счётчики типов**, без физики.
- Ортогональность: ни одна из 6 осей не имеет понятия «сколько раз можно прочитать».

**selfref_bits.c — 8-я ось РЕКУРСИЯ** ⚡VER [§7.3]: Kleene 1938, Гёдель, Тарский.
- Примитив: решение b = f(b)

| функция | f(0) f(1) | фикс. точки |
|---|---|---|
| identity | 0 1 | {0,1} |
| **negation** | 1 0 | **НЕТ — лжец** |
| const 0 | 0 0 | {0} |
| const 1 | 1 1 | {1} |

- Coupled 2-bit: AND/OR → 3 фикс., NAND/XOR → 0
- Kleene witness F_c(b)=c⊕b: F_0 фикс {0,1}, F_1 нет
- 2-бит quine под SWAP: только (0,0) и (1,1)
- **Лжец как certificate** ✓DOK: b=¬b — структурный факт, Тарский разрешим
- Ортогональность: ни одна из 7 осей не имеет понятия фиксированной точки.

**church_bits.c — 9-я ось ПОВЕДЕНИЕ** ⚡VER [§7.4]: Church 1936.
- Примитив: TRUE=λxy.x, FALSE=λxy.y. Бит — функция, не значение.
- Ops: NOT=λxy.pyx, AND=λxy.p(qxy)y, OR=λxy.px(qxy), IF=cte
- TRUE(7,42)=7, FALSE(7,42)=42
- NOT(NOT TRUE)≡TRUE extensionally ✓
- De Morgan, absorption ✓ (доказательство пробой на всех парах)
- Ортогональность: ни одна из 8 осей не ставит функцию на уровень примитива.

**modal_bits.c — 10-я ось МИРЫ** ⚡VER [§7.5]: Kripke 1963.
- Примитив: b: W→{0,1} + R⊆W×W
- (□b)(w)=1 iff b(w')=1 для всех wRw'; ◇ симметрично
- **5 экспериментов**:
  - S5 на 4-world: p=(1,0,1,1) → □p=(0,0,0,0), ◇p=(1,1,1,1) — модальности коллапсируют
  - Duality □p=¬◇¬p ✓ 5/5
  - K-axiom валиден везде (минимальная модальная)
  - 4-axiom □p→□□p: на транзитивном 4/4 ✓, нетранзитивная цепь 1/4 ✗ — точно характеризует транзитивность
  - **Modal ≠ probabilistic**: одинаковые truth, разные frames → разные □p. Frame несёт инфо, недоступную marginal probability.
- Ортогональность: ни одна из 9 осей не имеет понятия «в каком мире я нахожусь».

**relational_bits.c — 11-я ось СВЯЗЬ** ⚡VER [§7.6]: Tarski 1941, Codd 1970.
- Примитив: R⊆A×B. Все 10 предыдущих — свойства одной сущности; relational — связь между двумя.
- Ops: union, intersection, converse, composition (R;S)(i,k)=∨_j R(i,j)∧S(j,k), R⁺ transitive closure, R* Kleene star
- Composition associative ✓
- R⁺ пути 0→1→...→4: верхний треугольник
- R* с циклом {0,1,2}: полный 3×3 блок
- 3 представления (edge list, adj matrix, Bool function)
- Ортогональность: edge structure, composition применяется к (a,c) через промежуточный b — принципиально иное.

**Сводка фазы E** [§7.7]:
| # | ось | фундамент |
|---|---|---|
| 7 | linear | Girard |
| 8 | self-ref | Kleene |
| 9 | higher-order | Church 1936 |
| 10 | modal | Kripke 1963 |
| 11 | relational | Tarski 1941 |

Гипотеза «6 осей» ⊘ROLL опровергнута 5 раз подряд.

## §I.3.2 Фаза F: hierarchy_v2 + dependency graph [§8]

**hierarchy_v2.c** ⚡VER [§8.1]: явно суперсидит unified_hierarchy.c.

**12 witnesses** (12/12 passing):
| # | ось | инвариант |
|---|---|---|
| 1 | binary | XOR коммутативен |
| 2 | phase | +1+(−1)=0 |
| 3 | ebit/ghz | Φ⁺ ранг 2 |
| 4 | probability | Σp_i=1 |
| 5 | reversible | Toffoli²=id |
| 6 | stream | S(x⊕y)=Sx⊕Sy |
| 7 | braid | Yang-Baxter |
| 8 | linear | budget-1 single-use |
| 9 | self-ref | b=¬b нет решений |
| 10 | higher-order | ¬¬TRUE≡TRUE ext. |
| 11 | modal | □p=¬◇¬p |
| 12 | relational | composition associative |

Нет принципиальной верхней границы (см. §I.4 — Часть II добавит ещё 6+).

**axis_dependencies.c** ⚡VER [§8.2]: 12×12 матрица симуляций.

**Уровни**: 2=native, 1=encoded, 0=none.

**Native inclusions** (level 2):
- binary ⊂ всё
- phase ⊃ prob
- ebit ⊃ phase, prob
- braid ⊃ phase
- church ⊃ relational

**Encoded** (level 1):
- church → self-ref (Y-комбинатор), modal, linear, rev, stream, braid, phase, ebit, prob (λ-исчисление Тьюринг-полно)
- linear ↔ modal (!A↔□A через S4)
- linear ↔ rev
- stream → всё (rule 110)
- modal ↔ relational

**Транзитивное замыкание**:
| ось | native | encoded | итого |
|---|---|---|---|
| binary | 1 | 0 | 1/12 |
| phase | 3 | 0 | 3/12 |
| ebit | 4 | 0 | 4/12 |
| prob | 2 | 0 | 2/12 |
| rev | 2 | 3 | 5/12 |
| **stream** | 2 | 10 | **12/12** |
| braid | 4 | 0 | 4/12 |
| linear | 2 | 3 | 5/12 |
| selfref | 2 | 0 | 2/12 |
| **church** | 3 | 9 | **12/12** |
| modal | 2 | 3 | 5/12 |
| relational | 2 | 3 | 5/12 |

**Минимальный базис greedy set cover**: **{stream}** покрывает все 12 через encoding.

**8 нативно независимых**: ebit, rev, stream, braid, linear, selfref, church, modal.
**3 нативно зависимые**: phase ⊂ ebit/braid; prob ⊂ phase/ebit/braid; relational ⊂ church.

## §I.3.3 Интерпретация графа [§8.3]

**Caveat**: Тьюринг-эквивалентность СЛАБА. Stream/church симулируют phase ТОЛЬКО через интерпретатор. Алгебраическая структура (ebit, braid, rev) НЕ сохраняется. WHT не становится нативной в rule 110.

**Правильная картина**:
- ≤8 нативно независимых
- 2 «универсальных» через encoding (stream, church) — кросс-парадигмальная симуляция
- Остальные = разные алгебраические миры

Аналогия: Turing machines симулируют квантовые схемы (медленно), но нативные квантовые примитивы изучают отдельно.

## §I.3.4 Финальное состояние Части I [§9]

**Положительные** (P1-P6):
- P1: фазовый переход R=3→R=4 SHA-256 ✓ 4 методами
- P2: 1765× R=1 inversion (единственное число vs реальная криптофункция)
- P3: HDC унифицирующий субстрат
- P4: phase bits = строгое расширение (минус → интерференция, exact removal, native WHT, Bell, GHZ, DJ/BV)
- P5: ✓DOK GHZ± неотличимы prob, отличимы phase
- P6: 12 осей, 8 нативно независимых

**Отрицательные** (N1-N4):
- N1 ✗NEG: HDV не пробивает R=2
- N2 ✗NEG: p-adic не видит SHA-256
- N3 ⊘ROLL: «6 осей»
- N4 ✓DOK: classical no-cloning суперпозиции из линейности

**Открытые** (Q1-Q5): сколько осей? строгая независимость? минимальный базис в сильном смысле? real-world speedup из не-quantum? универсальный фазовый переход для других хэшей?

**Методология**: M1 комбинирование > изобретение; M2 честность отрицательных; M3 измеримость инвариантов; M4 плато как остановка.

**Часть I плато**: 12 осей нижняя оценка, верх неизвестен. Часть II (см. §I.4) добавит 6 осей + комбинационные клетки.
