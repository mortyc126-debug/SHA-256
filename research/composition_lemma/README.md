# Composition Lemma — research line

**Цель**: формализовать Composition Lemma (informal в UNIFIED_METHODOLOGY.md, §"PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ") и искать её нарушение — операцию с суперлинейной композицией advantage'а через раунды SHA-256.

**Контекст**: одно из двух доступных направлений атаки, оставшихся после закрытия Prismatic Program (Sessions 1-69). Альтернатива — side-channels, которая out-of-scope как inженерия.

**Режим**: медленный, по сессии за раз. Result-oriented, не speed-oriented.

## Sessions

- [SESSION_1.md](SESSION_1.md) (2026-04-26) — Формализация: precise statement Composition Lemma, operational definition "break", catalog of 5 кандидатов, methodological pitfalls.
- [SESSION_2.md](SESSION_2.md) (2026-04-26) — Φ-manifold candidate ⊘SCOPED: blocked by MI(W;Φ)≈0 для pre/coll. Refinement CL: split на CL-D/CL-P/CL-C; CL-D тривиально нарушена (не цель), CL-P/CL-C — настоящий target.
- [SESSION_3.md](SESSION_3.md) (2026-04-26) — OTOC higher-order ⊘SCOPED: T_max(k) bounded by mixing time для всех k. Identity OTOC^(k) ≡ Walsh chain-k → уже измерено в IT-5S, chain_3 saturates by r=20. SHA's 40-round design margin ≫ T_max,∞.
- [SESSION_4.md](SESSION_4.md) (2026-04-26) — Path-bit / Hopf algebra ⊘SCOPED: T_max(path-bit) = **2 раунда** (§94.5 ✗NEG conservation refuted at R=2). Самый быстро-затухающий кандидат каталога. Triangulation с Prismatic Program (69 sessions) — same conclusion, different path.
- [SESSION_5.md](SESSION_5.md) (2026-04-26) — META-audit: расширенный каталог ~31 classical direction, structural filter применён, 30 ⊘SCOPED либо prior closure. Single open: Witt/prismatic (long-horizon, отдельная линия `research/prismatic/`). Initial phase Composition-Lemma program complete; transition to **maintenance mode**. [⚠ corrected by Session 6]
- [SESSION_6.md](SESSION_6.md) (2026-04-26) — Корректировка Session 5: research/prismatic/ **уже** на plateau (Sessions 1-21 specialist, 22-69 empirical exhaustion). Honest acknowledgment: три research lines конвергируют на same plateau. Maintenance mode уточнён до **B-lateral** (допускает 1-3 сессии для structural completeness, e.g., Theorem 67.1 chain analysis).

## Финальный каталог (после Session 5)

**Полный audit ~31 classical direction** в SESSION_5 §2. Все ⊘SCOPED либо prior closure, кроме Witt/prismatic.

Ключевые ⊘SCOPED через structural filter (наша программа):

| Кандидат | CL-D | CL-P | CL-C | Closure |
|---|---|---|---|---|
| ~~Path-bit / Hopf algebra~~ | break | T_max=2 | T_max=2 | Session 4 |
| ~~Φ-manifold 6D~~ | break | blocked (MI≈0) | blocked | Session 2 |
| ~~OTOC higher-order~~ | break | bounded T_max(k) | bounded | Session 3 |

Остальные 27 направлений — prior closure (Prismatic Program / Том II §II.8 / scoping 2026-04).

**Open**: только Witt/prismatic (#32 в audit) — separate research line `research/prismatic/`, 5-10 sessions horizon.

## Status: honest plateau (after Session 6 correction)

**Triangulation на plateau**: три research lines независимо приходят к одному выводу.

| Линия | Sessions | Финал |
|---|---|---|
| Prismatic cohomology (research/prismatic/ 1-21) | 21 | "stable plateau, requires specialist expertise" |
| Empirical exhaustion (research/prismatic/ 22-69) | 48 | 9 attack frameworks конвергируют на ≤46 раундов |
| Composition-Lemma structural filter (this dir 1-5) | 5 | 30/31 directions ⊘SCOPED |

Conclusion: **SHA-256 не атакуется классически at session-level capability**. Further progress requires specialist expertise (char-2 Lie classification, absolute prismatic site, bialgebra framework) — beyond session scope.

**Maintenance mode B-lateral**: допускает 1-3 сессии для structural completeness (e.g., Theorem 67.1 chain analysis, cross-ARX Lucas-XOR application). Не пробивает plateau, но extends infrastructure.

## Refined target

Ищем break **CL-P или CL-C** (не CL-D — distinguishing нарушается тривиально и не считается атакой). Критерий первого фильтра: есть ли у кандидата handle для **управления** intermediate структурой из входа? Если MI(input; structure) ≈ 0 — кандидат ⊘SCOPED для pre/coll за одну сессию.

## Stopping criterion

Каждый кандидат ≤ 5 сессий до ⚡VER signal или ⊘SCOPED закрытия.
