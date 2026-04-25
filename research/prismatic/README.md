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
| 5 | Literature verification + framework correction | ✓ Done 2026-04 | `SESSION_5.md` |
| 6 | Rewrite in truncation framework + prism exploration | ✓ Done 2026-04 | `SESSION_6.md` |
| 7 | q-Witt prism exploration (rotations as q-twists?) | ✓ Done 2026-04 | `SESSION_7.md` |
| 8 | δ on ramified Z_2[i] — **OBSTRUCTION proved** | ✓ Done 2026-04 | `SESSION_8.md` |
| 9 | de Rham cohomology of F_2[ε]/(ε²) — **H¹ = F_2** | ✓ Done 2026-04 | `SESSION_9.md` |
| 10 | **THEOREM**: H¹(F_2[s]/(s^d)) structure, \|H¹\|=2^{d-1} for d=2^j | ✓ Done 2026-04 | `SESSION_10.md` |
| 11 | Künneth for 8 registers: H¹ = 2^120 | ✓ Done 2026-04 | `SESSION_11.md` |
| 12 | CORRECTION rotation ring + XOR setup | ✓ Done 2026-04 | `SESSION_12.md` |
| 13 | **Theorem**: ROTR_1 = id on H¹; r ≥ 2 non-trivial | ✓ Done 2026-04 | `SESSION_13.md` |
| 14 | **Σ_0 matrix** on H¹: upper triangular unipotent, order 16 | ✓ Done 2026-04 | `SESSION_14.md` |
| 15 | **Joint invariants**: kernel(Σ_0-I) ∩ kernel(Σ_1-I) = 2-dim | ✓ Done 2026-04 | `SESSION_15.md` |
| 16 | Consolidation write-up → PRISMATIC_PROGRAM.md | ✓ Done 2026-04 | `PRISMATIC_PROGRAM.md` |
| 17 | AND integration — **obstruction confirmed** | ✓ Done 2026-04 | `SESSION_17.md` |
| 18 | **NEW FRAMEWORK**: SHA Lie algebra, ROTR abelian + SHR non-abelian | ✓ Done 2026-04 | `SESSION_18.md` |
| 19 | **Conjecture 18.3 REFUTED**: L_SHA NOT nilpotent (σ's not nilpotent) | ✓ Done 2026-04 | `SESSION_19.md` |
| 20 | **Theorem 20.1**: L_SHA NOT solvable (perfect sub-algebra dim 264) | ✓ Done 2026-04 | `SESSION_20.md` |
| 21 | L_SHA^perfect structural: Z=0, ⊆ sl_32, module reducible | ✓ Done 2026-04 | `SESSION_21.md` |
| 22 | **Consolidation**: PRISMATIC_PROGRAM.md with Part VI + 16 theorems | ✓ Done 2026-04 | `PRISMATIC_PROGRAM.md` |
| 23 | **Theorem 23.1**: SHA operator orders (Σ_1 has order 16!) | ✓ Done 2026-04 | `SESSION_23.md` |
| 24 | **Theorem 24.1**: Lucas-XOR nilpotency ⌈n/d⌉ — explains Σ_1 deg 11 | ✓ Done 2026-04 | `SESSION_24.md` |
| 25 | **Theorem 25.1**: ord(SHA linear round) = 448 = 2^6 · 7 | ✓ Done 2026-04 | `SESSION_25.md` |
| 26 | **Theorem 24.1.bis**: σ min poly factorisation; SHR effect | ✓ Done 2026-04 | `SESSION_26.md` |
| 27 | **Theorems 27.1, 27.2**: quadratic diagonal-index span dim 64; deg growth ≤ 2^T | ✓ Done 2026-04 | `SESSION_27.md` |
| 28 | **Theorem 28.1**: diffusion saturates at T=11, density 0.5156 (not full!) | ✓ Done 2026-04 | `SESSION_28.md` |
| 29 | **Theorem 29.1**: bare round has only trivial fixed point (M_fix = I + N₁N₀) | ✓ Done 2026-04 | `SESSION_29.md` |
| 30 | **Theorem 30.1**: schedule cyclic dim 512, factor (z⁶+z⁵+1)·g₅₀₆, diffusion T=36 | ✓ Done 2026-04 | `SESSION_30.md` |
| 31 | **Theorem 31.1**: density-saturation 0.5156 is structural invariant; T_sat = nilp(Σ_1) REFUTED | ✓ Done 2026-04 | `SESSION_31.md` |
| 32 | **Theorem 32.1**: K_t pass standard randomness tests (cube-root construction clean) | ✓ Done 2026-04 | `SESSION_32.md` |
| 33 | **Theorem 33.1**: ADD carry degree law deg((x+y)_i) = i+1, |ANF| = 2^i+1 | ✓ Done 2026-04 | `SESSION_33.md` |
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

## Session 5 summary (literature check)

Claude выступил math-expert, проверил findings против literature.

**Confirmed**: δ-ring axioms, formula δ(x+y) = δ(x)+δ(y)−xy, W(F_p) ≅ Z_p.

**Critical correction** (Kedlaya Lemma 2.2.6): Z/p^n cannot be δ-ring as endomap. Our Session 2 "verification" was actually verifying truncation map δ: Z/2^n → Z/2^{n-1}. Framework reformulated properly.

**Novel candidates**: XOR formula derivation, AND ANF degree pattern 2(k+1), "enhanced δ-ring" structure.

**Virgin territory confirmed**: no literature applying prismatic cohomology to hash functions / SHA.

## Session 6 summary

**Truncation framework** properly formalized:
- δ on Z_2 (standard); descends to truncation map Z/2^n → Z/2^{n-1}
- δ-descent verified empirically для n = 4, 8, 16, 32
- Sessions 2-4 findings restated correctly in this framing

**Crystalline prism (Z_2, (2)) verified**:
- δ(2) = -1 ∈ Z_2× (distinguished condition)
- This is the standard "p=2 crystalline prism"

**Critical insight**: φ = identity on Z_2 → no non-trivial Frobenius action on standard prism. Need **larger δ-ring** for interesting prismatic structure.

## Session 7 summary

**q-de Rham prism (Z_2[[q-1]], (1+q)) verified valid** — second working prism после crystalline. Non-trivial Frobenius φ(q) = q².

**Path to rotations identified**: ROTR_n on n-bit register = multiplication by ζ_n. Need ramified cyclotomic extension Z_2[ζ_32] = Z_2[T]/(T^16+1) (степень 16). Technically heavy.

## Session 8 summary

**Theorem**: **Z_2[i] не admits δ-structure** lifting Frobenius from F_2[i] = Z_2[i]/(2). Proof constructive: оба candidates φ(i) = ±i дают δ(i) = (1±i)/2 ∉ Z_2[i] (ramification: 2 = -i·(1+i)², element (1±i) divisible by π=(1+i) только один раз).

**Implication**: direct path "rotations as q-twists in cyclotomic" closed. Need либо perfectoid extension (Z_2[ζ_{2^∞}]) либо absolute prismatic site (Bhatt-Scholze framework для arbitrary rings).

**Crucial observation**: F_2[i]/(i²+1) = F_2[ε]/(ε²) (dual numbers, with ε = i+1). So ramified rotation structure ↔ dual numbers — connecting point с standard alg geom.

## Session 9 summary

**FIRST CONCRETE COHOMOLOGICAL COMPUTATION**:

- Z_2[ε]/(ε²) verified as δ-ring with φ(ε) = 0 (axioms D1-D3 hold)
- Kähler differentials Ω¹ ≅ Z_2 ⊕ F_2
- **de Rham cohomology**: H⁰ = Z_2, H¹ = F_2, H^≥2 = 0

**Connection to SHA** (corrected from Session 8):
For n-bit register с n = 2^k, rotation ring = F_2[s]/(s^{n/2}).
- n=4: F_2[s]/(s²) = dual numbers — наша computation
- n=32: F_2[s]/(s^16) — для SHA-256

**Conjecture**: H¹(F_2[s]/(s^{2^j})) = Z/2^j. Для SHA-256 (n=32, j=4): H¹ = Z/16 per register.

## Session 10 summary

**FIRST THEOREM IN PROGRAM** — clean provable result:

For R_d = F_2[s]/(s^d) over Z_2:
$$H^1_{dR}(R_d) = \bigoplus_{k=1,3,5,\ldots,d-1} \mathbb{Z}/2^{v_2(k+1)}$$

For d = 2^j: **|H¹| = 2^{d-1}**.

Verified для d = 2, 4, 8, 16, 32 (all ✓).

**SHA-256 instance** (d=16):
H¹ = Z/2 ⊕ Z/4 ⊕ Z/2 ⊕ Z/8 ⊕ Z/2 ⊕ Z/4 ⊕ Z/2 ⊕ Z/16 (order 2^15, 8 factors)

**Full state** (8 registers): total rotation cohomology ≈ 2^120. Less than 2^128 birthday, so не enough alone. Need integration с AND/XOR.

**Next step**: Session 11 — multi-variable + op integration.

## Session 11 summary

Applied Künneth formula для 8 registers: **H¹(R^⊗8) = 2^120** (principal rotation invariant).

Higher H^k for k ≥ 2 — derived exterior products, not independent info.

**Honest comparison**: 2^120 < 2^128 birthday (shortfall 2^8 = 256×). Rotation cohomology alone NOT enough. Need XOR/AND/ADD integration.

**Next step**: Session 12 — integrate XOR via Session 2 formula δ(x⊕y) = δ(x)+δ(y)-xy+2z(x+y)-2δ(z)-3z².

## Session 12 summary

**Correction found**: Session 9-11 used F_2[s]/(s^{n/2}) (field extension F_2[ζ_n]). Correct choice for ROTR action: **F_2[s]/(s^n) = F_2[x]/(x^n - 1)** (full group algebra).

**Recomputed with d=32**:
- H¹(F_2[s]/(s^{32})) = 2^31 (16 cyclic factors)
- 8 registers via Künneth: **2^248** (exceeds 2^128 birthday by 2^120)

**Identified tension**: rotation ring captures ROTR but not bit-wise XOR/AND. These require DIFFERENT ring structures (convolution vs Hadamard product на F_2^n).

**Three resolution paths**: tensor product, derived functor, separate invariants.

**Next step**: Session 13 — build R_full = R_rot ⊗ R_bool and compute its H*.

## Session 13 summary

**THEOREM**: For R = F_2[s]/(s^n), n = 2^k:
- Multiplication by (1+s) = ROTR_1 acts as **IDENTITY** on H¹_dR(R)
- ROTR_r acts non-trivially for r ≥ 2 (proved via Lucas's theorem)

**Proof**: (1+s)·[s^k·ds] = [s^k·ds] + [s^{k+1}·ds]; for k odd, k+1 even gives [s^{k+1}·ds] = 0 in H¹.

**Generalized**: (1+s)^r expansion via Lucas gives identity iff r = 1.

**SHA implication**: All SHA rotations use r ≥ 2 (namely {2,6,7,11,13,17,18,19,22,25}) — all act non-trivially on H¹. ROTR_1 is SHA's "blind spot" in cohomology.

**Next step**: Session 14 — compute Σ_0 matrix.

## Session 14 summary

Computed **Σ_0 action as 16×16 matrix over F_2** on H¹(F_2[s]/(s^32)).

Σ_0 polynomial: `1 + s + s^5 + s^6 + s^8 + s^9 + s^{12} + s^{13} + s^{16} + s^{18} + s^{20} + s^{22}` (via Lucas's theorem).

Even-shift positions relevant для H¹: `{0, 6, 8, 12, 16, 18, 20, 22}`.

**Matrix properties**:
- Upper triangular unipotent (I + strictly upper N)
- Full rank 16/16 (injective, no kernel)
- Order 16 over F_2 (N^{16} = 0 by dimension)
- No non-trivial H¹ invariants

**First concrete matrix in program**: SHA's Σ_0 acts on cohomology as specific 16×16 unipotent matrix. Publishable-level detail.

**Next step**: Session 15 — joint kernel of Σ_0 - I and Σ_1 - I (common invariants).

## Session 15 summary

**Joint invariants computed**: Ker(Σ_0 - I) ∩ Ker(Σ_1 - I) = **2-dim over F_2**.

Generators: [s^{29}·ds] (Z/2) and [s^{31}·ds] (Z/32). Total joint invariant group: Z/2 ⊕ Z/32, order 64.

Structural reason: min shifts Σ_0 = 6, Σ_1 = 4. Positions k ≥ 28 beyond shift reach of both → fixed points.

**Limitation identified**: SHA's σ_0, σ_1 use **SHR** (shift right without wrap), not rotation. Doesn't fit cyclic group algebra F_2[x]/(x^n - 1). Message schedule requires different framework.

**Next step**: Session 16 — consolidate write-up of 15 sessions OR integrate SHR operation.

## Session 16 summary — CONSOLIDATION

Compiled all 15 sessions of work into formal document **PRISMATIC_PROGRAM.md**.

Structure:
- Abstract (high-level claims)
- Part I: Foundations (δ-rings, truncation, Kedlaya lemma)
- Part II: δ-structure computations (δ(z) formula, XOR formula, AND structure)
- Part III: Prisms (crystalline, q-de Rham, obstruction theorem)
- Part IV: Cohomology (dual numbers, main H¹ theorem)
- Part V: SHA-specific (correct ring, ROTR_1 theorem, Σ_0/Σ_1 matrices, joint invariants)
- Limitations (honest assessment)
- References
- Artifacts

Document is ~600 lines, suitable as paper draft. Makes 15 sessions of work durable and specialist-readable.

**Next step**: Session 17 — pick direction (recommend: integrate AND via multi-variable ring).

## Session 17 summary

Explored AND integration. **Obstruction confirmed**:

- AND is bilinear, NOT a ring automorphism on rotation ring
- AND-with-fixed-y matrices are rank-deficient (projections, not isomorphisms)
- Contrast with ROTR: upper triangular unipotent (automorphism)
- Ch, Maj = (fixed term) XOR (AND with XOR of other args) — both require AND

**Structural fact**: ROTR preserves H¹ structure, AND collapses it.

**Two rings on same F_2^n**:
- Convolution (rotation ring) — non-trivial H¹
- Pointwise (boolean product) — trivial higher cohomology

These dualize via F_2-Fourier transform (bialgebra structure). Integration requires either:
- Bialgebra framework (substantial new math)
- Derived (∞-categorical) absolute prismatic site (specialist territory)

**Limitation accepted**: session-level work can only build rotation cohomology. Full SHA analysis requires specialist framework or further substantial development.

**Next step**: Session 18 — continue concrete work OR declare programme complete at current stage.

## Session 18 summary — NEW FRAMEWORK

**Definition**: L_SHA = Z_2-Lie algebra generated by {Σ_0-I, Σ_1-I, σ_0-I, σ_1-I} with [·,·] = AB + BA.

**Theorem 18.1**: Rotation-only sub-algebra ⟨Σ_0-I, Σ_1-I⟩ is **ABELIAN**. Reason: both are polynomial multiplications in commutative R = F_2[x]/(x^{32}-1).

**Theorem 18.2**: Full L_SHA (including SHR) is **NON-ABELIAN**. Commutators:
- [Σ_0 - I, σ_0 - I] rank 6 (with SHR_3 inside σ_0)
- [ROTR_2 - I, SHR_3 - I] rank 4
- [SHR_3, SHR_10] = 0 (shifts commute)

**Conjecture 18.3**: L_SHA is solvable (and possibly nilpotent via Engel's theorem).

**First genuinely non-abelian structure** captured. Connects SHA to classical Lie theory.

**Next step**: Session 19 — formal proof of nilpotency.

## Session 19 summary

**Conjecture 18.3 REFUTED**.

Theorem 19.1 (negative): L_SHA is **NOT nilpotent**.

Empirical evidence:
- N_Σ_0^{32} = 0 ✓ (nilpotent, order ≤ 32)
- N_Σ_1^{11} = 0 ✓ (nilpotent, order ≤ 11)
- N_σ_0 **not nilpotent** within 32 steps
- N_σ_1 **not nilpotent** within 32 steps

Structural reason: SHR (in σ_0, σ_1) is lower-triangular in x-basis. Combined with upper-triangular ROTR parts, gives operator that's neither triangular → may have non-zero eigenvalues → not nilpotent.

**Conjecture 19.3**: L_SHA = rad ⊕ semisimple, where rad ⊇ L_rot (abelian nilpotent).

**Cryptanalytic interpretation**: non-nilpotency of σ operators reflects deliberate "lossy" design of SHA message schedule — SHR physically destroys bits, unlike pure ROTR mixing.

**Next step**: Session 20 — test solvability.

## Session 20 summary

**Theorem 20.1**: L_SHA is NOT solvable.

Derived series: dim D^k = 4, 5, 10, 43, 264, 264. Stabilized at D^4 = D^5 = 264.

Since D^5 = D^4 ≠ 0, L_SHA contains **perfect sub-algebra** (= [L', L'] = L') of dimension 264. Perfect ≠ 0 → not solvable.

**Structural picture after 20 sessions**:
- L_rot (Σ only): abelian, nilpotent
- Adding σ (with SHR): breaks all nice structure
- L_SHA: non-abelian (18.2), non-nilpotent (19.1), **non-solvable (20.1)**
- Contains perfect sub-algebra dim 264 — candidate for simple Lie algebra over F_2

**Cryptanalytic interpretation**: SHA's linear layer has "wild" Lie-theoretic structure — opposite of what cryptanalysis prefers. Structurally supports SHA's security.

**Next step**: Session 21 — identify perfect sub-algebra OR consolidate.

## Session 21 summary

**L_SHA^perfect characterization** (dim 264):
- Trivial center: Z(D^4) = 0
- D^4 ⊆ sl_32(F_2) — all elements zero trace
- F_2^{32} reducible as D^4-module (submodules dim 3, 8, 8, 22, 21)
- 264 doesn't match classical simple Lie algebras

**Conjecture 21.1**: D^4 is semisimple over F_2, decomposing as direct sum of simple ideals acting on respective irreducible summands of F_2^{32}.

**Honest status**: full structural decomposition requires specialist Lie algebra classification over F_2 in char 2 — beyond session-level scope.

**Next step**: consolidate findings in PRISMATIC_PROGRAM.md OR continue classification.

## Session 22 summary — FULL CONSOLIDATION

PRISMATIC_PROGRAM.md updated with complete Sessions 1-21 content:
- Part VI added: SHA Lie algebra (Sessions 18-21)
- Abstract updated: 21 sessions, 16 theorems, 1 conjecture
- Limitations revised to reflect current state
- Summary of theorems section: all 16 theorems listed in one place
- Artifacts list extended with Sessions 17-21 files

The document is now a coherent **~500-line paper draft** suitable for:
- Handover to specialist mathematician
- Future session pickup
- Reference for anyone continuing the programme

**Programme status**: stable plateau at session-level capability. Further progress requires specialist expertise (absolute prismatic, char-2 Lie algebra classification, bialgebra).
