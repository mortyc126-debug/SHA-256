# Composition Lemma — research line

**Цель**: формализовать Composition Lemma (informal в UNIFIED_METHODOLOGY.md, §"PRISMATIC PROGRAM — ИТОГ 69 СЕССИЙ") и искать её нарушение — операцию с суперлинейной композицией advantage'а через раунды SHA-256.

**Контекст**: одно из двух доступных направлений атаки, оставшихся после закрытия Prismatic Program (Sessions 1-69). Альтернатива — side-channels, которая out-of-scope как inженерия.

**Режим**: медленный, по сессии за раз. Result-oriented, не speed-oriented.

## Sessions

- [SESSION_1.md](SESSION_1.md) (2026-04-26) — Формализация: precise statement Composition Lemma, operational definition "break", catalog of 5 кандидатов, methodological pitfalls.

## Кандидаты (упорядочены по plausibility/cost)

1. **Φ-manifold 6D** (Том II §II.9.1) — 6 свободных раундов как координаты; самый прямой. **→ Session 2 target**.
2. **Path-bit / Hopf algebra** (Том I §80-84) — non-abelian composition signature space.
3. **OTOC higher-order** (§III.8) — 4-point/6-point measurements в 40-round margin (r=24..64).
4. **Resonance / cycle structure** — низкая plausibility (Sessions 41, 62 уже закрыли).
5. **Witt / prismatic** (D-6) — long-horizon (5-10 сессий), отдельная линия research/prismatic/.

## Stopping criterion

Каждый кандидат ≤ 5 сессий до ⚡VER signal или ⊘SCOPED закрытия.
