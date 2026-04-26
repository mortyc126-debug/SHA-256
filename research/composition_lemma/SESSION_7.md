# Session 7: Conjecture 21.1 attack plan — D^4 semisimple over F_2?

**Дата**: 2026-04-26
**Статус**: ?OPEN — analytic setup для empirical attack на specialist-territory вопрос.
**Цель**: выбрать ОДИН specialist-territory open question и спланировать session-level path к его разрешению. Цель — РЕАЛЬНЫЙ структурный прогресс, не lateral closure.

**Choice**: Conjecture 21.1 (D^4 = L_SHA^perfect dim 264 — semisimple over F_2?). Single specialist question с potential session-level resolution через computation, не требующая years of specialist study.

---

## 1. Почему именно Conjecture 21.1

Из Session 6 §3.1, три specialist-territory open вопроса:
- (a) Char-2 Lie algebra classification of D^4 (Conjecture 21.1)
- (b) Absolute prismatic site (Bhatt-Scholze framework)
- (c) Bialgebra framework (rotation × pointwise dualization)

**(a) выбрано** по следующим критериям:

| Критерий | (a) Conj 21.1 | (b) Absolute prismatic | (c) Bialgebra |
|---|---|---|---|
| Session-level computability | да (Killing form, ideals — finite computation) | нет (∞-categorical) | нет (substantial new math) |
| Concrete artifact для verify | да (D^4 dim 264 explicit basis from Session 21) | абстрактный | абстрактный |
| Time to first result | ~1-3 sessions | месяцы literature | месяцы literature |
| Cryptanalytic impact if resolved | structural; possibly none direct | high if breakthrough; very low probability | unclear |
| Fail-fast возможно | да (computation bivariant) | нет | нет |

**Решение**: (a). Может быть resolved at session level if reasonable luck; clean closure if fails.

---

## 2. Recap Conjecture 21.1 + объект attack

**Из research/prismatic/SESSION_21.md**:

L_SHA^perfect = D^4 = derived subalgebra от 4-th iteration:
- L_SHA = ⟨Σ_0 - I, Σ_1 - I, σ_0 - I, σ_1 - I⟩_Lie (Z_2-Lie algebra с [A,B] = AB + BA)
- D^k+1 = [D^k, D^k]
- D^4 = D^5 (stabilized) — это perfect subalgebra
- dim D^4 = 264 over F_2
- D^4 ⊆ sl_32(F_2) (trace zero — rank 1023)
- Z(D^4) = 0 (trivial center)
- F_2^32 reducible (cyclic submodules dim 3, 8, 8, 22, 21 — overlapping, не direct summands)

**Conjecture 21.1**: D^4 is semisimple over F_2 — direct sum simple Lie algebras.

**Status**: trivial center + non-solvability указывают на semisimplicity в char 0. Но F_2 (char 2) — есть char-2 pathology.

---

## 3. Theory primer (что значит "semisimple over F_2")

В char 0 (например над ℝ или ℂ), semisimple Lie algebra — определена как:
- Trivial radical (no solvable ideals ≠ 0), ИЛИ эквивалентно
- Killing form K(x,y) = tr(ad_x ∘ ad_y) is non-degenerate, ИЛИ
- Direct sum simple Lie algebras

В char 2 эти три definition'а **не эквивалентны**. Restricted Lie algebras (Jacobson 1937) — корректный framework для char p:
- L = restricted Lie algebra если есть [p]-power map x → x^[p] совместимый с bracket.
- Semisimple restricted = no nontrivial restricted ideals.
- Block-Wilson classification (1988): simple restricted Lie algebras over F_p — classical type + Cartan type (Witt, special, Hamiltonian, contact).

**Для D^4 над F_2**: needs check
1. Has [2]-power structure? (Probably yes — induced from matrix multiplication.)
2. Killing form non-degenerate?
3. If yes — match to Block-Wilson classification.
4. If no — D^4 имеет nontrivial radical, nontrivial restricted-radical structure.

---

## 4. Computational план (3 subgoals для следующих sessions)

### Subgoal A: Killing form non-degenerate?

**Computation**: K(x_i, x_j) = tr(ad_{x_i} ∘ ad_{x_j}) для basis {x_1, ..., x_264} of D^4.
- ad_{x_i}: D^4 → D^4, ad_{x_i}(z) = [x_i, z]
- Each ad_{x_i} is 264 × 264 matrix over F_2
- K is 264 × 264 symmetric matrix over F_2
- **Question**: rank K?

