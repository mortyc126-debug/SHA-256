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
| 2 | δ-structure на W_n(F_2), SHA-op compatibility | ✓ Done 2026-04 | `SESSION_2.md` |
| 3 | Formalize "δ-ring with AND" / λ-ring connection | ✓ Done 2026-04 | `SESSION_3.md` |
| 4 | Prove ANF degree 2(k+1) bound | ✓ Done 2026-04 | `SESSION_4.md` |
| 5 | Formal theorem + ROTR in enhanced δ-ring | Planned | - |
| 6 | Prism formalization | Planned | - |
| 7 | Prismatic cohomology of Bool ring (exact computation) | Planned | - |
| 8 | Extension to SHA round function | Planned | - |
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

## Session 2 summary

Результаты:
- ✓ Z/2^n (= W_n(F_2)) — nontrivial δ-ring (for n=4,6,8 axioms hold fully)
- ✓ ADD is fully δ-compatible (by axiom D2)
- **✓ NEW RESULT**: XOR discrepancy has EXACT formula:
  ```
  δ(x⊕y) = δ(x) + δ(y) - xy + 2z(x+y) - 2δ(z) - 3z²,  z = x ∧ y
  ```
- AND is a PRIMITIVE operation — no clean δ-formula. Needs extension axiom.
- ROTR — no clean formula. Same obstruction as Witt-filtration from earlier scoping.

**Core picture**: SHA = ADD (free) + AND (extension) + ROTR (obstruction).

## Session 3 summary

Результаты:
- ✗ δ(x AND y) НЕ является low-degree polynomial in (x, y, δ(x), δ(y))
- ✓ **НО**: bit-level ANF структурен — output bit k имеет max degree **2(k+1)**, только чётные степени
- Число ANF terms растёт медленно (1, 3, 5, 9 для битов 0..3)
- Conclusion: AND — genuine primitive, но с CONTROLLED complexity

## Session 4 summary

**Theorem (informal)**: δ(z) = Σ_{i≥1} 2^{i-1}(1-2^i) z_i − Σ_{i<j} 2^{i+j} z_i z_j **over Z**. Quadratic polynomial in z-bits. Verified exact.

Via carry cascade analysis: bit k of δ(z) mod 2^{n-1} has ANF degree **k+1** in z-bits. In (x, y) vars via z_i = x_i y_i: degree **2(k+1)**. Matches Session 3 observation.

**Proposed structure**: "Enhanced δ-ring" (A, δ, β) где β is idempotent bilinear (AND). Compatibility: δ∘β has bounded ANF per bit.

**Next step**: Session 5 — formal proof + ROTR analysis в этом framework.
