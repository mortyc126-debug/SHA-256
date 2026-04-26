# Session 19: L_SHA nilpotency — CONJECTURE REFUTED

**Дата**: 2026-04-22
**Цель Session 18 переданная**: prove L_SHA nilpotent via Engel's theorem.

## Главный result — Conjecture 18.3 REFUTED

**Теорема 19.1 (negative)**: L_SHA **NOT nilpotent**.

**Доказательство**: For L_SHA to be nilpotent by Engel's theorem, every element must act nilpotently on underlying F_2^{32}. Empirically:

| Generator | Nilpotency test (M^k = 0) |
|---|---|
| N_Σ_0 = Σ_0 − I | N_Σ_0^{32} = 0 ✓ (nilpotent, order ≤ 32) |
| N_Σ_1 = Σ_1 − I | N_Σ_1^{11} = 0 ✓ (nilpotent, order ≤ 11) |
| N_σ_0 = σ_0 − I | **NOT nilpotent** в 32 steps |
| N_σ_1 = σ_1 − I | **NOT nilpotent** в 32 steps |

Since N_σ_0 and N_σ_1 are NOT nilpotent matrices, Engel's hypothesis fails. Moreover:

**Corollary 19.2**: The ideal ⟨N_σ_0, N_σ_1⟩ contains non-nilpotent elements, so L_SHA is not nilpotent.

## Структурное понимание — почему σ ломает nilpotency

**Σ_0, Σ_1** = XOR of ROTR_r's. Each ROTR = multiplication by (1+s)^r in F_2[s]/(s^{32}). All upper triangular в s-basis. Their subtraction of I gives strictly upper triangular (zero diagonal) → **nilpotent**.

**σ_0, σ_1** = ROTR + ROTR + **SHR**. SHR is **lower triangular** in x-basis. Combining with upper triangular ROTR parts gives matrix that's **neither upper nor lower triangular** → may be non-nilpotent.

Specifically, σ − I has NON-ZERO DIAGONAL contribution from SHR (depending on specific shift), making it not nilpotent.

## Что это значит

### Теоретически
- **L_SHA is not nilpotent** → доказано
- Is it solvable? (weaker property) — open question
- If neither nilpotent nor solvable → contains simple sub-algebra → much richer structure

### Cryptanalytically
- Non-nilpotent Lie algebra has some elements with **non-zero spectrum** (eigenvalues ≠ 0)
- This means **SHA's σ operations create cycling behavior** in linear action
- Cycling = information preservation/reflection, not just mixing

**Ironically**: non-nilpotency of L_SHA might be **cryptographically GOOD** for SHA — it means σ operations don't just "forget" information (nilpotent mixing), they have structural cycling.

### Sub-algebra structure
- **L_rot** = ⟨Σ_0, Σ_1⟩ IS abelian AND nilpotent (trivially, all elements nilpotent commuting)
- **L_SHA** with σ's is NOT nilpotent
- Middle ground: L_SHA solvable? нужно проверить iterated commutator

## Updated picture of SHA Lie algebra

```
L_SHA (Z_2-Lie algebra, F_2-dim finite)
├── L_rot = ⟨Σ_0, Σ_1⟩
│   ├── Abelian (Theorem 18.1)
│   └── Nilpotent
└── Adding N_σ_0, N_σ_1
    └── Breaks both abelianness AND nilpotency
```

So L_SHA is:
- ✗ NOT abelian (Theorem 18.2)
- ✗ NOT nilpotent (Theorem 19.1)
- ? Solvable (unresolved)
- ? Semisimple / simple (unresolved)

## Dimension considerations

Matrices are 32×32 over F_2, so live in gl_{32}(F_2) = ambient Lie algebra of dimension 32² = 1024.

L_SHA is a sub-algebra of gl_{32}(F_2). Its dimension ≤ 1024.

If L_SHA closes under brackets after several iterations, we get finite dim. The computation of full closure is expensive (timed out в session).

## Revised conjecture

**Conjecture 19.3** (replacing 18.3): L_SHA has structure:

$$\text{rad}(L_{SHA}) \supseteq L_{rot} \text{ (nilpotent radical)}$$

and quotient $L_{SHA} / \text{rad}$ is semisimple over F_2.

This would mean: "rotations form nilpotent structural core, σ's generate semisimple quotient that captures essential cryptographic non-linearity."

**Not proven**. Would require full L_SHA closure + radical decomposition.

## Open questions для Session 20+

### Q1: What is dim(L_SHA)?
Closure of brackets is expensive. Could refine computation or use theoretical bounds.

### Q2: Is L_SHA solvable?
Simpler than semisimple classification. Need to check if derived series terminates.

### Q3: Structural decomposition
Does L_SHA = rad ⊕ semisimple (Levi decomposition over F_2 is subtle)?

### Q4: Connection to attack
Even if we classify L_SHA structurally, does it give cryptanalytic handle?

## Honest reflection

Session 19 refuted previous conjecture. This is GOOD epistemic work:
- Tested hypothesis (Conjecture 18.3: L_SHA nilpotent)
- Found empirical evidence against it (σ not nilpotent)
- Formalized as Theorem 19.1

**Structural insight gained**: SHA's σ operators (with SHR) are fundamentally different from Σ operators (pure ROTR). This reflects the cryptographic design:
- Σ's = rotations (linear mixing, no information loss)
- σ's = rotations + SHR (shift information to oblivion)

SHR destroys bits literally. In Lie algebra: makes operator non-nilpotent in ring-theoretic sense. Cryptographic: makes message schedule "lossy" in controlled way.

**Session 20 target**: test solvability (weaker than nilpotent) of L_SHA. Formal tool.

## Status

- ✓ Verified generators Σ nilpotent, σ NOT nilpotent
- ✓ Refuted Conjecture 18.3 formally (Theorem 19.1)
- ✓ Understood structural reason (SHR breaks nilpotency)
- ✓ Proposed new conjecture 19.3 (Levi-like decomposition)
- → Session 20: test solvability или compute dim(L_SHA)

## Artifacts

- `session_19_nilpotent.py` — nilpotency test for generators
- `SESSION_19.md` — this file