If rank = 264 (full) → K non-degenerate → D^4 semisimple in classical sense → Conjecture 21.1 confirmed strongly.

If rank < 264 → K degenerate → radical может быть нетривиален. Но в char 2 K может быть degenerate **даже** для simple algebras (e.g., psl_2 in char 2). Так что degeneracy alone doesn't refute Conjecture 21.1.

**Cost estimate**: O(264^4) ≈ 5 × 10^9 operations over F_2. Feasible на GPU/CPU за минуты.

**Code spec** (для Session 8):
```python
# Pseudocode
basis = extract_D4_basis_from_session_21()  # 264 matrices in sl_32(F_2)
# Compute structure constants
N = 264
struct = np.zeros((N, N, N), dtype=np.uint8)
for i, j in product(range(N), range(N)):
    bracket = basis[i] @ basis[j] + basis[j] @ basis[i]  # over F_2
    struct[i, j, :] = decompose_in_basis(bracket, basis)
# Killing form
K = np.zeros((N, N), dtype=np.uint8)
for i, j in product(range(N), range(N)):
    K[i, j] = trace_F2(ad(i) @ ad(j))  # ad(i)[k, l] = struct[i, k, l]
# Rank K over F_2
rank = gf2_rank(K)
print(f"Killing form rank: {rank} / 264")
```

### Subgoal B: Minimal ideals of D^4

**Computation**: find minimal nonzero ideals I ⊆ D^4 (subspace closed under brackets [D^4, I] ⊆ I).
- Random element x ∈ D^4
- I_x = ⟨x, [D^4, x], [D^4, [D^4, x]], ...⟩ — smallest ideal containing x
- Iterate over different x; find minimal I_x

Если все minimal ideals — full D^4 itself → D^4 simple (Conjecture stronger version).
Если есть proper minimal ideals I_1, ..., I_k → D^4 not simple, but possibly direct sum L_1 ⊕ ... ⊕ L_k.
Если есть nilpotent ideals → D^4 not semisimple.

**Cost estimate**: O(264^2 · |ideal|) per random x. ~10^6 operations per ideal candidate.

### Subgoal C: [2]-power structure

**Computation**: для каждого basis element x_i, compute x_i^2 (= x_i · x_i in matrix algebra). Verify это лежит в D^4 (Lie subalgebra closed under squaring → restricted).
- If yes → D^4 is restricted Lie algebra → Block-Wilson framework applies.
- If no → some elements squared escape D^4 → D^4 не closed under [2] → unrestricted.

**Cost**: O(264 · 32^3) — trivial.

---

## 5. Cryptanalytic significance — что мы получим

Honestly: **direct attack маловероятен** даже если Conjecture 21.1 разрешена. Lie algebra structure of SHA's linear layer — это **structural fact**, not obviously cryptanalytic exploit.

Но возможные импликации:

### Если D^4 semisimple = direct sum simple ideals L_i

Each L_i acts on irreducible submodule V_i ⊆ F_2^32. Decomposition F_2^32 = ⊕ V_i — это **invariant decomposition** SHA's linear layer.

Implication: **bit-pattern invariants** соответствующие V_i. Each bit-pattern класс является invariant subspace. Если SHA's nonlinear layer (Ch, Maj, ADD, σ message schedule) **respects** decomposition partially → decomposition might be exploitable.

Specifically: could give **structured input class** где SHA acts as smaller "effective" hash. Не break, но reduction в effective state space — тип weak-message attack.

### Если D^4 not semisimple (radical ≠ 0)

Radical = nilpotent ideal. Inside radical, elements have orderly structure (filtration по powers). Может give **slow-mixing subspaces** в SHA — coordinates that scramble slower than average.

Connection с Том III bit5_max signal (IT-4): maybe это residue от Lie radical of D^4? Если так — explanation для IT-4 mechanism.

### Если D^4 simple

Strongest result. SHA's linear layer = single irreducible Lie algebra. Probably means very rigid — minimal exploitable structure. **Reinforces** Composition Lemma (less structure = harder to break).

---

## 6. Risks и mitigation

### Risk 1: Specialist verification needed

Char-2 Lie algebra classification — niche specialist field. Block-Wilson classification existence я знаю, но full apparatus я могу путать. Если получаем result, нужна specialist review для confidence.

**Mitigation**: формулировать as "computation result claims X, would need specialist verification". Honest. Not over-claim.

