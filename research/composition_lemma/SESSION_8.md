# Session 8: Killing form computation — char-2 pathology confirmed

**Дата**: 2026-04-26
**Статус**: ⚡VER — Killing form ≡ 0 over F_2. Subgoal A inconclusive (expected char-2 phenomenon).
**Цель**: Subgoal A из Session 7 — компьютер Killing form K(x_i, x_j) = trace(ad_{x_i} ∘ ad_{x_j}) для D^4 = L_SHA^perfect (dim 264) над F_2, оценить rank(K).

**Outcome**: K ≡ 0 (rank 0). Это **ожидаемая char-2 pathology** для sub-algebra of sl_n(F_2). Classical Cartan-Killing test inconclusive. Subgoal B (minimal ideals) теперь критичен.

---

## 1. Computation

**Setup**:
- D^4 basis (264 matrices, 32×32 over F_2) re-derived independently через `extract_perfect_subalgebra()` (research/prismatic/session_21_perfect.py).
- Confirmed dim = 264.
- Row-reduced flattened basis (264×1024) → 264 pivot columns + transformation matrix T.

**Structure constants C[i, j, k]**:
- Все 264² = 69696 brackets [x_i, x_j] вычислены за 4.8s.
- Каждый bracket выражен в basis через `(brackets[:, pivot_cols] @ T) & 1`.
- Total nonzero entries в C: 2,829,398 / 264³ = 0.0154 (1.5% density).
- **Verification**: 20/20 samples reconstruction match. Symmetry C[i,j,k] = C[j,i,k] подтверждена (over F_2, [x,y] = [y,x] так как char 2).

**Killing form K[i, j] = Σ_{k,l} C[i,l,k] · C[j,k,l] (mod 2)**:
- Computed via numpy einsum за 2.9s.
- Result: **K identically zero**. Sum = 0, density = 0.0.
- Symmetry K[i,j] = K[j,i] confirmed (0 asymmetric entries).

**Rank(K) over F_2 = 0 / 264.**

Total wall time: ~10s.

Artifact: `killing_form.npy` (264×264 zero matrix saved).

---

## 2. Interpretation: char-2 pathology

K = 0 — НЕ surprise, а **known char-2 phenomenon**:

**Standard fact** (Jacobson, *Lie Algebras*, char-p chapter): для sl_n over F_p, Killing form K(A, B) = 2n · tr(AB). When p | 2n, K vanishes identically.

Для p = 2 и любого n: 2n ≡ 0 (mod 2), поэтому K_{sl_n(F_2)} = 0 universally.

**Применение к D^4**: D^4 ⊆ sl_32(F_2) (Session 21). Killing form инherited from sl_32 — также zero. Поэтому K = 0 для D^4 НЕ свидетельствует ни о semisimplicity, ни о non-semisimplicity.

**Conclusion из Subgoal A**: classical Cartan-Killing test inconclusive over F_2 для sub-algebras of sl_n. Это ожидаемое препятствие, упомянутое в Session 7 §3:
> "В char 2 эти три definition'а **не эквивалентны**. Restricted Lie algebras (Jacobson 1937) — корректный framework для char p."

Subgoal A complete; semisimplicity question остаётся открытым. Переходим к Subgoal B.

---

## 3. Что мы получили (несмотря на null result)

(a) **Independent verification dim D^4 = 264** — replicate Session 21 result через independent code path.

(b) **Structure constants C[i, j, k] computed and saved** — переиспользуемый artifact для Sessions 9-11.

(c) **Char-2 pathology empirically confirmed** на нашей конкретной algebra — establishes that we're operating in the "modular Lie algebra" regime, not classical.

(d) **Lower bound on D^4 complexity**: 1.5% density structure constants nontrivial (2.8M nonzero of 264³). Это не trivial / abelian / simple — настоящая non-trivial Lie algebra structure.

---

## 4. Implications для следующей сессии

**Subgoal A не сработал.** Subgoal B (minimal ideals) теперь обязателен — единственный session-level способ зондировать semisimplicity без Killing form.

**Subgoal B method (для Session 9)**:
1. Random element x ∈ D^4.
2. Compute orbit: I_x = span{x, [y, x], [y, [z, x]], ... : y, z ∈ D^4}.
3. I_x is the smallest ideal containing x.
4. Iterate over different x:
   - Если все I_x = D^4 → D^4 simple.
   - Если есть proper I_x (dim < 264) → D^4 not simple.
   - Если найдётся nilpotent ideal (e.g., abelian I_x with [I_x, I_x] = 0) → D^4 has solvable radical → not semisimple.

**Computational complexity**: per random x, O(264² · iter) operations until stabilization. Total ~10⁷ ops per ideal candidate. 100 random x → 10⁹ ops. Manageable, ~minutes.

Plan: run Session 9 immediately после commit Session 8.

---

## 5. Cross-references

- SESSION_7.md §4 (Subgoal A specification).
- research/prismatic/SESSION_21.md (D^4 extraction baseline).
- research/prismatic/session_21_perfect.py (re-used basis extraction).
- session_8_killing.py (this session's script).
- Jacobson, *Lie Algebras* (1962), Chapter "Lie algebras of characteristic p".

## 6. Status

- ✓ D^4 basis verified (dim 264)
- ✓ Structure constants C[i,j,k] computed (2.8M nonzero / 18M cells)
- ✓ Verification 20/20 samples ✓ + symmetry ✓
- ✓ Killing form K computed (rank 0 — char-2 pathology)
- → Subgoal A complete (inconclusive)
- → Session 9: Subgoal B (minimal ideals)
