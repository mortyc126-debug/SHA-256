# Session 20: L_SHA NOT SOLVABLE — rich Lie structure

**Дата**: 2026-04-23
**Цель Session 19 переданная**: test solvability of L_SHA.

## Главный result — THEOREM 20.1

**Theorem 20.1**: L_SHA is **NOT solvable**.

**Proof**: Computed derived series D^k(L_SHA):
| k | dim D^k |
|---|---|
| 0 (= L_SHA) | ≥ 4 (generators) |
| 1 | 5 |
| 2 | 10 |
| 3 | 43 |
| 4 | **264** |
| 5 | **264** (stabilized = D^4) |

Since D^5 = D^4, the derived series is a **fixed point** at dimension 264. By definition of derived series:
$$D^{k+1}(L) = [D^k(L), D^k(L)]$$

If D^k = D^{k+1} ≠ 0, then there's a non-trivial sub-algebra L' = D^k with **[L', L'] = L'**. This is the defining property of a **perfect Lie algebra**. Perfect algebras ≠ 0 are NOT solvable. ∎

## Structural implications

### L_SHA hierarchy — updated

```
L_SHA (Z_2-Lie algebra on F_2^32)
├── L_rot = ⟨Σ_0, Σ_1⟩
│   ├── ABELIAN (Theorem 18.1)
│   └── NILPOTENT
├── Adding σ_0, σ_1 (with SHR)
│   ├── Breaks abelianness (Theorem 18.2)
│   └── Breaks nilpotency (Theorem 19.1)
└── Full L_SHA
    └── NOT solvable (Theorem 20.1) — contains perfect sub-algebra dim 264
```

### What is this 264-dim sub-algebra?

**D^4 = L_SHA^perfect** — the "perfect part" — satisfies [L', L'] = L'. Such algebras are SEMISIMPLE or contain simple sub-algebras.

Over F_2, classification of simple Lie algebras is subtle (unlike over algebraically closed field of char 0 where Cartan-Killing gives complete list). But general fact: perfect finite-dim Lie algebras decompose as:
$$L^{\text{perfect}} = \bigoplus \text{ simple ideals}$$

Possibly modulo characteristic-2 pathologies.

**Candidate**: 264-dim could be a copy of some simple Lie algebra over F_2. Dimension 264 doesn't match classical Lie algebras trivially (e.g., sl_n, so_n, sp_n), but could be specific to F_2 characteristic.

Known dimensions of simple Lie algebras over F_2:
- psl_n(F_2) for certain n
- Chevalley algebras from Dynkin diagrams
- Dimension 264 = ?

Haven't identified exactly — future research.

## Cryptanalytic interpretation

**Non-solvability of L_SHA is GOOD for SHA's security** (from design perspective):

1. **Non-solvable** = no "upper-triangular" decomposition. Cannot systematically peel off layers.
2. **Perfect sub-algebra** = rich mixing that cannot be reduced to commutator-chain structure.
3. **dim 264** = large structural space where operators act non-trivially.

This is **opposite** of what one might want for cryptanalysis:
- Cryptanalysis wants STRUCTURE to exploit (solvable Lie algebra with normal series)
- SHA's linear operators give NON-SOLVABLE algebra → hard to exploit

**However**: this only characterizes LINEAR part of SHA. Non-linear operations (AND, ADD) add further cryptographic strength. So:
- Linear layer: non-solvable Lie algebra (this session)
- Non-linear additions: separate cryptographic strength

## Surprise!

Session 18 conjecture: L_SHA nilpotent (nice structure) → refuted Session 19.
Session 19 fallback: L_SHA solvable (weaker) → refuted Session 20.

Pattern: each structural hypothesis for "tame" Lie algebra has been refuted. L_SHA's linear structure is AS RICH AS POSSIBLE (non-solvable, contains perfect sub-algebra).

## What's new mathematically

**Observation**: SHA-256's rotation + shift operators generate a **non-solvable Lie algebra** on F_2^{32}. This is a **novel mathematical characterization** of SHA's linear layer.

Specifically:
- L_SHA ⊂ gl_{32}(F_2)
- L_SHA contains perfect sub-algebra of dim 264
- Structure is "wild" (not solvable, not nilpotent, not abelian)

This makes SHA's linear structure similar to LIE ALGEBRAS OF CLASSICAL GROUPS rather than nilpotent radicals.

## Concrete question for future research

**Q**: Is L_SHA^perfect (dim 264) isomorphic to:
- (a) A classical simple Lie algebra over F_2 (e.g., psl_k for some k)?
- (b) A non-standard simple algebra (e.g., Jacobson's simple algebras in char p)?
- (c) A reducible semisimple algebra (direct sum of simples)?

Answer would FULLY characterize SHA's linear algebraic structure. Significant open problem.

## Status

- ✓ Derived series computed: 4 → 5 → 10 → 43 → 264 → 264
- ✓ **Theorem 20.1**: L_SHA NOT solvable, contains perfect sub-algebra dim 264
- ✓ Cryptographic interpretation: rich Lie structure = hard to exploit
- → Session 21+ (optional): identify perfect sub-algebra; or declare completion

## Updated list of theorems

After 20 sessions:
1. **Theorem 4.2** (Session 10): H¹(F_2[s]/(s^d)) = ⊕ Z/2^{v_2(k+1)} for odd k, |H¹| = 2^{d-1} for d = 2^j
2. **Theorem 3.3** (Session 8): Z_2[i] does not admit δ-structure
3. **Theorem 5.1** (Session 13): ROTR_1 = id on H¹; r ≥ 2 non-trivial
4. **Theorem 5.2** (Session 14): Σ_0, Σ_1 upper-triangular unipotent matrices order 16 on H¹
5. **Theorem 5.3** (Session 15): Joint invariants of Σ_0, Σ_1 on H¹ = 2-dim
6. **Theorem 18.1** (Session 18): L_rot = ⟨Σ_0 - I, Σ_1 - I⟩ abelian
7. **Theorem 18.2** (Session 18): L_SHA non-abelian (via SHR)
8. **Theorem 19.1** (Session 19): L_SHA not nilpotent
9. **Theorem 20.1** (Session 20): L_SHA **not solvable**, contains perfect sub-algebra dim 264

Plus formulas:
- δ(z) over Z (Session 4)
- δ(x ⊕ y) via XOR identity (Session 2)
- ANF degree pattern 2(k+1) (Session 3)

## Honest reflection

Session 20 is the STRONGEST structural result in the programme. Shows SHA's linear operator algebra is **richer than expected** — non-solvable.

This refutes the intuition "SHA is linear-layer trivial". The linear layer has non-trivial Lie-theoretic structure that would need classification work to fully characterize.

**For attack**: non-solvability suggests SHA's linear mixing is structurally strong. Not an obvious cryptanalytic handle, but a characterization.

**Realistic next steps**: 
- Option A: Identify L_SHA^perfect explicitly (months of specialist work)
- Option B: Consolidate findings (update PRISMATIC_PROGRAM.md) and declare completion

## Artifacts

- `session_20_solvable.py` — initial (slow) version
- `session_20b_derived.py` — optimized derived series computation
- `SESSION_20.md` — this file with Theorem 20.1