### Risk 2: Computation correctness

Session 21 уже extracted D^4 basis. Если basis incorrect — все downstream computations wrong. Need verify basis first.

**Mitigation**: Session 8 starts с verifying D^4 basis re-derivation. Independent computation от Session 21 code.

### Risk 3: No cryptanalytic insight even if structure resolved

Most likely outcome: D^4 turns out to be specific simple Lie algebra или их direct sum, no actionable attack.

**Mitigation**: Even null result valuable — adds to structural infrastructure. Same value as Conjecture 21.1 closure.

### Risk 4: Computation takes more than 1-2 sessions

5 × 10^9 operations may need optimization. F_2 arithmetic packed (64 bits per uint64) reduces by 64×. Still nontrivial.

**Mitigation**: Session 8 = setup + small-scale verification; Session 9 = full Killing form; Session 10 = ideals.

---

## 7. Plan следующих sessions

### Session 8: Setup + Killing form computation

- Re-derive D^4 basis (independent от research/prismatic/session_21_perfect.py)
- Implement Lie bracket в F_2-matrix arithmetic
- Compute structure constants C^k_{ij}
- Compute Killing form K
- Compute rank(K) over F_2
- Result: K non-degenerate? Yes/No.

**Expected outcome**: 1 session of focused implementation + computation.

### Session 9: Minimal ideals

- Random element approach
- Find list of minimal ideals
- Test if direct sum: dim L_1 + ... + dim L_k = 264?
- If overlap → L not direct sum — check radical structure

**Expected outcome**: 1 session.

### Session 10: Restricted structure + Block-Wilson matching

- Verify [2]-power closure
- Compute structure of each minimal ideal: dim, derived series, center
- Match to Block-Wilson classification: classical type? Cartan type? Unknown?
- If matched — name the simple algebras
- If unmatched — possibly NEW simple Lie algebra (significant if true; needs specialist verify)

**Expected outcome**: 1 session.

### Session 11: Cryptanalytic translation

- Each L_i acts on V_i ⊆ F_2^32 — describe V_i bit-pattern explicitly
- Connect к SHA bit-level invariants: do V_i correspond to known bias structures (bit5_max, MSB transitions T_67.1)?
- Honest assessment: any exploitable structure derived?

**Expected outcome**: 1 session — final integration.

**Total**: 4-5 sessions для полного разрешения Conjecture 21.1.

---

## 8. Honest probability estimates

- **Killing form non-degenerate** (Conjecture 21.1 confirmed strongly): ~50%.
- **D^4 = direct sum 2-5 simple Lie algebras** (conjecture confirmed): ~40%.
- **D^4 has nontrivial radical** (conjecture refuted): ~20%.
- **Direct cryptanalytic exploit derived**: <5%. Most likely outcome — structural infrastructure без direct attack.
- **Unexpected breakthrough**: <1%, но имеет ненулевую вероятность.

**Decision**: продолжаем потому что значимый структурный прогресс достижим даже при null cryptanalytic result. Pure structural completeness — sufficient justification.

---

## 9. Cross-references

- research/prismatic/SESSION_20.md (D^4 dim 264 derivation).
- research/prismatic/SESSION_21.md (структурные facts: trivial center, sl_32 inclusion, reducibility).
- research/prismatic/PRISMATIC_PROGRAM.md (consolidated Sessions 1-21).
- SESSION_6.md §3.1 (specialist directions catalog).
- Block, Wilson, *"Classification of restricted simple Lie algebras"* (J. Algebra 1988).
- Jacobson, *"Lie Algebras"* (1962, char-p chapter).

## 10. Status

- ✓ Conjecture 21.1 chosen as session-level target
- ✓ Theory primer установлен (semisimplicity in char 2)
- ✓ Computational план (3 subgoals: Killing form, minimal ideals, restricted)
- ✓ Risk mitigation strategy
- ✓ Plan Session 8-11 (4-5 sessions to resolution)
- → Session 8: setup + Killing form computation

**Programme status update**: maintenance mode B-lateral активирован — реальная попытка resolution specialist question, не closure кандидата.

**Decision points для review**:
- §4 computational specs могут потребовать дополнительной разработки в Session 8 при попытке implementation.
- §5 cryptanalytic implications — speculative, может быть пересмотрены после получения concrete results.
- §8 probability estimates — мои оценки, а не based on systematic analysis. Subject to revision.
