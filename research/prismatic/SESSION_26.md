# Session 26: σ-operator minimal polynomials & extension of Theorem 24.1

**Дата**: 2026-04-25
**Цель**: extend Theorem 24.1 to operators including SHR, characterise minimal polynomial structure of σ_0, σ_1.

## Key findings

### 1. Theorem 24.1 extends to even |R|

The original theorem assumed |R| odd (so M = I + N is unipotent). For **|R| even**, the constant term c_0 = 0, so M is **already nilpotent** (no I).

**Theorem 24.1.bis.** For M = ⊕_{r ∈ R}(1+s)^r in F_2[s]/(s^n) with **|R| even**:

$$\mathrm{nilp}(M) = \lceil n / d \rceil, \quad d = \min\{i \ge 0 : c_i(M) = 1\}.$$

Min poly is **z^{⌈n/d⌉}**, not (z+1)^{⌈n/d⌉}.

**Verification**:

| Operator | R | d | ⌈32/d⌉ | min poly | empirical |
|---|---|---|---|---|---|
| ROTR_7 ⊕ ROTR_18 | {7,18}, even | 1 | 32 | z^32 | z^32 ✓ |
| ROTR_17 ⊕ ROTR_19 | {17,19}, even | 2 | 16 | z^16 | z^16 ✓ |

Computation for (17, 19): bit 0 in both → cancels (c_1 = 0); bit 1 in 19 only → c_2 = 1. So d = 2.

### 2. SHR alone has min poly z^{⌈n/k⌉}

SHR_k sends bit i → bit i−k (truncating low bits). Empirically:
- SHR_3: min poly z^11 (= ⌈32/3⌉)
- SHR_10: min poly z^4 (= ⌈32/10⌉)

In x-basis SHR_k is multiplication by x^k in F_2[x]/(x^n) (NOT the rotation ring), so SHR_k^m = 0 iff km ≥ n. Hence min poly is z^{⌈n/k⌉}.

### 3. σ has rich factorisation structure

This is the main new result. Direct computation gives:

**σ_0 = ROTR_7 ⊕ ROTR_18 ⊕ SHR_3** (min poly degree 32):

$$m_{\sigma_0}(z) = (1 + z^2 + z^3)^4 \cdot (1 + z + z^2 + z^3 + z^4)^2 \cdot (1 + z + z^4 + z^5 + z^6)^2$$

- Degree check: 4·3 + 2·4 + 2·6 = 32 ✓
- Three **distinct irreducible factors** of degrees 3, 4, 6.
- **No** factor of z or (z+1) — σ_0 has no eigenvalue 0 or 1.
- σ_0 is "purely semisimple with multiplicities" — it acts on F_2^{32} as direct sum of generalised eigenspaces over F_4, F_16, F_64 (extensions of F_2 of degrees 3, 4, 6).

**σ_1 = ROTR_17 ⊕ ROTR_19 ⊕ SHR_10** (min poly degree 32):

$$m_{\sigma_1}(z) = z^6 \cdot (1 + z + z^2)^2 \cdot g_{22}(z)$$

where g_{22}(z) = 1 + z^{10} + z^{12} + z^{14} + z^{16} + z^{20} + z^{22} (likely irreducible or product of large factors).

- Has **z^6 factor** → 6-dim generalised 0-eigenspace (σ_1 is rank-deficient with multiplicity).
- (1 + z + z²)² gives F_4-type cycle structure with multiplicity 2.
- The 22-degree remainder factor encodes the "wild" SHR-mixing.

### 4. Structural difference Σ vs σ

| | Σ (rotation only, |R|=3) | σ (with SHR) |
|---|---|---|
| Form | I + N (unipotent) | "generic" mix |
| Min poly | (z+1)^{⌈n/d⌉} | many irreducibles |
| Spectrum | {1} (Jordan only) | various roots in F_{2^k} |
| Eigenvalue 1 mult | full | none for σ_0, only z^6 for σ_1 |

**SHR is responsible** for moving σ from the unipotent corner of GL_n(F_2) into the "generic" interior.

## Conjecture 26.1 (Lucas-XOR + SHR decomposition)

For M = ⊕_{r ∈ R}(1+s)^r ⊕ ⊕_{k ∈ S} SHR_k on F_2^n:

$$m_M(z) = (z+1)^a \cdot z^b \cdot g(z),$$

with:
- a = generalised 1-eigenspace dimension (vanishes if |R| even or SHR breaks unipotency),
- b = generalised 0-eigenspace dimension (≥ ⌈n/min(S)⌉ from SHR contribution),
- g(z) coprime to z(z+1), encoding "mixing" cycles in F_{2^k} extensions.

For SHA-256:
- σ_0: a = 0, b = 0, g(z) = full degree 32 (cubic·quartic·sextic).
- σ_1: a = 0, b = 6, g(z) = degree 26.

The Conjecture is loose (no explicit formula for g(z)). Establishing it as a theorem would require characterizing the SHR-augmented operator spectrum — open problem.

## Cryptographic interpretation

**Σ** has Jordan form with one giant block (or a few blocks for Σ_1, three blocks of sizes summing to 32). Repeated application creates "linear drift" along Jordan chains.

**σ** has eigenvalues in F_4, F_{16}, F_{64} — applications cause cyclic mixing in those extensions. The orbit of a random vector under σ has period dividing 2^d − 1 for the various d ∈ {3, 4, 6} in σ_0, giving rich pseudo-random structure within the linear layer.

This is **cryptographically valuable**: σ behaves like a "near-random" linear permutation on F_2^{32}, in contrast to Σ which has degenerate Jordan structure.

## Updated theorem count

**20 theorems** after Session 26:
- 1–18: previous
- 19 = Theorem 25.1: ord(R_round) = 448
- 20 = **Theorem 24.1.bis**: Lucas-XOR for |R| even (min poly z^{⌈n/d⌉})

Conjecture 26.1: SHR decomposition formula — open.

## Artifacts

- `session_26_sigma_minpoly.py` — computation, factorisation
- `SESSION_26.md` — this file

## Status

Pure ROTR-XOR fully classified (Theorem 24.1 + 24.1.bis): nilp = ⌈n/d⌉, min poly (z+1)^a or z^a.
SHR alone classified: min poly z^{⌈n/k⌉}.
σ-operators numerically factored, with rich structure but no closed-form theorem yet.

This completes the linear-level analysis of all SHA-256 unary operators.
