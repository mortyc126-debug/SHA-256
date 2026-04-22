# Prismatic cohomology → SHA-256

**Long-term research program**: применение prismatic cohomology (Bhatt-Scholze 2019) к cryptanalysis SHA-256.

**Вероятность прорыва**: крайне низкая (< 1% в 10 лет). Но это **единственный mathematically principled target** после того как все session-level direction были scoped (см. `/research/qt_minimal/`).

**Философия работы**: медленно, session-by-session. Каждая session = один маленький математический шаг. Документирование критично — каждая session строит на предыдущей.

## Почему эта direction

После 6 scoping-раундов (см. `../qt_minimal/CROSS_POLLINATION.md`) мы локализовали SHA's core obstruction:

- SHA combines три алгебры: Z/2^n (ADD), F_2 (XOR/AND), Galois (rotations)
- Нет basis где все три simultaneously просты
- **No-go theorem** для linear F_2-basis change

**Prismatic cohomology** — единственная existing math natively handling mixed-characteristic structure. Никогда не применялась к крипто.

## Session structure

| Session | Цель | Status | Файл |
|---|---|---|---|
| 1 | δ-ring foundations | ✓ Done 2026-04 | `SESSION_1.md` |
| 2 | δ-structure на W_n(F_2), SHA-op compatibility | Planned | `SESSION_2.md` |
| 3 | Prism formalization | Planned | - |
| 4 | Prismatic cohomology of Bool ring (exact computation) | Planned | - |
| 5 | Extension to SHA round function | Planned | - |
| ... | ... |  | |

Expected timeline: десятки sessions spread по месяцам/годам. Каждая session commitable standalone.

## Artifacts

- `delta_rings.py` — Session 1 code: δ-ring definition + concrete examples
- `SESSION_1.md` — Session 1 notes
- `README.md` — этот файл

## Key references (для будущих sessions)

Не прочитаны пока, но будут нужны:

- Bhatt-Scholze, *"Prisms and Prismatic Cohomology"* (2019, arxiv:1905.08229) — foundation paper
- Bhatt, *"Prismatic F-gauges"* (lecture notes, 2022)
- Kedlaya, *"Notes on prismatic cohomology"* (lecture notes)
- Joyal, *"δ-anneaux et vecteurs de Witt"* (1985) — original δ-ring source

## Session 1 summary

Понято:
- δ-ring (A, δ) axioms D1-D3, equivalent to Frobenius lift φ(x) = x^p + pδ(x)
- Z_p has standard δ(x) = (x-x^p)/p, φ = identity
- Z/p^k has δ: Z/p^k → Z/p^{k-1} (loss of one level)
- **Bool ring F_2[t]/(t²-t) has TRIVIAL δ-structure** (idempotence kills it)

Следствие для SHA: нельзя просто объявить SHA на Bool_256 и применять prismatic — всё тривиально. Нужна Witt-reformulation SHA.

**Next step**: Session 2 — δ-compatibility SHA operations на W_n(F_2).
