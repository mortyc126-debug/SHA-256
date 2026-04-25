# Session 25: Order of full SHA-256 linear round

**Дата**: 2026-04-25
**Цель**: compute the order of the full SHA-256 round function, restricted to its linear part.

## Setup

A standard SHA-256 round on state (a, b, c, d, e, f, g, h) ∈ (F_2^{32})^8:

```
T_1 = h + Σ_1(e) + Ch(e, f, g) + K_t + W_t
T_2 = Σ_0(a) + Maj(a, b, c)
(a, b, c, d, e, f, g, h) ← (T_1+T_2, a, b, c, d+T_1, e, f, g)
```

**Linear part** (drop nonlinear Ch, Maj and the input scalars K, W):

```
R: (a, b, c, d, e, f, g, h) ↦ (Σ_0(a) ⊕ Σ_1(e) ⊕ h,  a,  b,  c,  d ⊕ Σ_1(e) ⊕ h,  e,  f,  g)
```

R is a 256×256 invertible linear operator on F_2^{256}.

## Main result

**Theorem 25.1.** The full SHA-256 linear round R has

$$\boxed{\mathrm{ord}(R) = 448 = 2^6 \cdot 7}$$

on F_2^{256}. Furthermore:
- R is **not** unipotent.
- min-poly_R has degree **256** (= dim, so R is "cyclic" in the sense that F_2^{256} is a single R-cyclic module).
- dim ker(R − I) = **1** (a unique invariant 1-dim subspace).
- **R^7 is unipotent** with nilpotency index **64**.
- R^{64} has order **7**.

So R decomposes as R = R_{ss} · R_u (commuting, in the Jordan–Chevalley sense over F_2 after extension), with R_{ss} of order 7 and R_u unipotent of order 2^6 = 64.

## Where do 7 and 64 come from?

### Factor 64 = 2^6 (unipotent part)

ord(Σ_0) = 32 = 2^5 (Session 23). ord(Σ_1) = 16 = 2^4. The compression of Σ-effects through the register-coupling lifts the unipotent order to 2^6, **one level higher** than max(2^5, 2^4) = 32.

This makes sense: the register cycle smears Σ-applications across 8 positions, increasing the effective nilpotency from max(32, 11) ≈ 32 (Theorem 24.1 nilpotencies) up to **64**, slightly larger than the 32-bit word width.

### Factor 7 (semisimple part)

The register permutation alone (Σ_0 = Σ_1 = 0):
```
a' = h, b' = a, c' = b, ..., g' = f, h' = g
```
has **order 8** (clean 8-cycle a→b→c→d→e→f→g→h→a).

But once Σ_1 turns on, the **e register acquires a self-loop**: e' = d ⊕ Σ_1(e) ⊕ h. This breaks the clean 8-cycle into something with effective period 7.

**Why exactly 7?** Heuristically: 8 registers → 8-cycle, but one register (e) has a non-trivial Σ_1-feedback that shortens the orbit by one position. Computationally verified: R^{64} has order exactly 7.

## Structural interpretation

R sits in the affine group Aff(F_2^{256}) = GL_{256}(F_2) ⋉ F_2^{256}. Its order in GL is 448. The invariant 1-dim subspace ker(R − I) corresponds to a single "rotation-symmetric" combination of all 8 registers — concretely, the state where all registers carry the same constant fixed by Σ_0 + Σ_1 + I (a 1-dimensional joint kernel).

## Cryptographic interpretation

A linear-only SHA-256 would cycle every **448 rounds**. SHA-256 uses 64 rounds — well below the linear period, so distinguishing "round counts mod 448" might leave structural traces if the nonlinearity (Ch, Maj, K, W, ADD-carry) were turned off. With nonlinearity present, R loses this clean periodic structure entirely.

The number 64 (rounds in SHA-256) is interestingly close to the unipotent factor 64. Numerical coincidence with the choice of 64 rounds, but **mathematically these are different concerns**:
- 64 rounds chosen by NIST for security margin against differential attacks.
- 64 = unipotent order is consequence of Σ-cycling in F_2^{32}.
Connection is loose at best.

## Theorem statement

**Theorem 25.1.** Let R: F_2^{256} → F_2^{256} be the linear part of the SHA-256 round (as defined above). Then:

1. R is invertible with ord(R) = 448 = 2^6 · 7.
2. min-poly_R has degree 256, with dim ker(R − I) = 1.
3. R^7 is unipotent of nilpotency 64; R^{64} has order 7.
4. R = R_{ss} R_u, R_{ss} of order 7, R_u unipotent of order 64, [R_{ss}, R_u] = 0.

**Proof.** Direct computation (session_25_round.py). ∎

## Updated theorem count

**19 theorems** after Session 25:
- 1–18: previous sessions
- 19 = **Theorem 25.1**: order of full SHA-256 linear round = 448

## Artifacts

- `session_25_round.py` — builds R, computes order, decomposition
- `SESSION_25.md` — this file

## Status

- ord(R) = 448 confirmed
- Decomposition R = R_{ss}^{ord 7} · R_u^{ord 64} characterized
- Min poly = char poly = degree 256 (cyclic vector exists)

This gives a **complete linear-level characterization** of SHA-256's round function. Nonlinear ops (Ch, Maj, ADD) remain outside this analysis.
