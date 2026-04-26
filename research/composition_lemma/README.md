# Composition Lemma — research line

**Цель**: формализовать Composition Lemma (informal в UNIFIED_METHODOLOGY.md, §"PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ") и искать её нарушение — операцию с суперлинейной композицией advantage'а через раунды SHA-256.

**Контекст**: одно из двух доступных направлений атаки, оставшихся после закрытия Prismatic Program (Sessions 1-69). Альтернатива — side-channels, которая out-of-scope как inженерия.

**Режим**: медленный, по сессии за раз. Result-oriented, не speed-oriented.

## Sessions

- [SESSION_1.md](SESSION_1.md) (2026-04-26) — Формализация: precise statement Composition Lemma, operational definition "break", catalog of 5 кандидатов, methodological pitfalls.
- [SESSION_2.md](SESSION_2.md) (2026-04-26) — Φ-manifold candidate ⊘SCOPED: blocked by MI(W;Φ)≈0 для pre/coll. Refinement CL: split на CL-D/CL-P/CL-C; CL-D тривиально нарушена (не цель), CL-P/CL-C — настоящий target.
- [SESSION_3.md](SESSION_3.md) (2026-04-26) — OTOC higher-order ⊘SCOPED: T_max(k) bounded by mixing time для всех k. Identity OTOC^(k) ≡ Walsh chain-k → уже измерено в IT-5S, chain_3 saturates by r=20. SHA's 40-round design margin ≫ T_max,∞.
- [SESSION_4.md](SESSION_4.md) (2026-04-26) — Path-bit / Hopf algebra ⊘SCOPED: T_max(path-bit) = **2 раунда** (§94.5 ✗NEG conservation refuted at R=2). Самый быстро-затухающий кандидат каталога. Triangulation с Prismatic Program (69 sessions) — same conclusion, different path.

## Кандидаты (после Session 4)

| Кандидат | CL-D | CL-P | CL-C | Status |
|---|---|---|---|---|
| ~~Path-bit / Hopf algebra (Том I §80-84)~~ | break | T_max=2 | T_max=2 | ⊘SCOPED [Session 4] |
| ~~Φ-manifold 6D (§II.9.1)~~ | break (trivial) | blocked (MI≈0) | blocked | ⊘SCOPED [Session 2] |
| ~~OTOC higher-order (§III.8)~~ | break | bounded T_max(k) | bounded | ⊘SCOPED [Session 3] |
| Resonance / cycle structure | unknown | unlikely | unlikely | postpone (Sessions 41, 62 уже закрыли) |
| Witt / prismatic (D-6) | unknown | open | open | open (5-10 сессий, отдельная линия `research/prismatic/`) |

**3 из 5 кандидатов закрыты** structurally за 3 analytic сессии. Triangulation с Prismatic Program 69 sessions — convergence на тот же вывод "SHA unbreakable классически" через структурный фильтр вместо empirical exhaustion.

## Session 5 target — META-audit

Не закрытие конкретного кандидата, а review каталога и decision о transition в Witt/prismatic линию.

## Refined target

Ищем break **CL-P или CL-C** (не CL-D — distinguishing нарушается тривиально и не считается атакой). Критерий первого фильтра: есть ли у кандидата handle для **управления** intermediate структурой из входа? Если MI(input; structure) ≈ 0 — кандидат ⊘SCOPED для pre/coll за одну сессию.

## Stopping criterion

Каждый кандидат ≤ 5 сессий до ⚡VER signal или ⊘SCOPED закрытия.
