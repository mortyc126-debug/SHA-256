# Composition Lemma — research line

**Цель**: формализовать Composition Lemma (informal в UNIFIED_METHODOLOGY.md, §"PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ") и искать её нарушение — операцию с суперлинейной композицией advantage'а через раунды SHA-256.

**Контекст**: одно из двух доступных направлений атаки, оставшихся после закрытия Prismatic Program (Sessions 1-69). Альтернатива — side-channels, которая out-of-scope как inженерия.

**Режим**: медленный, по сессии за раз. Result-oriented, не speed-oriented.

## Sessions

- [SESSION_1.md](SESSION_1.md) (2026-04-26) — Формализация: precise statement Composition Lemma, operational definition "break", catalog of 5 кандидатов, methodological pitfalls.
- [SESSION_2.md](SESSION_2.md) (2026-04-26) — Φ-manifold candidate ⊘SCOPED: blocked by MI(W;Φ)≈0 для pre/coll. Refinement CL: split на CL-D/CL-P/CL-C; CL-D тривиально нарушена (не цель), CL-P/CL-C — настоящий target.
- [SESSION_3.md](SESSION_3.md) (2026-04-26) — OTOC higher-order ⊘SCOPED: T_max(k) bounded by mixing time для всех k. Identity OTOC^(k) ≡ Walsh chain-k → уже измерено в IT-5S, chain_3 saturates by r=20. SHA's 40-round design margin ≫ T_max,∞.
- [SESSION_4.md](SESSION_4.md) (2026-04-26) — Path-bit / Hopf algebra ⊘SCOPED: T_max(path-bit) = **2 раунда** (§94.5 ✗NEG conservation refuted at R=2). Самый быстро-затухающий кандидат каталога. Triangulation с Prismatic Program (69 sessions) — same conclusion, different path.
- [SESSION_5.md](SESSION_5.md) (2026-04-26) — META-audit: расширенный каталог ~31 classical direction, structural filter применён, 30 ⊘SCOPED либо prior closure. Single open: Witt/prismatic (long-horizon, отдельная линия `research/prismatic/`). Initial phase Composition-Lemma program complete; transition to **maintenance mode**.

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

## Status: initial phase complete

Triangulation Composition-Lemma structural filter (4 analytic sessions) с Prismatic Program (69 empirical sessions) — same conclusion "SHA unbreakable классически" через independent paths.

**Maintenance mode**: новые сессии — только при появлении нового candidate-направления из литературы или Witt/prismatic breakthrough.

## Refined target

Ищем break **CL-P или CL-C** (не CL-D — distinguishing нарушается тривиально и не считается атакой). Критерий первого фильтра: есть ли у кандидата handle для **управления** intermediate структурой из входа? Если MI(input; structure) ≈ 0 — кандидат ⊘SCOPED для pre/coll за одну сессию.

## Stopping criterion

Каждый кандидат ≤ 5 сессий до ⚡VER signal или ⊘SCOPED закрытия.
